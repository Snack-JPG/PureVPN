import paramiko
import time
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

class ExistingServerVPNManager:
    """Simplified VPN manager for existing server - no provisioning needed"""
    
    def __init__(self):
        # Server connection details (will be set from environment)
        self.server_ip = os.getenv("EXISTING_SERVER_IP")
        self.ssh_username = os.getenv("SSH_USERNAME", "root")
        self.ssh_password = os.getenv("SSH_PASSWORD")
        self.ssh_key_path = os.getenv("SSH_KEY_PATH")
        self.wireguard_port = int(os.getenv("WIREGUARD_PORT", "51820"))
        
        # Pool state file
        self.pool_state_file = "existing_server_state.json"
        self.pool_state = self._load_pool_state()
        
        # Validate configuration
        if not self.server_ip:
            raise Exception("EXISTING_SERVER_IP must be set in environment")
        if not (self.ssh_password or self.ssh_key_path):
            raise Exception("Either SSH_PASSWORD or SSH_KEY_PATH must be set")
    
    def _load_pool_state(self) -> Dict:
        """Load current server state"""
        try:
            if os.path.exists(self.pool_state_file):
                with open(self.pool_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load state: {e}")
        
        return {
            "server_ip": None,
            "peers": {},  # username -> {ip, public_key, added_at}
            "last_activity": datetime.now().isoformat()
        }
    
    def _save_pool_state(self):
        """Save current server state"""
        try:
            with open(self.pool_state_file, 'w') as f:
                json.dump(self.pool_state, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save state: {e}")
    
    def _get_ssh_client(self) -> paramiko.SSHClient:
        """Create SSH connection to the server"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                # Use SSH key
                ssh.connect(
                    hostname=self.server_ip,
                    username=self.ssh_username,
                    key_filename=self.ssh_key_path,
                    timeout=30
                )
            elif self.ssh_password:
                # Use password
                ssh.connect(
                    hostname=self.server_ip,
                    username=self.ssh_username,
                    password=self.ssh_password,
                    timeout=30
                )
            else:
                raise Exception("No SSH authentication method available")
                
            return ssh
        except Exception as e:
            ssh.close()
            raise Exception(f"SSH connection failed: {e}")
    
    async def join_or_create_vpn(self, username: str) -> Dict:
        """Add user to existing VPN server"""
        print(f"🔗 Adding user {username} to existing server {self.server_ip}")
        
        # Check if user already exists
        if username in self.pool_state["peers"]:
            print(f"✅ User {username} already has access")
            peer_info = self.pool_state["peers"][username]
            config = await self._generate_client_config(username, peer_info)
            return {
                "status": "already_connected",
                "server_ip": self.server_ip,
                "config": config
            }
        
        # Add new peer
        result = await self._add_peer_to_existing_server(username)
        result["status"] = "joined_existing"
        return result
    
    async def _add_peer_to_existing_server(self, username: str) -> Dict:
        """Add a new peer to the existing WireGuard server"""
        ssh = None
        try:
            ssh = self._get_ssh_client()
            
            # Get next available IP (10.0.0.2, 10.0.0.3, etc.)
            used_ips = set()
            for peer in self.pool_state["peers"].values():
                if "ip" in peer:
                    used_ips.add(peer["ip"].split("/")[0])
            
            peer_ip = None
            for i in range(2, 255):
                candidate_ip = f"10.0.0.{i}"
                if candidate_ip not in used_ips:
                    peer_ip = candidate_ip
                    break
            
            if not peer_ip:
                raise Exception("No available IP addresses")
            
            print(f"🔑 Generating keys for {username} (IP: {peer_ip})")
            
            # Create client directory if it doesn't exist
            stdin, stdout, stderr = ssh.exec_command("mkdir -p /etc/wireguard/clients")
            
            # Generate client keys
            stdin, stdout, stderr = ssh.exec_command(
                f"cd /etc/wireguard && wg genkey | tee clients/{username}_private.key | wg pubkey > clients/{username}_public.key"
            )
            
            # Get the generated keys
            stdin, stdout, stderr = ssh.exec_command(f"cat /etc/wireguard/clients/{username}_private.key")
            private_key = stdout.read().decode().strip()
            
            stdin, stdout, stderr = ssh.exec_command(f"cat /etc/wireguard/clients/{username}_public.key")
            public_key = stdout.read().decode().strip()
            
            # Get server public key
            stdin, stdout, stderr = ssh.exec_command("cat /etc/wireguard/server_public.key || wg show wg0 public-key")
            server_public_key = stdout.read().decode().strip()
            
            if not server_public_key:
                # Try to extract from wg0.conf
                stdin, stdout, stderr = ssh.exec_command("grep 'PrivateKey' /etc/wireguard/wg0.conf | cut -d'=' -f2 | tr -d ' ' | wg pubkey")
                server_public_key = stdout.read().decode().strip()
            
            if not server_public_key:
                raise Exception("Could not get server public key")
            
            print(f"🔧 Adding peer to WireGuard config")
            
            # Add peer to server config
            peer_config = f"""
# Peer: {username}
[Peer]
PublicKey = {public_key}
AllowedIPs = {peer_ip}/32
"""
            
            # Append to wg0.conf
            stdin, stdout, stderr = ssh.exec_command(f'echo "{peer_config}" >> /etc/wireguard/wg0.conf')
            
            # Add peer to running interface (if WireGuard is running)
            stdin, stdout, stderr = ssh.exec_command(f"wg set wg0 peer {public_key} allowed-ips {peer_ip}/32")
            
            # Generate client config
            client_config = f"""[Interface]
PrivateKey = {private_key}
Address = {peer_ip}/24
DNS = 8.8.8.8, 1.1.1.1

[Peer]
PublicKey = {server_public_key}
Endpoint = {self.server_ip}:{self.wireguard_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
            
            # Update state
            self.pool_state["peers"][username] = {
                "ip": peer_ip,
                "public_key": public_key,
                "private_key": private_key,
                "added_at": datetime.now().isoformat()
            }
            self.pool_state["server_ip"] = self.server_ip
            self.pool_state["last_activity"] = datetime.now().isoformat()
            self._save_pool_state()
            
            print(f"✅ Added {username} to VPN server")
            
            return {
                "server_ip": self.server_ip,
                "peer_ip": peer_ip,
                "config": client_config
            }
            
        finally:
            if ssh:
                ssh.close()
    
    async def _generate_client_config(self, username: str, peer_info: Dict) -> str:
        """Generate client config from stored peer info"""
        ssh = None
        try:
            ssh = self._get_ssh_client()
            
            # Get server public key
            stdin, stdout, stderr = ssh.exec_command("cat /etc/wireguard/server_public.key || wg show wg0 public-key")
            server_public_key = stdout.read().decode().strip()
            
            if not server_public_key:
                stdin, stdout, stderr = ssh.exec_command("grep 'PrivateKey' /etc/wireguard/wg0.conf | cut -d'=' -f2 | tr -d ' ' | wg pubkey")
                server_public_key = stdout.read().decode().strip()
            
            client_config = f"""[Interface]
PrivateKey = {peer_info['private_key']}
Address = {peer_info['ip']}/24
DNS = 8.8.8.8, 1.1.1.1

[Peer]
PublicKey = {server_public_key}
Endpoint = {self.server_ip}:{self.wireguard_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
            return client_config
            
        finally:
            if ssh:
                ssh.close()
    
    async def disconnect_user(self, username: str) -> Dict:
        """Remove user from VPN"""
        if username not in self.pool_state["peers"]:
            raise Exception(f"User {username} not found")
        
        ssh = None
        try:
            ssh = self._get_ssh_client()
            peer_info = self.pool_state["peers"][username]
            public_key = peer_info["public_key"]
            
            print(f"🗑️ Removing {username} from VPN")
            
            # Remove from running interface
            stdin, stdout, stderr = ssh.exec_command(f"wg set wg0 peer {public_key} remove")
            
            # Remove from config file (basic approach)
            stdin, stdout, stderr = ssh.exec_command(f"sed -i '/# Peer: {username}/,/^$/d' /etc/wireguard/wg0.conf")
            
            # Remove client files
            stdin, stdout, stderr = ssh.exec_command(f"rm -f /etc/wireguard/clients/{username}_*")
            
            # Remove from state
            del self.pool_state["peers"][username]
            self.pool_state["last_activity"] = datetime.now().isoformat()
            self._save_pool_state()
            
            print(f"✅ Removed {username} from VPN")
            return {"success": True, "message": f"User {username} removed"}
            
        finally:
            if ssh:
                ssh.close()
    
    async def get_pool_status(self) -> Dict:
        """Get current server status"""
        peer_count = len(self.pool_state["peers"])
        
        return {
            "active_servers": 1 if self.server_ip else 0,
            "total_peers": peer_count,
            "max_peers_per_server": 50,  # Reasonable limit for existing server
            "available_slots": 50 - peer_count,
            "server_ip": self.server_ip
        }
    
    async def get_user_config(self, username: str) -> str:
        """Get config for specific user"""
        if username not in self.pool_state["peers"]:
            raise Exception(f"User {username} not found")
        
        peer_info = self.pool_state["peers"][username]
        return await self._generate_client_config(username, peer_info)
    
    async def test_connection(self) -> Dict:
        """Test SSH connection to server"""
        ssh = None
        try:
            ssh = self._get_ssh_client()
            
            # Test basic commands
            stdin, stdout, stderr = ssh.exec_command("whoami && date")
            output = stdout.read().decode().strip()
            
            # Check if WireGuard is installed
            stdin, stdout, stderr = ssh.exec_command("which wg")
            wg_installed = len(stdout.read().decode().strip()) > 0
            
            # Check if WireGuard is running
            stdin, stdout, stderr = ssh.exec_command("systemctl is-active wg-quick@wg0")
            wg_running = "active" in stdout.read().decode().strip()
            
            return {
                "connection": "success",
                "server_info": output,
                "wireguard_installed": wg_installed,
                "wireguard_running": wg_running
            }
            
        except Exception as e:
            return {
                "connection": "failed",
                "error": str(e)
            }
        finally:
            if ssh:
                ssh.close() 