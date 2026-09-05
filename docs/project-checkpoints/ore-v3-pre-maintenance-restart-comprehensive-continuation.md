# ORE Miner V3 — Pre-Maintenance-Restart Comprehensive Continuation Checkpoint

## 1. Purpose, status, and authority boundary

This document is a continuation and recovery checkpoint constructed immediately
before a controlled Mac restart. It is documentation only. It is not a
governance decision, implementation freeze, numeric-envelope adoption, research
finding, readiness record, or operational authorization. If it conflicts with
a controlling primary source, the primary source controls.

The checkpoint is presently an uncommitted candidate. Its exact bytes and hash
identify the document; no checkpoint commit or remote authority exists unless a
later separately authorized workflow establishes one. No production,
configuration, test, data, ledger, raw, observer, log, implementation-candidate,
governance, or research file was changed in constructing it. No live process
was stopped or signaled.

Point-in-time operational observations below were captured at
`2026-09-05T17:30:28Z`. PIDs, file sizes, cursors, and final records can advance
after that instant and must be recaptured at shutdown.

## 2. Repository authentication

Read-only preflight produced:

| Property | Exact result |
| --- | --- |
| Repository | `/Users/anisbaker/Documents/orev3` |
| Branch | `research/post-v1` |
| Local HEAD | `a46173a0420d0bfd4babd17cd1ebbaa911bce241` |
| Tracking branch | `origin/research/post-v1` |
| Tracking HEAD | `a46173a0420d0bfd4babd17cd1ebbaa911bce241` |
| Ahead / behind | `0 / 0` |
| Index | empty; nothing staged |
| Pre-checkpoint tracked modifications | `20` |
| Pre-checkpoint untracked paths | `30` |
| Complete pre-checkpoint mutable population | `50` paths |
| Target before construction | absent |
| Pre-checkpoint `git diff --check` | passed, no output |

Tracking equality is not remote proof. One live read-only remote-ref query was
attempted and failed exactly as follows; no second query was attempted:

```text
fatal: unable to access 'https://github.com/elaremalaka/orev3.git/': Could not resolve host: github.com
```

Nothing was pushed.

## 3. Governance authentication and prerequisite chain

The controlling bounded-streaming governance is:

`docs/research/governance/rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md`

Its SHA-256 was recomputed from current bytes as:

`ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3`

This exactly matches the expected identity. The controlling prerequisite chain
identified by that governance and authenticated from current bytes is:

| Authority | SHA-256 |
| --- | --- |
| `docs/research/experiments/rq003-experiment-005-signed-share-imbalance-predictive-evaluation.md` | `38afa9005bb43050d23e430335e11654c374d4e2d6f4a9f541782c005bffefdc` |
| `docs/research/governance/rq003-minimum-effect-scope-clarification-v1.md` | `f736ac301a49be5acca58ef75f5130c1533328cf83cc359c9a69b596c53c2f4b` |
| `docs/research/governance/rq003-experiment-005-source-processing-prerequisite-v1.md` | `d6d5d0fb3777cdb2a95e3bbff53b4815c574de68e31d4b5f7f1a0409580799a4` |
| `docs/research/governance/rq003-experiment-005-slice3-authority-prerequisite-v1.md` | `d3e8748c63f0a870a3b1e1439fa73ada0145c7502bccc8fd834987e8fb29a36e` |

The governance also records historical frozen identities for the source-
processing configuration (`042e2540...`) and implementation
(`16e67e96...`). Their working-tree bytes are now implementation candidates and
therefore intentionally have different current hashes, recorded in Section 6.
This checkpoint does not promote those candidate bytes.

## 4. Frozen prospective implementation surface

The governance freezes a prospective surface of exactly **38 paths: 26
production/configuration paths and 12 test paths**. Every path is REQUIRED; the
table authorizes no edit. Candidate implementation edits may exist only within
this surface. A 39th trust-bearing implementation path requires renewed bounded
governance. This checkpoint is documentation and is **not** part of the
38-path implementation surface.

Production/configuration paths (26):

```text
config/research/readiness/rq003-experiment-005-source-processing-v1.json
config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json
src/orev3/execution/schemas/v1/evidence-preparation-policy-bounded-streaming-v1.schema.json
src/orev3/execution/readiness_record.py
src/orev3/execution/registry.py
src/orev3/execution/readiness_contracts.py
src/orev3/execution/preparation.py
src/orev3/execution/evidence_preparation.py
src/orev3/execution/evidence_preparation_worker.py
src/orev3/execution/preparation_worker.py
src/orev3/execution/detached_evidence.py
src/orev3/execution/readiness_candidate.py
src/orev3/execution/current_readiness.py
src/orev3/execution/git_state.py
src/orev3/execution/test_policy.py
src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json
src/orev3/execution/external_inputs.py
src/orev3/execution/filesystem_capability.py
src/orev3/execution/runtime.py
src/orev3/execution/bounded_streaming_worker_bootstrap.py
src/orev3/execution/input_projection_worker.py
src/orev3/execution/readiness_test_worker.py
src/orev3/execution/dataset_validation.py
src/orev3/execution/replay_preparation.py
src/orev3/execution/replay_preparation_worker.py
src/orev3/experiments/rq003_experiment5_source_processing.py
```

