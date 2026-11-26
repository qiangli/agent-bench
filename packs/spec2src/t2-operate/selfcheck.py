#!/usr/bin/env python3
"""Exercise the operate task offline, including its pack-runner entry point."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TASK = Path(__file__).resolve().parent
FIXTURE = TASK / "fixture"
SCRIPTS = TASK.parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from arm_home import HOME_NAME


def exercise(root):
    workspace = root / "workspace"
    shutil.copytree(FIXTURE, workspace)
    home = root / HOME_NAME
    home.mkdir()
    tools = root / "tools"
    tools.mkdir()
    stub = tools / "conform"
    stub.write_text(
        "#!/bin/sh\n"
        # The DAG test runs in the workspace. Only the grader requests JSON.
        'if [ "$7" = 120s ]; then\n'
        '  [ "$*" = "run CONTRACT.md --path $EXPECTED_BIN --fresh-home --timeout 120s --json" ] &&\n'
        '    [ -z "${DISPLAY+x}${WAYLAND_DISPLAY+x}" ] &&\n'
        '    [ ! -e form ] && [ -f CONTRACT.md ] && [ -f examples/contact.json ] || exit 1\n'
        'fi\n'
        """echo '[{"name":"F-01","status":"PASS","detail":"ok"}]'\n""")
    stub.chmod(0o755)
    env = dict(os.environ, HOME=str(home), PATH=str(tools) + os.pathsep + os.environ["PATH"],
               EXPECTED_BIN=str(home / ".local/bin"), PYTHONDONTWRITEBYTECODE="1")
    env.pop("BENCH_SPEC2SRC_ARM_DIR", None)

    def grade(**overrides):
        command = [sys.executable, str(SCRIPTS / "pack_runner.py"), "grade", "--pack",
                   "spec2src", "--task", "t2-operate", "--workspace", str(workspace),
                   "--fixture", str(FIXTURE)]
        return json.loads(subprocess.check_output(command, env={**env, **overrides}, timeout=30))

    untouched = grade()
    assert untouched["verdict"] == "FAIL" and untouched["why"].startswith("install:"), untouched
    assert untouched["report"] is None, untouched

    subprocess.run(["sh", str(TASK / "reference/operate.sh"), str(workspace)],
                   env=env, check=True, stdout=subprocess.DEVNULL, timeout=30)
    passed = grade(BENCH_SPEC2SRC_ARM_DIR=str(root), HOME=str(root / "grader-home"),
                   DISPLAY="test", WAYLAND_DISPLAY="test")
    assert passed["layers"] == dict.fromkeys(("protected", "install", "contract", "run", "serve"),
                                             "PASS"), passed
    assert (passed["verdict"], passed["points"], passed["fail"], passed["void"]) == (
        "PASS", 2, False, False), passed
    assert passed["report"] == dict(build=0, test=0, install=0, run=0, serve=143), passed

    dag = workspace / "dag.md"
    original = dag.read_bytes()
    dag.write_bytes(b"!" + original[1:])
    changed = grade()
    assert changed["verdict"] == "FAIL" and changed["layers"]["protected"] == "FAIL", changed
    assert "dag.md" in changed["why"], changed
    dag.write_bytes(original)

    answer = workspace / "answer.json"
    contents = answer.read_bytes()
    answer.unlink()
    missing = grade()
    assert missing["verdict"] == "FAIL" and missing["why"].startswith("run:"), missing
    assert missing["layers"]["run"] == "FAIL" and missing["fail"], missing
    answer.write_bytes(contents)

    unknown = grade(PATH=str(root / "empty-path"))
    assert unknown["verdict"] == unknown["layers"]["contract"] == "INCONCLUSIVE", unknown
    assert unknown["points"] == 0 and not unknown["fail"], unknown
    page = workspace / "page.html"
    content = page.read_text()
    page.write_text(content.replace("Full name", ""))
    incomplete = grade(PATH=str(root / "empty-path"))
    assert incomplete["verdict"] == "FAIL" and incomplete["why"].startswith("serve:"), incomplete
    page.write_text(content)

    (workspace / "report.txt").write_text("unparseable")
    advisory = grade()
    assert advisory["verdict"] == "PASS" and advisory["report"] is None, advisory


def main():
    hashes = {str(p.relative_to(FIXTURE)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in FIXTURE.rglob("*") if p.is_file()}
    manifest = (TASK / "task.yaml").read_text().split("sha256:\n")[1]
    assert hashes == dict(line.strip().split(": ") for line in manifest.splitlines())
    with tempfile.TemporaryDirectory(prefix="spec2src-operate-") as tmp:
        try:
            exercise(Path(tmp).resolve())
        finally:
            subprocess.run([sys.executable, str(SCRIPTS / "reap.py"), tmp], check=True)
    print("spec2src/t2-operate selfcheck: ok")


if __name__ == "__main__":
    main()
