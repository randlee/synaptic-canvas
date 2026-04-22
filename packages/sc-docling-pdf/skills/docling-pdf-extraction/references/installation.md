# Installation — Docling CLI

Verified against the Docling CLI and docs current on 2026-04-19.

## Runtime Tiers

There are two practical runtime tiers for this skill:

- Core conversion: `text`, `scan`, and baseline `rich` commands without enrichment
- Advanced enrichment / VLM: `--pipeline vlm`, `--enrich-picture-description`, `--enrich-chart-extraction`, and enrichment-heavy workflows

Core conversion works with a plain `docling` install.
Advanced enrichment needs extra dependencies and a compatible `transformers` version.

## Check First

```bash
which docling && docling --version
```

If both succeed, skip to **Model Pre-Download** below.

> **Note for Claude Code agents:** The bash environment may not share PATH with
> interactive shells. If `which docling` fails but you believe docling is installed,
> try the full path checks below before concluding it needs to be installed.

---

## Find an Existing Installation

```bash
# Check all likely locations
for candidate in \
  "$(which docling 2>/dev/null)" \
  "$HOME/.local/bin/docling" \
  "$HOME/.venvs/docling/bin/docling" \
  "$(python3 -m site --user-base 2>/dev/null)/bin/docling" \
  "/opt/homebrew/bin/docling" \
  "/usr/local/bin/docling"; do
  [ -x "$candidate" ] && echo "Found: $candidate" && break
done

# Also check the Python package metadata
python3 -m pip show docling 2>/dev/null | grep -E "^(Name|Version|Location)"
```

If found but not on PATH, use the full path for all docling commands,
or add its directory to PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"   # adjust to actual location
```

---

## Install

Requires Python 3.10+.

### macOS

```bash
# Recommended: virtual environment
python3 -m venv ~/.venvs/docling
source ~/.venvs/docling/bin/activate
python -m pip install -U docling

# Add to ~/.zshrc for persistent access:
echo 'export PATH="$HOME/.venvs/docling/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

```bash
# Standard + OCR + VLM support
python -m pip install -U "docling[easyocr,vlm]"

# Known-good ceiling for Granite-based advanced enrichment:
python -m pip install -U "transformers<5.5" "peft>=0.18.1"
```

```bash
# Or with uv
uv tool install 'docling[easyocr,vlm]'
# uv tools are placed in ~/.local/bin — ensure that's on PATH
```

```bash
# Or system-wide via pip3 (e.g. Python.framework installs)
python3 -m pip install -U docling
# Binary lands in the Python framework bin, e.g.:
#   /Library/Frameworks/Python.framework/Versions/3.11/bin/docling
# Add to PATH if not already present:
echo 'export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

```bash
# Intel Macs: use the compatibility extra from the official docs
python3 -m pip install -U "docling[mac_intel]"
```

Notes:
- Apple Silicon: `--device mps` is usually the best choice.
- Intel Mac: MPS is unavailable, so use `--device cpu`.
- The `docling` package also installs the companion `docling-tools` CLI.

### Linux

```bash
# Recommended: virtual environment
python3 -m venv ~/.venvs/docling
source ~/.venvs/docling/bin/activate
python -m pip install -U docling

# Add to ~/.bashrc:
echo 'export PATH="$HOME/.venvs/docling/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

```bash
# Standard + OCR + VLM support
python -m pip install -U "docling[easyocr,vlm]"

# Known-good ceiling for Granite-based advanced enrichment:
python -m pip install -U "transformers<5.5" "peft>=0.18.1"
```

```bash
# Or with pipx (manages isolated envs automatically)
pipx install 'docling[easyocr,vlm]'
# pipx ensures ~/.local/bin is on PATH
```

### Windows

```powershell
# PowerShell — recommended: virtual environment
python -m venv $env:USERPROFILE\.venvs\docling
& "$env:USERPROFILE\.venvs\docling\Scripts\Activate.ps1"
python -m pip install -U docling
```

```powershell
# Standard + OCR + VLM support
python -m pip install -U "docling[easyocr,vlm]"

# Known-good ceiling for Granite-based advanced enrichment:
python -m pip install -U "transformers<5.5" "peft>=0.18.1"
```

```powershell
# Or with uv
uv tool install "docling[easyocr,vlm]"
# Binary at %USERPROFILE%\.local\bin\docling.exe
# Add to PATH via System Properties > Environment Variables
```

> **Windows note:** Use `--device cpu` on Windows — MPS (Apple GPU) is Mac-only.
> CUDA is available if you have an NVIDIA GPU: `--device cuda`.

---

## Optional Extras

```bash
python3 -m pip install -U "docling[easyocr]"     # OCR for scanned docs
python3 -m pip install -U "docling[rapidocr]"    # lightweight OCR alternative
python3 -m pip install -U "docling[vlm]"         # VLM pipeline support
```

## Compatibility Note: `transformers`

Docling `2.90.0` declares this VLM dependency range:

```text
transformers >= 4.42.0, < 6.0.0, != 5.0.*, != 5.1.*, != 5.2.*, != 5.3.*
```

However, local runtime validation for this skill found that Granite-based chart extraction is not compatible with `transformers 5.5.x`.

