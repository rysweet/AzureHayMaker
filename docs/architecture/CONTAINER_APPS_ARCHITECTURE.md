---
layout: default
title: Container Apps
parent: Architecture
nav_order: 4
description: "Azure Container Apps architecture for agent execution"
permalink: /architecture/container-apps/
---

# Container Apps Architecture
{: .no_toc }

Architecture for Azure Container Apps deployment and agent execution.
{: .fs-6 .fw-300 }

1. TOC
{:toc}

---

**Requirements Implemented**

---

## 🎯 Architecture Overview

### Orchestrator
- **Platform**: Azure Container Apps
- **Workload Profile**: E16 (128GB RAM, 16 vCPU)
- **Scheduling**: KEDA CRON (4x daily + startup trigger)
- **Scaling**: 0-1 replicas (scale to zero when idle)
- **Environment**: Same for dev and prod

### Agent Containers
- **Platform**: Azure Container Apps
- **Memory**: 64GB RAM per container (already configured)
- **CPU**: 2 vCPU per container
- **NODE_OPTIONS**: --max-old-space-size=32768 (32GB heap)
- **Scaling**: Dynamic based on orchestrator demands

---

## 📊 Specifications

### Orchestrator Container App
```
Name: haymaker-{env}-{suffix}-orchestrator
Workload Profile: E16
- RAM: 128 GB
- vCPU: 16 cores
- Min Replicas: 0
- Max Replicas: 1

KEDA CRON Rules:
1. Scheduled: "0 0,6,12,18 * * *" (4x daily)
2. Startup: "@reboot"

Environment Variables:
- All Azure config
- Key Vault references for secrets
- Service Bus, Storage, Cosmos DB
- NODE_OPTIONS: --max-old-space-size=32768
```

### Agent Containers
```
Memory: 64 GB per container
CPU: 2 cores per container
Environment Variables:
- Azure credentials (via Key Vault)
- Scenario configuration
- NODE_OPTIONS: --max-old-space-size=32768
```

---

## ✅ Why This Architecture

### Meets All Requirements
1. ✅ **Dedicated Plan**: E16 workload profile (dedicated hardware)
2. ✅ **128GB RAM**: Captain's preferred specification
3. ✅ **Scheduled Execution**: KEDA CRON (4x daily + startup)
4. ✅ **NODE_OPTIONS**: Added to all containers (32GB heap)
5. ✅ **GitOps**: Fully automated via Bicep
6. ✅ **Same Sizes**: dev and prod both use E16

### Advantages over Function App
- Higher memory limit (128GB vs 14GB max)
- Dedicated hardware guarantee
- Better for long-running processes
- Scales to zero when idle
- Native KEDA support

### Advantages over Bare VM
- Managed service (no VM maintenance)
- Auto-scaling built-in
- Integrated with Azure ecosystem
- Easier to deploy and manage
- GitOps friendly

---

## 💰 Cost Comparison

### Container Apps E16 (This Architecture)
- **E16 Workload Profile**: ~$876/month (128GB, 16 vCPU)
- **Supporting Services**: ~$100/month
- **Total**: ~$976/month

### vs Current State
- **Current Waste**: $2,164/month (21 duplicate sets)
- **After Cleanup**: $976/month
- **Savings**: $1,188/month ($14,256/year!)

### vs VM
- **VM E16s_v3**: ~$876/month
- **Container Apps E16**: ~$876/month
- **Same cost, better management!**

---

## 🏗️ Infrastructure Components

```
GitHub Actions (GitOps)
    ↓
Container Apps Environment
├─ E16 Workload Profile (128GB RAM)
│  └─ Orchestrator Container
│      ├─ KEDA CRON Trigger (4x daily)
│      ├─ Startup Trigger (@reboot)
│      └─ Python orchestrator code
│
├─ Dynamic Agent Containers (64GB each)
│  └─ Scenario execution
│
└─ Supporting Resources
    ├─ Key Vault (secrets)
    ├─ Service Bus (events)
    ├─ Storage (artifacts)
    ├─ Cosmos DB (logs)
    └─ Log Analytics (monitoring)
```

---

## 🔄 Execution Flow

### Scheduled Execution (4x Daily)
```
1. KEDA CRON Trigger fires (00:00, 06:00, 12:00, 18:00 UTC)
2. Container Apps scales orchestrator from 0 → 1
3. Orchestrator container starts (128GB RAM available)
4. Selects 5/15/30 scenarios (based on SIMULATION_SIZE)
5. Deploys agent containers (64GB RAM each, NODE_OPTIONS set)
6. Monitors execution for 8 hours
7. Cleanup resources
8. Orchestrator scales back to 0
```

### Startup Execution
```
1. @reboot trigger fires on environment start
2. Orchestrator scales to 1
3. Same flow as scheduled
```

---

## 🔒 Security

- **Secrets**: All in Key Vault, referenced by containers
- **Identity**: Managed Identity for all Azure access
- **Network**: Can add VNet integration if needed
- **RBAC**: Least privilege roles
- **Audit**: All actions logged

---

## 🚀 Deployment

### GitOps Workflow
```bash
# Automatic on push to develop/main
git push origin develop

# Or manual trigger
gh workflow run deploy-containerapps.yml
```

### Validation
```bash
# Check orchestrator status
az containerapp show \
  --name haymaker-dev-{suffix}-orchestrator \
  --resource-group haymaker-dev-rg

# View logs
az containerapp logs show \
  --name haymaker-dev-{suffix}-orchestrator \
  --resource-group haymaker-dev-rg \
  --follow
```

---

## 📈 Scaling

### Orchestrator
- **Min**: 0 (scale to zero saves money)
- **Max**: 1 (single orchestrator instance)
- **Triggers**: KEDA CRON only

### Agents
- **Dynamic**: Created by orchestrator as needed
- **Max**: Limited by SIMULATION_SIZE (5/15/30)
- **Lifecycle**: Deploy → Run 8h → Cleanup

---

## ✅ Success Criteria

- [x] Orchestrator uses E16 profile (128GB RAM)
- [x] KEDA CRON scheduling implemented
- [x] NODE_OPTIONS added to all containers
- [x] GitOps automation complete
- [x] Same sizes for dev and prod
- [ ] Deployed and tested
- [ ] Agents executing successfully

---

## 🎯 Next Steps

1. **Deploy**: Run GitOps workflow
2. **Verify**: Check orchestrator starts with 128GB
3. **Test**: Execute sample scenario
4. **Monitor**: Memory usage should be <128GB
5. **Validate**: Agents run with NODE_OPTIONS

**This architecture meets ALL Captain's requirements!**

🏴‍☠️ Fair winds! ⚓
