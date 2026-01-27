"""Unit tests for environment validation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import ClientAuthenticationError
from pydantic import SecretStr

from azure_haymaker.llm import LLMResponse
from azure_haymaker.models.config import (
    CosmosDBConfig,
    LogAnalyticsConfig,
    OrchestratorConfig,
    SimulationSize,
    StorageConfig,
    TableStorageConfig,
)
from azure_haymaker.orchestrator.validation import (
    ValidationReport,
    ValidationResult,
    validate_anthropic_api,
    validate_azure_credentials,
    validate_environment,
    validate_llm_provider,
)


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_validation_result_passed(self) -> None:
        """Test successful validation result."""
        result = ValidationResult(
            check_name="test_check",
            passed=True,
            details={"test": "data"},
        )

        assert result.passed
        assert result.error is None
        assert result.details == {"test": "data"}

    def test_validation_result_failed(self) -> None:
        """Test failed validation result."""
        result = ValidationResult(
            check_name="test_check",
            passed=False,
            error="Something went wrong",
        )

        assert not result.passed
        assert result.error == "Something went wrong"


class TestValidationReport:
    """Tests for ValidationReport model."""

    def test_validation_report_all_passed(self) -> None:
        """Test validation report when all checks pass."""
        report = ValidationReport(
            overall_passed=True,
            results=[
                ValidationResult(check_name="check1", passed=True),
                ValidationResult(check_name="check2", passed=True),
            ],
        )

        assert report.overall_passed
        assert len(report.get_failed_checks()) == 0

    def test_validation_report_some_failed(self) -> None:
        """Test validation report with failures."""
        report = ValidationReport(
            overall_passed=False,
            results=[
                ValidationResult(check_name="check1", passed=True),
                ValidationResult(check_name="check2", passed=False, error="Failed"),
            ],
        )

        assert not report.overall_passed
        failed = report.get_failed_checks()
        assert len(failed) == 1
        assert failed[0].check_name == "check2"


@pytest.fixture
def mock_config() -> OrchestratorConfig:
    """Create a mock configuration for testing."""
    return OrchestratorConfig(
        target_tenant_id="12345678-1234-1234-1234-123456789012",
        target_subscription_id="87654321-4321-4321-4321-210987654321",
        main_sp_client_id="11111111-1111-1111-1111-111111111111",
        main_sp_client_secret=SecretStr("super-secret"),
        anthropic_api_key=SecretStr("sk-ant-test"),
        service_bus_namespace="haymaker-sb",
        container_registry="haymaker.azurecr.io",
        container_image="haymaker-agent:latest",
        key_vault_url="https://haymaker-kv.vault.azure.net",
        simulation_size=SimulationSize.SMALL,
        vnet_integration_enabled=False,
        storage=StorageConfig(
            account_name="haymakerstorage",
            container_logs="execution-logs",
            container_state="execution-state",
            container_reports="execution-reports",
            container_scenarios="scenarios",
        ),
        table_storage=TableStorageConfig(
            account_name="haymakertables",
            table_execution_runs="ExecutionRuns",
            table_scenario_status="ScenarioStatus",
            table_resource_inventory="ResourceInventory",
        ),
        cosmosdb=CosmosDBConfig(
            endpoint="https://haymakerdb.documents.azure.com:443/",
            database_name="haymaker",
            container_metrics="metrics",
        ),
        log_analytics=LogAnalyticsConfig(
            workspace_id="12345678-1234-1234-1234-123456789012",
            workspace_key=SecretStr("workspace-key"),
        ),
    )


class TestValidateAzureCredentials:
    """Tests for Azure credentials validation."""

    @pytest.mark.asyncio
    async def test_validate_azure_credentials_success(
        self, mock_config: OrchestratorConfig
    ) -> None:
        """Test successful Azure credentials validation."""
        with patch(
            "azure_haymaker.orchestrator.validation.ResourceManagementClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.resource_groups.list.return_value = []
            mock_client.return_value = mock_instance

            result = await validate_azure_credentials(mock_config)

            assert result.passed
            assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_azure_credentials_failure(
        self, mock_config: OrchestratorConfig
    ) -> None:
        """Test Azure credentials validation failure."""
        with patch(
            "azure_haymaker.orchestrator.validation.ResourceManagementClient"
        ) as mock_client:
            mock_client.side_effect = ClientAuthenticationError("Auth failed")

            result = await validate_azure_credentials(mock_config)

            assert not result.passed
            assert result.error is not None
            assert "Auth failed" in result.error


class TestValidateLLMProvider:
    """Tests for LLM provider validation."""

    @pytest.mark.asyncio
    async def test_validate_llm_provider_success(self, mock_config: OrchestratorConfig) -> None:
        """Test successful LLM provider validation."""
        with patch("azure_haymaker.orchestrator.validation.create_llm_client") as mock_create:
            mock_response = LLMResponse(
                content="Hello",
                model="claude-sonnet-4-5-20250929",
                usage={"input_tokens": 5, "output_tokens": 1},
            )
            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            result = await validate_llm_provider(mock_config)

            assert result.passed
            assert result.error is None
            assert result.details["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_validate_llm_provider_failure(self, mock_config: OrchestratorConfig) -> None:
        """Test LLM provider validation failure."""
        with patch("azure_haymaker.orchestrator.validation.create_llm_client") as mock_create:
            mock_create.side_effect = Exception("API key invalid")

            result = await validate_llm_provider(mock_config)

            assert not result.passed
            assert result.error is not None
            assert "API key invalid" in result.error


class TestValidateAnthropicAPI:
    """Tests for Anthropic API validation (backward compatibility)."""

    @pytest.mark.asyncio
    async def test_validate_anthropic_api_success(self, mock_config: OrchestratorConfig) -> None:
        """Test successful Anthropic API validation via backward compatibility alias."""
        with patch("azure_haymaker.orchestrator.validation.create_llm_client") as mock_create:
            mock_response = LLMResponse(
                content="Hello",
                model="claude-sonnet-4-5-20250929",
                usage={"input_tokens": 5, "output_tokens": 1},
            )
            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            result = await validate_anthropic_api(mock_config)

            assert result.passed
            assert result.error is None
            # The backward compat alias uses 'anthropic_api' check_name
            assert result.check_name == "anthropic_api"

    @pytest.mark.asyncio
    async def test_validate_anthropic_api_failure(self, mock_config: OrchestratorConfig) -> None:
        """Test Anthropic API validation failure via backward compatibility alias."""
        with patch("azure_haymaker.orchestrator.validation.create_llm_client") as mock_create:
            mock_create.side_effect = Exception("API key invalid")

            result = await validate_anthropic_api(mock_config)

            assert not result.passed
            assert result.error is not None
            assert "API key invalid" in result.error


class TestValidateEnvironment:
    """Tests for complete environment validation."""

    @pytest.mark.asyncio
    async def test_validate_environment_all_pass(self, mock_config: OrchestratorConfig) -> None:
        """Test complete environment validation when all checks pass."""
        with (
            patch(
                "azure_haymaker.orchestrator.validation.validate_azure_credentials",
                return_value=ValidationResult(check_name="azure_credentials", passed=True),
            ),
            patch(
                "azure_haymaker.orchestrator.validation.validate_llm_provider",
                return_value=ValidationResult(check_name="llm_provider", passed=True),
            ),
            patch(
                "azure_haymaker.orchestrator.validation.validate_container_image",
                return_value=ValidationResult(check_name="container_image", passed=True),
            ),
            patch(
                "azure_haymaker.orchestrator.validation.validate_service_bus",
                return_value=ValidationResult(check_name="service_bus", passed=True),
            ),
        ):
            report = await validate_environment(mock_config)

            assert report.overall_passed
            assert len(report.results) >= 4
            assert all(r.passed for r in report.results)

    @pytest.mark.asyncio
    async def test_validate_environment_some_fail(self, mock_config: OrchestratorConfig) -> None:
        """Test complete environment validation with failures."""
        with (
            patch(
                "azure_haymaker.orchestrator.validation.validate_azure_credentials",
                return_value=ValidationResult(check_name="azure_credentials", passed=True),
            ),
            patch(
                "azure_haymaker.orchestrator.validation.validate_llm_provider",
                return_value=ValidationResult(
                    check_name="llm_provider", passed=False, error="LLM failed"
                ),
            ),
            patch(
                "azure_haymaker.orchestrator.validation.validate_container_image",
                return_value=ValidationResult(check_name="container_image", passed=True),
            ),
            patch(
                "azure_haymaker.orchestrator.validation.validate_service_bus",
                return_value=ValidationResult(check_name="service_bus", passed=True),
            ),
        ):
            report = await validate_environment(mock_config)

            # LLM provider is not critical, so overall should still pass
            assert report.overall_passed
            failed = report.get_failed_checks()
            assert len(failed) == 1
            assert failed[0].check_name == "llm_provider"
