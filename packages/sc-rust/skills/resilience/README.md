# Resilience Reference Notes

## I/O and System Calls Are Mockable (M-MOCKABLE-SYSCALLS) { #M-MOCKABLE-SYSCALLS }

Code that performs I/O or system interaction should be structured so tests can replace the side-effecting boundary with a deterministic stand-in. The goal is reliable testing and isolation of system effects, not abstraction for its own sake.
