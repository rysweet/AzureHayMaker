"""Service Principal Manager for Azure HayMaker (Facade Module).

This module re-exports functionality from specialized submodules
to maintain backward compatibility with existing code.

**REFACTORED**: This module has been split into focused submodules:
- sp_validation: Input validation and sanitization
- rbac_manager: RBAC role assignments
- graph_operations: Microsoft Graph API operations with retry logic
- secret_manager: Key Vault secret storage
- secret_rotation: Secret expiration and rotation
- sp_lifecycle: Service principal creation/deletion coordination

Each submodule follows the "Bricks & Studs" philosophy with clear responsibilities
and `__all__` exports.

For new code, import directly from the specialized modules.
This facade maintains backward compatibility for existing imports.
"""

# Re-export from sp_validation
# Re-export ServicePrincipalError from exceptions
from azure_haymaker.exceptions import ServicePrincipalError

# Re-export from graph_operations
from azure_haymaker.orchestrator.graph_operations import DEFAULT_SECRET_VALIDITY_DAYS

# Re-export from rbac_manager
from azure_haymaker.orchestrator.rbac_manager import (
    CUSTOM_RBAC_ROLE_DEFINITION,
    ROLE_DEFINITIONS,
    ROLE_PROPAGATION_WAIT,
)

# Re-export from secret_rotation
from azure_haymaker.orchestrator.secret_rotation import (
    SecretExpirationInfo,
    check_and_rotate_expiring_secrets,
    check_secret_expiration,
    rotate_service_principal_secret,
)

# Re-export from sp_lifecycle
from azure_haymaker.orchestrator.sp_lifecycle import (
    ServicePrincipalDetails,
    create_service_principal,
    delete_service_principal,
    list_haymaker_service_principals,
    verify_sp_deleted,
)
from azure_haymaker.orchestrator.sp_validation import sanitize_odata_value

# Maintain __all__ for explicit public API
__all__ = [
    # Validation
    "sanitize_odata_value",
    # RBAC
    "CUSTOM_RBAC_ROLE_DEFINITION",
    "ROLE_DEFINITIONS",
    "ROLE_PROPAGATION_WAIT",
    # Constants
    "DEFAULT_SECRET_VALIDITY_DAYS",
    # Lifecycle
    "ServicePrincipalDetails",
    "create_service_principal",
    "delete_service_principal",
    "list_haymaker_service_principals",
    "verify_sp_deleted",
    # Rotation
    "SecretExpirationInfo",
    "check_and_rotate_expiring_secrets",
    "check_secret_expiration",
    "rotate_service_principal_secret",
    # Exceptions
    "ServicePrincipalError",
]
