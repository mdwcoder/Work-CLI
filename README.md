# Work Time Tracker 🚀

A beautiful, terminal-based time, highly optimized, and robust time tracking tool for Linux.

![Banner](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge)

## Features

*   **⚡ Optimized Performance**: Zero resource usage when idle to minimal resource usage when running.
*   **🎨 Beautiful UI**: Powered by `rich` for a modern terminal experience.
*   **🛡️ Robust Design**: SQLite database with transaction safety and automatic backups.
*   **🔌 Auto-Installation**: Includes a smart `init.sh` to configure your shell automatically.

## Quick Start

1.  **Install/Setup**:
    ```bash
    ./init.sh
    ```
    This script will:
    *   Detect your shell (Bash, Zsh, Fish, etc.).
    *   Create a virtual environment automatically.
    *   Add the `work` alias to your config file.

2.  **Reload Shell**:
    ```bash
    source ~/.bashrc  # Or ~/.zshrc, ~/.config/fish/config.fish
    ```

3.  **Use it**:
    ```bash
    work
    ```

## Command Reference

The tool uses the alias `work`. Here is the full command list:

| Command | Action | Usage Example |
| :--- | :--- | :--- |
| **ON** | Start the timer 🚀 | `work ON` |
| **OFF** | Stop the timer 🛑 | `work OFF` |
| **TIME** | Show current session duration ⏱️ | `work TIME` |
| **TIME-TODAY** | Show total time worked today 📅 | `work TIME-TODAY` |
| **BACKUP** | Create a timestamped backup of the DB 💾 | `work BACKUP` |
| **DB** | Show database path 📂 | `work DB` |
| **TIME-SELECT** | Time for a specific date 🗓️ | `work TIME-SELECT 15/01/2026` |
| **TIME-RANGE** | Time for a date range 📊 | `work TIME-RANGE 01/01/2026 31/01/2026` |
| **INIT-TIME** | Time of first login today 🌅 | `work INIT-TIME` |
| **INIT-TIME_WHEN**| Time of first login on specific date | `work INIT-TIME_WHEN 01/01/2026` |
| **CLEAR-ALL** | Wipe all data (Requires confirmation) 🗑️ | `work CLEAR-ALL` |

Run `work` without arguments to see the interactive help table.

## Technical Details

*   **Logic**: `Working_Code.py` handles all logic and database interactions.
*   **Runner**: `working_runner.sh` manages the Python virtual environment (`venv`) transparently.
*   **Database**: Data is stored in `working_code.db` (SQLite).
*   **Backups**: Created as `working_code.db_YYYY-MM-DD_HH-MM`.

## Requirements

*   Python 3+ (Automatically handled)
*   Linux (Manjaro optimized)
