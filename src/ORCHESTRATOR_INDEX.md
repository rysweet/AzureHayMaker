# Azure HayMaker FastAPI Orchestrator - Complete Documentation Index

**A SIMPLE orchestrator that WORKS - No Azure Functions, No Durable Functions**

## Quick Navigation

### 🚀 Getting Started
- **[ORCHESTRATOR_QUICKSTART.md](ORCHESTRATOR_QUICKSTART.md)** - Get running in 5 minutes
- **[ORCHESTRATOR_SUMMARY.md](ORCHESTRATOR_SUMMARY.md)** - What we built and why

### 📚 Documentation
- **[ORCHESTRATOR_README.md](ORCHESTRATOR_README.md)** - Complete documentation
- **[DEPLOY_ORCHESTRATOR.md](DEPLOY_ORCHESTRATOR.md)** - Azure deployment guide
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Migrate from Azure Functions

### 💻 Code Files
- **[orchestrator_server.py](orchestrator_server.py)** - Main FastAPI application (350 lines)
- **[Dockerfile.orchestrator](Dockerfile.orchestrator)** - Docker image definition
- **[docker-compose.orchestrator.yml](docker-compose.orchestrator.yml)** - Docker Compose setup
- **[requirements-orchestrator.txt](requirements-orchestrator.txt)** - Python dependencies

### 🔧 Scripts
- **[run_orchestrator.sh](run_orchestrator.sh)** - Quick start script
- **[test_orchestrator.sh](test_orchestrator.sh)** - Test script

### ⚙️ Configuration
- **[.env.orchestrator.example](.env.orchestrator.example)** - Environment template
- **[.github-workflows-orchestrator.yml](.github-workflows-orchestrator.yml)** - CI/CD pipeline

## Documentation by Purpose

### I Want to...

#### Run it Locally
1. Read: [ORCHESTRATOR_QUICKSTART.md](ORCHESTRATOR_QUICKSTART.md) - "Local Testing" section
2. Run: `./run_orchestrator.sh`
3. Test: `./test_orchestrator.sh`

#### Deploy to Azure
1. Read: [DEPLOY_ORCHESTRATOR.md](DEPLOY_ORCHESTRATOR.md)
2. Build: `az acr build ...`
3. Deploy: `az containerapp create ...`

#### Understand the Architecture
1. Read: [ORCHESTRATOR_SUMMARY.md](ORCHESTRATOR_SUMMARY.md) - "Architecture Comparison" section
2. Read: [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) - "Architecture Comparison" section
3. Review: [orchestrator_server.py](orchestrator_server.py) - Code is simple and readable

#### Migrate from Azure Functions
1. Read: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
2. Follow: Step-by-step migration process
3. Test: Verify feature parity

#### Customize the Orchestrator
1. Read: [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) - "Development" section
2. Edit: [orchestrator_server.py](orchestrator_server.py)
3. Test: `./run_orchestrator.sh` and `./test_orchestrator.sh`

#### Troubleshoot Issues
1. Read: [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) - "Troubleshooting" section
2. Read: [DEPLOY_ORCHESTRATOR.md](DEPLOY_ORCHESTRATOR.md) - "Troubleshooting" section
3. Read: [ORCHESTRATOR_QUICKSTART.md](ORCHESTRATOR_QUICKSTART.md) - "Troubleshooting" section

#### Set Up CI/CD
1. Read: [.github-workflows-orchestrator.yml](.github-workflows-orchestrator.yml)
2. Copy to: `.github/workflows/orchestrator.yml`
3. Configure: GitHub secrets

## API Reference

| Endpoint | Method | Description | Documentation |
|----------|--------|-------------|---------------|
| `/` | GET | Health check | [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) |
| `/api/metrics` | GET | Execution metrics | [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) |
| `/api/executions` | GET | List executions | [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) |
| `/api/executions/{id}` | GET | Get execution | [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) |
| `/api/execute` | POST | Trigger execution | [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) |
| `/api/validate` | POST | Validate environment | [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) |
| `/api/scenarios` | GET | List scenarios | [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) |

## File Organization

```
src/
├── orchestrator_server.py              # Main FastAPI app
├── Dockerfile.orchestrator             # Docker image
├── docker-compose.orchestrator.yml     # Docker Compose
├── requirements-orchestrator.txt       # Dependencies
├── .env.orchestrator.example           # Environment template
├── .github-workflows-orchestrator.yml  # CI/CD pipeline
├── run_orchestrator.sh                 # Quick start script
├── test_orchestrator.sh                # Test script
└── Documentation:
    ├── ORCHESTRATOR_INDEX.md           # This file
    ├── ORCHESTRATOR_QUICKSTART.md      # 5-minute guide
    ├── ORCHESTRATOR_SUMMARY.md         # What we built
    ├── ORCHESTRATOR_README.md          # Complete docs
    ├── DEPLOY_ORCHESTRATOR.md          # Azure deployment
    └── MIGRATION_GUIDE.md              # Migrate from Functions
```

