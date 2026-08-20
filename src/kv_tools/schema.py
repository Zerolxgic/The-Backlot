from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from .models import VaultObject

_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


@dataclass(frozen=True)
class SchemaContract:
    markdown_template: str
    machine_schema: dict[str, Any]


def distribution_template() -> str:
    return files("kv_tools.resources").joinpath("kv-v0-schema.md.tmpl").read_text(encoding="utf-8")


def supported_contract() -> SchemaContract:
    template = distribution_template()
    match = _BLOCK.search(template)
    if not match:
        raise RuntimeError("The packaged kv-v0 distribution has no embedded JSON Schema.")
    return SchemaContract(template, json.loads(match.group(1)))


def instance_contract(obj: VaultObject) -> dict[str, Any] | None:
    match = _BLOCK.search(obj.document.body)
    return json.loads(match.group(1)) if match else None


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
