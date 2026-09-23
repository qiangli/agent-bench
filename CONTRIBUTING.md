# Contributing

New tasks are welcome — they are data, not code.

## A task must

1. Live in `packs/<pack>/<task>/` with a `task.yaml`, a `fixture/`, a `grader/`
   and, where possible, a `reference/` solution.
2. Be **self-contained**: no network access, no external services, no real
   accounts. Anything the task needs is in `fixture/`.
3. Have a grader that decides pass/fail mechanically (tests, file checks, git
   state). Rubric-scored tasks must list exactly what is scored.
4. Pass `scripts/validate.sh`: the untouched fixture fails, the reference passes.
5. Carry the canary line from `CANARY` in its manifest, graders and references.

## Never include

- **Private system information**: real hostnames, IP addresses, user names,
  e-mail addresses, home directories or absolute local paths, tokens or keys.
  Use placeholders (`host-a`, `user`, `/workspace`, `example.invalid`).
  `scripts/check-private.sh` must pass; enable it as a pre-commit hook once
  per clone with `git config core.hooksPath scripts/hooks`. Never commit
  generated files (`__pycache__`, `*.pyc`): they embed absolute local paths.
- **Material under a non-permissive license.** Contributions are MIT. Do not
  copy code, fixtures, prompts or test suites from GPL/AGPL/LGPL/SSPL/BUSL,
  "non-commercial", or unlicensed sources, or from other benchmarks unless
  their license is OSI-approved permissive (MIT, BSD, Apache-2.0, ISC) and you
  keep its notice. Citing a paper's idea is fine; copying its data is not.
- Content from proprietary products or internal incidents. A task inspired by a
  real incident is rewritten from scratch with invented names.
