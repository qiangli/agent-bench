# Sprint 446 / Story 2140: Claude script delivery versus canonical skill

A single guarded `script,on` pair ran Claude Opus 5.5 on the unchanged
`skill-uptake/t6-pdf-fact` task and grader. Each arm had a 100-second budget
and 20-second quiet period. The pair found no competing bench runner.

The quota refresh returned analyzer door status 502. The runner accepted
measured, nonstale cached Claude subscription rows: 5h 0–1% and week 40%.
Both real-HOME canaries and before/after write-deny controls passed. Neither
arm changed a protected home or recorded a sandbox denial. Vendor usage was
attributed separately: four provider requests per arm, with token counts in
`summary.json`. Raw transcripts, request IDs, and full home paths stay outside
the repository.

Both arms completed the PDF fact task and scored **1/1**. Neither showed
skill discovery or format use. The score difference (script minus canonical)
is **0**; this comparison supports retaining the canonical default. It does
not satisfy S21's per-band matrix or the config-task YAML-versus-JSON view
criterion. The sanitized receipt is `summary.json`; raw guard evidence is
kept locally at `/tmp/s446-s21-claude-script-on-1915b`.
