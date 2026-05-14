---
name: cis-audit
description: Generate a CIS compliance audit checklist for a given platform. Usage: /cis-audit <platform>
---

Generate a CIS compliance audit checklist for the specified platform.

## Instructions

1. Parse the platform from user input (e.g. "AWS", "Ubuntu 22.04", "Windows Server 2022", "Microsoft 365").
2. Call `get_benchmark_summary` to get the section structure of the relevant benchmark.
3. For each top-level section, call `search_controls` with a representative query to pull key controls.
4. Produce a formatted audit checklist grouped by section:
   - [ ] Control ID — Title (Level 1 / Level 2 if determinable from text)
   - Concise audit action in one line
5. End with a note about Level 1 (essential) vs Level 2 (defense-in-depth) profiles.
6. Offer to expand any section into full remediation steps.

## Format

```
# CIS Audit Checklist: <Platform Name>
Generated: <date>

## Section 1: <Section Name>
- [ ] 1.1 — <Control Title>
      Audit: <how to verify>
- [ ] 1.2 — <Control Title>
      ...

## Section 2: ...
```

## Example invocations

- `/cis-audit AWS Foundations`
- `/cis-audit Ubuntu 22.04`
- `/cis-audit Microsoft 365`
