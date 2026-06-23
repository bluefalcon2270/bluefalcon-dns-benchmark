# ==========================================
# BlueFalcon DNS Benchmark Pro - GUI Module
# ==========================================
import sys
import logging
import queue
import concurrent.futures
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTabWidget, QTextEdit, QListWidget, QLineEdit, QInputDialog,
    QAbstractItemView, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QUrl, QTimer
from PyQt6.QtGui import QFont, QColor, QIntValidator, QDoubleValidator, QDesktopServices, QIcon

from core import APP_VERSION, AppUtils, NetworkUtils, ConfigManager, logger, LOG_FILE, BASE_DIR

# Material Design 3 Dark Theme Colors
C_SURFACE = "#131314"
C_CONTAINER = "#1E1F22"
C_PRIMARY = "#A8C7FA"      
C_PRIMARY_BG = "#0742A0"   
C_SUCCESS = "#81C995"      
C_ERROR = "#F28B82"        
C_WARNING = "#FDD663"      
C_PRO = "#FFD700"          
C_TEXT_MAIN = "#E3E3E3"
C_TEXT_MUTED = "#8E918F"
C_BORDER = "#444746"

# --- Google Material Design 3 (M3) Stylesheet ---
DARK_STYLESHEET = f"""
QWidget {{
    background-color: {C_SURFACE};
    color: {C_TEXT_MAIN};
    font-family: 'Roboto', 'Segoe UI', system-ui, sans-serif;
}}
QTableWidget {{
    background-color: {C_CONTAINER};
    gridline-color: {C_BORDER};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
}}
QHeaderView::section {{
    background-color: {C_SURFACE};
    padding: 6px;
    border: 1px solid {C_BORDER};
    font-weight: bold;
    font-size: 13px;
}}
QPushButton {{
    background-color: {C_PRIMARY_BG};
    color: {C_PRIMARY};
    border: none;
    border-radius: 16px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #063580;
}}
QPushButton#successBtn {{
    background-color: {C_SUCCESS};
    color: {C_SURFACE};
}}
QPushButton#successBtn:hover {{
    background-color: #6BBA80;
}}
QPushButton#dangerBtn {{
    background-color: #601410;
    color: {C_ERROR};
}}
QPushButton#dangerBtn:hover {{
    background-color: #400D0B;
}}
QPushButton#outlineBtn {{
    background-color: transparent;
    border: 1px solid {C_BORDER};
    color: {C_TEXT_MAIN};
}}
QPushButton#outlineBtn:hover {{
    background-color: {C_CONTAINER};
}}
QPushButton#iconBtn {{
    background-color: transparent;
    border: 1px solid {C_BORDER};
    border-radius: 20px;
    color: {C_TEXT_MAIN};
    padding: 0px;
    font-size: 20px;
}}
QPushButton#iconBtn:hover {{
    background-color: {C_CONTAINER};
}}
QPushButton#sortBtn {{
    background-color: transparent;
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    color: {C_TEXT_MAIN};
    padding: 2px 12px;
    margin-bottom: 6px;
    font-size: 18px;
}}
QPushButton#sortBtn:hover {{
    background-color: {C_CONTAINER};
}}
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {C_BORDER};
}}
QTabBar::tab {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 24px;
    margin-right: 4px;
    font-weight: bold;
    color: {C_TEXT_MUTED};
}}
QTabBar::tab:selected {{
    color: {C_PRIMARY};
    border-bottom: 2px solid {C_PRIMARY};
}}
QTabBar::tab:hover {{
    color: {C_TEXT_MAIN};
}}
QLineEdit, QListWidget, QTextEdit, QComboBox {{
    background-color: {C_CONTAINER};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {C_PRIMARY_BG};
}}
QComboBox::drop-down {{
    border: none;
}}
"""

class QLogSignal(QThread):
    new_log = pyqtSignal(str)

class QLogHandler(logging.Handler):
    def __init__(self, signal_emitter):
        super().__init__()
        self.signal_emitter = signal_emitter

    def emit(self, record):
        msg = self.format(record)
        self.signal_emitter.new_log.emit(msg)

