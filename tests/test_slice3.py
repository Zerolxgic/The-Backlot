from __future__ import annotations

import json
import os
import io
import shutil
import subprocess
from pathlib import Path

import pytest

from kv_tools.capture import CaptureExecutionError, CaptureRefusal, capture_text
from kv_tools import classification as classification_module
from kv_tools.classification import classify_capture
from kv_tools.cli import main
from kv_tools.initializer import initialize_vault
from kv_tools.models import ValidationReport
from kv_tools.parser import parse_markdown
from kv_tools.validator import validate_vault


def make_vault(tmp_path: Path, name: str = "vault") -> Path:
    vault = tmp_path / name
    initialize_vault(vault, "Synthetic Root")
    return vault


def _git(repository: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    if shutil.which("git") is None:
        pytest.skip("Git is unavailable on this test machine.")
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check:
        assert result.returncode == 0, result.stderr
    return result


def _assert_unmerged(repository: Path, relative: Path) -> str:
    path = relative.as_posix()
    output = _git(repository, "ls-files", "-u", "--", path).stdout
    entries = [line.split(maxsplit=3) for line in output.splitlines()]
    assert {entry[2] for entry in entries} == {"1", "2", "3"}
    assert {entry[3] for entry in entries} == {path}
    return output


def _create_target_conflict(tmp_path: Path, *, nested: bool) -> tuple[Path, Path, Path, str]:
    repository = tmp_path / "repository"
    if nested:
        repository.mkdir(parents=True)
        _git(repository, "init", "-b", "main")
        vault = repository / "nested" / "vault"
        vault.parent.mkdir(parents=True, exist_ok=True)
        initialize_vault(vault, "Synthetic Root")
    else:
        initialize_vault(repository, "Synthetic Root")
        _git(repository, "init", "-b", "main")
        vault = repository
    _git(repository, "config", "user.email", "slice3@example.test")
    _git(repository, "config", "user.name", "Slice 3 Test")
    captured = capture_text("base body\n", title="Conflict target", vault=str(vault))
    source = vault / captured.relative_path
    relative = source.relative_to(repository)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "base")
    base = source.read_bytes()
    _git(repository, "checkout", "-b", "conflict")
    source.write_bytes(base + b"branch change\n")
    _git(repository, "add", "--", relative.as_posix())
    _git(repository, "commit", "-m", "branch change")
    _git(repository, "checkout", "main")
    source.write_bytes(base + b"main change\n")
    _git(repository, "add", "--", relative.as_posix())
    _git(repository, "commit", "-m", "main change")
    assert _git(repository, "merge", "conflict", check=False).returncode == 1
    return repository, vault, source, captured.object_id


def test_classify_refuses_genuine_target_git_conflicts_at_top_level_and_nested_vault(tmp_path: Path) -> None:
    for nested in (False, True):
        repository, vault, source, object_id = _create_target_conflict(tmp_path / str(nested), nested=nested)
        relative = source.relative_to(repository)
        before_bytes = source.read_bytes()
        before_index = _git(repository, "ls-files", "-s").stdout
        before_unmerged = _assert_unmerged(repository, relative)

        with pytest.raises(CaptureRefusal, match="unresolved in the Git index"):
            classify_capture(object_id, "claim", vault=str(vault))

        assert source.read_bytes() == before_bytes
        assert not list((vault / "30_resources").glob("resource-*.md"))
        assert _git(repository, "ls-files", "-s").stdout == before_index
        assert _assert_unmerged(repository, relative) == before_unmerged
        assert _git(repository, "status", "--short", "--", relative.as_posix()).stdout.startswith("UU")


def test_classify_ignores_unrelated_git_conflict_and_leaves_index_untouched(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "slice3@example.test")
    _git(repository, "config", "user.name", "Slice 3 Test")
    vault = repository / "vault"
    initialize_vault(vault, "Synthetic Root")
    unrelated = repository / "unrelated.txt"
    unrelated.write_text("base\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "base")
    captured = capture_text("body", vault=str(vault))
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "capture")
    _git(repository, "checkout", "-b", "conflict")
    unrelated.write_text("branch\n", encoding="utf-8")
    _git(repository, "add", "unrelated.txt")
    _git(repository, "commit", "-m", "branch change")
    _git(repository, "checkout", "main")
    unrelated.write_text("main\n", encoding="utf-8")
    _git(repository, "add", "unrelated.txt")
    _git(repository, "commit", "-m", "main change")
    assert _git(repository, "merge", "conflict", check=False).returncode == 1
    before_index = _git(repository, "ls-files", "-s").stdout
    _assert_unmerged(repository, Path("unrelated.txt"))
    target_relative = (vault / captured.relative_path).relative_to(repository)
    assert not _git(repository, "ls-files", "-u", "--", target_relative.as_posix()).stdout

    result = classify_capture(captured.object_id, "claim", vault=str(vault))

    assert (vault / result.relative_path).exists()
    assert _git(repository, "ls-files", "-s").stdout == before_index
    _assert_unmerged(repository, Path("unrelated.txt"))


