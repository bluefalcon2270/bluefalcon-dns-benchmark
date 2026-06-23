# ==========================================
# BlueFalcon DNS Benchmark Pro - Launcher
# ==========================================
import sys
import ctypes
from gui import ModernDNSApp
from core import APP_VERSION

if __name__ == "__main__":
    # Tell Windows Shell: "Do not group me with python.exe, I am my own software"
    if sys.platform.startswith('win'):
        try:
            myappid = f"bluefalcon.dnsbenchmark.pro.v{APP_VERSION}"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception: pass

    # Launch the main CustomTkinter application
    app = ModernDNSApp()
    app.mainloop()