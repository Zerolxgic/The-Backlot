# Slice 3 — Operator-Directed Capture → Resource Classification

## Status

**DESIGN ACCEPTED / CONTRACT LOCKED**

Accepted: 2026-08-23

Implementation is **not authorized by this contract alone**.

This document defines the bounded implementation contract for Slice 3. Decisions D1–D30 are locked. Builder implementation must conform to this contract and the governing `kv-v0` canonical specification.

If implementation reveals a genuine contradiction or an inability to satisfy a locked invariant, the Builder must stop the smallest affected work and return the issue for design review rather than weakening the contract.

---

# 1. Objective

Slice 3 adds one operator-directed processing step to the Knowledge Vault:

**Capture → Resource classification**

The workflow allows an authorized operator to identify exactly one valid active `kv-v0` Capture by permanent ID, choose exactly one Resource knowledge class, and reclassify that same continuing canonical object in place.

The operation:

- preserves permanent object identity;
- preserves the existing knowledge body;
- preserves historical origin and scope;
- assigns only the selected Resource class and its deterministic initial non-adjudicated knowledge state;
- moves the object into Resource-oriented physical navigation;
- validates the prospective result before canonical mutation;
- performs one coherent canonical transition;
- reports success, refusal, failure, rollback, or indeterminate outcome truthfully.

Slice 3 does **not** evaluate whether the knowledge is true, supported, accepted, rejected, authoritative, broadly applicable, or otherwise epistemically mature.

---

# 2. Primary Operator Surface

```text
kv classify <ID> --class <RESOURCE_CLASS> [--vault <PATH>]
```

Required positional argument:

```text
<ID>
```

must be one permanent `kv-` UUIDv7 object ID.

Required class:

```text
--class claim
--class observation
--class practice
--class decision
--class concept
--class operating_knowledge
--class hypothesis
```

Optional Vault override:

```text
--vault <PATH>
```

No aliases, class inference, default class, interactive chooser, or case normalization are introduced.

---

# 3. Deterministic Initial Resource States

Classification assigns exactly one class-specific initial state:

```text
claim               → unassessed
observation         → recorded
practice            → candidate
decision            → proposed
concept             → emerging
operating_knowledge → proposed
hypothesis          → unresolved
```

These states are deliberately non-adjudicated.

Slice 3 does not provide a `--state` override.

Classification does not itself establish acceptance, support, rejection, dispute, definition, authority, or evidentiary standing.

---

# 4. Core Success Invariant

Before successful classification:

```text
exactly one eligible active Capture exists with permanent ID X
```

After confirmed successful classification:

```text
exactly one canonical object exists with permanent ID X

kind: resource

knowledge_class:
  the operator-selected class

knowledge_state:
  that class's deterministic initial state

physical navigation:
  30_resources/

preserved:
  schema
  id
  title
  lifecycle state
  scope
  created
  provenance
  exact body bytes
```

No canonical Capture representation of X remains after confirmed success.

---

# 5. Decision D1 — Identity Continuity

**LOCKED**

A Capture may be classified in place as a Resource only when the operator is identifying the semantic class of one continuing canonical knowledge object.

The transformation is one-to-one and meaning-preserving.

The following remain the same object:

```text
Capture ID X
↓
Resource ID X
```

Permanent `id` remains unchanged.

`created` remains unchanged.

The substantive body remains unchanged.

Materially valid historical provenance remains unchanged.

Classification does not authorize synthesis, substantive rewriting, splitting, merging, summarization, distillation, or material transformation.

If one Capture would produce multiple objects, or if the desired Resource materially transforms the original knowledge, the in-place workflow is ineligible.

Such work requires a future derived-object workflow with new permanent IDs while preserving the original Capture.

Ambiguous continuity causes refusal.

The tool does not infer continuity.

---

# 6. Decision D2 — Allowed Resource Classes

**LOCKED**

Slice 3 supports all seven `kv-v0` Resource knowledge classes:

```text
claim
observation
practice
decision
concept
operating_knowledge
hypothesis
```

The operator selects the class explicitly.

The tool does not infer the class from body content, title, scope, filename, provenance, folder location, or surrounding Vault objects.

Classification is not acceptance.

Classification is not evaluation.

Classification is not evidentiary judgment.

---

# 7. Decision D3 — Initial Knowledge State

**LOCKED**

The resulting Resource always receives the deterministic initial state defined in Section 3.

No alternate `knowledge_state` may be supplied during classification.

Later movement within a Resource class belongs to a separate evaluation, evidence, or acceptance workflow.

---

# 8. Decision D4 — Prospective Validity

**LOCKED**

Before canonical mutation, the service must construct the complete prospective Resource representation in memory and validate the resulting Vault state using the governing validator machinery.

Classification may proceed only if the resulting Resource is valid using:

- the unchanged existing body;
- preserved metadata;
- the explicitly authorized `kind` transformation;
- the operator-selected `knowledge_class`;
- the deterministic initial `knowledge_state`.

The classifier does not invent missing requirements.

It does not repair the source.

It does not generate rationale.

It does not synthesize evidence.

It does not generate authority.

It does not rewrite scope.

It does not rewrite provenance.

