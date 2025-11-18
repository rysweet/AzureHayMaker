# Azure HayMaker - Requirements Clarification Document

**Date:** 2025-11-17
**Project:** Azure HayMaker
**Document Type:** Requirements Analysis and Clarification
**Status:** Draft for Review

---

## Executive Summary

This document clarifies and structures 5 user-requested changes to the Azure HayMaker project. Each requirement has been analyzed for clarity, dependencies, risks, and success criteria. The requirements range from Simple to Complex based on scope, cross-system impact, and implementation effort.

**Requirements Overview:**
1. Make Service Bus subscription creation idempotent (Simple - 2-4 hours)
2. Enable agent auto-execution on startup with monitoring (Medium - 1-2 days)
3. Display agent execution output (Simple - 2-3 hours)
4. Consolidate secret management using .env with proper .gitignore (Medium - 4-8 hours)
5. Create comprehensive presentation with PPTX skill (Complex - 1-2 days)

**Total Estimated Effort:** 3-5 days
**Interdependencies:** Requirements 1-4 should be completed before Requirement 5 (presentation needs working system)
**Critical Risks:** Secret management (Req 4) has security implications; must verify .gitignore coverage

---

## Requirement 1: Idempotent Service Bus Subscription Creation

### Type
Bug Fix / Infrastructure Enhancement

### Current State Problems

**Issue Description:**
The Azure HayMaker deployment pipeline fails when Service Bus subscriptions already exist. The Bicep template at `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/servicebus.bicep` creates a hardcoded subscription named "log-processor" without checking for existence.

**Error Behavior:**
- Deployment fails with resource already exists error
- Prevents re-deployments and updates
- Blocks GitOps automation flow
- No recovery mechanism available

**Current Code Location:**
- File: `infra/bicep/modules/servicebus.bicep` (lines 59-70)
- Resource: `logProcessingSubscription`
- Parent: `agentLogsTopic`

### Requirements

**Functional Requirements:**
1. Service Bus subscription creation must be idempotent
2. Deployment must succeed whether subscription exists or not
3. Existing subscription settings must not be modified unless explicitly changed in template
4. No manual cleanup required between deployments

**Non-Functional Requirements:**
- Deployment time increase less than 5 seconds
- No breaking changes to existing subscription behavior
- Maintain all current security and access controls

### Proposed Solution

**High-level Approach:**
Bicep templates are already idempotent by design. The issue likely stems from:
- Deployment validation failures (not actual resource creation)
- Parameter mismatches between existing and desired state
- Subscription naming conflicts

**Implementation Steps:**
1. Review existing Bicep template subscription properties
2. Verify deployment validation command in GitHub Actions workflow
3. Add conditional deployment logic if needed
4. Test with existing subscription present
5. Verify GitHub Actions pipeline completes successfully

**Files to Modify:**
- `infra/bicep/modules/servicebus.bicep` (review only, may not need changes)
- `.github/workflows/deploy-dev.yml` (validation step, lines 41-57)
- `.github/workflows/deploy-staging.yml` (if exists)
- `.github/workflows/deploy-prod.yml` (if exists)

### Acceptance Criteria

- [ ] Deploy infrastructure when Service Bus subscription does NOT exist - succeeds
- [ ] Deploy infrastructure when Service Bus subscription DOES exist - succeeds
- [ ] Re-deploy without changes - succeeds (no-op deployment)
- [ ] Re-deploy with property changes - applies changes correctly
- [ ] GitHub Actions workflow completes all stages without errors
- [ ] No manual cleanup steps required between deployments
- [ ] Unit test added to validate Bicep template idempotency
- [ ] Documentation updated with deployment behavior

### Testing Requirements

**Test Scenarios:**
1. Clean deployment (no resources exist)
2. Re-deployment (all resources exist)
3. Partial deployment (some resources exist)
4. Property change deployment (update existing subscription)

**Test Environment:** Dev environment (haymaker-dev-rg)

**Rollback Strategy:** Bicep deployments are declarative; previous state can be re-applied by re-running prior deployment

### Impact Assessment

- **Severity:** Medium (blocks re-deployments, but workaround exists: manual deletion)
- **Users Affected:** All developers and CI/CD pipeline
- **Workaround Available:** Yes (manual deletion via Azure Portal or CLI)
- **Data Loss Risk:** No

### Complexity Assessment

**Complexity:** Simple

**Justification:**
- Single file review/modification
- Bicep templates are inherently idempotent
- Likely configuration issue, not code change
- Clear test criteria
- Low risk of side effects

**Estimated Effort:** 2-4 hours

---

## Requirement 2: Enable Agent Auto-Execution on Startup

### Type
Feature Request

### Objective

Enable agents to automatically execute their scenarios when the Azure HayMaker orchestration service starts, rather than waiting for scheduled timer triggers. This allows for immediate testing and validation after deployment.

### Current State Problems

