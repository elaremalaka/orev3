from __future__ import annotations

import inspect
import ast
import hashlib
import subprocess
from pathlib import Path

import pytest

from orev3.execution.git_state import (
    GitAuthorityError,
    GitDiagnosticCode,
    GitRepository,
    RequiredCommittedObject,
    SourceCandidateRequirements,
    inspect_committed_requirements,
)
from orev3.execution.readiness import resolve_git_launch_authority


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("commit", "protocol_path", "implementation_path"),
    (
        (
            "3ba070ba3c2173d63df690054c4c91957b640db9",
            "docs/research/experiments/rq003-experiment-002d-share-imbalance-characterization.md",
            "src/orev3/experiments/rq003_experiment2d.py",
        ),
        (
            "d06734d715ff85aa6e35d373b6bc6d8854425615",
            "docs/research/experiments/rq003-experiment-003-miner-count-predictive-evaluation.md",
            "src/orev3/experiments/rq003_experiment3.py",
        ),
        (
            "ca1e3f722a246b70d61f1b6705a8bbc2806ad416",
            "docs/research/experiments/rq003-experiment-004-deployment-per-miner-predictive-evaluation.md",
            "src/orev3/experiments/rq003_experiment4.py",
        ),
    ),
)
def test_historical_implementation_commits_cannot_satisfy_required_protocol(
    commit: str, protocol_path: str, implementation_path: str
) -> None:
    requirements = SourceCandidateRequirements(
        "historical-regression",
        (
            RequiredCommittedObject(implementation_path),
            RequiredCommittedObject(protocol_path),
        ),
        (
            (protocol_path, "protocol", "top_level", ""),
            ("src/orev3", "source_tree", "top_level", ""),
        ),
    )
    with pytest.raises(GitAuthorityError) as error:
        inspect_committed_requirements(GitRepository(ROOT), commit, requirements)
    assert error.value.code == GitDiagnosticCode.OBJECT_NOT_FOUND
    assert error.value.repository_path == protocol_path


def test_experiment4_coherent_commit_passes_only_source_protocol_inspection() -> None:
    protocol = "docs/research/experiments/rq003-experiment-004-deployment-per-miner-predictive-evaluation.md"
    requirements = SourceCandidateRequirements(
        "rq003-experiment-004",
        (
            RequiredCommittedObject("src/orev3/experiments/rq003_experiment4.py"),
            RequiredCommittedObject(
                protocol,
                "356f7b2c2d9e24520983e9f692675f6f6c432b7741ce1066a29b6f11b9d407b5",
            ),
            RequiredCommittedObject(
                "docs/research/specifications/rq003-research-execution-specification-v2.md"
            ),
        ),
        (
            (protocol, "protocol", "top_level", ""),
            (
                "docs/research/specifications/rq003-research-execution-specification-v2.md",
                "execution_specification",
                "top_level",
                "",
            ),
            ("src/orev3", "source_tree", "top_level", ""),
        ),
    )
    scopes = inspect_committed_requirements(
        GitRepository(ROOT),
        "c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd",
        requirements,
    )
    assert {scope.repository_path for scope in scopes} == {
        protocol,
        "docs/research/specifications/rq003-research-execution-specification-v2.md",
        "src/orev3",
    }
    assert all("readiness" not in scope.repository_path for scope in scopes)


def test_experiment4_coherent_commit_has_exact_protocol_binding() -> None:
    commit = "c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd"
    implementation_path = "src/orev3/experiments/rq003_experiment4.py"
    protocol_path = "docs/research/experiments/rq003-experiment-004-deployment-per-miner-predictive-evaluation.md"
    implementation = subprocess.run(
        ("git", "show", f"{commit}:{implementation_path}"),
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    protocol = subprocess.run(
        ("git", "show", f"{commit}:{protocol_path}"),
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assignments: dict[str, str] = {}
    for node in ast.parse(implementation).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in {
                "EXPERIMENT4_PROTOCOL_REVISION",
                "EXPERIMENT4_PROTOCOL_DOCUMENT_SHA256",
            }:
                assignments[target.id] = ast.literal_eval(node.value)
    assert assignments == {
        "EXPERIMENT4_PROTOCOL_REVISION": "1",
        "EXPERIMENT4_PROTOCOL_DOCUMENT_SHA256": hashlib.sha256(protocol).hexdigest(),
    }


def test_normal_authority_api_has_no_manual_source_commit_parameter() -> None:
    parameters = inspect.signature(resolve_git_launch_authority).parameters
    assert "source_commit" not in parameters
    assert "commit" not in parameters
    assert "governing_commit" not in parameters