It does not interactively ask the operator to complete missing canonical content.

Example:

A Decision Resource requires the governing Decision body structure.

If the existing Capture body already satisfies that requirement, classification may proceed.

If it does not, classification refuses and leaves the Capture unchanged.

---

# 9. Decision D5 — Metadata Transformation

**LOCKED**

Preserve:

```text
schema
id
title
state
scope
created
provenance
body
```

Change:

```text
kind: capture
→
kind: resource
```

Add:

```text
knowledge_class: <operator-selected class>
knowledge_state: <deterministic initial state>
```

Do not automatically alter:

```text
title
scope
created
provenance
lifecycle state
```

Do not synthesize:

```text
evidence
authority
relationships
supersession
timestamps
processing metadata
history metadata
optional future fields
```

No retitling occurs.

No empty metadata scaffolding is added.

---

# 10. Decision D6 — Source Capture Eligibility

**LOCKED — CONSOLIDATED CORRECTION INCLUDED**

The target must resolve to exactly one valid:

```text
schema: kv-v0
kind: capture
state: active
```

object addressed by permanent ID.

The source Capture itself must be valid under its declared schema.

Classification does not repair an invalid source by transforming it.

Archived Captures are ineligible.

Superseded Captures are ineligible.

Unsupported schema generations are ineligible under this initial workflow.

The selected Vault must possess trustworthy global identity integrity.

**Any persisted duplicate permanent ID anywhere in the selected Vault blocks `kv classify`.**

Classification is identity-dependent work and cannot proceed while global permanent-ID uniqueness is violated.

Other unrelated pre-existing conformance findings do not automatically block classification when they do not compromise write-critical invariants.

A successful classification may therefore occur in a Vault containing unrelated errors, but operation success must never be presented as overall Vault health.

---

# 11. Decision D7 — Physical Relocation

**LOCKED**

A successful Capture → Resource transition places the continuing canonical object under:

```text
30_resources/
```

Physical placement remains a human-navigation consequence.

Folder location does not determine semantic kind.

The source path does not determine eligibility.

Semantic transformation and physical relocation constitute one operator-visible classification action.

No normal successful outcome may leave two canonical representations of the permanent ID.

If the source object already occupies the exact deterministically calculated final Resource path, physical relocation is unnecessary.

In that case, classification may still succeed because a real semantic Capture → Resource mutation occurred.

The source object itself is not considered a destination collision when source path and final calculated path are the same physical file.

---

# 12. Decision D8 — Filename Continuity

**LOCKED**

The resulting Resource uses a deterministic Resource-oriented navigation filename.

Conceptual form:

```text
resource-<title-slug>-<ID-fragment>.md
```

The name is derived from:

- the current canonical title;
- the unchanged permanent ID.

The old Capture basename is not semantic input.

Classification does not simply replace `capture-` with `resource-`.

A manually renamed or stale Capture filename does not alter destination derivation.

The filename does not encode:

```text
knowledge_class
knowledge_state
scope
authority
provenance
evidence
```

The filename remains noncanonical.

The service never overwrites an existing destination.

Collision extension remains deterministic and ID-derived.

If a safe unique destination cannot be established under the accepted naming rules, classification refuses.

---

# 13. Decision D9 — Vault Routing and Target Resolution

**LOCKED — SLICE 2 ROUTING SEMANTICS PRESERVED**

Vault routing uses exactly this precedence:

```text
1. --vault
2. KV_VAULT
3. machine-local configured default Vault
4. fail
```

Routing is short-circuiting.

A valid higher-priority source prevents consultation of lower-priority sources.

A present but invalid higher-priority source fails rather than falling through.

No routing occurs from:

```text
current working directory
repository discovery
filesystem proximity
target ID search across Vaults
scope
Git state
```

Path semantics remain consistent with the accepted Capture workflow:

```text
--vault
may be relative or absolute

KV_VAULT
must resolve from an absolute path

configured default Vault
is stored as an absolute path
```

After one Vault is selected, the target ID is resolved only inside that Vault.

---

# 14. Decision D10 — Operator Authorization and Confirmation

**LOCKED**

One explicit invocation containing:

- one permanent target ID;
- one allowed Resource class;

is sufficient execution confirmation when the caller already possesses the necessary authority to perform the action.

No second interactive confirmation is required.

The class is mandatory.

The tool does not infer it.

No body, state, title, scope, evidence, rationale, provenance, authority, or acceptance input is added to the command.

Missing semantic requirements cause deterministic refusal.

The existence of `kv classify` does not grant authority to an agent, script, or automation.

CLI capability and execution authority remain separate.

Agent-autonomous classification is outside Slice 3.

---

# 15. Decision D11 — Service Ownership and Concurrency

**LOCKED**

Classification is implemented as reusable `kv_tools` service logic.

The CLI remains a thin interface.

Classification uses the same per-Vault cooperating-writer serialization mechanism used by existing canonical writers.

There is no independent classification lock.

After deterministic Vault routing, the service acquires exclusive cooperating-writer ownership **before reading mutable canonical state used to determine the operation**.

Writer ownership is held through:

