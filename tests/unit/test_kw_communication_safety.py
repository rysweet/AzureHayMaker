"""Unit tests for Knowledge Worker communication safety controls.

This module tests the communication safety layer that ensures all M365 operations
stay internal-only (no external email or messaging). This is a CRITICAL security
component - the tests here verify defense-in-depth at the application layer.

Components tested:
- CommunicationValidator: Validates recipients are internal-only
- ExternalRecipientError: Custom exception for blocked external recipients
- filter_recipients: Filters recipient lists to internal-only
- validate_or_raise: Validates or raises exception

Reference: ARCHITECTURE.md Section 7 - Communication Safety Controls
"""

import pytest

# Import paths based on ARCHITECTURE.md specification
# The CommunicationValidator should be in:
# src/azure_haymaker/knowledge_worker/safety/communication.py
# or similar location

try:
    from azure_haymaker.knowledge_worker.safety.communication import (
        CommunicationValidator,
        ExternalRecipientError,
    )

    SAFETY_AVAILABLE = True
except ImportError:
    SAFETY_AVAILABLE = False
    # Create placeholder for test collection
    CommunicationValidator = None
    ExternalRecipientError = None


pytestmark = pytest.mark.skipif(
    not SAFETY_AVAILABLE, reason="Knowledge Worker safety module not yet implemented"
)


class TestExternalRecipientError:
    """Tests for ExternalRecipientError exception."""

    def test_exception_is_exception_subclass(self) -> None:
        """Test that ExternalRecipientError is a proper exception."""
        assert issubclass(ExternalRecipientError, Exception)

    def test_exception_with_message(self) -> None:
        """Test exception includes blocked recipients in message."""
        error = ExternalRecipientError("External recipients blocked: ['external@gmail.com']")
        assert "external@gmail.com" in str(error)

    def test_exception_can_be_raised(self) -> None:
        """Test exception can be raised and caught."""
        with pytest.raises(ExternalRecipientError) as exc_info:
            raise ExternalRecipientError("Test external recipient blocked")
        assert "external recipient" in str(exc_info.value).lower()


class TestCommunicationValidatorInit:
    """Tests for CommunicationValidator initialization."""

    def test_init_with_domain_and_upns(self) -> None:
        """Test initializing validator with tenant domain and allowed UPNs."""
        validator = CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={"user1@haymaker.onmicrosoft.com", "user2@haymaker.onmicrosoft.com"},
        )
        assert validator.tenant_domain == "haymaker.onmicrosoft.com"
        assert len(validator.allowed_upns) == 2

    def test_init_normalizes_domain_to_lowercase(self) -> None:
        """Test that tenant domain is normalized to lowercase."""
        validator = CommunicationValidator(
            tenant_domain="HAYMAKER.OnMicrosoft.COM",
            allowed_upns=set(),
        )
        assert validator.tenant_domain == "haymaker.onmicrosoft.com"

    def test_init_normalizes_upns_to_lowercase(self) -> None:
        """Test that allowed UPNs are normalized to lowercase."""
        validator = CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={"User1@Haymaker.OnMicrosoft.COM", "USER2@HAYMAKER.ONMICROSOFT.COM"},
        )
        assert "user1@haymaker.onmicrosoft.com" in validator.allowed_upns
        assert "user2@haymaker.onmicrosoft.com" in validator.allowed_upns

    def test_init_with_empty_upns(self) -> None:
        """Test initializing with empty allowed UPNs set."""
        validator = CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns=set(),
        )
        assert len(validator.allowed_upns) == 0