Test paths (12):

```text
tests/experiments/test_rq003_experiment5_source_processing.py
tests/execution/test_phase3b_external_inputs.py
tests/execution/test_phase3b_reconstruction.py
tests/execution/test_phase3b_integration.py
tests/execution/test_phase3b_authority.py
tests/execution/test_phase3c_schema_registry.py
tests/execution/test_phase3c_readiness_record_v2.py
tests/experiments/test_rq003_experiment5_configuration.py
tests/execution/test_phase3b_worker_boundaries.py
tests/execution/test_phase3a_preparation.py
tests/execution/test_phase3c_readiness_candidate.py
tests/execution/test_phase3c_current_readiness.py
```

## 5. Complete current mutable boundary

Classification is based on path purpose, governing surface membership, and
continuation history—not mtime. Before this file there were 50 mutable paths.
After creation there are 51, classified completely below.

### 5.1 Inherited pre-existing research/documentation boundary (28)

```text
 M docs/research/backlog/RESEARCH-BACKLOG.md
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

### 5.2 Current Stage-1/2/3A implementation candidate (22)

The complete population is the 22-row manifest in Section 6. Nineteen paths
are tracked modifications and three are untracked. All are inside the frozen
38-path surface.

### 5.3 Checkpoint path itself (1)

```text
?? docs/project-checkpoints/ore-v3-pre-maintenance-restart-comprehensive-continuation.md
```

## INHERITED MUTABLE-BOUNDARY BYTE MANIFEST

This manifest was mechanically reconstructed from current bytes immediately
before this checkpoint revision. Every entry has the classification
**inherited research/documentation — not implementation authority**.

| State | Path | Bytes | SHA-256 | Classification |
| --- | --- | ---: | --- | --- |
| M | `docs/research/backlog/RESEARCH-BACKLOG.md` | 6,508 | `927be537233fd0d3f3d66bb5e633117b12a3f23f07245a73c5e51da724d2c272` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/findings/rq003-participant-state-synthesis.md` | 12,282 | `30fe030aaef12ccc16ebd5675a0f71247a083d67e2f6230f315392e874f913fd` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/governance-post-v1-investigation.md` | 14,475 | `b88d5a3964d9f433ba23761990162912a8eb007d204104800399f9fb08df8731` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/governance/rq003-delta-min-governance-decision.md` | 8,849 | `01c9a0d195a436e2b89585d4f819a2c22f5974be068a4c7cf39693e3acb06c32` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/governance/rq003-delta-min-governance-placement-review.md` | 10,548 | `91b8d83957bce189ab1bdf06f45d9a9d227b950fd31bb2cf35f498c983655318` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/governance/rq003-delta-min-scientific-justification.md` | 11,048 | `798c5d855ab69b954db7e140d1d3bff36255ae94c5aa6c6261164da3568bc9ff` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/governance/rq003-experiment-2b-authorization-review.md` | 10,458 | `b70e0b763a511a41b3cfa914a478c6c34aafab32ba877053f8e1fed0352af4d2` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/governance/rq003-governance-consistency-review.md` | 9,058 | `7d29cd1132c4e1127a930b5433689baca52bdc5a079131dab96949e36ba5d0c4` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/protocol-revision-strategy.md` | 27,581 | `f132677105e6662bcd85a9b8e37710a7b047e05b97c7422cbcddc164104243ec` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rb001-dataset-build-performance.md` | 19,620 | `eb64fa2ae735f48fa2eb728d8d7c8afcc24b56559508bbbe011f28749d562b3b` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rb001a-freeze-verification-investigation.md` | 18,838 | `7e107d74224103f6df75513dcb9bcb58beef15d290d6be5910d878bb635ca90f` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rb001b-proof-carrying-snapshot-artifact.md` | 29,497 | `d12cbc2be2ff84eadbe9df70b2c791af13d6eec078875a2a7f42334a82377fb7` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rfc013-candidacy-assessment.md` | 20,790 | `60f19c7ce5d40c885d41b2a65c0e427d0b67ed093fbcfc0b110324a4ef17db04` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rq003-decision-quality-theory-design.md` | 15,425 | `d57fc95520e9e9921c11dd00a85047f4459f6f10a3db3ddacc488d883b852e57` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rq003-decision-quality-theory.md` | 12,874 | `7cf40c53592a464e19c59668d3112ead4f0b83b8864774731b6281fab0c66879` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rq003-measurement-implementation-alignment.md` | 17,960 | `f4a0e70971afb2f7e2e97f74cec99c10d127568124c90011da1c5da18a1b067e` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rq003-participant-state-consistency-review.md` | 15,555 | `e8f3f2023b932e8cb1c3e8b315d33219bd820e3c9302976266ab580fdb9fafef` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rq003-phase3a-immutable-context.md` | 22,025 | `8a742ba03fedba130d88248459fae3546c20cd58118028dbe8de92f64cde4bfa` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rq003-phase4-pipeline-review.md` | 16,995 | `61e1d807e5990a99a11908baba90d6c805f84550938c968dfc6774654d8cf3d8` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/investigations/rq003-protocol-state-discovery.md` | 16,882 | `b1b6e16a81966f0e565ab7e3497826e2c52e165373b7466fc7bccaa6083650ef` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/observer-transition-analysis.md` | 9,968 | `ec044a9b9a6a039b0882452656e5a663fc31cf186e1fede6f782b1322e7bca6f` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/post-v1-observer-validation.md` | 9,825 | `32dd20cc2dd24e78cd31b8c774b81fe27e0ae8658b7199cc48f19efb277933bf` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/promotion-domain-rfc012.md` | 11,093 | `6affa44af19f6cec979ffed4ae2dda6d4af07269bdabe9dc5f8aa86cd5fc70ca` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/questions/RQ-003-phase3-feature-framework.md` | 33,486 | `85059b2d3ffbb680f861cf6c5f542d6f97a40f0576976798baa24569358df6b5` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/rfc012-readiness-review.md` | 23,219 | `0ea0347f63a1398abb96b652f63ff55bfecd9c6d980407230b9d2d93bbf26fc7` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/rfc012/rfc012-implementation-plan-readiness-review.md` | 23,788 | `2490b334673590367ff396204c4e44a308b131fa3fc3e4d4feea0191f3043e15` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/rfc012/rfc012-validation-analysis.md` | 13,351 | `10b9898d012bdb47a685541756342118599e6dd8cb783f01182e2754bf7f9b57` | inherited research/documentation — not implementation authority |
| ?? | `docs/research/specifications/rq003-research-execution-profiles-proposal.md` | 15,457 | `18f4e0a7ed4dc747a041cead8d9403695a7d284d71a6d6bb58e186d5ea3466e3` | inherited research/documentation — not implementation authority |

The 22 implementation-candidate entries in Section 6 and these 28 inherited
entries together form the complete 50-path mutable-state byte manifest
immediately before this checkpoint revision. The checkpoint path itself is the
51st mutable path after its creation and this revision.

## 6. Current implementation-candidate hash manifest

Hashes and sizes were mechanically recomputed from current bytes. `M` means
tracked and modified from HEAD; `??` means untracked.

| State | Path | Bytes | SHA-256 | Role / stage |
| --- | --- | ---: | --- | --- |
| M | `config/research/readiness/rq003-experiment-005-source-processing-v1.json` | 4,641 | `f17f2934bc313ec31332a490138a8b63c8a5fe0013ff55fae0b2c541a77a550a` | Stage 1 mode/limits/binding |
| M | `src/orev3/execution/dataset_validation.py` | 7,227 | `64101e23d231977950662df12948fa4d9544f2e51c831d9cf26eb5aaa8c80f80` | Stage 2 streaming summaries |
| M | `src/orev3/execution/evidence_preparation.py` | 40,811 | `25749df28d847136602e09342c33603e143eb68d2976443e6f98db6913ad0a2d` | Stage 2 orchestration/comparison |
| M | `src/orev3/execution/evidence_preparation_worker.py` | 37,868 | `2d6941c13e0a36279661793de693e30385285c6c0a5133074279b313cd8d3259` | Stage 2 worker boundary |
| M | `src/orev3/execution/external_inputs.py` | 6,224 | `c4852715e6874477f13ed29fdef062a2b2376fcb785283a127f6b9166eaf134a` | Stage 2 source streaming |
| M | `src/orev3/execution/filesystem_capability.py` | 13,331 | `eeea22f8ae32ea9fc2fbc37f7460118b070ded8642a2a72d2c18adf6b71a6a38` | Stage 2 bounded publication |
| M | `src/orev3/execution/input_projection_worker.py` | 7,478 | `6151c0f92df17f5066009ff132fab084cc0731c7e56905d01ace853e97dd2e3e` | Stage 2 projection worker |
| M | `src/orev3/execution/preparation.py` | 34,170 | `b3ffcf6135ba7e9455f7d07e7871929d4d0c1fd510f0a5e229c96e324c4824fa` | Stage 1/3A preparation binding |
| M | `src/orev3/execution/readiness_contracts.py` | 47,972 | `6fb4c4993f9314a79c7cffc7879b6f9f79d452b7339162a42bd1297a82be19f2` | Stage 1 policy reconstruction |
| M | `src/orev3/execution/readiness_record.py` | 106,769 | `f9b1a33632f7e31cf26b19e14e7a2d39a697742ebd6d9bbd63c251c907a6c806` | Stage 1 schema/record foundation |
| M | `src/orev3/execution/replay_preparation.py` | 11,337 | `3f14ad0f18dd8b3bfead86c39f435916df13690884b966435958028eb70d7896` | Stage 2 streaming Replay |
| M | `src/orev3/execution/runtime.py` | 90,038 | `95e872355356d053cc743ba13b4f568be8003e97664c045d51c1b533fdc64f42` | Stage 3A launcher/runtime |
| M | `src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json` | 12,522 | `c401708cc5b1803d8e2f20538469dc6a9b5f3050f818e0388913a1ac6e266844` | Stage 1 configuration schema |
| M | `src/orev3/experiments/rq003_experiment5_source_processing.py` | 106,848 | `b06ecce03f8b3a5c74235f5f97399be1039dad0074257d8e38f212b688875835` | Stage 2 source processor |
| M | `tests/execution/test_phase3a_preparation.py` | 19,967 | `f1a22ea91821c52a8f387926ff4472700ba0ae8c51e0a0a1ce465a0a8957da1e` | Stage 1/3A preparation tests |
| M | `tests/execution/test_phase3b_authority.py` | 17,760 | `bbfb27c246894469301038ec80ce5c01cc7f8c278aaa7e65c99c8e6f877cc0f2` | Stage 1/2 authority tests |
| M | `tests/execution/test_phase3b_reconstruction.py` | 32,402 | `f25a494fbcdd263b2cfc32146f24c9e0104fbe15a0a5e068bc12da2d3b7b66fb` | Stage 2 reconstruction tests |
| M | `tests/execution/test_phase3b_worker_boundaries.py` | 58,381 | `d73edd612dc4d1e0767ace6ef997d9283cc03baf7a1e8bd31088353d9927e65d` | Stage 3A boundary tests |
| M | `tests/experiments/test_rq003_experiment5_source_processing.py` | 54,434 | `b274ad03c66810a9aa3abad0b61045fbc012079b00ce9366a5ab7793c7a7966f` | Stage 2 semantic tests |
| ?? | `config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json` | 4,165 | `86ecbaa792277229650874a8bb27624c68ee7dbaf135fa301a719926b604261d` | Stage 1 bounded policy |
| ?? | `src/orev3/execution/bounded_streaming_worker_bootstrap.py` | 33,555 | `d0973c6d6c2b715ad118c05e6c88a68c3a82f679534840960c1a749cd4a13654` | Stage 3A bootstrap |
| ?? | `src/orev3/execution/schemas/v1/evidence-preparation-policy-bounded-streaming-v1.schema.json` | 7,200 | `2a89187c8f07a57b92ba1ddf209c5e68079823dd0f3a4bbe25307b162ea011b3` | Stage 1 policy schema |

## 7. Stage status and numeric mode

### 7.1 Stage 1

Stage 1 has a local measurement-mode policy/configuration/schema/identity
foundation: the bounded-streaming policy and schema exist; the Experiment-005
source-processing configuration binds the measurement mode, deferred numeric
vector, governed source/cardinality values, and bounded-policy identity; and
readiness reconstruction/preparation layers carry the candidate generation and
policy binding. These bytes are unstaged, uncommitted, unreviewed as a final
freeze, and non-authoritative. They must not be called frozen implementation.

### 7.2 Stage 2

**STAGE 2 BOUNDED STREAMING SEMANTIC CANDIDATE READY — STAGE 3 MAY BEGIN**

The candidate establishes complete-member authentication before semantic
influence; compact offset/coordinate indexing; parser and cardinality limits;
scientific inertness of malformed unreferenced input; per-round authenticated
reconstruction; incremental streaming projection; a path-backed result;
independent streaming validation; sequential double reconstruction; bounded
complete-stream byte/identity comparison; streaming Replay reconstruction; and
scientific parity with the frozen ordering, selection, identity, and
outcome-isolation rules. It remains candidate implementation, not adopted or
frozen authority.

### 7.3 Stage 3A

**STAGE 3A LAUNCHER/BOOTSTRAP CANDIDATE COMPLETE — STAGE 3C MAY BEGIN**

Final current hashes central to Stage 3A are:

| Path | SHA-256 |
| --- | --- |
| `src/orev3/execution/runtime.py` | `95e872355356d053cc743ba13b4f568be8003e97664c045d51c1b533fdc64f42` |
| `src/orev3/execution/bounded_streaming_worker_bootstrap.py` | `d0973c6d6c2b715ad118c05e6c88a68c3a82f679534840960c1a749cd4a13654` |
| `tests/execution/test_phase3b_worker_boundaries.py` | `d73edd612dc4d1e0767ace6ef997d9283cc03baf7a1e8bd31088353d9927e65d` |

The candidate implements the canonical request artifact and positional
`pread` authentication; scratch-FD normalization; `os.posix_spawn` file
actions and exact launch vector; authenticated `/usr/bin/time`; Darwin process
query ownership; process-instance and topology authority; `KERN_PROCARGS2`;
exact FD 0–6 authority with type-specific pipe/socket/vnode decoding;
duplicate-alias rejection; exact gate-release orchestration; Model-A closures;
Model-B authority for exactly 36 modules and 8 shells; complete thread census
and five denial hooks; non-returning status-70 terminal behavior; invocation
cleanup; and sole reaper/`waitpid` behavior. These remain candidate semantics.

### 7.4 Governed-host acceptance gap

The current Codex execution environment is **NOT** a qualified governed Stage-3
host. The observed failure is:

```text
sandbox-exec: sandbox_apply: Operation not permitted
status 71
```

Required `/usr/bin/time` host measurement operations are also restricted.
Status 71 is an environment/Seatbelt admission observation and is neither
candidate success nor candidate failure. The independently established
sequencing interpretation is:

**STAGE-3 IMPLEMENTATION MAY PROCEED — GOVERNED-HOST ACCEPTANCE DEFERRED**

### 7.5 Stage 3C

**STAGE 3C HAS NOT BEGUN.**

No candidate implementation authority has yet been added for reservation
protocol semantics, the logical disk ledger, crash/orphan recovery,
publication/deduplication, or RSS/watchdog acceptance machinery. The exact next
development boundary after restart remains Stage 3C, subject to storage
headroom. Governed-host acceptance remains deferred.

### 7.6 Numeric mode

The exact current mode is:

`BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`

No final numeric envelope is adopted. Controller/worker RSS and watchdog fields
remain `measurement_pending`; the watchdog remains
`measurement_pending_not_active`. Provisional projection and disk measurement
bounds are safety/planning values, not final production ceilings. Numeric
adoption requires governed-host evidence, independent review, separate
authorization, identity regeneration, and the required post-adoption rerun.

## 8. Test evidence

**UNAUDITED CONTINUATION-HISTORY TEST REPORT.** The following historic counts
were reported by prior implementation lanes. Checkpoint construction and this
documentation-only revision did not rerun the tests, and no durable repository
test-evidence artifact independently authenticates these exact counts. They are
orientation and continuation evidence only:

- deterministic worker-boundary suite: **53 passed / 8 deselected**;
- complete worker-boundary suite: **53 passed / 8 status-71 Seatbelt failures**;
- Phase-3A + Phase-3B integration: **15 passed / 13 status-71-derived failures**;
- Python compilation: passed; and
- `git diff --check`: passed.

Implementation freeze or governed acceptance may not rely solely on these
historic counts. Current repository bytes mechanically expose extensive
Stage-1/2 unit coverage for policy/configuration binding, source
authentication/limits, reconstruction, stream comparison, Replay parity, and
worker boundaries, but source presence does not authenticate a reported test
run. No additional numeric or full-envelope governed-host result was discovered
or claimed.

## 9. Storage state and safety boundary

The shutdown-review planning audit recorded:

| Item | Approximate value |
| --- | ---: |
| Filesystem free | 17.56 GiB |
| ORE repository allocated | 15.92 GiB |
| `data/` | 15.32 GiB |
| `data/ledger/` | 8.87 GiB |
| RFC-007 live ledger at shutdown review | 8.67 GiB |
| User pytest temp | 3.03 GiB |
| Large pytest garbage tree | 2.78 GiB |
| Conservative Stage-3C/full-envelope target | at least 30 GiB free |
| Preferred target | approximately 40 GiB free |

At checkpoint construction, `df -k` reported exactly `18,965,584 KiB`
available (about 18.09 GiB), repository `du` reported `16,691,256 KiB`,
`data/` `16,067,424 KiB`, `data/ledger/` `9,300,540 KiB`, user pytest temp
`3,172,592 KiB`, and the large garbage tree `2,909,696 KiB`. The active
RFC-007 main database was `8,671,232,000` logical bytes at a later stat during
construction and continued changing. Differences reflect time and filesystem
accounting. This is host-storage planning, **NOT numeric-envelope adoption**.

Stage 3C must not begin immediately after reboot until free space is
reassessed. Allow macOS storage accounting to settle and compare the result
with this checkpoint. Target at least 30 GiB free before disk-heavy work and
prefer about 40 GiB. Do not automatically delete anything. The repository,
data, Git state, `.venv`, and current candidate must not be deleted for cleanup.
Prefer non-ORE caches. Pytest temporary material requires provenance review
before any deletion.

## 10. Live observer authentication

At the checkpoint instant:

| Property | Observation |
| --- | --- |
| Observer PID | `10655` |
| Command | `/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python -m orev3.observer.collect` |
| Working directory | `/Users/anisbaker/Documents/orev3` |
| Observer tee | PID `10656`, `tee logs/observer/current.log` |
| Caffeinate | PID `10657`, `caffeinate -i python -m orev3.observer.collect` |
| Observed relationship | observer, tee, and caffeinate share PGID `10655`; caffeinate is a child of observer PID `10655`, while observer and tee have parent `67293` |
| Current output file | `data/raw/observer_2026-09-05.jsonl` |
| Final observed round | `393914` |
| Final observed slot | `rpc_slot = 444576455` |
| Final observed timestamp | `2026-09-05T17:28:53.051674Z` |
| File size | `12,244,958` bytes |
| Framing | terminal LF present; sampled final tail contained no CR; final JSON valid |
| Record identity fields | `schema_version=2`; `collector_session_id=bb01bb00-30a7-4a14-9945-a0e22037ac87`; board `round_id=393914`; record UUID as ingested by RFC-007 `25c7643d-9bb0-5c2d-a676-67289051b785` |

The process remained live and the file may have advanced. These values are the
pre-stop checkpoint observation, not the final shutdown record.

## 11. Live RFC-007 collector and ledger authentication

At the checkpoint instant:

| Property | Observation |
| --- | --- |
| Collector PID | `78317` |
| Tee PID | `78318` |
| Process group | `78317` |
| Exact collector command | `/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python -m orev3.collection.cli run --config config/collection/rfc007_burn_in_v1.json --ledger data/ledger/rfc007_live_ledger_v1.sqlite` |
| Tee command | `tee -a logs/rfc007_paper_collection_v1.log` |
| Config | `config/collection/rfc007_burn_in_v1.json` |
| Ledger | `data/ledger/rfc007_live_ledger_v1.sqlite` |
| Log | `logs/rfc007_paper_collection_v1.log` |
| SQLite journal mode | `wal` (queried with read-only connection and `query_only=1`) |
| Main ledger stat during construction | `8,671,232,000` bytes; still live/changing |
| WAL / SHM | WAL present, `18,350,512` bytes; SHM present, `65,536` bytes at observed stat |
| Writer lock | `data/ledger/rfc007_live_ledger_v1.sqlite.writer.lock`, present, 6 bytes |
| Latest run | `cbf90bcf-f883-4ecc-8bb6-6de5d45b8ad3` |
| Prior run | `5ef710f0-33f8-5cdb-80a7-f2ad0c95e5d2` |
| Started | `2026-07-25T22:07:20.460132+00:00` |
| Ended | `NULL`, expected while live |
| Validation status | `proven` |
| Live-state read-only integrity scan | `PRAGMA integrity_check` completed with `ok` |
| Today's source ID | `18263b8d-cc96-5756-b726-4cdfb8a5badc` |
| Today's cursor | byte offset `12,244,958`, line `11,478`, inode `128649637` |
| Cursor timestamps | last ingested `2026-09-05T17:29:29.169588Z`; last observed `2026-09-05T17:28:53.051674Z` |

The cursor exactly equaled the observer file size at the checkpoint instant.
Read-only counts then visible included 2 collector runs, 45 source cursors,
1,619,531 ingested source records, 1,617,230 opportunities, zero partial
opportunities, 1,617,230 paper decisions, 2,301 final outcomes, and 118,053
paper-accounting rows. These counts can advance.

RFC-007 and RFC-008 are separate:

- **RFC-007 live collector:** `config/collection/rfc007_burn_in_v1.json` and
  `data/ledger/rfc007_live_ledger_v1.sqlite`.
- **RFC-008 historical/system ledger:**
  `data/ledger/rfc008_paper_ledger_v1.sqlite`.

The current live collector is RFC-007.

## 12. Controlled shutdown authority

The established order is exact and mandatory:

```text
OBSERVER FIRST
→ RFC-007 CATCH-UP
→ RFC-007 COLLECTOR SECOND
→ DURABILITY VERIFICATION
→ REBOOT
```

No round boundary is required.

### 12.1 Stop the observer first

Use **Control-C in the observer's controlling terminal**. Wait for:

```text
Snapshot collection stopped.
```

Then verify the observer and associated caffeinate process have exited. Do not
prefer SIGTERM. Do not use SIGKILL.

### 12.2 Require RFC-007 catch-up

After the observer stops and before collector SIGINT, require the RFC-007
`source_cursors.byte_offset` for today's observer file to equal the final
observer file byte size. Do not stop the collector before checking this unless
an emergency requires it.

### 12.3 Stop RFC-007 second

Use the actual current Python PID at stop time:

```sh
kill -INT <current RFC-007 collector PID>
```

Send SIGINT to Python specifically, not terminal-wide Control-C. Wait for:

```text
RFC-007 paper collector stopped cleanly
```

Then verify collector and tee have exited. Do not send repeated SIGINT while
the current batch is completing. Do not use SIGKILL.

## 13. Pre-reboot verification commands

Current PIDs are observations only. If any PID changes, use the actual
pre-stop PIDs in the known-PID checks.

### 13.1 Process absence

```sh
ps -p 10655,10656,10657,78317,78318 -o pid=,ppid=,pgid=,command=
pgrep -fal 'orev3\.observer\.collect'
pgrep -fal 'orev3\.collection\.cli run.*rfc007_burn_in_v1\.json.*rfc007_live_ledger_v1\.sqlite'
pgrep -fal 'tee.*(observer/current\.log|rfc007_paper_collection_v1\.log)'
pgrep -fal 'caffeinate.*orev3\.observer\.collect'
```

All commands must show absence of the known and replacement observer,
caffeinate, RFC-007 collector, and associated tee processes. Review false
positives caused by the checking command itself.

### 13.2 Observer final framing and identity

Set `OBSERVER_FILE` to the actual UTC-date output stopped above:

```sh
OBSERVER_FILE=data/raw/observer_2026-09-05.jsonl
stat -f '%z' "$OBSERVER_FILE"
tail -c 1 "$OBSERVER_FILE" | od -An -t x1
tail -n 1 "$OBSERVER_FILE" | python -m json.tool
python -c 'import json,os; p="data/raw/observer_2026-09-05.jsonl"; o=json.loads(open(p,"rb").read().splitlines()[-1]); print(os.stat(p).st_size, o["board"]["round_id"], o["rpc_slot"], o["observed_at_utc"])'
```

The terminal byte must be hexadecimal `0a`; the final line must parse as one
JSON object. Record final byte size, round, slot, and timestamp for the gap
record.

### 13.3 Read-only SQLite durability verification

These commands do not authorize `wal_checkpoint`, `VACUUM`, repair, or any
write-mode SQLite access:

```sh
ls -l data/ledger/rfc007_live_ledger_v1.sqlite \
  data/ledger/rfc007_live_ledger_v1.sqlite-wal \
  data/ledger/rfc007_live_ledger_v1.sqlite-shm \
  data/ledger/rfc007_live_ledger_v1.sqlite.writer.lock

