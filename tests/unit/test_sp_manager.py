"""Tests for Service Principal Manager.

This module tests the creation, role assignment, and deletion of ephemeral
service principals for scenario execution.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.keyvault.secrets import SecretClient

from azure_haymaker.orchestrator.sp_manager import (
    ServicePrincipalDetails,
    ServicePrincipalError,
    create_service_principal,
    delete_service_principal,
    list_haymaker_service_principals,
    verify_sp_deleted,
)


class TestServicePrincipalDetails:
    """Test ServicePrincipalDetails dataclass."""

    def test_service_principal_details_creation(self):
        """Test creating ServicePrincipalDetails instance."""
        details = ServicePrincipalDetails(
            sp_name="AzureHayMaker-test-scenario-admin",
            client_id="12345678-1234-1234-1234-123456789abc",
            principal_id="87654321-4321-4321-4321-cba987654321",
            secret_reference="scenario-sp-test-scenario-secret",
            created_at="2025-11-14T12:00:00Z",
        )

        assert details.sp_name == "AzureHayMaker-test-scenario-admin"
        assert details.client_id == "12345678-1234-1234-1234-123456789abc"
        assert details.principal_id == "87654321-4321-4321-4321-cba987654321"
        assert details.secret_reference == "scenario-sp-test-scenario-secret"
        assert details.created_at == "2025-11-14T12:00:00Z"


class TestCreateServicePrincipal:
    """Test service principal creation."""

    @pytest.mark.asyncio
    async def test_create_service_principal_success(self):
        """Test successful service principal creation with role assignment."""
        # Mock Microsoft Graph client
        mock_graph_client = MagicMock()
        mock_app_result = MagicMock()
        mock_app_result.id = "app-obj-id"
        mock_app_result.app_id = "12345678-1234-1234-1234-123456789abc"

        mock_sp_result = MagicMock()
        mock_sp_result.id = "87654321-4321-4321-4321-cba987654321"

        mock_password_credential = MagicMock()
        mock_password_credential.secret_text = "test-secret-value"

        # Configure mock chains
        mock_graph_client.applications.post.return_value = mock_app_result
        mock_graph_client.service_principals.post.return_value = mock_sp_result
        mock_graph_client.applications.by_application_id().add_password.post.return_value = (
            mock_password_credential
        )

        # Mock Key Vault client
        mock_kv_client = AsyncMock(spec=SecretClient)

        # Mock Azure authorization client
        mock_auth_client = MagicMock()

        with (
            patch(
                "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
                return_value=mock_graph_client,
            ),
            patch(
                "azure_haymaker.orchestrator.sp_manager.AuthorizationManagementClient",
                return_value=mock_auth_client,
            ),
            patch("azure_haymaker.orchestrator.sp_manager.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await create_service_principal(
                scenario_name="test-scenario",
                subscription_id="sub-12345",
                roles=["Contributor"],
                key_vault_client=mock_kv_client,
            )

        # Verify SP details
        assert result.sp_name == "AzureHayMaker-test-scenario-admin"
        assert result.client_id == "12345678-1234-1234-1234-123456789abc"
        assert result.principal_id == "87654321-4321-4321-4321-cba987654321"
        assert result.secret_reference == "scenario-sp-test-scenario-secret"
        assert result.created_at is not None

        # Verify Key Vault secret was stored
        mock_kv_client.set_secret.assert_called_once()
        call_args = mock_kv_client.set_secret.call_args
        assert call_args[0][0] == "scenario-sp-test-scenario-secret"
        assert call_args[0][1] == "test-secret-value"

    @pytest.mark.asyncio
    async def test_create_service_principal_graph_api_failure(self):
        """Test handling of Microsoft Graph API failure."""
        mock_graph_client = MagicMock()
        mock_graph_client.applications.post.side_effect = Exception("Graph API error")

        mock_kv_client = AsyncMock(spec=SecretClient)

        with (
            patch(
                "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
                return_value=mock_graph_client,
            ),
            pytest.raises(ServicePrincipalError, match="Graph API error"),
        ):
            await create_service_principal(
                scenario_name="test-scenario",
                subscription_id="sub-12345",
                roles=["Contributor"],
                key_vault_client=mock_kv_client,
            )

    @pytest.mark.asyncio
    async def test_create_service_principal_keyvault_failure(self):
        """Test handling of Key Vault storage failure."""
        mock_graph_client = MagicMock()
        mock_app_result = MagicMock()
        mock_app_result.id = "app-obj-id"
        mock_app_result.app_id = "12345678-1234-1234-1234-123456789abc"

        mock_sp_result = MagicMock()
        mock_sp_result.id = "87654321-4321-4321-4321-cba987654321"

        mock_password_credential = MagicMock()
        mock_password_credential.secret_text = "test-secret-value"

        mock_graph_client.applications.post.return_value = mock_app_result
        mock_graph_client.service_principals.post.return_value = mock_sp_result
        mock_graph_client.applications.by_application_id().add_password.post.return_value = (
            mock_password_credential
        )

        # Mock Key Vault client with failure
        mock_kv_client = AsyncMock(spec=SecretClient)
        mock_kv_client.set_secret.side_effect = Exception("Key Vault error")

        with (
            patch(
                "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
                return_value=mock_graph_client,
            ),
            pytest.raises(ServicePrincipalError, match="Key Vault error"),
        ):
            await create_service_principal(
                scenario_name="test-scenario",
                subscription_id="sub-12345",
                roles=["Contributor"],
                key_vault_client=mock_kv_client,
            )

    @pytest.mark.asyncio
    async def test_create_service_principal_multiple_roles(self):
        """Test service principal creation with multiple role assignments."""
        mock_graph_client = MagicMock()
        mock_app_result = MagicMock()
        mock_app_result.id = "app-obj-id"
        mock_app_result.app_id = "12345678-1234-1234-1234-123456789abc"

        mock_sp_result = MagicMock()
        mock_sp_result.id = "87654321-4321-4321-4321-cba987654321"

        mock_password_credential = MagicMock()
        mock_password_credential.secret_text = "test-secret-value"

        mock_graph_client.applications.post.return_value = mock_app_result
        mock_graph_client.service_principals.post.return_value = mock_sp_result
        mock_graph_client.applications.by_application_id().add_password.post.return_value = (
            mock_password_credential
        )

        mock_kv_client = AsyncMock(spec=SecretClient)
        mock_auth_client = MagicMock()

        with (
            patch(
                "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
                return_value=mock_graph_client,
            ),
            patch(
                "azure_haymaker.orchestrator.sp_manager.AuthorizationManagementClient",
                return_value=mock_auth_client,
            ),
            patch("azure_haymaker.orchestrator.sp_manager.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await create_service_principal(
                scenario_name="test-scenario",
                subscription_id="sub-12345",
                roles=["Contributor", "Reader"],
                key_vault_client=mock_kv_client,
            )

        # Verify both roles were assigned
        assert mock_auth_client.role_assignments.create.call_count == 2


class TestDeleteServicePrincipal:
    """Test service principal deletion."""

    @pytest.mark.asyncio
    async def test_delete_service_principal_success(self):
        """Test successful service principal and secret deletion."""
        mock_graph_client = MagicMock()
        mock_sp_list = MagicMock()
        mock_sp = MagicMock()
        mock_sp.id = "sp-obj-id"
        mock_sp.app_id = "app-id-12345"
        mock_sp_list.value = [mock_sp]

        mock_graph_client.service_principals.get.return_value = mock_sp_list

        mock_kv_client = AsyncMock(spec=SecretClient)

        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
            return_value=mock_graph_client,
        ):
            await delete_service_principal(
                sp_name="AzureHayMaker-test-scenario-admin",
                key_vault_client=mock_kv_client,
            )

        # Verify SP was deleted
        mock_graph_client.service_principals.by_service_principal_id().delete.assert_called_once()

        # Verify Key Vault secret was deleted
        mock_kv_client.begin_delete_secret.assert_called_once_with(
            "scenario-sp-test-scenario-secret"
        )

    @pytest.mark.asyncio
    async def test_delete_service_principal_not_found(self):
        """Test deletion when service principal doesn't exist."""
        mock_graph_client = MagicMock()
        mock_sp_list = MagicMock()
        mock_sp_list.value = []

        mock_graph_client.service_principals.get.return_value = mock_sp_list

        mock_kv_client = AsyncMock(spec=SecretClient)

        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
            return_value=mock_graph_client,
        ):
            # Should not raise error, just log warning
            await delete_service_principal(
                sp_name="AzureHayMaker-nonexistent-admin",
                key_vault_client=mock_kv_client,
            )

        # Verify we still tried to delete the secret
        mock_kv_client.begin_delete_secret.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_service_principal_keyvault_not_found(self):
        """Test deletion when Key Vault secret doesn't exist."""
        mock_graph_client = MagicMock()
        mock_sp_list = MagicMock()
        mock_sp = MagicMock()
        mock_sp.id = "sp-obj-id"
        mock_sp.app_id = "app-id-12345"
        mock_sp_list.value = [mock_sp]

        mock_graph_client.service_principals.get.return_value = mock_sp_list

        mock_kv_client = AsyncMock(spec=SecretClient)
        mock_kv_client.begin_delete_secret.side_effect = ResourceNotFoundError("Secret not found")

        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
            return_value=mock_graph_client,
        ):
            # Should not raise error for missing secret
            await delete_service_principal(
                sp_name="AzureHayMaker-test-scenario-admin",
                key_vault_client=mock_kv_client,
            )

        # Verify SP deletion was still attempted
        mock_graph_client.service_principals.by_service_principal_id().delete.assert_called_once()


