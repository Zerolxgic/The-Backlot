from __future__ import annotations

import argparse
import os
import sys
from typing import Mapping, TextIO

from .capture import CaptureExecutionError, CaptureRefusal, capture_text, verify_vault_target
from .classification import classify_capture
from .configuration import (
    ConfigurationError,
    ConfigurationExecutionError,
    clear_default_vault,
    read_default_vault,
    set_default_vault,
)
from .initializer import InitializationError, initialize_vault
from .reporting import render_report
from .validator import validate_vault


def _windows_stdin_content_available(stream: TextIO) -> bool:
    try:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        handle = msvcrt.get_osfhandle(stream.fileno())
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        file_type_pipe = 3
        file_type_disk = 1
        broken_pipe = 109
        file_type = kernel32.GetFileType(wintypes.HANDLE(handle))
        if file_type == file_type_pipe:
            available = wintypes.DWORD()
            if kernel32.PeekNamedPipe(wintypes.HANDLE(handle), None, 0, None, ctypes.byref(available), None):
                return available.value > 0
            return False if ctypes.get_last_error() == broken_pipe else False
        if file_type == file_type_disk:
            return os.fstat(stream.fileno()).st_size > stream.tell()
    except (AttributeError, OSError, ValueError):
        return False
    return False


def _stdin_content_available(stream: TextIO) -> bool:
    if stream.isatty():
        return False
    try:
        return stream.tell() < len(stream.getvalue())  # type: ignore[attr-defined]
    except (AttributeError, OSError, ValueError):
        pass
    if os.name == "nt":
        return _windows_stdin_content_available(stream)
    try:
        import array
        import fcntl
        import termios

        available = array.array("i", [0])
        fcntl.ioctl(stream.fileno(), termios.FIONREAD, available, True)
        return available[0] > 0
    except (AttributeError, OSError, ValueError):
        return False


def _read_redirected_stdin(stream: TextIO) -> str:
    """Read real stdin without TextIOWrapper universal-newline translation."""
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        try:
            return stream.read()
        except OSError as exc:
            raise CaptureExecutionError(f"Could not read redirected standard input: {exc}") from exc
    try:
        payload = buffer.read()
    except OSError as exc:
        raise CaptureExecutionError(f"Could not read redirected standard input: {exc}") from exc
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CaptureExecutionError(f"Could not decode redirected standard input as UTF-8: {exc}") from exc


def _capture_content(text: str | None, stream: TextIO) -> str:
    has_stdin_content = _stdin_content_available(stream)
    if text is not None and has_stdin_content:
        raise CaptureRefusal("Supply content through either --text or redirected standard input, not both.")
    if text is not None:
        return text
    if not has_stdin_content:
        raise CaptureRefusal("Capture requires --text or redirected standard input with available content; interactive input is not started automatically.")
    return _read_redirected_stdin(stream)


def _render_capture_failure(error: CaptureExecutionError) -> None:
    print(f"ERROR: {error}", file=sys.stderr)
    if error.indeterminate:
        print("Publication outcome: indeterminate. Do not blindly retry this Capture.", file=sys.stderr)
    else:
        print("No Capture was written.", file=sys.stderr)


