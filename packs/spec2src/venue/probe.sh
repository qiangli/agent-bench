#!/usr/bin/env bash
# Probe a binding in a real isolated arm, without the task: is it signed in, does it
# have quota, and does the judge the task names resolve on its PATH?
# usage: probe.sh AGENT   -> "PROBE <agent> ok" or "PROBE <agent> FAIL ..."
# A one-shot probe does not work for every tool (opencode answers "Session not found");
# for those, the first scored batch is the check and a launch failure is a venue fault.
set -u
AGENT=${1:?agent}
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
out=$S2S_HOME/runs/probe; mkdir -p "$out"; cd "$S2S_BENCH"
guard=(sandbox-exec -f "$S2S_GUARD")
root=$(mktemp -d /tmp/s2s-probe.XXXXXX); pre=$root/pre; arm=$root/arm; ws=$root/ws; mkdir -p "$pre" "$arm" "$ws"
preenv=(); while IFS= read -r l; do [ -n "$l" ] && preenv+=("$l"); done <<< "$(python3 scripts/arm_home.py prepare --arm-dir "$pre" --tool none)"
tool=$("${guard[@]}" env "${preenv[@]}" bashy agent show "$AGENT" --field tool)
bin=$("${guard[@]}" env "${preenv[@]}" bashy tool show "$tool" --field cli.binary 2>/dev/null); case $bin in */*) ;; *) bin= ;; esac
armenv=(); while IFS= read -r l; do [ -n "$l" ] && armenv+=("$l"); done <<< "$(python3 scripts/arm_home.py prepare --arm-dir "$arm" --tool "$tool" ${bin:+--binary "$bin"})"
acd=$(printf '%s\n' "${armenv[@]}" | sed -n 's/^CLAUDE_CONFIG_DIR=//p'); agh=$(printf '%s\n' "${armenv[@]}" | sed -n 's/^GEMINI_CLI_HOME=//p')
if [ "$("${guard[@]}" env "${armenv[@]}" bashy tool show "$tool" --field cli.launch.trust_preseed 2>/dev/null)" = .claude.json ]; then
  "${guard[@]}" python3 scripts/trust_preseed.py --workspace "$ws" --home "$acd" >/dev/null
elif [ "$tool" = agy ]; then
  "${guard[@]}" python3 scripts/trust_preseed.py --tool agy --workspace "$ws" --home "$agh" >/dev/null
fi
"${guard[@]}" env "${armenv[@]}" BASHY_CHAT_INBOX=off ENABLE_CLAUDEAI_MCP_SERVERS=false BASHY_ALLOW_UNSAFE_AGENT_LAUNCH=1 \
  bashy chat --agent "$AGENT" --yolo -m "Run the command: conform version. Then reply with one line: READY followed by the version it printed." \
  --cwd "$ws" --timeout 180s > "$out/$AGENT.log" 2>&1 </dev/null
rc=$?
if /usr/bin/grep -a -q "READY.*[0-9]\.[0-9]" "$out/$AGENT.log"; then echo "PROBE $AGENT ok"
else echo "PROBE $AGENT FAIL rc=$rc (read $out/$AGENT.log: sign-in, quota, or the judge not on PATH)"; fi
rm -rf "$root"
