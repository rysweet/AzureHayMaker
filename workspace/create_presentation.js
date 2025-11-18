const PptxGenJS = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

// Azure color palette
const colors = {
  azureBlue: '0078D4',
  lightBlue: '00A4EF',
  darkBlue: '003366',
  gray: '505050',
  lightGray: 'E0E0E0',
  white: 'FFFFFF',
  black: '000000',
  green: '2ECC71',
  red: 'E74C3C',
  orange: 'F39C12'
};

const pptx = new PptxGenJS();
pptx.defineLayout({ name: '16x9', width: 10, height: 5.625 });
pptx.layout = '16x9';
pptx.author = 'Azure HayMaker Team';
pptx.title = 'Azure HayMaker - Autonomous Cloud Security Testing';
pptx.subject = 'Architecture, Deployment, and Demo';

// Helper to create section header
function addSectionHeader(slide, text) {
  slide.addShape('rect', {
    x: 0, y: 0, w: '100%', h: 0.8,
    fill: { color: colors.azureBlue }
  });
  slide.addText(text, {
    x: 0.5, y: 0.2, w: 9, h: 0.5,
    fontSize: 32, bold: true, color: colors.white,
    fontFace: 'Arial'
  });
}

// Helper for two-column layout
function addTwoColumnContent(slide, leftContent, rightContent, yStart = 1.5) {
  if (leftContent) {
    slide.addText(leftContent, {
      x: 0.5, y: yStart, w: 4.5, h: 3.5,
      fontSize: 14, fontFace: 'Arial', valign: 'top'
    });
  }
  if (rightContent) {
    slide.addText(rightContent, {
      x: 5.5, y: yStart, w: 4.5, h: 3.5,
      fontSize: 14, fontFace: 'Arial', valign: 'top'
    });
  }
}

// Slide 1: Cover Slide
let slide = pptx.addSlide();
try {
  slide.addImage({
    path: path.join(__dirname, '../presentation-assets/images/haystack-cover.jpg'),
    x: 0, y: 0, w: '100%', h: '100%'
  });
} catch (e) {
  slide.background = { color: colors.azureBlue };
}
slide.addShape('rect', {
  x: 0, y: 3, w: '100%', h: 2.5,
  fill: { color: '000000', transparency: 40 }
});
slide.addText('Azure HayMaker', {
  x: 0.5, y: 3.2, w: 9, h: 0.8,
  fontSize: 54, bold: true, color: colors.white, fontFace: 'Arial'
});
slide.addText('Autonomous Cloud Security Testing with AI Agents', {
  x: 0.5, y: 4.1, w: 9, h: 0.5,
  fontSize: 24, color: colors.white, fontFace: 'Arial'
});
slide.addText('Architecture, Deployment, and Demo • November 2025', {
  x: 0.5, y: 4.8, w: 9, h: 0.4,
  fontSize: 16, color: colors.lightGray, fontFace: 'Arial'
});

// Slide 2: The Problem
slide = pptx.addSlide();
addSectionHeader(slide, 'Why Azure HayMaker?');
slide.addText('The Challenge', {
  x: 0.5, y: 1.2, w: 9, h: 0.4,
  fontSize: 24, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: '50+ Azure services with unique security models', options: { bullet: true } },
  { text: 'Manual testing doesn\'t scale', options: { bullet: true } },
  { text: 'Configuration drift goes undetected', options: { bullet: true } },
  { text: 'Compliance validation is time-consuming', options: { bullet: true } }
], {
  x: 0.5, y: 1.8, w: 4.5, h: 2,
  fontSize: 16, fontFace: 'Arial'
});
slide.addText('Current Limitations', {
  x: 5.5, y: 1.2, w: 4.5, h: 0.4,
  fontSize: 24, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: 'Manual checklists (slow, inconsistent)', options: { bullet: true } },
  { text: 'Static security scanners (limited scope)', options: { bullet: true } },
  { text: 'Penetration tests (expensive, infrequent)', options: { bullet: true } },
  { text: 'Configuration audits (point-in-time only)', options: { bullet: true } }
], {
  x: 5.5, y: 1.8, w: 4.5, h: 2,
  fontSize: 16, fontFace: 'Arial'
});

