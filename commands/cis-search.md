---
name: cis-search
description: Semantic search across all CIS benchmarks. Usage: /cis-search <topic>
---

Search the CIS benchmark database for controls related to the given topic.

## Instructions

1. Extract the search query from the user's input (everything after `/cis-search`).
2. If a specific benchmark is mentioned (e.g. "in AWS", "for Ubuntu"), extract it as a filter.
3. Call the `search_controls` MCP tool with:
   - `query`: the topic
   - `benchmark_filter`: the platform name if specified (empty string otherwise)
   - `n_results`: 5 (default) or as specified by the user
4. Present the results clearly, grouping by benchmark if multiple are returned.
5. After showing results, offer to:
   - Get more detail on a specific control
   - Search within a specific benchmark
   - Generate a remediation checklist

## Example invocations

- `/cis-search MFA enforcement` → search all benchmarks for MFA-related controls
- `/cis-search password policy in Windows Server 2022` → filter to that benchmark
- `/cis-search audit logging for AWS` → filter to AWS benchmarks