```text
baseline construction
target resolution
eligibility checking
prospective construction
prospective validation
pre-mutation conflict recheck
canonical mutation
relocation
post-publication verification
completion determination
```

The lock remains transient and noncanonical.

Slice 3 introduces no daemon, persistent lock database, distributed lock, actor registry, or permission DSL.

---

# 16. Decision D12 — Atomic Mutation and Failure Truthfulness

**LOCKED**

The operation is one transactional operator action even if the filesystem implementation requires multiple guarded steps.

Exit `0` is permitted only after the service proves:

- the complete intended Resource exists at the final path;
- the permanent ID is unchanged;
- the final object matches the authorized prospective candidate;
- the old Capture path no longer represents a separate canonical Capture;
- required validation conditions remain satisfied;
- no operation-owned temporary state remains.

A semantic or conformance refusal before canonical mutation leaves the original Capture unchanged.

If execution fails after mutation begins, the service performs bounded rollback when the exact original Capture can be safely restored.

If exact restoration is proven:

```text
execution failed
original state restored
no net canonical change
```

If neither complete success nor exact restoration can be proven:

```text
INCOMPLETE / INDETERMINATE
```

The command must identify the affected ID and relevant source/destination paths and explicitly instruct the operator to inspect state before another canonical write.

Blind retry is not recommended after an indeterminate result.

The service does not intentionally persist duplicate representations of the permanent ID as a transition mechanism.

The implementation should favor continuously valid intermediate states.

If satisfying these requirements would require new persistent transaction or recovery infrastructure, the Builder must stop for design review rather than weakening the contract.

---

# 17. Decision D13 — Baseline and Prospective Validation

**LOCKED — CONSOLIDATED CORRECTION INCLUDED**

Baseline state is established while holding writer ownership.

The resulting prospective Vault is validated using the same governing validator machinery used for canonical `kv-v0` validation.

The prospective model represents replacement of one continuing identity:

```text
old Capture absent
new Resource present
same permanent ID
```

It must not represent both objects simultaneously and thereby manufacture a duplicate-ID finding.

Unrelated pre-existing findings do not automatically block classification.

Write-critical blockers include:

- validator execution failure;
- missing, malformed, ambiguous, or untrustworthy governing schema;
- invalid source target;
- unsafe filesystem boundary;
- target-critical broken references;
- target-critical ambiguous references;
- global permanent-ID duplication;
- any other condition preventing trustworthy identity-dependent mutation.

**Any persisted duplicate permanent ID anywhere in the selected Vault blocks classification.**

The prospective validation pipeline must execute normally.

The target Resource must validate.

The classification may not introduce a new attributable `ERROR`.

When distinguishing pre-existing findings from operation-attributable findings, comparison must use stable structured finding identity and permanent object identity where available rather than naïve path/message equality.

A path move alone must not manufacture a false "new error."

Warnings retain their governing severity and are surfaced truthfully.

A validator execution failure before canonical mutation is exit `2` with known no-write state.

---

# 18. Decision D14 — Historical Representation

**LOCKED**

After successful in-place classification, exactly one current canonical object remains for the permanent ID.

Slice 3 creates no:

```text
historical duplicate Capture
tombstone
redirect object
alias object
self-supersession
classification-only lineage edge
classification provenance entry
```

The old Capture path ceases representing the object.

Permanent ID provides canonical continuity.

Git history may preserve supporting filesystem history, but Git history is not required for semantic identity and is not manipulated by `kv classify`.

Durable action/time/actor history is deferred to a future separately designed capability.

---

# 19. Decision D15 — Repeat Invocation and Target-Kind Boundary

**LOCKED**

`kv classify` is exclusively a:

```text
Capture → Resource
```

workflow.

Any non-Capture target causes clean refusal.

This includes a Resource already having the requested class.

Re-running the same classification is **not** idempotent success.

Exit `0` means this invocation actually completed a Capture → Resource mutation.

If a Resource already has the requested class, the command may report the current class/state while refusing.

A Resource with another class also refuses.

Resource → Resource class correction belongs to future design.

Resource → Capture reversal is not implemented.

After a prior indeterminate outcome, current Resource state may be reported, but current state alone is not treated as proof of what the earlier invocation caused.

---

# 20. Decision D16 — CLI Name and Argument Surface

**LOCKED**

The operator-facing command is:

```text
kv classify <ID> --class <RESOURCE_CLASS> [--vault <PATH>]
```

Exact classes:

```text
claim
observation
practice
decision
concept
operating_knowledge
hypothesis
```

No aliases.

No inference.

No default.

No case normalization.

No interactive chooser.

No body/title/scope/state/evidence/rationale/provenance/authority arguments.

Invalid or missing CLI arguments fail before canonical mutation and provide corrective usage information.

Help text explains:

- Capture-only boundary;
- seven allowed Resource classes;
- each class's deterministic initial state;
- classification does not evaluate;
- classification does not accept or reject;
- classification does not rewrite;
- classification does not split or merge;
- classification does not infer class.

---

# 21. Decision D17 — Operator-Facing Result Output

**LOCKED — FAILURE TAXONOMY CLARIFIED**

Normal output is concise and deterministic.

No progress chatter is emitted.

## Success

Exit:

