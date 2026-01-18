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

Run the PowerShell installer to set up the environment and alias:

```powershell
.\install.ps1
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
| `work ON` | Start timer 🚀 | `work ON` |
| `work OFF` | Stop timer 🛑 | `work OFF` |
| `work TIME` | Current duration ⏱️ | `work TIME` |
| `work TIME-TODAY` | Total today 📅 | `work TIME-TODAY` |
| `work TIME-SELECT [date]` | Specific date 🗓️ | `work TIME-SELECT 15/01/2026` |
| `work TIME-RANGE [d1] [d2]` | Date range 📊 | `work TIME-RANGE 01/01/ 31/01/` |
| `work BACKUP` | Manual backup 💾 | `work BACKUP` |
| `work CLEAR-ALL` | Wipe data 🗑️ | `work CLEAR-ALL` |

Run `work` without arguments to see the help menu.

---

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

