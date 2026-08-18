# ORE Miner V3 — Execution Readiness Phase 3B Handoff

## 1. Governing objective

> **The ultimate objective of ORE Miner V3 is to build an ORE miner that can
> be trusted to operate with real SOL.**

Research, historical data, Replay, experiments, simulation, paper mining, and
Execution Readiness are supporting mechanisms. They exist to establish enough
evidence, correctness, safety, and operational confidence for future miner
decisions to influence real capital safely. They are not the end product, and
the project is not pursuing research publication for its own sake.

Execution Readiness is research-integrity infrastructure. It makes the
evidence chain reproducible and the transition into official experimentation
fail closed; it does not itself authorize live mining or real-SOL exposure.
The project must not become trapped indefinitely building research
infrastructure. Once Execution Readiness is complete and adopted, reassess the
evidence and proceed along the shortest defensible route toward the actual
miner.

## 2. Checkpoint purpose and authority

This checkpoint ends the working session that froze and remotely verified
Execution Readiness Phase 3B. It is a navigation and handoff document, not a
replacement for a primary specification, protocol, finding, manifest, or Git
history. If this summary conflicts with a primary governing source, the
primary source controls.

The checkpoint records repository state at:

- branch: `research/post-v1`;
- local and remote HEAD: `5cd7413d89699720545e473776d80c347bb5adb9`;
- synchronization: ahead `0`, behind `0`; and
- highest implemented Phase 3B result:
  `EVIDENCE_PREPARATION_VALIDATED`.

## 3. Project identity and architecture

ORE Miner V3 is a clean-sheet successor to the archived V1/V2 work. The V3
repository was created as a standalone architecture rather than extending the
earlier miners. The governing progression is:

```text
Observer
  -> Historical Dataset
  -> Replay Engine
  -> Strategy Lab
  -> Decision Engine
  -> Portfolio Simulator
  -> Paper Miner
  -> Live Miner
  -> Adaptive Strategy
```

The Observer, historical lifecycle/dataset machinery, Replay Engine, research
feature and experiment infrastructure, Strategy Lab foundations, and
Execution Readiness through Phase 3B have substantive tracked implementations
and tests. The repository also contains scaffolding and research-domain code
for later decision, simulation, economics, and paper components, but that must
not be mistaken for a completed operational miner. Decision Engine integration,
portfolio-level validation, paper-miner validation, Live Miner operational
safety, and adaptive strategy promotion remain future work. No current
readiness result authorizes real-SOL operation.

The durable architecture rule is that research-time outcomes may be labels or
evaluation inputs only after the decision/ranking boundary. They may never
enter the strategy-visible decision state.

## 4. Security and real-capital principles

- No private keys, seed phrases, passwords, API keys, tokens, credentials,
  personal secrets, confidential information, or sensitive environment values
  belong in Git.
- Environment-specific secrets remain outside tracked source. Local secret
  material must not enter logs, fixtures, manifests, or command history.
- Historical and research correctness does not authorize real-SOL deployment.
- Real-SOL operation requires independent runtime safety, exposure limits,
  transaction safeguards, monitoring, failure handling, and strategy-promotion
  governance.
- Execution Readiness is necessary research-integrity infrastructure, not
  live-capital authorization or a capital-risk control.

See the tracked [Security Policy](../../SECURITY.md) and
[Architecture Overview](../architecture/overview.md).

## 5. Observer, dataset, and Replay foundation

The first V3 executable foundation was a read-only Observer. It uses Solana
JSON-RPC without a wallet or transaction authority, reads and decodes the ORE
Board and Treasury accounts, derives the Board-selected Round account, and
decodes the 25 mining squares. Later collection code persisted immutable raw
observations and assembled them into ordered round lifecycles.

[RFC-012](../rfcs/RFC-012-OBSERVER-FINALIZATION-CAPTURE.md) established the
critical finalization boundary. After a confirmed contiguous Board transition,
the Observer receives one bounded opportunity to read the predecessor Round's
already-finalized protocol state. It does not infer, synthesize, or predict an
outcome. Snapshot state and finalized outcome evidence remain distinct, and
outcome-only fields remain outside Replay's decision context.

