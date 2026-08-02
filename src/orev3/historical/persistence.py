from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from orev3.historical.models import (
    ObservationReference,
    RoundLifecycle,
    RoundLifecycleIndexRecord,
)


def lifecycle_to_index_record(
    lifecycle: RoundLifecycle,
) -> RoundLifecycleIndexRecord:
    """
    Convert an in-memory RoundLifecycle into a compact
    persistent record.

    Raw snapshot bodies are not duplicated.
    """

    references = [
        ObservationReference(
            source_file=(
                snapshot.source_file
            ),
            source_line_number=(
                snapshot.source_line_number
            ),
            observed_at_utc=(
                snapshot.observed_at_utc
            ),
            rpc_slot=(
                snapshot.rpc_slot
            ),
        )
        for snapshot
        in lifecycle.observation_history
    ]

    return RoundLifecycleIndexRecord(
        round_id=lifecycle.round_id,
        start_slot=lifecycle.start_slot,
        end_slot=lifecycle.end_slot,
        first_observed_at_utc=(
            lifecycle.first_observed_at_utc
        ),
        last_observed_at_utc=(
            lifecycle.last_observed_at_utc
        ),
        first_observed_rpc_slot=(
            lifecycle.first_observed_rpc_slot
        ),
        last_observed_rpc_slot=(
            lifecycle.last_observed_rpc_slot
        ),
        observation_count=(
            lifecycle.observation_count
        ),
        collector_session_ids=(
            lifecycle.collector_session_ids
        ),
        source_schema_versions=(
            lifecycle.source_schema_versions
        ),
        source_files=(
            lifecycle.source_files
        ),
        observation_references=(
            references
        ),
        finalized_outcome=(
            lifecycle.finalized_outcome
        ),
        finalized_outcome_source=(
            lifecycle.finalized_outcome_source
        ),
        finalized_outcome_capture_mode=(
            lifecycle.finalized_outcome_capture_mode
        ),
        finalized_outcome_evidence_identities=(
            lifecycle.finalized_outcome_evidence_identities
        ),
        quality=lifecycle.quality,
    )


def write_round_index(
    records: list[
        RoundLifecycleIndexRecord
    ],
    output_path: str | Path,
) -> Path:
    """
    Atomically replace a reproducible derived JSONL index.

    Raw Observer files remain untouched.
    """

    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temp_name = tempfile.mkstemp(
        prefix=(
            path.name + "."
        ),
        suffix=".tmp",
        dir=path.parent,
    )

    temp_path = Path(
        temp_name
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            for record in records:
                handle.write(
                    record.model_dump_json()
                )
                handle.write(
                    "\n"
                )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temp_path,
            path,
        )

    except Exception:
        try:
            temp_path.unlink(
                missing_ok=True
            )
        finally:
            raise

    return path


def write_manifest(
    manifest,
    output_path: str | Path,
) -> Path:
    """
    Atomically write the dataset build manifest.
    """

    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    temp_path.write_text(
        manifest.model_dump_json(
            indent=2
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temp_path,
        path,
    )

    return path
