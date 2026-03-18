#!/usr/bin/env bash
# install.sh — AIVC installer
#
# Usage:
#   bash install.sh                  # install from the current directory
#   curl -fsSL <raw_url> | bash      # install from GitHub (repo cloned to ~/.aivc)
#
# What it does:
#   1. Checks that 'uv' is available.
#   2. Resolves the AIVC source directory (current dir or ~/.aivc/).
#   3. Creates an isolated venv via 'uv venv'.
#   4. Installs the package with semantic dependencies via 'uv pip install'.
#   5. Registers AIVC in ~/.gemini/antigravity/mcp_config.json using Python's
#      json module (no jq, no sed — crash-safe).
#
# NO FALLBACK: any error aborts the entire script (set -euo pipefail).

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Colour

info()    { echo -e "${BLUE}[aivc]${NC} $*"; }
success() { echo -e "${GREEN}[aivc]${NC} $*"; }
die()     { echo -e "${RED}[aivc] ERROR:${NC} $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------------------------

command -v uv >/dev/null 2>&1 || die "'uv' is not installed. Install it with: curl -fsSL https://astral.sh/uv/install.sh | sh"
command -v python3 >/dev/null 2>&1 || die "python3 is required but not found."

# ---------------------------------------------------------------------------
# 2. Resolve source directory
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-install.sh}")" 2>/dev/null && pwd || true)"
AIVC_HOME="${HOME}/.aivc"

# If the script is being piped (BASH_SOURCE is empty) or run outside the repo,
# we clone/update the repo into ~/.aivc/repo.
if [[ -f "${SCRIPT_DIR}/pyproject.toml" ]] && grep -q 'name = "aivc"' "${SCRIPT_DIR}/pyproject.toml" 2>/dev/null; then
    SOURCE_DIR="${SCRIPT_DIR}"
    info "Using local source directory: ${SOURCE_DIR}"
else
    REPO_DIR="${AIVC_HOME}/repo"
    info "Source directory not found locally — cloning into ${REPO_DIR} ..."
    mkdir -p "${AIVC_HOME}"
    if [[ -d "${REPO_DIR}/.git" ]]; then
        git -C "${REPO_DIR}" pull --ff-only
    else
        REPO_URL="${AIVC_REPO_URL:-https://github.com/hjamet/aivc.git}"
        git clone "${REPO_URL}" "${REPO_DIR}"
    fi
    SOURCE_DIR="${REPO_DIR}"
fi

# ---------------------------------------------------------------------------
# 3. Create isolated venv
# ---------------------------------------------------------------------------

VENV_DIR="${AIVC_HOME}/venv"
info "Creating virtual environment at ${VENV_DIR} ..."
uv venv "${VENV_DIR}" --python python3

# ---------------------------------------------------------------------------
# 4. Install the package with semantic dependencies
# ---------------------------------------------------------------------------

info "Installing aivc[semantic] into the venv (this may take a moment for PyTorch/model downloads) ..."
uv pip install --python "${VENV_DIR}/bin/python" -e "${SOURCE_DIR}[semantic]"

# ---------------------------------------------------------------------------
# 5. Inject AIVC into ~/.gemini/antigravity/mcp_config.json
# ---------------------------------------------------------------------------

MCP_CONFIG="${HOME}/.gemini/antigravity/mcp_config.json"
info "Configuring MCP server entry in ${MCP_CONFIG} ..."

# Use Python's json module to safely read, update, and write the config.
# If mcp_config.json does not exist, it is created from scratch.
"${VENV_DIR}/bin/python" - <<PYEOF
import json
import pathlib
import sys

config_path = pathlib.Path("${MCP_CONFIG}")
config_path.parent.mkdir(parents=True, exist_ok=True)

if config_path.exists():
    raw = config_path.read_text(encoding="utf-8")
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"[aivc] ERROR: {config_path} contains invalid JSON: {exc}")
else:
    config = {}

if "mcpServers" not in config:
    config["mcpServers"] = {}

config["mcpServers"]["aivc"] = {
    "command": "${VENV_DIR}/bin/python",
    "args": ["-m", "aivc.server"],
    "env": {
        "AIVC_STORAGE_ROOT": str(pathlib.Path.home() / ".aivc" / "storage")
    },
}

config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
print(f"[aivc] MCP entry written to {config_path}")
PYEOF

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

success "AIVC installed successfully!"
echo ""
echo "  Storage root : ${AIVC_HOME}/storage"
echo "  Venv         : ${VENV_DIR}"
echo "  MCP config   : ${MCP_CONFIG}"
echo ""
echo "Restart Gemini Antigravity to pick up the new MCP server."
