# Knowledge Worker Activity Framework - Research Notes

## Research Summary

This document captures research findings for building a Knowledge Worker Activity Framework within Azure HayMaker to simulate realistic M365 knowledge worker activity.

---

## 1. Existing Azure HayMaker Architecture

**Source**: `/home/azureuser/src/h2/docs/ARCHITECTURE.md`, `README.md`

### Current System Overview
- **50+ Azure scenarios** across 10 technology areas
- **Goal-seeking agents** that autonomously deploy, operate, and cleanup
- **Three-phase lifecycle**: Deployment → Operations (8h) → Cleanup
- **Container Apps execution** with isolated credentials per scenario
- **Tag-based resource tracking** for complete cleanup verification
- **Orchestrator API** for execution control and monitoring

### Agent Structure
- `AgentBase` class with lifecycle hooks (`on_start`, `on_execute`, `on_cleanup`)
- Configuration via `AgentConfig` dataclass (name, goal, max_turns, success_criteria, constraints)
- AutoMode execution via amplihack framework
- Prompts stored in `prompt.md` files alongside agents

### Key Design Principles
- Zero-BS Philosophy: Real functionality, no stubs
- Complete Cleanup: Tag-based tracking and forced removal
- Observable Operations: Comprehensive logging
- Goal-Seeking: Autonomous problem resolution

---

## 2. CLI for Microsoft 365 (PnP CLI)

**Source**: https://pnp.github.io/cli-microsoft365/

### What It Is
- NPM package for managing Microsoft 365 tenants and SharePoint Framework projects
- Cross-platform (Windows, macOS, Linux)
- Works with any shell (Bash, PowerShell, etc.)

### Authentication Methods
1. **Device Code Flow** (Default): Interactive, navigate to aka.ms/devicelogin
2. **Browser Authentication**: `--authType browser`
3. **Username/Password**: `--authType password` (not for MFA-enabled accounts)
4. **Certificate-Based**: `--authType certificate` with .pfx/.pem file (best for automation)
5. **Client Secret**: `--authType secret` (limited SharePoint support)

### App Registration Requirements
- Requires Microsoft Entra application with appId (client ID) and tenant ID
- Setup command: `m365 setup` guides through app registration
- For app-only context (automation), need **application permissions**, not delegated

### Key Commands (Grouped)
- **SharePoint Online (spo)**: Sites, CDNs, content types, lists
- **Teams (teams)**: Team management, channels, messaging
- **Entra (entra)**: User management, groups
- **Planner**: Task management
- **Outlook**: Email operations

### Automation Capabilities
- Scripts can combine multiple CLI commands
- CI/CD integration (GitHub Actions, Azure DevOps)
- File input via `@` token for complex content
- Token substitution: `@meId`, `@meUserName`

---

## 3. Windows 365 Cloud PC Provisioning

**Source**: Microsoft Learn docs, sccmentor.com automation guides

### Automated Provisioning Steps (Microsoft)
1. **License Assignment**: Assign Windows 365 licenses to users
2. **Network Configuration**: Azure Network Connection (optional)
3. **Localization Setup**: Regional settings (optional)
4. **Device Images**: Custom images (optional)
5. **Provisioning Policy**: Create policy linking users to Cloud PCs

### Graph API Commands (via PowerShell/Microsoft.Graph.Beta)
```powershell
# License assignment
Get-MgSubscribedSku                    # Enumerate available licenses
Invoke-MgGraphRequest                   # Apply licenses to users

# Group management
New-MgBetaGroup                         # Create Entra ID groups
New-MgBetaGroupMember                   # Add users to groups

# Azure networking (optional)
New-AzResourceGroup                     # Create resource groups
New-AzVirtualNetwork                    # Create VNets
New-MgBetaDeviceManagementVirtualEndpointOnPremiseConnection  # Azure Network Connection

# Provisioning
Get-MgBetaDeviceManagementVirtualEndpointGalleryImage  # Query OS images
New-MgBetaDeviceManagementVirtualEndpointProvisioningPolicy  # Create policies
Set-MgBetaDeviceManagementVirtualEndpointProvisioningPolicy  # Assign policies

# Cloud PC management
Get-MgBetaDeviceManagementVirtualEndpointCloudPc  # List Cloud PCs
```

### Bulk Provisioning Workflow
1. Store user UPNs in text file (one per line)
2. Assign licenses to all users via Graph API
3. Create Entra ID security groups (naming convention important)
4. Populate groups with licensed users
5. Configure networking infrastructure (if not Microsoft-hosted)
6. Create provisioning policies targeting groups

### Graph X-Ray Tool
- Browser extension reveals Graph API calls made by Intune portal
- Generates PowerShell code snippets from captured API calls
- Useful for discovering undocumented API endpoints

---

## 4. Goal-Seeking Agent Pattern

**Source**: `.claude/skills/goal-seeking-agent-pattern/SKILL.md`

