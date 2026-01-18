# Work-CLI: Visual Time Tracker 🚀

A beautiful, robust, and highly optimized time tracking tool for the terminal. Works on Linux, macOS, and Windows.

![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge)

## Features

*   **⚡ Optimized Performance**: Zero resource usage when idle.
*   **🛡️ Robust & Safe**: Automatic error handling, database locking protection, and permission checks.
*   **🎨 Beautiful UI**: Powered by `rich` for a modern experience.
*   **🐳 Docker Ready**: Run it anywhere without installing Python locally.
*   **💾 Auto-Backups**: Your data is backed up automatically.

---

## 🚀 Installation

Choose your preferred method:

### 🐧 Linux / 🍎 macOS (Recommended)

The interactive installer will detect your shell (Bash/Zsh/Fish), create a virtual environment, and set up the alias.

```bash
./init.sh
```
*Supports: Arch, Manjaro, Debian, Ubuntu, Fedora, macOS*

### 🪟 Windows

1.  **PowerShell (Recommended)**:
    Run the installer to set up the environment and add the `work` alias permanently:
    ```powershell
    .\install.ps1
    ```

2.  **Command Prompt (CMD)**:
    You can also run the tool directly using the batch runner:
    ```cmd
    scripts\working_runner.bat ON
    ```

### 🐳 Docker (Portable)

No Python installed? No problem.

**Using Docker Compose (Recommended):**
```bash
docker compose run --rm work-cli
```

**Using pure Docker:**
```bash
docker build -t work-cli .
docker run --rm -v $(pwd)/data:/app/data work-cli
```

---

## 🛠️ Usage

Once installed, just use the `work` command.

| Command | Action | Example |
| :--- | :--- | :--- |
| `work ON [desc]` | Start timer 🚀 (Optional description) | `work ON "Bug Fix"` |
| `work OFF` | Stop timer 🛑 | `work OFF` |
| `work TIME` | Current duration ⏱️ | `work TIME` |
| `work TIME-TODAY` | Total today 📅 | `work TIME-TODAY` |
| `work TIME-SELECT [date]` | Specific date 🗓️ | `work TIME-SELECT 15/01/2026` |
| `work TIME-RANGE [d1] [d2]` | Date range 📊 | `work TIME-RANGE 01/01/ 31/01/` |
| `work BACKUP` | Manual backup 💾 | `work BACKUP` |
| `work CLEAR-ALL` | Wipe data 🗑️ | `work CLEAR-ALL` |


### 6. 🌍 Multi-language Support
The tool supports **English (EN), Spanish (ES), French (FR), and Portuguese (PT)**.

```bash
work LANG      # Check current language
work LANG-SET  # Change language (Interactive)
```

### 7. 🤖 AI Integration (New!)
Analyze your work habits using **Google Gemini** or **OpenAI ChatGPT**.

#### Configuration
First, set your provider and API Key:
```bash
work AI-CONFIG
```
*   **Google Gemini**: Highly recommended. You can get a **free API Key** at [Google AI Studio](https://aistudio.google.com/app/apikey).
*   **OpenAI**: Requires a paid API key.

#### Usage
Ask questions about your work history:
```bash
# Ask about full history
work AI-GEN-ASK "What is my average daily work time?"

# Ask about a specific date range
work AI-SEL-ASK-RANGE-TIME 01/01/2026 31/01/2026 "Summarize my work in January"
```

### 8. 📊 Export Data (New!)
Export your work history to share or analyze externally.

```bash
# Export to CSV (Spreadsheet friendly)
work EXPORT-CSV 01/01/2026 31/01/2026

# Export to PDF (Beautiful Report)
work EXPORT-PDF 01/01/2026 31/01/2026
```

### 9. 💾 Backup Management (Advanced)
By default, the system creates backups automatically (Frequency: MONTHLY).

```bash
# Configure Auto-Backup Frequency
work CONFIG-BACKUP-AUTO DAILY      # Every day
work CONFIG-BACKUP-AUTO MONTHLY    # Every month (Default)
work CONFIG-BACKUP-AUTO CUSTOM 3   # Every 3 months
work CONFIG-BACKUP-AUTO NEVER      # Disable auto-backup

# Restore from a backup file (WARNING: Overwrites current data)
# Files are located in the 'backup/' directory
work LOAD-BACKUP backup_20260101_120000.db
```

## ⚙️ Technical Details

*   **Logic**: `src/Working_Code.py` | Core logic with global error wrapping.
*   **Data**: `data/working_code.db` | SQLite database.
*   **Backups**: `backup/` | Automatic backups on change.
*   **Runner**: `scripts/working_runner.sh` | Venv manager.

**Requirements:**
*   Python 3.8+ (if running locally)
*   OR Docker

---
*Created with ❤️ for efficiency.*

