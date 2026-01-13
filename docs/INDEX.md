# Azure HayMaker Documentation

Complete documentation for the Azure HayMaker orchestration service.

## 📚 Quick Links

- [Getting Started](GETTING_STARTED.md) - New user guide
- [Architecture Overview](architecture/ARCHITECTURE_DIAGRAM.md) - System design
- [Deployment Guide](DEPLOYMENT.md) - How to deploy
- [CLI Guide](CLI_GUIDE.md) - Command-line usage
- [GitOps Setup](GITOPS_SETUP.md) - CI/CD configuration

## 🏗️ Architecture

Comprehensive architecture documentation for understanding the system design.

- [Architecture Diagram](architecture/ARCHITECTURE_DIAGRAM.md) - High-level system overview
- [Monitoring Layers](architecture/ARCHITECTURE_MONITORING_LAYERS.md) - Observability architecture
- [Container Apps Architecture](architecture/CONTAINER_APPS_ARCHITECTURE.md) - Container deployment details
- [Container Manager Architecture](architecture/CONTAINER_MANAGER_ARCHITECTURE.md) - Container lifecycle management
- [VM Architecture (128GB)](architecture/VM_128GB_ARCHITECTURE.md) - Large VM deployment guide
- [Core Architecture](ARCHITECTURE.md) - Core architecture documentation

### Knowledge Worker Framework

- [Knowledge Worker Architecture](knowledge-worker-framework/ARCHITECTURE.md) - Framework design and components
- [Windows 365 Cloud PC Provisioning](knowledge-worker-framework/WINDOWS365_CLOUD_PC.md) - Cloud PC endpoint provisioning
- [Windows VM Fallback Strategy](knowledge-worker-framework/WINDOWS_VM_FALLBACK.md) - Cascade fallback for resilient provisioning
- [Computer Use Knowledge Worker Agents](knowledge-worker-framework/COMPUTER_USE_AGENTS.md) - Browser automation agents for M365 web apps on Windows VMs

## 💻 Implementation

Detailed implementation guides and specifications.

- [Implementation Guide](implementation/IMPLEMENTATION_GUIDE.md) - Step-by-step implementation
- [Implementation Spec](implementation/IMPLEMENTATION_SPEC.md) - Technical specifications
- [Design Decisions](design/DESIGN_DECISIONS.md) - Key architectural decisions

## 🚀 Deployment & Operations

Guides for deploying and operating Azure HayMaker.

### Deployment
- [Deployment Guide](DEPLOYMENT.md) - Main deployment documentation
- [Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md) - Pre-deployment verification
- [Deployment Validation](deployment/DEPLOYMENT_VALIDATION.md) - Post-deployment testing
- [Verify Auto-Granted Permissions](howto/verify-auto-granted-permissions.md) - How to verify PermissionGranter auto-consent

### Operations
- [Monitoring](operations/MONITORING.md) - Monitoring and observability
- [On-Demand Execution](ON_DEMAND_EXECUTION.md) - Manual scenario execution
- [Container Apps Status](CONTAINER_APPS_STATUS.md) - Container deployment status
- [Function App Structure](FUNCTION_APP_STRUCTURE.md) - Azure Functions organization

## 🧪 Testing

Testing strategies and test plans.

- [Testing Plan](testing/TESTING_PLAN.md) - Comprehensive test strategy
- [E2E Walkthrough](E2E_WALKTHROUGH.md) - End-to-end testing guide

## 🏢 Knowledge Worker Framework

Documentation for the Knowledge Worker Activity Framework.

- [Windows 365 + M365 E2E Demo](knowledge-worker-framework/WINDOWS365_E2E_DEMO.md) - Complete demonstration with telemetry
- [Windows 365 Cloud PC Provisioning](knowledge-worker-framework/WINDOWS365_CLOUD_PC.md) - Cloud PC management and graceful degradation
- [Knowledge Worker Architecture](knowledge-worker-framework/ARCHITECTURE.md) - Framework design and components

## 📖 Reference

Quick reference guides and supporting documentation.

- [Best Practices](reference/BEST_PRACTICES.md) - Recommended practices
- [FAQ](reference/FAQ.md) - Frequently asked questions
- [Glossary](reference/GLOSSARY.md) - Terms and definitions
- [Troubleshooting](reference/TROUBLESHOOTING.md) - Common issues and solutions
- [Vision](reference/VISION.md) - Project vision and goals

