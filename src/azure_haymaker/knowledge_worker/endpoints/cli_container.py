"""M365 CLI Container management for Knowledge Worker Activity Framework.

Provides container deployment and management for workers using
CLI-based M365 activity execution.
"""

import asyncio
import json as json_mod
import logging
import os
import shlex
import subprocess
from typing import Any

from azure.identity import ClientSecretCredential
from azure.mgmt.appcontainers import ContainerAppsAPIClient

from azure_haymaker.knowledge_worker.models.worker import (
    WorkerConfig,
    WorkerIdentity,
)

logger = logging.getLogger(__name__)


class ContainerDeploymentError(Exception):
    """Raised when container deployment operations fail."""

    pass


class M365CLIContainerManager:
    """Manages M365 CLI containers for knowledge worker activity.

    Each container runs M365 CLI (PnP) with certificate authentication,
    executing worker activities via Graph API calls. This provides
    a cost-effective alternative to Cloud PCs for scale workers.

    Container Configuration:
        - Image: M365 CLI with Python activity scheduler
        - Resources: 0.25 vCPU, 0.5 GB RAM
        - Auth: Certificate-based via Key Vault mount

    Attributes:
        config: Orchestrator configuration
        run_id: HayMaker run ID for this deployment
    """

    CONTAINER_IMAGE = "haymakerorchacr.azurecr.io/kw-m365-cli:latest"
    DEFAULT_CPU = "0.25"
    DEFAULT_MEMORY = "0.5Gi"

    def __init__(
        self,
        config: Any,
        run_id: str,
    ):
        """Initialize M365CLIContainerManager.

        Args:
            config: Orchestrator configuration with container settings
            run_id: HayMaker run ID for resource tagging
        """
        self.config = config
        self.run_id = run_id

    async def deploy_worker_container(
        self,
        worker: WorkerIdentity,
        activity_config: WorkerConfig,
    ) -> str:
        """Deploy a container for a knowledge worker.

        The container runs M365 CLI with:
        - Certificate authentication
        - Worker identity configuration
        - Activity schedule

        Args:
            worker: Worker identity
            activity_config: Activity patterns for this worker

        Returns:
            Container App resource ID
        """
        container_name = f"kw-{self.run_id[:8]}-{worker.worker_id}"

        # Build environment variables
        env_vars = {
            "WORKER_ID": worker.worker_id,
            "WORKER_UPN": worker.user_principal_name,
            "WORKER_DEPARTMENT": worker.department,
            "WORKER_PERSONA": worker.persona.value,
            "TEAM_IDS": ",".join(worker.team_ids),
            "M365_APP_ID": getattr(self.config, "m365_app_client_id", ""),
            "M365_TENANT_ID": getattr(self.config, "target_tenant_id", ""),
            "M365_CERT_PATH": "/secrets/m365-cert.pem",
            "EMAIL_PER_HOUR": str(activity_config.email_per_hour),
            "TEAMS_MESSAGES_PER_HOUR": str(activity_config.teams_messages_per_hour),
            "DOCUMENTS_PER_DAY": str(activity_config.documents_per_day),
            "MEETINGS_PER_DAY": str(activity_config.meetings_per_day),
            "WORK_START_HOUR": str(activity_config.work_start_hour),
            "WORK_END_HOUR": str(activity_config.work_end_hour),
        }

        try:
            # Deploy container
            resource_id = await self._deploy_container_app(
                name=container_name,
                image=self.CONTAINER_IMAGE,
                env_vars=env_vars,
                cpu=self.DEFAULT_CPU,
                memory=self.DEFAULT_MEMORY,
            )

            logger.info(f"CLI container deployed for worker: {worker.worker_id} -> {resource_id}")

            return resource_id

        except Exception as e:
            logger.error(f"Failed to deploy container for {worker.worker_id}: {e}")
            raise

    async def deploy_batch(
        self,
        workers: list[tuple[WorkerIdentity, WorkerConfig]],
        max_parallel: int = 10,
    ) -> list[str]:
        """Deploy containers for multiple workers in parallel.

        Args:
            workers: List of (identity, config) tuples
            max_parallel: Maximum concurrent deployments

        Returns:
            List of container resource IDs
        """
        resource_ids: list[str] = []

        # Deploy in batches
        for i in range(0, len(workers), max_parallel):
            batch = workers[i : i + max_parallel]

            tasks = [self.deploy_worker_container(worker, config) for worker, config in batch]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, str):
                    resource_ids.append(result)
                else:
                    logger.error(f"Container deployment failed: {result}")

        logger.info(f"Deployed {len(resource_ids)} of {len(workers)} containers")
        return resource_ids

    async def stop_container(
        self,
        container_name: str,
    ) -> bool:
        """Stop a running container by scaling to zero replicas.

        Args:
            container_name: Container app name

        Returns:
            True if stopped successfully

        Raises:
            ContainerDeploymentError: If stop operation fails
        """
        try:
            resource_group = getattr(self.config, "resource_group_name", "azure-haymaker-rg")

            # Scale to zero replicas to stop the container
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "az",
                    "containerapp",
                    "update",
                    "--name",
                    container_name,
                    "--resource-group",
                    resource_group,
                    "--min-replicas",
                    "0",
                    "--max-replicas",
                    "0",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Failed to stop container {container_name}: {error_msg}")
                raise ContainerDeploymentError(f"Failed to stop container: {error_msg}")

            logger.info(f"Stopped container: {container_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop container {container_name}: {e}")
            raise ContainerDeploymentError(f"Failed to stop container: {e}") from e

    async def delete_container(
        self,
        resource_id: str,
    ) -> bool:
        """Delete a container app.

        Args:
            resource_id: Full Azure resource ID or container name

        Returns:
            True if deleted successfully

        Raises:
            ContainerDeploymentError: If delete operation fails
        """
        try:
            # Extract container name from resource ID if full ID provided
            if "/providers/Microsoft.App/containerApps/" in resource_id:
                container_name = resource_id.split("/")[-1]
            else:
                container_name = resource_id

            resource_group = getattr(self.config, "resource_group_name", "azure-haymaker-rg")

            # Delete the container app
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "az",
                    "containerapp",
                    "delete",
                    "--name",
                    container_name,
                    "--resource-group",
                    resource_group,
                    "--yes",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Failed to delete container {container_name}: {error_msg}")
                raise ContainerDeploymentError(f"Failed to delete container: {error_msg}")

            logger.info(f"Deleted container: {container_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete container {resource_id}: {e}")
            raise ContainerDeploymentError(f"Failed to delete container: {e}") from e

    async def list_containers_for_run(self) -> list[dict[str, Any]]:
        """List all containers for this run.

        Uses naming convention (kw-{run_id[:8]}-*) to find containers
        belonging to this HayMaker run.

        Returns:
            List of container info dictionaries with name, state, and resource_id

        Raises:
            ContainerDeploymentError: If list operation fails
        """
        try:
            resource_group = getattr(self.config, "resource_group_name", "azure-haymaker-rg")

            # List all container apps in resource group
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "az",
                    "containerapp",
                    "list",
                    "--resource-group",
                    resource_group,
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Failed to list containers: {error_msg}")
                raise ContainerDeploymentError(f"Failed to list containers: {error_msg}")

            all_containers = json_mod.loads(result.stdout)

            # Filter containers by naming convention: kw-{run_id[:8]}-*
            run_prefix = f"kw-{self.run_id[:8]}"
            containers = []

            for container in all_containers:
                if container.get("name", "").startswith(run_prefix):
                    containers.append(
                        {
                            "name": container["name"],
                            "state": container.get("properties", {}).get(
                                "provisioningState", "Unknown"
                            ),
                            "resource_id": container["id"],
                            "fqdn": container.get("properties", {})
                            .get("configuration", {})
                            .get("ingress", {})
                            .get("fqdn"),
                        }
                    )

            logger.info(f"Listed {len(containers)} containers for run: {self.run_id[:8]}")
            return containers

        except Exception as e:
            logger.error(f"Failed to list containers for run {self.run_id}: {e}")
            raise ContainerDeploymentError(f"Failed to list containers: {e}") from e

    async def get_container_status(
        self,
        container_name: str,
    ) -> dict[str, Any] | None:
        """Get status of a container.

        Queries Azure Container Apps API for detailed container status
        including provisioning state, replica count, and FQDN.

        Args:
            container_name: Container app name

        Returns:
            Status dictionary with name, state, replicas, fqdn, or None if not found

        Raises:
            ContainerDeploymentError: If status query fails
        """
        try:
            resource_group = getattr(self.config, "resource_group_name", "azure-haymaker-rg")

            # Get container app details
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "az",
                    "containerapp",
                    "show",
                    "--name",
                    container_name,
                    "--resource-group",
                    resource_group,
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                if "not found" in error_msg.lower():
                    logger.warning(f"Container not found: {container_name}")
                    return None
                logger.error(f"Failed to get container status for {container_name}: {error_msg}")
                raise ContainerDeploymentError(f"Failed to get container status: {error_msg}")

            container_data = json_mod.loads(result.stdout)
            properties = container_data.get("properties", {})

            status = {
                "name": container_name,
                "state": properties.get("provisioningState", "Unknown"),
                "replicas": properties.get("template", {}).get("scale", {}).get("minReplicas", 0),
                "fqdn": properties.get("configuration", {}).get("ingress", {}).get("fqdn"),
                "resource_id": container_data.get("id"),
            }

            logger.debug(f"Container status for {container_name}: {status['state']}")
            return status

        except Exception as e:
            logger.error(f"Failed to get container status for {container_name}: {e}")
            raise ContainerDeploymentError(f"Failed to get container status: {e}") from e

    async def _deploy_container_app(
        self,
        name: str,
        image: str,
        env_vars: dict[str, str],
        cpu: str,
        memory: str,
    ) -> str:
        """Deploy M365 CLI container app to Azure Container Apps.

        Uses Azure CLI for deployment with proper credential handling
        and environment configuration.

        Args:
            name: Container app name
            image: Container image
            env_vars: Environment variables
            cpu: CPU allocation (e.g., "0.25")
            memory: Memory allocation (e.g., "0.5Gi")

        Returns:
            Resource ID of deployed container

        Raises:
            ContainerDeploymentError: If deployment fails
        """
        try:
            # Create credential for Azure SDK operations
            credential = ClientSecretCredential(
                tenant_id=os.getenv("AZURE_TENANT_ID"),
                client_id=os.getenv("AZURE_CLIENT_ID"),
                client_secret=os.getenv("AZURE_CLIENT_SECRET"),
            )

            # Validate required credentials exist
            client_id = os.getenv("AZURE_CLIENT_ID", "")
            tenant_id = os.getenv("AZURE_TENANT_ID", "")
            client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

            if not all([client_id, tenant_id, client_secret]):
                raise ContainerDeploymentError(
                    "Missing required Azure credentials: AZURE_CLIENT_ID, "
                    "AZURE_CLIENT_SECRET, and AZURE_TENANT_ID must be set"
                )

            # Get Container Apps Environment (use haymaker-fastapi-cae like scenario containers)
            resource_group = getattr(self.config, "resource_group_name", "azure-haymaker-rg")
            subscription_id = getattr(self.config, "target_subscription_id", "")
            environment_name = "haymaker-fastapi-cae"

            # Verify environment exists using SDK
            env_client = ContainerAppsAPIClient(
                credential=credential, subscription_id=subscription_id
            )

            try:
                env = await asyncio.to_thread(
                    env_client.managed_environments.get,
                    resource_group_name=resource_group,
                    environment_name=environment_name,
                )
                logger.info(
                    f"Verified Container Apps Environment: {env.name} (State: {env.provisioning_state})"
                )
            except Exception as env_error:
                logger.error(f"Failed to verify Container Apps Environment: {env_error}")
                raise ContainerDeploymentError(
                    f"Container Apps Environment not accessible: {env_error}"
                ) from env_error

            # Build login command using env var for password to avoid cmdline exposure
            login_shell_cmd = (
                f"az login --service-principal "
                f"-u {shlex.quote(client_id)} "
                f"-t {shlex.quote(tenant_id)} "
                f'-p "$AZURE_CLIENT_SECRET"'
            )

            login_result = await asyncio.to_thread(
                subprocess.run,
                login_shell_cmd,
                shell=True,
                capture_output=True,
                text=True,
                env=os.environ,
            )
            if login_result.returncode != 0:
                logger.warning(
                    f"CLI login warning (may already be logged in): {login_result.stderr}"
                )

            # Get ACR credentials for registry authentication
            acr_creds = subprocess.run(
                [
                    "az",
                    "acr",
                    "credential",
                    "show",
                    "--name",
                    "haymakerorchacr",
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
            )
            acr_data = json_mod.loads(acr_creds.stdout)
            acr_username = acr_data["username"]
            acr_password = acr_data["passwords"][0]["value"]

            # Build environment variable arguments for Azure CLI
            env_args = []
            for key, value in env_vars.items():
                env_args.extend([f"{key}={value}"])

            # Build container app command - pass registry password via env var
            deploy_env = os.environ.copy()
            deploy_env["ACR_PASSWORD"] = acr_password

            cli_command = [
                "az",
                "containerapp",
                "create",
                "--name",
                name,
                "--resource-group",
                resource_group,
                "--environment",
                environment_name,
                "--image",
                image,
                "--cpu",
                cpu,
                "--memory",
                memory,
                "--ingress",
                "internal",
                "--target-port",
                "80",
                "--min-replicas",
                "0",
                "--max-replicas",
                "1",
                "--registry-server",
                "haymakerorchacr.azurecr.io",
                "--registry-username",
                acr_username,
                "--env-vars",
                *env_args,
                "--query",
                "properties.latestRevisionFqdn",
                "-o",
                "tsv",
            ]

            # Build shell command with password from env var
            base_cmd = " ".join(shlex.quote(arg) for arg in cli_command)
            shell_cmd = f'{base_cmd} --registry-password "$ACR_PASSWORD"'

            logger.info(f"Deploying M365 CLI container: {name}")
            logger.debug(f"  Environment: {environment_name}")
            logger.debug(f"  Resource Group: {resource_group}")
            logger.debug(f"  CPU: {cpu}, Memory: {memory}")

            result = await asyncio.to_thread(
                subprocess.run,
                shell_cmd,
                shell=True,
                capture_output=True,
                text=True,
                env=deploy_env,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"CLI deployment failed: {error_msg}")
                raise ContainerDeploymentError(f"Failed to deploy via CLI: {error_msg}")

            fqdn = result.stdout.strip()
            deployed_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.App/containerApps/{name}"

            logger.info(f"Successfully deployed M365 CLI container: {name}")
            logger.info(f"  Resource ID: {deployed_id}")
            logger.info(f"  FQDN: {fqdn}")

            return deployed_id

        except Exception as e:
            logger.error(f"Failed to deploy container app {name}: {e}")
            raise ContainerDeploymentError(f"Failed to deploy container app: {e}") from e
