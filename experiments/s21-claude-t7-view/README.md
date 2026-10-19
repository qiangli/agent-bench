# S21 Claude t7 reader view comparison

Guarded pair on 2026-10-18 PDT, using `scripts/guarded_pair.py` with
`--agent claude-opus5.5 --task t7-json-yaml --model claude-opus-5-5`
`--budget 100 --quiet 20 --view-order yaml,json`. Both arms used the same
skill artifact, task, model, grader, and budget. Only the `bashy chat` reader
view preference differed. The candidate was the read-only seat Bashy build.

| View | Guard | Score | Provider requests | Observed format use |
| --- | --- | --- | ---: | --- |
| YAML | PASS | 1/1 | 5 | none |
| JSON | PASS | 1/1 | 5 | none |

Both arms completed the configuration edit and conversion. Their scores tie;
neither arm showed format use, so this run does not establish a YAML advantage
or a YAML-preferring agent. The JSON canonical fallback remains appropriate.
The other S21 band comparisons required by the plan remain unmeasured; this
pair alone does not satisfy S21 acceptance.

The local raw evidence is `/tmp/s446-s21-claude-t7-view-1933/`. Its pair
manifest recorded `PAIRED`, both arm reports recorded `PASS` with no failures,
and there were no concurrent guarded runs. The YAML arm had refreshed Claude
subscription quota before launch. The JSON arm's refresh returned analyzer
door 502, so it used a nonstale cached Claude row under the bounded exception.
Each arm had one attempt, a 100 second budget, and provider usage recorded in
`summary.json`. Raw vendor transcripts and protected home paths are excluded
from this repository.