class TestVerifySpDeleted:
    """Test verification of service principal deletion."""

    @pytest.mark.asyncio
    async def test_verify_sp_deleted_success_not_found(self):
        """Test verification when SP is deleted (not found)."""
        mock_graph_client = MagicMock()
        mock_sp_list = MagicMock()
        mock_sp_list.value = []

        mock_graph_client.service_principals.get.return_value = mock_sp_list

        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
            return_value=mock_graph_client,
        ):
            result = await verify_sp_deleted("AzureHayMaker-test-scenario-admin")

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_sp_deleted_still_exists(self):
        """Test verification when SP still exists."""
        mock_graph_client = MagicMock()
        mock_sp_list = MagicMock()

        mock_sp = MagicMock()
        mock_sp.display_name = "AzureHayMaker-test-scenario-admin"
        mock_sp_list.value = [mock_sp]

        mock_graph_client.service_principals.get.return_value = mock_sp_list

        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
            return_value=mock_graph_client,
        ):
            result = await verify_sp_deleted("AzureHayMaker-test-scenario-admin")

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_sp_deleted_none_response(self):
        """Test verification when SP list response is None."""
        mock_graph_client = MagicMock()
        mock_graph_client.service_principals.get.return_value = None

        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
            return_value=mock_graph_client,
        ):
            result = await verify_sp_deleted("AzureHayMaker-test-scenario-admin")

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_sp_deleted_api_error(self):
        """Test verification handles API errors."""
        mock_graph_client = MagicMock()
        mock_graph_client.service_principals.get.side_effect = Exception("Graph API error")

        with (
            patch(
                "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
                return_value=mock_graph_client,
            ),
            pytest.raises(ServicePrincipalError, match="Graph API error"),
        ):
            await verify_sp_deleted("AzureHayMaker-test-scenario-admin")


