# Azure HayMaker - Structured Requirements Document

## Project Overview

**Objective**: Build a production-ready orchestration service that generates benign telemetry to simulate ordinary Azure tenant operations using multiple service principals executing diverse administrative scenarios.

**Key Constraint**: All operations must adhere to Zero-BS Philosophy (no stubs, TODOs, faked APIs, or placeholder data).

---

## Non-Negotiable Requirements

### 1. Repository Setup
- GitHub repository: `rysweet/AzureHayMaker` (public, open source)
- Default branch: `main`
- Branch protection: PRs required for merging to main
- Auto-update PR branches when out of date
- Local git repository initialized at: `/Users/ryan/src/AzureHayMaker`

### 2. Technology Stack
- **Language**: Python
- **Package Manager**: uv
- **Testing**: pytest
- **Linting**: ruff
- **Type Checking**: pyright
- **Pre-commit Hooks**: Must enforce linting, formatting, type safety, and test execution

### 3. Azure Tools Required
- Azure CLI (az)
- Terraform
- Azure Bicep
- EntraID admin capabilities

### 4. External Dependencies
- Anthropic API (Claude Code)
- Azure Container Apps
- Azure Functions (for scheduling)
- Azure Event Bus (for agent logging)

---

## Phase 1: Groundwork - Scenario Creation

### Objective
Research Azure Architecture Center and create 50+ operational scenarios with corresponding goal-seeking agents.

### Requirements

