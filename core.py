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

APP_VERSION = "2.7"

BASE_DIR = Path.cwd()
LOG_FILE = BASE_DIR / "bluefalcon-app.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("BlueFalconCore")

class AppUtils:
    @staticmethod
    def get_resource_path(relative_path: str) -> Path:
        base_path = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else BASE_DIR
        return base_path / relative_path

    @staticmethod
    def is_admin() -> bool:
        try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except: return False

class NetworkUtils:
    @staticmethod
    def get_system_dns() -> list[str]:
        system_dns = []
        try:
            cmd = 'powershell -NoProfile -Command "(Get-WmiObject Win32_NetworkAdapterConfiguration -Filter \'IPEnabled=True AND DefaultIPGateway IS NOT NULL\').DNSServerSearchOrder"'
            output = subprocess.check_output(cmd, text=True, creationflags=0x08000000)
            for line in output.splitlines():
                ip = line.strip()
                if ip and ip not in system_dns: system_dns.append(ip)
        except: pass
        return system_dns if system_dns else ["1.1.1.1"]

    @staticmethod
    def tcp_test(ip: str, port: int, timeout: float) -> tuple[bool, str | int]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            t0 = time.time()
            sock.connect((ip, port))
            dt = round((time.time() - t0) * 1000)
            sock.close()
            return True, f"{dt} ms", dt
        except: return False, "Timeout", 0

    @staticmethod
    def test_dns_domain(dns_ip: str, domain: str, timeout: float, retries: int) -> tuple[bool, str, int]:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [dns_ip]
        
        # Enforce exact retry logic. Total time = lifetime. Time per try = timeout.
        resolver.lifetime = float(timeout)
        resolver.timeout = float(timeout) / max(1.0, float(retries))
        
        try:
            ans = resolver.resolve(domain, "A", lifetime=timeout)
            ips = [x.to_text() for x in ans]
            if not ips: return False, "No IP", 0
            
            # The TCP test does not need retries, just a hard timeout
            ok, t_res = NetworkUtils.tcp_test(ips[0], 443, float(timeout))
            if ok: return True, f"{t_res} ms", t_res
            else: return False, str(t_res), 0
                
        except dns.resolver.NXDOMAIN: return False, "NXDOMAIN", 0
        except dns.resolver.NoAnswer: return False, "No Answer", 0
        except dns.resolver.NoNameservers: return False, "ServFail", 0
        except dns.exception.Timeout: return False, "DNS Timeout", 0
        except Exception: return False, "?", 0

class ConfigManager:
    @staticmethod
    def get_available_profiles() -> list[str]:
        profiles = [p.name for p in BASE_DIR.glob("config_*.txt")]
        if not profiles:
            ConfigManager.save_single_profile("config_default.txt", {"dns_list": ["1.1.1.1 Cloudflare", "8.8.8.8 Google"], "domain_list": ["google.com"], "network_list": ["Default"]})
            return ["config_default.txt"]
        return sorted(profiles)

    @staticmethod
    def load_single_profile(filename: str) -> dict:
        data = {"dns_list": [], "domain_list": [], "network_list": []}
        filepath = BASE_DIR / filename
        if filepath.exists():
            with filepath.open("r", encoding="utf-8") as f:
                curr = None
                for line in f:
                    line = line.strip()
                    if not line: continue
                    if "DNS List" in line: curr = "dns_list"
                    elif "Domain List" in line: curr = "domain_list"
                    elif "Network" in line: curr = "network_list"
                    elif curr: data[curr].append(line)
        return data

    @staticmethod
    def load_multiple_profiles(filenames: list[str]) -> dict:
        merged_data = {"dns_list": [], "domain_list": [], "network_list": []}
        seen_dns, seen_domains, seen_networks = set(), set(), set()

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
        with (BASE_DIR / filename).open("w", encoding="utf-8") as f:
            f.write("DNS List:\n" + "\n".join(data.get("dns_list", [])) + "\n\nDomain List:\n" + "\n".join(data.get("domain_list", [])) + "\n\nNetwork:\n" + "\n".join(data.get("network_list", [])))

    @staticmethod
    def parse_dns_list(lines: list[str], sys_dns: list[str]) -> list[dict]:
        return [{"ip": l.split()[0], "name": " ".join(l.split()[1:]), "row_id": f"r{i}", "is_system": l.split()[0] in sys_dns} for i, l in enumerate(lines)]

    @staticmethod
    def format_domain(raw_domain: str) -> str:
        parts = raw_domain.replace("http://", "").replace("https://", "").split('.')
        return (parts[-2] if len(parts) >= 2 else parts[0]).capitalize()