#!/usr/bin/env python3
"""Shared helpers for the sc-launchpad runtime."""

from __future__ import annotations


def resolve_teammate_mode(
    parent_env: dict[str, str],
    atm_identity: str | None,
) -> tuple[bool, str | None, str | None]:
    """Enable teammate mode only when team and identity are both present."""
    parent_team = parent_env.get("ATM_TEAM", "").strip() or None
    identity = atm_identity.strip() if atm_identity and atm_identity.strip() else None
    if parent_team and identity:
        return True, parent_team, identity
    return False, None, None


def build_child_env(
    parent_env: dict[str, str],
    teammate_mode: bool,
    team: str | None,
    identity: str | None,
) -> dict[str, str]:
    """Copy the parent environment and normalize only ATM variables."""
    env = parent_env.copy()
    if teammate_mode:
        env["ATM_TEAM"] = team or ""
        env["ATM_IDENTITY"] = identity or ""
        return env
    env.pop("ATM_TEAM", None)
    env.pop("ATM_IDENTITY", None)
    return env

