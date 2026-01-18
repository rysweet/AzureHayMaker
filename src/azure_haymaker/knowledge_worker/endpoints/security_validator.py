"""Security validation and IP whitelisting enforcement.

Provides security validation for Azure Windows VM management:
- IP address/CIDR validation
- Wildcard rejection (no '*', '0.0.0.0/0')
- RDP port accessibility checks
- Computer Use readiness verification

SECURITY REQUIREMENTS:
    This module enforces security-first design:
    - allowed_source_ips parameter is REQUIRED (no wildcards allowed)
    - Network security groups reject wildcard IP ranges ('*', '0.0.0.0/0')
    - Public IP addresses require explicit IP whitelisting

Philosophy:
- Single responsibility: Security validation only
- Standard library dependencies only
- Self-contained and regeneratable
"""

import ipaddress
import logging
import socket
from typing import Callable

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Security validation for Windows VM management.

    Validates IP addresses, enforces wildcard rejection, and verifies
    Computer Use Agent readiness.
    """

    # Wildcard values that are explicitly rejected
    WILDCARD_VALUES = {"*", "0.0.0.0/0", "::/0", "any", "internet"}

    def validate_ip_addresses(self, ip_list: list[str]) -> list[str]:
        """Validate IP addresses/CIDR ranges.

        Args:
            ip_list: List of IP addresses or CIDR ranges

        Returns:
            Validated list of IP addresses/CIDR ranges

        Raises:
            ValueError: If any IP address/range is invalid or contains wildcards
        """
        if not isinstance(ip_list, list):
            raise ValueError("allowed_source_ips must be a list")

        if not ip_list:
            raise ValueError(
                "allowed_source_ips cannot be empty. "
                "Must specify explicit IP addresses/ranges for security."
            )

        validated = []
        for ip_str in ip_list:
            if not isinstance(ip_str, str):
                raise ValueError(f"IP address must be string, got: {type(ip_str)}")

            # Check for wildcard patterns
            validated_ip = self._validate_single_ip(ip_str)
            validated.append(validated_ip)

        return validated

    def _validate_single_ip(self, ip_str: str) -> str:
        """Validate a single IP address or CIDR range.

        Args:
            ip_str: IP address or CIDR range to validate

        Returns:
            Validated IP address/CIDR range as string

        Raises:
            ValueError: If IP is invalid or wildcard
        """
        ip_str_lower = ip_str.lower().strip()

        # Check for wildcard patterns
        if ip_str_lower in self.WILDCARD_VALUES:
            raise ValueError(
                f"Wildcard IP '{ip_str}' is not allowed. "
                f"Must specify explicit IP addresses/CIDR ranges for security. "
                f"Example: ['203.0.113.0/24'] for your organization's network."
            )

        try:
            # Validate as IP network (supports both single IPs and CIDR ranges)
            network = ipaddress.ip_network(ip_str, strict=False)

            # Additional check: reject 0.0.0.0/0 and ::/0 after parsing
            if self._is_wildcard_cidr(network):
                raise ValueError(
                    f"Wildcard CIDR range '{ip_str}' is not allowed. "
                    f"Must specify explicit IP addresses/ranges for security."
                )

            return str(network)

        except ValueError as e:
            # Re-raise with better message if it's our security check
            if "Wildcard" in str(e):
                raise
            raise ValueError(
                f"Invalid IP address or CIDR range: '{ip_str}'. "
                f"Expected format: '1.2.3.4/32' or '10.0.0.0/8'. Error: {e}"
            ) from e

    def _is_wildcard_cidr(self, network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> bool:
        """Check if a network is a wildcard CIDR (0.0.0.0/0 or ::/0).

        Args:
            network: IP network to check

        Returns:
            True if network is wildcard, False otherwise
        """
        if network.version == 4 and network.num_addresses == 2**32:
            return True
        if network.version == 6 and network.num_addresses == 2**128:
            return True
        return False


async def verify_computer_use_ready(
    vm_name: str,
    public_ip: str,
    rdp_port: int,
    get_vm_status_func: Callable[[str], str | None],
    timeout_seconds: int = 30,
) -> bool:
    """Verify VM is ready for Computer Use Agent.

    Checks:
    - VM provisioning state is "Succeeded"
    - RDP port is accessible

    Args:
        vm_name: VM name to verify
        public_ip: Public IP address of VM
        rdp_port: RDP port number (usually 3389)
        get_vm_status_func: Async function to get VM status
        timeout_seconds: Socket connection timeout

    Returns:
        True if VM is ready for Computer Use, False otherwise
    """
    logger.info(f"Verifying Computer Use readiness: {vm_name}")

    # Check VM provisioning state
    status = await get_vm_status_func(vm_name)
    if status != "Succeeded":
        logger.warning(f"VM {vm_name} not ready: status={status}")
        return False

    # Check RDP port accessibility
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout_seconds)
            sock.connect((public_ip, rdp_port))
            logger.info(f"RDP port accessible on {vm_name}")
            return True

    except (TimeoutError, ConnectionRefusedError, OSError) as e:
        # Sanitize error message
        logger.warning(
            f"RDP port not accessible on {vm_name}: {type(e).__name__}",
            exc_info=True,  # Full details in debug logs only
        )
        return False


__all__ = [
    "SecurityValidator",
    "verify_computer_use_ready",
]