The cumulative archived RQ-003 discovery dataset is documented by
[Discovery Session 1](../research/notebook/discovery-session-001.md):

| Binding | Tracked value |
| --- | --- |
| Dataset version | `replay-dataset-v1` |
| Dataset SHA-256 | `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7` |
| Replay rounds | 18,653 |
| Raw observation references | 1,390,766 |
| Complete lifecycles | 17,912 |
| Incomplete lifecycles | 741 |
| Locally observed outcomes | 3,507 |
| Missing outcomes | 15,146 |
| Integrity status | `valid` |

The managed payload stores compact lifecycle records and ordered references
to immutable raw observation lines rather than duplicating all snapshots.
Replay reopens those references, normalizes Board/Treasury/Round state,
selects a governed decision observation, and exposes only information that
would have been available by that observation. Outcome metadata is not part of
the decision-time projection.

The dataset digest is shared across the completed RQ-003 experiments, but a
Replay identity also binds experiment-specific decision selection and
configuration. It must not be treated as one universal digest. Recorded Replay
identities include:

| Experiment | Replay identity |
| --- | --- |
| Experiment 1 | `e2de7374318bff7d2644b9394106f2ddbf938e9cf8bf4133b3bb5bfe304fe31b` |
| Experiment 2A | `2f69bc29607259bae7a8308ca5517f529194449b2d363b853166f342d2063600` |
| Experiment 2C | `dbd08e16db7589162f436210b9a4d0a61d3b12f97129ca53d9e55cf687a06bcf` |
| Experiment 2D | `ae796fdeaecf5f703d4c36049fd69747b71de3ed89f158df344579c8f1859925` |
| Experiment 3 | `1ebe70716be53315299a96c4c1162034dcfb63a5a231e42b1e6d6df115b5ef4f` |
| Experiment 4 | `885f4b8c5c064692d86ea7d5dbd2d5ca93ea238b504c80bed3e7945e2676e1fb` |

This foundation is substantial and should be reused, not rebuilt casually.
Its dataset and Replay identities remain bounded by the governing protocols
and findings that recorded them.

## 6. Governing research question

[RQ-003 — Decision-Time Winning-Square Information](../research/questions/RQ-003-winning-square-predictability.md)
asks whether information available at or before a deterministic ORE decision
observation contains reproducible, chronologically out-of-sample information
about the finalized winning square beyond deterministic and seeded-random
uninformed baselines.

RQ-003 concerns information content. It does not choose a model, Strategy,
deployment, economic allocation, or live-mining policy. It expressly permits
a negative answer and requires outcomes to remain unavailable until after the
outcome-blind decision/ranking state is frozen.

## 7. Findings 001–006

| Finding | Experiment and tracked path | Concise scientific conclusion | Validity and limitation boundary |
| --- | --- | --- | --- |
| 001 | Experiment 1, [Direct Deployment Ordering](../research/findings/rq003-experiment-001-analysis.md) | Valid negative evidence: descending deployed lamports did not meet the predeclared superiority conditions against both uninformed baselines. | Bounded to the declared direct ordering, `end_slot - 5` decision point, Replay population, and protocol revision; it does not rule out every other eligible deployment-derived procedure. |
| 002 | Experiment 2A, [Deployment-per-Miner Ordering Characterization](../research/findings/rq003-experiment-002-analysis.md) | Deployment per Miner materially changes candidate ordering relative to raw Deployment. | Outcome-blind ordering characterization only; it establishes structural novelty, not winning-square prediction, authorization for Experiment 2B, profitability, or Strategy value. |
| 003 | Experiment 2C, [Miner Count Ordering Characterization](../research/findings/rq003-experiment-002c-analysis.md) | Miner Count ordering is empirically distinct from both raw Deployment and Deployment per Miner, with substantial tie structure. | Outcome-blind ordering characterization only; it does not show which ordering ranks winners better or authorize predictive promotion. |
| 004 | Experiment 2D, [Signed Deployment–Miner Share Imbalance Characterization](../research/findings/rq003-experiment-002d-analysis.md) | Signed Share Imbalance has measurable ordering structure: it is distinct from the direct participant-state orderings and overlaps substantially, but not completely, with Deployment per Miner. | Retrospective archival reconstruction of a valid sealed outcome-blind experiment; no predictive, profitability, Strategy, or live-deployment conclusion follows. |
| 005 | Experiment 3, [Miner Count Predictive Evaluation](../research/findings/rq003-experiment-003-analysis.md) | Valid negative evidence: direct descending Miner Count did not meet the protocol's winner-ranking superiority requirements. | Bounded to the frozen measurement, direct ordering, decision point, Replay population, and revision; it does not eliminate every relationship or combined use of Miner Count. |
| 006 | Experiment 4, [Deployment-per-Miner Predictive Evaluation](../research/findings/rq003-experiment-004-analysis.md) | Valid negative evidence: Deployment per Miner is not supported as a predictive winner-ranking signal at the tested decision point. | Bounded to the governed direct descending procedure and population; it does not establish universal uselessness, profitability, or live-deployment suitability. |