#### 1.1 Claude Code Skill Development
**Source**: Azure Architecture Center (https://learn.microsoft.com/en-us/azure/architecture/)

**Deliverable**: Claude Code skill(s) with progressive disclosure that cover:
- All main Technology Areas from Azure Architecture Center
- Comprehensive documentation/knowledge of:
  - Azure CLI usage
  - Terraform on Azure
  - Azure Bicep
  - EntraID administration
- Installation instructions for all required tools
- Clear references to official documentation

**Acceptance Criteria**:
- [ ] Skill can answer questions about each Technology Area
- [ ] Skill provides working commands for Azure CLI, Terraform, and Bicep
- [ ] Skill includes or references installation procedures
- [ ] Documentation links are validated and current

#### 1.2 Scenario Document Creation
**Quantity**: Minimum 50 distinct scenarios (5 per Technology Area)

**Storage Location**: `/Users/ryan/src/AzureHayMaker/docs/scenarios/`

**Each Scenario Must Include**:

1. **Context**:
   - Technology Area classification
   - Fictional company profile (small to mid-size)
   - Minimal viable implementation description

2. **Three Discrete Operation Phases**:
   - **Phase 1: Deployment and Validation**
     - All commands/scripts required for infrastructure deployment
     - User account creation commands
     - Role assignment commands
     - Validation checks to confirm successful deployment

   - **Phase 2: Mid-Day Operations and Management**
     - Management commands for ongoing operations
     - Benign administrative actions
     - Health checks and monitoring commands

   - **Phase 3: Cleanup and Tear-Down**
     - Complete resource removal commands
     - User account deletion
     - Role assignment removal
     - Validation that all resources are deleted

3. **Automation Approach**:
   - Use Azure CLI, Terraform, OR Bicep (whichever is easiest)
   - All operations must be automatable (no manual portal clicks)

4. **Documentation**:
   - Links to relevant Azure documentation
   - Links to automation tool documentation
   - Prerequisites and dependencies

5. **Tenant/Subscription Scoping**:
   - ALL operations scoped to single tenant and subscription
   - If Azure docs suggest multi-tenant/subscription, simplify to single tenant
   - Document any simplifications made

**Acceptance Criteria**:
- [ ] Minimum 50 scenarios created
- [ ] Each scenario has all three operation phases
- [ ] All commands are copy-pasteable and executable
- [ ] Documentation links are valid
- [ ] Each scenario can be executed independently
- [ ] Single tenant/subscription scoping verified

#### 1.3 Goal-Seeking Agent Generation
**Source Pattern**: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/blob/main/docs/GOAL_AGENT_GENERATOR_GUIDE.md

**Storage Location**: `/Users/ryan/src/AzureHayMaker/src/agents/`

**Agent Count**: One agent per scenario (50+ agents)

**Each Agent Must**:

1. **Configuration**:
   - Embed corresponding scenario document in prompt
   - Include all necessary tool documentation links
   - Include Azure documentation links
   - Receive service principal credentials via environment variables

2. **Behavior**:
   - Instantiate the scenario in target tenant
   - Execute for minimum 8 hours
   - Perform benign management operations throughout
   - Autonomously resolve encountered problems (goal-seeking)
   - Clean up and tear down all resources at completion

3. **Logging**:
   - Keep detailed log of all actions
   - Post logs to control program via event bus
   - Log all resource creation with resource IDs

4. **Resource Management**:
   - Tag all resources with: `AzureHayMaker-managed`
   - Use unique names per run (include timestamp/UUID)
   - Track all created resources for cleanup verification

**Acceptance Criteria**:
- [ ] One agent per scenario created
- [ ] Each agent includes complete scenario documentation
- [ ] Agents can receive SP credentials from environment
- [ ] Logging mechanism integrated
- [ ] Resource tagging implemented
- [ ] Unique naming strategy implemented
- [ ] Goal-seeking behavior pattern implemented

---

## Phase 2: Service Design

### Objective
Design the orchestration service architecture that schedules and manages scenario execution.

### Requirements

#### 2.1 Core Service Architecture

**Hosting**: Azure Functions (scheduled execution)
- Reference: https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-scheduled-function

**Execution Schedule**: 4 times per day
- US regions execution window
- Asia regions execution window
- Middle East regions execution window
- Europe regions execution window

#### 2.2 Configuration Requirements

The service MUST accept and validate:

1. **Target Tenant ID** (Azure tenant identifier)
2. **Target Tenant Service Principal**:
   - Client ID
   - Client Secret (securely stored)
3. **ANTHROPIC_API_KEY** (securely stored)
4. **Simulation Size** (integer: determines N scenarios to execute)

**Credential Protection**:
- Service principal secrets must be stored securely (Azure Key Vault recommended)
- Secrets must never be logged
- Secrets passed to container apps via secure environment variables only
- Rotation mechanism consideration required

#### 2.3 Service Principal Management

**Main Service SP**:
- Must have permissions to:
  - Create/delete service principals
  - Assign roles
  - Create/manage Azure Container Apps
  - Create/manage Azure Event Bus resources
  - Query subscription resources
  - Delete resources (for cleanup enforcement)

**Scenario-Specific SPs**:
- Naming convention: `AzureHayMaker-<ScenarioName>-admin`
- Each SP created fresh at execution start
- Minimum required roles:
  - User Assignment Administrator (for role assignments)
  - Contributor (for resource management)
- Each SP deleted after scenario completion and cleanup verification

#### 2.4 Service Workflow

**Startup Phase**:
1. Validate required configuration present
2. Validate credentials work (test API calls)
3. Validate required tools installed (az CLI, terraform, bicep)
4. Validate Anthropic API access
5. Validate web fetch capability
6. Log validation results

**Selection Phase**:
1. Calculate N = f(simulation_size)
2. Randomly select N scenario documents + corresponding agents
3. Log selected scenarios

**Provisioning Phase**:
1. Create dedicated SP for each scenario
2. Assign required roles to each SP
3. Start event bus service for agent logging
4. Log SP creation and role assignments

**Execution Phase**:
1. Launch each scenario agent in separate Azure Container App instance
2. Container specs per instance:
   - Minimum 64GB RAM
   - Minimum 2 CPUs
   - Container image with all required tools pre-installed
3. Pass SP credentials to container via environment variables
4. Monitor agent log messages on event bus
5. Record all log messages
6. Track all provisioned resources (extract from logs)

**Monitoring Phase**:
1. Provide queryable endpoint for:
   - Execution statistics
   - List of provisioned resources
   - List of created SP names
   - Agent status
   - Error logs

**Cleanup Phase** (after 8 hours):
1. Check each scenario completed cleanup
2. Query Azure for resources with tag: `AzureHayMaker-managed`
3. Force-remove any remaining resources
4. Delete all scenario-specific SPs
5. Log cleanup actions
6. Generate execution summary report

#### 2.5 Container Image Requirements

**Base Image**: Must include
- Python runtime
- Azure CLI (az)
- Terraform
- Azure Bicep
- Required Python packages (uv environment)
- Anthropic SDK
- Logging client for event bus

**Acceptance Criteria**:
- [ ] All tools pre-installed and validated
- [ ] Image build automated
- [ ] Image size optimized reasonably
- [ ] Security scanning passed

#### 2.6 Design Review Process

**Requirement**: Multiple reviews by specialist sub-agents

**Review Dimensions**:
1. **Security Review**:
   - Credential management
   - Least privilege principle
   - Secret storage
   - Network security

2. **Architecture Review**:
   - Component design
   - Scalability
   - Failure modes
   - Recovery mechanisms

3. **Operations Review**:
   - Monitoring strategy
   - Logging completeness
   - Debugging capability
   - Resource cleanup guarantee

4. **Cost Review**:
   - Resource sizing justification
   - Execution frequency optimization
   - Cleanup verification to prevent cost leaks

**Acceptance Criteria**:
- [ ] Design document created
- [ ] All four review dimensions addressed
- [ ] Each review conducted by appropriate specialist
- [ ] All critical issues resolved
- [ ] Design approved before implementation begins

---

## Phase 3: Implementation

### Objective
Build the orchestration service using test-driven development.

### Requirements

#### 3.1 Development Methodology

**Approach**: Test-Driven Development (TDD)
1. Write test first
2. Implement minimal code to pass
3. Refactor
4. Repeat

**Test Coverage Requirements**:
- Minimum 80% code coverage
- 100% coverage for critical paths:
  - Credential validation
  - SP creation/deletion
  - Resource cleanup verification
  - Configuration validation

#### 3.2 Code Structure

**Directory Structure**:
```
src/
├── orchestrator/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── validation.py      # Startup validation
│   ├── sp_manager.py      # Service principal management
│   ├── scenario_selector.py
│   ├── container_manager.py
│   ├── event_bus.py       # Logging infrastructure
│   ├── cleanup.py         # Resource cleanup
│   └── monitoring.py      # Status endpoint
├── agents/
│   └── [generated agents]
└── common/
    ├── azure_client.py
    ├── logging.py
    └── utils.py

tests/
├── unit/
│   └── [unit tests for each module]
├── integration/
│   └── [integration tests]
└── e2e/
    └── [end-to-end tests]

docs/
└── scenarios/
    └── [scenario documents]
```

#### 3.3 Module Specifications

**config.py**:
- Load configuration from environment/config file
- Validate all required fields present
- Provide type-safe access to configuration
- NO default values for secrets

**validation.py**:
- Validate Azure credentials work
- Validate Anthropic API access
- Validate required tools installed
- Validate permissions sufficient
- Return detailed validation results

**sp_manager.py**:
- Create service principal with naming convention
- Assign roles to service principal
- Delete service principal
- List all HayMaker-created SPs
- Handle rate limiting and retries

**scenario_selector.py**:
- Load available scenarios from filesystem
- Randomly select N scenarios based on simulation_size
- Validate scenario documents are well-formed
- Return selected scenarios with agent paths

**container_manager.py**:
- Build container image with all tools
- Deploy container apps
- Pass environment variables securely
- Monitor container status
- Retrieve container logs
- Delete container apps

**event_bus.py**:
- Initialize event bus
- Receive log messages from agents
- Store log messages persistently
- Provide query interface for logs
- Extract resource IDs from logs

**cleanup.py**:
- Query resources by tag
- Delete resources
- Verify deletion
- Delete service principals
- Generate cleanup report

**monitoring.py**:
- Provide HTTP endpoint
- Return execution statistics
- Return resource lists
- Return SP lists
- Return agent status

#### 3.4 Testing Requirements

**Unit Tests**:
- Each module tested independently
- Mock external dependencies (Azure API, Anthropic API)
- Test error conditions
- Test edge cases

**Integration Tests**:
- Test module interactions
- Test Azure API calls (against test subscription)
- Test Anthropic API calls
- Test event bus functionality

**End-to-End Tests**:
- Test complete workflow with 1-2 simple scenarios
- Test cleanup verification
- Test failure recovery
- Test monitoring endpoints

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] Coverage >= 80%
- [ ] Critical paths have 100% coverage
- [ ] No flaky tests
- [ ] Tests run in CI/CD pipeline

