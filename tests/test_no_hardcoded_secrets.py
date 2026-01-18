"""Test to verify no hardcoded secrets in documentation.

This test ensures that documentation examples follow security best practices
by using Key Vault references instead of hardcoded credentials.

Philosophy:
- Zero-BS: Test real security requirements, not placeholders
- Ruthless Simplicity: Direct pattern matching, no complex parsing
"""

import re
from pathlib import Path

import pytest


class TestHardcodedSecrets:
    """Test suite for detecting hardcoded secrets in documentation."""

    # Patterns that indicate potential hardcoded secrets
    HARDCODED_SECRET_PATTERNS = [
        # VPN shared keys that are not variables or Key Vault references
        r'--value\s+"[^$][^"]*"',  # --value "hardcoded" (not --value "$VAR")
        r'sharedKey:\s+"[^$][^"]*"',  # sharedKey: "hardcoded"
        r'shared-key\s+"[^$][^"]*"',  # shared-key "hardcoded"

        # Common test credentials patterns
        r'(password|secret|key).*[:=]\s*"[^$][A-Za-z0-9]{8,}"',  # Generic secrets
    ]

    # Allowed patterns (these are OK to have)
    ALLOWED_PATTERNS = [
        r'\$\{.*\}',  # Variable interpolation ${VAR}
        r'\$\(.*\)',  # Command substitution $(cmd)
        r'<.*>',     # Placeholders <your-key>
        r'"\*{3,}"',  # Masked values "***"
    ]

    @pytest.fixture
    def docs_directory(self) -> Path:
        """Get the src/docs_scenarios directory."""
        repo_root = Path(__file__).parent.parent
        docs_dir = repo_root / "src" / "docs_scenarios"
        assert docs_dir.exists(), f"Documentation directory not found: {docs_dir}"
        return docs_dir

    def test_no_hardcoded_vpn_keys(self, docs_directory: Path):
        """Test that VPN documentation doesn't contain hardcoded shared keys."""
        vpn_doc = docs_directory / "networking-02-vpn-gateway.md"
        assert vpn_doc.exists(), f"VPN documentation not found: {vpn_doc}"

        content = vpn_doc.read_text()

        # Check for hardcoded --value patterns
        hardcoded_value_pattern = r'--value\s+"([^$][^"]*)"'
        matches = re.findall(hardcoded_value_pattern, content, re.MULTILINE)

        # Filter out allowed patterns
        violations = []
        for match in matches:
            # Skip if it's a placeholder
            if not (match.startswith('<') and match.endswith('>')):
                violations.append(f'--value "{match}"')

        assert len(violations) == 0, (
            f"Found {len(violations)} hardcoded shared key(s) in {vpn_doc.name}:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nExpected: Key Vault references like $(az keyvault secret show ...)"
        )

    def test_vpn_doc_uses_keyvault_pattern(self, docs_directory: Path):
        """Test that VPN documentation demonstrates Key Vault pattern."""
        vpn_doc = docs_directory / "networking-02-vpn-gateway.md"
        content = vpn_doc.read_text()

        # Verify Key Vault pattern is documented
        keyvault_patterns = [
            r'az keyvault secret show',
            r'KEY_VAULT_NAME',
            r'--query "value"',
        ]

        for pattern in keyvault_patterns:
            assert re.search(pattern, content), (
                f"VPN documentation should demonstrate Key Vault pattern. "
                f"Missing: {pattern}"
            )

    def test_all_docs_no_obvious_secrets(self, docs_directory: Path):
        """Test all documentation files for obvious hardcoded secrets."""
        violations = []

        for doc_file in docs_directory.glob("**/*.md"):
            content = doc_file.read_text()

            # Check for patterns like: secretValue="SomeHardcodedValue123"
            obvious_secret_pattern = r'(secret|password|key)\w*\s*[:=]\s*"[A-Za-z0-9]{10,}"'
            matches = re.findall(obvious_secret_pattern, content, re.IGNORECASE)

            if matches:
                # Filter out variable references and placeholders
                for match in matches:
                    if not any(re.search(allowed, match) for allowed in self.ALLOWED_PATTERNS):
                        violations.append(f"{doc_file.name}: {match}")

        assert len(violations) == 0, (
            f"Found {len(violations)} potential hardcoded secret(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v"])