### Finding 004 archival status

Finding 004 is explicitly a retrospective archival reconstruction of
Experiment 2D. No contemporaneous standalone Finding 004 was found in
repository history. The later Participant-State Family Review first used that
label while reconstructing the result from the valid sealed Experiment 2D
artifacts. The standalone finding does not imply that a contemporaneous
standalone document existed, and it adds no rerun, metric, or new scientific
analysis.

## 8. Experiment history and readiness lesson

- **Experiment 1** tested direct descending Deployment and produced valid
  negative predictive evidence.
- **Experiment 2A** characterized Deployment per Miner outcome-blindly.
  **Experiment 2B** was a conditional predictive protocol and was not
  authorized by Finding 002. **Experiment 2C** characterized Miner Count, and
  **Experiment 2D** characterized Signed Deployment–Miner Share Imbalance;
  these were structural, outcome-blind experiments.
- **Experiment 3** performed the governed predictive evaluation of direct
  Miner Count and produced valid negative evidence.
- **Experiment 4** performed the governed predictive evaluation of Deployment
  per Miner and produced valid negative evidence.

The execution-history lesson is operational rather than a reinterpretation of
the findings. The Experiment 2D implementation commit
`3ba070ba3c2173d63df690054c4c91957b640db9`, Experiment 3 implementation
commit `d06734d715ff85aa6e35d373b6bc6d8854425615`, and Experiment 4 implementation
commit `ca1e3f722a246b70d61f1b6705a8bbc2806ad416` each lacked the protocol document
required by its governed source scopes. Their immutable-source preflights
correctly failed. Coherent protocol-bearing source states were later frozen at
`b09400d723d7bb9cd72efcf2b45c986eef000bb8`,
`7f0418fbefa78de883d9e2590f7f6de031989811`, and
`c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd`, respectively. A stale Experiment
4 governing SHA was also later requested and correctly rejected.

The scientific execution machinery generally failed correctly. The lifecycle
failed because there was no durable pre-execution readiness state identifying
one coherent remote-backed source and its reviewed authority. That gap
motivated Experiment Execution Readiness v1. Experiments 1–4 remain governed
by their historical protocols, source bindings, manifests, and attempt
histories. Do not create retrospective readiness records for them.

## 9. Known missing-outcome limitation

The later RQ-003 predictive evaluations record:

| Population | Count |
| --- | ---: |
| Replay rounds | 18,653 |
| Ranked decisions | 18,651 |
| Primary evaluations | 3,198 |
| Lifecycle-sensitivity evaluations | 309 |
| Missing outcomes | 15,146 |

Missing outcomes are approximately 81% of Replay and are a known issue that
requires later investigation. They were kept missing, were not imputed or
counted as losses, and were explicitly reconciled in Experiments 3 and 4.
This checkpoint performs no new analysis and does not claim that the missing
rate invalidates a historical finding; the findings' own validity and
limitation statements remain controlling.

## 10. Historical documentation restoration

The historical cleanup restored Findings 001–006 and completed the minimum
13-document clean-checkout dependency closure:

