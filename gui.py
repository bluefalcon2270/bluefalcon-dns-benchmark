# ==========================================
# BlueFalcon DNS Benchmark Pro - GUI Module
# ==========================================
import os
import threading
import queue
import concurrent.futures
import csv
import re
from datetime import datetime
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
import pandas as pd

from core import APP_VERSION, AppUtils, NetworkUtils, ConfigManager

# Material Design 3 Dark Theme Colors
C_BG = "#121212"
C_CARD = "#1E1E1E"
C_PRIMARY = "#A8C7FA"      # Light Blue
C_PRIMARY_BG = "#0742A0"   # Dark Blue
C_SUCCESS = "#81C995"      # Green
C_ERROR = "#F28B82"        # Red
C_WARNING = "#FDD663"      # Yellow
C_PRO = "#FFD700"          # Gold/Pro
C_TEXT_MAIN = "#E3E3E3"
C_TEXT_MUTED = "#8E918F"
C_BORDER = "#444746"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ScrollableTable(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=C_CARD, corner_radius=16, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg=C_CARD, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.v_scroll = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)
        self.v_scroll.grid(row=0, column=1, sticky="ns", pady=5, padx=(0,5))
        self.h_scroll = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview)
        self.h_scroll.grid(row=1, column=0, sticky="ew", padx=5, pady=(0,5))

        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.inner_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.canvas.bind_all("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(int(-1*(e.delta/120)), "units"))

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Shift-MouseWheel>")

class ModernDNSApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"BlueFalcon DNS Benchmark Pro v{APP_VERSION}")
        self.geometry("1280x850")
        self.minsize(1000, 650)
        self.configure(fg_color=C_BG)

        # Apply Universal Icon to Titlebar
        icon_path = AppUtils.get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except Exception: pass

        # State Variables
        self.display_mode = "live"
        self.history_results = []
        
        self.config_data = {"dns_list": [], "domain_list": [], "network_list": []}
        self.active_profiles = []
        
        self.system_dns = NetworkUtils.get_system_dns()
        self.dns_list = []
        self.domains = []
        self.networks = []
        
        self.ui_cells = {} 
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

        self.build_ui()
        self.build_grid()
        self.process_queue()

    def build_ui(self):
        self.app_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.app_bar.pack(fill="x", padx=30, pady=(25, 15))
        
        title_frame = ctk.CTkFrame(self.app_bar, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(title_frame, text="🌐", font=("Segoe UI Emoji", 28)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(title_frame, text="DNS Benchmark", font=("Helvetica", 24, "bold"), text_color=C_TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(title_frame, text="Pro", font=("Helvetica", 24, "bold"), text_color=C_PRO).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(title_frame, text=f"v{APP_VERSION}", font=("Segoe UI", 12, "italic"), text_color=C_TEXT_MUTED).pack(side="left", padx=(10,0), pady=(8,0))

        btn_frame = ctk.CTkFrame(self.app_bar, fg_color="transparent")
        btn_frame.pack(side="right")
        
        ctk.CTkButton(btn_frame, text="📂 Profiles", font=("Helvetica", 14, "bold"), command=self.open_profiles_manager, 
                      fg_color=C_PRIMARY_BG, hover_color="#063580", text_color=C_PRIMARY, corner_radius=20, width=100, height=36).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📊 History", font=("Helvetica", 14, "bold"), command=self.open_history, 
                      fg_color=C_SUCCESS, hover_color="#6BBA80", text_color=C_BG, corner_radius=20, width=100, height=36).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="⚙️ Settings", font=("Helvetica", 14, "bold"), command=self.open_settings, 
                      fg_color=C_CARD, hover_color=C_BORDER, border_width=1, border_color=C_BORDER, corner_radius=20, width=100, height=36).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="ℹ️ About", font=("Helvetica", 14, "bold"), command=self.open_about, 
                      fg_color=C_CARD, hover_color=C_BORDER, border_width=1, border_color=C_BORDER, corner_radius=20, width=80, height=36).pack(side="left", padx=5)

        self.control_card = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=16)
        self.control_card.pack(fill="x", padx=30, pady=(0, 20), ipady=10)

        self.btn_start = ctk.CTkButton(self.control_card, text="🚀 Start Benchmark", font=("Helvetica", 15, "bold"),
                                       command=self.toggle_scan, fg_color=C_PRIMARY_BG, text_color=C_PRIMARY, 
                                       hover_color="#063580", corner_radius=20, width=180, height=42)
        self.btn_start.pack(side="left", padx=20, pady=10)
        
        ctk.CTkLabel(self.control_card, text="Network:", font=("Helvetica", 13, "bold"), text_color=C_TEXT_MUTED).pack(side="left", padx=(5, 5))
        self.combo_network = ctk.CTkComboBox(self.control_card, variable=self.selected_network_var, values=["Default"], width=130, fg_color=C_BG)
        self.combo_network.pack(side="left", padx=(0, 15))

        self.progress_bar = ctk.CTkProgressBar(self.control_card, width=200, height=8, progress_color=C_PRIMARY, fg_color=C_BG)
        self.progress_bar.pack(side="left", padx=10)
        self.progress_bar.set(0)
        
        self.lbl_progress_text = ctk.CTkLabel(self.control_card, text="", text_color=C_PRIMARY, font=("Helvetica", 13, "bold"))
        self.lbl_progress_text.pack(side="left", padx=(0, 10))

        self.lbl_status = ctk.CTkLabel(self.control_card, text="Waiting for profile load...", text_color=C_WARNING, font=("Helvetica", 14, "bold"))
        self.lbl_status.pack(side="left", padx=10)

        self.btn_sort = ctk.CTkButton(self.control_card, text="⏬ Sort Results", font=("Helvetica", 14, "bold"), command=self.sort_results,
                                      fg_color="transparent", text_color=C_TEXT_MAIN, border_width=1, border_color=C_BORDER, hover_color=C_BG, corner_radius=20, width=130, height=36)
        self.btn_sort.pack(side="right", padx=20)

        self.btn_export = ctk.CTkButton(self.control_card, text="💾 Export CSV", font=("Helvetica", 14, "bold"), command=self.export_csv,
                                        fg_color="transparent", text_color=C_TEXT_MAIN, border_width=1, border_color=C_BORDER, hover_color=C_BG, corner_radius=20, width=130, height=36)
        self.btn_export.pack(side="right", padx=5)

        self.table_scroll = ScrollableTable(self)
        self.table_scroll.pack(padx=30, pady=(0, 30), fill="both", expand=True)

    def load_selected_profiles(self, filenames):
        self.display_mode = "live"
        self.is_sorted = False
        self.active_profiles = filenames
        if not filenames:
            self.config_data = {"dns_list": [], "domain_list": [], "network_list": []}
            self.lbl_status.configure(text="No profile loaded", text_color=C_WARNING)
        else:
            self.config_data = ConfigManager.load_multiple_profiles(filenames)
            names = [f.replace("config_", "").replace(".txt", "") for f in filenames]
            self.lbl_status.configure(text=f"Loaded: {', '.join(names)}", text_color=C_SUCCESS)
            
        self.dns_list = ConfigManager.parse_dns_list(self.config_data.get("dns_list", []), self.system_dns)
        self.domains = self.config_data.get("domain_list", [])
        
        self.networks = self.config_data.get("network_list", [])
        if not self.networks:
            self.networks = ["Unknown"]
        self.combo_network.configure(values=self.networks)
        self.selected_network_var.set(self.networks[0])
        
        self.build_grid()

    def load_history_data(self, selected_criteria, df):
        self.display_mode = "history"
        self.lbl_status.configure(text="Viewing Aggregated History Mode", text_color=C_PRIMARY)
        
        mask = pd.Series(False, index=df.index)
        for net, ts in selected_criteria:
            mask |= (df['Network'] == net) & (df['Timestamp'] == ts)
            
        filtered_df = df[mask].copy()
        filtered_df['DNS_Name'] = filtered_df['DNS_Name'].fillna("")
        
        grouped = filtered_df.groupby(['DNS_IP', 'DNS_Name']).agg(
            Test_Count=('Errors', 'count'),
            Avg_Errors=('Errors', 'mean'),
            Avg_Ping=('Avg_Ping_ms', lambda x: x[x > 0].mean() if (x > 0).any() else -1)
        ).reset_index()
        
        grouped = grouped.sort_values(by=['Avg_Errors', 'Avg_Ping'], ascending=[True, True])
        
        self.history_results = grouped.to_dict('records')
        self.build_grid()

    def calculate_metrics(self, row_id):
        if not self.results_data or row_id not in self.results_data: return "-", "-"
        row_res = self.results_data[row_id]
        successes, total_time, total_domains = 0, 0, len(self.domains)
        if total_domains == 0: return "-", "-"

        for dom in self.domains:
            res = row_res.get(dom, {"success": False, "time": 0})
            if res["success"]:
                successes += 1
                total_time += res["time"]

        failures = total_domains - successes
        avg_ping_str = "Failed" if successes == 0 else f"{round(total_time / successes)} ms"

        return avg_ping_str, str(failures)

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def build_grid(self):
        for widget in self.table_scroll.inner_frame.winfo_children():
            widget.destroy()
        self.ui_cells.clear()

        if self.display_mode == "history":
            if not getattr(self, "history_results", None):
                return

            headers = ["#", "DNS Server", "Avg Errors", "Avg Ping (ms)", "Tests Sent"]
            total_cols = len(headers) * 2 - 1

            for col_idx, text in enumerate(headers):
                actual_col = col_idx * 2 
                if col_idx == 0: width = 40
                elif col_idx == 1: width = 220
                elif col_idx == 2: width = 120
                elif col_idx == 3: width = 120
                else: width = 120
                
                lbl = ctk.CTkLabel(self.table_scroll.inner_frame, text=text, font=("Helvetica", 14, "bold"), 
                                   fg_color=C_BG, text_color=C_TEXT_MAIN, corner_radius=6, width=width, height=32)
                lbl.grid(row=0, column=actual_col, padx=4, pady=(15, 10), sticky="ew")

                if col_idx < len(headers) - 1:
                    ctk.CTkFrame(self.table_scroll.inner_frame, width=2, fg_color=C_BG).grid(row=0, column=actual_col+1, rowspan=len(self.history_results)*2+1, sticky="ns", pady=10)

            for row_index, row_data in enumerate(self.history_results):
                grid_row = (row_index * 2) + 1
                
                ctk.CTkLabel(self.table_scroll.inner_frame, text=str(row_index + 1), font=("Helvetica", 13, "bold"), text_color=C_TEXT_MUTED).grid(row=grid_row, column=0, padx=4, pady=8)

                srv_frame = ctk.CTkFrame(self.table_scroll.inner_frame, fg_color="transparent", cursor="hand2")
                srv_frame.grid(row=grid_row, column=2, padx=10, pady=8, sticky="w")
                srv_frame.bind("<Double-Button-1>", lambda e, ip=row_data['DNS_IP']: self.copy_to_clipboard(ip))
                
                lbl_ip = ctk.CTkLabel(srv_frame, text=row_data['DNS_IP'], font=("Helvetica", 14, "bold"), text_color=C_PRIMARY)
                lbl_ip.pack(side="left")
                lbl_ip.bind("<Double-Button-1>", lambda e, ip=row_data['DNS_IP']: self.copy_to_clipboard(ip))

                if row_data['DNS_Name']:
                    ctk.CTkLabel(srv_frame, text=f" {row_data['DNS_Name']}", font=("Helvetica", 12), text_color=C_TEXT_MUTED).pack(side="left", padx=(4,0))

                avg_err = round(row_data['Avg_Errors'], 2)
                err_color = C_SUCCESS if avg_err < 1 else (C_WARNING if avg_err <= 3 else C_ERROR)
                ctk.CTkLabel(self.table_scroll.inner_frame, text=str(avg_err), font=("Helvetica", 15, "bold"), text_color=err_color).grid(row=grid_row, column=4)

                ping_val = row_data['Avg_Ping']
                ping_str = f"{round(ping_val)} ms" if ping_val != -1 else "Failed"
                ctk.CTkLabel(self.table_scroll.inner_frame, text=ping_str, font=("Helvetica", 14, "bold"), text_color=C_TEXT_MAIN).grid(row=grid_row, column=6)

                ctk.CTkLabel(self.table_scroll.inner_frame, text=str(int(row_data['Test_Count'])), font=("Helvetica", 14, "bold"), text_color=C_TEXT_MUTED).grid(row=grid_row, column=8)

                ctk.CTkFrame(self.table_scroll.inner_frame, height=1, fg_color=C_BG).grid(row=grid_row + 1, column=0, columnspan=total_cols, sticky="ew", padx=10)

            return

        if not self.active_profiles:
            ctk.CTkLabel(self.table_scroll.inner_frame, text="No Configuration Loaded. Click '📂 Profiles' to select files.", 
                         font=("Helvetica", 16, "bold"), text_color=C_WARNING).grid(row=0, column=0, padx=30, pady=30)
            return

        if not self.dns_list or not self.domains:
            ctk.CTkLabel(self.table_scroll.inner_frame, text="Selected profile(s) are empty. Please add data via Settings.", 
                         font=("Helvetica", 16), text_color=C_TEXT_MUTED).grid(row=0, column=0, padx=30, pady=30)
            return

        display_domains = [ConfigManager.format_domain(d) for d in self.domains]
        headers = ["#", "DNS Server", "Errors", "Avg Ping"] + display_domains
        total_cols = len(headers) * 2 - 1

        for col_idx, text in enumerate(headers):
            actual_col = col_idx * 2 
            
            if col_idx == 0: width = 40
            elif col_idx == 1: width = 160
            elif col_idx == 2: width = 60
            elif col_idx == 3: width = 90
            else: width = 110
            
            lbl = ctk.CTkLabel(self.table_scroll.inner_frame, text=text, font=("Helvetica", 13, "bold"), 
                               fg_color=C_BG, text_color=C_TEXT_MAIN, corner_radius=6, width=width, height=32)
            lbl.grid(row=0, column=actual_col, padx=4, pady=(15, 10), sticky="ew")

            if col_idx < len(headers) - 1:
                ctk.CTkFrame(self.table_scroll.inner_frame, width=2, fg_color=C_BG).grid(row=0, column=actual_col+1, rowspan=len(self.dns_list)*2+1, sticky="ns", pady=10)

        for row_index, info in enumerate(self.dns_list):
            grid_row = (row_index * 2) + 1
            row_id = info["row_id"]
            self.ui_cells[row_id] = {}

            lbl_row_num = ctk.CTkLabel(self.table_scroll.inner_frame, text=str(row_index + 1), font=("Helvetica", 13, "bold"), text_color=C_TEXT_MUTED)
            lbl_row_num.grid(row=grid_row, column=0, padx=4, pady=8)

            srv_frame = ctk.CTkFrame(self.table_scroll.inner_frame, fg_color="transparent", cursor="hand2")
            srv_frame.grid(row=grid_row, column=2, padx=10, pady=8, sticky="w")
            srv_frame.bind("<Double-Button-1>", lambda e, ip=info["ip"]: self.copy_to_clipboard(ip))
            
            lbl_ip = ctk.CTkLabel(srv_frame, text=info["ip"], font=("Helvetica", 14, "bold"), text_color=C_PRIMARY)
            lbl_ip.pack(side="left")
            lbl_ip.bind("<Double-Button-1>", lambda e, ip=info["ip"]: self.copy_to_clipboard(ip))

            if info["is_system"]:
                ctk.CTkLabel(srv_frame, text=" [System]", font=("Helvetica", 11, "bold"), text_color=C_WARNING).pack(side="left", padx=(4,0))
            if info["name"]:
                ctk.CTkLabel(srv_frame, text=f" {info['name']}", font=("Helvetica", 12), text_color=C_TEXT_MUTED).pack(side="left", padx=(4,0))

            avg_text, err_text = self.calculate_metrics(row_id)
            
            grade_color = C_TEXT_MUTED
            if err_text != "-":
                err_val = int(err_text)
                if err_val == 0: grade_color = C_SUCCESS
                elif err_val <= 2: grade_color = C_WARNING
                else: grade_color = C_ERROR

            lbl_grade = ctk.CTkLabel(self.table_scroll.inner_frame, text=err_text, font=("Helvetica", 15, "bold"), text_color=grade_color)
            lbl_grade.grid(row=grid_row, column=4)
            self.ui_cells[row_id]["_grade"] = lbl_grade

            lbl_avg = ctk.CTkLabel(self.table_scroll.inner_frame, text=avg_text, font=("Helvetica", 14, "bold"), text_color=C_TEXT_MAIN)
            lbl_avg.grid(row=grid_row, column=6)
            self.ui_cells[row_id]["_avg"] = lbl_avg

            for col_idx, domain in enumerate(self.domains, start=4):
                actual_col = col_idx * 2
                lbl_cell = ctk.CTkLabel(self.table_scroll.inner_frame, text="-", text_color=C_BORDER, font=("Helvetica", 14, "bold"), width=110)
                lbl_cell.grid(row=grid_row, column=actual_col, padx=4, pady=8)
                self.ui_cells[row_id][domain] = lbl_cell

            ctk.CTkFrame(self.table_scroll.inner_frame, height=1, fg_color=C_BG).grid(row=grid_row + 1, column=0, columnspan=total_cols, sticky="ew", padx=10)

    def toggle_scan(self):
        if self.display_mode == "history":
            self.display_mode = "live"
            self.build_grid()

        if self.is_scanning:
            self.stop_event.set()
            self.lbl_status.configure(text="Aborting...", text_color=C_WARNING)
            self.btn_start.configure(state="disabled")
            return

        if not self.dns_list or not self.domains:
            messagebox.showwarning("Warning", "Configuration empty. Load profiles or add data.")
            return

        self.is_scanning = True
        self.is_sorted = False
        self.stop_event.clear()
        self.results_data = {d["row_id"]: {} for d in self.dns_list}
        self.total_tasks = len(self.dns_list) * len(self.domains)
        self.completed_tasks = 0
        self.progress_bar.set(0)
        self.lbl_progress_text.configure(text=f"0 / {self.total_tasks}")
        self.combo_network.configure(state="disabled")
        
        self.btn_start.configure(text="🛑 Stop Scan", fg_color="#601410", text_color=C_ERROR, hover_color="#400D0B")
        self.lbl_status.configure(text="Benchmarking...", text_color=C_PRIMARY)
        
        for row_id in self.ui_cells:
            if "_grade" in self.ui_cells[row_id]: self.ui_cells[row_id]["_grade"].configure(text="-", text_color=C_TEXT_MUTED)
            if "_avg" in self.ui_cells[row_id]: self.ui_cells[row_id]["_avg"].configure(text="-")
            for dom in self.domains:
                if dom in self.ui_cells[row_id]: self.ui_cells[row_id][dom].configure(text="...", text_color=C_TEXT_MUTED)

        threading.Thread(target=self._scan_engine, daemon=True).start()

    def _scan_engine(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.current_workers) as exe:
            future_map = {}
            for d in self.dns_list:
                for dom in self.domains:
                    f = exe.submit(NetworkUtils.test_dns_domain, d["ip"], dom, self.current_timeout)
                    future_map[f] = (d["row_id"], dom)

            for future in concurrent.futures.as_completed(future_map):
                if self.stop_event.is_set(): break
                row_id, domain = future_map[future]
                try:
                    success, text, t_val = future.result()
                    self.update_queue.put((row_id, domain, success, text, t_val))
                except Exception:
                    self.update_queue.put((row_id, domain, False, "?", 0))

        self.update_queue.put(("DONE", None, None, None, None))

    def process_queue(self):
        while not self.update_queue.empty():
            try:
                row_id, domain, success, text, time_val = self.update_queue.get_nowait()
                
                if row_id == "DONE":
                    self.is_scanning = False
                    self.btn_start.configure(state="normal", text="🚀 Start Benchmark", fg_color=C_PRIMARY_BG, text_color=C_PRIMARY, hover_color="#063580")
                    self.combo_network.configure(state="normal")
                    self.progress_bar.set(1.0)
                    self.lbl_progress_text.configure(text=f"{self.total_tasks} / {self.total_tasks}")
                    
                    if self.stop_event.is_set():
                        self.lbl_status.configure(text="Scan Aborted", text_color=C_ERROR)
                    else:
                        self.lbl_status.configure(text="Scan Complete. Saving history...", text_color=C_SUCCESS)
                        self._save_to_history()
                        self.lbl_status.configure(text="Scan Complete & Saved", text_color=C_SUCCESS)
                    
                    for r_id in self.ui_cells:
                        avg, err_text = self.calculate_metrics(r_id)
                        if "_grade" in self.ui_cells[r_id] and err_text != "-": 
                            err_val = int(err_text)
                            c = C_SUCCESS if err_val == 0 else (C_WARNING if err_val <= 2 else C_ERROR)
                            self.ui_cells[r_id]["_grade"].configure(text=err_text, text_color=c)
                        if "_avg" in self.ui_cells[r_id]: 
                            self.ui_cells[r_id]["_avg"].configure(text=avg)
                else:
                    self.completed_tasks += 1
                    if self.total_tasks > 0:
                        self.progress_bar.set(self.completed_tasks / self.total_tasks)
                        self.lbl_progress_text.configure(text=f"{self.completed_tasks} / {self.total_tasks}")

                    self.results_data[row_id][domain] = {"success": success, "text": text, "time": time_val}

                    if row_id in self.ui_cells and domain in self.ui_cells[row_id]:
                        lbl = self.ui_cells[row_id][domain]
                        if success: lbl.configure(text=text, text_color=C_SUCCESS)
                        else: lbl.configure(text=text, text_color=C_ERROR, font=("Helvetica", 12))

            except queue.Empty: break
        self.after(50, self.process_queue)

    def _save_to_history(self):
        network = self.selected_network_var.get()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_file = "benchmark_history.csv"
        file_exists = os.path.exists(history_file)

        try:
            with open(history_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Network", "DNS_IP", "DNS_Name", "Errors", "Avg_Ping_ms"])

                for info in self.dns_list:
                    r_id = info["row_id"]
                    avg_ping_str, err_text = self.calculate_metrics(r_id)
                    
                    ping_val = -1
                    if "ms" in avg_ping_str:
                        ping_val = int(avg_ping_str.replace(" ms", ""))
                    
                    err_val = int(err_text) if err_text != "-" else len(self.domains)
                    
                    writer.writerow([timestamp, network, info["ip"], info["name"], err_val, ping_val])
        except Exception as e:
            print(f"Failed to save history: {e}")

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
                row_id = info["row_id"]
                row_res = self.results_data.get(row_id, {})
                success_count = sum(1 for d in self.domains if row_res.get(d, {}).get("success"))
                total_time = sum(row_res.get(d, {}).get("time", 0) for d in self.domains if row_res.get(d, {}).get("success"))
                        
                fail_count = len(self.domains) - success_count
                avg_ping = (total_time / success_count) if success_count > 0 else float('inf')
                return (fail_count, avg_ping)

            self.dns_list.sort(key=get_sort_key)
            self.is_sorted = True
            self.build_grid()
            
            for row_id, dom_data in self.results_data.items():
                if row_id in self.ui_cells:
                    avg, err_text = self.calculate_metrics(row_id)
                    if err_text != "-":
                        err_val = int(err_text)
                        c = C_SUCCESS if err_val == 0 else (C_WARNING if err_val <= 2 else C_ERROR)
                        self.ui_cells[row_id]["_grade"].configure(text=err_text, text_color=c)
                    self.ui_cells[row_id]["_avg"].configure(text=avg)
                    
                    for dom, res in dom_data.items():
                        if dom in self.ui_cells[row_id]:
                            lbl = self.ui_cells[row_id][dom]
                            if res["success"]: lbl.configure(text=res["text"], text_color=C_SUCCESS)
                            else: lbl.configure(text=res["text"], text_color=C_ERROR, font=("Helvetica", 12))

    def get_best_successful_dns(self):
        if not self.results_data: return []
            
        valid_dns = []
        for info in self.dns_list:
            row_id = info["row_id"]
            row_res = self.results_data.get(row_id, {})
            
            success_count = sum(1 for d in self.domains if row_res.get(d, {}).get("success"))
            if success_count > 0:
                original_line = f"{info['ip']} {info['name']}".strip()
                valid_dns.append(original_line)
                
        return valid_dns

    def export_csv(self):
        if self.display_mode == "history":
            messagebox.showwarning("Warning", "Exporting is available for Live scans only. You can find all history data directly in 'benchmark_history.csv'.")
            return

        if not self.results_data or self.is_scanning:
            messagebox.showwarning("Warning", "Complete a scan before exporting.")
            return

        fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Export CSV")
        if not fp: return

        try:
            with open(fp, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                display_domains = [ConfigManager.format_domain(d) for d in self.domains]
                headers = ["DNS IP", "Name", "System DNS", "Errors", "Avg Ping"] + display_domains
                writer.writerow(headers)

                for info in self.dns_list:
                    row_id = info["row_id"]
                    avg_ping, err_text = self.calculate_metrics(row_id)
                    row_data = [info["ip"], info["name"], "Yes" if info["is_system"] else "No", err_text, avg_ping]
                    
                    for dom in self.domains:
                        res = self.results_data.get(row_id, {}).get(dom, {})
                        row_data.append(res.get("text", "-") if res.get("success") else res.get("text", "Error"))
                        
                    writer.writerow(row_data)
            messagebox.showinfo("Success", f"Data exported to:\n{fp}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")


    def open_history(self):
        if not os.path.exists("benchmark_history.csv"):
            messagebox.showinfo("History", "No history found. Complete a benchmark scan first.")
            return

        win = ctk.CTkToplevel(self, fg_color=C_BG)
        win.title("Manage History")
        win.geometry("500x650")
        win.transient(self)
        win.grab_set()

        try:
            df = pd.read_csv("benchmark_history.csv")
        except Exception as e:
            messagebox.showerror("Error", f"Could not read history file: {e}", parent=win)
            win.destroy()
            return

        top_frame = ctk.CTkFrame(win, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(top_frame, text="📊 History Selector", font=("Helvetica", 22, "bold"), text_color=C_TEXT_MAIN).pack(side="left")

        scroll = ctk.CTkScrollableFrame(win, fg_color=C_CARD, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        checkboxes = {}
        updating_flag = {"state": False} 

        def on_master_toggle(net):
            if updating_flag["state"]: return
            updating_flag["state"] = True
            
            state = checkboxes[net]['master_var'].get()
            for var in checkboxes[net]['slaves'].values():
                var.set(state)
                
            updating_flag["state"] = False

        def on_slave_toggle(net):
            if updating_flag["state"]: return
            updating_flag["state"] = True
            
            all_checked = all(var.get() for var in checkboxes[net]['slaves'].values())
            checkboxes[net]['master_var'].set(all_checked)
            
            updating_flag["state"] = False

        for net, group in df.groupby("Network"):
            master_var = tk.BooleanVar(value=False)
            slave_vars = {}
            
            cb_master = ctk.CTkCheckBox(scroll, text=f"Network: {net}", font=("Helvetica", 15, "bold"), 
                                        variable=master_var, command=lambda n=net: on_master_toggle(n), text_color=C_PRIMARY)
            cb_master.pack(anchor="w", padx=10, pady=(15, 5))
            
            timestamps = sorted(group["Timestamp"].unique(), reverse=True)
            for ts in timestamps:
                var = tk.BooleanVar(value=False)
                
                cb_slave = ctk.CTkCheckBox(scroll, text=f"{ts}", font=("Helvetica", 13), 
                                           variable=var, command=lambda n=net: on_slave_toggle(n))
                cb_slave.pack(anchor="w", padx=(40, 10), pady=4)
                slave_vars[ts] = var
                
            checkboxes[net] = {'master_var': master_var, 'slaves': slave_vars}

        def load_aggregated():
            selected_criteria = []
            for net, data in checkboxes.items():
                for ts, var in data['slaves'].items():
                    if var.get():
                        selected_criteria.append((net, ts))

            if not selected_criteria:
                messagebox.showwarning("Warning", "Please select at least one test to aggregate.", parent=win)
                return

            self.load_history_data(selected_criteria, df)
            win.destroy()

        btn_load = ctk.CTkButton(win, text="📥 Load Aggregated Results", font=("Helvetica", 15, "bold"), 
                                 command=load_aggregated, fg_color=C_SUCCESS, text_color=C_BG, hover_color="#6BBA80", height=42)
        btn_load.pack(fill="x", padx=20, pady=(5, 20))


    def open_profiles_manager(self):
        win = ctk.CTkToplevel(self, fg_color=C_BG)
        win.title("Profile Manager")
        win.geometry("450x550")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        top_frame = ctk.CTkFrame(win, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(20, 5))
        
        ctk.CTkLabel(top_frame, text="📁 Profiles", font=("Helvetica", 20, "bold"), text_color=C_TEXT_MAIN).pack(side="left")

        def create_empty():
            name = simpledialog.askstring("New Empty Profile", "Enter profile name (e.g., gaming, work):", parent=win)
            if name:
                clean_name = "".join([c for c in name if c.isalnum() or c in " _-"]).strip().replace(" ", "_")
                if clean_name:
                    filename = f"config_{clean_name}.txt"
                    if filename not in ConfigManager.get_available_profiles():
                        ConfigManager.save_single_profile(filename, {"dns_list": [], "domain_list": [], "network_list": ["Default_Network"]})
                        win.destroy()
                        self.open_profiles_manager()
                    else:
                        messagebox.showwarning("Exists", "Profile already exists.", parent=win)

        btn_new = ctk.CTkButton(top_frame, text="+ New", font=("Helvetica", 12, "bold"), width=60, height=28, 
                                command=create_empty, fg_color=C_CARD, text_color=C_TEXT_MAIN, 
                                hover_color=C_BORDER, border_width=1, border_color=C_BORDER)
        btn_new.pack(side="right")

        scroll = ctk.CTkScrollableFrame(win, fg_color=C_CARD, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        profiles = ConfigManager.get_available_profiles()
        checkbox_vars = {}

        for prof in profiles:
            var = tk.BooleanVar(value=(prof in self.active_profiles))
            cb = ctk.CTkCheckBox(scroll, text=prof, variable=var, font=("Helvetica", 14), text_color=C_TEXT_MAIN)
            cb.pack(anchor="w", pady=8, padx=10)
            checkbox_vars[prof] = var

        def apply_load():
            selected = [p for p, var in checkbox_vars.items() if var.get()]
            self.load_selected_profiles(selected)
            win.destroy()

        def save_best_profile():
            best_dns_lines = self.get_best_successful_dns()
            if not best_dns_lines:
                messagebox.showwarning("Warning", "No successful DNS results found. All pings failed.", parent=win)
                return
                
            max_num = 0
            for p in profiles:
                match = re.match(r"config_best_(\d+)\.txt", p)
                if match:
                    num = int(match.group(1))
                    if num > max_num: max_num = num
                    
            new_filename = f"config_best_{max_num + 1}.txt"
            data_to_save = {"dns_list": best_dns_lines, "domain_list": self.domains, "network_list": self.networks}
            ConfigManager.save_single_profile(new_filename, data_to_save)
            messagebox.showinfo("Success", f"Saved {len(best_dns_lines)} working DNS servers to {new_filename}", parent=win)
            win.destroy()
            self.open_profiles_manager()

        btn_frame_main = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame_main.pack(fill="x", padx=20, pady=(10, 15))
        
        btn_load = ctk.CTkButton(btn_frame_main, text="📥 Load Selected", font=("Helvetica", 14, "bold"), 
                      command=apply_load, fg_color=C_SUCCESS, text_color=C_BG, hover_color="#6BBA80")
        btn_load.pack(side="left", expand=True, padx=(0, 5), fill="x")

        btn_best = ctk.CTkButton(btn_frame_main, text="🌟 Save Bests", font=("Helvetica", 14, "bold"), 
                                 command=save_best_profile, fg_color=C_PRIMARY_BG, text_color=C_PRIMARY)
        btn_best.pack(side="right", expand=True, padx=(5, 0), fill="x")

        def check_selections(*args):
            if any(var.get() for var in checkbox_vars.values()):
                btn_load.configure(state="normal", fg_color=C_SUCCESS, text_color=C_BG)
            else:
                btn_load.configure(state="disabled", fg_color=C_BORDER, text_color=C_TEXT_MUTED)

        for var in checkbox_vars.values():
            var.trace_add("write", check_selections)
        check_selections()

        if self.display_mode == "history" or not self.is_sorted or self.is_scanning:
            btn_best.configure(state="disabled", fg_color=C_BORDER, text_color=C_TEXT_MUTED)

    def open_settings(self):
        win = ctk.CTkToplevel(self, fg_color=C_BG)
        win.title("Settings")
        win.geometry("450x520")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="⚙️ Configuration", font=("Helvetica", 20, "bold"), text_color=C_TEXT_MAIN).pack(pady=(25, 10))

        profiles = ConfigManager.get_available_profiles()
        default_sel = profiles[0] if profiles else "None"
        
        sel_frame = ctk.CTkFrame(win, fg_color="transparent")
        sel_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(sel_frame, text="Select Profile to Edit:", font=("Helvetica", 13)).pack(side="left", padx=5)
        combo_profile = ctk.CTkComboBox(sel_frame, values=profiles, state="readonly", width=180)
        combo_profile.set(default_sel)
        combo_profile.pack(side="right")

        card = ctk.CTkFrame(win, fg_color=C_CARD, corner_radius=12)
        card.pack(fill="x", padx=30, pady=15, ipady=10)
        
        def open_editor_wrapper(list_key, title_name):
            sel_file = combo_profile.get()
            if not sel_file or sel_file == "None": return
            self._open_editor(sel_file, title_name, list_key)

        ctk.CTkButton(card, text="📝 Edit DNS List", font=("Helvetica", 14), command=lambda: open_editor_wrapper("dns_list", "DNS Servers"), 
                      fg_color="transparent", border_width=1, border_color=C_BORDER, text_color=C_TEXT_MAIN).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(card, text="🌐 Edit Domains", font=("Helvetica", 14), command=lambda: open_editor_wrapper("domain_list", "Domain Targets"), 
                      fg_color="transparent", border_width=1, border_color=C_BORDER, text_color=C_TEXT_MAIN).pack(pady=(0,10), padx=20, fill="x")
        ctk.CTkButton(card, text="📡 Edit Networks (ISPs)", font=("Helvetica", 14), command=lambda: open_editor_wrapper("network_list", "Network Targets"), 
                      fg_color="transparent", border_width=1, border_color=C_BORDER, text_color=C_TEXT_MAIN).pack(pady=(0,10), padx=20, fill="x")

        param_card = ctk.CTkFrame(win, fg_color=C_CARD, corner_radius=12)
        param_card.pack(fill="x", padx=30, pady=5)

        f1 = ctk.CTkFrame(param_card, fg_color="transparent")
        f1.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f1, text="Timeout (seconds):", font=("Helvetica", 13)).pack(side="left")
        e_timeout = ctk.CTkEntry(f1, width=80, justify="center")
        e_timeout.insert(0, str(self.current_timeout))
        e_timeout.pack(side="right")

        f2 = ctk.CTkFrame(param_card, fg_color="transparent")
        f2.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(f2, text="Thread Limit:", font=("Helvetica", 13)).pack(side="left")
        e_workers = ctk.CTkEntry(f2, width=80, justify="center")
        e_workers.insert(0, str(self.current_workers))
        e_workers.pack(side="right")

        def apply():
            try:
                self.current_timeout = float(e_timeout.get())
                self.current_workers = int(e_workers.get())
                win.destroy()
            except: messagebox.showerror("Error", "Numeric values required.", parent=win)

        ctk.CTkButton(win, text="Save App Settings", font=("Helvetica", 14, "bold"), command=apply, 
                      fg_color=C_PRIMARY_BG, text_color=C_PRIMARY, hover_color="#063580").pack(pady=15)

    def _open_editor(self, filename, title, key):
        win = ctk.CTkToplevel(self, fg_color=C_BG)
        win.title(f"Editing {filename}")
        win.geometry("500x600")
        win.transient(self)
        win.grab_set()

        file_data = ConfigManager.load_single_profile(filename)

        ctk.CTkLabel(win, text=f"Edit {title}", font=("Helvetica", 18, "bold"), text_color=C_TEXT_MAIN).pack(pady=(20, 5))
        ctk.CTkLabel(win, text=f"File: {filename}", font=("Helvetica", 12), text_color=C_TEXT_MUTED).pack(pady=(0, 10))
        
        tb = ctk.CTkTextbox(win, font=("Consolas", 14), fg_color=C_CARD, border_width=1, border_color=C_BORDER)
        tb.pack(padx=20, pady=10, fill="both", expand=True)
        tb.insert("1.0", "\n".join(file_data.get(key, [])))

        def save():
            lines = [line.strip() for line in tb.get("1.0", "end-1c").split("\n") if line.strip()]
            file_data[key] = lines
            ConfigManager.save_single_profile(filename, file_data)
            
            if filename in self.active_profiles:
                self.load_selected_profiles(self.active_profiles)
                
            win.destroy()

        ctk.CTkButton(win, text="Save File", font=("Helvetica", 14, "bold"), command=save, fg_color=C_SUCCESS, text_color=C_BG, hover_color="#6BBA80").pack(pady=20)

    def open_about(self):
        win = ctk.CTkToplevel(self, fg_color=C_BG)
        win.title("About")
        win.geometry("450x300")
        win.resizable(False, False)
        win.transient(self) 
        win.grab_set() 
        
        ctk.CTkLabel(win, text=f"BlueFalcon DNS Benchmark Pro", font=("Helvetica", 22, "bold"), text_color=C_TEXT_MAIN).pack(pady=(30, 0))
        ctk.CTkLabel(win, text=f"Version {APP_VERSION}", font=("Helvetica", 14), text_color=C_PRIMARY).pack()
        
        desc = "A highly optimized, multi-threaded networking utility engineered for accurate DNS latency and testing.\n\nFeatures profile workspaces, ISP Analytics history, and smart metrics."
        ctk.CTkLabel(win, text=desc, font=("Helvetica", 13), text_color=C_TEXT_MUTED, wraplength=380, justify="center").pack(padx=20, pady=25)
        
        ctk.CTkLabel(win, text="Developer: BlueFalcon", font=("Helvetica", 13, "bold"), text_color=C_TEXT_MAIN).pack()
        ctk.CTkLabel(win, text="Bluefalcon2270@gmail.com", font=("Helvetica", 12), text_color=C_TEXT_MUTED).pack()