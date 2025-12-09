"""Sample tenant configurations for testing."""

from datetime import datetime, timezone
from uuid import uuid4


def sample_tenant_context():
    """Create a sample TenantContext for testing."""
    return {
        "tenant_id": str(uuid4()),
        "tenant_name": "test-tenant",
        "subscription_id": str(uuid4()),
        "region": "eastus",
    }


def sample_target_tenant_config():
    """Create a sample TargetTenantConfig for testing."""
    return {
        "name": "customer-a",
        "display_name": "Customer A",
        "description": "Test customer A",
        "tenant_id": str(uuid4()),
        "subscription_id": str(uuid4()),
        "region": "eastus",
        "credentials": {"keyvault_secret_prefix": "customer-a"},
        "enabled": True,
        "scenarios": [
            "compute-01-linux-vm-web-server",
            "databases-01-mysql-wordpress",
        ],
        "scenario_selection_mode": "all",
        "max_scenarios_per_execution": 10,
        "schedule": {
            "cron": "0 */6 * * *",
            "timezone": "UTC",
            "enabled": True,
        },
        "resource_tags": {
            "Environment": "Test",
            "Customer": "CustomerA",
            "ManagedBy": "HayMaker",
        },
        "resource_naming": {
            "prefix": "test-cust-a",
            "suffix": "",
            "include_timestamp": True,
        },
        "limits": {
            "max_resource_groups": 20,
            "max_vms": 10,
            "max_storage_accounts": 5,
            "max_cost_per_day_usd": 50.0,
        },
        "monitoring": {
            "enable_alerts": True,
            "alert_email": "ops@example.com",
            "enable_cost_alerts": True,
            "cost_alert_threshold_usd": 40.0,
        },
        "cleanup": {
            "auto_cleanup": True,
            "cleanup_delay_hours": 0,
            "retain_failed_resources": True,
            "retention_days": 30,
        },
    }


def sample_meta_orchestrator_config():
    """Create a sample MetaOrchestratorConfig for testing."""
    return {
        "name": "test-orchestrator",
        "infrastructure_tenant_id": str(uuid4()),
        "max_concurrent_tenants": 5,
        "max_concurrent_scenarios_per_tenant": 10,
        "polling_interval_seconds": 30,
        "health_check_interval_seconds": 60,
        "execution_timeout_hours": 24,
        "max_retry_attempts": 3,
        "retry_delay_seconds": 60,
        "enable_circuit_breaker": True,
        "circuit_breaker_threshold": 5,
        "storage_account_name": "haymakertestStorage",
        "application_insights_key": str(uuid4()),
        "log_level": "info",
        "enable_tenant_isolation": True,
        "enable_cost_tracking": True,
        "enable_distributed_tracing": True,
    }


def sample_multi_tenant_config():
    """Create a complete multi-tenant configuration for testing."""
    tenant_a_id = str(uuid4())
    tenant_b_id = str(uuid4())
    tenant_a_sub_id = str(uuid4())
    tenant_b_sub_id = str(uuid4())

    return {
        "meta_orchestrator": sample_meta_orchestrator_config(),
        "target_tenants": [
            {
                "name": "tenant-a",
                "display_name": "Tenant A",
                "tenant_id": tenant_a_id,
                "subscription_id": tenant_a_sub_id,
                "region": "eastus",
                "credentials": {"keyvault_secret_prefix": "tenant-a"},
                "enabled": True,
                "scenarios": ["compute-01-linux-vm-web-server"],
                "schedule": {"cron": "0 */6 * * *", "timezone": "UTC", "enabled": True},
            },
            {
                "name": "tenant-b",
                "display_name": "Tenant B",
                "tenant_id": tenant_b_id,
                "subscription_id": tenant_b_sub_id,
                "region": "westus",
                "credentials": {"keyvault_secret_prefix": "tenant-b"},
                "enabled": True,
                "scenarios": ["databases-01-mysql-wordpress"],
                "schedule": {"cron": "0 0,12 * * *", "timezone": "UTC", "enabled": True},
            },
        ],
    }


def invalid_tenant_context_non_uuid():
    """Invalid TenantContext with non-UUID tenant_id."""
    return {
        "tenant_id": "not-a-uuid",
        "tenant_name": "test-tenant",
        "subscription_id": str(uuid4()),
        "region": "eastus",
    }


def invalid_target_tenant_duplicate_name():
    """Two target tenants with duplicate names."""
    tenant_config = sample_target_tenant_config()
    return [tenant_config, tenant_config.copy()]


def invalid_target_tenant_invalid_cron():
    """Invalid cron expression in schedule."""
    config = sample_target_tenant_config()
    config["schedule"]["cron"] = "invalid cron expression"
    return config


def disabled_tenant_config():
    """Target tenant config with enabled=False."""
    config = sample_target_tenant_config()
    config["name"] = "disabled-tenant"
    config["enabled"] = False
    return config
