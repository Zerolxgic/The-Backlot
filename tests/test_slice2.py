from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path

import pytest
import yaml

from kv_tools import capture as capture_module
from kv_tools import configuration
from kv_tools.capture import CaptureExecutionError, CaptureRefusal, capture_text, resolve_vault_target, verify_vault_target
from kv_tools.cli import main
from kv_tools.configuration import ConfigurationError, ConfigurationExecutionError
from kv_tools.initializer import initialize_vault
from kv_tools.parser import parse_markdown
from kv_tools.validator import validate_vault


class InteractiveInput(io.StringIO):
    def isatty(self) -> bool:
        return True


class RedirectedInput(io.StringIO):
    def isatty(self) -> bool:
        return False


def make_vault(tmp_path: Path, name: str = "vault") -> Path:
    vault = tmp_path / name
    initialize_vault(vault, "Synthetic Root")
    return vault


def root_id(vault: Path) -> str:
    return parse_markdown(vault / "20_areas/root.md").data["id"]


def captures(vault: Path) -> list[Path]:
    return sorted((vault / "05_inbox").glob("*.md"))


def write_object(vault: Path, relative: str, metadata: dict[str, object], body: str = "# Synthetic\n") -> Path:
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True) + "---\n" + body, encoding="utf-8")
    return path


def replace_metadata(path: Path, **changes: object) -> None:
    parsed = parse_markdown(path)
    path.write_text(
        "---\n" + yaml.safe_dump(parsed.data | changes, sort_keys=False, allow_unicode=True) + "---\n" + parsed.body,
        encoding="utf-8",
    )


def fresh_id(number: int) -> str:
    return f"kv-018f0000-0000-7000-8000-{number:012d}"


def tree(vault: Path) -> dict[str, bytes]:
    return {str(path.relative_to(vault)): path.read_bytes() for path in vault.rglob("*") if path.is_file()}


def test_capture_cli_content_channels_and_verbatim_body(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path)
    body = "First line\n\n  leading spaces stay\nUnicode: λ\n"
    assert main(["capture", "--text", body, "--vault", str(vault)], stdin=InteractiveInput()) == 0
    document = parse_markdown(captures(vault)[0])
    assert document.body == body
    assert "leading spaces stay" not in capsys.readouterr().out

    stdin_body = "multiline\nfrom redirected stdin\n"
    assert main(["capture", "--vault", str(vault)], stdin=RedirectedInput(stdin_body)) == 0
    assert parse_markdown(captures(vault)[1]).body == stdin_body

    before = captures(vault)
    assert main(["capture", "--text", "conflict", "--vault", str(vault)], stdin=RedirectedInput("also content")) == 1
    assert main(["capture", "--vault", str(vault)], stdin=InteractiveInput()) == 1
    assert captures(vault) == before


