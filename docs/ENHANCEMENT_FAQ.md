# Enhancement Roadmap - Frequently Asked Questions

**Answers to common questions about the Azure HayMaker enhancement roadmap.**

Last Updated: 2025-11-30

---

## General Questions

### Q: Why do we need an enhancement roadmap?

**A**: Azure HayMaker has 4 open PRs and many potential improvements, but no clear prioritization or resource allocation. The roadmap provides:
- Data-driven prioritization (ROI for each enhancement)
- Clear timeline and milestones (quarterly phases)
- Resource allocation (how many people, how much budget)
- Risk assessment (what could go wrong, how to mitigate)

**Without roadmap**: Ad-hoc development, unclear priorities, resource conflicts
**With roadmap**: Strategic direction, predictable execution, measurable progress

---

### Q: How were these 10 enhancements chosen?

**A**: Identified through comprehensive project analysis:
1. Reviewed entire codebase (50+ scenarios, agent framework, orchestrator)
2. Analyzed 4 open PRs for patterns and gaps
3. Consulted existing issues and PR comments
4. Identified security vulnerabilities (PR #121 review)
5. Analyzed core use case requirements (SIEM integration for red team)
6. Evaluated business opportunities (multi-tenant for SaaS/MSP)

**Prioritization based on**:
- Business impact (revenue, cost savings, risk mitigation)
- Technical complexity (effort estimation)
- Dependencies (what blocks what)
- ROI calculations (quantified value)

---

### Q: Can I suggest a new enhancement not on this list?

**A**: Absolutely! Use the enhancement issue template:

```bash
gh issue create --template enhancement.md
```

**Required information**:
- Priority (P0/P1/P2) with justification
- Business value (revenue, cost savings, or strategic benefit)
- Complexity estimate
- Dependencies and blockers

New enhancements will be evaluated against existing roadmap and may be added if they provide higher ROI or address critical gaps.

---

## Priority & Scheduling Questions

### Q: Why is Windows VM Security (#125) P0-Critical?

**A**: **Production blocker** with critical security vulnerabilities:
- Credentials exposed in plaintext (logs)
- RDP accessible from ANY internet IP (unrestricted NSG)
- No disk encryption, no JIT access
- Current security score: 72/100 (C grade)

**Cannot deploy to customer environments** with these issues. SOC 2 certification (required for enterprise sales) impossible without fixes.

**ROI**: 1,165% (highest of all enhancements)
**Effort**: 1-2 weeks (low complexity)
**Decision**: Must fix before production deployment

---

### Q: Why is SIEM Export (#124) P0-Critical?

**A**: **Core use case blocked**.

Azure HayMaker's mission is generating "hay" telemetry to hide red team "needles". For red team exercises, the hay **MUST appear in the target organization's SIEM**. Currently, telemetry stays within HayMaker storage.

**Without SIEM export**: Tool cannot fulfill its primary purpose
**With SIEM export**: Enables all red team exercises (core value prop)

**ROI**: 120% ($150K/year in enabled contracts)

---

### Q: Can we skip P0-Critical items and go straight to Multi-Tenant (#126)?

**A**: **Not recommended**.

Multi-tenant has highest SaaS revenue potential ($450K/year), but:
1. Security issues (#125) make ANY deployment risky
2. SIEM export (#124) is core use case - multi-tenant without SIEM = useless for red team
3. Multi-tenant is high complexity (6 weeks) - fix P0 items first (3.5 weeks total)

**Recommended sequence**: Fix security → Enable SIEM → Then add multi-tenant

---

### Q: Why is Distributed Tracing (#127) only 36% ROI?

**A**: Lower direct financial return but **high strategic value**:
- Enables faster debugging (MTTR: 4hrs → 30min)
- Foundation for other enhancements (Dashboard needs tracing data)
- Operational maturity signal (enterprise customers expect this)

**ROI is conservative** - only counts quantifiable time savings, not strategic value. Still recommended for Q2 as operational foundation.

---

## Budget & Resources Questions

### Q: Can we do this with fewer than 3 FTE?

**A**: Yes, with timeline adjustments.

**Option 1**: 2 FTE (60% slower)
- Q1: 12-14 weeks (from 8-10 weeks)
- Q2: 18 weeks (from 12 weeks)
- Defer some P1-High to Q3

**Option 2**: 1 FTE + contractors
- Use contractors for well-defined work (Issue #125 security fixes)
- FTE focuses on complex items (#126 multi-tenant)

**Option 3**: 2 FTE + community contributions
- Excellent contributor docs enable external help
- Assume 20-30% of work done by community

**Minimum viable**: 2 FTE for P0-Critical only, defer rest

---

### Q: What if we only have budget for Q1 ($113K)?

**A**: **Q1 alone delivers 432% ROI**.

Focus on P0-Critical items:
- Issue #124: SIEM Export
- Issue #125: Windows VM Security

**Delivers**:
- ✅ Production-ready security posture
- ✅ Core use case functional
- ✅ Platform ready for customer deployments

**Defer to 2027**: P1-High and P2-Medium items

**Re-evaluate**: After Q1, reassess ROI and decide on Q2-Q4 based on actual results

---

### Q: Can we hire contractors instead of FTE?

**A**: Yes, for specific enhancements.

**Good for contractors** (well-defined scope):
- #125: Windows VM Security (security consultant, 1-2 weeks)
- #124: SIEM Export (integration specialist, 2-3 weeks)
- #127: Distributed Tracing (observability engineer, 2 weeks)
- #131: GitHub Actions (DevOps engineer, 2 weeks)

**Better for FTE** (complex, requires deep context):
- #126: Multi-Tenant (architectural changes, 6 weeks)
- #130: Local Dev Mode (touches entire codebase, 4 weeks)

**Hybrid approach**: 1-2 FTE + contractors for specialized work = optimal

---

## Technical Questions

### Q: Do we have to use the exact technologies specified (e.g., React for dashboard)?

**A**: No, specs provide recommendations but alternatives are acceptable.

**Examples**:
- Dashboard: React, Vue, or Svelte all work - team preference
- SIEM connectors: Can prioritize Splunk over Sentinel if customer base demands it
- Testing framework: pytest is current stack, but could use alternatives

**Requirement**: Maintain architecture principles (modular, well-tested, documented)

**Process**: If deviating significantly, update spec and get architecture review

---

### Q: Can we implement enhancements in different order than roadmap?

**A**: Yes, with dependency awareness.

**Hard dependencies**:
- #124 (SIEM Export) REQUIRES PR #119 merged first
- Dashboard REQUIRES #124 and #127 for rich data

**Recommended order** considers:
1. **Dependencies** (what blocks what)
2. **ROI** (highest return first)
3. **Risk** (security fixes before feature adds)
4. **Team skills** (match work to available expertise)

**Example valid reorder**: Start #128 (Cost Enforcement) before #127 (Tracing) - both P1-High, no dependencies, similar effort

**Invalid reorder**: Start Dashboard before #124 - missing data source

---

### Q: What if an enhancement takes 2x longer than estimated?

**A**: See [Risk Mitigation Playbooks](RISK_MITIGATION_PLAYBOOKS.md) - Risk #1 (Budget Overrun).

**Response**:
1. Assess cause (complexity vs. scope creep)
2. Options: Reduce scope / Extend timeline / Add resources / Defer
3. Update Roadmap Status document
4. Communicate to stakeholders
5. Adjust quarterly milestones if needed

**Contingency budget**: 20% reserve ($67K) for overruns

---

## Business Questions

### Q: How confident are we in the $1.2M value projection?

**A**: **Conservative estimates with sensitivity analysis**.

**Confidence levels**:
- **High confidence** (80%+): Security breach avoidance, cost savings, productivity gains
- **Medium confidence** (60%): SaaS revenue (depends on market adoption)
- **Lower confidence** (40%): MSP contracts (early-stage market)

**Sensitivity analysis included**:
- Even with 2x cost overruns, 4 of 5 top enhancements remain positive ROI
- Even with 50% lower adoption, multi-tenant still delivers 119% ROI

**Data sources**:
- Industry benchmarks (IBM breach cost report: $8M average)
- Current pipeline (12 enterprise leads requiring SOC 2)
- Historical data (manual process time savings)

---

### Q: What's the competitive landscape for these enhancements?

**A**: **12-18 month lead on competitors** (based on complexity analysis).

**Current competitors**: None with native SIEM export for Azure telemetry generation

**Post-roadmap competitive moat**:
- SIEM export: First to market (12-month lead)
- Multi-tenant: Complex to replicate (18-month lead)
- GitHub Actions: Unique integration (indefinite lead)

**Market advantage**: Open-source + enterprise-grade security + SIEM integration = unmatched

---

## Implementation Questions

### Q: Can I start working on an enhancement now?

**A**: **Yes!** See [Quick Start for Contributors](QUICK_START_CONTRIBUTORS.md) (15 minutes).

**Steps**:
1. Pick an enhancement from GitHub Issues
2. Read the implementation spec (specs/ directory)
3. Use starter code template (examples/ directory) if available
4. Create branch, write tests, implement, create PR

**No approval needed** to start contributing - just follow the specs!

---

### Q: What if I disagree with an implementation spec?

**A**: **Feedback welcome!**

**Process**:
1. Comment on the GitHub issue with your concerns
2. Propose alternative approach with rationale
3. Team discusses trade-offs
4. Update spec if alternative is better
5. Proceed with revised approach

**Philosophy**: Specs are **living documents**, not set in stone. Better ideas are always welcome.

---

### Q: Do I need Azure resources to test my changes?

**A**: Depends on the enhancement.

**No Azure required**:
- Unit tests (use mocks)
- #130: Local Dev Mode (that's the point!)
- Code templates and examples

**Azure required**:
- Integration tests (optional but recommended)
- E2E testing (MANDATORY before PR merge)
- #124: SIEM Export (need Sentinel workspace for testing)
- #125: VM Security (need subscription for VM provisioning)

**Budget**: Ask for test Azure subscription access if needed

---

## Process Questions

### Q: How do I know if my PR is ready to merge?

**A**: Use the PR template checklist:

**Required**:
- [ ] All unit tests passing
- [ ] Integration tests passing (if applicable)
- [ ] **E2E testing completed** (MANDATORY - test like a user would)
- [ ] Security scan passed (no hardcoded secrets)
- [ ] Code review completed
- [ ] Philosophy compliance verified (no TODOs, stubs, placeholders)

**E2E testing is non-negotiable** - see user preferences in PROJECT.md

---

### Q: What happens after an enhancement is merged?

**A**: Post-merge checklist:

1. **Update Roadmap Status** - Mark enhancement as Complete ✅
2. **Update OKRs** - Score Key Results as achieved
3. **Measure actual ROI** - Compare to projections
4. **Document learnings** - Add to DISCOVERIES.md if non-obvious
5. **Celebrate** - Shout-out in CHANGELOG
6. **Monitor** - Track metrics defined in Monitoring Strategy

**Continuous improvement**: Use actual results to refine future estimates

---

## Roadmap Management Questions

### Q: Can we adjust the roadmap mid-quarter?

**A**: Yes, quarterly retrospectives are designed for this.

**Adjustment triggers**:
- New information (customer feedback, market changes)
- Significant variance (2x cost overrun, timeline delays)
- Priority shifts (new P0-Critical issue discovered)
- Resource changes (team size, budget adjustments)

**Process**:
1. Update Roadmap Status with proposed changes
2. Discuss in monthly roadmap review meeting
3. Get stakeholder approval
4. Update GitHub milestones and issue priorities
5. Communicate changes to team

**Philosophy**: Roadmap is a **plan**, not a **prison**. Adapt as needed.

---

### Q: How do we handle conflicts between enhancements and other work?

**A**: Prioritization framework:

**Priority order**:
1. **P0-Critical bugs** in production (drop everything)
2. **P0-Critical enhancements** (#124, #125)
3. **Customer commitments** (contracted features)
4. **P1-High enhancements**
5. **P2-Medium enhancements**
6. **Nice-to-haves**

**If conflict**: Defer lower-priority work, adjust timeline, communicate impact

---

### Q: What if actual ROI is much lower than projected?

**A**: **Re-evaluate and course correct**.

**Triggers for re-evaluation**:
- Actual ROI <50% of projected
- Payback period 2x longer than estimated
- Benefits don't materialize (no SaaS revenue from multi-tenant)

**Actions**:
1. Root cause analysis (why was projection wrong?)
2. Assess continuation (stop, pivot, or persevere)
3. Update Cost-Benefit Analysis with actual data
4. Adjust future roadmap based on learnings

**Example**: If multi-tenant delivers only $100K instead of $450K:
- ROI drops from 233% to 70%
- Still positive, but reassess Q3-Q4 priorities
- Maybe defer Dashboard, focus on higher-ROI items

---

## Success Metrics Questions

### Q: How do we measure success?

**A**: Three layers of measurement:

**1. Delivery Metrics** (Did we execute the plan?)
- Enhancement completion % (10 enhancements delivered)
- Budget variance (<10% target)
- Timeline variance (<20% target)

**2. Quality Metrics** (Did we build it right?)
- Test coverage (>85%)
- Security score (>90/100)
- Code review scores (>85/100)

**3. Business Metrics** (Did it create value?)
- Actual ROI vs. projected
- Customer adoption (10+ tenants, 5+ SaaS customers)
- Revenue generated (SaaS MRR, MSP contracts)

**See**: [Quarterly OKRs](QUARTERLY_OKRS.md) for specific Key Results per quarter

---

### Q: What defines "done" for an enhancement?

**A**: Acceptance criteria from GitHub issue + OKR achievement.

**Minimum requirements**:
- [ ] All scope items implemented
- [ ] Tests passing (unit, integration, E2E)
- [ ] Security review passed
- [ ] Documentation updated
- [ ] Deployed to production
- [ ] Success metrics met (from OKRs)

**Example for #124 (SIEM Export)**:
- Sentinel, Splunk, Syslog connectors working
- 99.9% delivery SLA achieved
- <1s latency (p95)
- 10K events/sec throughput demonstrated
- End-to-end red team exercise successful

**Not done until customers validate it works in real red team scenarios**

---

## Getting Help

### Q: Where do I get help with an enhancement?

**A**: Multiple support channels:

**Technical Questions**:
- Comment on GitHub issue (#124-131)
- Check implementation spec in specs/ directory
- Review code examples in examples/ directory
- Ask in GitHub Discussions

**Process Questions**:
- Read Contributing Guide (docs/CONTRIBUTING_ENHANCEMENTS.md)
- Check Quick Start (docs/QUICK_START_CONTRIBUTORS.md)
- Ask in GitHub Discussions

**Strategic Questions**:
- Review Executive Summary (docs/EXECUTIVE_SUMMARY.md)
- Check Cost-Benefit Analysis (specs/ENHANCEMENT_COST_BENEFIT_ANALYSIS.md)
- Request stakeholder meeting

---

### Q: Who approves changes to the roadmap?

**A**: Depends on impact:

**Minor changes** (no approval needed):
- Timeline adjustments <1 week
- Resource shifts within same quarter
- Spec clarifications

**Moderate changes** (Product Owner approval):
- Timeline adjustments >1 week
- Scope reductions
- Priority changes within same tier (P1↔P1)

**Major changes** (Stakeholder approval):
- Budget changes >20%
- Priority tier changes (P1→P0 or P0→P2)
- Adding/removing enhancements
- Quarterly phase shifts

**Emergency changes** (Executive approval):
- Production security issues requiring immediate resources
- Market shifts requiring strategic pivot

---

## Related Documentation

- [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Full strategic plan
- [Executive Summary](EXECUTIVE_SUMMARY.md) - Business case and ROI
- [Quick Start Guide](QUICK_START_CONTRIBUTORS.md) - 15-minute onboarding
- [Contributing Guide](CONTRIBUTING_ENHANCEMENTS.md) - Detailed workflow
- [GitHub Issues](https://github.com/rysweet/AzureHayMaker/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) - All enhancements

---

## Still Have Questions?

**Open a GitHub Discussion**: https://github.com/rysweet/AzureHayMaker/discussions

**Or comment on relevant issue**: https://github.com/rysweet/AzureHayMaker/issues

We're here to help! 🚀
