# 🚀 Pure VPN - 5-Minute Setup

Get your own **self-hosted VPN** running in 5 minutes with any VPS provider!

## 💰 Cost: ~$6/month for unlimited users

## 📋 What You Need
1. **A VPS Server** (any provider works)
2. **5 minutes** of your time
3. **Basic copy-paste skills**

---

## Step 1: Get a VPS (2 minutes)

### Option A: Vultr (Recommended)
1. Go to [Vultr.com](https://vultr.com) and sign up
2. Click "Deploy Instance" → **Ubuntu 22.04 LTS**
3. Choose **Regular Performance** - $6/month plan
4. Select location closest to you
5. Click "Deploy Now"
6. **Save your IP and password!**

### Option B: DigitalOcean
1. Go to [DigitalOcean.com](https://digitalocean.com) and sign up
2. Create Droplet → **Ubuntu 22.04** → **Basic $6/month**
3. Choose datacenter region
4. **Save your IP and password!**

### Option C: Any Provider
- Linode, AWS, Google Cloud, etc.
- Minimum: 1GB RAM, 1 vCPU, Ubuntu 22.04

---

## Step 2: Install Pure VPN (3 minutes)

Copy and paste these commands **one by one**:

### A) SSH to your server
```bash
ssh root@YOUR-VPS-IP
# (Replace YOUR-VPS-IP with your actual IP)
```

### B) Download and run setup
```bash
# Install WireGuard
apt update && apt install -y wireguard ufw git

# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-wireguard.conf
sysctl -p /etc/sysctl.d/99-wireguard.conf

# Configure firewall
ufw allow ssh && ufw allow 51820/udp && ufw --force enable

# Clone Pure VPN
git clone https://github.com/Snack-JPG/PureVPN.git
cd PureVPN

# Run automated setup
chmod +x deploy-to-vps.sh
./deploy-to-vps.sh
```

### C) Configure and start
```bash
# Edit configuration
cd /opt/pure-vpn
nano backend/.env

# Change these two lines:
# EXISTING_SERVER_IP=127.0.0.1  →  EXISTING_SERVER_IP=YOUR-VPS-IP
# SSH_PASSWORD=your_password_here  →  SSH_PASSWORD=your-actual-password

# Save and exit (Ctrl+X, then Y, then Enter)

# Start Pure VPN
./start-production.sh
```

---

## Step 3: Use Your VPN! 🎉

### Open your dashboard:
```
http://YOUR-VPS-IP:3001
```

### Connect your devices:

#### 📱 **Phone (iPhone/Android)**
1. Download **WireGuard** app
2. Open your Pure VPN dashboard on phone
3. Enter your name → Click "Connect"
4. Scan QR code → Done!

#### 💻 **Computer (Windows/Mac/Linux)**
1. Download **WireGuard** from [wireguard.com](https://www.wireguard.com/install/)
2. Open your Pure VPN dashboard
3. Enter your name → Click "Connect"
4. Download `.conf` file → Import to WireGuard → Done!

---

## 🎯 That's It!

You now have:
- ✅ **Your own VPN server** accessible from anywhere
- ✅ **Unlimited users** (share with family/friends)
- ✅ **No monthly limits** on bandwidth
- ✅ **Complete privacy** (you control everything)
- ✅ **Beautiful web interface** for easy management

### 🌍 Share with Others
Send your family/friends this URL: `http://YOUR-VPS-IP:3001`

They can create their own VPN configs instantly!

---

## 🔧 Management Commands

```bash
# SSH to your VPS and run:

# Start Pure VPN
cd /opt/pure-vpn && ./start-production.sh

# Stop Pure VPN
cd /opt/pure-vpn && ./stop-production.sh

# Check status
systemctl status pure-vpn-backend pure-vpn-frontend

# View logs
journalctl -u pure-vpn-backend -f
```

---

## 💡 Tips

### 🌐 **Add a Domain** (Optional)
1. Point your domain to your VPS IP
2. Access via `http://yourdomain.com:3001`

### 🔒 **Add SSL** (Optional)
```bash
# Install Let's Encrypt
apt install certbot
certbot certonly --standalone -d yourdomain.com
# Then configure nginx reverse proxy
```

### 📱 **Bookmark on Phone**
Add `http://YOUR-VPS-IP:3001` to your phone's home screen for quick access!

---

## 🆘 Need Help?

### Common Issues:
- **Can't connect to dashboard**: Check firewall with `ufw status`
- **VPN not working**: Run `wg show` to check WireGuard status
- **Forgot your VPS IP**: Check your VPS provider dashboard

### Get Support:
- [GitHub Issues](https://github.com/Snack-JPG/PureVPN/issues)
- [GitHub Discussions](https://github.com/Snack-JPG/PureVPN/discussions)

---

## 🎉 Enjoy Your Pure VPN!

**You now have a professional-grade VPN that:**
- Costs less than commercial VPNs
- Gives you complete control
- Works on all your devices
- Can be shared with unlimited users
- Looks beautiful and is easy to use

**Welcome to the world of self-hosted privacy!** 🔒✨ 