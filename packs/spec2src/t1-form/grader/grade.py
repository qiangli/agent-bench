#!/usr/bin/env python3
"""Snapshot a spec-to-source candidate and consume a private venue verdict.

The venue owns all behavioural checks. This adapter reports only aggregate
outcomes; assertion details and hidden case material never enter the record.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path


LAYERS = ("cli", "hidden", "ui")
VERDICTS = {"PASS", "FAIL", "INCONCLUSIVE"}


def reported_accounting() -> dict[str, int | None]:
    """Use only isolated, structured provider receipts; leave absent data unknown."""
    account = {"tokens_in": None, "tokens_out": None,
               "agent_visible_tool_calls": None, "underlying_commands": None}
    arm_name = os.environ.get("BENCH_SPEC2SRC_ARM_DIR") or os.environ.get("SPEC2SRC_ARM_DIR")
    if not arm_name:
        return account
    arm = Path(arm_name)
    if not arm.is_dir():
        return account
    tool = os.environ.get("BENCH_SPEC2SRC_TOOL") or os.environ.get("SPEC2SRC_TOOL")
    if tool == "claude":
        messages: dict[str, dict] = {}
        for path in arm.rglob("*.jsonl"):
            if ".claude" not in path.parts or "projects" not in path.parts:
                continue
            try:
                with path.open(encoding="utf-8", errors="replace") as source:
                    for line in source:
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue
                        if not isinstance(event, dict):
                            continue
                        message = event.get("message", {})
                        if event.get("type") != "assistant" or not isinstance(message, dict):
                            continue
                        key = message.get("id") or event.get("uuid")
                        if key:
                            messages[str(key)] = message
            except OSError:
                continue
        usage = [message["usage"] for message in messages.values()
                 if isinstance(message.get("usage"), dict)]
        if usage and all(isinstance(item.get("input_tokens"), int) and
                         isinstance(item.get("output_tokens"), int) for item in usage):
            account["tokens_in"] = sum(item["input_tokens"] for item in usage)
            account["tokens_out"] = sum(item["output_tokens"] for item in usage)
        calls = {}
        for message in messages.values():
            for block in message.get("content", []) if isinstance(message.get("content"), list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("id"):
                    calls[block["id"]] = block
        if messages:
            account["agent_visible_tool_calls"] = len(calls)
            account["underlying_commands"] = sum(block.get("name") in ("Bash", "bash", "exec_command")
                                                 for block in calls.values())
    elif tool == "codex":
        final_usage = None
        calls = {}
        found = False
        for path in arm.rglob("*.jsonl"):
            if ".codex" not in path.parts or "sessions" not in path.parts:
                continue
            try:
                with path.open(encoding="utf-8", errors="replace") as source:
                    for line in source:
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue
                        if not isinstance(event, dict):
                            continue
                        found = True
                        payload = event.get("payload", {})
                        if not isinstance(payload, dict):
                            payload = {}
                        if event.get("type") == "event_msg" and payload.get("type") == "token_count":
                            info = payload.get("info") or {}
                            final_usage = info.get("total_token_usage") or final_usage
                        elif event.get("type") == "turn.completed":
                            final_usage = event.get("usage") or final_usage
                        if event.get("type") in ("item.started", "item.completed"):
                            item = event.get("item", {})
                            if isinstance(item, dict) and item.get("id"):
                                calls[item["id"]] = item.get("type")
            except OSError:
                continue
        if isinstance(final_usage, dict):
            incoming = final_usage.get("input_tokens")
            outgoing = final_usage.get("output_tokens")
            if isinstance(incoming, int) and isinstance(outgoing, int):
                account["tokens_in"] = incoming
                account["tokens_out"] = outgoing
        if found and calls:
            account["agent_visible_tool_calls"] = len(calls)
            account["underlying_commands"] = sum(kind == "command_execution" for kind in calls.values())
    return account


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(workspace: Path, destination: Path) -> str:
    """Archive every workspace entry except Git metadata, without dereferencing links."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz", dereference=False) as archive:
        for path in sorted(workspace.rglob("*")):
            relative = path.relative_to(workspace)
            if ".git" in relative.parts or path == destination:
                continue
            archive.add(path, arcname=str(relative), recursive=False)
    return sha256(destination)


def rate(results: list[dict], layer: str) -> dict[str, int | float | None]:
    statuses = [item.get("status") for item in results if item.get("layer") == layer]
    passed = sum(status == "PASS" for status in statuses)
    counted = sum(status in ("PASS", "FAIL") for status in statuses)
    return {"passed": passed, "counted": counted,
            "rate": round(passed / counted, 4) if counted else None}


