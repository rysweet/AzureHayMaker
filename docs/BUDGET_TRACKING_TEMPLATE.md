# Budget Tracking Template for Enhancement Roadmap

**Purpose**: Track actual spending vs. planned budget for all enhancements

**Update Frequency**: Weekly

---

## Portfolio-Level Budget Summary

| Quarter | Planned Budget | Actual Spend | Variance | % Complete | Forecast at Completion |
|---------|----------------|--------------|----------|------------|------------------------|
| Q1 2026 | $113,000 | $0 | $0 (0%) | 0% | $113,000 |
| Q2 2026 | $162,000 | $0 | $0 (0%) | 0% | $162,000 |
| Q3 2026 | $40,000 | $0 | $0 (0%) | 0% | $40,000 |
| Q4 2026 | $22,000 | $0 | $0 (0%) | 0% | $22,000 |
| **TOTAL** | **$337,000** | **$0** | **$0** | **0%** | **$337,000** |

**Contingency Reserve**: $67,000 (20%)
**Total Available**: $404,000

---

## Q1 2026: Security & Compliance Foundation

**Planned Budget**: $113,000
**Actual Spend**: $0
**Variance**: $0 (0%)

### Issue #124: SIEM Telemetry Export

| Category | Planned | Actual | Variance | Notes |
|----------|---------|--------|----------|-------|
| **Developer Time** | $52,500 | $0 | $0 | 3.5 weeks × $150/hr × 100 hrs/wk |
| **Infrastructure** | $2,400 | $0 | $0 | Event Hub, Storage (annual) |
| **Testing** | $9,000 | $0 | $0 | 1 week testing |
| **Documentation** | $4,500 | $0 | $0 | 0.5 week docs |
| **Maintenance (Year 1)** | $10,500 | $0 | $0 | 20% of dev cost |
| **Subtotal** | **$78,900** | **$0** | **$0** | |

**Status**: 🔴 Not Started
**% Complete**: 0%
**Forecast at Completion**: $78,900

---

### Issue #125: Windows VM Security Hardening

| Category | Planned | Actual | Variance | Notes |
|----------|---------|--------|----------|-------|
| **Developer Time** | $18,000 | $0 | $0 | 1.5 weeks × $150/hr × 80 hrs/wk |
| **Infrastructure** | $3,000 | $0 | $0 | Key Vault, Bastion (annual) |
| **Testing** | $6,000 | $0 | $0 | Security audit, pen testing |
| **Documentation** | $3,000 | $0 | $0 | Security docs |
| **Maintenance (Year 1)** | $3,600 | $0 | $0 | 20% of dev cost |
| **Subtotal** | **$33,600** | **$0** | **$0** | |

**Status**: 🔴 Not Started
**% Complete**: 0%
**Forecast at Completion**: $33,600

---

## Q2 2026: Operational Excellence

**Planned Budget**: $162,000
**Actual Spend**: $0
**Variance**: $0 (0%)

### Issue #126: Multi-Tenant Resource Isolation

| Category | Planned | Actual | Variance | Notes |
|----------|---------|--------|----------|-------|
| **Developer Time** | $90,000 | $0 | $0 | 6 weeks × $150/hr × 100 hrs/wk |
| **Infrastructure** | $12,000 | $0 | $0 | Test subscriptions (annual) |
| **Testing** | $15,000 | $0 | $0 | Multi-tenant testing |
| **Documentation** | $7,500 | $0 | $0 | Architecture docs |
| **Maintenance (Year 1)** | $18,000 | $0 | $0 | 20% of dev cost |
| **Subtotal** | **$142,500** | **$0** | **$0** | |

**Status**: 🔴 Not Started
**% Complete**: 0%
**Forecast at Completion**: $142,500

---

### Other Q2 Enhancements

**Issue #127: Distributed Tracing**
- Planned: $46,200 | Actual: $0 | Variance: $0

**Issue #128: Cost Budget Enforcement**
- Planned: $34,500 | Actual: $0 | Variance: $0

**Issue #129: Agent Health Checks**
- Planned: $25,000 | Actual: $0 | Variance: $0

---

## Budget Tracking Instructions

### Weekly Updates

**Every Friday**, update this document:

1. **Capture actual spend**:
   ```bash
   # Developer hours this week
   - Developer A: X hours on #125
   - Developer B: Y hours on #124

   # Infrastructure costs (from Azure Cost Management)
   - Event Hub: $Z
   - Key Vault: $Z
   ```

2. **Calculate variance**:
   - Variance = Actual - Planned
   - Variance % = (Variance / Planned) × 100%

3. **Update forecast**:
   - If ahead of schedule: May come in under budget
   - If behind schedule: May need more time/money
   - Forecast = (Actual Spend / % Complete) × 100%

4. **Flag concerns**:
   - Variance >20%: 🟡 Yellow flag (monitor closely)
   - Variance >50%: 🔴 Red flag (escalate immediately)

---

### Monthly Reviews

**Last Friday of each month**, generate summary:

