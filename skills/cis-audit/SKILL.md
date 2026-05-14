---
name: CIS Audit Checklist
description: >
  Activated when the user asks to audit, assess, or check compliance of a system 
  against CIS benchmarks. Generates structured checklists organized by CIS section.
version: 1.0.0
---

# CIS Audit Checklist Skill

When a user wants to audit a system or generate a compliance checklist, retrieve
the benchmark structure and produce a formatted, actionable checklist.

## When to activate

- "Audit our AWS environment"
- "Give me a CIS checklist for Ubuntu 22.04"
- "What should I check on a new Windows Server?"
- "Generate a hardening checklist for [platform]"

## Approach

1. Call `get_benchmark_summary` to get section structure
2. Search 2-3 high-priority topics per section (IAM, network, logging, encryption)
3. Produce a `- [ ]` checklist grouped by section number
4. Mark Level 1 controls with `[L1]` and Level 2 with `[L2]` when determinable
5. Include the Control ID for every item so findings are traceable

## Output format

```markdown
# CIS Audit: {Platform}

## Section 1 — Identity and Access Management
- [ ] [L1] 1.1 — {Title}: {one-line audit action}
- [ ] [L1] 1.2 — {Title}: {one-line audit action}
- [ ] [L2] 1.3 — {Title}: {one-line audit action}

## Section 2 — ...
```

After the checklist, note that Level 1 = baseline security, Level 2 = higher
security environments (may impact usability).
