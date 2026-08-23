from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from .capture import (
    CaptureExecutionError,
    CaptureRefusal,
    _VaultWriteLock,
    _inspect_baseline,
    _valid_id,
    navigation_filename,
    resolve_vault_target,
)
from .configuration import ConfigurationError
from .models import Finding, VaultObject
from .registry import ResolutionKind
from .validator import validate_vault


_INITIAL_STATES = {
    "claim": "unassessed",
    "observation": "recorded",
    "practice": "candidate",
    "decision": "proposed",
    "concept": "emerging",
    "operating_knowledge": "proposed",
    "hypothesis": "unresolved",
}


@dataclass(frozen=True)
class ClassificationResult:
    object_id: str
    knowledge_class: str
    knowledge_state: str
    relative_path: Path
    baseline_errors: tuple[Finding, ...]
    warnings: tuple[Finding, ...]


def _frontmatter_and_body(raw: bytes) -> tuple[dict[str, object], bytes]:
    """Parse only frontmatter while retaining the exact UTF-8 body byte sequence."""
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != b"---":
        raise CaptureRefusal("Target Capture has invalid frontmatter. No changes were made.")
    closing = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == b"---"), None)
    if closing is None:
        raise CaptureRefusal("Target Capture has incomplete frontmatter. No changes were made.")
    try:
        data = yaml.load(b"".join(lines[1:closing]).decode("utf-8"), Loader=yaml.BaseLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise CaptureRefusal(f"Target Capture frontmatter cannot be parsed: {exc}. No changes were made.") from exc
    if not isinstance(data, dict):
        raise CaptureRefusal("Target Capture frontmatter is not a mapping. No changes were made.")
    return data, b"".join(lines[closing + 1:])


def _render_resource(metadata: dict[str, object], body: bytes) -> bytes:
    ordered = {
        "schema": metadata["schema"], "id": metadata["id"], "title": metadata["title"],
        "kind": "resource", "state": metadata["state"], "scope": metadata["scope"],
        "created": metadata["created"], "provenance": metadata["provenance"],
    }
    if "relationships" in metadata:
        ordered["relationships"] = metadata["relationships"]
    ordered["knowledge_class"] = metadata["knowledge_class"]
    ordered["knowledge_state"] = metadata["knowledge_state"]
    frontmatter = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True).encode("utf-8").rstrip(b"\n")
    return b"---\n" + frontmatter + b"\n---\n" + body