#### 3.5 Code Review Process

**Standard Workflow**:
1. Implementation in feature branch
2. Self-review
3. Automated checks (pre-commit hooks)
4. Peer review (can be AI specialist agents)
5. Address feedback
6. Approval and merge

**Review Checklist**:
- [ ] Tests written and passing
- [ ] Type hints present
- [ ] Error handling appropriate
- [ ] Logging sufficient for debugging
- [ ] No secrets in code
- [ ] Documentation updated
- [ ] No performance regressions

---

## Phase 4: Quality Assurance - Zero-BS Compliance

### Objective
Perform two comprehensive passes to ensure complete adherence to Zero-BS Philosophy.

### Requirements

#### 4.1 Zero-BS Philosophy Principles

**Prohibited**:
- Stub functions (functions that return placeholder data)
- TODO comments indicating incomplete work
- Faked APIs (mock APIs in production code)
- Faked data (hardcoded test data in production)
- Placeholder implementations
- Comments like "// to be implemented"
- Functions that always return success without actual work

**Required**:
- Every function does real work
- Every API call is genuine
- Every error is handled
- Every validation is performed
- Every cleanup is verified
- Quality over speed

#### 4.2 First Zero-BS Pass

**Focus**: Identify and eliminate all violations

**Process**:
1. Automated scan for prohibited patterns:
   - Search for "TODO"
   - Search for "FIXME"
   - Search for "stub"
   - Search for "placeholder"
   - Search for "mock" (except in test code)
   - Search for "fake" (except in test code)

