from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .filesystem import NAVIGATION_DIRECTORIES, discover_markdown
from .models import ValidationReport, VaultObject
from .parser import as_object, parse_markdown
from .registry import ResolutionKind, VaultRegistry
from .schema import canonical_json, instance_contract, supported_contract

KINDS = {"index", "capture", "project", "area", "resource", "source", "tool", "map", "meta"}
STATES = {"active", "superseded", "archived"}
RESOURCE_STATES = {"claim": {"unassessed", "accepted", "contested", "rejected"}, "observation": {"recorded", "accepted", "disputed"}, "practice": {"candidate", "accepted", "rejected"}, "decision": {"proposed", "accepted", "rejected"}, "concept": {"emerging", "defined", "accepted", "rejected"}, "operating_knowledge": {"proposed", "accepted", "rejected"}, "hypothesis": {"unresolved", "supported", "refuted"}}
DIRECTORY_KIND = {"00_index": "index", "05_inbox": "capture", "10_projects": "project", "20_areas": "area", "30_resources": "resource", "40_sources": "source", "50_tools": "tool", "60_maps": "map", "90_meta": "meta"}


def _refs(value: Any, key: str = "ref") -> list[str]:
    if not isinstance(value, list): return []
    return [entry.get(key) for entry in value if isinstance(entry, dict) and isinstance(entry.get(key), str)]


def _reference(report: ValidationReport, registry: VaultRegistry, obj: VaultObject, ref: str, field: str, rule: str, *, allow_self: bool = False) -> VaultObject | None:
    if obj.id == ref and not allow_self:
        report.add("KV-REF-SELF", "ERROR", "Self-reference is not permitted for this field.", obj, field, (ref,)); return None
    resolution = registry.resolve(ref)
    if resolution.kind is ResolutionKind.MISSING:
        report.add(rule, "ERROR", f"Reference does not resolve: {ref}.", obj, field, (ref,))
    elif resolution.kind is ResolutionKind.AMBIGUOUS:
        report.add("KV-REF-AMBIGUOUS", "ERROR", f"Reference is ambiguous: {ref}.", obj, field, (ref,))
    return resolution.object


def _cycle(report: ValidationReport, objects: Iterable[VaultObject], edges, rule: str, name: str) -> None:
    graph = {obj.id: [ref for ref in edges(obj) if isinstance(ref, str)] for obj in objects if obj.id}
    seen: set[str] = set(); active: set[str] = set()
    def visit(node: str) -> bool:
        if node in active: return True
        if node in seen: return False
        seen.add(node); active.add(node)
        found = any(visit(target) for target in graph.get(node, ()) if target in graph)
        active.remove(node); return found
    if any(visit(node) for node in graph):
        report.add(rule, "ERROR", f"{name} contains a cycle.")


def validate_vault(root: Path | str) -> ValidationReport:
    root = Path(root)
    report = ValidationReport()
    if not root.exists() or not root.is_dir():
        report.execution_diagnostics.append(f"Vault path is not a directory: {root}")
        return report
    for name in NAVIGATION_DIRECTORIES:
        if not (root / name).is_dir(): report.add("KV-FS-DIRECTORY", "ERROR", f"Required navigation directory is missing: {name}.")
    paths, symlinks = discover_markdown(root)
    for path in symlinks: report.add("KV-FS-SYMLINK", "ERROR", "Canonical-object symlinks are not followed.", VaultObject(parse_markdown(path), {}))
    documents = [parse_markdown(path) for path in paths]
    objects: list[VaultObject] = []
    for document in documents:
        if document.diagnostics:
            for diag in document.diagnostics: report.add("KV-PARSE-FRONTMATTER", "ERROR", diag.message, VaultObject(document, {}), diag.field)
        else:
            objects.append(as_object(document))
    registry = VaultRegistry(objects)
    for object_id, duplicates in registry.duplicates().items():
        for obj in duplicates: report.add("KV-ID-DUPLICATE", "ERROR", f"Persisted ID is duplicated: {object_id}.", obj, "id")
    try: contract = supported_contract()
    except Exception as exc:
        report.execution_diagnostics.append(str(exc)); return report
    schema_objects = [o for o in objects if o.metadata.get("kind") == "meta" and o.metadata.get("meta_type") == "schema" and o.metadata.get("defines_schema") == "kv-v0" and o.metadata.get("state") == "active"]
    if len(schema_objects) != 1:
        report.add("KV-SCHEMA-ACTIVE", "ERROR", f"Expected exactly one active kv-v0 Schema Meta; found {len(schema_objects)}.")
    else:
        embedded = instance_contract(schema_objects[0])
        if embedded is None: report.add("KV-SCHEMA-EMBEDDED", "ERROR", "Schema Meta has no embedded machine-readable JSON Schema.", schema_objects[0])
        elif canonical_json(embedded) != canonical_json(contract.machine_schema): report.add("KV-SCHEMA-DRIFT", "ERROR", "kv-v0 machine contract materially differs from the supported distribution.", schema_objects[0])
    structural = Draft202012Validator(contract.machine_schema)
    for obj in objects:
        metadata = obj.metadata
        for error in sorted(structural.iter_errors(metadata), key=lambda e: list(e.path)):
            field = str(next(iter(error.path), "frontmatter")); report.add("KV-STRUCTURE", "ERROR", error.message, obj, field)
        _semantic_object(report, obj, root)
    _integrity(report, objects, registry)
    return report


