# Azure HayMaker Presentations

This directory contains presentation materials for Azure HayMaker.

## Azure_HayMaker_Overview.pptx

**Created**: 2025-11-17
**Slides**: 32
**Size**: 924KB
**Format**: PowerPoint (.pptx)

### Presentation Structure

#### Section A: Overview & Architecture (9 slides)
1. **Cover Slide** - Title with farm imagery theme
2. **The Problem** - Why Azure HayMaker (challenges & limitations)
3. **The Solution** - What it does and key innovation
4. **High-Level Architecture** - System overview with architecture diagram
5. **Component Breakdown** - Orchestrator, Agent, and Event layers
6. **Technology Stack** - Complete technology choices table
7. **Security Model** - Identity management, secret management, audit
8. **Execution Flow** - End-to-end workflow from trigger to cleanup
9. **Benefits** - Key advantages (continuous validation, zero manual effort, cost-effective)

#### Section B: Deployment (8 slides)
10. **Prerequisites** - Azure requirements and tools needed
11. **GitOps Workflow** - Continuous deployment strategy with diagram
12. **GitHub Actions Pipeline** - CI/CD stages (validate, test, deploy, smoke tests)
13. **Bicep Infrastructure** - Modular IaC structure
14. **Environment Configuration** - Dev, Staging, Prod comparison table
15. **Secret Management (THE FIX)** - Before/After comparison showing Key Vault references
16. **Deployment Steps** - Step-by-step deployment guide
17. **Troubleshooting** - Common deployment issues and solutions

#### Section C: CLI Usage (8 slides)
18. **CLI Installation** - Installing via uv package manager
19. **CLI Configuration** - Setting up endpoints and authentication
20. **Status Command** - Checking orchestrator status
21. **Agents List Command** - Viewing agent execution
22. **Logs Command (Tail)** - Viewing recent log entries
23. **Logs Command (Follow)** - Streaming logs in real-time
24. **Resources Command** - Listing deployed Azure resources
25. **Deploy On-Demand** - Triggering scenario execution immediately

#### Section D: Demo (6 slides)
26. **Demo Scenario** - Linux VM web server (compute-01)
27. **Demo - Deployment** - Starting the agent with CLI output
28. **Demo - Execution Logs** - Real-time agent execution logs
29. **Demo - Resources Created** - Azure Portal view of deployed resources
30. **Demo - Cleanup** - Autonomous cleanup verification
31. **Key Takeaways** - Summary of main points

#### Section E: Closing (1 slide)
32. **Q&A / Resources** - Questions, resources, and thank you

### Design Features

**Color Palette**: Azure professional blues
- Primary: #0078D4 (Azure Blue)
- Secondary: #00A4EF (Light Blue)
- Accent: #003366 (Dark Blue)
- Supporting: Grays, Green (#2ECC71), Red (#E74C3C), Orange (#F39C12)

**Typography**: Arial (web-safe, professional)

**Layout Patterns**:
- Section headers with colored bars
- Two-column layouts for comparison content
- Code blocks with monospace fonts (Courier New)
- Tables for structured data
- Bullet lists with proper hierarchy

**Visual Elements**:
- Architecture diagrams (where available)
- GitOps workflow diagram (where available)
- Cover image with farm theme
- Color-coded status indicators (✓, ❌, ⏳)
- Code examples with gray backgrounds

### Content Highlights

**Security Fix Emphasis** (Slide 15):
- Shows BEFORE/AFTER comparison
- Highlights the critical security improvement
- Color-coded (red for before, green for after)
- Clear explanation of Key Vault references

**Real CLI Examples**:
- All CLI slides show realistic terminal output
- Formatted with monospace fonts
- Include actual command syntax
- Show expected responses

**Demo Scenario**:
- Complete lifecycle: Deploy → Operate → Cleanup
- Real resource names and outputs
- Timing information included
- Cleanup verification emphasized

### Usage

**Presenting**:
- Duration: 45-60 minutes (with Q&A)
- Section A: 15 minutes (overview)
- Section B: 12 minutes (deployment)
- Section C: 10 minutes (CLI)
- Section D: 10 minutes (demo)
- Q&A: 8-13 minutes

**Speaker Notes**:
Speaker notes are embedded in the outline but not in the presentation itself. Refer to `/presentation-assets/PRESENTATION_OUTLINE.md` for detailed speaking points.

**Live Demo Tips**:
1. Have dev environment pre-deployed
2. Pre-stage an agent for on-demand deployment
3. Keep terminal windows ready for CLI commands
4. Have Azure Portal open for resource verification
5. Prepare backup screenshots if live demo fails

### Technical Details

**Generated With**: PptxGenJS (Node.js library)
**Source Script**: `/workspace/create_presentation.js`
**Architecture Diagrams**:
- `/presentation-assets/diagrams/01-high-level-architecture.png`
- `/presentation-assets/diagrams/04-gitops-workflow.png`

**Cover Image**: `/presentation-assets/images/haystack-cover.jpg` (farm cattle theme)

### Future Enhancements

**When Real Data Available**:
1. Add actual screenshots from deployed dev environment
2. Capture real CLI output from running system
3. Include Azure Portal screenshots showing resources
4. Add Application Insights metrics dashboard
5. Include real agent execution logs with timestamps

**Additional Slides to Consider**:
- Architecture deep dive (component interactions)
- Scenario library overview (50+ scenarios)
- Cost analysis with actual data
- Performance metrics and SLAs
- Roadmap and future features
- Security compliance checklist

### Regenerating the Presentation

To regenerate or modify:

```bash
# Edit the script
vi workspace/create_presentation.js

# Regenerate
cd workspace
node create_presentation.js
```

### Validation

**File Structure**: Valid PPTX (ZIP archive with proper Office Open XML structure)
**Slide Count**: 32 slides (confirmed)
**File Size**: 924KB
**Format Compatibility**: PowerPoint 2010+ compatible

### Notes

- Presentation follows "retcon" approach - documents DESIRED state
- Security fix (Req 4) is prominently featured
- All content based on comprehensive session work
- Ready for stakeholder presentation
- Designed to drive reality to match the documented state

---

**Created by**: Azure HayMaker Team
**Last Updated**: 2025-11-17
**Version**: 1.0
