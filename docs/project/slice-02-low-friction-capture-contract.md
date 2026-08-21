# The Vault — Slice 2 Low-Friction Capture Contract

## Identity

- Project: The Vault / The Backlot
- Slice: Slice 2 — Low-Friction Capture
- Contract date: 2026-08-21
- Schema: `kv-v0`
- Public tooling repository: The Backlot
- Implementation target: `knowledge-vault-tools`
- Current public release baseline: `v0.1.0`
- Status: **ACCEPTED — IMPLEMENTATION NOT YET AUTHORIZED**

This document turns the accepted Capture design decisions into a bounded implementation contract.
It does not change `kv-v0`, reopen Slice 1, authorize implementation, initialize another vault, or
grant agents authority beyond the task that explicitly invokes this contract.

## Governing Authority

For semantic and implementation interpretation, apply this order:

1. `Knowledge Vault V0 — Canonical Specification (Design Accepted)`
2. The active repository-native `kv-v0` Schema Meta contract
3. Locked Knowledge Vault Architecture Decisions 1–8
4. Locked Capture Decisions 1–18 summarized in this contract
5. Existing Slice 1 closeout, traceability, and implementation records
6. This contract as the bounded Slice 2 implementation record

If this contract conflicts with the canonical `kv-v0` specification, the canonical specification wins.
If implementation pressure exposes a genuine contradiction, stop the smallest affected work and report
it rather than weakening the governing contract by inference.

## Objective

Implement the first trustworthy live-knowledge write workflow for the Knowledge Vault:

> Preserve operator-originated text as a valid canonical `kind: capture` object with minimal operator
> input, deterministic metadata, explicit target resolution, bounded validation, crash-safe publication,
> and no automatic interpretation or downstream processing.

Normal success path:

```text
operator text
  -> resolve one Vault
  -> acquire cooperating write ownership
  -> inspect write-critical Vault state
  -> generate Capture metadata
  -> construct complete candidate
  -> prospectively validate resulting Vault state
  -> atomically publish under 05_inbox/
  -> concise confirmation
  -> stop
```

Capture means **preservation only**. It does not mean understanding, classification, evaluation,
acceptance, project routing, source ingestion, archival, or action.

## Initial CLI Surface

Primary manual form:

```text
kv capture --text "<content>"
```

Standard input is the alternate content channel when `--text` is absent.

Optional Capture arguments:

```text
--title <title>
--scope <kv-ID>
--vault <path>
```

Initial machine-configuration commands:

```text
kv config set-default-vault <path>
kv config show
kv config clear-default-vault
```

No short-option aliases are required by this slice.

## Locked Capture Decisions

### Decision 1 — Verbatim body preservation

A Capture preserves operator-supplied content as given. Capture creation may perform only
storage-required normalization and must not semantically rewrite, summarize, correct, classify,
or enrich the content.

Storage-required normalization is limited to mechanical serialization necessary to represent the
supplied text safely as canonical Markdown. It must not normalize Unicode characters, trim leading
or trailing content whitespace, collapse spaces, remove blank lines, change punctuation, or
otherwise alter textual meaning. Platform/newline serialization may use a deterministic text
representation, but logical line structure and all non-newline content must be preserved.

### Decision 2 — Title derivation

Title precedence is:

1. operator-supplied title;
2. extractive title from captured content;
3. mechanical fallback when safe extraction is not possible.

Title derivation may select, trim, normalize, or truncate operator-supplied language but may not
introduce substantive words, concepts, conclusions, or certainty absent from the captured content.
The title is navigation metadata, not identity or an authoritative semantic summary.

### Decision 3 — Physical persistence

A new Capture is constructed as a complete candidate before canonical persistence.

Default physical destination:

```text
05_inbox/
```

`kind: capture`, not folder location, is semantic authority.

The filename is a human-recognizable derivative of the Capture title plus a collision-resistant
fragment derived from the permanent ID. Filenames carry no canonical semantic meaning.

The Markdown file contains generated `kv-v0` frontmatter followed directly by the verbatim
operator-supplied body. No generated body heading or semantic enrichment is added.