```text
0
```

Standard output includes at minimum:

```text
permanent ID
resulting knowledge class
initial knowledge state
final Vault-relative path
```

## Clean refusal

Exit:

```text
1
```

means:

```text
the command executed normally
the requested classification did not occur
canonical mutation did not begin
```

Standard error includes:

- concise refusal reason;
- affected permanent ID where available;
- requested class;
- useful current class/kind/state where relevant;
- explicit confirmation that no changes were made.

Examples include:

```text
target not found
target is not a Capture
target is archived
target is superseded
unsupported schema
Decision body lacks required Rationale
source is invalid
baseline changed before mutation
safe deterministic destination cannot be established
```

## Execution failure

Exit:

```text
2
```

means:

```text
the operation could not execute normally
```

This includes:

- filesystem execution failures;
- validator execution failure;
- unexpected OS failure;
- post-mutation execution failure;
- rollback execution failure;
- incomplete/indeterminate outcome.

Execution-failure output distinguishes:

```text
known no-write
proven rollback
incomplete / indeterminate
```

Indeterminate output identifies:

```text
ID
source path
destination path
```

and states that the Vault must be inspected before another canonical write.

CLI-parser usage failures occur before the classification service and follow the established `kv` CLI parser behavior.

## Vault health

A successful classification may coexist with unrelated pre-existing Vault errors.

In such a case:

- classification remains exit `0`;
- stderr warns that unrelated findings exist;
- detailed findings remain the responsibility of `kv validate`.

No JSON or verbose output mode is introduced in Slice 3.

---

# 22. Decision D18 — Git and Worktree Ownership

**LOCKED**

`kv classify` operates against the current canonical filesystem working tree.

It does not operate against Git HEAD or the Git index.

A globally dirty repository does not itself block classification.

Unrelated:

```text
modified files
staged files
untracked files
```

are operator-owned and must not be altered, cleaned, restored, staged, committed, or stashed.

Valid uncommitted edits to the target Capture are part of the current canonical source representation and must be preserved.

Rollback uses the exact pre-operation filesystem representation.

It does not use:

```text
git checkout
git restore
git reset
```

A staged target does not itself block classification.

`kv classify` does not manipulate staging state.

Where Git metadata is available, an unresolved/unmerged Git conflict affecting the target itself is write-critical ambiguity and causes refusal.

Unrelated Git conflicts do not independently block classification unless they compromise required write-critical state.

Classification does not run:

```text
git add
git mv
git commit
git push
```

Canonical mutation, Git staging, Git commit, operator acceptance, and release are separate actions.

Git is not required for core classification correctness.

---

# 23. Decision D19 — Preflight and Dry-Run Behavior

**LOCKED**

Slice 3 has no operator-facing:

```text
--dry-run
--preview
--check
--confirm
```

classification mode.

Prospective construction and validation remain mandatory internally.

A valid classification invocation requests a real mutation.

It either:

- completes;
- refuses;
- or fails truthfully.

Exit `0` remains reserved for a mutation actually completed by that invocation.

A future inspection, proposal, readiness, or preview capability requires separate design.

---

# 24. Decision D20 — Schema-Version Eligibility

**LOCKED**

Initial `kv classify` supports only:

```text
schema: kv-v0
```

The source Capture must be validly governed by `kv-v0`.

The resulting Resource remains:

```text
schema: kv-v0
```

Classification does not migrate schemas.

It does not infer future compatibility.

It does not reinterpret future schemas as kv-v0.

A valid but unsupported schema causes compatibility refusal.

Malformed, missing, ambiguous, or untrustworthy schema state follows the write-critical failure rules.

Tool version and schema version remain independent concepts.

Future schema support must be explicitly implemented.

Schema migration remains a separate workflow.

---

# 25. Decision D21 — Timestamps and Operation History

**LOCKED**

The existing:

```text
created
```

value is preserved exactly.

Classification adds no canonical:

```text
modified
updated
classified_at
reclassified_at
processed_at
```

or equivalent timestamp.

Filesystem mtime and Git timestamps are not canonical metadata.

Classification does not use the current clock merely because a classification occurred.

No hidden or sidecar classification history file is added.

No transaction/event history database is introduced.

Future durable action/time/actor history requires separate design.

---

# 26. Decision D22 — Provenance Preservation

**LOCKED**

The complete valid and materially meaningful source provenance is preserved unchanged.

Classification does not:

```text
add provenance
remove provenance
rewrite provenance
reinterpret provenance
normalize provenance for semantic purposes
replace provenance based on class
```

Provenance records origin and lineage.

It does not record:

```text
Resource class
evidence
standing
acceptance
authority
classification action
```

Invalid provenance makes the source Capture ineligible.

Classification does not repair provenance.

Future provenance correction or augmentation requires a separately authorized maintenance workflow.

If a future schema creates a provenance constraint incompatible with preservation, prospective validation refuses rather than rewriting history.

---

# 27. Decision D23 — Exact Body Preservation

**LOCKED**

The source canonical body payload is preserved **byte-for-byte**.

Classification grants no authority to:

```text
normalize
trim
rewrite
correct
summarize
restructure
reflow
expand
contract
Unicode-normalize
newline-normalize
```

