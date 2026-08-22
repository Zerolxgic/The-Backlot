from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import ParseDiagnostic, ParsedDocument, VaultObject


def parse_markdown_text(path: Path, text: str) -> ParsedDocument:
    if not text.startswith("---"):
        return ParsedDocument(path, None, None, text, [ParseDiagnostic("Document does not begin with YAML frontmatter.")])
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return ParsedDocument(path, None, None, text, [ParseDiagnostic("Invalid opening frontmatter delimiter.")])
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return ParsedDocument(path, "".join(lines[1:]), None, "", [ParseDiagnostic("Frontmatter closing delimiter is missing.")])
    raw = "".join(lines[1:end])
    body = "".join(lines[end + 1:])
    try:
        # BaseLoader intentionally keeps scalar metadata textual. In particular, YAML must
        # not silently reinterpret a canonical YYYY-MM-DD value as a Python date object.
        loaded: Any = yaml.load(raw, Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        return ParsedDocument(path, raw, None, body, [ParseDiagnostic(f"Malformed YAML frontmatter: {exc}")])
    if not isinstance(loaded, dict):
        return ParsedDocument(path, raw, None, body, [ParseDiagnostic("Frontmatter must be a YAML mapping.")])
    return ParsedDocument(path, raw, loaded, body)


def parse_markdown(path: Path) -> ParsedDocument:
    return parse_markdown_text(path, path.read_text(encoding="utf-8"))


def as_object(document: ParsedDocument) -> VaultObject | None:
    return VaultObject(document, document.data) if document.data is not None else None