// Slide 3: The Solution
slide = pptx.addSlide();
addSectionHeader(slide, 'Azure HayMaker: Autonomous Security Testing');
slide.addText('What It Does', {
  x: 0.5, y: 1.2, w: 4.5, h: 0.4,
  fontSize: 20, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: 'Deploys 50+ distinct Azure operational scenarios', options: { bullet: true } },
  { text: 'Uses AI agents (Claude Sonnet 4.5) for autonomous execution', options: { bullet: true } },
  { text: 'Runs continuously (4x daily across global regions)', options: { bullet: true } },
  { text: 'Self-provisioning, self-contained, self-cleaning', options: { bullet: true } },
  { text: 'Generates benign security telemetry for monitoring', options: { bullet: true } }
], {
  x: 0.5, y: 1.7, w: 4.5, h: 2.5,
  fontSize: 14, fontFace: 'Arial'
});
slide.addText('Key Innovation', {
  x: 5.5, y: 1.2, w: 4.5, h: 0.4,
  fontSize: 20, bold: true, color: colors.green, fontFace: 'Arial'
});
slide.addText([
  { text: 'Goal-seeking agents that troubleshoot their own issues', options: { bullet: true } },
  { text: 'Complete lifecycle automation (deploy → operate → cleanup)', options: { bullet: true } },
  { text: 'Zero manual intervention required', options: { bullet: true } }
], {
  x: 5.5, y: 1.7, w: 4.5, h: 2.5,
  fontSize: 14, fontFace: 'Arial'
});

// Slide 4: High-Level Architecture
slide = pptx.addSlide();
addSectionHeader(slide, 'High-Level Architecture');
try {
  slide.addImage({
    path: path.join(__dirname, '../presentation-assets/diagrams/01-high-level-architecture.png'),
    x: 0.5, y: 1.2, w: 9, h: 4
  });
} catch (e) {
  slide.addText('Architecture Diagram\n[Diagram: 01-high-level-architecture.png]', {
    x: 0.5, y: 1.5, w: 9, h: 3.5,
    fontSize: 14, fontFace: 'Courier New', align: 'center', valign: 'middle',
    fill: { color: colors.lightGray }
  });
}

// Slide 5: Component Breakdown
slide = pptx.addSlide();
addSectionHeader(slide, 'System Components');
slide.addText([
  { text: 'Orchestrator Layer', options: { bullet: false, bold: true, fontSize: 18, color: colors.azureBlue } },
  { text: 'Azure Durable Functions (Python)', options: { bullet: true, indentLevel: 1 } },
  { text: 'Manages scheduling, provisioning, monitoring', options: { bullet: true, indentLevel: 1 } },
  { text: '', options: { breakLine: true } },
  { text: 'Agent Execution Layer', options: { bullet: false, bold: true, fontSize: 18, color: colors.azureBlue } },
  { text: 'Azure Container Apps with Claude Sonnet 4.5', options: { bullet: true, indentLevel: 1 } },
  { text: '64GB RAM, 2 CPU per agent', options: { bullet: true, indentLevel: 1 } },
  { text: '', options: { breakLine: true } },
  { text: 'Event & Storage Layer', options: { bullet: false, bold: true, fontSize: 18, color: colors.azureBlue } },
  { text: 'Service Bus (real-time streaming)', options: { bullet: true, indentLevel: 1 } },
  { text: 'Cosmos DB (historical logs, 7-day TTL)', options: { bullet: true, indentLevel: 1 } }
], {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 14, fontFace: 'Arial'
});

// Slide 6: Technology Stack
slide = pptx.addSlide();
addSectionHeader(slide, 'Technology Choices');
const techRows = [
  ['Component', 'Technology', 'Why?'],
  ['Orchestrator', 'Durable Functions', 'Long-running workflows, checkpointing'],
  ['Agents', 'Container Apps', 'Isolation, managed, secure secrets'],
  ['AI Model', 'Claude Sonnet 4.5', 'Goal-seeking, troubleshooting'],
  ['Event Bus', 'Service Bus', 'Guaranteed delivery, DLQ'],
  ['Log Storage', 'Cosmos DB', 'Fast queries, TTL, partitioning'],
  ['Secret Management', 'Key Vault', 'RBAC, audit logs, rotation'],
  ['Infrastructure', 'Bicep', 'Azure-native, readable, modular'],
  ['CI/CD', 'GitHub Actions', 'Native OIDC, matrix builds']
];
slide.addTable(techRows, {
  x: 0.5, y: 1.2, w: 9, h: 3.8,
  fontSize: 12, fontFace: 'Arial',
  border: { pt: 1, color: colors.lightGray },
  fill: { color: colors.lightGray },
  color: colors.black,
  align: 'left',
  valign: 'middle',
  rowH: [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4]
});

// Slide 7: Security Model
slide = pptx.addSlide();
addSectionHeader(slide, 'Security Architecture');
slide.addText([
  { text: 'Identity Management', options: { bullet: false, bold: true, fontSize: 16, color: colors.azureBlue } },
  { text: 'Main SP: Orchestrator with Contributor + User Access Admin', options: { bullet: true } },
  { text: 'Scenario SPs: Ephemeral, created per-agent, deleted after cleanup', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: 'Secret Management', options: { bullet: false, bold: true, fontSize: 16, color: colors.azureBlue } },
  { text: 'All secrets in Azure Key Vault', options: { bullet: true } },
  { text: 'Function App uses Key Vault references (NOT direct values)', options: { bullet: true } },
  { text: 'Secrets NEVER visible in Azure Portal', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: 'Audit & Compliance', options: { bullet: false, bold: true, fontSize: 16, color: colors.azureBlue } },
  { text: 'All Azure Activity logged (90 days)', options: { bullet: true } },
  { text: 'Key Vault access logged (2 years)', options: { bullet: true } }
], {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 13, fontFace: 'Arial'
});

