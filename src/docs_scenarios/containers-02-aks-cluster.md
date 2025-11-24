# Scenario: Azure Kubernetes Service (AKS) Cluster

## Technology Area
Containers

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Technology / Cloud Services
- **Use Case**: Run microservices-based applications on managed Kubernetes

## Scenario Description
Deploy a managed Kubernetes cluster using Azure Kubernetes Service (AKS). Set up node pools, deploy sample applications, configure ingress controller, and implement autoscaling policies for production-ready container orchestration.

## Azure Services Used
- Azure Kubernetes Service (AKS)
- Azure Container Registry (image storage)
- Azure Virtual Network (networking)
- Azure Monitor (logging and monitoring)
- Azure Key Vault (secrets management)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed with kubectl extension
- Docker installed (for building images)
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-containers-aks-${UNIQUE_ID}-rg"
LOCATION="eastus"
AKS_CLUSTER="azurehaymaker-aks-${UNIQUE_ID}"
ACR_REGISTRY="azmkraks${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
LOG_ANALYTICS="azurehaymaker-logs-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=containers-aks Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Virtual Network
az network vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --address-prefix "10.0.0.0/16" \
  --subnet-name "aks-subnet" \
  --subnet-prefixes "10.0.0.0/22" \
  --tags ${TAGS}

SUBNET_ID=$(az network vnet subnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "aks-subnet" \
  --query id -o tsv)

# Step 3: Create Azure Container Registry
az acr create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${ACR_REGISTRY}" \
  --sku Standard \
  --admin-enabled true \
  --tags ${TAGS}

# Step 4: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 5: Create Log Analytics Workspace
az monitor log-analytics workspace create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS}" \
  --query customerId -o tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS}" \
  --query primarySharedKey -o tsv)

# Step 6: Create AKS Cluster
az aks create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER}" \
  --location "${LOCATION}" \
  --node-count 2 \
  --vm-set-type VirtualMachineScaleSets \
  --load-balancer-sku standard \
  --enable-managed-identity \
  --network-plugin azure \
  --vnet-subnet-id "${SUBNET_ID}" \
  --docker-bridge-address "172.17.0.1/16" \
  --service-cidr "10.0.0.0/16" \
  --dns-service-ip "10.0.0.10" \
  --enable-addons monitoring \
  --workspace-resource-id "/subscriptions/$(az account show --query id -o tsv)/resourcegroups/${RESOURCE_GROUP}/providers/microsoft.operationalinsights/workspaces/${LOG_ANALYTICS}" \
  --enable-cluster-autoscaling \
  --min-count 1 \
  --max-count 5 \
  --attach-acr "${ACR_REGISTRY}" \
  --tags ${TAGS}

# Step 7: Get credentials
az aks get-credentials \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER}" \
  --overwrite-existing

# Step 8: Build and push sample container image
cat > /tmp/Dockerfile <<EOF
FROM nginx:alpine
RUN echo '<html><body><h1>AKS Sample App</h1><p>Scenario: containers-aks</p></body></html>' > /usr/share/nginx/html/index.html
EOF

ACR_LOGIN_SERVER=$(az acr show \
  --name "${ACR_REGISTRY}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query loginServer -o tsv)

az acr build \
  --registry "${ACR_REGISTRY}" \
  --image "aks-sample:v1" \
  --file /tmp/Dockerfile \
  /tmp/

# Step 9: Create sample Kubernetes deployment manifest
cat > /tmp/deployment.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aks-sample-app
  labels:
    app: aks-sample
spec:
  replicas: 2
  selector:
    matchLabels:
      app: aks-sample
  template:
    metadata:
      labels:
        app: aks-sample
    spec:
      containers:
      - name: app
        image: ${ACR_LOGIN_SERVER}/aks-sample:v1
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 250m
            memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: aks-sample-service
spec:
  type: LoadBalancer
  selector:
    app: aks-sample
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
EOF

# Step 10: Deploy application to AKS
kubectl apply -f /tmp/deployment.yaml

echo ""
echo "=========================================="
echo "AKS Cluster Created: ${AKS_CLUSTER}"
echo "ACR Registry: ${ACR_LOGIN_SERVER}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify AKS Cluster
az aks show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER}"

