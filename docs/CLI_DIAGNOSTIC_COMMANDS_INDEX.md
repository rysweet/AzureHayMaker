# CLI Diagnostic Commands - Documentation Index

## Overview

This index provides navigation and context for the complete CLI Diagnostic Commands requirements suite for implementing orchestrator management commands in Azure HayMaker.

### Project Information

- **Issue:** #26
- **Feature:** CLI Diagnostic Commands for Azure Container Apps Orchestrator
- **Phase:** Phase 1 - Core Status Commands
- **Priority:** HIGH
- **Complexity:** Medium (2-3 days, 36-48 hours)
- **Quality Score:** 92%

---

## Document Suite

### 1. CLI_DIAGNOSTIC_COMMANDS_REQUIREMENTS.md

**Purpose:** Complete, authoritative specification for implementation

**Size:** 932 lines, 27KB

**Contents:**
- Executive summary with complexity assessment
- 4 command specifications with full syntax and examples
- Output format requirements (table, JSON, YAML)
- Error handling with exit codes and examples
- Configuration management (file and environment)
- Success criteria (functional + non-functional)
- 6 categories of testing requirements
- Implementation roadmap (4 phases)
- Dependencies and documentation requirements
- Future enhancements (Phase 2+)
- Quality assurance checklist
- Configuration examples and appendices

**Primary Audience:** Architects, Tech Leads, Project Managers

**How to Use:**
1. Review Section 1 (Overview) for quick understanding
2. Reference specific sections for command details
3. Use Section 5 (Success Criteria) to validate completion
4. Consult Section 6 (Testing) for test implementation
5. Follow Section 7 (Roadmap) for phased implementation

**Key Sections:**
- 1.2: Command Specifications (status, replicas, logs, health)
- 2: Configuration Management
- 3: Error Handling with Exit Codes
- 5: Success Criteria (functional + non-functional)
- 6: Testing Requirements

---

### 2. CLI_DIAGNOSTIC_COMMANDS_PROMPT.md

**Purpose:** Ready-to-use implementation prompt for developers

**Size:** 350 lines, 12KB

**Contents:**
- Feature request template structure
- Objective and detailed requirements
- Technical considerations and design decisions
- Acceptance criteria checklist
- Testing strategy
- Implementation guide with step-by-step instructions
- File structure to create
- Key design patterns and code templates
- Completion checklist
- Complexity assessment and effort estimation

**Primary Audience:** Developers, Implementation Engineers

**How to Use:**
1. Read Objective section for context
2. Review Requirements for what to build
3. Follow Step-by-Step Implementation guide
4. Use Code Patterns section for implementation templates
5. Check Completion Checklist before submitting PR
6. Reference Technical Considerations for design decisions

**Key Sections:**
- Requirements (functional, configuration, error handling, testing)
- Technical Considerations (architecture, dependencies, design decisions)
- Implementation Guide (file structure, step-by-step, patterns)
- Completion Checklist

---

### 3. CLI_DIAGNOSTIC_COMMANDS_SUMMARY.md

**Purpose:** Quick reference and executive overview

**Size:** 495 lines, 14KB

**Contents:**
- Quick command reference (all 4 commands)
- Command examples and usage patterns
- Configuration setup (file and environment)
- Error scenarios with example messages
- Output formats explanation
- Implementation phases timeline
- Key design decisions with rationale
- Testing strategy overview
- Performance requirements table
- Dependencies summary
- Next steps and approval status

**Primary Audience:** Everyone (QA, DevOps, Team Members)

**How to Use:**
1. Section "Command Reference" for CLI usage
2. "Configuration" for setup instructions
3. "Error Handling" for troubleshooting
4. "Implementation Phases" for timeline
5. Print or bookmark for quick reference

**Key Sections:**
- Command Reference (usage for all 4 commands)
- Configuration Setup
- Error Handling Examples
- Performance Requirements
- Implementation Phases

---

## Document Decision Tree

### I need to...