class TestCommunicationValidatorIsInternal:
    """Tests for CommunicationValidator.is_internal() method.

    This is the core validation method - it MUST correctly identify
    internal vs external recipients to prevent data leakage.
    """

    @pytest.fixture
    def validator(self) -> CommunicationValidator:
        """Create a validator with standard test configuration."""
        return CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={
                "kw-abc12345-engi-001@haymaker.onmicrosoft.com",
                "kw-abc12345-engi-002@haymaker.onmicrosoft.com",
                "kw-abc12345-exec-001@haymaker.onmicrosoft.com",
                "team-engineering@haymaker.onmicrosoft.com",
            },
        )

    # --- Tests for VALID internal recipients ---

    def test_is_internal_with_allowed_upn(self, validator: CommunicationValidator) -> None:
        """Test that explicitly allowed UPN is considered internal."""
        assert validator.is_internal("kw-abc12345-engi-001@haymaker.onmicrosoft.com") is True

    def test_is_internal_with_allowed_upn_case_insensitive(
        self, validator: CommunicationValidator
    ) -> None:
        """Test that UPN matching is case-insensitive."""
        assert validator.is_internal("KW-ABC12345-ENGI-001@HAYMAKER.ONMICROSOFT.COM") is True
        assert validator.is_internal("Kw-Abc12345-Engi-001@Haymaker.OnMicrosoft.Com") is True

    def test_is_internal_with_tenant_domain(self, validator: CommunicationValidator) -> None:
        """Test that any address in tenant domain is considered internal."""
        # Even if not in allowed_upns, same domain = internal
        assert validator.is_internal("anyuser@haymaker.onmicrosoft.com") is True

    def test_is_internal_with_whitespace_stripped(self, validator: CommunicationValidator) -> None:
        """Test that leading/trailing whitespace is stripped."""
        assert validator.is_internal("  kw-abc12345-engi-001@haymaker.onmicrosoft.com  ") is True
        assert validator.is_internal("\tkw-abc12345-engi-001@haymaker.onmicrosoft.com\n") is True

    def test_is_internal_with_team_mailbox(self, validator: CommunicationValidator) -> None:
        """Test that team/shared mailboxes in allowed list are internal."""
        assert validator.is_internal("team-engineering@haymaker.onmicrosoft.com") is True

    # --- Tests for INVALID external recipients ---

    @pytest.mark.parametrize(
        "external_recipient",
        [
            "attacker@gmail.com",
            "external@outlook.com",
            "hacker@evil.com",
            "user@competitor.com",
            "someone@yahoo.com",
            "test@hotmail.com",
        ],
    )
    def test_is_internal_rejects_external_domains(
        self, validator: CommunicationValidator, external_recipient: str
    ) -> None:
        """Test that common external domains are rejected."""
        assert validator.is_internal(external_recipient) is False

    @pytest.mark.parametrize(
        "typosquat_domain",
        [
            "user@haymakerr.onmicrosoft.com",  # Extra 'r'
            "user@haymaker.onmicrosoft.net",  # Wrong TLD
            "user@haymaker.microsoft.com",  # Missing 'on'
            "user@hay-maker.onmicrosoft.com",  # Extra hyphen
            "user@haymakeronmicrosoft.com",  # Missing dot
        ],
    )
    def test_is_internal_rejects_typosquat_domains(
        self, validator: CommunicationValidator, typosquat_domain: str
    ) -> None:
        """Test that typosquatting domain attempts are rejected."""
        assert validator.is_internal(typosquat_domain) is False

    def test_is_internal_rejects_subdomain_attacks(self, validator: CommunicationValidator) -> None:
        """Test that subdomain attacks are rejected."""
        # Attacker might try: haymaker.onmicrosoft.com.evil.com
        assert validator.is_internal("user@haymaker.onmicrosoft.com.evil.com") is False
        assert validator.is_internal("user@sub.haymaker.onmicrosoft.com") is False

    def test_is_internal_rejects_empty_string(self, validator: CommunicationValidator) -> None:
        """Test that empty string is rejected."""
        assert validator.is_internal("") is False

    def test_is_internal_rejects_no_at_sign(self, validator: CommunicationValidator) -> None:
        """Test that addresses without @ are rejected."""
        assert validator.is_internal("userwithnodomain") is False
        assert validator.is_internal("just-a-string") is False

    def test_is_internal_rejects_malformed_addresses(
        self, validator: CommunicationValidator
    ) -> None:
        """Test that malformed email addresses are rejected."""
        assert validator.is_internal("@nodomain.com") is False
        assert validator.is_internal("user@") is False
        assert validator.is_internal("user@@domain.com") is False


