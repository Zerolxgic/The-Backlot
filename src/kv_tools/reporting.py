from __future__ import annotations

from .models import Finding, ValidationReport


def finding_sort_key(finding: Finding) -> tuple[str, str, str, str]:
    return (str(finding.path or ""), finding.rule_id, finding.field or "", finding.message)


def render_report(report: ValidationReport) -> str:
    lines = [f"{report.status}: {report.counts['ERROR']} error(s), {report.counts['WARNING']} warning(s), {report.counts['INFO']} info"]
    for finding in sorted(report.findings, key=finding_sort_key):
        location = f" [{finding.path}]" if finding.path else ""
        field = f" field={finding.field}" if finding.field else ""
        lines.append(f"{finding.severity} {finding.rule_id}{location}{field}: {finding.message}")
    for diagnostic in sorted(report.execution_diagnostics):
        lines.append(f"INFO KV-EXEC: {diagnostic}")
    return "\n".join(lines)