def _semantic_object(report: ValidationReport, obj: VaultObject, root: Path) -> None:
    m = obj.metadata
    allowed = {"schema", "id", "title", "kind", "state", "scope", "created", "provenance", "superseded_by", "relationships"}
    allowed |= {"resource": {"knowledge_class", "knowledge_state", "evidence", "authority"}, "project": {"canonical_truth"}, "source": {"source_type", "locators", "creators", "published", "accessed"}, "tool": {"tool_type", "adoption_state", "authority", "official_links"}, "meta": {"meta_type", "authority", "defines_schema"}}.get(m.get("kind"), set())
    for key in m.keys() - allowed:
        report.add("KV-METADATA-UNEXPECTED", "ERROR", f"Field is not allowed for kind {m.get('kind')!r}: {key}.", obj, key)
    if m.get("schema") != "kv-v0": report.add("KV-SCHEMA-DECLARED", "ERROR", "Object must declare schema: kv-v0.", obj, "schema")
    if m.get("kind") not in KINDS: report.add("KV-KIND", "ERROR", "kind is not a controlled kv-v0 value.", obj, "kind")
    if m.get("state") not in STATES: report.add("KV-STATE", "ERROR", "state is not a controlled lifecycle value.", obj, "state")
    try: date.fromisoformat(m.get("created", ""))
    except (TypeError, ValueError): report.add("KV-CREATED", "ERROR", "created must be YYYY-MM-DD.", obj, "created")
    provenance = m.get("provenance")
    if not isinstance(provenance, list) or not provenance: report.add("KV-PROVENANCE", "ERROR", "provenance must be a non-empty list.", obj, "provenance")
    elif any(not isinstance(x, dict) or x.get("kind") not in {"operator","external","source","project","agent","derived"} for x in provenance): report.add("KV-PROVENANCE", "ERROR", "provenance uses an invalid kind or shape.", obj, "provenance")
    parent = obj.document.path.parent.name
    expected = DIRECTORY_KIND.get(parent)
    if expected and m.get("kind") != expected: report.add("KV-DIRECTORY-KIND", "WARNING", f"Directory suggests {expected}, but metadata declares {m.get('kind')!r}; metadata remains authoritative.", obj, "kind")
    if m.get("state") == "superseded":
        if not isinstance(m.get("superseded_by"), list) or not m["superseded_by"]: report.add("KV-SUPERSEDED-REQUIRED", "ERROR", "Superseded object requires non-empty superseded_by.", obj, "superseded_by")
    elif "superseded_by" in m: report.add("KV-SUPERSEDED-STALE", "ERROR", "Non-superseded object may not retain superseded_by.", obj, "superseded_by")
    kind = m.get("kind")
    if kind == "resource": _resource_rules(report, obj)
    if kind == "project":
        ct = m.get("canonical_truth")
        if not isinstance(ct, dict) or ct.get("mode") not in {"vault","referenced"} or not isinstance(ct.get("ref"), str): report.add("KV-PROJECT-CANONICAL", "ERROR", "Project requires canonical_truth mode and ref.", obj, "canonical_truth")
    if kind == "source":
        if m.get("source_type") not in {"webpage","article","paper","documentation","repository","book","video","audio","conversation","dataset","other"}: report.add("KV-SOURCE-TYPE", "ERROR", "Source requires a controlled source_type.", obj, "source_type")
        if any(isinstance(x, dict) and x.get("kind") == "url" for x in m.get("locators", [])) and not m.get("accessed"): report.add("KV-SOURCE-ACCESSED", "ERROR", "URL Source locator requires accessed.", obj, "accessed")
    if kind == "tool":
        if m.get("tool_type") not in {"software","service","model","protocol","hardware","other"}: report.add("KV-TOOL-TYPE", "ERROR", "Tool requires a controlled tool_type.", obj, "tool_type")
        if m.get("adoption_state") not in {"unassessed","evaluating","adopted","rejected","retired"}: report.add("KV-TOOL-ADOPTION", "ERROR", "Tool requires a controlled adoption_state.", obj, "adoption_state")
        if m.get("adoption_state") in {"adopted", "rejected", "retired"} and not isinstance(m.get("authority"), dict): report.add("KV-AUTHORITY-REQUIRED", "ERROR", "This Tool adoption state requires authority.", obj, "authority")
    if kind == "meta":
        if m.get("meta_type") not in {"schema","policy","convention","template","other"} or not isinstance(m.get("authority"), dict): report.add("KV-META", "ERROR", "Meta requires controlled meta_type and authority.", obj)
        if m.get("meta_type") == "schema" and not isinstance(m.get("defines_schema"), str): report.add("KV-META-SCHEMA", "ERROR", "Schema Meta requires defines_schema.", obj, "defines_schema")
    if kind == "area" and ("# Purpose" not in obj.document.body or "# Boundaries" not in obj.document.body): report.add("KV-BODY-AREA", "ERROR", "Area body requires Purpose and Boundaries sections.", obj)
    for relation in m.get("relationships", []) if isinstance(m.get("relationships"), list) else []:
        if not isinstance(relation, dict) or relation.get("relation") not in {"related_to", "part_of", "applies_to", "uses", "depends_on"} or not isinstance(relation.get("ref"), str): report.add("KV-RELATIONSHIP-SHAPE", "ERROR", "relationships must use a controlled relation and permanent ref.", obj, "relationships")


