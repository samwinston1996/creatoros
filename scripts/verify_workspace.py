#!/usr/bin/env python3
"""Verify that a CreatorOS repository family is safe and coherent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable, List, Sequence

EXPECTED_REPOSITORIES = (
    "creatoros",
    "creator-tool-arsenal",
    "creator-brain",
    "creator-production-platform",
    "creator-governance",
    "creator-content-workspace",
)
REQUIRED_HUMAN_GATES = (
    "claims-and-script",
    "final-quality",
    "public-posting",
)
OBJECT_GATE_KEYS = {
    "claims_and_script",
    "final_quality",
    "public_posting",
}
AUDIO_VIDEO_EXTENSIONS = {
    ".aac", ".aiff", ".avi", ".flac", ".m4a", ".mkv", ".mov", ".mp3",
    ".mp4", ".mpeg", ".wav", ".webm",
}
PRIVATE_PATH_PARTS = {
    "analytics-exports", "credentials", "episodes", "licensed-media",
    "narration", "raw-footage", "renders",
}
ABSOLUTE_PRIVATE_PATH = re.compile(
    r"(?:/" + r"Users/|/" + r"home/|[A-Za-z]:[\\/](?:Users|Documents)[\\/])"
)
IGNORED_PARTS = {".git", "__pycache__"}


def _walk_files(repository: Path) -> Iterable[Path]:
    if (repository / ".git").is_dir():
        result = subprocess.run(
            ["git", "-C", str(repository), "ls-files", "-z"],
            capture_output=True,
            check=True,
        )
        for relative in result.stdout.decode("utf-8").split("\0"):
            if relative:
                path = repository / relative
                if path.is_file():
                    yield path
        return

    for path in repository.rglob("*"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.is_file():
            yield path


def _records(value: Any) -> Iterable[dict]:
    if isinstance(value, dict):
        yield value
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def _is_example_or_catalog(path: Path, repository: Path) -> bool:
    relative_parts = path.relative_to(repository).parts
    return any(part in {"examples", "catalog"} for part in relative_parts[:-1])


def _check_human_defaults(path: Path, value: Any, errors: List[str]) -> None:
    if "schemas" in path.parts:
        return
    for record in _records(value):
        human_gates = record.get("human_gates")
        if isinstance(human_gates, list) and tuple(human_gates) != REQUIRED_HUMAN_GATES:
            errors.append(f"{path}: human-gate defaults must require {', '.join(REQUIRED_HUMAN_GATES)}")
        elif isinstance(human_gates, dict):
            if set(human_gates) != OBJECT_GATE_KEYS or any(human_gates.values()):
                errors.append(f"{path}: human-gate defaults must contain all gates set to false")

        human_checks = record.get("human_checks")
        if isinstance(human_checks, dict):
            if set(human_checks) != OBJECT_GATE_KEYS or any(human_checks.values()):
                errors.append(f"{path}: human-gate defaults must contain all checks set to false")

        if "license-record" in path.name and record.get("review_status") != "needs-human-review":
            errors.append(f"{path}: license review must default to needs-human-review")

        gates = record.get("gates")
        if isinstance(gates, list):
            gate_map = {
                gate.get("id"): gate.get("actor")
                for gate in gates
                if isinstance(gate, dict)
            }
            if gate_map != {gate: "human" for gate in REQUIRED_HUMAN_GATES}:
                errors.append(f"{path}: approval gates must be the expected human gates")


def verify_workspace(repos_root: Path) -> List[str]:
    """Return deterministic validation errors for a CreatorOS repositories root."""
    repos_root = Path(repos_root).expanduser().resolve()
    errors: List[str] = []

    repositories = []
    for name in EXPECTED_REPOSITORIES:
        repository = repos_root / name
        if not repository.is_dir():
            errors.append(f"missing repository: {name}")
        else:
            repositories.append(repository)

    for repository in repositories:
        for path in _walk_files(repository):
            relative = path.relative_to(repository)
            if path.suffix.lower() in AUDIO_VIDEO_EXTENSIONS:
                errors.append(f"{repository.name}/{relative}: audio/video file is not allowed in a system repository")
            if any(part.lower() in PRIVATE_PATH_PARTS for part in relative.parts[:-1]):
                errors.append(f"{repository.name}/{relative}: private-content path is not allowed")

            text = None
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                pass

            if text is not None and ABSOLUTE_PRIVATE_PATH.search(text):
                errors.append(f"{repository.name}/{relative}: absolute private path is not allowed")

            if path.suffix.lower() == ".json":
                try:
                    value = json.loads(text if text is not None else path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    errors.append(f"{repository.name}/{relative}: invalid JSON ({exc})")
                    continue

                if _is_example_or_catalog(path, repository):
                    records = list(_records(value))
                    if not records:
                        errors.append(f"{repository.name}/{relative}: examples/catalog JSON must contain an object record")
                    for record in records:
                        if record.get("schema_version") != "1.0.0":
                            errors.append(f"{repository.name}/{relative}: schema_version must be 1.0.0")

                _check_human_defaults(path, value, errors)

    return sorted(set(errors))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos-root", required=True, type=Path, help="directory containing CreatorOS sibling repositories")
    args = parser.parse_args(argv)
    errors = verify_workspace(args.repos_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"CreatorOS workspace verification failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print("CreatorOS workspace verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
