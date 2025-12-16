# Getting Started: Local Development Mode with Mocked Azure (Issue #130)

**Your complete guide to implementing Issue #130**

**Priority**: P2-Medium | **Effort**: 4 weeks | **ROI**: 200%

---

## What You're Building

Create a complete local development environment with mocked Azure services so developers can build and test without cloud costs, internet connection, or complex setup.

**Why It Matters**: New developers currently spend days setting up Azure resources. This cuts it to minutes.

**Business Value**: Reduces onboarding time by 80%, enables offline development, saves $5K+/month in dev/test costs.

---

## Before You Start (20 minutes)

### 1. Understand Current Architecture

```bash
# Review current Azure client usage
grep -r "from azure" src/ | head -20
grep -r "AsyncCloudClient\|ContainerAppClient" src/ | head -10
```

### 2. Check Dependencies

```bash
# Review what we need to mock
cat pyproject.toml | grep -A 10 "dependencies"
```

### 3. Understand Dependency Injection

```bash
# See if project already uses dependency injection
grep -r "Depends\|inject" src/ | head -10
```

---

## Phase 1: Create Mock Azure Client Base (Days 1-3, ~15 hours)

### Create Directory Structure

```bash
mkdir -p src/azure_haymaker/mocks
mkdir -p src/azure_haymaker/mocks/azure
touch src/azure_haymaker/mocks/__init__.py
touch src/azure_haymaker/mocks/base.py
touch src/azure_haymaker/mocks/azure/__init__.py
touch src/azure_haymaker/mocks/azure/container_apps.py
touch src/azure_haymaker/mocks/azure/key_vault.py
touch src/azure_haymaker/mocks/azure/service_bus.py
touch src/azure_haymaker/mocks/azure/graph_api.py
```

### Create Branch

```bash
git checkout main
git pull origin main
git checkout -b feat/issue-130-local-dev-mode
```

### Implement Mock Base Classes

**File**: `src/azure_haymaker/mocks/base.py`

```python
from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime
import uuid

class MockClient(ABC):
    """Base class for all mock Azure clients."""

    def __init__(self, environment: str = "local"):
        self.environment = environment
        self.call_count = 0
        self.call_history = []

    def _record_call(self, method: str, args: dict, result: Any = None):
        """Track all API calls for testing/debugging."""
        self.call_history.append({
            "timestamp": datetime.now(),
            "method": method,
            "args": args,
            "result": result
        })
        self.call_count += 1

    @abstractmethod
    async def health_check(self) -> dict:
        """Return service health status."""
        pass
```

### Implement Mock Container Apps Client

**File**: `src/azure_haymaker/mocks/azure/container_apps.py`

```python
import asyncio
import uuid
from datetime import datetime

class MockContainerAppClient:
    """Mocks Azure Container Apps API."""

    def __init__(self):
        self.apps = {}  # id -> app_data
        self.deployments = {}  # id -> deployment_data

    async def create_container_app(
        self,
        resource_group: str,
        name: str,
        image: str,
        cpu: str = "0.25",
        memory: str = "0.5Gi",
        **kwargs
    ) -> dict:
        """Mock creating a container app."""

        app_id = str(uuid.uuid4())
        app = {
            "id": app_id,
            "name": name,
            "resource_group": resource_group,
            "image": image,
            "cpu": cpu,
            "memory": memory,
            "status": "Provisioned",
            "created_at": datetime.now().isoformat(),
            "properties": {
                "provisioned": True,
                "outboundIpAddresses": ["203.0.113.1"],
                "fqdn": f"{name}.azurecontainerapps.io"
            }
        }

        self.apps[app_id] = app
        return app

    async def get_container_app(self, resource_group: str, name: str) -> dict:
        """Mock getting container app details."""
        # Find by name
        for app_id, app in self.apps.items():
            if app["name"] == name and app["resource_group"] == resource_group:
                return app
        raise Exception(f"Container app {name} not found")

    async def create_deployment(
        self,
        app_id: str,
        image: str,
        cpu: str = "0.25",
        memory: str = "0.5Gi"
    ) -> dict:
        """Mock creating app deployment."""

        deployment_id = str(uuid.uuid4())
        deployment = {
            "id": deployment_id,
            "app_id": app_id,
            "image": image,
            "status": "Running",
            "created_at": datetime.now().isoformat(),
            "replicas": 1
        }

        self.deployments[deployment_id] = deployment
        return deployment

    async def get_app_logs(
        self,
        app_id: str,
        replica: str | None = None,
        tail: int = 100
    ) -> list[str]:
        """Mock retrieving app logs."""

        # Return mock logs
        return [
            f"[2025-11-30T{i:02d}:00:00Z] Agent initialized",
            f"[2025-11-30T{i:02d}:00:01Z] Starting knowledge worker",
            f"[2025-11-30T{i:02d}:00:02Z] Connected to service bus"
        ]

    async def health_check(self) -> dict:
        return {"status": "healthy", "type": "container_apps"}
```