def _resource_rules(report: ValidationReport, obj: VaultObject) -> None:
    m = obj.metadata; cls = m.get("knowledge_class"); state = m.get("knowledge_state")
    if cls not in RESOURCE_STATES or state not in RESOURCE_STATES.get(cls, set()): report.add("KV-RESOURCE-STATE", "ERROR", "Resource requires compatible controlled knowledge_class and knowledge_state.", obj); return
    evidence = m.get("evidence", []); supports = _refs([e for e in evidence if isinstance(e, dict) and e.get("relation") == "supports"]); challenges = _refs([e for e in evidence if isinstance(e, dict) and e.get("relation") == "challenges"])
    if not isinstance(evidence, list) or any(not isinstance(e, dict) or e.get("relation") not in {"supports", "challenges"} or not isinstance(e.get("ref"), str) for e in evidence): report.add("KV-EVIDENCE-SHAPE", "ERROR", "evidence must use supports/challenges with permanent refs.", obj, "evidence")
    required = {("claim","accepted"): (1,0), ("claim","contested"): (1,1), ("claim","rejected"): (0,1), ("observation","disputed"): (0,1), ("practice","accepted"): (1,0), ("hypothesis","supported"): (1,0), ("hypothesis","refuted"): (0,1)}.get((cls,state), (0,0))
    if len(supports) < required[0] or len(challenges) < required[1]: report.add("KV-EVIDENCE-MINIMUM", "ERROR", "Resource does not meet its deterministic evidence minimum.", obj, "evidence")
    authority_required = (cls in {"decision","operating_knowledge"} and state in {"accepted","rejected"})
    if authority_required and not isinstance(m.get("authority"), dict): report.add("KV-AUTHORITY-REQUIRED", "ERROR", "This Resource standing requires authority.", obj, "authority")
    if cls == "decision" and "# Rationale" not in obj.document.body: report.add("KV-BODY-RATIONALE", "ERROR", "Decision Resource requires a Rationale section.", obj)
    if cls == "operating_knowledge" and state == "accepted" and "# Rationale" not in obj.document.body: report.add("KV-BODY-RATIONALE", "ERROR", "Accepted Operating Knowledge requires a Rationale section.", obj)


