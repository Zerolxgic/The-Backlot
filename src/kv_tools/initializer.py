from __future__ import annotations

import shutil
import tempfile
import uuid
from datetime import date
from pathlib import Path

import yaml

from .filesystem import NAVIGATION_DIRECTORIES, atomic_publish, destination_is_empty_directory
from .schema import distribution_template
from .validator import validate_vault


class InitializationError(RuntimeError): pass


def _new_id() -> str:
    return f"kv-{uuid.uuid7()}"


def _write(path: Path, metadata: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n" + body.strip() + "\n", encoding="utf-8")


def initialize_vault(destination: Path | str, root_title: str) -> Path:
    destination = Path(destination)
    if not root_title.strip(): raise InitializationError("--root-title must not be empty.")
    if destination.exists() and not destination_is_empty_directory(destination): raise InitializationError("Destination must not exist or be an empty ordinary directory.")
    parent = destination.parent; parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="kv-init-", dir=parent))
    try:
        for directory in NAVIGATION_DIRECTORIES: (staging / directory).mkdir()
        root_id, schema_id, home_id = (_new_id() for _ in range(3)); created = date.today().isoformat()
        base = {"schema":"kv-v0", "state":"active", "created":created, "provenance":[{"kind":"operator"}]}
        _write(staging / "20_areas/root.md", base | {"id":root_id,"title":root_title,"kind":"area","scope":root_id}, f"# {root_title}\n\n# Purpose\n\nRoot area for this vault.\n\n# Boundaries\n\nThe primary scope boundary for this vault.")
        template = distribution_template().replace("{{SCHEMA_ID}}", schema_id).replace("{{ROOT_ID}}", root_id).replace("{{CREATED}}", created)
        (staging / "90_meta/kv-v0-schema.md").write_text(template, encoding="utf-8")
        _write(staging / "00_index/home.md", base | {"id":home_id,"title":"Home","kind":"index","scope":root_id}, "# Home\n\nThis vault has been initialized. Start with the navigation directories when adding knowledge.")
        report = validate_vault(staging)
        if report.execution_diagnostics:
            raise InitializationError("Staged bootstrap could not complete validation: " + "; ".join(report.execution_diagnostics))
        if report.errors:
            raise InitializationError("Staged bootstrap failed conformance validation: " + "; ".join(f.rule_id for f in report.errors))
        atomic_publish(staging, destination); return destination
    except Exception:
        shutil.rmtree(staging, ignore_errors=True); raise
