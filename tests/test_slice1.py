from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
import yaml

from kv_tools.cli import main
from kv_tools import initializer
from kv_tools.initializer import InitializationError, initialize_vault
from kv_tools.models import ValidationReport
from kv_tools.parser import parse_markdown
from kv_tools.validator import validate_vault


def digest_tree(path: Path) -> dict[str, str]:
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob("*.md")}


def test_init_and_validate_absent_destination(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    initialize_vault(vault, "Synthetic Root")
    assert {p.name for p in vault.iterdir()} == {"00_index","05_inbox","10_projects","20_areas","30_resources","40_sources","50_tools","60_maps","90_meta","99_archive"}
    assert len(list(vault.rglob("*.md"))) == 3
    docs = [parse_markdown(p) for p in vault.rglob("*.md")]
    ids = [d.data["id"] for d in docs]
    assert len(set(ids)) == 3 and all(value.startswith("kv-") and value.split("-")[3].startswith("7") for value in ids)
    report = validate_vault(vault)
    assert report.status == "PASS"


def test_init_empty_and_nonempty_refusal(tmp_path: Path) -> None:
    empty = tmp_path / "empty"; empty.mkdir(); initialize_vault(empty, "Synthetic Root")
    before = digest_tree(empty)
    with pytest.raises(InitializationError): initialize_vault(empty, "Other")
    assert digest_tree(empty) == before
    nonempty = tmp_path / "nonempty"; nonempty.mkdir(); (nonempty / "operator-file.txt").write_text("keep")
    with pytest.raises(InitializationError): initialize_vault(nonempty, "Synthetic Root")


def test_invalid_duplicate_is_read_only(tmp_path: Path) -> None:
    vault = tmp_path / "vault"; initialize_vault(vault, "Synthetic Root")
    home = vault / "00_index/home.md"; root = vault / "20_areas/root.md"
    home.write_text(home.read_text().replace("id: kv-", "id: kv-", 1).replace(parse_markdown(home).data["id"], parse_markdown(root).data["id"]), encoding="utf-8")
    before = digest_tree(vault); report = validate_vault(vault)
    assert "KV-ID-DUPLICATE" in {f.rule_id for f in report.errors}
    assert digest_tree(vault) == before


def test_malformed_frontmatter_is_diagnosed(tmp_path: Path) -> None:
    vault = tmp_path / "vault"; initialize_vault(vault, "Synthetic Root")
    (vault / "30_resources/broken.md").write_text("---\nid: [bad\n---\nbody", encoding="utf-8")
    report = validate_vault(vault)
    assert any(f.rule_id == "KV-PARSE-FRONTMATTER" for f in report.errors)


def test_cli_statuses_and_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    vault = tmp_path / "vault"; assert main(["init", str(vault), "--root-title", "Synthetic Root"]) == 0
    assert main(["validate", str(vault)]) == 0
    assert "PASS:" in capsys.readouterr().out
    (vault / "00_index/home.md").write_text("bad", encoding="utf-8")
    assert main(["validate", str(vault)]) == 1
    assert capsys.readouterr().out.startswith("FAIL:")
    assert main(["validate", str(tmp_path / "missing")]) == 2
    execution_output = capsys.readouterr().out
    assert execution_output.startswith("FAIL:")
    assert "INFO KV-EXEC:" in execution_output


def test_staged_execution_failure_does_not_publish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "vault"
    report = ValidationReport(execution_diagnostics=["synthetic validator execution failure"])
    assert report.execution_diagnostics
    monkeypatch.setattr(initializer, "validate_vault", lambda path: report)

    with pytest.raises(InitializationError, match="could not complete validation"):
        initializer.initialize_vault(destination, "Synthetic Root")

    assert not destination.exists()
    assert not list(tmp_path.glob("kv-init-*"))


def test_schema_drift_and_directory_warning(tmp_path: Path) -> None:
    vault = tmp_path / "vault"; initialize_vault(vault, "Synthetic Root")
    schema = vault / "90_meta/kv-v0-schema.md"; schema.write_text(schema.read_text().replace('"kv-v0"', '"kv-v0-drift"', 1), encoding="utf-8")
    report = validate_vault(vault)
    assert any(f.rule_id == "KV-SCHEMA-DRIFT" for f in report.errors)
    shutil.copy(vault / "00_index/home.md", vault / "20_areas/mismatch.md")
    report = validate_vault(vault)
    assert any(f.rule_id == "KV-DIRECTORY-KIND" for f in report.warnings)


def replace_metadata(path: Path, **changes: object) -> None:
    parsed = parse_markdown(path); metadata = parsed.data | changes
    path.write_text("---\n" + yaml.safe_dump(metadata, sort_keys=False).strip() + "\n---\n" + parsed.body, encoding="utf-8")


def rules(report) -> set[str]: return {finding.rule_id for finding in report.errors}


def test_parser_and_schema_failures(tmp_path: Path) -> None:
    vault = tmp_path / "vault"; initialize_vault(vault, "Synthetic Root")
    home = vault / "00_index/home.md"; replace_metadata(home, title="", unexpected="no")
    report = validate_vault(vault)
    assert {"KV-STRUCTURE", "KV-METADATA-UNEXPECTED"} <= rules(report)
    schema = vault / "90_meta/kv-v0-schema.md"; replace_metadata(schema, state="archived")
    assert "KV-SCHEMA-ACTIVE" in rules(validate_vault(vault))
    shutil.copy(schema, vault / "90_meta/second.md"); replace_metadata(schema, state="active"); replace_metadata(vault / "90_meta/second.md", id="kv-018f0000-0000-7000-8000-000000000001", state="active")
    assert "KV-SCHEMA-ACTIVE" in rules(validate_vault(vault))


def test_identity_and_reference_cases(tmp_path: Path) -> None:
    vault = tmp_path / "vault"; initialize_vault(vault, "Synthetic Root")
    home = vault / "00_index/home.md"; replace_metadata(home, id="not-a-kv-id")
    assert "KV-STRUCTURE" in rules(validate_vault(vault))
    initialize_vault(tmp_path / "other", "Other")
    vault = tmp_path / "other"; root = vault / "20_areas/root.md"; root_id = parse_markdown(root).data["id"]
    replace_metadata(vault / "00_index/home.md", scope="kv-018f0000-0000-7000-8000-000000000099")
    assert "KV-SCOPE-REFERENCE" in rules(validate_vault(vault))
    replace_metadata(vault / "00_index/home.md", scope=parse_markdown(vault / "00_index/home.md").data["id"])
    assert "KV-ROOT-UNIQUE" in rules(validate_vault(vault))
    assert validate_vault(vault).status == "FAIL"  # root self-scope remains permitted, but Index self-scope is not.


def test_scope_and_graph_integrity_cases(tmp_path: Path) -> None:
    vault = tmp_path / "vault"; initialize_vault(vault, "Synthetic Root")
    root = vault / "20_areas/root.md"; home = vault / "00_index/home.md"
    replace_metadata(home, scope=parse_markdown(home).data["id"]); assert "KV-ROOT-UNIQUE" in rules(validate_vault(vault))
    replace_metadata(home, scope=parse_markdown(root).data["id"]); replace_metadata(root, scope=parse_markdown(home).data["id"])
    assert "KV-SCOPE-KIND" in rules(validate_vault(vault))
    initialize_vault(tmp_path / "graphs", "Graphs"); vault = tmp_path / "graphs"; root = vault / "20_areas/root.md"; home = vault / "00_index/home.md"
    replace_metadata(home, state="superseded", superseded_by=[parse_markdown(home).data["id"], parse_markdown(home).data["id"]])
    assert {"KV-REF-SELF", "KV-SUPERSEDED-DUPLICATE", "KV-SUPERSEDED-CYCLE"} <= rules(validate_vault(vault))
    initialize_vault(tmp_path / "authority", "Authority"); vault = tmp_path / "authority"; root = vault / "20_areas/root.md"; root_id = parse_markdown(root).data["id"]
    replace_metadata(root, authority={"kind":"delegated", "ref": root_id})
    assert {"KV-AUTHORITY-CYCLE", "KV-AUTHORITY-ROOT"} <= rules(validate_vault(vault))


def test_each_kind_and_resource_evidence_rules(tmp_path: Path) -> None:
    vault = tmp_path / "vault"; initialize_vault(vault, "Synthetic Root"); root_id = parse_markdown(vault / "20_areas/root.md").data["id"]
    base = {"schema":"kv-v0","state":"active","scope":root_id,"created":"2026-01-01","provenance":[{"kind":"operator"}]}
    entries = [("00_index/i.md", "index", {}),("05_inbox/c.md", "capture", {}),("10_projects/p.md", "project", {"canonical_truth":{"mode":"vault","ref":"kv-018f0000-0000-7000-8000-000000000011"}}),("30_resources/r.md", "resource", {"knowledge_class":"claim","knowledge_state":"accepted","evidence":[]}), ("40_sources/s.md", "source", {"source_type":"webpage","locators":[{"kind":"url","value":"https://example.test"}]}),("50_tools/t.md", "tool", {"tool_type":"software","adoption_state":"adopted"}),("60_maps/m.md", "map", {}),("90_meta/policy.md", "meta", {"meta_type":"policy","authority":{"kind":"operator"}})]
    for number, (relative, kind, extra) in enumerate(entries, 11):
        ident = f"kv-018f0000-0000-7000-8000-{number:012d}"; data = base | {"id":ident,"title":kind,"kind":kind} | extra
        if kind == "project": data["canonical_truth"]["ref"] = ident
        (vault / relative).write_text("---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n# Synthetic\n", encoding="utf-8")
    found = rules(validate_vault(vault))
    assert {"KV-EVIDENCE-MINIMUM", "KV-SOURCE-ACCESSED", "KV-AUTHORITY-REQUIRED"} <= found


def test_symlink_detection_portably(tmp_path: Path) -> None:
    vault = tmp_path / "vault"; initialize_vault(vault, "Synthetic Root")
    link = vault / "00_index/link.md"
    try: link.symlink_to(vault / "00_index/home.md")
    except OSError: pytest.skip("Windows symlink creation is unavailable in this environment; portable detector is implemented.")
    assert "KV-FS-SYMLINK" in rules(validate_vault(vault))
