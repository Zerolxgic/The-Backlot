from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParseDiagnostic:
    message: str
    field: str | None = None


@dataclass
class ParsedDocument:
    path: Path
    raw_frontmatter: str | None
    data: dict[str, Any] | None
    body: str
    diagnostics: list[ParseDiagnostic] = field(default_factory=list)


@dataclass
class VaultObject:
    document: ParsedDocument
    metadata: dict[str, Any]

    @property
    def id(self) -> str | None:
        value = self.metadata.get("id")
        return value if isinstance(value, str) else None


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    message: str
    path: Path | None = None
    object_id: str | None = None
    field: str | None = None
    related_refs: tuple[str, ...] = ()


@dataclass
class ValidationReport:
    findings: list[Finding] = field(default_factory=list)
    execution_diagnostics: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "WARNING"]

    @property
    def status(self) -> str:
        return "FAIL" if self.execution_diagnostics or self.errors else "PASS"

    @property
    def counts(self) -> dict[str, int]:
        return {s: sum(f.severity == s for f in self.findings) for s in ("ERROR", "WARNING", "INFO")}

    def add(self, rule_id: str, severity: str, message: str, obj: VaultObject | None = None,
            field: str | None = None, related_refs: tuple[str, ...] = ()) -> None:
        self.findings.append(Finding(rule_id, severity, message, obj.document.path if obj else None,
                                     obj.id if obj else None, field, related_refs))