def _write_capture_confirmation(text: str) -> None:
    """Write a published-Capture confirmation without requiring Unicode stdout."""
    encoding = getattr(sys.stdout, "encoding", None)
    if encoding:
        try:
            text.encode(encoding)
        except UnicodeEncodeError:
            text = text.encode(encoding, errors="backslashreplace").decode(encoding)
    print(text)


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="kv")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("path")
    init.add_argument("--root-title", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("path")
    capture = commands.add_parser("capture", help="Preserve one operator-originated text Capture.")
    capture.add_argument("--text", help="Capture content. Omit only when redirected standard input contains content.")
    capture.add_argument("--title", help="Optional single-line navigation title.")
    capture.add_argument("--scope", help="Optional permanent kv-UUIDv7 scope ID.")
    capture.add_argument("--vault", help="Explicit Vault path; takes precedence over KV_VAULT and config.")
    classify = commands.add_parser(
        "classify",
        help="Classify one active Capture as one Resource; selection is operator-directed, not inferred.",
        description=("Classify exactly one active Capture without evaluating, accepting/rejecting, rewriting its body, "
                     "or splitting/merging objects. Classes and deterministic initial states: claim=unassessed, "
                     "observation=recorded, practice=candidate, decision=proposed, concept=emerging, "
                     "operating_knowledge=proposed, hypothesis=unresolved."),
    )
    classify.add_argument("id", help="Permanent kv-UUIDv7 ID of the active Capture.")
    classify.add_argument("--class", dest="knowledge_class", required=True,
                          choices=("claim", "observation", "practice", "decision", "concept", "operating_knowledge", "hypothesis"),
                          help="Operator-selected Resource class; assigns its deterministic initial state without evaluation or acceptance.")
    classify.add_argument("--vault", help="Explicit Vault path; takes precedence over KV_VAULT and config.")
    config = commands.add_parser("config", help="Manage the local noncanonical default Vault path.")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    config_set = config_commands.add_parser("set-default-vault", help="Verify and set the local default Vault.")
    config_set.add_argument("path")
    config_commands.add_parser("show", help="Show the local default Vault, if configured.")
    config_commands.add_parser("clear-default-vault", help="Clear the local default Vault.")
    args = parser.parse_args(argv)
    if args.command == "init":
        try: initialize_vault(args.path, args.root_title)
        except InitializationError as exc: print(f"ERROR: {exc}", file=sys.stderr); return 1
        except OSError as exc: print(f"ERROR: {exc}", file=sys.stderr); return 2
        print(f"Initialized kv-v0 vault: {args.path}"); return 0
    if args.command == "validate":
        report = validate_vault(args.path)
        print(render_report(report))
        return 2 if report.execution_diagnostics else (1 if report.errors else 0)
    if args.command == "config":
        try:
            if args.config_command == "set-default-vault":
                default = set_default_vault(args.path, verify_vault_target)
                print(f"Default Vault: {default}")
            elif args.config_command == "show":
                default = read_default_vault()
                print(f"Default Vault: {default}" if default else "No default Vault configured.")
            else:
                changed = clear_default_vault()
                print("Default Vault cleared." if changed else "Default Vault already unset.")
            return 0
        except (ConfigurationError, CaptureRefusal) as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 1
        except (ConfigurationExecutionError, CaptureExecutionError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    if args.command == "classify":
        try:
            result = classify_capture(args.id, args.knowledge_class, vault=args.vault, environ=environ)
        except CaptureRefusal as exc:
            print(f"REFUSED: ID={args.id}; requested class={args.knowledge_class}; {exc}", file=sys.stderr)
            if "No changes were made." not in str(exc):
                print("No changes were made.", file=sys.stderr)
            return 1
        except CaptureExecutionError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            if exc.indeterminate:
                print("Classification outcome: INCOMPLETE / INDETERMINATE. Do not blindly retry.", file=sys.stderr)
            elif "PROVEN ROLLBACK" in str(exc):
                print("Classification outcome: PROVEN ROLLBACK.", file=sys.stderr)
            else:
                print("Classification outcome: KNOWN NO-WRITE.", file=sys.stderr)
            return 2
        print(f"ID: {result.object_id}")
        print(f"Class: {result.knowledge_class}")
        print(f"Initial state: {result.knowledge_state}")
        print(f"Path: {result.relative_path.as_posix()}")
        if result.baseline_errors:
            print(f"WARNING: Vault retains {len(result.baseline_errors)} pre-existing conformance error(s); run kv validate for detail.", file=sys.stderr)
        for warning in result.warnings:
            print(f"WARNING [{warning.rule_id}]: {warning.message}", file=sys.stderr)
        return 0
    try:
        content = _capture_content(args.text, stdin or sys.stdin)
        result = capture_text(content, title=args.title, scope=args.scope, vault=args.vault, environ=environ)
    except CaptureRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        print("No Capture was written.", file=sys.stderr)
        return 1
    except CaptureExecutionError as exc:
        _render_capture_failure(exc)
        return 2
    _write_capture_confirmation(f"Captured: {result.title}")
    _write_capture_confirmation(f"ID: {result.object_id}")
    _write_capture_confirmation(f"Path: {result.relative_path.as_posix()}")
    if result.baseline_errors:
        _write_capture_confirmation(
            f"WARNING: Capture published, but the Vault retains {len(result.baseline_errors)} pre-existing conformance error(s)."
        )
    for finding in result.warnings:
        _write_capture_confirmation(f"WARNING {finding.rule_id}: {finding.message}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