2. Manual review of each module:
   - Verify all functions do real work
   - Verify all API calls are genuine
   - Verify all error handling is complete
   - Verify all validations execute
   - Verify all cleanup is verified

3. Document findings

4. Fix all violations

5. Re-test after fixes

**Acceptance Criteria**:
- [ ] Zero prohibited patterns found
- [ ] All modules manually reviewed
- [ ] All violations documented and fixed
- [ ] All tests still pass
- [ ] Documentation confirms Zero-BS compliance

#### 4.3 Second Zero-BS Pass

**Focus**: Deep verification and edge cases

**Process**:
1. Review error handling paths:
   - Verify errors are caught
   - Verify errors are logged
   - Verify errors are handled (not ignored)
   - Verify recovery mechanisms work

2. Review cleanup code:
   - Verify cleanup always executes (even on error)
   - Verify cleanup verification is genuine
   - Verify forced cleanup has safeguards

3. Review validation code:
   - Verify validations aren't bypassed
   - Verify validation results are used
   - Verify edge cases are handled

4. Review production vs test separation:
   - Verify no test code in production paths
   - Verify no test data in production
   - Verify no test configurations in production

5. Document findings

6. Fix any remaining violations

7. Final re-test

**Acceptance Criteria**:
- [ ] All error paths verified
- [ ] All cleanup code verified
- [ ] All validation code verified
- [ ] Production/test separation verified
- [ ] Zero violations found
- [ ] All tests pass
- [ ] Final documentation complete

#### 4.4 Quality Metrics

**Definition of Done**:
- Zero TODOs in production code
- Zero stub functions
- Zero faked APIs in production
- Zero faked data in production
- 100% of functions do real work
- 100% of error paths handled
- 100% of cleanup verified
- All tests pass
- Documentation complete and accurate

---

## Success Criteria (Project-Wide)

### Functional Success
- [ ] 50+ scenarios documented and executable
- [ ] 50+ goal-seeking agents generated
- [ ] Orchestration service deploys successfully
- [ ] Service executes on schedule (4x daily)
- [ ] Agents execute in container apps
- [ ] Logging infrastructure captures all agent logs
- [ ] Monitoring endpoint returns accurate data
- [ ] Resource cleanup verified after each execution
- [ ] No resource leaks detected

### Quality Success
- [ ] Zero-BS Philosophy: 100% compliance
- [ ] Test coverage >= 80%
- [ ] All tests pass
- [ ] No critical security issues
- [ ] Code review approved
- [ ] Documentation complete

### Operational Success
- [ ] Service runs reliably for 1 week
- [ ] No manual intervention required
- [ ] All scenarios complete successfully
- [ ] Cleanup always succeeds
- [ ] Logs provide sufficient debugging information
- [ ] Monitoring data is accurate

---

## Critical Constraints and Clarifications

### Single Tenant/Subscription Scope
**Requirement**: ALL operations must be scoped to a single tenant and single subscription.

**Implication**: If Azure Architecture Center guidance suggests multi-tenant or multi-subscription approaches, simplify to single tenant/subscription. Document the simplification in the scenario.

### Credential Security
**Requirement**: Service principal credentials must be protected at all times.

**Implementation**:
- Store secrets in Azure Key Vault
- Pass to containers via secure environment variables only
- Never log credentials
- Clear credentials from memory after use
- Consider rotation mechanism

### Resource Naming Uniqueness
**Requirement**: Resource names must be unique per execution run.

**Implementation**: Include timestamp and/or UUID in resource names to prevent conflicts between runs.

### Resource Tagging
**Requirement**: ALL created resources must be tagged with `AzureHayMaker-managed`.

**Implementation**: Verify tagging in scenario execution, use tag for cleanup verification.