1. [Research Question 002](../research/research-question-002-post-transition-finalization.md);
2. [RFC-012 Phase 3 walkthrough](../research/rfc012/phase3-walkthrough.md);
3. [RFC-012 Phase 5 walkthrough](../research/rfc012/phase5-walkthrough.md);
4. [Discovery Session 002](../research/notebook/discovery-session-002.md);
5. [Discovery Session 003](../research/notebook/discovery-session-003.md);
6. [Discovery Session 004](../research/notebook/discovery-session-004.md);
7. [RQ-003 candidacy assessment](../research/investigations/rq003-candidacy-assessment.md);
8. [RQ-003 feature audit](../research/questions/RQ-003-feature-audit.md);
9. [RQ-003 feature eligibility resolution](../research/questions/RQ-003-feature-eligibility-resolution.md);
10. [Experiment 0B characterization](../research/notebook/experiment-000-characterization.md);
11. [Signal Discovery Roadmap](../research/investigations/rq003-signal-discovery-roadmap.md), including its reviewed archival correction;
12. [Participant-State Family Review](../research/findings/rq003-participant-state-family-review.md); and
13. [Predictive Evaluation Roadmap](../research/investigations/rq003-predictive-evaluation-roadmap.md).

The minimum dependency closure is committed and remote-backed. Ignored
generated analysis artifacts remain intentionally outside Git; local existence
does not make them authority. Remaining unrelated untracked research documents
were not absorbed into that closure and are listed in Section 20.

## 11. Why Experiment Execution Readiness exists

The frozen [Experiment Execution Readiness v1 specification](../research/specifications/experiment-execution-readiness-v1.md)
defines this authority chain:

```text
coherent pushed source commit S
  -> isolated readiness validation
  -> canonical readiness record
  -> reviewed and pushed readiness seal commit R
  -> official executor freshly resolves remote authority H and R
  -> clean detached S
  -> profile-specific execution
  -> scientific and control manifests
  -> validity disposition
  -> frozen finding
```

- **S** is the exact coherent source commit containing the protocol,
  implementation/adapter, bindings, governed scopes, tests, configuration,
  input declarations, and artifact declarations.
- **R** is a separate later readiness-seal commit containing the reviewed
  canonical readiness record and establishing its tracked seal path.
- **H** is the freshly fetched approved remote-head authority snapshot used
  during launch resolution; it is not caller-supplied local state.

Normal official execution must derive these objects. It must not accept a
manually copied source SHA as authority. Every transition is fail closed, and
a later stage may not repair or infer a missing earlier stage.

## 12. Execution Readiness phase status

| Phase | State | Frozen authority and implemented boundary |
| --- | --- | --- |
| **Phase 1 — Normative Foundation** | **COMPLETE / FROZEN / REMOTE-BACKED** | Commit `58fe8364f592ae642424b732d5f85c928d531137` froze [Experiment Execution Readiness v1](../research/specifications/experiment-execution-readiness-v1.md), SHA-256 `6aea25aac1b701619bde4db309fdeb341a4fc3fd790e6ee9fcfa4414e9a9db6b`. |
| **Phase 2 — Git Authority Foundation** | **COMPLETE / FROZEN / REMOTE-BACKED** | Commit `7d31b561b6a8e8fb298b13cd3ad5729908f1e913` implemented canonical identities, repository authority, automatic S resolution, R derivation primitives, S/R/H semantics, governed scopes, Git safety, and historical missing-protocol regressions. Highest result: `GIT_AUTHORITY_VALIDATED`. It does not provide `EXECUTION_READY`. |
| **Phase 3A — Preparation Authority** | **COMPLETE / FROZEN / REMOTE-BACKED** | Commit `adc602b618e3a32d12defa72fb113298f5e7d7b3` implemented detached committed S, a closed dependency root, the PEP 751 lock, offline artifact manifest, runtime/host binding, macOS Seatbelt network denial, and the declarative adapter registry. Highest result: `PREPARATION_ENVIRONMENT_VALIDATED`. It provides neither `READINESS_VALIDATED` nor `EXECUTION_READY`. |
| **Phase 3B — Evidence Preparation** | **COMPLETE / FROZEN / REMOTE-BACKED** | Commit `5cd7413d89699720545e473776d80c347bb5adb9` implemented exact readiness tests, immutable preparation snapshots, dataset reconstruction, structurally outcome-blind projection, sibling Seatbelt workers, selector and Replay reconstruction, pre-outcome population accounting, and profile/artifact reconciliation. Highest result: internal/non-authoritative `EVIDENCE_PREPARATION_VALIDATED`. It provides neither `READINESS_VALIDATED` nor `EXECUTION_READY`. |