The candidate must pass applicable validation before publication. Failure must not leave a
partially written canonical object.

### Decision 4 — Scope default

A Capture with no explicitly supplied narrower scope is scoped to the Vault's designated root object.

Capture creation discovers the root from the target Vault and does not hardcode a permanent ID.
The system does not infer scope from wording, filename, directory, current working directory,
recent activity, or agent judgment.

An explicitly supplied narrower scope must resolve validly before publication. Invalid or ambiguous
scope fails rather than silently falling back to root.

Initial `--scope` input accepts a permanent `kv-...` ID only.

### Decision 5 — Provenance default

The ordinary content-only Capture workflow is operator-originated and defaults to:

```yaml
provenance:
  - kind: operator
```

A tool or agent that merely transports, formats for storage, validates, or persists verbatim
operator-originated input does not gain `agent` provenance.

Additional or different provenance is not inferred from URLs, quoted-looking text, filenames,
content patterns, or other heuristics.

### Decision 6 — Operator-facing contract

The Capture operation targets one explicitly resolved Vault and requires only content.

Optional operator overrides are limited to title, narrower scope, and explicit Vault target.
All other canonical metadata and persistence mechanics are generated by the system.

Successful acknowledgement is concise and identifies the created Capture.

### Decision 7 — Vault target resolution

Target resolution precedence is:

1. explicit `--vault` path;
2. explicit `KV_VAULT` environment value;
3. machine-local configured default Vault;
4. otherwise fail.

Selection is not inferred from captured content, current working directory, nearby repositories,
recent activity, filesystem scanning, or agent judgment.

If a higher-priority target is supplied but invalid, resolution fails rather than falling through.

Vault-target resolution is precedence-ordered and short-circuiting. Once a higher-precedence
routing source is present and successfully resolves to a compatible Vault, lower-precedence routing
sources are not consulted and defects in those unused sources do not affect that invocation. If the
selected higher-precedence source is present but invalid, resolution fails rather than consulting a
lower-precedence source.

Machine-local routing is operational state, not canonical knowledge. The resolved target must still
be verified as a compatible Vault before publication.

### Decision 8 — Content intake boundary

The initial Capture workflow accepts operator-supplied textual content only.

Content may come from `--text` or standard input, but the channels must not compete or be
silently merged.

URLs, paths, Markdown, code, quotations, and other textual forms are opaque content during intake.
Capture does not fetch, dereference, import, classify, enrich, or infer external provenance.

Source ingestion, file import, attachments, clipboard-specific behavior, and richer intake are
separate future workflows.

### Decision 9 — Completion boundary

A successful Capture operation ends when the supplied content has been safely published as a
valid canonical `kind: capture` object and confirmation has been returned.

Capture creation performs no automatic classification, distillation, promotion, evidence evaluation,
relationship creation, project routing, acceptance, archival, deletion, or downstream action.

Later processing may reclassify one continuing object in place while preserving permanent identity.
If processing produces multiple or materially transformed knowledge objects, those receive new
permanent IDs with meaningful provenance and the original Capture is preserved.

Successful Capture establishes preservation, not understanding, truth, acceptance, or completion.

### Decision 10 — Failure and operator confirmation

Success is reported only after:

- exactly one target Vault is resolved;
- exactly one content input is acquired;
- required generated metadata and scope are resolved;
- a complete candidate passes applicable validation;
- the canonical file is safely and atomically published.

`kv capture` never overwrites an existing canonical file.

Atomic publication must ensure interruption can leave at most a complete canonical Capture or
no Capture, never a partially written canonical object.

A clean refusal before publication guarantees no canonical Capture was written. A known
pre-publication execution failure likewise guarantees no write.

If publication may have begun and final state cannot be established with certainty, the tool must
not falsely claim success or no-write. When it retains control, it reports an **indeterminate**
outcome and must not encourage a blind retry that could create another Capture with a new ID.

Successful confirmation includes:

- title;
- permanent ID;
- canonical relative path.

The captured body is not echoed by default.

Exit behavior:

```text
0 = successfully published
1 = cleanly refused; no publication
2 = could not execute normally
```

An exit-2 message must distinguish a known no-write condition from an indeterminate publication
outcome when that distinction is known.

