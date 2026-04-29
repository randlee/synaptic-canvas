# Library Resilience Reference Notes

## Don't Glob Re-Export Items (M-NO-GLOB-REEXPORTS) { #M-NO-GLOB-REEXPORTS }

Prefer explicit re-exports over wildcard public surfaces so downstream callers can see what is intentionally stable and accidental exports do not leak through convenience globs.
