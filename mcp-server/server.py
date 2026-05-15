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


@mcp.custom_route("/health", methods=["GET"])
async def health(request):  # noqa: ANN001 — starlette Request
    from starlette.responses import JSONResponse
    col = collection()
    return JSONResponse({"status": "ok", "service": "cis-benchmarks-mcp", "chunks": col.count()})

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


# ═══════════════════════════════════════════════════════════════
# PROMPTS
# Pre-baked templates that prime Claude with context and output
# format before it starts calling tools.
# ═══════════════════════════════════════════════════════════════

# ── Audit & Checklists ───────────────────────────────────────────

@mcp.prompt(title="Full Platform Audit")
def audit_platform(platform: str) -> str:
    """Generate a complete CIS compliance audit checklist for a platform."""
    return (
        f"You are a CIS compliance auditor. Use get_benchmark_summary to retrieve the "
        f"section structure for '{platform}', then use search_controls to find the key "
        f"controls in each section. Produce a full audit checklist formatted as:\n\n"
        f"# CIS Audit: {platform}\n\n"
        f"## Section N — <Name>\n"
        f"- [ ] [L1/L2] Control ID — Title\n"
        f"      Audit: one-line verification step\n\n"
        f"Group by section. Mark Level 1 controls [L1] and Level 2 [L2] where "
        f"determinable. End with a summary of total controls by level."
    )


@mcp.prompt(title="New System Hardening Guide")
def new_system_hardening(platform: str) -> str:
    """Step-by-step hardening guide for a freshly provisioned system."""
    return (
        f"You are a security engineer hardening a brand new {platform} system. "
        f"Use search_controls with benchmark_filter='{platform}' to find controls "
        f"in this priority order: (1) identity & access, (2) network, (3) logging & "
        f"monitoring, (4) patching & updates, (5) encryption, (6) application config.\n\n"
        f"For each area produce:\n"
        f"**<Area>**\n"
        f"- Control ID: Title — `concrete command or config step`\n\n"
        f"Focus on Level 1 controls. Flag any that require a maintenance window or "
        f"may impact availability."
    )


@mcp.prompt(title="Pre-Audit Readiness Check")
def pre_audit_readiness(platform: str, audit_date: str) -> str:
    """Prepare a client for an upcoming CIS compliance audit."""
    return (
        f"A CIS compliance audit for {platform} is scheduled for {audit_date}. "
        f"Use search_controls with benchmark_filter='{platform}' to identify the "
        f"highest-risk control areas. Produce:\n\n"
        f"1. **Critical gaps to close before {audit_date}** (Level 1 controls most "
        f"   commonly failed)\n"
        f"2. **Evidence to collect** (screenshots, config exports, logs per control)\n"
        f"3. **Quick wins** (controls fixable in under 1 hour)\n"
        f"4. **Likely exceptions** (controls that need formal exception documentation)\n\n"
        f"Be direct about risk — flag anything that would be an automatic fail."
    )


@mcp.prompt(title="Level 1 Quick Wins")
def quick_wins(platform: str) -> str:
    """Find the easiest Level 1 controls to implement immediately."""
    return (
        f"Use search_controls with benchmark_filter='{platform}' to find Level 1 CIS "
        f"controls for {platform} that can be implemented quickly (under 30 minutes, "
        f"no downtime, low risk of breakage). Focus on: password policies, account "
        f"settings, basic logging, unused service disablement.\n\n"
        f"Output as a prioritised list:\n"
        f"### Quick Win N — Control ID: Title\n"
        f"**Time:** ~X minutes  **Risk:** Low/Medium\n"
        f"**Steps:** 1. ... 2. ... 3. ...\n"
        f"**Verify:** how to confirm it's applied\n\n"
        f"Aim for 10 wins. Sort by impact-to-effort ratio."
    )


# ── Remediation ──────────────────────────────────────────────────

@mcp.prompt(title="Explain & Remediate Control")
def explain_control(control_id: str, benchmark: str) -> str:
    """Plain-language explanation and remediation steps for a specific control."""
    return (
        f"Use search_controls(query='{control_id}', benchmark_filter='{benchmark}') "
        f"to retrieve the full text of this control. Then produce:\n\n"
        f"## {benchmark} — Control {control_id}\n\n"
        f"**What it means** (2-3 sentences, plain language, no jargon)\n\n"
        f"**Why it matters** (specific risk if not implemented — data breach, "
        f"ransomware pivot, compliance failure, etc.)\n\n"
        f"**How to implement**\n"
        f"```\nstep-by-step commands or config changes\n```\n\n"
        f"**How to verify** (audit command or check)\n\n"
        f"**Gotchas** (anything that commonly breaks or needs testing first)"
    )


