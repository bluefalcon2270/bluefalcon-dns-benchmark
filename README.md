# BlueFalcon DNS Benchmark Pro

![Version](https://img.shields.io/badge/version-v1.0-A8C7FA.svg)
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0742A0.svg)
![License](https://img.shields.io/badge/license-MIT-81C995.svg)

A high-performance, multi-threaded Windows desktop utility engineered for accurate DNS latency benchmarking, custom profile workspaces, and deep ISP network analytics. 

Built with **CustomTkinter** for a native Material Design 3 Dark aesthetic.

---

## ⚡ Quick Start (Ready-to-Run)

> **No Python required!** If you just want to use the software without dealing with code, download the pre-compiled standalone executable:
>
> 1. Navigate to the **[Releases Page](../../releases)** *(Link active upon first GitHub Release)*.
> 2. Download the latest `BlueFalcon_DNS_Benchmark_Pro_v1.0.exe`.
> 3. Double-click and run directly on any Windows 10/11 machine.

---

## 🛠️ Windows Source Deployment

To run, inspect, or modify the raw Python source code on your local Windows environment, open **Command Prompt (`cmd.exe`)** or **PowerShell** and follow these steps:

### 1. Clone the Repository
```cmd
git clone [https://github.com/bluefalcon2270/bluefalcon-dns-benchmark.git](https://github.com/bluefalcon2270/bluefalcon-dns-benchmark.git)
cd bluefalcon-dns-benchmark
```

### 2. Create a Virtual Environment (Recommended)
Isolate the project dependencies from your global Python setup:
```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install Required Dependencies
Create a `requirements.txt` file in your root folder containing:
```text
customtkinter>=5.2.0
dnspython>=2.4.0
pandas>=2.1.0
```
Then run the package installer:
```cmd
pip install -r requirements.txt
```

### 4. Launch the Application
```cmd
python main.py
```

---

## 📁 Repository Workspace Hierarchy

```text
bluefalcon-dns-benchmark/
│
├── main.py                   # Main GUI and multi-threaded resolution engine
├── requirements.txt          # Explicit Windows package dependencies
├── README.md                 # Primary documentation
├── config_default.txt        # Auto-generated default testing profile
└── benchmark_history.csv     # Local database for ISP historical aggregations
```

---

## 🚀 Core Functionality

* **Asynchronous Thread Pooling:** Fire up to 1,000 concurrent socket workers to test massive lists of DNS servers against multiple web targets simultaneously.
* **Native Windows Gateway Detection:** Utilizes background Windows PowerShell calls to automatically pull and benchmark your router's active local gateway DNS.
* **Smart Grading Matrix:** Ranks servers in real-time based on zero-packet-loss stability and lowest average response times (ms).
* **ISP History Aggregator:** Automatically logs all completed benchmarks to a local CSV, allowing you to filter and average out historical performance across different Wi-Fi/LTE networks over time.
* **Profile Workspaces:** Create, edit, and instantly hot-swap custom `.txt` configuration profiles tailored for specific use cases (e.g., Gaming, Secure Browsing, Geo-unblocking).

---

## 🪪 Brand & Licensing

Engineered exclusively under the **BlueFalcon** desktop software label.

* **GitHub:** [@bluefalcon2270](https://github.com/bluefalcon2270)
* **Direct Contact:** `Bluefalcon2270@gmail.com`