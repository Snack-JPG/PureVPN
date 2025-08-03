import requests
import time
import json
import os
import asyncio
import base64
import random
import string
from datetime import datetime
from typing import Dict, List, Optional

class SimpleVPNManager:
    def __init__(self):
        self.vultr_api_key = os.getenv("VULTR_API_KEY")
        self.region = os.getenv("SERVER_REGION", "ewr")
        self.wireguard_port = int(os.getenv("WIREGUARD_PORT", "51820"))
        self.clients = os.getenv("CLIENTS", "austin,brother,phone").split(",")
        
        self.api_base = "https://api.vultr.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.vultr_api_key}",
            "Content-Type": "application/json"
        }
        
        self.current_instance = None
        self.server_configs = {}
        self.setup_password = None
        
    def _generate_password(self) -> str:
        """Generate a random password for the instance"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    async def start_vpn(self) -> Dict:
        """Launch Vultr instance and install WireGuard"""
        print("🚀 Starting VPN deployment...")
        
        # Generate a password for this deployment
        self.setup_password = self._generate_password()
        
        # Create cloud-init script that uses a simple HTTP callback instead of SSH polling
        cloud_init_script = self._generate_simple_cloud_init_script()
        
        # Base64 encode for Vultr
        cloud_init_b64 = base64.b64encode(cloud_init_script.encode('utf-8')).decode('utf-8')
        
        # Create instance
        instance_data = {
            "region": self.region,
            "plan": "vc2-1c-1gb",
            "os_id": 1743,
            "label": f"instantvpn-{int(time.time())}",
            "user_data": cloud_init_b64,
            "enable_ipv6": True,
            "backups": "disabled",
            "ddos_protection": False,
            "activation_email": False
        }
        
        print("📦 Creating Vultr instance...")
        print(f"   Plan: vc2-1c-1gb ($6/month)")
        print(f"   Region: {self.region}")
        print(f"   OS: Ubuntu 22.04 LTS")
        
        response = requests.post(
            f"{self.api_base}/instances",
            headers=self.headers,
            json=instance_data
        )
        
        if response.status_code != 202:
            raise Exception(f"Failed to create instance: {response.text}")
        
        instance = response.json()["instance"]
        instance_id = instance["id"]
        
        print(f"✅ Instance created! ID: {instance_id}")
        
        # Wait for instance to be ready
        server_ip = await self._wait_for_instance_ready(instance_id)
        
        self.current_instance = {
            "id": instance_id,
            "ip": server_ip,
            "created_at": datetime.now()
        }
        
        print(f"✅ Instance ready! IP: {server_ip}")
        print("⏳ Waiting for WireGuard setup via cloud-init...")
        
        # Wait for setup completion by polling the instance metadata
        await self._wait_for_setup_completion(server_ip)
        
        # Generate configs by fetching from a simple HTTP endpoint we created
        await self._fetch_configs_via_http(server_ip)
        
        return {
            "server_ip": server_ip,
            "instance_id": instance_id,
            "status": "running"
        }
    
    async def _wait_for_instance_ready(self, instance_id: str, max_wait: int = 300) -> str:
        """Wait for instance to be active"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.api_base}/instances/{instance_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    instance = response.json()["instance"]
                    if instance["status"] == "active" and instance["main_ip"]:
                        return instance["main_ip"]
                    print(f"   Status: {instance['status']}")
                
            except Exception as e:
                print(f"   Waiting... {e}")
            
            time.sleep(10)
        
        raise Exception("Instance startup timed out")
    
    async def _wait_for_setup_completion(self, server_ip: str, max_wait: int = 600):
        """Wait for setup by checking a simple HTTP endpoint"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Try to fetch the status from our simple web server
                response = requests.get(
                    f"http://{server_ip}:8080/status",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "ready":
                        print("✅ WireGuard setup completed!")
                        return
                    else:
                        print(f"   Setup progress: {data.get('message', 'In progress...')}")
                
            except requests.exceptions.RequestException:
                elapsed = int(time.time() - start_time)
                print(f"   Waiting for setup completion... ({elapsed}s elapsed)")
            
            await asyncio.sleep(15)
        
        raise Exception("WireGuard setup timed out")
    
    async def _fetch_configs_via_http(self, server_ip: str):
        """Fetch configs via simple HTTP endpoint"""
        try:
            for client in self.clients:
                response = requests.get(
                    f"http://{server_ip}:8080/config/{client}",
                    timeout=30
                )
                
                if response.status_code == 200:
                    config = response.text.strip()
                    if config:
                        self.server_configs[client] = config
                        print(f"✅ Retrieved config for {client}")
                    else:
                        print(f"❌ Empty config for {client}")
                else:
                    print(f"❌ Failed to get config for {client}: {response.status_code}")
        
        except Exception as e:
            raise Exception(f"Failed to fetch configs: {e}")
    
    def _generate_simple_cloud_init_script(self) -> str:
        """Generate a cloud-init script that serves configs via HTTP"""
        script = f"""#!/bin/bash

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1
date

echo "Starting InstantVPN setup..."

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y wireguard wireguard-tools python3 python3-pip curl

