#!/bin/bash
#
# VM Orchestrator Setup Script
#
# Sets up the Azure HayMaker orchestrator service on a newly deployed VM.
# This script should be run ON the VM after successful deployment.
#
# Usage:
#   # Run remotely from deployment machine
#   ssh azureuser@<vm-ip> 'bash -s' < scripts/setup_vm_orchestrator.sh
#
#   # Or copy and run directly on VM
#   scp scripts/setup_vm_orchestrator.sh azureuser@<vm-ip>:~/
#   ssh azureuser@<vm-ip>
#   ./setup_vm_orchestrator.sh
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/rysweet/AzureHayMaker.git"
INSTALL_DIR="/opt/haymaker"
SERVICE_USER="haymaker"
SERVICE_NAME="haymaker-orchestrator"

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

check_running_as_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_dependencies() {
    print_header "Installing Dependencies"

    print_info "Updating package lists..."
    apt-get update -qq

    print_info "Installing Python 3.11 and tools..."
    apt-get install -y python3.11 python3.11-venv python3-pip git curl

    # Install uv for package management
    if ! command -v uv &> /dev/null; then
        print_info "Installing uv package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    print_success "Dependencies installed"
    echo
}

create_service_user() {
    print_header "Creating Service User"

    if id "$SERVICE_USER" &>/dev/null; then
        print_info "User $SERVICE_USER already exists"
    else
        print_info "Creating user: $SERVICE_USER"
        useradd -m -s /bin/bash "$SERVICE_USER"
        print_success "User created: $SERVICE_USER"
    fi

    echo
}

clone_repository() {
    print_header "Cloning Repository"

    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory already exists: $INSTALL_DIR"
        print_info "Pulling latest changes..."
        cd "$INSTALL_DIR"
        sudo -u "$SERVICE_USER" git pull
    else
        print_info "Cloning repository..."
        sudo -u "$SERVICE_USER" git clone "$REPO_URL" "$INSTALL_DIR"
        print_success "Repository cloned"
    fi

    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

    echo
}

setup_python_environment() {
    print_header "Setting Up Python Environment"

    cd "$INSTALL_DIR"

    print_info "Installing Python dependencies..."
    sudo -u "$SERVICE_USER" uv sync

    print_success "Python environment configured"
    echo
}

create_systemd_service() {
    print_header "Creating Systemd Service"

    # Create service file
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Azure HayMaker Orchestrator Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Main orchestrator process
ExecStart=$INSTALL_DIR/.venv/bin/python -m azure_haymaker.orchestrator.main

# Restart on failure
Restart=always
RestartSec=10

# Resource limits
MemoryMax=120G
MemoryHigh=100G

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

    print_success "Systemd service created: /etc/systemd/system/${SERVICE_NAME}.service"

    # Reload systemd
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"

    echo
}

configure_logging() {
    print_header "Configuring Logging"

    # Create log directory
    mkdir -p /var/log/haymaker
    chown "$SERVICE_USER:$SERVICE_USER" /var/log/haymaker

    # Configure log rotation
    cat > /etc/logrotate.d/haymaker << EOF
/var/log/haymaker/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 $SERVICE_USER $SERVICE_USER
    sharedscripts
    postrotate
        systemctl reload $SERVICE_NAME > /dev/null 2>&1 || true
    endscript
}
EOF

    print_success "Logging configured"
    echo
}

enable_and_start_service() {
    print_header "Enabling and Starting Service"

    # Enable service to start on boot
    systemctl enable "$SERVICE_NAME"
    print_success "Service enabled for automatic startup"

    # Start the service
    print_info "Starting service..."
    systemctl start "$SERVICE_NAME"

    # Wait a moment for service to start
    sleep 3

    # Check status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service started successfully"
    else
        print_error "Service failed to start"
        print_info "Check logs: journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi

    echo
}

verify_installation() {
    print_header "Verifying Installation"

    # Check service status
    print_info "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager -l

    echo
    print_info "Recent logs:"
    journalctl -u "$SERVICE_NAME" -n 20 --no-pager

    echo
    print_info "Memory usage:"
    free -h

    echo
}

print_next_steps() {
    print_header "Installation Complete!"

    cat << EOF
✅ Azure HayMaker orchestrator is now running on this VM!

Service Management:
  - Status:  sudo systemctl status $SERVICE_NAME
  - Logs:    sudo journalctl -u $SERVICE_NAME -f
  - Restart: sudo systemctl restart $SERVICE_NAME
  - Stop:    sudo systemctl stop $SERVICE_NAME

Monitoring:
  - Memory:  free -h
  - CPU:     top -u $SERVICE_USER
  - Logs:    tail -f /var/log/haymaker/*.log

Next Steps:
1. Monitor memory usage over next few hours
   Expected: 60-70GB during SDK initialization
   Peak: <100GB normal, 120GB hard limit

2. Verify agent deployment works
   Check logs for successful agent launches

3. Monitor for 24-48 hours before cutover from Function Apps

4. Update service endpoints to point to this VM

Troubleshooting:
  - If service won't start: check journalctl -u $SERVICE_NAME
  - If out of memory: increase VM size to Standard_E20s_v3 (160GB)
  - If connectivity issues: check NSG rules and firewall

Documentation: /opt/haymaker/docs/VM_ORCHESTRATOR_MIGRATION_GUIDE.md
EOF

    echo
}

# Main execution
main() {
    print_header "Azure HayMaker Orchestrator Setup"

    check_running_as_root
    install_dependencies
    create_service_user
    clone_repository
    setup_python_environment
    create_systemd_service
    configure_logging
    enable_and_start_service
    verify_installation
    print_next_steps

    print_success "Setup complete!"
}

# Run main function
main
