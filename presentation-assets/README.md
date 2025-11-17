# Azure HayMaker Presentation Assets

This directory contains all assets, instructions, and materials needed to create the comprehensive Azure HayMaker presentation.

---

## Directory Contents

### Documentation Files

1. **PRESENTATION_OUTLINE.md**
   - Complete slide-by-slide outline (30-34 slides)
   - Full content for each slide
   - Speaker notes
   - Delivery timing guidelines
   - Status: ✅ COMPLETE

2. **ARCHITECTURE_DIAGRAMS.md**
   - Specifications for 8 architecture diagrams
   - Detailed descriptions of components and data flows
   - Style guidelines and export settings
   - Tool recommendations
   - Status: 📝 READY TO CREATE

3. **COVER_IMAGE_INSTRUCTIONS.md**
   - Instructions for sourcing hay farm cover image
   - Multiple sourcing options (Unsplash, Pexels, AI generation)
   - Image preparation scripts
   - PowerPoint integration guide
   - Status: 📝 READY TO SOURCE

4. **CLI_EXAMPLES_TO_CAPTURE.md**
   - Complete list of CLI commands to run
   - Expected outputs to capture
   - Azure Portal screenshots needed
   - File naming conventions
   - Status: ⏳ WAITING FOR DEPLOYMENT

---

## Prerequisites

Before creating the presentation, ensure:

1. **Azure Deployment Complete**
   - [ ] Dev environment deployed
   - [ ] Function App running
   - [ ] At least one agent execution completed
   - [ ] CLI installed and configured

2. **Tools Available**
   - [ ] PowerPoint or Google Slides
   - [ ] Draw.io or diagram tool (for architecture diagrams)
   - [ ] Terminal for CLI screenshots
   - [ ] Azure Portal access
   - [ ] Image editor (optional)

3. **Content Ready**
   - [ ] Cover image sourced (see COVER_IMAGE_INSTRUCTIONS.md)
   - [ ] CLI screenshots captured (see CLI_EXAMPLES_TO_CAPTURE.md)
   - [ ] Architecture diagrams created (see ARCHITECTURE_DIAGRAMS.md)
   - [ ] Azure Portal screenshots taken

---

## Creation Workflow

### Phase 1: Prepare Assets (Est: 2 hours)

**Step 1: Source Cover Image** (30 min)
```bash
# Follow COVER_IMAGE_INSTRUCTIONS.md
# Recommended: Use Unsplash
cd presentation-assets
# Download image from https://unsplash.com/s/photos/hay-bales
# Save as: haystack-cover.jpg (1920x1080)
```

**Step 2: Create Architecture Diagrams** (1 hour)
```bash
# Follow ARCHITECTURE_DIAGRAMS.md
# Use Draw.io or PowerPoint
# Create 8 diagrams as specified
# Export as PNG (1920x1080 or as specified)
# Save to: presentation-assets/diagrams/
```

**Step 3: Capture CLI Screenshots** (30 min)
```bash
# Follow CLI_EXAMPLES_TO_CAPTURE.md
# Requires live deployment
# Run all specified commands
# Capture terminal output
# Save to: presentation-assets/screenshots/
```

---

### Phase 2: Create Presentation (Est: 4-6 hours)

**Step 1: Set Up Presentation** (30 min)
- Create new PowerPoint or Google Slides
- Set slide dimensions: 16:9 (1920x1080)
- Choose professional template or create custom
- Set up master slides for consistency

**Step 2: Build Slides** (3-4 hours)

Follow **PRESENTATION_OUTLINE.md** structure:

1. **Section A: Overview & Architecture** (10 slides)
   - Use: Architecture diagrams from Phase 1
   - Insert: Cover image
   - Content: Copy from outline

2. **Section B: Deployment Guide** (7 slides)
   - Use: GitOps workflow diagram
   - Use: Secret management comparison
   - Content: Copy from outline, add code blocks

3. **Section C: CLI Usage Guide** (8 slides)
   - Use: CLI screenshots from Phase 1
   - Use: Terminal output captures
   - Content: Format as code blocks with syntax highlighting

4. **Section D: Real Demo** (6 slides)
   - Use: CLI screenshots (deployment)
   - Use: Azure Portal screenshots
   - Use: Real log output
   - Content: Emphasize "real" examples

5. **Closing Slides** (3 slides)
   - Summary, roadmap, Q&A
   - Add QR codes to GitHub repo (optional)

**Step 3: Polish & Review** (1-2 hours)
- Check all slides for consistency
- Verify all text is readable
- Test animations (if any)
- Proofread all content
- Check image quality
- Verify code examples are correct

---

