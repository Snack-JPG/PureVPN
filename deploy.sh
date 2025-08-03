#!/bin/bash

# Pure VPN Deployment Script
# Automates the setup of Pure VPN on a fresh server

set -e

echo "🔒 Pure VPN Deployment Script"
echo "=============================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root. Please run as a normal user with sudo privileges."
   exit 1
fi

# Get server details
echo "📋 Server Configuration"
echo "----------------------"
read -p "Enter your VPS IP address: " SERVER_IP
read -p "Enter SSH username (default: root): " SSH_USERNAME
SSH_USERNAME=${SSH_USERNAME:-root}

# Ask for authentication method
echo
echo "🔐 Choose authentication method:"
echo "1) Password"
echo "2) SSH Key"
read -p "Enter choice (1 or 2): " AUTH_METHOD

if [[ $AUTH_METHOD == "1" ]]; then
    read -s -p "Enter SSH password: " SSH_PASSWORD
    echo
elif [[ $AUTH_METHOD == "2" ]]; then
    read -p "Enter path to SSH private key: " SSH_KEY_PATH
    if [[ ! -f "$SSH_KEY_PATH" ]]; then
        log_error "SSH key file not found: $SSH_KEY_PATH"
        exit 1
    fi
else
    log_error "Invalid choice. Please run the script again."
    exit 1
fi

echo
log_info "Testing connection to $SERVER_IP..."

# Test SSH connection
if [[ $AUTH_METHOD == "1" ]]; then
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$SSH_USERNAME@$SERVER_IP" "echo 'Connection successful'" > /dev/null 2>&1
else
    ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$SSH_USERNAME@$SERVER_IP" "echo 'Connection successful'" > /dev/null 2>&1
fi

if [[ $? -eq 0 ]]; then
    log_success "SSH connection successful"
else
    log_error "Failed to connect to server. Please check your credentials and try again."
    exit 1
fi

echo
log_info "Installing Pure VPN dependencies on server..."

# Prepare server setup commands
SERVER_SETUP_COMMANDS="
# Update system
sudo apt update && sudo apt upgrade -y

# Install WireGuard and dependencies
sudo apt install -y wireguard ufw

# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-wireguard.conf
sudo sysctl -p /etc/sysctl.d/99-wireguard.conf

# Configure firewall
sudo ufw allow ssh
sudo ufw allow 51820/udp
sudo ufw --force enable

# Create WireGuard directory and set permissions
sudo mkdir -p /etc/wireguard/clients
sudo chmod 700 /etc/wireguard
sudo chmod 600 /etc/wireguard/* 2>/dev/null || true

echo '✅ Server setup completed successfully!'
"

# Execute server setup
if [[ $AUTH_METHOD == "1" ]]; then
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USERNAME@$SERVER_IP" "$SERVER_SETUP_COMMANDS"
else
    ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "$SSH_USERNAME@$SERVER_IP" "$SERVER_SETUP_COMMANDS"
fi

log_success "Server setup completed"

echo
log_info "Setting up Pure VPN locally..."

# Check if Pure VPN directory exists
if [[ ! -d "backend" ]] || [[ ! -d "frontend" ]]; then
    log_error "Please run this script from the Pure VPN project directory"
    exit 1
fi

# Install Python dependencies
log_info "Installing Python dependencies..."
cd backend
if command -v python3 &> /dev/null; then
    python3 -m pip install -r requirements.txt
else
    log_error "Python 3 is required but not installed"
    exit 1
fi

# Create .env file
log_info "Creating environment configuration..."
cat > .env << EOF
# Pure VPN Configuration
EXISTING_SERVER_IP=$SERVER_IP
SSH_USERNAME=$SSH_USERNAME
WIREGUARD_PORT=51820

EOF

if [[ $AUTH_METHOD == "1" ]]; then
    echo "SSH_PASSWORD=$SSH_PASSWORD" >> .env
else
    echo "SSH_KEY_PATH=$SSH_KEY_PATH" >> .env
fi

log_success "Backend configuration completed"

# Install Node.js dependencies
cd ../frontend
log_info "Installing Node.js dependencies..."
if command -v npm &> /dev/null; then
    npm install
else
    log_error "Node.js and npm are required but not installed"
    exit 1
fi

log_success "Frontend setup completed"

# Make start script executable
cd ..
chmod +x start.sh

echo
log_success "🎉 Pure VPN deployment completed successfully!"
echo
echo "🚀 Quick Start:"
echo "   1. Run: ./start.sh"
echo "   2. Open: http://localhost:3001"
echo "   3. Enter a username and click 'Connect to Pure VPN'"
echo "   4. Download the config file or scan the QR code"
echo
echo "📖 For detailed instructions, see README.md"
echo "🆘 Need help? Visit: https://github.com/yourusername/pure-vpn"
echo 