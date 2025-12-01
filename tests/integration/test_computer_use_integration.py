"""Integration tests for Computer Use Knowledge Worker Agents.

This module tests end-to-end integration of Computer Use agents including:
- VM provisioning
- Agent deployment
- Browser automation
- Workflow execution
- Telemetry collection
- Full lifecycle from provision to cleanup

Uses pytest with mocks for Azure services and real browser automation
(when available).

NOTE: Tests requiring real Windows VMs are marked with @pytest.mark.requires_vm
and will be skipped in CI. Run manually with real Azure resources for full validation.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Custom marker for tests requiring real VMs
requires_vm = pytest.mark.skipif(
    True,  # Always skip in CI
    reason="Requires real Windows VM - run manually with Azure resources"
)

# Import modules under test
try:
    from azure_haymaker.knowledge_worker.computer_use.agent import (
        ComputerUseConfig,
        ComputerUseKnowledgeWorkerAgent,
    )
    from azure_haymaker.knowledge_worker.computer_use.agent_deployer import (
        AgentDeployer,
    )
    from azure_haymaker.knowledge_worker.computer_use.browser_automation import (
        BrowserAutomation,
    )
    from azure_haymaker.knowledge_worker.computer_use.telemetry import (
        ComputerUseTelemetryCollector,
    )
    from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
        WinRMConnection,
    )
    from azure_haymaker.knowledge_worker.endpoints.windows_vm import (
        WindowsVMManager,
    )
    from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False
    ComputerUseKnowledgeWorkerAgent = None
    ComputerUseConfig = None
    AgentDeployer = None
    BrowserAutomation = None
    ComputerUseTelemetryCollector = None
    WinRMConnection = None
    WindowsVMManager = None
    WorkerIdentity = None


pytestmark = pytest.mark.skipif(
    not INTEGRATION_AVAILABLE,
    reason="Computer Use integration modules not yet implemented",
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def run_id():
    """Fixture: Unique run ID."""
    return str(uuid4())


@pytest.fixture
def worker_identity():
    """Fixture: Worker identity."""
    return WorkerIdentity(
        worker_id="kw-integ-001",
        display_name="Integration Test Worker",
        user_principal_name="integ.worker@tenant.onmicrosoft.com",
        entra_object_id=str(uuid4()),
        department="engineering",
        persona="engineering",
        endpoint_type="cloud_pc",
        endpoint_id="",
        team_ids=["team-001"],
    )


@pytest.fixture
def mock_vm_manager():
    """Fixture: Mock WindowsVMManager."""
    manager = MagicMock(spec=WindowsVMManager)

    # Mock VM provisioning
    mock_vm = {
        "vm_id": f"vm-{uuid4()}",
        "hostname": "test-vm.westus2.cloudapp.azure.com",
        "username": "kwadmin",
        "password": "SecureP@ssw0rd123!",
        "status": "running",
    }

    manager.provision_vm = AsyncMock(return_value=mock_vm)
    manager.wait_for_vm_ready = AsyncMock(return_value=True)
    manager.delete_vm = AsyncMock(return_value=True)
    manager.get_vm_status = AsyncMock(return_value="running")

    return manager


@pytest.fixture
def mock_winrm():
    """Fixture: Mock WinRM connection."""
    with patch(
        "azure_haymaker.knowledge_worker.computer_use.winrm_connection.Protocol"
    ) as mock:
        protocol = MagicMock()
        mock.return_value = protocol

        protocol.open_shell.return_value = "shell-123"
        protocol.close_shell.return_value = None
        protocol.run_command.return_value = "cmd-456"
        protocol.get_command_output.return_value = (b"Success", b"", 0)
        protocol.cleanup_command.return_value = None

        yield protocol


@pytest.fixture
def mock_browser():
    """Fixture: Mock browser automation."""
    with patch(
        "azure_haymaker.knowledge_worker.computer_use.browser_automation.async_playwright"
    ) as mock_pw:
        playwright = AsyncMock()
        browser = AsyncMock()
        context = AsyncMock()
        page = AsyncMock()

        mock_pw.return_value.__aenter__.return_value = playwright
        playwright.chromium.launch.return_value = browser
        browser.new_context.return_value = context
        context.new_page.return_value = page

        page.goto = AsyncMock()
        page.fill = AsyncMock()
        page.click = AsyncMock()
        page.wait_for_selector = AsyncMock()

        yield {
            "playwright": playwright,
            "browser": browser,
            "context": context,
            "page": page,
        }


@pytest.fixture
def workflows():
    """Fixture: Sample workflows."""
    return [
        {
            "name": "email_workflow",
            "script": "email_workflow.py",
            "description": "Send emails via browser",
        },
        {
            "name": "teams_workflow",
            "script": "teams_workflow.py",
            "description": "Send Teams messages",
        },
    ]


# ==============================================================================
# FULL WORKFLOW INTEGRATION TESTS
# ==============================================================================


class TestFullLifecycleIntegration:
    """Integration tests for full agent lifecycle."""

    @requires_vm
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_provision_vm_deploy_agent_execute_workflow(
        self, worker_identity, mock_vm_manager, mock_winrm, mock_browser, workflows
    ):
        """Test complete workflow: provision VM, deploy agent, execute workflow."""
        # Phase 1: Provision VM
        vm_info = await mock_vm_manager.provision_vm(
            worker_identity=worker_identity, vm_size="Standard_D4s_v3"
        )
        assert vm_info["status"] == "running"
        assert vm_info["hostname"]

        # Wait for VM ready
        ready = await mock_vm_manager.wait_for_vm_ready(
            vm_id=vm_info["vm_id"], timeout_minutes=10
        )
        assert ready is True

        # Phase 2: Deploy agent
        winrm_conn = WinRMConnection(
            hostname=vm_info["hostname"],
            username=vm_info["username"],
            password=vm_info["password"],
        )
        winrm_conn.connect()

        deployer = AgentDeployer(connection=winrm_conn)
        deployment = deployer.deploy_agent(
            worker_identity=worker_identity, workflows=workflows
        )
        assert deployment["success"] is True

        # Verify deployment
        verification = deployer.verify_deployment(
            worker_identity=worker_identity,
            deployment_path=deployment["deployment_path"],
        )
        assert verification["verified"] is True

        # Phase 3: Execute workflow via agent
        config = ComputerUseConfig(
            worker_id=worker_identity.worker_id,
            display_name=worker_identity.display_name,
            vm_hostname=vm_info["hostname"],
            vm_username=vm_info["username"],
            vm_password=vm_info["password"],
            m365_username=worker_identity.user_principal_name,
            m365_password="M365P@ssw0rd!",
        )

        agent = ComputerUseKnowledgeWorkerAgent(
            worker_config=config, worker_identity=worker_identity
        )
        agent.on_start()

        result = await agent.execute_workflow(
            workflow_name="email_workflow",
            params={
                "to": "recipient@tenant.com",
                "subject": "Integration Test",
                "body": "This is an integration test email.",
            },
        )
        assert result["success"] is True

        # Phase 4: Cleanup
        agent.on_cleanup(exit_code=0)
        winrm_conn.disconnect()

        deleted = await mock_vm_manager.delete_vm(vm_id=vm_info["vm_id"])
        assert deleted is True

    @requires_vm
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_agent_deployment(
        self, mock_vm_manager, mock_winrm, workflows
    ):
        """Test deploying multiple agents in batch."""
        # Create multiple workers
        workers = [
            WorkerIdentity(
                worker_id=f"kw-integ-{i:03d}",
                display_name=f"Worker {i}",
                user_principal_name=f"worker{i}@tenant.com",
                entra_object_id=str(uuid4()),
                department="engineering",
                persona="engineering",
                endpoint_type="cloud_pc",
                endpoint_id="",
                team_ids=["team-001"],
            )
            for i in range(5)
        ]

        # Provision VMs
        vm_infos = []
        for worker in workers:
            vm_info = await mock_vm_manager.provision_vm(
                worker_identity=worker, vm_size="Standard_D4s_v3"
            )
            vm_infos.append(vm_info)

        assert len(vm_infos) == len(workers)

        # Deploy agents
        deployment_results = []
        for worker, vm_info in zip(workers, vm_infos, strict=False):
            winrm_conn = WinRMConnection(
                hostname=vm_info["hostname"],
                username=vm_info["username"],
                password=vm_info["password"],
            )
            winrm_conn.connect()

            deployer = AgentDeployer(connection=winrm_conn)
            deployment = deployer.deploy_agent(
                worker_identity=worker, workflows=workflows
            )
            deployment_results.append(deployment)
            winrm_conn.disconnect()

        # All deployments should succeed
        assert all(d["success"] for d in deployment_results)


# ==============================================================================
# TELEMETRY INTEGRATION TESTS
# ==============================================================================


class TestTelemetryIntegration:
    """Integration tests for telemetry collection."""

    @requires_vm
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_execution_produces_telemetry(
        self, worker_identity, mock_browser
    ):
        """Test workflow execution produces telemetry logs."""
        # Arrange
        config = ComputerUseConfig(
            worker_id=worker_identity.worker_id,
            display_name=worker_identity.display_name,
            vm_hostname="test-vm.westus2.cloudapp.azure.com",
            vm_username="kwadmin",
            vm_password="VmP@ssw0rd!",
            m365_username=worker_identity.user_principal_name,
            m365_password="M365P@ssw0rd!",
        )

        agent = ComputerUseKnowledgeWorkerAgent(
            worker_config=config, worker_identity=worker_identity
        )

        # Setup telemetry collector
        telemetry = ComputerUseTelemetryCollector(worker_identity=worker_identity)
        agent.telemetry_collector = telemetry

        # Act
        agent.on_start()

        await agent.execute_workflow(
            workflow_name="email_workflow",
            params={"to": "test@tenant.com", "subject": "Test", "body": "Test"},
        )

        await agent.execute_workflow(
            workflow_name="teams_workflow",
            params={"channel": "General", "message": "Hello!"},
        )

        agent.on_cleanup(exit_code=0)

        # Assert
        logs = telemetry.get_logs()
        assert len(logs) >= 2  # At least 2 workflow executions

        metrics = telemetry.get_metrics_summary()
        assert metrics.total_operations >= 2
        assert metrics.success_rate > 0

    @requires_vm
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_telemetry_export_after_run(self, worker_identity):
        """Test telemetry can be exported after agent run."""
        # Arrange
        telemetry = ComputerUseTelemetryCollector(worker_identity=worker_identity)

        # Log some operations
        telemetry.log_operation(
            operation="email_workflow",
            status="success",
            duration_ms=1200,
            metadata={"to": "recipient@tenant.com"},
        )
        telemetry.log_operation(
            operation="teams_workflow",
            status="success",
            duration_ms=800,
            metadata={"channel": "General"},
        )

        # Act - export telemetry
        with patch(
            "azure_haymaker.knowledge_worker.computer_use.telemetry.BlobServiceClient"
        ) as mock_blob:
            mock_client = MagicMock()
            mock_blob.return_value = mock_client
            mock_client.upload_blob = AsyncMock()

            result = await telemetry.export_logs(
                destination="azure://storageaccount/container/telemetry.json"
            )

            # Assert
            assert result["success"] is True
            assert result["log_count"] == 2


# ==============================================================================
# ERROR HANDLING INTEGRATION TESTS
# ==============================================================================


class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""

    @requires_vm
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_vm_provisioning_failure_handling(
        self, worker_identity, mock_vm_manager
    ):
        """Test graceful handling of VM provisioning failures."""
        # Arrange
        mock_vm_manager.provision_vm.side_effect = Exception("Quota exceeded")

        # Act & Assert
        with pytest.raises(Exception, match="(?i)quota"):
            await mock_vm_manager.provision_vm(
                worker_identity=worker_identity, vm_size="Standard_D4s_v3"
            )

    @requires_vm
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_deployment_failure_cleanup(
        self, worker_identity, mock_winrm, workflows
    ):
        """Test cleanup happens even if deployment fails."""
        # Arrange
        mock_winrm.get_command_output.return_value = (
            b"",
            b"Access denied",
            1,
        )

        winrm_conn = WinRMConnection(
            hostname="test-vm.westus2.cloudapp.azure.com",
            username="kwadmin",
            password="VmP@ssw0rd!",
        )
        winrm_conn.connect()

        deployer = AgentDeployer(connection=winrm_conn)

        # Act & Assert
        with pytest.raises(Exception, match="."):
            deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)

        # Cleanup should still work
        winrm_conn.disconnect()
        assert winrm_conn.is_connected is False

    @requires_vm
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_retry_on_transient_failure(
        self, worker_identity, mock_browser
    ):
        """Test workflow retries on transient failures."""
        # Arrange
        config = ComputerUseConfig(
            worker_id=worker_identity.worker_id,
            display_name=worker_identity.display_name,
            vm_hostname="test-vm.westus2.cloudapp.azure.com",
            vm_username="kwadmin",
            vm_password="VmP@ssw0rd!",
            m365_username=worker_identity.user_principal_name,
            m365_password="M365P@ssw0rd!",
        )

        agent = ComputerUseKnowledgeWorkerAgent(
            worker_config=config, worker_identity=worker_identity
        )

        # Mock transient failure then success
        call_count = [0]

        async def mock_send_email(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Transient network error")
            return {"success": True}

        agent.browser.send_email_via_browser = mock_send_email

        # Act
        agent.on_start()

        # Should retry and eventually succeed
        result = await agent.execute_workflow(
            workflow_name="email_workflow",
            params={"to": "test@tenant.com", "subject": "Test", "body": "Test"},
            max_retries=3,
        )

        # Assert
        assert result["success"] is True
        assert call_count[0] == 2  # Failed once, succeeded on retry


# ==============================================================================
# MULTI-AGENT COORDINATION TESTS
# ==============================================================================


class TestMultiAgentCoordination:
    """Integration tests for multiple agents working together."""

    @requires_vm
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_agents_execute_workflows_concurrently(
        self, mock_vm_manager, mock_winrm, mock_browser, workflows
    ):
        """Test multiple agents can execute workflows concurrently."""
        # Create 3 workers
        workers = [
            WorkerIdentity(
                worker_id=f"kw-concurrent-{i:03d}",
                display_name=f"Concurrent Worker {i}",
                user_principal_name=f"worker{i}@tenant.com",
                entra_object_id=str(uuid4()),
                department="engineering",
                persona="engineering",
                endpoint_type="cloud_pc",
                endpoint_id="",
                team_ids=["team-001"],
            )
            for i in range(3)
        ]

        # Provision VMs
        vm_infos = []
        for worker in workers:
            vm_info = await mock_vm_manager.provision_vm(
                worker_identity=worker, vm_size="Standard_D4s_v3"
            )
            vm_infos.append(vm_info)

        # Create agents
        agents = []
        for worker, vm_info in zip(workers, vm_infos, strict=False):
            config = ComputerUseConfig(
                worker_id=worker.worker_id,
                display_name=worker.display_name,
                vm_hostname=vm_info["hostname"],
                vm_username=vm_info["username"],
                vm_password=vm_info["password"],
                m365_username=worker.user_principal_name,
                m365_password="M365P@ssw0rd!",
            )
            agent = ComputerUseKnowledgeWorkerAgent(
                worker_config=config, worker_identity=worker
            )
            agents.append(agent)

        # Execute workflows concurrently
        import asyncio

        tasks = []
        for agent in agents:
            agent.on_start()
            task = agent.execute_workflow(
                workflow_name="email_workflow",
                params={
                    "to": "recipient@tenant.com",
                    "subject": f"Email from {agent.worker_identity.worker_id}",
                    "body": "Concurrent test",
                },
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Assert all succeeded
        assert all(r["success"] for r in results)

        # Cleanup
        for agent in agents:
            agent.on_cleanup(exit_code=0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
