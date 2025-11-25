# Shared Agent Library

This directory contains canonical versions of reusable agents that are referenced by multiple Azure scenario agents.

## Purpose

Instead of duplicating agent definitions across 49 different Azure agents, we maintain single source of truth versions here. Individual agents reference these shared definitions via `agents.json` configuration files.

## Benefits

- **DRY Principle**: Don't Repeat Yourself - one copy, not 43
- **Consistency**: All agents use identical definitions
- **Maintainability**: Update once, applies everywhere
- **Reduced Size**: ~29,000 lines eliminated from duplication

## Shared Agents

### documenter.md (knowledge-archaeologist)
Deep research and knowledge excavation specialist. Uncovers hidden patterns, historical context, and buried insights from codebases.

**Used by**: 43 Azure agents
**Size**: ~288 lines

### tester.md (amplihack-improvement-workflow)
Improvement workflow agent with progressive validation. Enforces simplicity-first design for amplihack project improvements.

**Used by**: 37 Azure agents
**Size**: ~366 lines

### monitor.md (xpia-defense)
Cross-Prompt Injection Attack defense specialist. Provides transparent AI security protection with sub-100ms processing.

**Used by**: 6 Azure agents
**Size**: ~147 lines

### data-processor.md (prompt-writer)
Prompt engineering specialist who transforms requirements into clear, actionable prompts with built-in quality assurance.

**Used by**: 6 Azure agents
**Size**: ~433 lines

## Usage

Azure agents reference these shared definitions in their `.claude/agents.json` files:

```json
{
  "shared_agents": [
    {"name": "documenter", "path": "../../../_shared/documenter.md"},
    {"name": "tester", "path": "../../../_shared/tester.md"}
  ]
}
```

## Consolidation Metrics

- **Before**: ~29,000 lines duplicated across 92 files
- **After**: ~1,234 lines in 4 shared files
- **Reduction**: ~27,766 lines (95.7% reduction)

## Related

- GitHub Issue #54: Consolidate duplicate agent definitions
- Fix Branch: `fix/issue-54-duplicate-agents`