### Implement Mock Key Vault Client

**File**: `src/azure_haymaker/mocks/azure/key_vault.py`

```python
class MockKeyVaultClient:
    """Mocks Azure Key Vault API."""

    def __init__(self):
        self.secrets = {}  # name -> value
        self._init_default_secrets()

    def _init_default_secrets(self):
        """Initialize with reasonable defaults for local dev."""
        self.secrets = {
            "AzureAdTenantId": "00000000-0000-0000-0000-000000000000",
            "GraphApiToken": "mock-token-12345",
            "ServiceBusConnectionString": "Endpoint=sb://localhost:5672;...",
            "StorageAccountKey": "DefaultEndpointsProtocol=https;..."
        }

    async def get_secret(self, name: str) -> str:
        """Get secret value."""
        if name not in self.secrets:
            raise Exception(f"Secret '{name}' not found")
        return self.secrets[name]

    async def set_secret(self, name: str, value: str) -> dict:
        """Set secret value."""
        self.secrets[name] = value
        return {"name": name, "value": value}

    async def health_check(self) -> dict:
        return {"status": "healthy", "type": "key_vault"}
```

### Implement Mock Graph API Client

**File**: `src/azure_haymaker/mocks/azure/graph_api.py`

```python
import uuid
from datetime import datetime, timedelta

class MockGraphApiClient:
    """Mocks Microsoft Graph API."""

    def __init__(self):
        self.users = self._create_mock_users()
        self.mailboxes = {}

    def _create_mock_users(self) -> dict:
        """Create mock tenant users."""
        return {
            "user1@example.com": {
                "id": str(uuid.uuid4()),
                "displayName": "Test User 1",
                "mail": "user1@example.com"
            },
            "user2@example.com": {
                "id": str(uuid.uuid4()),
                "displayName": "Test User 2",
                "mail": "user2@example.com"
            }
        }

    async def get_users(self, filter_query: str | None = None) -> list[dict]:
        """Get users from tenant."""
        users = list(self.users.values())
        if filter_query:
            # Simple mock filtering
            pass
        return users

    async def send_email(
        self,
        from_user: str,
        to_user: str,
        subject: str,
        body: str
    ) -> dict:
        """Mock sending email."""
        return {
            "id": str(uuid.uuid4()),
            "status": "sent",
            "from": from_user,
            "to": to_user,
            "subject": subject,
            "sent_at": datetime.now().isoformat()
        }

    async def health_check(self) -> dict:
        return {"status": "healthy", "type": "graph_api"}
```

---

## Phase 2: Create Dependency Injection Layer (Days 4-5, ~12 hours)

### Create Client Factory

**File**: `src/azure_haymaker/clients/factory.py`

```python
import os
from typing import Literal

class ClientFactory:
    """Factory for creating real or mock Azure clients based on environment."""

    @staticmethod
    def create_container_apps_client(mode: str = None):
        """Create container apps client."""
        mode = mode or os.getenv("AZURE_CLIENT_MODE", "real")

        if mode == "mock":
            from azure_haymaker.mocks.azure.container_apps import MockContainerAppClient
            return MockContainerAppClient()
        else:
            from azure.containerapp import ContainerAppClient
            return ContainerAppClient()

    @staticmethod
    def create_key_vault_client(mode: str = None):
        """Create key vault client."""
        mode = mode or os.getenv("AZURE_CLIENT_MODE", "real")

        if mode == "mock":
            from azure_haymaker.mocks.azure.key_vault import MockKeyVaultClient
            return MockKeyVaultClient()
        else:
            from azure.keyvault.secrets import SecretClient
            return SecretClient()

    @staticmethod
    def create_graph_api_client(mode: str = None):
        """Create Graph API client."""
        mode = mode or os.getenv("AZURE_CLIENT_MODE", "real")

        if mode == "mock":
            from azure_haymaker.mocks.azure.graph_api import MockGraphApiClient
            return MockGraphApiClient()
        else:
            from msgraph.core import GraphClient
            return GraphClient()
```