## 🗺️ Planning & Strategy

Strategic planning and roadmap documentation.

### Roadmap & Planning

> 📢 **NEW**: [Roadmap Announcement](ROADMAP_ANNOUNCEMENT.md) - Stakeholder announcement draft for 2025-2026 roadmap

- ⭐ [**Executive Summary**](EXECUTIVE_SUMMARY.md) - **START HERE** 10-minute overview for leadership
- [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Strategic roadmap for platform evolution (2025-2026)
- [Final Verification Report](FINAL_VERIFICATION_REPORT.md) - **NEW** Quality verification and readiness confirmation
- [Visual Roadmap](VISUAL_ROADMAP.md) - Mermaid diagrams and visual timeline
- [Roadmap Status](ROADMAP_STATUS.md) - Live tracking of enhancement progress
- [Enhancement Quick Reference](ENHANCEMENT_QUICK_REFERENCE.md) - One-page summary for stakeholders
- [One-Page Roadmap Summary](ONE_PAGE_ROADMAP_SUMMARY.md) - **NEW** Printable single-page reference
- [Enhancement Comparison Matrix](ENHANCEMENT_COMPARISON_MATRIX.md) - Side-by-side comparison of all 10 enhancements
- [Enhancement FAQ](ENHANCEMENT_FAQ.md) - Frequently asked questions
- [Before/After Transformation](BEFORE_AFTER_TRANSFORMATION.md) - How roadmap planning transformed the project
- [Dependency Graph Visual](DEPENDENCY_GRAPH_VISUAL.md) - Standalone dependency visualization
- [Master Deliverables Catalog](MASTER_DELIVERABLES_CATALOG.md) - **NEW** Complete index of all 85+ deliverables
- [Deliverables Index](DELIVERABLES_INDEX.md) - Session output catalog
- [Enhancement Dependencies](../specs/ENHANCEMENT_DEPENDENCIES.md) - Dependencies and critical path analysis
- [Cost-Benefit Analysis](../specs/ENHANCEMENT_COST_BENEFIT_ANALYSIS.md) - ROI analysis (267% portfolio ROI)

### Contributing & Onboarding

**New to the roadmap?** Start here:
- ⭐ [What to Read First](WHAT_TO_READ_FIRST.md) - **NEW** Reading guide by role (10 min to find your path)
- [Enhancement Decision Tree](ENHANCEMENT_DECISION_TREE.md) - **NEW** Choose which enhancement to work on

**Contributing guides**:
- [Quick Start for Contributors](QUICK_START_CONTRIBUTORS.md) - 15-minute general onboarding
- [Contributing to Enhancements](CONTRIBUTING_ENHANCEMENTS.md) - Detailed contributor workflow
- [Issue-to-Spec Mapping](ISSUE_SPEC_MAPPING.md) - Quick reference: which spec for which issue

**Enhancement-Specific Getting Started Guides** (Step-by-step for each enhancement):
  - [Getting Started: SIEM Export (#124)](GETTING_STARTED_124_SIEM_EXPORT.md) - P0-Critical, 3.5w, ROI: 120%
  - [Getting Started: VM Security (#125)](GETTING_STARTED_125_VM_SECURITY.md) - P0-Critical, 2w, ROI: 1,165%
  - [Getting Started: Multi-Tenant (#126)](GETTING_STARTED_126_MULTI_TENANT.md) - P1-High, 6w, ROI: 233%
  - [Getting Started: Distributed Tracing (#127)](GETTING_STARTED_127_DISTRIBUTED_TRACING.md) - P1-High, 2w, ROI: 36%
  - [Getting Started: Cost Enforcement (#128)](GETTING_STARTED_128_COST_ENFORCEMENT.md) - P1-High, 1.5w, ROI: 184%
  - [Getting Started: Circuit Breakers & Health Checks (#129)](GETTING_STARTED_129_CIRCUIT_BREAKERS.md) - P1-High, 2w, ROI: 150%
  - [Getting Started: Local Development Mode (#130)](GETTING_STARTED_130_LOCAL_DEV.md) - P2-Medium, 4w, ROI: 200%
  - [Getting Started: GitHub Actions CI/CD (#131)](GETTING_STARTED_131_GITHUB_ACTIONS.md) - P2-Medium, 2.5w, ROI: 180%
  - [Getting Started: Analytics Dashboard (#132)](GETTING_STARTED_132_DASHBOARD.md) - P2-Medium, 3w, ROI: 160%
  - [Getting Started: Testing Framework (#133)](GETTING_STARTED_133_TESTING.md) - P2-Medium, 4w, ROI: 190%

**Resources**:
- [GitHub Issues](https://github.com/rysweet/AzureHayMaker/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) - All enhancement issues
- [GitHub Milestones](https://github.com/rysweet/AzureHayMaker/milestones) - Quarterly milestones (Q1-Q4 2026)
- [Master Deliverables Catalog](MASTER_DELIVERABLES_CATALOG.md) - **NEW** Complete index of all 85+ deliverables

### Production Readiness
- [Production Readiness Checklist](PRODUCTION_READINESS_CHECKLIST.md) - Go/no-go criteria for production
- [Monitoring Strategy](MONITORING_STRATEGY.md) - Observability and alerting strategy
- [Risk Mitigation Playbooks](RISK_MITIGATION_PLAYBOOKS.md) - Tactical playbooks for identified risks
- [Stakeholder Presentation Outline](STAKEHOLDER_PRESENTATION_OUTLINE.md) - 30-minute presentation deck outline

### Tracking & Reporting
- [Project Success Metrics](PROJECT_SUCCESS_METRICS.md) - **NEW** Real-time metrics dashboard
- [Quarterly OKRs](QUARTERLY_OKRS.md) - **NEW** Objectives and Key Results for measuring progress
- [Weekly Status Report Template](WEEKLY_STATUS_REPORT_TEMPLATE.md) - **NEW** Template for weekly updates
- [Budget Tracking Template](BUDGET_TRACKING_TEMPLATE.md) - **NEW** Track actual vs. planned spending
- [Lessons Learned](LESSONS_LEARNED.md) - **NEW** What worked, what didn't, insights from planning
- [Implementation Checklist](IMPLEMENTATION_CHECKLIST.md) - **NEW** Step-by-step guide for implementing enhancements

### Implementation Specifications
- [All Specifications Index](../specs/README.md) - Complete specification directory
- [Ultrathink Session Summary](ULTRATHINK_SESSION_SUMMARY.md) - Complete planning session details and methodology
- **P0-Critical Specs:**
  - [SIEM Telemetry Export](../specs/SIEM_TELEMETRY_EXPORT.md) - Streaming telemetry to external SIEM platforms
  - [Windows VM Security Hardening](../specs/WINDOWS_VM_SECURITY_HARDENING.md) - Security fixes for Windows VM provisioning

## 🎯 Scenarios

Information about Azure scenarios and management.

- [Scenario Management](SCENARIO_MANAGEMENT.md) - Managing execution scenarios
- [Scenario Catalog](scenarios/) - All available scenarios

## 🔧 CLI & Tools

Command-line interface and diagnostic tools.

- [CLI Guide](CLI_GUIDE.md) - Command-line usage
- [CLI Diagnostic Commands](CLI_DIAGNOSTIC_COMMANDS_INDEX.md) - Diagnostic command index
- [CLI Diagnostic Features](CLI_DIAGNOSTIC_FEATURES_SPEC.md) - Feature specifications

## 🔐 Security

Security documentation and fixes.

- [Security Fixes](SECURITY_FIXES.md) - Security improvements and patches
- [Security Policy](SECURITY.md) - Security reporting and policies

## 🎨 Presentations

- [Azure HayMaker Overview](presentations/) - PowerPoint presentations

## 📝 Contributing

- [Contributing Guide](CONTRIBUTING.md) - General contribution guidelines
- [Contributing to Enhancements](CONTRIBUTING_ENHANCEMENTS.md) - Enhancement-specific workflow
- [Quick Start for Contributors](QUICK_START_CONTRIBUTORS.md) - **NEW** 15-minute onboarding
- [Changelog](../CHANGELOG.md) - **NEW** Version history and planning updates

---

**Project Repository**: [Azure HayMaker](https://github.com/rysweet/AzureHayMaker)

**License**: See [LICENSE](../LICENSE)
