#!/usr/bin/env python3
"""Bounded, resumable OCI executor for the frozen Bash# L2 experiment."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from bashsharp_l2_experiment import ARMS, ROOT, digest, rows, tree_digest, validate_manifest
from pack_runner import grade

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r'(?i)(OPENAI_API_KEY[=\"\': ]+)[^\s\"\']+'),
)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, check=False, **kwargs)


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]", text)
    return text


def image_identity(engine: str, image: str) -> str:
    done = run([engine, "image", "inspect", "--format", "{{.Id}}", image])
    if done.returncode or not done.stdout.strip():
        raise ValueError(f"cannot inspect provider image {image}: {done.stderr.strip()}")
    return done.stdout.strip()


def stop_container(engine: str, name: str) -> None:
    run([engine, "stop", "--time", "1", name], timeout=10)
    run([engine, "rm", "--force", name], timeout=10)


def bounded_container(command: list[str], engine: str, name: str, timeout: int) -> tuple[int, str, str, bool]:
    process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired as error:
        stop_container(engine, name)
        stdout, stderr = process.communicate(timeout=10)
        if error.stdout and not stdout: stdout = error.stdout
        if error.stderr and not stderr: stderr = error.stderr
        return 124, stdout or "", stderr or "", True


def base_row(manifest: dict, task: str, repetition: int, arm: str, image_id: str) -> dict:
    fixture = ROOT / "packs/l2" / task / "fixture"
    return {
        "task": task, "repetition": repetition, "arm": arm,
        "model": manifest["model"], "agent": manifest["agent"],
        "provider": manifest["provider"], "provider_cli": manifest["provider_cli"],
        "provider_image_id": image_id,
        "candidate_sha256": manifest["candidate_sha256"],
        "fixture_tree_sha256": tree_digest(fixture),
        "model_options_sha256": manifest["model_options_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
    }


def invoke(args, manifest: dict, task: str, repetition: int, arm: str, image_id: str, log_dir: Path) -> dict:
    fixture = ROOT / "packs/l2" / task / "fixture"
    task_meta = next(item for item in manifest["tasks"] if item["id"] == task)
    row = base_row(manifest, task, repetition, arm, image_id)
    work = Path(tempfile.mkdtemp(prefix="s381-"))
    name = f"s381-{uuid.uuid4().hex[:20]}"
    started = time.monotonic()
    try:
        shutil.copytree(fixture, work / "work")
        if digest(work / "work/TASK.md") != task_meta["task_prompt_sha256"]:
            raise ValueError("copied TASK.md does not match the frozen task prompt")
        assets = work / "assets"
        shutil.copytree(ROOT / "experiments/bashsharp-l2/arms", assets)
        # A real evaluator-only negative control. This directory is intentionally
        # absent from every mount given to the agent principal.
        control = work / "evaluator-only/marker.txt"
        control.parent.mkdir()
        marker = f"S381_PLANTED_READ_{uuid.uuid4().hex}"
        control.write_text(marker + "\n")
        row["negative_control_sha256"] = digest(control)

        environment = {
            "BASHY_EXPERIMENT_ARM": arm,
            "BASHY_EXPERIMENT_CANDIDATE": "/candidate/bashy",
            "BASHY_EXPERIMENT_ASSETS": "/opt/s381/arms",
            "BASHY_EXPERIMENT_PROMPT": task_meta["prompt"],
            "BASHY_EXPERIMENT_BUDGET_SECONDS": str(manifest["budget_seconds"]),
            "S381_MODEL": manifest["model"],
            "S381_MODEL_OPTIONS": json.dumps(manifest["model_options"], sort_keys=True, separators=(",", ":")),
            "S381_MODEL_OPTIONS_SHA256": manifest["model_options_sha256"],
            "S381_AUTH_KIND": args.auth_kind,
        }
        command = [
            args.engine, "run", "--name", name, "--rm", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--pids-limit", str(args.pids_limit), "--memory", args.memory,
            "--cpus", str(args.cpus), "--userns=keep-id",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m", "--network", args.network,
            "--secret", f"{args.secret_name},target=s381-auth,mode=0400",
            "-v", f"{work/'work'}:/work:rw",
            "-v", f"{Path(manifest['candidate_path'])}:/candidate/bashy:ro",
            "-v", f"{assets}:/opt/s381/arms:ro", "-w", "/work",
        ]
        for key, value in environment.items():
            command.extend(["-e", f"{key}={value}"])
        command.append(args.image)
        returncode, stdout, stderr, timed_out = bounded_container(
            command, args.engine, name, manifest["budget_seconds"]
        )
        elapsed = round(time.monotonic() - started, 3)
        terminal = redact(stdout + stderr)
        log_path = log_dir / f"{task}-r{repetition}-{arm}.log"
        log_path.write_text(terminal)
        result = grade("l2", task, work / "work", fixture)
        row.update({
            "points": result["points"], "fail": bool(result["fail"]),
            "terminal_output": terminal[-16000:], "elapsed_seconds": elapsed,
            "provider_exit_code": returncode, "raw_log": str(log_path),
        })
        if marker in terminal:
            row.update({"void": True, "void_reason": "planted evaluator-only marker appeared in agent output"})
            return row
        if timed_out:
            row.update({"void": True, "void_reason": "provider trial exceeded the enforced budget"})
            return row
        receipt_line = next(
            (line.removeprefix("S381_RECEIPT:") for line in reversed(stdout.splitlines()) if line.startswith("S381_RECEIPT:")),
            None,
        )
        try:
            receipt = json.loads(receipt_line) if receipt_line else None
        except json.JSONDecodeError:
            receipt = None
        if returncode != 0:
            row.update({"void": True, "void_reason": f"provider adapter exited {returncode}"})
        elif not isinstance(receipt, dict):
            row.update({"void": True, "void_reason": "provider adapter emitted no valid receipt"})
        elif any((
            receipt.get("provider") != manifest["provider"],
            receipt.get("cli_version") != manifest["provider_cli"],
            receipt.get("model") != manifest["model"],
            receipt.get("model_options_sha256") != manifest["model_options_sha256"],
            receipt.get("prompt_sha256") != task_meta["provider_prompt_sha256"],
            receipt.get("forbidden_action_types") != [],
            not isinstance(receipt.get("command_executions"), int),
            receipt.get("command_executions", 0) < 1,
            not isinstance(receipt.get("tokens"), int), receipt.get("tokens", -1) < 0,
            receipt.get("token_source") != "codex-turn.completed",
        )):
            row.update({"void": True, "void_reason": "provider receipt metadata or usage did not match the manifest"})
        else:
            row.update({
                "tokens": receipt["tokens"], "token_source": receipt["token_source"],
                "provider_usage": receipt.get("usage"),
            })
        return row
    except Exception as error:
        stop_container(args.engine, name)
        row.update({
            "void": True, "void_reason": f"executor error: {type(error).__name__}: {error}",
            "terminal_output": "", "elapsed_seconds": round(time.monotonic() - started, 3),
        })
        return row
    finally:
        shutil.rmtree(work, ignore_errors=True)


def schedule(manifest: dict) -> list[tuple[str, int, str]]:
    jobs = []
    rng = random.Random(str(manifest["seed"]))
    for repetition in range(1, manifest["k"] + 1):
        tasks = [item["id"] for item in manifest["tasks"]]
        rng.shuffle(tasks)
        for index, task in enumerate(tasks):
            rotation = (index + repetition - 1) % len(ARMS)
            jobs.extend((task, repetition, arm) for arm in ARMS[rotation:] + ARMS[:rotation])
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True); parser.add_argument("--raw", required=True)
    parser.add_argument("--image", required=True); parser.add_argument("--engine", default="podman")
    parser.add_argument("--secret-name", default="s381-codex-auth")
    parser.add_argument("--auth-kind", choices=("api-key", "auth-json"), default="auth-json")
    parser.add_argument("--jobs", type=int, default=4); parser.add_argument("--cpus", type=float, default=1)
    parser.add_argument("--memory", default="1500m"); parser.add_argument("--pids-limit", type=int, default=256)
    parser.add_argument("--network", default="slirp4netns")
    parser.add_argument("--limit", type=int, help="run only the first N pending trials (smoke use only)")
    args = parser.parse_args()
    if args.jobs < 1 or args.jobs > 4: parser.error("--jobs must be between 1 and 4")
    if args.limit is not None and args.limit < 1: parser.error("--limit must be positive")
    manifest = json.loads(Path(args.manifest).read_text())
    validate_manifest(manifest)
    if manifest.get("schema") != "bashsharp-l2-v3" or manifest.get("provider") != "codex":
        parser.error("manifest is not the supported Codex v3 experiment")
    if Path(manifest["candidate_path"]).read_bytes()[:4] != b"\x7fELF":
        parser.error("manifest candidate is not a Linux ELF executable")
    if digest(Path(manifest["candidate_path"])) != manifest["candidate_sha256"]:
        parser.error("candidate changed after prepare")
    image_id = image_identity(args.engine, args.image)
    output = Path(args.raw); output.parent.mkdir(parents=True, exist_ok=True)
    log_dir = output.parent / "logs"; log_dir.mkdir(exist_ok=True)
    completed = set()
    if output.exists():
        completed = {(row["task"], row["repetition"], row["arm"]) for row in rows(output)}
    pending = [job for job in schedule(manifest) if job not in completed]
    if args.limit is not None: pending = pending[:args.limit]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool, output.open("a") as stream:
        futures = [pool.submit(invoke, args, manifest, *job, image_id, log_dir) for job in pending]
        for future in concurrent.futures.as_completed(futures):
            stream.write(json.dumps(future.result(), sort_keys=True) + "\n")
            stream.flush(); os.fsync(stream.fileno())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
