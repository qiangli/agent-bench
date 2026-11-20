# Manager ranking — plan (2026-11-19)

Which current models can **manage a bashy sprint** (conduct other agents) or
**supervise sprint managers**? Public leaderboards rank the candidates;
agent-bench certificates decide. This page is the reusable plan and metric
catalog; the data files beside it are the inputs to `yoke-seedfit`.

## Requirements (operator)

1. **No capability area is dropped.** Math is the only exclusion.
2. **Browser use is first-class** — bashy's browser drives forms and web-UI
   debugging.
3. **Steerability is first-class** — a manager must take corrections from a
   human or another agent mid-run, hold boundaries, hand off, report honestly.
4. **Hands-on managers.** A manager must code and drive the shell at least as
   well as the agents it steers, so it can step in when a worker fails.
   (Same rule as the band ladder: L4 code ≥ the L3 median; nobody reviews
   uphill.)
5. **Missing data is handled fairly** — never scored as 0, never silently
   dropped (rules below).
6. **Anchors** (operator experience): Claude Fable 5.x, Claude Opus 5.5,
   GPT-6.x Astra, GPT-6.x Sol are known-good managers; Claude ahead of Codex.
   Anchors set the *line*, never the weights.

## Candidates (vendors' current front-page models)

| vendor | models |
|---|---|
| Anthropic | Claude Fable 5.2, Claude Opus 5.5, Claude Sonnet 5.5 |
| OpenAI | GPT-6.2 Astra, GPT-6.2 Sol |
| Google | Gemini 4 Carbon, Gemini 4 Neon |
| Moonshot | Kimi K3.1 Pro |
| Meta | Muse Wonder Full (Muse Wonder 1.0 rows stand in, flagged) |
| Z.ai | GLM-5.3 |
| DeepSeek | DeepSeek V4.1 Flash 1017 |

## Areas and weights (`seedfit-manager.yaml`)

Areas are read from a config file (`agent-bench/data/seedfit-manager.yaml`) (`yoke-seedfit --config`, schema
`bashy-seedfit-config-v1`) — not hard-coded. Every matrix area must be listed
or explicitly excluded; a listed area with no rows is an error, so a typo
cannot drop an area.

| area | weight | notes |
|---|---|---|
| coding & terminal (`coding-debug-test`) | .20 | hands-on floor |
| browser use (`browser-use`) | .15 | first-class |
| steerability & collaboration (`steerability-collab`) | .15 | first-class |
| tool use (`tool-use-agentic`) | .10 | |
| review & judging (`judge-review-verify`) | .10 | proxies only |
| orchestration (`orchestration-workflow`) | .10 | proxies only (GDPval, Vending-Bench Arena, RLI) |
| long-horizon (`long-horizon`) | .05 | |
| computer use (`computer-use`) | .05 | |
| security (`security`) | .05 | |
| research (`research-browse`) | .03 | |
| reasoning (`reasoning-knowledge`) | .02 | |
| architecture & planning, multimodal | — | no current public rows: measured by agent-bench (seedfit rejects a configured area with no rows) |
| math | — | excluded |

## Metric catalog

Coverage is out of the 11 candidates. Provenance: **I** independent,
**O** official board, **V** vendor-reported, **A** aggregator, **P** human
preference.

### Coding & terminal
| metric | source | prov | coverage |
|---|---|---|---|
| Terminal-Bench 4.1 | tbench.ai | O | 9 |
| Terminal-Bench 4.0 (Vals re-run, mini-swe-agent) | vals.ai | I | 11 |
| Terminal-Bench 4.0 (AA re-run) | artificialanalysis.ai | I | 11 |
| Vibe Code Bench 1.1 (OpenHands) | vals.ai | I | 11 |
| SWE-Atlas overall | Scale Labs | I | 10 |
| AA Coding Agent Index v2.1 | artificialanalysis.ai | I | ~7 |
| CursorBench 4.1 | cursor.com | V (harness owner) | 4 |
| SWE-Bench Pro V2 | Scale (mirror) | A | sparse |
| WebDev Arena | arena.ai | P | 8+ |

### Browser use
| metric | source | prov | coverage |
|---|---|---|---|
| LiveBench 2.0 browser | livebench.ai | A (runs own evals) | 10 |
| Browser Use Bench v2.1 | browser-use.com | I | 4 + 2 inherited |
| BrowseComp (OSS runs) | Mercor APEX | I | 3 + 2 inherited |
| BrowseComp (vendor) | via aggregators | V | 3 |
| DRACO | via Steel | V | 2 |
| Vals Web Search | vals.ai | I | 1 |

### Steerability & collaboration
| metric | source | prov | coverage |
|---|---|---|---|
| Agent Arena Steering Index (real sessions) | arena.ai | O | 11 |
| Agent Arena Overall | arena.ai | O | 11 |
| Agent Arena Alignment (unauthorized / deceptive actions) | arena.ai | O | 5 |
| HiL-Bench (asks when information is missing) | Scale Labs | I | 6 + 2 inherited |
| MultiChallenge (multi-turn instruction following) | Scale Labs | I | 3 |
| Text Arena: instruction following / multi-turn | arena.ai | P | 3–4 |

### Tool use
| metric | source | prov | coverage |
|---|---|---|---|
| AutomationBench | artificialanalysis.ai | I | 11 |
| MCP-Atlas | Scale Labs | O | 2 + 3 inherited |
| τ³-Banking | artificialanalysis.ai | I | 1 |
| Toolathlon-Verified | model cards | V | 3 |

