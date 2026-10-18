#!/usr/bin/env python3
"""ATM identity names for launched agents: per-family name pools and the generator.

Shared by sc-launch-term and sc-launchpad. Canonical copy:
``packages/shared/scripts/agent_identity.py``; packages receive byte-identical copies
via ``python3 scripts/sync-shared-scripts.py`` (declared under ``shared_scripts`` in
each manifest). Never edit a package copy.

A generated identity is ``<Name>-<4 hex>``, with the name drawn from the pool of the
model family (``opus``, ``sol``, ``gemini``, ...); unknown families use a neutral pool.

Standard library only; Python 3.9+.
"""

from __future__ import annotations

import secrets


# Per-tool identity name pools.
_IDENTITY_NAMES: dict[str, list[str]] = {
    "gemini": [
        "Gamma",
        "Galaxian",
        "Grimaldi",
        "Ganymede",
        "Grogu",
        "Grievous",
        "Greedo",
        "Glitch",
        "Gauss",
        "Glimmer",
    ],
    "haiku": [
        "Homer",
        "Helix",
        "Helios",
        "Horus",
        "Halo",
        "Hal",
        "Hex",
        "Hive",
        "Heretic",
        "Hydra",
    ],
    "sonnet": [
        "Sinatra",
        "Santana",
        "Slash",
        "Spock",
        "Skynet",
        "Striker",
        "Siren",
        "Sentinel",
        "Sting",
        "Synth",
    ],
    "opus": [
        "Orion",
        "Oracle",
        "Omega",
        "Orwell",
        "Obiwan",
        "Optimus",
        "Oblivion",
        "Onyx",
        "Odyssey",
        "Octane",
    ],
    "fable": [
        "Fable",
        "Folklore",
        "Fiction",
        "Fairytale",
        "Fantasy",
        "Fathom",
        "Fresco",
        "Fableton",
        "Figment",
        "Fablewood",
    ],
    # Codex model identities use the model alias initial and a sci-fi/cyberpunk
    # vocabulary. The `codex` alias is the Codex default model (`sol`), mapped below.
    "astra": [
        "Ash",
        "Atreides",
        "Avasarala",
        "Akira",
        "Automata",
        "Axiom",
        "Aegis",
        "Apex",
        "Arclight",
        "Avatar",
    ],
    "sol": [
        "Smith",
        "Switch",
        "Spoon",
        "Saito",
        "Sark",
        "Seraph",
        "Sombra",
        "Synth",
        "Specter",
        "Sentinel",
    ],
    "terra": [
        "Trinity",
        "Tank",
        "Turing",
        "Tyrell",
        "Tessier",
        "Talon",
        "Tracer",
        "Titan",
        "Terminal",
        "Turin",
    ],
    "luna": [
        "Lamb",
        "Link",
        "Lucy",
        "Lyra",
        "Lambda",
        "Lazarus",
        "Lumen",
        "Lotus",
        "Lucid",
        "Legion",
    ],
}

_IDENTITY_ALIASES = {"codex": "sol"}

_FALLBACK_NAMES: list[str] = [
    "Amber",
    "Bold",
    "Calm",
    "Deft",
    "Eager",
    "Fleet",
    "Gold",
    "Hale",
    "Iron",
    "Jade",
]


def generate_identity(tool: str | None = None) -> str:
    pool_key = _IDENTITY_ALIASES.get(tool or "", tool or "")
    pool = _IDENTITY_NAMES.get(pool_key, _FALLBACK_NAMES)
    name = secrets.choice(pool)
    suffix = secrets.token_hex(2)
    return f"{name}-{suffix}"


def resolve_identity(identity: str | None, tool: str | None = None) -> str | None:
    if not identity:
        identity = generate_identity(tool)
    return identity