Validation warnings retain their existing non-failing meaning and are surfaced.

### Decision 11 — Write ownership

Canonical Capture creation is owned by the bounded Knowledge Vault Capture service/library
exposed through `kv capture`.

Operator interfaces, agents, scripts, and other transports submit requests but do not directly
construct or persist canonical Capture files.

The caller must already possess execution permission to request the write. Access to the CLI,
filesystem, or Capture API does not itself create semantic or execution authority.

`kv capture` owns deterministic metadata generation, validation, collision-safe publication, and
confirmation. It does not infer or manufacture caller authority.

Machine-enforceable delegation and permission policy remain outside this slice.

### Decision 12 — Minimal concurrency boundary

Within one local Vault working tree, cooperating canonical writers are serialized so only one
Knowledge Vault writer owns the write boundary at a time.

The writer acquires exclusive ownership **before reading state on which the write depends** and
retains it through:

```text
baseline inspection
-> candidate construction
-> applicable validation
-> atomic publication
-> completion / rollback
```

Competing cooperating writers may wait or fail cleanly without interleaving canonical mutation.

The coordination mechanism is transient operational state and never becomes `kv-v0` metadata
or canonical knowledge.

This slice does not claim distributed coordination across separate clones, machines, Git histories,
or external/manual filesystem edits.

`kv capture` performs no automatic Git commit, pull, merge, push, or conflict resolution.

### Decision 13 — Pre-existing Vault state

`kv capture` does not require:

- a clean Git working tree;
- synchronized Git history;
- an entirely error-free Vault as a universal write precondition.

Before publication, Capture must establish that write-critical dependencies and global invariants
required for safe Capture remain trustworthy, including:

- governing schema;
- designated root;
- identity registry and uniqueness;
- target scope resolution;
- filesystem write boundary.

The following block Capture when they prevent safe interpretation:

- validator execution failure;
- duplicate or indeterminate identity state;
- ambiguous or unavailable governing schema;
- ambiguous or unavailable root;
- invalid required scope;
- any equivalent write-critical condition.

Pre-existing conformance failures outside the Capture dependency boundary may remain without
globally blocking an otherwise safe Capture, consistent with bounded stopping.

The prospective resulting state must introduce no new `ERROR` findings attributable to the Capture.

Capture does not repair, normalize, commit, merge, or otherwise alter unrelated existing state.

When Capture succeeds while pre-existing conformance errors remain, acknowledgement must
distinguish successful Capture publication from overall Vault health and disclose that pre-existing
errors remain.

### Decision 14 — Machine-local configuration ownership

Knowledge Vault machine configuration is noncanonical operational state owned by the local `kv`
installation and stored outside all Vault repositories in the platform-appropriate per-user
configuration location.

Initial configuration contains only an optional default Vault-root path.

It must not duplicate canonical Vault identity, schema, root IDs, knowledge metadata, Git state,
credentials, or agent authority.

Setting, changing, or clearing the default requires explicit operator action. `kv init`, validation,
Capture, repository operations, and ordinary Vault use do not silently change it.

The configured default is stored as an absolute machine-local path, verified when configured, and
reverified when used.

Missing, stale, malformed, or unreadable configuration fails explicitly rather than triggering
filesystem discovery, silent repair, or inferred fallback.

Machine configuration is not a credential store. Named/multiple-Vault registries are deferred.

### Decision 15 — CLI surface and argument semantics

Primary manual command:

```text
kv capture --text "<content>"
```

If `--text` is absent and redirected/piped standard input exists, standard input is used.

Supplying both channels is an error.
Supplying neither causes an immediate clean refusal with actionable usage guidance rather than
entering an implicit interactive mode.

Optional Capture arguments are exactly:

```text
--title <title>
--scope <kv-ID>
--vault <path>
```

`--scope` performs no title, alias, fuzzy, or inferred resolution.

Invocation-local `--vault` may use an explicitly supplied relative or absolute path.

Empty or whitespace-only content is refused, without trimming or otherwise rewriting the accepted
body after the non-whitespace check.