### Core Characteristics
- **Autonomy**: Decide HOW to achieve goals
- **Adaptability**: Adjust strategy based on runtime conditions
- **Goal-Oriented**: Focus on outcomes, not procedures
- **Multi-Phase**: Decompose objectives into phases with dependencies
- **Self-Monitoring**: Track progress, detect failures, course-correct

### When to Use
- Problem space is large with many valid approaches
- Context varies significantly
- Failures expected and autonomous recovery valuable
- Objectives clear but path is flexible
- Multi-step complexity requiring coordination

### Architecture Components
1. **Goal Definition**: Extracted from natural language prompts
2. **Execution Plan**: Multi-phase plan with dependencies
3. **Skill Synthesis**: Map capabilities to available skills/tools
4. **Agent Assembly**: Combine into executable bundle

### Execution Flow
```
Goal Analysis → Planning → Skill Synthesis → Agent Assembly → Execution (Auto-Mode)
```

### Error Handling Strategies
- Retry with exponential backoff
- Alternative strategies for same goal
- Graceful degradation (accept partial success)
- Escalation to human when limits reached

---

## 5. M365 Workflow Automation

**Source**: Power Automate guides, workflow automation articles

### Power Automate Patterns
- **Triggers**: Events that initiate workflows (new email, file creation, schedule)
- **Actions**: Tasks executed after trigger (send email, update spreadsheet)
- **Flows**: Automated sequences combining triggers and actions
- 700+ connectors available

### Email Automation
- Automatic email sorting by sender/subject/keywords
- Priority email flagging
- Notification consolidation into digests
- Automated approval workflows

### Document Management
- Multi-stage document routing/approval
- AI-powered content categorization
- Metadata tagging with naming conventions
- Time-based archival scheduling

### Teams Automation
- Channel alerts for SharePoint updates
- Project milestone notifications
- Task assignment/completion alerts
- Quiet hours support

### SharePoint Automation
- Automatic task creation from list changes
- Workload-based assignment distribution
- Recurring task automation

---

## 6. Magentic Orchestration Framework

**Source**: Microsoft Agent Framework docs, magentic-ui GitHub

### What It Is
- Multi-agent orchestration pattern based on Magentic-One/AutoGen
- Manager coordinates specialized agents dynamically
- Maintains shared context, tracks progress, adapts in real-time

### Execution Phases
1. **Planning**: Manager analyzes task, creates initial plan
2. **Agent Selection**: Identify best agent for each subtask
3. **Execution**: Selected agent performs their portion
4. **Progress Assessment**: Evaluate and update plan
5. **Iteration**: Repeat until completion
6. **Final Synthesis**: Integrate outputs into final result

### Magentic UI Agents
- **Orchestrator**: Overall coordination
- **Web Surfer**: Web navigation/automation
- **Coder**: Code execution
- **File Surfer**: File analysis
- **Action Guard**: Approval for sensitive operations
- **Plan Learning**: Learn from previous executions

### Integration Patterns
- Co-Planning: Collaborative step-by-step plans
- Co-Tasking: Human interruption and guidance
- MCP Server integration for extensibility

---

## 7. Gadugi Agentic Test Framework

**Source**: https://github.com/rysweet/gadugi-agentic-test

### What It Is
- AI-powered testing framework using autonomous agents
- Tests "outside-in" like actual users
- Multi-agent orchestration with adaptive test generation

### Agent Types
- **ElectronUIAgent**: Electron app testing via Playwright
- **CLIAgent**: CLI testing with session management
- **ComprehensionAgent**: AI-generated tests from docs
- **IssueReporter**: Automated GitHub issue creation
- **PriorityAgent**: Issue classification/prioritization

### Features
- Adaptive element selection
- Visual regression testing
- WebSocket monitoring
- Automatic retry with contextual recovery
- YAML scenario definitions

---

## 8. Endpoint Options Analysis

### Option A: Windows 365 Cloud PCs
**Pros**:
- Full Windows desktop experience
- Native M365 integration
- Managed via Intune/Graph API
- Distinct endpoints per knowledge worker
- Realistic user telemetry

**Cons**:
- Higher cost (~$20-50/user/month)
- Licensing complexity (Windows 365 Enterprise)
- Provisioning time (10-30 minutes per Cloud PC)
- Scale limits need investigation

### Option B: Azure Virtual Desktop (AVD)
**Pros**:
- More cost-effective at scale
- Pooled vs personal desktops
- Better for session-based activity

**Cons**:
- More complex setup
- Not as direct 1:1 endpoint mapping
- Different telemetry patterns

### Option C: Container-Based M365 CLI Execution
**Pros**:
- Lowest cost
- Fastest provisioning
- Easy scale (similar to current HayMaker agents)

**Cons**:
- Not true endpoint simulation
- Limited to CLI-accessible operations
- May not generate all desired telemetry

### Recommendation
**Hybrid Approach**:
- Use Windows 365 Cloud PCs for core knowledge workers (10-50)
- Use M365 CLI containers for scale-out activity (remaining 50-250)
- Ensures distinct endpoint telemetry while managing costs

---

## 9. Knowledge Worker Persona Categories

