# Cross-Tenant Architecture

This document describes the architecture for Azure HayMaker cross-tenant orchestration.

## Two-Tier Architecture

Azure HayMaker cross-tenant orchestration uses a two-tier model:

1. **Infrastructure Tenant** - Hosts the orchestrator service, secrets, and state
2. **Target Tenant(s)** - Where scenarios deploy resources and generate telemetry

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INFRASTRUCTURE TENANT                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Azure HayMaker Orchestrator                       │    │
│  │              (FastAPI on App Service / Container App)                │    │
│  │                                                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │   Scheduler  │  │  Execution   │  │   Cleanup    │              │    │
│  │  │   (cron)     │  │   Manager    │  │   Manager    │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └────────────────────────────────┬────────────────────────────────────┘    │
│                                   │                                          │
│  ┌────────────┐  ┌────────────┐  │  ┌────────────┐  ┌────────────┐        │
│  │ Key Vault  │  │   Table    │  │  │    Blob    │  │   Service  │        │
│  │ (secrets)  │  │  Storage   │  │  │  Storage   │  │    Bus     │        │
│  └────────────┘  └────────────┘  │  └────────────┘  └────────────┘        │
│                                   │                                          │
└───────────────────────────────────┼──────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │ Cross-Tenant Auth     │                       │
            │ (Service Principal)   │                       │
            ▼                       ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   TARGET TENANT A   │  │   TARGET TENANT B   │  │   TARGET TENANT C   │
│                     │  │                     │  │                     │
│  ┌──────────────┐   │  │  ┌──────────────┐   │  │  ┌──────────────┐   │
│  │ Container    │   │  │  │ Container    │   │  │  │ Container    │   │
│  │ Apps Env     │   │  │  │ Apps Env     │   │  │  │ Apps Env     │   │
│  └──────┬───────┘   │  │  └──────┬───────┘   │  │  └──────┬───────┘   │
│         │           │  │         │           │  │         │           │
│  ┌──────▼───────┐   │  │  ┌──────▼───────┐   │  │  ┌──────▼───────┐   │
│  │   Scenario   │   │  │  │   Scenario   │   │  │  │   Scenario   │   │
│  │   Agents     │   │  │  │   Agents     │   │  │  │   Agents     │   │
│  └──────────────┘   │  │  └──────────────┘   │  │  └──────────────┘   │
│                     │  │                     │  │                     │
│  Azure Resources:   │  │  Azure Resources:   │  │  Azure Resources:   │
│  - VMs, AKS, etc.   │  │  - VMs, AKS, etc.   │  │  - VMs, AKS, etc.   │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

## Component Responsibilities

### Infrastructure Tenant Components

| Component | Responsibility |
|:----------|:---------------|
| **Orchestrator** | FastAPI service that schedules and coordinates executions |
| **Key Vault** | Stores all secrets including target tenant SP credentials |
| **Table Storage** | Execution state, schedule persistence, agent status |
| **Blob Storage** | Execution reports, logs, scenario documents |
| **Service Bus** | Event streaming from agents to orchestrator |

### Target Tenant Components

| Component | Responsibility |
|:----------|:---------------|
| **Container Apps Environment** | Hosts scenario agent containers |
| **Scenario Agents** | Autonomous containers executing scenarios |
| **Deployed Resources** | VMs, AKS clusters, databases created by scenarios |
| **Ephemeral Service Principals** | Per-execution SPs for scenario resource access |

## Authentication Flow

### Cross-Tenant Service Principal Authentication

```
┌─────────────────┐                    ┌─────────────────┐
│  Infrastructure │                    │  Target Tenant  │
│     Tenant      │                    │                 │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         │  1. Multi-tenant app registration    │
         │─────────────────────────────────────>│
         │                                      │
         │  2. SP created in target tenant      │
         │<─────────────────────────────────────│
         │                                      │
         │  3. Role assignments granted         │
         │  (Contributor on subscription)       │
         │<─────────────────────────────────────│
         │                                      │
         │  4. Orchestrator authenticates       │
         │  with target tenant credentials      │
         │─────────────────────────────────────>│
         │                                      │
         │  5. Deploy Container Apps + agents   │
         │─────────────────────────────────────>│
         │                                      │
```

