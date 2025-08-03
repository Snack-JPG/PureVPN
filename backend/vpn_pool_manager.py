import requests
import time
import json
import os
import asyncio
import base64
import random
import string
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import paramiko
from io import StringIO

# Force IPv4 only for requests
import urllib3
original_getaddrinfo = socket.getaddrinfo

def getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = getaddrinfo_ipv4_only

class VPNPoolManager:
    def __init__(self):
        self.vultr_api_key = os.getenv("VULTR_API_KEY")
        self.region = os.getenv("SERVER_REGION", "ewr")
        self.wireguard_port = int(os.getenv("WIREGUARD_PORT", "51820"))
        self.max_peers_per_server = 3
        
        self.api_base = "https://api.vultr.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.vultr_api_key}",
            "Content-Type": "application/json"
        }
        
        # Pool state file
        self.pool_state_file = "vpn_pool_state.json"
        self.pool_state = self._load_pool_state()
        
    def _load_pool_state(self) -> Dict:
        """Load VPN pool state from file"""
        try:
            if os.path.exists(self.pool_state_file):
                with open(self.pool_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load pool state: {e}")
        
        return {
            "servers": {},  # server_id -> {ip, peers, created_at, last_activity}
            "user_assignments": {}  # user -> {server_id, peer_ip, config}
        }
    
    def _save_pool_state(self):
        """Save VPN pool state to file"""
        try:
            with open(self.pool_state_file, 'w') as f:
                json.dump(self.pool_state, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save pool state: {e}")
    
    def _generate_ssh_key_pair(self) -> Tuple[str, str]:
        """Generate SSH key pair for server access"""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Get private key in OpenSSH format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # Get public key in OpenSSH format
        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        ).decode('utf-8')
        
        return private_pem, public_ssh
    
    async def join_or_create_vpn(self, username: str) -> Dict:
        """Join existing VPN or create new one if needed"""
        print(f"🔍 Finding VPN slot for user: {username}")
        
        # Check if user already has a connection
        if username in self.pool_state["user_assignments"]:
            assignment = self.pool_state["user_assignments"][username]
            server_id = assignment["server_id"]
            
            # Verify server still exists
            if await self._verify_server_exists(server_id):
                print(f"✅ User {username} already connected to server {server_id}")
                return {
                    "status": "already_connected",
                    "server_ip": self.pool_state["servers"][server_id]["ip"],
                    "config": assignment["config"]
                }
            else:
                # Server no longer exists, remove assignment
                del self.pool_state["user_assignments"][username]
                if server_id in self.pool_state["servers"]:
                    del self.pool_state["servers"][server_id]
                self._save_pool_state()
        
        # Find available server
        available_server = await self._find_available_server()
        
        if available_server:
            print(f"🔗 Joining existing server: {available_server['id']}")
            result = await self._add_peer_to_server(username, available_server)
            result["status"] = "joined_existing"
            return result
        else:
            print("🚀 No available servers, creating new one...")
            result = await self._create_new_server(username)
            result["status"] = "created_new"
            return result
    
    async def _find_available_server(self) -> Optional[Dict]:
        """Find a server with available peer slots"""
        for server_id, server_info in self.pool_state["servers"].items():
            peer_count = len(server_info.get("peers", {}))
            if peer_count < self.max_peers_per_server:
                # Verify server is still running
                if await self._verify_server_exists(server_id):
                    return {"id": server_id, **server_info}
                else:
                    # Server no longer exists, will be cleaned up
                    continue
        return None
    
    async def _verify_server_exists(self, server_id: str) -> bool:
        """Verify server still exists in Vultr"""
        try:
            response = requests.get(
                f"{self.api_base}/instances/{server_id}",
                headers=self.headers
            )
            return response.status_code == 200 and response.json()["instance"]["status"] == "active"
        except:
            return False
    
    async def _add_peer_to_server(self, username: str, server: Dict) -> Dict:
        """Add a new peer to existing server via SSH"""
        server_ip = server["ip"]
        server_id = server["id"]
        
        print(f"📡 Connecting to server {server_ip} to add peer {username}")
        
        # Get next available IP
        existing_peers = self.pool_state["servers"][server_id].get("peers", {})
        used_ips = set(peer.get("ip", "").split("/")[0] for peer in existing_peers.values())
        
        for i in range(2, 255):  # 10.0.0.2 onwards
            peer_ip = f"10.0.0.{i}"
            if peer_ip not in used_ips:
                break
        else:
            raise Exception("No available IP addresses")
        
        try:
            # SSH into server using root password
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Use the setup password from server creation
            setup_password = server.get("setup_password", "InstantVPN2024!")  # fallback
            ssh_client.connect(
                hostname=server_ip,
                username="root",
                password=setup_password,
                timeout=30
            )
            
            # Generate keys for new peer
            stdin, stdout, stderr = ssh_client.exec_command(
                f"cd /etc/wireguard && wg genkey | tee clients/{username}_private.key | wg pubkey > clients/{username}_public.key"
            )
            
            # Get the keys
            stdin, stdout, stderr = ssh_client.exec_command(f"cat /etc/wireguard/clients/{username}_private.key")
            private_key = stdout.read().decode().strip()
            
            stdin, stdout, stderr = ssh_client.exec_command(f"cat /etc/wireguard/clients/{username}_public.key")
            public_key = stdout.read().decode().strip()
            
            stdin, stdout, stderr = ssh_client.exec_command(f"cat /etc/wireguard/server_public.key")
            server_public_key = stdout.read().decode().strip()
            
            # Add peer to server config
            peer_config = f"""
[Peer]
PublicKey = {public_key}
AllowedIPs = {peer_ip}/32
"""
            
            stdin, stdout, stderr = ssh_client.exec_command(
                f'echo "{peer_config}" >> /etc/wireguard/wg0.conf'
            )
            
            # Restart WireGuard to apply changes
            stdin, stdout, stderr = ssh_client.exec_command("systemctl restart wg-quick@wg0")
            
            ssh_client.close()
            
            # Create client config
            client_config = f"""[Interface]
PrivateKey = {private_key}
Address = {peer_ip}/24
DNS = 8.8.8.8

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_ip}:{self.wireguard_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
            
            # Update pool state
            if "peers" not in self.pool_state["servers"][server_id]:
                self.pool_state["servers"][server_id]["peers"] = {}
            
            self.pool_state["servers"][server_id]["peers"][username] = {
                "ip": peer_ip,
                "public_key": public_key,
                "added_at": datetime.now().isoformat()
            }
            self.pool_state["servers"][server_id]["last_activity"] = datetime.now().isoformat()
            
            self.pool_state["user_assignments"][username] = {
                "server_id": server_id,
                "peer_ip": peer_ip,
                "config": client_config
            }
            
            self._save_pool_state()
            
            print(f"✅ Added {username} as peer to server {server_id}")
            
            return {
                "server_ip": server_ip,
                "server_id": server_id,
                "peer_ip": peer_ip,
                "config": client_config
            }
            
        except Exception as e:
            raise Exception(f"Failed to add peer: {e}")
    
    async def _create_new_server(self, username: str) -> Dict:
        """Create a new VPN server and add first peer"""
        print("🏗️ Creating new VPN server...")
        
        # Generate setup password
        setup_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # Create cloud-init script
        cloud_init_script = self._generate_cloud_init_script(setup_password)
        cloud_init_b64 = base64.b64encode(cloud_init_script.encode('utf-8')).decode('utf-8')
        
        # Create instance
        instance_data = {
            "region": self.region,
            "plan": "vc2-1c-1gb",
            "os_id": 1743,  # Ubuntu 22.04
            "label": f"vpn-pool-{int(time.time())}",
            "user_data": cloud_init_b64,
            "enable_ipv6": True,
            "backups": "disabled",
            "ddos_protection": False,
            "activation_email": False
        }
        
        response = requests.post(
            f"{self.api_base}/instances",
            headers=self.headers,
            json=instance_data
        )
        
        if response.status_code != 202:
            raise Exception(f"Failed to create instance: {response.text}")
        
        instance = response.json()["instance"]
        server_id = instance["id"]
        
        print(f"✅ Server created! ID: {server_id}")
        
        # Wait for server to be ready
        server_ip = await self._wait_for_server_ready(server_id)
        
        print(f"✅ Server ready! IP: {server_ip}")
        print("⏳ Waiting for WireGuard setup...")
        
        # Wait for setup completion
        await self._wait_for_server_setup(server_ip, setup_password)
        
        # Add to pool state
        self.pool_state["servers"][server_id] = {
            "ip": server_ip,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "setup_password": setup_password,
            "peers": {}
        }
        
        # Add first peer
        server_info = {"id": server_id, **self.pool_state["servers"][server_id]}
        result = await self._add_peer_to_server(username, server_info)
        
        return result
    
    def _generate_cloud_init_script(self, setup_password: str) -> str:
        """Generate cloud-init script for new server"""
        return f"""#!/bin/bash

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1
date

echo "Starting VPN Pool Server setup..."

# Update system
apt-get update
apt-get upgrade -y

# Install WireGuard
apt-get install -y wireguard wireguard-tools

# Set root password
echo 'root:{setup_password}' | chpasswd

# Generate server keys
cd /etc/wireguard
wg genkey | tee server_private.key | wg pubkey > server_public.key
chmod 600 server_private.key

SERVER_PRIVATE_KEY=$(cat server_private.key)
SERVER_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)

