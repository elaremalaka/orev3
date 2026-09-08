# ORE Miner V3 — Stage 3C Cross-Layer Frozen Comprehensive Continuation Checkpoint Candidate

**COMPREHENSIVE CONTINUATION CHECKPOINT CANDIDATE —
REVIEW REQUIRED — NOT YET GIT-EFFECTIVE**

Drafted 2026-09-07 for Stage 3C — Orientation & Implementation Boundary.

## 1. Objective, purpose and status

The overarching objective remains **to build an ORE miner that can eventually be trusted to operate with real SOL**. Execution Readiness, research infrastructure, experiments, validation, governance and paper mining are supporting means toward that objective, not endpoints in themselves. This document does not claim real-SOL readiness or production mining authority.

This is a new documentation candidate, not a governance decision, Git adoption of implementation, readiness record, numeric-envelope adoption or operational authorization. Primary controlling governance prevails over this checkpoint. A contradiction requires reconciliation, not an inferred policy edit.

The preceding independent read-only review concluded:

> STAGE 3C CROSS-LAYER FINAL RE-FREEZE PASSED —
> CORRECTED ACQUISITION/PINNED-OWNERSHIP BOUNDARY FROZEN

> CHECKPOINT NOW WARRANTED

> SLICE 4 REMAINS THE NEXT BOUNDED IMPLEMENTATION STEP

These are the recorded review dispositions, not new implementation validation performed while drafting. The checkpoint is warranted by a durable combined milestone: frozen Slice-1 reservation, Slice-2 operation-root/recovery, Slice-3 descriptor accounting/serialization, adopted Stage-3C clarifications, cross-layer DescriptorOwner/result-cell migration, controller and worker acquisition lifetimes, F1 classification, F3 uncertain close, F2 delivery/reentry/restoration/teardown, and acquisition-specific invocation eliminating the active context handoff. Independent controller/worker terminal evidence is included.

The implementation candidate is independently FROZEN **but remains uncommitted and unpushed**. This checkpoint itself is CANDIDATE, REVIEW REQUIRED and NOT YET GIT-EFFECTIVE. The review's checkpoint recommendation explains drafting; it does not adopt this document.

## 2. Authenticated repository authority

| Property | Authenticated starting value |
| --- | --- |
| Repository | `/Users/erale/Documents/orev3` |
| Branch / tracking | `research/post-v1` / `origin/research/post-v1` |
| Local HEAD | `90018eeb54cb1e8590f526f72579ba262dd868d4` |
| Tracking HEAD | `90018eeb54cb1e8590f526f72579ba262dd868d4` |
| Independently queried live remote HEAD | `90018eeb54cb1e8590f526f72579ba262dd868d4` |
| Parent | `d14b516277441a3849525014a92c09529347eadb` |
| Ahead / behind | 0 / 0 |
| Index | Empty |
| Starting mutable boundary | 28 tracked modifications + 30 untracked = 58 |
| Starting identities | 695 / 695 matched preceding final re-freeze |
| `git diff --check` | Pass |

Live remote equality was established by read-only `git ls-remote origin refs/heads/research/post-v1`, not inferred from the tracking ref. The repository path is the current authenticated host path; historical checkpoints may contain older host paths.

The authoritative Git chain remains separate from worktree identities. A frozen worktree file differing from HEAD is not remote-backed merely because this checkpoint lists it.

## 3. Relevant Git-effective history

The following commits were authenticated through repository history. They are ancestors of current HEAD; the current live remote query backs that ancestry.

| Commit | Authority |
| --- | --- |
| `a46173a0420d0bfd4babd17cd1ebbaa911bce241` | Controlling bounded-streaming prerequisite document's current committed revision |
| `045c041453d232e1288e6031fc528d61f8989caa` | Stage-3C recovery-permission clarification |
| `95295a8bd074d803e9405a533915b5592a484ae7` | Stage-3C category-attribution clarification |
| `a7f0ea131237fd6f073f14a3d2fc8544920e6aba` | Stage-3C admission-serialization clarification |
| `fcc2f3f42c94c691b65012fab9d0c75bebc4ef94` | Stage-3C acquisition-lifetime clarification |
| `d14b516277441a3849525014a92c09529347eadb` | Stage-3C controller retirement-status clarification |
| `90018eeb54cb1e8590f526f72579ba262dd868d4` | Stage-3C worker acquisition-lifetime clarification; current remote-backed HEAD |

None of these entries commits the current frozen implementation candidate.

## 4. Seven-document controlling governance inventory

Every row was hashed from repository bytes and compared byte-for-byte with its committed HEAD blob. All seven are Git-effective, including documents whose filenames retain “candidate”. The final column identifies the last commit affecting the authenticated current document, not an inferred implementation adoption.

| Repository-relative path | Role | Bytes | SHA-256 | Git-effective commit |
| --- | --- | ---: | --- | --- |
| `docs/research/governance/rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md` | Controlling bounded-streaming prerequisite, scope, resource and acceptance authority | 179582 | `ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3` | `a46173a0420d0bfd4babd17cd1ebbaa911bce241` |
| `docs/research/governance/rq003-stage3c-acquisition-lifetime-clarification-candidate.md` | Pre-existing ownership, deferred supported cancellation and acquisition classification | 30330 | `1e2c235f11689cd64c65840b3055f377ebef8d9614ea31574e398a15bf29fdcd` | `fcc2f3f42c94c691b65012fab9d0c75bebc4ef94` |
| `docs/research/governance/rq003-stage3c-admission-serialization-clarification-candidate.md` | Serialized observation/admission, exclusion and decision finality | 18602 | `56b4e402a9b4e62853e285be3ed7ca7b7c2d1a0d34d71a7c9ee757b8dffdcfed` | `a7f0ea131237fd6f073f14a3d2fc8544920e6aba` |
| `docs/research/governance/rq003-stage3c-category-attribution-clarification-candidate.md` | Fixed creation-role attribution and category accounting | 19936 | `2e735f2ffe1b4d537495dd7db62d75e21bb6db822c20863f5dc29781c508c101` | `95295a8bd074d803e9405a533915b5592a484ae7` |
| `docs/research/governance/rq003-stage3c-controller-retirement-status-clarification-candidate.md` | Controller-only acquisition uncertainty retirement and status 12 | 18484 | `d9bf01b2449b1819545ef4c186407eb0c16c929534d6ff4bc2f37b8a4b33a304` | `d14b516277441a3849525014a92c09529347eadb` |
| `docs/research/governance/rq003-stage3c-recovery-permission-clarification-candidate.md` | Confined recovery permission, leases, terminal T1/T2 and durability boundaries | 47955 | `7df413610a54adcacb06f5c01dc43b7ce2c04c5244922519871d745c0395f716` | `045c041453d232e1288e6031fc528d61f8989caa` |
| `docs/research/governance/rq003-stage3c-worker-pinned-input-acquisition-lifetime-clarification-candidate.md` | Affected workers' read-only pinned acquisition lifetime and actual unsuccessful termination | 24156 | `be25dd7422e10c6dc775bb3fabbfc0688c71606fdaf8196305f1282208628a9c` | `90018eeb54cb1e8590f526f72579ba262dd868d4` |

The controlling document's referenced prerequisite chain remains controlling. The following authenticated supporting identities are retained for continuation; this table does not create new authority:

| Repository-relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `docs/research/experiments/rq003-experiment-005-signed-share-imbalance-predictive-evaluation.md` | 60015 | `38afa9005bb43050d23e430335e11654c374d4e2d6f4a9f541782c005bffefdc` |
| `docs/research/governance/rq003-minimum-effect-scope-clarification-v1.md` | 7529 | `f736ac301a49be5acca58ef75f5130c1533328cf83cc359c9a69b596c53c2f4b` |
| `docs/research/governance/rq003-experiment-005-source-processing-prerequisite-v1.md` | 46395 | `d6d5d0fb3777cdb2a95e3bbff53b4815c574de68e31d4b5f7f1a0409580799a4` |
| `docs/research/governance/rq003-experiment-005-slice3-authority-prerequisite-v1.md` | 63427 | `d3e8748c63f0a870a3b1e1439fa73ada0145c7502bccc8fd834987e8fb29a36e` |

## 5. Historical checkpoint and protected documentation

The [prior comprehensive checkpoint](ore-v3-pre-maintenance-restart-comprehensive-continuation.md) is preserved unchanged as a historical continuation source. Its repository history records commit `c76e7fd4ac65e35dda0369f1fab05f61c6e953e9`. Its historical prose includes the status and host observations at its drafting time; those observations are not current live-operation evidence. This new candidate does not overwrite or silently supersede it before separate review and authorized adoption.

RFC-007 and RFC-008 working bytes are authenticated below but are pre-existing tracked modifications, not Git-effective versions merely by inclusion here. The backlog modification is also unrelated protected mutable work.

| Repository-relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `docs/project-checkpoints/ore-v3-pre-maintenance-restart-comprehensive-continuation.md` | 41050 | `b0c2ff4fcca6429549792b4a8ff473c39d0a56bede1b86317cd7701c06271925` |
| `docs/research/RFC-007-CONTINUOUS-PAPER-COLLECTION.md` | 15337 | `1d48fc5e1e773e617894a20cc0461e2c6f1ba408a0d2c315bddcda020c642ece` |
| `docs/research/RFC-008-OPERATOR-RUNBOOK.md` | 36759 | `90a2b630ebf8456ba3c7db127feb0312114a7ebaa141711f9803ca72c74ece15` |
| `docs/research/backlog/RESEARCH-BACKLOG.md` | 6508 | `927be537233fd0d3f3d66bb5e633117b12a3f23f07245a73c5e51da724d2c272` |

## 6. Frozen implementation candidate and mutable-boundary classification

The frozen Stage-3C candidate includes the inherited bounded-streaming implementation and ownership-migrated callers, not only the latest two-path correction. The following **28 mutable implementation/configuration/test paths** comprise **25 modified tracked paths and 3 untracked paths**. Their exact worktree bytes are frozen; their current modifications/additions are not committed or pushed.

| Repository-relative path | Worktree status | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `config/research/readiness/rq003-experiment-005-source-processing-v1.json` | M | 4641 | `f17f2934bc313ec31332a490138a8b63c8a5fe0013ff55fae0b2c541a77a550a` |
| `src/orev3/execution/current_readiness.py` | M | 45857 | `6986ba8f81742b8eb40f8e83022297ed4b081e125dc5644ea84f53fdd9250d18` |
| `src/orev3/execution/dataset_validation.py` | M | 7387 | `327af72ca47a9c579f5741b9bc6af33bf568a69e3432ab645773fe5b9d657c78` |
| `src/orev3/execution/evidence_preparation.py` | M | 40811 | `25749df28d847136602e09342c33603e143eb68d2976443e6f98db6913ad0a2d` |
| `src/orev3/execution/evidence_preparation_worker.py` | M | 38101 | `eecd8e2d6c713254d8f53daaf712d833c380f6d0dca1c557ecef4ad8dfc8ff86` |
| `src/orev3/execution/external_inputs.py` | M | 6474 | `9108a8e753bb522ec2fd6e6ee631b379ae0aec2e63cb658e8824371a83c91313` |
| `src/orev3/execution/filesystem_capability.py` | M | 23574 | `40c02368343ddc9a4adf04b59f0871972d8139758708e1d24e491452d728eb00` |
| `src/orev3/execution/input_projection_worker.py` | M | 9187 | `f169ebc1ef4ba16b343937bf1a5544e13b5170cdf42175a59e3186fba832ca23` |
| `src/orev3/execution/preparation.py` | M | 34170 | `b3ffcf6135ba7e9455f7d07e7871929d4d0c1fd510f0a5e229c96e324c4824fa` |
| `src/orev3/execution/projection.py` | M | 6584 | `ce125338ac816ed91c723ee7508887d08b7c8b859d7dbbf54ec1bf9b64f4df23` |
| `src/orev3/execution/readiness_contracts.py` | M | 47972 | `6fb4c4993f9314a79c7cffc7879b6f9f79d452b7339162a42bd1297a82be19f2` |
| `src/orev3/execution/readiness_record.py` | M | 106769 | `f9b1a33632f7e31cf26b19e14e7a2d39a697742ebd6d9bbd63c251c907a6c806` |
| `src/orev3/execution/replay_preparation.py` | M | 11814 | `1f98b1404eeeb9bde6046961a854c578dd29ef06493f6f44b3d65cc8135b6b3d` |
| `src/orev3/execution/replay_preparation_worker.py` | M | 5572 | `901ce12dab86544d9bb54dd44c532b9842b87f93dbd236f211ea6f05f25ea708` |
| `src/orev3/execution/runtime.py` | M | 165138 | `0f5fc3b008afaa9f83b638d0b744cfb8fa72437aeb35e03696ce6d80bb7bd7c4` |
| `src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json` | M | 12522 | `c401708cc5b1803d8e2f20538469dc6a9b5f3050f818e0388913a1ac6e266844` |
| `src/orev3/experiments/rq003_experiment5_source_processing.py` | M | 106848 | `b06ecce03f8b3a5c74235f5f97399be1039dad0074257d8e38f212b688875835` |
| `tests/execution/test_phase3a_preparation.py` | M | 19967 | `f1a22ea91821c52a8f387926ff4472700ba0ae8c51e0a0a1ce465a0a8957da1e` |
| `tests/execution/test_phase3b_authority.py` | M | 17760 | `bbfb27c246894469301038ec80ce5c01cc7f8c278aaa7e65c99c8e6f877cc0f2` |
| `tests/execution/test_phase3b_external_inputs.py` | M | 14075 | `eb8969ff94ba507e3b7bbc7e84f22807b2de5185067a73022acb718af6554570` |
| `tests/execution/test_phase3b_reconstruction.py` | M | 32678 | `3a6ce08a12d4bc856d855270fdba8bcb22616a68f6bd8eddd5040d5b0fe153ee` |
| `tests/execution/test_phase3b_worker_boundaries.py` | M | 280647 | `1da5a9f3ecab510c1b9b0f8c640334b1d77dc663b1a49d6e9db9d14d050345b5` |
| `tests/execution/test_phase3c_current_readiness.py` | M | 35043 | `ddf82574f110a7d80903406dfd07245ac0469feea4ef9925e1c9288c775baa71` |
| `tests/execution/test_phase3c_readiness_record_v2.py` | M | 70259 | `ce13aaf1d55d576991cff3400ba27620d788585a3ac1e99e1b6fbafc44aa854a` |
| `tests/experiments/test_rq003_experiment5_source_processing.py` | M | 54434 | `b274ad03c66810a9aa3abad0b61045fbc012079b00ce9366a5ab7793c7a7966f` |
| `config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json` | ?? | 4165 | `86ecbaa792277229650874a8bb27624c68ee7dbaf135fa301a719926b604261d` |
| `src/orev3/execution/bounded_streaming_worker_bootstrap.py` | ?? | 43167 | `8e86f67a7f8f1ec6f408c838875581bfd3323a94727343af503bdec1a58c46bf` |
| `src/orev3/execution/schemas/v1/evidence-preparation-policy-bounded-streaming-v1.schema.json` | ?? | 7200 | `2a89187c8f07a57b92ba1ddf209c5e68079823dd0f3a4bbe25307b162ea011b3` |

The latest acquisition-invocation correction alone changed runtime.py by +21/-22 lines and test_phase3b_worker_boundaries.py by +438/-76 lines relative to the immediately preceding candidate. No unrelated production body changed. The latest test migration changed 16 existing functions, deleted no prior tests, preserved existing assertion expressions (including embedded subprocess assertions), and added 76 invocation cases. This historical delta is distinct from the full dirty-worktree delta against HEAD.

### Mutable boundary reconciliation

| Population before this draft | Tracked modifications | Untracked | Total |
| --- | ---: | ---: | ---: |
| Frozen Stage-3C candidate above | 25 | 3 | 28 |
| Unrelated pre-existing RFC/backlog modifications | 3 | 0 | 3 |
| Unrelated untracked research/documentation below | 0 | 27 | 27 |
| Total starting boundary | 28 | 30 | 58 |
| New checkpoint candidate only | 0 | 1 | 1 |
| Expected boundary after this draft | 28 | 31 | 59 |

The checkpoint candidate is not an implementation candidate path. The unrelated populations are preservation boundaries only, not frozen Stage-3C implementation. No future staging plan may treat the whole dirty worktree as one adoption unit.

Unrelated untracked files, all to remain untouched:

| Repository-relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `docs/research/findings/rq003-participant-state-synthesis.md` | 12282 | `30fe030aaef12ccc16ebd5675a0f71247a083d67e2f6230f315392e874f913fd` |
| `docs/research/governance-post-v1-investigation.md` | 14475 | `b88d5a3964d9f433ba23761990162912a8eb007d204104800399f9fb08df8731` |
| `docs/research/governance/rq003-delta-min-governance-decision.md` | 8849 | `01c9a0d195a436e2b89585d4f819a2c22f5974be068a4c7cf39693e3acb06c32` |
| `docs/research/governance/rq003-delta-min-governance-placement-review.md` | 10548 | `91b8d83957bce189ab1bdf06f45d9a9d227b950fd31bb2cf35f498c983655318` |
| `docs/research/governance/rq003-delta-min-scientific-justification.md` | 11048 | `798c5d855ab69b954db7e140d1d3bff36255ae94c5aa6c6261164da3568bc9ff` |
| `docs/research/governance/rq003-experiment-2b-authorization-review.md` | 10458 | `b70e0b763a511a41b3cfa914a478c6c34aafab32ba877053f8e1fed0352af4d2` |
| `docs/research/governance/rq003-governance-consistency-review.md` | 9058 | `7d29cd1132c4e1127a930b5433689baca52bdc5a079131dab96949e36ba5d0c4` |
| `docs/research/investigations/protocol-revision-strategy.md` | 27581 | `f132677105e6662bcd85a9b8e37710a7b047e05b97c7422cbcddc164104243ec` |
| `docs/research/investigations/rb001-dataset-build-performance.md` | 19620 | `eb64fa2ae735f48fa2eb728d8d7c8afcc24b56559508bbbe011f28749d562b3b` |
| `docs/research/investigations/rb001a-freeze-verification-investigation.md` | 18838 | `7e107d74224103f6df75513dcb9bcb58beef15d290d6be5910d878bb635ca90f` |
| `docs/research/investigations/rb001b-proof-carrying-snapshot-artifact.md` | 29497 | `d12cbc2be2ff84eadbe9df70b2c791af13d6eec078875a2a7f42334a82377fb7` |
| `docs/research/investigations/rfc013-candidacy-assessment.md` | 20790 | `60f19c7ce5d40c885d41b2a65c0e427d0b67ed093fbcfc0b110324a4ef17db04` |
| `docs/research/investigations/rq003-decision-quality-theory-design.md` | 15425 | `d57fc95520e9e9921c11dd00a85047f4459f6f10a3db3ddacc488d883b852e57` |
| `docs/research/investigations/rq003-decision-quality-theory.md` | 12874 | `7cf40c53592a464e19c59668d3112ead4f0b83b8864774731b6281fab0c66879` |
| `docs/research/investigations/rq003-measurement-implementation-alignment.md` | 17960 | `f4a0e70971afb2f7e2e97f74cec99c10d127568124c90011da1c5da18a1b067e` |
| `docs/research/investigations/rq003-participant-state-consistency-review.md` | 15555 | `e8f3f2023b932e8cb1c3e8b315d33219bd820e3c9302976266ab580fdb9fafef` |
| `docs/research/investigations/rq003-phase3a-immutable-context.md` | 22025 | `8a742ba03fedba130d88248459fae3546c20cd58118028dbe8de92f64cde4bfa` |
| `docs/research/investigations/rq003-phase4-pipeline-review.md` | 16995 | `61e1d807e5990a99a11908baba90d6c805f84550938c968dfc6774654d8cf3d8` |
| `docs/research/investigations/rq003-protocol-state-discovery.md` | 16882 | `b1b6e16a81966f0e565ab7e3497826e2c52e165373b7466fc7bccaa6083650ef` |
| `docs/research/observer-transition-analysis.md` | 9968 | `ec044a9b9a6a039b0882452656e5a663fc31cf186e1fede6f782b1322e7bca6f` |
| `docs/research/post-v1-observer-validation.md` | 9825 | `32dd20cc2dd24e78cd31b8c774b81fe27e0ae8658b7199cc48f19efb277933bf` |
| `docs/research/promotion-domain-rfc012.md` | 11093 | `6affa44af19f6cec979ffed4ae2dda6d4af07269bdabe9dc5f8aa86cd5fc70ca` |
| `docs/research/questions/RQ-003-phase3-feature-framework.md` | 33486 | `85059b2d3ffbb680f861cf6c5f542d6f97a40f0576976798baa24569358df6b5` |
| `docs/research/rfc012-readiness-review.md` | 23219 | `0ea0347f63a1398abb96b652f63ff55bfecd9c6d980407230b9d2d93bbf26fc7` |
| `docs/research/rfc012/rfc012-implementation-plan-readiness-review.md` | 23788 | `2490b334673590367ff396204c4e44a308b131fa3fc3e4d4feea0191f3043e15` |
| `docs/research/rfc012/rfc012-validation-analysis.md` | 13351 | `10b9898d012bdb47a685541756342118599e6dd8cb783f01182e2754bf7f9b57` |
| `docs/research/specifications/rq003-research-execution-profiles-proposal.md` | 15457 | `18f4e0a7ed4dc747a041cead8d9403695a7d284d71a6d6bb58e186d5ea3466e3` |

