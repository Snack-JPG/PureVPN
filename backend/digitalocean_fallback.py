import requests
import time
import json
import os
import asyncio
import base64
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import paramiko

class DigitalOceanVPNManager:
    """Fallback VPN manager using DigitalOcean API"""
    
    def __init__(self):
        self.do_token = os.getenv("DIGITALOCEAN_TOKEN")
        self.region = os.getenv("SERVER_REGION", "nyc1")
        self.wireguard_port = int(os.getenv("WIREGUARD_PORT", "51820"))
        self.max_peers_per_server = 3
        
        self.api_base = "https://api.digitalocean.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.do_token}",
            "Content-Type": "application/json"
        }
        
        # Pool state file
        self.pool_state_file = "vpn_pool_state_do.json"
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
            "servers": {},
            "user_assignments": {}
        }
    
    def _save_pool_state(self):
        """Save VPN pool state to file"""
        try:
            with open(self.pool_state_file, 'w') as f:
                json.dump(self.pool_state, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save pool state: {e}")
    
    async def join_or_create_vpn(self, username: str) -> Dict:
        """Join existing VPN or create new one if needed"""
        print(f"🔍 [DigitalOcean] Finding VPN slot for user: {username}")
        
        # Check if user already has a connection
        if username in self.pool_state["user_assignments"]:
            assignment = self.pool_state["user_assignments"][username]
            server_id = assignment["server_id"]
            
            if await self._verify_server_exists(server_id):
                print(f"✅ User {username} already connected to server {server_id}")
                return {
                    "status": "already_connected",
                    "server_ip": self.pool_state["servers"][server_id]["ip"],
                    "config": assignment["config"]
                }
            else:
                del self.pool_state["user_assignments"][username]
                if server_id in self.pool_state["servers"]:
                    del self.pool_state["servers"][server_id]
                self._save_pool_state()
        
        # Find available server
        available_server = await self._find_available_server()
        
        if available_server:
            print(f"🔗 Joining existing DigitalOcean server: {available_server['id']}")
            result = await self._add_peer_to_server(username, available_server)
            result["status"] = "joined_existing"
            return result
        else:
            print("🚀 No available servers, creating new DigitalOcean droplet...")
            result = await self._create_new_server(username)
            result["status"] = "created_new"
            return result
    
    async def _create_new_server(self, username: str) -> Dict:
        """Create a new DigitalOcean droplet"""
        print("🏗️ Creating new DigitalOcean VPN server...")
        
        # Generate setup password
        setup_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # Create cloud-init script (same as Vultr)
        cloud_init_script = self._generate_cloud_init_script(setup_password)
        
        # Create droplet
        droplet_data = {
            "name": f"vpn-pool-{int(time.time())}",
            "region": self.region,
            "size": "s-1vcpu-1gb",  # $6/month
            "image": "ubuntu-22-04-x64",
            "user_data": cloud_init_script,
            "monitoring": False,
            "ipv6": False,
            "vpc_uuid": None,
            "ssh_keys": [],
            "backups": False,
            "tags": ["vpn-pool"]
        }
        
        response = requests.post(
            f"{self.api_base}/droplets",
            headers=self.headers,
            json=droplet_data
        )
        
        if response.status_code != 202:
            raise Exception(f"Failed to create DigitalOcean droplet: {response.text}")
        
        droplet = response.json()["droplet"]
        server_id = str(droplet["id"])
        
        print(f"✅ DigitalOcean droplet created! ID: {server_id}")
        
        # Wait for droplet to be ready
        server_ip = await self._wait_for_server_ready(server_id)
        
        print(f"✅ Droplet ready! IP: {server_ip}")
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
    
    async def _wait_for_server_ready(self, server_id: str, max_wait: int = 300) -> str:
        """Wait for DigitalOcean droplet to be active"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.api_base}/droplets/{server_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    droplet = response.json()["droplet"]
                    if droplet["status"] == "active" and droplet["networks"]["v4"]:
                        public_ip = None
                        for network in droplet["networks"]["v4"]:
                            if network["type"] == "public":
                                public_ip = network["ip_address"]
                                break
                        if public_ip:
                            return public_ip
                    print(f"   Status: {droplet['status']}")
                
            except Exception as e:
                print(f"   Waiting... {e}")
            
            await asyncio.sleep(10)
        
        raise Exception("DigitalOcean droplet startup timed out")
    
    # Reuse the same methods from VPNPoolManager for peer management
    async def _add_peer_to_server(self, username: str, server: Dict) -> Dict:
        """Add a new peer to existing server via SSH (same logic as Vultr)"""
        # ... same implementation as VPNPoolManager
        pass
    
    def _generate_cloud_init_script(self, setup_password: str) -> str:
        """Generate cloud-init script for new server (same as Vultr)"""
        # ... same implementation as VPNPoolManager
        pass
    
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