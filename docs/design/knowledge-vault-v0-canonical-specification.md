Knowledge Vault V0 -- Canonical Specification

Status: DESIGN ACCEPTED  
Schema identifier: kv-v0  
Implementation status: Not implemented  
Production status: Not production-validated

1. Purpose and Acceptance Boundary

The Knowledge Vault is the durable, human-readable canonical knowledge layer within the  
broader Personal R&D Infrastructure. V0 is designed for trustworthy capture, provenance,  
organization, connection, preservation, and agent-readable governance. Intelligence, semantic  
search, embeddings, graphs, databases, applications, and visual interfaces may be derived  
from the vault, but they do not replace the vault as canonical knowledge truth.

"kv-v0 design accepted" means the schema and behavioral contract have passed consolidation,  
representative-object stress testing, agent-behavior testing, and deliberate break testing. It does  
not mean the system is implemented, migrated, production-validated, operationally accepted, or  
complete.

2. Foundational Principles

2.1 Human-readable canonical truth

The Knowledge Vault uses human-readable Markdown as the durable canonical knowledge  
form. Structured metadata exists to identify, route, validate, and govern knowledge; nuanced  
reasoning remains in document bodies.

2.2 Scoped canonical truth

Canonical truth is scoped. Project repositories or other explicitly declared project-canonical  
locations govern project operational truth when a Project declares them as canonical. The  
Knowledge Vault governs cross-project knowledge and vault governance. External sources  
remain authoritative for claims about themselves.

The vault may summarize, reference, derive, and connect other canonical sources, but it must  
not silently replace them. Canonicality is independent from lifecycle, acceptance,  
implementation, verification, correctness, and evidentiary support.

2.3 Type-sensitive knowledge acceptance

Knowledge acceptance is type-sensitive. Different knowledge classes require different evidence,  
reasoning, experience, or operator authority. Acceptance is scoped and revisable. It is not a  
claim of permanent or universal truth. Lifecycle state and epistemic standing are separate  
dimensions.

2.4 Processing is not standing

Capture, investigation/sourcing, distillation, classification, evaluation, and promotion describe  
how knowledge is worked with. They do not form a universal metadata lifecycle.

Conceptual processing flow:  
Capture → Investigate / Source → Distill → Classify → Evaluate → Promote

Processing never grants acceptance by itself. Agent synthesis, classification, or evidence  
collection may inform acceptance, but acceptance follows the requirements of the relevant  
knowledge class.

Within-class promotion may advance knowledge_state on the same object. Cross-class  
promotion creates a new object with a new permanent ID and provenance linking to its  
predecessor.

3. Universal Object Contract

Every knowledge-bearing Markdown object governed by kv-v0 begins with YAML frontmatter  
containing exactly these universal mandatory core fields:

```yaml  
---  
schema:  
id:  
title:  
kind:  
state:  
scope:  
created:  
provenance:  
---  
```

These are universal unless a later explicit schema generation changes the contract.

The following are not universal V0 fields: updated, tags, related, author, confidence, version,  
canonical, project.

Conditional metadata such as knowledge_class, knowledge_state, evidence, relationships,  
authority, canonical_truth, source_type, tool_type, adoption_state, meta_type, and  
defines_schema appears only where required or allowed by the applicable object contract.

3.1 schema

All V0 objects declare schema: kv-v0.

schema identifies the metadata contract used to interpret the object. It is not a content revision  
number. Ordinary edits do not change schema. A schema migration preserves permanent  
object identity. Multiple schema generations may coexist during a controlled migration.

Agents must not invent schema identifiers. If an agent encounters an unknown schema, it must  
locate the appropriate active schema definition or stop schema-dependent interpretation/editing.

The declared schema is authoritative for validation and interpretation. An object must not be  
silently interpreted under a different schema merely because its shape resembles that schema.

For each schema identifier, exactly one active kind: meta, meta_type: schema object may define  
that identifier. Superseded and archived historical schema definitions may remain.

3.2 id

id is the permanent globally unique identity of the vault object.

V0 format: kv- + UUIDv7.

IDs are non-semantic, immutable, never reused, and independent of title, path, kind, state,  
scope, or schema generation.

