# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-05-14

### Added
- MCP server (`mcp-server/server.py`) with three tools: `list_benchmarks`, `search_controls`, `get_benchmark_summary`
- Support for both **stdio** (Claude Code subprocess) and **streamable-http** transports via `--transport` flag
- PDF indexer (`mcp-server/indexer.py`) using PyMuPDF + ChromaDB — indexes 27 CIS benchmarks into a local vector store (17,684 chunks)
- Three Claude Code slash commands: `/cis-search`, `/cis-audit`, `/cis-benchmark`
- Three auto-activating skills: `cis-search`, `cis-audit`, `cis-benchmark-lookup`
- `cis-compliance-auditor` agent for deep-dive compliance workflows
- `scripts/setup.sh` for one-shot environment bootstrap using `uv`
- Plugin manifest at `.claude-plugin/plugin.json`

### Benchmarks indexed (v1.0.0)
- AWS: Foundations v6.0, Compute Services v1.1, Storage Services v1.0
- Azure: Foundations v5.0.0, Compute Services v2.0, Database Services v2.0, Storage v1.0.0
- DigitalOcean: Foundations v1.0.0, Services v1.0
- Google Workspace: Foundations v1.3.0
- HPE Aruba: CX Switch v1.0.1
- FortiGate: 7.4.x v1.0.1
- Microsoft 365: Foundations v6.0.1
- Intune: Office v1.1, Windows 11 v4.0
- RHEL: 8 v4.0, 9 v2.0, 10 v1.0.1
- Ubuntu: 22.04 LTS v3.0, 24.04 LTS v1.0
- VMware ESXi: 6.5 v1.0.0, 6.7 v1.3.0, 7.0 v1.5.0, 8 v1.2.0
- Windows Server: 2019 v3.0.0, 2022 v5.0.0, 2025 v2.0.0

[Unreleased]: https://github.com/wyre-technology/claudeCISBenchmarks/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/wyre-technology/claudeCISBenchmarks/releases/tag/v1.0.0
