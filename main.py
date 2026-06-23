# ==========================================
# BlueFalcon DNS Benchmark Pro - Launcher
# ==========================================
import sys
import ctypes
import platform
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from gui import ModernDNSApp, DARK_STYLESHEET
from core import APP_VERSION, logger, AppUtils

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught runtime variance caught", exc_info=(exc_type, exc_value, exc_traceback))

def main():
    sys.excepthook = handle_exception
    
    app = QApplication(sys.argv)
    
    icon_path = AppUtils.get_resource_path("icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        
    app.setStyleSheet(DARK_STYLESHEET)

    if platform.system() != "Windows":
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Unsupported OS")
        msg.setText("BlueFalcon DNS Benchmark Pro is engineered exclusively for Windows 10/11 platforms.")
        msg.exec()
        sys.exit(1)

    try:
        myappid = f"bluefalcon.dnsbenchmark.pro.v{APP_VERSION}"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    try:
        window = ModernDNSApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Critical window system exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()