**Issue Description:**
Currently, agents only execute on timer triggers (4x daily). After deployment or service restart, there is no agent activity until the next scheduled execution. This creates delays in:
- Post-deployment validation
- Development testing cycles
- Troubleshooting and debugging

**Current Behavior:**
- Timer triggers defined in CRON schedule
- Orchestrator waits for next trigger
- No startup execution hook
- CLI requires manual scenario deployment (`haymaker deploy --scenario`)

**Code Locations:**
- Orchestrator: `src/azure_haymaker/orchestrator/` (need to identify startup trigger)
- Timer configuration: Likely in Function App host.json or function bindings
- Agent API: `src/azure_haymaker/orchestrator/agents_api.py`

### Requirements

**Functional Requirements:**
1. On orchestration service startup, automatically trigger agent selection and execution
2. Use the same scenario selection logic as scheduled executions
3. Execute configured number of agents based on SIMULATION_SIZE
4. Log startup execution separately from scheduled executions
5. Provide CLI command to monitor running agents
6. Display real-time execution status and logs

**Non-Functional Requirements:**
- Startup execution must not delay service availability
- Must be disableable via configuration flag (AUTO_RUN_ON_STARTUP=true/false)
- Execution monitoring must update at least every 30 seconds
- Log streaming should support tail and follow modes

### User Story

As a developer
I want agents to run automatically when the orchestrator starts
So that I can immediately validate deployments and see system behavior without waiting for scheduled triggers

### Proposed Solution

**High-level Approach:**
1. Add startup trigger to orchestration Durable Function
2. Create configuration flag AUTO_RUN_ON_STARTUP in .env
3. Implement startup activity that invokes existing orchestration workflow
4. Enhance CLI monitoring commands for real-time status display
5. Add continuous monitoring mode to CLI

**Implementation Steps:**
1. Review Azure Durable Functions startup patterns
2. Add application startup trigger to orchestrator
3. Create startup activity that calls existing scenario selection and execution
4. Add AUTO_RUN_ON_STARTUP environment variable to .env and .env.example
5. Update GitHub Actions to include new environment variable
6. Enhance `haymaker agents list` to show real-time status
7. Enhance `haymaker logs` to support continuous monitoring
8. Add tests for startup execution behavior

**Files to Create/Modify:**
- `src/azure_haymaker/orchestrator/startup_trigger.py` (new)
- `src/azure_haymaker/orchestrator/agents_api.py` (enhance monitoring)
- `.env.example` (add AUTO_RUN_ON_STARTUP)
- `.env` (add AUTO_RUN_ON_STARTUP=true)
- `.github/workflows/deploy-dev.yml` (add environment variable)
- `cli/src/haymaker_cli/main.py` (enhance monitoring commands)
- `cli/src/haymaker_cli/client.py` (add polling support)

### Acceptance Criteria

- [ ] Orchestrator automatically triggers agent execution on startup when AUTO_RUN_ON_STARTUP=true
- [ ] Orchestrator skips startup execution when AUTO_RUN_ON_STARTUP=false
- [ ] Startup execution uses same scenario selection logic as scheduled runs
- [ ] Startup execution respects SIMULATION_SIZE configuration
- [ ] Startup logs tagged with execution_type: "startup" vs "scheduled"
- [ ] CLI command `haymaker agents list` shows running agents with status
- [ ] CLI command `haymaker agents list --status running` filters correctly
- [ ] CLI command `haymaker logs --agent-id <id> --follow` streams logs in real-time
- [ ] Monitoring updates at least every 30 seconds
- [ ] Documentation updated with startup behavior and monitoring commands
- [ ] Unit tests added for startup trigger logic
- [ ] Integration tests verify end-to-end startup execution

### Technical Considerations

**Architecture Impacts:**
- Adds new trigger type to Durable Functions orchestrator
- May increase cold start time by 5-15 seconds
- Requires CLI to poll APIs for real-time updates

**Dependencies:**
- Azure Durable Functions framework supports startup triggers
- Service Bus subscriptions must exist (Requirement 1)
- Agents API must return real-time status

**Integration Points:**
- Orchestrator startup → scenario selection activity
- CLI → Agents API (polling)
- Service Bus → log streaming

### Testing Requirements

**Test Scenarios:**
1. Startup with AUTO_RUN_ON_STARTUP=true → agents execute
2. Startup with AUTO_RUN_ON_STARTUP=false → no execution
3. Startup with SIMULATION_SIZE=small → correct number of agents
4. Monitor running agents via CLI → status updates shown
5. Follow logs via CLI → new logs appear in real-time
6. Service restart during execution → no duplicate executions

**Test Environment:** Dev environment

**Rollback Strategy:** Set AUTO_RUN_ON_STARTUP=false and restart service

### Complexity Assessment

**Complexity:** Medium

**Justification:**
- Multiple file modifications (6-8 files)
- New trigger type requires understanding Durable Functions patterns
- CLI enhancements for monitoring and streaming
- Integration testing across orchestrator and CLI
- Configuration management in multiple places
- Moderate risk of execution conflicts with scheduled runs

**Estimated Effort:** 1-2 days

