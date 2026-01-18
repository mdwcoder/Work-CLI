import typer
import sqlite3
import shutil
import os
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import platform
import sys
from datetime import datetime, timedelta
import typer
import sqlite3
import shutil
import os
import locale
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.align import Align
from rich.traceback import install
from pathlib import Path
from typing import Optional
from translations import get_text, TRANSLATIONS

# Install rich traceback handler for prettier unhandled exceptions
install(show_locals=False)

# Configuration
DB_NAME = "working_code.db"
SCRIPT_DIR = Path(__file__).parent.absolute()
# Go up one level from src/ to root, then into data/
DB_PATH = SCRIPT_DIR.parent / "data" / DB_NAME
BACKUP_DIR = SCRIPT_DIR.parent / "backup"

# Platform specific robustness
SYSTEM_PLATFORM = platform.system()

# UI Theme
BORDER_STYLE = "bright_blue"
TITLE_STYLE = "bold white on bright_blue"
SUCCESS_STYLE = "bold green"
WARNING_STYLE = "bold yellow"
ERROR_STYLE = "bold red"

app = typer.Typer(help="Visual Time Tracker for Terminal", add_completion=False)
console = Console()

# --- UI Helper ---
class UI:
    @staticmethod
    def is_fast_mode():
        return get_config("ui_mode") == "fast"

    @staticmethod
    def print(content, title=None, style=None, border_style="blue", box_type=box.ROUNDED):
        if UI.is_fast_mode():
            # Fast Mode: Plain text
            if title:
                print(f"--- {title.upper()} ---")
            
            if isinstance(content, Text):
                print(content.plain)
            elif isinstance(content, str):
                # Strip basic coloring if rudimentary
                print(content) 
            else:
                print(content)
        else:
            # Normal Mode: Rich Panel
            if isinstance(content, str):
                msg = Align.center(content, vertical="middle")
            elif isinstance(content, Text):
                msg = Align.center(content, vertical="middle")
            else:
                msg = content # Assume renderable like Table
                
            console.print(Panel(msg, title=title, border_style=border_style, box=box_type, padding=(1, 2) if title else (0,0)))

    @staticmethod
    def table(columns, rows):
        if UI.is_fast_mode():
            # Fast Table
            print("\n" + "\t".join([c for c, _ in columns]))
            for row in rows:
                print("\t".join([str(r) for r in row]))
            print("")
        else:
            t = Table(box=box.SIMPLE)
            for col, style in columns:
                t.add_column(col, style=style)
            for row in rows:
                t.add_row(*[str(r) for r in row])
            console.print(t)

# --- Config & Helpers ---

def get_language() -> str:
    """Determine language: DB -> System -> Default (EN)."""
    # 1. Check DB
    try:
        if DB_PATH.exists():
            lang = get_config("language")
            if lang and lang in TRANSLATIONS:
                return lang
    except Exception:
        pass # Fallback if DB invalid or error

    # 2. Check System
    try:
        sys_lang, _ = locale.getdefaultlocale()
        if sys_lang:
             prefix = sys_lang.split("_")[0].upper()
             # Map common codes
             if prefix in ["ES", "EN", "FR", "PT"]:
                 return prefix
             if prefix == "BR": return "PT" # Portuguese Brazil
    except Exception:
        pass
        
    # 3. Default
    return "EN"

def T(key: str) -> str:
    """Short helper to translate text based on current context."""
    return get_text(key, get_language())

def check_db_permissions():
    """Ensure we have write permissions to the database directory."""
    if not DB_PATH.parent.exists():
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
             console.print(f"[{ERROR_STYLE}]{T('error_critical_dir')}:[/{ERROR_STYLE}] {DB_PATH.parent}")
             console.print(T('check_permissions'))
             sys.exit(1)
             
    if DB_PATH.exists() and not os.access(DB_PATH, os.W_OK):
        console.print(f"[{ERROR_STYLE}]{T('error_critical_write')}:[/{ERROR_STYLE}] {DB_PATH}")
        console.print(T('check_permissions'))
        sys.exit(1)

def get_db_connection():
    check_db_permissions()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10) # 10s timeout to handle potential locks
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError as e:
        console.print(f"[{ERROR_STYLE}]{T('database_error')}:[/{ERROR_STYLE}] {e}")
        console.print(f"[{WARNING_STYLE}]{T('database_locked_hint')}[/{WARNING_STYLE}]")
        raise typer.Exit(code=1)



def get_config(key: str) -> Optional[str]:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT value FROM config WHERE key=?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else None
    except Exception:
        return None
    finally:
        conn.close()

import hashlib
import secrets

# Logging Config
LOGS_DIR = SCRIPT_DIR.parent / "logs"
LOG_FILE = LOGS_DIR / "log.txt"

def log_audit(action: str, details: str = ""):
    """Append to audit log."""
    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
    user = get_current_user_name() or "SYSTEM/GUEST"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{user}] [{action}] {details}\n"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