# Create base server config
cat > wg0.conf << EOF
[Interface]
PrivateKey = $SERVER_PRIVATE_KEY
Address = 10.0.0.1/24
ListenPort = {self.wireguard_port}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

# Create clients directory
mkdir -p clients

# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Start WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

echo "VPN Pool Server setup completed!"
echo "SUCCESS" > /root/setup_complete
date
"""
    
    async def _wait_for_server_ready(self, server_id: str, max_wait: int = 300) -> str:
        """Wait for server to be active"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.api_base}/instances/{server_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    instance = response.json()["instance"]
                    if instance["status"] == "active" and instance["main_ip"]:
                        return instance["main_ip"]
                    print(f"   Status: {instance['status']}")
                
            except Exception as e:
                print(f"   Waiting... {e}")
            
            await asyncio.sleep(10)
        
        raise Exception("Server startup timed out")
    
    async def _wait_for_server_setup(self, server_ip: str, setup_password: str, max_wait: int = 300):
        """Wait for WireGuard setup completion"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(
                    hostname=server_ip,
                    username="root",
                    password=setup_password,
                    timeout=10
                )
                
                # Check if setup is complete
                stdin, stdout, stderr = ssh_client.exec_command("test -f /root/setup_complete && echo 'READY'")
                result = stdout.read().decode().strip()
                
                if result == "READY":
                    print("✅ Server setup completed!")
                    ssh_client.close()
                    return
                
                ssh_client.close()
                
            except Exception:
                pass
            
            elapsed = int(time.time() - start_time)
            print(f"   Waiting for setup... ({elapsed}s elapsed)")
            await asyncio.sleep(15)
        
        raise Exception("Server setup timed out")
    
    async def disconnect_user(self, username: str) -> Dict:
        """Remove user from VPN"""
        if username not in self.pool_state["user_assignments"]:
            raise Exception(f"User {username} not connected")
        
        assignment = self.pool_state["user_assignments"][username]
        server_id = assignment["server_id"]
        
        if server_id in self.pool_state["servers"]:
            server = self.pool_state["servers"][server_id]
            
            try:
                # Remove peer via SSH
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(
                    hostname=server["ip"],
                    username="root",
                    password=server["setup_password"],
                    timeout=30
                )
                
                # Remove peer from config (this is basic - could be improved)
                public_key = server["peers"][username]["public_key"]
                stdin, stdout, stderr = ssh_client.exec_command(
                    f"wg set wg0 peer {public_key} remove"
                )
                
                # Remove from persistent config (basic approach)
                stdin, stdout, stderr = ssh_client.exec_command(
                    f"grep -v '{public_key}' /etc/wireguard/wg0.conf > /tmp/wg0.conf && mv /tmp/wg0.conf /etc/wireguard/wg0.conf"
                )
                
                ssh_client.close()
                
                # Remove from pool state
                del server["peers"][username]
                server["last_activity"] = datetime.now().isoformat()
                
            except Exception as e:
                print(f"Warning: Failed to remove peer from server: {e}")
        
        # Remove user assignment
        del self.pool_state["user_assignments"][username]
        self._save_pool_state()
        
        # Check if server should be shut down
        await self._cleanup_idle_servers()
        
        return {"success": True, "message": f"User {username} disconnected"}
    
    async def _cleanup_idle_servers(self):
        """Remove servers with no peers that have been idle for 30+ minutes"""
        current_time = datetime.now()
        servers_to_remove = []
        
        for server_id, server in self.pool_state["servers"].items():
            peer_count = len(server.get("peers", {}))
            last_activity = datetime.fromisoformat(server["last_activity"])
            idle_time = current_time - last_activity
            
            if peer_count == 0 and idle_time > timedelta(minutes=30):
                print(f"🗑️ Shutting down idle server {server_id}")
                try:
                    # Destroy server
                    response = requests.delete(
                        f"{self.api_base}/instances/{server_id}",
                        headers=self.headers
                    )
                    if response.status_code == 204:
                        servers_to_remove.append(server_id)
                except Exception as e:
                    print(f"Failed to destroy server {server_id}: {e}")
        
        # Remove from state
        for server_id in servers_to_remove:
            del self.pool_state["servers"][server_id]
        
        if servers_to_remove:
            self._save_pool_state()
    
    async def get_pool_status(self) -> Dict:
        """Get current pool status"""
        active_servers = 0
        total_peers = 0
        
        for server_id, server in self.pool_state["servers"].items():
            if await self._verify_server_exists(server_id):
                active_servers += 1
                total_peers += len(server.get("peers", {}))
        
        return {
            "active_servers": active_servers,
            "total_peers": total_peers,
            "max_peers_per_server": self.max_peers_per_server,
            "available_slots": (active_servers * self.max_peers_per_server) - total_peers
        }
    
    async def get_user_config(self, username: str) -> str:
        """Get config for specific user"""
        if username not in self.pool_state["user_assignments"]:
            raise Exception(f"User {username} not connected")
        
        return self.pool_state["user_assignments"][username]["config"] 