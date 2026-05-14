"""Tests for the 19 MCP prompt templates.

Strategy: call each prompt's underlying .fn() directly (synchronous,
returns the raw string) so we can assert on content without spinning up
a full MCP session. Tests cover:
  - All 19 prompts are registered
  - Every prompt returns a non-empty string
  - Every prompt references at least one MCP tool by name
  - Parameter interpolation works (platform names appear in output)
  - Per-prompt structural contracts (table headers, checklist format, etc.)
"""

import pytest

# conftest.py sets sys.path; this import must come after
import server

# ── Helpers ──────────────────────────────────────────────────────────────────

TOOL_NAMES = {"search_controls", "get_benchmark_summary", "list_benchmarks"}

ALL_PROMPTS = server.mcp._prompt_manager._prompts

EXPECTED_PROMPT_NAMES = {
    # Audit & Checklists
    "audit_platform",
    "new_system_hardening",
    "pre_audit_readiness",
    "quick_wins",
    # Remediation
    "explain_control",
    "remediation_plan",
    "remediation_script",
    # Gap Analysis & Compliance
    "gap_analysis",
    "exception_documentation",
    "cross_platform_policy",
    # MSP / Client-Facing
    "client_executive_summary",
    "onboarding_hardening",
    "vendor_assessment",
    # Security Domains
    "iam_review",
    "logging_requirements",
    "network_hardening",
    "encryption_requirements",
    "patch_management",
    "compare_benchmarks",
}

# Sample args for every prompt — used in parametrized tests
SAMPLE_ARGS: dict[str, dict] = {
    "audit_platform":           {"platform": "Ubuntu 22.04"},
    "new_system_hardening":     {"platform": "Windows Server 2022"},
    "pre_audit_readiness":      {"platform": "AWS Foundations", "audit_date": "2026-07-01"},
    "quick_wins":               {"platform": "Azure Foundations"},
    "explain_control":          {"control_id": "1.1.1", "benchmark": "CIS Ubuntu 22.04"},
    "remediation_plan":         {"platform": "RHEL 9", "findings": "Weak passwords, no MFA, audit logging disabled"},
    "remediation_script":       {"control_id": "1.1.2", "benchmark": "CIS Ubuntu 22.04", "os_version": "Ubuntu 22.04 LTS"},
    "gap_analysis":             {"platform": "AWS Foundations", "current_state": "MFA not enforced, S3 buckets public"},
    "exception_documentation":  {"control_id": "2.1", "benchmark": "CIS Azure Foundations", "reason": "Legacy system incompatibility"},
    "cross_platform_policy":    {"topic": "MFA enforcement"},
    "client_executive_summary": {"client_name": "Acme Corp", "platform": "Microsoft 365", "findings": "3 critical gaps found"},
    "onboarding_hardening":     {"client_name": "New Client Ltd", "platforms": "AWS, Windows Server 2022, Ubuntu 22.04"},
    "vendor_assessment":        {"vendor_platform": "Microsoft 365", "data_classification": "confidential"},
    "iam_review":               {"platform": "AWS Foundations"},
    "logging_requirements":     {"platform": "Azure Foundations"},
    "network_hardening":        {"platform": "FortiGate"},
    "encryption_requirements":  {"platform": "VMware ESXi 8"},
    "patch_management":         {"platform": "RHEL 9"},
    "compare_benchmarks":       {"platform_a": "Ubuntu 22.04", "platform_b": "RHEL 9"},
}


def call(name: str) -> str:
    """Call a prompt's underlying function with sample args."""
    fn = ALL_PROMPTS[name].fn
    return fn(**SAMPLE_ARGS[name])


# ── Registration ─────────────────────────────────────────────────────────────


def test_all_19_prompts_registered():
    assert len(ALL_PROMPTS) == 19, (
        f"Expected 19 prompts, got {len(ALL_PROMPTS)}. "
        f"Missing: {EXPECTED_PROMPT_NAMES - set(ALL_PROMPTS)}"
    )


def test_no_unexpected_prompts():
    unexpected = set(ALL_PROMPTS) - EXPECTED_PROMPT_NAMES
    assert not unexpected, f"Unexpected prompts registered: {unexpected}"


def test_all_prompts_have_titles():
    for name, prompt in ALL_PROMPTS.items():
        assert prompt.title, f"Prompt '{name}' has no title"


def test_all_prompts_covered_by_sample_args():
    missing = set(ALL_PROMPTS) - set(SAMPLE_ARGS)
    assert not missing, f"No sample args defined for: {missing}"


# ── Parametrized: universal contracts ────────────────────────────────────────


@pytest.mark.parametrize("name", sorted(EXPECTED_PROMPT_NAMES))
def test_prompt_returns_nonempty_string(name):
    result = call(name)
    assert isinstance(result, str)
    assert len(result) > 50, f"Prompt '{name}' returned suspiciously short output: {result!r}"


