# Simple VM Deployment for Orchestrator (64GB RAM)

## Quick Command (No Bicep Issues!)

```bash
az vm create \
  --resource-group haymaker-dev-rg \
  --name haymaker-dev-orchestrator-vm \
  --size Standard_E8s_v3 \
  --image Canonical:0001-com-ubuntu-server-noble:24_04-lts-gen2:latest \
  --admin-username azureuser \
  --ssh-key-values ~/.ssh/haymaker-orchestrator-key.pub \
  --public-ip-sku Standard \
  --assign-identity \
  --location westus2
```

**Specs**: 64GB RAM, 8 vCPU, Ubuntu 24.04 LTS

**After Creation**:
1. Get IP: `az vm list-ip-addresses -g haymaker-dev-rg -n haymaker-dev-orchestrator-vm`
2. SSH: `ssh -i ~/.ssh/haymaker-orchestrator-key azureuser@<IP>`
3. Setup: Follow NEXT_STEPS.md

**Estimated Time**: 5-10 minutes
