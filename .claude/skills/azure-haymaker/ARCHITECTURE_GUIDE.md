# Azure Architecture Guide

Comprehensive architecture patterns and best practices for all 10 Azure technology areas. This guide complements the AzureHayMaker scenarios.

## Technology Areas Overview

Each section provides architectural guidance, common patterns, and references to specific AzureHayMaker scenarios.

---

## 1. AI & Machine Learning

### Architecture Patterns

**Pattern: Vision API Integration**
- Use Cognitive Services Vision for image analysis
- Store images in Blob Storage
- Process results with Logic Apps or Functions
- **Scenario**: `ai-ml-01-cognitive-services-vision.md`

**Pattern: Text Analytics Pipeline**
- Ingest text data from various sources
- Use Text Analytics for sentiment/entity extraction
- Store results in Cosmos DB for analysis
- **Scenario**: `ai-ml-02-text-analytics.md`

**Pattern: Azure OpenAI Deployment**
- Deploy GPT models for completion/chat
- Implement rate limiting and content filtering
- Monitor token usage and costs
- **Scenario**: `ai-ml-03-azure-openai.md`

**Pattern: MLOps with Azure ML**
- ML Workspace for experiment tracking
- Automated training pipelines
- Model versioning and deployment
- **Scenario**: `ai-ml-04-ml-workspace.md`

**Pattern: Conversational AI**
- Bot Service for chat interfaces
- QnA Maker for knowledge base
- LUIS for intent recognition
- **Scenario**: `ai-ml-05-bot-service.md`

### Best Practices
- Start with pre-built APIs before custom models
- Implement caching to reduce API costs
- Use managed identities for authentication
- Monitor API quotas and throttling
- Implement content safety filters

---

## 2. Analytics

### Architecture Patterns

**Pattern: Batch ETL**
- Extract data from sources to Storage
- Transform with Data Factory pipelines
- Load into SQL Database/Synapse
- **Scenario**: `analytics-01-batch-etl-pipeline.md`

**Pattern: Real-time Streaming**
- Ingest from Event Hubs/IoT Hub
- Process with Stream Analytics
- Output to multiple sinks
- **Scenario**: `analytics-02-realtime-streaming.md`

**Pattern: Modern Data Warehouse**
- Synapse Analytics for big data
- Data Lake for raw storage
- Power BI for visualization
- **Scenario**: `analytics-03-synapse-analytics.md`

**Pattern: Big Data Processing**
- Databricks for Spark workloads
- Delta Lake for data reliability
- MLflow for experiment tracking
- **Scenario**: `analytics-04-databricks.md`

**Pattern: Embedded Analytics**
- Power BI Embedded in applications
- Row-level security
- Automated refresh schedules
- **Scenario**: `analytics-05-power-bi-embed.md`

### Best Practices
- Use partitioning for large datasets
- Implement incremental loading
- Monitor pipeline execution times
- Use PolyBase for fast data movement
- Optimize for cost with serverless options

---

## 3. Compute

### Architecture Patterns

**Pattern: IaaS Web Server**
- VMs for full control
- Load Balancer for HA
- NSGs for security
- **Scenarios**: `compute-01-linux-vm-web-server.md`, `compute-02-windows-vm-iis.md`

**Pattern: PaaS Web Application**
- App Service for managed hosting
- Auto-scaling based on metrics
- Deployment slots for staging
- **Scenario**: `compute-03-app-service-python.md`

**Pattern: Serverless Functions**
- Functions for event-driven code
- Consumption plan for cost efficiency
- Durable Functions for stateful workflows
- **Scenario**: `compute-04-azure-functions-http.md`

**Pattern: Auto-Scaling Compute**
- VM Scale Sets for horizontal scaling
- Custom autoscale rules
- Health monitoring
- **Scenario**: `compute-05-vm-scale-set.md`

### Best Practices
- Use PaaS when possible (App Service > VMs)
- Implement health probes
- Use availability zones for HA
- Right-size VM SKUs
- Use spot instances for non-critical workloads

---

## 4. Containers

### Architecture Patterns

**Pattern: Simple Container Deployment**
- Container Apps for serverless containers
- Automatic HTTPS and scaling
- Integrated monitoring
- **Scenario**: `containers-01-simple-web-app.md`

**Pattern: Kubernetes Cluster**
- AKS for orchestration
- Multiple node pools
- Network policies
- **Scenario**: `containers-02-aks-cluster.md`

**Pattern: Serverless Containers**
- Container Instances for burst workloads
- No cluster management
- Per-second billing
- **Scenario**: `containers-03-container-instances.md`

**Pattern: Ingress & Routing**
- AKS with Ingress Controller
- TLS termination
- Path-based routing
- **Scenario**: `containers-04-aks-ingress.md`

**Pattern: Microservices Architecture**
- Multiple containers per app
- Service discovery
- Shared storage volumes
- **Scenario**: `containers-05-multi-container-app.md`