@mcp.prompt(title="Prioritised Remediation Plan")
def remediation_plan(platform: str, findings: str) -> str:
    """Turn a list of audit findings into a prioritised remediation plan."""
    return (
        f"You are creating a remediation plan for {platform}. The following findings "
        f"were identified:\n\n{findings}\n\n"
        f"For each finding, use search_controls to retrieve the CIS control details. "
        f"Then produce a plan grouped by priority:\n\n"
        f"### P1 — Critical (fix within 24-48 hours)\n"
        f"### P2 — High (fix within 1 week)\n"
        f"### P3 — Medium (fix within 30 days)\n"
        f"### P4 — Low / Enhancement\n\n"
        f"For each item: Control ID, title, one-line fix, estimated effort, owner "
        f"(sysadmin / security / vendor). End with a total effort estimate."
    )


@mcp.prompt(title="Remediation Script Generator")
def remediation_script(control_id: str, benchmark: str, os_version: str = "") -> str:
    """Generate a remediation script for a specific CIS control."""
    context = f" running {os_version}" if os_version else ""
    return (
        f"Use search_controls(query='{control_id}', benchmark_filter='{benchmark}') "
        f"to get the full control text. Then write a remediation script for a system"
        f"{context}.\n\n"
        f"Requirements:\n"
        f"- Idempotent (safe to run multiple times)\n"
        f"- Includes a pre-check that skips if already compliant\n"
        f"- Includes a post-check that verifies the change was applied\n"
        f"- Comments reference the CIS control ID\n"
        f"- Exits non-zero on failure\n\n"
        f"Produce the script, then a one-line command to verify compliance."
    )


# ── Gap Analysis & Compliance ────────────────────────────────────

@mcp.prompt(title="Gap Analysis")
def gap_analysis(platform: str, current_state: str) -> str:
    """Identify CIS compliance gaps from a description of current configuration."""
    return (
        f"Perform a CIS gap analysis for {platform}. Current state:\n\n"
        f"{current_state}\n\n"
        f"Use search_controls with benchmark_filter='{platform}' to check the key "
        f"control areas. For each area, assess whether the current state meets, "
        f"partially meets, or fails the CIS requirement.\n\n"
        f"Output:\n"
        f"| Control ID | Title | Status | Gap Description |\n"
        f"|---|---|---|---|\n"
        f"| ... | ... | ✅ Met / ⚠️ Partial / ❌ Failed | ... |\n\n"
        f"End with: total controls assessed, pass rate, top 3 priority gaps."
    )


@mcp.prompt(title="Exception Documentation")
def exception_documentation(control_id: str, benchmark: str, reason: str) -> str:
    """Draft formal exception documentation for a control that can't be implemented."""
    return (
        f"Use search_controls(query='{control_id}', benchmark_filter='{benchmark}') "
        f"to retrieve the control details. Then draft a formal security exception document:\n\n"
        f"## Security Exception Request\n\n"
        f"**Control:** {control_id} — [title from search]\n"
        f"**Benchmark:** {benchmark}\n"
        f"**Date:** [today]\n\n"
        f"**Business Justification:** {reason}\n\n"
        f"**Risk Assessment:** What risk does non-compliance introduce?\n\n"
        f"**Compensating Controls:** What alternative mitigations are in place?\n\n"
        f"**Review Date:** When should this exception be reassessed?\n\n"
        f"**Approvals:** [ ] Security Lead  [ ] System Owner  [ ] Compliance\n\n"
        f"Keep the tone formal and auditor-facing."
    )


@mcp.prompt(title="Cross-Platform Policy Check")
def cross_platform_policy(topic: str) -> str:
    """Find what CIS recommends about a topic across all platforms."""
    return (
        f"Use search_controls(query='{topic}', n_results=15) to find how CIS addresses "
        f"'{topic}' across all indexed benchmarks. Group the results by platform category "
        f"(Cloud, Linux, Windows, Network, SaaS).\n\n"
        f"For each category, summarise:\n"
        f"- The consensus recommendation\n"
        f"- Any platform-specific variations worth noting\n"
        f"- The strictest requirement across all benchmarks\n\n"
        f"End with: 'Universal baseline' — the one policy that satisfies all CIS "
        f"benchmarks on this topic simultaneously."
    )


