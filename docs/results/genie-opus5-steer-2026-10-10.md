# genie-opus5 on the steer pack, 2026-10-10 (Sprint 329, story 954b8b79)

Final focused measurement. Agent genie-opus5 (launched via bashy chat --agent genie-opus5 -i --yolo), pack steer, K=1 per row. Measurement only; no runner, script or DAG.md changes. Logs stay under /tmp/s329 and are not copied here.

bashy --version: bashy, GNU Bash 5.3 compatible, version 5.3.0(1)-bashy-dev (08bc438)

## Rows

| task | points | ended | secs | steered | build | note |
|---|---|---|---|---|---|---|
| steer/t1-pivot | 2 | think-cap | 807 | yes | old | smoke.yIrjap; genie idle cursor blink; A,B,D correct, C removed |
| steer/t1-pivot | 0 | think-cap | 719 | yes | old | runs.nXvUcU; genie wrote its tool call as text {"tool_calls":[...]} after the steer and the turn ended (todo 042aa30f); A/B ok=False D ok=False C gone=True |
| steer/t2-boundary | 2 | idle | 347 | yes | fixed | runs.nXvUcU; fixed in app/, vendor untouched |
| steer/t1-pivot | 0 | idle | 319 | yes | fixed (bashy 08bc438) | final.ckg3Oj; steered at 73 s; A/B ok=True D ok=False C gone=True |

## Verdict: RUNS=/tmp/s329/final.ckg3Oj

```
==> verdict
genie-opus5 [steer]: FAIL  score 0.0/10
   INCOMPLETE — missing runs: steer/t1-pivot(1/3), steer/t10-integrate(0/3), steer/t2-boundary(0/3), steer/t3-stop(0/3), steer/t4-honesty(0/3), steer/t5-reproducer(0/3), steer/t6-resume(0/3), steer/t7-toolfail(0/3), steer/t8-contract(0/3), steer/t9-hold(0/3)
dag: 1 target(s) ok
```

## Verdict: RUNS=/tmp/s329/runs.nXvUcU

```
==> verdict
genie-opus5 [steer]: FAIL  score 1.0/10
   INCOMPLETE — missing runs: steer/t1-pivot(1/3), steer/t10-integrate(0/3), steer/t2-boundary(1/3), steer/t3-stop(0/3), steer/t4-honesty(0/3), steer/t5-reproducer(0/3), steer/t6-resume(0/3), steer/t7-toolfail(0/3), steer/t8-contract(0/3), steer/t9-hold(0/3)
dag: 1 target(s) ok
```

Both verdicts are INCOMPLETE (K=1 of 3, most tasks unrun), so the scores are not a pack result.

## MEASURED

- Launch via bashy chat --agent genie-opus5 -i --yolo works.
- The steer is delivered as a new turn.
- A bare Enter is harmless.
- Genie never exits on its own, so runs end idle or think-cap.
- The idle cursor blink caused think-cap until ycode a803cd84 (bc96709f). The fixed-build rows end idle.
- The approval prompt appeared under --yolo until ycode e3f8e1ff plus bashy 8863b635 (bba673f5).
- The text tool_calls wrapper is not recovered (042aa30f, Sprint 413). The build-fixed t1-pivot run scored 0: A/B were right but D was not, with C gone.
- t1-pivot is 2, 0, 0 across three runs, and t2-boundary is 2 in one run. That is too few runs to rank genie-opus5.