Appendix A preserves all 695 starting identities, including unchanged support files and unrelated work. It is an authentication inventory, not a claim that all 695 paths belong to Stage 3C or have newly acquired authority.

## 7. Slice 1 — frozen reservation authority

The reservation core and allowance primitive preserve the reviewed Slice-1 F1/F2 reservation properties; these historical reservation labels are distinct from the later acquisition F1 and cancellation F2 defect labels.

Preparing a request does not grant capacity. Issuing an ACK commits the complete ledger/sequence transition. Rejection leaves ledger and sequence unchanged. A matching allowance is single-use, with governed operation/category/sequence checks. No arbitrary worker claim becomes controller observation authority.

Short-write capacity is reconciled only through the governed accepted same-category transition or authenticated orderly completion. Bare transport EOF does not release capacity; it freezes admission pending classification. Failed/uncertain execution retains the acknowledged conservative floor. Post-ACK transport failure cannot undo a committed reservation.

This is frozen primitive authority, not writer/IPC activation. Reservation regressions passed (197); overlapping accounting selections also preserve these rules.

## 8. Slice 2 — frozen operation-root and recovery authority

Controller namespace ownership, descriptor authentication, coordination exclusion and operation leases govern confined operation roots. Recovery is descriptor-confined and fail closed on ambiguity, substitution or unauthenticated state. Handoff preserves one disposal authority and aggregate orphan accounting; deletion, orphanhood or release is not inferred from a numeric FD or process death alone.

Recovery terminal states retain their exact distinction: T1 is the authenticated lease-only terminal directory; T2 is the authenticated empty terminal directory. Restart handling reauthenticates state and required exclusion/durability barriers. An ordinary missing-lease root is not automatically a valid terminal T2 state.

R1 uncertain-close non-retry and entry-safety corrections remain frozen. Incomplete entry and exceptional teardown do not admit healthy-looking continuation. An uncertain lease remains observable; repeated cleanup does not retry its integer; FD reuse cannot close an unrelated replacement. Independent resources still receive teardown attempts. F3 uncertain-close disposition is part of this boundary.

Evidence: entry_safety 35; operation_recovery 152; operation_recovery_r1 or handoff 56; independent lease uncertainty/FD-reuse probes.

## 9. Slice 3 — frozen descriptor accounting and serialization

ControllerDescriptorAccounting binds authenticated descriptor/inode identity to a fixed creation role and category. The five categories are snapshot_growth, projection_publication, reconstruction_growth, controller_temporary_growth and worker_output_growth. Logical size is observed from authenticated descriptors; a worker/request assertion does not replace observation.

Preparation and ACK admission serialize controller-owned observation, existing-charge validation, target binding and sequence transition. Stale preparation rejects before ACK. Controller mutation/activity exclusion and coordination authority protect the modeled admission interval; they do not claim to intercept malicious trusted-code raw OS operations or authorize general writer execution.

Decision-slot publication preserves complete pre-commit or complete post-commit state. Pre-publication invalidation prevents ACK authority; post-publication failure cannot roll back commitment. Rejection finality and entry safety remain intact.

Independent evidence:

| Case | Required and observed state |
| --- | --- |
| Unexplained reconstruction 5 + controller request 10 / budget 10 | Reject; charged=0, reserved=0, sequence=0, no ACK |
| Stale preparation | Reject before ACK/sequence advancement |
| Pre-publication invalidation | No commitment |
| Post-publication invalidation | Complete committed state retained |
| Authoritative orderly reservation 10 -> actual 3, then scratch-close failure | Charged/reserved 3 remains authoritative; sequence 1 retained; seven unwritten bytes are not restored; resource ownership may quarantine |

Evidence: finality 34; admission 112; descriptor_accounting 195; reservation 197, plus independent probes. No Slice-1/2/3 body was redesigned by the invocation correction.

## 10. Cross-layer DescriptorOwner/result-cell architecture

Exactly one explicit enclosing DescriptorOwner disposal authority exists before acquisition. DescriptorOwner._receive registers the result cell before calling the installed actor policy. Successful DescriptorAcquisition.acquire records the descriptor into that cell. Helpers and callers receive borrowed access, not a transfer of disposal authority at return or assignment.

An interrupted final policy/helper return therefore cannot erase known ownership. Close uncertainty is retained explicitly and the uncertain integer becomes non-retryable. No second ledger, independent automatic closer, finalizer, __del__, atexit or GC-dependent cleanup supplies correctness.

Ownership-migrated shared callers remain actor-neutral. Explicit policy routing, not filename/stack heuristics, selects controller or worker disposition.

## 11. Controller acquisition and cancellation model

The frozen invocation is:

```text
pre-existing registered result cell
  -> policy-owned bounded invocation
  -> protection setup / supported cancellation deferral
  -> descriptor acquisition
  -> definitive failure / known ownership / unprovable ownership classification
  -> eligible cancellation handling
  -> exact restoration and teardown
  -> complete or discoverably failed state
  -> final return
  -> borrowed descriptor access
```

Production has no .protected() invocation, no _controller_protected_scope, and no caller-visible active acquisition context. Caller receipt is neither an ownership transfer nor a completion acknowledgement. The private generator is driven through its whole active lifetime inside one policy invocation; its empty terminal yield yields no active value to caller work.

Protection covers only acquisition setup, acquisition/classification and eligible delivery/restoration/teardown. Actor-routing controller_acquisition_policy contexts do not defer cancellation across whole readiness, publication, scientific processing or unrelated waits.

Supported raising handlers are converted to deferral across the bounded interval. Nested acquisition preserves outer handler/delivery ownership. One original request selects one active delivery; request B during delivery A is explicitly subsumed/coalesced. Later independent request C remains deliverable after clean completion. Exact original handlers are restored on clean teardown.

Known-owner policy uncertainty fails closed and rejects later acquisition; it does not automatically select status 12. Numerical depth may remain stale only when incomplete ended work remains authoritatively discoverable as failed. No future acquisition may treat stale depth as legitimate healthy nesting.

## 12. Final F1/F2/F3 dispositions

### F1 — acquisition classification

Genuine native acquisition failure is ordinary failure. Post-success unprovable ownership selects the actor-specific terminal disposition. Exception class alone is insufficient to establish a definitive native failure. The controller uses authenticated RETIRING/status 12; the two affected workers select irreversible failed invocation and actual unsuccessful termination.

The CPython C-call classification evidence is runtime-qualified, not a universal Python atomicity promise. filesystem_capability.py remains the authenticated frozen implementation.

### F2 — cancellation and lifetime final invariants

The corrected classes include rejection-finality interaction, cancellation delivery entry, duplicate delivery on handler reentry, signal restoration, teardown entry and the context-manager handoff reconciliation. The final acquisition-specific invocation removes the unnecessary live context handoff rather than strengthening a caller-receipt enum.

Restoration authority is recorded before temporary handler installation. Unrestored, unresolved and restored obligations remain distinct. Exact handler identity is verified before restored publication. Partial restoration and interruption during failure recording retain unfinished obligations. Executing invocation failure leaves retained incomplete authority immediately discoverable with GC disabled. Complete state is published only after the owned obligations settle.

Synthetic exceptions at obsolete wrapper boundaries were not adopted as a universal production cancellation mechanism. Supported real signal intent is deferred; detected acquisition uncertainty still retires and detected policy incompleteness still fails closed. Arbitrary Python return atomicity is not required.

### F3 — uncertain close

Uncertainty exists before interruptible detailed failure recording. The uncertain descriptor integer is non-retryable; ownership/disposition remains explicit. Operation lease uncertainty stays observable. Repeated cleanup fails closed without retrying the integer, unrelated replacement FDs survive, and independent resources continue receiving teardown attempts.

## 13. Actor/status and worker model

| Actor/domain | Frozen disposition |
| --- | --- |
| Controller acquisition ownership genuinely unprovable | Process-wide irreversible RETIRING; non-returning terminal route; status 12; BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE |
| Known-owner controller policy/restoration uncertainty | Existing failure/quarantine; later normal acquisition rejected; no automatic status 12 |
| INPUT_PROJECTOR and REPLAY_PREPARATION acquisition uncertainty | Irreversible failed invocation and actual unsuccessful termination; existing generic unsuccessful transport/status 10 where applicable |
| Import/session integrity | Status 70 only for BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY |

A numeric returncode alone does not authenticate semantic attribution. No worker acquires controller status 12; status 10 is not expanded into cause-specific authority; status 70 remains integrity-only.

The worker clarification covers existing read-only pinned inputs and non-creating traversal, including delayed replay iterator reopen. Worker death reclaims kernel-local references; it does not establish deletion, orphanhood, external-reference cleanup or child cleanup. No worker semantics were redesigned by the controller invocation correction.

evidence_preparation_worker.py is an explicitly routed detached controller despite its filename. Controller routing surrounds snapshot_declared_input(), publish_projection_path() and publish_projection(). Shared helpers themselves are not controller actors. Runtime namespace operations and current readiness likewise use explicit routing without broadening cancellation deferral.

## 14. Recorded independent re-freeze validation

