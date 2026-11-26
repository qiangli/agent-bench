#!/usr/bin/env python3
"""Offline checks for the public pack adapter and its private-venue boundary."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True
PACK = Path(__file__).resolve().parent
TASK = PACK / "t1-form"
GRADER = TASK / "grader" / "grade.py"
RUNNER = PACK.parents[1] / "scripts" / "pack_runner.py"
FILES = ("CONTRACT.md", "SKILL.md", "features.yaml", "examples/contact.json", "TASK.md")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_grade(workspace: Path, env: dict[str, str], through_runner: bool = False) -> dict:
    command = ([sys.executable, str(RUNNER), "grade", "--pack", "spec2src",
                "--task", "t1-form", "--workspace", str(workspace),
                "--fixture", str(TASK / "fixture")]
               if through_runner else [sys.executable, str(GRADER), str(workspace),
                                      str(TASK / "fixture")])
    done = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
    check(done.returncode == 0, f"grader exit {done.returncode}: {done.stderr[:200]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def main() -> int:
    manifest = (TASK / "task.yaml").read_text()
    for name in FILES:
        actual = hashlib.sha256((TASK / "fixture" / name).read_bytes()).hexdigest()
        check(f"  {name}: {actual}" in manifest, f"missing fixture digest: {name}")
    check(sorted(str(p.relative_to(TASK / "fixture")) for p in (TASK / "fixture").rglob("*") if p.is_file()) == sorted(FILES),
          "fixture contains unexpected files")
    check("hidden" not in (TASK / "fixture" / "TASK.md").read_text().lower(),
          "subject prompt mentions private cases")

    with tempfile.TemporaryDirectory(prefix="spec2src-check-") as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        shutil.copytree(TASK / "fixture", workspace)
        (workspace / ".git").mkdir()
        (workspace / ".git" / "HEAD").write_text("not for snapshot\n")
        fake = root / "fake_grade.py"
        fake.write_text(
            "import json, os, sys, tarfile\n"
            "with tarfile.open(sys.argv[1]) as archive:\n"
            "    names = archive.getnames()\n"
            "assert '.git' not in names and '.git/HEAD' not in names\n"
            "assert 'TASK.md' in names and 'form' in names\n"
            "assert os.environ.get('SPEC2SRC_TEST_MARKER') == 'passed-through'\n"
            "print(os.environ['SPEC2SRC_FAKE_RESPONSE'])\n"
        )
        base = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                "SPEC2SRC_GRADE_CMD": f"{sys.executable} {fake}",
                "SPEC2SRC_TEST_MARKER": "passed-through",
                "SPEC2SRC_SNAPSHOT_PATH": str(root / "candidate.tar.gz")}
        null = run_grade(workspace, base)
        check(null["verdict"] == "FAIL" and null["points"] == 0 and null["fail"],
              f"null control: {null}")
        check((root / "candidate.tar.gz").is_file(), "snapshot not retained")

        subprocess.run([sys.executable, str(TASK / "reference" / "solve.py"), str(workspace)],
                       check=True)
        check((workspace / "form").stat().st_mode & 0o111 != 0, "reference launcher not executable")

        cases = [
            ("PASS", {"cli": "PASS", "hidden": "PASS", "ui": "PASS"}, 2, False),
            ("FAIL", {"cli": "PASS", "hidden": "FAIL", "ui": "PASS"}, 0, True),
            ("INCONCLUSIVE", {"cli": "PASS", "hidden": "INCONCLUSIVE", "ui": "PASS"}, 0, False),
        ]
        for verdict, layers, points, failed in cases:
            payload = {"verdict": verdict, "layers": layers,
                       "results": [{"layer": "cli", "name": "visible-1", "status": "PASS", "detail": "visible detail"},
                                   {"layer": "hidden", "name": "PRIVATE_CASE", "status": layers["hidden"], "detail": "PRIVATE_DETAIL"}],
                       "venue": {"internal": "PRIVATE_VENUE"}}
            env = {**base, "SPEC2SRC_FAKE_RESPONSE": json.dumps(payload)}
            answer = run_grade(workspace, env, through_runner=True)
            check(answer["verdict"] == verdict and answer["layers"] == layers, str(answer))
            check(answer["points"] == points and answer["fail"] is failed, str(answer))
            check(answer["snapshot_sha256"] == hashlib.sha256((root / "candidate.tar.gz").read_bytes()).hexdigest(),
                  "snapshot hash mismatch")
            check(answer["task_sha256"] == hashlib.sha256((workspace / "TASK.md").read_bytes()).hexdigest(),
                  "task hash mismatch")
            check(answer["visible_pass_rate"] == 1.0, "visible rate mismatch")
            check("PRIVATE_CASE" not in json.dumps(answer) and "PRIVATE_DETAIL" not in json.dumps(answer)
                  and "PRIVATE_VENUE" not in json.dumps(answer), "private result leaked")
            if verdict == "PASS":
                hard_rule = subprocess.run([sys.executable,
                                            str(PACK.parents[1] / "scripts" / "spec2src_integrity.py"),
                                            json.dumps(answer)], capture_output=True, text=True, check=True)
                integrity = json.loads(hard_rule.stdout)
                check(integrity["verdict"] == "FAIL" and integrity["fail"] and
                      integrity["snapshot_sha256"] == answer["snapshot_sha256"],
                      "integrity override lost grade evidence")

        unset = {key: value for key, value in base.items() if key != "SPEC2SRC_GRADE_CMD"}
        answer = run_grade(workspace, unset)
        check(answer["verdict"] == "INCONCLUSIVE" and answer["why"] == "no grade venue",
              f"unset venue: {answer}")
        arm = root / "arm" / ".claude" / "projects" / "isolated"
        arm.mkdir(parents=True)
        (arm / "turn.jsonl").write_text(json.dumps({
            "type": "assistant", "message": {"id": "msg-1", "usage": {
                "input_tokens": 13, "output_tokens": 7}, "content": [
                {"type": "tool_use", "id": "call-1", "name": "Bash"},
                {"type": "tool_use", "id": "call-2", "name": "Read"}]}}) + "\n")
        usage_env = {**base, "SPEC2SRC_TOOL": "claude", "SPEC2SRC_ARM_DIR": str(root / "arm"),
                     "SPEC2SRC_FAKE_RESPONSE": json.dumps({"verdict": "PASS", "layers": cases[0][1], "results": [], "venue": {}})}
        usage = run_grade(workspace, usage_env)
        check((usage["tokens_in"], usage["tokens_out"],
               usage["agent_visible_tool_calls"], usage["underlying_commands"]) == (13, 7, 2, 1),
              f"structured usage: {usage}")
        base["SPEC2SRC_FAKE_RESPONSE"] = json.dumps({"verdict": "PASS", "layers": cases[0][1], "results": [], "venue": {}})
        done = subprocess.run([sys.executable, str(RUNNER), "validate", "--pack", "spec2src"],
                              env=base, capture_output=True, text=True, timeout=30)
        check(done.returncode == 0, f"validate: {done.stdout} {done.stderr}")
        controls = subprocess.run([sys.executable, str(PACK / "controls.py")],
                                  env=base, capture_output=True, text=True, timeout=30)
        control_rows = [json.loads(line) for line in controls.stdout.splitlines()]
        check(controls.returncode == 0 and len(control_rows) == 4 and
              [row["control"] for row in control_rows] == ["null", "reference", "reference", "reference"] and
              all(row["ok"] for row in control_rows),
              f"controls: {controls.stdout} {controls.stderr}")
    print("spec2src pack self-check: ok (fixture hashes, null, reference x3, PASS/FAIL/INCONCLUSIVE, unset venue, validate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