### Update Orchestrator to Use Factory

**File**: `src/orchestrator_server.py`

```python
import os
from azure_haymaker.clients.factory import ClientFactory

# Determine mode from environment
AZURE_CLIENT_MODE = os.getenv("AZURE_CLIENT_MODE", "real")

# Create clients
container_apps_client = ClientFactory.create_container_apps_client(AZURE_CLIENT_MODE)
key_vault_client = ClientFactory.create_key_vault_client(AZURE_CLIENT_MODE)
graph_api_client = ClientFactory.create_graph_api_client(AZURE_CLIENT_MODE)
```

---

## Phase 3: Create Test Data Generators (Days 6-8, ~15 hours)

### Create Scenario Test Data

**File**: `src/azure_haymaker/mocks/test_data.py`

```python
import random
from datetime import datetime, timedelta

class TestDataGenerator:
    """Generates realistic test data for scenarios."""

    @staticmethod
    def generate_users(count: int = 5) -> list[dict]:
        """Generate mock users."""
        users = []
        for i in range(count):
            users.append({
                "id": f"user-{i}",
                "displayName": f"Test User {i}",
                "mail": f"user{i}@example.com",
                "department": random.choice(["Engineering", "Sales", "Marketing"])
            })
        return users

    @staticmethod
    def generate_events(scenario: str, count: int = 100) -> list[dict]:
        """Generate mock telemetry events for scenario."""
        events = []
        base_time = datetime.now()

        for i in range(count):
            events.append({
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "event_type": f"{scenario}_event",
                "severity": random.choice(["info", "warning", "error"]),
                "data": {
                    "user": f"user{random.randint(1, 5)}",
                    "action": random.choice(["read", "write", "delete"])
                }
            })
        return events

    @staticmethod
    def generate_cost_data(scenarios: list[str]) -> dict:
        """Generate mock cost data."""
        costs = {}
        for scenario in scenarios:
            costs[scenario] = {
                "estimated_usd": round(random.uniform(1, 50), 2),
                "actual_usd": round(random.uniform(0.5, 60), 2)
            }
        return costs
```

---

## Phase 4: Create Docker Compose for Local Environment (Days 9-10, ~12 hours)

### Create Docker Compose File

**File**: `docker-compose.local.yml`

```yaml
version: "3.8"

services:
  orchestrator:
    build:
      context: .
      dockerfile: Dockerfile.local
    ports:
      - "8000:8000"
    environment:
      AZURE_CLIENT_MODE: mock
      LOCAL_DEV_MODE: "true"
      LOG_LEVEL: DEBUG
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
    command: uvicorn src.orchestrator_server:app --host 0.0.0.0 --reload

  sqlite:
    image: nouchka/sqlite3:latest
    volumes:
      - ./data/local.db:/root/mydb.db
    ports:
      - "5432:5432"

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - ./data/minio:/data
    command: minio server /data --console-address ":9001"
```

### Create Local Dockerfile

**File**: `Dockerfile.local`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

# Copy source
COPY src /app/src
COPY tests /app/tests

# Set local dev environment
ENV AZURE_CLIENT_MODE=mock
ENV LOCAL_DEV_MODE=true

CMD ["uvicorn", "src.orchestrator_server:app", "--host", "0.0.0.0", "--reload"]
```

---

## Phase 5: Create CLI for Local Development (Days 11-13, ~15 hours)

### Create Local Dev CLI

**File**: `src/azure_haymaker/cli/local_dev.py`

```python
import click
import subprocess
import os
from pathlib import Path

@click.group()
def local_dev():
    """Local development commands."""
    pass

@local_dev.command()
def setup():
    """Set up local development environment."""
    click.echo("Setting up local dev environment...")

    # Create data directories
    Path("./data").mkdir(exist_ok=True)
    Path("./data/minio").mkdir(exist_ok=True)

    # Copy example env
    if not Path(".env.local").exists():
        with open(".env.local", "w") as f:
            f.write("AZURE_CLIENT_MODE=mock\n")
            f.write("LOCAL_DEV_MODE=true\n")
            f.write("LOG_LEVEL=DEBUG\n")

    click.echo("✓ Setup complete. Run 'python -m azure_haymaker.cli start'")