An explicitly supplied title must be non-empty and single-line; otherwise Decision 2 applies.

Capture must never silently truncate content. If implementation requires an operational size limit,
the limit must be documented and excess input must be refused before publication.

Initial configuration commands are exactly:

```text
kv config set-default-vault <path>
kv config show
kv config clear-default-vault
```

Absence of a configured default Vault is a valid machine state. When no default has ever been
configured, `kv config show` succeeds with exit status `0` and reports that the default Vault is
not configured. `kv config clear-default-vault` is idempotent: if no default is configured, it also
succeeds with exit status `0` and reports that the default is already unset. This does not weaken
Decision 18: malformed, unsupported, unreadable, or otherwise invalid configuration remains an
explicit configuration error.

CLI help and failure messages must explain the operation and corrective action in
operator-understandable language.

### Decision 16 — Generated core metadata

For an ordinary new Capture, `kv` generates all non-operator-supplied universal metadata required
by `kv-v0`.

```yaml
schema: kv-v0
id: <new permanent kv-UUIDv7>
title: <Decision 2 or explicit title>
kind: capture
state: active
scope: <Decision 4>
created: <Decision 16 local calendar date>
provenance:
  - kind: operator
```

The initial Capture CLI does not allow overriding generated `schema`, `id`, `kind`, `state`,
`created`, or provenance.

`created` is derived once from the local calendar date of the machine executing the Capture
transaction, using the operation time captured when candidate identity is created.

That date remains unchanged if validation or publication crosses midnight.

Remote-source timestamps, content dates, filesystem timestamps, Git timestamps, or inferred dates
do not substitute for `created`.

### Decision 17 — Origin and agent contribution

The initial `kv capture` workflow is an operator-originated knowledge intake path.

Provenance reflects origin of knowledge, not the process, interface, agent, script, or device that
transported the request.

An authorized agent or software transport that merely transmits, escapes, formats for storage, or
invokes Capture on verbatim operator-originated content does not acquire `agent` provenance.

If an agent materially authors, rewrites, summarizes, synthesizes, expands, reasons about, or
otherwise contributes knowledge to the payload, that material must not be persisted through this
initial operator-Capture path with sole `operator` provenance.

General provenance-capable intake for agent-authored, external, derived, project-originated, or
mixed-origin material is a separate future workflow.

`kv capture` does not infer provenance from text content and exposes no provenance-control CLI
flags in this slice.

Execution authorization and knowledge provenance remain separate concerns.

Decision 17 does not weaken Decision 1: minor non-semantic handling may remain operator
provenance, but `kv capture` itself still does not receive authority to semantically clean or rewrite
the Capture body.

### Decision 18 — Environment routing and TOML configuration

`KV_VAULT` is an explicit runtime routing mechanism and must contain a non-empty **absolute**
path to a Vault root.

Relative `KV_VAULT` values are invalid and are refused rather than resolved against the process
working directory.

`kv` does not perform filesystem discovery, home-directory shorthand expansion, environment
variable interpolation, or inferred path resolution on `KV_VAULT`.

If `KV_VAULT` is present but invalid, target resolution fails and does not fall through to the
configured default.

Machine-local configuration format for this slice is **TOML**.

The configuration file is named:

```text
config.toml
```

and lives in the platform-appropriate per-user Knowledge Vault configuration directory outside all
Vault repositories.

The initial TOML surface contains exactly one supported setting:

```toml
default_vault = '<absolute machine-local Vault-root path>'
```

No canonical identity, root ID, schema ID, Git state, credentials, authority, provenance, agent
configuration, or other knowledge metadata is stored there.

An existing configuration file must be valid TOML and contain only settings understood by this
configuration generation.

Malformed TOML, unsupported keys/tables, an invalid `default_vault` type, or a non-absolute
stored path produces an explicit configuration error rather than silent repair, ignored
configuration, inferred fallback, or destructive overwrite.

Configuration writes must be crash-safe so interrupted updates do not leave a partially written
configuration file.

`set-default-vault` normalizes and stores the resolved absolute path.
`clear-default-vault` removes the supported setting and may remove `config.toml` when no supported
settings remain. If no default Vault is configured, `show` reports that valid absence and exits `0`;
`clear-default-vault` is an idempotent success and exits `0`. Invalid existing configuration remains
an error and is not treated as equivalent to an absent default.