---

## Requirement 3: Show Agent Execution Output

### Type
Feature Request / Enhancement

### Objective

Provide immediate visibility into agent execution output through the CLI, allowing users to see what agents are doing in real-time.

### Current State Problems

**Issue Description:**
The user requested to "show me the output" but there is no clear mechanism to view agent execution output. The current system has:
- Agents API that returns agent status (src/azure_haymaker/orchestrator/agents_api.py)
- Log endpoint that returns empty results (lines 309-316: placeholder implementation)
- CLI logs command that attempts to retrieve logs but gets no data

**Current Limitations:**
- Log storage not implemented (line 306 comment: "logs should be queried from Log Analytics or Cosmos DB")
- Service Bus topic exists but no historical log storage
- CLI can poll but gets empty responses

### Requirements

**Functional Requirements:**
1. Display real-time agent execution output via CLI
2. Show agent stdout/stderr streams
3. Display structured log entries (timestamp, level, message, agent_id)
4. Support tail mode (last N entries) and follow mode (continuous streaming)
5. Filter logs by agent ID
6. Persist logs to queryable storage (Log Analytics or Cosmos DB)

**Non-Functional Requirements:**
- Logs available within 30 seconds of generation
- Support at least 7 days of log retention
- Handle high-volume logging (up to 1000 events/minute per agent)
- CLI output formatted clearly with syntax highlighting

### User Story

As a developer
I want to see the execution output from running agents
So that I can monitor progress, debug issues, and verify correct behavior

### Proposed Solution

**High-level Approach:**
1. Implement dual-write pattern: Service Bus (real-time) + Cosmos DB (historical)
2. Update agents_api.py to query Cosmos DB for historical logs
3. Enhance CLI formatters to display logs with rich formatting
4. Add real-time streaming via Service Bus subscription polling

**Implementation Steps:**
1. Create Cosmos DB container for logs (if not exists)
2. Update agent execution to write logs to both Service Bus and Cosmos DB
3. Implement query_logs_from_cosmosdb function in agents_api.py
4. Update get_agent_logs endpoint to query Cosmos DB
5. Enhance CLI format_log_entries to display rich formatted output
6. Add real-time polling for follow mode in CLI
7. Add integration tests for log storage and retrieval

**Files to Modify:**
- `src/azure_haymaker/orchestrator/agents_api.py` (lines 115-150, implement log querying)
- `src/azure_haymaker/orchestrator/event_bus.py` (add Cosmos DB dual-write)
- `infra/bicep/modules/cosmosdb.bicep` (verify logs container exists)
- `cli/src/haymaker_cli/formatters.py` (enhance format_log_entries)
- `cli/src/haymaker_cli/client.py` (ensure polling works)

### Acceptance Criteria

- [ ] Agent execution logs stored in Cosmos DB with schema (timestamp, level, message, agent_id, scenario, run_id)
- [ ] CLI command `haymaker logs --agent-id <id>` displays last 100 log entries by default
- [ ] CLI command `haymaker logs --agent-id <id> --tail 50` displays last 50 entries
- [ ] CLI command `haymaker logs --agent-id <id> --follow` streams new logs in real-time
- [ ] Logs formatted with rich syntax highlighting (colors, timestamps, levels)
- [ ] Logs include all stdout/stderr from agent execution
- [ ] Logs queryable via API endpoint GET /api/v1/agents/{agent_id}/logs
- [ ] Log retention policy set to 7 days minimum
- [ ] Integration test verifies end-to-end log flow (write → store → retrieve)
- [ ] Documentation updated with log querying examples

### Technical Considerations

**Architecture Impacts:**
- Adds Cosmos DB query dependency to agents API
- Increases Cosmos DB RU consumption
- Dual-write pattern requires error handling for partial failures

**Dependencies:**
- Cosmos DB container for logs (may need to add to Bicep)
- Service Bus subscription active (Requirement 1)
- Agents must be instrumented to publish logs

**Integration Points:**
- Agent container → Service Bus → Event Bus client
- Event Bus client → Cosmos DB (dual-write)
- Agents API → Cosmos DB (query)
- CLI → Agents API → User display

### Testing Requirements

**Test Scenarios:**
1. Agent executes and generates logs → logs appear in Cosmos DB
2. Query logs via API → returns correct entries
3. CLI tail mode → displays last N entries
4. CLI follow mode → streams new entries as they arrive
5. Multiple agents running → logs correctly filtered by agent_id
6. Log retention after 7 days → old logs removed

**Test Environment:** Dev environment

**Rollback Strategy:** Remove Cosmos DB query logic, revert to placeholder response

### Complexity Assessment

**Complexity:** Simple

**Justification:**
- Implementation already scaffolded in agents_api.py
- Cosmos DB likely already configured
- CLI formatters already exist
- Clear technical pattern (dual-write + query)
- Limited scope (3-4 files)
- Low risk

**Estimated Effort:** 2-3 hours

---

## Requirement 4: Consolidate Secret Management with .env

