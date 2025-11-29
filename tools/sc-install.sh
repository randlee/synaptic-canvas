#!/usr/bin/env bash
set -euo pipefail

# Synaptic Canvas installer
# Install Claude Code packages with automatic token substitution

VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<EOF
Synaptic Canvas Installer v$VERSION

Usage:
  sc-install.sh install <package> --dest <path/to/.claude> [options]
  sc-install.sh uninstall <package> --dest <path/to/.claude>
  sc-install.sh list
  sc-install.sh info <package>

Commands:
  install     Install a package to target .claude directory
  uninstall   Remove a package from target .claude directory
  list        List available packages
  info        Show package details

Options:
  --dest      Target .claude directory (required for install/uninstall)
  --force     Overwrite existing files
  --no-expand Keep {{VAR}} tokens unexpanded
  --help      Show this help

Examples:
  sc-install.sh install git-worktree --dest ~/myrepo/.claude
  sc-install.sh list
  sc-install.sh info git-worktree
EOF
}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*" >&2; }
error() { echo -e "${RED}✗${NC} $*" >&2; }

# Parse arguments
ACTION=""
PACKAGE=""
DEST=""
FORCE="false"
EXPAND="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    install|uninstall|list|info)
      ACTION="$1"; shift
      [[ $# -gt 0 && ! "$1" =~ ^-- ]] && { PACKAGE="$1"; shift; } || true
      ;;
    --dest) DEST="$2"; shift 2 ;;
    --force) FORCE="true"; shift ;;
    --no-expand) EXPAND="false"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) error "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

# Resolve auto variables - returns value for given auto type
resolve_auto_var() {
  local auto_type="$1" dest_dir="$2"
  case "$auto_type" in
    git-repo-basename)
      local repo_root
      repo_root="$(cd "$dest_dir/.." && git rev-parse --show-toplevel 2>/dev/null || true)"
      [[ -n "$repo_root" ]] && basename "$repo_root" || echo ""
      ;;
    *) echo "" ;;
  esac
}

# List available packages
cmd_list() {
  echo "Available packages:"
  echo ""
  for pkg_dir in "$REPO_ROOT"/packages/*/; do
    [[ -d "$pkg_dir" ]] || continue
    local name desc
    name="$(basename "$pkg_dir")"
    if [[ -f "$pkg_dir/manifest.yaml" ]]; then
      desc=$(grep -m1 "^description:" "$pkg_dir/manifest.yaml" | sed 's/^description:[[:space:]]*//' | sed 's/^>//' | head -c 60)
      printf "  %-20s %s\n" "$name" "$desc"
    else
      printf "  %-20s (no manifest)\n" "$name"
    fi
  done
}

# Show package info
cmd_info() {
  local pkg="$1"
  local pkg_dir="$REPO_ROOT/packages/$pkg"
  
  [[ -d "$pkg_dir" ]] || { error "Package not found: $pkg"; exit 1; }
  [[ -f "$pkg_dir/manifest.yaml" ]] || { error "No manifest.yaml in $pkg"; exit 1; }
  
  echo "Package: $pkg"
  echo "Path: $pkg_dir"
  echo ""
  cat "$pkg_dir/manifest.yaml"
}

