# RFC-012 Validation Dataset — 48 Hour Snapshot

## Dataset

RFC-012 Validation

## Snapshot Created

2026-08-11

## Archive Checkpoint

Archived at the approximately 48-hour RFC-012 collection checkpoint.

## Naming Clarification

The name **RFC-012 Validation — 48 Hour** identifies the RFC-012 collection
checkpoint at which this dataset was archived. It does **not** mean that the
replay dataset contains only 48 hours of observations.

The replay dataset is cumulative. It spans the complete retained observation
history available to the Dataset Builder at the archive checkpoint, including
observations collected before RFC-012. The archived payload covers referenced
observations from `2026-07-23T04:47:51.776566Z` through
`2026-08-11T04:51:11.866288Z`.

## Source

ORE Miner V3

RFC-012 implementation

## Observer

RFC-012 complete

Post-Version-1.0 RFC-012 implementation

## Purpose

This dataset was archived as the first exploratory dataset following the
completion of RFC-012.

It is intended for discovery sessions and early research.

It is **not** intended to be the final effectiveness dataset.

## Dataset Files

- Local payload: `replay_dataset_v1.jsonl`
- Local metadata: `replay_dataset_v1.metadata.json`

The replay payload is a generated 227,867,665-byte artifact and is not an
ordinary Git commit candidate. Its machine-readable metadata also remains a
local research artifact because the payload is intentionally excluded from
source control. This README records the human-readable archive identity and
workflow. A separately approved artifact-storage workflow is required to
distribute the payload or its metadata.

## Dataset Identity

- Dataset version: `replay-dataset-v1`
- Metadata schema version: `2`
- Created at: `2026-08-11T04:50:44.880680+00:00`
- Replay rounds: `18,653`
- Snapshots: `1,390,766`
- Complete rounds: `17,912`
- Incomplete rounds: `741`
- Missing outcomes: `15,146`
- Integrity status: `valid`
- Dataset SHA-256:
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`

The local payload's computed SHA-256 matches the local metadata.

## Notes

- Observer was collecting normally.
- RFC-012 runtime integration active.
- Warning suppression for malformed historical records implemented.
- Dataset archived before any future dataset builds overwrite
  `data/derived/`.

## Known Issues

- The RB-001 performance investigation chain is complete. It concluded that
  the primary optimization path is a candidate architectural RFC; RFC-013 has
  been recommended but is not authorized.
- Dataset Builder progress reporting remains tracked separately as RB-002.

## Intended Research Use

This dataset will be used during:

- Discovery Session 1
- Candidate Research Question generation
- Early strategy exploration

The one-week validation dataset will be archived separately and will become
the primary dataset for formal RFC-012 effectiveness analysis.

---

## Research Lineage

Previous Snapshot

None

This is the first archived RFC-012 research dataset. It is cumulative through
the 48-hour RFC-012 collection checkpoint.

Next Snapshot

RFC-012 Validation — 1 Week

(To be created.)
