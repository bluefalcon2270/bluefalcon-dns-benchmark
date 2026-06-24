# Version 42.0 | File: ui_shared.py | Shared UI Elements, Themes, and Engines
import os
import sys
import csv
import concurrent.futures
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from datetime import datetime
from core import NetworkUtils, ConfigManager

# ==========================================
# Application Configuration & Constants
# ==========================================
APP_VERSION = "42.0"

# Material Design 3 (Google) Dark Theme Colors
C_BG = "#131314"            # Deep App Background
C_CARD = "#1E1F20"          # Surface/Card Color
C_PRIMARY = "#A8C7FA"       # MD3 Light Blue Text
C_PRIMARY_BG = "#0A56D1"    # MD3 Dark Blue Button
C_SUCCESS = "#81C995"       # MD3 Green
C_ERROR = "#F28B82"         # MD3 Red
C_WARNING = "#FDE293"       # MD3 Yellow
C_PRO = "#FFD700"           # Gold/Pro
C_TEXT_MAIN = "#E2E2E2"     # Main Text
C_TEXT_MUTED = "#C4C7C5"    # Muted/Secondary Text
C_BORDER = "#444746"        # MD3 Outline/Border

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==========================================
# Custom Widgets
# ==========================================
class ScrollableTable(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=C_CARD, corner_radius=24, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background=C_CARD,
                        foreground=C_TEXT_MAIN,
                        fieldbackground=C_CARD,
                        rowheight=32,
                        borderwidth=0,
                        font=("Segoe UI", 11))
        style.map('Treeview', background=[('selected', C_PRIMARY_BG)])
        style.configure("Treeview.Heading",
                        background=C_BG,
                        foreground=C_TEXT_MAIN,
                        font=("Segoe UI", 12, "bold"),
                        borderwidth=0)
        style.map("Treeview.Heading", background=[('active', C_BORDER)])

        self.tree = ttk.Treeview(self, show="headings", selectmode="browse")
        
        self.vsb = ctk.CTkScrollbar(self, orientation="vertical", command=self.tree.yview)
        self.hsb = ctk.CTkScrollbar(self, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(15, 5), pady=(15, 5))
        self.vsb.grid(row=0, column=1, sticky="ns", padx=(0, 15), pady=(15, 5))
        self.hsb.grid(row=1, column=0, sticky="ew", padx=(15, 5), pady=(0, 15))

# ==========================================
# Engines and Handlers
# ==========================================
class ScannerEngine:
    @staticmethod
    def run_scan(dns_list, domains, timeout, workers, update_queue, stop_event):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as exe:
            future_map = {}
            for d in dns_list:
                for dom in domains:
                    f = exe.submit(NetworkUtils.test_dns_domain, d["ip"], dom, timeout)
                    future_map[f] = (d["row_id"], dom)

            for future in concurrent.futures.as_completed(future_map):
                if stop_event.is_set(): break
                row_id, domain = future_map[future]
                try:
                    success, text, t_val = future.result()
                    update_queue.put((row_id, domain, success, text, t_val))
                except Exception:
                    update_queue.put((row_id, domain, False, "?", 0))

        update_queue.put(("DONE", None, None, None, None))

class DataManager:
    @staticmethod
    def calculate_metrics(results_data, row_id, domains):
        if not results_data or row_id not in results_data: return "-", "-"
        row_res = results_data[row_id]
        successes, total_time, total_domains = 0, 0, len(domains)
        if total_domains == 0: return "-", "-"

        for dom in domains:
            res = row_res.get(dom, {"success": False, "time": 0})
            if res["success"]:
                successes += 1
                total_time += res["time"]

        failures = total_domains - successes
        avg_ping_str = "Failed" if successes == 0 else f"{round(total_time / successes)} ms"

        return avg_ping_str, str(failures)

    @staticmethod
    def save_to_history(dns_list, domains, results_data, network):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_file = "benchmark_history.csv"
        file_exists = os.path.exists(history_file)

        try:
            with open(history_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Network", "DNS_IP", "DNS_Name", "Errors", "Avg_Ping_ms"])

                for info in dns_list:
                    r_id = info["row_id"]
                    avg_ping_str, err_text = DataManager.calculate_metrics(results_data, r_id, domains)
                    
                    ping_val = -1
                    if "ms" in avg_ping_str:
                        ping_val = int(avg_ping_str.replace(" ms", ""))
                    
                    err_val = int(err_text) if err_text != "-" else len(domains)
                    
                    writer.writerow([timestamp, network, info["ip"], info["name"], err_val, ping_val])
        except Exception as e:
            print(f"Failed to save history: {e}")

    @staticmethod
    def export_csv(dns_list, domains, results_data, display_mode, is_scanning):
        if display_mode == "history":
            messagebox.showwarning("Warning", "Exporting is available for Live scans only. You can find all history data directly in 'benchmark_history.csv'.")
            return

        if not results_data or is_scanning:
            messagebox.showwarning("Warning", "Complete a scan before exporting.")
            return

        fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Export CSV")
        if not fp: return

        try:
            with open(fp, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                display_domains = [ConfigManager.format_domain(d) for d in domains]
                headers = ["DNS IP", "Name", "System DNS", "Errors", "Avg Ping"] + display_domains
                writer.writerow(headers)

                for info in dns_list:
                    row_id = info["row_id"]
                    avg_ping, err_text = DataManager.calculate_metrics(results_data, row_id, domains)
                    row_data = [info["ip"], info["name"], "Yes" if info["is_system"] else "No", err_text, avg_ping]
                    
                    for dom in domains:
                        res = results_data.get(row_id, {}).get(dom, {})
                        row_data.append(res.get("text", "-") if res.get("success") else res.get("text", "Error"))
                        
                    writer.writerow(row_data)
            messagebox.showinfo("Success", f"Data exported to:\n{fp}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")

    @staticmethod
    def get_best_successful_dns(dns_list, domains, results_data):
        if not results_data: return []
            
        valid_dns = []
        for info in dns_list:
            row_id = info["row_id"]
            row_res = results_data.get(row_id, {})
            
            success_count = sum(1 for d in domains if row_res.get(d, {}).get("success"))
            if success_count > 0:
                original_line = f"{info['ip']} {info['name']}".strip()
                valid_dns.append(original_line)
                
        return valid_dns