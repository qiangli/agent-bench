#!/usr/bin/env python3
"""Grade the installed app and the artifacts of the operate drill."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from arm_home import HOME_NAME


def protected(workspace, fixture):
    for source in sorted(fixture.rglob("*")):
        if source.is_file():
            name = source.relative_to(fixture)
            target = workspace / name
            try:
                if target.is_file() and target.read_bytes() == source.read_bytes():
                    continue
            except OSError:
                pass
            return "FAIL", f"{name} changed or missing"
    return "PASS", ""


def contract(fixture, bindir):
    conform = shutil.which("conform")
    if not conform:
        return "INCONCLUSIVE", "conform unavailable"
    env = os.environ.copy()
    for key in ("DISPLAY", "WAYLAND_DISPLAY"):
        env.pop(key, None)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy2(fixture / "CONTRACT.md", tmp)
            shutil.copytree(fixture / "examples", Path(tmp) / "examples")
            done = subprocess.run(
                [os.path.abspath(conform), "run", "CONTRACT.md", "--path", str(bindir),
                 "--fresh-home", "--timeout", "120s", "--json"],
                cwd=tmp, env=env, capture_output=True, timeout=600)
        if done.returncode:
            return "FAIL", f"conform exited {done.returncode}"
        rows = json.loads(done.stdout)
        if isinstance(rows, list) and rows and all(
                isinstance(row, dict) and row.get("status") == "PASS" for row in rows):
            return "PASS", ""
        return "FAIL", "expected passing contract results"
    except subprocess.TimeoutExpired:
        return "FAIL", "conform timed out"
    except (ValueError, OSError):
        return "FAIL", "could not run conform or read its results"


def run_answer(path):
    try:
        answer = json.loads(path.read_text())
        expected = {"schema_version": "bashy-form-v1", "id": "drill-1", "status": "pending"}
        if (isinstance(answer, dict) and isinstance(answer.get("url"), str)
                and all(answer.get(k) == v for k, v in expected.items())):
            return "PASS", ""
    except (OSError, ValueError):
        pass
    return "FAIL", "missing or invalid answer.json"


def serve(page, definition):
    try:
        content = page.read_text()
        for field in json.loads(definition.read_text())["fields"]:
            if field["label"] not in content:
                return "FAIL", f"missing field label {field['label']}"
    except (OSError, ValueError):
        return "FAIL", "could not read page or field labels"
    return "PASS", ""


def report(path):
    try:
        statuses = {}
        for line in path.read_text().splitlines():
            step, code = line.split()
            statuses[step] = int(code)
        return statuses or None
    except (OSError, ValueError):
        return None


def grade(workspace, fixture):
    arm = os.environ.get("BENCH_SPEC2SRC_ARM_DIR")
    home = Path(arm) / HOME_NAME if arm else Path(os.environ["HOME"])
    bindir = home.absolute() / ".local/bin"
    launcher = bindir / "form"
    installed = launcher.is_file() and os.access(launcher, os.X_OK)
    checks = {
        "protected": protected(workspace, fixture),
        "install": ("PASS", "") if installed else ("FAIL", "missing executable form"),
        "contract": contract(fixture, bindir),
        "run": run_answer(workspace / "answer.json"),
        "serve": serve(workspace / "page.html", fixture / "examples/contact.json"),
    }
    layers = {name: status for name, (status, _) in checks.items()}
    verdict = next((v for v in ("FAIL", "INCONCLUSIVE") if v in layers.values()), "PASS")
    why = next((f"{name}: {reason}" for name, (status, reason) in checks.items()
                if status == verdict and reason), "all checks passed")
    return {"verdict": verdict, "layers": layers, "points": 2 if verdict == "PASS" else 0,
            "fail": verdict == "FAIL", "why": why, "void": False,
            "report": report(workspace / "report.txt")}


if __name__ == "__main__":
    print(json.dumps(grade(Path(sys.argv[1]), Path(sys.argv[2]))))