Renames, moves, content edits, state changes, scope changes, ordinary reclassification, and  
schema migration do not change id. New copies and materially new derived objects receive new  
IDs.

Structured references use permanent IDs rather than filenames, paths, or titles. Agents  
generate IDs only through an approved UUIDv7-compliant mechanism.

Duplicate persisted IDs are a critical identity-integrity failure. Identity-dependent work must stop  
until the collision is explicitly repaired. Agents must not choose a winner or manufacture a  
replacement identity from path, title, timestamps, content similarity, or other inference.

3.3 title

Each object has exactly one title. title is human-readable, mutable, non-unique, and used for  
display, navigation, search, and visual interfaces. title is not identity and must never replace  
permanent IDs in structured references.  
Titles should describe the object rather than encode kind, state, scope, or other metadata.  
Filenames should normally remain recognizable relative to titles but need not match them.  
Aliases are not universal V0 metadata.

3.4 kind

Controlled V0 kind vocabulary:  
index  
capture  
project  
area  
resource  
source  
tool  
map  
meta

Agents may not invent new kinds. If material cannot yet be classified, retain or create kind:  
capture and flag schema review if necessary.

The following are not kinds: archive, decision, concept, hypothesis, note, document, research.

Folder location and kind may correlate, but folder location never defines kind.

3.5 state

Controlled lifecycle vocabulary:  
active  
superseded  
archived

active: The object participates in the live knowledge system and may be retrieved, referenced,  
related, or acted upon according to its other metadata. active does not mean true, accepted,  
verified, complete, implemented, recent, or authoritative.

superseded: The object remains a valid historical record but has been replaced in its former  
current role by one or more identified successor objects. superseded does not mean false,  
invalid, or rejected.

When state: superseded, superseded_by is required and is always a non-empty list of  
permanent vault IDs.

Example:

```yaml  
superseded_by:  
- kv-...  
- kv-...  
```

The listed objects collectively replace the predecessor's former current role. One-to-one  
replacement uses a one-item list. Supersession does not transfer epistemic standing, authority,  
scope, or other metadata. Each successor independently satisfies the requirements of its new  
role.

Agents follow every supersession branch until the current non-superseded successor leaves  
relevant to the task are reached. Supersession graphs must be acyclic. Duplicate successor  
IDs, dangling successor refs, and self-supersession are invalid.

archived: The object is intentionally retained for history, reference, or preservation but is  
removed from the normal live working set. archived does not mean false, rejected, superseded,  
unimportant, or complete.

Archival is explicit or policy-governed. It is never inferred automatically from age, processing,  
completion, project completion, or apparent irrelevance. An archived object may later return to  
active if the same object becomes relevant again. Physical placement in an archive folder does  
not determine lifecycle state.

3.6 scope

scope contains exactly one permanent vault ID identifying the primary boundary within which  
the object should be interpreted and applied by default. Free-form scope strings are invalid.

Valid V0 scope targets are project, area, tool, and meta objects. Scope references must resolve  
to existing scope-capable objects.

Exactly one designated root-scope object may self-reference its own permanent ID in scope to  
bootstrap the hierarchy. All other objects must scope to a different valid scope-capable object.

The exact title, filename, permanent ID, and whether the root is kind: area or kind: meta are not  
fixed by this specification.

When narrower scope is unknown for a new Capture, use the designated Personal R&D root  
scope rather than unknown, general, unassigned, or global.

Scope may narrow or broaden without changing object identity. Broadening scope is a  
deliberate knowledge-promotion or authority decision. Agents must not broaden scope from  
inference alone.

Relationships may indicate relevance outside the primary scope, but they do not transfer  
epistemic standing, governance authority, or scope to another target.  
A scope reference remains historically meaningful even if the referenced scope object later  
becomes superseded or archived.

3.7 created

created is required and uses date-only ISO form YYYY-MM-DD.

It records the date this specific vault object first came into existence. It is not source publication  
date, last edited date, filesystem creation date, review date, or verification date.

created is normally immutable through renames, moves, content edits, reclassification, scope  
changes, lifecycle changes, and schema migrations.

When migrating an existing object, preserve the earliest reliably known creation date if the same  
object identity is preserved. If an older historical date is unknown, do not guess. Use the date  
the object enters the vault and preserve uncertainty separately when materially important.

