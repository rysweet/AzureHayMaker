# Deploying 128GB Orchestrator VM

**Captain's specification: 128GB RAM preferred**

---

## VM Specifications

**Size**: Standard_E16s_v3
- **RAM**: 128 GB
- **vCPU**: 16 cores
- **Storage**: Premium SSD
- **Cost**: ~$876/month

**Why 128GB?**
- Azure SDK initialization: 60-70GB required
- Overhead and buffers: 20-30GB
- **Total need**: 90-100GB minimum
- **128GB**: Comfortable margin (Captain's preferred!)

---

## Deployment Options

### Option A: Azure Portal (Recommended - 30 min)
```bash
./deploy-vm-portal-guide.sh
```

Follow on-screen instructions to create VM via Portal.

### Option B: Azure CLI with Bicep (If loadTextContent works)
```bash
az deployment group create \
  --resource-group haymaker-dev-rg \
  --template-file infra/bicep/main-vm.bicep \
  --parameters infra/bicep/parameters/vm-128gb-dev.bicepparam
```

### Option C: Simple Azure CLI
```bash
az vm create \
  --resource-group haymaker-dev-rg \
  --name haymaker-orchestrator-128gb \
  --size Standard_E16s_v3 \
  --image Canonical:0001-com-ubuntu-server-noble:24_04-lts-gen2:latest \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard \
  --assign-identity \
  --location westus2
```

**Note**: Using `--generate-ssh-keys` avoids parameter escaping!

---

## After Deployment

1. Get VM IP:
```bash
az vm list-ip-addresses -g haymaker-dev-rg -n haymaker-orchestrator-128gb --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv
```

2. SSH into VM:
```bash
ssh azureuser@<IP>
```

3. Follow: `NEXT_STEPS.md` for orchestrator setup

---

## Verification

Once orchestrator running:
- Check memory usage: `free -h` (should show 128GB total)
- Monitor during startup: `top` or `htop`
- Verify no crashes: Check logs
- Test agent execution: Run one scenario

---

**Tracked in**: Issue #15
