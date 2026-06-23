# ==========================================
# BlueFalcon DNS Benchmark Pro - Core Module
# ==========================================
import sys
import time
import socket
import subprocess
import ctypes
import logging
from pathlib import Path
import dns.resolver

APP_VERSION = "2.2.0"

# Setup Paths
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "bluefalcon-app.log"

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BlueFalconCore")

class AppUtils:
    @staticmethod
    def get_resource_path(relative_path: str) -> Path:
        """ Resolves absolute path to bundled resources for PyInstaller. """
        try:
            base_path = Path(sys._MEIPASS)
        except Exception:
            base_path = BASE_DIR
        return base_path / relative_path

    @staticmethod
    def is_admin() -> bool:
        """ Check if the application has Windows Administrator privileges. """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def check_internet_connection() -> bool:
        """ Pre-flight check to see if the user is completely offline. """
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=2.0)
            return True
        except OSError:
            return False

class NetworkUtils:
    @staticmethod
    def get_system_dns() -> list[str]:
        system_dns = []
        try:
            cmd = 'powershell -NoProfile -Command "(Get-WmiObject Win32_NetworkAdapterConfiguration -Filter \'IPEnabled=True AND DefaultIPGateway IS NOT NULL\').DNSServerSearchOrder"'
            output = subprocess.check_output(cmd, text=True, creationflags=0x08000000)
            for line in output.splitlines():
                ip = line.strip()
                if ip and ip not in system_dns: 
                    system_dns.append(ip)
            if system_dns: 
                return system_dns
        except Exception as e:
            logger.warning(f"Failed to fetch System DNS via PowerShell: {e}")
                
        try:
            resolver = dns.resolver.Resolver()
            return resolver.nameservers
        except Exception as e:
            logger.warning(f"Failed to fetch System DNS via fallback: {e}")
            return []

    @staticmethod
    def tcp_test(ip: str, port: int, timeout: float) -> tuple[bool, str | int]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            t0 = time.time()
            sock.connect((ip, port))
            dt = (time.time() - t0) * 1000
            sock.close()
            return True, round(dt)
        except socket.timeout: 
            return False, "TCP Timeout"
        except ConnectionRefusedError: 
            return False, "Refused"
        except OSError as e:
            if e.errno == 10051: return False, "Unreachable"
            return False, "TCP Err"
        except Exception: 
            return False, "TCP Err"

    @staticmethod
    def test_dns_domain(dns_ip: str, domain: str, timeout: float) -> tuple[bool, str, int]:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [dns_ip]
        resolver.timeout = timeout
        resolver.lifetime = timeout
        
        try:
            ans = resolver.resolve(domain, "A")
            ips = [x.to_text() for x in ans]
            if not ips: 
                return False, "No IP", 0
                
            ok, t_res = NetworkUtils.tcp_test(ips[0], 443, timeout)
            if ok: 
                return True, f"{t_res} ms", t_res
            else: 
                return False, str(t_res), 0
                
        except dns.resolver.NXDOMAIN: return False, "NXDOMAIN", 0
        except dns.resolver.NoAnswer: return False, "No Answer", 0
        except dns.resolver.NoNameservers: return False, "ServFail", 0
        except dns.exception.Timeout: return False, "DNS Timeout", 0
        except Exception as e: return False, "?", 0


class ConfigManager:
    @staticmethod
    def get_available_profiles() -> list[str]:
        profiles = [p.name for p in BASE_DIR.glob("config_*.txt") if p.is_file()]
        if not profiles:
            default = "config_default.txt"
            ConfigManager.save_single_profile(default, {
                "dns_list": ["1.1.1.1 Cloudflare", "8.8.8.8 Google"], 
                "domain_list": ["google.com", "cloudflare.com"],
                "network_list": ["Default_Network"]
            })
            return [default]
        return sorted(profiles)

    @staticmethod
    def load_single_profile(filename: str) -> dict:
        data = {"dns_list": [], "domain_list": [], "network_list": []}
        filepath = BASE_DIR / filename
        if filepath.exists():
            try:
                with filepath.open("r", encoding="utf-8") as f:
                    current = None
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        if line.lower() == "dns list:": current = "dns_list"; continue
                        elif line.lower() == "domain list:": current = "domain_list"; continue
                        elif line.lower() == "network:": current = "network_list"; continue
                        
                        if current: data[current].append(line)
            except Exception as e:
                logger.error(f"Failed to load profile {filename}: {e}")
        return data

    @staticmethod
    def load_multiple_profiles(filenames: list[str]) -> dict:
        merged_data = {"dns_list": [], "domain_list": [], "network_list": []}
        seen_dns = set()
        seen_domains = set()
        seen_networks = set()

        for fname in filenames:
            data = ConfigManager.load_single_profile(fname)
            
            for dns in data.get("dns_list", []):
                ip_only = dns.split()[0] if dns else ""
                if ip_only and ip_only not in seen_dns:
                    seen_dns.add(ip_only)
                    merged_data["dns_list"].append(dns)
                    
            for dom in data.get("domain_list", []):
                if dom not in seen_domains:
                    seen_domains.add(dom)
                    merged_data["domain_list"].append(dom)

            for net in data.get("network_list", []):
                if net not in seen_networks:
                    seen_networks.add(net)
                    merged_data["network_list"].append(net)
                    
        return merged_data

    @staticmethod
    def save_single_profile(filename: str, data: dict):
        filepath = BASE_DIR / filename
        try:
            with filepath.open("w", encoding="utf-8") as f:
                f.write("DNS List:\n")
                for item in data.get("dns_list", []): f.write(f"{item}\n")
                f.write("\n\nDomain List:\n")
                for item in data.get("domain_list", []): f.write(f"{item}\n")
                f.write("\n\nNetwork:\n")
                for item in data.get("network_list", []): f.write(f"{item}\n")
            logger.info(f"Successfully saved profile: {filename}")
        except Exception as e:
            logger.error(f"Failed to save profile {filename}: {e}")

    @staticmethod
    def parse_dns_list(lines: list[str], system_dns_list: list[str]) -> list[dict]:
        parsed = []
        for idx, line in enumerate(lines):
            parts = line.split(maxsplit=1)
            if not parts: continue
            ip = parts[0]
            name = parts[1] if len(parts) > 1 else ""
            is_system = ip in system_dns_list
            parsed.append({
                "ip": ip, "name": name, "row_id": f"row_{idx}", 
                "is_system": is_system
            })
        return parsed

    @staticmethod
    def format_domain(raw_domain: str) -> str:
        try:
            clean = raw_domain.replace("http://", "").replace("https://", "")
            parts = clean.split('.')
            main_name = parts[-2] if len(parts) >= 2 else parts[0]
            return main_name.capitalize()
        except Exception:
            return str(raw_domain).capitalize()