# Changelog

All notable changes to Azure HayMaker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planning

#### Added - 2025-11-30

- **Strategic Enhancement Roadmap** - Complete 12-month roadmap with 10 prioritized enhancements ([docs/ENHANCEMENT_ROADMAP.md](docs/ENHANCEMENT_ROADMAP.md))
  - P0-Critical: SIEM Telemetry Export (#124), Windows VM Security Hardening (#125)
  - P1-High: Multi-Tenant Isolation (#126), Distributed Tracing (#127), Cost Budget Enforcement (#128), Circuit Breakers (#129)
  - P2-Medium: Local Dev Mode (#130), GitHub Actions Agent (#131), Analytics Dashboard, Testing Framework
  - Portfolio ROI: 267% ($336K → $1.2M value over 12 months)

- **Implementation Specifications** - Detailed technical specs for P0-Critical enhancements:
  - SIEM Telemetry Export ([specs/SIEM_TELEMETRY_EXPORT.md](specs/SIEM_TELEMETRY_EXPORT.md)) - Sentinel, Splunk, Syslog connectors
  - Windows VM Security Hardening ([specs/WINDOWS_VM_SECURITY_HARDENING.md](specs/WINDOWS_VM_SECURITY_HARDENING.md)) - Key Vault, NSG restrictions, disk encryption

- **Strategic Analysis Documents**:
  - Enhancement Dependencies Analysis ([specs/ENHANCEMENT_DEPENDENCIES.md](specs/ENHANCEMENT_DEPENDENCIES.md))
  - Cost-Benefit Analysis with ROI calculations ([specs/ENHANCEMENT_COST_BENEFIT_ANALYSIS.md](specs/ENHANCEMENT_COST_BENEFIT_ANALYSIS.md))
  - Enhancement Quick Reference Card ([docs/ENHANCEMENT_QUICK_REFERENCE.md](docs/ENHANCEMENT_QUICK_REFERENCE.md))

- **Contributor Resources**:
  - Enhancement Contributor Guide ([docs/CONTRIBUTING_ENHANCEMENTS.md](docs/CONTRIBUTING_ENHANCEMENTS.md))
  - Specifications Directory Index ([specs/README.md](specs/README.md))

- **GitHub Project Infrastructure**:
  - 10 enhancement issues created (#124-131) with proper labels
  - 8 new labels (P0-critical, P1-high, P2-medium, telemetry, security, infrastructure, cost-optimization, developer-experience)
  - 4 quarterly milestones (Q1-Q4 2026)
  - Enhancement issue template (`.github/ISSUE_TEMPLATE/enhancement.md`)
  - PR template with E2E testing requirements (`.github/PULL_REQUEST_TEMPLATE.md`)

#### Changed - 2025-11-30

- **PROJECT.md** - Updated with strategic direction, current state, and roadmap links
- **README.md** - Added Planning & Strategy section with roadmap links
- **docs/INDEX.md** - Added Planning & Strategy section with comprehensive links
- **PATTERNS.md** - Added 2 new patterns:
  - Comprehensive Enhancement Analysis with ROI Justification
  - GitHub Project Scaffolding for Enhancement Tracking
- **DISCOVERIES.md** - Added Strategic Enhancement Portfolio Planning discovery (2025-11-30)

### In Progress (Open PRs)

#### Computer Use Knowledge Worker Agents - PR #123
- Browser automation with Playwright for realistic M365 workflows
- 95 tests (46 core tests passing, 100% coverage)
- Security score: 85-90/100
- Depends on: PR #121 (Windows VM provisioning)

#### Windows VM Fallback - PR #121
- Windows VM provisioning as fallback when Cloud PC unavailable
- 47 unit tests passing (100%)
- **⚠️ Security issues identified** (72/100 score) - See Issue #125
- Blocked by: Security hardening required before merge

#### W365 + M365 E2E with Telemetry - PR #119
- Complete telemetry collection for M365 activities
- Graceful degradation patterns
- 41 tests passing (100%)
- **Ready to merge** - Unblocks Issues #124, #127, #132

#### Knowledge Worker CLI - PR #112
- CLI commands for Knowledge Worker management
- E2E validation with real Azure tenant
- Ready to merge

---

## Release History

*No releases yet - project in active development*

---

## Contributing

See [CONTRIBUTING_ENHANCEMENTS.md](docs/CONTRIBUTING_ENHANCEMENTS.md) for how to contribute to planned enhancements.

---

## [Planning Methodology]

This roadmap was created using multi-agent analysis with:
- Comprehensive codebase exploration
- ROI-driven cost-benefit analysis
- Dependency mapping and critical path identification
- Phased quarterly planning with resource allocation
- GitHub project infrastructure setup

See [ULTRATHINK_SESSION_SUMMARY.md](docs/ULTRATHINK_SESSION_SUMMARY.md) for complete planning session details.
