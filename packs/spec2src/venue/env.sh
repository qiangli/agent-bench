# Sourced by run.sh and probe.sh. The fixed conditions of a spec2src drill.
# Required from the caller:
#   S2S_HOME       a private working directory OUTSIDE any source tree. It holds:
#                    tools/conform   the standalone judge for the session host
#                    tools/open, tools/xdg-open   no-op stand-ins: the session host is
#                                    headless for a subject (see below)
#                    adapters/       a frozen copy of the bashy adapter cache
#                    guard.sb        the sandbox profile (see guard.sb.template)
#                  and receives runs/, grades/ and probe logs.
#   S2S_GRADE_CMD  the private grade command (takes a snapshot path, prints one JSON object)
: "${S2S_HOME:?set S2S_HOME to the private drill directory}"
S2S_BENCH=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
for need in tools/conform tools/open tools/xdg-open adapters guard.sb; do
  [ -e "$S2S_HOME/$need" ] || { echo "missing $S2S_HOME/$need" >&2; exit 2; }
done
# A plain system shell in every arm. bashy chat otherwise routes the agent's commands
# through bashy, and operator tool settings may pin the same; a tool the task names on
# PATH must resolve to the binary, the same way for every vendor.
S2S_PATH=$(printf '%s' "$PATH" | tr ':' '\n' | /usr/bin/grep -v '/\.bashy/shims$' | paste -sd: -)
export BASHY_FORCE_AGENT_SHELL=0 BENCH_PLAIN_SHELL=1 SHELL=/bin/zsh
export PATH=$S2S_HOME/tools:$S2S_PATH
# Headless for a subject: a build that opens its page with the system `open` or
# `xdg-open` would put a tab in the operator's browser, and the browser's open
# connection can block a build whose server handles one connection at a time (the
# judge then reports a page timeout). The stand-ins in tools/ come first on PATH.
# Logins kept in the OS keychain are invisible in an isolated arm without these opt-ins.
export BENCH_CLAUDE_KEYCHAIN=1 BENCH_AGY_KEYCHAIN=1 BENCH_MUSE_KEYCHAIN=1
# No tool updates itself mid-session.
export OPENCODE_DISABLE_AUTOUPDATE=1
# bashy chat cannot build its adapters in a fresh HOME; every arm reads one frozen copy.
export BASHY_ADAPTER_CACHE=$S2S_HOME/adapters BASHY_HINTS=off
S2S_GUARD=$S2S_HOME/guard.sb
