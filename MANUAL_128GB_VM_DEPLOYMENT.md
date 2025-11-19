# Manual 128GB VM Deployment - Azure Portal

**Since Azure CLI has parameter escaping issues, use Portal**

---

## 🎯 Quick Portal Deployment (30 minutes)

### Step 1: Navigate to Azure Portal
1. Open: https://portal.azure.com
2. Click: "Create a resource"
3. Search: "Ubuntu Server 24.04 LTS"
4. Click: "Create" → "Virtual machine"

### Step 2: Basics Configuration

**Project details**:
- Subscription: (Your Azure subscription)
- Resource group: `haymaker-dev-rg`

**Instance details**:
- Virtual machine name: `haymaker-orchestrator-128gb`
- Region: `(US) West US 2`
- Availability options: No infrastructure redundancy required
- Security type: Standard
- Image: Ubuntu Server 24.04 LTS - Gen2

**Size** (CRITICAL!):
- Click "See all sizes"
- Search: "E16s_v3"
- Select: **Standard_E16s_v3**
  - 16 vCPUs
  - 128 GiB RAM
  - **THIS IS THE KEY REQUIREMENT!**

**Administrator account**:
- Authentication type: SSH public key
- Username: `azureuser`
- SSH public key source: Use existing public key
- SSH public key: 
```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDXL/CnsziUa6Rn/xoFq+HiyLx++q29ersziJIQ/Yz4LRSoscF6cw/tYkf7rORv0LYD6jf9AcOSi62eJnB6hZr353WcPssM3xmPc/PjLMV1lZGe6Y50tZBj9HXObE/+ox+Djtvnb1LiHZYiYHDMKZXe5F3WZb2PxTvQUuHftjhgW57Aekedxz2Vrguo2k0fAjKjXL9Vr6YciY3Ppy4vC15yR9TR/bvKj188vR2JXgjfRfX//KuFjS4dbhz0XIhT1D8TPgEq5ES3PHvBalknGqwFDZZ2pBYn9tDc1ZjzPEJer8Q80qOOVYnA4wywx6mA9HBfa/48qpMGG1ulr5JPKoE2iGyYWSnk/+UODgLgqKkC4M2PyHZZ+EJ9PNGxpHyMT8NuEm3kxAbFsHLEhQYofALGjA46Me/BEoP5+jvoeX8onZfTosYGUgImcAAKQahpNCUFrxE30QhIi/YAA6SzywKKeEmuBxdhPeE+hWGGKzU9Fna26gSA63sWqlx52JjRfSovdmA2HX22Z0AipRBFYpLnaFRAaWPNQhkGO8OaEkpXCjbKQYzc5oc0HYPvS4zSXOaewITLuhzVxs/XtrZnbjyr5DmrrN11jqD89OylDFPFSLUXAbVQ13ZXnPmao+qfeQQy2dof3P/2XzyjCWHelPO3KuEsZ5hv2RsAvc3w3l+P+Q== haymaker-orchestrator
```

### Step 3: Disks
- OS disk type: Premium SSD (default)
- Delete with VM: Yes

### Step 4: Networking
- Virtual network: Create new or use existing
- Public IP: Create new (Standard SKU)
- NIC network security group: Basic
- Public inbound ports: Allow selected ports
- Select inbound ports: SSH (22), HTTPS (443)

### Step 5: Management
- Identity: **System assigned managed identity** = ON (Important!)
- Enable auto-shutdown: Off
- Enable backup: Off (optional for dev)

### Step 6: Monitoring
- Boot diagnostics: Enable
- OS guest diagnostics: Off (optional)

### Step 7: Advanced
- Leave defaults

### Step 8: Tags
- Environment: `dev`
- Project: `AzureHayMaker`
- Orchestrator: `true`
- RAM: `128GB`

### Step 9: Review + Create
- Review settings
- Ensure **Standard_E16s_v3** size is shown
- Click "Create"
- Wait 5-10 minutes

---

## After VM Created

### Get IP Address
```bash
az vm list-ip-addresses -g haymaker-dev-rg -n haymaker-orchestrator-128gb \
  --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv
```

### SSH Into VM
```bash
# Use generated key
ssh -i ~/.ssh/id_rsa azureuser@<IP>

# Or use our specific key
ssh -i ~/.ssh/haymaker-orchestrator-key azureuser@<IP>
```

### Grant Key Vault Access
```bash
# Get VM principal ID
VM_PRINCIPAL=$(az vm show -n haymaker-orchestrator-128gb -g haymaker-dev-rg --query identity.principalId -o tsv)

# Grant Key Vault Secrets User role
az role assignment create \
  --assignee $VM_PRINCIPAL \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/<subscription-id>/resourceGroups/haymaker-dev-rg/providers/Microsoft.KeyVault/vaults/haymaker-dev-yow3ex-kv
```

### Setup Orchestrator
Follow: `NEXT_STEPS.md` for complete setup instructions

---

## Verification

Once deployed:
```bash
# Check VM exists
az vm show -n haymaker-orchestrator-128gb -g haymaker-dev-rg --query "{name:name, size:hardwareProfile.vmSize}" -o json

# Should show:
# {
#   "name": "haymaker-orchestrator-128gb",
#   "size": "Standard_E16s_v3"
# }
```

---

**This is the reliable path to 128GB VM deployment!**

**Estimated time**: 30 minutes

🏴‍☠️ Fair winds! ⚓
