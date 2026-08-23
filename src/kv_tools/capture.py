from __future__ import annotations

import json
import errno
import os
import re
import sys
import tempfile
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping

import yaml

from .configuration import ConfigurationError, read_default_vault
from .filesystem import NAVIGATION_DIRECTORIES, discover_markdown
from .models import Finding, ParsedDocument, ValidationReport, VaultObject
from .parser import as_object, parse_markdown, parse_markdown_text
from .registry import ResolutionKind, VaultRegistry
from .validator import validate_vault


_KV_ID = re.compile(r"^kv-[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_SCOPE_KINDS = {"project", "area", "tool", "meta"}
_LOCK_NAME = ".kv-capture.lock"
_WINDOWS_EPOCH_OFFSET_SECONDS = 11_644_473_600


class CaptureRefusal(ValueError):
    """A known pre-publication condition means no Capture was written."""


class CaptureExecutionError(RuntimeError):
    """Capture could not complete normally; publication certainty is explicit."""

    def __init__(self, message: str, *, indeterminate: bool = False) -> None:
        super().__init__(message)
        self.indeterminate = indeterminate


@dataclass(frozen=True)
class CaptureResult:
    title: str
    object_id: str
    relative_path: Path
    baseline_errors: tuple[Finding, ...]
    warnings: tuple[Finding, ...]


@dataclass(frozen=True)
class _Baseline:
    report: ValidationReport
    registry: VaultRegistry
    root: VaultObject


def _new_id() -> str:
    return f"kv-{uuid.uuid7()}"


def _finding_key(finding: Finding) -> tuple[object, ...]:
    return (
        finding.rule_id,
        finding.severity,
        str(finding.path) if finding.path else None,
        finding.object_id,
        finding.field,
        finding.message,
        finding.related_refs,
    )


def _error_summary(findings: list[Finding]) -> str:
    return ", ".join(sorted({finding.rule_id for finding in findings}))


def _valid_id(value: str) -> bool:
    return bool(_KV_ID.fullmatch(value))


def _objects(root: Path) -> list[VaultObject]:
    paths, _ = discover_markdown(root)
    result: list[VaultObject] = []
    for path in paths:
        document = parse_markdown(path)
        obj = as_object(document)
        if obj is not None:
            result.append(obj)
    return result


def _inspect_baseline(root: Path) -> _Baseline:
    try:
        report = validate_vault(root)
    except OSError as exc:
        raise CaptureExecutionError(f"Validator could not inspect the selected Vault: {exc}") from exc
    if report.execution_diagnostics:
        raise CaptureExecutionError(
            "Validator could not inspect the selected Vault: " + "; ".join(report.execution_diagnostics)
        )
    missing_directories = [finding for finding in report.errors if finding.rule_id == "KV-FS-DIRECTORY"]
    if missing_directories:
        raise CaptureRefusal("Selected Vault is missing required navigation directories (KV-FS-DIRECTORY).")
    duplicate_ids = [finding for finding in report.errors if finding.rule_id == "KV-ID-DUPLICATE"]
    if duplicate_ids:
        raise CaptureRefusal("Selected Vault has duplicate permanent identities (KV-ID-DUPLICATE).")

    objects = _objects(root)
    registry = VaultRegistry(objects)
    schemas = [
        obj for obj in objects
        if obj.metadata.get("kind") == "meta"
        and obj.metadata.get("meta_type") == "schema"
        and obj.metadata.get("defines_schema") == "kv-v0"
        and obj.metadata.get("state") == "active"
    ]
    if len(schemas) != 1:
        raise CaptureRefusal("Selected Vault has no unique active kv-v0 Schema Meta (KV-SCHEMA-ACTIVE).")
    schema_errors = [finding for finding in report.errors if finding.path == schemas[0].document.path]
    if schema_errors:
        raise CaptureRefusal("Selected Vault's governing schema is invalid: " + _error_summary(schema_errors) + ".")

    roots = [
        obj for obj in objects
        if obj.id and obj.metadata.get("scope") == obj.id and obj.metadata.get("kind") in _SCOPE_KINDS
    ]
    if len(roots) != 1:
        raise CaptureRefusal("Selected Vault has no unique valid designated root (KV-ROOT-UNIQUE).")
    root_errors = [finding for finding in report.errors if finding.path == roots[0].document.path]
    if root_errors:
        raise CaptureRefusal("Selected Vault's designated root is invalid: " + _error_summary(root_errors) + ".")
    return _Baseline(report, registry, roots[0])


def verify_vault_target(root: Path) -> None:
    """Verify a target without creating canonical content, for config set-default-vault."""
    try:
        if not root.is_dir():
            raise CaptureRefusal(f"Vault path is not a directory: {root}")
    except OSError as exc:
        raise CaptureExecutionError(f"Could not inspect Vault path: {root}: {exc}") from exc
    _inspect_baseline(root)


def resolve_vault_target(
    explicit_vault: str | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve only the selected routing source; never discover a Vault from the filesystem."""
    environment = os.environ if environ is None else environ
    if explicit_vault is not None:
        if not explicit_vault:
            raise CaptureRefusal("--vault must not be empty.")
        try:
            return Path(explicit_vault).resolve()
        except OSError as exc:
            raise CaptureRefusal(f"--vault path cannot be resolved: {explicit_vault}: {exc}") from exc
    if "KV_VAULT" in environment:
        value = environment["KV_VAULT"]
        if not value:
            raise CaptureRefusal("KV_VAULT must not be empty.")
        path = Path(value)
        if not path.is_absolute():
            raise CaptureRefusal("KV_VAULT must be an absolute path.")
        try:
            return path.resolve()
        except OSError as exc:
            raise CaptureRefusal(f"KV_VAULT path cannot be resolved: {value}: {exc}") from exc
    configured = read_default_vault()
    if configured is None:
        raise CaptureRefusal("No Vault target was supplied. Use --vault, KV_VAULT, or kv config set-default-vault.")
    try:
        return configured.resolve()
    except OSError as exc:
        raise CaptureRefusal(f"Configured default Vault cannot be resolved: {configured}: {exc}") from exc


def _extract_title(content: str) -> str:
    for line in content.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        candidate = re.sub(r"^#{1,6}\s+", "", candidate)
        candidate = " ".join(candidate.split())
        if any(character.isalnum() for character in candidate):
            return candidate[:96].rstrip()
    return "Capture"


def _title(content: str, explicit_title: str | None) -> str:
    if explicit_title is None:
        return _extract_title(content)
    if not explicit_title.strip():
        raise CaptureRefusal("--title must not be empty.")
    if "\n" in explicit_title or "\r" in explicit_title:
        raise CaptureRefusal("--title must be a single logical line.")
    return explicit_title


def _slug(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-.")
    return (normalized[:64].rstrip("-. ") or "capture")


def navigation_filename(kind: str, title: str, object_id: str, *, extended_id: bool = False) -> str:
    """Return the shared deterministic noncanonical navigation filename for a continuing object."""
    fallback = "capture" if kind == "capture" else "resource"
    slug = _slug(title) or fallback
    identifier = object_id.removeprefix("kv-") if extended_id else object_id[-12:]
    return f"{kind}-{slug}-{identifier}.md"


def _render(metadata: dict[str, object], body: str) -> str:
    frontmatter = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).rstrip("\n")
    return f"---\n{frontmatter}\n---\n{body}"


def _windows_process_liveness(process_id: int, lock_created: float | None) -> bool | None:
    """Return True (live), False (dead/reused), or None (uncertain) on Windows."""
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.GetProcessTimes.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        )
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
    except (AttributeError, OSError):
        return None

    process_query_limited_information = 0x1000
    synchronize = 0x00100000
    invalid_parameter = 87
    still_active = 259
    handle = kernel32.OpenProcess(process_query_limited_information | synchronize, False, process_id)
    if not handle:
        return False if ctypes.get_last_error() == invalid_parameter else None
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return None
        if exit_code.value != still_active:
            return False
        if lock_created is None:
            return True
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        creation_ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
        creation_time = creation_ticks / 10_000_000 - _WINDOWS_EPOCH_OFFSET_SECONDS
        # A process born after the lock was created owns a recycled PID, not this lock.
        return False if creation_time > lock_created else True
    finally:
        kernel32.CloseHandle(handle)


class _VaultWriteLock:
    def __init__(self, root: Path, *, timeout_seconds: float = 5.0, stale_after_seconds: float = 300.0,
                 operation: str = "Capture") -> None:
        self.path = root / _LOCK_NAME
        self.timeout_seconds = timeout_seconds
        self.stale_after_seconds = stale_after_seconds
        self.token = str(uuid.uuid4())
        self._owned = False
        self.operation = operation

    def _lock_is_stale(self) -> bool:
        try:
            text = self.path.read_text(encoding="utf-8")
            payload = json.loads(text)
            process_id = payload.get("pid")
            created = float(payload.get("created", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            try:
                created = self.path.stat().st_mtime
            except OSError:
                return False
            process_id = None
        if isinstance(process_id, int) and process_id > 0:
            if sys.platform == "win32":
                liveness = _windows_process_liveness(process_id, created if created > 0 else None)
                if liveness is False:
                    return True
                return False
            try:
                os.kill(process_id, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
            except OSError as exc:
                # Windows reports an impossible/dead PID as ERROR_INVALID_PARAMETER (87)
                # rather than ProcessLookupError. Treat only that documented no-process
                # outcome like ESRCH; permission and other operational errors keep the lock.
                if exc.errno == errno.ESRCH or getattr(exc, "winerror", None) == 87:
                    return True
                return False
            return False
        return time.time() - created > self.stale_after_seconds

    def _remove_stale_lock(self) -> bool:
        if not self._lock_is_stale():
            return False
        try:
            self.path.unlink()
            return True
        except FileNotFoundError:
            return True
        except OSError:
            return False

    def __enter__(self) -> _VaultWriteLock:
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if self._remove_stale_lock():
                    continue
                if time.monotonic() >= deadline:
                    raise CaptureRefusal(
                        f"Another cooperating Knowledge Vault writer currently owns this Vault. No {self.operation} was written."
                    )
                time.sleep(0.05)
                continue
            except OSError as exc:
                raise CaptureExecutionError(f"Could not acquire {self.operation} write ownership: {exc}") from exc
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump({"pid": os.getpid(), "created": time.time(), "token": self.token}, handle)
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                try:
                    self.path.unlink()
                except OSError:
                    pass
                raise CaptureExecutionError(f"Could not establish {self.operation} write ownership: {exc}") from exc
            self._owned = True
            return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self._owned:
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("token") == self.token:
                self.path.unlink()
        except FileNotFoundError:
            pass
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        self._owned = False


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _publish_candidate(destination: Path, rendered: str) -> None:
    """Publish a fully written candidate through a no-overwrite hard-link boundary."""
    temporary: Path | None = None
    published = False
    rendered_bytes = rendered.encode("utf-8")
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".kv-capture-", suffix=".tmp", dir=destination.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(rendered_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists():
            raise CaptureRefusal(f"Capture destination already exists: {destination.name}. No Capture was written.")
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise CaptureRefusal(f"Capture destination already exists: {destination.name}. No Capture was written.") from exc
        published = True
        _fsync_directory(destination.parent)
        try:
            confirmed = destination.read_bytes() == rendered_bytes
        except OSError as exc:
            raise CaptureExecutionError(
                f"Capture publication may have succeeded but could not be confirmed: {exc}", indeterminate=True
            ) from exc
        if not confirmed:
            raise CaptureExecutionError(
                "Capture publication outcome is indeterminate; the destination content could not be confirmed.",
                indeterminate=True,
            )
    except CaptureRefusal:
        raise
    except CaptureExecutionError:
        raise
    except OSError as exc:
        if published:
            raise CaptureExecutionError(
                f"Capture publication outcome is indeterminate: {exc}", indeterminate=True
            ) from exc
        raise CaptureExecutionError(f"Capture failed before publication; no Capture was written: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _scope(baseline: _Baseline, scope_id: str | None) -> str:
    if scope_id is None:
        return baseline.root.id  # The root has a verified permanent ID.
    if not _valid_id(scope_id):
        raise CaptureRefusal("--scope must be a permanent kv-UUIDv7 ID.")
    resolution = baseline.registry.resolve(scope_id)
    if resolution.kind is ResolutionKind.MISSING:
        raise CaptureRefusal(f"Requested scope does not resolve: {scope_id}.")
    if resolution.kind is ResolutionKind.AMBIGUOUS:
        raise CaptureRefusal(f"Requested scope is ambiguous: {scope_id}.")
    target = resolution.object
    if target is None or target.metadata.get("kind") not in _SCOPE_KINDS:
        raise CaptureRefusal("Requested scope must resolve to a project, area, tool, or meta object.")
    invalid = [finding for finding in baseline.report.errors if finding.path == target.document.path]
    if invalid:
        raise CaptureRefusal("Requested scope is invalid: " + _error_summary(invalid) + ".")
    return scope_id


def capture_text(
    content: str,
    *,
    title: str | None = None,
    scope: str | None = None,
    vault: str | None = None,
    environ: Mapping[str, str] | None = None,
    lock_timeout_seconds: float = 5.0,
) -> CaptureResult:
    """Safely preserve one operator-originated text payload as one canonical Capture."""
    if not content.strip():
        raise CaptureRefusal("Capture content must not be empty or whitespace-only.")
    try:
        root = resolve_vault_target(vault, environ=environ)
    except ConfigurationError as exc:
        raise CaptureRefusal(str(exc)) from exc
    try:
        if not root.is_dir():
            raise CaptureRefusal(f"Selected Vault path is not a directory: {root}")
    except OSError as exc:
        raise CaptureExecutionError(f"Could not inspect selected Vault path: {exc}") from exc

    with _VaultWriteLock(root, timeout_seconds=lock_timeout_seconds):
        baseline = _inspect_baseline(root)
        resolved_scope = _scope(baseline, scope)
        object_id = _new_id()
        for _ in range(10):
            if baseline.registry.resolve(object_id).kind is ResolutionKind.MISSING:
                break
            object_id = _new_id()
        else:
            raise CaptureExecutionError("Could not generate an unused permanent Capture identity.")
        resolved_title = _title(content, title)
        relative = Path("05_inbox") / navigation_filename("capture", resolved_title, object_id)
        destination = root / relative
        metadata: dict[str, object] = {
            "schema": "kv-v0",
            "id": object_id,
            "title": resolved_title,
            "kind": "capture",
            "state": "active",
            "scope": resolved_scope,
            "created": date.today().isoformat(),
            "provenance": [{"kind": "operator"}],
        }
        rendered = _render(metadata, content)
        candidate: ParsedDocument = parse_markdown_text(destination, rendered)
        prospective = validate_vault(root, additional_documents=[candidate])
        if prospective.execution_diagnostics:
            raise CaptureExecutionError(
                "Prospective validation could not complete; no Capture was written: "
                + "; ".join(prospective.execution_diagnostics)
            )
        baseline_keys = {_finding_key(finding) for finding in baseline.report.errors}
        introduced = [
            finding for finding in prospective.errors
            if _finding_key(finding) not in baseline_keys
        ]
        if introduced:
            raise CaptureRefusal(
                "Capture candidate would introduce validation errors: " + _error_summary(introduced) + ". No Capture was written."
            )
        _publish_candidate(destination, rendered)
        return CaptureResult(
            resolved_title,
            object_id,
            relative,
            tuple(baseline.report.errors),
            tuple(prospective.warnings),
        )
