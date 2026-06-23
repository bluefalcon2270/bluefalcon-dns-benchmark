# ==========================================
# BlueFalcon DNS Benchmark Pro - GUI Module
# ==========================================
import sys
import csv
import concurrent.futures
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTabWidget, QTextEdit, QListWidget, QLineEdit, QInputDialog,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QIntValidator, QDoubleValidator

from core import APP_VERSION, AppUtils, NetworkUtils, ConfigManager, logger, LOG_FILE, BASE_DIR

# --- PyQt Dark Theme Stylesheet ---
DARK_STYLESHEET = """
QWidget {
    background-color: #121212;
    color: #E3E3E3;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QTableWidget {
    background-color: #1E1E1E;
    gridline-color: #444746;
    border: 1px solid #444746;
    border-radius: 8px;
}
QHeaderView::section {
    background-color: #121212;
    padding: 4px;
    border: 1px solid #444746;
    font-weight: bold;
}
QPushButton {
    background-color: #0742A0;
    color: #A8C7FA;
    border: none;
    border-radius: 15px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #063580;
}
QPushButton#successBtn {
    background-color: #81C995;
    color: #121212;
}
QPushButton#successBtn:hover {
    background-color: #6BBA80;
}
QPushButton#dangerBtn {
    background-color: #601410;
    color: #F28B82;
}
QPushButton#dangerBtn:hover {
    background-color: #400D0B;
}
QPushButton#outlineBtn {
    background-color: transparent;
    border: 1px solid #444746;
    color: #E3E3E3;
}
QPushButton#outlineBtn:hover {
    background-color: #1E1E1E;
}
QProgressBar {
    border: 1px solid #444746;
    border-radius: 4px;
    text-align: center;
    background-color: #1E1E1E;
}
QProgressBar::chunk {
    background-color: #A8C7FA;
}
QTabWidget::pane {
    border: 1px solid #444746;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #1E1E1E;
    border: 1px solid #444746;
    padding: 8px 20px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #0742A0;
    color: #A8C7FA;
}
QLineEdit, QListWidget, QTextEdit {
    background-color: #1E1E1E;
    border: 1px solid #444746;
    border-radius: 4px;
    padding: 4px;
}
"""

# --- Custom Log Handler to bridge Python logging to PyQt ---
class QLogSignal(QThread):
    new_log = pyqtSignal(str)

class QLogHandler(logging.Handler):
    def __init__(self, signal_emitter):
        super().__init__()
        self.signal_emitter = signal_emitter

    def emit(self, record):
        msg = self.format(record)
        self.signal_emitter.new_log.emit(msg)

