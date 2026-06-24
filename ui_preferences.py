# Version 44.0 | File: ui_preferences.py | Preferences and Settings Modal
import os
import re
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
import pandas as pd

from core import ConfigManager
from ui_shared import C_BG, C_CARD, C_PRIMARY, C_PRIMARY_BG, C_SUCCESS, C_ERROR, C_WARNING, C_PRO, C_TEXT_MAIN, C_TEXT_MUTED, C_BORDER, get_resource_path, DataManager, APP_VERSION

class PreferencesBuilder:
    @staticmethod
    def open_preferences(app):
        win = ctk.CTkToplevel(app, fg_color=C_BG)
        win.title("Preferences")
        win.geometry("600x700")
        win.transient(app)
        win.grab_set()
        
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            win.iconbitmap(icon_path)

        tabview = ctk.CTkTabview(win, fg_color=C_CARD, corner_radius=24, segmented_button_fg_color=C_BG, segmented_button_selected_color=C_PRIMARY_BG, segmented_button_selected_hover_color="#0842A0", text_color=C_TEXT_MAIN)
        tabview.pack(fill="both", expand=True, padx=20, pady=20)

        tabview.add("Settings")
        tabview.add("Profiles")
        tabview.add("History")
        tabview.add("About")

        PreferencesBuilder._build_settings_tab(tabview.tab("Settings"), app, win)
        PreferencesBuilder._build_profiles_tab(tabview.tab("Profiles"), app, win)
        PreferencesBuilder._build_history_tab(tabview.tab("History"), app, win)
        PreferencesBuilder._build_about_tab(tabview.tab("About"), app, win)

    @staticmethod
    def _build_settings_tab(parent, app, win):
        profiles = ConfigManager.get_available_profiles()
        default_sel = profiles[0] if profiles else "None"
        
        sel_frame = ctk.CTkFrame(parent, fg_color="transparent")
        sel_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(sel_frame, text="Select Profile to Edit:", font=("Segoe UI", 13)).pack(side="left", padx=5)
        combo_profile = ctk.CTkComboBox(sel_frame, values=profiles, state="readonly", width=180, corner_radius=8, border_color=C_BORDER)
        combo_profile.set(default_sel)
        combo_profile.pack(side="right")

        card = ctk.CTkFrame(parent, fg_color=C_BG, corner_radius=24)
        card.pack(fill="x", padx=10, pady=15, ipady=10)
        
        def open_editor_wrapper(list_key, title_name):
            sel_file = combo_profile.get()
            if not sel_file or sel_file == "None": return
            PreferencesBuilder._open_editor(app, sel_file, title_name, list_key)

        ctk.CTkButton(card, text="📝 Edit DNS List", font=("Segoe UI", 14), command=lambda: open_editor_wrapper("dns_list", "DNS Servers"), 
                      fg_color="transparent", border_width=1, border_color=C_BORDER, text_color=C_TEXT_MAIN, corner_radius=24, height=40).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(card, text="🌐 Edit Domains", font=("Segoe UI", 14), command=lambda: open_editor_wrapper("domain_list", "Domain Targets"), 
                      fg_color="transparent", border_width=1, border_color=C_BORDER, text_color=C_TEXT_MAIN, corner_radius=24, height=40).pack(pady=(0,10), padx=20, fill="x")
        ctk.CTkButton(card, text="📡 Edit Networks (ISPs)", font=("Segoe UI", 14), command=lambda: open_editor_wrapper("network_list", "Network Targets"), 
                      fg_color="transparent", border_width=1, border_color=C_BORDER, text_color=C_TEXT_MAIN, corner_radius=24, height=40).pack(pady=(0,10), padx=20, fill="x")

        param_card = ctk.CTkFrame(parent, fg_color=C_BG, corner_radius=24)
        param_card.pack(fill="x", padx=10, pady=5)

        f1 = ctk.CTkFrame(param_card, fg_color="transparent")
        f1.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f1, text="Timeout (seconds):", font=("Segoe UI", 13)).pack(side="left")
        e_timeout = ctk.CTkEntry(f1, width=80, justify="center", corner_radius=8, border_color=C_BORDER)
        e_timeout.insert(0, str(app.current_timeout))
        e_timeout.pack(side="right")

        f2 = ctk.CTkFrame(param_card, fg_color="transparent")
        f2.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(f2, text="Thread Limit:", font=("Segoe UI", 13)).pack(side="left")
        e_workers = ctk.CTkEntry(f2, width=80, justify="center", corner_radius=8, border_color=C_BORDER)
        e_workers.insert(0, str(app.current_workers))
        e_workers.pack(side="right")

        def apply():
            try:
                app.current_timeout = float(e_timeout.get())
                app.current_workers = int(e_workers.get())
                messagebox.showinfo("Success", "Settings applied successfully.", parent=win)
            except: messagebox.showerror("Error", "Numeric values required.", parent=win)

        ctk.CTkButton(parent, text="Save App Settings", font=("Segoe UI", 14, "bold"), command=apply, 
                      fg_color=C_PRIMARY_BG, text_color=C_TEXT_MAIN, hover_color="#0842A0", corner_radius=24, height=40).pack(pady=15)

    @staticmethod
    def _open_editor(app, filename, title, key):
        win = ctk.CTkToplevel(app, fg_color=C_BG)
        win.title(f"Editing {filename}")
        win.geometry("500x600")
        win.transient(app)
        win.grab_set()
        
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            win.iconbitmap(icon_path)

        file_data = ConfigManager.load_single_profile(filename)

        ctk.CTkLabel(win, text=f"Edit {title}", font=("Segoe UI", 18, "bold"), text_color=C_TEXT_MAIN).pack(pady=(20, 5))
        ctk.CTkLabel(win, text=f"File: {filename}", font=("Segoe UI", 12), text_color=C_TEXT_MUTED).pack(pady=(0, 10))
        
        tb = ctk.CTkTextbox(win, font=("Consolas", 14), fg_color=C_CARD, border_width=1, border_color=C_BORDER, corner_radius=16)
        tb.pack(padx=20, pady=10, fill="both", expand=True)
        tb.insert("1.0", "\n".join(file_data.get(key, [])))

        def save():
            lines = [line.strip() for line in tb.get("1.0", "end-1c").split("\n") if line.strip()]
            file_data[key] = lines
            ConfigManager.save_single_profile(filename, file_data)
            
            if filename in app.active_profiles:
                app.load_selected_profiles(app.active_profiles)
            win.destroy()

        ctk.CTkButton(win, text="Save File", font=("Segoe UI", 14, "bold"), command=save, fg_color=C_SUCCESS, text_color=C_BG, hover_color="#6BBA80", corner_radius=24, height=40).pack(pady=20)


    @staticmethod
    def _build_profiles_tab(parent, app, win):
        def create_empty():
            name = simpledialog.askstring("New Empty Profile", "Enter profile name (e.g., gaming, work):", parent=win)
            if name:
                clean_name = "".join([c for c in name if c.isalnum() or c in " _-"]).strip().replace(" ", "_")
                if clean_name:
                    filename = f"config_{clean_name}.txt"
                    if filename not in ConfigManager.get_available_profiles():
                        ConfigManager.save_single_profile(filename, {"dns_list": [], "domain_list": [], "network_list": ["Default_Network"]})
                        win.destroy()
                        PreferencesBuilder.open_preferences(app)
                    else:
                        messagebox.showwarning("Exists", "Profile already exists.", parent=win)

        btn_new = ctk.CTkButton(parent, text="+ Create New Profile", font=("Segoe UI", 14, "bold"), height=40, corner_radius=24,
                                command=create_empty, fg_color=C_BG, text_color=C_TEXT_MAIN, 
                                hover_color=C_BORDER, border_width=1, border_color=C_BORDER)
        btn_new.pack(fill="x", padx=10, pady=(10, 5))

        scroll = ctk.CTkScrollableFrame(parent, fg_color=C_BG, corner_radius=16)
        scroll.pack(fill="both", expand=True, padx=10, pady=5)

        profiles = ConfigManager.get_available_profiles()
        checkbox_vars = {}

        for prof in profiles:
            var = tk.BooleanVar(value=(prof in app.active_profiles))
            cb = ctk.CTkCheckBox(scroll, text=prof, variable=var, font=("Segoe UI", 14), text_color=C_TEXT_MAIN, corner_radius=6, border_color=C_BORDER, hover_color=C_PRIMARY_BG)
            cb.pack(anchor="w", pady=8, padx=10)
            checkbox_vars[prof] = var

        def apply_load():
            selected = [p for p, var in checkbox_vars.items() if var.get()]
            app.load_selected_profiles(selected)
            all_profiles = ConfigManager.get_available_profiles()
            app.combo_profile.configure(values=["Select Profile"] + all_profiles)
            
            if selected:
                app.combo_profile.set(selected[0])
            else:
                app.combo_profile.set("Select Profile")
            win.destroy()

        def save_best_profile():
            best_dns_lines = DataManager.get_best_successful_dns(app.dns_list, app.domains, app.results_data)
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
            data_to_save = {"dns_list": best_dns_lines, "domain_list": app.domains, "network_list": app.networks}
            ConfigManager.save_single_profile(new_filename, data_to_save)
            messagebox.showinfo("Success", f"Saved {len(best_dns_lines)} working DNS servers to {new_filename}", parent=win)
            
            all_profiles = ConfigManager.get_available_profiles()
            app.combo_profile.configure(values=["Select Profile"] + all_profiles)
            
            win.destroy()
            PreferencesBuilder.open_preferences(app)

        btn_frame_main = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame_main.pack(fill="x", padx=10, pady=(10, 15))
        
        btn_load = ctk.CTkButton(btn_frame_main, text="📥 Load Selected", font=("Segoe UI", 14, "bold"), height=40, corner_radius=24,
                      command=apply_load, fg_color=C_SUCCESS, text_color=C_BG, hover_color="#6BBA80")
        btn_load.pack(side="left", expand=True, padx=(0, 5), fill="x")

        btn_best = ctk.CTkButton(btn_frame_main, text="🌟 Save Bests", font=("Segoe UI", 14, "bold"), height=40, corner_radius=24,
                                 command=save_best_profile, fg_color=C_PRIMARY_BG, text_color=C_TEXT_MAIN, hover_color="#0842A0")
        btn_best.pack(side="right", expand=True, padx=(5, 0), fill="x")

    @staticmethod
    def _build_history_tab(parent, app, win):
        if not os.path.exists("benchmark_history.csv"):
            ctk.CTkLabel(parent, text="No history found. Complete a benchmark scan first.", text_color=C_WARNING).pack(pady=30)
            return

        try:
            df = pd.read_csv("benchmark_history.csv")
        except Exception as e:
            ctk.CTkLabel(parent, text=f"Error reading history: {e}", text_color=C_ERROR).pack(pady=30)
            return

        scroll = ctk.CTkScrollableFrame(parent, fg_color=C_BG, corner_radius=16)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

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
            
            cb_master = ctk.CTkCheckBox(scroll, text=f"Network: {net}", font=("Segoe UI", 15, "bold"), 
                                        variable=master_var, command=lambda n=net: on_master_toggle(n), text_color=C_PRIMARY, corner_radius=6, border_color=C_BORDER, hover_color=C_PRIMARY_BG)
            cb_master.pack(anchor="w", padx=10, pady=(15, 5))
            
            timestamps = sorted(group["Timestamp"].unique(), reverse=True)
            for ts in timestamps:
                var = tk.BooleanVar(value=False)
                cb_slave = ctk.CTkCheckBox(scroll, text=f"{ts}", font=("Segoe UI", 13), 
                                           variable=var, command=lambda n=net: on_slave_toggle(n), corner_radius=6, border_color=C_BORDER, hover_color=C_PRIMARY_BG)
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
            app.load_history_data(selected_criteria, df)
            win.destroy()

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        btn_load = ctk.CTkButton(btn_frame, text="📥 Load History Data", font=("Segoe UI", 14, "bold"), height=40, corner_radius=24,
                                 command=load_aggregated, fg_color=C_SUCCESS, text_color=C_BG, hover_color="#6BBA80")
        btn_load.pack(side="left", expand=True, padx=(0, 5), fill="x")

        btn_export = ctk.CTkButton(btn_frame, text="💾 Export CSV", font=("Segoe UI", 14, "bold"), height=40, corner_radius=24,
                                   command=lambda: DataManager.export_csv(app.dns_list, app.domains, app.results_data, app.display_mode, app.is_scanning), 
                                   fg_color=C_BG, text_color=C_TEXT_MAIN, border_width=1, border_color=C_BORDER, hover_color=C_BORDER)
        btn_export.pack(side="right", expand=True, padx=(5, 0), fill="x")

    @staticmethod
    def _build_about_tab(parent, app, win):
        ctk.CTkLabel(parent, text="🌐", font=("Segoe UI Emoji", 48)).pack(pady=(40, 0))
        ctk.CTkLabel(parent, text=f"DNS Benchmark Pro", font=("Segoe UI", 24, "bold"), text_color=C_TEXT_MAIN).pack(pady=(10, 0))
        ctk.CTkLabel(parent, text=f"Version {APP_VERSION}", font=("Segoe UI", 14), text_color=C_PRIMARY).pack(pady=(5, 20))
        
        info_frame = ctk.CTkFrame(parent, fg_color=C_BG, corner_radius=24)
        info_frame.pack(fill="x", padx=40, pady=10, ipady=10)
        
        ctk.CTkLabel(info_frame, text="Developer:", font=("Segoe UI", 13), text_color=C_TEXT_MUTED).pack(pady=(10, 0))
        ctk.CTkLabel(info_frame, text="BlueFalcon", font=("Segoe UI", 16, "bold"), text_color=C_PRO).pack()

        def open_github():
            webbrowser.open_new_tab("https://github.com/bluefalcon2270/bluefalcon-dns-benchmark")

        btn_git = ctk.CTkButton(parent, text="⭐ GitHub Repository", font=("Segoe UI", 14, "bold"), command=open_github,
                                fg_color="#282A2C", hover_color="#383A3C", text_color=C_TEXT_MAIN, corner_radius=24, height=44)
        btn_git.pack(pady=30)