# Version 46.0 | File: ui_main.py | Main Dashboard and Event Loop
import os
import sys
import threading
import queue
import ctypes
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import pandas as pd

from core import NetworkUtils, ConfigManager
from ui_shared import C_BG, C_CARD, C_PRIMARY, C_PRIMARY_BG, C_SUCCESS, C_ERROR, C_WARNING, C_TEXT_MAIN, C_TEXT_MUTED, C_BORDER, APP_VERSION, get_resource_path, ScrollableTable, ScannerEngine, DataManager
from ui_views import ViewBuilder

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ModernDNSApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        if sys.platform.startswith('win'):
            try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f'bluefalcon.dnsbenchmarkpro.gui.{APP_VERSION}')
            except Exception: pass

        self.title(f"DNS Benchmark Pro v{APP_VERSION}")
        self.geometry("1400x850")
        self.minsize(1100, 650)
        self.configure(fg_color=C_BG)
        
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path): self.iconbitmap(icon_path)

        self.display_mode = "live"
        self.history_results = []
        self.config_data = {"dns_list": [], "domain_list": [], "network_list": []}
        self.active_profiles = []
        
        self.system_dns = NetworkUtils.get_system_dns()
        self.dns_list = []
        self.domains = []
        self.networks = []
        
        self.tree_items = {} 
        self.results_data = {} 
        self.update_queue = queue.Queue()
        
        self.is_scanning = False
        self.is_sorted = False
        self.stop_event = threading.Event()
        self.total_tasks = 0
        self.completed_tasks = 0

        self.current_timeout = 5.0
        self.current_workers = 1000
        
        self.selected_network_var = tk.StringVar(value="Default")
        self.selected_profile_var = tk.StringVar(value="Select Profile")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.build_sidebar()
        self.main_container = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.views = {}
        self.build_all_views()
        self.select_sidebar_frame("live")

        profiles = ConfigManager.get_available_profiles()
        if profiles:
            self.combo_profile.configure(values=["Select Profile"] + profiles)
            self.combo_profile.set("Select Profile")

        self.build_grid()
        self.process_queue()

    def build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=C_CARD)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(self.sidebar_frame, text="🌐 DNS Pro", font=("Segoe UI", 22, "bold"), text_color=C_PRIMARY).pack(pady=(30, 40), padx=20)

        self.btn_nav_live = ctk.CTkButton(self.sidebar_frame, text="📊 Live Benchmark", font=("Segoe UI", 15, "bold"), corner_radius=12, height=44, fg_color="transparent", text_color=C_TEXT_MAIN, anchor="w", command=lambda: self.select_sidebar_frame("live"))
        self.btn_nav_live.pack(fill="x", padx=15, pady=5)

        self.btn_nav_history = ctk.CTkButton(self.sidebar_frame, text="🕒 History", font=("Segoe UI", 15, "bold"), corner_radius=12, height=44, fg_color="transparent", text_color=C_TEXT_MAIN, anchor="w", command=lambda: self.select_sidebar_frame("history"))
        self.btn_nav_history.pack(fill="x", padx=15, pady=5)

        self.btn_nav_profiles = ctk.CTkButton(self.sidebar_frame, text="📁 Profiles", font=("Segoe UI", 15, "bold"), corner_radius=12, height=44, fg_color="transparent", text_color=C_TEXT_MAIN, anchor="w", command=lambda: self.select_sidebar_frame("profiles"))
        self.btn_nav_profiles.pack(fill="x", padx=15, pady=5)

        self.btn_nav_settings = ctk.CTkButton(self.sidebar_frame, text="⚙️ Settings", font=("Segoe UI", 15, "bold"), corner_radius=12, height=44, fg_color="transparent", text_color=C_TEXT_MAIN, anchor="w", command=lambda: self.select_sidebar_frame("settings"))
        self.btn_nav_settings.pack(fill="x", padx=15, pady=5)

        self.btn_nav_about = ctk.CTkButton(self.sidebar_frame, text="ℹ️ About", font=("Segoe UI", 15, "bold"), corner_radius=12, height=44, fg_color="transparent", text_color=C_TEXT_MAIN, anchor="w", command=lambda: self.select_sidebar_frame("about"))
        self.btn_nav_about.pack(side="bottom", fill="x", padx=15, pady=20)

    def select_sidebar_frame(self, name):
        self.btn_nav_live.configure(fg_color=C_PRIMARY_BG if name == "live" else "transparent")
        self.btn_nav_history.configure(fg_color=C_PRIMARY_BG if name == "history" else "transparent")
        self.btn_nav_profiles.configure(fg_color=C_PRIMARY_BG if name == "profiles" else "transparent")
        self.btn_nav_settings.configure(fg_color=C_PRIMARY_BG if name == "settings" else "transparent")
        self.btn_nav_about.configure(fg_color=C_PRIMARY_BG if name == "about" else "transparent")

        for view in self.views.values(): view.grid_forget()
        self.views[name].grid(row=0, column=0, sticky="nsew")

    def build_all_views(self):
        self.views["live"] = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.build_live_ui(self.views["live"])

        self.views["history"] = ViewBuilder.build_history_view(self, self.main_container)
        self.views["profiles"] = ViewBuilder.build_profiles_view(self, self.main_container)
        self.views["settings"] = ViewBuilder.build_settings_view(self, self.main_container)
        self.views["about"] = ViewBuilder.build_about_view(self, self.main_container)

    def refresh_sidebar_views(self):
        for name in ["history", "profiles", "settings", "about"]:
            if name in self.views: self.views[name].destroy()
        self.views["history"] = ViewBuilder.build_history_view(self, self.main_container)
        self.views["profiles"] = ViewBuilder.build_profiles_view(self, self.main_container)
        self.views["settings"] = ViewBuilder.build_settings_view(self, self.main_container)
        self.views["about"] = ViewBuilder.build_about_view(self, self.main_container)

    def build_live_ui(self, parent):
        self.control_card = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=24)
        self.control_card.pack(fill="x", padx=30, pady=(30, 20), ipady=12)

        left_frame = ctk.CTkFrame(self.control_card, fg_color="transparent")
        left_frame.pack(side="left", padx=20, fill="y")

        # UI Jitter Fix: Strict width parameter enforced
        self.btn_start = ctk.CTkButton(left_frame, text="🚀 Start Benchmark", font=("Segoe UI", 14, "bold"), command=self.toggle_scan, fg_color=C_PRIMARY_BG, text_color=C_TEXT_MAIN, hover_color="#0842A0", corner_radius=24, width=170, height=40)
        self.btn_start.pack(side="left", padx=(5, 10), pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(left_frame, width=200, height=12, progress_color=C_PRIMARY, fg_color=C_BG, corner_radius=12)
        self.progress_bar.pack(side="left", padx=(5, 10))
        self.progress_bar.set(0)

        # UI Jitter Fix: Enforced explicit box width and west alignment
        self.lbl_progress_text = ctk.CTkLabel(left_frame, text="", text_color=C_TEXT_MAIN, font=("Segoe UI", 13, "bold"), width=95, anchor="w")
        self.lbl_progress_text.pack(side="left", padx=(0, 15))

        # UI Jitter Fix: Strict width blocks domino effect
        self.lbl_status = ctk.CTkLabel(left_frame, text="No Configuration Loaded", text_color=C_WARNING, font=("Segoe UI", 13, "bold"), width=230, anchor="w")
        self.lbl_status.pack(side="left", padx=(5, 0))
        
        right_frame = ctk.CTkFrame(self.control_card, fg_color="transparent")
        right_frame.pack(side="right", padx=20, fill="y")

        self.btn_sort = ctk.CTkButton(right_frame, text="🔽 Sort", font=("Segoe UI", 13, "bold"), command=self.sort_results, fg_color="transparent", text_color=C_TEXT_MAIN, border_width=1, border_color=C_BORDER, hover_color=C_BG, corner_radius=24, width=80, height=36)
        self.btn_sort.pack(side="right", padx=(10, 5), pady=10)

        self.combo_profile = ctk.CTkComboBox(right_frame, variable=self.selected_profile_var, values=["Select Profile"], width=150, height=36, fg_color=C_BG, corner_radius=8, border_color=C_BORDER, justify="center", command=self.on_profile_select)
        self.combo_profile.pack(side="right", padx=(5, 10))
        ctk.CTkLabel(right_frame, text="Profile:", font=("Segoe UI", 13, "bold"), text_color=C_TEXT_MUTED).pack(side="right")

        self.combo_network = ctk.CTkComboBox(right_frame, variable=self.selected_network_var, values=["Default"], width=130, height=36, fg_color=C_BG, corner_radius=8, border_color=C_BORDER, justify="center")
        self.combo_network.pack(side="right", padx=(5, 15))
        ctk.CTkLabel(right_frame, text="Network:", font=("Segoe UI", 13, "bold"), text_color=C_TEXT_MUTED).pack(side="right")

        self.table_scroll = ScrollableTable(parent)
        self.table_scroll.pack(padx=30, pady=(0, 30), fill="both", expand=True)
        self.table_scroll.tree.bind("<Double-1>", self.on_tree_double_click)

    def on_profile_select(self, choice):
        self.load_selected_profiles([] if choice == "Select Profile" else [choice])

    def load_selected_profiles(self, filenames):
        self.display_mode = "live"
        self.is_sorted = False
        self.active_profiles = filenames
        if not filenames:
            self.config_data = {"dns_list": [], "domain_list": [], "network_list": []}
            self.lbl_status.configure(text="No Configuration Loaded", text_color=C_WARNING)
        else:
            self.config_data = ConfigManager.load_multiple_profiles(filenames)
            names = [f.replace("config_", "").replace(".txt", "") for f in filenames]
            self.lbl_status.configure(text=f"Loaded: {', '.join(names)}", text_color=C_SUCCESS)
            
        self.dns_list = ConfigManager.parse_dns_list(self.config_data.get("dns_list", []), self.system_dns)
        self.domains = self.config_data.get("domain_list", [])
        self.networks = self.config_data.get("network_list", [])
        if not self.networks: self.networks = ["Unknown"]
        self.combo_network.configure(values=self.networks)
        self.selected_network_var.set(self.networks[0])
        
        self.build_grid()

    def load_history_data(self, selected_criteria, df):
        self.display_mode = "history"
        self.lbl_status.configure(text="Viewing Aggregated History Mode", text_color=C_PRIMARY)
        mask = pd.Series(False, index=df.index)
        for net, ts in selected_criteria: mask |= (df['Network'] == net) & (df['Timestamp'] == ts)
        filtered_df = df[mask].copy()
        filtered_df['DNS_Name'] = filtered_df['DNS_Name'].fillna("")
        grouped = filtered_df.groupby(['DNS_IP', 'DNS_Name']).agg(Test_Count=('Errors', 'count'), Avg_Errors=('Errors', 'mean'), Avg_Ping=('Avg_Ping_ms', lambda x: x[x > 0].mean() if (x > 0).any() else -1)).reset_index()
        self.history_results = grouped.sort_values(by=['Avg_Errors', 'Avg_Ping'], ascending=[True, True]).to_dict('records')
        self.build_grid()

    def on_tree_double_click(self, event):
        region = self.table_scroll.tree.identify("region", event.x, event.y)
        if region in ("cell", "tree"):
            iid = self.table_scroll.tree.focus()
            if iid:
                vals = self.table_scroll.tree.item(iid, "values")
                if vals and len(vals) > 1:
                    ip_clean = str(vals[1]).replace("[System]", "").strip()
                    self.clipboard_clear()
                    self.clipboard_append(ip_clean)
                    self.update()
                    self.lbl_status.configure(text=f"Copied: {ip_clean}", text_color=C_SUCCESS)

    def build_grid(self):
        for item in self.table_scroll.tree.get_children(): self.table_scroll.tree.delete(item)
        self.tree_items.clear()

        if self.display_mode == "history":
            if not getattr(self, "history_results", None): return
            self.table_scroll.tree.configure(columns=["id", "address", "name", "errors", "ping", "tests"])
            self.table_scroll.tree.heading("id", text="#", anchor="center"); self.table_scroll.tree.column("id", width=40, anchor="center")
            self.table_scroll.tree.heading("address", text="DNS Address", anchor="center"); self.table_scroll.tree.column("address", width=180, anchor="w")
            self.table_scroll.tree.heading("name", text="DNS Name", anchor="center"); self.table_scroll.tree.column("name", width=140, anchor="center")
            self.table_scroll.tree.heading("errors", text="Avg Errors", anchor="center"); self.table_scroll.tree.column("errors", width=100, anchor="center")
            self.table_scroll.tree.heading("ping", text="Avg Ping (ms)", anchor="center"); self.table_scroll.tree.column("ping", width=120, anchor="center")
            self.table_scroll.tree.heading("tests", text="Tests Sent", anchor="center"); self.table_scroll.tree.column("tests", width=100, anchor="center")

            for i, r in enumerate(self.history_results):
                ping_str = f"{round(r['Avg_Ping'])} ms" if r['Avg_Ping'] != -1 else "Failed"
                self.table_scroll.tree.insert("", "end", values=[i + 1, r['DNS_IP'], r['DNS_Name'], round(r['Avg_Errors'], 2), ping_str, int(r['Test_Count'])])
            return

        if not self.active_profiles or not self.dns_list or not self.domains:
            self.table_scroll.tree.configure(columns=["msg"])
            self.table_scroll.tree.heading("msg", text="No Configuration Loaded. Navigate to Profiles to create or load configurations.", anchor="w")
            self.table_scroll.tree.column("msg", width=800, anchor="w")
            return

        display_domains = [ConfigManager.format_domain(d) for d in self.domains]
        self.table_scroll.tree.configure(columns=["id", "address", "name", "errors", "ping"] + self.domains)

        self.table_scroll.tree.heading("id", text="#", anchor="center"); self.table_scroll.tree.column("id", width=40, minwidth=40, anchor="center")
        self.table_scroll.tree.heading("address", text="DNS Address", anchor="center"); self.table_scroll.tree.column("address", width=180, minwidth=150, anchor="w")
        self.table_scroll.tree.heading("name", text="DNS Name", anchor="center"); self.table_scroll.tree.column("name", width=140, minwidth=100, anchor="center")
        self.table_scroll.tree.heading("errors", text="Errors", anchor="center"); self.table_scroll.tree.column("errors", width=80, minwidth=60, anchor="center")
        self.table_scroll.tree.heading("ping", text="Avg Ping", anchor="center"); self.table_scroll.tree.column("ping", width=100, minwidth=80, anchor="center")

        for i, d in enumerate(self.domains):
            self.table_scroll.tree.heading(d, text=display_domains[i], anchor="center")
            self.table_scroll.tree.column(d, width=110, minwidth=90, anchor="center")

        for row_index, info in enumerate(self.dns_list):
            addr_text = f"{info['ip']} [System]" if info["is_system"] else info["ip"]
            avg, err_text = DataManager.calculate_metrics(self.results_data, info["row_id"], self.domains)
            self.tree_items[info["row_id"]] = self.table_scroll.tree.insert("", "end", iid=info["row_id"], values=[row_index + 1, addr_text, info["name"], err_text, avg] + ["-"] * len(self.domains))

    def toggle_scan(self):
        if self.display_mode == "history": self.display_mode = "live"; self.build_grid()
        if self.is_scanning:
            self.stop_event.set()
            self.lbl_status.configure(text="Aborting...", text_color=C_WARNING)
            self.btn_start.configure(state="disabled")
            return
        if not self.dns_list or not self.domains:
            messagebox.showwarning("Warning", "Configuration empty. Load profiles or add data.")
            return

        self.is_scanning = True; self.is_sorted = False; self.stop_event.clear()
        self.results_data = {d["row_id"]: {} for d in self.dns_list}
        self.total_tasks = len(self.dns_list) * len(self.domains); self.completed_tasks = 0
        self.progress_bar.set(0); self.lbl_progress_text.configure(text=f"0 / {self.total_tasks}")
        self.combo_network.configure(state="disabled")
        
        self.btn_start.configure(text="🛑 Stop Scan", fg_color="#8C1D18", text_color=C_TEXT_MAIN, hover_color="#601410")
        self.lbl_status.configure(text="Benchmarking...", text_color=C_PRIMARY)
        
        for iid in self.tree_items.values():
            vals = list(self.table_scroll.tree.item(iid, "values"))
            vals[3] = "-"; vals[4] = "-"
            for i in range(5, len(vals)): vals[i] = "..."
            self.table_scroll.tree.item(iid, values=vals)

        threading.Thread(target=ScannerEngine.run_scan, args=(self.dns_list, self.domains, self.current_timeout, self.current_workers, self.update_queue, self.stop_event), daemon=True).start()

    def process_queue(self):
        try:
            processed_tasks = 0
            while not self.update_queue.empty() and processed_tasks < 500:
                try:
                    row_id, domain, success, text, time_val = self.update_queue.get_nowait()
                    if row_id == "DONE":
                        self.is_scanning = False
                        self.btn_start.configure(state="normal", text="🚀 Start Benchmark", fg_color=C_PRIMARY_BG, text_color=C_TEXT_MAIN, hover_color="#0842A0")
                        self.combo_network.configure(state="normal")
                        self.progress_bar.set(1.0)
                        self.lbl_progress_text.configure(text=f"{self.total_tasks} / {self.total_tasks}")
                        
                        if self.stop_event.is_set(): self.lbl_status.configure(text="Scan Aborted", text_color=C_ERROR)
                        else:
                            self.lbl_status.configure(text="Saving history...", text_color=C_SUCCESS)
                            DataManager.save_to_history(self.dns_list, self.domains, self.results_data, self.selected_network_var.get())
                            self.lbl_status.configure(text="Scan Complete", text_color=C_SUCCESS)
                        
                        for r_id, iid in self.tree_items.items():
                            current_vals = list(self.table_scroll.tree.item(iid, "values"))
                            avg, err_text = DataManager.calculate_metrics(self.results_data, r_id, self.domains)
                            current_vals[3] = err_text; current_vals[4] = avg
                            self.table_scroll.tree.item(iid, values=current_vals)
                    else:
                        self.completed_tasks += 1
                        if self.total_tasks > 0:
                            self.progress_bar.set(self.completed_tasks / self.total_tasks)
                            self.lbl_progress_text.configure(text=f"{self.completed_tasks} / {self.total_tasks}")
                        self.results_data[row_id][domain] = {"success": success, "text": text, "time": time_val}

                        if row_id in self.tree_items:
                            iid = self.tree_items[row_id]
                            current_vals = list(self.table_scroll.tree.item(iid, "values"))
                            try:
                                current_vals[5 + self.domains.index(domain)] = text
                                self.table_scroll.tree.item(iid, values=current_vals)
                            except ValueError: pass
                except queue.Empty: break
                except Exception as e: print(f"Task processing error: {e}")
                processed_tasks += 1
        finally:
            self.after(50, self.process_queue)

    def sort_results(self):
        if self.display_mode == "history":
            if not getattr(self, "history_results", None):
                messagebox.showinfo("Info", "Load history data to sort.")
                return
            self.history_results.sort(key=lambda x: (x['Avg_Errors'], x['Avg_Ping']))
            self.build_grid()
        else:
            if not self.results_data or self.is_scanning:
                messagebox.showinfo("Info", "Complete a scan before sorting.")
                return
            def get_sort_key(info):
                row_res = self.results_data.get(info["row_id"], {})
                success_count = sum(1 for d in self.domains if row_res.get(d, {}).get("success"))
                total_time = sum(row_res.get(d, {}).get("time", 0) for d in self.domains if row_res.get(d, {}).get("success"))
                return (len(self.domains) - success_count, (total_time / success_count) if success_count > 0 else float('inf'))

            self.dns_list.sort(key=get_sort_key)
            self.is_sorted = True
            self.build_grid()
            
            for row_id, dom_data in self.results_data.items():
                if row_id in self.tree_items:
                    iid = self.tree_items[row_id]
                    current_vals = list(self.table_scroll.tree.item(iid, "values"))
                    avg, err_text = DataManager.calculate_metrics(self.results_data, row_id, self.domains)
                    current_vals[3] = err_text; current_vals[4] = avg
                    for dom, res in dom_data.items():
                        try: current_vals[5 + self.domains.index(dom)] = res["text"]
                        except Exception: pass
                    self.table_scroll.tree.item(iid, values=current_vals)