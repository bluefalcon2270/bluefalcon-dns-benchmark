# Version 44.0 | File: core.py | Network and Configuration Management
import os
import time
import socket
import subprocess
import sys
import dns.resolver
import dns.exception

class NetworkUtils:
    @staticmethod
    def get_system_dns():
        system_dns = []
        if sys.platform.startswith('win'):
            try:
                cmd = 'powershell -NoProfile -Command "(Get-WmiObject Win32_NetworkAdapterConfiguration -Filter \'IPEnabled=True AND DefaultIPGateway IS NOT NULL\').DNSServerSearchOrder"'
                output = subprocess.check_output(cmd, text=True, creationflags=0x08000000)
                for line in output.splitlines():
                    ip = line.strip()
                    if ip and ip not in system_dns: system_dns.append(ip)
                if system_dns: return system_dns
            except Exception: pass 
                
        try:
            resolver = dns.resolver.Resolver()
            return resolver.nameservers
        except Exception:
            return []

    @staticmethod
    def tcp_test(ip, port, timeout):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            t0 = time.time()
            sock.connect((ip, port))
            dt = (time.time() - t0) * 1000
            sock.close()
            return True, round(dt)
        except socket.timeout: return False, "TCP Timeout"
        except ConnectionRefusedError: return False, "Refused"
        except OSError as e:
            if e.errno == 10051: return False, "Unreachable"
            return False, "TCP Err"
        except Exception: return False, "TCP Err"

    @staticmethod
    def test_dns_domain(dns_ip, domain, timeout):
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [dns_ip]
        resolver.timeout = timeout
        resolver.lifetime = timeout
        
        try:
            ans = resolver.resolve(domain, "A")
            ips = [x.to_text() for x in ans]
            if not ips: return False, "No IP", 0
                
            ok, t_res = NetworkUtils.tcp_test(ips[0], 443, timeout)
            if ok: return True, f"{t_res} ms", t_res
            else: return False, str(t_res), 0
                
        except dns.resolver.NXDOMAIN: return False, "NXDOMAIN", 0
        except dns.resolver.NoAnswer: return False, "No Answer", 0
        except dns.resolver.NoNameservers: return False, "ServFail", 0
        except dns.exception.Timeout: return False, "DNS Timeout", 0
        except Exception: return False, "?", 0


class ConfigManager:
    @staticmethod
    def get_available_profiles():
        profiles = [f for f in os.listdir('.') if f.startswith('config_') and f.endswith('.txt')]
        if not profiles:
            default = "config_default.txt"
            ConfigManager.save_single_profile(default, {
                "dns_list": [], 
                "domain_list": [],
                "network_list": ["Default_Network", "MCI", "Irancell", "TCI"]
            })
            return [default]
        return sorted(profiles)

    @staticmethod
    def load_single_profile(filename):
        data = {"dns_list": [], "domain_list": [], "network_list": []}
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    current = None
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        if line.lower() == "dns list:": current = "dns_list"; continue
                        elif line.lower() == "domain list:": current = "domain_list"; continue
                        elif line.lower() == "network:": current = "network_list"; continue
                        
                        if current: data[current].append(line)
            except Exception: pass
        return data

    @staticmethod
    def load_multiple_profiles(filenames):
        merged_data = {"dns_list": [], "domain_list": [], "network_list": []}
        seen_dns = set()
        seen_domains = set()
        seen_networks = set()

        for fname in filenames:
            data = ConfigManager.load_single_profile(fname)
            
            for dns in data["dns_list"]:
                ip_only = dns.split()[0] if dns else ""
                if ip_only and ip_only not in seen_dns:
                    seen_dns.add(ip_only)
                    merged_data["dns_list"].append(dns)
                    
            for dom in data["domain_list"]:
                if dom not in seen_domains:
                    seen_domains.add(dom)
                    merged_data["domain_list"].append(dom)

            for net in data.get("network_list", []):
                if net not in seen_networks:
                    seen_networks.add(net)
                    merged_data["network_list"].append(net)
                    
        return merged_data

    @staticmethod
    def save_single_profile(filename, data):
        with open(filename, "w", encoding="utf-8") as f:
            f.write("DNS List:\n")
            for item in data.get("dns_list", []): f.write(f"{item}\n")
            f.write("\n\nDomain List:\n")
            for item in data.get("domain_list", []): f.write(f"{item}\n")
            f.write("\n\nNetwork:\n")
            for item in data.get("network_list", []): f.write(f"{item}\n")

    @staticmethod
    def parse_dns_list(lines, system_dns_list):
        parsed = []
        for idx, line in enumerate(lines):
            parts = line.split(maxsplit=1)
            if not parts: continue
            ip = parts[0]
            name = parts[1] if len(parts) > 1 else ""
            is_system = ip in system_dns_list
            parsed.append({
                "ip": ip, "name": name, "row_id": f"row_{idx}", 
                "dup_id": None, "is_system": is_system
            })
        return parsed

    @staticmethod
    def format_domain(raw_domain):
        try:
            clean = raw_domain.replace("http://", "").replace("https://", "")
            parts = clean.split('.')
            main_name = parts[-2] if len(parts) >= 2 else parts[0]
            return main_name.capitalize()
        except Exception:
            return str(raw_domain).capitalize()