New copies and derived objects receive their own created values.

3.8 provenance

provenance is mandatory on every vault Markdown object. It records direct or materially  
significant origins and lineage, not exhaustive ancestry.

Controlled provenance kinds:  
operator  
external  
source  
project  
agent  
derived

Example:

```yaml  
provenance:  
- kind: operator  
- kind: source  
refs:  
- kv-...  
```

operator: Direct operator-originated knowledge.  
external: The object directly represents or originates from outside the vault.  
source: The object is materially derived from one or more vault Source records.  
project: The object is materially derived from project work or experience.  
agent: An agent materially contributed the knowledge.  
derived: The object is synthesized or derived from one or more existing vault objects.

Use multiple provenance entries rather than a mixed kind.

Provenance is not evidence, truth, acceptance, or authority. Minor editing does not change  
provenance. Material knowledge contribution may add provenance.

In-place reclassification preserves materially meaningful provenance. New entries may be  
added when additional direct origins become understood, but valid historical provenance must  
not be removed merely to make the object resemble a freshly created object of its new kind.

provenance.kind: derived creates directed historical ancestry and must be acyclic. An object  
may not directly or indirectly derive from itself.

Later influence or reinterpretation must not falsify derivation history. Use evidence, relationships,  
body context, or a new derived object where appropriate.

4. Resource Epistemic Model

Every kind: resource object requires knowledge_class and knowledge_state.

Controlled knowledge classes:  
claim  
observation  
practice  
decision  
concept  
operating_knowledge  
hypothesis

4.1 claim

Meaning: A checkable assertion. V0 deliberately uses claim rather than fact until standing is  
justified.  
Allowed states: unassessed, accepted, contested, rejected.  
Evidence: accepted requires at least one supports ref; contested requires at least one supports  
and one challenges ref; rejected requires at least one challenges ref; unassessed requires  
none.

4.2 observation

Meaning: A directly encountered or recorded occurrence.  
Allowed states: recorded, accepted, disputed.  
Evidence: disputed requires at least one challenges ref; recorded and accepted have no  
universal evidence requirement. Supporting evidence may still be attached where useful.

4.3 practice

Meaning: A reusable method or pattern intended to guide future behavior.  
Allowed states: candidate, accepted, rejected.  
Evidence: accepted requires at least one supports ref. Candidate and rejected have no  
universal evidence requirement in V0.

4.4 decision

Meaning: An authoritative choice within scope.  
Allowed states: proposed, accepted, rejected.  
Authority: proposed does not require authority; accepted and rejected require authority.  
Every Decision Resource requires a body section titled Rationale.  
Rejection means the proposed choice was legitimately declined within scope. It does not  
necessarily mean the underlying proposition is false.

4.5 concept

Meaning: A defined idea, term, mental model, or abstraction.  
Allowed states: emerging, defined, accepted, rejected.  
No universal evidence requirement.  
Transition into accepted requires legitimate acceptance authorization, but persistent authority  
metadata is not universally required for Concept in V0.

4.6 operating_knowledge

Meaning: Knowledge describing how the operator, system, workflow, or agents are intended to  
work.  
Allowed states: proposed, accepted, rejected.  
Authority: proposed does not require authority; accepted and rejected require authority.  
Accepted Operating Knowledge requires body rationale. Retained rejected Operating  
Knowledge should preserve why it was rejected.

4.7 hypothesis

Meaning: A proposition that may be true or useful but is not established.  
Allowed states: unresolved, supported, refuted.  
Evidence: supported requires at least one supports ref; refuted requires at least one challenges  
ref; unresolved requires none.  
Hypotheses do not become accepted. When a supported hypothesis should become accepted  
knowledge of another class, create a new object with a new ID and provenance linking the  
hypothesis.

4.8 Class stability and promotion

knowledge_class normally remains stable after classification. True misclassification may be  
corrected in place. Promotion into a different epistemic role creates a new Resource with a new  
permanent ID and meaningful provenance to the predecessor. Within-class maturation retains  
the same ID.

5. Evidence

evidence is conditional structured metadata used on Resources.

Controlled evidence relations: supports, challenges.

Shape:

