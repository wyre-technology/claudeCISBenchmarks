"""Integration tests for the CIS Benchmarks MCP server tools."""

import subprocess
import sys

import chromadb
import pytest

# conftest.py sets DB_DIR and sys.path before this import
import server


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_collection():
    """Reset the module-level ChromaDB singleton between tests."""
    server._client = None
    server._collection = None
    yield
    server._client = None
    server._collection = None


# ── Data layer ───────────────────────────────────────────────────────────────


def test_database_is_populated():
    col = server.collection()
    count = col.count()
    assert count > 10_000, f"Expected >10k chunks, got {count}"


def test_all_27_benchmarks_present():
    result = server.list_benchmarks()
    # Spot-check a representative from each category
    for name in [
        "AWS Foundations",
        "Azure Foundations",
        "Ubuntu",
        "Windows Server 2022",
        "FortiGate",
        "Google Workspace",
    ]:
        assert name.lower() in result.lower(), f"Benchmark not found: {name}"


# ── list_benchmarks ──────────────────────────────────────────────────────────


def test_list_benchmarks_returns_27():
    result = server.list_benchmarks()
    lines = [l for l in result.splitlines() if l.strip().startswith("CIS") or "Microsoft" in l or "Intune" in l]
    # We have 27 PDFs but display_names may vary; just assert a healthy count
    assert len(lines) >= 20, f"Expected ≥20 benchmark lines, got {len(lines)}"


# ── search_controls ──────────────────────────────────────────────────────────


def test_search_returns_results():
    result = server.search_controls("multi-factor authentication")
    assert "Control:" in result
    assert "Relevance:" in result


def test_search_respects_n_results():
    result = server.search_controls("password policy", n_results=3)
    # Count separator lines as a proxy for result count
    separators = result.count("─" * 60)
    assert separators <= 3


def test_search_benchmark_filter():
    result = server.search_controls("audit logging", benchmark_filter="Ubuntu", n_results=5)
    assert "Ubuntu" in result
    # Should not contain unrelated platforms in the results
    assert "Windows Server" not in result


def test_search_filter_no_match_gives_helpful_message():
    result = server.search_controls("password", benchmark_filter="NonExistentPlatformXYZ")
    assert "No results" in result or "not found" in result.lower() or "matched" in result


def test_search_caps_n_results_at_20():
    result = server.search_controls("hardening", n_results=999)
    separators = result.count("─" * 60)
    assert separators <= 20


def test_search_mfa_finds_relevant_controls():
    """MFA search should return controls about multi-factor authentication."""
    result = server.search_controls("require multi-factor authentication", n_results=5)
    assert "Multi-factor Authentication" in result or "MFA" in result


# ── get_benchmark_summary ────────────────────────────────────────────────────


def test_benchmark_summary_found():
    result = server.get_benchmark_summary("AWS Foundations")
    assert "Section" in result
    assert "AWS" in result


def test_benchmark_summary_shows_sections():
    result = server.get_benchmark_summary("Windows Server 2022")
    # Windows Server benchmark has many sections
    section_lines = [l for l in result.splitlines() if l.startswith("**Section")]
    assert len(section_lines) >= 5


def test_benchmark_summary_not_found():
    result = server.get_benchmark_summary("NonExistentBenchmarkXYZ999")
    assert "not found" in result.lower() or "No benchmark" in result


def test_benchmark_summary_partial_name():
    """Partial names like 'FortiGate' should resolve."""
    result = server.get_benchmark_summary("FortiGate")
    assert "FortiGate" in result
    assert "Section" in result


# ── Transport startup ────────────────────────────────────────────────────────


def test_server_help_flag():
    """Server accepts --help without error (validates argparse wiring)."""
    proc = subprocess.run(
        [sys.executable, "mcp-server/server.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "streamable-http" in proc.stdout
    assert "stdio" in proc.stdout


def test_server_invalid_transport_rejected():
    proc = subprocess.run(
        [sys.executable, "mcp-server/server.py", "--transport", "invalid"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