// Slide 8: Execution Flow
slide = pptx.addSlide();
addSectionHeader(slide, 'End-to-End Workflow');
slide.addText([
  { text: '1. Timer Trigger (4x daily at 00:00, 06:00, 12:00, 18:00 UTC)', options: { bullet: false } },
  { text: '2. Validation (credentials, APIs, quotas)', options: { bullet: false } },
  { text: '3. Selection (random N scenarios based on simulation_size)', options: { bullet: false } },
  { text: '4. Provisioning (parallel)', options: { bullet: false } },
  { text: 'Create service principals', options: { bullet: true, indentLevel: 1 } },
  { text: 'Deploy Container Apps', options: { bullet: true, indentLevel: 1 } },
  { text: '5. Monitoring (8 hours)', options: { bullet: false } },
  { text: 'Subscribe to Service Bus', options: { bullet: true, indentLevel: 1 } },
  { text: 'Aggregate logs to Cosmos DB', options: { bullet: true, indentLevel: 1 } },
  { text: '6. Cleanup Verification', options: { bullet: false } },
  { text: 'Query Azure Resource Graph', options: { bullet: true, indentLevel: 1 } },
  { text: '7. Forced Cleanup (if needed)', options: { bullet: false } },
  { text: '8. Report Generation & Archival', options: { bullet: false } }
], {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 13, fontFace: 'Arial'
});

// Slide 9: Benefits
slide = pptx.addSlide();
addSectionHeader(slide, 'Key Benefits');
slide.addText([
  { text: 'Continuous Validation', options: { bullet: false, bold: true, fontSize: 18, color: colors.green } },
  { text: '4x daily execution ensures configurations stay compliant', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: 'Zero Manual Effort', options: { bullet: false, bold: true, fontSize: 18, color: colors.green } },
  { text: 'Complete automation from deployment to cleanup', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: 'Cost-Effective', options: { bullet: false, bold: true, fontSize: 18, color: colors.green } },
  { text: 'Automatic cleanup prevents cost accumulation', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: 'Comprehensive Coverage', options: { bullet: false, bold: true, fontSize: 18, color: colors.green } },
  { text: '50+ scenarios across all Azure service categories', options: { bullet: true } }
], {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 14, fontFace: 'Arial'
});

// SECTION B: DEPLOYMENT SLIDES (Slides 10-17)

// Slide 10: Prerequisites
slide = pptx.addSlide();
addSectionHeader(slide, 'Deployment Prerequisites');
slide.addText('Azure Requirements', {
  x: 0.5, y: 1.2, w: 4.5, h: 0.3,
  fontSize: 18, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: 'Active subscription with quota', options: { bullet: true } },
  { text: 'Owner or Contributor role', options: { bullet: true } },
  { text: 'Function Apps (Premium tier)', options: { bullet: true } },
  { text: 'Container Apps (64GB instances)', options: { bullet: true } }
], {
  x: 0.5, y: 1.6, w: 4.5, h: 1.8,
  fontSize: 14, fontFace: 'Arial'
});
slide.addText('Tools Required', {
  x: 5.5, y: 1.2, w: 4.5, h: 0.3,
  fontSize: 18, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: 'Azure CLI (latest)', options: { bullet: true } },
  { text: 'Bicep CLI (latest)', options: { bullet: true } },
  { text: 'GitHub CLI (optional)', options: { bullet: true } },
  { text: 'Anthropic API key', options: { bullet: true } }
], {
  x: 5.5, y: 1.6, w: 4.5, h: 1.8,
  fontSize: 14, fontFace: 'Arial'
});

// Slide 11: GitOps Workflow
slide = pptx.addSlide();
addSectionHeader(slide, 'GitOps Continuous Deployment');
try {
  slide.addImage({
    path: path.join(__dirname, '../presentation-assets/diagrams/04-gitops-workflow.png'),
    x: 0.5, y: 1.2, w: 9, h: 3.5
  });
} catch (e) {
  slide.addText('GitOps Workflow Diagram\n[Diagram: 04-gitops-workflow.png]', {
    x: 0.5, y: 1.5, w: 9, h: 3.5,
    fontSize: 14, fontFace: 'Courier New', align: 'center', valign: 'middle',
    fill: { color: colors.lightGray }
  });
}