class TestListHaymakerServicePrincipals:
    """Test listing HayMaker service principals."""

    @pytest.mark.asyncio
    async def test_list_haymaker_service_principals_success(self):
        """Test listing all HayMaker service principals."""
        mock_graph_client = MagicMock()
        mock_sp_list = MagicMock()

        mock_sp1 = MagicMock()
        mock_sp1.display_name = "AzureHayMaker-scenario1-admin"

        mock_sp2 = MagicMock()
        mock_sp2.display_name = "AzureHayMaker-scenario2-admin"

        mock_sp3 = MagicMock()
        mock_sp3.display_name = "OtherServicePrincipal"

        mock_sp_list.value = [mock_sp1, mock_sp2, mock_sp3]
        mock_graph_client.service_principals.get.return_value = mock_sp_list

        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
            return_value=mock_graph_client,
        ):
            result = await list_haymaker_service_principals()

        # Should only return HayMaker SPs
        assert len(result) == 2
        assert "AzureHayMaker-scenario1-admin" in result
        assert "AzureHayMaker-scenario2-admin" in result
        assert "OtherServicePrincipal" not in result

    @pytest.mark.asyncio
    async def test_list_haymaker_service_principals_empty(self):
        """Test listing when no HayMaker service principals exist."""
        mock_graph_client = MagicMock()
        mock_sp_list = MagicMock()
        mock_sp_list.value = []

        mock_graph_client.service_principals.get.return_value = mock_sp_list

        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient",
            return_value=mock_graph_client,
        ):
            result = await list_haymaker_service_principals()

        assert result == []
