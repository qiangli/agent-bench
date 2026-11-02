# Agent collaboration capabilities and proposed operating bands

Research date: 2026-11-02

Status: Research synthesis and proposed capability model

## Purpose and main findings

Effective agent collaboration requires two complementary abilities: an agent must be steerable by an authorized party, and agents responsible for coordination must be able to steer others. Tool proficiency enables execution, but does not establish either collaboration or management competence.

This report translates research on agent workflow patterns into observable capabilities for workers, managers, and supervisors of managers. It proposes five cumulative operating bands:

| Band | Role | Distinguishing capability |
|---|---|---|
| L1 | Controllable responder | Reliably accepts bounded instructions and lifecycle control |
| L2 | Tool-using executor | Performs and verifies concrete work through tools |
| L3 | Steerable collaborator | Remains aligned through corrections, handoffs, and changing circumstances |
| L4 | Agent manager | Steers workers and integrates their work into a verified result |
| L5 | Supervisor of managers | Steers managed teams toward a coherent overall outcome |

These labels are a proposed interpretation of the research discussion. They do not rename existing packs, change certificate thresholds, or assign actual agents to bands. The repository's [README](../README.md) distinguishes certificate gates from bands derived through ongoing duty ratings; that distinction remains applicable.

The central design recommendation is to evaluate observable behavior and resulting state. An agent saying that it stopped, delegated, verified, or completed a task is a claim to check. Useful evidence includes tool traces, artifacts, command acknowledgments, dependency state, and independent outcome checks.

## Research scope and evidence

The research combines workflow taxonomies, implementation examples, production engineering reports, and empirical studies. These sources serve different purposes. A taxonomy identifies design choices; an implementation illustrates mechanics; a controlled experiment can test a particular comparison. Repeated mention of a pattern across explanatory articles does not constitute independent experimental confirmation.

### Comparison of the six requested sources

