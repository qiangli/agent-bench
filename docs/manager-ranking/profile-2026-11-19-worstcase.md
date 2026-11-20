# Manager profile — per-area ability (θ)

Each area is fitted on its own (score(m,b) = sigmoid(a_b·θ_m − d_b + h_harness + s_source), regularised quasi-binomial maximum likelihood (dispersion φ from Pearson residuals), Levenberg–Marquardt on the exact Hessian from a fixed start); θ is standardised within the area over the models it covers. Role = weight-averaged θ; weakest = lowest weighted area; hands-on = θ over the hands-on areas. Line = lowest anchor role − 1.645·se. Hands-on is relative: a model *can manage* a worker when its hands-on θ − 1.645·se ≥ the worker's hands-on θ (nobody manages uphill). Missing cells: on a benchmark covering at least 0.50 of the candidates, a candidate without a row gets (lowest observed − 0.05), kept above zero (*floored* column); on sparser boards missing cells are skipped. A model with no real row in an area is flagged *must measure* (ᶠ). Inherited rows come from the same line's predecessor.

| anchor line (role) | anchors |
|---|---|
| -0.31 | fable5.2, opus5.5, gpt6.2-astra, gpt6.2-sol |

## Ranking

| model | role ± se | hands-on ± se | can manage | weakest | verdict | must measure | inherited | floored |
|---|---|---|---|---|---|---|---|---|
| fable5.2 | 1.14 ± 0.20 | 1.03 ± 0.35 | 6: gemini4-neon, gpt6.2-sol, kimi-k3.1-pro, deepseek-v4.1-flash-1017, muse-wonder-full, glm-5.3 | security (-1.19) | anchor | security | 2 | 3 |
| gemini4-carbon | 0.75 ± 0.22 | 1.00 ± 0.35 | 5: gemini4-neon, kimi-k3.1-pro, deepseek-v4.1-flash-1017, muse-wonder-full, glm-5.3 | browser-use (-0.37) | candidate |  | 0 | 5 |
| opus5.5 | 0.57 ± 0.19 | 0.92 ± 0.33 | 4: gemini4-neon, deepseek-v4.1-flash-1017, muse-wonder-full, glm-5.3 | security (-0.62) | anchor |  | 0 | 1 |
| gpt6.2-astra | 0.55 ± 0.26 | 0.66 ± 0.31 | 3: deepseek-v4.1-flash-1017, muse-wonder-full, glm-5.3 | computer-use (-1.80) | anchor | computer-use | 12 | 0 |
| sonnet5.5 | 0.16 ± 0.20 | 0.73 ± 0.30 | 3: deepseek-v4.1-flash-1017, muse-wonder-full, glm-5.3 | security (-1.40) | candidate |  | 0 | 4 |
| gemini4-neon | 0.13 ± 0.28 | 0.25 ± 0.32 | 2: deepseek-v4.1-flash-1017, glm-5.3 | orchestration-workflow (-2.00) | candidate | computer-use, orchestration-workflow | 0 | 15 |
| gpt6.2-sol | 0.13 ± 0.27 | 0.44 ± 0.29 | 2: deepseek-v4.1-flash-1017, glm-5.3 | computer-use (-1.80) | anchor | computer-use | 9 | 4 |
| muse-wonder-full | -0.20 ± 0.20 | 0.08 ± 0.28 | 2: deepseek-v4.1-flash-1017, glm-5.3 | browser-use (-1.37) | candidate |  | 13 | 9 |
| kimi-k3.1-pro | -0.21 ± 0.26 | 0.41 ± 0.29 | 2: deepseek-v4.1-flash-1017, glm-5.3 | computer-use (-1.80) | candidate | computer-use | 3 | 4 |
| deepseek-v4.1-flash-1017 | -0.90 ± 0.27 | -1.02 ± 0.39 | 0:  | computer-use (-1.80) | below line | computer-use | 7 | 7 |
| glm-5.3 | -1.05 ± 0.26 | -0.80 ± 0.32 | 0:  | steerability-collab (-1.85) | below line | browser-use, computer-use | 0 | 8 |

## Area matrix (θ)

