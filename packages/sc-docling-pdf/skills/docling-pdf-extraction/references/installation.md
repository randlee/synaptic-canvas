# Installation — Docling CLI

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

# Also check pip
pip show docling 2>/dev/null | grep -E "^(Name|Version|Location)"
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
pip install docling

# Add to ~/.zshrc for persistent access:
echo 'export PATH="$HOME/.venvs/docling/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

```bash
# Or with uv (fast)
uv tool install docling
# uv tools are placed in ~/.local/bin — ensure that's on PATH
```

```bash
# Or system-wide via pip3 (e.g. Python.framework installs)
pip3 install docling
# Binary lands in the Python framework bin, e.g.:
#   /Library/Frameworks/Python.framework/Versions/3.11/bin/docling
# Add to PATH if not already present:
echo 'export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Linux

```bash
# Recommended: virtual environment
python3 -m venv ~/.venvs/docling
source ~/.venvs/docling/bin/activate
pip install docling

# Add to ~/.bashrc:
echo 'export PATH="$HOME/.venvs/docling/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

```bash
# Or with pipx (manages isolated envs automatically)
pipx install docling
# pipx ensures ~/.local/bin is on PATH
```

### Windows

```powershell
# PowerShell — recommended: virtual environment
python -m venv $env:USERPROFILE\.venvs\docling
& "$env:USERPROFILE\.venvs\docling\Scripts\Activate.ps1"
pip install docling
```

```powershell
# Or with uv
uv tool install docling
# Binary at %USERPROFILE%\.local\bin\docling.exe
# Add to PATH via System Properties > Environment Variables
```

> **Windows note:** Use `--device cpu` on Windows — MPS (Apple GPU) is Mac-only.
> CUDA is available if you have an NVIDIA GPU: `--device cuda`.

---

## Optional Extras

```bash
pip install docling[easyocr]    # best OCR engine for scanned docs
pip install docling[rapidocr]   # lightweight OCR alternative
pip install "docling[all]"      # all extras
```

---

## Model Pre-Download

Docling downloads AI models (~1–2 GB) on first use. Pre-download for offline / faster startup:

```bash
docling tools models download
docling tools models download --output-dir ~/.docling/models

# Reference pre-downloaded models:
docling convert INPUT.pdf --artifacts-path ~/.docling/models
```

### VLM Models (large, optional — only for `--pipeline vlm`)

```bash
docling tools models download --vlm-model granite_docling  # ~4 GB, best quality
docling tools models download --vlm-model smol_docling     # ~1.5 GB, faster
```

---

## Verify Installation

```bash
docling --version
docling convert https://arxiv.org/pdf/2408.09869 --to markdown --output /tmp/docling-test
cat /tmp/docling-test/*.md | head -30
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

**`torch` version conflict:**
```bash
pip install docling --upgrade && pip install torch torchvision --upgrade
```

**Homebrew Python / externally managed environment error:**
```bash
pip install docling --break-system-packages
# Or use a venv (preferred)
```
