# Monitoring & Observability Guide

**How to monitor Azure HayMaker in production**

---

## Quick Health Check

```bash
./scripts/health-check.sh
```

Shows status of:
- Key Vault
- Service Bus
- Function App/VM
- API endpoints

---

## Azure Portal Monitoring

### Application Insights
1. Navigate to: `haymaker-dev-yow3ex-func-insights`
2. View: Live Metrics, Failures, Performance
3. Custom queries in Logs

### Log Analytics
1. Navigate to: `haymaker-dev-logs`
2. Query agent execution logs
3. Create custom dashboards
4. Set up alerts

---

## Key Metrics to Track

### Orchestrator Health
- Execution success rate
- Average execution time
- Memory usage
- CPU utilization

### Agent Performance
- Deployment success rate
- Average scenario runtime
- Cleanup success rate
- Resource creation counts

### Cost Metrics
- Daily spend
- Monthly trends
- Resource utilization
- Waste identification

---

## Alerting Recommendations

### Critical Alerts
- Orchestrator crashes
- Agent deployment failures > 50%
- Key Vault access denied
- Cost spike > 20%

### Warning Alerts
- Execution time > 10 hours
- Memory usage > 80%
- Failed cleanup attempts
- Unusual resource counts

---

## Log Queries

### Recent Orchestrator Runs
```kusto
traces
| where timestamp > ago(24h)
| where message contains "orchestrator"
| order by timestamp desc
```

### Failed Agent Deployments
```kusto
traces
| where timestamp > ago(7d)
| where severityLevel >= 3
| where message contains "agent"
| summarize count() by bin(timestamp, 1h)
```

### Cost Anomalies
```kusto
AzureMetrics
| where ResourceProvider == "MICROSOFT.WEB"
| summarize cost=sum(Total) by bin(TimeGenerated, 1d)
```

---

## Dashboards

### Recommended Panels
1. Orchestrator execution timeline
2. Agent success/failure rates
3. Cost trends (daily/monthly)
4. Resource utilization
5. Error rates by type

### Custom Views
- Executive dashboard (high-level metrics)
- Operations dashboard (detailed logs)
- Cost dashboard (spend analysis)

---

## Automation Monitoring

### Health Check Cron
```bash
# Add to crontab for regular health checks
0 */6 * * * /path/to/scripts/health-check.sh >> /var/log/haymaker-health.log
```

### Cost Alert Script
```bash
# Daily cost check
0 9 * * * /path/to/scripts/estimate-costs.sh | mail -s "HayMaker Daily Costs" admin@example.com
```

---

## Troubleshooting

**If metrics missing**: Verify Application Insights configured

**If logs empty**: Check Log Analytics workspace connection

**If costs unexpected**: Run `./scripts/estimate-costs.sh`

---

**Set up monitoring BEFORE production deployment!**
