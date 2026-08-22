from __future__ import annotations

import json
import os
import sys
import tempfile
import tomllib
from pathlib import Path


class ConfigurationError(ValueError):
    """A configuration value is missing or does not match the Slice 2 contract."""


class ConfigurationExecutionError(RuntimeError):
    """The local configuration could not be read or safely updated."""


def config_path() -> Path:
    """Return the per-user, noncanonical Knowledge Vault configuration path."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "Knowledge Vault" / "config.toml"


def _read(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationExecutionError(f"Could not read configuration: {path}: {exc}") from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"Configuration is malformed TOML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError("Configuration must be a TOML table.")
    for key, value in data.items():
        if key != "default_vault":
            category = "table" if isinstance(value, dict) else "key"
            raise ConfigurationError(f"Configuration contains unsupported {category}: {key}.")
    value = data.get("default_vault")
    if value is None:
        return {}
    if not isinstance(value, str):
        raise ConfigurationError("Configuration default_vault must be a string path.")
    if not value:
        raise ConfigurationError("Configuration default_vault must not be empty.")
    location = Path(value)
    if not location.is_absolute():
        raise ConfigurationError("Configuration default_vault must be an absolute path.")
    return {"default_vault": value}


def read_default_vault(path: Path | None = None) -> Path | None:
    data = _read(path or config_path())
    value = data.get("default_vault")
    return Path(value) if value is not None else None


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


def _replace(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def _write_default_vault(path: Path, vault: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=path.parent)
    except OSError as exc:
        raise ConfigurationExecutionError(f"Could not prepare configuration update: {exc}") from exc
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(f"default_vault = {json.dumps(str(vault), ensure_ascii=False)}\n")
            handle.flush()
            os.fsync(handle.fileno())
        _replace(temporary, path)
        _fsync_directory(path.parent)
    except OSError as exc:
        raise ConfigurationExecutionError(f"Could not safely update configuration: {exc}") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def set_default_vault(path_value: str, verify_target, *, path: Path | None = None) -> Path:
    """Verify and atomically persist the single supported machine-local setting."""
    location = path or config_path()
    _read(location)  # Existing malformed or unsupported configuration is never overwritten.
    if not path_value:
        raise ConfigurationError("Default Vault path must not be empty.")
    try:
        normalized = Path(path_value).resolve(strict=True)
    except OSError as exc:
        raise ConfigurationError(f"Default Vault path cannot be resolved: {path_value}: {exc}") from exc
    verify_target(normalized)
    _write_default_vault(location, normalized)
    return normalized


def clear_default_vault(*, path: Path | None = None) -> bool:
    """Clear the only supported setting. Returns whether a setting was present."""
    location = path or config_path()
    data = _read(location)
    if "default_vault" not in data:
        return False
    try:
        location.unlink()
        _fsync_directory(location.parent)
    except OSError as exc:
        raise ConfigurationExecutionError(f"Could not clear configuration: {exc}") from exc
    return True
