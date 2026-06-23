<div align="center">

# 🦅 BlueFalcon DNS Benchmark Pro

**A professional Windows desktop utility to benchmark DNS latency, evaluate packet loss, and aggregate ISP analytics.**

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)
[![Version](https://img.shields.io/badge/Version-v1.0-007AFF?style=for-the-badge)](https://github.com/bluefalcon2270/bluefalcon-dns-benchmark/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@BlueFalcon2270)

<br />
</div>

A high-performance, multi-threaded Windows desktop application designed to take the guesswork out of optimizing your internet resolution. Operate in **Live Mode** to test custom nameservers against an array of web targets at 1,000 threads per second, or switch to **History Mode** to analyze your local ISP's long-term routing health.

![alt text](<app_screenshot.png>)

## 🚀 How to Use

**Step 1: Download**
* Navigate to the **Releases** section on the right side of this repository.
* Download the compiled `BlueFalcon_DNS_Benchmark_Pro_v1.0.exe`. No installation is required.

**Step 2: First Launch**
* Place the `.exe` inside a dedicated folder anywhere on your computer.
* Double-click to run. The application will automatically trigger a background PowerShell request to detect and map your router's default Windows local gateway DNS.

**Step 3: Choose your Workflow**
* **Live Benchmarking:** Click **`🚀 Start Benchmark`**. The engine will spin up its asynchronous pool, test all listed servers against your target domains, calculate packet drop rates, and assign each server a real-time reliability grade.
* **Profile Hot-Swapping:** Click **`📂 Profiles`** to instantly pull up custom `.txt` testing batches (e.g., *Gaming*, *Secure*, *Uncensored*) or save the top-performing servers from your last live run as a brand new workspace.
* **ISP Analytics:** Click **`📊 History`** to pull up your local CSV database, cross-examine past benchmark sessions, filter by adapter (Wi-Fi vs Ethernet vs Cellular), and discover your true average response time over time.

<br>

## 🌟 Architecture & Core Modules

Built inside a highly optimized, single-file structure (`main.py`) using **CustomTkinter** for a native Material Design 3 Dark aesthetic:

* `NetworkUtils`: The resolution engine. Handles the `concurrent.futures` thread pool, raw `socket` TCP handshakes, and native `dns.resolver` domain probes.
* `ConfigManager`: The workspace parser. Manages zero-friction I/O operations for local text profiles and handles multi-file dataset merges on the fly.
* `ScrollableTable`: A custom-bound Canvas view engineered to keep the UI entirely freeze-free even when rendering hundreds of live, rapidly updating data rows.

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

3. **Launch Suite:**
```cmd
   python main.py
```

### PyInstaller Compilation (.exe)

To pack the source script into a standalone executable for Windows distribution, open your terminal in the project root and run:

```cmd
pyinstaller --noconsole --onefile --name "BlueFalcon_DNS_Benchmark_Pro_v1.0" "main.py"
```
*(Note: If you assign an application icon to the project later, append `--icon="icon.ico"` to the command).*

<br>

## ✅ Supported Systems

* **Windows 11:** Fully Supported (x64 / ARM64 via native OS emulation)
* **Windows 10:** Fully Supported (Requires native PowerShell 5.1+ for local Gateway auto-detection)