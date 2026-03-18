#!/usr/bin/env bash
# install_dev.sh — AIVC development installer
# Install local repo in an isolated local .venv, with ALL dependencies
# and registers it as the active MCP server.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[aivc-dev]${NC} $*"; }
success() { echo -e "${GREEN}[aivc-dev]${NC} $*"; }
die()     { echo -e "${RED}[aivc-dev] ERROR:${NC} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

command -v uv >/dev/null 2>&1 || die "'uv' is not installed."

VENV_DIR="${SCRIPT_DIR}/.venv"
info "Creating local virtual environment at ${VENV_DIR} ..."
uv venv "${VENV_DIR}" --python python3

info "Installing aivc[all] into the local venv ..."
uv pip install --python "${VENV_DIR}/bin/python" -e ".[all]"

MCP_CONFIG="${HOME}/.gemini/antigravity/mcp_config.json"
info "Configuring MCP server entry in ${MCP_CONFIG} ..."

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
        sys.exit(f"[aivc-dev] ERROR: {config_path} contains invalid JSON: {exc}")
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
print(f"[aivc-dev] MCP entry written to {config_path}")
PYEOF

success "AIVC Dev environment installed in ${VENV_DIR}!"
echo "Go ahead and restart Gemini's MCP servers to pick up the changes."
