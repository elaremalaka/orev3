from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any


NAMESPACE = uuid.UUID("4ba9dff3-f946-5a35-b966-0ad8d84c594d")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def deterministic_id(kind: str, *parts: object) -> str:
    material = canonical_json(
        {"kind": kind, "parts": [str(part) for part in parts]}
    )
    return str(uuid.uuid5(NAMESPACE, material))


def opportunity_id(round_id: int, observation_index: int) -> str:
    return deterministic_id("opportunity", round_id, observation_index)


def source_record_id(source_name: str, line_number: int, raw: Any) -> str:
    digest = hashlib.sha256(canonical_json(raw).encode("utf-8")).hexdigest()
    return deterministic_id("source-record", source_name, line_number, digest)


def event_id(
    event_type: str,
    source: str,
    source_id: str,
) -> str:
    return deterministic_id("event", event_type, source, source_id)


def new_run_id() -> str:
    """Runs and sessions are intentionally generated UUIDs."""
    return str(uuid.uuid4())