### Review & judging (proxies — no current code-review board)
| metric | source | prov | coverage |
|---|---|---|---|
| BullshitBench v2 (pushes back on nonsense) | GitHub | I | 11 (Muse Wonder stands in) |
| AA Omniscience (knows what it does not know) | artificialanalysis.ai | I | 11 |
| SimpleQA Verified | Epoch | I | 6 |

### Orchestration and planning (proxies — no current orchestration board)
| metric | source | prov | coverage |
|---|---|---|---|
| GDPval-AA v2.1 | artificialanalysis.ai | I | 8 + 2 inherited |
| Vending-Bench Arena (multi-agent) | Andon Labs | I | ~6 |
| Remote Labor Index | Scale Labs | I | 3 |

### Long-horizon
| metric | source | prov | coverage |
|---|---|---|---|
| LiveBench long_agentic | livebench.ai | A | 10 |
| Vending-Bench 2 | Andon Labs (+ Epoch mirror) | O / A | 8 + 2 inherited |

### Computer use
| metric | source | prov | coverage |
|---|---|---|---|
| OSWorld 2.1 | model cards | V | 6 |

### Security
| metric | source | prov | coverage |
|---|---|---|---|
| Vals CyberBench v1.1 | vals.ai | I | 6 |
| AA Cyber Index (+ CWE-Bench, DeepsecBench, CyberGym-E2E) | artificialanalysis.ai | I | 6 |
| ExploitGym | cybergym.io | V | 3 |
| Model-card cyber suites | vendors | V | 10 |

### Research
| metric | source | prov | coverage |
|---|---|---|---|
| HLE-Diamond (AA run) | artificialanalysis.ai | I | 11 |
| Parallel Search Intelligence | parallel.ai | I (search vendor) | 10 |
| LiveBench research | livebench.ai | A | ~10 |
| HLE with tools | model cards | V | 6 |

### Reasoning
| metric | source | prov | coverage |
|---|---|---|---|
| AA Intelligence Index v5 | artificialanalysis.ai | I | 11 |
| CritPt agentic-hard | artificialanalysis.ai | I | 11 |
| Epoch Capabilities Index | epoch.ai | A | 9 |
| ARC-AGI-3 | arcprize.org | O | 5 |
| HLE-Diamond (Scale) | Scale Labs | I | 8 |
| Vals Index | vals.ai | A | 8 |

### Deliberately left out
- Math (AIME etc.) — operator exclusion.
- Superseded board versions (Terminal-Bench 2.x/3.0, SWE-bench Verified,
  OSWorld-Verified, BFCL v4, METR) — replaced above; no current-model rows.
- GPQA — saturated, no longer run on new models.
- AA IFBench — no current-model data.

## Missing data — fair handling

A missing cell is filled in this order; every filled cell is flagged:

1. **Measured** value. Vendor-reported and human-preference rows are
   discounted (0.5 via the fit's source offset); a run without the discount
   is reported beside it.
2. **Inherited** from the newest measured predecessor of the *same line* on
   the *same board version* (GPT-6 Astra → GPT-6.2 Astra; Fable 5.1 →
   Fable 5.2). No uplift; wider uncertainty; replaced as soon as a real row
   exists. Never across tiers or vendors. Disclosed counter-example:
   Terminal-Bench 4.1 GPT-6 Luna 15.2 < GPT-5.6 Luna 17.6.
3. **The model's own conservative bound** in that area (from its measured
   benchmarks there).
4. **Batch floor** (lowest score minus the board's published ±) — and the
   model is flagged *must be measured* by agent-bench.

Sparse boards are coverage-weighted (models present ÷ 11), never excluded.
Ranking uses the conservative bound (score − 2·uncertainty), so thin data
costs confidence, not the whole score.

## Ranking

Per area: the seedfit item-response fit (benchmark difficulty and
discrimination, harness and source offsets) over that area's rows.
Then, per model:

- **role score** = weighted sum of area scores (weights above);
- **weakest area** — a manager is capped by its weakest required area;
- **hands-on check** — coding & terminal ≥ the median anchor;
- **anchor line** — lowest anchor's role score minus its 90% interval.

Models above the line and passing the hands-on check are **candidates**;
within one interval of the line are **near**.

## Steps

| # | step | status |
|---|---|---|
| 1 | seedfit reads areas from `--config` (no hard-coded list) | **done** (tests green; default output unchanged) |
| 2 | data files in `agent-bench/data/`: `benchmark-matrix-2026-11.tsv` (451 rows), `lineage-2026-11.tsv`, `seedfit-manager.yaml` | **done** |
| 3 | seedfit `--per-area` (manager profile), `--lineage`, declared scales `[range LO..HI]` / `[elo anchor A]` so Elo, $ and index metrics are fitted, not skipped | **done** (tests green) |
| 4 | run → `profile-2026-11-19.*` (primary), `profile-2026-11-19-worstcase.*` (sensitivity), summary `results-2026-11-19.md`; equal area weights, hands-on as a relative dominance gate; bashy viewer | **done** |
| 5 | agent-bench certificates on the gate host: `l2`, `steer`, `review`, `manager` (+ a new `browser` pack) for candidates and near models, anchors as controls | operator go-ahead |

## Known limits

- No public board measures orchestration, code review or steering of *other
  agents* directly; those areas are proxies until agent-bench measures them.
- Newest releases (GPT-6.2, Gemini 4 Neon) lack rows on several boards.
- Many browser, computer-use and security numbers are vendor-reported.
- agent-bench has no browser pack yet.
