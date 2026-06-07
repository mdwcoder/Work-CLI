[Español](README.es.md) | [English](README.en.md)

---

# ⚡ Work-CLI
> **The Ultimate Terminal Time Tracker**
> *Privacy-First, Multi-User, AI-Powered, and Cross-Platform.*

![Work-CLI Banner](https://img.shields.io/badge/Work--CLI-Fast_%26_Secure-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8%2B-yellow?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🚀 Overview
**Work-CLI** is a professional time-tracking tool designed for developers who love the terminal. It combines robust time management with advanced features like AI analysis, automated backups, and military-grade encryption.

### ✨ Key Features
*   **⏱️ Time Tracking**: Start/Stop/Pause with descriptions.
*   **📊 Reporting**: CSV/PDF exports and Email integration.
*   **🤖 AI Insights**: Ask Gemini about your productivity trends.
*   **👤 Multi-User**: Secure, isolated accounts with hashed passwords.
*   **🔐 Privacy**: AES-256 encryption for your sensitive data.
*   **💾 Auto-Backup**: Set it and forget it.

---

## 📥 Installation

### 🐧 Linux / 🍎 MacOS
```bash
# Clone & Install
git clone https://github.com/mdwcoder/Work-CLI.git
cd Work-CLI/
chmod +x init.sh
./init.sh
```
*Follow the interactive wizard to set your language, shell, and admin user.*

### 🪟 Windows (PowerShell)
```powershell
# Run the installer script
.\install.ps1
```

---

## ⚡ Quick Start

### 1. Start Working
```bash
work ON "Refactoring Login System"
# Returns: 🚀 Timer Started at 09:00:00 [Encrypted]
```

### 2. Check Status
```bash
work TIME
# Returns: ⏱️ Current Session: 01:23:45
```

### 3. Finish Work
```bash
work OFF
# Returns: 🛑 Stopped. Duration: 04:30:00
```

---

## 🔧 Core Commands

### 📅 Time Management
| Command | Action |
| :--- | :--- |
| `work ON [Desc]` | Start timer (Description optional) |
| `work OFF` | Stop current timer |
| `work TIME-TODAY` | Show total time today 📅 |
| `work TIME-SELECT [Date]` | Show time for specific date |
| `work TIME-RANGE [D1] [D2]` | Show total time in range |
| `work INIT-TIME` | Show what time you started today 🌅 |

### 📊 Reporting & Exports
| Command | Action |
| :--- | :--- |
| `work EXPORT-CSV [D1] [D2]` | Export data to CSV |
| `work EXPORT-PDF [D1] [D2]` | Export data to PDF report |
| `work SEND-TO` | **Wait-free**: Generate & Email Report 📧 |
| `work SEND-BACKUP-TO` | Email report from an old Backup 📦 |

---

## 🛡️ Advanced Security & Privacy

### 👤 User Management
Securely share your machine without sharing your logs.
*   **Register**: `work REGISTER`
*   **Login**: `work LOGIN`
*   **Logout**: `work USER-LOG-OUT`
*   **Delete**: `work USER-DELETE` (Permanent!)

### 🔐 Encryption (AES-256)
Protect your session descriptions.
*   **Enable**: `work ENCRIPT-ON`
*   **Migration**: `work CHANGE-KEY` (Rotates keys securely)

### 📜 Audit Logs
All sensitive actions (Logins, Deletions, Backups) are recorded in `logs/log.txt`.

---

## ⚡ Fast Mode
Toggle "Fast Mode" to disable rich UI elements (panels, colors) for a cleaner, plain-text experience.

*   **Enable**: `work FAST-MODE`
*   **Disable**: `work NORMAL-MODE`

---

## 🤖 AI Integration (Gemini)

Unlock insights about your work patterns.

1.  **Configure**: `work AI-CONFIG` (Enter API Key)
2.  **Ask**:
    ```bash
    work AI-GEN-ASK "How was my productivity last week?"
    ```
3.  **Contextual**:
    ```bash
    work AI-SEL-ASK-RANGE-TIME 01/01/2024 31/01/2024 "Summarize my main tasks"
    ```

---

## 💾 Backup & Data
Your data is yours. Local SQLite database.

*   **Location**: `data/working_code.db`
*   **Manual Backup**: `work BACKUP`
*   **Auto-Backup**: Configurable (`work CONF-BACKUP-AUTO`)
    *   `DAILY`, `MONTHLY`, `CUSTOM N`
*   **Restore**: `work LOAD-BACKUP`

---

## 🛠️ Technical Specs
*   **Language**: Python 3.8+
*   **Database**: SQLite3
*   **Dependencies**: `typer`, `rich`, `cryptography`, `xhtml2pdf`

---

*Built with ❤️ for efficiency.*