### Minimum Execution Duration
**Requirement**: Each agent must execute for minimum 8 hours.

**Implementation**: Agents should continue benign operations throughout duration, not just deploy and idle.

### Cleanup Verification
**Requirement**: Service must verify cleanup completion, and force-remove any remaining resources.

**Implementation**:
1. Check agent reported cleanup complete
2. Query Azure for tagged resources
3. If resources remain, force delete
4. Verify deletion succeeded
5. Log any resources that cannot be deleted

### Tool Installation
**Requirement**: All required tools (Azure CLI, Terraform, Bicep) must be available.

**Implementation**: Pre-install in container image, validate on startup.

---

## Deliverables by Phase

### Phase 1 Deliverables
1. Claude Code skill(s) for Azure Architecture Center coverage
2. 50+ scenario documents in `/Users/ryan/src/AzureHayMaker/docs/scenarios/`
3. 50+ goal-seeking agents in `/Users/ryan/src/AzureHayMaker/src/agents/`
4. Documentation of scenario creation process

### Phase 2 Deliverables
1. Architecture design document
2. Security review documentation
3. Architecture review documentation
4. Operations review documentation
5. Cost review documentation
6. Design approval sign-off

### Phase 3 Deliverables
1. Orchestration service source code
2. Container image build scripts
3. Deployment scripts/templates
4. Comprehensive test suite
5. Code review documentation
6. User documentation

### Phase 4 Deliverables
1. First Zero-BS pass report
2. Second Zero-BS pass report
3. Final quality metrics report
4. Zero-BS compliance certification

---

## Assumptions and Decisions Required

### Assumptions
1. Azure subscription with sufficient quota for container apps exists
2. GitHub account has appropriate permissions
3. Target tenant is a test/dev tenant (not production)
4. Anthropic API access is available and funded

### Decisions Required Before Implementation
1. **Simulation Size Mapping**: Define function `N = f(simulation_size)`
   - Suggestion: simulation_size ∈ {small, medium, large} → N ∈ {5, 15, 30}

2. **Event Bus Technology**: Specific Azure service
   - Options: Azure Event Hubs, Azure Service Bus, Azure Event Grid
   - Recommendation needed based on log volume and retention requirements

3. **Container Registry**: Where to store container images
   - Options: Azure Container Registry, Docker Hub, GitHub Container Registry

4. **Schedule Timing**: Exact times for 4 daily executions
   - Need timezone and hour specifications for US, Asia, Middle East, Europe

5. **Failure Handling**: What happens if a scenario agent fails?
   - Retry logic? Alert? Continue with others?

6. **Cost Budget**: Is there a cost constraint per execution?
   - Impacts container sizing and scenario selection

---

## Risk Assessment

### High Risk
1. **Service Principal Permission Escalation**: Created SPs might gain excessive permissions
   - Mitigation: Strict role assignment logic, audit logging, time-limited SPs

2. **Resource Cleanup Failure**: Resources might not be deleted, causing cost accumulation
   - Mitigation: Forced cleanup verification, alerting on failed cleanup, cost monitoring

3. **Credential Leakage**: SP secrets might be exposed in logs or errors
   - Mitigation: Credential scrubbing in logs, secure storage, environment variable hygiene

### Medium Risk
1. **Container App Quota Exhaustion**: Might hit subscription limits
   - Mitigation: Quota validation before execution, graceful handling of quota errors

2. **API Rate Limiting**: Azure or Anthropic APIs might throttle requests
   - Mitigation: Retry logic with exponential backoff, request spacing

3. **Agent Execution Timeout**: Agents might hang or fail to complete
   - Mitigation: Container timeout settings, health checks, forced termination after deadline

### Low Risk
1. **Scenario Document Quality Variance**: Some scenarios might be poorly documented
   - Mitigation: Scenario validation during selection, manual review of generated scenarios

2. **Tool Version Compatibility**: Azure CLI/Terraform/Bicep versions might conflict
   - Mitigation: Pin versions in container image, test compatibility

---

## Next Steps

1. **Review and Approval**: Stakeholder reviews this requirements document
2. **Decision Resolution**: Make decisions on open questions (Assumptions section)
3. **Phase 1 Kickoff**: Begin groundwork - scenario creation
4. **Iterative Refinement**: Update this document as new information emerges

---

## Document Version Control

- **Version**: 1.0
- **Date**: 2025-11-14
- **Status**: Draft for Review
- **Next Review**: After Phase 1 completion