| Source | Coverage | Contribution to collaboration requirements |
|---|---|---|
| [Agentic Workflow Patterns repository](https://github.com/arunpshankar/Agentic-Workflow-Patterns) | Reflection, web access, semantic routing, parallel delegation, dynamic sharding, task decomposition, dynamic decomposition, and DAG orchestration | Separates splitting data from splitting responsibilities. Its YAML-defined DAG example highlights dependency scheduling. The README supplies implementation references rather than comparative performance evidence. |
| [Neo4j workflow guide](https://neo4j.com/blog/agentic-ai/what-are-agentic-workflows/) | Planning, tool use, reflection, orchestration, and production controls | Emphasizes actionable plans, typed tool interfaces, explicit handoffs, shared state, bounded retries, and idempotency. Graph-based context is an option, not a prerequisite for collaboration. |
| [Diego Carpintero on Hugging Face](https://huggingface.co/blog/dcarpintero/design-patterns-for-building-agentic-workflows) | Evaluator–optimizer, context augmentation, chaining, parallelization, routing, and orchestrator–workers | Makes intermediate gates, aggregation choices, actionable feedback, and stopping conditions explicit. This is a community article rather than a Hugging Face experimental result. |
| [Anthropic on effective agents](https://www.anthropic.com/research/building-effective-agents) | Predefined workflows versus model-directed agents; chaining, routing, parallelization, orchestration, and evaluation loops | Distinguishes predefined subtasks from runtime decomposition, and parallel sectioning from voting. Provides a foundation for choosing an appropriate coordination mechanism. |
| [ByteByteGo workflow overview](https://blog.bytebytego.com/p/top-ai-agentic-workflow-patterns) | Reflection, tool use, ReAct, planning, and multi-agent collaboration | Clarifies upfront planning versus interleaved action and observation. Provides accessible terminology, with substantial overlap with other sources. |
| [Google Cloud design guide](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system) | Sequential, parallel, loop, critique, refinement, coordinator, hierarchy, swarm, ReAct, human intervention, and custom logic | Extends the design space to decentralized handoffs and intervention points. Separates code-controlled scheduling from model-directed coordination. |

The repository assessment above is based on its README and pattern descriptions, not execution or a full audit of its implementations.

### Empirical findings and their limits

[Google Research's January 2026 analysis](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/) compared 180 agent configurations. Centralized coordination improved its financial-analysis workload by 80.9% relative to the single-agent baseline, while multi-agent approaches performed worse on sequential planning. The useful implication is task dependence: communication and decomposition can help independent work while interfering with tightly coupled execution. These numbers are not universal gains or penalties.

[Anthropic's research system report](https://www.anthropic.com/research/multi-agent-research-system) reported a 90.2% improvement over its single-agent baseline on an internal research evaluation. Token expenditure was also a major explanatory factor. The result supports breadth-oriented delegation in that setting, but does not isolate collaboration from additional compute.

[Cursor's July 2026 swarm report](https://cursor.com/blog/agent-swarm-model-economics) describes planner–worker trees, separate contexts, and ownership constraints. Its revised system improved over its previous swarm across tested model configurations on a held-out SQL suite. This comparison supports the specific engineering changes; it does not establish superiority over every single-agent alternative.

[MAST](https://arxiv.org/abs/2503.13657) collected more than 1,600 traces across seven multi-agent frameworks and identified 14 failure modes grouped around system design, inter-agent alignment, and verification. Its model population is older than current frontier systems, so it is most useful here as a source of failure categories to test.

These findings support evaluating coordination benefit under matched budgets and realistic dependencies. They do not establish a universal ranking of workflow patterns.

## A taxonomy for evaluating collaboration

Workflow structure, decision authority, feedback, and runtime support should be recorded separately. Combining them into a single list obscures which capability an agent actually possesses.

| Dimension | Examples | Evaluation question |
|---|---|---|
| Control flow | Chain, route, parallel execution, dependency graph, loop | Does work occur in a valid order with appropriate branching? |
| Decision authority | Predefined code, single agent, manager, supervisor, peer handoff | Who decides assignments, changes, acceptance, and termination? |
| Feedback | Tool observations, self-critique, independent critic, executable checks, human input | What evidence causes behavior to change? |
| Runtime support | Retrieval, memory, checkpoints, permissions, retries, tracing, budgets | What infrastructure makes the behavior possible and reliable? |

This four-part taxonomy is the report's synthesis. A system can combine several patterns: a supervisor can direct managers, each manager can schedule a dependency graph, and each worker can use a reactive tool loop with verification.

### Distinctions that affect capability assessment

**Routing and decomposition differ.** Routing chooses an existing path or specialist; decomposition identifies the pieces of work needed for a particular objective. A good classifier is not necessarily a good manager. This follows the distinction between routing and orchestrator–workers in [Anthropic's taxonomy](https://www.anthropic.com/research/building-effective-agents).

**Parallelism has different purposes.** Task sectioning divides responsibilities; data sharding partitions inputs; voting repeats a task to obtain alternative judgments. Sectioning needs interface and integration checks. Sharding needs coverage and duplicate checks. Voting needs a reliable aggregation rule and evaluation of correlated mistakes. These distinctions draw on [Anthropic](https://www.anthropic.com/research/building-effective-agents) and the [pattern repository](https://github.com/arunpshankar/Agentic-Workflow-Patterns).

**Planning and scheduling differ.** Planning determines necessary work. Scheduling determines when work is eligible to run. A model can propose a plan that a deterministic scheduler executes. A DAG represents acyclic dependencies; iterative repair requires a separate loop or revised execution graph.

**Reflection and verification differ.** A critique provides feedback. Verification checks a claim against evidence. Another agent's agreement may be useful but is not equivalent to a passing executable test or an observed external outcome. The evaluator–optimizer workflow needs feedback that identifies actionable defects and explicit exit conditions, as discussed in the [Hugging Face community article](https://huggingface.co/blog/dcarpintero/design-patterns-for-building-agentic-workflows).

**ReAct and explicit planning can coexist.** A worker may select its next tool call from observations while maintaining a larger plan. Upfront plans become less useful when new information invalidates their assumptions; reactive execution can lose global constraints without persistent task state. [ByteByteGo](https://blog.bytebytego.com/p/top-ai-agentic-workflow-patterns) explains the underlying distinction.

**The term swarm does not identify a unique topology.** [Google Cloud](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system) describes decentralized peer communication and handoffs, whereas the cited Cursor design uses planner–worker trees. Evaluations should name the actual authority and communication structure.

## Steering and steerability

Steering is the ability to direct another agent's behavior toward an objective and check that the direction took effect. Steerability is the ability to receive that direction, interpret its scope, update behavior, and report the resulting state accurately.

### Steering other agents

A manager must convert an objective into bounded assignments with clear deliverables, constraints, ownership, and acceptance criteria. It must observe progress, detect deviation, issue corrections, and verify compliance. Delegating a prompt and waiting for a final message is insufficient evidence of management.

A supervisor of managers must additionally reconcile objectives across teams. It must distinguish a worker failure from a management failure, decide which manager owns a disputed dependency, and intervene without creating conflicting chains of command. A locally successful team can still fail the overall objective by violating a shared interface or optimizing the wrong priority.

### Responding to steering

A collaborator must distinguish a replacement instruction from an addition, clarification, cancellation, or status request. It should preserve requirements that remain valid and explicitly identify conflicts that prevent compliance.

Steering also has a temporal dimension. A correction may arrive before execution, during a tool call, after an artifact has changed, or after work has been delegated. The receiving agent must reconcile completed effects with the new instruction and prevent stale work from being treated as current.

### Robotic control and semantic control

Robotic control covers lifecycle commands with precise state transitions. Semantic control covers changes in goals, constraints, priorities, methods, or acceptance criteria. Both are needed, but they should be evaluated separately.

| Command | Proposed observable semantics | Typical failure |
|---|---|---|
| Start | Begin the identified task within its authorized scope | Starts the wrong task or duplicates an existing run |
| Pause | Stop initiating new task actions at the defined safe boundary and preserve continuation state | Acknowledges pause while continuing to issue actions |
| Resume | Continue the identified paused task after checking current constraints and relevant state | Replays already completed side effects or uses superseded instructions |
| Stop or cancel | End the identified execution and prevent automatic continuation | Stops locally while delegated work continues |
| Reset | Clear only the specified working state and establish a new execution context | Deletes durable artifacts or inherited constraints outside the reset scope |
| Status | Report actual execution state, blockers, completed effects, and pending work | Reports an intention or stale plan as current state |

These semantics are proposed contracts for tests, not claims that every harness implements these commands identically. Reset does not inherently mean rollback. Stop does not undo a completed external action. Tests must define how in-flight operations are treated and what acknowledgment means.

Immediate interruption can be enforced by a runtime independently of model cooperation. Agent-level tests should also check semantic understanding, preservation of state, and behavior after resumption. Record whether the result was achieved by the agent, the harness, or both.

## Proposed cumulative operating bands

### L1 controllable responder

L1 establishes a minimum control contract. The agent follows bounded instructions, acknowledges state, respects explicit scope, and responds correctly to lifecycle commands. Tool proficiency is not required at this level.

Evidence should distinguish command receipt from successful transition. For example, a pause acknowledgment is insufficient if new work continues afterward. A reset test should check that only the specified state was discarded.

### L2 tool using executor

L2 adds the ability to complete concrete tasks using tools such as web search, terminal shell, and coding environments. The agent selects appropriate tools, supplies valid inputs, interprets failures, and verifies resulting artifacts or state.

It should handle ordinary recoverable errors within a bounded retry policy and distinguish attempted work from successful work. Tool proficiency must be scoped: competence in web research does not establish competence in coding or shell operations.

### L3 steerable collaborator

L3 adds sustained alignment during execution. The agent can revise its own plan, accept mid-run changes, communicate blockers, hand off usable state, and recover from interruption. It preserves unchanged constraints while updating the parts of the task that changed.

L3 can coordinate with peers within an assigned authority boundary. It need not manage a team. A decisive test changes a requirement after work has begun and checks the final artifact, continuation state, and communications for correct adoption of the change.

### L4 agent manager

L4 adds responsibility for a team outcome. The agent decomposes objectives, selects workers, defines contracts, manages dependencies and ownership, monitors progress, and issues corrective steering. It can stop or replace a worker and reconcile partial results.

The manager must verify the integrated result. Several successful worker reports do not establish successful integration. Tests should include false completion, incompatible outputs, missing work, and a worker that misunderstands a correction.

### L5 supervisor of managers

L5 adds responsibility for multiple managed teams. The agent partitions objectives across managers, sets decision boundaries, allocates resources, evaluates managerial performance, and resolves cross-team dependencies.

The supervisor must identify when team-level optimization harms the global objective. It must also propagate cancellation, transfer responsibility from a failed manager, and verify overall completion without relying exclusively on managerial summaries.

### Band gates and domain attributes

The proposed bands are cumulative: L5 requires L4 capabilities, and so on. Certification should therefore preserve lower-level gates rather than letting high scores in one area compensate for broken control or dishonest reporting.

Record domain proficiency separately from band qualification. An illustrative profile might contain a proposed band of L3 and independently evaluated attributes for web research, shell execution, coding, and review. The profile should also identify the model, harness version, tool permissions, context limits, and tested budgets.

No empirical pass threshold is established by this report. Thresholds require calibration against repeated trials, known failures, and agents with differing demonstrated competence.

## Mapping workflow capabilities to bands

The minimum band below means responsibility for operating the capability, rather than simply participating in a workflow that uses it.

| Capability | Minimum proposed band | Required evidence |
|---|---|---|
| Command acknowledgment and basic status | L1 | Correct distinction between received, running, paused, stopped, and completed |
| Start, stop, pause, resume, reset | L1 | Correct lifecycle transition within defined scope |
| Tool selection and context retrieval | L2 | Appropriate invocation and interpretation of actual results |
| Prescribed sequence with intermediate gates | L2 | Prerequisites respected and failures detected |
| Reactive action and observation | L2 | Next action changes appropriately after feedback |
| Self-review and executable verification | L2 | Concrete defects detected and repairs checked |
| Replanning its own task | L3 | Updated plan preserves valid constraints |
| Checkpoint recovery and context continuity | L3 | Commitments, evidence, and outstanding work survive interruption |
| Structured communication and handoff | L3 | Another agent can continue without reconstructing essential state |
| Human or manager checkpoint | L3 | Correct suspension, correction handling, and continuation |
| Peer collaboration within assigned authority | L3 | Ownership and constraints survive peer exchanges |
| Routing work to agents | L4 | Suitable assignment and recovery from misrouting |
| Task decomposition and parallel delegation | L4 | Bounded assignments with coherent interfaces |
| Sharding and dependency scheduling | L4 | Complete coverage without duplicate effects or premature execution |
| Assigning critics and aggregating judgments | L4 | Disagreements resolved against acceptance criteria and evidence |
| Monitoring and correcting workers | L4 | Drift detected and correction confirmed |
| Team integration and acceptance | L4 | Combined artifact independently checked |
| Delegation through managers | L5 | Clear team boundaries and managerial accountability |
| Cross-team conflict resolution | L5 | Shared interfaces and competing priorities reconciled |
| Manager evaluation and replacement | L5 | Management failure diagnosed and ownership transferred |
| Global cancellation and completion | L5 | All delegated obligations accounted for |

An L2 worker can participate in a large DAG scheduled entirely by code. That does not make the worker L4. Similarly, a hierarchy implemented by a framework does not establish that its top-level model can supervise managers. Capability attribution depends on who makes and verifies the consequential decisions.

## Proposed collaboration contracts

The following contracts are original design recommendations derived from the capability model. They are suitable inputs to synthetic benchmark tasks and do not prescribe a particular transport or framework.

### Assignment contract

An assignment should specify its objective, deliverable, acceptance criteria, owner, constraints, dependencies, resource budget, and escalation conditions. It should identify which decisions the recipient may make and which require coordination with the sender.

### Communication contract

Messages should identify the relevant task, sender role, instruction or observation, and whether acknowledgment or action is required. Revisions should be distinguishable from duplicates and superseded messages. Tests should check delayed, duplicated, and out-of-order delivery rather than assuming a perfect channel.

Acknowledgment should have defined meaning. Receipt, acceptance, execution, and verification are different states. A manager should not infer completed compliance from a receipt acknowledgment.

### Handoff contract

A handoff should preserve the current objective and constraints, completed work and supporting evidence, artifacts, unresolved issues, known failures, pending operations, and the next responsible owner. A successor should reconcile the handoff against actual state before taking consequential action.

### Acceptance contract

A completion claim should identify the delivered artifact or state, the criteria checked, the evidence produced, and any unmet criteria. The accepting manager or supervisor retains responsibility for the appropriate independent checks.

### Authority and intervention contract

The system should define who may assign, redirect, pause, cancel, accept, or reset a task. Conflicting instructions require a known precedence or escalation mechanism. Cross-team corrections should not silently bypass the manager who remains accountable for the work.

## Benchmark design recommendations

### Test families

| Family | Target bands | Intervention or fixture | Observable outcome |
|---|---|---|---|
| Lifecycle control | L1–L5 | Pause, resume, cancel, or scoped reset at defined points | Correct state transition and absence of prohibited later actions |
| Tool execution | L2–L5 | Tool errors, malformed responses, or ambiguous success | Correct recovery and truthful outcome report |
| Semantic steering | L3–L5 | Change one requirement during execution | New requirement adopted while other constraints remain intact |
| Handoff and recovery | L3–L5 | Restart with incomplete or stale recorded state | State reconciled before continuation |
| Routing | L4–L5 | Ambiguous request or unavailable specialist | Correct route or justified fallback |
| Decomposition | L4–L5 | Mixed independent and dependent work | Appropriate task boundaries and ordering |
| Sharding | L4–L5 | Boundary cases and duplicate input records | Complete coverage with controlled duplicate handling |
| Verification | L4–L5 | Worker falsely reports success | False completion rejected based on evidence |
| Aggregation | L4–L5 | Conflicting findings or wrong majority | Evidence-based resolution rather than blind consensus |
| Dependency recovery | L4–L5 | Failed prerequisite or revised interface | Dependent work held, revised, or invalidated appropriately |
| Manager supervision | L5 | Manager reports local success while violating global requirements | Supervisor detects and corrects the mismatch |
| Global control | L5 | Cancel or change scope across active teams | Propagation confirmed and outstanding effects accounted for |

Use synthetic tools and fixtures for certificate tasks. The repository's [contribution rules](../CONTRIBUTING.md) require self-contained tasks without external services or real accounts. A local search fixture can test retrieval behavior, although it does not establish live-web proficiency. Live integration evaluations should be reported separately.

### Measurements

Measure verified task success, constraint violations, and truthful reporting alongside latency and cost. For collaboration, add correction adoption, handoff completeness, detection of false completion, duplicate work, dependency violations, and intervention burden.

For lifecycle commands, measure both acknowledgment latency and time to the specified execution boundary. For supervisors, measure propagation across the delegation tree and whether work continues under abandoned ownership.

Report repeated-trial reliability rather than only the best result. Record the denominator and uncertainty for success rates. Preserve individual hard-rule failures even when an aggregate quality score is high.

[Anthropic's evaluation guidance](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) distinguishes the trace from the resulting environment and emphasizes repeated trials. This distinction is particularly useful when a manager's report sounds correct but the integrated artifact is not.

### Controlled comparisons

Compare architectures under both matched total resource budgets and operational latency constraints. Equal worker budgets are not equal system budgets when a manager, critics, and retries consume additional resources.

Useful comparisons include single executor versus managed workers; static assignment versus adaptive routing; self-critique versus independent review; uninterrupted work versus restart; and centralized management versus peer handoff. Vary task coupling explicitly so an architecture is not rewarded only on workloads tailored to its strengths.

Hold fixtures, graders, permissions, and tool behavior constant where possible. Record model changes separately from harness changes. Evaluate executable outcomes without exposing graders or reference solutions to the tested agent.

## Relationship to existing certificates

The following is a coverage interpretation, not a declaration that a pack awards the proposed band.

| Existing pack or mechanism | Relevant coverage | Remaining consideration |
|---|---|---|
| `floor` | Baseline sanity | Does not establish complete lifecycle control |
| `l1` | One-shot instruction following | Existing format differs from the proposed L1 control contract |
| `l2` | Terminal tool execution | Tool domains and recovery conditions need separate coverage |
| `steer` | Corrections, boundaries, stop, honesty, recovery, integration | Strong overlap with proposed L3 and some L4 behaviors |
| `review` | Detection of defects and clean changes | Review proficiency is a domain attribute, not management qualification |
| `manager` | Decomposition, routing, integration, replanning, checkpoints | Strong overlap with proposed L4; calibration remains important |
| `judge` | Calibration of architectural and code judgments | Supports evaluators but does not establish control or supervision |
| `skill-uptake` | Discovery and use of available procedures | Useful across executor, collaborator, and manager roles |
| `l5` | Frontier harness gaps under development | Does not automatically correspond to the proposed supervisor band |

The [README](../README.md) identifies long-horizon state and cross-machine continuation as coverage gaps. The proposed model additionally highlights supervision of managers, distributed command propagation, authority conflicts, and distinguishing runtime control from agent cooperation.

Before adopting these band names operationally, reconcile them with existing league and duty-rating terminology. Preserve historical result labels so earlier evaluations remain interpretable.

## Recommended next research steps

1. Specify lifecycle semantics, including command scope, acknowledgment meaning, and treatment of in-flight operations.
2. Define minimal assignment, correction, handoff, and acceptance contracts with observable state changes.
3. Construct synthetic tasks that isolate each proposed band transition rather than combining every difficulty in one scenario.
4. Add L5 scenarios where manager reports conflict with independently observable global state.
5. Calibrate graders and thresholds using repeated runs and deliberately defective reference behaviors.
6. Compare architectures at matched budgets and retain patterns only where they improve the intended outcomes.

The research hypothesis is that reliable collaboration depends on a cumulative progression from control, through execution and steerability, to management and supervision. The proposed bands make that hypothesis testable; they are not yet a validated universal scale.

## Additional runtime research references

- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents): incremental work, durable progress, and fresh-session continuity.
- [Effective context engineering for AI agents](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents): selective context, compaction, and separate agent contexts.
- [Code execution with MCP](https://www.anthropic.com/research/code-execution-with-mcp): tool discovery and processing intermediate data outside the model context.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): thread checkpoints and cross-thread stores as distinct persistence mechanisms.

These runtime mechanisms can support several bands. Their presence alone does not establish that an agent uses them correctly or collaborates effectively.
