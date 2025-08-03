# 🚀 Pure VPN - VPS Quick Start

Deploy Pure VPN directly to your VPS server for access from anywhere!

## 📋 Prerequisites

- VPS with WireGuard already installed and working
- Root or sudo access to the VPS
- Domain name (optional, can use IP address)

## 🛠️ Step 1: Get a VPS

### Recommended Providers

#### Option A: Vultr (Most Popular)
1. Sign up at [Vultr.com](https://vultr.com)
2. Create a server:
   - **OS**: Ubuntu 22.04 LTS
   - **Plan**: Regular Performance ($6/month)
   - **Location**: Choose closest to you
3. Note your server IP and root password

#### Option B: DigitalOcean
1. Sign up at [DigitalOcean.com](https://digitalocean.com)
2. Create a droplet:
   - **Image**: Ubuntu 22.04 LTS
   - **Size**: Basic $6/month (1GB RAM)
   - **Datacenter**: Choose closest to you

#### Option C: Any VPS Provider
- Linode, AWS EC2, Google Cloud, etc.
- Minimum requirements: 1GB RAM, 1 vCPU, 25GB storage

## 🔧 Step 2: Automated Deployment Script

### Method 1: Clone and Deploy

```bash
# SSH to your VPS
ssh root@YOUR-VPS-IP

# Clone Pure VPN
git clone https://github.com/Snack-JPG/PureVPN.git
cd PureVPN

# Run automated deployment
chmod +x deploy-to-vps.sh
./deploy-to-vps.sh

# Configure your credentials
cd /opt/pure-vpn
nano backend/.env  # Update EXISTING_SERVER_IP and SSH_PASSWORD

# Start Pure VPN
./start-production.sh
```

### Method 2: Upload Script

```bash
# On your local machine
git clone https://github.com/Snack-JPG/PureVPN.git
cd PureVPN

# Upload deployment script to your VPS
scp deploy-to-vps.sh root@YOUR-VPS-IP:/root/

# SSH to your VPS
ssh root@YOUR-VPS-IP

# Run the deployment script
chmod +x deploy-to-vps.sh
./deploy-to-vps.sh
```

## 🛠️ Step 3: Manual Setup (Alternative)

If you prefer manual setup:

### Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python and other dependencies
sudo apt-get install -y python3 python3-pip git wireguard ufw
```

### Setup Pure VPN

```bash
# Create directory
sudo mkdir -p /opt/pure-vpn
sudo chown $USER:$USER /opt/pure-vpn
cd /opt/pure-vpn

# Clone Pure VPN
git clone https://github.com/Snack-JPG/PureVPN.git .

# Setup backend
cd backend
pip3 install -r requirements.txt

# Create environment file
cp .env.example .env
nano .env  # Update with your server details
```

### Configure Environment

Edit `/opt/pure-vpn/backend/.env`:

```env
EXISTING_SERVER_IP=127.0.0.1
SSH_USERNAME=root
SSH_PASSWORD=your_actual_password
WIREGUARD_PORT=51820
PRODUCTION=true
ALLOWED_ORIGINS=http://YOUR-VPS-IP:3001
```

### Setup Frontend

```bash
cd /opt/pure-vpn/frontend
npm install
npm run build
```

### Start Services

```bash
# Start backend (in background)
cd /opt/pure-vpn/backend
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &

# Start frontend (in background)
cd ../frontend  
nohup npm start -- --port 3001 --hostname 0.0.0.0 > ../logs/frontend.log 2>&1 &
```

### Configure Firewall

```bash
# Allow Pure VPN ports
sudo ufw allow 8000/tcp comment "Pure VPN Backend"
sudo ufw allow 3001/tcp comment "Pure VPN Frontend"
sudo ufw allow 51820/udp comment "WireGuard VPN"
sudo ufw allow ssh
sudo ufw --force enable
```

---

## 🌐 Access Your Pure VPN

Once deployed, you can access Pure VPN from **any device**:

- **Direct IP**: `http://YOUR-VPS-IP:3001`
- **With Domain**: `http://yourdomain.com:3001` (if you have one)
- **Mobile**: Works perfectly on phones/tablets
- **Multiple Users**: Family and friends can all use it

## 📱 Connect from Any Device

1. **Open Pure VPN**: Visit `http://YOUR-VPS-IP:3001`
2. **Enter Username**: Choose any username
3. **Click Connect**: Dashboard generates your config
4. **Use QR Code**: Scan with WireGuard mobile app
5. **Or Download**: Download `.conf` file for desktop

## 🔧 Management Commands

### Check Status
```bash
# Check if services are running
sudo systemctl status pure-vpn-backend
sudo systemctl status pure-vpn-frontend

# Check ports
sudo netstat -tlnp | grep :3001
sudo netstat -tlnp | grep :8000

# View logs
sudo journalctl -u pure-vpn-backend -f
sudo journalctl -u pure-vpn-frontend -f
```

### Start/Stop Services
```bash
# Start
cd /opt/pure-vpn
./start-production.sh

# Stop  
./stop-production.sh

# Restart
sudo systemctl restart pure-vpn-backend
sudo systemctl restart pure-vpn-frontend
```

### Update Pure VPN
```bash
cd /opt/pure-vpn
git pull origin main
cd frontend && npm run build
sudo systemctl restart pure-vpn-frontend pure-vpn-backend
```

## 🔒 Security & SSL

### Basic Security
- Pure VPN runs on non-standard ports (8000, 3001)
- Only accessible via HTTP (consider HTTPS for production)
- No authentication on dashboard (suitable for personal/family use)

### Add SSL (Optional)
```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot

# Get SSL certificate (requires domain)
sudo certbot certonly --standalone -d yourdomain.com

# Configure nginx as reverse proxy with SSL
# (Advanced setup - see documentation)
```

## 💰 Cost Analysis

### Monthly VPS Costs
- **Vultr**: $6/month (1GB RAM, 1 vCPU, 25GB SSD)
- **DigitalOcean**: $6/month (1GB RAM, 1 vCPU, 25GB SSD)
- **Linode**: $5/month (1GB RAM, 1 vCPU, 25GB SSD)
- **AWS EC2**: ~$8-10/month (t3.micro with data transfer)

### What You Get
- ✅ **Unlimited Users**: Add family, friends, team members
- ✅ **Unlimited Bandwidth**: No monthly limits
- ✅ **24/7 Availability**: Always accessible worldwide
- ✅ **Complete Control**: Your VPN, your rules
- ✅ **No Subscriptions**: One-time setup

### vs Commercial VPN Services
- **ExpressVPN**: $12.95/month per user
- **NordVPN**: $11.95/month per user  
- **Surfshark**: $12.95/month
- **Pure VPN**: $6/month for unlimited users

## 🎯 Perfect For

- **Personal Use**: Access your VPN from anywhere
- **Family Sharing**: Give family members easy VPN access  
- **Small Teams**: Business VPN without monthly subscriptions
- **Travel**: Connect to your home VPN from any location
- **Privacy**: Complete control over your VPN infrastructure

## 🆘 Troubleshooting

### Can't Connect to Dashboard
```bash
# Check if services are running
sudo netstat -tlnp | grep :3001
sudo netstat -tlnp | grep :8000

# Check firewall
sudo ufw status

# Check logs
tail -f /opt/pure-vpn/logs/frontend.log
tail -f /opt/pure-vpn/logs/backend.log
```

### VPN Not Working
```bash
# Check WireGuard
sudo systemctl status wg-quick@wg0
sudo wg show

# Test SSH connection (from VPS to itself)
ssh root@127.0.0.1 "echo 'SSH works'"

# Check Pure VPN backend
curl http://localhost:8000/health
```

### Port Issues
```bash
# Kill processes on required ports
sudo fuser -k 8000/tcp
sudo fuser -k 3001/tcp

# Check what's using ports
sudo lsof -i :8000
sudo lsof -i :3001
```

---

## 🎉 Success!

Your Pure VPN is now running on your VPS and accessible from anywhere in the world!

**Dashboard URL**: `http://YOUR-VPS-IP:3001`

### 🌍 Share with Others
- Send the URL to family/friends for instant VPN access
- They just enter a username and get their own VPN configuration
- No technical knowledge required!

### 📱 Mobile Setup
1. Visit the URL on your phone
2. Enter your name
3. Scan the QR code with WireGuard app
4. Connected!

### 💻 Desktop Setup
1. Visit the URL on your computer
2. Enter your name  
3. Download the `.conf` file
4. Import to WireGuard
5. Connected!

**Enjoy your self-hosted, globally accessible Pure VPN!** 🚀 