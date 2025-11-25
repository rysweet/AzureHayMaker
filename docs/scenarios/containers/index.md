---
layout: default
title: Containers
parent: Scenarios
nav_order: 4
has_children: true
description: "Container scenarios including AKS and Container Apps"
permalink: /scenarios/containers/
---

# Container Scenarios
{: .no_toc }

Scenarios for Azure container services including AKS, Container Apps, and Container Instances.
{: .fs-6 .fw-300 }

---

## Available Scenarios

| Scenario | Description | Complexity |
|:---------|:------------|:-----------|
| [Simple Web App](../containers-01-simple-web-app/) | Container App deployment | Low |
| [AKS Cluster](../containers-02-aks-cluster/) | Kubernetes cluster setup | High |
| [Container Instances](../containers-03-container-instances/) | Quick container deployment | Low |
| [AKS with Ingress](../containers-04-aks-ingress/) | AKS with NGINX ingress | High |
| [Multi-Container App](../containers-05-multi-container-app/) | Multi-service application | Medium |

## Technologies Used

- Azure Kubernetes Service (AKS)
- Azure Container Apps
- Azure Container Instances
- Azure Container Registry
- NGINX Ingress Controller

## Prerequisites

- Azure subscription with Container services enabled
- Container Registry for storing images
- Kubernetes knowledge (for AKS scenarios)
