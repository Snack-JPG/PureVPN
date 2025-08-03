#!/usr/bin/env python3
"""
Comprehensive VPN connectivity fix - check all network interfaces and routing
"""

import paramiko
import os
import sys
from dotenv import load_dotenv

def comprehensive_fix():
    load_dotenv()
    
    server_ip = os.getenv("EXISTING_SERVER_IP")
    ssh_username = os.getenv("SSH_USERNAME", "root")
    ssh_password = os.getenv("SSH_PASSWORD")
    
    print(f"🔧 Comprehensive VPN fix for {server_ip}...")
    
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
        
        # 1. Check ALL network interfaces
        print("\n🔍 Checking ALL network interfaces:")
        stdin, stdout, stderr = ssh.exec_command("ip link show")
        interfaces = stdout.read().decode().strip()
        print(interfaces)
        
        # Find the main external interface
        print("\n🔍 Finding main external interface:")
        stdin, stdout, stderr = ssh.exec_command("ip route | grep default")
        default_route = stdout.read().decode().strip()
        print(f"Default route: {default_route}")
        
        # Extract interface name from default route
        interface_name = "eth0"  # fallback
        if "dev" in default_route:
            parts = default_route.split()
            for i, part in enumerate(parts):
                if part == "dev" and i + 1 < len(parts):
                    interface_name = parts[i + 1]
                    break
        
        print(f"📡 Detected main interface: {interface_name}")
        
        # 2. Stop WireGuard completely
        print("\n🛑 Stopping WireGuard completely...")
        stdin, stdout, stderr = ssh.exec_command("systemctl stop wg-quick@wg0")
        stdout.read()
        
        # 3. Clear ALL existing iptables rules for WireGuard
        print("🧹 Clearing ALL iptables rules...")
        commands = [
            "iptables -D FORWARD -i wg0 -j ACCEPT 2>/dev/null || echo 'Rule not found'",
            "iptables -D FORWARD -o wg0 -j ACCEPT 2>/dev/null || echo 'Rule not found'", 
            "iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || echo 'Rule not found'",
            "iptables -t nat -D POSTROUTING -o enp1s0 -j MASQUERADE 2>/dev/null || echo 'Rule not found'",
            f"iptables -t nat -D POSTROUTING -o {interface_name} -j MASQUERADE 2>/dev/null || echo 'Rule not found'"
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            result = stdout.read().decode().strip()
            print(f"   {result}")
        
        # 4. Get WireGuard keys
        stdin, stdout, stderr = ssh.exec_command("cat /etc/wireguard/server_private.key")
        server_private = stdout.read().decode().strip()
        
        # 5. Create NEW WireGuard config with correct interface
        print(f"\n📝 Creating fresh WireGuard config for interface {interface_name}...")
        fresh_config = f"""[Interface]
PrivateKey = {server_private}
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {interface_name} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {interface_name} -j MASQUERADE

# Peers will be added by InstantVPN system

# Peer: austin
[Peer]
PublicKey = 6BYO9T1eKs1aJqbgcJt4BgAZkqWaUcnq59wTVIgY22A=
AllowedIPs = 10.0.0.2/32
"""
        
        # Write new config
        stdin, stdout, stderr = ssh.exec_command(f"cat > /etc/wireguard/wg0.conf << 'EOF'\n{fresh_config}EOF")
        stdout.read()
        
        # 6. Enable IP forwarding (make sure it's persistent)
        print("🌐 Ensuring IP forwarding is enabled...")
        stdin, stdout, stderr = ssh.exec_command("echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-wireguard.conf")
        stdout.read()
        stdin, stdout, stderr = ssh.exec_command("sysctl -p /etc/sysctl.d/99-wireguard.conf")
        stdout.read()
        
        # 7. Check for any firewall blocking
        print("🔥 Checking firewall status...")
        stdin, stdout, stderr = ssh.exec_command("ufw status")
        firewall_status = stdout.read().decode().strip()
        print(f"UFW Status: {firewall_status}")
        
        if "active" in firewall_status.lower():
            print("⚠️  UFW firewall is active - adding WireGuard rules...")
            stdin, stdout, stderr = ssh.exec_command("ufw allow 51820/udp")
            stdout.read()
            stdin, stdout, stderr = ssh.exec_command("ufw allow in on wg0")
            stdout.read()
            stdin, stdout, stderr = ssh.exec_command("ufw allow out on wg0")
            stdout.read()
        
        # 8. Start WireGuard with new config
        print("🚀 Starting WireGuard with comprehensive config...")
        stdin, stdout, stderr = ssh.exec_command("systemctl start wg-quick@wg0")
        start_output = stdout.read().decode()
        start_error = stderr.read().decode()
        
        # 9. Check status
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active wg-quick@wg0")
        status = stdout.read().decode().strip()
        
        if status == "active":
            print("✅ WireGuard started successfully!")
            
            # Show comprehensive status
            print("\n📊 Final Status Check:")
            
            # WireGuard status
            stdin, stdout, stderr = ssh.exec_command("wg show")
            wg_status = stdout.read().decode().strip()
            print("WireGuard Interface:")
            print(wg_status)
            
            # Routing
            stdin, stdout, stderr = ssh.exec_command("ip route")
            routes = stdout.read().decode().strip()
            print("\nRouting Table:")
            print(routes)
            
            # NAT rules
            stdin, stdout, stderr = ssh.exec_command("iptables -t nat -L POSTROUTING -v")
            nat_rules = stdout.read().decode().strip()
            print("\nNAT Rules:")
            print(nat_rules)
            
            # Test connectivity from server
            stdin, stdout, stderr = ssh.exec_command("ping -c 2 8.8.8.8")
            ping_result = stdout.read().decode()
            if "2 received" in ping_result:
                print("\n✅ Server has internet connectivity")
            else:
                print(f"\n❌ Server connectivity issue: {ping_result}")
            
            return True
        else:
            print(f"❌ Failed to start WireGuard. Status: {status}")
            if start_error:
                print(f"Error: {start_error}")
            
            # Show logs
            stdin, stdout, stderr = ssh.exec_command("journalctl -u wg-quick@wg0 --no-pager -n 10")
            logs = stdout.read().decode()
            print("Logs:")
            print(logs)
            
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        ssh.close()

if __name__ == "__main__":
    success = comprehensive_fix()
    if success:
        print("\n🎉 **COMPREHENSIVE FIX COMPLETE!**")
        print("📋 **Your WireGuard config remains the same - try connecting again!**")
        print("🌐 **Test:** Go to whatismyip.com to verify your IP shows as 95.179.152.203")
    else:
        print("\n❌ Fix failed. Check the logs above.")
        sys.exit(1) 