This section records the preceding independent review, not tests rerun during checkpoint drafting. Every pytest invocation in that review used exactly:

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src /Users/erale/Documents/orev3/.venv/bin/python -B -m pytest -p no:cacheprovider -q
```

Focused arguments were tests/execution/test_phase3b_worker_boundaries.py -k followed by the exact selection below. Overlapping selections MUST NOT be summed into a distinct-test total.

| Selection | Passed | Deselected | Failed |
| --- | ---: | ---: | ---: |
| `acquisition_lifetime_f2_invocation` | 76 | 1038 | 0 |
| `acquisition_lifetime_f2_teardown` | 92 | 1022 | 0 |
| `acquisition_lifetime_f2_restoration` | 51 | 1063 | 0 |
| `acquisition_lifetime_f2_reentry` | 84 | 1030 | 0 |
| `acquisition_lifetime_f2` | 330 | 784 | 0 |
| `acquisition_lifetime_f` | 399 | 715 | 0 |
| `acquisition_lifetime` | 509 | 605 | 0 |
| `entry_safety` | 35 | 1079 | 0 |
| `operation_recovery` | 152 | 962 | 0 |
| `operation_recovery_r1 or handoff` | 56 | 1058 | 0 |
| `descriptor_accounting_admission_finality` | 34 | 1080 | 0 |
| `descriptor_accounting_admission` | 112 | 1002 | 0 |
| `descriptor_accounting` | 195 | 919 | 0 |
| `reservation` | 197 | 917 | 0 |

Broader commands used the same prefix; exact appended arguments and recorded results:

```text
tests/execution/test_phase3b_external_inputs.py tests/execution/test_phase3b_reconstruction.py
```

65 passed; 0 deselected; 0 failed

```text
tests/execution/test_phase3b_worker_boundaries.py -k 'not acquisition_lifetime and not descriptor_accounting and not operation_recovery and not reservation and not readiness_worker and not projection_worker and not projector_rejection and not semantic_worker and not exact_readiness and not malicious_conftest and not real_sibling'
```

49 passed; 1065 deselected; 0 failed

```text
tests/features tests/execution/test_phase3b_authority.py tests/execution/test_phase3b_reconstruction.py tests/experiments/test_rq003_experiment5_source_processing.py -k 'not finite_input_projection_worker_invokes_governed_decoder'
```

513 passed; 1 deselected; 0 failed; established decoder exclusion retained

```text
tests/execution/test_phase3a_preparation.py::test_adapter_v4_phase3a_generation_uses_exact_v11_authority_documents tests/execution/test_phase3a_preparation.py::test_phase3a_generation_dispatch_rejects_cross_enum_before_repository_access tests/execution/test_phase3a_preparation.py::test_success_is_non_authoritative_and_explicitly_incomplete tests/execution/test_phase3a_preparation.py::test_normal_api_cannot_accept_fabricated_source_candidate
```

4 passed; 0 deselected; 0 failed

```text
tests/execution/test_phase3b_worker_boundaries.py -k 'projection_worker or projector_rejection or semantic_worker'
```

Enclosing tool sandbox: 4 passed, 1108 deselected, 2 environmental failures. Identical command outside only the enclosing restriction: 6 passed, 1108 deselected, 0 failed.

```text
tests/execution/test_phase3c_current_readiness.py::test_regular_current_input_exact_bytes_reaches_execution_ready
```

1 passed; 0 deselected; 0 failed

```text
tests/execution/test_phase3c_readiness_record_v2.py -k 'not git_validator'
```

13 passed; 22 deselected; 0 failed

The worker environmental failure was exactly `sandbox_apply: Operation not permitted`. Project sandbox profiles and permissions remained unchanged for the rerun. This qualification does not conceal a changed project sandbox or grant governed-host acceptance.

Readiness/scientific production bodies were AST-identical relative to the prior candidate, supporting targeted readiness qualification. No readiness/Experiment-005 operational execution authority was granted.

## 15. Independent adversarial evidence and limits

These are preceding-review probes outside permanent tests, using isolated interpreters and synthetic resources. Critical lifetime probes disabled GC and asserted ownership/state before harness cleanup.

| Probe family | Recorded evidence |
| --- | --- |
| Final policy return | 15 KI/SystemExit/BaseException cases across regular, directory, definitive native failure, known-owner teardown failure and clean cancellation outcomes; known descriptors retained and valid; no false retirement |
| Real SIGINT at nine acquisition phases | 27 cases; 24 clean with later delivery, 3 restoration interruptions explicitly fail closed with later acquisition rejected |
| Internal teardown/partial restoration/failure recording | 12 independent cases; incomplete scope/obligations retained; known descriptors retained |
| Additional teardown/restoration boundaries | 30 injections; no healthy incomplete state; post-completion interruption remains clean |
| F1 actors | 15 cases: 3 ordinary native failures plus four post-success exception forms for each actor; controller authenticated exit 12, workers actual unsuccessful exit 10; no terminal continuation |
| F3 lease uncertainty | 4 exception/real-SIGINT cases; six distinct teardown attempts, one lease-close attempt, explicit uncertainty, reused replacement FD survives repeated cleanup |
| Handler reentry | 16 normal/KI/SystemExit/BaseException cases across no nesting, pinned, sequential and reentrant acquisition; one A delivery, B subsumption, later C delivery |
| RETIRING dominance | Isolated classification, reentry, teardown and restoration probes; canonical identifier and one terminal owner; ordinary returncode 12 |
| Accounting/finality | Independent cross-category 5+10/budget-10, stale preparation, pre/post publication finality and orderly 10->3 cases from Section 9 |

The final-return and phase matrices establish clean-or-governed-failure outcomes, not an unconditional clean-restoration promise. The six implementation-development failures reported before the independent review concerned new expectations incorrectly demanding clean state after restoration interruption. Final expectations required retained ownership, fail-closed policy and rejected later acquisition; independent probes confirmed that disposition. No old governed assertion was weakened.

An independent reentry harness initially targeted macOS's /tmp symlink and was correctly rejected by pinned-path validation. Retargeting the synthetic probe to /private/tmp passed without production changes. This is a harness correction, not a production exception.

Permanent regressions, synthetic exception injection, trace-aligned real signal intent and governed-host acceptance are distinct evidence classes. No probe establishes arbitrary asynchronous Python return atomicity.

## 16. Runtime qualification and deferred acceptance

Authenticated evidence runtime: **CPython 3.14.5; macOS 15.0.1; Darwin/POSIX; arm64; GIL enabled**, using the repository .venv interpreter. Immediate generator-frame closure on escaping exception and signal/C-call evidence are qualified to this runtime. No universal Python or unsupported-runtime guarantee is asserted.

The following remain **DEFERRED**:

- Production signal timing.
- Launcher/Seatbelt enforcement.
- Worker no-descendant topology.
- Filesystem durability.
- Production runtime qualification.
- Provider/backend integration.
- Production adapter/registry.
- RSS/watchdog behavior.
- Real-capital operation.

Synthetic and isolated subprocess evidence is not governed-host acceptance.

## 17. Numeric mode and closed downstream authority

Numeric mode remains exactly:

```text
BOUNDED_STREAMING_MEASUREMENT_CANDIDATE
```

No numeric-envelope adoption occurred.

No authority is granted for Slice-4 implementation; writer/worker/IPC activation; publication/dedup activation or redesign; RSS/watchdog activation; numeric adoption; governed-host acceptance; readiness/Experiment-005 execution; provider/outcome authority; production adapter/registry/Source S; wallet/funding; transaction construction/signing/submission; capital allocation; real-SOL activity; or production mining.

No F1/F3/DescriptorOwner redesign, status allocation/expansion, native component or process-spawn/PID-lifetime redesign is authorized. Status 12 remains controller-only, status 10 generic worker unsuccessful transport and status 70 integrity-only.

## 18. Next bounded implementation step — planning only

**SLICE 4 REMAINS THE NEXT BOUNDED IMPLEMENTATION STEP**

The independently assessed next step is controller-side reserve-before-growth enforcement for the bounded bootstrap-request artifact. It requires separate future authorization and is neither implemented nor authorized by this checkpoint.

Expected integration facts already supported by frozen primitives: fixed controller_temporary_growth attribution; descriptor-backed logical-size observation; serialized admission; reservation before each bounded growth; matching single-use allowance; short-write reconciliation; failed/uncertain retention; and the frozen owner/policy acquisition mechanism.

The existing bootstrap-request writer is not thereby declared integrated with Slice 4. Request creation/acquisition and writes still need that separately authorized bounded integration. No additional prerequisite was exposed by the preceding review; that assessment does not permit editing.

## 19. Fresh-lane continuation and authentication procedure

1. Begin in Stage 3C — Orientation & Implementation Boundary. Read repository instructions and the seven primary governance documents. Preserve the objective and all non-authorizations above.
2. Authenticate repository path, branch, upstream, local HEAD, parent, tracking HEAD, ahead/behind, index and actual mutable status. Independently query the live remote branch with read-only git ls-remote. Do not fetch/stage/commit/push as an implicit prerequisite.
3. Authenticate this checkpoint's exact bytes/line count/SHA-256 against its externally reported draft identity and subsequent independent review/adoption record. A file cannot embed its own final SHA-256 without self-reference; the draft task's final report supplies that identity. If unavailable, obtain an independently authenticated reference before relying on this candidate.
4. Recompute the seven governance identities and compare their working bytes to HEAD blobs. Check the Git ancestry and exact commits in Section 3.
5. Recompute every Appendix A path's byte count and SHA-256, and verify no listed path is missing. Reconcile the path population: 695 starting paths plus this one candidate is 696. Do not infer identity from mtime, status counts or passing tests.
6. Reconcile the frozen mutable candidate table separately from unrelated tracked and untracked work. Expected draft boundary is 28 tracked modifications + 31 untracked = 59; index empty. A later separately authorized adoption may legitimately change Git state, but requires explicit reconciled authority.
7. Distinguish committed remote-backed HEAD from frozen uncommitted candidate bytes. Neither this document nor a re-freeze PASS means implementation changes have been committed.
8. Treat previous test/probe counts as recorded evidence for these exact candidate identities. This draft task ran document/identity validation only; it did not rerun implementation suites or create new implementation validation.
9. Preserve the historical prior checkpoint. This candidate requires a separate READ-ONLY independent checkpoint review for authority, completeness, identities, mutable classification, frozen behavior, evidence, non-authorizations, continuation rules and absence of authority expansion.
10. Stop on identity, Git, governance or implementation-boundary mismatch. Do not silently repair files, invent policy, broaden scope or continue under assumed equivalence.
11. Require separate explicit authorization for any checkpoint adoption/status edit, staging/commit/push, implementation-candidate Git adoption or Slice 4. Passing checkpoint review alone authorizes none of these actions.

For a read-only inventory use git ls-files --cached --others --exclude-standard -z and hash the resulting unique paths. Appendix A paths are repository-relative. Use Python -B with PYTHONDONTWRITEBYTECODE=1 for repository helper validation to avoid bytecode writes. Do not run an automatic formatter or mutate project sandbox profiles.

## 20. Draft/adoption boundary and self-review expectations

The only authorized write is this new checkpoint document. All 695 starting paths must remain byte-exact with no removals and no additional path beyond this checkpoint. The implementation candidate stays frozen and uncommitted; checkpoint drafting does not reopen or adopt it.

This candidate is not authority to commit the entire worktree or bundle frozen implementation files. Any future staging plan must be separately derived and explicitly authorized. Checkpoint-only adoption is separate from implementation-candidate adoption unless a later explicit instruction says otherwise. Any convention-required status/adoption edit after review also needs separate authorization.

Draft self-review must check the Git/worktree distinction, all hashes/commits, population classification, objective, status semantics, runtime limits, deferrals, non-authorizations, historical-checkpoint preservation and fresh-lane procedure. Independent checkpoint review is a separate task and is not performed by the drafting lane.

## Appendix A — Complete starting preservation manifest (695 paths)

This appendix is the authenticated pre-draft byte baseline. It deliberately includes unrelated work for preservation verification. **Membership is not Stage-3C candidacy, governance adoption or permission to stage.** Only Section 6 classifies the mutable Stage-3C candidate; Section 4 identifies the seven controlling documents.

The checkpoint candidate itself is excluded to avoid self-reference. Its final identity is supplied in the drafting report. Exactly one new path is expected after drafting; every row below must remain exact.

| Repository-relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `.env.example` | 156 | `b54f5c8dd277d96c6b74694b79d34fb5aa1f1df238ec455f015e2c1485a66828` |
| `.gitignore` | 3099 | `431a61a1b1d0897cbe0165d2f4863354fdb3895a112d0dae42b42feca7725f9b` |
| `AGENTS.md` | 1848 | `c412fe24ec8bfe6a4eddff23c0cd335c2839012efdf7ce10cbea4ebcc73540be` |
| `README.md` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `SECURITY.md` | 2733 | `7007839784dc78e8484eb3b545a6ec83d64e1c98a277e82993ae6ced6af98c38` |
| `VERSION.md` | 2259 | `a82f9e2c6a83c89d18268a421e3983c7bd810569d4e47d01491842beff91a152` |
| `config/collection/rfc007_burn_in_v1.json` | 1248 | `c1c41cf39ee3c43bcebe3f345d6ba02e3f53e5f3043e52b82448311c9967e9d3` |
| `config/collection/rfc008_paper_v1.json` | 2316 | `6ff8d08105ea18d338b72b9c8cf42430a7900e6a28382f0b2a52d551982338fa` |
| `config/collection/rfc008_resolver_v1.json` | 763 | `1220a73f256769ee175dc66ba3b2246ce88944fa2cae743e55ec3f177489b722` |
| `config/economics/rfc005_assumptions_v1.json` | 1251 | `b033149f9145d4286f2b4acc1ece1fe1207fb7a269709d81548d9b9a5674ae42` |
| `config/ledger/rfc006_collection_v1.json` | 418 | `40e2b501110753b94fc2893699de333b44dbb70abcb5e84e6fe6f680bb2b44bf` |
| `config/research/readiness/adapter-registry-v1.json` | 234 | `0178164bd7a7ee36f55717e7a43799fd282831ec5eab276845bbb41aaa3f74c5` |
| `config/research/readiness/attempt-authority-contract-v1.json` | 2046 | `d926771bb1eb182383df17f912519aeec80cd3fb18ae0757341a14f6220fbbd5` |
| `config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json` | 4165 | `86ecbaa792277229650874a8bb27624c68ee7dbaf135fa301a719926b604261d` |
| `config/research/readiness/evidence-preparation-policy-v1.json` | 2992 | `4810b07d9789ffbdff6bbd5ece5cf146b7168a5c25431ed50e7b4452b7afa730` |
| `config/research/readiness/offline-artifact-manifest-v1.json` | 7791 | `6c02495dc8164b55a8c6aab8bcd4f34d8853489323b435b1807048beace2eafc` |
| `config/research/readiness/readiness-test-policy-v1.json` | 576 | `918772c164dc0686fae8d8b284698ae43afe514e52a38625b3f5c1ec91747572` |
| `config/research/readiness/readiness-test-policy-v2.json` | 809 | `2601d8d306ef435b5cb3657464610426d357736f0143f03dda765a16f349668b` |
| `config/research/readiness/repository-authority-v1.json` | 280 | `77fbdfa2f1c459b11a0ba0972b1981860d2e9308228d7fed36c8a005ef16a564` |
| `config/research/readiness/rq003-experiment-005-source-processing-v1.json` | 4641 | `f17f2934bc313ec31332a490138a8b63c8a5fe0013ff55fae0b2c541a77a550a` |
| `config/research/readiness/runtime-contract-v1.json` | 73876 | `a57c3b8c9abb1c4dca4b372f2fc3a9a29de5688c0eb1a3af224230e1d5c8920e` |
| `data/processed/.gitkeep` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `data/raw/.gitkeep` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `data/recovery/rfc007_gate_b_outcome_recovery_v1/evidence.jsonl` | 107697 | `0d04f1b7586963612d784982fd1ca7d4213b8a9466680d5a3a0d9c73611eda77` |
| `data/recovery/rfc007_gate_b_outcome_recovery_v1/manifest.json` | 4684 | `fbb47f3b1dd7c4763f990f1c913bc9efc970cd25eb834a34591e78bea84810ea` |
| `data/research/README.md` | 2193 | `678ebf6c16297e5ff2b72b191fd4f89d2fe3d5f4f659b47a321d04002b5d810a` |
| `data/research/analyses/README.md` | 504 | `feb103b0fd5bdcdc4ac66baa39452572569c2c74ff4398b85f25d7e042448276` |
| `data/research/exports/README.md` | 330 | `b10e22af541853428cd49efda22c41bf2b8820092c871df855bf737c38ae9b4b` |
| `data/research/snapshots/rfc012-validation-48hr/README.md` | 3158 | `c8f34f4f2bdc8e8dd564ec025c5a2cf7876a6adf1114823f89841d9d9f4b9ae5` |
| `data/research/square_features_v1_slots_20.manifest.json` | 401 | `2f9a4de8fae921cf634e09d7153dec20a248d278e2fa843315f479e5921eb105` |
| `data/research/square_features_v2_slots_20.manifest.json` | 404 | `b5028d943d81bb3024dae7b8d0e5c6e484a375f31ce0e5e7c990d01ef1090a68` |
| `docs/PROJECT_CONSTITUTION.md` | 3266 | `1542767c36fc7ea417095c270860b030c66b77561eb1c1e03c69a9364658426d` |
| `docs/README.md` | 1588 | `0e680e06f20483b0cc01d1992c800ab64b12641e0cb1365867c61424fd1db2ce` |
| `docs/adr/ADR-001-dataset-first.md` | 424 | `ac526ca2949ee56b0d55a77914b525f3625bdb3708c3e06f2fb33e0caf6678b4` |
| `docs/adr/ADR-002-immutable-datasets.md` | 282 | `3a40b9455b23e033aeaa1cbbd961f34cf0cd500df1f5ca5e54c6bc6674da57ef` |
| `docs/adr/ADR-003-evidence-driven-strategies.md` | 336 | `44fc7a6c1d7d2261bcf734ee72e74721bcd52e7db3c63f3e7ecdc8ed9cd6e2b5` |
| `docs/adr/ADR-004-walk-forward-validation.md` | 312 | `e7580267ebacfc30ea06321ef94992a71e712b58f27e57225804a6e6f0afbbc5` |
| `docs/adr/ADR-005-production-miner-gate.md` | 475 | `6480e4c6c2e4f7daa816ff399fc9c1afef6751f56375c252bbe9d0b43129557b` |
| `docs/adr/README.md` | 199 | `17962256ac0c95bf9dc51b3cea9a9c81aef67a76ce58dbc8377cba0109445f6b` |
| `docs/architecture.md` | 1885 | `99c0be8c43b6a015a8f220ae4585c7cebd63ac5f6e43ddef10f49f10855584fe` |
| `docs/architecture/REPOSITORY-ARCHITECTURE.md` | 10141 | `78bd36b1469c2bd31ec1876933935a26ce6c8b34d365e9c1dc1d6580968afdca` |
| `docs/architecture/analysis.md` | 399 | `8f153bb52b183a0affe7ab5883fc777ecb8f3735e8b26071dce9e4dd0d806453` |
| `docs/architecture/datasets.md` | 398 | `d724c03d0e46787ec0bb796d275ef0ad4279b94232b678e21ce0f51798f22a36` |
| `docs/architecture/evaluation.md` | 475 | `fa44aa6d35aef67fa9d5985b9d0382b727276d9956b6b98673bd1f3774100be7` |
| `docs/architecture/models.md` | 453 | `296d5e442350c732c106eaf1057b400500bc4d74ebde4efbf86e29a2937f4f6f` |
| `docs/architecture/overview.md` | 814 | `c7d9b5d172a9f389e9cf3d286054d1e45d9f4b5f49aaf9ede3101b20285abd83` |
| `docs/architecture/replay.md` | 551 | `50dfd6c42990e98167192a16e15fec66846aeda04aad92474616c9d1da01118d` |
| `docs/architecture/strategies.md` | 423 | `a287838b78e7ae99c2f3f19739a198caabe0814b0e87500d63a1a7237dc5eeac` |
| `docs/development/coding-standards.md` | 415 | `5778888a63f2462d50b41f688d1ce2b8ec862b101ed3af344877421d5b681567` |
| `docs/development/contributing.md` | 395 | `b1a05957436726dc921635f61504796a47d40a43fdd5d1b524d0d4e00f0b7f3d` |
| `docs/development/release-process.md` | 484 | `abea314a8bb3d423897dbf45ca6ab0c321d65dce4271b01bf5a7539cf34b9fb1` |
| `docs/development/testing.md` | 443 | `513294fcdf9862030b2f75ea9a8b8e1582e31c1a8ffcfca412589db4044b9bc6` |
| `docs/glossary.md` | 804 | `077fd48cd40ac06657ff663c62cbeb8a9180037c932b1bd8829ea8523963f0c7` |
| `docs/project-checkpoints/ore-v3-execution-readiness-comprehensive-completion.md` | 28868 | `58d0815759a36cc8cc38ab78548c2effdc1df2dab92cd81b89f45078fdd7a77f` |
| `docs/project-checkpoints/ore-v3-execution-readiness-phase3b-handoff.md` | 30500 | `25dffdbaf0a59872476014a83c2a84b91df9f06c2dab765c1b9780ff4d485853` |
| `docs/project-checkpoints/ore-v3-execution-readiness-phase3c-intermediate.md` | 12491 | `5800b9daf5a9625672966e24ee8f42240cea6e72685e6292285d602fa6e9cff9` |
| `docs/project-checkpoints/ore-v3-post-shared-prerequisites-comprehensive-continuation.md` | 37622 | `bf62eda11311f6e893d393f75db8bcbb8ddf2dcb19cca66d9c97edba77086eb6` |
| `docs/project-checkpoints/ore-v3-pre-maintenance-restart-comprehensive-continuation.md` | 41050 | `b0c2ff4fcca6429549792b4a8ff473c39d0a56bede1b86317cd7701c06271925` |
| `docs/project_snapshot_001.md` | 11491 | `c85bef453976f0e6ee69aa00f9268a4b52cf47e2a343ec5b0829cabb4fa9910a` |
| `docs/project_snapshot_002.md` | 4569 | `ec00aa1f127eb24baad80ee69901ce8b6ee93df6e37981569ab65f12f2386a0a` |
| `docs/project_snapshot_003.md` | 7470 | `0aae84280d20696e0f12f39060b115ae1f7cd960d6735725701f2133f7bf1167` |
| `docs/project_snapshot_004.md` | 6646 | `a7d30041c1949bf00f3d5e1f10b893affaf9c438a373d1b6a003906b944d6117` |
| `docs/project_snapshot_005.md` | 5162 | `c79c72a56b4869c3972d5c7a71e39ee29aab2526ec1aa97cbff4b08633379137` |
| `docs/research/CHECKPOINT_v0.1.md` | 5183 | `becd0e408ac3286679a7474d90cb0bef5310b3f899bdb56b57f84a792f06c68a` |
| `docs/research/DATA-COLLECTION-PLAN.md` | 1684 | `08de76017bf738047dd8626138c605c441af78c1d360c51ab4fec073902ec4d1` |
| `docs/research/EXPERIMENTS.md` | 1864 | `43305628a66ef050281c58e0905a37916897639d165e30d9c00b3c8c5e9047c6` |
| `docs/research/PROJECT_MEMORY.md` | 1164 | `5221d833675ffb84360b2c98018324bc9b95a635177cc83a41fef52da11a48f9` |
| `docs/research/PROJECT_MEMORY_PHASE2.md` | 1354 | `07d847ff883453e2b54918ea0cfed3135333a6d09c9dddcc15be358a7f1bf547` |
| `docs/research/README.md` | 3319 | `183b3841f55fa85e5e49f93f6dda3f67c842c138cdd11721e3dfdf7be58233ce` |
| `docs/research/RESEARCH_OPERATING_MODEL.md` | 2995 | `36b8c270841674c19de1fa9d2913a238ce2ba805f79177aa226225a6bdc9adf9` |
| `docs/research/RFC-003B.3-FEATURE-AUDIT.md` | 7909 | `4f3d2440efbd3f52323be3166d61f163bc014acd24eebafa49679f99dca83004` |
| `docs/research/RFC-003B.4-END-TO-END-VALIDATION.md` | 8714 | `5fb10dafcc775c5e01186134af69bb8dbf79b216253ada0064705c7ac0c881ea` |
| `docs/research/RFC-004-BASELINE-MODELING.md` | 13279 | `6f4936bff41fd9e177e989247892217ee02ea67afaee2d8d3647e262315cb174` |
| `docs/research/RFC-005-ECONOMIC-SIMULATION.md` | 20740 | `3a6f76c757b77de9916183e6839b607b416693a7385e89f73fc9cca9986d88f4` |
| `docs/research/RFC-006-PARTICIPANT-ECONOMIC-LEDGER.md` | 17881 | `7d43b007a40be85c643b12a8406e4c0a50cbfe99056c69ec12f41906a81f7fdf` |
| `docs/research/RFC-007-CLOSURE.md` | 7138 | `5ec2995ab0d9fff6c0dc21b260a3343daf33d706b4109ee4c58fc14b8e6afaaa` |
| `docs/research/RFC-007-CONTINUOUS-PAPER-COLLECTION.md` | 15337 | `1d48fc5e1e773e617894a20cc0461e2c6f1ba408a0d2c315bddcda020c642ece` |
| `docs/research/RFC-008-CANDIDATE-SELECTION.md` | 8500 | `ae6ca1aa47ebee25308e32309533996004c6fcb35e92b047767d64ebfb68d531` |
| `docs/research/RFC-008-DECISION-TABLE.md` | 1886 | `16421d2dbd6d27cf2ec5da483d1de63ebf7c2ea44e72e1d70f40627a4882734f` |
| `docs/research/RFC-008-ECONOMIC-THRESHOLD-APPROVAL-AMENDMENT.md` | 3317 | `715765a94fe08978fb8d60cd5e2f17d38838d9a6e44d679001f7a485dfaa7e11` |
| `docs/research/RFC-008-HUMAN-APPROVAL-CHECKLIST.md` | 5271 | `6d2a9a11613bf62a412661a9769f244720e08fccb7a5af2ef67c7e080c889dc1` |
| `docs/research/RFC-008-IMPLEMENTATION-PLAN.md` | 8815 | `4f3c55b038899e4b9da6a4d0c315f5d871b2d2a83b46b676919370c12d1b5b44` |
| `docs/research/RFC-008-OPERATOR-RUNBOOK.md` | 36759 | `90a2b630ebf8456ba3c7db127feb0312114a7ebaa141711f9803ca72c74ece15` |
| `docs/research/ROADMAP.md` | 1043 | `80ba4bc3b00de6fb056eaf27e7a136bdb5366462677e2630dac4505eccead491` |
| `docs/research/backlog/RESEARCH-BACKLOG.md` | 6508 | `927be537233fd0d3f3d66bb5e633117b12a3f23f07245a73c5e51da724d2c272` |
| `docs/research/backlog/rq003-instrumentation-backlog.md` | 8742 | `be484574ef6ca99cb1ea5878d40ebb276b860a7cafbce28aef87757f1a213310` |
| `docs/research/checkpoints/PHASE2_START.md` | 874 | `99574474ae2c070587525e6dde535cbfec7f988ad0207b4f9458fcd08bf338cd` |
| `docs/research/dataset-management-investigation.md` | 16569 | `54d084949a7b3f4bcea472af95cba40fc0817a4c608fc1340cdee756d1fc6b99` |
| `docs/research/datasets/square_features_v1.md` | 819 | `c285e8105e3ee5488acb90a90fc554392ebb609a5afe5eb057b2351d87620161` |
| `docs/research/deployment-semantics-investigation.md` | 16058 | `b50cb42e9c9a8d0360db816574a84b907ba48f680bf886dfa1222e09c9982ed0` |
| `docs/research/experiments/rq003-experiment-001-direct-deployment-ordering.md` | 25199 | `de65715208d624989e3a45d879a34dfa272a7bb1308b1e95c0ce7c071c576cc1` |
| `docs/research/experiments/rq003-experiment-002a-deployment-per-miner-characterization.md` | 17390 | `cc923c112c640b0e6484ab7f2677e3f3b4b745fdc30b73236f0cabaed1486f9c` |
| `docs/research/experiments/rq003-experiment-002b-deployment-per-miner-ranking.md` | 15528 | `33af6c6df445d81acc3b9f1e2b77ff7d7de6a34c266b7d06b47bc4466e87b795` |
| `docs/research/experiments/rq003-experiment-002c-miner-count-characterization.md` | 16525 | `d18d2eb8603f079f56a0aadcbde17d87855ddbb1c06f21b94d4f3d0772384d23` |
| `docs/research/experiments/rq003-experiment-002d-share-imbalance-characterization.md` | 20101 | `3fb25bbbcac39d03243418468c37a571fce282f1d4ee6bdacfe010813b29d90a` |
| `docs/research/experiments/rq003-experiment-003-miner-count-predictive-evaluation.md` | 27534 | `e6c8261b312f889b102737a66a06171c872504f44a4e5c02505ddf10141b7069` |
| `docs/research/experiments/rq003-experiment-004-deployment-per-miner-predictive-evaluation.md` | 28852 | `356f7b2c2d9e24520983e9f692675f6f6c432b7741ce1066a29b6f11b9d407b5` |
| `docs/research/experiments/rq003-experiment-005-signed-share-imbalance-predictive-evaluation.md` | 60015 | `38afa9005bb43050d23e430335e11654c374d4e2d6f4a9f541782c005bffefdc` |
| `docs/research/findings/rq003-experiment-001-analysis.md` | 10839 | `2f84b20af683f3ba40a558c60e19ee30227c70449d65e9d6e8d186db67833a63` |
| `docs/research/findings/rq003-experiment-002-analysis.md` | 8877 | `5618bd9f770ad3edbf635477a477f555c155d2c948995c2bcbae23f10d424753` |
| `docs/research/findings/rq003-experiment-002c-analysis.md` | 12573 | `538348d87a9ba792029842dcd3e559845ac359b510754fd706382e4061e85fd0` |
| `docs/research/findings/rq003-experiment-002d-analysis.md` | 11313 | `b6f0715d183e5dc93f601da3670f7515ca9741faaeb67472dbe4d151264b0447` |
| `docs/research/findings/rq003-experiment-003-analysis.md` | 12731 | `907bfadf15bd66e30edc6393c220b815d97a7c807b075bdd4fa09284f54eaed9` |
| `docs/research/findings/rq003-experiment-004-analysis.md` | 13376 | `85cffbd29347f3e3ff59401b6c65fc1968dd3a9d694c4096769fb3d8ec6958f1` |
| `docs/research/findings/rq003-participant-state-family-review.md` | 15432 | `c5156d72b169a5cfe2df589cd485154a755dbf8644c4ad30ae63d6ba26d0b60f` |
| `docs/research/findings/rq003-participant-state-synthesis.md` | 12282 | `30fe030aaef12ccc16ebd5675a0f71247a083d67e2f6230f315392e874f913fd` |
| `docs/research/governance-post-v1-investigation.md` | 14475 | `b88d5a3964d9f433ba23761990162912a8eb007d204104800399f9fb08df8731` |
| `docs/research/governance/execution-readiness-v1-clarification-decision.md` | 83358 | `ce9e7cd57df0d31db5aea0c7674edc3b3b717b96a790d5c7e3075364df151477` |
| `docs/research/governance/execution-readiness-v1.1-detached-evidence-publication.md` | 40071 | `7b91d9f63ebfe0dfc72bdc1dfe2fdb687e6f1f60877537206d649cc8d00bd077` |
| `docs/research/governance/execution-readiness-v1.1-prerequisite-authority-identities.md` | 26324 | `50c5bfbfa419ffe723665bbe9e853f98ec301e47a13f6ec55adcf03d9d01f88c` |
| `docs/research/governance/execution-readiness-v1.1-readiness-record-v2.md` | 52434 | `debe9e0f91e3f420ad673ced84890071f0123cfe8ab159d20a08973c09817cb3` |
| `docs/research/governance/execution-readiness-v1.1-readiness-test-policy-versioning.md` | 14044 | `e0d79b517b126633bb2f39448c61a84307dfd3b51628a39c8501eb7653fe20fd` |
| `docs/research/governance/execution-readiness-v1.1-zero-input-phase3b-evidence.md` | 38083 | `1c70699297837ab18f1081075626f2fa4d2d586607f2dd3a25d930ea212538ef` |
| `docs/research/governance/rq003-delta-min-governance-decision.md` | 8849 | `01c9a0d195a436e2b89585d4f819a2c22f5974be068a4c7cf39693e3acb06c32` |
| `docs/research/governance/rq003-delta-min-governance-placement-review.md` | 10548 | `91b8d83957bce189ab1bdf06f45d9a9d227b950fd31bb2cf35f498c983655318` |
| `docs/research/governance/rq003-delta-min-scientific-justification.md` | 11048 | `798c5d855ab69b954db7e140d1d3bff36255ae94c5aa6c6261164da3568bc9ff` |
| `docs/research/governance/rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md` | 179582 | `ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3` |
| `docs/research/governance/rq003-experiment-005-configuration-resource-readiness-revision-v1.md` | 61387 | `1183ccce903b96fc2c49dccc6cd59a78ff1c75c7aefe489350f49806cc7a6658` |
| `docs/research/governance/rq003-experiment-005-controller-pure-stdlib-exposure-prerequisite-v1.md` | 26492 | `2936575f0513da94c53874ef6aa2a10d823273c499a523cf791357579d38346b` |
| `docs/research/governance/rq003-experiment-005-slice3-authority-prerequisite-v1.md` | 63427 | `d3e8748c63f0a870a3b1e1439fa73ada0145c7502bccc8fd834987e8fb29a36e` |
| `docs/research/governance/rq003-experiment-005-source-processing-prerequisite-v1.md` | 46395 | `d6d5d0fb3777cdb2a95e3bbff53b4815c574de68e31d4b5f7f1a0409580799a4` |
| `docs/research/governance/rq003-experiment-2b-authorization-review.md` | 10458 | `b70e0b763a511a41b3cfa914a478c6c34aafab32ba877053f8e1fed0352af4d2` |
| `docs/research/governance/rq003-governance-consistency-review.md` | 9058 | `7d29cd1132c4e1127a930b5433689baca52bdc5a079131dab96949e36ba5d0c4` |
| `docs/research/governance/rq003-minimum-effect-scope-clarification-v1.md` | 7529 | `f736ac301a49be5acca58ef75f5130c1533328cf83cc359c9a69b596c53c2f4b` |
| `docs/research/governance/rq003-minimum-scientifically-relevant-effect.md` | 14305 | `3f297e0a2c9e18290402b41c171a8d31a5595fe021931433f8de3205e9a885d3` |
| `docs/research/governance/rq003-stage3c-acquisition-lifetime-clarification-candidate.md` | 30330 | `1e2c235f11689cd64c65840b3055f377ebef8d9614ea31574e398a15bf29fdcd` |
| `docs/research/governance/rq003-stage3c-admission-serialization-clarification-candidate.md` | 18602 | `56b4e402a9b4e62853e285be3ed7ca7b7c2d1a0d34d71a7c9ee757b8dffdcfed` |
| `docs/research/governance/rq003-stage3c-category-attribution-clarification-candidate.md` | 19936 | `2e735f2ffe1b4d537495dd7db62d75e21bb6db822c20863f5dc29781c508c101` |
| `docs/research/governance/rq003-stage3c-controller-retirement-status-clarification-candidate.md` | 18484 | `d9bf01b2449b1819545ef4c186407eb0c16c929534d6ff4bc2f37b8a4b33a304` |
| `docs/research/governance/rq003-stage3c-recovery-permission-clarification-candidate.md` | 47955 | `7df413610a54adcacb06f5c01dc43b7ce2c04c5244922519871d745c0395f716` |
| `docs/research/governance/rq003-stage3c-worker-pinned-input-acquisition-lifetime-clarification-candidate.md` | 24156 | `be25dd7422e10c6dc775bb3fabbfc0688c71606fdaf8196305f1282208628a9c` |
| `docs/research/investigations/protocol-revision-strategy.md` | 27581 | `f132677105e6662bcd85a9b8e37710a7b047e05b97c7422cbcddc164104243ec` |
| `docs/research/investigations/rb001-dataset-build-performance.md` | 19620 | `eb64fa2ae735f48fa2eb728d8d7c8afcc24b56559508bbbe011f28749d562b3b` |
| `docs/research/investigations/rb001a-freeze-verification-investigation.md` | 18838 | `7e107d74224103f6df75513dcb9bcb58beef15d290d6be5910d878bb635ca90f` |
| `docs/research/investigations/rb001b-proof-carrying-snapshot-artifact.md` | 29497 | `d12cbc2be2ff84eadbe9df70b2c791af13d6eec078875a2a7f42334a82377fb7` |
| `docs/research/investigations/rfc013-candidacy-assessment.md` | 20790 | `60f19c7ce5d40c885d41b2a65c0e427d0b67ed093fbcfc0b110324a4ef17db04` |
| `docs/research/investigations/rq003-candidacy-assessment.md` | 14978 | `780d83d95f7611daa21d2d4be0ad9f0f8a60b6a7540038a327584da3dc655ff1` |
| `docs/research/investigations/rq003-decision-quality-theory-design.md` | 15425 | `d57fc95520e9e9921c11dd00a85047f4459f6f10a3db3ddacc488d883b852e57` |
| `docs/research/investigations/rq003-decision-quality-theory.md` | 12874 | `7cf40c53592a464e19c59668d3112ead4f0b83b8864774731b6281fab0c66879` |
| `docs/research/investigations/rq003-deployment-share-order-equivalence.md` | 10336 | `778bbe7c59d7b914b94ea4a51b431d25d8bf6a8125189539ad919c8f20a9ce24` |
| `docs/research/investigations/rq003-feature-set-1-design.md` | 13601 | `764fbf2a17c0da767b2ed0d22cf69c5df91f9ddcc466bf1f30aca5f00a8e1dda` |
| `docs/research/investigations/rq003-measurement-catalog.md` | 21850 | `b6a546a6f9b5c647900298617151271b66f283dca39f14639d3b595edb84a14b` |
| `docs/research/investigations/rq003-measurement-implementation-alignment.md` | 17960 | `f4a0e70971afb2f7e2e97f74cec99c10d127568124c90011da1c5da18a1b067e` |
| `docs/research/investigations/rq003-participant-state-consistency-review.md` | 15555 | `e8f3f2023b932e8cb1c3e8b315d33219bd820e3c9302976266ab580fdb9fafef` |
| `docs/research/investigations/rq003-phase3-design-review.md` | 19608 | `a16bdcc0a450d3d4872f05a324a5b0bda484a8f8ffc68f1ab1fc2b4ac6dc8a35` |
| `docs/research/investigations/rq003-phase3a-immutable-context.md` | 22025 | `8a742ba03fedba130d88248459fae3546c20cd58118028dbe8de92f64cde4bfa` |
| `docs/research/investigations/rq003-phase4-pipeline-review.md` | 16995 | `61e1d807e5990a99a11908baba90d6c805f84550938c968dfc6774654d8cf3d8` |
| `docs/research/investigations/rq003-predictive-evaluation-roadmap.md` | 15222 | `cc104c3228f64c40ccd4fc5fa29c97915b84e389bb99b1f00d5e96f257bb568c` |
| `docs/research/investigations/rq003-protocol-state-discovery.md` | 16882 | `b1b6e16a81966f0e565ab7e3497826e2c52e165373b7466fc7bccaa6083650ef` |
| `docs/research/investigations/rq003-signal-discovery-roadmap.md` | 26891 | `58de36207b6d56996b016bc9bd1799686d2e4c2de45ea12398733e12c797e602` |
| `docs/research/journal/2026.md` | 900 | `4285fb5db127544fb5a66e94dd8e4f7b1b461b5046438ae739b356107df0e938` |
| `docs/research/notebook/discovery-session-001.md` | 19630 | `017042a335ce80e798bb1581572201a3bdd4971531b1a025b0321f379913e3ca` |
| `docs/research/notebook/discovery-session-002.md` | 18012 | `82b0ed36dea9d523b41654822ba81515787a54f2d8b5889098b524841641d608` |
| `docs/research/notebook/discovery-session-003.md` | 19519 | `ec446ecaea1f5c1d0b8437a12233fc62187c28a3b0259638f23a463285d8c4fb` |
| `docs/research/notebook/discovery-session-004.md` | 22842 | `1feecb6a904db6e6a7a2fbfb7a192c436e861a473b6d2c2bda754817b33cfc2a` |
| `docs/research/notebook/experiment-000-characterization.md` | 18592 | `053432f3a027c2cd66efdced911a532c43b65564df1ee4c05fc508d810dd329e` |
| `docs/research/observer-persistence-validation-v1.0.1.md` | 11009 | `89d7da2f2fe919cc78b2ee8eb2da0863adcc67ecfa8f6e405687eb26413755dc` |
| `docs/research/observer-transition-analysis.md` | 9968 | `ec044a9b9a6a039b0882452656e5a663fc31cf186e1fede6f782b1322e7bca6f` |
| `docs/research/ore-resource-semantics.md` | 24854 | `b581c65627c64728217bbeebe1889df2fda8c5ca23fdc051a5a4a80195a26c57` |
| `docs/research/ore-v4-compatibility-assessment.md` | 25202 | `84ebab189305da0138040196088b2752c94a0372c36a97fe218eb4d12e76cde0` |
| `docs/research/outcome-provenance-investigation.md` | 22228 | `78595cf04be79e704c3ba8a2d231f6b039eb942010950a87da61ac317cf04f6c` |
| `docs/research/post-v1-observer-validation.md` | 9825 | `32dd20cc2dd24e78cd31b8c774b81fe27e0ae8658b7199cc48f19efb277933bf` |
| `docs/research/promotion-domain-rfc012.md` | 11093 | `6affa44af19f6cec979ffed4ae2dda6d4af07269bdabe9dc5f8aa86cd5fc70ca` |
| `docs/research/questions/RQ-003-feature-audit.md` | 40996 | `73e7976cf5b24d7ece23490a4b6eefc3d13acf1e8d45382e824e944617adfe21` |
| `docs/research/questions/RQ-003-feature-eligibility-resolution.md` | 24745 | `ea756c6ca5a3dc24d8c14dc0a764085894bc206af824f8c32c02a1461ac0602e` |
| `docs/research/questions/RQ-003-phase3-feature-framework.md` | 33486 | `85059b2d3ffbb680f861cf6c5f542d6f97a40f0576976798baa24569358df6b5` |
| `docs/research/questions/RQ-003-winning-square-predictability.md` | 28870 | `28cbc412bb0b4211e7a7b59b4f1697127dde429f0cff3447d1e18035ff549b58` |
| `docs/research/research-question-002-post-transition-finalization.md` | 15610 | `c38019369e1b3032bac52751b1e3f46111b26a620d00002299ea75194c3f1aa7` |
| `docs/research/rfc/RFC-001-square-feature-eda.md` | 3093 | `cc56ab5f815723a0ff324605735aebca2bbcc51c8928f3798551603393466bd7` |
| `docs/research/rfc/RFC-002-CONDITIONAL-ANALYSIS.md` | 1187 | `de049533b4dc1f9f197568229ae3c58ef3e6cf767530e56a3653e1e1d5a76858` |
| `docs/research/rfc/RFC-002B-STABILITY-ATTRIBUTION.md` | 763 | `f1d8579201e71cb439bdddd49fe379beae528dc9e888b705a5dbda2265c249ab` |
| `docs/research/rfc008/approval_manifest_v1.json` | 2448 | `9fe94099ed3d9e15e015eef72db5543f16c756b1c3c5463f014e18467a44d789` |
| `docs/research/rfc008/economic_threshold_v1.json` | 2309 | `4ca4814d70e3c5c6984950437bd29ae6cce324b72331f358e75004a29cee7595` |
| `docs/research/rfc008/preholdout_evidence_v1.json` | 7121 | `5ad61b1dc81241382f99bc93fd8c4ca6205203e6d5b07dec1082db82bb0b721a` |
| `docs/research/rfc008/release_implementation_approval_v1.json` | 3729 | `ca8caa96c75f0fa29431bdc8bec0ce5e7abe1f097fcdaa78111f255913c844a8` |
| `docs/research/rfc008/rfc008_candidate_v1.json` | 2609 | `406217a08268e369570fc1203f0188bdb89363c0cfaae7e168b0b2e43d930e2b` |
| `docs/research/rfc008/schema2_approval_field_authority_v1.json` | 56533 | `4b78d1e880b6559e7da86edd3517e88c767ea08737fd4bc85585ed533b0aa314` |
| `docs/research/rfc009/rfc008_continuation_approval_epoch_3.json` | 1488 | `26c6a5e4af362feae951989004c4c67aafed83074e77f45bcbdf6fbf3e91ba63` |
| `docs/research/rfc009/rfc008_continuation_approval_epoch_4.json` | 1488 | `2d42919c55ef6cf2b8446042161f814a8d42ff83b10f2757a56dd378d14766e3` |
| `docs/research/rfc009/rfc008_continuation_approval_epoch_4_revision_2.json` | 1714 | `08570d92f75ae84ff354d452d0bcf6b05e663b09610bda982a37139c5c50397b` |
| `docs/research/rfc009/rfc008_continuation_approval_v1.json` | 1101 | `709b9ef4b1f9fea181e98182ba46a083acb799da4279e716140b959397bb5281` |
| `docs/research/rfc010/RFC-010-IMPLEMENTATION-PLAN.md` | 16541 | `39ff055535d157992de890944eb627db71bd455ad38f1de912edcaa6ca68ddae` |
| `docs/research/rfc011/RFC-011-IMPLEMENTATION-PLAN.md` | 19456 | `5d61e43394f7c4228f303c6b4a07815eb4addff05dfca08eff0cdb3e1125146a` |
| `docs/research/rfc012-readiness-review.md` | 23219 | `0ea0347f63a1398abb96b652f63ff55bfecd9c6d980407230b9d2d93bbf26fc7` |
| `docs/research/rfc012/RFC-012-IMPLEMENTATION-PLAN.md` | 36806 | `dd60e5fab0f24512d677ffa7771333547ae0d6e3f887b6fbd457475f2afe5876` |
| `docs/research/rfc012/phase3-walkthrough.md` | 19919 | `b53000e20f94a69efbc8c5fc4fb1ed6c99704c8e26d640ebc14d384baf833732` |
| `docs/research/rfc012/phase5-walkthrough.md` | 30979 | `b9af75c0e31fa1265c77a25f1f1d624c69d91c466058cf0360091dab3b585ce8` |
| `docs/research/rfc012/rfc012-implementation-plan-readiness-review.md` | 23788 | `2490b334673590367ff396204c4e44a308b131fa3fc3e4d4feea0191f3043e15` |
| `docs/research/rfc012/rfc012-validation-analysis.md` | 13351 | `10b9898d012bdb47a685541756342118599e6dd8cb783f01182e2754bf7f9b57` |
| `docs/research/specifications/experiment-execution-readiness-v1.1.md` | 102274 | `e938499cc254ce2d65fce925fb6e33c5d8b9dcea73a91a2c01e1017e8fb17da9` |
| `docs/research/specifications/experiment-execution-readiness-v1.md` | 59209 | `6aea25aac1b701619bde4db309fdeb341a4fc3fd790e6ee9fcfa4414e9a9db6b` |
| `docs/research/specifications/rq003-research-execution-profiles-proposal.md` | 15457 | `18f4e0a7ed4dc747a041cead8d9403695a7d284d71a6d6bb58e186d5ea3466e3` |
| `docs/research/specifications/rq003-research-execution-specification-v2.md` | 6180 | `75597ab27d2d2867c68be886785c1884db83b9a26c0428c337ff23d218ef9497` |
| `docs/research/specifications/rq003-research-execution-specification.md` | 18373 | `3f7da6977f3a4f7c31766c856fc9cc000ed6a6a0d4dffcbf6e5cd0193d948eb2` |
| `docs/rfcs/RFC-003B-HANDOFF.md` | 4116 | `341b87c33f47d812affc40f4c1555108f499aa3d1dc088711fe67a51c0fbbf05` |
| `docs/rfcs/RFC-008-PREREGISTERED-ROUND-LEVEL-STRATEGY-EVALUATION.md` | 21215 | `0dd4f76d183307fd1f03cf03ae26908072eb05156d915fd4cdb68bb58ad56142` |
| `docs/rfcs/RFC-009-CONTINUATION-AUTHORITY.md` | 7157 | `eda462f002e62e69d6915ad74e6457448fcd85b3add086e0b140cd741054256c` |
| `docs/rfcs/RFC-010-STRATEGY-LAB.md` | 13091 | `31a8e2924d53724d8202637e3ee778f125d810ceb6a173a494109c8fe0f8c372` |
| `docs/rfcs/RFC-011-ORE-DEPLOYMENT-ECONOMICS.md` | 30826 | `b04cc652c29866a5ff9b42aa21167f0937fa71c5bdab4dd1a9047b5f5b88f773` |
| `docs/rfcs/RFC-012-OBSERVER-FINALIZATION-CAPTURE.md` | 36601 | `782b76c4c59a764ec2a41c24022267e80317ac8ee7f39d0f41043d3b434b6075` |
| `logs/.gitkeep` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `pyproject.toml` | 396 | `22ab75bc3ab42bc1f172ea985236205694081b18258acb20311cd0a0933780b4` |
| `reports/research/conditional_analysis_v1.md` | 8306 | `6bf418787b6d0a9960b7933e1b861c86567b682765ac880c44ecd0cb08a6e924` |
| `reports/research/rfc001_v2/square_statistics_v1.md` | 4424 | `ff5f719d7efaf0263a45b59bce37b5295dbb37986d540db885bc1667c610760d` |
| `reports/research/rfc001_v2_new_only/square_statistics_v1.md` | 4430 | `132558b6766bc49b2835cbe08f9650874393f65a4cbb1adf86cc1287a9ae13ea` |
| `reports/research/rfc002_v2/conditional_analysis_v1.md` | 8342 | `4827f91752428e3b104452828d4cc5ff665effa4275f51eefc0461883ed58fb6` |
| `reports/research/rfc002_v2_new_only/conditional_analysis_v1.md` | 8347 | `1c8975ff3924c85340fee1b0e1c4ad62b2cc18ae036d1c932b5a279221705f7f` |
| `reports/research/rfc002b_v2/stability_analysis_v1.md` | 8849 | `ab07bf3adb50e30296a7c21e50a152669f9fac59d765e7f854622df7ec39c066` |
| `reports/research/rfc002b_v2_new_only/stability_analysis_v1.md` | 8857 | `b2a16470d0f6c467a33dc50ec52bb2e2cd99cab800281d1ada87f4dcdfb8601d` |
| `reports/research/square_statistics_v1.md` | 4416 | `ceeb444d72b2d2bae096818a07ca97dbe6c83ecaa43e6f30f02d1c8ea156df66` |
| `reports/research/stability_analysis_v1.md` | 8783 | `5be3b8497355a37998e188ae38603e7c67c35acd009d4b7b2a5b7bc22b5648ed` |
| `requirements/pylock.readiness-v1.toml` | 10189 | `11afcc39df18db5b1d90fb7355decb0d4c96a02ee602f3cdce9b23b0d6682258` |
| `results/README.md` | 386 | `c97b61039deb1d673bde6994f0ab3cdb62cc91665d98aeb45696ed610f130ecd` |
| `results/research/conditional_congestion_buckets_v1.csv` | 977 | `49ce76d560bcab1953d2dc01d66ba803de401968e670d5baba26cd42530b1a34` |
| `results/research/conditional_geometry_congestion_v1.csv` | 3132 | `58289b6f7a77f052216fa5af44f66216ca74c614044d066c858ca2d51a03d889` |
| `results/research/conditional_geometry_rank_v1.csv` | 2475 | `cb5e1dca9c74fd2c79b3871c2b60ce97c5b0e55ab013e40d84e75611aa934619` |
| `results/research/conditional_neighbor_congestion_v1.csv` | 930 | `af232d58f47bad9b2a8db82af73639216cda3a1a28b573d5b465cbc1e9fad7ce` |
| `results/research/conditional_rank_buckets_v1.csv` | 1002 | `2de3432aa19c9b4fbcb451282a3477f3305f2780208568307c1cc5ce15dd3571` |
| `results/research/feature_correlations_v1.csv` | 1267 | `6bcf38fe65166183a61c83d13ab6be7787aa83a6235cf787aa4ab643adfcc4fb` |
| `results/research/geometry_statistics_v1.csv` | 1150 | `e9701d2132f6ecbb8e8072701c440d906fd9fbafd53018f2d9ae5c5920adf9d3` |
| `results/research/missingness_v1.csv` | 1249 | `d81d096cb5a2d67cd7a021e18d92d241becacd0c0d01f31c04c0dcf7e99e75da` |
| `results/research/rfc001_v2/feature_correlations_v1.csv` | 1287 | `797a8d553fa4a967df6301f8db1aecfcdad91cc3a8a3162bbfddcfe49fc8b2e6` |
| `results/research/rfc001_v2/geometry_statistics_v1.csv` | 1156 | `d7fe534696e340ca8621127965af4894226947ff924073e97c5df69e7981b459` |
| `results/research/rfc001_v2/missingness_v1.csv` | 1249 | `6a7cb025947235e6da6635dc179cc626b812f3f83e6a58f3c8fa360348b5433e` |
| `results/research/rfc001_v2/square_heatmap_v1.csv` | 2297 | `7dc02fb23b5614439f61dbef53fe77bc988483adcf2598a7d2a1e39b24f38fa4` |
| `results/research/rfc001_v2/square_statistics_v1.csv` | 6232 | `1574c41522d298923c1ce20738878f0f76baf6662df1613c2a2bd2b276498681` |
| `results/research/rfc001_v2_new_only/feature_correlations_v1.csv` | 1281 | `e51a0196b080a5e1f63f67d8087cd81524bc5bd97451610dbff7dd02e0199a84` |
| `results/research/rfc001_v2_new_only/geometry_statistics_v1.csv` | 1155 | `020a656b94be0ccc663d390481fac0e30cb92238bf2ddd6f995bf307d172c5ba` |
| `results/research/rfc001_v2_new_only/missingness_v1.csv` | 1249 | `e56e900d4f8501a7fd2e55fcea624e56fef6b3313e4d60265598e3348fe25a4e` |
| `results/research/rfc001_v2_new_only/square_heatmap_v1.csv` | 2305 | `13db3e92f1f435ee840e33a4b70446ac8c01af189b2c66f6b0ec8ceffd03d600` |
| `results/research/rfc001_v2_new_only/square_statistics_v1.csv` | 6270 | `aa767b7166a62109d845c553c107a55bc274fa6b360a1e6f36ac982f50f7a324` |
| `results/research/rfc002_v2/conditional_congestion_buckets_v1.csv` | 981 | `465e0fb31a3633d3d2406b5ba47938636f0537db25bc7ba63cfd9ed1545a5487` |
| `results/research/rfc002_v2/conditional_geometry_congestion_v1.csv` | 3150 | `bb5fa45367a4e0272528e5efde8a4d0e51084a1fca7215250336dcc58a1d4c76` |
| `results/research/rfc002_v2/conditional_geometry_rank_v1.csv` | 2587 | `71138e5905e920fdc938b4043fe307319c2cd49ccd0e59cf588b88207091c0dc` |
| `results/research/rfc002_v2/conditional_neighbor_congestion_v1.csv` | 937 | `998246e4bc300c694dfc38c69c7321bdac74fff06d47f836167ee737965dd1e3` |
| `results/research/rfc002_v2/conditional_rank_buckets_v1.csv` | 1005 | `0357371ed9f32434d555697747049fac2d3f70ec8ec413c74abd69d903c738a5` |
| `results/research/rfc002_v2_new_only/conditional_congestion_buckets_v1.csv` | 979 | `416a4b26ee4da03a956c2861ca91a6ac03c209248e51b3a8cfa1ffce933cb70f` |
| `results/research/rfc002_v2_new_only/conditional_geometry_congestion_v1.csv` | 3096 | `7a41be0ea70a1a46feab7a26142700102d62836d63fec8e441cd4e3dbec27811` |
| `results/research/rfc002_v2_new_only/conditional_geometry_rank_v1.csv` | 2606 | `4639075c5fdd5e2adf3d7ee04c6827865ad9066068cb3bc31d0b92eb0a8e23cb` |
| `results/research/rfc002_v2_new_only/conditional_neighbor_congestion_v1.csv` | 938 | `ef5453028993e07e7a537ffbb0a1e872649ce9ab1c0ea78e2d4872a0b4c58653` |
| `results/research/rfc002_v2_new_only/conditional_rank_buckets_v1.csv` | 1004 | `92bf00d928fc22029e3270250934b78b9261abf535ee61887b5a0eb7f76998f0` |
| `results/research/rfc002b_v2/stability_corner_squares_v1.csv` | 1236 | `003984319239e43f96b42d84d02784ca2cae3a5d47da46f244f48c86ce3ae64d` |
| `results/research/rfc002b_v2/stability_exclusion_summary_v1.csv` | 2068 | `9bd4bc38d07ac550723bda7c5fb51695da4c9db40269463ec7925c7dad61cb62` |
| `results/research/rfc002b_v2/stability_split_summary_v1.csv` | 1045 | `29eb1165269cea88f14f80f69afef57ddfad958233900744a383882cbf2b4a88` |
| `results/research/rfc002b_v2/stability_time_deciles_v1.csv` | 3491 | `2f26a25697ebe92c6891769b83c90d09e256c83f1918465233e43cebead2992c` |
| `results/research/rfc002b_v2_new_only/stability_corner_squares_v1.csv` | 1248 | `d285f831bf796af23cd5de9b72805fe9f23163448f1b1b649cb33e5fa39dcf1a` |
| `results/research/rfc002b_v2_new_only/stability_exclusion_summary_v1.csv` | 2070 | `52f9761ed6f1cb913e1574a04d027e658e4f44463a8f5d85191f3c00df66c639` |
| `results/research/rfc002b_v2_new_only/stability_split_summary_v1.csv` | 1045 | `773afcd198d5eafa084d961364d26567f56ee83830c6fce2720f7a79127b89a7` |
| `results/research/rfc002b_v2_new_only/stability_time_deciles_v1.csv` | 3488 | `d9b15ec4ab248b720645b063e6af4dd030726a0c27816d393bc9affe21616411` |
| `results/research/square_heatmap_v1.csv` | 2309 | `ef3055b0c3691ab707da846ba388330699e19e44a119e7b6746962a20f16b79b` |
| `results/research/square_statistics_v1.csv` | 5949 | `52b620e18bdb722014e93152369f69358725dc1168558cf281f0741332ceb4ba` |
| `results/research/stability_corner_squares_v1.csv` | 1238 | `cd98ee73b56c97f4032423187110471412a34c0d0538fb9c20969431975ed278` |
| `results/research/stability_exclusion_summary_v1.csv` | 2044 | `c12a9b7dda159dd196dfae92ed0cbddd90f7e5bd0838fc11aeb857d9206eb756` |
| `results/research/stability_split_summary_v1.csv` | 1037 | `0f896a9b3fecc373000e2118f6875f24f8020cae29c1760cf60a43ca944bd28c` |
| `results/research/stability_time_deciles_v1.csv` | 3448 | `db80de9074aee90f6ad9c5ae72dd2e5052217732e362820a89a54ea207a47dc1` |
| `results/timing_sweep_results.csv` | 775 | `07e8a15c8bd0ac973d06696f59c6f13b1fb4ca7c3a00067fc6bfdaf6d71da8fd` |
| `rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md` | 56008 | `43d0cb62d68c2bd04fcf093605eafcf52b28fec7d355a4a4bbbe878a518d51d6` |
| `src/orev3.egg-info/PKG-INFO` | 236 | `6c79716e945c210ce9f6b682bb4f0f16565bfe60bee7df322b317b8d6511460b` |
| `src/orev3.egg-info/SOURCES.txt` | 1961 | `aaf8b82f156e4abf14741171e1a56efaeaca77416a08c6c597019e6d4713f6bd` |
| `src/orev3.egg-info/dependency_links.txt` | 1 | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| `src/orev3.egg-info/requires.txt` | 52 | `a5cefd7fcb4f941da7e9219e6d2a476a61dca3fd7a9c7d197b74d4bb47dc2690` |
| `src/orev3.egg-info/top_level.txt` | 6 | `03ddfdb2ce05fea215fe5b84242eccc269e86fe28006a3a856a2ce4d0dd8df0b` |
| `src/orev3/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/analysis/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/analysis/analyze_temporal_behavior.py` | 11793 | `30137a74bb31d47486ddba7f7a68764d7cd6e24324356a12634bcbeb6847a8cd` |
| `src/orev3/analysis/analyze_winner_metric_dynamics.py` | 17952 | `0153c20204c7060cb50a72c59ac66379079c2230f6d33fff4f8eb1f76218b280` |
| `src/orev3/analysis/audit_feature_dataset.py` | 25506 | `cd8a8b1f8347ceaad54bb4bb09c3c95bfea5d4b1c6c6f102b29ce42ab5914fc7` |
| `src/orev3/analysis/feature_quality.py` | 22018 | `59c46cf61ac36c04c9eb4ed5b107d586ec17239774304e7f00f89d22dc779d27` |
| `src/orev3/analysis/inspect_observation_dataset.py` | 13716 | `814e525a33865b07f353ca203f3c94caf30b77a1831228cc8cc43165e024dd24` |
| `src/orev3/analysis/validate_feature_reproducibility.py` | 13463 | `9d7b91988a14693e02e510ba84e54732a3dc73ed01e6c15113afc997937c455c` |
| `src/orev3/analytics/__init__.py` | 202 | `071efe9221294772b298231e79cbea6e63642a3e62e84f9e2a7805635a9a0951` |
| `src/orev3/analytics/common.py` | 5380 | `71a54cc2a7d7396c565b88745fcf5a6ebfc97c35c663279051d8a24292f96ea5` |
| `src/orev3/analytics/conditional_analysis.py` | 12823 | `cd5085bff829c8358ae1557a074919ab905809715e08b3f702c3cc9bd8c58d28` |
| `src/orev3/analytics/report.py` | 6016 | `96e324c528ec87f704833d37dd782e38702eb1a09ef6e46b53fb7062b3da3423` |
| `src/orev3/analytics/square_statistics.py` | 3085 | `ff2778220f9fffa24edc5b171bb9c3897c6a779f08e239622d5d40a4a5922a92` |
| `src/orev3/analytics/stability_analysis.py` | 13135 | `f4c298ffb860dce03b609e07a1c183e6de84e942739a7c1d7ad2e669c5bb2948` |
| `src/orev3/analytics/statistics.py` | 7089 | `c9569574b4cd67eff9c0b7c95730b0de6ec342a1cca00bd7f2fd682b8441ee88` |
| `src/orev3/collection/__init__.py` | 109 | `c0ab683aec92c9a9f0cc6fd845bbb07939544484c2aba1734d423e2687bf54cd` |
| `src/orev3/collection/cli.py` | 19540 | `34361d330a9d3e625dbb04cffa02d5d82de2f1e9d8377ae79f6dc0a8cd3d8aba` |
| `src/orev3/collection/collector.py` | 24729 | `7c3bdbcae9c31b0322d3ba28d1fefef4fb38a1244be9245ea5d343c4a58f6c6a` |
| `src/orev3/collection/config.py` | 3351 | `eadb20de7314a97e0a2208cbea2918b8bdf77cd7a26bd8b23e73eb1382caa6af` |
| `src/orev3/collection/cursor_store.py` | 16177 | `894affebc33911871cea1a5cc05b5a6b60bb5d5b458bbc83eee31abd7ed11e3c` |
| `src/orev3/collection/gate_b.py` | 19421 | `16cabfc6399f343fad4adf09fe64d1eedbf7ef886a0d1b9882454de5a3ecf44a` |
| `src/orev3/collection/gate_b_analysis_dataset.py` | 34665 | `bc4b070246aba06620fd6cc3d3c5f132886fcdee6447318565d5e011ccbc9a13` |
| `src/orev3/collection/health.py` | 4768 | `c2998586be79e3fbaf500a86cc5314710f135a551a097dbaf8da839e90a8a4dd` |
| `src/orev3/collection/metrics.py` | 4872 | `d612fbd260a3b0946c963d71fdc9912de5e0ae285e697a59f219e88dfb8ff7cb` |
| `src/orev3/collection/opportunity_builder.py` | 2743 | `b084ded86b15930c1a3f6f6bd2b70e0369523eff772dfed664060481e4afb81b` |
| `src/orev3/collection/outcome_linker.py` | 5415 | `aecfeef2b819e24575c4840e5d340014f246bc2e9ca082f141527e6f4bf5493c` |
| `src/orev3/collection/outcome_recovery.py` | 43418 | `cd808c0ab56d4b47ab4e138f4331c3741de0a43827ee7fbdb0457790bf690709` |
| `src/orev3/collection/paper_accounting.py` | 2578 | `05bf1d6a4ee26b52d0d33c6fae523a0542430905de3d43f447f54359ac414bbd` |
| `src/orev3/collection/paper_strategy.py` | 3699 | `2405b7f4ef08ef352c0e361bd3868f2555a3e901d19bbf390f5c0cb24be2aaa3` |
| `src/orev3/collection/reporting.py` | 5748 | `2d4b4381afd1870959c30f7179d57e2ac6081bd790b76d9bac7678c66f2b2823` |
| `src/orev3/collection/restart_proof.py` | 4410 | `33d4e7f62cbb685e5d5f36c6627d378cedf4214ea8d296b88dce55a070c6b709` |
| `src/orev3/collection/schemas.py` | 9330 | `63a133ddf80cd0b8bcffe62431ba4dcb4a96674f948d28c5a04337f3497a9de4` |
| `src/orev3/collection/tailer.py` | 4797 | `a162e2e08169c3cc1f4d8fbee0632bb52a20d68bba4cb62977d5647637b9ff47` |
| `src/orev3/collection/writer_lock.py` | 1182 | `f2f7083a95539f3792fde58c2db55c49cc55020b85e2e1a0b440bc2f52ebdaf0` |
| `src/orev3/data/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/data/models.py` | 1585 | `c6893466b5b040067acf5d9dc11f2526f9a17ba6c5dd5b634ff80e3c672428f2` |
| `src/orev3/data/writer.py` | 9636 | `aa79cc11350fff261585b5c4f9cd24ab48414653d5519efdc7facf18bfeee133` |
| `src/orev3/dataset/__init__.py` | 2000 | `40e03d2415f49773cdb6a6a90ba617a65bb572408e294cdf98ec0e081503838c` |
| `src/orev3/dataset/build.py` | 2975 | `a804724c6bce9a77c1e63c9f46b64cf936dbe404c36b6bdf4709e766dbe9acb6` |
| `src/orev3/dataset/management.py` | 11237 | `1c58920b926b98a33f22e10e7aa105e4a413697af0ccd9d7ed3265d77a3d6e18` |
| `src/orev3/dataset/metadata.py` | 6582 | `34a821e74e081356aebe6f6fa7b11de7f2a8cd5eae7521d8957ebf94140d13b7` |
| `src/orev3/dataset/rfc012_outcomes.py` | 18963 | `fd827f63862865962f1b1328bdb44afef380bf7823e8db603a088a6e2c7f011b` |
| `src/orev3/dataset/rfc012_reporting.py` | 37953 | `f2b55e87d5ca9f1bc2bdc2982968bd11028056b3b1f12cd96f5605743a5fe1a8` |
| `src/orev3/dataset/stats.py` | 2290 | `f947c19a45e2a62123c5e6b49e81f186f7a623c92090693d8d63cd38b3047c8d` |
| `src/orev3/dataset/validate.py` | 1776 | `d488591c86e7cad8b79e828d41aebf861a63e11ba4ef7df1f6aaadde830ebf35` |
| `src/orev3/dataset/validation.py` | 15223 | `8c55dee15fa0997f239697901fca05b75e166768f390b7b8716f1c02a7ce059e` |
| `src/orev3/datasets/__init__.py` | 253 | `5834449baa55ff16899628b0f451233c5c4cd24b914fe5764975196fc5611b97` |
| `src/orev3/datasets/build_feature_dataset.py` | 2920 | `635c27c0f92efafd2e794aebeaf9225f6d2b9906c047e0ff849d2638ab8ceec6` |
| `src/orev3/datasets/build_observation_dataset.py` | 3719 | `90a980b72981bfcbb15a8b877dbf352e568eb7c55c6feda4591ea64e7d93d991` |
| `src/orev3/datasets/build_square_feature_dataset.py` | 13700 | `7c7412256b96fba1e5d23e9caa431ea03d23642c295d57190a6cfaf0407a1c17` |
| `src/orev3/datasets/observation_dataset.py` | 11202 | `21e340620a112e1c26255631269a3eb9d98e757a54926dfc91d65c8e78a9f428` |
| `src/orev3/datasets/rfc012_evidence.py` | 49903 | `f1aecc060a8824858f460be7e82c1561548e8103b9b4a6aa750bd65c406eee17` |
| `src/orev3/datasets/rfc012_transition.py` | 31171 | `941abb9f678aacd61d5483e5fedb22bb03a3a897aa7bab96a573e073c2c5559f` |
| `src/orev3/datasets/rq003_experiment0.py` | 20568 | `009a3d5654d71781e3d7d7239edc8a30267be1b4ee2986a3cd460e7e09aa9ff2` |
| `src/orev3/datasets/square_features.py` | 15275 | `9015657b846b4d8de23cb58eea594fb9e9ab3eb19565e73537db0c13c51d6787` |
| `src/orev3/decision/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/economics/__init__.py` | 57 | `9fa141114b2a8dd4e673b949746b5b9d41a0a7e6bcb0fb50085d430fe4210c3b` |
| `src/orev3/economics/aggregation.py` | 4844 | `20fe4b2f8ded50da61f5393ffe22e66ef9754f69dc140e60584b044086256a42` |
| `src/orev3/economics/bootstrap.py` | 1741 | `f2534a36a936241596e5436c300f52d5c065416cd8f06fcefe357c49d4214098` |
| `src/orev3/economics/cli.py` | 21108 | `c5ca299c371ba4562a34fb8cc54bebd8493d9cd7fca74c95b6fbeb7ab8c5b41d` |
| `src/orev3/economics/reporting.py` | 2071 | `f09974a9100186d0be701d07d03fef2c8761b94ec54ff4952c3086828e178ced` |
| `src/orev3/economics/reward_accounting.py` | 2071 | `ddf5c1120d93901d3ebb502953f46134082f8bb7adf2c7881a2899cbab3455c4` |
| `src/orev3/economics/schemas.py` | 5610 | `a3549a62bb4bc3161d8379e6d764c3c4816f8fe366ba17f7fdd1d5a74862a38a` |
| `src/orev3/economics/simulator.py` | 11681 | `b46c113d6e91fd91ac2a4f5871dea2e2b264d9922d0b4fde257f5fe7eaee32fe` |
| `src/orev3/economics/sizing.py` | 1035 | `ff7bb54d3642749c63be51c7afa1db891e6200c46a3de582bc577a96355a3e50` |
| `src/orev3/economics/strategy_selection.py` | 2228 | `d8301ed424cffc1a0600137aecb5d47f46bd30fc30a10ca5b94da27c29b23ab5` |
| `src/orev3/economics/validation.py` | 4491 | `e93cf5b586a44e0b614fa7f1b9ec69017ee2b2dab2fa5799823e15422ec4fdf3` |
| `src/orev3/execution/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/execution/attempts.py` | 17266 | `600f03b6197235eb59d3368253be8065bb9dc484740d33051a5279604a7f718c` |
| `src/orev3/execution/bounded_streaming_worker_bootstrap.py` | 43167 | `8e86f67a7f8f1ec6f408c838875581bfd3323a94727343af503bdec1a58c46bf` |
| `src/orev3/execution/canonical.py` | 34909 | `60eb3e9c2af6a433dc4146ad729219c3688a7d48eb5a382e910c9aaaaa3181ae` |
| `src/orev3/execution/contract_validation.py` | 17028 | `b5ea6df28a50b3ad5c2bc4469ad2a549614425cc7e494693b1f0f0f323e8d4e0` |
| `src/orev3/execution/control_storage.py` | 50400 | `818edf2ced96705f5bca57d8e99e918425fe00281ccceb8a18b524f4ab21953c` |
| `src/orev3/execution/current_readiness.py` | 45857 | `6986ba8f81742b8eb40f8e83022297ed4b081e125dc5644ea84f53fdd9250d18` |
| `src/orev3/execution/dataset_validation.py` | 7387 | `327af72ca47a9c579f5741b9bc6af33bf568a69e3432ab645773fe5b9d657c78` |
| `src/orev3/execution/detached_evidence.py` | 30516 | `69f0db286744073316b5d1061f19ece0ccae79c399ccc9831f349a1ecd3801b1` |
| `src/orev3/execution/evidence_preparation.py` | 40811 | `25749df28d847136602e09342c33603e143eb68d2976443e6f98db6913ad0a2d` |
| `src/orev3/execution/evidence_preparation_worker.py` | 38101 | `eecd8e2d6c713254d8f53daaf712d833c380f6d0dca1c557ecef4ad8dfc8ff86` |
| `src/orev3/execution/external_inputs.py` | 6474 | `9108a8e753bb522ec2fd6e6ee631b379ae0aec2e63cb658e8824371a83c91313` |
| `src/orev3/execution/filesystem_capability.py` | 23574 | `40c02368343ddc9a4adf04b59f0871972d8139758708e1d24e491452d728eb00` |
| `src/orev3/execution/git_state.py` | 100822 | `3894118917269266ab716091299f436b616df19eae29e31fb014af322d1a2b77` |
| `src/orev3/execution/input_projection_worker.py` | 9187 | `f169ebc1ef4ba16b343937bf1a5544e13b5170cdf42175a59e3186fba832ca23` |
| `src/orev3/execution/orchestrator.py` | 62121 | `1032c1ba5d3c04071376ba7bcfea37369a4b46446f1ed304321f1cf2fff8f54b` |
| `src/orev3/execution/outcome_gate.py` | 21919 | `af41522e29080eed74eb20deb90ab97007fa9cf4995e6e29ddc042e7684d0da7` |
| `src/orev3/execution/phase3b_components.py` | 27500 | `8e3b8c7b829d58a0a3c720f8474cf67dc418f095d81f8c0b3e7f50faa7fa574e` |
| `src/orev3/execution/preparation.py` | 34170 | `b3ffcf6135ba7e9455f7d07e7871929d4d0c1fd510f0a5e229c96e324c4824fa` |
| `src/orev3/execution/preparation_worker.py` | 2677 | `3cd9dc2ee50a07c254fd9f9f6d3419cc85b53ab58af54bdaafbb2cfe0f12f162` |
| `src/orev3/execution/projection.py` | 6584 | `ce125338ac816ed91c723ee7508887d08b7c8b859d7dbbf54ec1bf9b64f4df23` |
| `src/orev3/execution/readiness.py` | 9831 | `286fa022991ba971c0b01e26023e25ab922b37cc6d0ae8da64dd7b34233a1b67` |
| `src/orev3/execution/readiness_candidate.py` | 85795 | `547bd330dd633ef015476e66b89df7aa4f8cfd8d2ff66430b81a666c4cd8d1ef` |
| `src/orev3/execution/readiness_contracts.py` | 47972 | `6fb4c4993f9314a79c7cffc7879b6f9f79d452b7339162a42bd1297a82be19f2` |
| `src/orev3/execution/readiness_record.py` | 106769 | `f9b1a33632f7e31cf26b19e14e7a2d39a697742ebd6d9bbd63c251c907a6c806` |
| `src/orev3/execution/readiness_test_worker.py` | 3388 | `d4a8d9ea055c4e26237dc0edfe6fcaae59a4441d2897f4bc5a75b7ca839e5bc0` |
| `src/orev3/execution/registry.py` | 19073 | `5afb7dcad174bdcb49ce875caad71c893082ab1770fc5cc49c4907aec6e1194c` |
| `src/orev3/execution/replay_preparation.py` | 11814 | `1f98b1404eeeb9bde6046961a854c578dd29ef06493f6f44b3d65cc8135b6b3d` |
| `src/orev3/execution/replay_preparation_worker.py` | 5572 | `901ce12dab86544d9bb54dd44c532b9842b87f93dbd236f211ea6f05f25ea708` |
| `src/orev3/execution/runtime.py` | 165138 | `0f5fc3b008afaa9f83b638d0b744cfb8fa72437aeb35e03696ce6d80bb7bd7c4` |
| `src/orev3/execution/schemas/v1/adapter-declaration-v2.schema.json` | 15980 | `a58a5596ae30355657a994873134e1696e6cb614b51c21555314cd663e9bebd0` |
| `src/orev3/execution/schemas/v1/adapter-declaration-v3.schema.json` | 15881 | `e6b9294498f7b51d34c7e8c03bf18516dfd0a840ba340fddfb9ba919a8fe4d72` |
| `src/orev3/execution/schemas/v1/adapter-declaration-v4.schema.json` | 18679 | `985fd13cff1ca5d399a1f254879c397167d75c0355c0d066a22441d7e2d3ab70` |
| `src/orev3/execution/schemas/v1/adapter-declaration.schema.json` | 14240 | `55fccfb6984b2a565f2d02abc913f76306f774f4e7445ff31c1cb74ffb418cc4` |
| `src/orev3/execution/schemas/v1/adapter-registry.schema.json` | 3993 | `012b5f0f874a350987e21f53937d5994d52a7c213456c6ce3818f526884d318a` |
| `src/orev3/execution/schemas/v1/artifact-declaration-evidence.schema.json` | 869 | `8e003c64196398d9880a68c77d228dd6cb4938edab2a2971ad3354c7c4127c4d` |
| `src/orev3/execution/schemas/v1/attempt-allocation.schema.json` | 1668 | `57d38f63b0fd8196d8d5cef207cf7481d164421ba59496f0e38149b46881ffaf` |
| `src/orev3/execution/schemas/v1/attempt-authority-contract.schema.json` | 5962 | `81b6baff7d3776d3891134bd3e26a3c791f4eadd14ab534bbd797752786ab677` |
| `src/orev3/execution/schemas/v1/attempt-control-record.schema.json` | 24380 | `76b48b204325589cc3014f0f8335311fab09ee8fdf95913127a5f990848c2310` |
| `src/orev3/execution/schemas/v1/attempt-identity-material.schema.json` | 1760 | `ce2b69e1b0466318c54350f2237d52529f1b43ac14820138e05a2a3db63e71fa` |
| `src/orev3/execution/schemas/v1/dataset-validation-evidence.schema.json` | 1960 | `a79ebbdeb2f3822354b910808bde88e56ff55b39cce476ab540695c48d03d7a8` |
| `src/orev3/execution/schemas/v1/evidence-preparation-policy-bounded-streaming-v1.schema.json` | 7200 | `2a89187c8f07a57b92ba1ddf209c5e68079823dd0f3a4bbe25307b162ea011b3` |
| `src/orev3/execution/schemas/v1/evidence-preparation-policy.schema.json` | 6719 | `315cdf396c03098678235b558b8e5569973e1221b2dc878b52d8bab3ebc98b81` |
| `src/orev3/execution/schemas/v1/evidence-preparation-v2.schema.json` | 4556 | `44cf31c797e777dc17ed33d8e04597dd45c5f7d49e98adf4f67c66f34aa190b5` |
| `src/orev3/execution/schemas/v1/evidence-preparation.schema.json` | 3840 | `15538013df0b35a9514756963cb591b875101169cd98b04cf37b53290fc14731` |
| `src/orev3/execution/schemas/v1/execution-control-manifest.schema.json` | 23816 | `9464054245b0d85bb39fd2c8cb3549ef346bfc68612a5b709b4ee7b32bfa018f` |
| `src/orev3/execution/schemas/v1/immutable-input-snapshot.schema.json` | 1134 | `173e943980c87d27a4e27acdefc915fd5b5cd43a121b0058388f3072c6b81ce9` |
| `src/orev3/execution/schemas/v1/implementation-binding.schema.json` | 2111 | `e477b1301340b216b9a9310eb96750ab7881d85e7fbece9652c4e89490812acb` |
| `src/orev3/execution/schemas/v1/launch-authority-snapshot.schema.json` | 1399 | `da5a5ed23f4095fe812c6a84e6798bfd7ec707f0db0ba3a1ba22776b9ccafb9e` |
| `src/orev3/execution/schemas/v1/offline-artifact-manifest.schema.json` | 1699 | `cfa3606e0c5737fe0679f1152b7c5fbde123fb9ccb834d57d80b18a15416fd53` |
| `src/orev3/execution/schemas/v1/outcome-authorization.schema.json` | 1707 | `a5b6dd23c5f82d9fc2c3690935809479f07d764725fbdc058ba2ae4cafc7e426` |
| `src/orev3/execution/schemas/v1/outcome-blind-projection-evidence.schema.json` | 2240 | `44725f9357d2361ca1185eac74468e1cfe382cf418145198f88d342a753bfb75` |
| `src/orev3/execution/schemas/v1/output-namespace-identity-material.schema.json` | 983 | `deb02a2375d3479b0bb2129bda15e3aa9992713a22d944f4e78fa4b7a5b283c3` |
| `src/orev3/execution/schemas/v1/population-accounting-evidence-v2.schema.json` | 2726 | `5f311c04486fb2f71634a4b165004d6088b18699562500d8a6b1a5f2a4745991` |
| `src/orev3/execution/schemas/v1/population-accounting-evidence.schema.json` | 1394 | `115edbf8775f334cb7d60f2174e72a043ac05112d5b53ebaf3cfeacfd1257384` |
| `src/orev3/execution/schemas/v1/profile-conformance-evidence-v2.schema.json` | 2567 | `c8f31746b8252988583bf2df83855536baf40ef3dfe2dc869e27ee5479ec21cb` |
| `src/orev3/execution/schemas/v1/profile-conformance-evidence.schema.json` | 1431 | `7778a2d0cab2ca491452e89162ddb99da952a9f34cbf1192f4356ee0590684bc` |
| `src/orev3/execution/schemas/v1/profile-contract.schema.json` | 3799 | `117e0d32b9afcf4b76763842a3b9b9d7ed36d5a21c8f5b90d227f57338ae9298` |
| `src/orev3/execution/schemas/v1/readiness-failure-receipt.schema.json` | 18489 | `00e5d18b39e2a7f0e42536647c39b2478e946caca51773258feb337b2e5a54ad` |
| `src/orev3/execution/schemas/v1/readiness-record-v2.schema.json` | 23427 | `2436da1b932237a005cb703d210a6baee8e56b466bd54de0ac6a58d2d227e068` |
| `src/orev3/execution/schemas/v1/readiness-record.schema.json` | 24653 | `c354fa32d8882b8fd8231fa4fed0d943b6cac28dec43fe879d5df525f9d163b7` |
| `src/orev3/execution/schemas/v1/readiness-test-evidence.schema.json` | 1522 | `58b73eeade341e47d812f855b73958bd3d469c3dab47c1f942d7de829dd2b01f` |
| `src/orev3/execution/schemas/v1/readiness-test-policy-v2.schema.json` | 2867 | `2c09e2088c116b4fd2b2ee2cb60f193d5923c01a9c21e38766f3a3326d17b11b` |
| `src/orev3/execution/schemas/v1/readiness-test-policy.schema.json` | 2473 | `1aac9f934c4d58274578519098d1b1762637a3e77902d0b43dd2fef4866f8886` |
| `src/orev3/execution/schemas/v1/replay-evidence-v2.schema.json` | 2791 | `124b27cd9458697e3fff9e9f52305b2a416718abcbd08bcfe62692ca14912b0e` |
| `src/orev3/execution/schemas/v1/replay-evidence.schema.json` | 2577 | `a2666f32cc87d824c9e357cbb03534bfeaf5ac6c9f7ebd16e38ee38621b6d4d0` |
| `src/orev3/execution/schemas/v1/repository-authority.schema.json` | 1182 | `05bea86ebbcc9631da12b929c6b96f0b2111dee245ed198c894f75396d466029` |
| `src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json` | 12522 | `c401708cc5b1803d8e2f20538469dc6a9b5f3050f818e0388913a1ac6e266844` |
| `src/orev3/execution/schemas/v1/rq003-experiment-005-projection.schema.json` | 9350 | `734621c34456b079ca71f42610212d9cdd8a3fc76367c8ff67785428dbfa6fed` |
| `src/orev3/execution/schemas/v1/runtime-contract.schema.json` | 7613 | `d67aa372c7913051051b09cf35138a7c17d34e6f06f13c16c4ca522e376bb00e` |
| `src/orev3/execution/schemas/v1/source-scope.schema.json` | 1803 | `921938ec88ede21282bdbff191ab361751f127c27649d51d0eae28fc76c5ceb5` |
| `src/orev3/execution/test_policy.py` | 4727 | `d4fa16dd6bf399c4c771c72d1b9919becff69da353704512995cd43a3da293af` |
| `src/orev3/execution/zero_input_phase3b.py` | 3774 | `1bee17f4379930d854589fdc2748f35d5a9015b0a98028eca97199ed4b288f78` |
| `src/orev3/experiments/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/experiments/compare_baselines.py` | 3134 | `ec261a834be373a4742d02547dff2ead7b4ece7918e5ab247d563ca4f354c4bb` |
| `src/orev3/experiments/models.py` | 1863 | `8be83443bc9dca4f252ff99ad6d888630ac8863744de42ff903b161714a016ef` |
| `src/orev3/experiments/random_baseline_distribution.py` | 5861 | `4b646973b4145cf23386d4be94e2882988da4fdc610204ec8de8b293a8d60e91` |
| `src/orev3/experiments/rq003_execution_specification.py` | 58816 | `47de8ef93ba5560960e0dbd61cc51ec6ce2c4bd5a6750a307ba7fed26b378ab4` |
| `src/orev3/experiments/rq003_execution_specification_v2.py` | 46040 | `864676352e2d30b60148788f37c7f296e5138c24a8e82e90eb1bed269dae8c28` |
| `src/orev3/experiments/rq003_experiment1.py` | 76882 | `120f400e85a470b1acf9e51149883052f72c6b9218045ae491822838e54bc0d5` |
| `src/orev3/experiments/rq003_experiment2a.py` | 62123 | `2c61d4ca0ee7cc252e75a516009e274b014f25135d51becf4cf1bc621ad6fc65` |
| `src/orev3/experiments/rq003_experiment2c.py` | 53856 | `a80ab794885c1a8970233f2e56740b32e8c4ce2dfea582e6e502a1e64c4a7fe1` |
| `src/orev3/experiments/rq003_experiment2d.py` | 67001 | `b9b75f43e65f76d144b497fdef003cfe761baa78da84f3531420a20348e0a809` |
| `src/orev3/experiments/rq003_experiment3.py` | 80630 | `de7238fe0b82b9ed2687a11c824b64f9001362e1b7e748f2732ed14a133fa4da` |
| `src/orev3/experiments/rq003_experiment4.py` | 89544 | `0ceb71b4c6b9b329a514bd2793be504685ad81b420cf02d9f7918006bffa36ab` |
| `src/orev3/experiments/rq003_experiment5.py` | 29726 | `24a4b6635420b89b3d371b07077c8bd962316a9e261468a2d849a9ef2c69c0b6` |
| `src/orev3/experiments/rq003_experiment5_configuration.py` | 542 | `d0496ba1be92848fed4f56e9bed2287189a047f5213d84f96b38bd5031f7b0f4` |
| `src/orev3/experiments/rq003_experiment5_evaluation.py` | 64263 | `67ba120433aab4b8cc56fa399851eb5f4ab9d671d5c925c9dc464c9ad3d5d89e` |
| `src/orev3/experiments/rq003_experiment5_ranking.py` | 77654 | `fe8756130e22946c72fa749f6f37a86a5dadb7cd5a4276560cb25fc8a88697fc` |
| `src/orev3/experiments/rq003_experiment5_source_measurements.py` | 8836 | `8e7d14c54db68cd178da995fa2b188436d9936076acdd6741bd939b2d89d4a9d` |
| `src/orev3/experiments/rq003_experiment5_source_processing.py` | 106848 | `b06ecce03f8b3a5c74235f5f97399be1039dad0074257d8e38f212b688875835` |
| `src/orev3/experiments/run_baseline.py` | 3540 | `353ed76ea0f4cb23fbb5603b27db92903f63fadf96704af6d17edb87b09b3a07` |
| `src/orev3/experiments/runner.py` | 9004 | `02008bd9d8abc07fa775157cea8f8cf2342936973e75b4fba1ab51299dca884b` |
| `src/orev3/experiments/scorer.py` | 3314 | `91d63103a00ad0987f5594854233a8f3f058cfdc84d545e68c64db849a037fac` |
| `src/orev3/experiments/timing_sweep.py` | 7482 | `5491471cf24958b489782817e39da0caab1a27b6e66f429353dfc15a67375ae1` |
| `src/orev3/features/__init__.py` | 17397 | `a00f0faf10843c7105aff4f9758b891feeab02ee1067d98dc640e6e1c0276b52` |
| `src/orev3/features/base.py` | 901 | `fb2c4f10c925745d023a6227fad6042d976c8b3d6fffbe0fe32d8a60877f086f` |
| `src/orev3/features/board_summary.py` | 1558 | `d831119bd4541d475628239c591d948c304074e3e63859257d4514e7fcec0a3c` |
| `src/orev3/features/context.py` | 4148 | `1106e196782ce6e234623f595d759fe951e9f82190ac89c29a6be25d082cbdd6` |
| `src/orev3/features/pipeline.py` | 2386 | `2d2afaae3cbaa31b8a26cf13d4c23235f78c85d231558b7391cc1e2f3b5469aa` |
| `src/orev3/features/raw.py` | 686 | `8406584edba22aa07d3fe28b1ef3862c5d2eabf6d76ce916aebd752fd0d591f7` |
| `src/orev3/features/registry.py` | 2566 | `37eb5f64065480b0ddab36d82c5a309363013bca79327ce81782bc20e04aefd0` |
| `src/orev3/features/relative.py` | 3863 | `8ab9577dcbeccf2d17bf7e7ecb47c0f91930299fe2c4d1acd210cf90ce3bdbeb` |
| `src/orev3/features/rq003_active_round_motherlode.py` | 14799 | `e9c93eee6e1e8846f9b5ab28c6c1edd7916be53bc9a924ad016e0f290c460c73` |
| `src/orev3/features/rq003_contracts.py` | 24916 | `7b60c9e85593b4931d2a5e6aafbdcb4c1b35e79b3fc6150ef7a1185afb62fad3` |
| `src/orev3/features/rq003_deployed_lamports.py` | 13300 | `0f5c2bf522ffef9678d847aae31bd04a6fc20a01a5ba10e5efee3cf8362520f3` |
| `src/orev3/features/rq003_execution.py` | 54130 | `f70c7d7f4cfd726cdc287d8d2007fb80a96be37608482ce1f5e98eaaaf43655a` |
| `src/orev3/features/rq003_measurement_support.py` | 3537 | `5cd847fce42a11b98593630bad2b67a89c5a8ab24d73fa3eb48caf86c996d1a3` |
| `src/orev3/features/rq003_miner_count.py` | 12576 | `65bd1282b427ee0b631134272220f7f98c9f924cf74029c7c4988d4887f02fb7` |
| `src/orev3/features/rq003_production_cost_ema.py` | 13965 | `42feb5221a28f54f54e1492105b3da74c3e76938cafc34a6c9452b5b4e58ba6e` |
| `src/orev3/features/rq003_registry.py` | 21486 | `d7739d842a0d4cd99e50a3c8e17127fa7c591f94cf0b95d1ed160dac7163825a` |
| `src/orev3/features/rq003_total_miners.py` | 12690 | `8760c6f2aa0bda3862f8a5fcbb6cfc47c726f00d8456f2b18f4188f18f7efc89` |
| `src/orev3/features/rq003_total_vaulted.py` | 13305 | `a4b3ff0274ef2f2d7cfab8c0b8e1b42b171e23572ab2c6c431b5e13aebf844dd` |
| `src/orev3/features/rq003_total_winnings.py` | 13758 | `24df3574f3919af4a51df1233bfaaf692b14b03e221f0a68fe409af022e109dd` |
| `src/orev3/features/rq003_treasury_motherlode.py` | 13831 | `125a0db431a890eaafee711fabdb62586671e824cd14df0a8e0bdc2f03f05138` |
| `src/orev3/features/temporal.py` | 17578 | `6bc58b7e8cd88155cc3ce9379f302ec9401b517b366b5e2daa51f7d3593fb153` |
| `src/orev3/features/types.py` | 759 | `4c49fabde48811c20c401562aec84accc6fe014e1e62a621cff6d8eaa9caaa15` |
| `src/orev3/historical/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/historical/assembler.py` | 10728 | `4eec230a13c8bac25d48ed2efd7ef977b6f0c2e596dfbee645a5a0a58ae6505e` |
| `src/orev3/historical/build_dataset.py` | 5360 | `1a3d602e9e9e065e05d15570f43206db3a02ae4668700721ba95bec5a5af9b9e` |
| `src/orev3/historical/enricher.py` | 6244 | `12c4c1ae2f4603c269f676412ae12e04211abe198dddf258133b80c0b3b8e951` |
| `src/orev3/historical/inspect.py` | 2784 | `e9ee743e60348d69e100c19fbe19ee42d7b70a682a244b6fbb6a0f4e13d3ce78` |
| `src/orev3/historical/inspect_enrichment.py` | 3662 | `c7ce09981df353a7d667140a1c3e65d55f01b91d419fb0093bca3dc72eca4750` |
| `src/orev3/historical/inspect_lifecycles.py` | 5645 | `7427c7a45d0f1a88867c43e2c55bd4ec55a64ab5fa9e0248b82bdb6ffdcff699` |
| `src/orev3/historical/models.py` | 6838 | `e062903f86f81a7bf825ce0f30eaebc4af880510364a112fd90f13395367c4b6` |
| `src/orev3/historical/persistence.py` | 3993 | `db5c6695154a9d035f2e0f62ef6d38ae8464d16225444b8edb0ec205988fc80d` |
| `src/orev3/historical/reader.py` | 4575 | `0c7acec0a98e6d5967171c7f900a40daf0ee9b1dd46cf973fae59e06049b7359` |
| `src/orev3/ledger/__init__.py` | 77 | `4be755dc0ab04512ea1574629d3b46e81dbc6108db350c3f193e2a7244beb955` |
| `src/orev3/ledger/claim_attribution.py` | 2758 | `5ea0d55309e204d9778bf7b61f19c30fa676e1609d585dc4d873cd912efd6d3b` |
| `src/orev3/ledger/cli.py` | 8274 | `b3c812fe39c98539a822a08df33a6ad04f8e40d550d9080a4815720b67289a9f` |
| `src/orev3/ledger/completeness.py` | 1408 | `13033908369652a9b58cd810f8684f0d2fa268552473022cac5cbf6c832bcc89` |
| `src/orev3/ledger/decision_capture.py` | 2474 | `3d35e8cc5daa294759f7199517d10ae1cff2d058ec765911e29dc6c8b00a6b69` |
| `src/orev3/ledger/event_types.py` | 1819 | `070951ce7acbff5c25442eb92063d4073bcfdc2f15dafc9c36dd3f5d71a16e5f` |
| `src/orev3/ledger/historical_import.py` | 4554 | `c83a94479e5975fcfcbbecd0499a28997f6f7b771002b55996d563a034c53fd9` |
| `src/orev3/ledger/identifiers.py` | 1205 | `3452ecf96da4f66bbc84332bee19379f4a4084e30210bd472290f8c7bc0c9571` |
| `src/orev3/ledger/observation_capture.py` | 2469 | `0807a9f294b5cbf933c492c17dcb215de6056c603e96cc1f5d5cc66948722a5e` |
| `src/orev3/ledger/reconciliation.py` | 5416 | `ff0574c619ee0a6856ff68e593922fd35cd7fab91aa1f4c37693962a045f5e42` |
| `src/orev3/ledger/reporting.py` | 5761 | `8105d3ec81e4d659c710b2a4302489d47d5b21bdf971565a7123c5202571c10e` |
| `src/orev3/ledger/reward_observation.py` | 716 | `ce871968f3dac36e1a4ce8de3c8e33266c310e677db4fecfa38cd1b8da320253` |
| `src/orev3/ledger/schemas.py` | 11933 | `21317361e639ac0ad055c910d9a8053162baa846e71b06ce8d8cc845c6690a9a` |
| `src/orev3/ledger/storage.py` | 9860 | `d4353cfbbab44c210f05033c98a2de8ee418b02a769132de93bf29767629a378` |
| `src/orev3/ledger/transaction_observation.py` | 4269 | `2b0a24a90424941584b1b569a2ea7a37eed7fb6758fb8ff0c8cd8ba745a34bd3` |
| `src/orev3/ledger/validation.py` | 2671 | `6b42fe9abd15abf2f41bd2087806c56835292172a11ec08e1f49bb2d3e861ecd` |
| `src/orev3/ledger/wallet_snapshots.py` | 3035 | `6ae4649acca1a46aa62850037c52cc206ed2c178034d4d9f754b36a111a89644` |
| `src/orev3/modeling/__init__.py` | 48 | `71edcfb5437a0d5ea54e18c6cf0ce57fd0e55a4b7ad66ae403e194f3d656eadc` |
| `src/orev3/modeling/baselines.py` | 1960 | `33b0a7f8468eb956ec52dfed1ae9d3832ebc61738fb88726f3e8c86a1f075d76` |
| `src/orev3/modeling/data.py` | 6116 | `554ee48cffb36058976ac994b64ae0abd61c62168daa4735922357983d8453f1` |
| `src/orev3/modeling/feature_sets.py` | 2810 | `15358c792d2e6a3fb7911b23be69679c68c67e26c9bb7c9f633e2cf6915f8623` |
| `src/orev3/modeling/metrics.py` | 7453 | `af0a4ab648a7bf268de70d3f4beb1b3e7ef0d51ba2cccdbe6cb7f73bcb135abb` |
| `src/orev3/modeling/models.py` | 3828 | `fd8d94dbee18f3ad75403986dd01676279c0a4f2723cbdbe383f8b8ad0b7776e` |
| `src/orev3/modeling/run_baseline_modeling.py` | 22551 | `f9ff917bde9c3c977e98353f708b01609a32438224e5fa2b3e456833598188f1` |
| `src/orev3/modeling/splits.py` | 3239 | `b6bc2fd65b1eb0f545ae8037bab3c215aba75b8acfb42af1162cb08f20649079` |
| `src/orev3/observer/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/observer/accounts.py` | 5451 | `fc3559821bf92bd2f073da1e854dd9f0a85780dffafa86deb5b975df5d829260` |
| `src/orev3/observer/collect.py` | 10754 | `d7570a9b6047a6202e788624dc2606ec8d90a927615a0f52d1af34d02c3c675a` |
| `src/orev3/observer/inspect_round.py` | 4904 | `0463fc1da4850807bbee98d97fb4ff4de94bf9858a56af7d2a43b013384a8d81` |
| `src/orev3/observer/rfc012_runtime.py` | 8607 | `1e8e31421c660de35b28a561bf3d8ce05289be6d2c8292b80afefa3e187b208d` |
| `src/orev3/observer/rpc.py` | 7406 | `a547119fb76eb08049d7ebce876d8937082cd9df2b64416af9795f1482f29f5b` |
| `src/orev3/observer/run.py` | 4061 | `08614b3cde1f1c7616c7164368176a2d9bf3859a4f5f81df73e6c6aa68626bc5` |
| `src/orev3/paper/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/replay/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/replay/engine.py` | 6469 | `dc3afc0cbfb3a5f788ffb33f00d3b22055bd7a734c515d389bf3d7edcd6b85f5` |
| `src/orev3/replay/inspect.py` | 3762 | `a1c37ae1079db53ef03043292773d1c8482541c22eb5a2c38ea8dfd98471030b` |
| `src/orev3/replay/loader.py` | 3317 | `e4f71b6a985ced0411df348dfa525db1dcaf359747bd328ebc85a3eeeba80963` |
| `src/orev3/replay/models.py` | 1619 | `00c05111b06c577f473390c4bf734fcab46d85b51b9c81c823f43d5e9749607f` |
| `src/orev3/rfc008/__init__.py` | 132 | `2598c29d3ad594ffdde63692d4e353b029030b7b135af98383f60869a575700c` |
| `src/orev3/rfc008/accounting.py` | 2285 | `8b35377f3683ffc058502230bae8f8355e0c010337a7af0d59b8f5a4df44f460` |
| `src/orev3/rfc008/analysis.py` | 11506 | `205df8c7270123e877a5567a95a57524cd4b0833b802c22037c3f544712511a9` |
| `src/orev3/rfc008/approval.py` | 20609 | `ddc5cdb141b68d696b2c0fbe93d3a4f295e39a1842d07016f58b347e5ca3d13d` |
| `src/orev3/rfc008/approval_contract.py` | 18286 | `bd7a76be056174e1c7b2f7d462e2677f60aca457baadb522dcf694cc9d386a6b` |
| `src/orev3/rfc008/authorization.py` | 30862 | `6d636fe619f8a63333a43bd825f7971a2accdfc52eb11bc4eb8a1b51d3f442d6` |
| `src/orev3/rfc008/burnin.py` | 61937 | `844842a64635fcab1e5a8b430d1c96110bdc10b986a63838c8bc00fa19335697` |
| `src/orev3/rfc008/cli.py` | 76101 | `3ca81e30c6e4127559f2dbe563b88d8c623d7fee09da8e4de501aaae1939597b` |
| `src/orev3/rfc008/collector.py` | 14959 | `581cbd9b29219a4126e2a6d2860670ee71174e4caea576a90b83dca7b6791988` |
| `src/orev3/rfc008/config.py` | 4852 | `020adac8f5581ea098f0d69d58d704a5b88f93fb538c71428442d1d904b4729d` |
| `src/orev3/rfc008/dataset.py` | 8251 | `767ac339545c2f7ab63f166acd239620217fb4815fb4ca9cb1e974f9efb6ec06` |
| `src/orev3/rfc008/decisions.py` | 3822 | `3979ac39b4ca2e6a8034fc43a861f842a1035182fd22d0d05664b265624f1a93` |
| `src/orev3/rfc008/freeze.py` | 11186 | `61c3925c6728faf7cd625bff2ed9d3aced03120df836a217e1d26461d4d4627e` |
| `src/orev3/rfc008/lifecycle.py` | 28479 | `e6ce258da7bb21e01c0b4e196fec3e0522c48f6c87fcfed7efce8b6dd20ec7f0` |
| `src/orev3/rfc008/marker.py` | 68316 | `6551d4f005a66dbec17369a76ccaa2187e906ddfea36c5678939ba49863788b7` |
| `src/orev3/rfc008/migrations.py` | 39354 | `aa7d887b269b76db5dd4385ef72cd6b6eec6b6ef6df2c6994ebce816979c13ce` |
| `src/orev3/rfc008/outcomes.py` | 9493 | `cdfa8f6e93b0edccab47caa8548e6e56fed0317f555ab5210ef894c3b0a568da` |
| `src/orev3/rfc008/release_validation.py` | 31207 | `206437ab63dbddc25b6ff46c317ccf2894595d89e66476f120382cb721b55099` |
| `src/orev3/rfc008/resolver.py` | 11592 | `fb27382cd6c1ca3f7f179fa698f6b2a129a7e4981a6a84cdfa0d6511ebc8a168` |
| `src/orev3/rfc008/resolver_config.py` | 2077 | `16a7bc2e7f82d96879a1eca66665ddedd16357309c007bfe6141bba9650ac57b` |
| `src/orev3/rfc008/rotation.py` | 39732 | `41e7c824e7bff2570458802c2c3de03cb4d76680283966dce9a67b3ad29c1077` |
| `src/orev3/rfc008/schemas.py` | 39489 | `5cb0381ee44081eeb309c396a51fccc1931b162ca7ee6fab7d34c181cb4a65ea` |
| `src/orev3/rfc008/status.py` | 14725 | `df1ec019ca9ae15c3a58d65d328ba1bb5329ffbf516e5f1ce06861c00a69b40b` |
| `src/orev3/rfc008/storage.py` | 44974 | `9d1002c8b514b9d6bfd90fbabf60ed03cbfb4747c457201491dbc4a0f7f030a4` |
| `src/orev3/rfc008/strategies.py` | 995 | `a32c88427057836f35457f48c1f3a289049b25e4629cb665e18e1776cdf713bd` |
| `src/orev3/rfc008/supervision.py` | 29031 | `eed88fe82271def6eb82404ddc4117cacb33d9873dc494a765e3ff5f1007740d` |
| `src/orev3/rfc008/writer.py` | 1446 | `5adf23d13b15f81f119818ee43ed633e08d986bb962e342be05102581fad74c7` |
| `src/orev3/rfc009/__init__.py` | 408 | `9392212dd8f23257e6aed13b2535698ec961d8cd0e7e0dedd7e26e9948fdaf81` |
| `src/orev3/rfc009/continuation.py` | 72155 | `43bc3130072e0ab95f038987570c73ecaede141ca417d6102060c5fd95bd1fd1` |
| `src/orev3/simulator/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/strategies/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/orev3/strategies/base.py` | 631 | `a933c378cac28da3421a669f5800a7ae01c535ee6befdcb3d3389d410295e1eb` |
| `src/orev3/strategies/fixed_top4.py` | 1061 | `fa29317d44f0e2fddaa704d0ec6ac073d68c841dbbf651d63ba8792b3c882ae1` |
| `src/orev3/strategies/inspect.py` | 3009 | `1da06078e1485f51c57acd00cd5ccdc20bcfddd55f9f6e9575ae8034e56d1a55` |
| `src/orev3/strategies/least_crowded.py` | 1854 | `7e6934068aa5d15df42ab3210e1f8f619a6a81e71b04c3e04c3142c644ea423f` |
| `src/orev3/strategies/models.py` | 1432 | `68b83dc9496937ed048c1a4a5de13107d6b894e0cf8166419015d1746dbc3ce7` |
| `src/orev3/strategies/random_top4.py` | 1552 | `063865cbc70ec68c5852916a953838b174def23ee75ade2af2e31bad96aa7fd4` |
| `src/orev3/strategies/runner.py` | 1458 | `26a263f9e90a43a7d19c1708f6a27e3933d08baa76eb4301e7050d8c7aa6aee1` |
| `src/orev3/strategy_lab/__init__.py` | 4475 | `497e1360039168a415d7d31226940c0c77d97bb7f6d01fc8a6e270b4ac19990d` |
| `src/orev3/strategy_lab/baselines.py` | 7829 | `7dfbdf952932b3f59ed9a528271da8417f59c857487e615f3b18554cc582aa28` |
| `src/orev3/strategy_lab/constraints.py` | 14187 | `16289e73d670917deeb20448f4b2c59bffe1558c7068c9860aee0df2f6b360ce` |
| `src/orev3/strategy_lab/deployment.py` | 5415 | `c82896bb26b25151a11f0beb90b744cc87c4687b73f092049109b4c121556e7e` |
| `src/orev3/strategy_lab/economic_cli.py` | 19251 | `ee6a39ac2cbd726448859e2020033c987152752427d2510b8fd5f2b7ea339818` |
| `src/orev3/strategy_lab/economic_metrics.py` | 20218 | `9688b19af2f57ec39238b10635350862f3ccb894e03c46bf177c03198b6f6833` |
| `src/orev3/strategy_lab/economic_record.py` | 16735 | `425c6212cb52d26e98105914673c6b1a9768798b4526889723d8b06cfe130339` |
| `src/orev3/strategy_lab/economic_runner.py` | 15131 | `bd4fd01fef513bb4bb2f353bdbcb8159afba3267d5d5239f2eda20feaf654438` |
| `src/orev3/strategy_lab/economics.py` | 22995 | `2da43dd52bdf70832a1ba5f8c11416d4268bc5bb3f90b3a5da4674f67887267f` |
| `src/orev3/strategy_lab/evaluation.py` | 3785 | `c1a296628e95a300a89f666ef887e9244b0ae5be059db73db8b72f2e68f1eb5f` |
| `src/orev3/strategy_lab/experiment.py` | 5993 | `18f8c2d7f032cf1c4649c22b4e6939017df69c658fee2d6c775f862ad845d130` |
| `src/orev3/strategy_lab/interfaces.py` | 5459 | `c153aaed44f508465766b6ec2564fa6512db4639ccf9816e8d62dfb5448aac6e` |
| `src/orev3/strategy_lab/materialization.py` | 6611 | `ad9b0d608212a0014fcfaa9709d77218375c91f0b66b9fc33e0f9b0555127596` |
| `src/orev3/strategy_lab/metrics.py` | 3277 | `ac62a499edebb89bfa52e7d45e0c5b163ea883d5b8533a9c9fa4427c0d35f10e` |
| `src/orev3/strategy_lab/readiness.py` | 2647 | `56428e8033616ba92980a6576dce82340364142f154777955e088af20881a071` |
| `src/orev3/strategy_lab/registry.py` | 6112 | `a687466cb7e8dc14f47ae52e48579961e55141c3a06821a62fb993f1a4142a0d` |
| `src/orev3/strategy_lab/run.py` | 15571 | `e0d4c5c84668106414f45beee09f16c179491e2c6f3d311fdacb6c5d4d4db55d` |
| `src/orev3/strategy_lab/runner.py` | 6715 | `c63404db6661b873230a0510ad5bdcc273729726fdbd2cdc0d2ba9b206e0933d` |
| `src/orev3/strategy_lab/settlement.py` | 51942 | `fbcee1835430e9b31f9c904ffbda3006e0db1de6252ee3d1a7c7d48e2b5c3d62` |
| `src/orev3/strategy_lab/strategies.py` | 5478 | `5e78225118210fed0fbd21e3b262fbeb8e909e6709e1afaf353c94cafb26b951` |
| `src/orev3/strategy_lab/transactions.py` | 32574 | `375658600b28339e6e27f98f638f2691534a0f07dae211bbd733116089ad2f6a` |
| `tests/analytics/test_conditional_analysis.py` | 2963 | `a812c8ceeba6aab36a7c79aaf4943f46b95cbe2309cc595b5398afe3ee93dfbd` |
| `tests/analytics/test_square_statistics.py` | 4675 | `12446a5f65567abfe6c7965899b9b0fe76b7e042a82c67d2e6a6858666bc511f` |
| `tests/analytics/test_stability_analysis.py` | 2312 | `a315e808e1616ee1cdb00d5cb82b14aec6f4f4cc99302e390e05bec72f1bb667` |
| `tests/collection/__init__.py` | 49 | `87e6530a3df52699adeb02c6afe8720aa7876fe3f65b46075a44240befd0d628` |
| `tests/collection/conftest.py` | 3615 | `241518a9b0c086dcae4e8c551954418b80426ffeaaedd1ba2b00759c0e970825` |
| `tests/collection/test_burn_in_reporting_security.py` | 6289 | `897e6499a2e744cf45ae3ec94703cb2541002043b1e48ca17144a0ba3748658e` |
| `tests/collection/test_collector_restart_and_concurrency.py` | 6377 | `b6eb046a2f361c2c829a9c30739236b7f5c8269f73a593e2a6b7edfa3585df8e` |
| `tests/collection/test_gate_b.py` | 10582 | `c9e1f83dfc80cca7dc6e4fbe40740b1518847ea3248eee78ff2ff75121f012f3` |
| `tests/collection/test_gate_b_analysis_dataset.py` | 21055 | `66df91cb2e2b0f5d4c6ad4d90576ed7f0930df9e110af7db860bf3efbf649704` |
| `tests/collection/test_opportunity_and_strategy.py` | 3179 | `8ed59e3a42596745d09dd209c3b96b30ee837bd004ed2239b574f62162f647f3` |
| `tests/collection/test_outcome_and_accounting.py` | 3608 | `b5ee91afcfceb709fad8e8624d96db35fef085a4189d3c6f2cbce1f6bad21c9b` |
| `tests/collection/test_outcome_recovery.py` | 19914 | `8eb3f855ebd1866361da941383b585a8719e2414371df82167dcda3cb0620fee` |
| `tests/collection/test_restart_proof.py` | 15650 | `eab461377b7d49adc8ae49671b0c4b014d0a08379428da8e18671cad1985af14` |
| `tests/collection/test_tailer.py` | 4301 | `aca51d5f935327afb8cf4f82323c67149bdd4a19dbf0e2c90c6787ee1790f30a` |
| `tests/dataset/test_management.py` | 18492 | `87badd45275ccc83cd3d732945a790c5a7ee55d472e012f4ea6bd9e2842b1ccc` |
| `tests/dataset/test_rfc012_outcomes.py` | 20799 | `aa8a150a08d6bbe37cb02224d427fb5126b2b9fc16f08150ff9e1deb67a2f2db` |
| `tests/dataset/test_rfc012_reporting.py` | 24713 | `0244307974756362eb7db09c595f1378ad109f958abd787cacdb8717ca4fabd6` |
| `tests/datasets/test_feature_reproducibility.py` | 7274 | `2879bb6092c7f9e6e3cdd9f2ac895e12aa4ea7ea5b4644f218c9b4deaa5257b0` |
| `tests/datasets/test_observation_dataset.py` | 1477 | `8c734f3621f1a3700ab77f2d96114c00051adfc81f8516b60dbf3340515c67dd` |
| `tests/datasets/test_rfc012_evidence.py` | 19465 | `176f99c291d47045ad4855eab40c14e79cfd6739af9b5b84b9028de0acbeec83` |
| `tests/datasets/test_rfc012_transition.py` | 18472 | `91a6a68f1eeacbc74c9ef37074b604f9c1a77ba1e2c118ec9b1179e2ab3dc564` |
| `tests/datasets/test_rq003_experiment0.py` | 17687 | `ea5839c6c04efb8055fb70c99ffce293d8f8d6a59dea49ddbeb46060783e2cce` |
| `tests/datasets/test_square_feature_builder.py` | 2298 | `4f41fc01ec0acc9f98ff4d0d2bbe714a3960e9563321035abff9950d8f94c12f` |
| `tests/datasets/test_square_features.py` | 511 | `9a072df579136fff5a9d16ce63286c38dc9724f3e8f4b4513951123a7d2d9b9e` |
| `tests/economics/conftest.py` | 2921 | `45cc19558da4812057cc1a6d56c984401925bbf6e8bd3222b089e16dcaef4969` |
| `tests/economics/test_canonical_boundaries.py` | 863 | `e073bc45de2892424b88044a6d7451bf637bbc8dc9caff1de8173b8e41c7cfe2` |
| `tests/economics/test_metrics_bootstrap_bankroll.py` | 3516 | `8eae4cfdd921e6a0713c3e3b61a07e0de21932db67128cb009d8802da7ac953d` |
| `tests/economics/test_reporting_and_simulator.py` | 3359 | `fbd5b87d0c2f7852e40edbe0fd14cf7682019a97a2147fd3c0dd5009b0a5de27` |
| `tests/economics/test_sizing_and_accounting.py` | 3984 | `821646ef4c84607dfd85e1c3797786bfdb0f2f97747f7cca334e6f594f420b89` |
| `tests/economics/test_validation_and_selection.py` | 3246 | `5ab14588cc9f0f731572b387ee08b9389e8549fd44a663ab29ef15869500b008` |
| `tests/execution/golden/readiness_v1/canonical-accepted.json` | 24 | `bbbf11b76faa60f1bd0223fd578f993a5ce63b2a0928c11b1ce43f15b6537deb` |
| `tests/execution/golden/readiness_v1/canonical-invalid-float.json` | 14 | `4157e155c9158b65e7f45c225b3b9510c5a73618c306e534dc12d6ddb7fc89c7` |
| `tests/execution/golden/readiness_v1/canonical-invalid-null.json` | 15 | `2e5bb0a6612ff9082a69f530010db34d0b9c459b345be114936568de2fdcfaee` |
| `tests/execution/test_attempts.py` | 8704 | `89c6b52b98bda7dd8da39bb11dc38c84a663d8b74a19c51fcaefbdf16ae6e471` |
| `tests/execution/test_canonical.py` | 10039 | `a708044014b19a60d66cceff85481ccef8c5c695cf998401aaf8d6dae6d1a796` |
| `tests/execution/test_control_storage.py` | 28782 | `56cfc48e7a65957ef6412af6ab9c8cfd0dedd6286c35b9d96d760d7b91ffa217` |
| `tests/execution/test_experiment_configuration_resource.py` | 33667 | `e3cd4db387e3196a33ef4c57c09b5eb19af5dd5438cdf0277f3ac05186018cc7` |
| `tests/execution/test_git_state.py` | 10567 | `e6be8e750d4689fdff70ca039563af5f73129cb51915735a7ad74086d904ffb0` |
| `tests/execution/test_historical_readiness_regressions.py` | 5063 | `7842c01dda4c2e97f803ba59735976df520c4819a50dfea4d99b7211283f56a3` |
| `tests/execution/test_orchestrator.py` | 44714 | `ed7e34d7bedcb4a301fe5edbe441bff77fb677133d6378af4b3a9b7f09a0292d` |
| `tests/execution/test_outcome_gate.py` | 6932 | `df8e79fdf5e7027f0fa53dfbe151e06643be3b80224a9277485910115984d37a` |
| `tests/execution/test_phase3a_preparation.py` | 19967 | `f1a22ea91821c52a8f387926ff4472700ba0ae8c51e0a0a1ce465a0a8957da1e` |
| `tests/execution/test_phase3a_registry.py` | 10967 | `a46f3f877d958f3a41862fea0dc809926127eff838375bf02eacbc4215330d7b` |
| `tests/execution/test_phase3a_runtime.py` | 7374 | `99563fe2bbc09cabe4e891c999002fe1964eda92998149a978ef4c64b0e63b43` |
| `tests/execution/test_phase3b_authority.py` | 17760 | `bbfb27c246894469301038ec80ce5c01cc7f8c278aaa7e65c99c8e6f877cc0f2` |
| `tests/execution/test_phase3b_external_inputs.py` | 14075 | `eb8969ff94ba507e3b7bbc7e84f22807b2de5185067a73022acb718af6554570` |
| `tests/execution/test_phase3b_integration.py` | 23737 | `ed8ba1a7428daa68e135878e77527c1c7c8f938bb349f24061aff144758a2f4b` |
| `tests/execution/test_phase3b_reconstruction.py` | 32678 | `3a6ce08a12d4bc856d855270fdba8bcb22616a68f6bd8eddd5040d5b0fe153ee` |
| `tests/execution/test_phase3b_worker_boundaries.py` | 280647 | `1da5a9f3ecab510c1b9b0f8c640334b1d77dc663b1a49d6e9db9d14d050345b5` |
| `tests/execution/test_phase3c_current_readiness.py` | 35043 | `ddf82574f110a7d80903406dfd07245ac0469feea4ef9925e1c9288c775baa71` |
| `tests/execution/test_phase3c_readiness_candidate.py` | 36314 | `81f292c63fec6046dd5b01e27bab2bb15c4dd67a3dee464b9b01839b244eaeff` |
| `tests/execution/test_phase3c_readiness_contracts.py` | 87815 | `061ea0863c7c1bf77e0d7a6133e56abe8a648b71ffa6f45ec4e36d3fd3f1c258` |
| `tests/execution/test_phase3c_readiness_record_v2.py` | 70259 | `ce13aaf1d55d576991cff3400ba27620d788585a3ac1e99e1b6fbafc44aa854a` |
| `tests/execution/test_phase3c_schema_registry.py` | 64508 | `e54640d68dfdc485611206e79a37b7fa511e0cae489d975d438bafbe914fa373` |
| `tests/execution/test_readiness_authority.py` | 25733 | `68e82dddfd9fee0d28a90a5abbdf124d84de96e1cb0fa6e229c323864144a725` |
| `tests/execution/test_readiness_mandatory_v1.py` | 606 | `dcbf11cfac2eb3bde636830b246dfabc2a7d3ee0fefe60493c935d79080175f1` |
| `tests/execution/test_readiness_record.py` | 23631 | `a8277ba1fd1bfb52e24aafe57e74e036d8047d10c2665e4cf9178be56037075e` |
| `tests/experiments/test_rq003_execution_specification.py` | 15226 | `47e245f33b4539f903514a931574e949ece65b650b73dab43dc570874e79feef` |
| `tests/experiments/test_rq003_execution_specification_v2.py` | 17500 | `339caec0117f2478fe880ed9b14a80cd6d51818893cab7cd33f83aeae479e186` |
| `tests/experiments/test_rq003_experiment1.py` | 19279 | `f01b65a5b699f15277549190a4f0446567119bcc526a91311acd09c5875fae87` |
| `tests/experiments/test_rq003_experiment2a.py` | 16404 | `4046cb4ea33c7fab807cf36da29c4edc359a204acb480fbc0f45e07458b83986` |
| `tests/experiments/test_rq003_experiment2c.py` | 14500 | `4b2ef3a81a0b7605ca9ef0d6c29e2c065a01b00375b108ba3eb67aa897134db7` |
| `tests/experiments/test_rq003_experiment2d.py` | 16827 | `b0bcaee1a7b5a789815ea41cce1f2dc6a293ffc70fafc2854dabe95c4e38b09a` |
| `tests/experiments/test_rq003_experiment3.py` | 20709 | `651c18f8479abf3c9f81fbeca890de417ff40c73a7d231793827f225ce4be885` |
| `tests/experiments/test_rq003_experiment4.py` | 23301 | `181c421e34e998494f5bfbea67104ada37dec0ff83dd542cd4a2bf298a67ddc0` |
| `tests/experiments/test_rq003_experiment5.py` | 69332 | `bcf4456c68e595e9139f035148abf32279fdee3c0d0725029c4b2849c5c0d909` |
| `tests/experiments/test_rq003_experiment5_configuration.py` | 3974 | `ed6ef93c224a2a4445a013ef34b2a0e094dbd6ed6f4f59c76c67a07784254af7` |
| `tests/experiments/test_rq003_experiment5_source_processing.py` | 54434 | `b274ad03c66810a9aa3abad0b61045fbc012079b00ce9366a5ab7793c7a7966f` |
| `tests/features/test_feature_audit.py` | 2225 | `048cfcb70c1d02d604a4b44ce4e03e4f5836280bcf7744768ca734e3a5345003` |
| `tests/features/test_feature_framework.py` | 8134 | `4e4f311d729f6cca2d236e764518057ff024dcd994769447962069ee643ec1d3` |
| `tests/features/test_feature_quality.py` | 7391 | `c24aac75f56e100d14d0a3a8f07614f9b96b567e64216041e16388d9b835775b` |
| `tests/features/test_rq003_active_round_motherlode.py` | 18043 | `b5a29b1da00f2be6ec2115faf0b6e0c1d807414a63ea9886e2e72066727b07b5` |
| `tests/features/test_rq003_contracts.py` | 16973 | `cd0023db130ce02a9242b7c91057d599436132cfc1b4a62482582b0c130d9695` |
| `tests/features/test_rq003_deployed_lamports.py` | 14359 | `731c7494c82e244d9927c6766d8459000c58b117e82d1a078fcf4038d0b63ab0` |
| `tests/features/test_rq003_execution.py` | 22723 | `46f33ddd92a26b3d3dc180af8f8e362d8fb47e9a540a08776bf1c9206a220b92` |
| `tests/features/test_rq003_measurement_support.py` | 2758 | `13bd585aa324f5721f2ce7a92c27dc246ea18006706ff32deb48ca62b3ae986e` |
| `tests/features/test_rq003_miner_count.py` | 13934 | `81c739166ab849b7a4e45c92aef2b897d6f468fe52c33122d660f180eee6ebf6` |
| `tests/features/test_rq003_participant_state_consistency.py` | 5556 | `6dff55a152e34c0eea7818021ba97539e4ac7eec89b73b6208df8b4343164e20` |
| `tests/features/test_rq003_production_cost_ema.py` | 19215 | `630a94387c8b15b67b898e6d59b402bebe065f20a818c85a526737df17a4f969` |
| `tests/features/test_rq003_registry.py` | 15990 | `7cbd9784f0eb382c5200091dddabd26611a0e8667710d82fcff962e41191a19c` |
| `tests/features/test_rq003_total_miners.py` | 17295 | `db0aaedc8a03b13d4d35f9f54ec8214009cc02701bf8b91dd2c4a0e5b5ddc41e` |
| `tests/features/test_rq003_total_vaulted.py` | 17873 | `c0a4025d33313a301479d6f44cfd236300e7fa9036e6428caba1f8f7988b168d` |
| `tests/features/test_rq003_total_winnings.py` | 18418 | `d37325029846086e01e4a89e71a637347adfd72743fb43a9330b4abfa98d1b38` |
| `tests/features/test_rq003_treasury_motherlode.py` | 17732 | `ad55d49cc59714b0c0daf38fdbde03f16836ea98691ed79e991943bb58f9c79e` |
| `tests/features/test_temporal_features.py` | 11804 | `73f36fb9a476b4aa22b2cf9bd4a58d07f01af97b27821b01db190c7c06ed0f19` |
| `tests/ledger/__init__.py` | 40 | `68dfe76cabbecbe5762bffde5a164cd3cd627fae8ae87b2ffc5f38f1b76138af` |
| `tests/ledger/conftest.py` | 1311 | `a04fd8ec22ee5e04f5dd9b03d0aba53ce75d59be7541bad3969fc393b38c619d` |
| `tests/ledger/test_capture_and_import.py` | 3771 | `e270f5ec56257a0cfe053e354c45afd960bce8f9281a9d16adf00036292c68c3` |
| `tests/ledger/test_privacy_and_safety.py` | 1099 | `fd392970a242519d6681be4ed34d4a77f34a68339f24ca728565ed9b9d6c1361` |
| `tests/ledger/test_reconciliation_reporting.py` | 5849 | `ffaf08ee820a3225363f973f433759eae5625dd9d9910516f5a1ce3552fc2db6` |
| `tests/ledger/test_schemas_and_identifiers.py` | 3756 | `aa19a5b9397bed0c99e0ce454f9ed2eb93364da6fab13eb67dc036a4f39d41d5` |
| `tests/ledger/test_transaction_wallet_claim.py` | 6422 | `7117c7d4be83a6ce4a6d56c70768a6cc4b8a9c3dea66d476d24f7d95aaa23d36` |
| `tests/modeling/conftest.py` | 1222 | `40ab9bcfb4a17831d18295bbbc093ee441914374e75702f6f8a0439982648f2e` |
| `tests/modeling/test_data_and_features.py` | 4101 | `a55dce83829e1e1fbe71a6a8f34d965f66330ea6389794e08da1bcbf89cc896d` |
| `tests/modeling/test_metrics_and_baselines.py` | 4013 | `8844bc215e25dfb4b2f9d57efc250d53eec31769f611f5c2d03f79d6b67be49c` |
| `tests/modeling/test_models.py` | 693 | `9695c544f73e7a6246540ad727b524f9132ac01627da436e72a081ac8646f517` |
| `tests/modeling/test_splits.py` | 1594 | `1f3fe38f1dfe060a579a2f72be71a4fc9b900fd68a37aa7d9a17e6b6570e8448` |
| `tests/observer/test_finalized_persistence.py` | 9953 | `f9368dc89710cf86293d81d670a35fe3b3b1926e9fedbf423034365b4a8b7525` |
| `tests/observer/test_rfc012_runtime.py` | 19046 | `dcb406b9b76a4da62e83200fd7eda15360f175893094b1fec85b4549dbb7ef7b` |
| `tests/rfc008/__init__.py` | 21 | `6f92d3d99f9304e04120050fff8fc8cc802e2adfd11c7e3570034d746352e291` |
| `tests/rfc008/conftest.py` | 4768 | `240a852b26b3d7ad493890a4e2d1e81dbbe4bbe549b9891831b89ccf232a034d` |
| `tests/rfc008/test_approval_field_contract.py` | 17438 | `9a5e0582a0741188f8cb3c7b2065344bc240092e4c0564f73b468e03d57b78c1` |
| `tests/rfc008/test_approval_supersession.py` | 19424 | `968ca0d3a11fa8233ce6b5411cef93f907d471673961c3863ead5892261f4cd5` |
| `tests/rfc008/test_burnin_evidence_v4.py` | 13715 | `75da9ea4c895fba8fbe71c980fe3f30a878fe165ad3f02755867020faea7f92d` |
| `tests/rfc008/test_config_decisions.py` | 4980 | `3fb72bf2eb08aad11e9f4739b267e450caf61cd947714cecfe021a6cf9d45c57` |
| `tests/rfc008/test_dataset_analysis.py` | 7053 | `665dc9ad587b46623cad954f95e1bf265757368edfdf796b12698fc6160d23c6` |
| `tests/rfc008/test_final_operational_remediation.py` | 16685 | `8d7e9875bec4eb4348a6e9c1d8aacc2dc808b1c64a846a8cab297cf4581bc6d2` |
| `tests/rfc008/test_freeze_guards.py` | 2481 | `cb20a0d9a9e64df7ba206d1193b855d32093a16dbfa2b3f22ec8b6a06896f93c` |
| `tests/rfc008/test_lifecycle.py` | 9858 | `81a05fdb85ed77b2ac9251fe8d0fdb04340677614f015842e88742042bfd53db` |
| `tests/rfc008/test_marker_collector_status.py` | 8006 | `2c8f68443691c9e587202abd51b5b61170ade74d0b0bce72efa4922ecf78524c` |
| `tests/rfc008/test_marker_publication_race.py` | 15735 | `1c3b28b4563094a52d71d5eadec0fad4038ca2ffd68d670ce7013fd25cf381a2` |
| `tests/rfc008/test_migrations_identity.py` | 3235 | `6f4ce415383732ada42adc102d3ca0e5f2b9f4a5ec265dd56bef5b29d3a185b4` |
| `tests/rfc008/test_operational_authorization.py` | 62397 | `dbcb1b4aa0127d21917c144fdae847d826a3a78da94b636991ee67b31fed4705` |
| `tests/rfc008/test_preflight_release.py` | 34535 | `12bca5dbbe599b1360b514cd5a054813764594440c83de98a45cea0f5eef75ff` |
| `tests/rfc008/test_production_artifact_rotation.py` | 31172 | `0ffdef939ebc26eb72a1696195bbb76d3a74cf158af6197822220366510468fc` |
| `tests/rfc008/test_release_validation_authority.py` | 16948 | `8050ab229d082c443528b56e13f014b8bb6adb0bb8be0107e3412118a7f34991` |
| `tests/rfc008/test_release_validation_paths.py` | 12824 | `c7ca4ebbadf6d325485ae1abf114a06bd6fc2b2e5b0367455af82df9a7d554dc` |
| `tests/rfc008/test_resolver_burnin.py` | 16463 | `7c5a4c458acb68f8ea1be8ac5c432d05aef620e244eccf7d9c3d5c73a5af7304` |
| `tests/rfc008/test_safety_surface.py` | 2300 | `a085644a9bfdc94c43223c1538d46001ccd58a6c37d8d6aee907cba7df387b4c` |
| `tests/rfc008/test_storage_outcomes_accounting.py` | 5041 | `2a95137c524be318e1153099a897bb8934c82f4e590f894b817239aa8a160668` |
| `tests/rfc008/test_supervision.py` | 34887 | `aa630f046a1a84a343476fc6d99e6e475a127e763312cd9673fb4df8c5508a4a` |
| `tests/rfc008/test_supervision_remediation.py` | 17625 | `2535b4b3b33329222d6d65123ced631b5d749eef8ff6457d1c74b6f62a4e60f1` |
| `tests/rfc009/test_continuation.py` | 53476 | `08dd4d22e9143831305370c2d903d5cfcee8f7fddea41d349cb0b76f59075018` |
| `tests/strategy_lab/test_allocation_materialization.py` | 10403 | `60c2bb00c0ffb4e2848ad2239fde866600630c7229ea7430d9f08414f805e529` |
| `tests/strategy_lab/test_baselines.py` | 8476 | `b9071078cc83f90800e1a0dd8d91bc7f43766773ed09741754648b771f2eaa92` |
| `tests/strategy_lab/test_cli.py` | 11739 | `fbea90171921a5c451cd6f58943fa65f92bcefb9c1c5cca487ed6b10a5210c15` |
| `tests/strategy_lab/test_deployment.py` | 5848 | `5fd26531dd3c66eadf339f470def5b5235c44d5a4b820880dbe9c23148560ed5` |
| `tests/strategy_lab/test_economic_cli.py` | 12505 | `b13ddaf19a6ece0e1b5cf6d053c9483e905b08f718c5c92faf43e5f2f6c7ddb0` |
| `tests/strategy_lab/test_economic_metrics.py` | 15591 | `04a4288a6caae456589fd3ada6b091bb51d22cd5d52e3f3f77bcfee9908c0bc7` |
| `tests/strategy_lab/test_economic_simulation_record.py` | 17936 | `80b9dabd559dcfa9278cb67548845e162a22fd2e513a1291333bb04c2dfc6f37` |
| `tests/strategy_lab/test_economic_simulation_runner.py` | 18587 | `05232f32b440acfb4703033509258db3dbad6641996c900d0164a60287676f91` |
| `tests/strategy_lab/test_economics_foundation.py` | 17995 | `ea9486ba34907ead0e563fe49548df289291f61a7130b505608d5147d977cd11` |
| `tests/strategy_lab/test_end_to_end.py` | 10752 | `8f5d9b44be787a046b0d33c4112d97dabc18c2e0be0c6f0061c3dbe1aba946bb` |
| `tests/strategy_lab/test_evaluation.py` | 5082 | `a7d1009bfcb96ff7ca6b146ff893ecb4d7d63f2b3f3015f301e02bd4192939f6` |
| `tests/strategy_lab/test_interfaces.py` | 8164 | `8f6760fdc02cc4cc1407671c6236954d5a1cc492b4fc3ce5d9e3058e6d7864fe` |
| `tests/strategy_lab/test_metrics_registry.py` | 8087 | `d96af2668e020eca6bb4ece5656c72a5291b406ae7740a1075f8a88591a708ba` |
| `tests/strategy_lab/test_ore_settlement.py` | 22665 | `6b898d55c21755f762a795c454453116edc036f3cb991fb5b5ae60982d114eb6` |
| `tests/strategy_lab/test_protocol_constraints.py` | 12749 | `699bec777ce3423ccabc87d65f7ba4a84acc152362e8499a324cb4234773d729` |
| `tests/strategy_lab/test_readiness.py` | 4250 | `792fb4b99d48d5ccf2282c268b8c44c2fa9222e025485f29181fd07d1369700b` |
| `tests/strategy_lab/test_reference_strategies.py` | 5878 | `910a3d93242ebb926da132a1675aea0fdfc45b096f66f8d5be097683d34d4417` |
| `tests/strategy_lab/test_runner.py` | 13414 | `bd61acc690d0003c20ea718629c785dc2b9cb19c86aa859ad8f0558ab79f4d57` |
| `tests/strategy_lab/test_transaction_inclusion.py` | 14826 | `1f6998bd56a2ca23c59faceb6d62134e8aa0733e93240a9a31c1684455e3dfdb` |