# Check cluster status
az aks show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER}" \
  --query "powerState.code" -o tsv

# Verify ACR
az acr show \
  --name "${ACR_REGISTRY}" \
  --resource-group "${RESOURCE_GROUP}"

# List ACR repositories
az acr repository list \
  --name "${ACR_REGISTRY}" \
  --output table

# Get kubectl nodes
kubectl get nodes -o wide

# Get deployments
kubectl get deployments -o wide

# Get services
kubectl get svc -o wide

# Get pods
kubectl get pods -o wide

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Scale deployment
kubectl scale deployment aks-sample-app --replicas=4

# Operation 2: Check pod status
kubectl get pods -o wide

# Operation 3: View pod logs
kubectl logs -l app=aks-sample --tail=20

# Operation 4: Deploy updated image
az acr build \
  --registry "${ACR_REGISTRY}" \
  --image "aks-sample:v2" \
  --file /tmp/Dockerfile \
  /tmp/

# Operation 5: Update deployment with new image
kubectl set image deployment/aks-sample-app app=${ACR_LOGIN_SERVER}/aks-sample:v2

# Operation 6: Check deployment status
kubectl rollout status deployment/aks-sample-app

# Operation 7: Scale cluster nodes
az aks scale \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER}" \
  --node-count 3

# Operation 8: Monitor cluster metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ContainerService/managedClusters/${AKS_CLUSTER}" \
  --metric "node_cpu_usage_percentage" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 9: Add node pool
az aks nodepool add \
  --resource-group "${RESOURCE_GROUP}" \
  --cluster-name "${AKS_CLUSTER}" \
  --name "nodepool2" \
  --node-count 1

# Operation 10: View cluster events
kubectl get events --all-namespaces --sort-by='.lastTimestamp'
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete Kubernetes deployments
kubectl delete deployment aks-sample-app

# Step 2: Delete Kubernetes services
kubectl delete svc aks-sample-service

# Step 3: Delete AKS cluster
az aks delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER}" \
  --yes \
  --no-wait

# Step 4: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 5: Verify deletion
sleep 120
az group exists --name "${RESOURCE_GROUP}"

# Step 6: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 7: Clean up kubeconfig
kubectl config delete-context "${AKS_CLUSTER}"
kubectl config delete-cluster "${AKS_CLUSTER}"

# Step 8: Clean up local files
rm -rf /tmp/Dockerfile /tmp/deployment.yaml
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-containers-aks-${UNIQUE_ID}-rg`
- AKS Cluster: `azurehaymaker-aks-${UNIQUE_ID}`
- ACR Registry: `azmkraks${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- Log Analytics: `azurehaymaker-logs-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Kubernetes Service Overview](https://learn.microsoft.com/en-us/azure/aks/intro-kubernetes)
- [Create AKS Cluster](https://learn.microsoft.com/en-us/azure/aks/kubernetes-walkthrough)
- [AKS Cluster Autoscaling](https://learn.microsoft.com/en-us/azure/aks/cluster-autoscaler)
- [AKS Networking](https://learn.microsoft.com/en-us/azure/aks/concepts-network)
- [AKS CLI Reference](https://learn.microsoft.com/en-us/cli/azure/aks)

---

## Automation Tool
**Recommended**: Azure CLI (for provisioning) + kubectl (for Kubernetes management)

**Rationale**: Azure CLI handles AKS cluster provisioning while kubectl manages application deployments. This combination is optimal for container orchestration on Azure.

---

## Estimated Duration
- **Deployment**: 20-25 minutes (AKS cluster provisioning takes time)
- **Operations Phase**: 8 hours (with scaling, deployments, and monitoring)
- **Cleanup**: 10-15 minutes

---

## Notes
- AKS provides managed Kubernetes with automatic updates and patching
- Cluster autoscaling automatically adjusts node count based on resource demands
- Multiple node pools support workload isolation
- Network integration provides secure pod networking
- All operations scoped to single tenant and subscription
- RBAC and managed identity provide security