### Phase 3: Testing & Rehearsal (Est: 1-2 hours)

**Step 1: Technical Test**
- Open presentation on target device
- Test transitions
- Verify all images load
- Check for formatting issues
- Test any embedded videos/GIFs

**Step 2: Dry Run**
- Present to yourself or colleague
- Time each section
- Practice demos
- Prepare for Q&A
- Test backup slides

---

## File Organization

```
presentation-assets/
├── README.md                           # This file
├── PRESENTATION_OUTLINE.md             # Complete outline
├── ARCHITECTURE_DIAGRAMS.md            # Diagram specifications
├── COVER_IMAGE_INSTRUCTIONS.md         # Image sourcing guide
├── CLI_EXAMPLES_TO_CAPTURE.md          # Commands to run
│
├── images/
│   ├── haystack-cover.jpg              # Cover slide background
│   └── haystack-cover-darkened.jpg     # Alternative with overlay
│
├── diagrams/
│   ├── 01-high-level-architecture.png
│   ├── 02-orchestrator-workflow.png
│   ├── 03-agent-execution-timeline.png
│   ├── 04-dual-write-log-pattern.png
│   ├── 05-security-architecture.png
│   ├── 06-gitops-workflow.png
│   ├── 07-secret-management-comparison.png
│   └── 08-cli-architecture.png
│
├── screenshots/
│   ├── cli-help-output.png
│   ├── cli-status-running.png
│   ├── cli-agents-list-table.png
│   ├── cli-logs-tail-table.png
│   ├── cli-logs-follow-streaming.png
│   ├── cli-resources-list-table.png
│   ├── cli-deploy-command-complete.png
│   ├── portal-resource-group-overview.png
│   ├── portal-vm-details-running.png
│   ├── portal-nsg-rules.png
│   ├── portal-resource-tags.png
│   └── portal-resource-group-empty.png
│
└── final/
    └── Azure_HayMaker_Overview.pptx    # Final presentation
```

---

## Quick Start Guide

### For Immediate Presentation Needs

If you need to create the presentation quickly without live deployment:

**Option 1: Use Mock Data** (2-3 hours)
1. Use outline content as-is
2. Create diagrams from descriptions
3. Use formatted code blocks instead of screenshots
4. Label as "Example Output" where needed
5. Focus on architecture and concepts

**Option 2: Partial Real Data** (4-5 hours)
1. Use architecture diagrams (can be text-based in slides)
2. Use historical CLI output (if available)
3. Use staging environment for screenshots
4. Fill in gaps with well-formatted examples

**Option 3: Full Production** (6-8 hours)
1. Wait for deployment completion
2. Capture all live examples
3. Create all diagrams
4. Full polish and rehearsal

---

## Presentation Delivery Tips

### Technical Setup (Before Presenting)

**Equipment Checklist**:
- [ ] Laptop with presentation loaded
- [ ] HDMI/DisplayPort adapter (if needed)
- [ ] Backup presentation on USB drive
- [ ] Backup presentation in cloud (Google Drive/OneDrive)
- [ ] Terminal with CLI configured (for live demo)
- [ ] Azure Portal open and logged in
- [ ] GitHub repo open (for reference)

**Pre-Flight Check** (15 min before):
- [ ] Connect to projector/screen
- [ ] Test slide animations
- [ ] Verify internet connection
- [ ] Test CLI commands
- [ ] Open all necessary tabs/windows
- [ ] Set "Do Not Disturb" mode
- [ ] Close unnecessary applications

### During Presentation

**Timing Guide**:
- Section A (Overview): 15 minutes
- Section B (Deployment): 12 minutes
- Section C (CLI): 10 minutes
- Section D (Demo): 10 minutes
- Q&A: 8-13 minutes
- **Total**: 45-60 minutes

**Pacing Tips**:
- Don't rush through architecture slides
- Emphasize the security fix (Slide 16)
- Show enthusiasm during live demo
- Pause for questions at section breaks
- Have backup slides ready (appendices)

**Live Demo Tips**:
- Pre-deploy an agent before presenting
- Have screenshots as backup if demo fails
- Explain what you're doing as you type
- Use large terminal font (16-18pt minimum)
- Narrate the output as it appears

### Handling Questions

**Common Questions to Prepare For**:
1. "How much does this cost to run?"
2. "What happens if cleanup fails?"
3. "Can I add my own scenarios?"
4. "How do you ensure agents don't cause problems?"
5. "What's the security model for service principals?"
6. "How long does deployment take?"
7. "Can this run in Azure Government Cloud?"
8. "What AI models are supported?"

