---
name: cis-benchmark
description: Show structure and sections of a specific CIS benchmark. Usage: /cis-benchmark <name>
---

Display the section structure and key information for a specific CIS benchmark.

## Instructions

1. Extract the benchmark name from user input.
2. Call `get_benchmark_summary` with that name.
3. If the benchmark is not found, call `list_benchmarks` and show similar options.
4. Present the benchmark structure clearly with:
   - Full benchmark name and version
   - Section overview (numbered sections with control counts)
   - First 3 controls of each section as a preview
5. Offer to:
   - Run `/cis-audit <name>` for a full checklist
   - Search for a specific control within this benchmark
   - Compare with another related benchmark

## Example invocations

- `/cis-benchmark Azure Foundations`
- `/cis-benchmark FortiGate`
- `/cis-benchmark RHEL 9`
