#!/bin/bash
#
# VM Orchestrator Deployment Script
#
# Orchestrates full VM deployment process including:
# - Pre-deployment validation
# - Infrastructure deployment via GitHub Actions or Azure CLI
# - Post-deployment validation
# - Rollback testing
#
# Usage:
#   ./scripts/deploy_vm_orchestrator.sh --method github-actions --env dev
#   ./scripts/deploy_vm_orchestrator.sh --method azure-cli --env dev
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEPLOYMENT_METHOD="github-actions"
ENVIRONMENT="dev"
RESOURCE_GROUP="haymaker-dev-rg"
DRY_RUN=false
SKIP_VALIDATION=false

# Functions
print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

usage() {
    cat << EOF
VM Orchestrator Deployment Script

Usage: $0 [OPTIONS]

Options:
    --method <github-actions|azure-cli>  Deployment method (default: github-actions)
    --env <dev|staging|prod>             Environment (default: dev)
    --resource-group <name>              Azure resource group (default: haymaker-dev-rg)
    --dry-run                            Validate only, don't deploy
    --skip-validation                    Skip pre-deployment validation (NOT RECOMMENDED)
    --help                               Show this help message

Examples:
    # Deploy via GitHub Actions (recommended)
    $0 --method github-actions --env dev

    # Deploy via Azure CLI (manual)
    $0 --method azure-cli --env dev

    # Dry run (validation only)
    $0 --dry-run

EOF
    exit 0
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check if gh CLI is installed (for GitHub Actions method)
    if [ "$DEPLOYMENT_METHOD" = "github-actions" ]; then
        if ! command -v gh &> /dev/null; then
            print_error "GitHub CLI (gh) not found"
            print_info "Install: https://cli.github.com/"
            exit 1
        fi
        print_success "GitHub CLI found"

        # Check if authenticated
        if ! gh auth status &> /dev/null; then
            print_error "Not authenticated with GitHub"
            print_info "Run: gh auth login"
            exit 1
        fi
        print_success "GitHub authentication verified"
    fi

    # Check if az CLI is installed
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI (az) not found"
        print_info "Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    print_success "Azure CLI found"

    # Check if logged in to Azure
    if ! az account show &> /dev/null; then
        print_error "Not logged in to Azure"
        print_info "Run: az login"
        exit 1
    fi
    print_success "Azure authentication verified"

    # Check if resource group exists
    if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
        print_success "Resource group exists: $RESOURCE_GROUP"
    else
        print_error "Resource group not found: $RESOURCE_GROUP"
        print_info "Create it first: az group create --name $RESOURCE_GROUP --location <region>"
        exit 1
    fi

    # Check if Python is available (for validation scripts)
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        exit 1
    fi
    print_success "Python 3 found"

    echo
}

run_pre_deployment_validation() {
    print_header "Pre-Deployment Validation"

    if [ "$SKIP_VALIDATION" = true ]; then
        print_warning "Skipping pre-deployment validation (NOT RECOMMENDED)"
        echo
        return
    fi

    # Check if validation script exists
    if [ ! -f "scripts/validate_vm_deployment.py" ]; then
        print_error "Validation script not found: scripts/validate_vm_deployment.py"
        exit 1
    fi

    print_info "Running pre-deployment checks..."

    # This will check if we're ready to deploy (e.g., no conflicting resources)
    # For pre-deployment, we expect some checks to fail (VM doesn't exist yet)
    # So we don't exit on failure here
    python3 scripts/validate_vm_deployment.py --resource-group "$RESOURCE_GROUP" || {
        print_warning "Some validation checks failed (expected for new deployment)"
        print_info "Review output above to ensure no conflicts"
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Deployment cancelled by user"
            exit 0
        fi
    }

    echo
}

deploy_via_github_actions() {
    print_header "Deploying via GitHub Actions"

    print_info "Triggering workflow: deploy-vm-orchestrator.yml"

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY-RUN: Would trigger GitHub Actions workflow"
        print_info "Command: gh workflow run deploy-vm-orchestrator.yml"
        return
    fi

    # Trigger the workflow
    if gh workflow run deploy-vm-orchestrator.yml; then
        print_success "Workflow triggered successfully"

        print_info "Monitoring workflow execution..."
        print_info "View in browser: gh workflow view deploy-vm-orchestrator.yml --web"

        # Wait a moment for workflow to start
        sleep 5

        # Get the latest run
        RUN_ID=$(gh run list --workflow=deploy-vm-orchestrator.yml --limit 1 --json databaseId --jq '.[0].databaseId')

        if [ -n "$RUN_ID" ]; then
            print_info "Workflow run ID: $RUN_ID"
            print_info "Watching workflow progress..."

            # Watch the workflow (this will block until complete)
            gh run watch "$RUN_ID" || {
                print_error "Workflow failed or was cancelled"
                print_info "View logs: gh run view $RUN_ID"
                exit 1
            }

            print_success "Workflow completed successfully"
        else
            print_warning "Could not get workflow run ID"
            print_info "Check workflow status: gh workflow view deploy-vm-orchestrator.yml"
        fi
    else
        print_error "Failed to trigger workflow"
        exit 1
    fi

    echo
}

