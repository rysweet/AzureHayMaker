# Azure HayMaker - Cost Analysis

**Current deployment has significant cost optimization opportunity!**

---

## 📊 Current State (From Infrastructure Check)

### Deployed Resources
- **Key Vaults**: 21 instances
- **Service Bus Namespaces**: 18 instances
- **Function Apps**: 12 instances
- **Storage Accounts**: 21 instances
- **Log Analytics**: 1 workspace
- **Container App Environment**: 1 instance

### Estimated Monthly Cost

| Resource Type | Count | Unit Cost | Total |
|---------------|-------|-----------|-------|
| Key Vault | 21 | $0.03/vault | $0.63 |
| Service Bus (Standard) | 18 | $10/namespace | $180 |
| Function App (S1) | 12 | $73/app | $876 |
| Storage Account | 21 | $20/account | $420 |
| Log Analytics | 1 | $30/month | $30 |
| **TOTAL** | | | **~$1,507/month** |

---

## 💡 Optimization Opportunity

### Recommended Configuration
- **Key Vault**: 1 (delete 20)
- **Service Bus**: 1 (delete 17)
- **Function Apps**: 0 (replace with VM, delete all 12)
- **Storage Accounts**: 1 (delete 20)
- **VM**: 1 Standard_E8s_v3 (64GB RAM)

### Optimized Monthly Cost

| Resource Type | Count | Unit Cost | Total |
|---------------|-------|-----------|-------|
| Key Vault | 1 | $0.03/vault | $0.03 |
| Service Bus | 1 | $10/namespace | $10 |
| VM E8s_v3 | 1 | $438/month | $438 |
| Storage Account | 1 | $20/account | $20 |
| Log Analytics | 1 | $30/month | $30 |
| **TOTAL** | | | **~$498/month** |

### **Savings: ~$1,009/month (67% reduction!)**

---

## 🧹 How to Clean Up

### Automated Cleanup (Recommended)
```bash
# Clean up old Function Apps
./scripts/cleanup-old-function-apps.sh  # Saves $876/month

# TODO: Create cleanup scripts for:
# - Old Key Vaults
# - Old Service Bus namespaces
# - Old Storage Accounts
```

### Manual Cleanup
```bash
# List resources to delete
./scripts/list-all-resources.sh

# Delete via Portal or CLI
az resource delete --ids <resource-id>
```

---

## 🎯 Cleanup Strategy

### Phase 1: Function Apps (Immediate)
- **Action**: Run `./scripts/cleanup-old-function-apps.sh`
- **Savings**: $876/month
- **Risk**: Low (keeping latest one)
- **Time**: 5 minutes

### Phase 2: VM Deployment (Next Session)
- **Action**: Deploy 64GB VM
- **Cost**: +$438/month
- **Benefit**: Reliable orchestrator
- **Time**: 3 hours

### Phase 3: Infrastructure Cleanup (After VM Verified)
- **Action**: Delete old Key Vaults, Service Bus, Storage
- **Savings**: Additional $633/month
- **Risk**: Medium (verify dependencies first)
- **Time**: 30 minutes

### **Total Potential Savings**: $1,009/month

---

## 📈 Cost Comparison

### Current (All Resources)
- Monthly: ~$1,507
- Annual: ~$18,084

### After Cleanup
- Monthly: ~$498
- Annual: ~$5,976

### **Annual Savings**: ~$12,108 (67%!)

---

## 🚀 Next Steps

1. **Immediate** (5 min):
   ```bash
   ./scripts/cleanup-old-function-apps.sh
   ```
   Saves: $876/month

2. **Next Session** (3 hours):
   - Deploy VM
   - Test orchestrator
   - Verify before cleanup

3. **Final Cleanup** (30 min):
   - Remove old Key Vaults
   - Remove old Service Bus
   - Remove old Storage

---

## ⚠️ Important Notes

- **Always keep one working set** of resources
- **Test VM before cleanup** (Issue #13)
- **Verify dependencies** before deletion
- **Backup important data** (if any)

---

**Cleanup scripts ready - Captain decides when to execute!**