### Best Practices
- Use Container Apps for simple scenarios
- Use AKS for complex orchestration needs
- Implement pod security policies
- Use Azure Container Registry
- Monitor with Container Insights

---

## 5. Databases

### Architecture Patterns

**Pattern: Relational Database (MySQL)**
- Flexible Server for production
- VNet integration for security
- Backup and restore
- **Scenario**: `databases-01-mysql-wordpress.md`

**Pattern: Globally Distributed NoSQL**
- Cosmos DB for multi-region
- Automatic indexing
- Multiple consistency levels
- **Scenario**: `databases-02-cosmos-db.md`

**Pattern: PostgreSQL for Applications**
- Flexible Server deployment
- Extensions support
- Connection pooling
- **Scenario**: `databases-03-postgresql.md`

**Pattern: In-Memory Caching**
- Redis Cache for performance
- Session state storage
- Pub/sub messaging
- **Scenario**: `databases-04-redis-cache.md`

**Pattern: Managed SQL Instance**
- Near 100% SQL Server compatibility
- VNet integration
- Automated backups
- **Scenario**: `databases-05-sql-managed-instance.md`

### Best Practices
- Use managed services over IaaS
- Implement connection pooling
- Enable automated backups
- Use read replicas for scaling
- Monitor query performance

---

## 6. Hybrid + Multicloud

### Architecture Patterns

**Pattern: Hybrid Server Management**
- Azure Arc for on-prem servers
- Unified management
- Policy compliance
- **Scenario**: `hybrid-01-azure-arc.md`

**Pattern: Disaster Recovery**
- Azure Site Recovery for DR
- Automated failover
- Recovery plans
- **Scenario**: `hybrid-02-site-recovery.md`

**Pattern: On-Premises Azure**
- Azure Stack HCI
- Consistent Azure services
- Edge scenarios
- **Scenario**: `hybrid-03-azure-stack.md`

**Pattern: Private Connectivity**
- ExpressRoute for dedicated connection
- High bandwidth, low latency
- BGP routing
- **Scenario**: `hybrid-04-expressroute.md`

**Pattern: Migration Assessment**
- Azure Migrate for discovery
- Dependency mapping
- Cost estimation
- **Scenario**: `hybrid-05-azure-migrate.md`

### Best Practices
- Start with assessment tools
- Plan for network latency
- Use Azure Arc for unified management
- Implement backup strategies
- Consider data residency requirements

---

## 7. Identity

### Architecture Patterns

**Pattern: Service Principal Management**
- Create SPs for automation
- Rotate credentials regularly
- Scope permissions appropriately
- **Scenario**: `identity-01-service-principals.md`

**Pattern: Role-Based Access Control**
- Built-in roles vs custom roles
- Resource-level assignments
- Just-in-time access
- **Scenario**: `identity-02-rbac-assignments.md`

**Pattern: User & Group Management**
- Entra ID user lifecycle
- Dynamic groups
- B2B collaboration
- **Scenario**: `identity-03-entra-users-groups.md`

**Pattern: Application Registration**
- OAuth 2.0 flows
- API permissions
- Consent framework
- **Scenario**: `identity-04-app-registrations.md`

**Pattern: Conditional Access**
- Risk-based authentication
- MFA enforcement
- Device compliance
- **Scenario**: `identity-05-conditional-access.md`

### Best Practices
- Use managed identities when possible
- Implement least privilege
- Enable MFA for all users
- Regularly audit permissions
- Use Privileged Identity Management (PIM)

---

## 8. Networking

### Architecture Patterns

**Pattern: Hub-Spoke Topology**
- Central VNet for shared services
- Spoke VNets for workloads
- VNet peering
- **Scenario**: `networking-01-virtual-network.md`

**Pattern: Site-to-Site VPN**
- VPN Gateway for hybrid connectivity
- IPsec tunnels
- BGP routing
- **Scenario**: `networking-02-vpn-gateway.md`

**Pattern: Load Balancing**
- Standard Load Balancer for HA
- Health probes
- NAT rules
- **Scenario**: `networking-03-load-balancer.md`

**Pattern: Application Gateway**
- Layer 7 load balancing
- Web Application Firewall (WAF)
- SSL termination
- **Scenario**: `networking-04-application-gateway.md`

**Pattern: Private Connectivity**
- Private Endpoints for PaaS
- Private DNS zones
- Secure access
- **Scenario**: `networking-05-private-endpoint.md`

### Best Practices
- Segment networks with subnets
- Use NSGs for traffic filtering
- Implement DDoS protection
- Plan IP address space carefully
- Use Azure Firewall for centralized control

---

## 9. Security

### Architecture Patterns

**Pattern: Secrets Management**
- Key Vault for credentials
- Managed identities for access
- Automatic rotation
- **Scenario**: `security-01-key-vault-secrets.md`

