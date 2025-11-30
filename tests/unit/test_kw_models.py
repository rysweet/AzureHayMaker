"""Unit tests for Knowledge Worker models.

This module tests the core data models for the Knowledge Worker Activity Framework:
- WorkerIdentity: Represents a simulated knowledge worker
- WorkerConfig: Configuration for worker activity patterns
- WorkerPersona: Enum for worker persona types
- EndpointType: Enum for endpoint types
- Team: Team of knowledge workers
- TeamConfig: Configuration for team creation

These tests follow TDD - the models don't exist yet, so tests will fail initially.
"""

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

# Import paths based on ARCHITECTURE.md specification
# src/azure_haymaker/knowledge_worker/models/worker.py
# src/azure_haymaker/knowledge_worker/models/team.py

# Note: These imports will fail until the modules are implemented
try:
    from azure_haymaker.knowledge_worker.models.team import (
        Team,
        TeamConfig,
    )
    from azure_haymaker.knowledge_worker.models.worker import (
        EndpointType,
        WorkerConfig,
        WorkerIdentity,
        WorkerPersona,
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    # Create placeholder classes for test collection
    WorkerIdentity = None
    WorkerConfig = None
    WorkerPersona = None
    EndpointType = None
    Team = None
    TeamConfig = None


pytestmark = pytest.mark.skipif(
    not MODELS_AVAILABLE,
    reason="Knowledge Worker models not yet implemented"
)


class TestWorkerPersona:
    """Tests for WorkerPersona enum."""

    def test_persona_values_exist(self) -> None:
        """Test that all expected persona types are defined."""
        expected_personas = [
            "executive",
            "legal",
            "engineering",
            "hr",
            "finance",
            "sales",
            "operations",
            "marketing",
        ]
        for persona in expected_personas:
            assert hasattr(WorkerPersona, persona.upper()), f"Missing persona: {persona}"

    def test_persona_is_string_enum(self) -> None:
        """Test that persona values are strings."""
        assert WorkerPersona.EXECUTIVE.value == "executive"
        assert WorkerPersona.ENGINEERING.value == "engineering"
        assert WorkerPersona.LEGAL.value == "legal"

    @pytest.mark.parametrize(("persona", "expected_value"), [
        ("EXECUTIVE", "executive"),
        ("LEGAL", "legal"),
        ("ENGINEERING", "engineering"),
        ("HR", "hr"),
        ("FINANCE", "finance"),
        ("SALES", "sales"),
        ("OPERATIONS", "operations"),
        ("MARKETING", "marketing"),
    ])
    def test_persona_string_values(self, persona: str, expected_value: str) -> None:
        """Test each persona has correct string value."""
        persona_enum = getattr(WorkerPersona, persona)
        assert persona_enum.value == expected_value


class TestEndpointType:
    """Tests for EndpointType enum."""

    def test_endpoint_type_values(self) -> None:
        """Test that endpoint types have expected values."""
        assert EndpointType.CLOUD_PC.value == "cloud_pc"
        assert EndpointType.CLI_CONTAINER.value == "cli_container"
        assert EndpointType.WINDOWS_VM.value == "windows_vm"

    def test_endpoint_type_count(self) -> None:
        """Test that three endpoint types exist."""
        assert len(EndpointType) == 3


class TestWorkerIdentity:
    """Tests for WorkerIdentity model."""

    def test_create_worker_identity_minimal(self) -> None:
        """Test creating a worker identity with required fields only."""
        identity = WorkerIdentity(
            worker_id="kw-test-eng-001",
            display_name="Test Engineer",
            user_principal_name="kw-test-eng-001@tenant.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )
        assert identity.worker_id == "kw-test-eng-001"
        assert identity.display_name == "Test Engineer"
        assert identity.user_principal_name == "kw-test-eng-001@tenant.onmicrosoft.com"
        assert identity.department == "engineering"
        assert identity.persona == WorkerPersona.ENGINEERING

    def test_create_worker_identity_full(self) -> None:
        """Test creating a worker identity with all fields."""
        now = datetime.now(UTC)
        identity = WorkerIdentity(
            worker_id="kw-abc12345-exec-001",
            display_name="Executive One",
            user_principal_name="kw-abc12345-exec-001@haymaker.onmicrosoft.com",
            department="executive",
            persona=WorkerPersona.EXECUTIVE,
            entra_object_id="entra-obj-12345",
            endpoint_type=EndpointType.CLOUD_PC,
            endpoint_id="cloudpc-abc123",
            team_ids=["team-1", "team-2"],
            security_group_ids=["sg-1", "sg-2"],
            created_at=now,
            last_activity_at=now,
        )
        assert identity.entra_object_id == "entra-obj-12345"
        assert identity.endpoint_type == EndpointType.CLOUD_PC
        assert identity.endpoint_id == "cloudpc-abc123"
        assert identity.team_ids == ["team-1", "team-2"]
        assert identity.security_group_ids == ["sg-1", "sg-2"]
        assert identity.created_at == now
        assert identity.last_activity_at == now

    def test_worker_identity_default_values(self) -> None:
        """Test that optional fields have correct defaults."""
        identity = WorkerIdentity(
            worker_id="kw-test-001",
            display_name="Test Worker",
            user_principal_name="test@tenant.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )
        assert identity.entra_object_id == ""
        assert identity.endpoint_type == EndpointType.CLI_CONTAINER
        assert identity.endpoint_id == ""
        assert identity.team_ids == []
        assert identity.security_group_ids == []
        assert identity.created_at is None
        assert identity.last_activity_at is None

    def test_worker_identity_missing_required_field(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkerIdentity(
                worker_id="kw-test-001",
                display_name="Test Worker",
                # Missing: user_principal_name, department, persona
            )
        errors = exc_info.value.errors()
        error_fields = {err["loc"][0] for err in errors}
        assert "user_principal_name" in error_fields
        assert "department" in error_fields
        assert "persona" in error_fields

    def test_worker_identity_serialization(self) -> None:
        """Test JSON serialization of worker identity."""
        identity = WorkerIdentity(
            worker_id="kw-test-eng-001",
            display_name="Test Engineer",
            user_principal_name="kw-test-eng-001@tenant.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )
        json_str = identity.model_dump_json()
        data = json.loads(json_str)

        assert data["worker_id"] == "kw-test-eng-001"
        assert data["persona"] == "engineering"
        assert data["endpoint_type"] == "cli_container"

    def test_worker_identity_deserialization(self) -> None:
        """Test JSON deserialization of worker identity."""
        json_data = {
            "worker_id": "kw-test-001",
            "display_name": "Test Worker",
            "user_principal_name": "test@tenant.onmicrosoft.com",
            "department": "sales",
            "persona": "sales",
            "endpoint_type": "cloud_pc",
        }
        identity = WorkerIdentity.model_validate(json_data)

        assert identity.worker_id == "kw-test-001"
        assert identity.persona == WorkerPersona.SALES
        assert identity.endpoint_type == EndpointType.CLOUD_PC

    @pytest.mark.parametrize(("persona", "department"), [
        (WorkerPersona.EXECUTIVE, "executive"),
        (WorkerPersona.ENGINEERING, "engineering"),
        (WorkerPersona.LEGAL, "legal"),
        (WorkerPersona.HR, "hr"),
        (WorkerPersona.FINANCE, "finance"),
        (WorkerPersona.SALES, "sales"),
        (WorkerPersona.OPERATIONS, "operations"),
        (WorkerPersona.MARKETING, "marketing"),
    ])
    def test_persona_department_combinations(
        self, persona: WorkerPersona, department: str
    ) -> None:
        """Test valid persona and department combinations."""
        identity = WorkerIdentity(
            worker_id=f"kw-test-{department[:4]}-001",
            display_name=f"Test {department.title()} Worker",
            user_principal_name=f"kw-test-{department[:4]}-001@tenant.onmicrosoft.com",
            department=department,
            persona=persona,
        )
        assert identity.persona == persona
        assert identity.department == department


class TestWorkerConfig:
    """Tests for WorkerConfig model."""

    def test_create_worker_config_defaults(self) -> None:
        """Test creating worker config with default values."""
        config = WorkerConfig()

        assert config.email_per_hour == 5
        assert config.teams_messages_per_hour == 10
        assert config.documents_per_day == 3
        assert config.meetings_per_day == 4
        assert config.activity_variance_percent == 30
        assert config.work_start_hour == 8
        assert config.work_end_hour == 17
        assert config.preferred_communication == "teams"

    def test_create_worker_config_custom(self) -> None:
        """Test creating worker config with custom values."""
        config = WorkerConfig(
            email_per_hour=12,
            teams_messages_per_hour=20,
            documents_per_day=5,
            meetings_per_day=8,
            activity_variance_percent=20,
            work_start_hour=9,
            work_end_hour=18,
            preferred_communication="email",
        )

        assert config.email_per_hour == 12
        assert config.teams_messages_per_hour == 20
        assert config.documents_per_day == 5
        assert config.meetings_per_day == 8
        assert config.activity_variance_percent == 20
        assert config.work_start_hour == 9
        assert config.work_end_hour == 18
        assert config.preferred_communication == "email"

    @pytest.mark.parametrize(("field", "min_val", "max_val"), [
        ("email_per_hour", 0, 50),
        ("teams_messages_per_hour", 0, 100),
        ("documents_per_day", 0, 20),
        ("meetings_per_day", 0, 15),
        ("activity_variance_percent", 0, 100),
        ("work_start_hour", 0, 23),
        ("work_end_hour", 0, 23),
    ])
    def test_worker_config_field_bounds(
        self, field: str, min_val: int, max_val: int
    ) -> None:
        """Test field validation bounds."""
        # Test minimum value is valid
        config_min = WorkerConfig(**{field: min_val})
        assert getattr(config_min, field) == min_val

        # Test maximum value is valid
        config_max = WorkerConfig(**{field: max_val})
        assert getattr(config_max, field) == max_val

    @pytest.mark.parametrize(("field", "invalid_value"), [
        ("email_per_hour", -1),
        ("email_per_hour", 51),
        ("teams_messages_per_hour", -1),
        ("teams_messages_per_hour", 101),
        ("documents_per_day", -1),
        ("documents_per_day", 21),
        ("meetings_per_day", -1),
        ("meetings_per_day", 16),
        ("activity_variance_percent", -1),
        ("activity_variance_percent", 101),
        ("work_start_hour", -1),
        ("work_start_hour", 24),
        ("work_end_hour", -1),
        ("work_end_hour", 24),
    ])
    def test_worker_config_invalid_bounds(
        self, field: str, invalid_value: int
    ) -> None:
        """Test that out-of-bounds values raise ValidationError."""
        with pytest.raises(ValidationError):
            WorkerConfig(**{field: invalid_value})

    def test_worker_config_serialization(self) -> None:
        """Test JSON serialization of worker config."""
        config = WorkerConfig(
            email_per_hour=10,
            teams_messages_per_hour=15,
        )
        json_str = config.model_dump_json()
        data = json.loads(json_str)

        assert data["email_per_hour"] == 10
        assert data["teams_messages_per_hour"] == 15


class TestTeam:
    """Tests for Team model."""

    def test_create_team_minimal(self) -> None:
        """Test creating a team with required fields only."""
        team = Team(
            team_id="team-abc123",
            team_name="Engineering Team Alpha",
            department="engineering",
        )
        assert team.team_id == "team-abc123"
        assert team.team_name == "Engineering Team Alpha"
        assert team.department == "engineering"

    def test_create_team_full(self) -> None:
        """Test creating a team with all fields."""
        now = datetime.now(UTC)
        team = Team(
            team_id="team-exec-001",
            team_name="Executive Leadership",
            department="executive",
            security_group_id="sg-exec-001",
            m365_group_id="m365-exec-001",
            teams_team_id="teams-exec-001",
            member_ids=["worker-001", "worker-002", "worker-003"],
            manager_ids=["worker-001"],
            allowed_peer_team_ids=["team-eng-001", "team-sales-001"],
            sharepoint_site_id="sp-exec-001",
            shared_mailbox="exec-team@tenant.onmicrosoft.com",
            created_at=now,
            run_id="run-abc12345",
        )

        assert team.security_group_id == "sg-exec-001"
        assert team.m365_group_id == "m365-exec-001"
        assert team.teams_team_id == "teams-exec-001"
        assert len(team.member_ids) == 3
        assert len(team.manager_ids) == 1
        assert len(team.allowed_peer_team_ids) == 2
        assert team.sharepoint_site_id == "sp-exec-001"
        assert team.shared_mailbox == "exec-team@tenant.onmicrosoft.com"
        assert team.created_at == now
        assert team.run_id == "run-abc12345"

    def test_team_default_values(self) -> None:
        """Test that optional fields have correct defaults."""
        team = Team(
            team_id="team-001",
            team_name="Test Team",
            department="engineering",
        )

        assert team.security_group_id == ""
        assert team.m365_group_id == ""
        assert team.teams_team_id == ""
        assert team.member_ids == []
        assert team.manager_ids == []
        assert team.allowed_peer_team_ids == []
        assert team.sharepoint_site_id == ""
        assert team.shared_mailbox == ""
        assert team.created_at is None
        assert team.run_id == ""

    def test_team_missing_required_field(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Team(
                team_id="team-001",
                # Missing: team_name, department
            )
        errors = exc_info.value.errors()
        error_fields = {err["loc"][0] for err in errors}
        assert "team_name" in error_fields
        assert "department" in error_fields

    def test_team_serialization(self) -> None:
        """Test JSON serialization of team."""
        team = Team(
            team_id="team-eng-001",
            team_name="Engineering Team",
            department="engineering",
            member_ids=["worker-001", "worker-002"],
        )
        json_str = team.model_dump_json()
        data = json.loads(json_str)

        assert data["team_id"] == "team-eng-001"
        assert data["team_name"] == "Engineering Team"
        assert data["member_ids"] == ["worker-001", "worker-002"]

    def test_team_deserialization(self) -> None:
        """Test JSON deserialization of team."""
        json_data = {
            "team_id": "team-sales-001",
            "team_name": "Sales Team",
            "department": "sales",
            "allowed_peer_team_ids": ["team-marketing-001"],
        }
        team = Team.model_validate(json_data)

        assert team.team_id == "team-sales-001"
        assert team.department == "sales"
        assert team.allowed_peer_team_ids == ["team-marketing-001"]


class TestTeamConfig:
    """Tests for TeamConfig model."""

    def test_create_team_config_defaults(self) -> None:
        """Test creating team config with default values."""
        config = TeamConfig()

        assert config.min_members == 3
        assert config.max_members == 15
        assert config.manager_ratio == 0.1
        assert config.cross_team_communication_enabled is True
        assert config.max_peer_teams == 3

    def test_create_team_config_custom(self) -> None:
        """Test creating team config with custom values."""
        config = TeamConfig(
            min_members=5,
            max_members=20,
            manager_ratio=0.2,
            cross_team_communication_enabled=False,
            max_peer_teams=5,
        )

        assert config.min_members == 5
        assert config.max_members == 20
        assert config.manager_ratio == 0.2
        assert config.cross_team_communication_enabled is False
        assert config.max_peer_teams == 5

    @pytest.mark.parametrize(("field", "min_val", "max_val"), [
        ("min_members", 1, None),
        ("max_members", None, 50),
        ("manager_ratio", 0.0, 0.5),
        ("max_peer_teams", 0, 10),
    ])
    def test_team_config_field_bounds(
        self, field: str, min_val: float | None, max_val: float | None
    ) -> None:
        """Test field validation bounds."""
        if min_val is not None:
            config_min = TeamConfig(**{field: min_val})
            assert getattr(config_min, field) == min_val

        if max_val is not None:
            config_max = TeamConfig(**{field: max_val})
            assert getattr(config_max, field) == max_val

    @pytest.mark.parametrize(("field", "invalid_value"), [
        ("min_members", 0),
        ("max_members", 51),
        ("manager_ratio", -0.1),
        ("manager_ratio", 0.6),
        ("max_peer_teams", -1),
        ("max_peer_teams", 11),
    ])
    def test_team_config_invalid_bounds(
        self, field: str, invalid_value: float
    ) -> None:
        """Test that out-of-bounds values raise ValidationError."""
        with pytest.raises(ValidationError):
            TeamConfig(**{field: invalid_value})

    def test_team_config_serialization(self) -> None:
        """Test JSON serialization of team config."""
        config = TeamConfig(
            min_members=5,
            max_members=25,
            cross_team_communication_enabled=True,
        )
        json_str = config.model_dump_json()
        data = json.loads(json_str)

        assert data["min_members"] == 5
        assert data["max_members"] == 25
        assert data["cross_team_communication_enabled"] is True


class TestNamingConventions:
    """Tests for Knowledge Worker naming conventions from ARCHITECTURE.md."""

    @pytest.mark.parametrize(("run_id", "dept", "index", "expected"), [
        ("abc12345-full-uuid", "engineering", 1, "kw-abc12345-engi-001"),
        ("xyz99999-full-uuid", "executive", 5, "kw-xyz99999-exec-005"),
        ("test1234-full-uuid", "legal", 10, "kw-test1234-lega-010"),
        ("run00001-full-uuid", "hr", 99, "kw-run00001-hr-099"),
    ])
    def test_worker_id_pattern(
        self, run_id: str, dept: str, index: int, expected: str
    ) -> None:
        """Test worker ID follows naming pattern: kw-{run_id[:8]}-{dept[:4]}-{index:03d}."""
        # Pattern from ARCHITECTURE.md: kw-{run_id[:8]}-{dept[:4]}-{index:03d}
        generated_id = f"kw-{run_id[:8]}-{dept[:4]}-{index:03d}"
        assert generated_id == expected

    @pytest.mark.parametrize(("worker_id", "expected_valid"), [
        ("kw-abc12345-engi-001", True),
        ("kw-abc12345-exec-999", True),
        ("invalid-worker-id", False),
        ("kw-short-e-1", False),  # Too short components
        ("", False),
    ])
    def test_worker_id_validation(self, worker_id: str, expected_valid: bool) -> None:
        """Test worker ID validation pattern."""
        import re
        pattern = r"^kw-[a-z0-9]{8}-[a-z]{2,4}-\d{3}$"
        is_valid = bool(re.match(pattern, worker_id))
        assert is_valid == expected_valid
