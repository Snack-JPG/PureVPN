#!/bin/bash

# Pure VPN - VPS Deployment Script
# Deploy Pure VPN dashboard directly to your VPS server

set -e

echo "🚀 Pure VPN - VPS Deployment"
echo "============================="
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

# Check if running on the VPS
if [[ ! -f "/etc/wireguard/wg0.conf" ]]; then
    log_error "This script should be run on your VPS server where WireGuard is installed"
    exit 1
fi

# Get server details
echo "📋 VPS Configuration"
echo "--------------------"
VPS_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || hostname -I | awk '{print $1}')
echo "🌐 Detected VPS IP: $VPS_IP"

read -p "Enter your domain name (or press Enter to use IP): " DOMAIN_NAME
if [[ -z "$DOMAIN_NAME" ]]; then
    DOMAIN_NAME=$VPS_IP
    FULL_URL="http://$VPS_IP:3001"
else
    FULL_URL="http://$DOMAIN_NAME:3001"
fi

echo "🎯 Pure VPN will be accessible at: $FULL_URL"
echo

# Install Node.js if not present
log_info "Installing Node.js and dependencies..."
if ! command -v node &> /dev/null; then
    # Install Node.js 18.x
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

if ! command -v npm &> /dev/null; then
    sudo apt-get install -y npm
fi

# Install Python dependencies if not present
if ! command -v python3 &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
fi

log_success "Dependencies installed"

# Create Pure VPN directory
PURE_VPN_DIR="/opt/pure-vpn"
sudo mkdir -p $PURE_VPN_DIR
sudo chown $USER:$USER $PURE_VPN_DIR

log_info "Setting up Pure VPN in $PURE_VPN_DIR..."

# Copy or clone Pure VPN (assuming we're in the project directory)
if [[ -f "backend/main.py" ]]; then
    log_info "Copying Pure VPN files..."
    cp -r backend frontend package.json README.md $PURE_VPN_DIR/
else
    log_info "Cloning Pure VPN repository..."
    git clone https://github.com/yourusername/pure-vpn.git $PURE_VPN_DIR
fi

cd $PURE_VPN_DIR

# Setup backend
log_info "Setting up Python backend..."
cd backend
python3 -m pip install -r requirements.txt

# Create production environment file
cat > .env << EOF
# Pure VPN Production Configuration
EXISTING_SERVER_IP=127.0.0.1
SSH_USERNAME=root
SSH_PASSWORD=your_password_here
WIREGUARD_PORT=51820
PRODUCTION=true
ALLOWED_ORIGINS=http://$DOMAIN_NAME:3001,http://$VPS_IP:3001,http://localhost:3001
EOF

log_warning "⚠️  Please edit $PURE_VPN_DIR/backend/.env with your actual SSH credentials"

# Setup frontend
log_info "Setting up Node.js frontend..."
cd ../frontend
npm install

# Update Next.js config for production
cat > next.config.js << EOF
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
  env: {
    CUSTOM_KEY: 'pure-vpn-production',
  },
}

module.exports = nextConfig
EOF

log_info "Building frontend for production..."
npm run build

# Create systemd service for backend
log_info "Creating systemd services..."
sudo tee /etc/systemd/system/pure-vpn-backend.service > /dev/null << EOF
[Unit]
Description=Pure VPN Backend API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PURE_VPN_DIR/backend
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=$PURE_VPN_DIR/backend
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for frontend
sudo tee /etc/systemd/system/pure-vpn-frontend.service > /dev/null << EOF
[Unit]
Description=Pure VPN Frontend
After=network.target pure-vpn-backend.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PURE_VPN_DIR/frontend
Environment=PATH=/usr/bin:/usr/local/bin
Environment=NODE_ENV=production
ExecStart=/usr/bin/npm start -- --port 3001 --hostname 0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Create startup script
cat > $PURE_VPN_DIR/start-production.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting Pure VPN Production Services..."

# Start backend
sudo systemctl start pure-vpn-backend
echo "✅ Backend started on port 8000"

# Start frontend  
sudo systemctl start pure-vpn-frontend
echo "✅ Frontend started on port 3001"

echo
echo "🌐 Pure VPN is now running at:"
VPS_IP=$(curl -s ifconfig.me)
echo "   http://$VPS_IP:3001"
echo
echo "📊 Check status with:"
echo "   sudo systemctl status pure-vpn-backend"
echo "   sudo systemctl status pure-vpn-frontend"
echo
echo "📋 View logs with:"
echo "   sudo journalctl -u pure-vpn-backend -f"
echo "   sudo journalctl -u pure-vpn-frontend -f"
EOF

chmod +x $PURE_VPN_DIR/start-production.sh

# Create stop script
cat > $PURE_VPN_DIR/stop-production.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping Pure VPN Production Services..."

sudo systemctl stop pure-vpn-frontend
sudo systemctl stop pure-vpn-backend

echo "✅ Pure VPN services stopped"
EOF

chmod +x $PURE_VPN_DIR/stop-production.sh

# Setup firewall
log_info "Configuring firewall..."
sudo ufw allow 8000/tcp comment "Pure VPN Backend"
sudo ufw allow 3001/tcp comment "Pure VPN Frontend"

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable pure-vpn-backend
sudo systemctl enable pure-vpn-frontend

log_success "Pure VPN deployment completed!"

echo
echo "🎉 **DEPLOYMENT SUCCESSFUL!**"
echo "=============================="
echo
echo "🌐 **Access your Pure VPN at:** $FULL_URL"
echo
echo "🚀 **To start Pure VPN:**"
echo "   cd $PURE_VPN_DIR && ./start-production.sh"
echo
echo "🛑 **To stop Pure VPN:**"
echo "   cd $PURE_VPN_DIR && ./stop-production.sh"
echo
echo "⚙️  **Next steps:**"
echo "   1. Edit $PURE_VPN_DIR/backend/.env with your SSH credentials"
echo "   2. Run: cd $PURE_VPN_DIR && ./start-production.sh"
echo "   3. Open: $FULL_URL"
echo
echo "📊 **Monitor services:**"
echo "   sudo systemctl status pure-vpn-backend"
echo "   sudo systemctl status pure-vpn-frontend"
echo
echo "🔒 **Security Note:**"
echo "   Consider setting up SSL/HTTPS with Let's Encrypt for production use"
echo 