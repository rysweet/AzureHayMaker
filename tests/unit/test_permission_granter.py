"""Unit tests for PermissionGranter following TDD principles.

Tests ensure automatic Mail.ReadWrite permission granting functionality
works correctly for Knowledge Worker deployments.

Test Coverage:
- Happy path: Permission grant when not already present
- Idempotency: No-op when permission already granted
- Error handling: Service principal not found
- Error handling: Duplicate grant race condition
- Error handling: Graph API failures
- Phase setup integration
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from azure_haymaker.knowledge_worker.identity.permission_granter import PermissionGranter


class TestPermissionGranterHappyPath:
    """Test successful permission granting scenarios."""

    @pytest.mark.anyio
    async def test_ensure_mail_permission_when_not_granted(self):
        """Test granting Mail.ReadWrite when permission not yet present.

        Critical path: First-time permission grant must succeed.
        Verifies:
        - Service principal lookup succeeds
        - Permission check returns False (not granted)
        - Grant operation succeeds
        - Returns True
        """
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        sp_object_id = str(uuid4())
        graph_sp_id = str(uuid4())

        # Mock our service principal
        our_sp = Mock()
        our_sp.id = sp_object_id

        # Mock Graph service principal
        graph_sp = Mock()
        graph_sp.id = graph_sp_id

        # Mock service principal lookups
        mock_graph.service_principals.get = AsyncMock()

        async def mock_get_sp(request_configuration=None):
            filter_param = request_configuration.query_parameters.filter
            if app_id in filter_param:
                result = Mock()
                result.value = [our_sp]
                return result
            elif PermissionGranter.GRAPH_RESOURCE_APP_ID in filter_param:
                result = Mock()
                result.value = [graph_sp]
                return result
            result = Mock()
            result.value = []
            return result

        mock_graph.service_principals.get.side_effect = mock_get_sp

        # Mock permission check - not granted yet
        mock_sp_by_id = Mock()
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        assignments = Mock()
        assignments.value = []  # No permissions yet
        mock_sp_by_id.app_role_assignments.get = AsyncMock(return_value=assignments)

        # Mock grant operation
        mock_sp_by_id.app_role_assigned_to.post = AsyncMock()

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        result = await granter.ensure_mail_permission()

        # Assert
        assert result is True, "Should return True on successful grant"

        # Should grant BOTH Mail.ReadWrite and Mail.Send
        assert (
            mock_sp_by_id.app_role_assigned_to.post.call_count == 2
        ), "Should grant both permissions"

        # Verify both permissions were granted
        call_args_list = mock_sp_by_id.app_role_assigned_to.post.call_args_list
        # app_role_id is converted to UUID object, so compare string representations
        granted_role_ids = {str(call[0][0].app_role_id) for call in call_args_list}
        assert PermissionGranter.MAIL_READWRITE_ROLE_ID in granted_role_ids
        assert PermissionGranter.MAIL_SEND_ROLE_ID in granted_role_ids

    @pytest.mark.anyio
    async def test_ensure_mail_permission_when_already_granted(self):
        """Test idempotent behavior when permission already exists.

        Critical path: Repeated calls should not duplicate permissions.
        Verifies:
        - Service principal lookup succeeds
        - Permission check returns True (already granted)
        - No grant operation attempted
        - Returns True
        """
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        sp_object_id = str(uuid4())

        # Mock our service principal
        our_sp = Mock()
        our_sp.id = sp_object_id

        # Mock Graph service principal
        graph_sp = Mock()
        graph_sp.id = str(uuid4())

        # Mock service principal lookups
        async def mock_get_sp(request_configuration=None):
            filter_param = request_configuration.query_parameters.filter
            if app_id in filter_param:
                result = Mock()
                result.value = [our_sp]
                return result
            elif PermissionGranter.GRAPH_RESOURCE_APP_ID in filter_param:
                result = Mock()
                result.value = [graph_sp]
                return result
            result = Mock()
            result.value = []
            return result

        mock_graph.service_principals.get = AsyncMock(side_effect=mock_get_sp)

        # Mock permission check - already granted
        mock_sp_by_id = Mock()
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        # Mock BOTH permissions as already granted
        mail_readwrite_assignment = Mock()
        mail_readwrite_assignment.app_role_id = PermissionGranter.MAIL_READWRITE_ROLE_ID

        mail_send_assignment = Mock()
        mail_send_assignment.app_role_id = PermissionGranter.MAIL_SEND_ROLE_ID

        assignments = Mock()
        assignments.value = [mail_readwrite_assignment, mail_send_assignment]
        mock_sp_by_id.app_role_assignments.get = AsyncMock(return_value=assignments)

        # Mock grant operation (should not be called since both already granted)
        mock_sp_by_id.app_role_assigned_to.post = AsyncMock()

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        result = await granter.ensure_mail_permission()

        # Assert
        assert result is True, "Should return True when already granted"
        mock_sp_by_id.app_role_assigned_to.post.assert_not_called()


class TestPermissionGranterErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.anyio
    async def test_ensure_mail_permission_service_principal_not_found(self):
        """Test handling when service principal doesn't exist.

        Critical path: Graceful failure when app not registered.
        Verifies:
        - Service principal lookup returns None
        - Returns False
        - No grant operation attempted
        """
        # Arrange
        mock_graph = Mock()
        app_id = "nonexistent-app-id"

        # Mock service principal lookup - not found
        result = Mock()
        result.value = []
        mock_graph.service_principals.get = AsyncMock(return_value=result)

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        result = await granter.ensure_mail_permission()

        # Assert
        assert result is False, "Should return False when SP not found"

    @pytest.mark.anyio
    async def test_ensure_mail_permission_duplicate_grant(self):
        """Test handling duplicate grant race condition.

        Critical path: Idempotent when concurrent grants happen.
        Verifies:
        - Initial permission check shows not granted
        - Grant operation raises "already exists" error
        - Returns True (treats as success)
        """
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        sp_object_id = str(uuid4())
        graph_sp_id = str(uuid4())

        # Mock our service principal
        our_sp = Mock()
        our_sp.id = sp_object_id

        # Mock Graph service principal
        graph_sp = Mock()
        graph_sp.id = graph_sp_id

        # Mock service principal lookups
        async def mock_get_sp(request_configuration=None):
            filter_param = request_configuration.query_parameters.filter
            if app_id in filter_param:
                result = Mock()
                result.value = [our_sp]
                return result
            elif PermissionGranter.GRAPH_RESOURCE_APP_ID in filter_param:
                result = Mock()
                result.value = [graph_sp]
                return result
            result = Mock()
            result.value = []
            return result

        mock_graph.service_principals.get = AsyncMock(side_effect=mock_get_sp)

        # Mock permission check - not granted (race condition)
        mock_sp_by_id = Mock()
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        assignments = Mock()
        assignments.value = []
        mock_sp_by_id.app_role_assignments.get = AsyncMock(return_value=assignments)

        # Mock grant operation - raises "already exists"
        error = Exception("Permission already exists for this principal")
        mock_sp_by_id.app_role_assigned_to.post = AsyncMock(side_effect=error)

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        result = await granter.ensure_mail_permission()

        # Assert
        assert result is True, "Should return True on duplicate grant"

    @pytest.mark.anyio
    async def test_ensure_mail_permission_graph_api_error(self):
        """Test handling Graph API errors.

        Critical path: Graceful degradation on API failures.
        Verifies:
        - Graph API raises unexpected error
        - Returns False
        - Error logged appropriately
        """
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"

        # Mock Graph API failure
        error = Exception("Graph API rate limit exceeded")
        mock_graph.service_principals.get = AsyncMock(side_effect=error)

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        result = await granter.ensure_mail_permission()

        # Assert
        assert result is False, "Should return False on API error"


class TestPermissionGranterPhaseIntegration:
    """Test integration with deployment phases."""

    @pytest.mark.anyio
    async def test_phase_setup_grants_permission(self):
        """Test that phase setup calls permission granter.

        Critical path: Deployment phase 1 must grant permissions.
        Verifies:
        - PermissionGranter instantiated with correct params
        - ensure_mail_permission() called
        - Phase continues on success
        """
        # This is a placeholder for future phase integration tests
        # Will be implemented once PermissionGranter is integrated
        # into KnowledgeWorkerOrchestrator's phase 1 setup
        pytest.skip("Phase integration pending - test will be implemented with phase 1 changes")

    @pytest.mark.anyio
    async def test_phase_setup_continues_on_permission_failure(self):
        """Test that deployment continues if permission grant fails.

        Critical path: Permission grant is best-effort, not blocking.
        Verifies:
        - ensure_mail_permission() returns False
        - Deployment logs warning
        - Deployment continues to user provisioning
        """
        # This is a placeholder for future phase integration tests
        # Will be implemented once PermissionGranter is integrated
        # into KnowledgeWorkerOrchestrator's phase 1 setup
        pytest.skip("Phase integration pending - test will be implemented with phase 1 changes")


class TestPermissionGranterHelperMethods:
    """Test internal helper methods."""

    @pytest.mark.anyio
    async def test_get_service_principal_success(self):
        """Test successful service principal lookup."""
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        sp_id = str(uuid4())

        sp = Mock()
        sp.id = sp_id
        sp.app_id = app_id

        result = Mock()
        result.value = [sp]
        mock_graph.service_principals.get = AsyncMock(return_value=result)

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        sp_result = await granter._get_service_principal(app_id)

        # Assert
        assert sp_result is not None
        assert sp_result.id == sp_id
        assert sp_result.app_id == app_id

    @pytest.mark.anyio
    async def test_get_service_principal_not_found(self):
        """Test service principal lookup when not found."""
        # Arrange
        mock_graph = Mock()
        app_id = "nonexistent-app-id"

        result = Mock()
        result.value = []
        mock_graph.service_principals.get = AsyncMock(return_value=result)

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        sp_result = await granter._get_service_principal(app_id)

        # Assert
        assert sp_result is None

    @pytest.mark.anyio
    async def test_has_permission_true(self):
        """Test permission check when permission exists."""
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        sp_object_id = str(uuid4())

        assignment = Mock()
        assignment.app_role_id = PermissionGranter.MAIL_READWRITE_ROLE_ID

        assignments = Mock()
        assignments.value = [assignment]

        mock_sp_by_id = Mock()
        mock_sp_by_id.app_role_assignments.get = AsyncMock(return_value=assignments)
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        has_perm = await granter._has_permission(
            sp_object_id, PermissionGranter.MAIL_READWRITE_ROLE_ID
        )

        # Assert
        assert has_perm is True

    @pytest.mark.anyio
    async def test_has_permission_false(self):
        """Test permission check when permission doesn't exist."""
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        sp_object_id = str(uuid4())

        other_assignment = Mock()
        other_assignment.app_role_id = "some-other-permission-id"

        assignments = Mock()
        assignments.value = [other_assignment]

        mock_sp_by_id = Mock()
        mock_sp_by_id.app_role_assignments.get = AsyncMock(return_value=assignments)
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        has_perm = await granter._has_permission(
            sp_object_id, PermissionGranter.MAIL_READWRITE_ROLE_ID
        )

        # Assert
        assert has_perm is False

    @pytest.mark.anyio
    async def test_has_permission_empty_assignments(self):
        """Test permission check when no assignments exist."""
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        sp_object_id = str(uuid4())

        assignments = Mock()
        assignments.value = []

        mock_sp_by_id = Mock()
        mock_sp_by_id.app_role_assignments.get = AsyncMock(return_value=assignments)
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        has_perm = await granter._has_permission(
            sp_object_id, PermissionGranter.MAIL_READWRITE_ROLE_ID
        )

        # Assert
        assert has_perm is False

    @pytest.mark.anyio
    async def test_grant_app_role_success(self):
        """Test successful app role grant."""
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        principal_id = str(uuid4())
        resource_id = str(uuid4())
        app_role_id = PermissionGranter.MAIL_READWRITE_ROLE_ID

        mock_sp_by_id = Mock()
        mock_sp_by_id.app_role_assigned_to.post = AsyncMock()
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        result = await granter._grant_app_role(principal_id, resource_id, app_role_id)

        # Assert
        assert result is True
        mock_sp_by_id.app_role_assigned_to.post.assert_called_once()

        # Verify assignment structure
        call_args = mock_sp_by_id.app_role_assigned_to.post.call_args
        assignment = call_args[0][0]
        # IDs are converted to UUID objects, so compare string representations
        assert str(assignment.principal_id) == principal_id
        assert str(assignment.resource_id) == resource_id
        assert str(assignment.app_role_id) == app_role_id

    @pytest.mark.anyio
    async def test_grant_app_role_already_exists(self):
        """Test grant when role already exists (race condition)."""
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        principal_id = str(uuid4())
        resource_id = str(uuid4())
        app_role_id = PermissionGranter.MAIL_READWRITE_ROLE_ID

        error = Exception("Permission assignment already exists")
        mock_sp_by_id = Mock()
        mock_sp_by_id.app_role_assigned_to.post = AsyncMock(side_effect=error)
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        result = await granter._grant_app_role(principal_id, resource_id, app_role_id)

        # Assert
        assert result is True, "Should treat 'already exists' as success"

    @pytest.mark.anyio
    async def test_grant_app_role_api_error(self):
        """Test grant when API returns unexpected error."""
        # Arrange
        mock_graph = Mock()
        app_id = "test-app-id"
        principal_id = str(uuid4())
        resource_id = str(uuid4())
        app_role_id = PermissionGranter.MAIL_READWRITE_ROLE_ID

        error = Exception("Insufficient privileges")
        mock_sp_by_id = Mock()
        mock_sp_by_id.app_role_assigned_to.post = AsyncMock(side_effect=error)
        mock_graph.service_principals.by_service_principal_id.return_value = mock_sp_by_id

        granter = PermissionGranter(mock_graph, app_id)

        # Act
        result = await granter._grant_app_role(principal_id, resource_id, app_role_id)

        # Assert
        assert result is False, "Should return False on real API error"