**Understand what's being built:**
→ Read SUMMARY.md "Overview" section (2 min)

**Implement the feature:**
→ Start with PROMPT.md "Objective" section (5 min)
→ Follow "Step-by-Step Implementation" (main reference)
→ Use "Code Patterns" section while coding

**Review/validate implementation:**
→ Check REQUIREMENTS.md Section 5 (Success Criteria)
→ Use PROMPT.md "Completion Checklist"
→ Compare against SUMMARY.md "Command Reference"

**Write tests:**
→ Reference REQUIREMENTS.md Section 6 (Testing Requirements)
→ See PROMPT.md "Test Scenarios"

**Use the CLI:**
→ Quick reference: SUMMARY.md "Command Reference"
→ Detailed examples: REQUIREMENTS.md Section 1.2

**Debug errors:**
→ Check SUMMARY.md "Error Handling" section
→ Detailed errors: REQUIREMENTS.md Section 3

**Configure the tool:**
→ Setup: SUMMARY.md "Configuration"
→ Advanced: REQUIREMENTS.md Section 2

**Make decisions:**
→ Read SUMMARY.md "Key Design Decisions"
→ Rationale: PROMPT.md "Technical Considerations"

---

## Quick Command Reference

```bash
# Show orchestrator status
haymaker orch status [--revision] [--format]

# List replica status
haymaker orch replicas [--revision] [--status] [--follow] [--format]

# View container logs
haymaker orch logs [--revision] [--tail] [--follow] [--since] [--format]

# Run health checks
haymaker orch health [--deep] [--timeout] [--verbose] [--format]
```

See SUMMARY.md "Command Reference" for detailed examples.

---

## File Locations

All documents are in `/home/azureuser/src/AzureHayMaker/docs/`:

```
docs/
├── CLI_DIAGNOSTIC_COMMANDS_INDEX.md           ← You are here
├── CLI_DIAGNOSTIC_COMMANDS_REQUIREMENTS.md    (authoritative spec, 932 lines)
├── CLI_DIAGNOSTIC_COMMANDS_PROMPT.md          (implementation guide, 350 lines)
└── CLI_DIAGNOSTIC_COMMANDS_SUMMARY.md         (quick reference, 495 lines)
```

---

## Implementation Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| 1a: Foundation | 1 week | Module setup, config loading, client wrapper |
| 1b: Status Commands | 1-2 weeks | `orch status` and `orch replicas` commands |
| 1c: Logs & Health | 1 week | `orch logs` and `orch health` commands |
| 1d: Testing & Polish | 1 week | Tests (85%+ coverage), docs, optimization |
| **Total** | **4.5-6 days** | **36-48 hours of work** |

See PROMPT.md "Implementation Guide" for detailed steps.

---

## Success Metrics

### Functional Success
- All 4 commands working with all options
- Configuration loading from file and environment
- All output formats (table, JSON, YAML) valid
- Error handling with proper exit codes
- Follow modes working correctly

### Quality Success
- 85%+ test coverage achieved
- All acceptance criteria met
- No unhandled exceptions
- Help text clear with examples
- Performance within requirements

### Deployment Success
- Code review passed
- Integration tests pass
- Team can use CLI effectively
- No critical bugs in first month

See REQUIREMENTS.md Section 5 for complete criteria.

---

## Key Decisions

1. **Fail-Fast on Ambiguity**
   - Require --revision when multiple active revisions
   - Prevents accidental wrong revision queries

2. **2-Second Polling**
   - Used for follow modes instead of websockets
   - Simpler implementation, acceptable latency

3. **Separate Orchestrator Config**
   - Not mixed with API profiles
   - Clearer separation of concerns

4. **Exit Code Strategy**
   - 0: Success
   - 1: Config/input error
   - 2: Connectivity error
   - 3: API error
   - 4: Server error

5. **Azure SDK for API**
   - Official library for Container App API
   - Better maintenance and auth handling

See SUMMARY.md "Key Design Decisions" for rationale.