| model | browser-use (w 1.00) | coding-debug-test (w 1.00) | computer-use (w 1.00) | judge-review-verify (w 1.00) | long-horizon (w 1.00) | orchestration-workflow (w 1.00) | reasoning-knowledge (w 1.00) | research-browse (w 1.00) | security (w 1.00) | steerability-collab (w 1.00) | tool-use-agentic (w 1.00) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fable5.2 | 0.10 | 1.03 | 1.74 | 2.45 | 0.41 | 1.41 | 1.67 | 2.05 | -1.19ᶠ | 2.07 | 0.77 |
| gemini4-carbon | -0.37 | 1.00 | 0.06 | 1.06 | 1.16 | 1.64 | 1.18 | 1.15 | -0.18 | 0.58 | 0.94 |
| opus5.5 | 0.32 | 0.92 | 1.29 | 0.83 | 0.15 | 1.33 | 0.56 | 1.09 | -0.62 | 0.68 | -0.23 |
| gpt6.2-astra | 1.02 | 0.66 | -1.80ᶠ | 1.02 | 0.94 | 0.23 | 1.41 | 1.01 | 0.70 | 0.39 | 0.46 |
| sonnet5.5 | 0.24 | 0.73 | 0.53 | -0.46 | 0.03 | 0.89 | 0.45 | 0.41 | -1.40 | 0.43 | -0.06 |
| gemini4-neon | 0.98 | 0.25 | -1.80ᶠ | -0.30 | 1.56 | -2.00ᶠ | 0.12 | 0.75 | -0.10 | 0.78 | 1.23 |
| gpt6.2-sol | 0.73 | 0.44 | -1.80ᶠ | -0.74 | 0.58 | 0.09 | 1.02 | 0.71 | 0.66 | 0.04 | -0.34 |
| muse-wonder-full | -1.37 | 0.08 | -0.07 | -0.76 | -0.11 | 1.00 | -0.01 | 0.19 | -0.72 | -0.32 | -0.15 |
| kimi-k3.1-pro | -0.45 | 0.41 | -1.80ᶠ | 0.13 | -1.76 | 1.03 | -0.63 | -0.25 | 2.14 | -0.95 | -0.12 |
| deepseek-v4.1-flash-1017 | -0.95 | -1.02 | -1.80ᶠ | -0.98 | -1.76 | 0.03 | -1.09 | -1.08 | 0.87 | -1.31 | -0.85 |
| glm-5.3 | -1.57ᶠ | -0.80 | -1.80ᶠ | -0.86 | -0.79 | 0.07 | -0.87 | -1.61 | -0.47 | -1.85 | -0.98 |

## Area fits

| area | weight | hands-on | models | items | observations | converged | skipped rows | note |
|---|---|---|---|---|---|---|---|---|
| browser-use | 1.00 | false | 14 | 5 | 39 | true | item-single-model=1 | |
| coding-debug-test | 1.00 | true | 23 | 10 | 104 | true |  | |
| computer-use | 1.00 | false | 10 | 4 | 19 | true | item-single-model=1 | |
| judge-review-verify | 1.00 | false | 13 | 3 | 36 | true |  | |
| long-horizon | 1.00 | false | 17 | 2 | 29 | true |  | |
| orchestration-workflow | 1.00 | false | 21 | 3 | 40 | true |  | |
| reasoning-knowledge | 1.00 | false | 21 | 7 | 95 | true |  | |
| research-browse | 1.00 | false | 20 | 5 | 65 | true |  | |
| security | 1.00 | false | 13 | 6 | 41 | true |  | |
| steerability-collab | 1.00 | false | 14 | 7 | 54 | true |  | |
| tool-use-agentic | 1.00 | false | 24 | 4 | 37 | true |  | |

## Inherited rows

