#!/usr/bin/env python3
"""Generate/check Codex catalog parity with the existing plugin marketplace.

Preserve local and forwarded sources; never filter by skill count or host guesses.
Run after marketplace/metadata changes; --check is read-only for CI.
"""

import argparse
import json
from pathlib import Path

import yaml


def expected_files(root: Path) -> dict[Path, dict | str]:
    plugins = []
    files = {}
    marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    seen = set()
    inventory = ["# Codex plugin inventory", "",
                 "Generated from the existing marketplace; no entries are excluded.", "",
                 "Counts describe local source files, not a claim that every workflow was exercised.",
                 "Local skill packages use root portable manifests so Codex discovers their skills.",
                 "Command-only and forwarded plugins retain compatibility loading.", "",
                 "| Plugin | Source | Skills | Commands | Agents |",
                 "|---|---|---:|---:|---:|"]
    for entry in marketplace["plugins"]:
        name = entry["name"]
        if name in seen:
            raise ValueError(f"Duplicate marketplace plugin: {name}")
        seen.add(name)
        source = entry["source"]
        if isinstance(source, str):
            package = (root / source).resolve()
            if not package.is_relative_to(root.resolve()):
                raise ValueError(f"Plugin path escapes marketplace: {name}")
            if not any((package / manifest).is_file() for manifest in
                       ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json")):
                raise ValueError(f"Missing plugin manifest: {name}")
            source = {"source": "local", "path": "./" + package.relative_to(root.resolve()).as_posix()}
            counts = [len(list((package / folder).glob(pattern))) for folder, pattern in
                      (("skills", "*/SKILL.md"), ("commands", "**/*.md"), ("agents", "*.md"))]
            if counts[0]:
                manifest = yaml.safe_load((package / "manifest.yaml").read_text(encoding="utf-8"))
                if manifest["name"] != name:
                    raise ValueError(f"Plugin/manifest name mismatch: {name}")
                author = manifest["author"]
                files[package / "plugin.json"] = {
                    "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                    "name": name, "version": manifest["version"],
                    "description": manifest["description"].strip(),
                    "author": author if isinstance(author, dict) else {"name": str(author)},
                    "license": manifest["license"],
                }
            location = source["path"]
        elif isinstance(source, dict) and source.get("source") in ("git-subdir", "url", "github", "npm"):
            source = dict(source)
            if source["source"] == "github":
                repo = source.pop("repo")
                source.update(source="url", url=f"https://github.com/{repo}.git")
            if source.get("path") and not source["path"].startswith("./"):
                source["path"] = "./" + source["path"]
            counts = ["—"] * 3
            location = source.get("url", source.get("package", ""))
            location += (" / " + source["path"]) if source.get("path") else ""
        else:
            raise ValueError(f"Unsupported source for {name}: {source!r}; add a translation, do not omit it")
        inventory.append(f"| {name} | {location} | {' | '.join(map(str, counts))} |")
        plugins.append({
            "name": name,
            "source": source,
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": entry.get("category", "Productivity"),
        })
    files[root / ".agents/plugins/marketplace.json"] = {
        "name": "synaptic-canvas",
        "interface": {"displayName": "Synaptic Canvas"},
        "plugins": plugins,
    }
    files[root / "docs/CODEX-PLUGIN-INVENTORY.md"] = "\n".join(inventory) + "\n"
    return files


def sync(root: Path, *, check: bool) -> list[str]:
    changed = []
    for path, data in expected_files(root).items():
        expected = data if isinstance(data, str) else json.dumps(data, indent=2) + "\n"
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            changed.append(path.relative_to(root).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(expected, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = sync(Path(__file__).resolve().parents[1], check=args.check)
    for path in changed:
        print(f"{'OUT OF DATE' if args.check else 'Updated'}: {path}")
    return int(args.check and bool(changed))


if __name__ == "__main__":
    raise SystemExit(main())