```yaml  
evidence:  
- relation: supports  
ref: kv-...  
- relation: challenges  
ref: kv-...  
```

Evidence references use permanent vault IDs. Evidence is not provenance, authority,  
acceptance, proof, or bibliography. Detailed reasoning remains in the body.

Evidence requirements are minimum evidentiary conditions, not exclusive whitelists. Material  
counterevidence may remain attached even when the current knowledge_state is accepted or  
otherwise adjudicated.

knowledge_state records current adjudicated standing; evidence preserves the material  
evidentiary picture.

Adding or removing evidence does not automatically change knowledge_state. Agents may flag  
meaningful tension and propose review, but they do not silently alter epistemic standing.

Materially valid evidence must not be removed merely to make evidence agree with current  
standing. Removal requires correction of the evidence relationship itself or explicit authorization.

Evidence refs remain historically meaningful if referenced objects later become archived or  
superseded. Self-evidence is invalid under the global self-reference rule.

6. Relationships

relationships is optional structured semantic metadata for connections not already represented  
by scope, provenance, evidence, authority, or supersession.

Controlled V0 relationship types: related_to, part_of, applies_to, uses, depends_on.

Canonical directions:  
child → part_of → parent/container  
knowledge/object → applies_to → target  
subject/project → uses → tool/object  
subject → depends_on → dependency

related_to is symmetric in meaning. The other four are directed.

No self-relations. Do not store redundant inverse relations such as contains when part_of  
already expresses the canonical edge.

Do not introduce relationship types for meanings already represented elsewhere: derived_from  
belongs to provenance; supports/challenges belong to evidence; supersedes belongs to  
lifecycle.

Mention and co-occurrence do not establish a relationship. Agents should be conservative  
about inferred relationships and flag uncertainty.

Relationships do not change or transfer scope, epistemic standing, provenance, evidence, or  
authority.

7. Authority

authority is a reusable conditional governance field. It records the legitimate authority  
responsible for a governed state or standing wherever kv-v0 explicitly requires authority.

Controlled authority kinds: operator, delegated, system.

7.1 operator

```yaml  
authority:  
kind: operator  
```

The operator directly established the governed standing. No ref is required.

7.2 delegated

```yaml  
authority:  
kind: delegated  
ref: kv-...  
```

A non-operator actor exercised explicitly granted discretionary authority. ref identifies the direct  
governing delegation record, not merely the actor. A delegation record may be an applicable  
Meta governance object or an accepted Decision/Operating Knowledge Resource explicitly  
granting the authority.

7.3 system

```yaml  
authority:  
kind: system  
ref: kv-...  
```

A deterministic governing rule established the governed state rather than an actor exercising  
discretionary judgment. ref must resolve to a kind: meta object establishing the deterministic  
rule. Automation or agent execution alone does not constitute system authority.

7.4 Authority-chain integrity

Every delegated or system authority chain must be finite, acyclic, and ultimately terminate in  
authority.kind: operator. An object may not directly or indirectly derive authority from itself.  
Broken, circular, or unrooted authority chains cannot establish valid governed standing.

Historical authority references remain tied to the governing source that legitimately applied at  
the time. Later supersession or archival does not cause historical authority refs to be rewritten.  
Current actions require currently applicable authority. Historical reconstruction may legitimately  
traverse superseded or archived governance.

8. Kind-Specific Contracts

8.1 index

No kind-specific YAML beyond universal core and optional relationships.  
Purpose: durable navigation, orientation, discovery, and aggregation.  
An Index references knowledge but is not authoritative truth about target objects.  
Do not duplicate volatile project state, evidence, implementation status, or other canonical  
details into an Index.  
Listing objects together does not create semantic relationships.  
If substantive claims or reasoning accumulate in an Index, extract them into Resources.  
V0 does not require index_type or generation metadata.

8.2 capture

No kind-specific YAML beyond universal core.  
Capture means classification is unresolved.  
Capture has no knowledge_class, knowledge_state, processing_state, evidence requirement,  
required relationships, or required body template.  
Capture must remain low-friction and highly automatable, especially from a phone. The operator  
should usually provide only the content; schema, ID, default state, date, provenance, and  
default scope should be generated automatically by implementation.  
Agents preserve original uncertainty and context. They must not polish speculative language  
into accepted fact.  
A Capture may be reclassified in place when it clearly represents one continuing object.  
If one Capture yields multiple or materially transformed objects, create new IDs for the derived  
objects and preserve the original Capture.  
Processed Captures may later be archived through explicit or policy-governed action.

