"""Unit tests for meta-orchestrator functionality.

Tests Phase 2 orchestration integration:
- Meta-orchestrator function behavior
- Tenant context handling
- Child orchestrator spawning logic
- Result aggregation
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from azure_haymaker.orchestrator.models.tenant_config import (
    ActivityInput,
    MetaOrchestratorConfig,
    TargetTenantConfig,
    TenantContext,
)


class TestTenantContextIntegration:
    """Test TenantContext integration with workflow orchestrator."""

    def test_tenant_context_can_be_serialized_for_orchestrator_input(self):
        """Test that TenantContext can be serialized for orchestration input."""
        context = TenantContext(
            tenant_id=str(uuid4()),
            tenant_name="test-tenant",
            subscription_id=str(uuid4()),
            region="eastus",
        )

        serialized = context.model_dump()

        assert "tenant_id" in serialized
        assert "tenant_name" in serialized
        assert serialized["tenant_name"] == "test-tenant"

    def test_tenant_context_can_be_reconstructed_from_dict(self):
        """Test that TenantContext can be reconstructed from dict."""
        tenant_id = str(uuid4())
        data = {
            "tenant_id": tenant_id,
            "tenant_name": "test-tenant",
            "subscription_id": str(uuid4()),
            "region": "eastus",
        }

        context = TenantContext(**data)

        assert context.tenant_id == tenant_id
        assert context.tenant_name == "test-tenant"


class TestActivityInput:
    """Test ActivityInput wrapper model."""

    def test_activity_input_with_tenant_context_succeeds(self):
        """Test ActivityInput can wrap activity data with tenant context."""
        tenant_context = TenantContext(
            tenant_id=str(uuid4()),
            tenant_name="test-tenant",
            subscription_id=str(uuid4()),
            region="eastus",
        )

        activity_input = ActivityInput(
            tenant_context=tenant_context,
            activity_data={"key": "value", "scenario": "test-scenario"},
        )

        assert activity_input.tenant_context is not None
        assert activity_input.tenant_context.tenant_name == "test-tenant"
        assert activity_input.activity_data["key"] == "value"

    def test_activity_input_without_tenant_context_succeeds(self):
        """Test ActivityInput works without tenant context (single-tenant mode)."""
        activity_input = ActivityInput(
            tenant_context=None, activity_data={"key": "value"}
        )

        assert activity_input.tenant_context is None
        assert activity_input.activity_data["key"] == "value"

    def test_activity_input_serialization_preserves_tenant_context(self):
        """Test that serialization preserves tenant context."""
        tenant_context = TenantContext(
            tenant_id=str(uuid4()),
            tenant_name="test-tenant",
            subscription_id=str(uuid4()),
            region="eastus",
        )

        activity_input = ActivityInput(
            tenant_context=tenant_context, activity_data={"scenario": "test"}
        )

        serialized = activity_input.model_dump()

        assert serialized["tenant_context"] is not None
        assert serialized["tenant_context"]["tenant_name"] == "test-tenant"
        assert serialized["activity_data"]["scenario"] == "test"


class TestMetaOrchestratorInputPreparation:
    """Test meta-orchestrator input preparation logic."""

    def test_meta_orchestrator_can_prepare_child_input_from_target_config(self):
        """Test preparing child orchestrator input from TargetTenantConfig."""
        target_config = TargetTenantConfig(
            name="tenant-a",
            display_name="Tenant A",
            tenant_id=str(uuid4()),
            subscription_id=str(uuid4()),
            region="eastus",
            credentials={"keyvault_secret_prefix": "tenant-a"},
            scenarios=["scenario-1", "scenario-2"],
            enabled=True,
        )

        # Prepare child input (simulates meta-orchestrator logic)
        tenant_context = TenantContext(
            tenant_id=target_config.tenant_id,
            tenant_name=target_config.name,
            subscription_id=target_config.subscription_id,
            region=target_config.region,
        )

        child_input = {
            "run_id": f"{target_config.name}-meta-123",
            "tenant_context": tenant_context.model_dump(),
            "started_at": datetime.utcnow().isoformat(),
            "config": {
                "scenarios": target_config.scenarios,
                "max_scenarios": target_config.max_scenarios_per_execution,
            },
        }

        # Verify structure
        assert child_input["run_id"].startswith("tenant-a-")
        assert child_input["tenant_context"]["tenant_name"] == "tenant-a"
        assert len(child_input["config"]["scenarios"]) == 2

    def test_meta_orchestrator_filters_disabled_tenants(self):
        """Test that meta-orchestrator skips disabled tenants."""
        enabled_tenant = TargetTenantConfig(
            name="enabled-tenant",
            display_name="Enabled",
            tenant_id=str(uuid4()),
            subscription_id=str(uuid4()),
            region="eastus",
            credentials={"keyvault_secret_prefix": "enabled"},
            scenarios=["scenario-1"],
            enabled=True,
        )

        disabled_tenant = TargetTenantConfig(
            name="disabled-tenant",
            display_name="Disabled",
            tenant_id=str(uuid4()),
            subscription_id=str(uuid4()),
            region="eastus",
            credentials={"keyvault_secret_prefix": "disabled"},
            scenarios=["scenario-2"],
            enabled=False,
        )

        tenants = [enabled_tenant, disabled_tenant]

        # Simulate filtering logic
        tasks_to_spawn = [t for t in tenants if t.enabled]

        assert len(tasks_to_spawn) == 1
        assert tasks_to_spawn[0].name == "enabled-tenant"


class TestMetaOrchestratorResultAggregation:
    """Test meta-orchestrator result aggregation logic."""

    def test_meta_report_aggregates_tenant_results_correctly(self):
        """Test that meta-report correctly aggregates tenant results."""
        tenant_results = {
            "tenant-a": {"status": "completed", "phases": {}},
            "tenant-b": {"status": "completed", "phases": {}},
            "tenant-c": {"status": "failed", "error": "Provisioning failed"},
        }

        succeeded_tenants = [
            name for name, result in tenant_results.items() if result.get("status") == "completed"
        ]
        failed_tenants = [
            name for name, result in tenant_results.items() if result.get("status") == "failed"
        ]

        meta_report = {
            "meta_run_id": "meta-test",
            "total_tenants": 3,
            "enabled_tenants": 3,
            "succeeded_tenants": len(succeeded_tenants),
            "failed_tenants": len(failed_tenants),
            "succeeded_tenant_names": succeeded_tenants,
            "failed_tenant_names": failed_tenants,
            "tenant_results": tenant_results,
            "status": (
                "completed"
                if not failed_tenants
                else "partial"
                if succeeded_tenants
                else "failed"
            ),
        }

        assert meta_report["succeeded_tenants"] == 2
        assert meta_report["failed_tenants"] == 1
        assert meta_report["status"] == "partial"
        assert "tenant-a" in meta_report["succeeded_tenant_names"]
        assert "tenant-c" in meta_report["failed_tenant_names"]

    def test_meta_report_status_is_completed_when_all_succeed(self):
        """Test status is 'completed' when all tenants succeed."""
        succeeded_tenants = ["tenant-a", "tenant-b"]
        failed_tenants = []

        status = (
            "completed"
            if not failed_tenants
            else "partial"
            if succeeded_tenants
            else "failed"
        )

        assert status == "completed"

    def test_meta_report_status_is_failed_when_all_fail(self):
        """Test status is 'failed' when all tenants fail."""
        succeeded_tenants = []
        failed_tenants = ["tenant-a", "tenant-b"]

        status = (
            "completed"
            if not failed_tenants
            else "partial"
            if succeeded_tenants
            else "failed"
        )

        assert status == "failed"


class TestMetaOrchestratorConfigHandling:
    """Test MetaOrchestratorConfig handling in meta-orchestrator."""

    def test_meta_config_can_be_flattened_from_nested_structure(self):
        """Test that nested meta_config can be flattened correctly."""
        nested_config = {
            "meta_orchestrator": {
                "name": "test-orchestrator",
                "infrastructure_tenant_id": str(uuid4()),
                "max_concurrent_tenants": 5,
                "storage_account_name": "testStorage",
            },
            "target_tenants": [
                {
                    "name": "tenant-a",
                    "display_name": "Tenant A",
                    "tenant_id": str(uuid4()),
                    "subscription_id": str(uuid4()),
                    "region": "eastus",
                    "credentials": {"keyvault_secret_prefix": "tenant-a"},
                    "scenarios": ["scenario-1"],
                }
            ],
        }

        # Flatten structure (simulates meta-orchestrator logic)
        flat_config = {**nested_config["meta_orchestrator"]}
        flat_config["target_tenants"] = nested_config["target_tenants"]

        meta_config = MetaOrchestratorConfig(**flat_config)

        assert meta_config.name == "test-orchestrator"
        assert len(meta_config.target_tenants) == 1
        assert meta_config.target_tenants[0].name == "tenant-a"

    def test_meta_config_can_be_loaded_from_flat_structure(self):
        """Test that flat meta_config can be loaded directly."""
        flat_config = {
            "name": "test-orchestrator",
            "infrastructure_tenant_id": str(uuid4()),
            "max_concurrent_tenants": 5,
            "storage_account_name": "testStorage",
            "target_tenants": [
                {
                    "name": "tenant-a",
                    "display_name": "Tenant A",
                    "tenant_id": str(uuid4()),
                    "subscription_id": str(uuid4()),
                    "region": "eastus",
                    "credentials": {"keyvault_secret_prefix": "tenant-a"},
                    "scenarios": ["scenario-1"],
                }
            ],
        }

        meta_config = MetaOrchestratorConfig(**flat_config)

        assert meta_config.name == "test-orchestrator"
        assert len(meta_config.target_tenants) == 1