### Category 1: Executive/Management
- **Activities**: Email heavy, calendar management, document review, Teams meetings
- **Tools**: Outlook, Teams, Word, PowerPoint
- **Communication Pattern**: High email volume, cross-team communication

### Category 2: Legal/Compliance
- **Activities**: Contract review, policy documents, confidential communications
- **Tools**: Word, SharePoint (sensitive sites), Teams (private channels)
- **Communication Pattern**: Internal-only, document-heavy, limited external

### Category 3: Engineering/Technical
- **Activities**: Technical documentation, code review notes, architecture diagrams
- **Tools**: OneNote, Teams, SharePoint, technical file sharing
- **Communication Pattern**: Team-focused, technical discussions

### Category 4: HR/People Operations
- **Activities**: Employee onboarding docs, policy updates, confidential HR matters
- **Tools**: SharePoint (HR site), Word, Teams, Forms
- **Communication Pattern**: Organization-wide announcements, 1:1 communications

### Category 5: Finance/Accounting
- **Activities**: Reports, spreadsheets, financial analysis, budgeting
- **Tools**: Excel, PowerBI, SharePoint, Teams
- **Communication Pattern**: Periodic reporting, cross-departmental

### Category 6: Sales/Business Development
- **Activities**: Client communications, proposals, presentations, CRM updates
- **Tools**: Outlook, PowerPoint, Teams, SharePoint
- **Communication Pattern**: External-facing (but constrained to simulation)

### Category 7: Operations/Logistics
- **Activities**: Process documentation, scheduling, coordination
- **Tools**: Planner, Teams, SharePoint lists, Excel
- **Communication Pattern**: Cross-functional coordination

### Category 8: Marketing/Communications
- **Activities**: Content creation, campaign coordination, design review
- **Tools**: Word, PowerPoint, SharePoint, Teams
- **Communication Pattern**: Creative collaboration, approval workflows

---

## 10. Constraints and Requirements Summary

### Must Have
- [x] 50-300 knowledge workers
- [x] Distinct endpoints (not all same machine)
- [x] Internal-only communications (no external domains)
- [x] Team structure with security boundaries
- [x] Cross-team communication patterns
- [x] Complete resource tracking and cleanup
- [x] Realistic work scenarios per persona

### Nice to Have
- [ ] Personality variations within persona types
- [ ] Temporal patterns (work hours, meetings)
- [ ] Dynamic content generation (not static templates)
- [ ] Document version history simulation
- [ ] Meeting/calendar simulation

### Constraints
- Single tenant operation
- Domain admin access available
- Must tag all created resources
- Must support teardown at any time
- Must not communicate outside simulation environment

---

## 11. Architecture Decision Points

### Q1: Scenario Organization
**Options**:
- A) One scenario per knowledge worker (50-300 scenarios)
- B) One scenario per team (5-20 scenarios)
- C) One scenario per company department (5-10 scenarios)
- D) Single orchestrated scenario with worker pool

**Recommendation**: Option C - One scenario per department
- Manageable number of scenarios
- Natural security boundary alignment
- Workers within department share scenario context
- Cross-department interaction via orchestrator

### Q2: Identity Management
**Options**:
- A) Create Entra users per worker
- B) Use service principals per worker
- C) Hybrid (users for Cloud PC, SPs for CLI agents)

**Recommendation**: Option C - Hybrid approach
- Entra users required for Windows 365 licensing
- SPs work for CLI-based automation
- Both can be tracked and cleaned up

### Q3: Communication Safety
**Options**:
- A) Transport rules blocking external domains
- B) Agent-level enforcement (only allow internal addresses)
- C) Network-level restrictions
- D) All of the above

**Recommendation**: Option D - Defense in depth
- Transport rules as primary control
- Agent validation as secondary
- Network policies as tertiary

### Q4: Endpoint Distribution
**Options**:
- A) All Windows 365 Cloud PCs
- B) All container-based CLI agents
- C) Hybrid based on persona requirements

**Recommendation**: Option C - Hybrid
- Cloud PCs for personas needing true desktop experience
- CLI agents for personas that work primarily via API
- Balance cost vs realism

---

## Sources Referenced

1. Azure HayMaker codebase (`/home/azureuser/src/h2/`)
2. PnP CLI for Microsoft 365: https://pnp.github.io/cli-microsoft365/
3. Microsoft Learn - Windows 365 Deployment: https://learn.microsoft.com/en-us/windows-365/enterprise/
4. SCCMentor - Automating Windows 365: https://sccmentor.com/2024/11/25/automating-windows-365-part-3-provisioning-cloud-pcs/
5. Goal Agent Generator Guide: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/blob/main/docs/GOAL_AGENT_GENERATOR_GUIDE.md
6. Gadugi Agentic Test: https://github.com/rysweet/gadugi-agentic-test
7. Microsoft Agent Framework - Magentic: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/magentic
8. Magentic UI: https://github.com/microsoft/magentic-ui
9. Power Automate workflow guides

---

*Research completed: 2025-11-25*
