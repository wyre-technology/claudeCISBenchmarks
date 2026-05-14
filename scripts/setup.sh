#!/usr/bin/env bash
# Set up the CIS Benchmarks plugin: create venv, install deps, index PDFs.
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PLUGIN_DIR/.venv"
MCP_DIR="$PLUGIN_DIR/mcp-server"

echo "==> Creating Python 3.12 virtualenv at $VENV"
# Use uv if available (faster, handles Python version management)
if command -v uv &>/dev/null; then
    uv venv --python 3.12 "$VENV"
    uv pip install --python "$VENV/bin/python" -r "$MCP_DIR/requirements.txt"
else
    python3.12 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet -r "$MCP_DIR/requirements.txt"
fi

echo "==> Indexing PDFs (this may take several minutes on first run)"
PDF_DIR="$PLUGIN_DIR" \
DB_DIR="$MCP_DIR/data" \
"$VENV/bin/python" "$MCP_DIR/indexer.py"

echo ""
echo "Setup complete."
echo "Add the plugin to Claude Code by registering $PLUGIN_DIR/.mcp.json"
echo "or symlinking the plugin directory into ~/.claude/plugins/"