The final reviewed Phase 3B validation state was:

- complete `tests/execution`: **228 passed**;
- Phase 3A focused subset: **46 passed**;
- frozen Phase 2 subset: **94 passed**;
- `tests/experiments`: **96 passed**;
- Research Execution Specification v1/v2 subset: **29 passed**; and
- remaining reviewed Phase 3B issues: **0**.

These counts describe the frozen Phase 3B review result; this documentation
task did not rerun experiments or perform scientific analysis.

## 13. Phase 3B decisions that must remain deliberate

The following decisions arose from adversarial and conformance review and
must not be casually undone:

- macOS Seatbelt does not permit the required nested sandbox topology;
- Phase 3B therefore uses a small unsandboxed but tightly governed detached-S
  capability controller that launches independently sandboxed sibling workers;
- the controller routes capabilities but does not perform scientific parsing,
  Replay reconstruction, ranking, evaluation, or outcome authorization;
- scientific readiness-test, raw-input projector, and Replay workers remain
  sandboxed and capability-separated;
- raw semantic parsing occurs only in the isolated projector process;
- Replay receives only an exact outcome-blind projection and cannot access the
  raw store or import raw parser/projector modules;
- outcome-blind projection contracts use positive, recursively closed exact
  schemas, not outcome-name blacklists;
- Replay independently validates projection bytes before reconstruction;
- mutable input traversal is descriptor-pinned and no-follow rather than
  pathname-check-then-open;
- content-addressed objects are not trusted by digest-shaped path alone and
  are independently revalidated by each consumer; and
- profile contracts are closed semantic objects reconciled with the actual
  artifact dependency graph.

Changing these boundaries requires deliberate governed review with evidence
of a defect. Convenience is not sufficient reason to collapse them.

## 14. Remaining Execution Readiness work

### Next implementation work

Phase 3C has not yet been investigated or designed in detail. The known next
conceptual work is to turn validated Phase 3B evidence into a deterministic,
reviewable candidate readiness record without crossing prematurely into
launch or execution. This includes:

- candidate readiness-record generation;
- aggregate readiness identity;
- canonical candidate review and materialization;
- integration of `READINESS_REJECTED` receipts;
- seal/status workflow;
- the canonical tracked readiness path;
- the reviewed readiness seal commit R; and
- remote-backed reconstruction of current readiness.

The frozen specification, not this summary, determines the exact Phase 3C
boundary.

### Later launch and execution work

Subsequent work includes the official launch orchestrator, second-fetch launch
authority, attempt-local immutable input snapshots, launch smoke tests, shared
atomic attempt allocation, permanent ordinals, `STARTED` and terminal control
records, readiness-bound outcome authorization, ranking freeze, evaluation,
scientific/control manifest integration, recovery/status handling, and the
official-execution runbook. These are not implemented merely because Phase 3B
is complete.

## 15. Exact next action

> **Investigate and design Phase 3C against the frozen Execution Readiness v1
> specification and the now-frozen Phase 2 / Phase 3A / Phase 3B
> implementation.**

The fresh session must determine the smallest coherent Phase 3C scope needed
to transform validated Phase 3B evidence into a deterministic, reviewable
candidate readiness record and the next readiness lifecycle state while
preserving all frozen safety boundaries.

Do not begin Experiment 5. Do not resume signal research yet. Do not jump
directly to official execution. Do not redesign completed Phase 2, Phase 3A,
or Phase 3B without evidence of a defect.

## 16. Route back to the miner

After Execution Readiness:

1. Complete and adopt Execution Readiness.
2. Create the final durable Execution Readiness milestone/checkpoint.
3. Reassess the research evidence and known limitations.
4. Decide the next evidence or research step only if it is necessary.
5. Progress toward Decision Engine and Portfolio Simulator integration.
6. Establish paper-mining validation.
7. Define independent Live Miner operational-safety and strategy-promotion
   gates.