# Install a package
cmd_install() {
  local pkg="$1" dest="$2"
  local pkg_dir="$REPO_ROOT/packages/$pkg"
  local manifest="$pkg_dir/manifest.yaml"
  
  [[ -d "$pkg_dir" ]] || { error "Package not found: $pkg"; exit 1; }
  [[ -f "$manifest" ]] || { error "No manifest.yaml in $pkg"; exit 1; }
  [[ -n "$dest" ]] || { error "--dest is required"; exit 1; }
  
  # Validate dest is a .claude directory
  [[ "$dest" == *.claude* ]] || { error "--dest must point to a .claude directory"; exit 1; }
  
  mkdir -p "$dest"
  local dest_abs
  dest_abs="$(cd "$dest" && pwd)"
  
  # Detect REPO_NAME (the main/only variable we support for now)
  local REPO_NAME=""
  if [[ "$EXPAND" == "true" ]]; then
    if grep -q "auto: git-repo-basename" "$manifest" 2>/dev/null; then
      REPO_NAME=$(resolve_auto_var "git-repo-basename" "$dest_abs")
    fi
  fi
  
  info "Installing $pkg to $dest_abs"
  [[ -n "$REPO_NAME" ]] && info "REPO_NAME=$REPO_NAME"
  
  # Install a single file with token expansion
  install_file() {
    local file="$1"
    local src="$pkg_dir/$file"
    local dst="$dest_abs/$file"
    
    [[ -f "$src" ]] || { warn "Source not found: $src"; return; }
    
    if [[ -e "$dst" && "$FORCE" != "true" ]]; then
      warn "Skip (exists): $dst"
      return
    fi
    
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    
    # Make scripts executable
    if [[ "$file" == scripts/* ]]; then
      chmod +x "$dst"
    fi
    
    # Token expansion
    if [[ "$EXPAND" == "true" && -n "$REPO_NAME" ]]; then
      # macOS sed requires '' after -i, Linux doesn't
      if sed -i '' "s/{{REPO_NAME}}/$REPO_NAME/g" "$dst" 2>/dev/null; then
        : # macOS succeeded
      else
        sed -i "s/{{REPO_NAME}}/$REPO_NAME/g" "$dst"
      fi
    fi
    
    info "Installed: $file"
  }
  
  # Parse artifacts from manifest and install each file
  local current_section=""
  while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]+(commands|skills|agents|scripts):$ ]]; then
      current_section="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[[:space:]]+-[[:space:]]+(.+)$ && -n "$current_section" ]]; then
      install_file "${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[a-z] && ! "$line" =~ ^artifacts ]]; then
      current_section=""
    fi
  done < "$manifest"
  
  info "Done installing $pkg"
}

# Uninstall a package
cmd_uninstall() {
  local pkg="$1" dest="$2"
  local pkg_dir="$REPO_ROOT/packages/$pkg"
  local manifest="$pkg_dir/manifest.yaml"
  
  [[ -d "$pkg_dir" ]] || { error "Package not found: $pkg"; exit 1; }
  [[ -f "$manifest" ]] || { error "No manifest.yaml in $pkg"; exit 1; }
  [[ -n "$dest" ]] || { error "--dest is required"; exit 1; }
  
  local dest_abs
  dest_abs="$(cd "$dest" && pwd)"
  
  info "Uninstalling $pkg from $dest_abs"
  
  # Parse artifacts and remove
  local current_section=""
  while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]+(commands|skills|agents|scripts):$ ]]; then
      current_section="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[[:space:]]+-[[:space:]]+(.+)$ && -n "$current_section" ]]; then
      local file="${BASH_REMATCH[1]}"
      local dst="$dest_abs/$file"
      if [[ -e "$dst" ]]; then
        rm -f "$dst"
        info "Removed: $file"
      fi
    elif [[ "$line" =~ ^[a-z] && ! "$line" =~ ^artifacts ]]; then
      current_section=""
    fi
  done < "$manifest"
  
  info "Done uninstalling $pkg"
}

# Main dispatch
case "$ACTION" in
  list) cmd_list ;;
  info) [[ -n "$PACKAGE" ]] || { error "Package name required"; exit 1; }; cmd_info "$PACKAGE" ;;
  install) [[ -n "$PACKAGE" ]] || { error "Package name required"; exit 1; }; cmd_install "$PACKAGE" "$DEST" ;;
  uninstall) [[ -n "$PACKAGE" ]] || { error "Package name required"; exit 1; }; cmd_uninstall "$PACKAGE" "$DEST" ;;
  *) usage; exit 1 ;;
esac
