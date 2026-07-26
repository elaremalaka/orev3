from __future__ import annotations

import sqlite3

import pytest

from orev3.rfc008.migrations import (
    APPLICATION_ID,
    MIGRATIONS,
    Migration,
    apply_migrations,
)
from orev3.rfc008.storage import RFC008Store


def test_foreign_empty_and_partial_databases_fail_closed(tmp_path, config):
    foreign = tmp_path / "foreign.sqlite"
    sqlite3.connect(foreign).close()
    with pytest.raises(ValueError, match="database application"):
        RFC008Store(foreign, read_only=True)

    partial = tmp_path / "partial.sqlite"
    connection = sqlite3.connect(partial)
    connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
    connection.execute("CREATE TABLE unrelated(value TEXT)")
    connection.commit()
    connection.close()
    with pytest.raises(ValueError):
        RFC008Store(partial, config=config, read_only=True)


def test_rfc007_shape_is_rejected_even_without_configuration(tmp_path):
    path = tmp_path / "renamed.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)")
    connection.executemany(
        "INSERT INTO metadata VALUES (?,?)",
        (("schema_version", "1"), ("experiment_id", "rfc007")),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="database application"):
        RFC008Store(path, read_only=True)


def test_migrations_are_ordered_idempotent_and_checksum_locked():
    connection = sqlite3.connect(":memory:")
    apply_migrations(connection)
    apply_migrations(connection)
    assert connection.execute(
        "SELECT COUNT(*) FROM schema_migrations"
    ).fetchone()[0] == len(MIGRATIONS)
    altered = (
        Migration(
            1,
            MIGRATIONS[0].name,
            MIGRATIONS[0].statements + ("CREATE TABLE altered(value TEXT)",),
        ),
        *MIGRATIONS[1:],
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        apply_migrations(connection, altered)
    with pytest.raises(ValueError, match="contiguous"):
        apply_migrations(
            sqlite3.connect(":memory:"),
            (Migration(2, "skipped", ("CREATE TABLE x(v)",)),),
        )


def test_additive_test_migration_and_transactional_rollback():
    connection = sqlite3.connect(":memory:")
    base = Migration(1, "base", ("CREATE TABLE alpha(value INTEGER)",))
    additive = Migration(
        2, "additive", ("ALTER TABLE alpha ADD COLUMN note TEXT",)
    )
    apply_migrations(connection, (base, additive))
    assert [row[1] for row in connection.execute("PRAGMA table_info(alpha)")] == [
        "value",
        "note",
    ]

    failed_connection = sqlite3.connect(":memory:")
    failing = Migration(
        2,
        "failing",
        (
            "CREATE TABLE beta(value INTEGER)",
            "INSERT INTO table_that_does_not_exist VALUES (1)",
        ),
    )
    with pytest.raises(sqlite3.OperationalError):
        apply_migrations(failed_connection, (base, failing))
    assert failed_connection.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name='beta'"
    ).fetchone()[0] == 0
    assert failed_connection.execute(
        "SELECT COUNT(*) FROM schema_migrations"
    ).fetchone()[0] == 1
