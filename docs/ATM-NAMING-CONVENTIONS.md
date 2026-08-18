# ATM phase and sprint naming conventions

Status: canonical Synaptic Canvas naming contract

This document is the single source of truth for phase, sprint, plan, branch,
worktree, and retained-evidence identifiers shared by Synaptic Canvas and
consuming repositories such as ATM Core.  Consumer repositories should link to
this document and should not copy these rules into their own plan documents.

## Canonical identifiers

### Phase

The comparison and persistence key for a phase is an uppercase ASCII token:

```text
<PHASE> := [A-Z][A-Z0-9]*
```

Examples: `AN`, `AL`, `AI`.

The filesystem form is lowercase and prefixed with `phase-`: `phase-an`,
`phase-al`, and `phase-ai`.  A phase token is never encoded as `Phase AN`,
`phase_AN`, or a mixed-case value in persisted metadata.

### Sprint

The canonical sprint identifier is the phase key, a dot, and a positive
decimal number:

```text
<SPRINT> := <PHASE>.<number>
```

For example, `AN.1` and `AN.8` are canonical.  The same canonical string is
used in Synaptic Canvas `sprint_id`, ATM plan frontmatter, `aich_sprint`, and
TTL/report fields such as `triage:foundIn`.

The following are historical input spellings, not persisted values:

| Historical input | Canonical value | Diagnostic |
| --- | --- | --- |
| `AN-S1` | `AN.1` | `TTL.QA_RUN_KEY_MISMATCH` |
| `AN1` | `AN.1` | `NAMING.LEGACY_IDENTIFIER` |
| `an.1` | `AN.1` | `NAMING.NON_CANONICAL` |
| `Phase AN / Sprint 1` | `AN.1` | `NAMING.UNKNOWN_SPRINT_FORMAT` until explicitly mapped |

Ingestion may compare phase and sprint keys case-insensitively after trimming
surrounding whitespace.  It must retain the raw value in a diagnostic and
persist only the canonical value.  A case-insensitive match is not permission
to silently accept a legacy separator or an ambiguous format.

## Plan and evidence paths

Phase directories use the lowercase filesystem phase form:

```text
docs/plans/phase-an/
```

Sprint plan filenames use the canonical sprint ID followed by a stable,
lowercase kebab slug:

```text
docs/plans/phase-an/sprint-AN.8-validation-evidence.md
```

The plan frontmatter carries the canonical `sprint: AN.8` value when a sprint
is represented outside the filename.  Its `branch` and `worktree` fields are
the actual implementation locations; consumers must not infer the sprint ID
from either field.

Retained QA, report, and TTL evidence carries the same canonical sprint value.
For example:

```turtle
triage:QA-RUN-001
    a triage:Finding ;
    triage:foundIn triage:AN.8 ;
    triage:aich_sprint "AN.8" .
```

`AN-S1`, `AN1`, and lowercase equivalents in a new record are validation
errors.  Existing records may remain temporarily only when listed in the
historical inventory and accompanied by a migration note.

## Branch and worktree names

The sprint ID and implementation branch are related metadata, not aliases.
The recommended branch form is:

```text
<kind>/p<phase-lower>-s<number>-<slug>
```

where `<kind>` is one of `feature`, `fix`, `docs`, `plan`, `test`, or
`integrate`.  For example:

```text
feature/pan-s8-validation-evidence
```

The branch may use a more descriptive suffix when a fix round or integration
line needs it.  The sprint plan must still retain `sprint: AN.8` and the
actual `branch` value.  A worktree mirrors its branch below the repository's
worktree root:

```text
../atm-core-worktrees/feature/pan-s8-validation-evidence
```

Absolute worktree paths are tolerated for historical records, but new
frontmatter should use the repository-relative form above.  A branch or
worktree mismatch is a diagnostic against the metadata, not a reason to rename
an already-published commit history.

## Validation and migration

Every ingestion boundary follows this sequence:

1. trim the incoming identifier;
2. compare case-insensitively against the canonical grammar;
3. map an explicitly supported legacy spelling to its canonical value;
4. persist the canonical value and retain the original in the diagnostic; and
5. reject ambiguous or unknown forms with an actionable diagnostic.

The minimum diagnostics are:

- `TTL.QA_RUN_KEY_MISMATCH` — a TTL/report run key does not equal the
  canonical sprint key (for example `AN-S1` versus `AN.1`);
- `NAMING.NON_CANONICAL` — a supported value differs only by case or
  filesystem casing;
- `NAMING.LEGACY_IDENTIFIER` — a recognized historical separator/compact form
  needs migration; and
- `NAMING.UNKNOWN_SPRINT_FORMAT` — the value cannot be mapped without human
  confirmation.

Diagnostics must identify the file, field, raw value, canonical candidate (when
known), and the migration action.  Validation must fail the new record or run;
it must not silently treat a missing canonical key as a missing QA run.

The migration inventory is maintained with the consuming repository's
validation evidence.  Each historical exception records its raw spelling,
canonical replacement, owning file, migration status, and the commit that
performed the migration.  Once all references in an inventory entry are
canonical, the entry may be retained as historical documentation but must no
longer be accepted for new ingestion.

## Consumer links

- [ATM Core naming/validation integration](https://github.com/randlee/atm-core/blob/develop/docs/canonical-naming-conventions.md)
- [Synaptic Canvas project conventions](https://github.com/randlee/synaptic-canvas/tree/develop/docs)