### Type
Refactoring / Security Enhancement

### Objective

Simplify and consolidate secret management by using .env as the single source of truth for local development, ensuring all secret files are properly .gitignored to prevent accidental commits.

### Current State Problems

**Issue Description:**
User concern: "we should not store the secret in multiple places - I thought we were using .env?"

**Current State Analysis:**
Based on code review:
1. `.env` file exists with secrets (AZURE_CLIENT_SECRET, ANTHROPIC_API_KEY) - line 11, 14 of .env
2. `.env.example` has placeholders but mentions secrets "would normally come from Key Vault" (lines 44-49)
3. README.md describes configuration priority: ENV vars → Key Vault → .env (lines 47-51)
4. GitHub Actions injects secrets directly to Function App as environment variables (deploy-dev.yml lines 195-203)
5. `.gitignore` already includes .env patterns (line 52: `.env`, line 53-54: `.env.local`, `.env.*.local`)

**Problem Areas:**
- Confusion about whether to use .env vs Key Vault
- Secrets in GitHub Secrets (MAIN_SP_CLIENT_SECRET, ANTHROPIC_API_KEY) separate from .env
- No clear guidance on local vs production secret sources
- .env file contains real secrets (should not be in repo, but git status shows it as modified)

### Requirements

**Functional Requirements:**
1. Use .env as the single source for all secrets in local development
2. Use Azure Key Vault as the single source for all secrets in production (Azure Function App)
3. Remove GitHub Secrets injection directly to Function App environment variables
4. Instead, store secrets in Key Vault and have Function App read from Key Vault
5. Ensure all local secret files (.env, .env.local, .env.*.local, etc.) are in .gitignore
6. Verify .env file not tracked by git (or remove from tracking if present)
7. Document clear secret management strategy for local vs production

**Non-Functional Requirements:**
- No secret exposure in git history
- No secrets in GitHub Actions logs
- Deployment process remains simple for users
- Local development experience not complicated
- Production security maintained or improved

### User Story

As a developer
I want a simple, single place to manage secrets locally
So that I don't have to configure secrets in multiple locations and risk exposure

As a DevOps engineer
I want production secrets managed in Key Vault
So that secrets are secure, auditable, and rotatable

### Proposed Solution

**High-level Approach:**

**For Local Development:**
1. Use .env file exclusively (already working)
2. Document that .env is for local dev only
3. Ensure .env is properly .gitignored (already is)
4. Remove .env from git tracking if present

**For Production (Azure Function App):**
1. Store secrets in Azure Key Vault (infrastructure already deployed)
2. Update Function App to use Key Vault references instead of direct environment variables
3. Remove direct secret injection from GitHub Actions (lines 195-198 of deploy-dev.yml)
4. Add Key Vault secret creation step to GitHub Actions
5. Configure Function App with Key Vault references using format: `@Microsoft.KeyVault(SecretUri=...)`

**Implementation Steps:**

1. **Verify .env not in git tracking:**
   ```bash
   git rm --cached .env
   git commit -m "Remove .env from git tracking"
   ```

2. **Audit .gitignore coverage:**
   - Verify all .env patterns covered
   - Add any missing patterns

3. **Update GitHub Actions deploy workflow:**
   - Add step to create/update Key Vault secrets
   - Remove direct Function App appsettings injection
   - Add Key Vault reference configuration

4. **Update .env.example:**
   - Clarify local dev usage
   - Remove confusing Key Vault comments

5. **Update README.md:**
   - Simplify configuration priority: .env (local only), Key Vault (production only)
   - Remove environment variable override option (complicates mental model)

6. **Update Function App configuration code:**
   - Ensure config.py reads from environment variables
   - Environment variables populated from Key Vault references automatically

**Files to Modify:**
- `.gitignore` (verify coverage)
- `.env.example` (clarify usage)
- `README.md` (simplify configuration documentation)
- `.github/workflows/deploy-dev.yml` (add Key Vault secret creation, remove direct injection)
- `.github/workflows/deploy-staging.yml` (same changes)
- `.github/workflows/deploy-prod.yml` (same changes)
- `src/azure_haymaker/config.py` (verify Key Vault reference support)

**Files to Check/Remove from Git:**
- `.env` (if tracked, remove from git)

### Acceptance Criteria

- [ ] `.env` file not tracked by git (not in `git status`)
- [ ] `.env` file in .gitignore (verified)
- [ ] `.env.example` clearly documents local development usage only
- [ ] README.md configuration section simplified: .env (local) vs Key Vault (production)
- [ ] GitHub Actions creates/updates Key Vault secrets before Function App deployment
- [ ] GitHub Actions configures Function App with Key Vault references (format: `@Microsoft.KeyVault(SecretUri=...)`)
- [ ] GitHub Actions does NOT inject secrets as direct environment variables
- [ ] Function App successfully reads secrets from Key Vault in dev environment
- [ ] Local development continues to work with .env file
- [ ] No secrets visible in GitHub Actions logs
- [ ] Documentation includes secret rotation instructions
- [ ] All team members can deploy without manual secret configuration