the body.

Preservation includes:

- UTF-8 byte sequence;
- Unicode representation;
- spaces;
- tabs;
- blank lines;
- Markdown syntax;
- punctuation;
- LF;
- CRLF;
- bare CR;
- mixed newline forms;
- presence or absence of final newline.

The body payload begins after the valid YAML-frontmatter closing serialization boundary.

The service may decode or parse the body for validation and class-specific structural requirements.

Such interpretation does not authorize reserialization of the body.

Preservation and post-publication verification must use byte-aware behavior and must not rely on text readers that silently perform universal-newline or Unicode normalization.

If exact body preservation cannot be safely established, classification refuses or fails truthfully rather than normalizing content for convenience.

---

# 28. Decision D24 — Frontmatter Serialization

**LOCKED — CONSOLIDATED**

Exact source YAML presentation is not identity-bearing and is not preserved.

Operator clarification: a canonical metadata field valid on the source Capture, valid on the resulting Resource, and unchanged in semantic meaning by classification is preserved unchanged. This includes valid `relationships`. Invalid, unknown, prohibited, or semantically reinterpreted fields are refused rather than copied, translated, or silently deleted.

The service parses the valid source frontmatter, preserves the semantic values authorized by D5, applies the permitted classification changes, and serializes the resulting Resource frontmatter deterministically.

The initial normal Resource order is:

```text
schema
id
title
kind
state
scope
created
provenance
knowledge_class
knowledge_state
```

A valid `kv-v0` Capture has no Capture-specific conditional metadata.

Therefore the ordinary Slice 3 result is exactly:

```text
universal core metadata
+
knowledge_class
+
knowledge_state
```

Slice 3 does not define an open-ended carry-forward mechanism for fields that would make the Capture invalid under its original contract.

Frontmatter uses deterministic UTF-8 YAML serialization and LF line endings.

Frontmatter field order remains a presentation convention, not semantic authority.

Incidental source YAML formatting is not preservation-bearing, including:

```text
quote style
indentation quirks
key ordering
spacing
blank lines inside frontmatter
YAML comments
```

Substantive knowledge belongs in the Markdown body.

The deterministic frontmatter serialization boundary must not alter the exact body bytes protected by D23.

---

# 29. Decision D25 — Shared Navigation Filename Generation

**LOCKED**

Capture and Resource navigation filenames use one shared deterministic naming mechanism.

Conceptual forms:

```text
capture-<title-slug>-<ID-fragment>.md

resource-<title-slug>-<ID-fragment>.md
```

The slug is derived from the current canonical title.

The collision-resistant component is derived from the permanent ID.

The Resource workflow reuses the existing accepted Capture semantics for:

- slug generation;
- cross-platform filename safety;
- maximum filename length;
- ID fragment generation;
- deterministic collision extension.

If implementation requires extracting existing Capture filename behavior into a reusable helper, existing Capture behavior must remain unchanged.

Shared implementation does not authorize naming redesign.

Destination collisions are never resolved using:

```text
overwrite
random suffix
directory-order counter
-1
-2
-copy
-final
```

Any extension remains deterministically ID-derived.

Filename prefixes and slugs remain noncanonical navigation aids.

---

# 30. Decision D26 — Filesystem Boundary and Link Safety

**LOCKED**

After D9 selects one Vault, the service resolves a stable physical Vault root.

That resolved root becomes the entire filesystem mutation boundary for the invocation.

Every:

```text
source path
destination path
temporary publication path
rollback path
```

must remain physically contained within that root.

Containment must use filesystem-aware resolution rather than naïve string-prefix matching.

The target Capture must resolve to a regular file physically contained in the selected Vault.

Classification does not mutate the target through an internal:

```text
symbolic link
junction
reparse-point file
equivalent indirection
```

The destination `30_resources/` path and its write-critical parent path components must likewise resolve safely inside the same Vault boundary.

The operation must not escape through:

```text
..
absolute path injection
drive switching
UNC redirection
symlink
junction
mount indirection that violates the established boundary
```

The operator-supplied Vault root path itself may be an alias/link to the physical Vault.

That alias may be resolved once.

The resolved physical root then becomes authoritative for containment checks.

Unrelated links elsewhere in the Vault do not automatically block classification unless they affect the target, destination, governing interpretation, references, or another write-critical invariant.

Temporary operation state remains transient and noncanonical.

D26 does not authorize a persistent hidden runtime directory.

---

# 31. Decision D27 — Filesystem Capability Requirements

**LOCKED**

Classification proceeds only when the underlying filesystem and path arrangement provide the publication, rename/replace, containment, rollback, and verification semantics required by D12.

The service does not silently downgrade to a weaker copy-delete workflow merely because preferred same-filesystem rename/replace semantics are unavailable.

A fallback is permitted only if it independently satisfies every already-locked transactional invariant.

Otherwise classification refuses or fails before unsafe canonical mutation.

`05_inbox/` and `30_resources/` are expected to permit compatible movement inside one Vault filesystem/volume.

If mount, device, volume, or filesystem boundaries make that impossible under the required guarantees, the initial workflow is unsupported.