sqlite3 -readonly data/ledger/rfc007_live_ledger_v1.sqlite \
  'PRAGMA query_only=ON; PRAGMA query_only; PRAGMA journal_mode; PRAGMA integrity_check;'

sqlite3 -readonly -header -column data/ledger/rfc007_live_ledger_v1.sqlite \
  "PRAGMA query_only=ON;
   SELECT run_id,prior_run_id,started_at,ended_at,validation_status
     FROM collector_runs ORDER BY started_at DESC LIMIT 1;
   SELECT source_id,source_path,source_inode,byte_offset,line_number,record_json
     FROM source_cursors
    WHERE source_path='data/raw/observer_2026-09-05.jsonl';
   SELECT 'collector_runs' AS name,count(*) AS value FROM collector_runs
   UNION ALL SELECT 'source_cursors',count(*) FROM source_cursors
   UNION ALL SELECT 'ingested_source_records',count(*) FROM ingested_source_records
   UNION ALL SELECT 'opportunities',count(*) FROM opportunities
   UNION ALL SELECT 'partial_opportunities',count(*) FROM partial_opportunities
   UNION ALL SELECT 'paper_decisions',count(*) FROM paper_decisions
   UNION ALL SELECT 'final_outcomes',count(*) FROM final_outcomes
   UNION ALL SELECT 'paper_accounting',count(*) FROM paper_accounting;"

