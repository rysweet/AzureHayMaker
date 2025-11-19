# Alternative: Deploy Orchestrator to VM Instead of Function App

## Problem
Function App containers crash with SIGABRT (exit code 134) even with:
- Python 3.11
- Premium V2 P3 plan (8GB RAM)
- All environment variables configured
- Cosmos DB optional

## Root Cause Hypothesis
Azure Functions has memory/resource constraints even on Premium plans that cause issues with:
- Heavy Azure SDK initialization
- Durable Functions framework
- Multiple concurrent imports

## Solution: Deploy to Azure VM

### Architecture Change
```
BEFORE:
GitHub Actions → Azure Functions (Durable Functions) → Container Apps

AFTER:
GitHub Actions → Azure VM (systemd service) → Container Apps
```

### VM Specifications
- **Size**: Standard_D4s_v3 (4 vCPU, 16 GB RAM)
- **OS**: Ubuntu 24.04 LTS
- **Runtime**: Python 3.11 via systemd service
- **Dependencies**: Install all via pip in venv

### Implementation Steps

1. **Create VM Bicep Module** (`infra/bicep/modules/vm.bicep`)
   - Ubuntu 24.04 VM
   - System-assigned managed identity
   - NSG allowing HTTPS inbound
   - Custom script extension for setup

2. **Create VM Setup Script** (`scripts/vm-setup.sh`)
   ```bash
   #!/bin/bash
   # Install Python 3.11
   apt-get update
   apt-get install -y python3.11 python3.11-venv

   # Create service user
   useradd -m -s /bin/bash haymaker

   # Install code
   cd /opt/haymaker
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Create systemd service
   cp haymaker-orchestrator.service /etc/systemd/system/
   systemctl enable haymaker-orchestrator
   systemctl start haymaker-orchestrator
   ```

3. **Create Systemd Service** (`deployment/haymaker-orchestrator.service`)
   ```ini
   [Unit]
   Description=Azure HayMaker Orchestrator
   After=network.target

   [Service]
   Type=simple
   User=haymaker
   WorkingDirectory=/opt/haymaker
   Environment="PATH=/opt/haymaker/venv/bin"
   EnvironmentFile=/opt/haymaker/.env
   ExecStart=/opt/haymaker/venv/bin/python -m azure_haymaker.orchestrator
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

4. **Update main.bicep**
   - Replace functionApp module with vm module
   - Keep all other resources (Key Vault, Service Bus, Storage)
   - Grant VM managed identity same RBAC roles

5. **Migrate Durable Functions to Simple Scheduler**
   - Use APScheduler instead of Durable Functions
   - Cron schedule: 0 */6 * * * (every 6 hours)
   - State tracking in Table Storage
   - Same orchestration logic

### Benefits
- Full control over memory and resources
- No Azure Functions runtime constraints
- Can add swap space if needed
- Easier to debug (direct SSH access)
- More predictable resource usage

### Effort Estimate
- 2-3 hours to implement
- Lower risk than continuing Function App debugging

### Next Steps if P3V2 Fails
1. Create VM Bicep module
2. Migrate orchestrator code to use APScheduler
3. Deploy and test
4. Compare costs (VM vs Functions)