Platform-specific Windows and Linux implementation techniques are permitted when they produce the same operator-visible correctness contract.

The tool does not claim universal transactional behavior across every:

```text
SMB
NFS
FUSE
cloud-sync virtual filesystem
network filesystem
exotic virtual storage layer
```

Support exists only when required guarantees can be established.

Uncertainty causes refusal rather than best-effort mutation.

---

# 32. Decision D28 — Concurrent External Modification Detection

**LOCKED**

The shared Vault writer lock coordinates cooperating `kv_tools` writers only.

Classification additionally performs optimistic conflict detection against non-cooperating filesystem actors such as editors or unrelated scripts.

While holding writer ownership, the service captures an exact baseline sufficient to identify the source representation it validated.

The baseline includes at minimum:

- resolved source path;
- permanent ID;
- exact canonical source bytes;
- exact body bytes;
- parsed canonical metadata;
- reliable filesystem identity/state where available.

Immediately before the first canonical mutation, the service verifies that the target and write-critical dependencies remain consistent with the validated baseline.

The invocation refuses without mutation if the target:

```text
changes
disappears
is replaced
changes file type
changes link status
changes permanent ID
changes canonical bytes
moves outside the safe boundary
otherwise invalidates the baseline
```

Where reliable filesystem identity information exists, replacement of the underlying file is treated conservatively as a conflict even if resulting bytes happen to match.

The prospective destination must also remain valid and available.

If external mutation invalidates the previously validated destination, the invocation refuses rather than silently selecting a different transaction plan late in execution.

The service does not:

```text
re-read changed content and continue
merge external edits
automatically retry until stable
```

One invocation operates on one established source baseline.

If that baseline changes before mutation, that invocation is over.

Interference after the final safe pre-mutation check is handled through D12 post-publication verification, rollback, and indeterminate-state semantics.

Slice 3 introduces no whole-Vault hash database, watcher, generation counter, daemon, or distributed transaction infrastructure.

---

# 33. Decision D29 — Writer-Lock Recovery

**LOCKED**

`kv classify` reuses the same shared per-Vault writer-ownership mechanism already accepted and hardened for canonical Vault writes.

It reuses the existing:

```text
lock format
ownership token behavior
process liveness checks
stale-lock determination
safe reclamation behavior
wait/refusal semantics
```

Classification does not create a second lock namespace.

A lock whose owner is established as live prevents concurrent classification according to the existing ownership contract.

A stale lock is reclaimed only when the shared implementation can establish that reclamation is safe.

Ambiguous ownership is not treated as stale.

Classification does not expose:

```text
--force
--break-lock
```

or equivalent bypass behavior.

Safe lock reclamation does not grant authority to delete unrelated temporary files or unexplained artifacts from a previous operation.

If unexplained filesystem state compromises trustworthy execution, classification refuses.

Any future manual recovery capability requires separate design.

---

# 34. Decision D30 — Scope and Reference Integrity

**LOCKED — CONSOLIDATED**

Classification preserves existing valid:

```text
scope
provenance refs
other universal/reference state legitimately present under the Capture contract
```

unchanged.

Preservation does not waive reference-integrity requirements.

Every reference required to establish the source Capture's validity and the prospective Resource's validity must remain sufficiently trustworthy.

A required target that is:

```text
missing
ambiguous
wrong kind
invalidly self-referential
cyclic where prohibited
otherwise contract-invalid
```

blocks classification.

The classifier does not repair, replace, delete, infer, redirect, broaden, or narrow references to make the operation succeed.

Target-relevant reference failure is write-critical even when pre-existing.

Unrelated Vault findings remain governed by D6/D13.

Reference checking remains bounded to the facts necessary to establish the target object's own governing contract.

Classification does not require every transitively reachable unrelated object to be finding-free.

Referenced objects do **not** automatically have to be `state: active`.

Where `kv-v0` preserves the validity or historical meaning of a reference to a superseded or archived object, classification preserves that reference and does not reject it merely because the referenced object's lifecycle state is non-active.

The Capture being classified itself remains subject to D6 and must be active.

Duplicate-ID ambiguity is never resolved through:

```text
path preference
first match
title similarity
filesystem order
timestamp
content similarity
```

Write-critical reference facts used during prospective validation must remain trustworthy through publication under D28.

For referenced objects, conflict detection protects the semantic facts classification depends upon; unrelated body edits do not necessarily require byte identity when they do not alter those facts.

Classification performs no:

```text
cross-Vault ID search
placeholder creation
scope fallback
reference migration
reference repair
```

---

# 35. End-to-End Operational Contract

The normal successful workflow is:

```text
operator invokes:
kv classify <ID> --class <CLASS>

↓
resolve exactly one Vault

↓
resolve physical Vault boundary

↓
acquire shared Vault writer ownership

↓
build baseline registry and governing schema state

↓
verify global permanent-ID uniqueness

↓
resolve exactly one target permanent ID

↓
capture exact source representation

↓
verify:
schema = kv-v0
kind = capture
state = active
source object valid
target references trustworthy
identity continuity appropriate

↓
construct prospective Resource:
same schema
same id
same title
kind = resource
same lifecycle state
same scope
same created
same provenance
selected knowledge_class
deterministic initial knowledge_state
same exact body bytes

↓
derive deterministic Resource filename/path

↓
validate prospective resulting Vault:
old Capture absent
Resource same ID at final path

↓
ensure no new attributable ERROR

↓
recheck target and write-critical external-conflict assumptions

↓
perform coherent canonical mutation

↓
verify final canonical state

↓
remove operation-owned transient state

↓
report confirmed success
```