// Slide 12: GitHub Actions Pipeline
slide = pptx.addSlide();
addSectionHeader(slide, 'CI/CD Pipeline Stages');
slide.addText([
  { text: 'Stage 1: Validate', options: { bullet: false, bold: true } },
  { text: 'Bicep template validation, syntax checks', options: { bullet: true, indentLevel: 1 } },
  { text: 'Stage 2: Test', options: { bullet: false, bold: true } },
  { text: 'pytest (276 tests), ruff, pyright', options: { bullet: true, indentLevel: 1 } },
  { text: 'Stage 3: Deploy Infrastructure', options: { bullet: false, bold: true } },
  { text: 'Create RG, deploy Bicep, inject secrets, wait for RBAC (60s)', options: { bullet: true, indentLevel: 1 } },
  { text: 'Stage 4: Deploy Function App', options: { bullet: false, bold: true } },
  { text: 'Package Python, deploy, configure, restart', options: { bullet: true, indentLevel: 1 } },
  { text: 'Stage 5: Smoke Tests', options: { bullet: false, bold: true } },
  { text: 'Verify Function responding, Key Vault access, Service Bus', options: { bullet: true, indentLevel: 1 } }
], {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 13, fontFace: 'Arial'
});
slide.addText('Duration: ~10-15 minutes per deployment', {
  x: 0.5, y: 5.3, w: 9, h: 0.3,
  fontSize: 12, italic: true, color: colors.gray, fontFace: 'Arial'
});

// Slide 13: Bicep Infrastructure
slide = pptx.addSlide();
addSectionHeader(slide, 'Infrastructure as Code (Bicep)');
slide.addText('Modular Design', {
  x: 0.5, y: 1.2, w: 9, h: 0.3,
  fontSize: 18, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: 'infra/bicep/', options: { bullet: false, fontFace: 'Courier New' } },
  { text: '├── main.bicep (Orchestrates all modules)', options: { bullet: false, fontFace: 'Courier New', indentLevel: 1 } },
  { text: '├── parameters/ (dev, staging, prod)', options: { bullet: false, fontFace: 'Courier New', indentLevel: 1 } },
  { text: '└── modules/', options: { bullet: false, fontFace: 'Courier New', indentLevel: 1 } },
  { text: '    ├── function-app.bicep', options: { bullet: false, fontFace: 'Courier New', indentLevel: 2 } },
  { text: '    ├── keyvault.bicep', options: { bullet: false, fontFace: 'Courier New', indentLevel: 2 } },
  { text: '    ├── servicebus.bicep', options: { bullet: false, fontFace: 'Courier New', indentLevel: 2 } },
  { text: '    ├── cosmosdb.bicep', options: { bullet: false, fontFace: 'Courier New', indentLevel: 2 } },
  { text: '    └── monitoring.bicep', options: { bullet: false, fontFace: 'Courier New', indentLevel: 2 } }
], {
  x: 0.5, y: 1.6, w: 9, h: 2.5,
  fontSize: 12, fontFace: 'Arial'
});
slide.addText('Key Features: Idempotent, Parameterized, Optional resources for dev', {
  x: 0.5, y: 4.5, w: 9, h: 0.5,
  fontSize: 13, fontFace: 'Arial'
});

// Slide 14: Environment Configuration
slide = pptx.addSlide();
addSectionHeader(slide, 'Environment Differences');
const envRows = [
  ['Aspect', 'Dev', 'Staging', 'Prod'],
  ['Function App', 'Consumption', 'Premium (EP1)', 'Elastic (EP2)'],
  ['Simulation Size', '5 scenarios', '15 scenarios', '30 scenarios'],
  ['Schedule', 'On startup', '2x daily', '4x daily'],
  ['Cosmos DB', 'Optional', 'Serverless', 'Provisioned'],
  ['Cost/Month', '$50-100', '$200-400', '$800-1200']
];
slide.addTable(envRows, {
  x: 0.5, y: 1.2, w: 9, h: 3,
  fontSize: 13, fontFace: 'Arial',
  border: { pt: 1, color: colors.lightGray },
  fill: { color: colors.lightGray },
  align: 'center',
  valign: 'middle'
});