8.3 project

Required:

```yaml  
canonical_truth:  
mode:  
ref:  
```

Controlled modes: vault, referenced.  
For mode: vault, ref must equal the Project's own permanent ID. The Project object is the  
canonical vault-native entry point, not necessarily the only file containing project truth.  
For mode: referenced, ref must resolve to a kind: source object identifying the external  
canonical-truth location.  
The Project is a durable identity, navigation hub, and knowledge hub. It is not a shadow  
project-management system.  
V0 does not require project lifecycle, stage, owner, repository path, branch, release, tasks,  
implementation state, or start/end dates.  
state describes the vault Project object, not the project's operational lifecycle.  
Agents must follow canonical_truth whenever current project operational truth matters.  
An unavailable or broken referenced canonical source does not authorize fallback promotion of  
a vault summary into canonical truth.  
Changing canonical_truth changes project truth routing and requires explicit task authority or  
applicable delegation. Agents must not infer and silently rewrite it.

8.4 area

No kind-specific YAML beyond universal core and optional relationships.  
An Area is a durable ongoing domain of attention, responsibility, learning, research, or practice  
with no inherent completion lifecycle.  
Area hierarchy uses part_of where appropriate.  
The body should explain Purpose and Boundaries.  
No area_type, priority, focus, review cadence, or project-like status is required.

8.5 resource

Requires knowledge_class and knowledge_state.  
Conditional: evidence, authority, relationships.  
Resource is the primary epistemic knowledge-bearing kind. Decision, Concept, Hypothesis,  
Practice, Claim, Observation, and Operating Knowledge are knowledge classes rather than  
top-level kinds.

8.6 source

Requires source_type.  
Controlled source_type: webpage, article, paper, documentation, repository, book, video, audio,  
conversation, dataset, other.  
Optional/conditional metadata: locators, creators, published, accessed.  
Controlled locator shape:

```yaml  
locators:  
- kind:  
value:  
```

Controlled locator kinds: url, doi, isbn.  
If any locator has kind: url, accessed is required. If no URL locator exists, accessed is optional.  
accessed records when the source was consulted or retrieved. It is not a freshness or  
verification field.  
published preserves known precision only, for example "YYYY", "YYYY-MM", or  
"YYYY-MM-DD".  
Unknown metadata is omitted rather than filled with placeholders.  
Source metadata identifies the artifact; it does not certify truth or reliability.  
Source disappearance, dead URLs, freshness checking, retrieval status, and snapshot  
availability are intentionally not V0 lifecycle semantics.

8.7 tool

Requires tool_type and adoption_state.  
Controlled tool_type: software, service, model, protocol, hardware, other.  
Controlled adoption_state: unassessed, evaluating, adopted, rejected, retired.  
Authority: unassessed/evaluating do not require authority; adopted/rejected/retired require  
authority.  
adoption_state records the current posture toward use. It does not mean installed, configured,  
running, required everywhere, or currently healthy.  
A Tool may move through adoption states repeatedly while retaining the same permanent ID.  
When a transition makes authority metadata inapplicable, stale authority metadata must not  
remain merely as historical residue in current frontmatter.  
Optional official_links with controlled types homepage, documentation, repository.  
V0 does not require provider, version, pricing, licensing, platform, install state, capability lists, or  
exhaustive history metadata.

8.8 map

No kind-specific YAML beyond universal core and optional relationships.  
A Map is a deliberately preserved visual or spatial representation used for exploration,  
communication, navigation, context reconstruction, or thread holding.  
A Map is a representation, not automatic canonical truth.  
Visual edges do not create canonical relationships, evidence, provenance, scope, authority, or  
accepted knowledge unless separately represented in underlying vault objects.  
Persisted map nodes should reference permanent IDs when they correspond to vault objects.  
Maps may contain speculative nodes, annotations, questions, and local visual groupings without  
creating new canonical objects.  
Temporary generated visualizations are not kind: map unless intentionally preserved.  
V0 does not require map_type, layout engine, render format, freshness metadata, or  
visualization schema.

