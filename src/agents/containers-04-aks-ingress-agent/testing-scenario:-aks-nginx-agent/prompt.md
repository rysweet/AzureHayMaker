# Scenario: AKS with NGINX Ingress Controller

## Technology Area
Containers

## Company Profile
- **Company Size**: Mid-size enterprise
- **Industry**: Financial Services / SaaS
- **Use Case**: Route external traffic to multiple microservices with SSL/TLS termination

## Scenario Description
Deploy AKS cluster with NGINX ingress controller for advanced routing capabilities. Configure ingress rules for multiple applications, implement SSL/TLS termination, and set up hostname-based routing.

## Azure Services Used
- Azure Kubernetes Service (AKS)
- Azure Container Registry (image storage)
- NGINX Ingress Controller (traffic routing)
- Azure Public IP (external access)
- Azure Key Vault (certificate storage)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed with kubectl and helm
- Docker installed
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-containers-ingress-${UNIQUE_ID}-rg"
LOCATION="eastus"
AKS_CLUSTER="azurehaymaker-aks-ingress-${UNIQUE_ID}"
ACR_REGISTRY="azmkringress${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
LOG_ANALYTICS="azurehaymaker-logs-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=containers-aks-ingress Owner=AzureHayMaker"
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

# Step 4: Create Log Analytics Workspace
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

# Step 5: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

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
  --service-cidr "10.1.0.0/16" \
  --dns-service-ip "10.1.0.10" \
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

# Step 8: Create namespace for ingress controller
kubectl create namespace ingress-nginx

# Step 9: Add Helm repository and install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --set controller.service.type=LoadBalancer \
  --set controller.service.externalTrafficPolicy=Local

# Step 10: Build sample applications
ACR_LOGIN_SERVER=$(az acr show \
  --name "${ACR_REGISTRY}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query loginServer -o tsv)

for APP_NAME in app-blue app-red; do
  cat > /tmp/Dockerfile_${APP_NAME} <<EOF
FROM nginx:alpine
RUN echo '<html><body><h1>${APP_NAME}</h1><p>Ingress routing demo</p></body></html>' > /usr/share/nginx/html/index.html
EOF

  az acr build \
    --registry "${ACR_REGISTRY}" \
    --image "${APP_NAME}:v1" \
    --file /tmp/Dockerfile_${APP_NAME} \
    /tmp/
done

# Step 11: Create application deployments
cat > /tmp/apps_deployment.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-blue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app-blue
  template:
    metadata:
      labels:
        app: app-blue
    spec:
      containers:
      - name: app-blue
        image: ${ACR_LOGIN_SERVER}/app-blue:v1
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: app-blue-service
spec:
  selector:
    app: app-blue
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-red
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app-red
  template:
    metadata:
      labels:
        app: app-red
    spec:
      containers:
      - name: app-red
        image: ${ACR_LOGIN_SERVER}/app-red:v1
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: app-red-service
spec:
  selector:
    app: app-red
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
EOF

kubectl apply -f /tmp/apps_deployment.yaml

# Step 12: Create ingress resource
cat > /tmp/ingress.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: main-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  rules:
  - host: app-blue.example.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-blue-service
            port:
              number: 80
  - host: app-red.example.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-red-service
            port:
              number: 80
EOF

kubectl apply -f /tmp/ingress.yaml

echo ""
echo "=========================================="
echo "AKS Cluster with Ingress: ${AKS_CLUSTER}"
echo "NGINX Ingress installed in namespace: ingress-nginx"
echo "=========================================="
```

### Validation
```bash
# Verify AKS Cluster
az aks show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER}"

# Check nodes
kubectl get nodes -o wide

# Get NGINX ingress controller service
kubectl get svc -n ingress-nginx

# Get external IP of ingress
INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Ingress External IP: ${INGRESS_IP}"

# Check deployments
kubectl get deployments -o wide

# Check services
kubectl get svc -o wide

# Check ingress rules
kubectl get ingress -o wide

# Check pods
kubectl get pods -o wide

# View ingress details
kubectl describe ingress main-ingress

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Scale application deployments
kubectl scale deployment app-blue --replicas=3
kubectl scale deployment app-red --replicas=3

# Operation 2: Check pods across deployments
kubectl get pods -o wide

# Operation 3: View ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=50

# Operation 4: Create new ingress rule
cat > /tmp/new_ingress.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
  - host: api.example.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-blue-service
            port:
              number: 80
EOF

kubectl apply -f /tmp/new_ingress.yaml

# Operation 5: Get all ingress rules
kubectl get ingress -A

# Operation 6: Monitor ingress metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ContainerService/managedClusters/${AKS_CLUSTER}" \
  --metric "node_network_in_bytes" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 7: Check NGINX controller configuration
kubectl get configmap -n ingress-nginx

# Operation 8: View NGINX metrics
kubectl top nodes

# Operation 9: Update ingress with path-based routing
cat > /tmp/path_based_ingress.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
  - host: multi-app.example.local
    http:
      paths:
      - path: /blue
        pathType: Prefix
        backend:
          service:
            name: app-blue-service
            port:
              number: 80
      - path: /red
        pathType: Prefix
        backend:
          service:
            name: app-red-service
            port:
              number: 80
EOF

kubectl apply -f /tmp/path_based_ingress.yaml

# Operation 10: Check service endpoints
kubectl get endpoints -o wide
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete ingress resources
kubectl delete ingress --all

# Step 2: Delete deployments and services
kubectl delete deployment app-blue app-red
kubectl delete svc app-blue-service app-red-service

# Step 3: Uninstall NGINX Ingress Controller
helm uninstall nginx-ingress -n ingress-nginx

# Step 4: Delete namespace
kubectl delete namespace ingress-nginx

# Step 5: Delete AKS cluster
az aks delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER}" \
  --yes \
  --no-wait

# Step 6: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 7: Verify deletion
sleep 120
az group exists --name "${RESOURCE_GROUP}"

# Step 8: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 9: Clean up kubeconfig
kubectl config delete-context "${AKS_CLUSTER}"
kubectl config delete-cluster "${AKS_CLUSTER}"

# Step 10: Clean up local files
rm -rf /tmp/Dockerfile_* /tmp/apps_deployment.yaml /tmp/ingress.yaml /tmp/new_ingress.yaml /tmp/path_based_ingress.yaml
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-containers-ingress-${UNIQUE_ID}-rg`
- AKS Cluster: `azurehaymaker-aks-ingress-${UNIQUE_ID}`
- ACR Registry: `azmkringress${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [AKS Ingress Controller](https://learn.microsoft.com/en-us/azure/aks/ingress-basic)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Helm Package Manager](https://helm.sh/docs/)
- [AKS Best Practices](https://learn.microsoft.com/en-us/azure/aks/best-practices)

---

## Automation Tool
**Recommended**: Azure CLI + kubectl + Helm

**Rationale**: Azure CLI provisions AKS, while kubectl and Helm manage ingress controller and applications. This combination is optimal for advanced Kubernetes networking scenarios.

---

## Estimated Duration
- **Deployment**: 25-30 minutes (AKS + NGINX setup)
- **Operations Phase**: 8 hours (with routing configuration and monitoring)
- **Cleanup**: 10-15 minutes

---

## Notes
- NGINX ingress controller provides advanced routing capabilities
- Path-based and hostname-based routing supported
- LoadBalancer service exposes ingress to external traffic
- Ingress controller can manage SSL/TLS with cert-manager
- All operations scoped to single tenant and subscription
- Auto-scaling works at both pod and node levels