class TestPermissionGranterConstants:
    """Test that required constants are defined correctly."""

    def test_mail_readwrite_role_id_defined(self):
        """Test that Mail.ReadWrite role ID constant is correct."""
        assert hasattr(PermissionGranter, "MAIL_READWRITE_ROLE_ID")
        # Official Microsoft Graph Mail.ReadWrite app role ID
        assert PermissionGranter.MAIL_READWRITE_ROLE_ID == "e2a3a72e-5f79-4c64-b1b1-878b674786c9"

    def test_graph_resource_app_id_defined(self):
        """Test that Microsoft Graph resource app ID constant is correct."""
        assert hasattr(PermissionGranter, "GRAPH_RESOURCE_APP_ID")
        # Official Microsoft Graph resource app ID
        assert PermissionGranter.GRAPH_RESOURCE_APP_ID == "00000003-0000-0000-c000-000000000000"


class TestPermissionGranterInitialization:
    """Test PermissionGranter initialization."""

    def test_initialization_with_valid_params(self):
        """Test successful initialization."""
        mock_graph = Mock()
        app_id = "test-app-id"

        granter = PermissionGranter(mock_graph, app_id)

        assert granter.graph_client == mock_graph
        assert granter.app_id == app_id

    def test_initialization_stores_graph_client(self):
        """Test that graph client is stored correctly."""
        mock_graph = Mock()
        app_id = "test-app-id"

        granter = PermissionGranter(mock_graph, app_id)

        assert granter.graph_client is mock_graph

    def test_initialization_stores_app_id(self):
        """Test that app ID is stored correctly."""
        mock_graph = Mock()
        app_id = "test-app-id-12345"

        granter = PermissionGranter(mock_graph, app_id)

        assert granter.app_id == app_id
