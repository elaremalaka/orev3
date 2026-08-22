from __future__ import annotations

import hashlib
import os
import stat
from types import SimpleNamespace
from pathlib import Path

import pytest

from orev3.execution.canonical import parse_json, validate_json_schema_instance
from orev3.execution.external_inputs import InputSnapshotError, ResourceLimits, snapshot_declared_input, snapshot_regular_file
from orev3.execution.projection import project_jsonl
from orev3.execution.dataset_validation import publish_projection
from orev3.execution.filesystem_capability import open_pinned_regular


LIMITS = ResourceLimits(1024 * 1024, 8, 2 * 1024 * 1024, 2 * 1024 * 1024, 100, 30, 65536, 65536, 4 * 1024 * 1024)


def test_final_immutable_snapshot_is_rehashed_and_identity_bound(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"; source.write_bytes(b'{"x":1}\n')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    declaration = {"external_input_identifier": "synthetic", "input_kind": "regular_file", "members": [{"byte_count": 8, "logical_identifier": "only", "member_path": "input", "sha256": digest}]}
    snapshot = snapshot_declared_input(declaration, locator_paths={"input": source}, object_store=tmp_path / "objects", limits=LIMITS)
    assert snapshot.material["input_snapshot_identity"] == snapshot.identity
    assert snapshot.members[0].content_object.read_bytes() == b'{"x":1}\n'
    schema = parse_json(Path("src/orev3/execution/schemas/v1/immutable-input-snapshot.schema.json").read_bytes())
    validate_json_schema_instance(snapshot.material, schema, schema_registry={})
    source.write_bytes(b"changed")
    assert snapshot.members[0].content_object.read_bytes() == b'{"x":1}\n'


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink"])
def test_unsafe_leaf_is_rejected(tmp_path: Path, unsafe: str) -> None:
    original = tmp_path / "original"; original.write_bytes(b"x")
    leaf = tmp_path / "leaf"
    if unsafe == "symlink": leaf.symlink_to(original)
    else: os.link(original, leaf)
    with pytest.raises(InputSnapshotError, match="INPUT_UNSAFE_TYPE"):
        snapshot_regular_file(leaf, logical_identifier="x", declared_byte_count=1, declared_sha256=hashlib.sha256(b"x").hexdigest(), object_store=tmp_path / "store", max_file_bytes=10)


def test_declared_mismatch_and_duplicate_collection_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "x"; source.write_bytes(b"x")
    declaration = {"external_input_identifier": "synthetic", "input_kind": "ordered_file_collection", "members": [{"byte_count": 1, "logical_identifier": "same", "member_path": "x", "sha256": hashlib.sha256(b"x").hexdigest()}, {"byte_count": 1, "logical_identifier": "same", "member_path": "y", "sha256": hashlib.sha256(b"x").hexdigest()}]}
    with pytest.raises(InputSnapshotError, match="duplicate collection member"):
        snapshot_declared_input(declaration, locator_paths={"x": source, "y": source}, object_store=tmp_path / "store", limits=LIMITS)
    with pytest.raises(InputSnapshotError, match="INPUT_MISMATCH"):
        snapshot_regular_file(source, logical_identifier="x", declared_byte_count=2, declared_sha256=hashlib.sha256(b"x").hexdigest(), object_store=tmp_path / "store2", max_file_bytes=10)


def test_mutation_during_copy_is_rejected_before_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import orev3.execution.filesystem_capability as module
    source = tmp_path / "source"; source.write_bytes(b"stable")
    actual = os.fstat; regular_calls = 0
    def changed(descriptor: int):
        nonlocal regular_calls
        value = actual(descriptor)
        if stat.S_ISREG(value.st_mode):
            regular_calls += 1
        if regular_calls == 3:
            return SimpleNamespace(st_mode=value.st_mode, st_nlink=value.st_nlink, st_dev=value.st_dev, st_ino=value.st_ino, st_size=value.st_size, st_mtime_ns=value.st_mtime_ns + 1, st_ctime_ns=value.st_ctime_ns)
        return value
    monkeypatch.setattr(module.os, "fstat", changed)
    with pytest.raises(InputSnapshotError, match="INPUT_MUTATED"):
        snapshot_regular_file(source, logical_identifier="x", declared_byte_count=6, declared_sha256=hashlib.sha256(b"stable").hexdigest(), object_store=tmp_path / "store", max_file_bytes=10)
    assert not (tmp_path / "store" / hashlib.sha256(b"stable").hexdigest()).exists()


def test_directory_and_fifo_are_rejected_without_reading(tmp_path: Path) -> None:
    directory = tmp_path / "directory"; directory.mkdir()
    fifo = tmp_path / "fifo"; os.mkfifo(fifo)
    for candidate in (directory, fifo):
        with pytest.raises(InputSnapshotError, match="INPUT_UNSAFE_TYPE"):
            snapshot_regular_file(candidate, logical_identifier="x", declared_byte_count=0, declared_sha256=hashlib.sha256(b"").hexdigest(), object_store=tmp_path / "store", max_file_bytes=10)


def test_intermediate_symlink_and_preexisting_unsafe_objects_reject(tmp_path: Path) -> None:
    real = tmp_path / "real"; real.mkdir(); source = real / "source"; source.write_bytes(b"x")
    alias = tmp_path / "alias"; alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(InputSnapshotError, match="symlink component"):
        snapshot_regular_file(alias / "source", logical_identifier="x", declared_byte_count=1, declared_sha256=hashlib.sha256(b"x").hexdigest(), object_store=tmp_path / "store", max_file_bytes=10)
    store = tmp_path / "objects"; store.mkdir(); digest = hashlib.sha256(b"x").hexdigest()
    outside = tmp_path / "outside"; outside.write_bytes(b"x")
    (store / digest).symlink_to(outside)
    with pytest.raises(InputSnapshotError, match="collision"):
        snapshot_regular_file(source, logical_identifier="x", declared_byte_count=1, declared_sha256=digest, object_store=store, max_file_bytes=10)


def test_consumer_rejects_replaced_or_hardlinked_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source"; source.write_bytes(b'{"x":1}\n')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    member = snapshot_regular_file(source, logical_identifier="x", declared_byte_count=8, declared_sha256=digest, object_store=tmp_path / "store", max_file_bytes=100)
    member.content_object.chmod(0o600); member.content_object.unlink(); member.content_object.write_bytes(b'{"x":2}\n')
    schema = {"additionalProperties": False, "properties": {"x": {"type": "integer"}}, "required": ["x"], "type": "object"}
    with pytest.raises(Exception, match="INPUT_MISMATCH"):
        project_jsonl(member.content_object, raw_schema=schema, projection_schema=schema, expected_raw_sha256=digest, expected_raw_size=8, max_raw_bytes=100, max_projection_bytes=100, max_records=2)
    member.content_object.unlink(); member.content_object.write_bytes(b'{"x":1}\n'); second = tmp_path / "second"; os.link(member.content_object, second)
    with pytest.raises(Exception, match="INPUT_MISMATCH"):
        project_jsonl(member.content_object, raw_schema=schema, projection_schema=schema, expected_raw_sha256=digest, expected_raw_size=8, max_raw_bytes=100, max_projection_bytes=100, max_records=2)


def test_intermediate_substitution_is_descriptor_pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import orev3.execution.filesystem_capability as capability
    original_directory = tmp_path / "source-directory"
    replacement_directory = tmp_path / "replacement-directory"
    original_directory.mkdir(); replacement_directory.mkdir()
    (original_directory / "input").write_bytes(b"A")
    (replacement_directory / "input").write_bytes(b"B")
    actual_open = capability.os.open
    swapped = False

    def racing_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal swapped
        descriptor = actual_open(path, flags, *args, **kwargs)
        if path == original_directory.name and not swapped:
            swapped = True
            original_directory.rename(tmp_path / "pinned-original")
            original_directory.symlink_to(replacement_directory, target_is_directory=True)
        return descriptor

    monkeypatch.setattr(capability.os, "open", racing_open)
    member = snapshot_regular_file(
        original_directory / "input",
        logical_identifier="x",
        declared_byte_count=1,
        declared_sha256=hashlib.sha256(b"A").hexdigest(),
        object_store=tmp_path / "store",
        max_file_bytes=10,
    )
    assert swapped
    assert member.content_object.read_bytes() == b"A"


def test_deleted_recreated_parent_cannot_redirect_pinned_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import orev3.execution.filesystem_capability as capability
    original_directory = tmp_path / "source-directory"
    original_directory.mkdir()
    (original_directory / "input").write_bytes(b"A")
    actual_open = capability.os.open
    replaced = False

    def racing_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal replaced
        descriptor = actual_open(path, flags, *args, **kwargs)
        if path == original_directory.name and not replaced:
            replaced = True
            original_directory.rename(tmp_path / "pinned-original")
            original_directory.mkdir()
            (original_directory / "input").write_bytes(b"B")
        return descriptor

    monkeypatch.setattr(capability.os, "open", racing_open)
    member = snapshot_regular_file(
        original_directory / "input",
        logical_identifier="x",
        declared_byte_count=1,
        declared_sha256=hashlib.sha256(b"A").hexdigest(),
        object_store=tmp_path / "store",
        max_file_bytes=10,
    )
    assert replaced
    assert member.content_object.read_bytes() == b"A"
    assert (original_directory / "input").read_bytes() == b"B"


def test_leaf_substitution_before_open_rejects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import orev3.execution.filesystem_capability as capability
    parent = tmp_path / "source"; parent.mkdir()
    leaf = parent / "input"; leaf.write_bytes(b"A")
    replacement = tmp_path / "replacement"; replacement.write_bytes(b"B")
    actual_open = capability.os.open
    swapped = False

    def racing_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal swapped
        if path == leaf.name and not swapped:
            swapped = True
            leaf.unlink(); leaf.symlink_to(replacement)
        return actual_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(capability.os, "open", racing_open)
    with pytest.raises(InputSnapshotError, match="INPUT_UNSAFE_TYPE"):
        snapshot_regular_file(leaf, logical_identifier="x", declared_byte_count=1, declared_sha256=hashlib.sha256(b"A").hexdigest(), object_store=tmp_path / "store", max_file_bytes=10)


def test_leaf_replacement_after_open_rejects_link_policy_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import orev3.execution.filesystem_capability as capability
    parent = tmp_path / "source"; parent.mkdir()
    leaf = parent / "input"; leaf.write_bytes(b"A")
    actual_open = capability.os.open
    swapped = False

    def racing_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal swapped
        descriptor = actual_open(path, flags, *args, **kwargs)
        if path == leaf.name and not swapped:
            swapped = True
            leaf.unlink(); leaf.write_bytes(b"B")
        return descriptor

    monkeypatch.setattr(capability.os, "open", racing_open)
    with pytest.raises(InputSnapshotError, match="INPUT_UNSAFE_TYPE"):
        snapshot_regular_file(leaf, logical_identifier="x", declared_byte_count=1, declared_sha256=hashlib.sha256(b"A").hexdigest(), object_store=tmp_path / "store", max_file_bytes=10)
    assert swapped and leaf.read_bytes() == b"B"


def test_store_substitution_cannot_redirect_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import orev3.execution.filesystem_capability as capability
    store = tmp_path / "store"; store.mkdir()
    attacker = tmp_path / "attacker"; attacker.mkdir()
    actual_open = capability.os.open
    swapped = False

    def racing_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal swapped
        descriptor = actual_open(path, flags, *args, **kwargs)
        if path == store.name and not swapped:
            swapped = True
            store.rename(tmp_path / "pinned-store")
            store.symlink_to(attacker, target_is_directory=True)
        return descriptor

    monkeypatch.setattr(capability.os, "open", racing_open)
    payload = b"projection"
    publish_projection(payload, store=store, expected_sha256=hashlib.sha256(payload).hexdigest())
    assert swapped
    assert not any(attacker.iterdir())
    assert (tmp_path / "pinned-store" / hashlib.sha256(payload).hexdigest()).read_bytes() == payload


@pytest.mark.parametrize(
    "raw",
    (
        "relative/input",
        "/tmp/../input",
        "/tmp/./input",
        "/tmp//input",
        "/tmp/input/",
    ),
)
def test_v1_locator_grammar_rejects_ambiguous_paths(raw: str) -> None:
    with pytest.raises(Exception):
        open_pinned_regular(raw, error_code="INPUT_UNSAFE_TYPE")


def test_v1_locator_grammar_accepts_absolute_unicode_path(tmp_path: Path) -> None:
    candidate = tmp_path / "café-資料"
    candidate.write_bytes(b"x")
    descriptor, _ = open_pinned_regular(candidate, error_code="INPUT_UNSAFE_TYPE")
    try:
        assert os.read(descriptor, 1) == b"x"
    finally:
        os.close(descriptor)