# ── MSP / Client-Facing ──────────────────────────────────────────

@mcp.prompt(title="Client Executive Summary")
def client_executive_summary(client_name: str, platform: str, findings: str) -> str:
    """Non-technical compliance summary for a client executive or board."""
    return (
        f"Write a non-technical executive summary of a CIS {platform} compliance "
        f"assessment for {client_name}. Findings:\n\n{findings}\n\n"
        f"Use search_controls if you need to verify control details. Structure:\n\n"
        f"## {client_name} — Security Compliance Summary\n\n"
        f"**Overall Posture:** [Red/Amber/Green] with one-sentence rationale\n\n"
        f"**What We Found:** 3-5 bullet points, plain language, business impact framing "
        f"(avoid technical jargon, relate to data breach / ransomware / regulatory risk)\n\n"
        f"**What We're Fixing:** prioritised list with target dates\n\n"
        f"**What's Working Well:** 2-3 positives\n\n"
        f"**Next Steps:** concrete actions with owners and dates\n\n"
        f"Tone: professional, clear, reassuring but honest. Max 1 page."
    )


@mcp.prompt(title="New Client Onboarding Hardening")
def onboarding_hardening(client_name: str, platforms: str) -> str:
    """Hardening checklist for a new MSP client across their platform stack."""
    return (
        f"You are onboarding a new MSP client: {client_name}. Their environment "
        f"includes: {platforms}.\n\n"
        f"For each platform, use get_benchmark_summary to get the section structure, "
        f"then use search_controls to identify the top 5 highest-impact Level 1 "
        f"controls.\n\n"
        f"Produce a 30-60-90 day hardening roadmap:\n\n"
        f"**Day 1-30 (Foundation):** IAM, MFA, basic logging — controls every client "
        f"must have immediately\n\n"
        f"**Day 31-60 (Hardening):** Network controls, patching cadence, encryption\n\n"
        f"**Day 61-90 (Optimisation):** Advanced monitoring, Level 2 controls, "
        f"exception documentation for anything skipped\n\n"
        f"Flag any controls that require change management approval."
    )


@mcp.prompt(title="Vendor / Third-Party Assessment")
def vendor_assessment(vendor_platform: str, data_classification: str) -> str:
    """Assess a vendor's platform against CIS controls for a given data tier."""
    return (
        f"Assess whether {vendor_platform} meets CIS requirements for handling "
        f"{data_classification} data. Use search_controls with "
        f"benchmark_filter='{vendor_platform}' focusing on: access control, "
        f"encryption at rest/transit, logging, and incident response.\n\n"
        f"Produce a vendor security questionnaire response template:\n\n"
        f"**Access Control** (CIS controls X.X-X.X)\n"
        f"- Required: ...\n"
        f"- Questions to ask vendor: ...\n\n"
        f"**Data Encryption** ...\n"
        f"**Audit Logging** ...\n"
        f"**Incident Response** ...\n\n"
        f"End with a pass/fail threshold: minimum controls required before "
        f"handling {data_classification} data."
    )


# ── Security Domain Deep-Dives ───────────────────────────────────

@mcp.prompt(title="IAM & Access Control Review")
def iam_review(platform: str) -> str:
    """Deep-dive into identity and access management controls for a platform."""
    return (
        f"Use search_controls with benchmark_filter='{platform}' and these queries in "
        f"sequence: 'identity access management', 'privileged accounts', "
        f"'service accounts', 'password policy', 'MFA multi-factor'. Consolidate "
        f"results into a comprehensive IAM review:\n\n"
        f"## IAM Controls: {platform}\n\n"
        f"### Account Management\n"
        f"### Privileged Access\n"
        f"### Authentication Requirements\n"
        f"### Service & Application Accounts\n"
        f"### Access Reviews & Recertification\n\n"
        f"For each section: list the CIS controls, current best practice, and a "
        f"one-line verification command where applicable."
    )


