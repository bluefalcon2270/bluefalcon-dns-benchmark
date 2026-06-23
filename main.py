# ==========================================
# BlueFalcon DNS Benchmark Pro - Launcher
# ==========================================
import sys
import ctypes
import platform
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

# Import GUI framework and Logic
from gui import ModernDNSApp, DARK_STYLESHEET
from core import APP_VERSION, logger

def handle_exception(exc_type, exc_value, exc_traceback):
    """ Global uncaught exception logger. """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def main():
    sys.excepthook = handle_exception
    
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)

    # Pre-Flight OS Enforcement
    if platform.system() != "Windows":
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Unsupported OS")
        msg.setText("BlueFalcon DNS Benchmark Pro is engineered exclusively for Windows 10/11.")
        msg.exec()
        sys.exit(1)

    # Windows Taskbar AppUserModelID Override
    try:
        myappid = f"bluefalcon.dnsbenchmark.pro.v{APP_VERSION}"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        logger.warning(f"Failed to inject AppUserModelID: {e}")

    # Launch Core Window
    try:
        window = ModernDNSApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Failed to start GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()