class BenchmarkWorker(QThread):
    finished_scan = pyqtSignal()

    def __init__(self, dns_list, domains, timeout, workers, result_queue):
        super().__init__()
        self.dns_list = dns_list
        self.domains = domains
        self.timeout = timeout
        self.max_workers = workers
        self.result_queue = result_queue
        self._is_running = True
        self.exe = None

    def run(self):
        logger.info(f"Initializing standard concurrent lookup mapping thread architecture.")
        self.exe = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        future_map = {}
        
        for d in self.dns_list:
            for dom in self.domains:
                if not self._is_running:
                    break
                f = self.exe.submit(NetworkUtils.test_dns_domain, d["ip"], dom, self.timeout)
                future_map[f] = (d["row_id"], dom)

        try:
            for future in concurrent.futures.as_completed(future_map):
                if not self._is_running:
                    break
                row_id, domain = future_map[future]
                try:
                    success, text, t_val = future.result()
                    self.result_queue.put((row_id, domain, success, text, t_val))
                except Exception:
                    self.result_queue.put((row_id, domain, False, "Err", 0))
        except Exception as e:
            logger.error(f"Worker iteration exception: {e}")
        finally:
            if self.exe:
                # Cancel pending unstarted threads immediately 
                self.exe.shutdown(wait=False, cancel_futures=True)
            self.result_queue.put("DONE")
            self.finished_scan.emit()

    def stop(self):
        self._is_running = False
        if self.exe:
            # Force threadpool to dump queue instantly on abort
            self.exe.shutdown(wait=False, cancel_futures=True)

class AddDNSDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add DNS Server")
        self.setFixedSize(350, 160)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g., 1.1.1.1")
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Cloudflare")
        
        form.addRow("IP Address:", self.ip_input)
        form.addRow("Provider Name:", self.name_input)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        ip = self.ip_input.text().strip()
        name = self.name_input.text().strip()
        if not ip:
            return None
        return f"{ip} {name}".strip()

class PreferencesWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumSize(600, 520)
        self.parent_app = parent

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_profiles = QWidget()
        self.tab_settings = QWidget()
        self.tab_about = QWidget()

        self.tabs.addTab(self.tab_profiles, "📁 Profile Builder")
        self.tabs.addTab(self.tab_settings, "⚙️ Settings")
        self.tabs.addTab(self.tab_about, "ℹ️ About")

        self.build_profile_tab()
        self.build_settings_tab()
        self.build_about_tab()

    def build_profile_tab(self):
        layout = QVBoxLayout(self.tab_profiles)
        layout.setContentsMargins(15, 20, 15, 15)
        
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

        grid = QGridLayout()
        grid.addWidget(QLabel("<b>DNS Servers</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Domains</b>"), 0, 1)
        grid.addWidget(QLabel("<b>Networks</b>"), 0, 2)

        self.list_dns = QListWidget()
        self.list_domains = QListWidget()
        self.list_nets = QListWidget()

        grid.addWidget(self.list_dns, 1, 0)
        grid.addWidget(self.list_domains, 1, 1)
        grid.addWidget(self.list_nets, 1, 2)

        def make_controls(list_widget, add_callback):
            h = QHBoxLayout()
            b_add = QPushButton("+")
            b_rem = QPushButton("-")
            b_add.setObjectName("outlineBtn")
            b_rem.setObjectName("outlineBtn")
            b_add.clicked.connect(add_callback)
            b_rem.clicked.connect(lambda: self.remove_list_item(list_widget))
            h.addWidget(b_add)
            h.addWidget(b_rem)
            return h

        grid.addLayout(make_controls(self.list_dns, self.add_dns_item), 2, 0)
        grid.addLayout(make_controls(self.list_domains, lambda: self.add_simple_item(self.list_domains, "Domain")), 2, 1)
        grid.addLayout(make_controls(self.list_nets, lambda: self.add_simple_item(self.list_nets, "Network Name")), 2, 2)

        layout.addLayout(grid)

        btn_save = QPushButton("💾 Save Profile")
        btn_save.setObjectName("successBtn")
        btn_save.clicked.connect(self.save_profile_from_gui)
        layout.addWidget(btn_save)

        self.load_selected_profile_to_gui(self.combo_profile.currentText())

    def create_new_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name:")
        if ok and name:
            clean = "".join([c for c in name if c.isalnum() or c in "_-"]).strip()
            filename = f"config_{clean}.txt"
            ConfigManager.save_single_profile(filename, {"dns_list": [], "domain_list": [], "network_list": ["Default_Network"]})
            self.combo_profile.clear()
            self.combo_profile.addItems(ConfigManager.get_available_profiles())
            self.combo_profile.setCurrentText(filename)

            if self.parent_app:
                self.parent_app.refresh_profile_list()

    def add_dns_item(self):
        dialog = AddDNSDialog(self)
        if dialog.exec():
            val = dialog.get_data()
            if val:
                self.list_dns.addItem(val)

    def add_simple_item(self, list_widget, title):
        text, ok = QInputDialog.getText(self, "Add Item", title)
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
        QMessageBox.information(self, "Success", f"Profile configuration written successfully to workspace directory.")
        if self.parent_app:
            self.parent_app.refresh_profile_list()
            self.parent_app.reload_active_profiles()

    def build_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)
        layout.setContentsMargins(30, 30, 30, 30)
        
        g = QGridLayout()
        g.addWidget(QLabel("Connection Timeout (Seconds):"), 0, 0)
        self.input_timeout = QLineEdit(str(self.parent_app.current_timeout if self.parent_app else 5.0))
        self.input_timeout.setValidator(QDoubleValidator(0.1, 30.0, 1))
        g.addWidget(self.input_timeout, 0, 1)

        g.addWidget(QLabel("Thread Worker Limit:"), 1, 0)
        self.input_threads = QLineEdit(str(self.parent_app.current_workers if self.parent_app else 100))
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
            QMessageBox.information(self, "Applied", "Settings applied for next scan.")

    def build_about_tab(self):
        layout = QVBoxLayout(self.tab_about)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel(f"<b>BlueFalcon DNS Benchmark Pro</b>")
        lbl_title.setFont(QFont("Segoe UI", 22))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_version = QLabel(f"Version {APP_VERSION}")
        lbl_version.setFont(QFont("Segoe UI", 12))
        lbl_version.setStyleSheet(f"color: {C_PRIMARY};")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_version)
        
        layout.addSpacing(20)

        lbl_desc = QLabel("A highly optimized, multi-threaded Windows networking utility engineered for accurate DNS latency benchmarking.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet(f"color: {C_TEXT_MUTED};")
        layout.addWidget(lbl_desc)
        
        layout.addSpacing(20)

        lbl_dev = QLabel("<b>Developer:</b> BlueFalcon")
        lbl_dev.setFont(QFont("Segoe UI", 12))
        lbl_dev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_dev)

        layout.addSpacing(30)

        btn_github = QPushButton("🌐 View Source on GitHub")
        btn_github.setFixedWidth(240)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/bluefalcon2270/bluefalcon-dns-benchmark")))
        layout.addWidget(btn_github, alignment=Qt.AlignmentFlag.AlignCenter)


class ModernDNSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"BlueFalcon DNS Benchmark Pro v{APP_VERSION}")
        self.setMinimumSize(1050, 700)
        
        if not AppUtils.is_admin():
            logger.warning("Application launched without Administrator privileges. Some WMI queries may fail.")
        if not AppUtils.check_internet_connection():
            logger.warning("No internet connection detected. Scans will likely fail.")
            QMessageBox.warning(self, "Offline", "No active internet connection detected. Proceed with caution.")

        self.current_timeout = 5.0
        self.current_workers = 100
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
        self.is_scanning = False

        self.result_queue = queue.Queue()
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.process_queue)

        self.init_ui()
        self.setup_logging_bridge()
        
        available = ConfigManager.get_available_profiles()
        if available:
            self.active_profiles = [available[0]]
            self.refresh_profile_list()
            self.reload_active_profiles()

    def _create_centered_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def set_progress_state(self, state: str):
        base_style = f"QProgressBar {{ border: 1px solid {C_BORDER}; border-radius: 4px; text-align: center; background-color: {C_CONTAINER}; "
        if state == "idle":
            color = "#5F6368"
            text_color = C_TEXT_MAIN
        elif state == "running":
            color = C_PRIMARY
            text_color = C_SURFACE
        elif state == "success":
            color = C_SUCCESS
            text_color = C_SURFACE
        elif state == "aborted":
            color = C_ERROR
            text_color = C_SURFACE
        else:
            color = "#5F6368"
            text_color = C_TEXT_MAIN
            
        self.progress_bar.setStyleSheet(f"{base_style} color: {text_color}; }} QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(15)

        self.btn_start = QPushButton("🚀 Start Benchmark")
        self.btn_start.setMinimumWidth(160)
        self.btn_start.clicked.connect(self.toggle_scan)
        top_bar.addWidget(self.btn_start)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedWidth(250)
        self.progress_bar.setFixedHeight(24)
        top_bar.addWidget(self.progress_bar)
        self.set_progress_state("idle")

        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet(f"color: {C_WARNING}; font-weight: bold; font-size: 13px;")
        top_bar.addWidget(self.lbl_status)

        top_bar.addStretch()

        self.combo_net = QComboBox()
        self.combo_net.setFixedWidth(160)
        top_bar.addWidget(self.combo_net)

        self.combo_profile_main = QComboBox()
        self.combo_profile_main.setFixedWidth(160)
        self.combo_profile_main.currentTextChanged.connect(self.switch_profile)
        top_bar.addWidget(self.combo_profile_main)

        btn_prefs = QPushButton("⚙")
        btn_prefs.setObjectName("iconBtn")
        btn_prefs.setToolTip("Preferences")
        btn_prefs.setFixedSize(40, 40)
        btn_prefs.clicked.connect(self.open_preferences)
        top_bar.addWidget(btn_prefs)

        main_layout.addLayout(top_bar)
        main_layout.addSpacing(10)

        self.workspace = QTabWidget()
        
        btn_sort = QPushButton("⇕")
        btn_sort.setObjectName("sortBtn")
        btn_sort.setToolTip("Sort")
        btn_sort.clicked.connect(self.sort_results)
        self.workspace.setCornerWidget(btn_sort, Qt.Corner.TopRightCorner)

        self.tab_table = QWidget()
        self.tab_logs = QWidget()
        
        self.workspace.addTab(self.tab_table, "📊 Live Results")
        self.workspace.addTab(self.tab_logs, "📝 System Logs")

        table_layout = QVBoxLayout(self.tab_table)
        table_layout.setContentsMargins(0, 10, 0, 0)
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        table_layout.addWidget(self.table)

        log_layout = QVBoxLayout(self.tab_logs)
        log_layout.setContentsMargins(0, 10, 0, 0)
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

    @pyqtSlot(str)
    def append_log(self, msg):
        self.log_viewer.append(msg)

    def open_preferences(self):
        self.prefs_win = PreferencesWindow(self)
        self.prefs_win.exec()

    def refresh_profile_list(self):
        current = self.combo_profile_main.currentText()
        self.combo_profile_main.blockSignals(True)
        self.combo_profile_main.clear()
        profiles = ConfigManager.get_available_profiles()
        self.combo_profile_main.addItems(profiles)
        if current in profiles:
            self.combo_profile_main.setCurrentText(current)
        elif profiles:
            self.combo_profile_main.setCurrentText(profiles[0])
        self.combo_profile_main.blockSignals(False)

    def switch_profile(self, profile_name):
        if profile_name and not self.is_scanning:
            self.active_profiles = [profile_name]
            self.reload_active_profiles()

    def reload_active_profiles(self):
        if not self.active_profiles: return
        self.config_data = ConfigManager.load_multiple_profiles(self.active_profiles)
        self.dns_list = ConfigManager.parse_dns_list(self.config_data.get("dns_list", []), self.system_dns)
        self.domains = self.config_data.get("domain_list", [])
        
        self.networks = self.config_data.get("network_list", ["Default"])
        self.combo_net.clear()
        self.combo_net.addItems(self.networks)

        self.build_table_headers()

    def build_table_headers(self):
        self.table.clear()
        headers = ["DNS Server", "Avg Ping", "Errors"] + [ConfigManager.format_domain(d) for d in self.domains]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.dns_list))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        for row, info in enumerate(self.dns_list):
            sys_mark = " ★" if info['is_system'] else ""
            self.table.setItem(row, 0, self._create_centered_item(f"{info['ip']} {info['name']}{sys_mark}"))
            self.table.setItem(row, 1, self._create_centered_item("-"))
            self.table.setItem(row, 2, self._create_centered_item("-"))
            for col in range(len(self.domains)):
                self.table.setItem(row, 3 + col, self._create_centered_item("..."))

    def toggle_scan(self):
        if self.is_scanning:
            self.is_scanning = False
            self.lbl_status.setText("Aborting immediately...")
            self.set_progress_state("aborted")
            
            self.btn_start.setEnabled(False)
            self.btn_start.setText("Stopping...")
            
            if self.worker:
                self.worker.stop()
                
            self.queue_timer.stop()
            
            while not self.result_queue.empty():
                try: self.result_queue.get_nowait()
                except queue.Empty: break
                    
            self.btn_start.setEnabled(True)
            self.btn_start.setText("🚀 Start Benchmark")
            self.btn_start.setObjectName("")
            self.btn_start.setStyleSheet("")
            self.combo_net.setEnabled(True)
            self.combo_profile_main.setEnabled(True)
            return

        if not self.dns_list or not self.domains:
            QMessageBox.warning(self, "Warning", "Configuration lists are currently empty.")
            return

        self.is_scanning = True
        self.results_data = {d["row_id"]: {} for d in self.dns_list}
        self.total_tasks = len(self.dns_list) * len(self.domains)
        self.completed_tasks = 0
        self.progress_bar.setMaximum(self.total_tasks)
        self.progress_bar.setValue(0)
        self.set_progress_state("running")
        
        self.combo_net.setEnabled(False)
        self.combo_profile_main.setEnabled(False)

        self.btn_start.setText("🛑 Stop Scan")
        self.btn_start.setObjectName("dangerBtn")
        self.btn_start.setStyleSheet("") 
        self.lbl_status.setText("Benchmarking...")
        self.lbl_status.setStyleSheet(f"color: {C_PRIMARY}; font-weight: bold;")

        while not self.result_queue.empty():
            try: self.result_queue.get_nowait()
            except queue.Empty: break

        self.worker = BenchmarkWorker(self.dns_list, self.domains, self.current_timeout, self.current_workers, self.result_queue)
        self.worker.finished_scan.connect(self.scan_finished)
        self.worker.start()
        self.queue_timer.start(30)

    def _process_single_result(self, item):
        row_id, domain, success, text, time_val = item
        
        self.completed_tasks += 1
        self.progress_bar.setValue(self.completed_tasks)
        
        if row_id not in self.results_data:
            return
            
        self.results_data[row_id][domain] = {"success": success, "text": text, "time": time_val}
        
        row_idx = int(row_id.split('_')[1])
        dom_idx = self.domains.index(domain)
        
        cell_item = self._create_centered_item(text)
        if success:
            cell_item.setForeground(QColor(C_SUCCESS))
        else:
            cell_item.setForeground(QColor(C_ERROR))
        self.table.setItem(row_idx, 3 + dom_idx, cell_item)

        self.recalculate_row_metrics(row_idx, row_id)

    def process_queue(self):
        if self.result_queue.empty():
            return
            
        processed = 0
        
        # Pausing graphical updates during batched injection completely mitigates UI stutter
        self.table.setUpdatesEnabled(False)
        
        while not self.result_queue.empty() and processed < 150:
            try:
                item = self.result_queue.get_nowait()
                if item == "DONE":
                    break
                self._process_single_result(item)
            except queue.Empty:
                break
            processed += 1
            
        self.table.setUpdatesEnabled(True)

    def recalculate_row_metrics(self, row_idx, row_id):
        if row_id not in self.results_data: return
        row_res = self.results_data[row_id]
        successes, total_time, total_domains = 0, 0, len(self.domains)
        
        for dom in self.domains:
            res = row_res.get(dom, {})
            if res.get("success"):
                successes += 1
                total_time += res.get("time", 0)

        failures = total_domains - successes
        avg_ping = "Failed" if successes == 0 else f"{round(total_time / successes)} ms"

        pi = self._create_centered_item(avg_ping)
        ei = self._create_centered_item(str(failures))
        
        if failures == 0: ei.setForeground(QColor(C_SUCCESS))
        elif failures <= 2: ei.setForeground(QColor(C_WARNING))
        else: ei.setForeground(QColor(C_ERROR))

        self.table.setItem(row_idx, 1, pi)
        self.table.setItem(row_idx, 2, ei)

    @pyqtSlot()
    def scan_finished(self):
        self.queue_timer.stop()
        
        self.table.setUpdatesEnabled(False)
        while not self.result_queue.empty():
            try:
                item = self.result_queue.get_nowait()
                if item != "DONE":
                    self._process_single_result(item)
            except queue.Empty:
                break
        self.table.setUpdatesEnabled(True)

        self.btn_start.setEnabled(True)
        self.combo_net.setEnabled(True)
        self.combo_profile_main.setEnabled(True)
        
        if self.is_scanning:
            self.is_scanning = False
            self.btn_start.setText("🚀 Start Benchmark")
            self.btn_start.setObjectName("")
            self.btn_start.setStyleSheet("")
            
            self.set_progress_state("success")
            self.lbl_status.setText("Scan Complete.")
            self.lbl_status.setStyleSheet(f"color: {C_SUCCESS}; font-weight: bold; font-size: 13px;")
            
        logger.info("Benchmark cycle ended.")

    def sort_results(self):
        if not self.results_data or (self.worker and self.worker.isRunning()):
            QMessageBox.information(self, "Info", "Complete a baseline run before sorting metrics.")
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
        self.build_table_headers()
        
        self.table.setUpdatesEnabled(False)
        for row_idx, info in enumerate(self.dns_list):
            row_id = info["row_id"]
            dom_data = self.results_data.get(row_id, {})
            
            self.recalculate_row_metrics(row_idx, row_id)
            for dom, res in dom_data.items():
                dom_idx = self.domains.index(dom)
                item = self._create_centered_item(res.get("text", "-"))
                if res.get("success"):
                    item.setForeground(QColor(C_SUCCESS))
                else:
                    item.setForeground(QColor(C_ERROR))
                self.table.setItem(row_idx, 3 + dom_idx, item)
        self.table.setUpdatesEnabled(True)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()