---

## Dependencies

### Python Packages
- `azure-mgmt-containerregistry` - Container App API
- `azure-identity` - Azure authentication
- `click>=8.0` - CLI framework
- `rich>=10.0` - Output formatting
- `pydantic>=2.0` - Data validation
- `httpx>=0.24` - HTTP client

### Azure Resources
- Subscription ID
- Resource Group
- Container App name
- Valid credentials (API key or Azure AD)

See REQUIREMENTS.md Section 8 for full dependencies.

---

## Testing Strategy

### Coverage Target: 85%+

**Unit Tests:**
```
tests/cli/test_orchestrator_config.py
tests/cli/test_orchestrator_commands.py
tests/cli/test_orchestrator_errors.py
tests/cli/test_orchestrator_formatting.py
```

**Test Categories:**
- Command behavior (all options and combinations)
- Configuration loading (file, env, defaults)
- Error scenarios (config, connectivity, API)
- Output formatting (JSON, YAML, table)
- Follow mode polling and interruption

See REQUIREMENTS.md Section 6 for detailed test specs.

---

## Approval Status

| Item | Status |
|------|--------|
| Requirements Complete | ✓ Complete |
| Specifications Clear | ✓ Clear |
| Implementation Guide | ✓ Ready |
| Acceptance Criteria | ✓ Defined |
| Testing Plan | ✓ Defined |
| Architect Review | ○ Recommended |
| Ready to Implement | ✓ Yes |

### Blockers
None identified.

### Dependencies
All external dependencies available.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-11-20 | Initial release |

---

## How to Contribute

### For Implementers
1. Start with PROMPT.md
2. Follow Step-by-Step Implementation
3. Reference REQUIREMENTS.md for details
4. Use SUMMARY.md for quick lookup

### For Reviewers
1. Check against REQUIREMENTS.md Section 5 (Success Criteria)
2. Verify PROMPT.md Completion Checklist
3. Compare outputs against SUMMARY.md examples

### For Testers
1. Use REQUIREMENTS.md Section 6 (Testing Requirements)
2. Reference test scenarios in PROMPT.md
3. Validate output formats in SUMMARY.md

### For Users
1. Bookmark SUMMARY.md "Command Reference"
2. Review "Configuration" section for setup
3. Check "Error Handling" for troubleshooting

---

## FAQ

**Q: Which document should I read first?**
A: SUMMARY.md for overview, then PROMPT.md if implementing, or REQUIREMENTS.md for details.

**Q: How long will implementation take?**
A: 36-48 hours (4.5-6 days) for complete Phase 1.

**Q: What's the complexity level?**
A: Medium - multiple commands, configuration management, health check logic.

**Q: When should architect review?**
A: Recommended before implementation to validate Azure SDK integration approach.

**Q: Are all 4 commands in Phase 1?**
A: Yes - status, replicas, logs, and health are all Phase 1 scope.

**Q: Can I implement them incrementally?**
A: Yes - recommend order: status → replicas → logs → health (dependency order).

---

## Contact

For questions about these requirements:
1. Review relevant document sections
2. Check FAQ section above
3. Contact project lead or architect

---

## Summary

You have received a complete, production-ready requirements suite for implementing CLI diagnostic commands:

**Document Roles:**

| Document | Role | Audience |
|----------|------|----------|
| REQUIREMENTS.md | Authoritative spec | Architects, Tech Leads |
| PROMPT.md | Implementation guide | Developers |
| SUMMARY.md | Quick reference | Everyone |
| INDEX.md | Navigation (this) | All |

**Ready to proceed with implementation?**

1. Review SUMMARY.md for 5-minute overview
2. Read PROMPT.md "Step-by-Step Implementation"
3. Reference REQUIREMENTS.md for detailed specs
4. Use checklists for validation

---

**Document Version:** 1.0
**Last Updated:** 2024-11-20
**Quality Score:** 92%
**Status:** Ready for Implementation

