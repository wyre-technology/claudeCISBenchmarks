#!/usr/bin/env bash
# Container entrypoint: download ChromaDB from DO Spaces if needed, then start the MCP server.
set -euo pipefail

DATA_DIR="${DB_DIR:-/app/mcp-server/data}"
PORT="${PORT:-8080}"

if [ ! -f "$DATA_DIR/chroma.sqlite3" ]; then
    echo "==> ChromaDB not found at $DATA_DIR — downloading from DO Spaces..."
    python /app/scripts/download-db-from-spaces.py
    echo "==> Download complete."
else
    echo "==> ChromaDB found at $DATA_DIR — skipping download."
fi

echo "==> Starting CIS Benchmarks MCP server on 0.0.0.0:${PORT}"
exec python /app/mcp-server/server.py \
    --transport streamable-http \
    --host 0.0.0.0 \
    --port "$PORT"
