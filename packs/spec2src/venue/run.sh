#!/usr/bin/env bash
# One scored (or smoke) spec2src run under the fixed drill conditions.
# usage: run.sh AGENT BATCH RUN_INDEX [SEED]
#   AGENT      a registered binding (bashy agent list)
#   BATCH      a label; results go to $S2S_HOME/runs/BATCH/results.jsonl
#   RUN_INDEX  1, 2 or 3 for this binding
#   SEED       the batch's order seed, recorded in the row
# env: S2S_HOME, S2S_GRADE_CMD (see env.sh); S2S_TASK (default t1-form);
#      S2S_CAP seconds (default 1800). The quiet-workspace cutoff equals the cap.
set -u
AGENT=${1:?agent}; BATCH=${2:?batch}; IDX=${3:?run index}; SEED=${4:-}
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
: "${S2S_GRADE_CMD:?set S2S_GRADE_CMD to the private grade command}"
TASK=${S2S_TASK:-t1-form}; CAP=${S2S_CAP:-1800}
mkdir -p "$S2S_HOME/runs/$BATCH"
cd "$S2S_BENCH"
env ${SEED:+SPEC2SRC_BATCH_SEED=$SEED} BENCH_GUARD=$S2S_GUARD \
  SPEC2SRC_GRADE_CMD=$S2S_GRADE_CMD SPEC2SRC_GRADE_KEEP=$S2S_HOME/grades \
  SPEC2SRC_SPEC_DIR=$S2S_BENCH/packs/spec2src/$TASK/fixture \
  bashy dag run AGENT="$AGENT" PACK=spec2src TASK="$TASK" RUNS="$S2S_HOME/runs/$BATCH" \
    K=1 RUN_INDEX="$IDX" BUDGET="$CAP" THINK="$CAP" \
  > "$S2S_HOME/runs/$BATCH/$AGENT-$IDX.runner.log" 2>&1 </dev/null
echo "exit=$? $AGENT $BATCH#$IDX"
tail -1 "$S2S_HOME/runs/$BATCH/results.jsonl" 2>/dev/null | cut -c1-800
