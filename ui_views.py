# Version 46.0 | File: ui_views.py | Sidebar View Content Builders
import os
import re
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
import pandas as pd

from core import ConfigManager
from ui_shared import C_BG, C_CARD, C_PRIMARY, C_PRIMARY_BG, C_SUCCESS, C_ERROR, C_WARNING, C_PRO, C_TEXT_MAIN, C_TEXT_MUTED, C_BORDER, get_resource_path, DataManager, APP_VERSION

class ViewBuilder:
    @staticmethod
    def build_settings_view(app, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        
        ctk.CTkLabel(frame, text="⚙️ App Settings", font=("Segoe UI", 24, "bold"), text_color=C_TEXT_MAIN).pack(anchor="w", pady=(20, 30), padx=30)
        
        param_card = ctk.CTkFrame(frame, fg_color=C_CARD, corner_radius=24)
        param_card.pack(fill="x", padx=30, pady=5)

        f1 = ctk.CTkFrame(param_card, fg_color="transparent")
        f1.pack(fill="x", padx=30, pady=20)
        ctk.CTkLabel(f1, text="Timeout (seconds):", font=("Segoe UI", 14)).pack(side="left")
        e_timeout = ctk.CTkEntry(f1, width=100, justify="center", corner_radius=8, border_color=C_BORDER)
        e_timeout.insert(0, str(app.current_timeout))
        e_timeout.pack(side="right")

        f2 = ctk.CTkFrame(param_card, fg_color="transparent")
        f2.pack(fill="x", padx=30, pady=(0, 20))
        ctk.CTkLabel(f2, text="Thread Limit:", font=("Segoe UI", 14)).pack(side="left")
        e_workers = ctk.CTkEntry(f2, width=100, justify="center", corner_radius=8, border_color=C_BORDER)
        e_workers.insert(0, str(app.current_workers))
        e_workers.pack(side="right")

        def apply():
            try:
                app.current_timeout = float(e_timeout.get())
                app.current_workers = int(e_workers.get())
                messagebox.showinfo("Success", "Settings applied successfully.")
            except Exception: messagebox.showerror("Error", "Numeric values required.")

        ctk.CTkButton(param_card, text="Save Settings", font=("Segoe UI", 14, "bold"), command=apply, fg_color=C_PRIMARY_BG, text_color=C_TEXT_MAIN, corner_radius=24, height=40).pack(pady=20)
        return frame

    @staticmethod
    def build_profiles_view(app, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        
        ctk.CTkLabel(frame, text="📁 Profile Manager", font=("Segoe UI", 24, "bold"), text_color=C_TEXT_MAIN).pack(anchor="w", pady=(20, 20), padx=30)

        profiles = ConfigManager.get_available_profiles()
        default_sel = profiles[0] if profiles else "None"
        
        edit_card = ctk.CTkFrame(frame, fg_color=C_CARD, corner_radius=24)
        edit_card.pack(fill="both", expand=True, padx=30, pady=10)

        sel_frame = ctk.CTkFrame(edit_card, fg_color="transparent")
        sel_frame.pack(fill="x", padx=30, pady=15)
        ctk.CTkLabel(sel_frame, text="Select Target Profile:", font=("Segoe UI", 14, "bold")).pack(side="left")
        combo_profile = ctk.CTkComboBox(sel_frame, values=profiles, state="readonly", width=220, corner_radius=8, border_color=C_BORDER, justify="center")
        combo_profile.set(default_sel)
        combo_profile.pack(side="right")
        
        # Integrated Tabbed Workspace
        tabview = ctk.CTkTabview(edit_card, fg_color=C_BG, corner_radius=16, segmented_button_selected_color=C_PRIMARY_BG, segmented_button_unselected_color=C_BORDER)
        tabview.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        
        tab_dns = tabview.add("📝 DNS Servers")
        tab_dom = tabview.add("🌐 Domain Targets")
        tab_net = tabview.add("📡 Networks")
        
        editors = {}
        for tab, key in [(tab_dns, "dns_list"), (tab_dom, "domain_list"), (tab_net, "network_list")]:
            tb = ctk.CTkTextbox(tab, font=("Consolas", 14), fg_color=C_CARD, border_width=1, border_color=C_BORDER, corner_radius=12)
            tb.pack(padx=10, pady=10, fill="both", expand=True)
            editors[key] = tb

        def load_profile_into_tabs(filename):
            if not filename or filename == "None": return
            file_data = ConfigManager.load_single_profile(filename)
            for key, tb in editors.items():
                tb.delete("1.0", "end")
                tb.insert("1.0", "\n".join(file_data.get(key, [])))

        combo_profile.configure(command=load_profile_into_tabs)
        load_profile_into_tabs(default_sel)

        def create_empty():
            name = simpledialog.askstring("New Empty Profile", "Enter profile name:")
            if name:
                clean_name = "".join([c for c in name if c.isalnum() or c in " _-"]).strip().replace(" ", "_")
                if clean_name:
                    filename = f"config_{clean_name}.txt"
                    if filename not in ConfigManager.get_available_profiles():
                        ConfigManager.save_single_profile(filename, {"dns_list": [], "domain_list": [], "network_list": ["Default_Network"]})
                        app.refresh_sidebar_views()
                    else:
                        messagebox.showwarning("Exists", "Profile already exists.")

        def save_best_profile():
            best_dns_lines = DataManager.get_best_successful_dns(app.dns_list, app.domains, app.results_data)
            if not best_dns_lines:
                messagebox.showwarning("Warning", "No successful DNS results found.")
                return
            max_num = 0
            for p in profiles:
                match = re.match(r"config_best_(\d+)\.txt", p)
                if match: max_num = max(max_num, int(match.group(1)))
            new_filename = f"config_best_{max_num + 1}.txt"
            ConfigManager.save_single_profile(new_filename, {"dns_list": best_dns_lines, "domain_list": app.domains, "network_list": app.networks})
            messagebox.showinfo("Success", f"Saved {len(best_dns_lines)} working DNS servers to {new_filename}")
            app.refresh_sidebar_views()

        def save_current_tab():
            sel_file = combo_profile.get()
            if not sel_file or sel_file == "None": return
            current_tab_name = tabview.get()
            key_map = {"📝 DNS Servers": "dns_list", "🌐 Domain Targets": "domain_list", "📡 Networks": "network_list"}
            key = key_map[current_tab_name]
            
            file_data = ConfigManager.load_single_profile(sel_file)
            tb = editors[key]
            lines = [line.strip() for line in tb.get("1.0", "end-1c").split("\n") if line.strip()]
            file_data[key] = lines
            ConfigManager.save_single_profile(sel_file, file_data)
            if sel_file in app.active_profiles: 
                app.load_selected_profiles(app.active_profiles)
            messagebox.showinfo("Success", f"Saved changes inside {current_tab_name} to {sel_file}")

        action_card = ctk.CTkFrame(frame, fg_color="transparent")
        action_card.pack(fill="x", padx=30, pady=(10, 20))
        ctk.CTkButton(action_card, text="+ Create New Profile", font=("Segoe UI", 14, "bold"), height=42, corner_radius=24, command=create_empty, fg_color=C_CARD, text_color=C_TEXT_MAIN, border_width=1, border_color=C_BORDER).pack(side="left", expand=True, padx=(0, 5), fill="x")
        ctk.CTkButton(action_card, text="🌟 Extract Bests from Scan", font=("Segoe UI", 14, "bold"), height=42, corner_radius=24, command=save_best_profile, fg_color=C_PRIMARY_BG, text_color=C_TEXT_MAIN).pack(side="left", expand=True, padx=(5, 5), fill="x")
        ctk.CTkButton(action_card, text="💾 Save Current Tab Content", font=("Segoe UI", 14, "bold"), height=42, corner_radius=24, command=save_current_tab, fg_color=C_SUCCESS, text_color=C_BG, hover_color="#6BBA80").pack(side="left", expand=True, padx=(5, 0), fill="x")
        
        return frame

    @staticmethod
    def build_history_view(app, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        ctk.CTkLabel(frame, text="🕒 History Analytics", font=("Segoe UI", 24, "bold"), text_color=C_TEXT_MAIN).pack(anchor="w", pady=(20, 10), padx=30)
        
        if not os.path.exists("benchmark_history.csv"):
            ctk.CTkLabel(frame, text="No history found. Complete a benchmark scan first.", text_color=C_WARNING).pack(pady=30)
            return frame

        try: df = pd.read_csv("benchmark_history.csv")
        except Exception as e:
            ctk.CTkLabel(frame, text=f"Error reading history: {e}", text_color=C_ERROR).pack(pady=30)
            return frame

        scroll = ctk.CTkScrollableFrame(frame, fg_color=C_CARD, corner_radius=24)
        scroll.pack(fill="both", expand=True, padx=30, pady=10)

        checkboxes = {}
        updating_flag = {"state": False} 

        def on_master_toggle(net):
            if updating_flag["state"]: return
            updating_flag["state"] = True
            state = checkboxes[net]['master_var'].get()
            for var in checkboxes[net]['slaves'].values(): var.set(state)
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
            cb_master = ctk.CTkCheckBox(scroll, text=f"Network: {net}", font=("Segoe UI", 15, "bold"), variable=master_var, command=lambda n=net: on_master_toggle(n), text_color=C_PRIMARY, corner_radius=6, border_color=C_BORDER)
            cb_master.pack(anchor="w", padx=20, pady=(15, 5))
            
            for ts in sorted(group["Timestamp"].unique(), reverse=True):
                var = tk.BooleanVar(value=False)
                cb_slave = ctk.CTkCheckBox(scroll, text=f"{ts}", font=("Segoe UI", 13), variable=var, command=lambda n=net: on_slave_toggle(n), corner_radius=6, border_color=C_BORDER)
                cb_slave.pack(anchor="w", padx=(50, 10), pady=4)
                slave_vars[ts] = var
            checkboxes[net] = {'master_var': master_var, 'slaves': slave_vars}

        def load_aggregated():
            selected_criteria = [(net, ts) for net, data in checkboxes.items() for ts, var in data['slaves'].items() if var.get()]
            if not selected_criteria:
                messagebox.showwarning("Warning", "Please select at least one test to aggregate.")
                return
            app.load_history_data(selected_criteria, df)
            app.select_sidebar_frame("live")

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=(10, 20))
        ctk.CTkButton(btn_frame, text="📥 Load Selected to Dashboard", font=("Segoe UI", 14, "bold"), height=42, corner_radius=24, command=load_aggregated, fg_color=C_SUCCESS, text_color=C_BG, hover_color="#6BBA80").pack(side="left", expand=True, padx=(0, 5), fill="x")
        ctk.CTkButton(btn_frame, text="💾 Export Live CSV", font=("Segoe UI", 14, "bold"), height=42, corner_radius=24, command=lambda: DataManager.export_csv(app.dns_list, app.domains, app.results_data, app.display_mode, app.is_scanning), fg_color=C_BG, text_color=C_TEXT_MAIN, border_width=1, border_color=C_BORDER).pack(side="right", expand=True, padx=(5, 0), fill="x")
        
        return frame

    @staticmethod
    def build_about_view(app, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        ctk.CTkLabel(frame, text="ℹ️ About", font=("Segoe UI", 24, "bold"), text_color=C_TEXT_MAIN).pack(anchor="w", pady=(20, 20), padx=30)
        
        card = ctk.CTkFrame(frame, fg_color=C_CARD, corner_radius=24)
        card.pack(fill="x", padx=30, pady=10, ipady=20)
        
        ctk.CTkLabel(card, text="🌐", font=("Segoe UI Emoji", 54)).pack(pady=(20, 0))
        ctk.CTkLabel(card, text=f"DNS Benchmark Pro", font=("Segoe UI", 24, "bold"), text_color=C_TEXT_MAIN).pack(pady=(10, 0))
        ctk.CTkLabel(card, text=f"Version {APP_VERSION}", font=("Segoe UI", 14), text_color=C_PRIMARY).pack(pady=(5, 20))
        
        ctk.CTkLabel(card, text="Developer:", font=("Segoe UI", 13), text_color=C_TEXT_MUTED).pack(pady=(10, 0))
        ctk.CTkLabel(card, text="BlueFalcon", font=("Segoe UI", 16, "bold"), text_color=C_PRO).pack()

        ctk.CTkButton(card, text="⭐ GitHub Repository", font=("Segoe UI", 14, "bold"), command=lambda: webbrowser.open_new_tab("https://github.com/bluefalcon2270/bluefalcon-dns-benchmark"), fg_color="#282A2C", hover_color="#383A3C", text_color=C_TEXT_MAIN, corner_radius=24, height=44).pack(pady=30)
        return frame