**Answer Strategy**:
- Refer to specific slides when possible
- Use concrete examples
- Be honest about limitations
- Offer to follow up if you don't know
- Point to documentation for details

---

## Customization Guide

### Branding

To add your organization's branding:

1. **Logo**:
   - Add to slide master
   - Position: Top-right or bottom-right corner
   - Size: Small (100-150px width)

2. **Colors**:
   - Update color scheme in slide master
   - Keep high contrast for readability
   - Use brand colors for accents only

3. **Fonts**:
   - Headings: Your brand font (or Segoe UI)
   - Body: Sans-serif (Arial, Calibri, Segoe UI)
   - Code: Monospace (Consolas, Courier New)

### Audience Customization

**For Technical Audience**:
- Include more code examples
- Show actual Bicep templates
- Deep dive into architecture
- Discuss performance metrics

**For Management Audience**:
- Focus on benefits and ROI
- Emphasize automation and cost savings
- Show high-level architecture only
- Highlight security improvements

**For Security Audience**:
- Emphasize secret management fix
- Detail RBAC model
- Show audit capabilities
- Discuss threat model

---

## Troubleshooting

### Common Issues

**Issue**: Images appear pixelated in presentation
- **Solution**: Re-export at higher DPI (300+)
- **Prevention**: Use vector graphics (SVG) where possible

**Issue**: Code blocks are hard to read
- **Solution**: Increase font size (14pt minimum)
- **Solution**: Use high-contrast color scheme
- **Prevention**: Test on projector before presenting

**Issue**: CLI screenshots have inconsistent styling
- **Solution**: Use same terminal theme for all captures
- **Solution**: Consistent font and size across all screenshots
- **Prevention**: Capture all screenshots in one session

**Issue**: Presentation file size is too large
- **Solution**: Compress images (85% quality JPEG)
- **Solution**: Remove unused slides/images
- **Prevention**: Optimize images before inserting

---

## Quality Checklist

Before finalizing presentation:

**Content**:
- [ ] All slides follow outline
- [ ] No lorem ipsum or placeholder text
- [ ] All code examples are correct
- [ ] All URLs are valid
- [ ] Consistent terminology throughout

**Visual**:
- [ ] All images are high quality
- [ ] Consistent color scheme
- [ ] Readable from distance (18pt+ font)
- [ ] Proper alignment and spacing
- [ ] No overlapping elements

**Technical**:
- [ ] Presentation opens without errors
- [ ] All animations work correctly
- [ ] File size is reasonable (<50MB)
- [ ] Compatible with target device
- [ ] Backup copies created

**Delivery**:
- [ ] Rehearsed at least once
- [ ] Timing is appropriate
- [ ] Live demo tested
- [ ] Q&A answers prepared
- [ ] Backup plan ready

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2025-11-17 | Initial outline and instructions | Draft |
| 1.1 | TBD | Add screenshots and diagrams | In Progress |
| 1.2 | TBD | Final polish and review | Pending |
| 2.0 | TBD | Final presentation ready | Target |

---

## Support & Resources

**Documentation**:
- Main README: `/README.md`
- Architecture Guide: `/specs/architecture.md`
- GitOps Setup: `/docs/GITOPS_SETUP.md`
- CLI Documentation: `/cli/README.md`

**Tools**:
- PowerPoint: Microsoft Office or Office 365
- Google Slides: https://slides.google.com
- Draw.io: https://app.diagrams.net/
- Unsplash: https://unsplash.com/
- Azure Portal: https://portal.azure.com/

**Contact**:
- GitHub Issues: For technical questions
- Project Team: For presentation guidance
- Documentation: For detailed reference

---

## Next Steps

1. **Immediate** (While deployment runs):
   - ✅ Review PRESENTATION_OUTLINE.md
   - ✅ Read ARCHITECTURE_DIAGRAMS.md
   - ✅ Read COVER_IMAGE_INSTRUCTIONS.md
   - 📝 Source cover image from Unsplash
   - 📝 Start creating architecture diagrams

2. **After Deployment Completes**:
   - ⏳ Run CLI commands from CLI_EXAMPLES_TO_CAPTURE.md
   - ⏳ Capture all screenshots
   - ⏳ Take Azure Portal screenshots
   - ⏳ Verify all outputs are realistic

3. **Final Steps**:
   - 📝 Create PowerPoint presentation
   - 📝 Insert all assets
   - 📝 Polish and review
   - 📝 Rehearse delivery
   - 🎯 Present!

---

**STATUS**: Assets preparation in progress. Ready to create presentation once deployment completes and screenshots are captured.

**ESTIMATED COMPLETION TIME**: 6-8 hours after all assets are available.