def result(verdict: str, layers: dict[str, str], reason: str, digest: str,
           task_digest: str | None, elapsed: float, results: list[dict] | None = None,
           void: bool = False, classification: str | None = None) -> dict:
    results = results or []
    visible = rate(results, "cli")
    hidden = rate(results, "hidden")
    return {
        "points": 2 if verdict == "PASS" else 0,
        "fail": verdict == "FAIL",
        "why": reason,
        "void": void,
        "verdict": verdict,
        "classification": classification or ("unclassified" if verdict == "INCONCLUSIVE"
                                             else "candidate" if verdict == "FAIL" else "confirmatory"),
        "layers": layers,
        "visible_pass_rate": visible["rate"],
        "visible_passed": visible["passed"],
        "visible_counted": visible["counted"],
        "hidden_pass_rate": hidden["rate"],
        "hidden_passed": hidden["passed"],
        "hidden_counted": hidden["counted"],
        "snapshot_sha256": digest,
        "task_sha256": task_digest,
        "grader_seconds": round(elapsed, 3),
        "binding": {"agent": os.environ.get("BENCH_SPEC2SRC_AGENT"),
                    "tool": os.environ.get("BENCH_SPEC2SRC_TOOL"),
                    "model": os.environ.get("BENCH_SPEC2SRC_MODEL")},
        "batch_seed": os.environ.get("SPEC2SRC_BATCH_SEED"),
        # Provider receipts are retained with the arm evidence. Do not infer
        # usage or cost from a changing TUI counter or price list.
        "cost": None,
        "attempt": int(os.environ.get("BENCH_SPEC2SRC_ATTEMPT", "1")),
        "retries": max(0, int(os.environ.get("BENCH_SPEC2SRC_ATTEMPT", "1")) - 1),
        "crashes": None,
        "human_interventions": None,
        **reported_accounting(),
    }


def grade(workspace: Path) -> dict:
    started = time.monotonic()
    task = workspace / "TASK.md"
    task_digest = sha256(task) if task.exists() and stat.S_ISREG(task.lstat().st_mode) else None
    requested = os.environ.get("BENCH_SPEC2SRC_SNAPSHOT_PATH") or os.environ.get("SPEC2SRC_SNAPSHOT_PATH")
    with tempfile.TemporaryDirectory(prefix="spec2src-snapshot-") as temporary:
        archive = Path(requested) if requested else Path(temporary) / "snapshot.tar.gz"
        digest = snapshot(workspace, archive)
        unknown = {layer: "INCONCLUSIVE" for layer in LAYERS}
        snapshot_only = os.environ.get("BENCH_SPEC2SRC_SNAPSHOT_ONLY", "")
        if snapshot_only in ("launch failed", "provider refused"):
            return result("INCONCLUSIVE", unknown, snapshot_only, digest,
                          task_digest, time.monotonic() - started, void=True,
                          classification="INCONCLUSIVE-venue")
        launcher = workspace / "form"
        try:
            mode = launcher.lstat().st_mode
        except FileNotFoundError:
            mode = 0
        if not stat.S_ISREG(mode) or not mode & 0o111:
            return result("FAIL", {layer: "FAIL" for layer in LAYERS},
                          "missing executable ./form", digest, task_digest,
                          time.monotonic() - started)
        command = os.environ.get("SPEC2SRC_GRADE_CMD", "").strip()
        if not command:
            return result("INCONCLUSIVE", unknown, "no grade venue", digest,
                          task_digest, time.monotonic() - started,
                          classification="INCONCLUSIVE-venue")
        try:
            args = shlex.split(command)
            if not args:
                raise ValueError("empty command")
            completed = subprocess.run([*args, str(archive)], capture_output=True,
                                       text=True, check=False,
                                       timeout=int(os.environ.get("SPEC2SRC_GRADE_TIMEOUT", "1800")))
            if completed.returncode:
                raise ValueError("grade venue failed")
            response = json.loads(completed.stdout)
            if not isinstance(response, dict) or not isinstance(response.get("layers"), dict):
                raise ValueError("invalid response")
            layers = {layer: response["layers"].get(layer) for layer in LAYERS}
            verdict = response.get("verdict")
            if verdict not in VERDICTS or any(value not in VERDICTS for value in layers.values()):
                raise ValueError("invalid verdict")
            combined = ("FAIL" if "FAIL" in layers.values() else
                        "PASS" if all(value == "PASS" for value in layers.values()) else
                        "INCONCLUSIVE")
            if verdict != combined:
                raise ValueError("inconsistent verdict")
            checks = response.get("results")
            if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
                raise ValueError("invalid results")
            if not isinstance(response.get("venue"), dict):
                raise ValueError("invalid venue")
            # Deliberately discard assertion names, details and venue metadata.
            return result(verdict, layers, f"grade venue: {verdict}", digest,
                          task_digest, time.monotonic() - started, checks)
        except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return result("INCONCLUSIVE", unknown, "grade venue error", digest,
                          task_digest, time.monotonic() - started,
                          classification="INCONCLUSIVE-venue")


if __name__ == "__main__":
    print(json.dumps(grade(Path(sys.argv[1]))))
