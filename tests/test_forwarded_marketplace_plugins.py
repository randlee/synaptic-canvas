"""Guard against forwarded (externally hosted) plugins disappearing from marketplace.json.

Forwarded plugins live in other repos and have no packages/<name> directory here,
so registry tooling has silently dropped them before. Every forwarded plugin must
be listed below; add new ones when they are added to marketplace.json.
"""

import json
from pathlib import Path

import pytest

MARKETPLACE_PATH = Path(__file__).parent.parent / ".claude-plugin" / "marketplace.json"

FORWARDED_PLUGINS = [
    "process-porn",
    "sc-lint-adoption",
    "sc-lint-version-adoption",
    "sc-observability",
]


def load_plugins() -> dict[str, dict]:
    marketplace = json.loads(MARKETPLACE_PATH.read_text())
    return {plugin["name"]: plugin for plugin in marketplace["plugins"]}


@pytest.mark.parametrize("name", FORWARDED_PLUGINS)
def test_forwarded_plugin_is_listed(name):
    plugins = load_plugins()
    assert name in plugins, f"{name} is missing from {MARKETPLACE_PATH.name}"
    assert isinstance(plugins[name]["source"], dict), f"{name} is no longer a forwarded source"
