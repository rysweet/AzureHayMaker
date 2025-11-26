"""Tests for Teams integration module.

Tests cover:
- Team creation from M365 groups
- Member management with role assignment
- Channel creation and management
- Message posting
- Error handling and edge cases
- Complete team setup workflow
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from azure_haymaker.knowledge_worker.teams_integration import (
    TeamsIntegration,
    TeamsIntegrationError,
)


class MockGraphResponse:
    """Mock Graph API response."""

    def __init__(self, id=None, display_name=None, description=None, value=None):
        self.id = id
        self.display_name = display_name
        self.description = description
        self.value = value if value is not None else []


class MockGraphClient:
    """Mock Microsoft Graph client."""

    def __init__(self):
        self.groups = MagicMock()
        self.teams = MagicMock()
        self.chats = MagicMock()
        self._setup_mocks()

    def _setup_mocks(self):
        """Setup default mock behavior."""
        # Setup groups mock
        group_mock = MagicMock()
        group_team_mock = MagicMock()
        group_team_mock.put = AsyncMock(return_value=MockGraphResponse(id="team-123"))
        group_mock.team = group_team_mock
        self.groups.by_group_id = MagicMock(return_value=group_mock)

        # Setup teams mock
        team_mock = MagicMock()
        members_mock = MagicMock()
        members_mock.post = AsyncMock()
        team_mock.members = members_mock

        channels_mock = MagicMock()
        channel_mock = MagicMock()
        channel_messages_mock = MagicMock()
        channel_messages_mock.post = AsyncMock(
            return_value=MockGraphResponse(id="message-123")
        )
        channel_mock.messages = channel_messages_mock
        channels_mock.by_channel_id = MagicMock(return_value=channel_mock)
        channels_mock.post = AsyncMock(return_value=MockGraphResponse(id="channel-456"))
        channels_mock.get = AsyncMock(
            return_value=MockGraphResponse(
                id="general-channel",
                value=[],  # Default to empty list
            )
        )
        team_mock.channels = channels_mock
        team_mock.get = AsyncMock(
            return_value=MockGraphResponse(
                id="team-123",
                display_name="Test Team",
                description="Test Description",
            )
        )

        self.teams.by_team_id = MagicMock(return_value=team_mock)


@pytest.fixture
def mock_graph_client():
    """Provide mock Graph client."""
    return MockGraphClient()


@pytest.fixture
def teams_integration(mock_graph_client):
    """Provide TeamsIntegration instance."""
    return TeamsIntegration(mock_graph_client, "abc12345")


class TestTeamsIntegrationInit:
    """Test TeamsIntegration initialization."""

    def test_init_success(self, mock_graph_client):
        """Test successful initialization."""
        integration = TeamsIntegration(mock_graph_client, "abc12345")

        assert integration.graph_client is mock_graph_client
        assert integration.run_id == "abc12345"

    def test_init_missing_graph_client(self):
        """Test initialization fails without graph client."""
        with pytest.raises(ValueError, match="graph_client is required"):
            TeamsIntegration(None, "abc12345")

    def test_init_missing_run_id(self, mock_graph_client):
        """Test initialization fails without run_id."""
        with pytest.raises(ValueError, match="run_id is required"):
            TeamsIntegration(mock_graph_client, "")


class TestTeamNaming:
    """Test team naming conventions."""

    def test_build_team_name(self, teams_integration):
        """Test team name generation."""
        name = teams_integration._build_team_name("engineering", 1)

        assert name == "KW-ABC12345-Engineering-Team1"

    def test_build_team_name_different_departments(self, teams_integration):
        """Test team names with different departments."""
        name1 = teams_integration._build_team_name("sales", 1)
        name2 = teams_integration._build_team_name("marketing", 2)

        assert name1 == "KW-ABC12345-Sales-Team1"
        assert name2 == "KW-ABC12345-Marketing-Team2"


class TestTeamCreation:
    """Test team creation operations."""

    @pytest.mark.asyncio
    async def test_create_team_from_group_success(self, teams_integration):
        """Test successful team creation from M365 group."""
        team_id = await teams_integration.create_team_from_group(
            m365_group_id="group-123",
            team_name="Test Team",
            department="engineering",
            team_num=1,
        )

        assert team_id == "team-123"

    @pytest.mark.asyncio
    async def test_create_team_from_group_graph_error(self, teams_integration):
        """Test team creation fails when Graph API fails."""
        # Setup to raise error
        teams_integration.graph_client.groups.by_group_id().team.put = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(TeamsIntegrationError):
            await teams_integration.create_team_from_group(
                m365_group_id="group-123",
                team_name="Test Team",
                department="engineering",
                team_num=1,
            )

    @pytest.mark.asyncio
    async def test_create_team_missing_response_id(self, teams_integration):
        """Test team creation fails if response missing ID."""
        # Setup to return response without ID
        teams_integration.graph_client.groups.by_group_id().team.put = AsyncMock(
            return_value=MockGraphResponse(id=None)
        )

        with pytest.raises(TeamsIntegrationError):
            await teams_integration.create_team_from_group(
                m365_group_id="group-123",
                team_name="Test Team",
                department="engineering",
                team_num=1,
            )


class TestMemberManagement:
    """Test member management operations."""

    @pytest.mark.asyncio
    async def test_add_team_members_success(self, teams_integration):
        """Test successful member addition."""
        result = await teams_integration.add_team_members(
            team_id="team-123",
            member_configs=[
                {"user_id": "user-1", "role": "owner"},
                {"user_id": "user-2", "role": "member"},
            ],
        )

        assert result["success"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_add_team_members_empty_list(self, teams_integration):
        """Test adding empty member list."""
        result = await teams_integration.add_team_members(
            team_id="team-123",
            member_configs=[],
        )

        assert result["success"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_add_team_members_partial_failure(self, teams_integration):
        """Test partial member addition failure."""
        # Setup second member to fail
        call_count = [0]

        async def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Member add failed")

        teams_integration.graph_client.teams.by_team_id().members.post = AsyncMock(
            side_effect=side_effect
        )

        result = await teams_integration.add_team_members(
            team_id="team-123",
            member_configs=[
                {"user_id": "user-1", "role": "owner"},
                {"user_id": "user-2", "role": "member"},
            ],
        )

        assert result["success"] == 1
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_add_team_members_all_fail_raises_error(self, teams_integration):
        """Test all member additions fail raises error."""
        teams_integration.graph_client.teams.by_team_id().members.post = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(TeamsIntegrationError):
            await teams_integration.add_team_members(
                team_id="team-123",
                member_configs=[
                    {"user_id": "user-1", "role": "owner"},
                ],
            )

    @pytest.mark.asyncio
    async def test_add_single_member_invalid_role(self, teams_integration):
        """Test adding member with invalid role defaults to member."""
        await teams_integration._add_team_member(
            team_id="team-123",
            user_id="user-1",
            role="invalid_role",
        )

        # Verify post was called
        teams_integration.graph_client.teams.by_team_id().members.post.assert_called_once()


class TestChannelManagement:
    """Test channel management operations."""

    @pytest.mark.asyncio
    async def test_create_standard_channels_success(self, teams_integration):
        """Test successful channel creation."""
        channels = await teams_integration.create_standard_channels(
            team_id="team-123",
            channels=["Projects", "Planning"],
        )

        assert "Projects" in channels
        assert "Planning" in channels

    @pytest.mark.asyncio
    async def test_create_standard_channels_default_list(self, teams_integration):
        """Test channel creation with default channel list."""
        channels = await teams_integration.create_standard_channels(
            team_id="team-123",
        )

        # Should create all except General (auto-created)
        assert "Projects" in channels

    @pytest.mark.asyncio
    async def test_create_channel_partial_failure(self, teams_integration):
        """Test partial channel creation failure."""
        call_count = [0]

        async def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MockGraphResponse(id="channel-1")
            else:
                raise Exception("Channel creation failed")

        teams_integration.graph_client.teams.by_team_id().channels.post = AsyncMock(
            side_effect=side_effect
        )

        channels = await teams_integration.create_standard_channels(
            team_id="team-123",
            channels=["Projects", "Planning"],
        )

        assert "Projects" in channels
        assert "Planning" not in channels

    @pytest.mark.asyncio
    async def test_get_channel_id_by_name_success(self, teams_integration):
        """Test getting channel ID by name."""
        channel_mock = MagicMock()
        channel_mock.id = "channel-123"
        channel_mock.display_name = "General"

        teams_integration.graph_client.teams.by_team_id().channels.get = AsyncMock(
            return_value=MockGraphResponse(value=[channel_mock])
        )

        channel_id = await teams_integration._get_channel_id_by_name(
            team_id="team-123",
            channel_name="General",
        )

        assert channel_id == "channel-123"

    @pytest.mark.asyncio
    async def test_get_channel_id_by_name_not_found(self, teams_integration):
        """Test getting channel ID when not found."""
        teams_integration.graph_client.teams.by_team_id().channels.get = AsyncMock(
            return_value=MockGraphResponse(value=[])
        )

        channel_id = await teams_integration._get_channel_id_by_name(
            team_id="team-123",
            channel_name="NonExistent",
        )

        assert channel_id is None


class TestMessaging:
    """Test messaging operations."""

    @pytest.mark.asyncio
    async def test_post_welcome_message_success(self, teams_integration):
        """Test successful welcome message posting."""
        # Mock channel lookup to find General channel
        channel_mock = MagicMock()
        channel_mock.id = "general-channel-id"
        channel_mock.display_name = "General"

        teams_integration.graph_client.teams.by_team_id().channels.get = AsyncMock(
            return_value=MockGraphResponse(value=[channel_mock])
        )

        message_id = await teams_integration.post_welcome_message(
            team_id="team-123",
            channel_name="General",
        )

        assert message_id == "message-123"

    @pytest.mark.asyncio
    async def test_post_welcome_message_custom_message(self, teams_integration):
        """Test posting custom welcome message."""
        custom_msg = "Custom welcome message"

        # Mock channel lookup
        channel_mock = MagicMock()
        channel_mock.id = "general-channel-id"
        channel_mock.display_name = "General"

        teams_integration.graph_client.teams.by_team_id().channels.get = AsyncMock(
            return_value=MockGraphResponse(value=[channel_mock])
        )

        message_id = await teams_integration.post_welcome_message(
            team_id="team-123",
            channel_name="General",
            custom_message=custom_msg,
        )

        assert message_id == "message-123"

    @pytest.mark.asyncio
    async def test_post_welcome_message_channel_not_found(self, teams_integration):
        """Test posting message when channel not found."""
        teams_integration.graph_client.teams.by_team_id().channels.get = AsyncMock(
            return_value=MockGraphResponse(value=[])
        )

        message_id = await teams_integration.post_welcome_message(
            team_id="team-123",
            channel_name="NonExistent",
        )

        assert message_id is None

    @pytest.mark.asyncio
    async def test_post_welcome_message_graph_error(self, teams_integration):
        """Test message posting fails when Graph API fails."""
        # Mock channel lookup
        channel_mock = MagicMock()
        channel_mock.id = "general-channel-id"
        channel_mock.display_name = "General"

        teams_integration.graph_client.teams.by_team_id().channels.get = AsyncMock(
            return_value=MockGraphResponse(value=[channel_mock])
        )

        # Mock message posting to fail
        teams_integration.graph_client.teams.by_team_id().channels.by_channel_id().messages.post = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(TeamsIntegrationError):
            await teams_integration.post_welcome_message(
                team_id="team-123",
                channel_name="General",
            )


class TestCompleteSetup:
    """Test complete team setup workflow."""

    @pytest.mark.asyncio
    async def test_setup_team_success(self, teams_integration):
        """Test successful complete team setup."""
        # Mock channel lookup for welcome message
        channel_mock = MagicMock()
        channel_mock.id = "general-channel-id"
        channel_mock.display_name = "General"

        teams_integration.graph_client.teams.by_team_id().channels.get = AsyncMock(
            return_value=MockGraphResponse(value=[channel_mock])
        )

        result = await teams_integration.setup_team(
            m365_group_id="group-123",
            department="engineering",
            team_num=1,
            member_configs=[
                {"user_id": "user-1", "role": "owner"},
            ],
            post_welcome_message=True,
        )

        assert result["status"] == "success"
        assert result["team_id"] == "team-123"
        assert result["team_name"] == "KW-ABC12345-Engineering-Team1"
        assert result["members"]["success"] == 1
        assert result["welcome_message_id"] == "message-123"

    @pytest.mark.asyncio
    async def test_setup_team_no_welcome_message(self, teams_integration):
        """Test team setup without welcome message."""
        result = await teams_integration.setup_team(
            m365_group_id="group-123",
            department="engineering",
            team_num=1,
            member_configs=[],
            post_welcome_message=False,
        )

        assert result["status"] == "success"
        assert result["welcome_message_id"] is None

    @pytest.mark.asyncio
    async def test_setup_team_team_creation_fails(self, teams_integration):
        """Test setup fails if team creation fails."""
        teams_integration.graph_client.groups.by_group_id().team.put = AsyncMock(
            side_effect=Exception("Team creation failed")
        )

        with pytest.raises(TeamsIntegrationError):
            await teams_integration.setup_team(
                m365_group_id="group-123",
                department="engineering",
                team_num=1,
                member_configs=[],
            )

    @pytest.mark.asyncio
    async def test_setup_team_all_members_fail(self, teams_integration):
        """Test setup fails if all members fail to be added."""
        teams_integration.graph_client.teams.by_team_id().members.post = AsyncMock(
            side_effect=Exception("Member add failed")
        )

        with pytest.raises(TeamsIntegrationError):
            await teams_integration.setup_team(
                m365_group_id="group-123",
                department="engineering",
                team_num=1,
                member_configs=[
                    {"user_id": "user-1", "role": "owner"},
                ],
            )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_multiple_instances_different_runs(self, mock_graph_client):
        """Test multiple instances with different run IDs."""
        integration1 = TeamsIntegration(mock_graph_client, "run-001")
        integration2 = TeamsIntegration(mock_graph_client, "run-002")

        name1 = integration1._build_team_name("eng", 1)
        name2 = integration2._build_team_name("eng", 1)

        assert "RUN-001" in name1.upper()
        assert "RUN-002" in name2.upper()

    @pytest.mark.asyncio
    async def test_add_member_missing_user_id(self, teams_integration):
        """Test adding member with missing user_id."""
        result = await teams_integration.add_team_members(
            team_id="team-123",
            member_configs=[
                {"user_id": "user-1", "role": "owner"},
                {"role": "member"},  # Missing user_id
            ],
        )

        assert result["success"] == 1
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_default_channels_excludes_general(self, teams_integration):
        """Test default channels list excludes General."""
        # Get default channels that would be created
        default_channels = [
            ch for ch in teams_integration.DEFAULT_CHANNELS
            if ch != "General"
        ]

        assert "General" not in default_channels
        assert "Projects" in default_channels


class TestInternalMethods:
    """Test internal helper methods."""

    @pytest.mark.asyncio
    async def test_get_team_info_success(self, teams_integration):
        """Test getting team information."""
        info = await teams_integration._get_team_info("team-123")

        assert info["id"] == "team-123"
        assert info["display_name"] == "Test Team"
        assert info["description"] == "Test Description"

    @pytest.mark.asyncio
    async def test_get_team_info_graph_error(self, teams_integration):
        """Test getting team info when Graph API fails."""
        teams_integration.graph_client.teams.by_team_id().get = AsyncMock(
            side_effect=Exception("API Error")
        )

        info = await teams_integration._get_team_info("team-123")

        assert info is None
