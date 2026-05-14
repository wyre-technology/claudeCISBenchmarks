---
name: CIS Control Search
description: >
  Automatically activated when the user asks about security controls, hardening 
  recommendations, compliance requirements, or mentions CIS benchmarks. Uses 
  semantic search across 27 CIS benchmarks to find relevant controls.
version: 1.0.0
---

# CIS Control Search Skill

When a user asks about security hardening, CIS controls, compliance requirements,
or platform-specific security settings, use the `cis-benchmarks` MCP tools to
find relevant controls.

## When to activate

- "What does CIS say about X?"
- "How do I harden Y?"
- "What are the password requirements for Z?"
- "Is MFA required in the CIS benchmark?"
- Any question about specific security configurations on indexed platforms

## How to use the tools

```
search_controls(query="<topic>", benchmark_filter="<platform if mentioned>", n_results=5)
```

Always cite the control ID and benchmark name in your response. If multiple
benchmarks have relevant controls, show the most relevant one first but mention
the others exist.

## Response format

When citing a control:
> **CIS {Benchmark Name}** — Control {ID}: {Title}
> {Key excerpt from the control}

Offer to expand with full remediation steps if the user needs implementation guidance.
