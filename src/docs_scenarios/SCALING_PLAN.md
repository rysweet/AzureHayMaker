# Scenario Generation Scaling Plan

## Current Status

### Completed Scenarios
1. **Analytics**: Batch ETL Pipeline (`analytics-01-batch-etl-pipeline.md`)
2. **Containers**: Simple Web App on Container Apps (`containers-01-simple-web-app.md`)
3. **Databases**: MySQL for WordPress (`databases-01-mysql-wordpress.md`)

**Total**: 3 of 50 scenarios complete

### Technology Areas Covered
- ✅ Analytics (1 of 5 complete)
- ✅ Containers (1 of 5 complete)
- ✅ Databases (1 of 5 complete)
- ⬜ AI & Machine Learning (0 of 5)
- ⬜ Compute (0 of 5)
- ⬜ Hybrid + Multicloud (0 of 5)
- ⬜ Identity (0 of 5)
- ⬜ Networking (0 of 5)
- ⬜ Security (0 of 5)
- ⬜ Web Apps (0 of 5)

---

## Scenario Quality Standards

The completed scenarios establish the quality bar:

### Structure Requirements
1. **Complete three-phase workflow**:
   - Phase 1: Deployment and Validation (with all az cli commands)
   - Phase 2: Mid-Day Operations (8+ hours of operations)
   - Phase 3: Cleanup and Tear-Down (complete resource removal)

2. **Comprehensive automation**:
   - All commands are runnable az cli / terraform / bicep
   - Environment variables clearly defined
   - Proper error handling considered
   - Validation steps included

3. **Documentation excellence**:
   - Company profile and use case clearly defined
   - All Azure services listed
   - Links to official Azure documentation
   - Resource naming conventions documented
   - Tagging strategy: `AzureHayMaker-managed=true`

4. **Operational realism**:
   - Minimum 8-hour operations phase
   - Multiple management operations defined
   - Monitoring and metrics included
   - Realistic business scenarios

---

## Scaling Strategy

### Approach 1: Agent-Assisted Generation (Recommended)

Use specialized agents to research and generate scenarios following the established template.

**Steps**:
1. For each remaining technology area:
   a. Use Explore agent to research Azure Architecture Center
   b. Identify 5 simple, deployable scenarios
   c. Use builder agent to generate scenario documents from template
   d. Review and validate generated scenarios
   e. Commit scenarios to repository

**Estimated Time**:
- Research per area: 15-30 minutes
- Generation per scenario: 10-15 minutes
- **Total**: ~15-20 hours for remaining 47 scenarios

**Advantages**:
- Maintains quality standards
- Leverages agent expertise
- Systematic and repeatable
- Can be done in batches

**Process for each scenario**:
```bash
1. Launch Explore agent with technology area focus
2. Review research output
3. Launch builder agent with:
   - Scenario template
   - Research findings
   - Quality requirements
4. Validate generated scenario
5. Save to docs/scenarios/
```

### Approach 2: Batch Generation with Templates

Create parameterized templates for common scenario patterns and generate multiple scenarios using scripting.

**Common Patterns Identified**:
- **Data Pipeline Pattern**: Data source → Processing → Data sink
- **Web Application Pattern**: Container/compute → networking → storage
- **Database Pattern**: Database service → networking → backup/security
- **Security Pattern**: Identity → RBAC → monitoring/audit
- **Networking Pattern**: VNet → subnets → routing/firewall

**Steps**:
1. Create pattern templates for each type
2. Define parameters (services, names, configurations)
3. Generate scenario variations from patterns
4. Review and customize for each technology area

**Estimated Time**:
- Template creation: 4-6 hours
- Generation: 1-2 hours
- Review/customization: 10-15 hours
- **Total**: ~15-20 hours

### Approach 3: Hybrid (Template + Agent Review)

Combine template generation with agent review for quality assurance.

**Steps**:
1. Use templates to generate initial scenarios quickly
2. Use reviewer agent to validate each scenario
3. Use builder agent to enhance scenarios that need work
4. Final human review of batch

**Estimated Time**: ~12-18 hours

---

## Recommended Path Forward

**Phase 1: Complete Representative Samples (2-3 more scenarios)**
- Create 1-2 more high-quality scenarios for additional tech areas
- Validates template applicability across diverse areas
- **Time**: 2-3 hours

**Phase 2: Agent-Assisted Batch Generation (Technology Area by Technology Area)**
- Use Explore + Builder agents systematically
- Generate 5 scenarios per technology area
- Review and commit in batches
- **Time**: 12-15 hours

**Phase 3: Quality Review Pass**
- Use reviewer agent to check all scenarios
- Validate automation commands
- Ensure consistency
- **Time**: 3-4 hours

**Total Estimated Time**: ~17-22 hours for remaining 47 scenarios

---

## Scenario Naming Convention

```
{technology-area}-{number}-{brief-description}.md
```

Examples:
- `analytics-01-batch-etl-pipeline.md`
- `analytics-02-realtime-streaming.md`
- `containers-01-simple-web-app.md`
- `databases-01-mysql-wordpress.md`
- `ai-ml-01-cognitive-services.md`
- `security-01-zero-trust-network.md`

---

## Next Steps

1. ✅ Complete 2-3 more representative scenarios
2. ⬜ Begin agent-assisted generation for remaining technology areas
3. ⬜ Prioritize technology areas based on common usage:
   - Web Apps (high priority - common use case)
   - Compute (high priority - VMs are ubiquitous)
   - Security (high priority - fundamental concern)
   - Networking (medium priority)
   - Identity (medium priority)
   - AI & ML (medium priority)
   - Hybrid + Multicloud (lower priority - more complex)

4. ⬜ After scenarios complete, generate goal-seeking agents (Phase 1.2)

---

## Quality Gates

Before marking a scenario as complete, verify:
- [ ] All three phases documented with commands
- [ ] At least 8 operations defined for mid-day management
- [ ] Cleanup commands remove all resources
- [ ] Resource naming includes unique ID
- [ ] All resources tagged with `AzureHayMaker-managed=true`
- [ ] Links to Azure documentation provided
- [ ] Company profile and use case described
- [ ] Estimated durations provided

---

## Goal-Seeking Agent Generation (Next Phase)

After scenarios are complete, use the Goal Agent Generator Guide to create agents:
- Reference: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/blob/main/docs/GOAL_AGENT_GENERATOR_GUIDE.md
- One agent per scenario
- Agent prompt includes full scenario document
- Agent has access to Azure CLI, Terraform, Bicep documentation
- Agent keeps logs and reports to control program
- Agent operates for 8+ hours
- Agent performs autonomous troubleshooting

---

## Success Criteria

Groundwork phase complete when:
- [ ] 50+ scenarios documented in `docs/scenarios/`
- [ ] 50+ goal-seeking agents created in `src/agents/`
- [ ] Claude Code skill(s) created for Azure guidance
- [ ] All scenarios tested for basic command validity
- [ ] Scenarios cover all 10 technology areas (5 each minimum)
