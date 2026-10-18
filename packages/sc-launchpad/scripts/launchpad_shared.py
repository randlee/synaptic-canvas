#!/usr/bin/env python3
"""Shared helpers for the sc-launchpad runtime."""

from __future__ import annotations

from agent_identity import generate_identity


def resolve_teammate_mode(
    parent_env: dict[str, str],
    atm_identity: str | None,
    identity_pool: str | None = None,
) -> tuple[bool, str | None, str | None]:
    """Teammate mode, team and identity for the child.

    Teammate mode needs the parent's ATM_TEAM. The identity is the explicit
    `atm_identity`; without one, a new identity is generated from the
    `identity_pool` family's names (same pools as sc-launch-term), so a team
    member always launches a distinct agent that can be addressed. With no
    `identity_pool` (e.g. isolation.tools='none') nothing is generated and the
    launch is not a teammate. Without a team nothing is generated either.
    """
    parent_team = parent_env.get("ATM_TEAM", "").strip() or None
    identity = atm_identity.strip() if atm_identity and atm_identity.strip() else None
    if not parent_team:
        return False, None, None
    if not identity and identity_pool is not None:
        identity = generate_identity(identity_pool)
    if identity:
        return True, parent_team, identity
    return False, None, None


def build_child_env(
    parent_env: dict[str, str],
    teammate_mode: bool,
    team: str | None,
    identity: str | None,
) -> dict[str, str]:
    """Copy the parent environment and normalize only ATM variables.

    Teammate mode sets the team and the registered identity, and BEADS_ACTOR to
    that identity so `bd` attributes the child's work to the child. Otherwise
    only ATM_IDENTITY and BEADS_ACTOR are dropped: the child stays on the
    parent's team (ATM_TEAM is kept) but must never take on the parent's
    identity.
    """
    env = parent_env.copy()
    if teammate_mode:
        env["ATM_TEAM"] = team or ""
        env["ATM_IDENTITY"] = identity or ""
        env["BEADS_ACTOR"] = identity or ""
        return env
    env.pop("ATM_IDENTITY", None)
    env.pop("BEADS_ACTOR", None)
    return env