### Technical Considerations

**Architecture Impacts:**
- Function App configuration changes from direct env vars to Key Vault references
- Adds Key Vault as runtime dependency for Function App
- Requires Managed Identity for Function App (likely already configured)

**Dependencies:**
- Key Vault deployed (already in infra/bicep/modules/keyvault.bicep)
- Function App Managed Identity enabled (likely already done)
- RBAC: Function App identity has "Key Vault Secrets User" role (need to verify)

**Integration Points:**
- GitHub Actions → Key Vault (create/update secrets)
- GitHub Actions → Function App (configure Key Vault references)
- Function App → Key Vault (read secrets at runtime)

**Security Considerations:**
- Key Vault secrets must be created via GitHub Actions using OIDC authentication
- No secrets in GitHub Actions logs (use add-mask)
- Key Vault access policies or RBAC must be configured correctly
- Secret rotation must not break running Function App

### Testing Requirements

**Test Scenarios:**
1. Local development with .env file → secrets loaded correctly
2. Deploy to dev environment → Function App reads secrets from Key Vault
3. Update secret in Key Vault → Function App uses new value (may require restart)
4. New developer setup → follows .env.example, no manual Key Vault configuration needed
5. Git status check → .env file not shown as tracked
6. Review GitHub Actions logs → no secrets exposed

**Test Environment:**
- Local: developer machine
- Dev: haymaker-dev-rg

**Rollback Strategy:**
- Revert GitHub Actions workflow to direct secret injection
- Function App continues working immediately

### Complexity Assessment

**Complexity:** Medium

**Justification:**
- Multiple workflow files to modify (3x GitHub Actions files)
- Key Vault reference configuration requires Azure-specific knowledge
- RBAC configuration verification needed
- Testing across local and production environments
- Security implications require careful validation
- Documentation updates across multiple files
- Moderate risk of breaking production deployments if misconfigured

**Estimated Effort:** 4-8 hours

---

## Requirement 5: Create Comprehensive Presentation

### Type
Documentation / Deliverable

### Objective

Create a professional, comprehensive PowerPoint presentation that provides an overview of Azure HayMaker architecture, deployment process, CLI usage, and real agent execution examples.

### Requirements

**Functional Requirements:**

**Presentation must include 4 main sections:**

**A) Overview & Architecture (8-12 slides):**
1. Cover slide with hay farm image
2. What is Azure HayMaker (problem statement)
3. Key features and benefits
4. High-level architecture diagram
5. Component breakdown:
   - Orchestrator (Durable Functions)
   - Agent execution layer (Container Apps)
   - Service Bus event system
   - Supporting infrastructure
6. Technology stack
7. Security model (SPs, RBAC, Key Vault)
8. Execution flow (timer trigger → orchestration → agents → cleanup)

**B) Deployment Guide (6-8 slides):**
1. Prerequisites (Azure subscription, GitHub, tools)
2. GitOps workflow overview
3. GitHub Actions pipeline stages
4. Bicep infrastructure-as-code
5. Environment configuration (dev, staging, prod)
6. Secret management (Key Vault references)
7. Deployment verification steps
8. Troubleshooting common issues

**C) CLI Usage Guide (6-8 slides):**
1. Installation and setup
2. Configuration (profiles, endpoints)
3. Core commands with examples:
   - `haymaker status`
   - `haymaker agents list`
   - `haymaker logs --agent-id <id> --follow`
   - `haymaker deploy --scenario <name> --wait`
   - `haymaker resources list`
   - `haymaker cleanup`
4. Real command output examples (screenshots or formatted text)
5. Advanced usage patterns

**D) Real Agent Execution Demo (4-6 slides):**
1. Select a real scenario (e.g., "compute-01-linux-vm-web-server")
2. Show deployment command
3. Show agent execution logs (real output from Azure)
4. Show resources created in Azure Portal (screenshots)
5. Show cleanup process and verification
6. Metrics and observability dashboard

**Non-Functional Requirements:**
- Professional design with consistent branding
- Clear, readable fonts (minimum 18pt for body text)
- Diagrams must be high-quality and legible
- Code examples with proper syntax highlighting
- Screenshots must be high-resolution
- Total slides: 25-35
- Cover slide must have hay farm image

### User Story

As a stakeholder
I want a comprehensive presentation explaining Azure HayMaker
So that I can understand the architecture, deployment process, and usage without reading code

As a developer
I want to see real examples of agent execution
So that I can understand how the system works in practice

### Proposed Solution

**High-level Approach:**
1. Use PPTX skill to create presentation programmatically
2. Generate hay farm image for cover slide (use image generation or find open-source image)
3. Extract architecture diagrams from specs/architecture.md
4. Use real CLI command outputs from running system
5. Capture screenshots from Azure Portal showing deployed resources
6. Include real agent execution logs from dev environment

**Implementation Steps:**