The configuration file is operational routing state only and has no canonical or semantic authority
over the targeted Vault.

## Required Slice 2 Capabilities

The Builder must implement, without semantic expansion:

1. Reusable Capture service in `kv_tools`; core semantics must not live only in CLI parsing.
2. `kv capture --text <content>`.
3. Capture through redirected/piped standard input when `--text` is absent.
4. Optional `--title`, `--scope <kv-ID>`, and `--vault <path>`.
5. Deterministic Vault target resolution:
   `--vault` -> `KV_VAULT` -> configured default -> fail.
6. TOML machine-local configuration with:
   - `kv config set-default-vault <path>`
   - `kv config show`
   - `kv config clear-default-vault`
7. Deterministic permanent UUIDv7 identity generation.
8. Deterministic extractive-title generation with mechanical fallback.
9. Deterministic human-recognizable filename derivation with collision-safe ID-derived suffixing.
10. Default root scope discovery and explicit ID-only narrower-scope resolution.
11. Operator provenance generation only for the supported operator-originated Capture path.
12. Prospective validation against the resulting Vault state before canonical publication.
13. Baseline-versus-prospective finding comparison sufficient to preserve Decision 13.
14. Serialization of cooperating writes inside one local Vault working tree.
15. Atomic/crash-safe canonical file publication.
16. Crash-safe machine-config updates.
17. Concise success, warning, refusal, execution-failure, and indeterminate-result reporting.
18. Deterministic behavior on Windows and supported filesystem/platform paths without Linux-only assumptions.
19. Preservation of existing `kv init` and `kv validate` behavior and Slice 1 conformance.

## Explicitly Out of Scope

Do not implement or silently introduce:

- Capture classification;
- reclassification command;
- distillation;
- promotion;
- acceptance/rejection workflows;
- automatic evidence evaluation;
- automatic relationship creation;
- project inference or project routing;
- automatic archival/deletion/processed-state tracking;
- Source ingestion;
- URL fetching/dereferencing;
- file import;
- PDF/document parsing;
- attachments;
- clipboard-specific semantics;
- voice transcription;
- phone/mobile application;
- agent-authored or mixed-provenance intake;
- provenance override flags;
- actor identity registry;
- permission/delegation DSL;
- general object writer/editor;
- automatic repair;
- Git commit/pull/push/merge;
- GitHub synchronization;
- distributed locks across machines/clones;
- database;
- daemon/background service;
- queue;
- persistent index;
- semantic search;
- embeddings;
- graph database;
- graph rendering;
- desktop/web UI;
- named multi-Vault registry;
- config-version/migration system unless implementation demonstrates an unavoidable need and stops for review;
- any `kv-v0` schema change.

If any excluded capability appears necessary to satisfy this contract, stop and return the dependency
for design review rather than expanding scope.

## Documentation Synchronization Gate

Before any Slice 2 feature implementation begins, the repository documentation surfaces must be
brought current from the operator-maintained Google Drive project documentation.

A bounded documentation-only Codex task must:

1. inspect the current Google Drive project documents under the operator's `01_PROJECTS/the-vault/kv-docs`
   documentation area;
2. identify the accepted/current documents that belong in the public repository;
3. add or update the corresponding repository copies as Markdown files;
4. preserve historical documents as historical records rather than rewriting them to match newer state;
5. ensure the repository-native rehydration record reflects the accepted Slice 2 contract state;
6. make no Slice 2 feature-code changes during this documentation synchronization task;
7. report exactly which documents were added, updated, intentionally left historical, or excluded.

The purpose of this gate is to ensure Google Drive working documentation and repository documentation
are synchronized before new feature work changes the codebase.

Completion of the documentation synchronization gate does **not** authorize Slice 2 implementation.
Feature implementation still requires a separate explicit operator authorization after the
documentation-only result has been reviewed.

## Builder Authority Boundary

The Builder may implement this accepted contract only after explicit operator authorization.

The Builder is not authorized to:

- reinterpret `kv-v0`;
- modify canonical schema semantics;
- reopen or rewrite Slice 1 history;
- modify the real private canonical Vault as implementation test data;
- copy private Vault content into public tests or fixtures;
- add adjacent features because they appear useful;
- resolve an ambiguity by inventing policy.

All fixtures for development and automated testing must remain synthetic and public-safe.

If private/live behavior must later be reproduced for a defect, create the smallest synthetic public
reproducer without copying private canonical objects.

## Required Test and Verification Matrix

At minimum, the public test suite must cover the following families.

### A. CLI content acquisition

- successful `--text`;
- successful multiline stdin;
- `--text` + stdin conflict;
- neither input supplied;
- empty string;
- whitespace-only input;
- multiline body preserved;
- Unicode/non-ASCII content preserved;
- no silent truncation.

### B. Title behavior

- valid explicit title;
- empty explicit title refused;
- multiline explicit title refused;
- extractive title generated deterministically;
- generated title introduces no substantive words absent from input;
- mechanical fallback when extraction is unsafe/unavailable;
- duplicate titles do not collide in identity or path.

### C. Generated canonical object

Verify exact required core metadata semantics:

- `schema: kv-v0`;
- UUIDv7 `kv-` ID;
- `kind: capture`;
- `state: active`;
- correct `created`;
- correct root/default scope;
- operator provenance;
- no unsupported Capture metadata;
- body begins directly after frontmatter with no generated heading.

### D. Scope

- default root discovery;
- explicit valid scope ID;
- missing scope ID;
- wrong-kind scope target;
- ambiguous identity target;
- no title/fuzzy lookup;
- no silent fallback to root after explicit-scope failure.

### E. Vault resolution

- explicit absolute `--vault`;
- explicit relative `--vault`;
- absolute `KV_VAULT`;
- configured default;
- precedence ordering;
- invalid higher-priority target blocks lower fallback;
- relative `KV_VAULT` refused;
- no target available;
- no current-directory or filesystem discovery.

### F. TOML configuration

- set default;
- show default;
- clear default;
- path normalized to absolute;
- configured target verified;
- malformed TOML;
- unsupported key;
- unsupported table;
- wrong value type;
- relative stored path;
- stale/missing target;
- unreadable config where testable;
- failed config write does not leave partial/corrupt replacement;
- config operations do not mutate canonical Vault files.

### G. Filename / publication

- human-recognizable deterministic slug;
- ID-derived collision resistance;
- existing path never overwritten;
- path collision safely extended or refused according to implementation;
- final canonical file in `05_inbox/`;
- no partially written `.md` visible after simulated failure;
- no generated body heading;
- canonical relative path returned on success.

### H. Existing Vault state / bounded stopping

- healthy Vault succeeds;
- unrelated pre-existing conformance error may coexist with successful Capture;
- successful acknowledgement reports remaining pre-existing errors;
- duplicate-ID baseline blocks;
- ambiguous/missing active schema blocks;
- missing/ambiguous root blocks;
- validator execution failure blocks;
- prospective candidate introducing new ERROR is not published;
- Capture does not repair or modify unrelated broken objects.

### I. Concurrency

- cooperating writer ownership acquired before state-dependent inspection;
- two Capture writers do not interleave canonical mutation;
- second writer waits or cleanly refuses according to chosen implementation;
- lock/ownership cleanup after normal completion;
- crash/stale behavior does not permanently strand the Vault;
- lock state is noncanonical and ignored by `kv-v0` object discovery.

### J. Failure and acknowledgement

- exit 0 only after confirmed publication;
- exit 1 clean refusal with known no-write;
- exit 2 pre-publication execution failure with known no-write;
- simulated post-publication-boundary uncertainty produces an indeterminate message when reportable;
- failure messages do not falsely claim no write when final state is unknown;
- blind retry is not recommended for indeterminate state;
- validator rule IDs remain visible where applicable;
- warnings remain non-failing and are surfaced;
- captured body is not echoed by default.

### K. Regression

- all existing Slice 1 tests continue to pass;
- `kv init` behavior unchanged;
- `kv validate` remains deterministic/read-only;
- no private knowledge appears in public fixtures or tests.

