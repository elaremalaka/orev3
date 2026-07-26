from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import pytest

import orev3.rfc008.marker as marker_module
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.marker import (
    create_marker_pair,
    marker_preflight,
    sha256_file,
    verify_marker,
)
from orev3.rfc008.schemas import ExperimentMarker
from orev3.rfc008.storage import strict_json

from .conftest import CONFIG_PATH
from .test_preflight_release import (
    APPROVAL,
    NOW,
    RESOLVER_CONFIG,
    rewrite_burn,
    write_release_and_burn_in,
)


ROOT = CONFIG_PATH.parents[2]
BRANCH = "research/rfc-007-paper-collection-burn-in"
AUTHORIZATION = "RFC008_MARKER_CREATION_AUTHORIZED"


@contextmanager
def race_directory():
    with tempfile.TemporaryDirectory(
        prefix="rfc008-marker-race-",
        dir="/tmp",
    ) as name:
        yield Path(name)


def observer_record(round_id: int, observed_at) -> dict[str, object]:
    return {
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "rpc_slot": 500,
        "board": {
            "round_id": round_id,
            "start_slot": 400,
            "end_slot": 575,
        },
        "round": {
            "round_id": round_id,
            "miner_counts": [1] * 25,
            "deployed_lamports": [1] * 25,
            "rewards": [0] * 25,
            "total_vaulted": 0,
            "total_winnings": 0,
        },
    }


def append_record(source: Path, round_id: int, observed_at) -> None:
    with source.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(observer_record(round_id, observed_at)))
        handle.write("\n")


def fixed_repository() -> dict[str, object]:
    return {
        "commit": "a" * 40,
        "parent": "9" * 40,
        "branch": BRANCH,
        "tracked_clean": True,
        "untracked_clean": True,
    }


def build_environment(directory: Path, monkeypatch):
    source = directory / "observer.jsonl"
    for offset, round_id in enumerate(range(346001, 346006)):
        append_record(source, round_id, NOW + timedelta(seconds=offset))
    config = RFC008Config.from_path(CONFIG_PATH).model_copy(
        update={"source_glob": str(directory / "observer*.jsonl")}
    )
    config_path = directory / "config.json"
    config_path.write_text(strict_json(config) + "\n")
    resolver_path = directory / "resolver.json"
    resolver_path.write_bytes(RESOLVER_CONFIG.read_bytes())
    release, burn = write_release_and_burn_in(directory, config)
    boundary = marker_module._last_complete_record(source)

    def bind_boundary(value):
        value["source_boundary"] = {
            "round_id": boundary.round_id,
            "source_path": boundary.source_path,
            "inode": boundary.source_inode,
            "byte_offset": boundary.source_byte_offset,
            "line_number": boundary.source_line_number,
            "record_sha256": boundary.source_record_sha256,
            "record_timestamp": boundary.source_observed_at.isoformat(),
            "observed_at": (NOW + timedelta(seconds=5)).isoformat(),
        }
        value["operational"]["selection_boundary_round_id"] = (
            boundary.round_id
        )

    rewrite_burn(burn, bind_boundary)
    monkeypatch.setattr(
        "orev3.rfc008.marker.repository_state",
        lambda root: fixed_repository(),
    )
    return {
        "source": source,
        "config": config,
        "config_path": config_path,
        "resolver_path": resolver_path,
        "release": release,
        "burn": burn,
        "burn_ledger": burn.with_suffix(".sqlite"),
        "marker": directory / "marker.json",
        "ledger": directory / "production.sqlite",
        "boundary": boundary,
    }


def create(environment, **updates):
    arguments = {
        "config_path": environment["config_path"],
        "resolver_config_path": environment["resolver_path"],
        "burn_in_evidence_path": environment["burn"],
        "release_approval_path": environment["release"],
        "marker_path": environment["marker"],
        "ledger_path": environment["ledger"],
        "approval_manifest_path": APPROVAL,
        "repository_root": ROOT,
        "expected_branch": BRANCH,
        "authorization_token": AUTHORIZATION,
        "created_at": NOW + timedelta(seconds=6),
    }
    arguments.update(updates)
    return create_marker_pair(**arguments)


