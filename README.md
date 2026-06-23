<div align="center">

# 🦅 BlueFalcon DNS Benchmark Pro

**A professional Windows desktop utility to benchmark DNS latency, evaluate packet loss, and aggregate ISP analytics.**

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)
[![Version](https://img.shields.io/badge/Version-v2.0-007AFF?style=for-the-badge)](https://github.com/bluefalcon2270/bluefalcon-dns-benchmark/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@BlueFalcon2270)

<br />
</div>

A high-performance, multi-threaded Windows desktop application designed to take the guesswork out of optimizing your internet resolution. Operate in **Live Mode** to test custom nameservers against an array of web targets at 1,000 threads per second, or dive into the **Log Viewer** to analyze the backend system diagnostics.

## 🚀 How to Use

**Step 1: Download**
* Navigate to the **Releases** section on the right side of this repository.
* Download the compiled `BlueFalcon_DNS_Benchmark_Pro_v2.0.exe`. No installation is required.

**Step 2: First Launch**
* Place the `.exe` inside a dedicated folder anywhere on your computer.
* Double-click to run. The application will silently verify Administrator privileges and run an offline network pre-flight check before booting the main GUI.

**Step 3: Choose your Workflow**
* **Live Benchmarking:** Click **`🚀 Start Benchmark`**. The engine will spin up an asynchronous `QThread` pool, test all listed servers, and dynamically render results without freezing the UI.
* **Profile Builder:** Click **`⚙️ Preferences`**. Under the *Profile Builder* tab, you can use the graphical interface to instantly Add, Remove, and Save custom testing batches without ever touching a raw text file.
* **System Logging:** Switch the main workspace to the **`📝 System Logs`** tab to view real-time engine stdout/stderr diagnostics.

<br>

## 🌟 Architecture & Core Modules

Completely rewritten from the ground up in v2.0 using a strict **PyQt6 Model-View-Controller** design pattern:

* `main.py`: Entry point launcher. Enforces Windows OS exclusivity, injects the native Taskbar `AppUserModelID`, and handles global uncaught exceptions.
* `core.py`: The robust backend engine. Enforces Python 3.10+ `pathlib` standards, handles concurrent TCP socket polling, and maps local PowerShell data safely.
* `gui.py`: The PyQt6 rendering interface. Features custom dark-mode stylesheets, a unified TabWidget preferences modal, and input-validated QLineEdit modules.

<br>

## 💻 For Developers

Ensure you are running **Python 3.10+** on Windows.

1. **Clone the repository:**
```cmd
   git clone [https://github.com/bluefalcon2270/bluefalcon-dns-benchmark.git](https://github.com/bluefalcon2270/bluefalcon-dns-benchmark.git)
   cd bluefalcon-dns-benchmark
```

2. **Install dependencies:**
```cmd
   pip install -r requirements.txt
```
*(Requirements for v2.0: `PyQt6`, `dnspython`, `pandas`)*

3. **Launch Suite:**
```cmd
   python main.py
```

### PyInstaller Compilation (.exe)

When packing a multi-file Python project, point PyInstaller **strictly at the entry point**. It will analyze the AST and swallow `core.py` and `gui.py` automatically. 

Run this exact command in PowerShell to bundle the scripts and inject your universal `.ico` asset into the runtime extraction path:

```powershell
pyinstaller --noconsole --onefile --icon="icon.ico" --add-data='icon.ico;.' --name="BlueFalcon_DNS_Benchmark_Pro_v2.0" main.py
```

<br>

## ✅ Supported Systems

* **Windows 11:** Fully Supported (x64 / ARM64 via native OS emulation)
* **Windows 10:** Fully Supported (Requires native PowerShell 5.1+ for local Gateway auto-detection)