## Key Features

### Simple Architecture
- FastAPI REST API
- APScheduler for cron jobs
- No Azure Functions
- No Durable Functions

### Works Everywhere
- Local development (Docker)
- Docker Compose
- Azure Container Apps
- Kubernetes
- Any VM with Docker

### Production Ready
- Health checks
- Metrics endpoint
- Structured logging
- Error handling
- Managed identity support
- Key Vault integration

## Quick Commands

### Local Development
```bash
# Start orchestrator
./run_orchestrator.sh

# Test endpoints
./test_orchestrator.sh

# View logs
docker logs -f azure-haymaker-orchestrator

# Stop orchestrator
docker stop azure-haymaker-orchestrator
```

### Docker Compose
```bash
# Start
docker-compose -f docker-compose.orchestrator.yml up -d

# Logs
docker-compose -f docker-compose.orchestrator.yml logs -f

# Stop
docker-compose -f docker-compose.orchestrator.yml down
```

### Azure Deployment
```bash
# Build and push
az acr build --registry yourregistry --image azure-haymaker-orchestrator:latest --file Dockerfile.orchestrator .

# Create Container App
az containerapp create --name haymaker-orchestrator ... # See DEPLOY_ORCHESTRATOR.md

# View logs
az containerapp logs show --name haymaker-orchestrator --resource-group azure-haymaker-rg --follow
```

## Documentation Status

| Document | Status | Purpose |
|----------|--------|---------|
| ORCHESTRATOR_INDEX.md | ✅ Complete | Navigation hub |
| ORCHESTRATOR_QUICKSTART.md | ✅ Complete | 5-minute guide |
| ORCHESTRATOR_SUMMARY.md | ✅ Complete | Overview |
| ORCHESTRATOR_README.md | ✅ Complete | Full documentation |
| DEPLOY_ORCHESTRATOR.md | ✅ Complete | Azure deployment |
| MIGRATION_GUIDE.md | ✅ Complete | Azure Functions migration |
| orchestrator_server.py | ✅ Complete | Main application |
| Dockerfile.orchestrator | ✅ Complete | Docker image |
| docker-compose.orchestrator.yml | ✅ Complete | Docker Compose |
| requirements-orchestrator.txt | ✅ Complete | Dependencies |
| run_orchestrator.sh | ✅ Complete | Quick start |
| test_orchestrator.sh | ✅ Complete | Testing |
| .env.orchestrator.example | ✅ Complete | Environment template |
| .github-workflows-orchestrator.yml | ✅ Complete | CI/CD pipeline |

## Support Resources

### Questions?
1. Check [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) - FAQ and troubleshooting
2. Check [ORCHESTRATOR_QUICKSTART.md](ORCHESTRATOR_QUICKSTART.md) - Common issues
3. Check logs: `docker logs azure-haymaker-orchestrator`

### Issues?
1. Read [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) - "Troubleshooting" section
2. Read [DEPLOY_ORCHESTRATOR.md](DEPLOY_ORCHESTRATOR.md) - "Troubleshooting" section
3. Check container health: `curl http://localhost:8080/`

### Need to Customize?
1. Read [ORCHESTRATOR_README.md](ORCHESTRATOR_README.md) - "Development" section
2. Edit [orchestrator_server.py](orchestrator_server.py)
3. Test locally before deploying

## Next Steps

1. **Read**: [ORCHESTRATOR_QUICKSTART.md](ORCHESTRATOR_QUICKSTART.md)
2. **Run**: `./run_orchestrator.sh`
3. **Test**: `./test_orchestrator.sh`
4. **Deploy**: Follow [DEPLOY_ORCHESTRATOR.md](DEPLOY_ORCHESTRATOR.md)

## Success Criteria

The orchestrator is working correctly when:
- ✅ Health check returns 200
- ✅ Metrics endpoint shows data
- ✅ Scenarios endpoint lists scenarios
- ✅ Validation passes
- ✅ Manual execution triggers successfully
- ✅ Scheduled executions run 4x daily
- ✅ All 6 orchestration phases complete
- ✅ No errors in logs

## Version History

- **v1.0** (2024-11-22): Initial FastAPI orchestrator
  - Replaced Azure Functions + Durable Functions
  - 350 lines of simple, working code
  - Full feature parity with original
  - Runs anywhere Docker runs

## License

Same as Azure HayMaker project.

---

**Start here**: [ORCHESTRATOR_QUICKSTART.md](ORCHESTRATOR_QUICKSTART.md)
