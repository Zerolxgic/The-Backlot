from __future__ import annotations

import argparse
import sys

from .initializer import InitializationError, initialize_vault
from .reporting import render_report
from .validator import validate_vault


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kv")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("path"); init.add_argument("--root-title", required=True)
    validate = commands.add_parser("validate"); validate.add_argument("path")
    args = parser.parse_args(argv)
    if args.command == "init":
        try: initialize_vault(args.path, args.root_title)
        except InitializationError as exc: print(f"ERROR: {exc}", file=sys.stderr); return 1
        except OSError as exc: print(f"ERROR: {exc}", file=sys.stderr); return 2
        print(f"Initialized kv-v0 vault: {args.path}"); return 0
    report = validate_vault(args.path)
    print(render_report(report))
    return 2 if report.execution_diagnostics else (1 if report.errors else 0)


if __name__ == "__main__": raise SystemExit(main())