def test_content_refusals_and_no_silent_truncation(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    for body in ("", " \t\n "):
        with pytest.raises(CaptureRefusal):
            capture_text(body, vault=str(vault))
    large = "x" * 200_000
    result = capture_text(large, vault=str(vault))
    assert parse_markdown(vault / result.relative_path).body == large


def test_title_behavior_and_duplicate_title_paths(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    explicit = capture_text("content", title="  A supplied title  ", vault=str(vault))
    assert parse_markdown(vault / explicit.relative_path).data["title"] == "  A supplied title  "
    extracted = capture_text("# Exact words from operator\nsecond line", vault=str(vault))
    assert extracted.title == "Exact words from operator"
    assert set(extracted.title.split()) <= {"Exact", "words", "from", "operator"}
    fallback = capture_text("\n---\n!!!", vault=str(vault))
    assert fallback.title == "Capture"
    same_one = capture_text("same text", title="Repeated title", vault=str(vault))
    same_two = capture_text("different text", title="Repeated title", vault=str(vault))
    assert same_one.object_id != same_two.object_id
    assert same_one.relative_path != same_two.relative_path
    for invalid in ("", " \t", "one\ntwo"):
        with pytest.raises(CaptureRefusal):
            capture_text("content", title=invalid, vault=str(vault))


def test_generated_capture_metadata_and_frontmatter_body_boundary(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    body = "The exact body begins immediately."
    result = capture_text(body, vault=str(vault))
    path = vault / result.relative_path
    document = parse_markdown(path)
    assert document.data == {
        "schema": "kv-v0",
        "id": result.object_id,
        "title": result.title,
        "kind": "capture",
        "state": "active",
        "scope": root_id(vault),
        "created": date.today().isoformat(),
        "provenance": [{"kind": "operator"}],
    }
    assert result.object_id.startswith("kv-") and result.object_id.split("-")[3].startswith("7")
    assert document.body == body
    raw = path.read_text(encoding="utf-8")
    assert raw.endswith("---\n" + body)
    assert "# " + result.title not in document.body


def test_scope_resolution_and_explicit_failure_never_falls_back(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    root = root_id(vault)
    area_id = fresh_id(41)
    write_object(
        vault,
        "20_areas/secondary.md",
        {"schema": "kv-v0", "id": area_id, "title": "Secondary", "kind": "area", "state": "active", "scope": root, "created": "2026-08-21", "provenance": [{"kind": "operator"}]},
        "# Purpose\n\nSecondary\n\n# Boundaries\n\nSynthetic\n",
    )
    assert capture_text("scoped", scope=area_id, vault=str(vault)).relative_path.parent == Path("05_inbox")
    before = captures(vault)
    for invalid_scope in (fresh_id(99), "Secondary", parse_markdown(vault / "00_index/home.md").data["id"]):
        with pytest.raises(CaptureRefusal):
            capture_text("must not fall back", scope=invalid_scope, vault=str(vault))
    assert captures(vault) == before


def test_ambiguous_identity_blocks_capture_before_scope_fallback(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    root = root_id(vault)
    write_object(
        vault,
        "20_areas/duplicate.md",
        {"schema": "kv-v0", "id": root, "title": "Duplicate", "kind": "area", "state": "active", "scope": root, "created": "2026-08-21", "provenance": [{"kind": "operator"}]},
        "# Purpose\n\nDuplicate\n\n# Boundaries\n\nSynthetic\n",
    )
    with pytest.raises(CaptureRefusal, match="KV-ID-DUPLICATE"):
        capture_text("cannot use ambiguous identity", scope=root, vault=str(vault))
    assert not captures(vault)


def test_vault_routing_precedence_short_circuit_and_no_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    explicit = make_vault(tmp_path, "explicit")
    environment = make_vault(tmp_path, "environment")
    configured = make_vault(tmp_path, "configured")
    monkeypatch.setattr(capture_module, "read_default_vault", lambda: configured)
    result = capture_text("explicit", vault=str(explicit), environ={"KV_VAULT": str(environment)})
    assert captures(explicit) == [explicit / result.relative_path]
    assert not captures(environment) and not captures(configured)

    monkeypatch.setattr(capture_module, "read_default_vault", lambda: (_ for _ in ()).throw(AssertionError("must not read config")))
    assert capture_text("still explicit", vault=str(explicit), environ={}).object_id

    monkeypatch.setattr(capture_module, "read_default_vault", lambda: configured)
    env_result = capture_text("environment", environ={"KV_VAULT": str(environment)})
    assert (environment / env_result.relative_path).exists()
    assert not (configured / env_result.relative_path).exists()

    monkeypatch.chdir(tmp_path)
    assert resolve_vault_target("explicit") == explicit.resolve()
    with pytest.raises(CaptureRefusal, match="absolute"):
        capture_text("relative environment", environ={"KV_VAULT": "environment"})
    monkeypatch.setattr(capture_module, "read_default_vault", lambda: None)
    monkeypatch.chdir(explicit)
    with pytest.raises(CaptureRefusal, match="No Vault target"):
        capture_text("no cwd discovery", environ={})


def test_invalid_selected_vault_blocks_lower_priority_routing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fallback = make_vault(tmp_path, "fallback")
    monkeypatch.setattr(capture_module, "read_default_vault", lambda: fallback)
    with pytest.raises(CaptureRefusal, match="not a directory"):
        capture_text("must not fall through", vault=str(tmp_path / "missing"), environ={"KV_VAULT": str(fallback)})
    assert not captures(fallback)


def test_machine_configuration_commands_and_no_canonical_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path)
    config_file = tmp_path / "machine" / "Knowledge Vault" / "config.toml"
    monkeypatch.setattr(configuration, "config_path", lambda: config_file)
    before = tree(vault)
    assert main(["config", "show"]) == 0
    assert "No default Vault configured." in capsys.readouterr().out
    assert main(["config", "clear-default-vault"]) == 0
    assert "already unset" in capsys.readouterr().out
    assert main(["config", "set-default-vault", str(vault)]) == 0
    assert configuration.read_default_vault() == vault.resolve()
    assert main(["config", "show"]) == 0
    assert str(vault.resolve()) in capsys.readouterr().out
    assert main(["config", "clear-default-vault"]) == 0
    assert not config_file.exists()
    assert tree(vault) == before


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not toml =", "malformed TOML"),
        ("other = 'value'", "unsupported key"),
        ("[other]\nvalue = 'x'", "unsupported table"),
        ("default_vault = 4", "must be a string"),
        ("default_vault = 'relative'", "must be an absolute"),
    ],
)
def test_machine_configuration_rejects_invalid_toml(tmp_path: Path, content: str, message: str) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError, match=message):
        configuration.read_default_vault(config_file)


def test_config_stale_target_failed_replace_and_unreadable_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    config_file = tmp_path / "config.toml"
    configuration.set_default_vault(str(vault), verify_vault_target, path=config_file)
    previous = config_file.read_bytes()
    monkeypatch.setattr(configuration, "_replace", lambda source, destination: (_ for _ in ()).throw(OSError("synthetic replacement failure")))
    with pytest.raises(ConfigurationExecutionError):
        configuration.set_default_vault(str(vault), verify_vault_target, path=config_file)
    assert config_file.read_bytes() == previous
    assert not list(config_file.parent.glob(".config-*.tmp"))

    stale = tmp_path / "stale.toml"
    stale.write_text(f"default_vault = {json.dumps(str(tmp_path / 'gone'))}\n", encoding="utf-8")
    monkeypatch.setattr(capture_module, "read_default_vault", lambda: configuration.read_default_vault(stale))
    with pytest.raises(CaptureRefusal, match="not a directory"):
        capture_text("stale config", environ={})

    unreadable = tmp_path / "unreadable.toml"
    unreadable.write_text("default_vault = 'C:/synthetic'", encoding="utf-8")
    original_read_text = Path.read_text

    def denied(path: Path, *args, **kwargs):
        if path == unreadable:
            raise OSError("synthetic unreadable configuration")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(ConfigurationExecutionError, match="Could not read configuration"):
        configuration.read_default_vault(unreadable)


def test_filename_collision_atomic_publication_and_indeterminate_outcome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    fixed = fresh_id(77)
    monkeypatch.setattr(capture_module, "_new_id", lambda: fixed)
    destination = vault / "05_inbox" / f"capture-title-{fixed[-12:]}.md"
    destination.write_text("operator-owned existing file", encoding="utf-8")
    with pytest.raises(CaptureRefusal, match="already exists"):
        capture_text("new content", title="Title", vault=str(vault))
    assert destination.read_text(encoding="utf-8") == "operator-owned existing file"

    monkeypatch.setattr(capture_module, "_new_id", lambda: fresh_id(78))
    monkeypatch.setattr(capture_module.os, "link", lambda source, target: (_ for _ in ()).throw(OSError("synthetic link failure")))
    with pytest.raises(CaptureExecutionError, match="before publication"):
        capture_text("link failure", title="Link Failure", vault=str(vault))
    assert not list((vault / "05_inbox").glob("*.tmp"))
    assert len(captures(vault)) == 1

    monkeypatch.undo()
    vault = make_vault(tmp_path, "indeterminate")
    monkeypatch.setattr(capture_module, "_fsync_directory", lambda directory: (_ for _ in ()).throw(OSError("synthetic post-link failure")))
    with pytest.raises(CaptureExecutionError) as error:
        capture_text("publication uncertainty", vault=str(vault))
    assert error.value.indeterminate
    assert len(captures(vault)) == 1


def test_bounded_existing_vault_state_and_write_critical_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    broken = vault / "30_resources/broken.md"
    broken.write_text("not frontmatter", encoding="utf-8")
    before = broken.read_bytes()
    result = capture_text("unrelated error may remain", vault=str(vault))
    assert result.baseline_errors
    assert broken.read_bytes() == before

    duplicate = make_vault(tmp_path, "duplicate")
    replace_metadata(duplicate / "00_index/home.md", id=root_id(duplicate))
    with pytest.raises(CaptureRefusal, match="KV-ID-DUPLICATE"):
        capture_text("blocked", vault=str(duplicate))

    schema_missing = make_vault(tmp_path, "schema-missing")
    replace_metadata(schema_missing / "90_meta/kv-v0-schema.md", state="archived")
    with pytest.raises(CaptureRefusal, match="KV-SCHEMA-ACTIVE"):
        capture_text("blocked", vault=str(schema_missing))

    root_missing = make_vault(tmp_path, "root-missing")
    replace_metadata(root_missing / "20_areas/root.md", scope=parse_markdown(root_missing / "00_index/home.md").data["id"])
    with pytest.raises(CaptureRefusal, match="KV-ROOT-UNIQUE"):
        capture_text("blocked", vault=str(root_missing))

    execution = make_vault(tmp_path, "execution")
    original_validate = capture_module.validate_vault

    def execution_failure(path, additional_documents=()):
        if not additional_documents:
            report = original_validate(path)
            report.execution_diagnostics.append("synthetic validator execution failure")
            return report
        return original_validate(path, additional_documents)

    monkeypatch.setattr(capture_module, "validate_vault", execution_failure)
    with pytest.raises(CaptureExecutionError, match="synthetic validator execution failure"):
        capture_text("blocked", vault=str(execution))


def test_prospective_validation_refuses_new_errors_without_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    before = captures(vault)
    monkeypatch.setattr(capture_module, "_render", lambda metadata, body: "---\nid: not-a-valid-object\n---\nbody")
    with pytest.raises(CaptureRefusal, match="KV-"):
        capture_text("candidate must fail", vault=str(vault))
    assert captures(vault) == before


def test_write_ownership_serializes_cooperating_writers_and_cleans_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    original_inspect = capture_module._inspect_baseline
    first_is_inspecting = threading.Event()
    release_first = threading.Event()
    results: list[str] = []
    failures: list[BaseException] = []

    def inspect_under_lock(path: Path):
        assert (path / ".kv-capture.lock").exists()
        if not first_is_inspecting.is_set():
            first_is_inspecting.set()
            assert release_first.wait(2)
        return original_inspect(path)

    monkeypatch.setattr(capture_module, "_inspect_baseline", inspect_under_lock)

    def writer(text: str) -> None:
        try:
            results.append(capture_text(text, vault=str(vault), lock_timeout_seconds=2).object_id)
        except BaseException as exc:  # Keep thread failure available to the assertion.
            failures.append(exc)

    first = threading.Thread(target=writer, args=("first",))
    second = threading.Thread(target=writer, args=("second",))
    first.start()
    assert first_is_inspecting.wait(2)
    second.start()
    release_first.set()
    first.join(3)
    second.join(3)
    assert not failures
    assert len(results) == 2 and len(set(results)) == 2
    assert len(captures(vault)) == 2
    assert not (vault / ".kv-capture.lock").exists()
    assert validate_vault(vault).status == "PASS"


def test_competing_and_stale_locks_do_not_strand_the_vault(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    lock = vault / ".kv-capture.lock"
    lock.write_text(json.dumps({"pid": os.getpid(), "created": 0, "token": "live"}), encoding="utf-8")
    with pytest.raises(CaptureRefusal, match="Another cooperating"):
        capture_text("competing", vault=str(vault), lock_timeout_seconds=0.05)
    lock.unlink()
    lock.write_text(json.dumps({"pid": 999_999_999, "created": 0, "token": "stale"}), encoding="utf-8")
    assert capture_text("stale cleared", vault=str(vault)).object_id
    assert not lock.exists()
    assert validate_vault(vault).status == "PASS"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process-handle liveness is platform-specific")
def test_windows_real_process_stale_lock_recovery_and_conservative_uncertainty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    lock = vault / ".kv-capture.lock"
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    try:
        lock.write_text(json.dumps({"pid": child.pid, "created": time.time(), "token": "live-child"}), encoding="utf-8")
        with pytest.raises(CaptureRefusal, match="Another cooperating"):
            capture_text("live child retains lock", vault=str(vault), lock_timeout_seconds=0.05)
    finally:
        child.terminate()
        child.wait(timeout=5)

    lock.write_text(json.dumps({"pid": child.pid, "created": time.time() - 400, "token": "dead-child"}), encoding="utf-8")
    assert capture_text("dead child lock recovers", vault=str(vault)).object_id
    assert not lock.exists()

    lock.write_text(json.dumps({"pid": 999_999_999, "created": time.time() - 400, "token": "impossible"}), encoding="utf-8")
    assert capture_text("impossible pid recovers", vault=str(vault)).object_id
    assert not lock.exists()

    lock.write_text(json.dumps({"pid": os.getpid(), "created": time.time(), "token": "uncertain"}), encoding="utf-8")
    monkeypatch.setattr(capture_module, "_windows_process_liveness", lambda pid, created: None)
    with pytest.raises(CaptureRefusal, match="Another cooperating"):
        capture_text("uncertain liveness does not steal", vault=str(vault), lock_timeout_seconds=0.05)


@pytest.mark.parametrize(
    "body",
    [
        "LF\nline\n",
        "CRLF\r\nline\r\n",
        "bare CR\rline\r",
        "mixed\rfirst\r\nsecond\nthird\r\n",
        "\r\n\r\nSurrounded by blanks\r\n\r\n",
        "Unicode λ and emoji 😀\r\nsecond line\r\n",
    ],
)
def test_publication_confirmation_is_byte_exact_for_newline_variants(tmp_path: Path, body: str) -> None:
    vault = make_vault(tmp_path)
    result = capture_text(body, vault=str(vault))
    raw = (vault / result.relative_path).read_bytes()
    assert raw.endswith(b"---\n" + body.encode("utf-8"))
    assert raw.count(b"---\n") == 2
    assert len(captures(vault)) == 1


def test_cli_distinguishes_available_stdin_content_from_nonconsole_stdin(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    command = [sys.executable, "-m", "kv_tools.cli", "capture", "--vault", str(vault)]

    empty_with_text = subprocess.Popen(
        [*command, "--text", "text in a nonconsole empty pipe"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert empty_with_text.wait(timeout=5) == 0
    assert empty_with_text.stdin is not None
    empty_with_text.stdin.close()
    assert "Captured:" in empty_with_text.stdout.read()
    assert empty_with_text.stderr.read() == ""

    empty_without_text = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert empty_without_text.wait(timeout=5) == 1
    assert empty_without_text.stdin is not None
    empty_without_text.stdin.close()
    assert "requires --text or redirected standard input" in empty_without_text.stderr.read()

    stdin_only = subprocess.run(
        command,
        input="multiline\nredirected stdin\n",
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert stdin_only.returncode == 0 and "Captured:" in stdin_only.stdout

    dual_channel = subprocess.run(
        [*command, "--text", "explicit text"],
        input="actual piped content\n",
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert dual_channel.returncode == 1
    assert "either --text or redirected standard input" in dual_channel.stderr
    assert len(captures(vault)) == 2


@pytest.mark.parametrize(
    "body",
    [
        b"LF only\nsecond line\n",
        b"CRLF only\r\nsecond line\r\n",
        b"bare CR\rsecond line\r",
        b"mixed\rfirst\r\nsecond\nthird\r\n",
        b"\r\n\r\nleading and trailing blanks\r\n\r\n",
        b"tabs\tand  multiple spaces\r\nsecond\tline\r\n",
        "Unicode e\u0301, \u00e9, \u03bb, and \U0001f600\r\nsecond line\r\n".encode("utf-8"),
    ],
)
def test_real_pipe_stdin_preserves_raw_body_bytes(tmp_path: Path, body: bytes) -> None:
    vault = make_vault(tmp_path)
    command = [sys.executable, "-m", "kv_tools.cli", "capture", "--title", "stdin fidelity", "--vault", str(vault)]
    completed = subprocess.run(command, input=body, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    assert b"Captured:" in completed.stdout
    assert b"indeterminate" not in completed.stderr.lower()
    files = captures(vault)
    assert len(files) == 1
    assert files[0].read_bytes().endswith(b"---\n" + body)


def test_disk_redirected_stdin_preserves_raw_body_bytes(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    body = "disk CRLF\r\nbare CR\rUnicode \u03bb \U0001f600 e\u0301\r\n".encode("utf-8")
    source = tmp_path / "stdin-source.txt"
    source.write_bytes(body)
    command = [sys.executable, "-m", "kv_tools.cli", "capture", "--vault", str(vault)]
    with source.open("rb") as stream:
        completed = subprocess.run(command, stdin=stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    files = captures(vault)
    assert len(files) == 1
    assert files[0].read_bytes().endswith(b"---\n" + body)


def test_custom_in_memory_stdin_and_invalid_utf8_remain_truthful(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    custom_body = "custom\r\ninput\rwith exact strings"
    assert main(["capture", "--vault", str(vault)], stdin=RedirectedInput(custom_body)) == 0
    assert captures(vault)[0].read_bytes().endswith(b"---\n" + custom_body.encode("utf-8"))

    command = [sys.executable, "-m", "kv_tools.cli", "capture", "--vault", str(vault)]
    invalid = subprocess.run(command, input=b"\xff", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    assert invalid.returncode == 2
    assert b"Could not decode redirected standard input" in invalid.stderr
    assert len(captures(vault)) == 1


@pytest.mark.parametrize(
    ("arguments", "stdin_body", "expected_title", "expected_body", "expect_escaped_title"),
    [
        (["--text", "Unicode 日本語 λ 😀\r\nsecond line\r\n"], None, "Unicode 日本語 λ 😀", "Unicode 日本語 λ 😀\r\nsecond line\r\n", True),
        (["--text", "explicit body\r\n", "--title", "Explicit 日本語 λ 😀"], None, "Explicit 日本語 λ 😀", "explicit body\r\n", True),
        (["--text", "Unicode 日本語 λ 😀 body\r\n", "--title", "ASCII title"], None, "ASCII title", "Unicode 日本語 λ 😀 body\r\n", False),
        (["--text", "ASCII body\r\n", "--title", "ASCII title"], None, "ASCII title", "ASCII body\r\n", False),
        ([], "Unicode 日本語 λ 😀\r\nstdin body\r\n".encode("utf-8"), "Unicode 日本語 λ 😀", "Unicode 日本語 λ 😀\r\nstdin body\r\n", True),
        (["--text", "Unicode 日本語 λ 😀\r\ntext body\r\n"], None, "Unicode 日本語 λ 😀", "Unicode 日本語 λ 😀\r\ntext body\r\n", True),
    ],
    ids=("auto-text", "explicit-text", "unicode-body-ascii-title", "ascii-control", "unicode-stdin", "unicode-text"),
)
def test_capture_cli_confirmation_remains_truthful_with_cp1252_stdout(
    tmp_path: Path,
    arguments: list[str],
    stdin_body: bytes | None,
    expected_title: str,
    expected_body: str,
    expect_escaped_title: bool,
) -> None:
    vault = make_vault(tmp_path)
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp1252:strict"
    completed = subprocess.run(
        [sys.executable, "-m", "kv_tools.cli", "capture", *arguments, "--vault", str(vault)],
        input=stdin_body,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        timeout=5,
    )

    stdout = completed.stdout.decode("cp1252")
    stderr = completed.stderr.decode("cp1252", errors="replace")
    displayed_title = (
        expected_title.encode("cp1252", errors="backslashreplace").decode("cp1252")
        if expect_escaped_title
        else expected_title
    )
    assert completed.returncode == 0, stderr
    assert "Traceback" not in stderr
    assert f"Captured: {displayed_title}" in stdout
    assert "ID: kv-" in stdout and "Path: 05_inbox/" in stdout
    assert "No Capture was written." not in stdout and "No Capture was written." not in stderr

    files = captures(vault)
    assert len(files) == 1
    document = parse_markdown(files[0])
    assert document.data["title"] == expected_title
    assert files[0].read_bytes().endswith(b"---\n" + expected_body.encode("utf-8"))


def test_capture_cli_unicode_confirmation_remains_natural_with_utf8_stdout(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    title = "Unicode 日本語 λ 😀"
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8:strict"
    completed = subprocess.run(
        [sys.executable, "-m", "kv_tools.cli", "capture", "--text", f"{title}\r\nbody\r\n", "--vault", str(vault)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        timeout=5,
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    assert f"Captured: {title}" in completed.stdout.decode("utf-8")
    document = parse_markdown(captures(vault)[0])
    assert document.data["title"] == title
    assert captures(vault)[0].read_bytes().endswith(f"---\n{title}\r\nbody\r\n".encode("utf-8"))


def test_cli_acknowledgement_exit_states_warnings_and_help(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    vault = make_vault(tmp_path)
    assert main(["capture", "--text", "Visible title\nbody-only content should stay private", "--vault", str(vault)], stdin=InteractiveInput()) == 0
    output = capsys.readouterr().out
    assert "Captured:" in output and "ID: kv-" in output and "Path: 05_inbox/" in output
    assert "body-only content should stay private" not in output

    assert main(["capture", "--text", "", "--vault", str(vault)], stdin=InteractiveInput()) == 1
    assert "No Capture was written." in capsys.readouterr().err

    original_publish = capture_module._publish_candidate
    monkeypatch.setattr(capture_module, "_publish_candidate", lambda path, rendered: (_ for _ in ()).throw(CaptureExecutionError("synthetic pre-publication failure")))
    assert main(["capture", "--text", "execution", "--vault", str(vault)], stdin=InteractiveInput()) == 2
    assert "No Capture was written." in capsys.readouterr().err
    monkeypatch.setattr(capture_module, "_publish_candidate", original_publish)

    monkeypatch.setattr(capture_module, "_publish_candidate", lambda path, rendered: (_ for _ in ()).throw(CaptureExecutionError("synthetic uncertainty", indeterminate=True)))
    assert main(["capture", "--text", "uncertain", "--vault", str(vault)], stdin=InteractiveInput()) == 2
    assert "indeterminate" in capsys.readouterr().err
    monkeypatch.setattr(capture_module, "_publish_candidate", original_publish)

    warning_id = fresh_id(90)
    write_object(
        vault,
        "20_areas/index-in-area.md",
        {"schema": "kv-v0", "id": warning_id, "title": "Warning", "kind": "index", "state": "active", "scope": root_id(vault), "created": "2026-08-21", "provenance": [{"kind": "operator"}]},
    )
    assert main(["capture", "--text", "warning", "--vault", str(vault)], stdin=InteractiveInput()) == 0
    assert "WARNING KV-DIRECTORY-KIND" in capsys.readouterr().out

    with pytest.raises(SystemExit) as help_exit:
        main(["capture", "--help"])
    assert help_exit.value.code == 0
    help_output = capsys.readouterr().out
    assert "Capture content." in help_output and "redirected standard input" in help_output


def test_slice1_regression_init_and_validate_remain_unchanged(tmp_path: Path) -> None:
    vault = tmp_path / "slice1-vault"
    assert main(["init", str(vault), "--root-title", "Slice 1 Root"]) == 0
    assert main(["validate", str(vault)]) == 0
    assert validate_vault(vault).status == "PASS"