def test_append_after_preflight_publishes_historical_boundary(
    monkeypatch,
) -> None:
    with race_directory() as directory:
        environment = build_environment(directory, monkeypatch)
        real_preflight = marker_module.marker_preflight

        def append_after_preflight(**kwargs):
            result = real_preflight(**kwargs)
            assert result["ready"]
            assert result["burn_in_source_boundary_valid"]
            append_record(
                environment["source"],
                346006,
                NOW + timedelta(seconds=6),
            )
            return result

        monkeypatch.setattr(
            "orev3.rfc008.marker.marker_preflight",
            append_after_preflight,
        )
        marker, digest = create(environment)
        persisted = verify_marker(
            environment["marker"],
            environment["config"],
            expected_sha256=digest,
        )
        boundary = environment["boundary"]
        assert marker == persisted
        assert marker.marker_schema_version == 2
        assert marker.latest_preholdout_round_id == boundary.round_id
        assert marker.first_eligible_round_id == boundary.round_id + 1
        assert marker.runtime_source_path == boundary.source_path
        assert marker.runtime_source_inode == boundary.source_inode
        assert marker.runtime_source_byte_offset == boundary.source_byte_offset
        assert marker.runtime_source_line_number == boundary.source_line_number
        assert (
            marker.runtime_source_record_sha256
            == boundary.source_record_sha256
        )
        assert marker.runtime_source_observed_at == boundary.source_observed_at
        assert marker.burn_in_boundary_observed_at == NOW + timedelta(seconds=5)
        assert sha256_file(environment["marker"]) == digest
        assert not environment["ledger"].exists()


@pytest.mark.parametrize(
    "change",
    ("missing", "mutation", "truncation", "replacement"),
)
def test_historical_record_change_after_preflight_fails_closed(
    monkeypatch,
    change,
) -> None:
    with race_directory() as directory:
        environment = build_environment(directory, monkeypatch)
        real_preflight = marker_module.marker_preflight

        def change_after_preflight(**kwargs):
            result = real_preflight(**kwargs)
            assert result["ready"]
            source = environment["source"]
            if change == "missing":
                source.unlink()
            elif change == "mutation":
                raw = source.read_bytes()
                source.write_bytes(raw.replace(b"346005", b"346009", 1))
            elif change == "truncation":
                os.truncate(
                    source,
                    environment["boundary"].source_byte_offset - 1,
                )
            else:
                replacement = directory / "replacement.jsonl"
                replacement.write_bytes(source.read_bytes())
                os.replace(replacement, source)
            return result

        monkeypatch.setattr(
            "orev3.rfc008.marker.marker_preflight",
            change_after_preflight,
        )
        with pytest.raises(
            marker_module.HistoricalSourceBoundaryError
        ):
            create(environment)
        assert not environment["marker"].exists()
        assert not Path(str(environment["marker"]) + ".sha256").exists()


@pytest.mark.parametrize(
    ("mutate", "expected_check"),
    (
        (
            lambda value: value["source_boundary"].__setitem__(
                "source_path", "/tmp/outside-observer.jsonl"
            ),
            "historical_source_path_changed",
        ),
        (
            lambda value: value["source_boundary"].__setitem__(
                "round_id", 346006
            ),
            "source_boundary_selection_mismatch",
        ),
        (
            lambda value: value["source_boundary"].__setitem__(
                "record_sha256", "0" * 64
            ),
            "historical_source_record_changed",
        ),
        (
            lambda value: value["source_boundary"].__setitem__(
                "line_number", 4
            ),
            "historical_source_record_offset_changed",
        ),
        (
            lambda value: value["source_boundary"].__setitem__(
                "byte_offset", value["source_boundary"]["byte_offset"] - 1
            ),
            "historical_source_record_offset_changed",
        ),
        (
            lambda value: value["source_boundary"].__setitem__(
                "record_timestamp",
                (NOW + timedelta(seconds=30)).isoformat(),
            ),
            "historical_source_timestamp_changed",
        ),
        (
            lambda value: value["operational"]["selected_round_ids"].__setitem__(
                0, 345999
            ),
            "source_boundary_selection_mismatch",
        ),
    ),
)
def test_boundary_field_mutations_fail_preflight(
    monkeypatch,
    mutate,
    expected_check,
) -> None:
    with race_directory() as directory:
        environment = build_environment(directory, monkeypatch)
        rewrite_burn(environment["burn"], mutate)
        result = marker_preflight(
            config_path=environment["config_path"],
            resolver_config_path=environment["resolver_path"],
            burn_in_evidence_path=environment["burn"],
            release_approval_path=environment["release"],
            marker_path=environment["marker"],
            ledger_path=environment["ledger"],
            approval_manifest_path=APPROVAL,
            repository_root=ROOT,
            expected_branch=BRANCH,
            now=NOW + timedelta(seconds=6),
        )
        checks = {failure["check"] for failure in result["failures"]}
        assert not result["ready"]
        assert expected_check in checks
        assert not environment["marker"].exists()


