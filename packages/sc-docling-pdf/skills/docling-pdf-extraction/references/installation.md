# Installation — Docling CLI

Verified against the Docling CLI and docs current on 2026-04-19.

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

---

## Verify Installation

```bash
docling --version
docling https://arxiv.org/pdf/2408.09869 --output /tmp/docling-test
ls /tmp/docling-test/
sed -n '1,30p' /tmp/docling-test/*.md
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
python3 -m pip install -U docling
python3 -m pip install -U torch torchvision
```

**Homebrew Python / externally managed environment error:**
```bash
python3 -m venv ~/.venvs/docling
source ~/.venvs/docling/bin/activate
python -m pip install -U docling
```
