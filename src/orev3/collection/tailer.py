from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from orev3.collection.schemas import SourceCursor, TailBatch, TailRecord
from orev3.ledger.identifiers import deterministic_id


class SourceChangedError(RuntimeError):
    pass


def new_cursor(path: str | Path, *, start_at_end: bool = False) -> SourceCursor:
    source = Path(path)
    stat = source.stat()
    byte_offset = 0
    line_number = 0
    if start_at_end:
        position = 0
        last_complete_offset = 0
        with source.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                line_number += chunk.count(b"\n")
                last_newline = chunk.rfind(b"\n")
                if last_newline >= 0:
                    last_complete_offset = position + last_newline + 1
                position += len(chunk)
        # Retain any in-progress final record so its later completion is read.
        byte_offset = last_complete_offset
    return SourceCursor(
        source_id=deterministic_id("collection-source", str(source.resolve())),
        source_path=str(source),
        byte_offset=byte_offset,
        line_number=line_number,
        source_size=stat.st_size,
        source_inode=stat.st_ino,
    )


def read_complete_lines(
    path: str | Path,
    cursor: SourceCursor | None,
    *,
    max_records: int,
    seen_content_hashes: set[str] | None = None,
    ingested_at: datetime | None = None,
    start_at_end: bool = False,
) -> TailBatch:
    source = Path(path)
    stat = source.stat()
    current = cursor or new_cursor(source, start_at_end=start_at_end)
    if stat.st_ino != current.source_inode:
        raise SourceChangedError("Observer source inode changed; manual review required")
    if stat.st_size < current.byte_offset:
        raise SourceChangedError("Observer source was truncated; cursor not reset")
    seen = seen_content_hashes if seen_content_hashes is not None else set()
    records: list[TailRecord] = []
    malformed = 0
    duplicates = 0
    offset = current.byte_offset
    line_number = current.line_number
    last_timestamp = current.last_observed_timestamp
    last_record_id = current.last_record_id
    partial = False
    now = ingested_at or datetime.now(timezone.utc)
    with source.open("rb") as handle:
        handle.seek(offset)
        while len(records) < max_records:
            start = handle.tell()
            line = handle.readline()
            if not line:
                break
            if not line.endswith(b"\n"):
                partial = True
                handle.seek(start)
                break
            offset = handle.tell()
            line_number += 1
            try:
                raw = json.loads(line)
                observed_at = datetime.fromisoformat(
                    str(raw["observed_at_utc"]).replace("Z", "+00:00")
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                malformed += 1
                continue
            content_hash = hashlib.sha256(line.rstrip(b"\n")).hexdigest()
            record_id = deterministic_id(
                "tail-record", current.source_id, line_number, content_hash
            )
            if content_hash in seen:
                duplicates += 1
                continue
            seen.add(content_hash)
            out_of_order = (
                last_timestamp is not None and observed_at < last_timestamp
            )
            records.append(
                TailRecord(
                    source_id=current.source_id,
                    source_path=str(source),
                    source_line_number=line_number,
                    start_offset=start,
                    end_offset=offset,
                    record_id=record_id,
                    content_sha256=content_hash,
                    observed_at=observed_at,
                    raw=raw,
                    out_of_order=out_of_order,
                )
            )
            last_timestamp = max(last_timestamp, observed_at) if last_timestamp else observed_at
            last_record_id = record_id
    updated_stat = source.stat()
    updated = current.model_copy(
        update={
            "byte_offset": offset,
            "line_number": line_number,
            "last_record_id": last_record_id,
            "last_observed_timestamp": last_timestamp,
            "last_ingested_at": now if records or malformed or duplicates else current.last_ingested_at,
            "source_size": updated_stat.st_size,
        }
    )
    return TailBatch(
        records=records,
        cursor=updated,
        malformed_records=malformed,
        duplicate_records=duplicates,
        partial_final_line=partial,
    )
