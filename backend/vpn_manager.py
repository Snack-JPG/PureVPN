import requests
import paramiko
import time
import json
import os
import asyncio
import subprocess
import base64
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

class VPNManager:
    def __init__(self):
        self.vultr_api_key = os.getenv("VULTR_API_KEY")
        self.region = os.getenv("SERVER_REGION", "ewr")  # Newark
        self.wireguard_port = int(os.getenv("WIREGUARD_PORT", "51820"))
        self.clients = os.getenv("CLIENTS", "austin,brother,phone").split(",")
        
        self.api_base = "https://api.vultr.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.vultr_api_key}",
            "Content-Type": "application/json"
        }
        
        self.current_instance = None
        self.server_configs = {}
        self.ssh_key_id = None
        self.ssh_private_key = None
        
    async def start_vpn(self) -> Dict:
        """Launch Vultr instance and install WireGuard"""
        print("🚀 Starting VPN deployment...")
        
        # Create SSH key for authentication
        ssh_key_id = await self._create_ssh_key()
        
        # Create cloud-init script
        cloud_init_script = self._generate_cloud_init_script()
        
        # Base64 encode the cloud-init script for Vultr
        cloud_init_b64 = base64.b64encode(cloud_init_script.encode('utf-8')).decode('utf-8')
        
        # Create instance payload
        instance_data = {
            "region": self.region,
            "plan": "vc2-1c-1gb",  # $6/month, ~$0.012/hour
            "os_id": 1743,  # Ubuntu 22.04 LTS
            "label": f"instantvpn-{int(time.time())}",
            "user_data": cloud_init_b64,  # Base64 encoded
            "sshkey_id": [ssh_key_id],  # SSH key for authentication
            "enable_ipv6": True,
            "backups": "disabled",
            "ddos_protection": False,
            "activation_email": False
        }
        
        print("📦 Creating Vultr instance...")
        print(f"   Plan: vc2-1c-1gb ($6/month)")
        print(f"   Region: {self.region}")
        print(f"   OS: Ubuntu 22.04 LTS")
        print(f"   SSH Key: {ssh_key_id}")
        print(f"   Cloud-init: Encoded ({len(cloud_init_script)} chars)")
        
        response = requests.post(
            f"{self.api_base}/instances",
            headers=self.headers,
            json=instance_data
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code != 202:
            error_detail = response.text
            print(f"❌ Failed to create instance: {error_detail}")
            
            # Cleanup SSH key
            await self._cleanup_ssh_key(ssh_key_id)
            
            # Try to parse error for better message
            try:
                error_json = response.json()
                if 'error' in error_json:
                    raise Exception(f"Vultr API Error: {error_json['error']}")
                else:
                    raise Exception(f"Vultr API Error (Status {response.status_code}): {error_detail}")
            except json.JSONDecodeError:
                raise Exception(f"Failed to create instance (Status {response.status_code}): {error_detail}")
        
        instance = response.json()["instance"]
        instance_id = instance["id"]
        
        print(f"✅ Instance created! ID: {instance_id}")
        print("⏳ Waiting for instance to boot...")
        
        # Wait for instance to be ready
        server_ip = await self._wait_for_instance_ready(instance_id)
        
        self.current_instance = {
            "id": instance_id,
            "ip": server_ip,
            "created_at": datetime.now(),
            "ssh_key_id": ssh_key_id
        }
        
        print(f"✅ Instance ready! IP: {server_ip}")
        print("⏳ Waiting for WireGuard installation to complete...")
        
        # Wait for WireGuard setup to complete
        await self._wait_for_wireguard_setup(server_ip)
        
        # Generate client configs
        await self._generate_client_configs(server_ip)
        
        return {
            "server_ip": server_ip,
            "instance_id": instance_id,
            "status": "running"
        }
    
    async def _create_ssh_key(self) -> str:
        """Create a temporary SSH key for Vultr authentication"""
        print("🔑 Generating SSH key for authentication...")
        
        # Generate SSH key pair
        key = paramiko.RSAKey.generate(2048)
        
        # Get public key in OpenSSH format
        public_key = f"ssh-rsa {key.get_base64()}"
        
        # Store private key for later use
        self.ssh_private_key = key
        
        # Upload public key to Vultr
        key_data = {
            "name": f"instantvpn-{int(time.time())}",
            "ssh_key": public_key
        }
        
        response = requests.post(
            f"{self.api_base}/ssh-keys",
            headers=self.headers,
            json=key_data
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to create SSH key: {response.text}")
        
        ssh_key_data = response.json()["ssh_key"]
        self.ssh_key_id = ssh_key_data["id"]
        
        print(f"✅ SSH key created: {self.ssh_key_id}")
        return self.ssh_key_id
    
    async def _cleanup_ssh_key(self, ssh_key_id: str):
        """Remove SSH key from Vultr"""
        try:
            response = requests.delete(
                f"{self.api_base}/ssh-keys/{ssh_key_id}",
                headers=self.headers
            )
            if response.status_code == 204:
                print(f"🗑️ SSH key {ssh_key_id} deleted")
        except Exception as e:
            print(f"⚠️ Failed to delete SSH key {ssh_key_id}: {e}")
    
    async def get_status(self) -> Dict:
        """Check current VPN status"""
        if not self.current_instance:
            return {"status": "stopped", "message": "No active VPN"}
        
        # Check instance status via API
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
        ssh_key_id = self.current_instance.get("ssh_key_id")
        
        # Calculate runtime cost (rough estimate)
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
        
        # Cleanup SSH key
        if ssh_key_id:
            await self._cleanup_ssh_key(ssh_key_id)
        
        self.current_instance = None
        self.server_configs = {}
        self.ssh_key_id = None
        self.ssh_private_key = None
        
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
    
    async def _wait_for_instance_ready(self, instance_id: str, max_wait: int = 300) -> str:
        """Wait for Vultr instance to be ready and return IP"""
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
                        # Wait extra time for SSH to be ready
                        print(f"   Instance active - waiting 60s for SSH to be ready...")
                        await asyncio.sleep(60)
                        return instance["main_ip"]
                    
                    print(f"   Status: {instance['status']}")
                
            except Exception as e:
                print(f"   Waiting for instance... ({e})")
            
            time.sleep(15)
        
        raise Exception("Instance startup timed out")
    
    def _generate_cloud_init_script(self) -> str:
        """Generate cloud-init script for WireGuard installation"""
        script = f"""#!/bin/bash

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting InstantVPN setup at $(date)"

# Update system
apt-get update
apt-get upgrade -y

# Install WireGuard
apt-get install -y wireguard wireguard-tools

# Generate server keys
cd /etc/wireguard
wg genkey | tee server_private.key | wg pubkey > server_public.key
chmod 600 server_private.key

# Get server keys
SERVER_PRIVATE_KEY=$(cat server_private.key)
SERVER_PUBLIC_KEY=$(cat server_public.key)

echo "Server public key: $SERVER_PUBLIC_KEY"

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
"""
        
        # Add client config generation
        for i, client in enumerate(self.clients, start=2):
            script += f"""
# Generate keys for {client}
wg genkey | tee /etc/wireguard/clients/{client}_private.key | wg pubkey > /etc/wireguard/clients/{client}_public.key
CLIENT_PRIVATE_KEY_{client.upper()}=$(cat /etc/wireguard/clients/{client}_private.key)
CLIENT_PUBLIC_KEY_{client.upper()}=$(cat /etc/wireguard/clients/{client}_public.key)

echo "Generated keys for {client}"

# Add client to server config
echo "" >> wg0.conf
echo "[Peer]" >> wg0.conf
echo "PublicKey = $CLIENT_PUBLIC_KEY_{client.upper()}" >> wg0.conf
echo "AllowedIPs = 10.0.0.{i}/32" >> wg0.conf

# Create client config file
cat > /etc/wireguard/clients/{client}.conf << EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE_KEY_{client.upper()}
Address = 10.0.0.{i}/24
DNS = 8.8.8.8

[Peer]
PublicKey = $SERVER_PUBLIC_KEY
Endpoint = $(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address):{self.wireguard_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
"""
        
        script += """
# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Start WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Verify WireGuard is running
wg show
systemctl status wg-quick@wg0

# Create completion marker
touch /root/wireguard_setup_complete
echo "SUCCESS" > /root/wireguard_setup_complete
chmod 644 /root/wireguard_setup_complete

echo "WireGuard setup completed successfully at $(date)!"
"""
        
        return script
    
    async def _wait_for_wireguard_setup(self, server_ip: str, max_wait: int = 600):
        """Wait for WireGuard setup to complete on the server"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Try to SSH and check for completion marker
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect using the generated SSH key
                ssh.connect(
                    server_ip, 
                    username='root', 
                    pkey=self.ssh_private_key,
                    timeout=30,
                    banner_timeout=30,
                    auth_timeout=30,
                    look_for_keys=False,
                    allow_agent=False
                )
                
                # Check for completion marker
                stdin, stdout, stderr = ssh.exec_command('test -f /root/wireguard_setup_complete && cat /root/wireguard_setup_complete')
                result = stdout.read().decode().strip()
                
                if result == "SUCCESS":
                    print("✅ WireGuard setup completed!")
                    ssh.close()
                    return
                elif result:
                    print(f"   Setup in progress... (marker: {result})")
                else:
                    print("   Setup marker not found, still installing...")
                
                # Check cloud-init logs for progress
                stdin, stdout, stderr = ssh.exec_command('tail -5 /var/log/user-data.log 2>/dev/null || echo "Log not found"')
                logs = stdout.read().decode().strip()
                if logs and logs != "Log not found":
                    print(f"   Recent log: {logs.split(chr(10))[-1]}")
                    
                ssh.close()
                
            except Exception as e:
                elapsed = int(time.time() - start_time)
                print(f"   Still waiting for SSH... ({elapsed}s elapsed) - {str(e)[:50]}")
            
            await asyncio.sleep(20)
        
        raise Exception("WireGuard setup timed out - check server logs")
    
    async def _generate_client_configs(self, server_ip: str):
        """Fetch client configs from the server"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect using the generated SSH key
            ssh.connect(
                server_ip, 
                username='root', 
                pkey=self.ssh_private_key,
                timeout=30
            )
            
            for client in self.clients:
                stdin, stdout, stderr = ssh.exec_command(f'cat /etc/wireguard/clients/{client}.conf')
                config = stdout.read().decode().strip()
                
                if config:
                    self.server_configs[client] = config
                    print(f"✅ Generated config for {client}")
                else:
                    print(f"❌ Failed to get config for {client}")
            
            ssh.close()
            
        except Exception as e:
            raise Exception(f"Failed to fetch client configs: {e}") 