## Manual Acceptance Exercise

Before operator acceptance, perform a hands-on test against a fresh synthetic Vault created from the
public tool, not against the real private Vault first.

Minimum manual flow:

```text
1. Create synthetic temporary Vault.
2. Configure it as default using kv config.
3. kv capture --text "..."
4. Inspect generated Markdown manually.
5. kv validate <vault> -> expected valid result.
6. Capture multiline stdin.
7. Capture with explicit --title.
8. Capture with explicit valid --scope.
9. Exercise --vault and KV_VAULT precedence.
10. Exercise at least one clean refusal.
11. Confirm Git-independent behavior.
12. Run full public test suite.
```

Only after the synthetic acceptance path passes may the operator separately authorize a limited
real-private-Vault Capture smoke test.

Implementation success does **not** itself authorize writing real operator knowledge into the private
Vault.

## Slice 2 Acceptance Gate

Slice 2 may be accepted only when all of the following are true:

- implementation matches Decisions 1–18;
- canonical `kv-v0` semantics are unchanged;
- required CLI and config surfaces behave as contracted;
- full public test suite passes;
- required Slice 2 tests pass;
- generated Capture Markdown is manually inspected for readability and fidelity;
- body preservation is demonstrated;
- target routing and TOML failure behavior are demonstrated;
- bounded pre-existing-error behavior is demonstrated;
- cooperating concurrency behavior is demonstrated;
- crash-safe publication behavior is demonstrated to the practical extent supported by deterministic tests;
- no existing canonical object is overwritten during tests;
- no private operator knowledge enters the public repository, fixtures, test corpus, or reports;
- existing Slice 1 capabilities remain valid;
- independent Auditor review returns PASS or all blocking findings are remediated and re-audited;
- the operator explicitly accepts Slice 2.

Builder completion or passing tests alone do not constitute operator acceptance.

## Definition of Done

Slice 2 is done when The Backlot contains a tested, reusable low-friction Capture implementation
that can safely preserve operator-originated text into a valid target Vault through:

```text
kv capture --text "..."
```

or standard input, using deterministic target routing, generated `kv-v0` metadata, default root or
explicit ID scope, extractive/mechanical title behavior, TOML machine configuration, bounded
pre-existing-state handling, serialized cooperating writes, prospective validation, crash-safe
publication, and truthful acknowledgement/failure reporting.

The completed implementation must preserve the following invariant:

> If Capture reports confirmed success, one complete canonical Capture exists at the reported path.
> If Capture cleanly refuses before publication, no new canonical Capture exists.
> If publication outcome cannot be established after an execution interruption, the tool does not
> manufacture certainty.

Slice 2 ends at safe preservation.

Anything that tries to understand, classify, enrich, route, promote, accept, process, ingest, or act
on the captured knowledge belongs to a later explicitly designed workflow.

## Historical / Process Reporting

Builder, Auditor, and Scout reports remain external historical process evidence:

```text
D:\Project-Playground\Vault-reports\Builder-reports
D:\Project-Playground\Vault-reports\Auditor-reports
D:\Project-Playground\Vault-reports\Scout-reports
```

The eventual Builder prompt for this slice should require a final Markdown report in the Builder
report directory. The independent audit prompt should require its final Markdown report in the
Auditor report directory.

These reports do not override canonical design, repository evidence, or operator authority.

## Authorization Boundary

This contract is **ACCEPTED** and establishes the bounded Slice 2 scope.

Acceptance of the contract does **not** authorize feature implementation. Before implementation, the
Documentation Synchronization Gate must be completed through a bounded documentation-only Codex task
that brings the accepted/current Google Drive project documents into the repository as Markdown while
preserving historical records.

Sequence:

```text
Slice 2 contract accepted
-> documentation-sync prompt drafted
-> operator authorizes documentation-only Codex task
-> repository documentation synchronized from Google Drive
-> operator reviews documentation-sync result
-> Slice 2 Builder prompt drafted
-> operator separately authorizes feature implementation
-> implementation
-> independent audit
-> remediation if required
-> operator acceptance
-> closeout
```