class TestCommunicationValidatorFilterRecipients:
    """Tests for CommunicationValidator.filter_recipients() method."""

    @pytest.fixture
    def validator(self) -> CommunicationValidator:
        """Create a validator with standard test configuration."""
        return CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={
                "worker1@haymaker.onmicrosoft.com",
                "worker2@haymaker.onmicrosoft.com",
            },
        )

    def test_filter_recipients_keeps_internal(self, validator: CommunicationValidator) -> None:
        """Test that internal recipients are kept."""
        recipients = [
            "worker1@haymaker.onmicrosoft.com",
            "worker2@haymaker.onmicrosoft.com",
        ]
        filtered = validator.filter_recipients(recipients)
        assert len(filtered) == 2
        assert "worker1@haymaker.onmicrosoft.com" in filtered
        assert "worker2@haymaker.onmicrosoft.com" in filtered

    def test_filter_recipients_removes_external(self, validator: CommunicationValidator) -> None:
        """Test that external recipients are removed."""
        recipients = [
            "worker1@haymaker.onmicrosoft.com",
            "external@gmail.com",
            "worker2@haymaker.onmicrosoft.com",
            "hacker@evil.com",
        ]
        filtered = validator.filter_recipients(recipients)
        assert len(filtered) == 2
        assert "external@gmail.com" not in filtered
        assert "hacker@evil.com" not in filtered

    def test_filter_recipients_all_external(self, validator: CommunicationValidator) -> None:
        """Test filtering when ALL recipients are external."""
        recipients = [
            "external1@gmail.com",
            "external2@outlook.com",
        ]
        filtered = validator.filter_recipients(recipients)
        assert len(filtered) == 0
        assert filtered == []

    def test_filter_recipients_empty_list(self, validator: CommunicationValidator) -> None:
        """Test filtering empty recipient list."""
        filtered = validator.filter_recipients([])
        assert filtered == []

    def test_filter_recipients_preserves_order(self, validator: CommunicationValidator) -> None:
        """Test that filtering preserves order of valid recipients."""
        recipients = [
            "worker2@haymaker.onmicrosoft.com",
            "external@gmail.com",
            "worker1@haymaker.onmicrosoft.com",
        ]
        filtered = validator.filter_recipients(recipients)
        assert filtered[0] == "worker2@haymaker.onmicrosoft.com"
        assert filtered[1] == "worker1@haymaker.onmicrosoft.com"

    def test_filter_recipients_handles_duplicates(self, validator: CommunicationValidator) -> None:
        """Test that duplicates in input are handled."""
        recipients = [
            "worker1@haymaker.onmicrosoft.com",
            "worker1@haymaker.onmicrosoft.com",
            "worker1@HAYMAKER.ONMICROSOFT.COM",  # Same, different case
        ]
        filtered = validator.filter_recipients(recipients)
        # Should keep duplicates as-is (not deduplicate)
        assert len(filtered) == 3


class TestCommunicationValidatorValidateOrRaise:
    """Tests for CommunicationValidator.validate_or_raise() method.

    This method should raise ExternalRecipientError if ANY external
    recipients are present.
    """

    @pytest.fixture
    def validator(self) -> CommunicationValidator:
        """Create a validator with standard test configuration."""
        return CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={
                "worker1@haymaker.onmicrosoft.com",
                "worker2@haymaker.onmicrosoft.com",
            },
        )

    def test_validate_or_raise_passes_all_internal(self, validator: CommunicationValidator) -> None:
        """Test that all-internal recipients pass validation."""
        recipients = [
            "worker1@haymaker.onmicrosoft.com",
            "worker2@haymaker.onmicrosoft.com",
        ]
        # Should not raise
        validator.validate_or_raise(recipients)

    def test_validate_or_raise_raises_on_external(self, validator: CommunicationValidator) -> None:
        """Test that external recipient raises ExternalRecipientError."""
        recipients = [
            "worker1@haymaker.onmicrosoft.com",
            "attacker@evil.com",
        ]
        with pytest.raises(ExternalRecipientError) as exc_info:
            validator.validate_or_raise(recipients)
        assert "attacker@evil.com" in str(exc_info.value)

    def test_validate_or_raise_raises_on_all_external(
        self, validator: CommunicationValidator
    ) -> None:
        """Test that all-external recipients raises ExternalRecipientError."""
        recipients = [
            "external1@gmail.com",
            "external2@outlook.com",
        ]
        with pytest.raises(ExternalRecipientError) as exc_info:
            validator.validate_or_raise(recipients)
        # Should include both external recipients in error message
        error_msg = str(exc_info.value)
        assert "external1@gmail.com" in error_msg or "external2@outlook.com" in error_msg

    def test_validate_or_raise_passes_empty_list(self, validator: CommunicationValidator) -> None:
        """Test that empty recipient list passes validation."""
        # Empty list = no external recipients = valid
        validator.validate_or_raise([])

    def test_validate_or_raise_includes_all_blocked_in_error(
        self, validator: CommunicationValidator
    ) -> None:
        """Test that error message includes all blocked recipients."""
        recipients = [
            "worker1@haymaker.onmicrosoft.com",
            "bad1@evil.com",
            "bad2@hacker.com",
            "bad3@external.com",
        ]
        with pytest.raises(ExternalRecipientError) as exc_info:
            validator.validate_or_raise(recipients)
        error_msg = str(exc_info.value)
        # All three external addresses should be mentioned
        assert "bad1@evil.com" in error_msg
        assert "bad2@hacker.com" in error_msg
        assert "bad3@external.com" in error_msg


