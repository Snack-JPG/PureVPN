#!/usr/bin/env python3
"""
Diagnostic script to check WireGuard server status and peer connectivity
"""

import paramiko
import os
import sys
from dotenv import load_dotenv

def diagnose_server():
    load_dotenv()
    
    server_ip = os.getenv("EXISTING_SERVER_IP")
    ssh_username = os.getenv("SSH_USERNAME", "root")
    ssh_password = os.getenv("SSH_PASSWORD")
    
    if not server_ip or not ssh_password:
        print("❌ Missing server configuration in .env file")
        return False
    
    print(f"🔍 Diagnosing WireGuard server {server_ip}...")
    
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
        
        # Check WireGuard service status
        print("\n🚀 WireGuard Service Status:")
        stdin, stdout, stderr = ssh.exec_command("systemctl status wg-quick@wg0")
        service_status = stdout.read().decode()
        print(service_status)
        
        # Check WireGuard interface details
        print("\n📊 WireGuard Interface Status:")
        stdin, stdout, stderr = ssh.exec_command("wg show wg0")
        wg_status = stdout.read().decode().strip()
        print(wg_status)
        
        # Check IP configuration
        print("\n🔗 Interface IP Configuration:")
        stdin, stdout, stderr = ssh.exec_command("ip addr show wg0")
        ip_config = stdout.read().decode().strip()
        print(ip_config)
        
        # Check current config file
        print("\n📝 Current WireGuard Config File:")
        stdin, stdout, stderr = ssh.exec_command("cat /etc/wireguard/wg0.conf")
        config_content = stdout.read().decode().strip()
        print(config_content)
        
        # Check if peers are properly loaded
        print("\n👥 Active Peers:")
        if "peer:" in wg_status.lower():
            print("✅ Peers are loaded and active")
        else:
            print("❌ No active peers found!")
            
        # Check IP forwarding
        print("\n🌐 IP Forwarding Status:")
        stdin, stdout, stderr = ssh.exec_command("cat /proc/sys/net/ipv4/ip_forward")
        ip_forward = stdout.read().decode().strip()
        print(f"IP Forward enabled: {'✅ YES' if ip_forward == '1' else '❌ NO'}")
        
        # Check iptables rules
        print("\n🔥 Iptables NAT Rules:")
        stdin, stdout, stderr = ssh.exec_command("iptables -t nat -L POSTROUTING -v")
        nat_rules = stdout.read().decode().strip()
        print(nat_rules)
        
        # Check routing
        print("\n🛣️  Routing Table:")
        stdin, stdout, stderr = ssh.exec_command("ip route")
        routes = stdout.read().decode().strip()
        print(routes)
        
        # Test connectivity from server
        print("\n🌍 Server Internet Connectivity:")
        stdin, stdout, stderr = ssh.exec_command("ping -c 2 8.8.8.8")
        ping_result = stdout.read().decode().strip()
        if "2 received" in ping_result:
            print("✅ Server has internet connectivity")
        else:
            print("❌ Server internet connectivity issues!")
            print(ping_result)
            
        # Check network interface
        print("\n🔌 Network Interface Status:")
        stdin, stdout, stderr = ssh.exec_command("ip link show eth0")
        eth_status = stdout.read().decode().strip()
        print(eth_status)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        ssh.close()

if __name__ == "__main__":
    diagnose_server() 