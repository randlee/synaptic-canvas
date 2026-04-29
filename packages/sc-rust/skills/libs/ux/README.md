# Library UX Reference Notes

## Errors are Canonical Structs (M-ERRORS-CANONICAL-STRUCTS) { #M-ERRORS-CANONICAL-STRUCTS }

Reusable library error contracts should prefer stable, named error types with explicit fields over ad hoc tuples, strings, or opaque wrappers.

## Complex Type Construction has Builders (M-INIT-BUILDER) { #M-INIT-BUILDER }

Types with many optional settings or construction invariants should prefer a builder over long constructors or loosely structured parameter sets.
