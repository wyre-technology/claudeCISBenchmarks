"""
MCP server exposing CIS benchmark RAG search as Claude tools.

Tools:
  list_benchmarks       — list all indexed benchmarks
  search_controls       — semantic search across all (or one) benchmark
  get_benchmark_summary — section-level overview of a specific benchmark

Transport modes:
  stdio (default)       — subprocess mode, used by Claude Code via .mcp.json
  streamable-http       — HTTP mode for remote/multi-client deployments

Usage:
  python server.py                                    # stdio
  python server.py --transport streamable-http        # HTTP on 127.0.0.1:8000
  python server.py --transport streamable-http --host 0.0.0.0 --port 9000
"""

from __future__ import annotations

import argparse
import os

import chromadb
from mcp.server.fastmcp import FastMCP

DB_DIR = os.environ.get(
    "DB_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
)

mcp = FastMCP("cis-benchmarks", stateless_http=True)

_client: chromadb.PersistentClient | None = None
_collection = None


def collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=DB_DIR)
        _collection = _client.get_collection("cis_controls")
    return _collection


# ─────────────────────────────────────────────────────────────


@mcp.tool()
def list_benchmarks() -> str:
    """List every CIS benchmark that has been indexed, with control count."""
    results = collection().get(limit=50_000, include=["metadatas"])
    counts: dict[str, int] = {}
    for m in results["metadatas"]:
        name = m["display_name"]
        counts[name] = counts.get(name, 0) + 1

    lines = ["Indexed CIS Benchmarks\n" + "─" * 40]
    for name in sorted(counts):
        lines.append(f"  {name}  ({counts[name]} sections)")
    return "\n".join(lines)


@mcp.tool()
def search_controls(
    query: str,
    benchmark_filter: str = "",
    n_results: int = 5,
) -> str:
    """
    Semantic search for CIS controls relevant to a topic.

    Args:
        query:            What to find, e.g. "MFA", "password length", "audit logging"
        benchmark_filter: Optional partial benchmark name to restrict results,
                          e.g. "AWS Foundations", "Ubuntu 22.04", "Windows Server 2022"
        n_results:        How many controls to return (default 5, max 20)
    """
    n_results = min(n_results, 20)
    fetch = min(n_results * 4, 60) if benchmark_filter else n_results

    raw = collection().query(
        query_texts=[query],
        n_results=fetch,
        include=["documents", "metadatas", "distances"],
    )

    docs = raw["documents"][0]
    metas = raw["metadatas"][0]
    dists = raw["distances"][0]

    if not docs:
        return "No results found."

    out = [f"Results for: **{query}**\n"]
    shown = 0
    for doc, meta, dist in zip(docs, metas, dists):
        if benchmark_filter and benchmark_filter.lower() not in meta["display_name"].lower():
            continue
        if shown >= n_results:
            break

        relevance = round((1 - dist) * 100, 1)
        ctrl = f"{meta['control_id']} — {meta['control_title']}" if meta["control_id"] else "(general section)"
        excerpt = doc[:900] + ("…" if len(doc) > 900 else "")

        out.append(
            f"### {meta['display_name']}\n"
            f"**Control:** {ctrl}  ·  **Relevance:** {relevance}%\n\n"
            f"{excerpt}\n\n"
            + "─" * 60
        )
        shown += 1

    if shown == 0:
        return f"No results matched benchmark filter: '{benchmark_filter}'"

    return "\n".join(out)


@mcp.tool()
def get_benchmark_summary(benchmark_name: str) -> str:
    """
    Return the top-level section structure of a specific CIS benchmark.

    Args:
        benchmark_name: Partial name, e.g. "AWS Foundations", "Ubuntu 24.04", "FortiGate"
    """
    results = collection().get(limit=50_000, include=["metadatas"])

    sections: dict[str, list[str]] = {}
    matched_name: str | None = None

    for m in results["metadatas"]:
        if benchmark_name.lower() not in m["display_name"].lower():
            continue
        matched_name = m["display_name"]
        cid = m["control_id"]
        if not cid:
            continue
        top = cid.split(".")[0]
        entry = f"  {cid}: {m['control_title']}"
        sections.setdefault(top, []).append(entry)

    if not matched_name:
        return f"No benchmark found matching: '{benchmark_name}'"

    lines = [f"## {matched_name}\n"]
    for sec in sorted(sections, key=lambda x: int(x)):
        lines.append(f"**Section {sec}** ({len(sections[sec])} controls)")
        for ctrl in sections[sec][:6]:
            lines.append(ctrl)
        if len(sections[sec]) > 6:
            lines.append(f"  … and {len(sections[sec]) - 6} more")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CIS Benchmarks MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    args = parser.parse_args()

    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")