# Set root password for emergency access
echo 'root:{self.setup_password}' | chpasswd

# Generate server keys
cd /etc/wireguard
wg genkey | tee server_private.key | wg pubkey > server_public.key
chmod 600 server_private.key

SERVER_PRIVATE_KEY=$(cat server_private.key)
SERVER_PUBLIC_KEY=$(cat server_public.key)
SERVER_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)

echo "Server IP: $SERVER_IP"
echo "Server Public Key: $SERVER_PUBLIC_KEY"

# Create server config
cat > wg0.conf << EOF
[Interface]
PrivateKey = $SERVER_PRIVATE_KEY
Address = 10.0.0.1/24
ListenPort = {self.wireguard_port}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

EOF

# Generate client configs
mkdir -p /etc/wireguard/clients
mkdir -p /var/www/configs
"""
        
        for i, client in enumerate(self.clients, start=2):
            script += f"""
# Generate keys for {client}
wg genkey | tee /etc/wireguard/clients/{client}_private.key | wg pubkey > /etc/wireguard/clients/{client}_public.key
CLIENT_PRIVATE_KEY=$(cat /etc/wireguard/clients/{client}_private.key)
CLIENT_PUBLIC_KEY=$(cat /etc/wireguard/clients/{client}_public.key)

# Add client to server config
cat >> wg0.conf << EOF

[Peer]
PublicKey = $CLIENT_PUBLIC_KEY
AllowedIPs = 10.0.0.{i}/32
EOF

# Create client config
cat > /var/www/configs/{client}.conf << EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE_KEY
Address = 10.0.0.{i}/24
DNS = 8.8.8.8

[Peer]
PublicKey = $SERVER_PUBLIC_KEY
Endpoint = $SERVER_IP:{self.wireguard_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

echo "Generated config for {client}"
"""
        
        script += f"""
# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Start WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Create simple HTTP server for config delivery
cat > /var/www/server.py << 'EOSERVER'
#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
from urllib.parse import urlparse

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Check if WireGuard is running
            wg_status = os.system('systemctl is-active --quiet wg-quick@wg0') == 0
            status = "ready" if wg_status else "setting_up"
            
            response = {{"status": status, "message": "WireGuard ready" if wg_status else "Setting up WireGuard"}}
            self.wfile.write(json.dumps(response).encode())
            
        elif path.startswith('/config/'):
            client = path.split('/')[-1]
            config_file = f'/var/www/configs/{{client}}.conf'
            
            if os.path.exists(config_file):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                
                with open(config_file, 'r') as f:
                    self.wfile.write(f.read().encode())
            else:
                self.send_response(404)
                self.end_headers()
                
        else:
            self.send_response(404)
            self.end_headers()

PORT = 8080
os.chdir('/var/www')
with socketserver.TCPServer(("", PORT), ConfigHandler) as httpd:
    print(f"Server starting on port {{PORT}}")
    httpd.serve_forever()
EOSERVER

# Start the HTTP server in background
cd /var/www
nohup python3 server.py > /var/log/config-server.log 2>&1 &

# Mark completion
touch /root/setup_complete
echo "SUCCESS" > /root/setup_complete

echo "InstantVPN setup completed at $(date)!"
date
"""
        
        return script
    
    async def get_status(self) -> Dict:
        """Check current VPN status"""
        if not self.current_instance:
            return {"status": "stopped", "message": "No active VPN"}
        
        try:
            response = requests.get(
                f"{self.api_base}/instances/{self.current_instance['id']}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                instance = response.json()["instance"]
                return {
                    "status": "running" if instance["status"] == "active" else instance["status"],
                    "server_ip": self.current_instance["ip"],
                    "instance_id": self.current_instance["id"],
                    "created_at": str(self.current_instance["created_at"]),
                    "estimated_hourly_cost": "$0.012"
                }
            else:
                return {"status": "unknown", "message": "Failed to check status"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def shutdown_vpn(self) -> Dict:
        """Destroy the current instance"""
        if not self.current_instance:
            raise Exception("No active VPN to shutdown")
        
        print("🛑 Shutting down VPN...")
        instance_id = self.current_instance["id"]
        
        # Calculate runtime cost
        created_time = self.current_instance["created_at"]
        runtime_hours = (datetime.now() - created_time).total_seconds() / 3600
        estimated_cost = f"${runtime_hours * 0.012:.3f}"
        
        # Destroy instance
        response = requests.delete(
            f"{self.api_base}/instances/{instance_id}",
            headers=self.headers
        )
        
        if response.status_code != 204:
            raise Exception(f"Failed to destroy instance: {response.text}")
        
        self.current_instance = None
        self.server_configs = {}
        self.setup_password = None
        
        print(f"✅ VPN destroyed! Estimated cost: {estimated_cost}")
        
        return {
            "instance_id": instance_id,
            "final_cost": estimated_cost,
            "runtime_hours": round(runtime_hours, 2)
        }
    
    async def get_client_config(self, client: str) -> str:
        """Get WireGuard config for specific client"""
        if client not in self.server_configs:
            raise Exception(f"Config not found for client: {client}")
        
        return self.server_configs[client] 