**Pattern: Identity Governance**
- Entra ID groups for access
- Role assignments
- Access reviews
- **Scenario**: `security-02-entra-id-groups.md`

**Pattern: Network Security**
- NSGs for traffic control
- Application Security Groups
- Flow logs for analysis
- **Scenario**: `security-03-network-security-groups.md`

**Pattern: Managed Identity**
- System-assigned vs user-assigned
- Cross-resource access
- No credential management
- **Scenario**: `security-04-managed-identity.md`

**Pattern: Security Posture**
- Security Center/Defender
- Policy compliance
- Threat protection
- **Scenario**: `security-05-security-center-policies.md`

### Best Practices
- Enable Azure Defender
- Use managed identities everywhere
- Implement defense in depth
- Encrypt data at rest and in transit
- Regular security assessments

---

## 10. Web Apps

### Architecture Patterns

**Pattern: Static Website**
- Storage static hosting
- CDN for global distribution
- Custom domains
- **Scenario**: `webapps-01-static-website.md`

**Pattern: Dynamic Web Application**
- App Service for runtime
- Application Insights for monitoring
- Deployment slots
- **Scenarios**: `webapps-02-nodejs-app-service.md`, `webapps-03-docker-app-service.md`

**Pattern: JAMstack Applications**
- Static Web Apps
- Serverless APIs
- GitHub integration
- **Scenario**: `webapps-04-static-web-apps.md`

**Pattern: API Management**
- API Gateway for backends
- Rate limiting and throttling
- Developer portal
- **Scenario**: `webapps-05-api-management.md`

### Best Practices
- Use CDN for static content
- Implement caching strategies
- Enable auto-scaling
- Use App Service Plans efficiently
- Monitor with Application Insights

---

## Cross-Cutting Concerns

### Security
- Always use managed identities
- Store secrets in Key Vault
- Enable Azure Defender
- Implement network segmentation
- Regular vulnerability assessments

### Monitoring
- Application Insights for apps
- Log Analytics for infrastructure
- Azure Monitor for metrics
- Set up alerts
- Create dashboards

### Cost Optimization
- Right-size resources
- Use autoscaling
- Reserve instances for predictable workloads
- Use spot VMs for batch jobs
- Monitor with Cost Management

### High Availability
- Use availability zones
- Implement load balancing
- Multi-region deployments
- Automated backups
- Disaster recovery plans

### DevOps
- Infrastructure as Code (Bicep/Terraform)
- CI/CD pipelines
- Blue-green deployments
- Automated testing
- GitOps workflows

---

## Reference: All AzureHayMaker Scenarios

### AI & Machine Learning
- ai-ml-01-cognitive-services-vision.md
- ai-ml-02-text-analytics.md
- ai-ml-03-azure-openai.md
- ai-ml-04-ml-workspace.md
- ai-ml-05-bot-service.md

### Analytics
- analytics-01-batch-etl-pipeline.md
- analytics-02-realtime-streaming.md
- analytics-03-synapse-analytics.md
- analytics-04-databricks.md
- analytics-05-power-bi-embed.md

### Compute
- compute-01-linux-vm-web-server.md
- compute-02-windows-vm-iis.md
- compute-03-app-service-python.md
- compute-04-azure-functions-http.md
- compute-05-vm-scale-set.md

### Containers
- containers-01-simple-web-app.md
- containers-02-aks-cluster.md
- containers-03-container-instances.md
- containers-04-aks-ingress.md
- containers-05-multi-container-app.md

### Databases
- databases-01-mysql-wordpress.md
- databases-02-cosmos-db.md
- databases-03-postgresql.md
- databases-04-redis-cache.md
- databases-05-sql-managed-instance.md

### Hybrid + Multicloud
- hybrid-01-azure-arc.md
- hybrid-02-site-recovery.md
- hybrid-03-azure-stack.md
- hybrid-04-expressroute.md
- hybrid-05-azure-migrate.md

### Identity
- identity-01-service-principals.md
- identity-02-rbac-assignments.md
- identity-03-entra-users-groups.md
- identity-04-app-registrations.md
- identity-05-conditional-access.md

### Networking
- networking-01-virtual-network.md
- networking-02-vpn-gateway.md
- networking-03-load-balancer.md
- networking-04-application-gateway.md
- networking-05-private-endpoint.md

### Security
- security-01-key-vault-secrets.md
- security-02-entra-id-groups.md
- security-03-network-security-groups.md
- security-04-managed-identity.md
- security-05-security-center-policies.md

### Web Apps
- webapps-01-static-website.md
- webapps-02-nodejs-app-service.md
- webapps-03-docker-app-service.md
- webapps-04-static-web-apps.md
- webapps-05-api-management.md

---

**Guide Version**: 1.0
**Last Updated**: 2024
**Scenarios**: 50 total across 10 technology areas
