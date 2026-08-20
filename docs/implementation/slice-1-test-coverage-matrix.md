# Slice 1 required test coverage matrix

This is an implementation coverage map for the original Builder prompt's section 7. It is non-normative; the canonical specification and active Schema Meta remain normative.

| Required family | Test coverage |
| --- | --- |
| Initialization | `test_init_and_validate_absent_destination`, `test_init_empty_and_nonempty_refusal`, `test_staged_execution_failure_does_not_publish` (forces a validator execution diagnostic and proves the initializer refuses publication without leaving a destination or staging directory) |
| Parser/schema | `test_parser_and_schema_failures` |
| Identity/references | `test_identity_and_reference_cases` |
| Scope/integrity | `test_scope_and_graph_integrity_cases` |
| Kind/epistemic | `test_each_kind_and_resource_evidence_rules` |
| Reporting/read-only/exit | `test_invalid_duplicate_is_read_only`, `test_cli_statuses_and_exit_codes`, `test_schema_drift_and_directory_warning` |
| Symlinks | `test_symlink_detection_portably` (skips only if Windows denies symlink creation) |

The metadata allowlist and evidence/relationship shape checks were added after these required negative tests exposed missing enforcement. See `slice-1-implementation-fixes.md`.