**Preparation:**
1. Ensure Requirements 1-4 completed (working system needed for real examples)
2. Deploy to dev environment
3. Trigger agent execution (Requirement 2)
4. Capture CLI outputs and screenshots
5. Find or generate hay farm image

**Content Creation:**
1. Create slide structure outline
2. Write slide content for each section
3. Generate/source diagrams (architecture from specs/architecture.md)
4. Format code examples with syntax highlighting
5. Add real CLI outputs
6. Add Azure Portal screenshots

**Presentation Generation:**
1. Invoke PPTX skill to create presentation
2. Add cover slide with hay farm image
3. Add content slides with text, diagrams, code, images
4. Apply consistent formatting and layout
5. Review and refine

**Files to Reference:**
- `specs/architecture.md` (architecture diagrams and descriptions)
- `README.md` (quick start guide)
- `docs/architecture/orchestrator.md` (orchestrator details)
- `cli/src/haymaker_cli/main.py` (CLI commands and examples)
- `.github/workflows/deploy-dev.yml` (GitOps deployment process)
- Real execution outputs from dev environment

**Output File:**
- `docs/presentations/Azure_HayMaker_Overview.pptx`

### Acceptance Criteria

- [ ] Presentation created with 25-35 slides
- [ ] Cover slide includes hay farm image (haystack on farm)
- [ ] Section A: Overview & Architecture (8-12 slides) with clear architecture diagrams
- [ ] Section B: Deployment Guide (6-8 slides) with GitOps workflow and GitHub Actions stages
- [ ] Section C: CLI Usage Guide (6-8 slides) with real command examples and outputs
- [ ] Section D: Real Agent Execution Demo (4-6 slides) with actual Azure execution logs and screenshots
- [ ] All code examples properly formatted with syntax highlighting
- [ ] All screenshots high-resolution and readable
- [ ] Diagrams clear and professional
- [ ] Consistent design and branding throughout
- [ ] No placeholder content (all real examples)
- [ ] Presentation opens and displays correctly in PowerPoint
- [ ] File saved to `docs/presentations/Azure_HayMaker_Overview.pptx`

### Technical Considerations

**Architecture Impacts:**
- None (documentation only)

**Dependencies:**
- PPTX skill available and functional
- Requirements 1-4 completed for real examples
- Dev environment deployed and agents executing
- Access to Azure Portal for screenshots
- Hay farm image sourced (open-source or generated)

**Integration Points:**
- PPTX skill for presentation creation
- Architecture documentation (specs/)
- CLI for command outputs
- Azure Portal for resource screenshots

### Testing Requirements

**Test Scenarios:**
1. Open presentation in PowerPoint → displays correctly
2. Navigate through slides → all content visible and formatted
3. Review images → high resolution and clear
4. Review code examples → syntax highlighting correct
5. Verify real examples → match actual system behavior

**Test Environment:**
- Local machine with PowerPoint installed
- Dev environment for real examples

**Rollback Strategy:** N/A (documentation deliverable)

### Complexity Assessment

**Complexity:** Complex

**Justification:**
- Requires working system (dependencies on Requirements 1-4)
- Needs real agent execution examples from Azure
- Requires screenshots from Azure Portal
- Large scope (25-35 slides with 4 major sections)
- Content creation + technical writing + design
- Multiple source documents to synthesize
- Image sourcing/generation for cover
- Quality review and refinement
- PPTX skill usage may require iteration

**Estimated Effort:** 1-2 days

---

## Dependencies and Execution Order

### Dependency Graph

```
Requirement 1 (Service Bus Idempotency)
    ↓
Requirement 2 (Agent Auto-Execution) ← depends on working Service Bus
    ↓
Requirement 3 (Show Output) ← depends on agents running
    ↓
Requirement 4 (Secret Management) ← independent, but should be done before final demo
    ↓
Requirement 5 (Presentation) ← depends on all above for real examples
```

### Recommended Execution Order

1. **Phase 1: Infrastructure Fixes (Parallel)**
   - Requirement 1: Service Bus idempotency (2-4 hours)
   - Requirement 4: Secret management (4-8 hours)
   - Total: 1 day (can overlap)

2. **Phase 2: Agent Execution (Sequential)**
   - Requirement 2: Auto-execution on startup (1-2 days)
   - Requirement 3: Show output (2-3 hours)
   - Total: 1-2 days

3. **Phase 3: Documentation (Sequential)**
   - Requirement 5: Create presentation (1-2 days)
   - Total: 1-2 days

**Total Project Duration:** 3-5 days

### Critical Path

The critical path is:
1. Req 1 (Service Bus) → 2. Req 2 (Auto-execution) → 3. Req 3 (Output) → 4. Req 5 (Presentation)

Requirement 4 (Secret Management) is on a separate path and can be done in parallel with other work, but should be completed before the final presentation demo.

---

## Risk Assessment

### High-Risk Items

**Requirement 4: Secret Management**
- **Risk:** Misconfiguration could break production deployments
- **Likelihood:** Medium
- **Impact:** High (production outage)
- **Mitigation:**
  - Test thoroughly in dev environment first
  - Maintain rollback capability (direct secret injection)
  - Document rollback procedure
  - Verify RBAC before production deployment