8.9 meta

Requires meta_type and authority.  
Controlled meta_type: schema, policy, convention, template, other.  
If meta_type: schema, defines_schema is required.  
For Meta, authority records the legitimate authority under which the object was established as  
vault governance.  
Every Meta object requires authority regardless of lifecycle state.  
Active Meta is established current vault governance within scope.  
Proposed governance changes should normally exist first as proposed Decision or Operating  
Knowledge Resources rather than immediately becoming active Meta.  
policy = binding governance rule.  
convention = accepted default.  
template = canonical scaffold.  
schema = canonical metadata contract definition.  
Agents may read and apply current Meta governance but may not materially create, alter,  
supersede, or archive governance without applicable authority.  
Superseded Meta preserves historical governance and its historical authority.

9. Body Requirements

Metadata describes and routes. Bodies contain nuance, reasoning, definitions, extracted  
knowledge, and human-readable governance.

Rationale is body content, not universal YAML.  
Every Decision Resource requires a Rationale section.  
Accepted Operating Knowledge requires rationale.  
Retained rejected Operating Knowledge should preserve why it was rejected.  
Agents may draft rationale but must not attribute reasoning to the operator unless it accurately  
reflects reasoning the operator actually accepted.  
Historical rationale for accepted decisions must not be silently rewritten to fit later knowledge.  
Materially new reasoning that produces a new choice should normally produce a new Decision  
object.  
Area bodies should explain Purpose and Boundaries.  
Project bodies should explain Purpose and Canonical Project Truth.  
Map bodies should explain the visual/cognitive purpose.  
Meta bodies must make the governing purpose unambiguous.

10. Agent Behavioral Contract

10.1 Three separate authority dimensions

Agents must distinguish:

1. Schema validity -- Is the representation valid under kv-v0?

2. Semantic/governance authority -- Is the resulting standing legitimately established?

3. Execution permission -- Is this agent authorized by the current task/runtime/delegation to  
make the write now?  
A schema-valid change does not grant permission to make it.

10.2 Acceptance

Transition into knowledge_state: accepted requires operator authorization unless explicitly  
delegated.  
Agents may create and work with non-accepted states within task authority.  
Agents may perform epistemic evaluation such as unresolved → supported or recorded →  
disputed when the task authorizes evaluation and requirements are satisfied.  
Acceptance remains a separate governed act.  
For Decision and Operating Knowledge, accepted and rejected states require authority.

10.3 Scope

Agents must not broaden scope through inference.  
Relationships such as applies_to may surface relevance elsewhere but do not transfer  
authoritative standing.

10.4 Evidence

Agents may add materially justified evidence when authorized to maintain the object.  
They do not remove valid evidence merely to align the evidentiary picture with current  
knowledge_state.  
New counterevidence may trigger a review recommendation but does not automatically change  
epistemic standing.

10.5 Canonical project truth

Agents follow Project canonical_truth when current project operational truth matters.  
Vault summaries do not override declared external canonical truth.  
Broken or unavailable canonical routing must be reported rather than silently repaired or  
bypassed.

10.6 Archival

Agents do not infer archival from age, processing, completion, or apparent irrelevance.  
Archival is explicit, task-authorized, delegated, or policy-governed.

10.7 Supersession

Agents may propose supersession when a legitimate replacement exists.  
They perform supersession only with applicable write authority.  
Supersession routes current-role continuity; it does not transfer acceptance or authority to  
successors.

10.8 Meta creation

An agent identifying a need for new governance should normally create or recommend  
proposed Decision/Operating Knowledge rather than directly creating active Meta without  
authority.

10.9 Historical rationale

Agents do not rewrite historical accepted rationale to make old choices appear to have been  
made for reasons discovered later.

10.10 Ordinary maintenance

Authorized maintenance agents may correct spelling, formatting, broken Markdown, obvious  
non-semantic errors, and similar presentation issues without creating new object identities or  
acceptance decisions.

11. Conflict Handling and Stop Conditions

11.1 No implicit precedence

