from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from orev3.ledger.identifiers import canonical_json
from orev3.rfc008.config import FrozenModel


class ResolverConfig(FrozenModel):
    schema_version: Literal[1] = 1
    resolver_version: Literal["rfc008-finalized-resolver-v1"]
    decoder_version: Literal["ore-round-decoder-v1"]
    commitment: Literal["finalized"]
    network: Literal["solana-mainnet"]
    expected_genesis_hash: str
    expected_program_owner: str
    provider_ids: tuple[str, ...]
    provider_url_environment_variables: tuple[str, ...]
    minimum_provider_count: Literal[2] = 2
    base_retry_seconds: int = Field(ge=1)
    maximum_retry_seconds: int = Field(ge=1, le=300)
    jitter_modulus_seconds: int = Field(ge=1, le=30)
    quarantine_after_seconds: int = Field(ge=1)
    burn_in_maximum_age_seconds: int = Field(ge=1)
    resolver_schema_version: Literal[1] = 1
    paper_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_provider_configuration(self):
        if len(self.provider_ids) != self.minimum_provider_count:
            raise ValueError("RFC-008 requires exactly two outcome providers")
        if len(set(self.provider_ids)) != len(self.provider_ids):
            raise ValueError("Outcome provider identities must be unique")
        if len(self.provider_url_environment_variables) != len(
            self.provider_ids
        ):
            raise ValueError("Each provider requires one environment variable")
        if self.maximum_retry_seconds < self.base_retry_seconds:
            raise ValueError("Maximum retry must not be below base retry")
        return self

    @classmethod
    def from_path(cls, path: str | Path) -> "ResolverConfig":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    @property
    def fingerprint(self) -> str:
        payload = canonical_json(self.model_dump(mode="json")).encode()
        return hashlib.sha256(payload).hexdigest()