| model | from | benchmark | variant |
|---|---|---|---|
| gpt6.2-astra | gpt6-astra | Browser Use Bench v2.1 | overall |
| gpt6.2-astra | gpt6-astra | BrowseComp | public 130 |
| gpt6.2-astra | gpt6-astra | BrowseComp | full |
| gpt6.2-astra | gpt6-astra | HiL-Bench | overall |
| gpt6.2-astra | gpt6-astra | tau3-bench | banking |
| gpt6.2-astra | gpt6-astra | GDPval-AA v2.1 | overall |
| gpt6.2-astra | gpt6-astra | Vending-Bench Arena | overall |
| gpt6.2-astra | gpt6-astra | Remote Labor Index | overall |
| gpt6.2-astra | gpt6-astra | Vending-Bench 2 | overall |
| gpt6.2-astra | gpt6-astra | Parallel Search Intelligence | overall |
| gpt6.2-astra | gpt6-astra | HLE with search (Parallel) | 100-question subset |
| gpt6.2-astra | gpt6-astra | HLE with tools | overall |
| gpt6.2-sol | gpt6.1-sol | Browser Use Bench v2.1 | overall |
| gpt6.2-sol | gpt6.1-sol | BrowseComp | public 130 |
| gpt6.2-sol | gpt6.1-sol | HiL-Bench | overall |
| gpt6.2-sol | gpt5.6-sol | MCP-Atlas | overall |
| gpt6.2-sol | gpt6.1-sol | GDPval-AA v2.1 | overall |
| gpt6.2-sol | gpt6-sol | Vending-Bench Arena | overall |
| gpt6.2-sol | gpt6-sol | Vending-Bench 2 | overall |
| gpt6.2-sol | gpt6.1-sol | Parallel Search Intelligence | overall |
| gpt6.2-sol | gpt6.1-sol | HLE with search (Parallel) | 100-question subset |
| gpt6.1-sol | gpt5.6-sol | MCP-Atlas | overall |
| gpt6.1-sol | gpt6-sol | Vending-Bench Arena | overall |
| gpt6.1-sol | gpt6-sol | Vending-Bench 2 | overall |
| gpt6-sol | gpt5.6-sol | MCP-Atlas | overall |
| fable5.2 | fable5.1 | MCP-Atlas | overall |
| fable5.2 | fable5.1 | Vending-Bench Arena | overall |
| kimi-k3.1-pro | kimi-k3 | MCP-Atlas | overall |
| kimi-k3.1-pro | kimi-k3 | Toolathlon-Verified | overall |
| kimi-k3.1-pro | kimi-k3 | ARC-AGI-2 | overall |
| muse-wonder-full | muse-wonder | Terminal-Bench 4.1 | overall |
| muse-wonder-full | muse-wonder | SWE-Atlas | overall |
| muse-wonder-full | muse-wonder | SWE-Bench Pro V2 | full |
| muse-wonder-full | muse-wonder | LiveBench 2.0 browser | overall |
| muse-wonder-full | muse-wonder | BrowseComp | public 130 |
| muse-wonder-full | muse-wonder | HiL-Bench | overall |
| muse-wonder-full | muse-wonder | BullshitBench v2 | overall |
| muse-wonder-full | muse-wonder | LiveBench 2.0 long_agentic | overall |
| muse-wonder-full | muse-wonder | Parallel Search Intelligence | overall |
| muse-wonder-full | muse-wonder | HLE with search (Parallel) | 100-question subset |
| muse-wonder-full | muse-wonder | LiveBench 2.0 research | overall |
| muse-wonder-full | muse-wonder | Epoch Capabilities Index | overall |
| muse-wonder-full | muse-wonder | HLE-Diamond (Scale) | no tools |
| deepseek-v4.1-flash-1017 | deepseek-v4.1-flash | BullshitBench v2 | overall |
| deepseek-v4.1-flash-1017 | deepseek-v4.1-flash | Remote Labor Index | overall |
| deepseek-v4.1-flash-1017 | deepseek-v4.1-flash | Vals CyberBench v1.1 | overall |
| deepseek-v4.1-flash-1017 | deepseek-v4.1-flash | SEC-Bench Pro | overall |
| deepseek-v4.1-flash-1017 | deepseek-v4.1-flash | CyberGym | overall |
| deepseek-v4.1-flash-1017 | deepseek-v4.1-flash | HLE with tools | overall |
| deepseek-v4.1-flash-1017 | deepseek-v4.1-flash | Epoch Capabilities Index | overall |