**Requirement 5: Presentation**
- **Risk:** Dependencies on Requirements 1-4 may cause delays
- **Likelihood:** Medium
- **Impact:** Medium (presentation incomplete or using mock data)
- **Mitigation:**
  - Start content outline early
  - Use dev environment for real examples (not prod)
  - Have backup plan with architecture diagrams only if agents not running

### Medium-Risk Items

**Requirement 2: Auto-Execution**
- **Risk:** Startup execution conflicts with scheduled runs
- **Likelihood:** Low
- **Impact:** Medium (duplicate agent execution, resource waste)
- **Mitigation:**
  - Add execution_type tracking
  - Implement execution locking/deduplication
  - Make feature optional via AUTO_RUN_ON_STARTUP flag

**Requirement 1: Service Bus Idempotency**
- **Risk:** Deployment validation may have other underlying issues
- **Likelihood:** Low
- **Impact:** Low (manual workaround exists)
- **Mitigation:**
  - Test with multiple deployment scenarios
  - Document workaround if issue persists

### Low-Risk Items

**Requirement 3: Show Output**
- **Risk:** Cosmos DB query performance issues with high log volume
- **Likelihood:** Low
- **Impact:** Low (slow CLI response, but functional)
- **Mitigation:**
  - Implement pagination
  - Add query time limits
  - Consider Log Analytics for large-scale queries

---

## Security Considerations

### Requirement 4: Secret Management (Critical)

**Security Enhancements:**
1. Secrets stored in Key Vault (production) vs .env (local only)
2. No secrets in GitHub Actions logs (use add-mask)
3. No secrets in git repository
4. RBAC-based access to Key Vault
5. Managed Identity for Function App (no stored credentials)

**Security Risks to Mitigate:**
1. .env file committed to git (verify .gitignore)
2. Key Vault secrets readable by unauthorized users (verify RBAC)
3. Function App can't access Key Vault (verify Managed Identity role)
4. Secrets in GitHub Actions logs (use add-mask for all secret values)

### All Requirements

**General Security Checks:**
- No secrets in code changes
- No secrets in commit messages
- No secrets in PR descriptions
- RBAC validated for all new Azure resource access
- Managed Identity used wherever possible

---

## Success Metrics

### Requirement 1: Service Bus Idempotency
- **Metric:** Deployment success rate
- **Target:** 100% success rate for re-deployments
- **Measurement:** GitHub Actions pipeline completion status

### Requirement 2: Agent Auto-Execution
- **Metric:** Time to first agent execution after deployment
- **Target:** Less than 60 seconds
- **Measurement:** Time from deployment completion to first agent log entry

### Requirement 3: Show Output
- **Metric:** Log availability latency
- **Target:** Logs available within 30 seconds of generation
- **Measurement:** Time from agent log emission to CLI display

### Requirement 4: Secret Management
- **Metric:** Configuration complexity score
- **Target:** Single source of truth (1 location per environment)
- **Measurement:** Number of places secrets must be configured

### Requirement 5: Presentation
- **Metric:** Completeness score
- **Target:** 100% of required sections present with real examples
- **Measurement:** Checklist of acceptance criteria

---

## Documentation Updates Required

### Files to Update

1. **README.md**
   - Update configuration section (Req 4)
   - Add startup execution documentation (Req 2)
   - Add CLI monitoring examples (Req 2, 3)

2. **.env.example**
   - Add AUTO_RUN_ON_STARTUP (Req 2)
   - Clarify local development usage (Req 4)
   - Remove confusing Key Vault comments (Req 4)

3. **specs/architecture.md**
   - Document startup trigger behavior (Req 2)
   - Document log storage architecture (Req 3)
   - Update secret management section (Req 4)

4. **New Documentation**
   - Create CLI usage guide (reference for Req 5)
   - Create deployment troubleshooting guide
   - Create secret rotation guide (Req 4)

---

## Open Questions

### Requirement 1: Service Bus Idempotency
1. Is this actually a Bicep idempotency issue, or a validation command issue?
2. Are there error logs from failed deployments we can review?

### Requirement 2: Agent Auto-Execution
1. Should startup execution use a different SIMULATION_SIZE, or same as scheduled?
2. Should startup execution be visible in metrics dashboard separately?
3. What happens if service restarts during scheduled execution? (conflict handling)

### Requirement 3: Show Output
1. Should logs be stored in Cosmos DB or Log Analytics? (Cosmos DB chosen for consistency)
2. What is the expected log volume per agent? (affects storage costs)
3. Should we implement log aggregation/sampling for high-volume scenarios?

### Requirement 4: Secret Management
1. Do we need secret rotation automation, or manual rotation is acceptable?
2. Should local development support Key Vault as an option, or .env only?
3. What is the process for onboarding new team members? (affects documentation)