// Slide 15: Secret Management (THE FIX)
slide = pptx.addSlide();
addSectionHeader(slide, 'Secret Management - THE FIX');
slide.addText('BEFORE (Insecure)', {
  x: 0.5, y: 1.2, w: 4.5, h: 0.3,
  fontSize: 16, bold: true, color: colors.red, fontFace: 'Arial'
});
slide.addText('az functionapp config appsettings set\n  --settings ANTHROPIC_API_KEY="sk-ant-..."\n\n❌ EXPOSED in Azure Portal!', {
  x: 0.5, y: 1.6, w: 4.5, h: 1.5,
  fontSize: 11, fontFace: 'Courier New',
  fill: { color: 'FFE6E6' }
});
slide.addText('AFTER (Secure)', {
  x: 0.5, y: 3.3, w: 4.5, h: 0.3,
  fontSize: 16, bold: true, color: colors.green, fontFace: 'Arial'
});
slide.addText('Step 1: Inject to Key Vault\naz keyvault secret set --vault-name $KV\n  --name anthropic-api-key\n  --value "$ANTHROPIC_API_KEY"\n\nStep 2: Function App references KV\nvalue: @Microsoft.KeyVault(\n  VaultName=...; SecretName=...)\n\n✅ NEVER visible in Portal!', {
  x: 0.5, y: 3.7, w: 4.5, h: 2,
  fontSize: 10, fontFace: 'Courier New',
  fill: { color: 'E6FFE6' }
});
slide.addText('Benefits', {
  x: 5.5, y: 1.2, w: 4.5, h: 0.3,
  fontSize: 16, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: 'Secrets NEVER visible in Portal', options: { bullet: true } },
  { text: 'Consistent across ALL environments', options: { bullet: true } },
  { text: 'Automatic rotation support', options: { bullet: true } },
  { text: 'Audit logs in Key Vault', options: { bullet: true } },
  { text: 'RBAC-controlled access', options: { bullet: true } }
], {
  x: 5.5, y: 1.6, w: 4.5, h: 2.5,
  fontSize: 13, fontFace: 'Arial'
});

// Slide 16: Deployment Steps
slide = pptx.addSlide();
addSectionHeader(slide, 'Deployment Steps');
slide.addText([
  { text: '1. Fork repository and clone', options: { bullet: false, bold: true } },
  { text: '2. Create service principal with Contributor role', options: { bullet: false, bold: true } },
  { text: 'az ad sp create-for-rbac --name AzureHayMaker-Main', options: { bullet: true, indentLevel: 1, fontFace: 'Courier New' } },
  { text: '3. Configure GitHub OIDC federated credentials', options: { bullet: false, bold: true } },
  { text: 'scripts/setup-oidc.sh', options: { bullet: true, indentLevel: 1, fontFace: 'Courier New' } },
  { text: '4. Add GitHub Secrets', options: { bullet: false, bold: true } },
  { text: 'AZURE_TENANT_ID, AZURE_CLIENT_ID, ANTHROPIC_API_KEY, etc.', options: { bullet: true, indentLevel: 1 } },
  { text: '5. Push to develop branch', options: { bullet: false, bold: true } },
  { text: 'GitHub Actions automatically deploys to dev environment', options: { bullet: true, indentLevel: 1 } },
  { text: '6. Verify deployment', options: { bullet: false, bold: true } },
  { text: 'haymaker status', options: { bullet: true, indentLevel: 1, fontFace: 'Courier New' } }
], {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 13, fontFace: 'Arial'
});