When multiple applicable active knowledge or governance objects materially conflict, agents  
must not invent precedence from created date, file order, apparent specificity, scope depth,  
source count, confidence, personal reasoning, or modification time.  
Precedence exists only where explicitly established by governing vault truth, supersession, or  
another authorized resolution.  
Scope hierarchy determines applicability, not automatic precedence.

11.2 Conflict detection is not resolution authority

Detecting a conflict does not authorize an agent to choose a winner, alter standing, rewrite  
governance, or manufacture a compromise.

11.3 Bounded stopping

When an unresolved contradiction, broken critical reference, unverifiable authority chain,  
unknown schema, or ambiguous governance condition prevents safe interpretation or action,  
stop the smallest dependent action necessary.  
Continue unrelated work when it can proceed safely.

11.4 Agents do not repair standing by inference

Detecting inconsistency does not authorize changes to lifecycle state, knowledge_state, scope,  
authority, canonical_truth, or governance standing.  
Agents may diagnose, flag, and propose repairs. Actual changes require applicable task and  
semantic authority.

11.5 Critical versus degradable reference failures

Broken critical references may prevent safe use of the object for dependent actions. Examples  
include scope, required authority.ref, Project canonical_truth.ref, superseded_by, and required  
evidence refs needed by current knowledge_state.  
Broken optional relationships or other noncritical edges may degrade graph quality without  
necessarily making the entire object unusable.

12. Integrity Invariants

12.1 Permanent ID uniqueness

Every persisted vault object has one globally unique permanent ID. Duplicate IDs halt  
identity-dependent work until explicitly repaired.

12.2 Self-reference deny-by-default

Self-reference is invalid unless kv-v0 explicitly allows that exact relationship.  
V0 defines exactly two self-reference exceptions:

1. The designated root-scope object may set scope to its own permanent ID.

2. A vault-native Project may set canonical_truth.ref to its own permanent ID when  
canonical_truth.mode is vault.  
All other self-references are invalid, including supersession, evidence, relationships, derived  
provenance, delegated authority, and system authority.

12.3 Supersession integrity

When state is superseded, superseded_by is required, non-empty, resolvable, duplicate-free,  
non-self-referential, and acyclic.  
When state is not superseded, superseded_by must not remain as stale current metadata.

12.4 Authority integrity

delegated and system refs resolve to valid governing sources. Authority derivation is acyclic and  
ultimately rooted in operator authority.

12.5 Derived provenance integrity

Derived provenance ancestry is acyclic.

12.6 Scope integrity

Every scope ref resolves to a valid project, area, tool, or meta object, except for the one  
designated root's explicit self-scope. A missing or wrong-kind scope is invalid.

12.7 Unique active schema definition

For each schema identifier, exactly one active Meta Schema object defines it. Multiple active  
definitions for the same identifier are invalid and block schema-dependent writes.

12.8 Declared schema governs interpretation

An invalid object under its declared schema remains invalid. Agents do not silently reinterpret a  
malformed kv-v1 object as kv-v0 merely because it resembles V0.

12.9 Cross-schema references

Cross-schema refs are permitted in principle because permanent identity persists across  
schema generations. Semantic use of a referenced object requires understanding its governing  
schema or an explicitly established compatibility rule. If the target schema cannot be safely  
interpreted, preserve the ref and stop only the dependent semantic action that requires  
understanding it.

12.10 Root uniqueness

Exactly one designated root-scope object may use the root self-scope exception. Zero roots  
means bootstrap is incomplete. Multiple roots are invalid.

13. Bootstrap, Migration, and Recovery Boundaries

13.1 Schema bootstrap

The canonical kv-v0 Schema Meta object itself declares schema: kv-v0 while defining kv-v0.  
Implementation therefore needs a minimal trusted bootstrap reader capable of parsing enough  
structure to locate and load the canonical schema definition. A bootstrap copy of the contract  
may exist for recovery/initialization but does not become a competing mutable canonical source.

13.2 Migration

Schema migration preserves id and created when object continuity is preserved. Agents do not  
migrate objects merely because a newer schema exists. Migration requires an explicit migration  
plan/governance action. Mixed schema generations may coexist during controlled migration.

13.3 Missing identity