deploy_via_azure_cli() {
    print_header "Deploying via Azure CLI"

    print_info "Deploying Bicep template: infra/bicep/main-vm.bicep"

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY-RUN: Would deploy Bicep template"
        print_info "Command: az deployment group create ..."
        return
    fi

    # Check if parameters file exists
    PARAMS_FILE="infra/bicep/parameters/${ENVIRONMENT}.json"
    if [ ! -f "$PARAMS_FILE" ]; then
        print_error "Parameters file not found: $PARAMS_FILE"
        print_info "Create parameters file or use inline parameters"
        exit 1
    fi

    # Generate deployment name
    DEPLOYMENT_NAME="vm-deployment-$(date +%s)"

    print_info "Deployment name: $DEPLOYMENT_NAME"
    print_info "Parameters file: $PARAMS_FILE"

    # Deploy
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file infra/bicep/main-vm.bicep \
        --parameters "@$PARAMS_FILE" \
        --name "$DEPLOYMENT_NAME" \
        --output table

    if [ $? -eq 0 ]; then
        print_success "Deployment completed successfully"

        # Get outputs
        print_info "Retrieving deployment outputs..."
        az deployment group show \
            --resource-group "$RESOURCE_GROUP" \
            --name "$DEPLOYMENT_NAME" \
            --query properties.outputs \
            --output table
    else
        print_error "Deployment failed"
        exit 1
    fi

    echo
}

run_post_deployment_validation() {
    print_header "Post-Deployment Validation"

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY-RUN: Would run post-deployment validation"
        return
    fi

    print_info "Waiting 30 seconds for resources to stabilize..."
    sleep 30

    print_info "Running post-deployment validation..."

    # Run validation script
    python3 scripts/validate_vm_deployment.py --resource-group "$RESOURCE_GROUP"

    if [ $? -eq 0 ]; then
        print_success "Post-deployment validation passed"
    else
        print_error "Post-deployment validation failed"
        print_info "Review errors above and run rollback if necessary"
        exit 1
    fi

    echo
}

test_rollback_procedures() {
    print_header "Testing Rollback Procedures"

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY-RUN: Would test rollback procedures"
        return
    fi

    print_info "Running rollback tests (dry-run mode)..."

    # Run rollback test script
    python3 scripts/test_vm_rollback.py --resource-group "$RESOURCE_GROUP" --dry-run

    if [ $? -eq 0 ]; then
        print_success "Rollback tests passed"
        print_info "Rollback procedures are available if needed"
    else
        print_warning "Rollback tests had issues"
        print_info "Review test output above"
    fi

    echo
}

print_next_steps() {
    print_header "Next Steps"

    cat << EOF
✅ Deployment Complete!

Next steps:
1. SSH into VM and setup orchestrator service
   $(az vm show --resource-group $RESOURCE_GROUP --query "[?contains(name, 'haymaker')].{name:name, ip:publicIps}" -o table)

2. Configure orchestrator systemd service
   See: docs/VM_ORCHESTRATOR_MIGRATION_GUIDE.md

3. Test orchestrator with real workloads
   Monitor memory usage: ssh <vm-ip> "free -h"

4. Monitor for 24-48 hours before decommissioning Function Apps

5. Update documentation with actual deployment outputs

For rollback instructions, see: docs/VM_ORCHESTRATOR_MIGRATION_GUIDE.md#rollback-procedure
EOF

    echo
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --method)
            DEPLOYMENT_METHOD="$2"
            shift 2
            ;;
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Main execution
main() {
    print_header "Azure HayMaker VM Orchestrator Deployment"

    print_info "Deployment Method: $DEPLOYMENT_METHOD"
    print_info "Environment: $ENVIRONMENT"
    print_info "Resource Group: $RESOURCE_GROUP"
    print_info "Dry Run: $DRY_RUN"
    echo

    # Execute deployment pipeline
    check_prerequisites
    run_pre_deployment_validation

    case $DEPLOYMENT_METHOD in
        github-actions)
            deploy_via_github_actions
            ;;
        azure-cli)
            deploy_via_azure_cli
            ;;
        *)
            print_error "Invalid deployment method: $DEPLOYMENT_METHOD"
            print_info "Valid methods: github-actions, azure-cli"
            exit 1
            ;;
    esac

    run_post_deployment_validation
    test_rollback_procedures
    print_next_steps

    print_success "Deployment pipeline complete!"
}

# Run main function
main