Empirically checked against wheel contents:
- `4.55.4`, `4.56.2`, `4.57.6`, and `5.4.0` include `HybridMambaAttentionDynamicCache`
- `5.5.0` through `5.5.4` do not

For this skill, if you intend to use advanced Granite-based enrichment, pin:

```bash
python3 -m pip install -U "transformers<5.5" "peft>=0.18.1"
```

---

## Model Pre-Download

Docling downloads AI models (~1–2 GB) on first use. Pre-download for offline / faster startup:

```bash
docling-tools models download
docling-tools models download --output-dir ~/.docling/models

# Reference pre-downloaded models:
docling --artifacts-path ~/.docling/models INPUT.pdf
```

### VLM Models (large, optional — only for `--pipeline vlm`)

```bash
# Downloader model names differ from CLI preset names.
docling-tools models download granitedocling
docling-tools models download smoldocling
```

### First-Use Download Note

The first run of some advanced features may spend minutes downloading model weights before any output files appear:
- `--pipeline vlm --vlm-model smoldocling`
- `--enrich-picture-description`
- `--enrich-chart-extraction`

If the process is alive and `~/.cache/huggingface/hub` is growing, it is usually still making progress.
For repeated use, pre-download models first.

---

## Verify Installation

```bash
docling --version
docling https://arxiv.org/pdf/2408.09869 --output /tmp/docling-test
ls /tmp/docling-test/
sed -n '1,30p' /tmp/docling-test/*.md
```

## Validate Advanced Runtime

Run this once after install, and again after any package upgrade, before using VLM or enrichment-heavy commands:

```bash
python3 - <<'PY'
import importlib
import importlib.metadata as md
import sys

def version(pkg):
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return None

issues = []

docling_v = version("docling")
transformers_v = version("transformers")
peft_v = version("peft")

print("docling:", docling_v)
print("transformers:", transformers_v)
print("peft:", peft_v)

if docling_v is None:
    issues.append("docling is not installed")

if transformers_v is None:
    issues.append("transformers is not installed")

if peft_v is None:
    issues.append("peft is missing; install docling[vlm] or pip install peft")

try:
    gm = importlib.import_module("transformers.models.granitemoehybrid.modeling_granitemoehybrid")
    has_symbol = hasattr(gm, "HybridMambaAttentionDynamicCache")
    print("HybridMambaAttentionDynamicCache:", has_symbol)
    if not has_symbol:
        issues.append("transformers is missing HybridMambaAttentionDynamicCache; pin transformers<5.5")
except Exception as exc:
    issues.append(f"granitemoehybrid import failed: {exc}")

if issues:
    print("\\nFAILED")
    for issue in issues:
        print("-", issue)
    sys.exit(1)

print("\\nOK: advanced runtime looks compatible")
PY
```

---

## Accelerator Flag by Platform

| Platform | Flag | Notes |
|----------|------|-------|
| Mac (Apple Silicon) | `--device mps` | Recommended; significant speedup |
| Mac (Intel) | `--device cpu` | MPS not available |
| Linux + NVIDIA GPU | `--device cuda` | Requires CUDA toolkit |
| Linux / Windows CPU | `--device cpu` | Fallback, slower |
| Auto-detect | `--device auto` | Default; picks best available |

---

## Troubleshooting

**`docling: command not found`** — binary not on PATH:
```bash
python3 -m site --user-base   # prints e.g. /Users/name/Library/Python/3.12
# Add /Users/name/Library/Python/3.12/bin to PATH
```

**MPS not available on Mac:**
```bash
python3 -c "import torch; print(torch.backends.mps.is_available())"
# False → upgrade: pip install torch --upgrade
```

**Docling warns `MPS is not available in the system. Fall back to 'CPU'` even though Torch reports MPS available:**

Docling's accelerator check can still choose CPU in some environments.
Treat this as a performance issue, not necessarily a broken installation.

Recommended responses:
- rerun with `--device cpu` if you need a predictable path
- use `--device cuda` on NVIDIA systems if available
- expect slower advanced runs on CPU, especially `smoldocling` and picture-description workflows
- prefer pre-downloading models before retrying

**`torch` version conflict:**
```bash
python3 -m pip install -U docling
python3 -m pip install -U torch torchvision
```

**`No module named 'peft'` while using VLM or picture/chart enrichment:**
```bash
python3 -m pip install -U "docling[vlm]" "peft>=0.18.1"
```

**`ImportError: cannot import name 'HybridMambaAttentionDynamicCache'`**

This indicates a `transformers` compatibility mismatch in the Granite-based runtime.
Pin to a known-good ceiling and rerun the validation block:

```bash
python3 -m pip install -U "transformers<5.5" "peft>=0.18.1"
```

If you cannot change the environment immediately, fall back to:
- `text`
- `scan`
- baseline `rich` without enrichment flags

These worked in local integration tests for this skill.

**Advanced run appears to hang with no output files yet**

Check whether first-use model downloads are still in progress:

```bash
find ~/.cache/huggingface/hub -type f -mmin -5 | head
du -sh ~/.cache/huggingface/hub/models--*
```

If those directories are growing, wait or pre-download models before retrying.

**Homebrew Python / externally managed environment error:**
```bash
python3 -m venv ~/.venvs/docling
source ~/.venvs/docling/bin/activate
python -m pip install -U docling
```