### Requirement 5: Presentation
1. What is the target audience? (technical developers, management, mixed?)
2. Is the presentation for internal use or external stakeholders?
3. Should we include cost analysis slides?
4. Should we include disaster recovery / business continuity slides?

---

## Next Steps

### Immediate Actions (Before Implementation)

1. **User Confirmation**
   - Review this requirements document with stakeholder
   - Confirm understanding and priorities
   - Get answers to open questions

2. **Environment Preparation**
   - Verify dev environment deployed and accessible
   - Verify access to Azure Portal for screenshots
   - Verify PPTX skill available

3. **Planning**
   - Create detailed task breakdown for each requirement
   - Assign priorities (all High priority)
   - Schedule implementation phases

### Implementation Phases

**Phase 1: Infrastructure Fixes (Day 1)**
- Morning: Implement Requirement 1 (Service Bus)
- Afternoon: Start Requirement 4 (Secret Management)

**Phase 2: Agent Features (Day 2-3)**
- Day 2: Complete Requirement 4 (Secret Management)
- Day 2: Implement Requirement 2 (Auto-Execution)
- Day 3: Implement Requirement 3 (Show Output)

**Phase 3: Documentation (Day 4-5)**
- Day 4: Start Requirement 5 (Presentation outline and content)
- Day 5: Complete Requirement 5 (Presentation creation and refinement)

### Definition of Done

Each requirement is considered done when:
- All acceptance criteria met
- Tests passing
- Code reviewed (if applicable)
- Documentation updated
- Deployed to dev environment
- Verified working end-to-end

---

## Appendix A: Configuration Files Summary

### Current Configuration Sources

**Local Development:**
- `.env` - secrets and configuration (NOT in git)
- `.env.example` - template (in git)

**Production (Azure Function App):**
- Environment variables (currently injected by GitHub Actions)
- Proposed: Key Vault references

**GitHub Actions:**
- GitHub Secrets (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, ANTHROPIC_API_KEY, etc.)
- Used during deployment pipeline

### Proposed Configuration Sources (After Requirement 4)

**Local Development:**
- `.env` ONLY - all secrets and configuration (NOT in git)

**Production (Azure Function App):**
- Key Vault references ONLY - all secrets
- Environment variables for non-secret config (SIMULATION_SIZE, etc.)

**GitHub Actions:**
- GitHub Secrets for deployment authentication (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID)
- GitHub Secrets for secret values to inject into Key Vault (MAIN_SP_CLIENT_SECRET, ANTHROPIC_API_KEY)
- No direct injection to Function App

---

## Appendix B: CLI Commands Reference

### Current CLI Commands (from cli/src/haymaker_cli/main.py)

```bash
# Status
haymaker status
haymaker status --format json

# Metrics
haymaker metrics
haymaker metrics --period 30d
haymaker metrics --scenario compute-01

# Agents
haymaker agents list
haymaker agents list --status running
haymaker agents list --limit 50

# Logs
haymaker logs --agent-id agent-123
haymaker logs --agent-id agent-123 --tail 50
haymaker logs --agent-id agent-123 --follow

# Resources
haymaker resources list
haymaker resources list --scenario compute-01
haymaker resources list --group-by type

# Cleanup
haymaker cleanup --dry-run
haymaker cleanup --execution-id exec-123
haymaker cleanup --scenario compute-01

# Deploy
haymaker deploy --scenario compute-01-linux-vm-web-server
haymaker deploy --scenario compute-01 --wait

# Config
haymaker config set endpoint https://haymaker.azurewebsites.net
haymaker config get endpoint
haymaker config list
```

### Proposed Enhancements (Requirements 2 & 3)

No new commands needed - existing commands enhanced with:
- Real-time monitoring support
- Log streaming support
- Improved output formatting

---

## Appendix C: File Locations Quick Reference

### Key Files by Requirement

**Requirement 1: Service Bus Idempotency**
- `infra/bicep/modules/servicebus.bicep`
- `.github/workflows/deploy-dev.yml`

**Requirement 2: Agent Auto-Execution**
- `src/azure_haymaker/orchestrator/` (new startup_trigger.py)
- `src/azure_haymaker/orchestrator/agents_api.py`
- `cli/src/haymaker_cli/main.py`
- `.env.example`

**Requirement 3: Show Output**
- `src/azure_haymaker/orchestrator/agents_api.py`
- `src/azure_haymaker/orchestrator/event_bus.py`
- `cli/src/haymaker_cli/formatters.py`

**Requirement 4: Secret Management**
- `.env` (verify not tracked)
- `.env.example`
- `.gitignore`
- `README.md`
- `.github/workflows/deploy-dev.yml`
- `.github/workflows/deploy-staging.yml`
- `.github/workflows/deploy-prod.yml`

**Requirement 5: Presentation**
- Output: `docs/presentations/Azure_HayMaker_Overview.pptx`
- References: `specs/architecture.md`, `README.md`, `docs/architecture/orchestrator.md`

---

**Document End**

This requirements clarification document is ready for review and approval before implementation begins.
