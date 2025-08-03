#!/usr/bin/env python3
"""
Fix WireGuard network interface from eth0 to enp1s0
"""

import paramiko
import os
import sys
from dotenv import load_dotenv

def fix_interface():
    load_dotenv()
    
    server_ip = os.getenv("EXISTING_SERVER_IP")
    ssh_username = os.getenv("SSH_USERNAME", "root")
    ssh_password = os.getenv("SSH_PASSWORD")
    
    print(f"🔧 Fixing network interface on {server_ip}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(
            hostname=server_ip,
            username=ssh_username,
            password=ssh_password,
            timeout=30
        )
        
        print("✅ Connected to server")
        
        # Get current config
        stdin, stdout, stderr = ssh.exec_command("cat /etc/wireguard/wg0.conf")
        current_config = stdout.read().decode()
        
        # Replace eth0 with enp1s0
        fixed_config = current_config.replace("eth0", "enp1s0")
        
        print("📝 Updating WireGuard config with correct interface...")
        
        # Write fixed config
        stdin, stdout, stderr = ssh.exec_command(f"cat > /etc/wireguard/wg0.conf << 'EOF'\n{fixed_config}EOF")
        stdout.read()
        
        # Stop WireGuard
        print("🛑 Stopping WireGuard...")
        stdin, stdout, stderr = ssh.exec_command("systemctl stop wg-quick@wg0")
        stdout.read()
        
        # Clear old iptables rules
        print("🧹 Clearing old iptables rules...")
        stdin, stdout, stderr = ssh.exec_command("iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || echo 'Rule not found'")
        stdout.read()
        
        # Start WireGuard with new config
        print("🚀 Starting WireGuard with fixed config...")
        stdin, stdout, stderr = ssh.exec_command("systemctl start wg-quick@wg0")
        start_output = stdout.read().decode()
        start_error = stderr.read().decode()
        
        # Check status
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active wg-quick@wg0")
        status = stdout.read().decode().strip()
        
        if status == "active":
            print("✅ WireGuard restarted successfully!")
            
            # Verify iptables rules
            print("🔍 Checking new iptables rules...")
            stdin, stdout, stderr = ssh.exec_command("iptables -t nat -L POSTROUTING -v | grep MASQUERADE")
            rules = stdout.read().decode().strip()
            print("New NAT rules:")
            print(rules)
            
            # Show current peers
            stdin, stdout, stderr = ssh.exec_command("wg show")
            wg_info = stdout.read().decode().strip()
            print("\n📊 WireGuard status:")
            print(wg_info)
            
            return True
        else:
            print(f"❌ Failed to restart WireGuard. Status: {status}")
            if start_error:
                print(f"Error: {start_error}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        ssh.close()

if __name__ == "__main__":
    success = fix_interface()
    if success:
        print("\n🎉 **FIXED!** Try connecting to your VPN again!")
        print("💡 You should now have internet connectivity through the VPN.")
    else:
        print("\n❌ Fix failed. Check the logs above.")
        sys.exit(1) 