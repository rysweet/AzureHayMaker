---
layout: default
title: Analytics
parent: Scenarios
nav_order: 2
has_children: true
description: "Analytics scenarios including Synapse and Databricks"
permalink: /scenarios/analytics/
---

# Analytics Scenarios
{: .no_toc }

Scenarios for Azure analytics services including data pipelines, streaming, and BI.
{: .fs-6 .fw-300 }

---

## Available Scenarios

| Scenario | Description | Complexity |
|:---------|:------------|:-----------|
| [Batch ETL Pipeline](../analytics-01-batch-etl-pipeline/) | Data Factory ETL | Medium |
| [Real-time Streaming](../analytics-02-realtime-streaming/) | Event Hubs streaming | High |
| [Synapse Analytics](../analytics-03-synapse-analytics/) | Data warehouse | High |
| [Databricks](../analytics-04-databricks/) | Apache Spark platform | High |
| [Power BI Embed](../analytics-05-power-bi-embed/) | Embedded analytics | Medium |

## Technologies Used

- Azure Data Factory
- Azure Event Hubs
- Azure Synapse Analytics
- Azure Databricks
- Power BI Embedded

## Prerequisites

- Azure subscription with analytics services enabled
- Sufficient capacity units for Synapse/Databricks
- Power BI Pro license (for embed scenarios)
