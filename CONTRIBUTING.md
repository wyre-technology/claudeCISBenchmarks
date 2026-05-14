# Contributing

Thank you for your interest in contributing to the CIS Benchmarks Claude plugin.

## Getting Started

1. Fork the repository and clone your fork
2. Run setup: `bash scripts/setup.sh` (requires Python 3.12+ and `uv`)
3. Add your CIS benchmark PDFs to the repo root, then re-run the indexer:
   ```bash
   PDF_DIR=. DB_DIR=mcp-server/data .venv/bin/python mcp-server/indexer.py
   ```

## What We Accept

- **New benchmark PDFs** — open a PR adding the PDF and updating `CHANGELOG.md`
- **Indexer improvements** — better control-section extraction, OCR support for image-based PDFs
- **New MCP tools** — e.g. `compare_benchmarks`, `get_remediation_steps`
- **New skills/commands** — new Claude Code entry points
- **Bug fixes** — incorrect chunking, wrong metadata, transport issues

## What We Don't Accept

- Changes to the indexed `mcp-server/data/` directory (regenerated locally from PDFs)
- Vendored CIS PDFs in the repo (they are excluded via `.gitignore` — users supply their own)

## Development Workflow

```bash
# Run the server in HTTP mode for interactive testing
DB_DIR=mcp-server/data .venv/bin/python mcp-server/server.py --transport streamable-http

# Re-index after changing the indexer
PDF_DIR=. DB_DIR=mcp-server/data .venv/bin/python mcp-server/indexer.py

# Test a search query directly
python - <<'EOF'
import os, chromadb
os.environ["DB_DIR"] = "mcp-server/data"
db = chromadb.PersistentClient(path="mcp-server/data")
col = db.get_collection("cis_controls")
r = col.query(query_texts=["your query here"], n_results=3, include=["metadatas","distances"])
for m, d in zip(r["metadatas"][0], r["distances"][0]):
    print(f"[{round((1-d)*100,1)}%] {m['display_name']} — {m['control_id']}: {m['control_title']}")
EOF
```

## Pull Request Checklist

- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] No PDFs or `.venv/` or `mcp-server/data/` committed
- [ ] Server starts in both `stdio` and `streamable-http` modes without error
- [ ] Brief description of what changed and why

## Code Style

- Python: follow existing style (no type-annotation imports, f-strings, simple functions)
- Markdown: keep skill/command/agent files concise and action-oriented

## Reporting Issues

Open a [GitHub Issue](https://github.com/wyre-technology/claudeCISBenchmarks/issues) with:
- Which benchmark and control you were searching for
- The query you used
- What you expected vs. what you got