A new object receives an ID before valid persistence. An already-existing object whose ID is lost  
presents an identity-recovery problem. Agents should attempt authorized recovery from  
history/references rather than casually manufacturing a new identity.

13.4 Malformed frontmatter

Malformed YAML means the object cannot be treated as a valid schema-loaded object. Agents  
may inspect raw body content for recovery but do not infer important metadata from prose  
without sufficient evidence and authority.

13.5 Partial and multi-object writes

Legitimate mutually referencing objects may require staged or transactional creation. Final  
persisted vault state must satisfy referential integrity. The schema should not be weakened  
merely to accommodate interrupted writes.

13.6 Concurrent writes

Concurrency control is an implementation concern. Last-write-wins must not silently resolve  
semantic conflicts. Use Git conflict detection, optimistic locking, transactions, revision checks, or  
equivalent implementation mechanisms.

14. Physical Organization Versus Semantic Organization

Folder placement never determines kind, state, knowledge_class, knowledge_state, scope, or  
authority.  
Physical organization is for human navigation and practical storage. Semantic organization is  
carried by permanent IDs and structured metadata.  
A superseded object may physically live under an archive folder while remaining state:  
superseded.  
Concept and Decision are semantic Resource classes rather than top-level physical categories  
required by V0.

15. Graph and Visual Derivation

Future knowledge graphs may derive nodes from vault objects and edges from provenance,  
evidence, relationships, superseded_by, scope, and authority.  
The derived graph does not become canonical truth merely because it is queryable or visual.  
Maps remain cognitive interfaces.  
Graph engines, embeddings, vector stores, semantic search, and databases are derived  
infrastructure.  
The canonical durable knowledge remains the human-readable vault.

16. Known Deferred Implementation Concerns

The following are deliberately not solved by kv-v0 metadata and should be addressed only  
when implementation/live use requires them:  
source freshness and availability checking  
source snapshot/archive retrieval  
local repository locator resolution  
machine-enforceable structured delegation/permission DSL  
atomic validation of mutually referencing objects  
warnings for active objects scoped to inactive boundaries  
concurrency and optimistic locking  
bootstrap loader and schema-recovery mechanics  
visualization/rendering format  
graph indexing  
semantic embeddings/search  
automated Capture intake UX  
migration tooling

These are not current schema failures.

17. Explicit V0 Non-Goals

V0 intentionally does not universally add:  
tags  
confidence numbers  
updated timestamps  
processing status  
project operational status  
provider  
pricing  
licensing  
installation state  
review cadence  
graph engine metadata  
permission DSL  
schema migration timestamps  
previous_schema  
migration IDs  
is_root flag  
file path fields  
object version counters  
checksums  
recovery status  
source freshness fields  
generic canonical booleans

These may be introduced only after real live-use pressure demonstrates a concrete necessity.

18. Canonical V0 Validation Summary

A valid kv-v0 object must:  
declare schema: kv-v0  
have a globally unique permanent UUIDv7-based kv- ID  
have exactly one title  
use one controlled kind  
use one controlled lifecycle state  
have one resolvable valid scope, except the explicit root self-scope  
have a valid created date  
have meaningful provenance  
satisfy its kind-specific required fields  
satisfy class-specific knowledge_state rules when kind: resource  
satisfy required evidence and authority conditions  
contain only controlled relationship/authority/provenance vocabularies  
obey self-reference restrictions  
obey acyclic supersession, authority, and derived-provenance invariants  
obey unique active schema-definition rules  
preserve history rather than silently normalizing it away

19. Design Acceptance Record

System Review Pass 1 -- Consolidation + Internal Consistency: PASS  
System Review Pass 2 -- Representative Object Stress Test: PASS  
System Review Pass 3 -- Agent Behavior Scenarios: PASS  
System Review Pass 4 -- Deliberate Break Testing: PASS

Final acceptance gates:  
Representability: PASS  
Agent interpretability: PASS  
Historical integrity: PASS  
Low-friction capture: PASS  
Schema justification: PASS

Final status: kv-v0 DESIGN ACCEPTED

This status means the schema and behavioral contract are sufficiently coherent, minimal,  
governable, historically preservative, and stress-tested to begin implementation design.

It does not mean implemented, migrated, production-validated, or operationally accepted.

The next phase is implementation design against this stable specification.