def _within(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _ordinary_path(root: Path, path: Path, *, must_exist: bool) -> None:
    if not _within(root, path):
        raise CaptureRefusal("Classification path is outside the selected Vault boundary. No changes were made.")
    current = root
    try:
        parts = path.relative_to(root).parts
    except ValueError as exc:
        raise CaptureRefusal("Classification path is outside the selected Vault boundary. No changes were made.") from exc
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise CaptureRefusal("Classification path uses link indirection. No changes were made.")
    if must_exist and (path.is_symlink() or not path.is_file()):
        raise CaptureRefusal("Classification target is not an ordinary regular file. No changes were made.")


def _ordinary_directory(root: Path, path: Path) -> None:
    if not _within(root, path) or not path.is_dir():
        raise CaptureRefusal("Classification destination is outside a safe Vault directory. No changes were made.")
    try:
        parts = path.relative_to(root).parts
    except ValueError as exc:
        raise CaptureRefusal("Classification destination is outside a safe Vault directory. No changes were made.") from exc
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise CaptureRefusal("Classification destination uses link indirection. No changes were made.")


def _comparison_key(finding: Finding, root: Path) -> tuple[object, ...]:
    """Compare validation facts without treating an isolated prospective root as a new finding."""
    try:
        path = finding.path.relative_to(root) if finding.path else None
    except ValueError:
        path = finding.path
    return (finding.rule_id, finding.severity, path, finding.object_id, finding.field, finding.message, finding.related_refs)


def _prospective_validate(
    root: Path, source: Path, destination_relative: Path, candidate: bytes
) -> tuple[tuple[Finding, ...], tuple[Finding, ...], Path]:
    """Validate replacement, never both representations, in an isolated filesystem copy."""
    try:
        with tempfile.TemporaryDirectory(prefix="kv-classify-prospective-", dir=root.parent) as temporary:
            copy_root = Path(temporary) / "vault"
            shutil.copytree(root, copy_root, symlinks=True)
            copy_source = copy_root / source.relative_to(root)
            copy_destination = copy_root / destination_relative
            copy_destination.parent.mkdir(parents=True, exist_ok=True)
            if copy_destination != copy_source and copy_destination.exists():
                raise CaptureRefusal("Classification destination already exists. No changes were made.")
            if copy_destination != copy_source:
                copy_source.unlink()
            copy_destination.write_bytes(candidate)
            report = validate_vault(copy_root)
    except CaptureRefusal:
        raise
    except OSError as exc:
        raise CaptureExecutionError(f"Prospective validation could not execute: {exc}") from exc
    if report.execution_diagnostics:
        raise CaptureExecutionError("Prospective validation could not execute: " + "; ".join(report.execution_diagnostics))
    return tuple(report.errors), tuple(report.warnings), copy_root


def _restore(source: Path, backup: Path, destination: Path) -> bool:
    try:
        if destination.exists():
            destination.unlink()
        if backup.exists():
            os.replace(backup, source)
        return source.exists() if source == destination else source.exists() and not destination.exists()
    except OSError:
        return False


def _target_has_unmerged_git_entry(root: Path, source: Path) -> bool:
    """Best-effort, read-only D18 check; unavailable Git metadata is non-blocking."""
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
        if top.returncode:
            return False
        top_level = Path(top.stdout.strip()).resolve()
        relative = source.resolve().relative_to(top_level)
        result = subprocess.run(["git", "-C", str(top_level), "ls-files", "-u", "--", relative.as_posix()], capture_output=True, text=True, check=False)
        return result.returncode == 0 and bool(result.stdout.strip())
    except (OSError, ValueError):
        return False


def classify_capture(
    object_id: str,
    knowledge_class: str,
    *,
    vault: str | None = None,
    environ: Mapping[str, str] | None = None,
    lock_timeout_seconds: float = 5.0,
) -> ClassificationResult:
    """Classify one valid active Capture as one continuing Resource identity."""
    if not _valid_id(object_id):
        raise CaptureRefusal("Classification ID must be a permanent kv-UUIDv7 ID. No changes were made.")
    if knowledge_class not in _INITIAL_STATES:
        raise CaptureRefusal(f"Unsupported Resource class: {knowledge_class}. No changes were made.")
    try:
        root = resolve_vault_target(vault, environ=environ)
    except ConfigurationError as exc:
        raise CaptureRefusal(str(exc)) from exc
    if not root.is_dir():
        raise CaptureRefusal(f"Selected Vault path is not a directory: {root}. No changes were made.")
    root = root.resolve()

    with _VaultWriteLock(root, timeout_seconds=lock_timeout_seconds, operation="classification"):
        baseline = _inspect_baseline(root)
        resolution = baseline.registry.resolve(object_id)
        if resolution.kind is ResolutionKind.MISSING:
            raise CaptureRefusal(f"Capture target was not found: {object_id}. No changes were made.")
        if resolution.kind is ResolutionKind.AMBIGUOUS:
            raise CaptureRefusal(f"Capture target is ambiguous: {object_id}. No changes were made.")
        target: VaultObject = resolution.object  # unique by the branch above
        if target.metadata.get("schema") != "kv-v0" or target.metadata.get("kind") != "capture" or target.metadata.get("state") != "active":
            raise CaptureRefusal(
                f"Target {object_id} is not an active kv-v0 Capture (schema={target.metadata.get('schema')}, kind={target.metadata.get('kind')}, state={target.metadata.get('state')}, knowledge_class={target.metadata.get('knowledge_class')}, knowledge_state={target.metadata.get('knowledge_state')}). No changes were made."
            )
        target_errors = [finding for finding in baseline.report.errors if finding.path == target.document.path]
        if target_errors:
            raise CaptureRefusal("Target Capture is invalid and cannot be classified. No changes were made.")
        source = target.document.path
        if target.metadata.get("scope") == object_id:
            raise CaptureRefusal(f"Target {object_id} has prohibited self-scope. No changes were made.")
        _ordinary_path(root, source, must_exist=True)
        if _target_has_unmerged_git_entry(root, source):
            raise CaptureRefusal(f"Target {object_id} is unresolved in the Git index. No changes were made.")
        source_identity = (source.stat().st_dev, source.stat().st_ino, source.stat().st_size, source.stat().st_mtime_ns)
        source_bytes = source.read_bytes()
        metadata, body = _frontmatter_and_body(source_bytes)
        if metadata != target.metadata:
            raise CaptureRefusal("Target Capture changed while being inspected. No changes were made.")
        result_metadata = dict(metadata)
        result_metadata["knowledge_class"] = knowledge_class
        result_metadata["knowledge_state"] = _INITIAL_STATES[knowledge_class]
        candidate = _render_resource(result_metadata, body)
        title = result_metadata.get("title")
        if not isinstance(title, str):
            raise CaptureRefusal("Target Capture title is invalid. No changes were made.")
        relative = Path("30_resources") / navigation_filename("resource", title, object_id)
        destination = root / relative
        _ordinary_directory(root, destination.parent)
        if destination != source and destination.exists():
            relative = Path("30_resources") / navigation_filename("resource", title, object_id, extended_id=True)
            destination = root / relative
            if destination != source and destination.exists():
                raise CaptureRefusal(f"Classification destination already exists: {relative.as_posix()}. No changes were made.")
        prospective_errors, prospective_warnings, prospective_root = _prospective_validate(root, source, relative, candidate)
        baseline_keys = {_comparison_key(finding, root) for finding in baseline.report.errors}
        introduced = [
            finding for finding in prospective_errors
            if _comparison_key(finding, prospective_root) not in baseline_keys
        ]
        if introduced:
            raise CaptureRefusal("Classification candidate would introduce validation errors: " + ", ".join(sorted({f.rule_id for f in introduced})) + ". No changes were made.")
        _ordinary_path(root, source, must_exist=True)
        _ordinary_directory(root, destination.parent)
        current_identity = (source.stat().st_dev, source.stat().st_ino, source.stat().st_size, source.stat().st_mtime_ns)
        if source.read_bytes() != source_bytes or current_identity != source_identity or (destination != source and destination.exists()):
            raise CaptureRefusal("Target or destination changed before mutation. No changes were made.")
        # Re-establish target-critical reference validity immediately before the
        # canonical transition.  The source bytes above protect the Capture
        # itself; this check protects its unchanged scope/provenance contract
        # from a non-cooperating edit that occurred during prospective work.
        current_baseline = _inspect_baseline(root)
        current_target = current_baseline.registry.resolve(object_id)
        if current_target.kind is not ResolutionKind.UNIQUE or current_target.object is None:
            raise CaptureRefusal("Target Capture became ambiguous or unavailable before mutation. No changes were made.")
        current_errors = [
            finding for finding in current_baseline.report.errors
            if finding.path == current_target.object.document.path
        ]
        if current_errors:
            raise CaptureRefusal("Target Capture or its required references changed before mutation. No changes were made.")

        temporary: Path | None = None
        backup: Path | None = None
        mutation_started = False
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix=".kv-classify-", suffix=".tmp", dir=destination.parent)
            temporary = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(candidate)
                handle.flush()
                os.fsync(handle.fileno())
            backup = source.with_name(f".kv-classify-backup-{object_id[-12:]}.tmp")
            if backup.exists():
                raise CaptureRefusal("Classification rollback location already exists. No changes were made.")
            os.replace(source, backup)
            mutation_started = True
            try:
                os.link(temporary, destination)
            except Exception:
                os.replace(backup, source)
                raise
            temporary.unlink()
            temporary = None
            final = destination.read_bytes()
            if final != candidate:
                raise CaptureExecutionError("Classification publication could not be verified.", indeterminate=True)
            final_report = validate_vault(root)
            if final_report.execution_diagnostics or any(f.path == destination for f in final_report.errors):
                raise CaptureExecutionError("Classification final state could not be validated.", indeterminate=True)
            backup.unlink()
            backup = None
        except CaptureRefusal:
            raise
        except Exception as exc:
            restored = False
            if backup is not None:
                restored = _restore(source, backup, destination)
            if not mutation_started:
                raise CaptureExecutionError(f"Classification execution failed before canonical mutation; KNOWN NO-WRITE for {object_id}: {exc}") from exc
            if restored:
                raise CaptureExecutionError(f"Classification failed after canonical mutation; PROVEN ROLLBACK for {object_id}: {exc}") from exc
            raise CaptureExecutionError(
                f"Classification outcome is INCOMPLETE / INDETERMINATE for {object_id}; inspect {source} and {destination} before another canonical write. Do not blindly retry: {exc}",
                indeterminate=True,
            ) from exc
        finally:
            if temporary is not None:
                try: temporary.unlink()
                except OSError: pass
        return ClassificationResult(object_id, knowledge_class, _INITIAL_STATES[knowledge_class], relative,
                                    tuple(baseline.report.errors), prospective_warnings)
