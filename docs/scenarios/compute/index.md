---
layout: default
title: Compute
parent: Scenarios
nav_order: 3
has_children: true
description: "Compute scenarios including VMs and Functions"
permalink: /scenarios/compute/
---

# Compute Scenarios
{: .no_toc }

Scenarios for Azure compute services including Virtual Machines, App Service, and Functions.
{: .fs-6 .fw-300 }

---

## Available Scenarios

| Scenario | Description | Complexity |
|:---------|:------------|:-----------|
| [Linux VM Web Server](../compute-01-linux-vm-web-server/) | Linux VM with nginx web server | Low |
| [Windows VM IIS](../compute-02-windows-vm-iis/) | Windows Server with IIS | Medium |
| [App Service Python](../compute-03-app-service-python/) | Flask web app on App Service | Low |
| [Azure Functions HTTP](../compute-04-azure-functions-http/) | HTTP-triggered Azure Functions | Low |
| [VM Scale Set](../compute-05-vm-scale-set/) | Auto-scaling VM deployment | High |

## Technologies Used

- Azure Virtual Machines (Linux/Windows)
- Azure App Service
- Azure Functions
- Virtual Machine Scale Sets
- Load Balancers

## Prerequisites

- Azure subscription with Compute provider registered
- Sufficient quota for VM sizes
- Network infrastructure (VNets, NSGs)
