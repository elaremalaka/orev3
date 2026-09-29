# Exact evidence retrieval and freeze verification

**DRAFT-UNREVIEWED. Proposed repository retention; accepted durable-location status and publication remain future gates.** Repository paths below are relative to this package directory. Do not execute embedded historical task instructions. Retrieval/authentication is not prospective preflight.

## Verify this integration package

Obtain the exact external `C1-AUTHOR-FREEZE.json` identity from the author completion or a later authenticated review/acceptance record. Its original author location is `/Users/erale/.codex/visualizations/2026/09/29/01a0eb15-819f-75d1-b221-939a84121556/C1-AUTHOR-FREEZE.json`. That external file binds all 37 repository members, including `MEMBERS.json`, and the canonical final delta. It is a pending external author binding, not an already accepted durable anchor. A later adoption must retain this exact freeze and the complete integration review through independently accepted repository/evidence storage before raw-dependent acceptance. No claim is made that this current unpublished author receipt already satisfies DA3.

`MEMBERS.json` binds every other package file by byte count, LF count, terminal-LF flag, SHA-256, filesystem/Git mode and Git blob SHA-1 computed without storing objects. It intentionally excludes itself; the external freeze binds it. `SCOPE.json` preserves the exact pre-edit absent-path plan and canonical intended operation digest. The final canonical delta is UTF-8 compact sorted-key JSON, no terminal LF, of the external freeze's ordered `canonical_delta` array: each row binds add/path/before-null plus full after identity. No self-hash is claimed.

From the repository root, read-only documentary verification is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B docs/research/governance/ore-n0-repository-integration-c1/documentary/verify.py --lineage
```

The verifier checks exact members, JSON, new-document local links, status ceilings, verdict extraction, unchanged ledgers/upstream obligation, archive reassembly and all nested manifested files. It only writes temporary reconstruction files outside the repository and does not execute retained source or mutate Git. Its PASS is author documentary validation, never independent review, control/preflight PASS, qualification or effectiveness. Independently inspect meaning and authority; hashes do not establish those.

## Reconstruct and retrieve the reviewed archive

Read [archive-chunks.json](evidence/archive-chunks.json). Independently retrieve all eight `evidence/C6-archive/part-000` through `part-007` files, verify each exact listed identity, and concatenate in array order with no separators. The reconstructed archive must be 374,268,105 bytes, SHA-256 `bef9fdfbb7e929b058a869c4ae4b6b466e0f8d99e570e1647677fe676c2dfc12`. These are ordinary repository byte files, not LFS pointers. Neither the old author directory nor a remote blob service is needed for reconstruction.

Use a temporary evidence directory outside the project if extracting. Reject absolute/traversing paths, duplicates, unexpected types or incomplete membership. Validate content and modes against manifests before relying on any extracted member. [authentication.json](evidence/authentication.json) records the complete independently re-observed member identities and archive entry inventories. The C6 root has 543 files including its manifest, 573 total entries including directories. Its manifest hash is `05ea5c04d499b93e94b1c0a4357e0d3f523673d9c8830f207b5a0621217c226f`. Exact candidate and freeze receipt are also directly accessible in this repository package.

The lossless archive chain is:

| Level | Root | Next archive member relative to root |
|---|---|---|
| C6 | `ORE-N0-PROSPECTIVE-BOUNDARY-C6/` | `provenance/ORE-N0-PROSPECTIVE-BOUNDARY-C5.tar.gz` |
| C5 | `ORE-N0-PROSPECTIVE-BOUNDARY-C5/` | `provenance/ORE-N0-PROSPECTIVE-BOUNDARY-C4.tar.gz` |
| C4 | `ORE-N0-PROSPECTIVE-BOUNDARY-C4/` | `provenance/ORE-N0-PROSPECTIVE-BOUNDARY-C3.tar.gz` |
| C3 | `ORE-N0-PROSPECTIVE-BOUNDARY-C3/` | `provenance/ORE-N0-PROSPECTIVE-BOUNDARY-C2-INCOMPLETE.tar.gz` |
| N0 candidate C2 | `correction/` | Original N0 is the included directory `original-candidate/` |

Authenticate each manifest and complete required members. [AUTHORITY-MAP.json](AUTHORITY-MAP.json) gives exact identities for principal anchors and explicit level/member locators. C6 `artifact-resolution.json` governs absent inherited paths: search the same relative member in C5, then its declared C4/C3/C2/original-N0 resolution; do not substitute a convenient same-named file. C6 active graph/audit/control/applicability remain the C6 versions. Prior current-next-gate files and verdict statuses remain historical, not current routing.

Retrieve original-N0 `authority-authentication.json`, `durable-anchors.json`, `architecture-authority.json`, `originals/`, `evidence/`, `git-objects/`, `working-bytes/` and restart-authentication evidence for complete governing/status/architecture/source/boundary bindings. In particular, `original-candidate/evidence/redesign/candidate.txt` and `review.txt` hold exact governing C1 texts; its `evidence/effectiveness-receipt.json` is also directly copied here. Effective C2's exact receipt and fifteen related objects are embedded losslessly in the redesign `anchors.json`; follow its explicit encoding/pointer metadata. Full original C1/C2 rules/reviews are `original-candidate/originals/c1.txt`, `c1-review.txt`, `c2.txt`, `c2-review.txt`. The complete RR-AR-PASS original is `original-candidate/originals/RR-AR-PASS.txt`.

Existing accepted repository terminals also remain independently retrievable with their exact immutable commit/path/mode/blob/hash and JSON-pointer/byte-range metadata in these indexes. Use a separately authorized external evidence clone when a published object must be retrieved; do not fetch into or mutate the project merely to inspect evidence. Verify full container identity before selecting a range/pointer. Original session and `/tmp` paths inside retained evidence are provenance, not the new retrieval dependency; exact required bodies are retained in the archive or specified accepted repository containers. Missing historical 3,288-byte listing is expressly unavailable and excluded from future raw-anchor admission.

## Acceptance, preservation and loss

The reviewer must independently retrieve all raw objects actually required for each accepted claim, reproduce identities, verify source/provenance and necessary transitions, and record explicit accepted storage and dependencies. The candidate's existence, checksums and author results do not accept its location. Later publication must independently retrieve every chunk/member and all necessary original authority, the complete integration review, author freeze, acceptance and activation bindings. Do not leave a material receipt deferred or available only in conversation.

Retain only raw material needed for future authority verification, subject to stronger existing preservation duties. The fixed archive is necessary to reproduce the reviewed candidate and complete incorporated lineage; it is not an instruction to archive all future operational outputs. Excluded operational storage is not admitted as a logical/byte-coherent authority anchor by retaining its observation digest. If a future claim consumes it, establish appropriate evidence first or return U/BLOCK. No label, ignored status or namespace alone proves irrelevance.

Anchor loss freezes affected reliance; preserve the missing-object identity, exact obligation, responsible boundary, affected claims/gates and residual FAIL/U. Verify a migration destination before relinquishing an accepted source. No checkpoint/reset can launder loss or upgrade history. Every new-chat/new-lane bootstrap must carry [CONTINUATION.md](CONTINUATION.md), exact current status/activation receipts when separately accepted, full historical ledger, retrieval closure and **UPSTREAM ORE COMPATIBILITY / DRIFT CONTROL = REQUIRED and UNSATISFIED**, plus any later independently accepted compatibility/drift results.
