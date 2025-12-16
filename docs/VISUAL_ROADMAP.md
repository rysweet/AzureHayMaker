# Visual Enhancement Roadmap 2025-2026

**Quick visual reference for Azure HayMaker enhancement timeline.**

See [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) for detailed specifications.

---

## Quarterly Timeline

```mermaid
gantt
    title Azure HayMaker Enhancement Roadmap 2025-2026
    dateFormat YYYY-MM-DD

    section Q1 2026 (P0-Critical)
    SIEM Telemetry Export #124           :crit, siem, 2026-01-06, 3.5w
    Windows VM Security #125             :crit, security, 2026-01-06, 2w

    section Q2 2026 (P1-High)
    Distributed Tracing #127             :trace, 2026-04-01, 2w
    Cost Budget Enforcement #128         :cost, 2026-04-01, 1.5w
    Agent Health Checks #129             :health, 2026-04-15, 2w
    Multi-Tenant Isolation #126          :tenant, 2026-05-01, 6w

    section Q3 2026 (P2-Medium)
    Local Dev Mode #130                  :dev, 2026-07-01, 4w
    GitHub Actions Agent #131            :gh, 2026-08-01, 2w

    section Q4 2026 (P2-Medium)
    Analytics Dashboard                  :dashboard, 2026-10-01, 3w
    Scenario Testing Framework           :testing, 2026-11-01, 4w
```

---

## Impact vs. Effort Matrix

```mermaid
quadrantChart
    title Enhancement Prioritization Matrix
    x-axis Low Effort --> High Effort
    y-axis Low Impact --> High Impact
    quadrant-1 Quick Wins
    quadrant-2 Strategic Investments
    quadrant-3 Consider Deferring
    quadrant-4 May Not Be Worth It

    Windows VM Security (125): [0.15, 0.95]
    SIEM Export (124): [0.5, 0.95]
    Cost Enforcement (128): [0.25, 0.85]
    Circuit Breakers (129): [0.35, 0.70]
    Distributed Tracing (127): [0.30, 0.70]
    Multi-Tenant (126): [0.85, 0.90]
    GitHub Actions (131): [0.35, 0.80]
    Local Dev Mode (130): [0.75, 0.65]
    Analytics Dashboard: [0.50, 0.65]
    Testing Framework: [0.75, 0.60]
```

---

## Dependency Flow

```mermaid
graph TD
    PR119[PR #119: W365 + M365 E2E]
    PR121[PR #121: Windows VM]
    PR123[PR #123: Computer Use]
    PR112[PR #112: KW CLI]

    E124[#124: SIEM Export<br/>P0-Critical]
    E125[#125: VM Security<br/>P0-Critical]
    E126[#126: Multi-Tenant<br/>P1-High]
    E127[#127: Distributed Tracing<br/>P1-High]
    E128[#128: Cost Enforcement<br/>P1-High]
    E129[#129: Circuit Breakers<br/>P1-High]
    E130[#130: Local Dev<br/>P2-Medium]
    E131[#131: GitHub Actions<br/>P2-Medium]
    E132[Analytics Dashboard<br/>P2-Medium]
    E133[Testing Framework<br/>P2-Medium]

    PR119 -->|unblocks| E124
    PR119 -->|unblocks| E127
    PR119 -->|unblocks| E132

    E125 -->|fixes| PR121
    PR121 -->|enables| PR123

    E124 -->|enhances| E127
    E127 -->|provides data| E132

    E126 -->|requires| ArchReview[Architecture Review]

    E129 -->|monitors| PR123

    E130 -->|improves| PR112
    E133 -->|tests| PR112

    style PR119 fill:#90EE90
    style E124 fill:#FF6B6B
    style E125 fill:#FF6B6B
    style E126 fill:#FFD93D
    style E127 fill:#FFD93D
    style E128 fill:#FFD93D
    style E129 fill:#FFD93D
```

**Legend**:
- 🟢 Green: Ready to merge
- 🔴 Red: P0-Critical
- 🟡 Yellow: P1-High
- ⬜ White: P2-Medium

---

## ROI Comparison

```mermaid
bar
    title Enhancement ROI Comparison
    x-axis [Windows VM Security, Multi-Tenant, Cost Enforcement, SIEM Export, Distributed Tracing]
    y-axis ROI Percentage (0-1200)
    bar [1165, 233, 184, 120, 36]
```

---

## Resource Allocation by Quarter

```mermaid
pie title Q1 2026 Budget Allocation ($78.9K)
    "SIEM Export" : 68400
    "Windows VM Security" : 10500
```

```mermaid
pie title Q2 2026 Budget Allocation ($142.5K)
    "Multi-Tenant" : 90000
    "Distributed Tracing" : 22500
    "Cost Enforcement" : 18000
    "Circuit Breakers" : 12000
```

---

## Priority Overview

| Priority | Count | Total Investment | Total Returns | Portfolio ROI |
|----------|-------|------------------|---------------|---------------|
| P0-Critical | 2 | $112,500 | $599,000 | 432% |
| P1-High | 4 | $161,700 | $635,000 | 293% |
| P2-Medium | 4 | $61,500 | TBD | TBD |
| **TOTAL** | **10** | **$335,700** | **$1,234,000** | **267%** |

---

## Quick Decision Guide

**Choose enhancement based on your goal:**

| Your Goal | Enhancement | Issue |
|-----------|-------------|-------|
| 🔒 Block production security risks | Windows VM Security | #125 |
| 🎯 Enable core red team use case | SIEM Telemetry Export | #124 |
| 💰 Prevent cost overruns | Cost Budget Enforcement | #128 |
| 🚀 Enable SaaS business model | Multi-Tenant Isolation | #126 |
| 🔍 Improve troubleshooting | Distributed Tracing | #127 |
| 🛡️ Improve reliability | Circuit Breakers | #129 |
| 👨‍💻 Improve developer experience | Local Dev Mode | #130 |
| 📊 Improve visibility | Analytics Dashboard | - |
| 🧪 Improve quality | Testing Framework | - |
| 🔗 Enable DevOps integration | GitHub Actions Agent | #131 |

---

## Files & Resources

**Documentation**:
- [Full Roadmap](ENHANCEMENT_ROADMAP.md) - Complete strategic plan
- [Quick Reference](ENHANCEMENT_QUICK_REFERENCE.md) - One-page summary
- [Roadmap Status](ROADMAP_STATUS.md) - Live progress tracking
- [Contributing Guide](CONTRIBUTING_ENHANCEMENTS.md) - How to contribute

**Specifications**:
- [Specs Index](../specs/README.md) - All implementation specs
- [SIEM Export Spec](../specs/SIEM_TELEMETRY_EXPORT.md) - P0-Critical
- [VM Security Spec](../specs/WINDOWS_VM_SECURITY_HARDENING.md) - P0-Critical
- [Dependencies](../specs/ENHANCEMENT_DEPENDENCIES.md) - Critical path
- [Cost-Benefit](../specs/ENHANCEMENT_COST_BENEFIT_ANALYSIS.md) - ROI analysis

**GitHub**:
- [All Issues](https://github.com/rysweet/AzureHayMaker/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
- [Milestones](https://github.com/rysweet/AzureHayMaker/milestones)
- [Pull Requests](https://github.com/rysweet/AzureHayMaker/pulls)

---

**Last Updated**: 2025-11-30
