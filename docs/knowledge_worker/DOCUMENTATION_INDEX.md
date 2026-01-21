# Knowledge Worker Documentation Index

Central index fer all knowledge worker agent documentation. This be created as part of Issue #287 to document the refactored agent modules.

## Quick Navigation

**Just want to use the agent?** → [API Quick Reference](./api_quick_reference.md)

**Want to understand the refactoring?** → [Agent Module Refactoring Guide](./agent_module_refactoring.md)

**Need module docstrings fer implementation?** → [Module Docstrings](./MODULE_DOCSTRINGS.md)

**Looking fer the source code README?** → [Agent Module README](../../src/azure_haymaker/knowledge_worker/agent/README.md)

## Documentation Files

### User-Facing Documentation

#### [API Quick Reference](./api_quick_reference.md)
**Type:** Reference (Diataxis)

**Use when:** Ye need quick access to API signatures and usage examples.

**Contents:**
- Import paths (old and new)
- All public APIs with signatures
- Usage examples fer each function
- Complete working examples
- Error handlin' guide
- Environment variables

#### [Agent Module Refactoring Guide](./agent_module_refactoring.md)
**Type:** Reference + Explanation (Diataxis)

**Use when:** Ye want to understand the new module structure or migrate code.

**Contents:**
- Module architecture overview
- Detailed documentation fer each module (config, core, m365_integration)
- Public APIs and contracts
- Backward compatibility information
- Migration guide
- Benefits of refactorin'
- Testing strategy

### Developer Documentation

#### [Module Docstrings](./MODULE_DOCSTRINGS.md)
**Type:** Reference (Diataxis)

**Use when:** Ye be implementin' the refactored modules and need docstring templates.

**Contents:**
- Complete module-level docstrings fer each file
- config.py docstring
- core.py docstring
- m365_integration.py docstring
- __init__.py facade docstring
- Usage examples in docstrings
- Standards and guidelines

#### [Agent Module README](../../src/azure_haymaker/knowledge_worker/agent/README.md)
**Type:** Tutorial + Reference (Diataxis)

**Use when:** Ye be workin' directly with the agent module source code.

**Contents:**
- Quick start guide
- Module responsibilities
- Dependency flow
- Usage examples
- Public APIs overview
- Testing information
- Philosophy alignment

#### [Knowledge Worker README](../../src/azure_haymaker/knowledge_worker/README.md)
**Type:** Tutorial + How-To (Diataxis)

**Use when:** Ye need comprehensive guide to the entire knowledge_worker module.

**Contents:**
- Overview of entire module
- Quick start fer basic usage
- Worker personas explanation
- M365 integration guide
- Communication safety
- Operations documentation
- Troubleshootin' guide
- References to refactored agent modules

## Documentation Structure

```
docs/knowledge_worker/
├── DOCUMENTATION_INDEX.md           # This file - central index
├── agent_module_refactoring.md      # Complete refactorin' guide
├── api_quick_reference.md           # Quick API reference
└── MODULE_DOCSTRINGS.md             # Docstring templates

src/azure_haymaker/knowledge_worker/
├── README.md                        # Module overview
└── agent/
    └── README.md                    # Agent modules quick start
```

## Documentation Philosophy

All documentation follows these principles:

### Eight Rules Compliance

1. ✅ **Location**: All docs in `docs/` directory
2. ✅ **Linking**: Every doc linked from this index
3. ✅ **Simplicity**: Plain language, minimal words
4. ✅ **Real Examples**: Runnable code, not placeholders
5. ✅ **Diataxis**: Each doc has clear type (tutorial/howto/reference/explanation)
6. ✅ **Scanability**: Descriptive headings, clear structure
7. ✅ **Local Links**: Relative paths with context
8. ✅ **Currency**: Created 2026-01-20, will be updated with code

### Diataxis Framework

| Document | Type | User Question | Structure |
|----------|------|--------------|-----------|
| API Quick Reference | Reference | "What's the signature?" | API listings with examples |
| Agent Module Refactoring | Reference + Explanation | "How is it structured?" | Architecture + rationale |
| Module Docstrings | Reference | "What goes in the docstring?" | Templates + standards |
| Agent README | Tutorial | "How do I use this?" | Quick start + examples |
| Knowledge Worker README | Tutorial + How-To | "How does it all work?" | Complete guide |

## Common Tasks

### I want to use the knowledge worker agent

1. Read [Knowledge Worker README](../../src/azure_haymaker/knowledge_worker/README.md)
2. Refer to [API Quick Reference](./api_quick_reference.md) fer specific APIs

### I want to understand the refactoring

1. Read [Agent Module Refactoring Guide](./agent_module_refactoring.md)
2. Review [Agent Module README](../../src/azure_haymaker/knowledge_worker/agent/README.md)

### I need to implement the refactored modules

1. Read [Module Docstrings](./MODULE_DOCSTRINGS.md) fer docstring templates
2. Follow [Agent Module Refactoring Guide](./agent_module_refactoring.md) fer specifications
3. Refer to [Agent Module README](../../src/azure_haymaker/knowledge_worker/agent/README.md) fer structure

### I need to migrate existing code

1. Check [Backward Compatibility](./agent_module_refactoring.md#backward-compatibility) section
2. Review [Migration Guide](./agent_module_refactoring.md#migration-guide)
3. Use [API Quick Reference](./api_quick_reference.md) fer new import paths

### I found a bug or want to contribute

1. Read [Knowledge Worker README](../../src/azure_haymaker/knowledge_worker/README.md) fer architecture
2. Check [Testing](./agent_module_refactoring.md#testing) section
3. Review module-specific READMEs fer implementation details

## Related Documentation

### Project-Wide Documentation

- [Bricks & Studs Pattern](../../.claude/context/PATTERNS.md#bricks--studs-module-design) - Philosophy behind the refactorin'
- [Zero-BS Implementation](../../.claude/context/PATTERNS.md#zero-bs-implementation) - Quality standards
- [PHILOSOPHY.md](../../.claude/context/PHILOSOPHY.md) - Development philosophy

### API Documentation

- KnowledgeWorkerConfig API (to be created)
- KnowledgeWorkerAgent API (to be created)
- M365 Operations API (to be created)

### Examples

- Basic agent usage (to be created)
- Email workflows (to be created)
- Calendar workflows (to be created)
- Multi-worker simulation (to be created)

## Version History

### v1.0.0 - 2026-01-20 (Issue #287)

**Created Documentation:**
- ✅ Agent Module Refactoring Guide
- ✅ API Quick Reference
- ✅ Module Docstrings
- ✅ Agent Module README
- ✅ Knowledge Worker README
- ✅ Documentation Index (this file)

**Refactoring:**
- Split agent.py (529 LOC) into 3 modules
- config.py (~85 LOC)
- core.py (~250 LOC)
- m365_integration.py (~193 LOC)
- Created facade fer backward compatibility

**Benefits:**
- Improved modularity
- Better testability
- Clearer responsibilities
- Maintained backward compatibility

## Feedback and Updates

This documentation be created through Document-Driven Development (DDD) where documentation be written BEFORE implementation. As the refactorin' progresses:

1. Documentation may be updated to match implementation details
2. Examples will be tested and verified
3. Edge cases will be documented as discovered
4. New sections may be added based on user feedback

If ye find any issues or have suggestions, please create an issue on GitHub.

---

**Created:** 2026-01-20
**Issue:** #287 (Refactor knowledge_worker agent modules)
**Pattern:** Bricks & Studs
**Status:** Retcon documentation (implementation pending)