def set_config(key: str, value: str):
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def init_db():
    conn = get_db_connection()
    
    # Users Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Events Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT,
            user_id INTEGER
        )
    ''')
    
    # Migrations
    try:
        conn.execute("ALTER TABLE events ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass 
        
    try:
        conn.execute("ALTER TABLE events ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass

    # Config Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    
# --- Auth Helpers ---

def hash_password(password: str) -> (str, str):
    """Return (hash, salt)."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()
    return pw_hash, salt

def verify_password(stored_password, stored_salt, provided_password) -> bool:
    """Verify password against storage."""
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        provided_password.encode('utf-8'), 
        stored_salt.encode('utf-8'), 
        100000
    ).hex()
    return pw_hash == stored_password

def get_current_user_id() -> Optional[int]:
    """Get logged in user ID from config."""
    uid = get_config("current_user_id")
    if uid and uid.isdigit():
        return int(uid)
    return None

def get_current_user_name() -> Optional[str]:
    """Get username for logging/display."""
    uid = get_current_user_id()
    if not uid:
        return None
        
    conn = get_db_connection()
    row = conn.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return row['username'] if row else None


def ensure_logged_in():
    """Check login status, exit if failed."""
    if not get_current_user_id():
        console.print(f"[red]{T('auth_login_required')}[/red]")
        raise typer.Exit(code=1)

@app.command(name="FAST-MODE")
def fast_mode():
    """Enable optimized mode (No colors/panels)."""
    init_db()
    set_config("ui_mode", "fast")
    print("Optimization enabled. FAST-MODE active.")

@app.command(name="NORMAL-MODE")
def normal_mode():
    """Disable optimized mode (Restore colors/panels)."""
    init_db()
    set_config("ui_mode", "normal")
    console.print(Panel(Align.center("[bold green]Normal UI restored.[/bold green]", vertical="middle"), 
                      title="Success", border_style="green", box=box.ROUNDED))

@app.command(name="USER-LOG-OUT")
def user_log_out():
    """Logout session (Alias)."""
    logout_user()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    ⚡ Work-CLI: Time Tracking, Reporting & Privacy.
    """
    # Whitelist
    whitelist = ["REGISTER", "LOGIN", "LANG-SET", "LANG", "DB", "AI-CONFIG", "FAST-MODE", "NORMAL-MODE"]
    
    if ctx.invoked_subcommand and ctx.invoked_subcommand.upper() not in whitelist:
         if not get_current_user_id():
             console.print(f"[bold red]🚫 {T('auth_login_required')}[/bold red]")
             raise typer.Exit(code=1)

    if ctx.invoked_subcommand is None:
        print_banner(T('app_subtitle'))
        
        # Build Command List
        columns = [("Command", "cyan"), ("Description", "white"), ("Example", "dim")]
        rows = [
            ("ON [Desc]", T("desc_start"), "work ON 'Project A'"),
            ("OFF", T("desc_stop"), "work OFF"),
            ("TIME", T("desc_time"), "work TIME"),
            ("TIME-TODAY", T("desc_today"), "work TIME-TODAY"),
            ("TIME-SELECT", T("desc_select"), "work TIME-SELECT 01/01/2024"),
            ("TIME-RANGE", T("desc_range"), "work TIME-RANGE 01/01/2024 31/01/2024"),
            ("INIT-TIME", T("desc_init"), "work INIT-TIME"),
            ("INIT-TIME_WHEN", T("desc_init_when"), "work INIT-TIME_WHEN 01/01/2024"),
            ("AI-GEN-ASK", T("desc_ai_ask"), "work AI-GEN-ASK \"Trend?\""),
            ("AI-SEL-ASK-RANGE-TIME", T("desc_ai_range_ask"), "work AI-SEL-ASK-RANGE-TIME d1 d2"),
            ("EXPORT-CSV", T("desc_export_csv"), "work EXPORT-CSV d1 d2"),
            ("EXPORT-PDF", T("desc_export_pdf"), "work EXPORT-PDF d1 d2"),
            ("SEND-TO", T("desc_send_to"), "work SEND-TO"),
            ("SEND-BACKUP-TO", T("desc_send_backup_to"), "work SEND-BACKUP-TO"),
            ("INIT-ENCRYPTION", T("desc_init_encryption"), "work INIT-ENCRYPTION"),
            ("GET-KEY", T("desc_get_key"), "work GET-KEY"),
            ("CHANGE-KEY", T("desc_change_key"), "work CHANGE-KEY"),
            ("ENCRIPT-ON", T("desc_encrypt_on"), "work ENCRIPT-ON"),
            ("ENCRIPT-OFF", T("desc_encrypt_off"), "work ENCRIPT-OFF"),
            ("LOGOUT", T("desc_logout"), "work LOGOUT"),
            ("USER-DELETE", T("desc_user_delete"), "work USER-DELETE"),
            ("REGISTER", T("desc_register"), "work REGISTER"),
            ("LOGIN", T("desc_login"), "work LOGIN"),
            ("BACKUP", T("desc_backup"), "work BACKUP"),
            ("CONF-BACKUP-AUTO", T("desc_conf_backup"), "work CONF-BACKUP-AUTO"),
            ("LOAD-BACKUP", T("desc_load_backup"), "work LOAD-BACKUP"),
            ("FAST-MODE", "Enable Fast Mode", "work FAST-MODE"),
            ("NORMAL-MODE", "Enable Normal Mode", "work NORMAL-MODE"),
            ("AI-CONFIG", T("desc_ai_config"), "work AI-CONFIG"),
            ("LANG-SET", T("desc_lang_set"), "work LANG-SET"),
            ("DB", T("desc_db"), "work DB"),
            ("CLEAR-ALL", T("desc_clear"), "work CLEAR-ALL"),
        ]
            
        UI.table(columns, rows)
        
        # User Status
        user = get_current_user_name()
        if user:
            UI.print(f"Logged in as: {user}", style="green")
        else:
            UI.print("Not logged in.", style="yellow")

@app.command(name="EXPORT-CSV")
def export_csv(start_date_str: str, end_date_str: str):
    """Export work history to CSV."""
    init_db()
    ensure_logged_in()
    try:
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        s_iso = start_date.strftime("%Y-%m-%dT00:00:00")
        e_iso = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        uid = get_current_user_id()
        
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT timestamp, event_type, description FROM events WHERE timestamp >= ? AND timestamp < ? AND user_id=? ORDER BY timestamp ASC",
            (s_iso, e_iso, uid)
        )
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        sessions = process_sessions(events)
        path = generate_csv_file(sessions, start_date_str, end_date_str)
        console.print(Panel(f"{T('export_csv_success')}:\n[blue]{path}[/blue] 📊", border_style="green"))

    except Exception as e:
        console.print(Panel(f"[bold red]Error: {e}[/bold red]", border_style="red"))

@app.command(name="EXPORT-PDF")
def export_pdf(start_date_str: str, end_date_str: str):
    """Export work history to PDF."""
    init_db()
    ensure_logged_in()
    try:
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        s_iso = start_date.strftime("%Y-%m-%dT00:00:00")
        e_iso = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        uid = get_current_user_id()
        
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT timestamp, event_type, description FROM events WHERE timestamp >= ? AND timestamp < ? AND user_id=? ORDER BY timestamp ASC",
            (s_iso, e_iso, uid)
        )
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        sessions = process_sessions(events)
        path = generate_pdf_file(sessions, start_date_str, end_date_str)
        console.print(Panel(f"{T('export_pdf_success')}:\n[blue]{path}[/blue] 📊", border_style="green"))

    except Exception as e:
        console.print(Panel(f"[bold red]Error: {e}[/bold red]", border_style="red"))

@app.command(name="REGISTER")
def register_user():
    """Create a new user."""
    init_db()
    console.print(Panel(f"[bold]{T('desc_register')}[/bold]", border_style="blue"))
    
    username = typer.prompt("Username")
    password = typer.prompt("Password", hide_input=True)
    confirm = typer.prompt("Confirm Password", hide_input=True)
    
    if password != confirm:
        console.print("[red]Passwords do not match.[/red]")
        raise typer.Exit(1)
        
    pw_hash, salt = hash_password(password)
    
    conn = get_db_connection()
    try:
        # Check if first user
        count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
        is_first = (count == 0)
        
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (username, pw_hash, salt, datetime.now().isoformat())
        )
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        # Claim orphans if first user
        if is_first:
            conn.execute("UPDATE events SET user_id = ? WHERE user_id IS NULL", (user_id,))
            console.print("[yellow]First user: Claimed all existing events.[/yellow]")
            
        conn.commit()
        console.print(f"[green]{T('auth_register_success')}[/green]")
        log_audit("REGISTER", f"New user: {username}")
        
        # Auto-login
        set_config("current_user_id", str(user_id))
        
    except sqlite3.IntegrityError:
        console.print("[red]Username already exists.[/red]")
    finally:
        conn.close()

@app.command(name="LOGIN")
def login_user():
    """Login to application."""
    init_db()
    username = typer.prompt("Username")
    password = typer.prompt("Password", hide_input=True)
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    
    if user and verify_password(user['password_hash'], user['salt'], password):
        set_config("current_user_id", str(user['id']))
        console.print(f"[green]{T('auth_login_success')} {username}[/green]")
        log_audit("LOGIN", "Success")
    else:
        console.print(f"[red]{T('auth_failed')}[/red]")
        log_audit("LOGIN", f"Failed attempt for {username}")
        
@app.command(name="LOGOUT")
def logout_user():
    """Logout session."""
    init_db()
    log_audit("LOGOUT")
    set_config("current_user_id", "")
    console.print(f"[yellow]{T('auth_logout')}[/yellow]")

@app.command(name="USER-DELETE")
def delete_user_account():
    """Delete current user."""
    init_db()
    uid = get_current_user_id()
    if not uid:
        console.print(f"[red]{T('auth_login_required')}[/red]")
        return
        
    console.print(f"[bold red]{T('auth_user_delete_confirm')}[/bold red]")
    password = typer.prompt("Password", hide_input=True, prompt_suffix=": ")
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    
    if user and verify_password(user['password_hash'], user['salt'], password):
        # Delete data first
        conn.execute("DELETE FROM events WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
        conn.close()
        
        set_config("current_user_id", "")
        log_audit("USER-DELETE", f"Deleted user {user['username']}")
        console.print("[red]Account and data deleted.[/red]")
    else:
        conn.close()
        console.print("[red]Invalid password.[/red]")
    conn.commit()
    conn.close()

# --- Core Logic ---

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        console.print(f"[{ERROR_STYLE}]{T('invalid_date_format')}[/{ERROR_STYLE}]")
        raise typer.Exit(code=1)


def get_active_session_start(conn) -> Optional[datetime]:
    """Returns the start time of the current session for current user."""
    uid = get_current_user_id()
    if not uid: return None
    
    cursor = conn.execute("SELECT timestamp, event_type FROM events WHERE user_id=? ORDER BY timestamp DESC LIMIT 1", (uid,))
    row = cursor.fetchone()
    if row and row['event_type'] == 'START':
        return datetime.fromisoformat(row['timestamp'])
    return None

def calculate_duration(start_time: datetime, end_time: datetime) -> timedelta:
    return end_time - start_time

def format_duration(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def print_banner(subtitle: str = ""):
    """Prints a styled banner."""
    if UI.is_fast_mode():
        print("\n=== WORK-CLI ===")
        if subtitle: print(f"--- {subtitle} ---")
        user = get_current_user_name()
        if user: print(f"User: {user}")
        print()
    else:
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_row(Text("⚡ WORK-CLI ⚡", style="bold magenta", justify="center"))
        
        # Show User info in banner
        user = get_current_user_name()
        if user:
             grid.add_row(Text(f"User: {user}", style="dim green", justify="center"))
             
        if subtitle:
            grid.add_row(Text(subtitle, style="cyan", justify="center"))
        
        console.print(Panel(grid, style=BORDER_STYLE, border_style=BORDER_STYLE, box=box.HEAVY))

# --- Commands ---

@app.command(name="ON")
def start_timer(description: str = typer.Argument(None)):
    """Start the timer. Optional: Add a description."""
    init_db()
    ensure_logged_in()
    
    conn = get_db_connection()
    if get_active_session_start(conn):
        UI.print(f"[bold yellow]{T('timer_already_running')}[/bold yellow]", title="Info", border_style="yellow")
        conn.close()
        return

    now = datetime.now()
    desc_enc = encrypt_text(description) if description else None
    
    # User ID check
    uid = get_current_user_id()
    
    conn.execute("INSERT INTO events (timestamp, event_type, description, user_id) VALUES (?, ?, ?, ?)", 
                 (now.isoformat(), 'START', desc_enc, uid))
    conn.commit()
    conn.close()
    
    log_audit("CMD_ON", f"Started. Desc: {description or 'None'}")
    
    UI.print(f"[bold green]{T('timer_started')}[/bold green]\nTime: [cyan]{now.strftime('%H:%M:%S')}[/cyan] 🚀", 
             title="Success", border_style="green", box_type=box.HEAVY)
    
    if not description:
         console.print(Align.center(f"[dim yellow]{T('tip_use_description')}[/dim yellow]"))
    else:
         console.print(Align.center(f"[dim]Note: {description}[/dim]"))

@app.command(name="OFF")
def stop_timer():
    """Stop the timer."""
    init_db()
    ensure_logged_in()
    
    conn = get_db_connection()
    start_time = get_active_session_start(conn)
    if not start_time:
        UI.print(f"[bold yellow]{T('timer_not_running')}[/bold yellow]", title="Info", border_style="yellow")
        conn.close()
        return

    now = datetime.now()
    duration = calculate_duration(start_time, now)
    uid = get_current_user_id()
    
    conn.execute("INSERT INTO events (timestamp, event_type, user_id) VALUES (?, ?, ?)", 
                 (now.isoformat(), 'STOP', uid))
    conn.commit()
    conn.close()
    
    log_audit("CMD_OFF", f"Stopped. Duration: {format_duration(duration)}")
    
    text = Text()
    text.append(f"{T('timer_stopped')}\n", style="bold red")
    text.append(f"{T('stopped_at')}: {now.strftime('%H:%M:%S')}\n", style="dim white")
    text.append(f"{T('duration')}:   {format_duration(duration)}", style="bold white")
    
    UI.print(text, title="Stopped", border_style="red", box_type=box.HEAVY)

@app.command(name="TIME")
def current_time():
    """Show current session time."""
    init_db()
    ensure_logged_in()
    conn = get_db_connection()
    start_time = get_active_session_start(conn)
    conn.close()

    if start_time:
        duration = calculate_duration(start_time, datetime.now())
        UI.print(f"{T('current_session')}:\n[bold cyan]{format_duration(duration)}[/bold cyan] ⏱️", 
                 title=T('active_timer'), border_style="cyan")
    else:
        UI.print(f"[dim]{T('timer_inactive')}[/dim]", title="Status", border_style="dim")

def calculate_daily_total(target_date: datetime) -> timedelta:
    conn = get_db_connection()
    uid = get_current_user_id()
    date_str = target_date.strftime("%Y-%m-%d")
    cursor = conn.execute(
        "SELECT timestamp, event_type FROM events WHERE timestamp LIKE ? AND user_id=? ORDER BY timestamp ASC", 
        (f"{date_str}%", uid)
    )
    events = cursor.fetchall()
    conn.close()

    total_duration = timedelta()
    session_start = None

    for event in events:
        ts = datetime.fromisoformat(event['timestamp'])
        etype = event['event_type']

        if etype == 'START':
            if session_start is None:
                session_start = ts
        elif etype == 'STOP':
            if session_start:
                total_duration += (ts - session_start)
                session_start = None

    if session_start:
        if target_date.date() == datetime.now().date():
             total_duration += (datetime.now() - session_start)
    
    return total_duration

@app.command(name="TIME-TODAY")
def time_today():
    """Show total time worked today."""
    init_db()
    ensure_logged_in()
    now = datetime.now()
    total = calculate_daily_total(now)
    
    UI.print(f"{T('total_time_today')} ([cyan]{now.strftime('%d/%m/%Y')}[/cyan])\n[bold green]{format_duration(total)}[/bold green] 📅", 
             title=T('daily_summary'), border_style="green", box_type=box.DOUBLE)

@app.command(name="DB")
def show_db_path():
    """Show database path."""
    UI.print(f"[bold]{T('database_path')}:[/bold]\n[blue]{DB_PATH}[/blue] 📂", title="Configuration", border_style="blue")

@app.command(name="BACKUP")
def backup_db():
    """Backup the database."""
    # Login required for backup? Probably yes to prevent leaking other users data if naive backup.
    # Actually, backing up the whole DB backs up ALL users. This is an admin/local/owner action.
    # Allowing it without login is a risk if someone else uses your PC.
    # Enforce login.
    init_db()
    ensure_logged_in()
    
    if not DB_PATH.exists():
        UI.print(f"[bold red]{T('database_exist_error')}[/bold red]", border_style="red")
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_name = f"{DB_NAME}_{timestamp}"
    backup_folder = BACKUP_DIR / f"backup_{timestamp}"
    backup_folder.mkdir(parents=True, exist_ok=True)
    
    backup_path = backup_folder / DB_NAME
    
    shutil.copy(DB_PATH, backup_path)
    
    # Backup Logs
    if LOGS_DIR.exists():
        log_backup = backup_folder / "logs"
        shutil.copytree(LOGS_DIR, log_backup)
    
    log_audit("BACKUP", f"Created backup at {backup_folder}")
    
    UI.print(f"{T('backup_created')}: [bold green]{backup_name}[/bold green]\n{T('location')}: [blue]{backup_folder}[/blue] 💾", 
             title="Backup Success", border_style="green", box=box.ROUNDED)

@app.command(name="TIME-SELECT")
def time_select(date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show total time specific date."""
    init_db()
    ensure_logged_in()
    target_date = parse_date(date_str)
    total = calculate_daily_total(target_date)
    UI.print(f"{T('total_time_on')} [cyan]{date_str}[/cyan]\n[bold magenta]{format_duration(total)}[/bold magenta] 🗓️", 
             title=T('historical_data'), border_style="magenta", box=box.ROUNDED)

@app.command(name="TIME-RANGE")
def time_range(start_date_str: str = typer.Argument(..., metavar="dd/mm/yyyy"), end_date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show total time in date range."""
    init_db()
    ensure_logged_in()
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    total_duration = timedelta()
    current_date = start_date
    while current_date <= end_date:
        total_duration += calculate_daily_total(current_date)
        current_date += timedelta(days=1)
        
    UI.print(f"Range: [cyan]{start_date_str}[/cyan] - [cyan]{end_date_str}[/cyan]\n"
             f"{T('total_time')}: [bold orange1]{format_duration(total_duration)}[/bold orange1] 📊",
             title=T('range_summary'), border_style="orange1", box=box.ROUNDED)

@app.command(name="INIT-TIME")
def init_time():
    """Show first start time today."""
    init_db()
    ensure_logged_in()
    today_str = get_today_str()
    conn = get_db_connection()
    uid = get_current_user_id()
    cursor = conn.execute(
        "SELECT timestamp FROM events WHERE timestamp LIKE ? AND event_type='START' AND user_id=? ORDER BY timestamp ASC LIMIT 1",
        (f"{today_str}%", uid)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        first_time = datetime.fromisoformat(row['timestamp'])
        UI.print(f"{T('first_start_today')}:\n[bold cyan]{first_time.strftime('%H:%M:%S')}[/bold cyan] 🌅", 
                 title="Start Time", border_style="cyan", box_type=box.ROUNDED)
    else:
        UI.print(f"[dim]{T('no_sessions_today')}[/dim]", title="Start Time", border_style="dim")

@app.command(name="INIT-TIME_WHEN")
def init_time_when(date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show first start time on specific date."""
    init_db()
    ensure_logged_in()
    target_date = parse_date(date_str)
    date_iso_prefix = target_date.strftime("%Y-%m-%d")
    uid = get_current_user_id()
    
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT timestamp FROM events WHERE timestamp LIKE ? AND event_type='START' AND user_id=? ORDER BY timestamp ASC LIMIT 1",
        (f"{date_iso_prefix}%", uid)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        first_time = datetime.fromisoformat(row['timestamp'])
        UI.print(f"{T('first_start_on')} [cyan]{date_str}[/cyan]:\n[bold cyan]{first_time.strftime('%H:%M:%S')}[/bold cyan] 🗓️", title="Historical Start Time", border_style="cyan")
    else:
        UI.print(f"[dim]{T('no_sessions_found')} {date_str}.[/dim]", title="Historical Start Time", border_style="dim")


@app.command(name="CLEAR-ALL")
def clear_all():
    """Clear all database data for current user."""
    ensure_logged_in() # Mandatory
    if not DB_PATH.exists():
        console.print(Panel(f"[yellow]{T('database_empty')}[/yellow]", border_style="yellow"))
        return
        
    confirm = typer.confirm(T('clear_confirmation'))
    if not confirm:
        console.print(T('aborted'))
        raise typer.Abort()
        
    conn = get_db_connection()
    uid = get_current_user_id()
    conn.execute("DELETE FROM events WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    console.print(Panel(f"[bold red]{T('database_cleared')}[/bold red]", title="Warning", border_style="red", box=box.HEAVY))

@app.command(name="LANG")
def show_lang():
    """Show current language."""
    init_db()
    lang = get_language()
    UI.print(f"{T('language_current')}: [bold cyan]{lang}[/bold cyan] 🌍", 
             title="Configuration", border_style="blue")

@app.command(name="LANG-SET")
def set_lang_command(code: Optional[str] = typer.Argument(None)):
    """Set the application language."""
    init_db()
    current = get_language()
    
    if code:
        code = code.upper()
        if code in TRANSLATIONS:
            set_config("language", code)
            new_lang_text = TRANSLATIONS[code]["language_updated"]
            UI.print(f"[bold green]{new_lang_text} {code}![/bold green]", border_style="green")
            return
        else:
             console.print(f"[yellow]Invalid code '{code}'. Showing menu...[/yellow]")

    console.print(f"[bold]{T('language_select')}:[/bold]")
    for code_key in TRANSLATIONS.keys():
        marker = "(*)" if code_key == current else "   "
        console.print(f"{marker} {code_key}")
        
    choice = typer.prompt("Code").upper()
    if choice in TRANSLATIONS:
        set_config("language", choice)
        new_lang_text = TRANSLATIONS[choice]["language_updated"]
        UI.print(f"[bold green]{new_lang_text} {choice}![/bold green]", border_style="green")
    else:
        console.print(f"[red]Invalid code. Available: {', '.join(TRANSLATIONS.keys())}[/red]")


# --- AI Commands ---

@app.command(name="AI-CONFIG")
def ai_config():
    """Configure AI Provider and Key."""
    init_db()
    UI.print(f"[bold]{T('ai_config_menu')}[/bold]", border_style="blue")
    
    console.print(f"1. GEMINI (Google)")
    console.print(f"2. OPENAI (ChatGPT)")
    
    choice = typer.prompt(T('ai_provider_select'))
    provider = "GEMINI" if choice == "1" else "OPENAI" if choice == "2" else None
    
    if not provider:
        console.print("[red]Invalid choice.[/red]")
        return
        
    api_key = typer.prompt(T('ai_key_prompt'), hide_input=True)
    if api_key:
        set_config("ai_provider", provider)
        set_config("ai_api_key", api_key)
        UI.print(f"[bold green]AI Configured successfully![/bold green]", border_style="green")
        set_config("ai_api_key", api_key)
        console.print(Panel(f"[bold green]{T('ai_key_saved')} {provider}![/bold green]", border_style="green"))

@app.command(name="AI-GEN-ASK")
def ai_gen_ask(question: str):
    """Ask AI with full context."""
    init_db()
    
    # helper to get ai
    provider = get_config("ai_provider")
    api_key = get_config("ai_api_key")
    
    if not provider or not api_key:
        UI.print(f"[yellow]AI not configured. Run 'work AI-CONFIG' first.[/yellow]", border_style="yellow")
        return

    from ai_handler import AIHandler
    
    # Loading
    if UI.is_fast_mode():
        print(f"Analyzing {provider}...")
        try:
             handler = AIHandler(provider, api_key)
             conn = get_db_connection()
             cursor = conn.execute("SELECT timestamp, event_type FROM events ORDER BY timestamp ASC")
             events = [dict(row) for row in cursor.fetchall()]
             conn.close()
             context = handler.format_context(events)
             response = handler.ask_ai(question, context)
             UI.print(response, title=f"🤖 {provider} Response", border_style="magenta")
        except Exception as e:
            UI.print(f"[bold red]{T('ai_error')}: {e}[/bold red]", border_style="red")
    else:
        with console.status(f"[bold green]{T('ai_analyzing')} {provider}...[/bold green]"):
            try:
                handler = AIHandler(provider, api_key)
                
                # Get all events
                conn = get_db_connection()
                cursor = conn.execute("SELECT timestamp, event_type FROM events ORDER BY timestamp ASC")
                events = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                context = handler.format_context(events)
                response = handler.ask_ai(question, context)
                
                UI.print(response, title=f"🤖 {provider} Response", border_style="magenta", box_type=box.ROUNDED)
                
            except Exception as e:
                UI.print(f"[bold red]{T('ai_error')}: {e}[/bold red]", border_style="red")

@app.command(name="AI-SEL-ASK-RANGE-TIME")
def ai_range_ask(start_date_str: str, end_date_str: str, question: str):
    """Ask AI with date range context."""
    init_db()
    
    provider = get_config("ai_provider")
    api_key = get_config("ai_api_key")
    
    if not provider or not api_key:
        console.print(Panel(f"[yellow]AI not configured. Run 'work AI-CONFIG' first.[/yellow]", border_style="yellow"))
        return
        
    from ai_handler import AIHandler
    
    # Loading
    with console.status(f"[bold green]{T('ai_analyzing')} {provider}...[/bold green]"):
        try:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            # Add one day to end_date to include it fully in string comparison if using ISO
            # But simple string compare roughly works if format matches key.
            # Better: Filter in python or proper SQL based on ISO.
            # Our timestamps are ISO `YYYY-MM-DDTHH:MM:SS`.
            # We can use LIKE 'YYYY-MM-DD%' logic in loop or SQL.
            
            # Simple SQL range filter:
            # We need start_date ISO at 00:00 and end_date at 23:59
            s_iso = start_date.strftime("%Y-%m-%dT00:00:00")
            e_iso = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
            
            conn = get_db_connection()
            cursor = conn.execute(
                "SELECT timestamp, event_type FROM events WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp ASC",
                (s_iso, e_iso)
            )
            events = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            handler = AIHandler(provider, api_key)
            context = handler.format_context(events)
            response = handler.ask_ai(question, context)
            
            UI.print(response, title=f"🤖 {provider} Response ({start_date_str} - {end_date_str})", border_style="magenta")

        except Exception as e:
            UI.print(f"[bold red]{T('ai_error')}: {e}[/bold red]", border_style="red")


# --- Export Commands ---

def process_sessions(events):
    """
    Process raw events into sessions (Start -> Stop).
    Returns list of dicts: {date, start, end, duration}
    """
    sessions = []
    session_start = None
    session_desc = None
    
    for ev in events:
        ts = datetime.fromisoformat(ev['timestamp'])
        etype = ev['event_type']
        
        if etype == 'START':
            if session_start is None:
                session_start = ts
                # Decrypt here
                raw_desc = ev.get('description', '') or ''
                session_desc = decrypt_text(raw_desc)
        elif etype == 'STOP':
            if session_start:
                duration = ts - session_start
                sessions.append({
                    "date": session_start.strftime("%Y-%m-%d"),
                    "start": session_start.strftime("%H:%M:%S"),
                    "end": ts.strftime("%H:%M:%S"),
                    "duration": duration, # Timedelta
                    "duration_str": format_duration(duration),
                    "description": session_desc
                })
                session_start = None
                session_desc = None
            
    # Handle active session (optional: skip or mark as active)
    # For export, usually we export finished sessions.
    return sessions

# --- Email & helpers ---
import webbrowser
import subprocess

def generate_csv_file(sessions, start_date_str, end_date_str) -> str:
    """Generate CSV file and return path."""
    import csv
    filename = f"work_history_{start_date_str.replace('/','')}-{end_date_str.replace('/','')}.csv"
    file_path = os.getcwd() + "/" + filename
    
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([T('header_date'), T('header_start'), T('header_end'), T('header_duration'), T('header_desc')])
        for s in sessions:
            writer.writerow([s['date'], s['start'], s['end'], s['duration_str'], s['description']])
    return file_path

def generate_pdf_file(sessions, start_date_str, end_date_str) -> str:
    """Generate PDF file and return path."""
    from xhtml2pdf import pisa
    total_sessions = len(sessions)
    total_duration = sum([s['duration'] for s in sessions], timedelta())
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Helvetica, sans-serif; padding: 20px; }}
            h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
            .summary {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #007bff; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>{T('report_title')}</h1>
        <p><strong>Range:</strong> {start_date_str} - {end_date_str}</p>
        
        <div class="summary">
            <h3>{T('report_summary')}</h3>
            <p><strong>{T('total_sessions')}:</strong> {total_sessions}</p>
            <p><strong>{T('total_duration')}:</strong> {format_duration(total_duration)}</p>
        </div>
        
        <table>
            <tr>
                <th>{T('header_date')}</th>
                <th>{T('header_start')}</th>
                <th>{T('header_end')}</th>
                <th>{T('header_duration')}</th>
                <th>{T('header_desc')}</th>
            </tr>
    """
    
    for s in sessions:
        html += f"""
            <tr>
                <td>{s['date']}</td>
                <td>{s['start']}</td>
                <td>{s['end']}</td>
                <td>{s['duration_str']}</td>
                <td>{s['description']}</td>
            </tr>
        """
        
    html += """
        </table>
    </body>
    </html>
    """
    
    filename = f"work_report_{start_date_str.replace('/','')}-{end_date_str.replace('/','')}.pdf"
    file_path = os.getcwd() + "/" + filename
    
    with open(file_path, "wb") as pdf_file:
        pisa.CreatePDF(html, dest=pdf_file)
        
    return file_path

@app.command(name="EXPORT-CSV")
def export_csv(start_date_str: str, end_date_str: str):
    """Export work history to CSV."""
    init_db()
    try:
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        s_iso = start_date.strftime("%Y-%m-%dT00:00:00")
        e_iso = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT timestamp, event_type, description FROM events WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp ASC",
            (s_iso, e_iso)
        )
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        sessions = process_sessions(events)
        path = generate_csv_file(sessions, start_date_str, end_date_str)
        UI.print(f"{T('export_csv_success')}:\n[blue]{path}[/blue] 📊", border_style="green")

    except Exception as e:
        UI.print(f"[bold red]Error: {e}[/bold red]", border_style="red")

@app.command(name="EXPORT-PDF")
def export_pdf(start_date_str: str, end_date_str: str):
    """Export work history to PDF."""
    init_db()
    try:
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        s_iso = start_date.strftime("%Y-%m-%dT00:00:00")
        e_iso = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT timestamp, event_type, description FROM events WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp ASC",
            (s_iso, e_iso)
        )
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        sessions = process_sessions(events)
        path = generate_pdf_file(sessions, start_date_str, end_date_str)
        UI.print(f"{T('export_pdf_success')}:\n[blue]{path}[/blue] 📄", border_style="green")

    except Exception as e:
         UI.print(f"[bold red]Error: {e}[/bold red]", border_style="red")

def open_email_client(file_path: str, subject: str, body: str):
    """Open default email client with attachment."""
    import urllib.parse
    
    # Try xdg-email (Linux)
    if SYSTEM_PLATFORM == "Linux" and shutil.which("xdg-email"):
        try:
            subprocess.call(["xdg-email", "--subject", subject, "--body", body, "--attach", file_path])
            UI.print(f"[green]{T('email_sent_auto')}[/green]", border_style="green")
            return
        except Exception:
            pass # Fallback

    # Generic Mailto (Can't attach file automatically in many cases)
    # We copy path to clipboard or just show it?
    params = {
        "subject": subject,
        "body": f"{body}\n\n[Attachment: {os.path.basename(file_path)}]"
    }
    qs = urllib.parse.urlencode(params).replace("+", "%20")
    mailto = f"mailto:?{qs}"
    
    webbrowser.open(mailto)
    UI.print(f"[yellow]{T('email_manual_hint')}[/yellow]\n[bold]{file_path}[/bold]", border_style="yellow")

def get_events_from_db(db_path, start_date_str, end_date_str):
    """Generic fetcher."""
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    s_iso = start_date.strftime("%Y-%m-%dT00:00:00")
    e_iso = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
    
    # Connection might need decrypt logic if using backup?
    # Actually decrypt logic is in 'process_sessions' which calls 'decrypt_text'
    # 'decrypt_text' uses global FERNET.
    # If we are using a backup, we assume the CURRENT key works for it (or it was decrypted before backup? no).
    # If backup was encrypted with OLD key, we can't decrypt it unless we have that key.
    # Assumption: User uses current key.
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
             "SELECT timestamp, event_type, description FROM events WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp ASC",
            (s_iso, e_iso)
        )
        events = [dict(row) for row in cur.fetchall()]
        conn.close()
        return events
    except Exception as e:
        console.print(f"[red]DB Error: {e}[/red]")
        return []

@app.command(name="SEND-TO")
def send_to():
    """Generate report and email it."""
    init_db()
    ensure_logged_in()
    
    # Interactive Prompts
    UI.print(f"[bold]{T('language_select')} Range:[/bold]") # Reuse? No, Custom prompt
    console.print("1. Today")
    console.print("2. This Month")
    console.print("3. Custom Range")
    
    choice = typer.prompt("Select", default="1")
    today = datetime.now()
    
    if choice == "1":
        s_str = today.strftime("%d/%m/%Y")
        e_str = s_str
    elif choice == "2":
        s_str = today.strftime("01/%m/%Y")
        # End of month? 
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        e_str = f"{last_day}/{today.month:02}/{today.year}"
    else:
        s_str = typer.prompt("Start (dd/mm/yyyy)")
        e_str = typer.prompt("End (dd/mm/yyyy)")

    # Format
    fmt = typer.prompt("Format (CSV/PDF)", default="PDF").upper()
    
    # Events
    events = get_events_from_db(DB_PATH, s_str, e_str)
    if not events:
        UI.print("[yellow]No data found.[/yellow]")
        return

    sessions = process_sessions(events)
    
    if fmt == "CSV":
        fpath = generate_csv_file(sessions, s_str, e_str)
    else:
        fpath = generate_pdf_file(sessions, s_str, e_str)
        
    subject = f"{T('email_subject')} ({s_str} - {e_str})"
    body = typer.prompt(T('email_body_prompt'), default="Please find the attached work report.")
    
    open_email_client(fpath, subject, body)

@app.command(name="SEND-BACKUP-TO")
def send_backup_to():
    """Email report from a backup file."""
    init_db()
    ensure_logged_in()

    if not BACKUP_DIR.exists():
        UI.print(f"[red]{T('backup_not_found')}[/red]", border_style="red")
        return
        
    backups = sorted(BACKUP_DIR.glob("*.db"), key=os.path.getmtime, reverse=True)
    if not backups:
        UI.print(f"[red]{T('backup_not_found')}[/red]", border_style="red")
        return

    UI.print("[bold]Select Backup:[/bold]")
    for i, b in enumerate(backups[:10]):
        console.print(f"{i+1}. {b.name}")
        
    idx = typer.prompt("Number", type=int)
    if idx < 1 or idx > len(backups):
        return
    
    target_db = backups[idx-1]
    
    # Range
    s_str = typer.prompt("Start (dd/mm/yyyy)", default="01/01/2024")
    e_str = typer.prompt("End (dd/mm/yyyy)", default=datetime.now().strftime("%d/%m/%Y"))
    
    # Format
    fmt = typer.prompt("Format (CSV/PDF)", default="PDF").upper()
    
    # Get Data
    events = get_events_from_db(target_db, s_str, e_str)
    sessions = process_sessions(events)
    
    if fmt == "CSV":
        fpath = generate_csv_file(sessions, s_str, e_str)
    else:
        fpath = generate_pdf_file(sessions, s_str, e_str)

    subject = f"{T('email_subject')} (Backup: {target_db.name})"
    body = typer.prompt(T('email_body_prompt'), default="Attached backup report.")
    
    open_email_client(fpath, subject, body)


# --- Backup Features ---

def check_auto_backup():
    """
    Check if auto-backup is needed based on config.
    Freq: DAILY, MONTHLY (default), NEVER, CUSTOM
    """
    try:
        freq = get_config("backup_freq")
        if not freq:
            freq = "MONTHLY"
            set_config("backup_freq", freq)
            
        if freq == "NEVER":
            return

        last_backup_str = get_config("last_auto_backup")
        # If no record, assume we need one (or maybe set to now to avoid immediate?) 
        # For safety, let's do one if never done.
        
        should_backup = False
        now = datetime.now()
        
        if not last_backup_str:
            should_backup = True
        else:
            last_backup = datetime.fromisoformat(last_backup_str)
            
            if freq == "DAILY":
                if now.date() > last_backup.date():
                    should_backup = True
            elif freq == "MONTHLY":
                # Check if month changed
                if now.month != last_backup.month or now.year != last_backup.year:
                    should_backup = True
            elif freq == "CUSTOM":
                # Custom interval in months (e.g., every 3 months)
                interval = int(get_config("backup_interval") or "1")
                # Simple check: month difference
                months_diff = (now.year - last_backup.year) * 12 + now.month - last_backup.month
                if months_diff >= interval:
                    should_backup = True

        if should_backup:
            backup_database() # This existing function handles the copy
            set_config("last_auto_backup", now.isoformat())
            # console.print(f"[dim]{T('backup_auto_triggered')}: {freq}[/dim]")

    except Exception:
        pass # Fail silently on auto-backup checks


@app.command(name="LOAD-BACKUP")
def load_backup(filename: str):
    """Restore database from a backup file."""
    # Safety: don't init db if we are going to overwrite it, 
    # but we need config? No, config is in DB. 
    # Just checking file existence is enough.
    
    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        UI.print(f"[bold red]{T('backup_not_found')}: {filename}[/bold red]", border_style="red")
        return
        
    if typer.confirm(f"{T('backup_restore_confirm')} '{filename}'?", abort=True):
        import shutil
        try:
            # Close existing connections if possible? 
            # In this script execution, we haven't opened yet unless init_db called.
            # We overwrite DB_PATH
            shutil.copy(backup_path, DB_PATH)
            UI.print(f"[bold green]{T('backup_restored')}[/bold green]", border_style="green")
        except Exception as e:
            UI.print(f"[bold red]Restore Error: {e}[/bold red]", border_style="red")

@app.command(name="CONFIG-BACKUP-AUTO")
def config_backup(frequency: str, interval: int = 1):
    """
    Configure auto-backup.
    FREQ: DAILY, MONTHLY, NEVER, CUSTOM
    INTERVAL: X (only for CUSTOM, e.g. every X months)
    """
    init_db()
    freq = frequency.upper()
    if freq not in ["DAILY", "MONTHLY", "NEVER", "CUSTOM"]:
         UI.print("[red]Invalid Frequency. Use: DAILY, MONTHLY, NEVER, CUSTOM[/red]", border_style="red")
         return
         
    set_config("backup_freq", freq)
    if freq == "CUSTOM":
        set_config("backup_interval", str(interval))
        
    UI.print(f"[bold green]{T('backup_config_updated')} {freq}[/bold green]", border_style="green")



# --- Encryption Features ---
from cryptography.fernet import Fernet

KEY_PATH = DB_PATH.parent / ".secret.key"
FERNET = None

def load_key():
    """Load encryption key if exists."""
    global FERNET
    if KEY_PATH.exists():
        with open(KEY_PATH, "rb") as key_file:
            key = key_file.read()
            try:
                FERNET = Fernet(key)
            except Exception:
                pass # Invalid key?

# Initialize key on module load
load_key()

def encrypt_text(text: str) -> str:
    """Encrypt text if FERNET is active."""
    if not FERNET or not text:
        return text
    try:
        return FERNET.encrypt(text.encode()).decode()
    except Exception:
        return text

def decrypt_text(text: str) -> str:
    """Decrypt text if FERNET is active."""
    if not FERNET or not text:
        return text
    try:
        # Check if it looks encrypted (starts with gAAAA...) - loose check
        # Or just try decrypt. 
        # If it wasn't encrypted (legacy data), decrypt might fail or return garbage if key matches?
        # Fernet tokens are URL safe base64.
        return FERNET.decrypt(text.encode()).decode()
    except Exception:
        # Fallback: maybe it wasn't encrypted
        return text

@app.command(name="INIT-ENCRYPTION")
def init_encryption(check_first: bool = False):
    """Initialize encryption setup."""
    # Check first mode for installer
    if check_first:
        if KEY_PATH.exists():
             return # Already setup
        if not typer.confirm(T('encrypt_init_prompt'), default=False):
             return
    
    # Generate Key
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as key_file:
        key_file.write(key)
    
    UI.print(f"[bold green]{T('encrypt_key_setup')}[/bold green]\n{T('encrypt_key_saved')}", border_style="green")
    load_key() # Reload
    
    # Enable:
    encrypt_on()

@app.command(name="GET-KEY")
def get_key():
    """Show the encryption key."""
    if KEY_PATH.exists():
        with open(KEY_PATH, "fb") as key_file:
             key = key_file.read().decode() # Read bytes, decode for display
        
        # Read as binary then decode to show string
        with open(KEY_PATH, "rb") as f:
            k = f.read().decode()
        UI.print(f"[bold red]SECRET KEY:[/bold red]\n{k}", border_style="red")
    else:
        UI.print(f"[yellow]{T('backup_not_found')} (Key)[/yellow]", border_style="yellow")

@app.command(name="CHANGE-KEY")
def change_key():
    """Change the encryption key (WIPES DATA)."""
    UI.print(f"[bold red]{T('encrypt_warning_wipe')}[/bold red]", border_style="red")
    if not typer.confirm("Confirm reset?"):
        return
        
    # Backup first?
    backup_db()
    
    # Delete DB and Key
    try:
        if DB_PATH.exists(): os.remove(DB_PATH)
        if KEY_PATH.exists(): os.remove(KEY_PATH)
        UI.print("[green]Data wiped. Starting setup...[/green]", border_style="green")
        init_encryption()
    except Exception as e:
        UI.print(f"[red]Error: {e}[/red]", border_style="red")

@app.command(name="ENCRIPT-ON")
def encrypt_on():
    """Enable encryption on existing data."""
    init_db()
    
    if not FERNET:
        # Generate temporary if not exists? Or demand init?
        # Better to run init logic.
        if not KEY_PATH.exists():
             init_encryption()
             return

    # Migrate: Plain -> Encrypt
    conn = get_db_connection()
    events = [dict(row) for row in conn.execute("SELECT id, description FROM events").fetchall()]
    
    for ev in events:
        desc = ev.get('description')
        if desc:
            # We assume it is plain text right now.
            # Safety: try to decrypt. If fail, it's plain. If succeed, it's already encrypted?
            # Double encryption is bad.
            # Simple heuristic: If we just turned on, we assume everything is plain unless we track state.
            # But the requirement says "Migrate".
            encrypted = encrypt_text(desc)
            conn.execute("UPDATE events SET description = ? WHERE id = ?", (encrypted, ev['id']))
            
    conn.commit()
    conn.close()
    UI.print(f"[bold green]{T('encrypt_enabled')}[/bold green]", border_style="green")

@app.command(name="ENCRIPT-OFF")
def encrypt_off():
    """Disable encryption (Decrypt data)."""
    global FERNET
    init_db()
    if not FERNET:
        UI.print("[red]Encryption not active.[/red]", border_style="red")
        return
        
    # Migrate: Encrypt -> Plain
    conn = get_db_connection()
    events = [dict(row) for row in conn.execute("SELECT id, description FROM events").fetchall()]
    
    for ev in events:
        desc = ev.get('description')
        if desc:
            plain = decrypt_text(desc)
            conn.execute("UPDATE events SET description = ? WHERE id = ?", (plain, ev['id']))
            
    conn.commit()
    conn.close()
    
    # Delete Key
    if KEY_PATH.exists():
        os.remove(KEY_PATH)
        
    FERNET = None
    
    UI.print(f"[bold yellow]{T('encrypt_disabled')}[/bold yellow]", border_style="yellow")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Working_Code Time Tracker
    """
    # Always check auto-backup on any run
    if DB_PATH.exists():
        try:
            check_auto_backup() 
        except: 
            pass

    if ctx.invoked_subcommand is None:
        # Custom Help
        print_banner(T("welcome_banner"))
        
        table = Table(box=box.ROUNDED, header_style="bold magenta", border_style="bright_blue", show_lines=True)
        table.add_column(T("col_command"), style="cyan bold", no_wrap=True)
        table.add_column(T("col_desc"), style="white")
        table.add_column(T("col_usage"), style="dim italic")

        # Map commands to description keys
        cmds = [
            ("ON", "desc_on", "work ON [Description]"),
            ("OFF", "desc_off", "work OFF"),
            ("TIME", "desc_time", "work TIME"),
            ("TIME-TODAY", "desc_time_today", "work TIME-TODAY"),
            ("DB", "desc_db", "work DB"),
            ("BACKUP", "desc_backup", "work BACKUP"),
            ("LOAD-BACKUP", "desc_load_backup", "work LOAD-BACKUP [file]"),
            ("CONFIG-BACKUP-AUTO", "desc_config_backup", "work CONFIG-BACKUP-AUTO [freq]"),
            ("TIME-SELECT", "desc_time_select", "work TIME-SELECT dd/mm/yyyy"),
            ("TIME-RANGE", "desc_time_range", "work TIME-RANGE d1/m1..."),
            ("INIT-TIME", "desc_init_time", "work INIT-TIME"),
            ("INIT-TIME_WHEN", "desc_init_time_when", "work INIT-TIME_WHEN..."),
            ("CLEAR-ALL", "desc_clear_all", "work CLEAR-ALL"),
            ("LANG", "desc_lang", "work LANG"),
            ("LANG-SET", "desc_lang_set", "work LANG-SET"),
            ("AI-CONFIG", "desc_ai_config", "work AI-CONFIG"),
            ("AI-GEN-ASK", "desc_ai_gen_ask", "work AI-GEN-ASK \"Query\""),
            ("AI-SEL-ASK-RANGE-TIME", "desc_ai_range_ask", "work AI-SEL-ASK-RANGE-TIME d1 d2 \"Query\""),
            ("EXPORT-CSV", "desc_export_csv", "work EXPORT-CSV d1 d2"),
            ("EXPORT-PDF", "desc_export_pdf", "work EXPORT-PDF d1 d2"),
            ("SEND-TO", "desc_send_to", "work SEND-TO"),
            ("SEND-BACKUP-TO", "desc_send_backup_to", "work SEND-BACKUP-TO"),
            ("INIT-ENCRYPTION", "desc_init_encryption", "work INIT-ENCRYPTION"),
            ("GET-KEY", "desc_get_key", "work GET-KEY"),
            ("CHANGE-KEY", "desc_change_key", "work CHANGE-KEY"),
            ("ENCRIPT-ON", "desc_encrypt_on", "work ENCRIPT-ON"),
            ("ENCRIPT-OFF", "desc_encrypt_off", "work ENCRIPT-OFF"),
        ]

        for cmd, desc_key, usage in cmds:
            table.add_row(cmd, T(desc_key), usage)
        
        console.print(table)
        console.print(Align.center(f"[dim]{T('help_footer')}[/dim]"))

if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        console.print(Panel(f"[bold red]An unexpected error occurred:[/bold red]\n{e}", title="System Error", border_style="red"))
        # In debug mode (optional), you might want to raise e to see the stack trace
        # raise e
