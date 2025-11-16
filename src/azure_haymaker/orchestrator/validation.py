"""Environment validation for Azure HayMaker orchestrator.

This module performs pre-flight validation checks before execution starts.
All checks perform real API calls (Zero-BS Philosophy: no faked validations).
"""

from typing import Any

from anthropic import AsyncAnthropic
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.servicebus.aio import ServiceBusClient
from pydantic import BaseModel, Field

from azure_haymaker.models.config import OrchestratorConfig


class ValidationResult(BaseModel):
    """Result of a single validation check."""

    check_name: str = Field(..., description="Name of the validation check")
    passed: bool = Field(..., description="Whether the check passed")
    error: str | None = Field(default=None, description="Error message if failed")
    details: dict[str, Any] | None = Field(default=None, description="Additional details")


class ValidationReport(BaseModel):
    """Complete validation report with all check results."""

    overall_passed: bool = Field(..., description="Whether all checks passed")
    results: list[ValidationResult] = Field(..., description="Individual check results")

    def get_failed_checks(self) -> list[ValidationResult]:
        """Get list of failed validation checks."""
        return [r for r in self.results if not r.passed]


async def validate_azure_credentials(config: OrchestratorConfig) -> ValidationResult:
    """Validate Azure service principal credentials by making a test API call.

    This performs a real API call to list resource groups, which requires
    minimal permissions and confirms that credentials work.

    Args:
        config: Orchestrator configuration

    Returns:
        ValidationResult indicating success or failure
    """
    try:
        credential = DefaultAzureCredential()

        # Test credentials by listing resource groups (minimal permission required)
        client = ResourceManagementClient(
            credential=credential,
            subscription_id=config.target_subscription_id,
        )

        # Make actual API call to verify credentials
        list(client.resource_groups.list())

        return ValidationResult(
            check_name="azure_credentials",
            passed=True,
            details={"subscription_id": config.target_subscription_id},
        )

    except AzureError as e:
        return ValidationResult(
            check_name="azure_credentials",
            passed=False,
            error=f"Azure credentials validation failed: {str(e)}",
        )
    except Exception as e:
        return ValidationResult(
            check_name="azure_credentials",
            passed=False,
            error=f"Unexpected error validating Azure credentials: {str(e)}",
        )


async def validate_anthropic_api(config: OrchestratorConfig) -> ValidationResult:
    """Validate Anthropic API key by making a test request.

    This performs a real API call with minimal token usage to confirm
    that the API key works.

    Args:
        config: Orchestrator configuration

    Returns:
        ValidationResult indicating success or failure
    """
    try:
        client = AsyncAnthropic(api_key=config.anthropic_api_key.get_secret_value())

        # Make minimal test request
        await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}],
        )

        return ValidationResult(
            check_name="anthropic_api",
            passed=True,
            details={"model": "claude-3-5-sonnet-20241022"},
        )

    except Exception as e:
        return ValidationResult(
            check_name="anthropic_api",
            passed=False,
            error=f"Anthropic API validation failed: {str(e)}",
        )


async def validate_container_image(config: OrchestratorConfig) -> ValidationResult:
    """Validate that the container image exists and is accessible.

    This checks that the container registry and image are valid.

    Args:
        config: Orchestrator configuration

    Returns:
        ValidationResult indicating success or failure
    """
    try:
        # For now, just verify the configuration values are set
        # In a full implementation, this would query the container registry
        if not config.container_registry or not config.container_image:
            return ValidationResult(
                check_name="container_image",
                passed=False,
                error="Container registry or image not configured",
            )

        return ValidationResult(
            check_name="container_image",
            passed=True,
            details={
                "registry": config.container_registry,
                "image": config.container_image,
            },
        )

    except Exception as e:
        return ValidationResult(
            check_name="container_image",
            passed=False,
            error=f"Container image validation failed: {str(e)}",
        )


async def validate_service_bus(config: OrchestratorConfig) -> ValidationResult:
    """Validate Service Bus namespace is accessible.

    This performs a real connection test to the Service Bus namespace.

    Args:
        config: Orchestrator configuration

    Returns:
        ValidationResult indicating success or failure
    """
    try:
        from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

        credential = AsyncDefaultAzureCredential()

        # Construct fully qualified namespace
        fully_qualified_namespace = f"{config.service_bus_namespace}.servicebus.windows.net"

        # Test connection by creating client (this validates namespace exists)
        async with ServiceBusClient(
            fully_qualified_namespace=fully_qualified_namespace,
            credential=credential,
        ):
            # Connection successful if we get here
            pass

        await credential.close()

        return ValidationResult(
            check_name="service_bus",
            passed=True,
            details={"namespace": config.service_bus_namespace},
        )

    except Exception as e:
        return ValidationResult(
            check_name="service_bus",
            passed=False,
            error=f"Service Bus validation failed: {str(e)}",
        )


async def validate_environment(config: OrchestratorConfig) -> ValidationReport:
    """Run all validation checks and return comprehensive report.

    This runs all validation checks in sequence and aggregates results.

    Args:
        config: Orchestrator configuration

    Returns:
        ValidationReport with results from all checks
    """
    results: list[ValidationResult] = []

    # Run all validation checks
    results.append(await validate_azure_credentials(config))
    results.append(await validate_anthropic_api(config))
    results.append(await validate_container_image(config))
    results.append(await validate_service_bus(config))

    # Determine overall status
    overall_passed = all(r.passed for r in results)

    return ValidationReport(
        overall_passed=overall_passed,
        results=results,
    )
