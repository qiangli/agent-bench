#!/usr/bin/env python3
"""Pinned Codex CLI adapter for one isolated S381 trial.

Stdout remains the provider's JSONL trace followed by one harness-owned receipt.
The receipt is derived from Codex's turn.completed event, never model prose.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROVIDER = "codex"
EXPECTED_CLI = "codex-cli 0.157.1"
SECRET = Path("/run/secrets/s381-auth")


def fail(message: str) -> int:
    print(f"S381 adapter: {message}", file=sys.stderr)
    return 2


def toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    raise ValueError("Codex model options must contain only string, number, or boolean values")


def secret_literals(text: str) -> set[str]:
    values = {text.strip()} if len(text.strip()) >= 16 else set()
    try:
        stack = [json.loads(text)]
    except json.JSONDecodeError:
        stack = []
    while stack:
        value = stack.pop()
        if isinstance(value, dict): stack.extend(value.values())
        elif isinstance(value, list): stack.extend(value)
        elif isinstance(value, str) and len(value) >= 16: values.add(value)
    return values


def redact(text: str, secrets: set[str]) -> str:
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    return text


def main() -> int:
    try:
        model = os.environ["S381_MODEL"]
        task_prompt = os.environ["BASHY_EXPERIMENT_PROMPT"]
        options_text = os.environ["S381_MODEL_OPTIONS"]
        options = json.loads(options_text)
        expected_options_sha = os.environ["S381_MODEL_OPTIONS_SHA256"]
        auth_kind = os.environ.get("S381_AUTH_KIND", "api-key")
    except (KeyError, json.JSONDecodeError) as error:
        return fail(f"invalid adapter environment: {error}")
    if not isinstance(options, dict):
        return fail("model options are not an object")
    actual_options_sha = hashlib.sha256(
        json.dumps(options, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if actual_options_sha != expected_options_sha:
        return fail("model options digest mismatch")
    if not SECRET.is_file():
        return fail("runtime authentication secret is missing")

    secret_text = SECRET.read_text()
    secrets = secret_literals(secret_text)
    child_env = dict(os.environ)
    codex_home = Path(tempfile.mkdtemp(prefix="s381-codex-home-"))
    action_home = Path("/tmp/s381-action-home")
    action_home.mkdir(mode=0o700)
    child_env["CODEX_HOME"] = str(codex_home)
    if auth_kind == "api-key":
        child_env["OPENAI_API_KEY"] = secret_text.strip()
        if not child_env["OPENAI_API_KEY"]:
            return fail("runtime API key secret is empty")
    elif auth_kind == "auth-json":
        shutil.copyfile(SECRET, codex_home / "auth.json")
        os.chmod(codex_home / "auth.json", 0o600)
    else:
        return fail("unsupported authentication kind")

    version = subprocess.run(
        ["codex", "--version"], text=True, capture_output=True, check=False, env=child_env
    )
    cli_version = version.stdout.strip()
    if version.returncode or cli_version != EXPECTED_CLI:
        return fail(f"expected {EXPECTED_CLI}, got {cli_version or 'no version'}")

    command = [
        "codex", "exec", "--json", "--ephemeral", "--ignore-user-config",
        "--ignore-rules", "--strict-config", "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox", "--model", model,
        "--cd", "/work",
        # Do not project provider credentials into model shell commands.
        "--config", "shell_environment_policy.inherit=none",
        "--config", 'shell_environment_policy.set.PATH="/usr/local/bin:/usr/bin:/bin"',
        "--config", 'shell_environment_policy.set.HOME="/tmp/s381-action-home"',
        "--config", 'shell_environment_policy.set.GIT_AUTHOR_NAME="S381 Agent"',
        "--config", 'shell_environment_policy.set.GIT_AUTHOR_EMAIL="s381-agent@invalid"',
        "--config", 'shell_environment_policy.set.GIT_COMMITTER_NAME="S381 Agent"',
        "--config", 'shell_environment_policy.set.GIT_COMMITTER_EMAIL="s381-agent@invalid"',
        "--config", 'shell_environment_policy.set.BASHY_EXPERIMENT_ARM="' + os.environ["BASHY_EXPERIMENT_ARM"] + '"',
        "--config", 'shell_environment_policy.set.BASHY_EXPERIMENT_CANDIDATE="/candidate/bashy"',
        "--config", 'shell_environment_policy.set.BASHY_EXPERIMENT_ASSETS="/opt/s381/arms"',
    ]
    try:
        for key, value in sorted(options.items()):
            if not isinstance(key, str) or not key or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_." for c in key):
                raise ValueError("invalid Codex model option key")
            command.extend(["--config", f"{key}={toml_value(value)}"])
    except ValueError as error:
        return fail(str(error))
    prompt = (
        task_prompt
        + "\n\nExperiment constraint: use shell commands for every workspace read, write, "
          "test, and git action. Do not use apply_patch, file-edit, MCP, web, or "
          "other action tools. The shell is the measured interface."
    )
    command.append(prompt)

    done = subprocess.run(command, text=True, capture_output=True, check=False, env=child_env)
    stdout, stderr = redact(done.stdout, secrets), redact(done.stderr, secrets)
    # JSONL is evidence; emit it unchanged. Codex writes diagnostics to stderr.
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    if done.returncode:
        return done.returncode
    events = []
    try:
        events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    except json.JSONDecodeError:
        return fail("Codex --json emitted invalid JSONL")
    completed = [event for event in events if event.get("type") == "turn.completed"]
    if len(completed) != 1 or not isinstance(completed[0].get("usage"), dict):
        return fail("Codex trace did not contain exactly one turn.completed usage event")
    usage = completed[0]["usage"]
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return fail("Codex usage lacks integer input_tokens/output_tokens")
    action_items = {}
    for event in events:
        if event.get("type") not in ("item.started", "item.completed") or not isinstance(event.get("item"), dict):
            continue
        item = event["item"]
        item_id = str(item.get("id", id(item)))
        action_items[item_id] = item.get("type")
    forbidden = sorted({kind for kind in action_items.values() if kind in (
        "file_change", "mcp_tool_call", "web_search", "computer_action"
    )})
    receipt = {
        "provider": PROVIDER,
        "cli_version": cli_version,
        "model": model,
        "model_options_sha256": actual_options_sha,
        "tokens": input_tokens + output_tokens,
        "token_source": "codex-turn.completed",
        "usage": usage,
        "command_executions": sum(kind == "command_execution" for kind in action_items.values()),
        "forbidden_action_types": forbidden,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
    }
    print("S381_RECEIPT:" + json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