def test_classify_allows_staged_target_and_dirty_untracked_unrelated_state(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "slice3@example.test")
    _git(repository, "config", "user.name", "Slice 3 Test")
    vault = repository / "vault"
    initialize_vault(vault, "Synthetic Root")
    unrelated = repository / "unrelated.txt"
    unrelated.write_text("base\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "base")
    captured = capture_text("body", vault=str(vault))
    source = vault / captured.relative_path
    _git(repository, "add", "--", source.relative_to(repository).as_posix())
    unrelated.write_text("dirty\n", encoding="utf-8")
    untracked = repository / "untracked.txt"
    untracked.write_text("untracked\n", encoding="utf-8")
    before_index = _git(repository, "ls-files", "-s").stdout
    before_unrelated = unrelated.read_bytes()
    before_untracked = untracked.read_bytes()

    result = classify_capture(captured.object_id, "claim", vault=str(vault))

    assert (vault / result.relative_path).exists()
    assert _git(repository, "ls-files", "-s").stdout == before_index
    assert unrelated.read_bytes() == before_unrelated
    assert untracked.read_bytes() == before_untracked


def test_classify_cli_clean_refusals_state_no_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    duplicate = vault / "20_areas" / "duplicate.md"
    duplicate.write_bytes((vault / captured.relative_path).read_bytes())
    assert main(["classify", captured.object_id, "--class", "claim", "--vault", str(vault)]) == 1
    duplicate_output = capsys.readouterr().err
    assert captured.object_id in duplicate_output and "requested class=claim" in duplicate_output
    assert "No changes were made." in duplicate_output

    monkeypatch.setattr("kv_tools.capture.read_default_vault", lambda: None)
    assert main(["classify", captured.object_id, "--class", "claim"], environ={}) == 1
    routing_output = capsys.readouterr().err
    assert captured.object_id in routing_output and "requested class=claim" in routing_output
    assert "No changes were made." in routing_output


@pytest.mark.parametrize(
    ("knowledge_class", "state"),
    [
        ("claim", "unassessed"), ("observation", "recorded"), ("practice", "candidate"),
        ("decision", "proposed"), ("concept", "emerging"),
        ("operating_knowledge", "proposed"), ("hypothesis", "unresolved"),
    ],
)
def test_classify_preserves_one_identity_and_exact_body_bytes(tmp_path: Path, knowledge_class: str, state: str) -> None:
    vault = make_vault(tmp_path, knowledge_class)
    body = b"# Rationale\r\n\r\nUnicode e\xcc\x81 and \xce\xbb\rbare CR\nno final newline"
    captured = capture_text(body.decode("utf-8"), title="Same continuing object", vault=str(vault))
    source = vault / captured.relative_path
    assert source.read_bytes().endswith(body)

    result = classify_capture(captured.object_id, knowledge_class, vault=str(vault))

    destination = vault / result.relative_path
    assert not source.exists() and destination.exists()
    document = parse_markdown(destination)
    assert document.data["id"] == captured.object_id
    assert document.data["kind"] == "resource"
    assert document.data["knowledge_class"] == knowledge_class
    assert document.data["knowledge_state"] == state
    assert destination.read_bytes().endswith(body)
    assert len(list(vault.rglob("*.md"))) == 4
    assert validate_vault(vault).status == "PASS"
    assert not list(vault.rglob(".kv-classify-*"))


def test_classify_refuses_non_capture_duplicate_and_invalid_decision_without_mutation(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("No Rationale heading here", title="Decision", vault=str(vault))
    source = vault / captured.relative_path
    before = source.read_bytes()
    with pytest.raises(CaptureRefusal, match="introduce validation errors"):
        classify_capture(captured.object_id, "decision", vault=str(vault))
    assert source.read_bytes() == before

    success = classify_capture(captured.object_id, "claim", vault=str(vault))
    with pytest.raises(CaptureRefusal, match="not an active kv-v0 Capture"):
        classify_capture(success.object_id, "claim", vault=str(vault))

    duplicate = vault / "20_areas/duplicate.md"
    duplicate.write_bytes((vault / success.relative_path).read_bytes())
    with pytest.raises(CaptureRefusal, match="KV-ID-DUPLICATE"):
        classify_capture(success.object_id, "claim", vault=str(vault))


def test_classify_cli_reports_exact_surface_and_refusal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    assert main(["classify", captured.object_id, "--class", "observation", "--vault", str(vault)]) == 0
    output = capsys.readouterr().out
    assert captured.object_id in output and "Class: observation" in output and "Initial state: recorded" in output
    assert main(["classify", captured.object_id, "--class", "observation", "--vault", str(vault)]) == 1
    assert "No changes were made." in capsys.readouterr().err


def test_classify_handles_final_resource_path_and_detects_external_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", title="Already at destination", vault=str(vault))
    source = vault / captured.relative_path
    final = vault / "30_resources" / f"resource-already-at-destination-{captured.object_id[-12:]}.md"
    source.replace(final)
    result = classify_capture(captured.object_id, "concept", vault=str(vault))
    assert result.relative_path == final.relative_to(vault)
    assert parse_markdown(final).data["kind"] == "resource"

    second = capture_text("body", vault=str(vault))
    second_source = vault / second.relative_path
    original = classification_module._prospective_validate
    def interfere(*args, **kwargs):
        second_source.write_bytes(second_source.read_bytes() + b"external change")
        return original(*args, **kwargs)
    monkeypatch.setattr(classification_module, "_prospective_validate", interfere)
    with pytest.raises(CaptureRefusal, match="changed before mutation"):
        classify_capture(second.object_id, "claim", vault=str(vault))


def test_classify_uses_deterministic_full_id_collision_extension(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", title="Collision", vault=str(vault))
    collision = vault / "30_resources" / f"resource-collision-{captured.object_id[-12:]}.md"
    collision.write_text("noncanonical collision marker", encoding="utf-8")
    result = classify_capture(captured.object_id, "claim", vault=str(vault))
    assert result.relative_path.name.endswith(f"-{captured.object_id.removeprefix('kv-')}.md")


def test_classify_restores_exact_original_after_post_mutation_validation_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("rollback body\r\n", vault=str(vault))
    source = vault / captured.relative_path
    before = source.read_bytes()
    original = classification_module.validate_vault
    def fail_final(path, *args, **kwargs):
        if Path(path) == vault and not source.exists():
            return ValidationReport(execution_diagnostics=["synthetic final verification failure"])
        return original(path, *args, **kwargs)
    monkeypatch.setattr(classification_module, "validate_vault", fail_final)
    with pytest.raises(Exception, match="PROVEN ROLLBACK"):
        classify_capture(captured.object_id, "claim", vault=str(vault))
    assert source.read_bytes() == before
    assert not list((vault / "30_resources").glob("resource-*.md"))


def test_classify_routing_precedence_and_no_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    explicit, environment, configured = (make_vault(tmp_path, name) for name in ("explicit", "environment", "configured"))
    monkeypatch.setattr("kv_tools.capture.read_default_vault", lambda: configured)
    captured = capture_text("body", vault=str(explicit))
    result = classify_capture(captured.object_id, "claim", vault=str(explicit), environ={"KV_VAULT": "relative"})
    assert (explicit / result.relative_path).exists()

    captured = capture_text("body", vault=str(environment))
    result = classify_capture(captured.object_id, "claim", environ={"KV_VAULT": str(environment)})
    assert (environment / result.relative_path).exists()

    captured = capture_text("body", vault=str(configured))
    result = classify_capture(captured.object_id, "claim", environ={})
    assert (configured / result.relative_path).exists()

    monkeypatch.chdir(explicit)
    monkeypatch.setattr("kv_tools.capture.read_default_vault", lambda: None)
    with pytest.raises(CaptureRefusal, match="No Vault target"):
        classify_capture(captured.object_id, "claim", environ={})
    with pytest.raises(CaptureRefusal, match="absolute"):
        classify_capture(captured.object_id, "claim", environ={"KV_VAULT": "relative"})
    with pytest.raises(CaptureRefusal, match="not a directory"):
        classify_capture(captured.object_id, "claim", vault=str(tmp_path / "missing"), environ={"KV_VAULT": str(environment)})


def test_classify_scope_reference_integrity_and_unrelated_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    source = vault / captured.relative_path
    before = source.read_bytes()
    root = vault / "20_areas/root.md"
    original = classification_module._prospective_validate

    def invalidate_scope(*args, **kwargs):
        result = original(*args, **kwargs)
        root.write_text(root.read_text(encoding="utf-8").replace("kind: area", "kind: index"), encoding="utf-8")
        return result

    monkeypatch.setattr(classification_module, "_prospective_validate", invalidate_scope)
    with pytest.raises(CaptureRefusal, match="governing schema is invalid"):
        classify_capture(captured.object_id, "claim", vault=str(vault))
    assert source.read_bytes() == before
    assert not list((vault / "30_resources").glob("resource-*.md"))

    vault = make_vault(tmp_path, "unrelated")
    captured = capture_text("body", vault=str(vault))
    (vault / "00_index/unrelated.md").write_text("not valid markdown", encoding="utf-8")
    result = classify_capture(captured.object_id, "claim", vault=str(vault))
    assert (vault / result.relative_path).exists()


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("kv-00000000-0000-7000-8000-000000000000", "Target Capture is invalid"),
        (None, "Target Capture is invalid"),
    ],
)
def test_classify_blocks_invalid_scope_and_provenance_references(tmp_path: Path, replacement: str | None, message: str) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    source = vault / captured.relative_path
    text = source.read_text(encoding="utf-8")
    if replacement is not None:
        text = text.replace(parse_markdown(source).data["scope"], replacement)
    else:
        text = text.replace("- kind: operator", "- kind: derived\n  ref: kv-00000000-0000-7000-8000-000000000000")
    source.write_text(text, encoding="utf-8")
    with pytest.raises(CaptureRefusal, match=message):
        classify_capture(captured.object_id, "claim", vault=str(vault))


def test_classify_accepts_historical_scope_and_ignores_referenced_body_only_edits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    root = vault / "20_areas/root.md"
    root.write_text(root.read_text(encoding="utf-8").replace("state: active", "state: archived"), encoding="utf-8")
    captured = capture_text("body", vault=str(vault))
    original = classification_module._prospective_validate

    def edit_nonsemantic_body(*args, **kwargs):
        result = original(*args, **kwargs)
        root.write_bytes(root.read_bytes() + b"\nnon-semantic body edit\n")
        return result

    monkeypatch.setattr(classification_module, "_prospective_validate", edit_nonsemantic_body)
    result = classify_capture(captured.object_id, "claim", vault=str(vault))
    assert (vault / result.relative_path).exists()


def test_classify_uses_shared_lock_and_recovers_stale_lock(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    lock = vault / ".kv-capture.lock"
    lock.write_text(json.dumps({"pid": os.getpid(), "created": 0, "token": "live"}), encoding="utf-8")
    with pytest.raises(CaptureRefusal, match="Another cooperating"):
        classify_capture(captured.object_id, "claim", vault=str(vault), lock_timeout_seconds=0.01)
    lock.unlink()
    lock.write_text(json.dumps({"pid": 999_999_999, "created": 0, "token": "stale"}), encoding="utf-8")
    result = classify_capture(captured.object_id, "claim", vault=str(vault))
    assert (vault / result.relative_path).exists()
    assert not lock.exists()


def test_classify_pre_mutation_and_rollback_failure_truthfulness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    source = vault / captured.relative_path
    before = source.read_bytes()
    monkeypatch.setattr(classification_module.shutil, "copytree", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("synthetic pre-mutation failure")))
    with pytest.raises(CaptureExecutionError, match="synthetic pre-mutation failure"):
        classify_capture(captured.object_id, "claim", vault=str(vault))
    assert source.read_bytes() == before
    assert not list(vault.rglob(".kv-classify-*"))

    monkeypatch.undo()
    original_link = classification_module.os.link
    monkeypatch.setattr(classification_module.os, "link", lambda *args: (_ for _ in ()).throw(OSError("synthetic publication failure")))
    with pytest.raises(Exception, match="PROVEN ROLLBACK"):
        classify_capture(captured.object_id, "claim", vault=str(vault))
    assert source.read_bytes() == before
    assert not list(vault.rglob(".kv-classify-*"))
    monkeypatch.setattr(classification_module.os, "link", original_link)


def test_classify_indeterminate_rollback_failure_preserves_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    source = vault / captured.relative_path
    monkeypatch.setattr(classification_module.os, "link", lambda *args: (_ for _ in ()).throw(OSError("synthetic publication failure")))
    original_replace = classification_module.os.replace

    def fail_inner_restore(source_path, destination_path):
        if Path(source_path).name.startswith(".kv-classify-backup-") and Path(destination_path) == source:
            raise OSError("synthetic rollback failure")
        return original_replace(source_path, destination_path)

    monkeypatch.setattr(classification_module.os, "replace", fail_inner_restore)
    monkeypatch.setattr(classification_module, "_restore", lambda *args: False)
    with pytest.raises(Exception, match="INCOMPLETE / INDETERMINATE"):
        classify_capture(captured.object_id, "claim", vault=str(vault))
    assert list(vault.rglob(".kv-classify-backup-*.tmp"))
    assert not source.exists()


def test_classify_refuses_target_symlink_when_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    source = vault / captured.relative_path
    original = classification_module._prospective_validate

    def replace_with_link(*args, **kwargs):
        result = original(*args, **kwargs)
        replacement = source.with_name("replacement.md")
        source.replace(replacement)
        try:
            source.symlink_to(replacement)
        except OSError:
            pytest.skip("Windows symlink creation is unavailable in this environment.")
        return result

    monkeypatch.setattr(classification_module, "_prospective_validate", replace_with_link)
    with pytest.raises(CaptureRefusal, match="ordinary regular file"):
        classify_capture(captured.object_id, "claim", vault=str(vault))
    assert not list((vault / "30_resources").glob("resource-*.md"))


def test_unrelated_symlink_warning_is_nonblocking_and_surfaced(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    unrelated = vault / "00_index/unrelated-link.md"
    try:
        unrelated.symlink_to(vault / "00_index/missing.md")
    except OSError:
        pytest.skip("Windows symlink creation is unavailable in this environment.")
    assert main(["classify", captured.object_id, "--class", "claim", "--vault", str(vault)]) == 0
    assert "pre-existing conformance error" in capsys.readouterr().err


def test_target_self_scope_and_provenance_cycle_refuse(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    captured = capture_text("body", vault=str(vault))
    source = vault / captured.relative_path
    before = source.read_bytes()
    source.write_text(source.read_text(encoding="utf-8").replace(parse_markdown(source).data["scope"], captured.object_id), encoding="utf-8")
    with pytest.raises(CaptureRefusal, match="self-scope"):
        classify_capture(captured.object_id, "claim", vault=str(vault))
    assert source.read_bytes() != before
    assert not list((vault / "30_resources").glob("resource-*.md"))


def test_classify_preserves_valid_relationships(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    root_id = parse_markdown(vault / "20_areas/root.md").data["id"]
    captured = capture_text("body", vault=str(vault))
    source = vault / captured.relative_path
    source.write_text(source.read_text(encoding="utf-8").replace("created:", f"relationships:\n- relation: related_to\n  ref: {root_id}\ncreated:"), encoding="utf-8")
    result = classify_capture(captured.object_id, "claim", vault=str(vault))
    resource = parse_markdown(vault / result.relative_path)
    assert resource.data["relationships"] == [{"relation": "related_to", "ref": root_id}]
    assert validate_vault(vault).status == "PASS"


@pytest.mark.parametrize("point", ["mkstemp", "write", "flush", "fsync", "replace"])
def test_f5_pre_mutation_failures_are_known_no_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str) -> None:
    vault = make_vault(tmp_path, point)
    captured = capture_text("body", vault=str(vault)); source = vault / captured.relative_path; before = source.read_bytes()
    reached = {"value": False}
    if point == "mkstemp":
        monkeypatch.setattr(classification_module.tempfile, "mkstemp", lambda **kwargs: (_ for _ in ()).throw(OSError("mkstemp")))
    elif point == "write":
        original = classification_module.os.fdopen
        class Broken(io.BytesIO):
            def write(self, value): reached["value"] = True; raise OSError("write")
        monkeypatch.setattr(classification_module.os, "fdopen", lambda *args, **kwargs: Broken() if (args[1] if len(args) > 1 else kwargs.get("mode")) == "wb" else original(*args, **kwargs))
    elif point == "flush":
        original = classification_module.os.fdopen
        class Broken(io.BytesIO):
            def flush(self): reached["value"] = True; raise OSError("flush")
        monkeypatch.setattr(classification_module.os, "fdopen", lambda *args, **kwargs: Broken() if (args[1] if len(args) > 1 else kwargs.get("mode")) == "wb" else original(*args, **kwargs))
    elif point == "fsync":
        original = classification_module.os.fsync; calls = {"count": 0}
        def fail_candidate(fd):
            calls["count"] += 1
            if calls["count"] > 1: raise OSError("fsync")
            return original(fd)
        monkeypatch.setattr(classification_module.os, "fsync", fail_candidate)
    else:
        original = classification_module.os.replace
        monkeypatch.setattr(classification_module.os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError("replace")) if Path(src) == source else original(src, dst))
    with pytest.raises(CaptureExecutionError, match="KNOWN NO-WRITE"):
        classify_capture(captured.object_id, "claim", vault=str(vault))
    assert source.read_bytes() == before and not list((vault / "30_resources").glob("resource-*.md"))
    if point not in {"write", "flush"}:
        assert not list(vault.rglob(".kv-classify-*"))
    assert not (vault / ".kv-capture.lock").exists()
    if point in {"write", "flush"}: assert reached["value"]


def test_f5_cli_labels_all_execution_outcomes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path); captured = capture_text("body", vault=str(vault))
    monkeypatch.setattr("kv_tools.cli.classify_capture", lambda *a, **k: (_ for _ in ()).throw(CaptureExecutionError("KNOWN NO-WRITE")))
    assert main(["classify", captured.object_id, "--class", "claim", "--vault", str(vault)]) == 2
    assert "KNOWN NO-WRITE" in capsys.readouterr().err
    monkeypatch.setattr("kv_tools.cli.classify_capture", lambda *a, **k: (_ for _ in ()).throw(CaptureExecutionError("PROVEN ROLLBACK")))
    assert main(["classify", captured.object_id, "--class", "claim", "--vault", str(vault)]) == 2
    assert "PROVEN ROLLBACK" in capsys.readouterr().err
    monkeypatch.setattr("kv_tools.cli.classify_capture", lambda *a, **k: (_ for _ in ()).throw(CaptureExecutionError("INCOMPLETE / INDETERMINATE", indeterminate=True)))
    assert main(["classify", captured.object_id, "--class", "claim", "--vault", str(vault)]) == 2
    assert "Do not blindly retry" in capsys.readouterr().err


@pytest.mark.parametrize("point", ["publication", "bytes", "validation"])
def test_f5_post_mutation_failures_prove_rollback_via_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], point: str) -> None:
    vault = make_vault(tmp_path, point); captured = capture_text("body", vault=str(vault)); source = vault / captured.relative_path; before = source.read_bytes()
    if point == "publication":
        monkeypatch.setattr(classification_module.os, "link", lambda *a: (_ for _ in ()).throw(OSError("publication")))
    elif point == "bytes":
        original = Path.read_bytes
        monkeypatch.setattr(Path, "read_bytes", lambda path: b"wrong" if path.parent.name == "30_resources" and path.suffix == ".md" else original(path))
    else:
        original = classification_module.validate_vault
        monkeypatch.setattr(classification_module, "validate_vault", lambda path, *a, **k: ValidationReport(execution_diagnostics=["final validation"]) if Path(path) == vault and not source.exists() else original(path, *a, **k))
    assert main(["classify", captured.object_id, "--class", "claim", "--vault", str(vault)]) == 2
    assert "PROVEN ROLLBACK" in capsys.readouterr().err
    assert source.read_bytes() == before and not list((vault / "30_resources").glob("resource-*.md"))
    assert not list(vault.rglob(".kv-classify-*")) and not (vault / ".kv-capture.lock").exists()


def test_f5_cli_indeterminate_preserves_rollback_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path); captured = capture_text("body", vault=str(vault)); source = vault / captured.relative_path
    original_replace = classification_module.os.replace
    monkeypatch.setattr(classification_module.os, "link", lambda *a: (_ for _ in ()).throw(OSError("publication")))
    monkeypatch.setattr(classification_module.os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError("rollback")) if Path(src).name.startswith(".kv-classify-backup-") and Path(dst) == source else original_replace(src, dst))
    monkeypatch.setattr(classification_module, "_restore", lambda *a: False)
    assert main(["classify", captured.object_id, "--class", "claim", "--vault", str(vault)]) == 2
    text = capsys.readouterr().err
    assert captured.object_id in text and str(source) in text and "30_resources" in text and "before another canonical write" in text and "Do not blindly retry" in text
    assert list(vault.rglob(".kv-classify-backup-*.tmp")) and not source.exists()