tail -n 20 logs/rfc007_paper_collection_v1.log
```

At shutdown, substitute the actual stopped UTC-date file if the date changed.

### 13.4 Clean-stop requirements

Before reboot, require every item:

- observer absent;
- observer caffeinate wrapper absent;
- collector absent;
- both relevant tee processes absent;
- observer final line valid and terminal-LF framed;
- collector latest run `ended_at` non-NULL;
- validation status acceptable/proven;
- RFC-007 cursor caught up exactly to final observer byte size;
- SQLite `integrity_check = ok`; and
- collector log ends with `RFC-007 paper collector stopped cleanly`.

If any item fails: **DO NOT REBOOT until reviewed.** Only after every clean-stop
verification succeeds may macOS be restarted.

## 14. Post-reboot startup order and exact commands

The mandatory order is:

```text
RFC-007 COLLECTOR FIRST
→ WAIT FOR COLLECTOR STARTUP LINE
→ OBSERVER SECOND
```

This order is mandatory because `live_start_mode=end` can skip records in a
new, uncursored UTC-date observer file if the observer starts first.

### 14.1 Restart RFC-007 first

```sh
cd /Users/anisbaker/Documents/orev3
source .venv/bin/activate
export PYTHONUNBUFFERED=1

PYTHONPATH=src python -m orev3.collection.cli run \
  --config config/collection/rfc007_burn_in_v1.json \
  --ledger data/ledger/rfc007_live_ledger_v1.sqlite \
  2>&1 | tee -a logs/rfc007_paper_collection_v1.log
