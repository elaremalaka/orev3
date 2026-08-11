# RFC-012 Validation Dataset — 48 Hour Snapshot

## Dataset

RFC-012 Validation

## Snapshot Created

2026-08-11

## Collection Period

Approximately 48 hours

## Source

ORE Miner V3

RFC-012 implementation

## Observer

RFC-012 complete

Post-Version-1.0 RFC-012 implementation

## Purpose

This snapshot was archived as the first exploratory dataset following the
completion of RFC-012.

It is intended for discovery sessions and early research.

It is **not** intended to be the final effectiveness dataset.

## Dataset Files

- Local payload: `replay_dataset_v1.jsonl`
- Local metadata: `replay_dataset_v1.metadata.json`

The replay payload is a generated 227,867,665-byte artifact and is not an
ordinary Git commit candidate. Its machine-readable metadata also remains a
local research artifact because the payload is intentionally excluded from
source control. This README records the human-readable snapshot identity and
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

- Dataset build performance investigation (RB-001) still open.
- Long-running full dataset builds under investigation.

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

This is the first archived RFC-012 research dataset.

Next Snapshot

RFC-012 Validation — 1 Week

(To be created.)