---

# 36. Clean Refusal Invariant

If classification refuses before canonical mutation:

```text
the original Capture remains canonically unchanged
```

Where byte preservation is applicable:

```text
original source bytes before invocation
==
source bytes after refusal
```

No:

```text
partial Resource
temporary canonical object
alternate ID
history record
Git mutation
```

is left behind.

---

# 37. Execution-Failure Invariant

If an execution failure occurs before canonical mutation:

```text
exit 2
known no-write
```

If an execution failure occurs after canonical mutation begins:

```text
attempt exact bounded rollback when safe
```

If rollback is proven:

```text
exit 2
original state restored
```

If neither complete success nor exact original restoration can be proven:

```text
exit 2
INCOMPLETE / INDETERMINATE
inspect before another canonical write
```

The command never converts uncertainty into a false success or a false no-write claim.

---

# 38. Required Implementation Boundaries

Slice 3 may implement:

- reusable classification service;
- thin `kv classify` CLI;
- shared filename helper extraction where necessary;
- parser/runtime support needed for exact body-byte preservation;
- prospective replacement validation;
- safe filesystem mutation and rollback logic;
- external modification detection;
- required deterministic reporting;
- synthetic/public-safe test coverage.

Slice 3 may refactor existing code only when necessary to support the accepted contract and only while preserving already accepted Slice 1 and Slice 2 behavior.

Refactoring does not authorize semantic redesign.

---

# 39. Explicitly Out of Scope

Do not implement:

```text
automatic class inference
agent-autonomous classification
Resource evaluation
accept/reject commands
evidence maintenance
authority maintenance
relationship creation
scope editing
title editing
provenance editing
body editing
distillation
summarization
Capture splitting
Capture merging
derived-object creation
Resource → Resource reclassification
Resource → Capture reversal
archival
supersession
Source ingestion
arbitrary file/PDF ingestion
schema migration
future-schema support
Git automation
Git staging
Git commits
Git pushes
transaction database
persistent journal
event history
audit database
daemon
watcher
filesystem monitor
database
persistent index
graph engine
embeddings
semantic search
UI
network service
distributed locking
permission DSL
JSON output
dry-run/preview mode
```

If one of these appears necessary to satisfy Slice 3, the Builder must stop and return the dependency for design review.

---

# 40. Required Test Families

The implementation must include synthetic/public-safe tests covering at least the following bounded families.

## A. CLI and routing

- all seven class values;
- missing/invalid class;
- missing ID;
- `--vault` routing;
- `KV_VAULT` routing;
- configured default routing;
- short-circuit precedence;
- invalid higher-priority routing without fallback;
- no CWD discovery.

## B. Eligibility

- one valid active Capture succeeds;
- missing target refuses;
- ambiguous target refuses;
- Resource target refuses;
- archived Capture refuses;
- superseded Capture refuses;
- invalid source Capture refuses;
- unsupported schema refuses;
- any Vault-wide duplicate persisted ID blocks classification.

## C. Class/state mapping

Verify exact mapping:

```text
claim → unassessed
observation → recorded
practice → candidate
decision → proposed
concept → emerging
operating_knowledge → proposed
hypothesis → unresolved
```

Verify no caller override exists.

## D. Class-specific prospective validity

At minimum:

- Decision with valid Rationale structure can classify;
- Decision without required Rationale refuses unchanged;
- other classes use only their valid initial-state requirements;
- classification never manufactures evidence or authority.

## E. Identity and metadata preservation

Verify exact preservation of:

```text
schema
id
title
state
scope
created
provenance
```

Verify exactly:

```text
kind = resource
knowledge_class = selected class
knowledge_state = deterministic initial state
```

## F. Body fidelity

Exercise exact byte preservation for:

- LF;
- CRLF;
- bare CR;
- mixed newlines;
- no final newline;
- final newline;
- leading/trailing blank lines;
- tabs;
- repeated spaces;
- Unicode;
- composed/decomposed Unicode;
- Markdown/code-like content.

Assert:

```text
before_body_bytes == after_body_bytes
```

## G. Filename and relocation

- current canonical title drives Resource slug;
- stale/manual source basename is ignored;
- permanent ID drives collision component;
- destination is under `30_resources/`;
- deterministic collision extension;
- no overwrite;
- source already equal to final destination path;
- no duplicate canonical ID representation remains after success.

## H. Prospective validation

- old Capture is modeled absent;
- Resource same ID is modeled present;
- no synthetic duplicate-ID finding is manufactured;
- new attributable errors block;
- unrelated pre-existing errors may remain;
- warnings preserve severity;
- validator execution failure is exit `2`.

## I. References