```

Wait for exactly:

```text
RFC-007 paper collector starting; observer remains untouched; no transaction can be built or submitted
```

### 14.2 Restart the observer second

```sh
cd /Users/anisbaker/Documents/orev3
source .venv/bin/activate
export PYTHONUNBUFFERED=1

caffeinate -i env PYTHONPATH=src python -m orev3.observer.collect
```

Start only one observer instance.

## 15. Post-reboot operational verification and collection gap

Require all of the following:

- exactly one RFC-007 collector;
- exactly one observer;
- only the intended tee/caffeinate wrappers;
- collector command uses `config/collection/rfc007_burn_in_v1.json` and
  `data/ledger/rfc007_live_ledger_v1.sqlite`;
- observer writes the intended current UTC-date file;
- observer round and slot advance;
- RFC-007 cursor advances;
- no duplicate collector initialization;
- the new collector run links to the prior run; and
- logs show no startup or recovery error.

Use `ps`/`pgrep` patterns from Section 13, `lsof` on the new PIDs, read-only
SQLite queries from Section 13, and tail the two logs. Do not infer health from
process existence alone.

The pre-stop operator must replace the checkpoint observation with the actual
final shutdown values and preserve:

| Gap edge | Round | Slot | Timestamp | Byte size |
| --- | ---: | ---: | --- | ---: |
| Checkpoint observation (not final stop) | 393914 | 444576455 | 2026-09-05T17:28:53.051674Z | 12,244,958 |
| Actual final pre-stop record | **record at shutdown** | **record at shutdown** | **record at shutdown** | **record at shutdown** |
| First post-restart record | **record after restart** | **record after restart** | **record after restart** | n/a |

The restart gap must be explicit. It must never be represented as continuous
observation.

Before Stage 3C, measure filesystem free space again, allow macOS accounting to
settle, compare it with Section 9, and seek at least 30 GiB free (prefer about
40 GiB). Do not automatically delete anything.

## 16. Development continuation boundary

After operational collection is healthy and storage is adequate, resume from:

**STAGE 3A LAUNCHER/BOOTSTRAP CANDIDATE COMPLETE — STAGE 3C MAY BEGIN**

Stage 3C is next and is bounded to:

- reservation IPC;
- controller-owned logical disk accounting;
- crash/orphan recovery;
- atomic publication/deduplication; and
- RSS/watchdog machinery.

Governed-host acceptance remains deferred. Preserve the current 22-path
candidate byte identities or account explicitly for every reviewed change.
Do not expand beyond the 38-path surface without renewed governance.

## 17. Downstream non-authorizations

This checkpoint creates no authority for:

- final numeric adoption;
- a production adapter;
- registry adoption or modification;
- Source S;
- readiness E or R;
- Experiment-005 execution;
- outcome or provider access;
- Paper Miner;
- wallet access;
- transaction construction or submission;
- capital deployment; or
- any SOL activity.

## 18. IF THIS CHAT/SESSION IS LOST

1. Authenticate this checkpoint's exact bytes against its recorded SHA-256 and
   determine whether a later authorized commit contains them; an uncommitted
   file has no checkpoint commit authority.
2. Authenticate repository path, branch, HEAD/upstream, index, complete mutable
   boundary, and all 22 current candidate hashes in Section 6. Do not overwrite
   unexplained divergence.
3. Determine from process state, logs, collector-run `ended_at`, cursor, and
   host uptime whether reboot has already occurred.
4. If pre-reboot, follow Sections 12–13 exactly: observer first, catch-up,
   collector second, durability checks, then reboot only after clean stop.
5. If post-reboot, verify state; if restart is needed, start RFC-007 first, wait
   for its startup line, then start the observer second, and verify Section 15.
6. Record the observation gap, reassess storage, and resume Stage 3C only after
   operational health and adequate headroom are established.

## 19. Checkpoint self-identity and construction scope

The authoritative candidate-byte identity fields below must be filled from the
final bytes after construction and verification:

| Property | Value |
| --- | --- |
| Path | `docs/project-checkpoints/ore-v3-pre-maintenance-restart-comprehensive-continuation.md` |
| SHA-256 | `SELF_IDENTITY_RECORDED_IN_FINAL_REPORT` |
| Byte count | `SELF_IDENTITY_RECORDED_IN_FINAL_REPORT` |
| Line count | `SELF_IDENTITY_RECORDED_IN_FINAL_REPORT` |
| Terminal LF | required and verified in final construction audit |
| CR bytes | required zero and verified in final construction audit |

Because embedding a file's own cryptographic digest within itself has no stable
finite fixed point, the SHA-256, bytes, and lines are reported externally in
the final handoff rather than substituted into the hashed file. The exact
checkpoint path is the only path authorized or changed by this task.

Final scope requirements are: 51 mutable paths total; 20 tracked modifications;
31 untracked paths including this checkpoint; empty index; nothing staged,
committed, pushed, reset, checked out, restored, stashed, cleaned, pruned,
garbage-collected, vacuumed, checkpointed, repaired, or deleted; all 50
pre-existing mutable paths byte-identical to their preflight state; and live
observer/collector/tee/caffeinate processes untouched.

## 20. Remaining ambiguity

- The live remote ref could not be authenticated because DNS resolution failed;
  local tracking equality is not remote proof.
- The checkpoint is uncommitted documentation and therefore has no commit or
  remote identity.
- Live PIDs, cursor, file sizes, and final record necessarily advance until the
  controlled stop; shutdown values must replace the point-in-time observations.
- Governed-host acceptance and final numeric evidence remain unavailable in the
  current Codex environment.
- Storage remains below the planning threshold and cleanup targets require
  separate provenance review.
- Stage 3C has not begun.

Subject to the final construction audit, the disposition is:

**COMPREHENSIVE PRE-RESTART CHECKPOINT CANDIDATE READY FOR INDEPENDENT REVIEW**