// Slide 17: Troubleshooting
slide = pptx.addSlide();
addSectionHeader(slide, 'Common Deployment Issues');
const troubleRows = [
  ['Issue', 'Solution'],
  ['Bicep validation fails', 'Run az deployment group validate locally'],
  ['RBAC access denied', 'Wait 60s for propagation, retry'],
  ['Container Registry unavailable', 'Use Basic tier or skip for dev'],
  ['Cosmos DB region error', 'Change region or use Table Storage'],
  ['Key Vault access denied', 'Check RBAC assignments and firewall'],
  ['Function App won\'t start', 'Verify Key Vault references correct']
];
slide.addTable(troubleRows, {
  x: 0.5, y: 1.2, w: 9, h: 3.5,
  fontSize: 12, fontFace: 'Arial',
  border: { pt: 1, color: colors.lightGray },
  fill: { color: colors.lightGray },
  align: 'left',
  valign: 'middle',
  rowH: [0.4, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
});

// SECTION C: CLI USAGE (Slides 18-25)

// Slide 18: CLI Installation
slide = pptx.addSlide();
addSectionHeader(slide, 'Installing the CLI');
slide.addText('# Install uv package manager\ncurl -LsSf https://astral.sh/uv/install.sh | sh\n\n# Clone repository\ngit clone https://github.com/your-org/AzureHayMaker.git\ncd AzureHayMaker/cli\n\n# Install CLI and dependencies\nuv sync\n\n# Verify installation\nuv run haymaker --help', {
  x: 0.5, y: 1.2, w: 9, h: 3.5,
  fontSize: 13, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});
slide.addText('Requirements: Python 3.11+, Network access to Function App API', {
  x: 0.5, y: 5, w: 9, h: 0.3,
  fontSize: 12, italic: true, color: colors.gray, fontFace: 'Arial'
});

// Slide 19: CLI Configuration
slide = pptx.addSlide();
addSectionHeader(slide, 'Configuring the CLI');
slide.addText('# Set Function App endpoint\nuv run haymaker config set endpoint \\\n  https://haymaker-dev-func.azurewebsites.net\n\n# View configuration\nuv run haymaker config list\n\n# Test connection\nuv run haymaker status\n\n# Output:\n✓ Orchestrator: Running\n✓ Last execution: 2025-11-17 12:00 UTC\n✓ Next scheduled: 2025-11-17 18:00 UTC\n✓ Active agents: 5\n✓ Pending cleanup: 0 resources', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 12, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 20: Status Command
slide = pptx.addSlide();
addSectionHeader(slide, 'Checking Orchestrator Status');
slide.addText('uv run haymaker status\n\n┌─────────────────────────────────────────┐\n│       Azure HayMaker Status             │\n├─────────────────────────────────────────┤\n│ Orchestrator Status:   ✓ Running        │\n│ Current Run ID:        run-2025-11-17   │\n│ Execution Started:     12:00:00 UTC     │\n│ Time Remaining:        3h 25m            │\n│                                         │\n│ Active Agents:         5 running         │\n│ Completed Agents:      0                │\n│ Resources Created:     127              │\n│                                         │\n│ Next Scheduled Run:    18:00:00 UTC     │\n└─────────────────────────────────────────┘', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 11, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 21: Agents List Command
slide = pptx.addSlide();
addSectionHeader(slide, 'Viewing Agent Execution');
slide.addText('uv run haymaker agents list\n\n┌─────────────┬──────────────┬─────────┬──────────┐\n│ Agent ID    │ Scenario     │ Status  │ Duration │\n├─────────────┼──────────────┼─────────┼──────────┤\n│ agent-abc   │ compute-01   │ Running │ 3h 20m   │\n│ agent-def   │ storage-01   │ Running │ 3h 18m   │\n│ agent-ghi   │ network-01   │ Running │ 3h 15m   │\n│ agent-jkl   │ ai-ml-01     │ Running │ 3h 13m   │\n│ agent-mno   │ database-01  │ Running │ 3h 10m   │\n└─────────────┴──────────────┴─────────┴──────────┘\n\n# Get details for specific agent\nuv run haymaker agents get agent-abc', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 11, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 22: Logs Command (Tail)
slide = pptx.addSlide();
addSectionHeader(slide, 'Viewing Agent Logs');
slide.addText('# Tail last 50 log entries\nuv run haymaker logs --agent-id agent-abc --tail 50\n\n┌──────────────────────────────────────────────┐\n│         Agent Logs: agent-abc                │\n├───────────┬────────┬─────────────────────────┤\n│ Timestamp │ Level  │ Message                 │\n├───────────┼────────┼─────────────────────────┤\n│ 12:05:23  │ INFO   │ Starting scenario       │\n│ 12:05:45  │ INFO   │ Resource group created  │\n│ 12:06:12  │ INFO   │ Virtual network created │\n│ 12:07:01  │ INFO   │ VM deployed             │\n│ 12:08:45  │ INFO   │ Web server accessible   │\n│ 15:25:34  │ INFO   │ Initiating cleanup      │\n│ 15:26:01  │ INFO   │ Cleanup completed ✓     │\n└───────────┴────────┴─────────────────────────┘', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 11, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 23: Logs Command (Follow)
slide = pptx.addSlide();
addSectionHeader(slide, 'Streaming Logs in Real-Time');
slide.addText('# Follow logs in real-time (like tail -f)\nuv run haymaker logs --agent-id agent-abc --follow\n\nFollowing logs for agent-abc (Ctrl+C to exit)\n\n12:05:23 INFO     Starting scenario: compute-01\n12:05:45 INFO     Resource group created\n12:06:12 INFO     Virtual network created\n12:06:34 INFO     NSG configured\n12:07:01 INFO     Virtual machine deployed\n12:07:23 WARNING  Public IP exposed (expected)\n12:08:45 INFO     Web server accessible\n12:09:12 INFO     Security validation: PASSED\n# ... logs continue streaming ...\n\n• Default poll interval: 5 seconds\n• Displays logs immediately as they arrive\n• Perfect for debugging live executions', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 11, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 24: Resources Command
slide = pptx.addSlide();
addSectionHeader(slide, 'Listing Deployed Resources');
slide.addText('# List resources by scenario\nuv run haymaker resources list --scenario compute-01\n\n┌─────────────────┬───────────────┬────────┐\n│ Resource Type   │ Resource Name │ Status │\n├─────────────────┼───────────────┼────────┤\n│ Resource Group  │ rg-agent-abc  │ Active │\n│ Virtual Network │ vnet-web      │ Active │\n│ NSG             │ nsg-web       │ Active │\n│ Public IP       │ pip-web       │ Active │\n│ Virtual Machine │ vm-web-server │ Running│\n└─────────────────┴───────────────┴────────┘\n\n# List ALL resources across ALL agents\nuv run haymaker resources list --all', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 11, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 25: Deploy On-Demand
slide = pptx.addSlide();
addSectionHeader(slide, 'Deploying Scenarios On-Demand');
slide.addText('# Deploy specific scenario immediately\nuv run haymaker deploy --scenario compute-01-linux-vm\n\n⏳ Step 1: Creating service principal...\n✓ Service principal created\n\n⏳ Step 2: Assigning roles...\n⏳ Waiting 60s for RBAC propagation...\n✓ Roles assigned\n\n⏳ Step 3: Deploying container app...\n✓ Container app deployed\n\n⏳ Step 4: Starting agent execution...\n✓ Agent started successfully\n\nAgent ID: agent-abc123\nScenario: compute-01-linux-vm\nStatus: Running', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 11, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// SECTION D: DEMO (Slides 26-31)

// Slide 26: Demo Scenario
slide = pptx.addSlide();
addSectionHeader(slide, 'Demo: Linux VM Web Server');
slide.addText('Scenario: compute-01-linux-vm-web-server', {
  x: 0.5, y: 1.2, w: 9, h: 0.3,
  fontSize: 18, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: 'Phase 1: Deploy (5-7 minutes)', options: { bullet: false, bold: true, fontSize: 16 } },
  { text: 'Create resource group, VNet, NSG, Ubuntu VM', options: { bullet: true } },
  { text: 'Assign public IP, install Nginx web server', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: 'Phase 2: Operate (8 hours)', options: { bullet: false, bold: true, fontSize: 16 } },
  { text: 'Serve HTTP traffic, generate logs, health checks', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: 'Phase 3: Cleanup (2-3 minutes)', options: { bullet: false, bold: true, fontSize: 16 } },
  { text: 'Stop VM, delete all resources, verify cleanup', options: { bullet: true } }
], {
  x: 0.5, y: 1.6, w: 9, h: 3.5,
  fontSize: 13, fontFace: 'Arial'
});

// Slide 27: Demo - Deployment
slide = pptx.addSlide();
addSectionHeader(slide, 'Starting the Agent');
slide.addText('uv run haymaker deploy --scenario compute-01 --wait\n\nDeploying scenario: compute-01-linux-vm\n\n⏳ Creating service principal...\n✓ SP created: AzureHayMaker-compute-01-admin\n\n⏳ Assigning roles (Contributor + User Access)...\n⏳ Waiting 60s for RBAC propagation...\n✓ Roles assigned\n\n⏳ Deploying container app...\n✓ Container deployed: ca-agent-abc123\n  Resources: 64GB RAM, 2 CPU\n  Image: haymaker.azurecr.io/agent:latest\n\n⏳ Starting agent execution...\n✓ Agent started successfully', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 11, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 28: Demo - Execution Logs
slide = pptx.addSlide();
addSectionHeader(slide, 'Watching the Agent Work');
slide.addText('uv run haymaker logs --agent-id agent-abc123 --follow\n\n15:30:45 INFO  Starting scenario: compute-01\n15:30:45 INFO  Phase 1: Deployment\n15:31:12 INFO  Creating resource group: rg-agent-abc\n15:31:34 INFO  ✓ Resource group created\n15:32:01 INFO  Deploying virtual network (10.0.0.0/16)\n15:32:23 INFO  ✓ VNet created with subnet\n15:32:45 INFO  Configuring NSG: Allow HTTP, SSH\n15:33:01 INFO  ✓ NSG configured\n15:34:12 INFO  Deploying VM: Standard_D2s_v3\n15:36:45 INFO  ✓ VM deployed (2m 33s)\n15:37:01 INFO  Assigning public IP: 40.112.45.67\n15:37:45 INFO  Installing Nginx via cloud-init\n15:38:23 INFO  ✓ Nginx started\n15:38:45 INFO  Testing web server...\n15:38:47 INFO  ✓ HTTP 200 OK\n15:38:50 INFO  Phase 2: Operations (8 hours)', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 10, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 29: Demo - Resources Created
slide = pptx.addSlide();
addSectionHeader(slide, 'Resources in Azure Portal');
slide.addText('Azure Portal View: Resource Group', {
  x: 0.5, y: 1.2, w: 9, h: 0.3,
  fontSize: 16, bold: true, fontFace: 'Arial'
});
slide.addText([
  { text: '5 Resources Created:', options: { bullet: false, bold: true } },
  { text: '', options: { breakLine: true } },
  { text: '1. Resource Group: rg-agent-abc123-westus2', options: { bullet: true } },
  { text: '2. Virtual Network: vnet-web (10.0.0.0/16)', options: { bullet: true } },
  { text: '3. Network Security Group: nsg-web', options: { bullet: true } },
  { text: '   • Allow HTTP (80) from Internet', options: { bullet: true, indentLevel: 1 } },
  { text: '   • Allow SSH (22) from home IP', options: { bullet: true, indentLevel: 1 } },
  { text: '4. Public IP Address: pip-web (40.112.45.67)', options: { bullet: true } },
  { text: '5. Virtual Machine: vm-web-server (Running)', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: 'All resources tagged:', options: { bullet: false, bold: true } },
  { text: 'AzureHayMaker-managed: true', options: { bullet: true, fontFace: 'Courier New' } },
  { text: 'Scenario: compute-01-linux-vm', options: { bullet: true, fontFace: 'Courier New' } },
  { text: 'Agent: agent-abc123', options: { bullet: true, fontFace: 'Courier New' } }
], {
  x: 0.5, y: 1.6, w: 9, h: 3.5,
  fontSize: 12, fontFace: 'Arial'
});

// Slide 30: Demo - Cleanup
slide = pptx.addSlide();
addSectionHeader(slide, 'Autonomous Cleanup');
slide.addText('uv run haymaker agents get agent-abc123\n\nAgent ID: agent-abc123\nScenario: compute-01-linux-vm\nStatus: Completed\nStarted: 2025-11-17 15:30:45 UTC\nEnded: 2025-11-17 15:46:19 UTC\nDuration: 15m 34s\n\nResources:\n  Created: 5 resources\n  Cleaned: 5 resources\n  Cleanup Status: ✓ Verified\n\nOrchestrator Cleanup Report:\n┌───────────────────────────────────────┐\n│     Cleanup Verification Report       │\n├───────────────────────────────────────┤\n│ Expected Deletions:  5 resources      │\n│ Actual Deletions:    5 resources      │\n│ Forced Deletions:    0 resources      │\n│ Service Principal:   ✓ Deleted        │\n│ Cleanup Status:      ✓ VERIFIED       │\n└───────────────────────────────────────┘', {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 10, fontFace: 'Courier New',
  fill: { color: colors.lightGray }
});

// Slide 31: Key Takeaways
slide = pptx.addSlide();
addSectionHeader(slide, 'Summary');
slide.addText([
  { text: '1. Autonomous Security Testing', options: { bullet: false, bold: true, fontSize: 16 } },
  { text: '50+ scenarios, self-provisioning, zero manual intervention', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: '2. Production-Ready Architecture', options: { bullet: false, bold: true, fontSize: 16 } },
  { text: 'Durable Functions, Container Apps, Key Vault, Cosmos DB', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: '3. GitOps-Driven Deployment', options: { bullet: false, bold: true, fontSize: 16 } },
  { text: 'Infrastructure as Code, automated CI/CD, consistent secrets', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: '4. Real-Time Monitoring', options: { bullet: false, bold: true, fontSize: 16 } },
  { text: 'CLI for management, streaming logs, resource tracking', options: { bullet: true } },
  { text: '', options: { breakLine: true } },
  { text: '5. Cost-Effective', options: { bullet: false, bold: true, fontSize: 16 } },
  { text: 'Automatic cleanup prevents cost accumulation', options: { bullet: true } }
], {
  x: 0.5, y: 1.2, w: 9, h: 4,
  fontSize: 13, fontFace: 'Arial'
});

// Slide 32: Q&A
slide = pptx.addSlide();
addSectionHeader(slide, 'Questions & Resources');
slide.addText('Resources', {
  x: 0.5, y: 1.2, w: 4.5, h: 0.3,
  fontSize: 18, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText([
  { text: 'GitHub Repository:', options: { bullet: true } },
  { text: '  github.com/your-org/AzureHayMaker', options: { fontFace: 'Courier New', fontSize: 11 } },
  { text: '', options: { breakLine: true } },
  { text: 'Documentation:', options: { bullet: true } },
  { text: '  /docs directory (comprehensive)', options: { fontSize: 11 } },
  { text: '', options: { breakLine: true } },
  { text: 'Architecture Guide:', options: { bullet: true } },
  { text: '  specs/architecture.md', options: { fontFace: 'Courier New', fontSize: 11 } },
  { text: '', options: { breakLine: true } },
  { text: 'Deployment Guide:', options: { bullet: true } },
  { text: '  docs/GITOPS_SETUP.md', options: { fontFace: 'Courier New', fontSize: 11 } }
], {
  x: 0.5, y: 1.6, w: 4.5, h: 3,
  fontSize: 12, fontFace: 'Arial'
});
slide.addText('Thank You!', {
  x: 5.5, y: 1.2, w: 4.5, h: 0.5,
  fontSize: 32, bold: true, color: colors.azureBlue, fontFace: 'Arial'
});
slide.addText('Questions?\nFeedback welcome!\n\nLet\'s discuss demos,\ndeployment strategies,\nor specific scenarios.', {
  x: 5.5, y: 2, w: 4.5, h: 2.5,
  fontSize: 16, fontFace: 'Arial', align: 'center'
});

// Save presentation
const outputPath = '/Users/ryan/src/AzureHayMaker/docs/presentations/Azure_HayMaker_Overview.pptx';
pptx.writeFile({ fileName: outputPath })
  .then(() => {
    console.log(`✓ Presentation created: ${outputPath}`);
    console.log(`  Total slides: 32`);
    console.log(`  Sections: Overview (9), Deployment (8), CLI (8), Demo (6), Closing (1)`);
  })
  .catch(err => {
    console.error('Error creating presentation:', err);
    process.exit(1);
  });