@mcp.prompt(title="Logging & Monitoring Requirements")
def logging_requirements(platform: str) -> str:
    """Extract all CIS logging and monitoring controls for a platform."""
    return (
        f"Use search_controls with benchmark_filter='{platform}' and queries: "
        f"'audit log', 'logging', 'monitoring', 'alerting', 'SIEM'. Produce:\n\n"
        f"## Logging & Monitoring: {platform}\n\n"
        f"**What to Log** — list of event types CIS requires capturing\n\n"
        f"**Log Retention** — minimum retention periods specified\n\n"
        f"**Alerting Thresholds** — events that must trigger alerts\n\n"
        f"**Log Integrity** — controls to prevent log tampering\n\n"
        f"**SIEM Integration Notes** — what to forward and at what priority\n\n"
        f"Format each control as: Control ID | What to configure | Verification"
    )


@mcp.prompt(title="Network Security Controls")
def network_hardening(platform: str) -> str:
    """All CIS network security and firewall controls for a platform."""
    return (
        f"Use search_controls with benchmark_filter='{platform}' and queries: "
        f"'network', 'firewall', 'port', 'protocol', 'encryption in transit', "
        f"'TLS', 'remote access'. Produce:\n\n"
        f"## Network Security: {platform}\n\n"
        f"### Ingress Controls (what should be blocked/allowed in)\n"
        f"### Egress Controls (outbound restrictions)\n"
        f"### Encryption in Transit\n"
        f"### Remote Access & VPN\n"
        f"### Network Segmentation\n\n"
        f"For each control: ID, requirement, and a config snippet or verification "
        f"command. Flag any controls that commonly cause application breakage."
    )


@mcp.prompt(title="Encryption & Data Protection")
def encryption_requirements(platform: str) -> str:
    """CIS encryption controls covering data at rest, in transit, and key management."""
    return (
        f"Use search_controls with benchmark_filter='{platform}' and queries: "
        f"'encryption', 'encrypt at rest', 'TLS', 'certificate', 'key management', "
        f"'secrets'. Produce:\n\n"
        f"## Encryption & Data Protection: {platform}\n\n"
        f"**Data at Rest** — required encryption standards and scope\n\n"
        f"**Data in Transit** — minimum TLS version, cipher suites\n\n"
        f"**Key Management** — key rotation, storage, access controls\n\n"
        f"**Secrets & Credentials** — how CIS says to handle API keys, passwords\n\n"
        f"Include the specific algorithm/standard each control requires "
        f"(e.g. AES-256, TLS 1.2+) and the verification method."
    )


@mcp.prompt(title="Patching & Vulnerability Management")
def patch_management(platform: str) -> str:
    """CIS controls covering patching cadence, vulnerability scanning, and EOL software."""
    return (
        f"Use search_controls with benchmark_filter='{platform}' and queries: "
        f"'patch', 'update', 'vulnerability', 'CVE', 'end of life', 'software "
        f"inventory'. Produce:\n\n"
        f"## Patching & Vulnerability Management: {platform}\n\n"
        f"**Patch Cadence** — required timelines for critical / high / medium\n\n"
        f"**Vulnerability Scanning** — frequency and scope required\n\n"
        f"**EOL / Unsupported Software** — what CIS says about running unsupported versions\n\n"
        f"**Software Inventory** — controls for knowing what's installed\n\n"
        f"Map each control to a concrete SLA: e.g. 'Critical patches: 24h, High: 7d'."
    )


@mcp.prompt(title="Compare Two Benchmarks")
def compare_benchmarks(platform_a: str, platform_b: str) -> str:
    """Side-by-side comparison of two CIS benchmarks to find overlaps and differences."""
    return (
        f"Use get_benchmark_summary for both '{platform_a}' and '{platform_b}'. "
        f"Then use search_controls to find controls in shared topic areas: "
        f"IAM, network, logging, encryption, patching.\n\n"
        f"Produce a side-by-side comparison:\n\n"
        f"## {platform_a} vs {platform_b}\n\n"
        f"| Topic | {platform_a} Requirement | {platform_b} Requirement | Stricter |\n"
        f"|---|---|---|---|\n\n"
        f"After the table:\n"
        f"**Common baseline** — controls both benchmarks agree on\n"
        f"**{platform_a}-specific** — unique requirements\n"
        f"**{platform_b}-specific** — unique requirements\n"
        f"**Recommendation** — if you had to implement only one policy covering both, "
        f"what would it be?"
    )


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