# --- Background Worker Thread ---
class BenchmarkWorker(QThread):
    progress_update = pyqtSignal(str, str, bool, str, int)  # row_id, domain, success, text, time_val
    finished_scan = pyqtSignal()

    def __init__(self, dns_list, domains, timeout, workers):
        super().__init__()
        self.dns_list = dns_list
        self.domains = domains
        self.timeout = timeout
        self.max_workers = workers
        self._is_running = True

    def run(self):
        logger.info(f"Starting benchmark worker: {len(self.dns_list)} IPs, {len(self.domains)} Domains.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as exe:
            future_map = {}
            for d in self.dns_list:
                for dom in self.domains:
                    f = exe.submit(NetworkUtils.test_dns_domain, d["ip"], dom, self.timeout)
                    future_map[f] = (d["row_id"], dom)

            for future in concurrent.futures.as_completed(future_map):
                if not self._is_running:
                    break
                row_id, domain = future_map[future]
                try:
                    success, text, t_val = future.result()
                    self.progress_update.emit(row_id, domain, success, text, t_val)
                except Exception as e:
                    self.progress_update.emit(row_id, domain, False, "Err", 0)

        self.finished_scan.emit()

    def stop(self):
        self._is_running = False


# --- Preferences & Profile Builder Window ---
class PreferencesWindow(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumSize(600, 500)
        self.parent_app = parent

        self.tab_profiles = QWidget()
        self.tab_settings = QWidget()
        self.tab_about = QWidget()

        self.addTab(self.tab_profiles, "📁 Profile Builder")
        self.addTab(self.tab_settings, "⚙️ Settings")
        self.addTab(self.tab_about, "ℹ️ About")

        self.build_profile_tab()
        self.build_settings_tab()
        self.build_about_tab()

    def build_profile_tab(self):
        layout = QVBoxLayout(self.tab_profiles)
        
        # Profile Selector
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Select Profile:"))
        self.combo_profile = QComboBox()
        self.combo_profile.addItems(ConfigManager.get_available_profiles())
        self.combo_profile.currentTextChanged.connect(self.load_selected_profile_to_gui)
        top_layout.addWidget(self.combo_profile)
        
        btn_new_prof = QPushButton("+ New Profile")
        btn_new_prof.setObjectName("outlineBtn")
        btn_new_prof.clicked.connect(self.create_new_profile)
        top_layout.addWidget(btn_new_prof)
        layout.addLayout(top_layout)

        # Lists Grid
        grid = QGridLayout()
        grid.addWidget(QLabel("<b>DNS Servers</b> (IP Name)"), 0, 0)
        grid.addWidget(QLabel("<b>Domains</b>"), 0, 1)
        grid.addWidget(QLabel("<b>Networks</b>"), 0, 2)

        self.list_dns = QListWidget()
        self.list_domains = QListWidget()
        self.list_nets = QListWidget()

        grid.addWidget(self.list_dns, 1, 0)
        grid.addWidget(self.list_domains, 1, 1)
        grid.addWidget(self.list_nets, 1, 2)

        # Add/Remove Buttons
        def make_controls(list_widget, item_type):
            h = QHBoxLayout()
            b_add = QPushButton("+")
            b_rem = QPushButton("-")
            b_add.setObjectName("outlineBtn")
            b_rem.setObjectName("outlineBtn")
            b_add.clicked.connect(lambda: self.add_list_item(list_widget, item_type))
            b_rem.clicked.connect(lambda: self.remove_list_item(list_widget))
            h.addWidget(b_add)
            h.addWidget(b_rem)
            return h

        grid.addLayout(make_controls(self.list_dns, "DNS (e.g., 8.8.8.8 Google)"), 2, 0)
        grid.addLayout(make_controls(self.list_domains, "Domain (e.g., google.com)"), 2, 1)
        grid.addLayout(make_controls(self.list_nets, "Network Name"), 2, 2)

        layout.addLayout(grid)

        # Save Action
        btn_save = QPushButton("💾 Save Profile")
        btn_save.setObjectName("successBtn")
        btn_save.clicked.connect(self.save_profile_from_gui)
        layout.addWidget(btn_save)

        self.load_selected_profile_to_gui(self.combo_profile.currentText())

    def create_new_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name (e.g., Gaming):")
        if ok and name:
            clean = "".join([c for c in name if c.isalnum() or c in "_-"]).strip()
            filename = f"config_{clean}.txt"
            ConfigManager.save_single_profile(filename, {"dns_list": [], "domain_list": [], "network_list": ["Default_Network"]})
            self.combo_profile.clear()
            self.combo_profile.addItems(ConfigManager.get_available_profiles())
            self.combo_profile.setCurrentText(filename)

    def add_list_item(self, list_widget, item_type):
        text, ok = QInputDialog.getText(self, f"Add {item_type}", "Value:")
        if ok and text.strip():
            list_widget.addItem(text.strip())

    def remove_list_item(self, list_widget):
        for item in list_widget.selectedItems():
            list_widget.takeItem(list_widget.row(item))

    def load_selected_profile_to_gui(self, filename):
        if not filename: return
        data = ConfigManager.load_single_profile(filename)
        self.list_dns.clear()
        self.list_dns.addItems(data.get("dns_list", []))
        self.list_domains.clear()
        self.list_domains.addItems(data.get("domain_list", []))
        self.list_nets.clear()
        self.list_nets.addItems(data.get("network_list", []))

    def save_profile_from_gui(self):
        filename = self.combo_profile.currentText()
        if not filename: return
        data = {
            "dns_list": [self.list_dns.item(i).text() for i in range(self.list_dns.count())],
            "domain_list": [self.list_domains.item(i).text() for i in range(self.list_domains.count())],
            "network_list": [self.list_nets.item(i).text() for i in range(self.list_nets.count())]
        }
        ConfigManager.save_single_profile(filename, data)
        QMessageBox.information(self, "Success", f"Profile {filename} saved successfully.")
        if self.parent_app:
            self.parent_app.reload_active_profiles()

    def build_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)
        
        g = QGridLayout()
        g.addWidget(QLabel("Connection Timeout (Seconds):"), 0, 0)
        self.input_timeout = QLineEdit(str(self.parent_app.current_timeout if self.parent_app else 5.0))
        self.input_timeout.setValidator(QDoubleValidator(0.1, 30.0, 1))
        g.addWidget(self.input_timeout, 0, 1)

        g.addWidget(QLabel("Thread Worker Limit:"), 1, 0)
        self.input_threads = QLineEdit(str(self.parent_app.current_workers if self.parent_app else 1000))
        self.input_threads.setValidator(QIntValidator(1, 5000))
        g.addWidget(self.input_threads, 1, 1)

        layout.addLayout(g)
        layout.addStretch()

        btn_apply = QPushButton("Apply Settings")
        btn_apply.clicked.connect(self.apply_settings)
        layout.addWidget(btn_apply)

    def apply_settings(self):
        if self.parent_app:
            self.parent_app.current_timeout = float(self.input_timeout.text())
            self.parent_app.current_workers = int(self.input_threads.text())
            logger.info(f"Settings updated: Timeout={self.parent_app.current_timeout}, Threads={self.parent_app.current_workers}")
            QMessageBox.information(self, "Applied", "Settings applied for next scan.")

    def build_about_tab(self):
        layout = QVBoxLayout(self.tab_about)
        
        lbl_title = QLabel(f"<b>BlueFalcon DNS Benchmark Pro</b> v{APP_VERSION}")
        lbl_title.setFont(QFont("Segoe UI", 16))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_desc = QLabel("A highly optimized, multi-threaded networking utility engineered for accurate DNS latency and testing.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_desc)

        lbl_link = QLabel('<a href="https://github.com/bluefalcon2270/bluefalcon-dns-benchmark" style="color: #A8C7FA;">GitHub Repository</a>')
        lbl_link.setOpenExternalLinks(True)
        lbl_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_link)
        
        layout.addStretch()


# --- Main Application Window ---
class ModernDNSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"BlueFalcon DNS Benchmark Pro v{APP_VERSION}")
        self.setMinimumSize(1000, 700)
        
        # Pre-Flight Checks
        if not AppUtils.is_admin():
            logger.warning("Application launched without Administrator privileges. Some WMI queries may fail.")
        if not AppUtils.check_internet_connection():
            logger.warning("No internet connection detected. Scans will likely fail.")
            QMessageBox.warning(self, "Offline", "No active internet connection detected. Proceed with caution.")

        # App State
        self.current_timeout = 5.0
        self.current_workers = 1000
        self.active_profiles = []
        self.config_data = {}
        self.system_dns = NetworkUtils.get_system_dns()
        self.dns_list = []
        self.domains = []
        self.networks = []
        self.results_data = {}
        self.total_tasks = 0
        self.completed_tasks = 0
        self.worker = None

        self.init_ui()
        self.setup_logging_bridge()
        
        # Load default profile on start
        default_prof = ConfigManager.get_available_profiles()[0]
        self.active_profiles = [default_prof]
        self.reload_active_profiles()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar
        top_bar = QHBoxLayout()
        title = QLabel(f"🌐 <b>DNS Benchmark</b> <span style='color:{C_PRO};'>Pro</span>")
        title.setFont(QFont("Helvetica", 20))
        top_bar.addWidget(title)
        top_bar.addStretch()

        btn_prefs = QPushButton("⚙️ Preferences")
        btn_prefs.setObjectName("outlineBtn")
        btn_prefs.clicked.connect(self.open_preferences)
        top_bar.addWidget(btn_prefs)
        
        main_layout.addLayout(top_bar)

        # Controls Card
        control_card = QWidget()
        control_card.setObjectName("card")
        control_layout = QHBoxLayout(control_card)

        self.btn_start = QPushButton("🚀 Start Benchmark")
        self.btn_start.clicked.connect(self.toggle_scan)
        control_layout.addWidget(self.btn_start)

        control_layout.addWidget(QLabel("Network:"))
        self.combo_net = QComboBox()
        control_layout.addWidget(self.combo_net)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        control_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet(f"color: {C_WARNING}; font-weight: bold;")
        control_layout.addWidget(self.lbl_status)
        control_layout.addStretch()

        btn_export = QPushButton("💾 Export CSV")
        btn_export.setObjectName("outlineBtn")
        btn_export.clicked.connect(self.export_csv)
        control_layout.addWidget(btn_export)

        main_layout.addWidget(control_card)

        # Main Workspace Tab
        self.workspace = QTabWidget()
        self.tab_table = QWidget()
        self.tab_logs = QWidget()
        
        self.workspace.addTab(self.tab_table, "📊 Live Results")
        self.workspace.addTab(self.tab_logs, "📝 System Logs")

        # Setup Table Tab
        table_layout = QVBoxLayout(self.tab_table)
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.table)

        # Setup Logs Tab
        log_layout = QVBoxLayout(self.tab_logs)
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.log_viewer)

        main_layout.addWidget(self.workspace)

    def setup_logging_bridge(self):
        self.log_signal = QLogSignal()
        self.log_signal.new_log.connect(self.append_log)
        handler = QLogHandler(self.log_signal)
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)
        logger.info("Application initialized. GUI Logging active.")

    @pyqtSlot(str)
    def append_log(self, msg):
        self.log_viewer.append(msg)

    def open_preferences(self):
        self.prefs_win = PreferencesWindow(self)
        self.prefs_win.show()

    def reload_active_profiles(self):
        if not self.active_profiles: return
        self.config_data = ConfigManager.load_multiple_profiles(self.active_profiles)
        self.dns_list = ConfigManager.parse_dns_list(self.config_data.get("dns_list", []), self.system_dns)
        self.domains = self.config_data.get("domain_list", [])
        
        self.networks = self.config_data.get("network_list", ["Default"])
        self.combo_net.clear()
        self.combo_net.addItems(self.networks)

        self.build_table_headers()
        logger.info(f"Loaded profiles. Found {len(self.dns_list)} DNS targets and {len(self.domains)} domains.")

    def build_table_headers(self):
        self.table.clear()
        headers = ["DNS Server", "Sys", "Avg Ping", "Errors"] + [ConfigManager.format_domain(d) for d in self.domains]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.dns_list))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        for row, info in enumerate(self.dns_list):
            self.table.setItem(row, 0, QTableWidgetItem(f"{info['ip']} {info['name']}"))
            self.table.setItem(row, 1, QTableWidgetItem("★" if info['is_system'] else ""))
            self.table.setItem(row, 2, QTableWidgetItem("-"))
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            for col in range(len(self.domains)):
                self.table.setItem(row, 4 + col, QTableWidgetItem("..."))

    def toggle_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.btn_start.setEnabled(False)
            self.lbl_status.setText("Aborting...")
            logger.warning("Scan aborted by user.")
            return

        if not self.dns_list or not self.domains:
            QMessageBox.warning(self, "Warning", "Configuration empty. Add data via Preferences.")
            return

        self.results_data = {d["row_id"]: {} for d in self.dns_list}
        self.total_tasks = len(self.dns_list) * len(self.domains)
        self.completed_tasks = 0
        self.progress_bar.setMaximum(self.total_tasks)
        self.progress_bar.setValue(0)
        
        self.btn_start.setText("🛑 Stop Scan")
        self.btn_start.setObjectName("dangerBtn")
        self.btn_start.setStyleSheet("") # Force repaint
        self.lbl_status.setText("Benchmarking...")
        self.lbl_status.setStyleSheet(f"color: {C_PRIMARY};")

        self.worker = BenchmarkWorker(self.dns_list, self.domains, self.current_timeout, self.current_workers)
        self.worker.progress_update.connect(self.handle_progress)
        self.worker.finished_scan.connect(self.scan_finished)
        self.worker.start()

    @pyqtSlot(str, str, bool, str, int)
    def handle_progress(self, row_id, domain, success, text, time_val):
        self.completed_tasks += 1
        self.progress_bar.setValue(self.completed_tasks)
        
        self.results_data[row_id][domain] = {"success": success, "text": text, "time": time_val}
        
        # Find row index
        row_idx = int(row_id.split('_')[1])
        dom_idx = self.domains.index(domain)
        
        item = QTableWidgetItem(text)
        if success:
            item.setForeground(QColor(C_SUCCESS))
        else:
            item.setForeground(QColor(C_ERROR))
        self.table.setItem(row_idx, 4 + dom_idx, item)

        self.recalculate_row_metrics(row_idx, row_id)

    def recalculate_row_metrics(self, row_idx, row_id):
        row_res = self.results_data[row_id]
        successes, total_time, total_domains = 0, 0, len(self.domains)
        
        for dom in self.domains:
            res = row_res.get(dom, {})
            if res.get("success"):
                successes += 1
                total_time += res.get("time", 0)

        failures = total_domains - successes
        avg_ping = "Failed" if successes == 0 else f"{round(total_time / successes)} ms"

        pi = QTableWidgetItem(avg_ping)
        ei = QTableWidgetItem(str(failures))
        
        if failures == 0: ei.setForeground(QColor(C_SUCCESS))
        elif failures <= 2: ei.setForeground(QColor(C_WARNING))
        else: ei.setForeground(QColor(C_ERROR))

        self.table.setItem(row_idx, 2, pi)
        self.table.setItem(row_idx, 3, ei)

    @pyqtSlot()
    def scan_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("🚀 Start Benchmark")
        self.btn_start.setObjectName("")
        self.btn_start.setStyleSheet("")
        
        self.lbl_status.setText("Scan Complete. Saving...")
        self.lbl_status.setStyleSheet(f"color: {C_SUCCESS}; font-weight: bold;")
        self._save_to_history()
        self.lbl_status.setText("Scan Complete & Saved.")
        logger.info("Benchmark cycle completed.")

    def _save_to_history(self):
        network = self.combo_net.currentText()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_exists = (BASE_DIR / "benchmark_history.csv").exists()

        try:
            with open(BASE_DIR / "benchmark_history.csv", mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Network", "DNS_IP", "DNS_Name", "Errors", "Avg_Ping_ms"])

                for row_idx, info in enumerate(self.dns_list):
                    err_item = self.table.item(row_idx, 3)
                    ping_item = self.table.item(row_idx, 2)
                    
                    err_val = int(err_item.text()) if err_item and err_item.text().isdigit() else len(self.domains)
                    ping_val = int(ping_item.text().replace(" ms", "")) if ping_item and "ms" in ping_item.text() else -1
                    
                    writer.writerow([timestamp, network, info["ip"], info["name"], err_val, ping_val])
        except Exception as e:
            logger.error(f"Failed to save history CSV: {e}")

    def export_csv(self):
        if not self.results_data or (self.worker and self.worker.isRunning()):
            QMessageBox.warning(self, "Warning", "Complete a scan before exporting.")
            return

        fp, _ = filedialog.getSaveFileName(self, "Export CSV", "", "CSV files (*.csv)")
        if not fp: return

        try:
            with open(fp, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                headers = ["DNS IP", "Name", "System DNS", "Avg Ping", "Errors"] + [ConfigManager.format_domain(d) for d in self.domains]
                writer.writerow(headers)

                for row_idx, info in enumerate(self.dns_list):
                    ping_val = self.table.item(row_idx, 2).text()
                    err_val = self.table.item(row_idx, 3).text()
                    row_data = [info["ip"], info["name"], "Yes" if info["is_system"] else "No", ping_val, err_val]
                    
                    for dom in self.domains:
                        res = self.results_data.get(info["row_id"], {}).get(dom, {})
                        row_data.append(res.get("text", "-") if res.get("success") else res.get("text", "Error"))
                        
                    writer.writerow(row_data)
            logger.info(f"Data exported to: {fp}")
            QMessageBox.information(self, "Success", f"Data exported successfully.")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def closeEvent(self, event):
        """ Graceful application shutdown intercept. """
        logger.info("Application close requested. Cleaning up threads...")
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        logger.info("Shutdown complete.")
        event.accept()