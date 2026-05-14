# CIS Benchmarks — Claude Code Plugin

A Claude Code plugin that brings 27 CIS security benchmarks into your AI workflow via semantic search. Ask Claude about hardening controls, generate audit checklists, and get remediation guidance — all grounded in the actual CIS benchmark text.

## What's Inside

| Component | Description |
|---|---|
| **MCP Server** | Python RAG server (PyMuPDF + ChromaDB) exposing 3 tools to Claude |
| `/cis-search` | Semantic search across all benchmarks |
| `/cis-audit` | Generate a CIS compliance checklist for a platform |
| `/cis-benchmark` | Browse the section structure of a benchmark |
| **cis-compliance-auditor** | Agent for deep-dive compliance workflows |
| 3 auto-skills | Context-activated skills for search, audit, and lookup |

## Benchmarks Covered

**Cloud:** AWS Foundations, AWS Compute, AWS Storage, Azure Foundations, Azure Compute, Azure Database, Azure Storage, DigitalOcean Foundations, DigitalOcean Services

**SaaS / Identity:** Microsoft 365, Google Workspace, Intune (Office + Windows 11)

**Linux:** RHEL 8/9/10, Ubuntu 22.04 LTS, Ubuntu 24.04 LTS

**Windows:** Windows Server 2019/2022/2025

**Virtualization:** VMware ESXi 6.5/6.7/7.0/8

**Network:** HPE Aruba CX Switch, FortiGate 7.4.x

## Requirements

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or pip
- [Claude Code](https://claude.ai/code)
- CIS benchmark PDFs (obtain from [CIS](https://www.cisecurity.org/cis-benchmarks))

## Setup

```bash
git clone https://github.com/wyre-technology/claudeCISBenchmarks
cd claudeCISBenchmarks

# Place your CIS benchmark PDFs in the repo root, then:
bash scripts/setup.sh
```

`setup.sh` creates a `.venv`, installs dependencies, and indexes all PDFs into a local ChromaDB vector store. The first run downloads the embedding model (~90 MB) and may take a few minutes.

## Registering with Claude Code

Add to your Claude Code MCP config or register the plugin directory. The `.mcp.json` at the repo root points Claude Code at the stdio server automatically:

```json
{
  "mcpServers": {
    "cis-benchmarks": {
      "command": "/path/to/claudeCISBenchmarks/.venv/bin/python",
      "args": ["/path/to/claudeCISBenchmarks/mcp-server/server.py", "--transport", "stdio"],
      "env": { "DB_DIR": "/path/to/claudeCISBenchmarks/mcp-server/data" }
    }
  }
}
```

## Running as an HTTP Server

For remote or multi-client deployments:

```bash
# Default: 127.0.0.1:8000
DB_DIR=mcp-server/data .venv/bin/python mcp-server/server.py --transport streamable-http

# Custom host/port
DB_DIR=mcp-server/data .venv/bin/python mcp-server/server.py \
  --transport streamable-http --host 0.0.0.0 --port 9000
```

Connect a client to `http://localhost:8000/mcp`.

## Usage Examples

```
/cis-search MFA enforcement
/cis-search password length in Windows Server 2022
/cis-audit AWS Foundations
/cis-benchmark FortiGate
```

Or just ask Claude naturally — the skills activate automatically when you ask about hardening, CIS controls, or compliance.

## Re-indexing

When you add new PDFs, re-run the indexer:

```bash
PDF_DIR=. DB_DIR=mcp-server/data .venv/bin/python mcp-server/indexer.py
```

## License

MIT — see [LICENSE](LICENSE).

> **Note:** CIS benchmark PDFs are not included in this repository. They are excluded via `.gitignore`. Obtain them from [cisecurity.org](https://www.cisecurity.org/cis-benchmarks).
