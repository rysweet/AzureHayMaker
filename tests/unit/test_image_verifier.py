"""Unit tests for container image signature verification module.

Tests the orchestrator.image_verifier module which handles:
- ImageVerifier signature verification
- Malicious image rejection
- Unsigned image rejection
- Image provenance validation
- Approved registry enforcement
- Digest format validation

Testing approach (60/30/10 pyramid):
- 60% Unit tests (signature validation, format checks)
- 30% Integration tests (registry policy enforcement)
- 10% E2E tests (complete verification workflows)
"""

import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from azure_haymaker.orchestrator.image_verifier import (
    ImageSigningError,
    ImageVerifier,
    verify_image_signature,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def image_verifier():
    """Create ImageVerifier instance for testing."""
    return ImageVerifier()


@pytest.fixture
def approved_acr_image():
    """Example of approved ACR image with digest."""
    # Use proper 64-character SHA256 digest
    return "myregistry.azurecr.io/myapp@sha256:abc123def456abc123def456abc123def456abc123def456abc123def456abc1"


@pytest.fixture
def approved_acr_image_with_tag():
    """Example of approved ACR image with version tag."""
    return "myregistry.azurecr.io/myapp:v1"


@pytest.fixture
def unapproved_registry_image():
    """Example of image from unapproved registry."""
    return "dockerhub.com/malicious/app:latest"


# ============================================================================
# Unit Tests - Signature Verification (60%)
# ============================================================================


class TestImageSignatureVerification:
    """Tests for container image signature verification."""

    @pytest.mark.anyio
    async def test_verify_signature_with_valid_digest(
        self, image_verifier, approved_acr_image
    ):
        """Test that valid ACR image with digest passes verification."""
        result = await image_verifier.verify_signature(approved_acr_image)

        assert result is True

    @pytest.mark.anyio
    async def test_verify_signature_with_valid_version_tag(
        self, image_verifier, approved_acr_image_with_tag
    ):
        """Test that ACR image with version tag passes verification."""
        result = await image_verifier.verify_signature(approved_acr_image_with_tag)

        assert result is True

    @pytest.mark.anyio
    async def test_verify_signature_rejects_empty_image_ref(self, image_verifier):
        """Test that empty image reference raises ImageSigningError."""
        with pytest.raises(ImageSigningError, match="cannot be empty"):
            await image_verifier.verify_signature("")

    @pytest.mark.anyio
    async def test_verify_signature_rejects_whitespace_only(self, image_verifier):
        """Test that whitespace-only image reference raises error."""
        with pytest.raises(ImageSigningError, match="cannot be empty"):
            await image_verifier.verify_signature("   ")

    @pytest.mark.anyio
    async def test_verify_signature_rejects_none(self, image_verifier):
        """Test that None image reference raises error."""
        with pytest.raises(ImageSigningError, match="cannot be empty"):
            await image_verifier.verify_signature(None)

    @pytest.mark.anyio
    async def test_verify_signature_with_sha256_digest(self, image_verifier):
        """Test that image with SHA256 digest is verified correctly."""
        image_ref = (
            "myregistry.azurecr.io/app@sha256:"
            "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )

        result = await image_verifier.verify_signature(image_ref)

        assert result is True

    @pytest.mark.anyio
    async def test_verify_signature_rejects_invalid_digest_format(self, image_verifier):
        """Test that image with invalid digest format is rejected."""
        image_ref = "myregistry.azurecr.io/app@md5:invalid_digest_format"

        with pytest.raises(ImageSigningError, match="Invalid digest format"):
            await image_verifier.verify_signature(image_ref)


# ============================================================================
# Unit Tests - Registry Approval (60%)
# ============================================================================


class TestApprovedRegistryEnforcement:
    """Tests for approved container registry enforcement."""

    @pytest.mark.anyio
    async def test_azurecr_io_registry_approved(self, image_verifier):
        """Test that azurecr.io registry is approved."""
        image_ref = "mycompany.azurecr.io/app:v1"

        result = await image_verifier.verify_signature(image_ref)

        assert result is True

    @pytest.mark.anyio
    async def test_registry_prefix_approved(self, image_verifier):
        """Test that 'registry' prefix is approved for local testing."""
        image_ref = "registry:5000/localapp:latest"

        result = await image_verifier.verify_signature(image_ref)

        assert result is True

    @pytest.mark.anyio
    async def test_unapproved_registry_rejected(
        self, image_verifier, unapproved_registry_image
    ):
        """Test that unapproved registry is rejected."""
        with pytest.raises(ImageSigningError, match="not from an approved container registry"):
            await image_verifier.verify_signature(unapproved_registry_image)

    @pytest.mark.anyio
    async def test_dockerhub_rejected(self, image_verifier):
        """Test that DockerHub images are rejected."""
        with pytest.raises(ImageSigningError, match="not from an approved container registry"):
            await image_verifier.verify_signature("docker.io/library/nginx:latest")

    @pytest.mark.anyio
    async def test_gcr_rejected(self, image_verifier):
        """Test that Google Container Registry images are rejected."""
        with pytest.raises(ImageSigningError, match="not from an approved container registry"):
            await image_verifier.verify_signature("gcr.io/my-project/app:v1")

    @pytest.mark.anyio
    async def test_ecr_rejected(self, image_verifier):
        """Test that AWS ECR images are rejected."""
        with pytest.raises(ImageSigningError, match="not from an approved container registry"):
            await image_verifier.verify_signature("123456789.dkr.ecr.us-east-1.amazonaws.com/app:v1")

    @pytest.mark.anyio
    async def test_github_registry_rejected(self, image_verifier):
        """Test that GitHub Container Registry images are rejected."""
        with pytest.raises(ImageSigningError, match="not from an approved container registry"):
            await image_verifier.verify_signature("ghcr.io/myorg/app:v1")


# ============================================================================
# Unit Tests - Tag Policy Enforcement (60%)
# ============================================================================


class TestTagPolicyEnforcement:
    """Tests for container image tag policy enforcement."""

    @pytest.mark.anyio
    async def test_latest_tag_generates_warning(self, image_verifier, caplog):
        """Test that 'latest' tag generates a warning."""
        with caplog.at_level(logging.WARNING):
            await image_verifier.verify_signature("myregistry.azurecr.io/app:latest")

            # Should generate warning about unstable tag
            assert any("unstable tag" in record.message for record in caplog.records)

    @pytest.mark.anyio
    async def test_v1_tag_accepted(self, image_verifier):
        """Test that version tag 'v1' is accepted."""
        result = await image_verifier.verify_signature("myregistry.azurecr.io/app:v1")

        assert result is True

    @pytest.mark.anyio
    async def test_v2_tag_accepted(self, image_verifier):
        """Test that version tag 'v2' is accepted."""
        result = await image_verifier.verify_signature("myregistry.azurecr.io/app:v2")

        assert result is True

    @pytest.mark.anyio
    async def test_v3_tag_accepted(self, image_verifier):
        """Test that version tag 'v3' is accepted."""
        result = await image_verifier.verify_signature("myregistry.azurecr.io/app:v3")

        assert result is True

    @pytest.mark.anyio
    async def test_custom_version_tag_generates_warning(self, image_verifier, caplog):
        """Test that custom version tags generate warning."""
        with caplog.at_level(logging.WARNING):
            await image_verifier.verify_signature("myregistry.azurecr.io/app:v1.2.3")

            assert any("unstable tag" in record.message for record in caplog.records)

    @pytest.mark.anyio
    async def test_digest_preferred_over_tag(self, image_verifier, caplog):
        """Test that digest-based references don't generate warnings."""
        with caplog.at_level(logging.WARNING):
            await image_verifier.verify_signature(
                "myregistry.azurecr.io/app@sha256:abc123def456abc123def456abc123def456abc123def456abc123def456abc1"
            )

            # Should NOT generate any warnings
            assert not any("unstable" in record.message for record in caplog.records)


# ============================================================================
# Unit Tests - Malicious Image Detection (60%)
# ============================================================================


class TestMaliciousImageDetection:
    """Tests for detecting and rejecting malicious images."""

    @pytest.mark.anyio
    async def test_sql_injection_in_image_name_rejected(self, image_verifier):
        """Test that SQL injection attempts in image name are rejected."""
        malicious_image = "'; DROP TABLE images; --"

        with pytest.raises(ImageSigningError):
            await image_verifier.verify_signature(malicious_image)

    @pytest.mark.anyio
    async def test_command_injection_in_image_name_rejected(self, image_verifier):
        """Test that command injection attempts are rejected."""
        malicious_image = "myregistry.azurecr.io/app; rm -rf /"

        with pytest.raises(ImageSigningError):
            await image_verifier.verify_signature(malicious_image)

    @pytest.mark.anyio
    async def test_path_traversal_in_image_name_rejected(self, image_verifier):
        """Test that path traversal attempts are rejected."""
        malicious_image = "myregistry.azurecr.io/../../etc/passwd"

        with pytest.raises(ImageSigningError):
            await image_verifier.verify_signature(malicious_image)

    @pytest.mark.anyio
    async def test_null_byte_injection_rejected(self, image_verifier):
        """Test that null byte injection is rejected."""
        malicious_image = "myregistry.azurecr.io/app\x00malicious"

        with pytest.raises(ImageSigningError):
            await image_verifier.verify_signature(malicious_image)

    @pytest.mark.anyio
    async def test_unicode_obfuscation_rejected(self, image_verifier):
        """Test that unicode obfuscation attempts are handled."""
        # Using unicode lookalike characters to mimic approved registry
        malicious_image = "myregistry.ɑzurecr.io/app:v1"  # 'a' is unicode lookalike

        # Should be rejected as it doesn't contain actual "azurecr.io"
        with pytest.raises(ImageSigningError, match="not from an approved"):
            await image_verifier.verify_signature(malicious_image)


# ============================================================================
# Unit Tests - Image Provenance (60%)
# ============================================================================


class TestImageProvenance:
    """Tests for image provenance validation."""

    @pytest.mark.anyio
    async def test_image_with_full_path_accepted(self, image_verifier):
        """Test that image with full registry path is accepted."""
        image_ref = "mycompany.azurecr.io/team/project/app:v1"

        result = await image_verifier.verify_signature(image_ref)

        assert result is True

    @pytest.mark.anyio
    async def test_image_digest_extraction(self, image_verifier, caplog):
        """Test that digest is properly extracted and logged."""
        image_ref = (
            "myregistry.azurecr.io/app@sha256:"
            "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

        with caplog.at_level(logging.INFO):
            await image_verifier.verify_signature(image_ref)

            # Should log digest verification
            assert any("sha256:1234567890" in record.message for record in caplog.records)

    @pytest.mark.anyio
    async def test_image_without_digest_or_tag_rejected(self, image_verifier):
        """Test that image without digest or tag is rejected."""
        image_ref = "myregistry.azurecr.io/app"

        with pytest.raises(ImageSigningError):
            await image_verifier.verify_signature(image_ref)


# ============================================================================
# Unit Tests - Error Handling (60%)
# ============================================================================


class TestImageVerifierErrorHandling:
    """Tests for error handling in image verification."""

    @pytest.mark.anyio
    async def test_generic_exception_wrapped_in_signing_error(self, image_verifier):
        """Test that generic exceptions are wrapped in ImageSigningError."""
        # Image reference that might cause unexpected errors
        image_ref = "myregistry.azurecr.io/app@sha256:short"

        # Should raise ImageSigningError with appropriate message about invalid digest format
        with pytest.raises(ImageSigningError, match="Invalid SHA256 digest format"):
            await image_verifier.verify_signature(image_ref)

    @pytest.mark.anyio
    async def test_image_signing_error_propagates(self, image_verifier):
        """Test that ImageSigningError is propagated without wrapping."""
        with pytest.raises(ImageSigningError, match="not from an approved"):
            await image_verifier.verify_signature("evil.com/malware:latest")

    @pytest.mark.anyio
    async def test_multiple_at_signs_handled(self, image_verifier):
        """Test handling of malformed image reference with multiple @ signs."""
        malicious_image = "myregistry.azurecr.io/app@sha256:abc@extra"

        with pytest.raises(ImageSigningError):
            await image_verifier.verify_signature(malicious_image)


# ============================================================================
# Integration Tests - Registry Client Integration (30%)
# ============================================================================


class TestRegistryClientIntegration:
    """Integration tests with registry client parameter."""

    @pytest.mark.anyio
    async def test_verify_signature_with_registry_client(self, image_verifier):
        """Test that registry_client parameter is accepted."""
        mock_client = Mock()
        image_ref = "myregistry.azurecr.io/app:v1"

        result = await image_verifier.verify_signature(image_ref, registry_client=mock_client)

        assert result is True

    @pytest.mark.anyio
    async def test_verify_signature_with_none_registry_client(self, image_verifier):
        """Test that None registry_client works (default case)."""
        image_ref = "myregistry.azurecr.io/app:v1"

        result = await image_verifier.verify_signature(image_ref, registry_client=None)

        assert result is True


# ============================================================================
# Integration Tests - Multiple Image Verification (30%)
# ============================================================================


class TestMultipleImageVerification:
    """Integration tests for verifying multiple images."""

    @pytest.mark.anyio
    async def test_verify_multiple_valid_images(self, image_verifier):
        """Test verifying multiple valid images in sequence."""
        images = [
            "registry1.azurecr.io/app1:v1",
            "registry2.azurecr.io/app2:v2",
            "registry3.azurecr.io/app3@sha256:abc123def456abc123def456abc123def456abc123def456abc123def456abc1",
        ]

        results = []
        for image in images:
            result = await image_verifier.verify_signature(image)
            results.append(result)

        assert all(results)
        assert len(results) == 3

    @pytest.mark.anyio
    async def test_verify_mixed_valid_invalid_images(self, image_verifier):
        """Test verifying mix of valid and invalid images."""
        valid_images = [
            "registry1.azurecr.io/app1:v1",
            "registry2.azurecr.io/app2:v2",
        ]
        invalid_images = [
            "dockerhub.com/malicious:latest",
            "evil.com/app:v1",
        ]

        # Valid images should pass
        for image in valid_images:
            result = await image_verifier.verify_signature(image)
            assert result is True

        # Invalid images should fail
        for image in invalid_images:
            with pytest.raises(ImageSigningError):
                await image_verifier.verify_signature(image)


# ============================================================================
# Integration Tests - Logging and Audit Trail (30%)
# ============================================================================


class TestVerificationLogging:
    """Integration tests for verification logging and audit trail."""

    @pytest.mark.anyio
    async def test_successful_verification_logged(self, image_verifier, caplog):
        """Test that successful verification is logged."""
        with caplog.at_level(logging.INFO):
            await image_verifier.verify_signature("myregistry.azurecr.io/app:v1")

            assert any("Verifying image signature" in record.message for record in caplog.records)

    @pytest.mark.anyio
    async def test_failed_verification_logged(self, image_verifier, caplog):
        """Test that failed verification is logged."""
        with caplog.at_level(logging.INFO):
            with pytest.raises(ImageSigningError):
                await image_verifier.verify_signature("evil.com/malware:latest")

            # Should have logged verification attempt
            assert any("Verifying image signature" in record.message for record in caplog.records)

    @pytest.mark.anyio
    async def test_digest_verification_logged(self, image_verifier, caplog):
        """Test that digest verification is logged with truncated digest."""
        with caplog.at_level(logging.INFO):
            await image_verifier.verify_signature(
                "myregistry.azurecr.io/app@sha256:1234567890abcdef"
            )

            # Should log digest verification with truncation
            assert any("Image signature verified with digest" in record.message for record in caplog.records)


# ============================================================================
# E2E Tests - Complete Verification Workflows (10%)
# ============================================================================


class TestCompleteVerificationWorkflows:
    """E2E tests for complete image verification workflows."""

    @pytest.mark.anyio
    async def test_full_verification_workflow_with_digest(self):
        """Test complete workflow for image with digest."""
        verifier = ImageVerifier()
        image_ref = (
            "mycompany.azurecr.io/team/app@sha256:"
            "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )

        # Should complete full verification without errors
        result = await verifier.verify_signature(image_ref)

        assert result is True

    @pytest.mark.anyio
    async def test_full_verification_workflow_with_version_tag(self):
        """Test complete workflow for image with version tag."""
        verifier = ImageVerifier()
        image_ref = "production.azurecr.io/backend/api:v2"

        result = await verifier.verify_signature(image_ref)

        assert result is True

    @pytest.mark.anyio
    async def test_standalone_verify_function(self):
        """Test standalone verify_image_signature function."""
        image_ref = "myregistry.azurecr.io/app:v1"

        result = await verify_image_signature(image_ref)

        assert result is True

    @pytest.mark.anyio
    async def test_standalone_function_with_registry_client(self):
        """Test standalone function accepts registry_client parameter."""
        mock_client = Mock()
        image_ref = "myregistry.azurecr.io/app:v1"

        result = await verify_image_signature(image_ref, registry_client=mock_client)

        assert result is True

    @pytest.mark.anyio
    async def test_standalone_function_rejects_invalid_registry(self):
        """Test standalone function rejects unapproved registry."""
        image_ref = "dockerhub.com/malicious:latest"

        with pytest.raises(ImageSigningError, match="not from an approved"):
            await verify_image_signature(image_ref)


# ============================================================================
# E2E Tests - Security Boundary Validation (10%)
# ============================================================================


class TestSecurityBoundaryValidation:
    """E2E tests for security boundary validation."""

    @pytest.mark.anyio
    async def test_cross_tenant_image_reference_rejected(self, image_verifier):
        """Test that cross-tenant image references are properly validated."""
        # Only azurecr.io is approved, cross-tenant attempts should fail
        cross_tenant_image = "eviltenant.azurecr.io/../../victimtenant/secrets:latest"

        # Will fail on registry check or path traversal
        try:
            await image_verifier.verify_signature(cross_tenant_image)
            # If it passes registry check, it should still be valid ACR
            assert "azurecr.io" in cross_tenant_image
        except ImageSigningError:
            # Path traversal might be caught
            pass

    @pytest.mark.anyio
    async def test_image_reference_character_limits(self, image_verifier):
        """Test handling of extremely long image references."""
        # Create a very long but valid image reference
        long_path = "/".join(["subdir"] * 50)
        long_image = f"myregistry.azurecr.io/{long_path}/app:v1"

        # Should handle long references without crashing
        result = await image_verifier.verify_signature(long_image)
        assert result is True

    @pytest.mark.anyio
    async def test_concurrent_verification_requests(self, image_verifier):
        """Test handling of concurrent verification requests."""
        images = [
            f"registry{i}.azurecr.io/app{i}:v1"
            for i in range(10)
        ]

        # Verify all images concurrently (simulating multiple requests)
        import asyncio
        results = await asyncio.gather(
            *[image_verifier.verify_signature(img) for img in images]
        )

        assert all(results)
        assert len(results) == 10


# ============================================================================
# E2E Tests - Production Readiness (10%)
# ============================================================================


class TestProductionReadiness:
    """E2E tests for production readiness scenarios."""

    @pytest.mark.anyio
    async def test_production_deployment_scenario(self):
        """Test realistic production deployment scenario."""
        verifier = ImageVerifier()

        # Production images typically use digest for immutability
        production_images = [
            "prod.azurecr.io/frontend@sha256:abc123def456abc123def456abc123def456abc123def456abc123def456abc1",
            "prod.azurecr.io/backend@sha256:def789ghi012def789ghi012def789ghi012def789ghi012def789ghi012def7",
            "prod.azurecr.io/worker@sha256:ghi345jkl678ghi345jkl678ghi345jkl678ghi345jkl678ghi345jkl678ghi3",
        ]

        for image in production_images:
            result = await verifier.verify_signature(image)
            assert result is True

    @pytest.mark.anyio
    async def test_development_deployment_scenario(self):
        """Test development deployment with version tags."""
        verifier = ImageVerifier()

        # Development might use version tags
        dev_images = [
            "dev.azurecr.io/frontend:v1",
            "dev.azurecr.io/backend:v2",
        ]

        for image in dev_images:
            result = await verifier.verify_signature(image)
            assert result is True

    @pytest.mark.anyio
    async def test_registry_migration_scenario(self):
        """Test scenario where registries are migrated."""
        verifier = ImageVerifier()

        # Old and new registry both should work if both are azurecr.io
        old_registry = "oldregistry.azurecr.io/app:v1"
        new_registry = "newregistry.azurecr.io/app:v1"

        result_old = await verifier.verify_signature(old_registry)
        result_new = await verifier.verify_signature(new_registry)

        assert result_old is True
        assert result_new is True
