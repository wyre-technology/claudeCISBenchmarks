---
name: CIS Benchmark Lookup
description: >
  Activated when the user wants to browse, compare, or understand the structure 
  of specific CIS benchmarks. Shows section overviews and helps navigate to 
  specific control areas.
version: 1.0.0
---

# CIS Benchmark Lookup Skill

When a user wants to explore a specific CIS benchmark, understand its scope, or
compare benchmarks, use the MCP tools to retrieve and present structured information.

## When to activate

- "What benchmarks do you have?"
- "Show me the CIS Azure benchmark"
- "What sections does the RHEL 9 benchmark cover?"
- "Compare the AWS and Azure benchmarks"
- "What version of the CIS benchmark covers Windows Server 2025?"

## Approach

For a single benchmark:
1. Call `get_benchmark_summary` with the benchmark name
2. Present section structure clearly with control counts
3. Highlight key sections relevant to the user's context

For listing all benchmarks:
1. Call `list_benchmarks`
2. Group by category: Cloud, OS (Linux), OS (Windows), Network, SaaS/Identity

For comparison:
1. Get summaries for both benchmarks
2. Note overlapping control areas (IAM, logging, network) and differences

## Groupings for presentation

- **Cloud**: AWS Foundations, AWS Compute, AWS Storage, Azure Foundations, Azure Compute, Azure Storage, Azure Database, DigitalOcean
- **Linux**: RHEL 8/9/10, Ubuntu 22.04/24.04
- **Windows**: Windows Server 2019/2022/2025, Intune
- **Virtualization**: VMware ESXi 6.5/6.7/7.0/8
- **Network**: HPE Aruba, FortiGate
- **SaaS/Identity**: Microsoft 365, Google Workspace
