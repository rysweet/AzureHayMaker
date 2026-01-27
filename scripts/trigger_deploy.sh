#!/bin/bash
#
# Trigger Developer Stack Deployment via GitHub Actions (OIDC)
#
# Reads configuration from local .env file and triggers the
# deploy-dev-stack.yml workflow using OIDC authentication.
#
# NO SECRETS NEEDED! Azure trusts GitHub Actions tokens directly.
# Just provide tenant/subscription/client IDs from your .env file.
#
# Usage:
#   ./scripts/trigger_deploy.sh                 # Use defaults from .env
#   ./scripts/trigger_deploy.sh --name mystack  # Custom naming prefix
#   ./scripts/trigger_deploy.sh --watch         # Watch workflow progress
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - .env file with Azure IDs (no secrets needed!)
#   - OIDC federated credential configured in Azure AD
#

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Defaults
ENV_FILE=".env"
NAMING_PREFIX=""
ENVIRONMENT="dev"
LOCATION="westus2"
SIMULATION_SIZE="small"
SKIP_IMAGE_BUILD=false
WATCH=false
USE_SECRETS=false

print_header() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
}

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

usage() {
    cat << EOF
Trigger Developer Stack Deployment (OIDC - No Secrets!)

Reads your local .env file and triggers the GitHub Actions workflow
to deploy your own isolated Azure HayMaker stack.

OIDC Authentication: No secrets needed! Just provide:
  - AZURE_TENANT_ID
  - AZURE_SUBSCRIPTION_ID  
  - AZURE_CLIENT_ID (Service Principal with OIDC federated credential)

Usage: $0 [OPTIONS]

Options:
    --env-file <path>       Path to .env file (default: .env)
    --name <prefix>         Naming prefix for resources (default: \$USER)
    --env <environment>     Environment: dev, staging, prod (default: dev)
    --location <region>     Azure region (default: westus2)
    --size <size>           Simulation size: small, medium, large (default: small)
    --skip-build            Skip Docker image build
    --watch                 Watch workflow progress after triggering
    --use-secrets           Don't pass credentials (use repo secrets instead)
    --help                  Show this help

Examples:
    # Deploy with your username as prefix
    $0

    # Deploy with custom prefix and watch progress
    $0 --name mystack --watch

    # Use repository secrets instead of .env credentials
    $0 --use-secrets --name mystack

EOF
    exit 0
}

load_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found: $ENV_FILE"
        print_info "Copy .env.example to .env and configure your credentials"
        exit 1
    fi

    # Export variables from .env file
    set -a
    source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
    set +a

    # Validate required variables
    local required_vars=(
        "AZURE_TENANT_ID"
        "AZURE_SUBSCRIPTION_ID"
        "AZURE_CLIENT_ID"
    )

    local missing=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing+=("$var")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        print_error "Missing required environment variables in $ENV_FILE:"
        for var in "${missing[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi

    # Use SIMULATION_SIZE from .env if set
    if [ -n "${SIMULATION_SIZE:-}" ]; then
        SIMULATION_SIZE="$SIMULATION_SIZE"
    fi
}

check_prerequisites() {
    # Check GitHub CLI
    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI (gh) not found"
        print_info "Install: https://cli.github.com/"
        exit 1
    fi

    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        print_error "Not authenticated with GitHub"
        print_info "Run: gh auth login"
        exit 1
    fi

    # Check we're in a git repo
    if ! git rev-parse --git-dir &> /dev/null; then
        print_error "Not in a git repository"
        exit 1
    fi
}

trigger_workflow() {
    print_header "🏴‍☠️ Triggering Developer Stack Deployment"

    # Set naming prefix
    if [ -z "$NAMING_PREFIX" ]; then
        NAMING_PREFIX="${USER:-developer}"
    fi

    print_info "Configuration:"
    echo "  Naming Prefix: $NAMING_PREFIX"
    echo "  Environment: $ENVIRONMENT"
    echo "  Location: $LOCATION"
    echo "  Simulation Size: $SIMULATION_SIZE"
    echo "  Skip Image Build: $SKIP_IMAGE_BUILD"
    echo ""
    
    if [ "$USE_SECRETS" = true ]; then
        echo "  Using repository secrets for Azure credentials"
    else
        echo "  Azure Tenant: $AZURE_TENANT_ID"
        echo "  Azure Subscription: $AZURE_SUBSCRIPTION_ID"
        echo "  Azure Client ID: $AZURE_CLIENT_ID"
        echo "  (OIDC - no secrets needed!)"
    fi
    echo ""

    # Build workflow arguments
    local args=(
        -f naming_prefix="$NAMING_PREFIX"
        -f environment="$ENVIRONMENT"
        -f location="$LOCATION"
        -f simulation_size="$SIMULATION_SIZE"
        -f skip_image_build="$SKIP_IMAGE_BUILD"
    )

    # Add Azure credentials if not using repo secrets
    if [ "$USE_SECRETS" = false ]; then
        args+=(
            -f azure_tenant_id="$AZURE_TENANT_ID"
            -f azure_subscription_id="$AZURE_SUBSCRIPTION_ID"
            -f azure_client_id="$AZURE_CLIENT_ID"
        )
    fi

    # Trigger the workflow
    print_info "Triggering workflow: deploy-dev-stack.yml"

    gh workflow run deploy-dev-stack.yml "${args[@]}"

    print_success "Workflow triggered!"
    echo ""

    # Get the run ID
    sleep 3
    RUN_ID=$(gh run list --workflow=deploy-dev-stack.yml --limit 1 --json databaseId --jq '.[0].databaseId')

    if [ -n "$RUN_ID" ]; then
        print_info "Workflow Run ID: $RUN_ID"
        print_info "View in browser: gh run view $RUN_ID --web"
        print_info "Watch progress: gh run watch $RUN_ID"
        echo ""

        if [ "$WATCH" = true ]; then
            print_info "Watching workflow progress..."
            gh run watch "$RUN_ID"
        fi
    fi

    # Print expected resources
    echo ""
    print_header "Expected Resources"
    echo ""
    echo "Resource Group: haymaker-${NAMING_PREFIX}-${ENVIRONMENT}-rg"
    echo "ACR: haymaker${NAMING_PREFIX}${ENVIRONMENT}acr"
    echo "Orchestrator: haymaker-${NAMING_PREFIX}-orch"
    echo ""
    echo "After deployment completes, test with:"
    echo "  curl https://haymaker-${NAMING_PREFIX}-orch.<region>.azurecontainerapps.io/"
    echo ""
    echo "Cleanup when done:"
    echo "  az group delete --name haymaker-${NAMING_PREFIX}-${ENVIRONMENT}-rg --yes"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --name)
            NAMING_PREFIX="$2"
            shift 2
            ;;
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --size)
            SIMULATION_SIZE="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_IMAGE_BUILD=true
            shift
            ;;
        --watch)
            WATCH=true
            shift
            ;;
        --use-secrets)
            USE_SECRETS=true
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

# Main
main() {
    check_prerequisites
    
    if [ "$USE_SECRETS" = false ]; then
        load_env_file
    fi
    
    trigger_workflow
    print_success "Arrr, workflow be triggered, Captain! 🏴‍☠️"
}

main