- valid scope preserved;
- missing scope target blocks;
- ambiguous scope target blocks;
- wrong-kind scope target blocks;
- permitted archived/superseded historical reference remains valid;
- target-critical provenance/reference integrity is enforced;
- unrelated graph defects do not cause unnecessary global paralysis.

## J. Concurrency

- cooperating writers serialize through shared lock;
- existing stale-lock behavior remains correct;
- ambiguous lock ownership is not stolen;
- external target modification before mutation causes clean refusal;
- target replacement is detected where reliably observable;
- destination race is detected without overwrite.

## K. Filesystem safety

- path containment;
- source symlink/reparse refusal;
- destination redirection refusal;
- traversal prevention;
- incompatible filesystem/volume behavior refuses safely;
- no unsafe copy-delete fallback.

## L. Failure and rollback

Exercise:

- known no-write refusal;
- execution failure before mutation;
- mutation failure with proven rollback;
- simulated post-mutation uncertainty;
- no false exit `0`;
- no false clean-refusal exit `1` after mutation begins;
- no operation-owned residual temp state after confirmed success or proven rollback.

## M. Git independence

- dirty unrelated worktree does not block;
- uncommitted valid target edits are preserved;
- staged target does not trigger Git manipulation;
- unresolved target conflict refuses where Git metadata is available;
- no Git staging, commit, reset, restore, or cleanup occurs.

## N. Regression

All accepted Slice 1 and Slice 2 tests must remain passing.

---

# 41. Builder Authority Boundary

The Builder is authorized only to implement this accepted Slice 3 contract when implementation authority is separately granted.

The Builder may choose implementation details inside the locked behavioral boundaries.

The Builder may not:

- weaken `kv-v0`;
- reinterpret a locked decision;
- expand Slice 3 into a generalized editor;
- add persistent infrastructure because it is convenient;
- infer operator authority;
- repair unrelated Vault defects;
- silently redesign existing Capture behavior;
- rewrite historical Slice 1 or Slice 2 records;
- access real private canonical data unless a later task explicitly authorizes a bounded private-Vault operation.

If a requirement cannot be satisfied:

```text
stop
preserve evidence
report the contradiction
request design review
```

A failing test does not authorize weakening an invariant.

---

# 42. Independent Audit Requirement

Builder completion does not establish acceptance.

After Builder implementation and Builder-side validation, Slice 3 requires an independent whole-slice audit.

The Auditor must independently verify:

- contract traceability;
- exact target/class behavior;
- body-byte fidelity;
- global identity safety;
- prospective validation;
- routing;
- reference integrity;
- writer serialization;
- external-edit detection;
- filesystem containment;
- relocation;
- rollback;
- truthful output/exit behavior;
- no regression of Slice 1 or Slice 2;
- no unauthorized scope expansion.

A Builder PASS is not an Auditor PASS.

An Auditor PASS is not operator closure.

---

# 43. Operator Acceptance and Closure Boundary

The lifecycle is:

```text
DESIGN ACCEPTED
↓
implementation authorization
↓
Builder implementation
↓
Builder validation
↓
independent audit
↓
bounded remediation / re-audit if needed
↓
operator implementation acceptance
↓
authorized operational verification if desired
↓
closeout documentation
↓
operator closure
```

Only the operator may declare Slice 3 closed.

Neither Builder nor Auditor may close the slice.

Historical failures, remediation, and re-audit evidence must remain historically truthful.

---

# 44. Definition of Done

Slice 3 implementation is complete only when:

- `kv classify` exists with the exact accepted surface;
- all seven Resource classes map to the correct deterministic starting states;
- exactly one valid active `kv-v0` Capture can be classified in place;
- permanent identity is preserved;
- title, lifecycle state, scope, created date, provenance, and body are preserved according to this contract;
- body bytes are proven exact;
- resulting Resource frontmatter is deterministic;
- the object is navigationally placed in `30_resources/`;
- no duplicate canonical representation remains;
- global ID ambiguity prevents identity-dependent mutation;
- relevant references remain trustworthy;
- prospective validation proves the replacement state before mutation;
- external modifications cannot be knowingly overwritten;
- existing cooperating-writer safety remains intact;
- filesystem mutation obeys containment and capability requirements;
- success, refusal, rollback, failure, and indeterminate outcomes are reported truthfully;
- no persistent runtime infrastructure is introduced;
- all Slice 3 tests pass;
- all prior Slice 1 and Slice 2 regression tests pass;
- independent audit satisfies the acceptance gate;
- the operator explicitly accepts the implementation.

Implementation completion is not equivalent to operator closure.

---

# 45. Slice Boundary Summary

Slice 3 answers exactly one operator question:

> **“What Resource class is this existing Capture?”**

It does not answer:

> Is it true?

> Is it accepted?

> Is it supported?

> Should its scope change?

> What evidence should be attached?

> Should its wording be improved?

> Should it become several objects?

> Should an agent classify it automatically?

Those remain future bounded workflows.

The intended processing sequence therefore remains:

```text
Capture
↓
Operator-Directed Classification
↓
Resource at deterministic initial state
↓
future evaluation / evidence / acceptance workflows
```

Slice 3 ends immediately after safe, validated, truthful Capture → Resource classification of one continuing canonical identity.