@local_dev.command()
def start():
    """Start local development environment."""
    click.echo("Starting local dev environment...")

    # Load .env.local
    if Path(".env.local").exists():
        with open(".env.local") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    # Start docker compose
    subprocess.run(["docker-compose", "-f", "docker-compose.local.yml", "up", "-d"])

    click.echo("✓ Local environment started")
    click.echo("  Orchestrator: http://localhost:8000")
    click.echo("  API Docs: http://localhost:8000/docs")
    click.echo("  MinIO: http://localhost:9001")

@local_dev.command()
def test():
    """Run tests with mock clients."""
    click.echo("Running tests with mock Azure clients...")

    os.environ["AZURE_CLIENT_MODE"] = "mock"
    subprocess.run(["pytest", "tests/", "-v", "--tb=short"])

@local_dev.command()
def stop():
    """Stop local development environment."""
    subprocess.run(["docker-compose", "-f", "docker-compose.local.yml", "down"])
    click.echo("✓ Local environment stopped")
```

---

## Phase 6: Create Example .env and Documentation (Days 14-15, ~10 hours)

### Create .env.local.example

**File**: `.env.local.example`

```bash
# Local Development Configuration

# Use mock Azure clients (don't require real Azure account)
AZURE_CLIENT_MODE=mock

# Enable local dev mode
LOCAL_DEV_MODE=true

# Logging
LOG_LEVEL=DEBUG

# Database (SQLite)
DATABASE_URL=sqlite:///./data/local.db

# Storage (MinIO)
MINIO_URL=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# No need for real Azure credentials in local mode
# But these can be empty strings instead of erroring
AZURE_TENANT_ID=mock-tenant-id
AZURE_SUBSCRIPTION_ID=mock-subscription-id
```

### Create Local Development Guide

**File**: `docs/LOCAL_DEVELOPMENT.md`

```markdown
# Local Development Setup

## Quick Start (5 minutes)

```bash
# 1. Set up local environment
python -m azure_haymaker.cli local-dev setup

# 2. Start local services
python -m azure_haymaker.cli local-dev start

# 3. Open API docs
open http://localhost:8000/docs
```

## What Gets Mocked

- Azure Container Apps (deployment, logs)
- Azure Key Vault (secrets)
- Microsoft Graph API (users, email)
- Azure Service Bus (queues, topics)
- Azure Storage (blobs)

## Limitations vs Cloud

- No real resource costs
- Mocks return fixed test data
- Performance not representative
- No multi-tenant isolation

## Running Tests

```bash
python -m azure_haymaker.cli local-dev test
```

## Switching to Real Azure

```bash
# Set environment variable
export AZURE_CLIENT_MODE=real

# Run orchestrator
uvicorn src.orchestrator_server:app
```
```

---

## Testing

### Unit Tests for Mock Clients

```bash
mkdir -p tests/unit/mocks
touch tests/unit/mocks/test_mock_container_apps.py
touch tests/unit/mocks/test_mock_key_vault.py
```

### Example Test

```python
import pytest
from azure_haymaker.mocks.azure.container_apps import MockContainerAppClient

@pytest.mark.asyncio
async def test_mock_container_app_creation():
    """Test creating mock container app."""
    client = MockContainerAppClient()

    app = await client.create_container_app(
        resource_group="test-rg",
        name="test-app",
        image="ubuntu:20.04"
    )

    assert app["name"] == "test-app"
    assert app["status"] == "Provisioned"
    assert "fqdn" in app["properties"]

@pytest.mark.asyncio
async def test_mock_container_app_retrieval():
    """Test retrieving created app."""
    client = MockContainerAppClient()

    created = await client.create_container_app(
        resource_group="test-rg",
        name="test-app-2",
        image="ubuntu:20.04"
    )

    retrieved = await client.get_container_app("test-rg", "test-app-2")
    assert retrieved["id"] == created["id"]
```

---

## Success Criteria

- [ ] All mock Azure clients implemented
- [ ] ClientFactory working (real/mock switching)
- [ ] Docker Compose file running locally
- [ ] CLI commands: setup, start, stop, test
- [ ] .env.local example created
- [ ] Test data generators working
- [ ] New developers can set up in <10 minutes
- [ ] Tests pass with mock clients
- [ ] Local mode doesn't require Azure credentials
- [ ] Documentation updated

---

## Estimated Timeline

**Optimistic**: 3 weeks
**Realistic**: 4 weeks
**Pessimistic**: 5 weeks

---

**Issue**: #130
**Related**: #131 (GitHub Actions), #133 (Testing Framework)

💻 **Ready to build local dev? Follow Phase 1 above!**
