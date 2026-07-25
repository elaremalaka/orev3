from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pytest

from orev3.collection.tailer import (
    SourceChangedError,
    new_cursor,
    read_complete_lines,
)

from .conftest import snapshot


def test_clean_append_cursor_persistence_and_restart(source_file: Path) -> None:
    first = read_complete_lines(source_file, None, max_records=10)
    assert len(first.records) == 1
    with source_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot(observed_index=1)) + "\n")
    second = read_complete_lines(
        source_file, first.cursor, max_records=10
    )
    assert len(second.records) == 1
    assert second.cursor.line_number == 2
    assert read_complete_lines(
        source_file, second.cursor, max_records=10
    ).records == []


def test_partial_final_line_is_not_consumed(source_file: Path) -> None:
    first = read_complete_lines(source_file, None, max_records=10)
    raw = json.dumps(snapshot(observed_index=1))
    with source_file.open("ab") as handle:
        handle.write(raw[:20].encode())
    partial = read_complete_lines(
        source_file, first.cursor, max_records=10
    )
    assert partial.partial_final_line
    assert partial.cursor.byte_offset == first.cursor.byte_offset
    with source_file.open("ab") as handle:
        handle.write(raw[20:].encode() + b"\n")
    completed = read_complete_lines(
        source_file, partial.cursor, max_records=10
    )
    assert len(completed.records) == 1


def test_duplicate_malformed_and_out_of_order(tmp_path: Path) -> None:
    path = tmp_path / "mixed.jsonl"
    first = snapshot(observed_index=2)
    earlier = snapshot(observed_index=1)
    line = json.dumps(first)
    path.write_text(
        line + "\n" + line + "\n{bad}\n" + json.dumps(earlier) + "\n",
        encoding="utf-8",
    )
    result = read_complete_lines(path, None, max_records=10)
    assert len(result.records) == 2
    assert result.duplicate_records == 1
    assert result.malformed_records == 1
    assert result.records[-1].out_of_order


def test_truncation_and_replacement_are_rejected(source_file: Path) -> None:
    cursor = read_complete_lines(source_file, None, max_records=10).cursor
    source_file.write_text("", encoding="utf-8")
    with pytest.raises(SourceChangedError, match="truncated"):
        read_complete_lines(source_file, cursor, max_records=10)
    source_file.unlink()
    source_file.write_text(json.dumps(snapshot()) + "\n", encoding="utf-8")
    with pytest.raises(SourceChangedError, match="inode"):
        read_complete_lines(source_file, cursor, max_records=10)


def test_rotation_has_distinct_source_identity(tmp_path: Path) -> None:
    first = tmp_path / "observer_a.jsonl"
    second = tmp_path / "observer_b.jsonl"
    first.write_text(json.dumps(snapshot()) + "\n")
    second.write_text(json.dumps(snapshot(round_id=43)) + "\n")
    assert new_cursor(first).source_id != new_cursor(second).source_id


def test_reading_preserves_source_bytes(source_file: Path) -> None:
    before = hashlib.sha256(source_file.read_bytes()).hexdigest()
    read_complete_lines(source_file, None, max_records=10)
    after = hashlib.sha256(source_file.read_bytes()).hexdigest()
    assert before == after


def test_start_at_end_only_reads_future_append(source_file: Path) -> None:
    cursor = new_cursor(source_file, start_at_end=True)
    assert read_complete_lines(
        source_file, cursor, max_records=10
    ).records == []
    with source_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot(observed_index=1)) + "\n")
    assert len(
        read_complete_lines(source_file, cursor, max_records=10).records
    ) == 1


def test_start_at_end_retains_existing_partial_line(tmp_path: Path) -> None:
    path = tmp_path / "active.jsonl"
    complete = json.dumps(snapshot())
    partial = json.dumps(snapshot(observed_index=1))
    path.write_bytes((complete + "\n" + partial[:30]).encode())
    cursor = new_cursor(path, start_at_end=True)
    assert cursor.line_number == 1
    with path.open("ab") as handle:
        handle.write(partial[30:].encode() + b"\n")
    result = read_complete_lines(path, cursor, max_records=10)
    assert len(result.records) == 1
