# UX Runtime Reference Notes

## Runtime-Aware Libraries Are Runtime-Abstracted (M-RUNTIME-ABSTRACTED) { #M-RUNTIME-ABSTRACTED }

If a library must support runtime-specific async or I/O behavior, keep that boundary explicit and controlled instead of scattering runtime conditionals throughout the API surface.
