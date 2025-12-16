"""Secret Injection Handler for Azure Container Apps

Handles secret injection from Azure Key Vault to Container Apps with RBAC propagation wait.

Philosophy:
- Zero-BS implementation: Every function works
- Ruthless simplicity: Standard library + Azure SDK only
- Clear error handling with comprehensive logging
- Exponential backoff for RBAC propagation

Public API:
    SecretInjectionHandler: Main handler class
    RBACPropagationError: RBAC timeout exception
    SecretInjectionError: Secret injection failure exception
"""

import contextlib
import logging
import subprocess
import time

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

__all__ = [
    "SecretInjectionHandler",
    "RBACPropagationError",
    "SecretInjectionError",
]

# Configure logging
logger = logging.getLogger(__name__)


class RBACPropagationError(Exception):
    """Raised when RBAC propagation times out"""

    pass


class SecretInjectionError(Exception):
    """Raised when secret injection fails"""

    pass


class SecretInjectionHandler:
    """Handles secret injection from Key Vault to Container Apps

    Features:
    - RBAC propagation wait with exponential backoff
    - Key Vault access verification
    - Secret injection via Azure CLI
    - Comprehensive error handling and logging
    """

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        max_retries: int = 5,
        initial_backoff_seconds: int = 10,
    ):
        """Initialize secret injection handler

        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            max_retries: Maximum number of retry attempts
            initial_backoff_seconds: Initial backoff delay in seconds
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.max_retries = max_retries
        self.initial_backoff_seconds = initial_backoff_seconds
        self.credential = DefaultAzureCredential()

    def wait_for_rbac_propagation(
        self,
        keyvault_name: str,
        identity_principal_id: str,
    ) -> bool:
        """Wait for RBAC role assignments to propagate

        Args:
            keyvault_name: Key Vault name
            identity_principal_id: Managed identity principal ID

        Returns:
            True if RBAC propagation successful

        Raises:
            RBACPropagationError: If RBAC propagation times out
            ValueError: If keyvault_name is empty
        """
        if not keyvault_name:
            raise ValueError("keyvault_name cannot be empty")

        logger.info(
            f"Waiting for RBAC propagation for Key Vault '{keyvault_name}' "
            f"and principal ID '{identity_principal_id}'"
        )

        for attempt in range(self.max_retries):
            # Check if Key Vault access is ready
            if self._check_keyvault_access(keyvault_name):
                logger.info(f"RBAC propagation complete after {attempt + 1} attempt(s)")
                return True

            # Calculate exponential backoff delay (sleep after every failed attempt, including the last one)
            delay = self.initial_backoff_seconds * (2**attempt)
            logger.info(
                f"Waiting for RBAC propagation... (attempt {attempt + 1}/{self.max_retries}), "
                f"sleeping {delay}s"
            )
            time.sleep(delay)

        # RBAC propagation timeout
        raise RBACPropagationError(
            f"RBAC propagation timeout after {self.max_retries} attempts for Key Vault '{keyvault_name}'. "
            f"Role assignments may not have propagated yet."
        )

    def _check_keyvault_access(self, keyvault_name: str) -> bool:
        """Check if Key Vault access is ready

        Args:
            keyvault_name: Key Vault name

        Returns:
            True if access is ready, False if forbidden (403)

        Raises:
            HttpResponseError: For non-403 HTTP errors
        """
        vault_url = f"https://{keyvault_name}.vault.azure.net"

        try:
            # Try to list secrets (minimal permission check)
            secret_client = SecretClient(vault_url=vault_url, credential=self.credential)
            # Consume iterator to trigger actual API call -  Need to get at least one item or exhaust iterator
            with contextlib.suppress(StopIteration):
                next(secret_client.list_properties_of_secrets())
            return True

        except HttpResponseError as e:
            if e.status_code == 403:
                # Forbidden - RBAC not propagated yet
                logger.debug(f"Key Vault access not ready: {e}")
                return False
            else:
                # Other errors should propagate
                raise

    def inject_secrets_to_container_app(
        self,
        container_app_name: str,
        keyvault_name: str,
        secrets: list[dict[str, str]],
    ) -> bool:
        """Inject secrets from Key Vault to Container App

        Args:
            container_app_name: Container app name
            keyvault_name: Key Vault name
            secrets: List of secret mappings, each with:
                - name: Environment variable name
                - keyvault_secret: Key Vault secret name

        Returns:
            True if injection successful

        Raises:
            ValueError: If secrets list is empty or invalid format
            SecretInjectionError: If injection fails after retries
        """
        # Validate inputs
        if not secrets:
            raise ValueError("secrets list cannot be empty")

        for secret in secrets:
            if "name" not in secret or "keyvault_secret" not in secret:
                raise ValueError("Secret must have 'name' and 'keyvault_secret' keys")

        logger.info(f"Injecting {len(secrets)} secret(s) to container app '{container_app_name}'")

        # Step 1: Create secrets with Key Vault references
        # Format: secretname=keyvaultref:https://vault.azure.net/secrets/name,identityref:system
        cmd_secret = [
            "az",
            "containerapp",
            "secret",
            "set",
            "--name",
            container_app_name,
            "--resource-group",
            self.resource_group,
            "--secrets",
        ]

        # Add secret references with Key Vault format
        secret_refs = []
        for secret in secrets:
            # Get Key Vault URI from keyvault name
            vault_uri = f"https://{keyvault_name}.vault.azure.net"
            # Secret name must be lowercase
            secret_name = secret["name"].lower()
            # Format: secretname=keyvaultref:https://vault.azure.net/secrets/secretname,identityref:system
            secret_ref = f"{secret_name}=keyvaultref:{vault_uri}/secrets/{secret['keyvault_secret']},identityref:system"
            secret_refs.append(secret_ref)

        cmd_secret.extend(secret_refs)

        # Retry logic for transient failures
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Step 1: Create secrets
                logger.info(f"Secret injection attempt {attempt + 1} - Creating secrets")
                result = subprocess.run(
                    cmd_secret,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode != 0:
                    last_error = result.stderr
                    logger.warning(f"Secret creation attempt {attempt + 1} failed: {result.stderr}")
                    print(f"Secret injection attempt {attempt + 1} failed: {result.stderr}")
                    if attempt < self.max_retries - 1:
                        time.sleep(5)
                        continue
                    else:
                        break

                logger.info("Secrets created successfully")

                # Step 2: Set environment variables to reference secrets
                cmd_env = [
                    "az",
                    "containerapp",
                    "update",
                    "--name",
                    container_app_name,
                    "--resource-group",
                    self.resource_group,
                    "--set-env-vars",
                ]

                env_refs = []
                for secret in secrets:
                    secret_name = secret["name"].lower()
                    # Use explicit env_var name if provided, otherwise uppercase the secret name
                    env_var_name = secret.get("env_var", secret["name"].upper())
                    env_refs.append(f"{env_var_name}=secretref:{secret_name}")

                cmd_env.extend(env_refs)

                logger.info("Setting environment variables to reference secrets")
                result_env = subprocess.run(cmd_env, capture_output=True, text=True, timeout=120)

                if result_env.returncode == 0:
                    logger.info(
                        f"Successfully injected secrets to container app '{container_app_name}'"
                    )
                    return True
                else:
                    last_error = result_env.stderr
                    logger.warning(f"Environment variable setup failed: {result_env.stderr}")
                    print(f"Secret injection attempt {attempt + 1} failed: {result_env.stderr}")

            except subprocess.TimeoutExpired:
                last_error = "Command timed out"
                logger.warning(f"Secret injection attempt {attempt + 1} timed out")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Secret injection attempt {attempt + 1} failed: {e}")

            # Sleep before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                time.sleep(5)

        # All retries failed
        logger.error(
            f"Failed to inject secrets to container app '{container_app_name}' "
            f"after {self.max_retries} attempts"
        )
        raise SecretInjectionError(
            f"Failed to inject secrets to container app '{container_app_name}': {last_error}"
        )