### Credential Flow

1. Orchestrator reads target tenant credentials from Key Vault
2. Uses `ClientSecretCredential` with target tenant ID
3. Authenticates to Azure Resource Manager in target tenant
4. Deploys Container Apps Environment and scenario agents
5. Each agent receives ephemeral SP credentials for its resources

## Data Flow

### Execution Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATOR (Infrastructure Tenant)             │
│                                                                           │
│  1. VALIDATION        2. SELECTION        3. PROVISIONING                 │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────────────────┐   │
│  │ Validate    │─────>│ Select      │─────>│ For each target tenant: │   │
│  │ environment │      │ scenarios   │      │ - Create ephemeral SPs  │   │
│  │ & config    │      │ based on    │      │ - Deploy container apps │   │
│  │             │      │ size        │      │ - Start scenario agents │   │
│  └─────────────┘      └─────────────┘      └─────────────────────────┘   │
│                                                     │                      │
│                                                     ▼                      │
│  6. REPORTING         5. CLEANUP           4. MONITORING (8 hours)        │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────────────────┐   │
│  │ Generate    │<─────│ Verify      │<─────│ Poll container status   │   │
│  │ reports     │      │ cleanup     │      │ Collect logs via        │   │
│  │ Store to    │      │ Force delete│      │   Service Bus           │   │
│  │ blob storage│      │ if needed   │      │ Track resource count    │   │
│  └─────────────┘      └─────────────┘      └─────────────────────────┘   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Cross-Tenant Data Flow

```
Infrastructure Tenant                        Target Tenant
┌──────────────────────┐                    ┌──────────────────────┐
│                      │   ARM API Calls    │                      │
│    Orchestrator      │───────────────────>│   Resource Manager   │
│                      │                    │                      │
│                      │   Container Logs   │                      │
│    Service Bus   <───│────────────────────│   Scenario Agents    │
│                      │                    │                      │
│                      │   Metrics/Status   │                      │
│    Table Storage <───│────────────────────│   Container Apps     │
│                      │                    │                      │
└──────────────────────┘                    └──────────────────────┘
```

## Multi-Tenant Registry

For organizations managing multiple target tenants, the orchestrator maintains a tenant registry in Key Vault:

```
Key Vault Secrets:
├── tenant-customerA-config     # JSON: {tenant_id, subscription_id, sp_client_id, ...}
├── tenant-customerA-secret     # Plain text SP secret
├── tenant-customerB-config
├── tenant-customerB-secret
├── tenant-prod-config
├── tenant-prod-secret
└── ...
```

### TenantConfig Model

```python
class TenantConfig:
    tenant_id: str              # Azure AD tenant ID
    subscription_id: str        # Target subscription ID
    sp_client_id: str           # Service principal client ID
    sp_client_secret: SecretStr # Service principal secret
    display_name: str | None    # Human-readable name
    enabled: bool               # Whether tenant is active
    resource_group: str | None  # Default resource group
```

## Security Considerations

### Isolation

- Each target tenant operates independently
- No cross-tenant data sharing between target tenants
- Ephemeral service principals created per execution
- All secrets stored in infrastructure tenant Key Vault

### Least Privilege

- Orchestrator SP: Only needs Container Apps Contributor in target tenant
- Scenario SPs: Scoped to specific resource types needed
- All SPs deleted after execution completes

### Network Security

- VNet integration available for Container Apps
- Private endpoints supported for storage and Key Vault
- Cross-tenant traffic uses Azure backbone (no public internet)

## Scaling Considerations

### Horizontal Scaling

- Orchestrator is stateless (state in Table Storage)
- Can run multiple orchestrator instances behind load balancer
- Each target tenant execution is independent

### Limits

| Resource | Limit | Notes |
|:---------|:------|:------|
| Target tenants | No hard limit | Practical limit ~100 per orchestrator |
| Concurrent executions per tenant | 10 | Configurable via rate limiter |
| Scenarios per execution | 30 (large) | Configurable via simulation_size |

## Related Documentation

- [API Reference](./API.md) - Endpoint specifications
- [Configuration Guide](./CONFIGURATION.md) - Setup and configuration
- [Security Guide](/AzureHayMaker/security) - Security best practices