@pytest.mark.parametrize("name", sorted(EXPECTED_PROMPT_NAMES))
def test_prompt_references_a_tool(name):
    result = call(name)
    referenced = {t for t in TOOL_NAMES if t in result}
    assert referenced, (
        f"Prompt '{name}' doesn't reference any MCP tool. "
        f"Expected one of: {TOOL_NAMES}"
    )


@pytest.mark.parametrize("name", sorted(EXPECTED_PROMPT_NAMES))
def test_prompt_interpolates_first_param(name):
    """The first argument value should appear somewhere in the prompt text."""
    result = call(name)
    first_val = next(iter(SAMPLE_ARGS[name].values()))
    assert first_val.lower() in result.lower(), (
        f"Prompt '{name}' did not interpolate first param value '{first_val}'"
    )


# ── Per-prompt structural contracts ──────────────────────────────────────────


def test_audit_platform_uses_checklist_format():
    result = call("audit_platform")
    assert "- [ ]" in result, "audit_platform should include checklist format '- [ ]'"
    assert "Section" in result


def test_new_system_hardening_covers_iam_and_network():
    result = call("new_system_hardening")
    assert "identity" in result.lower() or "access" in result.lower()
    assert "network" in result.lower()


def test_pre_audit_readiness_references_date():
    result = call("pre_audit_readiness")
    assert "2026-07-01" in result


def test_quick_wins_mentions_time_and_effort():
    result = call("quick_wins")
    assert "minute" in result.lower() or "hour" in result.lower()
    assert "effort" in result.lower() or "impact" in result.lower()


def test_explain_control_has_all_sections():
    result = call("explain_control")
    for section in ("What it means", "Why it matters", "How to implement", "How to verify"):
        assert section in result, f"explain_control missing section: '{section}'"


def test_remediation_plan_has_priority_tiers():
    result = call("remediation_plan")
    for tier in ("P1", "P2", "P3"):
        assert tier in result, f"remediation_plan missing priority tier: '{tier}'"


def test_remediation_script_requires_idempotency():
    result = call("remediation_script")
    assert "idempotent" in result.lower() or "safe to run" in result.lower()
    assert "os_version" not in result  # param should be interpolated, not literal


def test_gap_analysis_has_table_structure():
    result = call("gap_analysis")
    assert "|" in result, "gap_analysis should include a markdown table"
    assert "Met" in result or "Failed" in result or "Partial" in result


def test_exception_documentation_has_approval_block():
    result = call("exception_documentation")
    assert "Approvals" in result or "approval" in result.lower()
    assert "exception" in result.lower()


def test_cross_platform_policy_mentions_all_categories():
    result = call("cross_platform_policy")
    for category in ("Cloud", "Linux", "Windows"):
        assert category in result, f"cross_platform_policy missing category: '{category}'"


def test_client_executive_summary_uses_rag_status():
    result = call("client_executive_summary")
    assert "Red" in result or "Amber" in result or "Green" in result
    assert "Acme Corp" in result


def test_onboarding_hardening_has_30_60_90_plan():
    result = call("onboarding_hardening")
    assert "30" in result and "60" in result and "90" in result


def test_vendor_assessment_has_required_domains():
    result = call("vendor_assessment")
    for domain in ("Access Control", "Encryption", "Logging"):
        assert domain in result, f"vendor_assessment missing domain: '{domain}'"


def test_compare_benchmarks_interpolates_both_platforms():
    result = call("compare_benchmarks")
    assert "Ubuntu 22.04" in result
    assert "RHEL 9" in result
    assert "|" in result, "compare_benchmarks should include a markdown table"


def test_iam_review_covers_key_areas():
    result = call("iam_review")
    for area in ("Privileged", "Authentication", "password"):
        assert area.lower() in result.lower(), f"iam_review missing area: '{area}'"


def test_logging_requirements_covers_retention_and_alerting():
    result = call("logging_requirements")
    assert "retention" in result.lower() or "Retention" in result
    assert "alert" in result.lower() or "Alert" in result


def test_network_hardening_covers_ingress_and_egress():
    result = call("network_hardening")
    assert "ingress" in result.lower() or "Ingress" in result
    assert "egress" in result.lower() or "Egress" in result


def test_encryption_requirements_specifies_tls_and_rest():
    result = call("encryption_requirements")
    assert "TLS" in result or "transit" in result.lower()
    assert "rest" in result.lower() or "at rest" in result.lower()


def test_patch_management_has_sla_mapping():
    result = call("patch_management")
    assert "critical" in result.lower()
    assert "SLA" in result or "timeline" in result.lower() or "cadence" in result.lower()