```markdown
## Monthly Budget Review - [MONTH YEAR]

**Quarter**: Q[X] 2026

### Summary
- Total spent this month: $XX,XXX
- Cumulative spend for quarter: $XX,XXX
- Remaining budget: $XX,XXX
- Variance: ±X%

### By Enhancement
- #124: XX% complete, $XX spent, $XX remaining
- #125: XX% complete, $XX spent, $XX remaining

### Concerns
- [List any budget concerns]

### Forecast
- On track to complete Q[X] within budget: Yes / No
- Projected final cost: $XX,XXX (±X%)
```

Share in monthly roadmap review meeting.

---

### Quarterly Reconciliation

**End of each quarter**, reconcile actual vs. planned:

1. **Final costs**: Sum all spending for the quarter
2. **Variance analysis**: Why did we over/underspend?
3. **ROI calculation**: Use actual costs to recalculate ROI
4. **Lessons learned**: What cost assumptions were wrong?
5. **Adjust future quarters**: Update Q2-Q4 budgets based on learnings

---

## Cost Categories Explained

### Developer Time
**Calculation**: Hours × Hourly Rate

**Hourly rate**: $150/hr (fully loaded - includes salary, benefits, overhead)

**Tracking**:
- Use time tracking tool (Toggl, Harvest, or manual logs)
- Tag time entries with enhancement issue number
- Review weekly timesheets

**Example**:
```
Week 1: 40 hours on #125 → $6,000
Week 2: 35 hours on #125 → $5,250
Total: 75 hours → $11,250
```

---

### Infrastructure
**Calculation**: Azure service costs (monthly or annual)

**Tracking**:
- Tag all resources with: `Enhancement=issue-XXX`
- Query Azure Cost Management API weekly
- Review cost anomalies

**Example**:
```bash
# Query costs for #124
az costmanagement query \
  --type "ActualCost" \
  --dataset-filter "tags/Enhancement eq 'issue-124'" \
  --timeframe "MonthToDate"
```

---

### Testing
**Calculation**: Testing time + external services

**Includes**:
- QA engineer time (if separate from dev)
- Security audits (external firm)
- Penetration testing
- Load testing tools (if paid)

---

### Documentation
**Calculation**: Technical writer time OR developer time for docs

**Includes**:
- Implementation specs (if written by dedicated writer)
- API documentation
- User guides
- Architecture diagrams

**Our approach**: Developers write docs (included in dev time) + dedicated time for polishing

---

### Maintenance
**Calculation**: 20% of development cost (industry standard)

**Covers**:
- Bug fixes post-deployment
- Dependency updates
- Security patches
- Minor enhancements
- Support and troubleshooting

**Example**: $50K development → $10K/year maintenance

---

## Variance Thresholds

| Variance | Status | Action Required |
|----------|--------|-----------------|
| **<10%** | 🟢 Green | Normal - no action |
| **10-20%** | 🟡 Yellow | Monitor - identify cause |
| **20-50%** | 🟠 Orange | Escalate - mitigation plan needed |
| **>50%** | 🔴 Red | Emergency - stakeholder meeting |

---

## Budget Adjustment Process

**If variance exceeds 20%**:

1. **Analyze root cause**:
   - Underestimated complexity?
   - Scope creep?
   - Unforeseen dependencies?
   - Resource inefficiency?

2. **Calculate impact**:
   - How much additional budget needed?
   - Which other enhancements affected?
   - Can we reallocate from contingency?

3. **Propose solutions**:
   - Option A: Use contingency reserve
   - Option B: Reduce scope
   - Option C: Defer to next quarter
   - Option D: Request additional budget

4. **Get approval**:
   - Present to stakeholders
   - Document decision
   - Update roadmap

5. **Communicate**:
   - Update this budget tracking document
   - Update Roadmap Status
   - Notify affected teams

---

## Excel/Google Sheets Template

**Suggested structure** for spreadsheet tracking:

**Sheet 1: Summary**
| Quarter | Enhancement | Planned | Actual | Variance | % Complete | Status |
|---------|-------------|---------|--------|----------|------------|--------|

**Sheet 2: Q1 Detail**
| Week | Enhancement | Category | Planned | Actual | Variance | Notes |
|------|-------------|----------|---------|--------|----------|-------|

**Sheet 3: Q2 Detail**
[Same structure]

**Sheet 4: Analysis**
- Variance charts
- Burn rate graph
- Forecast vs. actual

---

## Integration with Financial Systems

**If using formal accounting**:

1. **Create cost centers** for each enhancement:
   - CC-E124: SIEM Export
   - CC-E125: VM Security
   - etc.

2. **Tag Azure resources** with cost center:
   ```json
   {
     "tags": {
       "CostCenter": "CC-E124",
       "Enhancement": "SIEM-Export",
       "Quarter": "Q1-2026"
     }
   }
   ```

3. **Extract from accounting system** monthly:
   - Developer time from payroll (tagged with enhancement)
   - Azure costs from Cost Management (tagged resources)
   - Contractor invoices (tagged by enhancement)

4. **Reconcile with this template**

---

## Related Documentation

- [Cost-Benefit Analysis](../specs/ENHANCEMENT_COST_BENEFIT_ANALYSIS.md) - Original projections
- [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Strategic plan with budgets
- [Roadmap Status](ROADMAP_STATUS.md) - Live progress tracking

---

**Update this document weekly** to maintain accurate budget visibility and enable data-driven decisions.