@pytest.mark.parametrize(
    ("change", "message"),
    (
        ("evidence", "Burn-in evidence changed"),
        ("ledger", "Burn-in ledger changed"),
        ("approval", "Release approval changed"),
        ("resolver", "Resolver configuration changed"),
        ("repository", "Repository state changed"),
    ),
)
def test_publication_inputs_changing_after_preflight_fail_closed(
    monkeypatch,
    change,
    message,
) -> None:
    with race_directory() as directory:
        environment = build_environment(directory, monkeypatch)
        real_preflight = marker_module.marker_preflight

        def change_after_preflight(**kwargs):
            result = real_preflight(**kwargs)
            assert result["ready"]
            if change == "evidence":
                environment["burn"].write_bytes(
                    environment["burn"].read_bytes() + b" "
                )
            elif change == "ledger":
                environment["burn_ledger"].write_bytes(
                    environment["burn_ledger"].read_bytes() + b" "
                )
            elif change == "approval":
                environment["release"].write_bytes(
                    environment["release"].read_bytes() + b" "
                )
            elif change == "resolver":
                value = json.loads(
                    environment["resolver_path"].read_text()
                )
                value["base_retry_seconds"] += 1
                environment["resolver_path"].write_text(
                    json.dumps(value)
                )
            return result

        monkeypatch.setattr(
            "orev3.rfc008.marker.marker_preflight",
            change_after_preflight,
        )
        if change == "repository":
            calls = 0

            def changing_repository(root):
                nonlocal calls
                calls += 1
                value = fixed_repository()
                if calls > 1:
                    value["tracked_clean"] = False
                return value

            monkeypatch.setattr(
                "orev3.rfc008.marker.repository_state",
                changing_repository,
            )
        with pytest.raises(ValueError, match=message):
            create(environment)
        assert not environment["marker"].exists()


@pytest.mark.parametrize(
    "race",
    ("marker", "sidecar", "ledger"),
)
def test_publication_path_races_fail_without_overwrite(
    monkeypatch,
    race,
) -> None:
    with race_directory() as directory:
        environment = build_environment(directory, monkeypatch)
        sidecar = Path(str(environment["marker"]) + ".sha256")
        protected = b"preexisting"

        def inject(point):
            if race == "marker" and point == "between_sidecar_and_marker":
                environment["marker"].write_bytes(protected)
            elif race == "sidecar" and point == "before_publish":
                sidecar.write_bytes(protected)
            elif race == "ledger" and point == "before_publish":
                environment["ledger"].write_bytes(protected)

        with pytest.raises(FileExistsError):
            create(environment, failure_injector=inject)
        if race == "marker":
            assert environment["marker"].read_bytes() == protected
            assert not sidecar.exists()
        elif race == "sidecar":
            assert sidecar.read_bytes() == protected
            assert not environment["marker"].exists()
        else:
            assert environment["ledger"].read_bytes() == protected
            assert not environment["marker"].exists()
            assert not sidecar.exists()
        assert not list(directory.glob(".*.tmp"))


def test_temporary_marker_has_no_collection_side_effects(monkeypatch) -> None:
    with race_directory() as directory:
        environment = build_environment(directory, monkeypatch)
        marker, digest = create(environment)
        persisted = ExperimentMarker.model_validate_json(
            environment["marker"].read_text()
        )
        assert marker == persisted
        assert persisted.collection_authorized is False
        assert (
            persisted.start_conditions[
                "collection_requires_separate_authorization"
            ]
            is True
        )
        assert sha256_file(environment["marker"]) == digest
        assert not environment["ledger"].exists()
        assert not (ROOT / "data/ledger/rfc008_marker_v1.json").exists()
        assert not (
            ROOT / "data/ledger/rfc008_marker_v1.json.sha256"
        ).exists()
        assert not (
            ROOT / "data/ledger/rfc008_paper_ledger_v1.sqlite"
        ).exists()
