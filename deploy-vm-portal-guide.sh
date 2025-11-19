#!/bin/bash
# Azure HayMaker - VM Deployment via Portal (Automated Instructions)

cat <<'EOF'

📋 AZURE PORTAL VM DEPLOYMENT - STEP-BY-STEP

1. Open Azure Portal: https://portal.azure.com
2. Click "Create a resource"
3. Search for "Ubuntu Server 24.04 LTS"
4. Click "Create"

CONFIGURATION:
================
Resource Group: haymaker-dev-rg
VM Name: haymaker-dev-orchestrator-vm
Region: West US 2
Size: Standard_E8s_v3 (64GB RAM, 8 vCPU)
  - Click "See all sizes"
  - Search "E8s_v3"
  - Select Standard_E8s_v3

Authentication:
  - Type: SSH public key
  - Username: azureuser
  - SSH Public Key: (paste from below)

NETWORKING:
================
Public IP: Yes (Standard SKU)
NSG: Allow SSH (22) and HTTPS (443)

MANAGEMENT:
================
Identity: System-assigned managed identity (Enable)
Auto-shutdown: Disabled
Monitoring: Enable

TAGS:
================
Environment: dev
Project: AzureHayMaker
ManagedBy: Portal
DeployedBy: Manual

5. Review + Create
6. Wait 5-10 minutes
7. Get IP address and SSH

SSH PUBLIC KEY TO USE:
================
EOF

cat ~/.ssh/haymaker-orchestrator-key.pub

cat <<'EOF'

AFTER VM CREATED:
================
ssh -i ~/.ssh/haymaker-orchestrator-key azureuser@<VM-IP>

Then follow: NEXT_STEPS.md

EOF