def _integrity(report: ValidationReport, objects: list[VaultObject], registry: VaultRegistry) -> None:
    roots = []
    for obj in objects:
        m = obj.metadata; scope = m.get("scope")
        if isinstance(scope, str):
            if scope == obj.id: roots.append(obj)
            else:
                target = _reference(report, registry, obj, scope, "scope", "KV-SCOPE-REFERENCE")
                if target and target.metadata.get("kind") not in {"project","area","tool","meta"}: report.add("KV-SCOPE-KIND", "ERROR", "scope must target project, area, tool, or meta.", obj, "scope")
        else: report.add("KV-SCOPE-REFERENCE", "ERROR", "scope must be one permanent ID.", obj, "scope")
        for ref in m.get("superseded_by", []) if isinstance(m.get("superseded_by"), list) else []: _reference(report, registry, obj, ref, "superseded_by", "KV-SUPERSEDED-REFERENCE")
        if isinstance(m.get("superseded_by"), list) and len(set(m["superseded_by"])) != len(m["superseded_by"]): report.add("KV-SUPERSEDED-DUPLICATE", "ERROR", "superseded_by may not contain duplicates.", obj, "superseded_by")
        for entry in m.get("provenance", []) if isinstance(m.get("provenance"), list) else []:
            if isinstance(entry, dict):
                for ref in entry.get("refs", []) if isinstance(entry.get("refs"), list) else []: _reference(report, registry, obj, ref, "provenance.refs", "KV-PROVENANCE-REFERENCE")
        for field in ("evidence", "relationships"):
            for ref in _refs(m.get(field, [])): _reference(report, registry, obj, ref, field, "KV-REF-MISSING")
        auth = m.get("authority")
        if isinstance(auth, dict):
            if auth.get("kind") not in {"operator","delegated","system"}: report.add("KV-AUTHORITY-SHAPE", "ERROR", "authority.kind is invalid.", obj, "authority")
            elif auth.get("kind") == "operator" and "ref" in auth: report.add("KV-AUTHORITY-SHAPE", "ERROR", "operator authority may not have ref.", obj, "authority")
            elif auth.get("kind") in {"delegated","system"}:
                ref = auth.get("ref")
                target = _reference(report, registry, obj, ref, "authority.ref", "KV-AUTHORITY-REFERENCE") if isinstance(ref, str) else None
                if not isinstance(ref, str): report.add("KV-AUTHORITY-SHAPE", "ERROR", "delegated/system authority requires exactly one ref.", obj, "authority.ref")
                if auth.get("kind") == "system" and target and target.metadata.get("kind") != "meta": report.add("KV-AUTHORITY-SYSTEM", "ERROR", "system authority must reference Meta.", obj, "authority.ref")
        ct = m.get("canonical_truth")
        if m.get("kind") == "project" and isinstance(ct, dict) and isinstance(ct.get("ref"), str):
            target = _reference(report, registry, obj, ct["ref"], "canonical_truth.ref", "KV-PROJECT-REFERENCE", allow_self=ct.get("mode") == "vault")
            if ct.get("mode") == "vault" and ct.get("ref") != obj.id: report.add("KV-PROJECT-SELF", "ERROR", "vault canonical_truth must self-reference.", obj, "canonical_truth.ref")
            if ct.get("mode") == "referenced" and target and target.metadata.get("kind") != "source": report.add("KV-PROJECT-REFERENCE", "ERROR", "referenced canonical_truth must target Source.", obj, "canonical_truth.ref")
    if len(roots) != 1: report.add("KV-ROOT-UNIQUE", "ERROR", f"Expected exactly one root self-scope object; found {len(roots)}.")
    _cycle(report, objects, lambda o: o.metadata.get("superseded_by", []), "KV-SUPERSEDED-CYCLE", "Supersession graph")
    _cycle(report, objects, lambda o: [r for e in o.metadata.get("provenance", []) if isinstance(e,dict) and e.get("kind") == "derived" for r in e.get("refs", [])], "KV-PROVENANCE-CYCLE", "Derived provenance graph")
    _cycle(report, objects, lambda o: [o.metadata.get("authority",{}).get("ref")] if isinstance(o.metadata.get("authority"),dict) and o.metadata["authority"].get("kind") in {"delegated","system"} else [], "KV-AUTHORITY-CYCLE", "Authority graph")
    for obj in objects:
        auth = obj.metadata.get("authority")
        if not isinstance(auth, dict) or auth.get("kind") not in {"delegated", "system"}:
            continue
        cursor = obj; visited: set[str] = set(); rooted = False
        while True:
            current = cursor.metadata.get("authority")
            if not isinstance(current, dict): break
            if current.get("kind") == "operator": rooted = True; break
            ref = current.get("ref")
            if not isinstance(ref, str) or ref in visited: break
            visited.add(ref); resolution = registry.resolve(ref)
            if resolution.kind is not ResolutionKind.UNIQUE: break
            cursor = resolution.object
        if not rooted: report.add("KV-AUTHORITY-ROOT", "ERROR", "Delegated/system authority chain must terminate in operator authority.", obj, "authority")
