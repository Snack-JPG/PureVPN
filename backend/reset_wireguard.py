#!/usr/bin/env python3
"""
Script to reset WireGuard on existing server - remove old peers and prepare for InstantVPN
"""

import paramiko
import os
import sys
from dotenv import load_dotenv

def reset_wireguard_server():
    load_dotenv()
    
    server_ip = os.getenv("EXISTING_SERVER_IP")
    ssh_username = os.getenv("SSH_USERNAME", "root")
    ssh_password = os.getenv("SSH_PASSWORD")
    
    if not server_ip or not ssh_password:
        print("❌ Missing server configuration in .env file")
        return False
    
    print(f"🔧 Connecting to server {server_ip} to reset WireGuard...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to server
        ssh.connect(
            hostname=server_ip,
            username=ssh_username,
            password=ssh_password,
            timeout=30
        )
        
        print("✅ Connected to server")
        
        # Completely stop and remove existing WireGuard interface
        print("🛑 Stopping and removing existing WireGuard interface...")
        stdin, stdout, stderr = ssh.exec_command("systemctl stop wg-quick@wg0")
        stdout.read()
        
        # Force remove interface if it exists
        stdin, stdout, stderr = ssh.exec_command("ip link delete wg0 2>/dev/null || echo 'Interface not found'")
        remove_result = stdout.read().decode().strip()
        print(f"   Interface removal: {remove_result}")
        
        # Kill any remaining WireGuard processes
        stdin, stdout, stderr = ssh.exec_command("pkill -f wg-quick || echo 'No wg-quick processes found'")
        stdout.read()
        
        # Backup existing config
        print("💾 Backing up existing config...")
        stdin, stdout, stderr = ssh.exec_command("cp /etc/wireguard/wg0.conf /etc/wireguard/wg0.conf.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo 'No existing config'")
        backup_result = stdout.read().decode().strip()
        print(f"   Backup: {backup_result}")
        
        # Get or generate server keys
        print("🔑 Setting up server keys...")
        stdin, stdout, stderr = ssh.exec_command("cd /etc/wireguard && ls server_private.key 2>/dev/null || echo 'missing'")
        has_server_key = "server_private.key" in stdout.read().decode()
        
        if not has_server_key:
            print("   Generating new server keys...")
            stdin, stdout, stderr = ssh.exec_command("cd /etc/wireguard && wg genkey | tee server_private.key | wg pubkey > server_public.key")
            stdout.read()
        else:
            print("   Using existing server keys")
        
        # Get server keys
        stdin, stdout, stderr = ssh.exec_command("cat /etc/wireguard/server_private.key")
        server_private = stdout.read().decode().strip()
        
        stdin, stdout, stderr = ssh.exec_command("cat /etc/wireguard/server_public.key")
        server_public = stdout.read().decode().strip()
        
        print(f"   Server public key: {server_public[:20]}...")
        
        # Create fresh WireGuard config
        print("📝 Creating fresh WireGuard configuration...")
        fresh_config = f"""[Interface]
PrivateKey = {server_private}
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Peers will be added by InstantVPN system
"""
        
        # Write new config
        stdin, stdout, stderr = ssh.exec_command(f"cat > /etc/wireguard/wg0.conf << 'EOF'\n{fresh_config}EOF")
        stdout.read()
        
        # Set permissions
        stdin, stdout, stderr = ssh.exec_command("chmod 600 /etc/wireguard/server_private.key /etc/wireguard/wg0.conf")
        stdout.read()
        
        # Create clients directory
        print("📁 Setting up clients directory...")
        stdin, stdout, stderr = ssh.exec_command("mkdir -p /etc/wireguard/clients && rm -f /etc/wireguard/clients/*")
        stdout.read()
        
        # Enable IP forwarding
        print("🌐 Enabling IP forwarding...")
        stdin, stdout, stderr = ssh.exec_command("echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-wireguard.conf && sysctl -p /etc/sysctl.d/99-wireguard.conf")
        stdout.read()
        
        # Clean up any existing iptables rules (optional)
        print("🧹 Cleaning up old iptables rules...")
        stdin, stdout, stderr = ssh.exec_command("iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || echo 'Rule not found'")
        stdout.read()
        
        # Wait a moment before starting
        print("⏳ Waiting before starting WireGuard...")
        stdin, stdout, stderr = ssh.exec_command("sleep 2")
        stdout.read()
        
        # Start WireGuard
        print("🚀 Starting WireGuard service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl enable wg-quick@wg0")
        stdout.read()
        
        stdin, stdout, stderr = ssh.exec_command("systemctl start wg-quick@wg0")
        start_output = stdout.read().decode()
        start_error = stderr.read().decode()
        
        # Check status
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active wg-quick@wg0")
        status = stdout.read().decode().strip()
        
        if status == "active":
            print("✅ WireGuard is running successfully!")
            
            # Show interface info
            stdin, stdout, stderr = ssh.exec_command("wg show")
            wg_info = stdout.read().decode().strip()
            print("📊 WireGuard interface info:")
            print(wg_info)
            
            # Show IP info
            stdin, stdout, stderr = ssh.exec_command("ip addr show wg0")
            ip_info = stdout.read().decode().strip()
            print("🔗 Interface IP configuration:")
            print(ip_info)
            
            return True
        else:
            print(f"❌ WireGuard failed to start. Status: {status}")
            
            if start_error:
                print(f"Start error: {start_error}")
            
            # Show detailed error logs
            stdin, stdout, stderr = ssh.exec_command("journalctl -u wg-quick@wg0 --no-pager -n 20")
            logs = stdout.read().decode()
            print("Recent logs:")
            print(logs)
            
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        ssh.close()

if __name__ == "__main__":
    print("🔄 Resetting WireGuard server for InstantVPN...")
    success = reset_wireguard_server()
    
    if success:
        print("\n✅ Server reset complete! Ready for InstantVPN.")
        print("🎯 Next: Start your InstantVPN backend and try joining the VPN.")
    else:
        print("\n❌ Server reset failed. Check the logs above.")
        sys.exit(1) 