class TestCommunicationValidatorEdgeCases:
    """Edge case tests for CommunicationValidator."""

    def test_validator_with_custom_domain(self) -> None:
        """Test validator with custom (non-onmicrosoft) domain."""
        validator = CommunicationValidator(
            tenant_domain="contoso.com",
            allowed_upns={"user@contoso.com"},
        )
        assert validator.is_internal("user@contoso.com") is True
        assert validator.is_internal("other@contoso.com") is True
        assert validator.is_internal("user@gmail.com") is False

    def test_validator_with_multiple_domains(self) -> None:
        """Test that validator only uses single tenant domain."""
        # Per ARCHITECTURE.md, only one tenant domain is configured
        validator = CommunicationValidator(
            tenant_domain="primary.onmicrosoft.com",
            allowed_upns={
                "user@primary.onmicrosoft.com",
                "user@secondary.onmicrosoft.com",  # From allowed list
            },
        )
        # Primary domain - internal
        assert validator.is_internal("user@primary.onmicrosoft.com") is True
        # Secondary domain user in allowed list - internal
        assert validator.is_internal("user@secondary.onmicrosoft.com") is True
        # Secondary domain user NOT in allowed list - depends on domain check
        # If implementation only checks allowed_upns, this should be False
        # If implementation checks domain, this would be False (different domain)
        # Based on ARCHITECTURE.md, domain check should fail for different domains
        assert validator.is_internal("other@secondary.onmicrosoft.com") is False

    def test_validator_thread_safety_consideration(self) -> None:
        """Test that validator is suitable for concurrent use.

        Note: This test documents the expected behavior. The validator
        should be immutable after construction (no state changes during
        validation calls).
        """
        validator = CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={"user@haymaker.onmicrosoft.com"},
        )
        # Verify initial state
        initial_upns = validator.allowed_upns.copy()

        # Perform many validations
        for _ in range(100):
            validator.is_internal("user@haymaker.onmicrosoft.com")
            validator.is_internal("external@gmail.com")
            validator.filter_recipients(["user@haymaker.onmicrosoft.com", "ext@x.com"])

        # State should not have changed
        assert validator.allowed_upns == initial_upns


class TestCommunicationValidatorIntegrationScenarios:
    """Integration-style tests for realistic scenarios."""

    def test_scenario_email_send_validation(self) -> None:
        """Test validation flow for email sending operation."""
        # Setup: Create validator with run's workers
        validator = CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={
                "kw-run001-engi-001@haymaker.onmicrosoft.com",
                "kw-run001-engi-002@haymaker.onmicrosoft.com",
                "kw-run001-exec-001@haymaker.onmicrosoft.com",
            },
        )

        # Scenario: Worker sends email to team
        to_recipients = ["kw-run001-engi-002@haymaker.onmicrosoft.com"]
        cc_recipients = ["kw-run001-exec-001@haymaker.onmicrosoft.com"]

        # Validate - should pass
        validator.validate_or_raise(to_recipients)
        validator.validate_or_raise(cc_recipients)

        # Scenario: Worker accidentally includes external recipient
        to_with_external = [
            "kw-run001-engi-002@haymaker.onmicrosoft.com",
            "external.contact@gmail.com",  # Blocked!
        ]

        with pytest.raises(ExternalRecipientError):
            validator.validate_or_raise(to_with_external)

    def test_scenario_teams_mention_validation(self) -> None:
        """Test validation flow for Teams @mention operation."""
        validator = CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={
                "kw-run001-engi-001@haymaker.onmicrosoft.com",
                "kw-run001-engi-002@haymaker.onmicrosoft.com",
            },
        )

        # Mentions in Teams channel post
        mentions = [
            "kw-run001-engi-001@haymaker.onmicrosoft.com",
            "kw-run001-engi-002@haymaker.onmicrosoft.com",
        ]

        # Filter and validate
        valid_mentions = validator.filter_recipients(mentions)
        assert len(valid_mentions) == 2

    def test_scenario_meeting_invite_validation(self) -> None:
        """Test validation flow for calendar meeting invitation."""
        validator = CommunicationValidator(
            tenant_domain="haymaker.onmicrosoft.com",
            allowed_upns={
                "kw-run001-exec-001@haymaker.onmicrosoft.com",
                "kw-run001-exec-002@haymaker.onmicrosoft.com",
                "kw-run001-engi-001@haymaker.onmicrosoft.com",
            },
        )

        # Executive schedules cross-team meeting
        attendees = [
            "kw-run001-exec-002@haymaker.onmicrosoft.com",  # Same team
            "kw-run001-engi-001@haymaker.onmicrosoft.com",  # Different team
        ]

        # Should pass - both are internal
        validator.validate_or_raise(attendees)

        # Someone tries to invite external consultant - blocked
        attendees_with_external = attendees + ["consultant@external-firm.com"]
        with pytest.raises(ExternalRecipientError):
            validator.validate_or_raise(attendees_with_external)