8. Only after those gates are satisfied, consider controlled real-SOL
   deployment.

The objective is to minimize unnecessary detours while preserving evidence
quality and capital safety. Execution Readiness must lead back toward a miner,
not become a permanent substitute for one.

## 17. Authoritative and non-authoritative material

### Authoritative

- tracked frozen specifications;
- tracked experiment protocols;
- tracked Findings 001–006;
- the tracked historical dependency closure;
- committed implementations and tests;
- remote-backed Git commits; and
- sealed execution artifacts where the governing protocols/findings record
  their identities.

### Non-authoritative unless separately reviewed

- remaining untracked research documents;
- working-tree-only notes;
- ignored generated artifacts merely because they exist locally; and
- this checkpoint's summaries wherever they conflict with a primary governing
  source.

Existence on disk is not authority. This checkpoint is a map into the primary
record, not a replacement for it.

## 18. Do not do these things in a fresh session

- Do not treat research infrastructure as the final product.
- Do not start Experiment 5 merely because Experiments 1–4 are complete.
- Do not bypass Execution Readiness.
- Do not use manually copied governing SHAs for prospective official
  execution.
- Do not retrospectively migrate Experiments 1–4 into readiness v1.
- Do not weaken outcome isolation.
- Do not collapse projector and Replay capability boundaries.
- Do not commit ignored generated analysis or runtime artifacts casually.
- Do not absorb remaining untracked research documents without review.
- Do not put secrets, private keys, or credentials in Git.
- Do not interpret readiness as real-SOL deployment authorization.
- Do not rewrite historical findings using later knowledge merely to make them
  look current.

## 19. Primary reading order

A fresh session should read these tracked sources before designing Phase 3C:

### Readiness and execution contracts

1. [Experiment Execution Readiness v1](../research/specifications/experiment-execution-readiness-v1.md)
2. [RQ-003 Research Execution Specification v1](../research/specifications/rq003-research-execution-specification.md)
3. [RQ-003 Research Execution Specification v2](../research/specifications/rq003-research-execution-specification-v2.md)

### Research authority and roadmap

4. [RQ-003](../research/questions/RQ-003-winning-square-predictability.md)
5. [Participant-State Family Review](../research/findings/rq003-participant-state-family-review.md)
6. [Predictive Evaluation Roadmap](../research/investigations/rq003-predictive-evaluation-roadmap.md)

### Findings

7. [Finding 001](../research/findings/rq003-experiment-001-analysis.md)
8. [Finding 002](../research/findings/rq003-experiment-002-analysis.md)
9. [Finding 003](../research/findings/rq003-experiment-002c-analysis.md)
10. [Finding 004](../research/findings/rq003-experiment-002d-analysis.md)
11. [Finding 005](../research/findings/rq003-experiment-003-analysis.md)
12. [Finding 006](../research/findings/rq003-experiment-004-analysis.md)

### Governing experiment protocols

13. [Experiment 1 protocol](../research/experiments/rq003-experiment-001-direct-deployment-ordering.md)
14. [Experiment 2A protocol](../research/experiments/rq003-experiment-002a-deployment-per-miner-characterization.md)
15. [Experiment 2B conditional protocol](../research/experiments/rq003-experiment-002b-deployment-per-miner-ranking.md)
16. [Experiment 2C protocol](../research/experiments/rq003-experiment-002c-miner-count-characterization.md)
17. [Experiment 2D protocol](../research/experiments/rq003-experiment-002d-share-imbalance-characterization.md)
18. [Experiment 3 protocol](../research/experiments/rq003-experiment-003-miner-count-predictive-evaluation.md)
19. [Experiment 4 protocol](../research/experiments/rq003-experiment-004-deployment-per-miner-predictive-evaluation.md)

### Observer, architecture, and security

20. [RFC-012 — Observer Finalization Capture](../rfcs/RFC-012-OBSERVER-FINALIZATION-CAPTURE.md)
21. [Architecture Overview](../architecture/overview.md)
22. [Repository Architecture](../architecture/REPOSITORY-ARCHITECTURE.md)
23. [Strategy Lab RFC-010](../rfcs/RFC-010-STRATEGY-LAB.md)
24. [Security Policy](../../SECURITY.md)

## 20. Current Git state

| Property | Value |
| --- | --- |
| Branch | `research/post-v1` |
| HEAD | `5cd7413d89699720545e473776d80c347bb5adb9` |
| `origin/research/post-v1` | `5cd7413d89699720545e473776d80c347bb5adb9` |
| Ahead / behind | `0 / 0` |
| Index | clean |

The working tree already contained this intentional tracked modification
before the checkpoint task:

```text
 M docs/research/backlog/RESEARCH-BACKLOG.md
```

The following untracked research documents also predate this checkpoint task:

```text
?? docs/research/findings/rq003-participant-state-synthesis.md
?? docs/research/governance-post-v1-investigation.md
?? docs/research/governance/rq003-delta-min-governance-decision.md
?? docs/research/governance/rq003-delta-min-governance-placement-review.md
?? docs/research/governance/rq003-delta-min-scientific-justification.md
?? docs/research/governance/rq003-experiment-2b-authorization-review.md
?? docs/research/governance/rq003-governance-consistency-review.md
?? docs/research/investigations/protocol-revision-strategy.md
?? docs/research/investigations/rb001-dataset-build-performance.md
?? docs/research/investigations/rb001a-freeze-verification-investigation.md
?? docs/research/investigations/rb001b-proof-carrying-snapshot-artifact.md
?? docs/research/investigations/rfc013-candidacy-assessment.md
?? docs/research/investigations/rq003-decision-quality-theory-design.md
?? docs/research/investigations/rq003-decision-quality-theory.md
?? docs/research/investigations/rq003-measurement-implementation-alignment.md
?? docs/research/investigations/rq003-participant-state-consistency-review.md
?? docs/research/investigations/rq003-phase3a-immutable-context.md
?? docs/research/investigations/rq003-phase4-pipeline-review.md
?? docs/research/investigations/rq003-protocol-state-discovery.md
?? docs/research/observer-transition-analysis.md
?? docs/research/post-v1-observer-validation.md
?? docs/research/promotion-domain-rfc012.md
?? docs/research/questions/RQ-003-phase3-feature-framework.md
?? docs/research/rfc012-readiness-review.md
?? docs/research/rfc012/rfc012-implementation-plan-readiness-review.md
?? docs/research/rfc012/rfc012-validation-analysis.md
?? docs/research/specifications/rq003-research-execution-profiles-proposal.md
```

These files are intentionally outside the completed historical dependency
closure. They must not automatically be committed, deleted, rewritten, or
treated as authority. Each requires separate review if it is ever adopted.
The new checkpoint itself is also untracked until a separately authorized
future commit; this task does not stage or commit it.

## 21. Verified commit chain

| Milestone | Commit | Parent | Subject |
| --- | --- | --- | --- |
| Readiness specification | `58fe8364f592ae642424b732d5f85c928d531137` | `9303d93802b41da8b4b679e00aac3923270a0d22` | `Freeze Experiment Execution Readiness v1 specification` |
| Phase 2 | `7d31b561b6a8e8fb298b13cd3ad5729908f1e913` | `58fe8364f592ae642424b732d5f85c928d531137` | `Implement Execution Readiness Phase 2 Git authority foundation` |
| Phase 3A | `adc602b618e3a32d12defa72fb113298f5e7d7b3` | `7d31b561b6a8e8fb298b13cd3ad5729908f1e913` | `Implement Execution Readiness Phase 3A preparation authority` |
| Phase 3B | `5cd7413d89699720545e473776d80c347bb5adb9` | `adc602b618e3a32d12defa72fb113298f5e7d7b3` | `Implement Execution Readiness Phase 3B evidence preparation` |

The frozen specification SHA-256 is
`6aea25aac1b701619bde4db309fdeb341a4fc3fd790e6ee9fcfa4414e9a9db6b`.

## 22. Resume instruction

Start the next session by verifying the Git state and frozen-spec digest, then
read the sources in Section 19. The first technical task is a **read-only Phase
3C investigation and design**. Stop before implementation until that design
has been reviewed and approved.
