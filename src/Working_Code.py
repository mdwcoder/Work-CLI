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

def init_db():
    conn = get_db_connection()
    # Events Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT
        )
    ''')
    # Migration for existing DBs if needed
    try:
        conn.execute("ALTER TABLE events ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass # Column likely exists
    
    # Config Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

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

def set_config(key: str, value: str):
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
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
    """Returns the start time of the current session if active, else None."""
    cursor = conn.execute("SELECT timestamp, event_type FROM events ORDER BY timestamp DESC LIMIT 1")
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
    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_row(Text("⚡ WORK-CLI ⚡", style="bold magenta", justify="center"))
    if subtitle:
        grid.add_row(Text(subtitle, style="cyan", justify="center"))
    
    console.print(Panel(grid, style=BORDER_STYLE, border_style=BORDER_STYLE, box=box.HEAVY))

# --- Commands ---

@app.command(name="ON")
def start_timer(description: str = typer.Argument(None)):
    """Start the timer. Optional: Add a description."""
    init_db()
    conn = get_db_connection()
    if get_active_session_start(conn):
        console.print(Panel(Align.center(f"[bold yellow]{T('timer_already_running')}[/bold yellow]", vertical="middle"), 
                          title="Info", border_style="yellow", box=box.ROUNDED, padding=(1, 2)))
        conn.close()
        return

    now = datetime.now()
    conn.execute("INSERT INTO events (timestamp, event_type, description) VALUES (?, ?, ?)", (now.isoformat(), 'START', description))
    conn.commit()
    conn.close()
    
    console.print(Panel(Align.center(f"[bold green]{T('timer_started')}[/bold green]\nTime: [cyan]{now.strftime('%H:%M:%S')}[/cyan] 🚀", vertical="middle"), 
                      title="Success", border_style="green", box=box.HEAVY, padding=(1, 5)))
    
    if not description:
         console.print(Align.center(f"[dim yellow]{T('tip_use_description')}[/dim yellow]"))
    else:
         console.print(Align.center(f"[dim]Note: {description}[/dim]"))

@app.command(name="OFF")
def stop_timer():
    """Stop the timer."""
    init_db()
    conn = get_db_connection()
    start_time = get_active_session_start(conn)
    if not start_time:
        console.print(Panel(Align.center(f"[bold yellow]{T('timer_not_running')}[/bold yellow]", vertical="middle"), 
                          title="Info", border_style="yellow", box=box.ROUNDED, padding=(1, 2)))
        conn.close()
        return

    now = datetime.now()
    duration = calculate_duration(start_time, now)
    conn.execute("INSERT INTO events (timestamp, event_type) VALUES (?, ?)", (now.isoformat(), 'STOP'))
    conn.commit()
    conn.close()
    
    text = Text()
    text.append(f"{T('timer_stopped')}\n", style="bold red")
    text.append(f"{T('stopped_at')}: {now.strftime('%H:%M:%S')}\n", style="dim white")
    text.append(f"{T('duration')}:   {format_duration(duration)}", style="bold white")
    
    console.print(Panel(Align.center(text, vertical="middle"), 
                      title="Stopped", border_style="red", box=box.HEAVY, padding=(1, 5)))

@app.command(name="TIME")
def current_time():
    """Show current session time."""
    init_db()
    conn = get_db_connection()
    start_time = get_active_session_start(conn)
    conn.close()

    if start_time:
        duration = calculate_duration(start_time, datetime.now())
        console.print(Panel(Align.center(f"{T('current_session')}:\n[bold cyan]{format_duration(duration)}[/bold cyan] ⏱️", vertical="middle"), 
                          title=T('active_timer'), border_style="cyan", box=box.ROUNDED, padding=(1, 4)))
    else:
        console.print(Panel(Align.center(f"[dim]{T('timer_inactive')}[/dim]", vertical="middle"), title="Status", border_style="dim", box=box.ROUNDED))

def calculate_daily_total(target_date: datetime) -> timedelta:
    conn = get_db_connection()
    date_str = target_date.strftime("%Y-%m-%d")
    cursor = conn.execute(
        "SELECT timestamp, event_type FROM events WHERE timestamp LIKE ? ORDER BY timestamp ASC", 
        (f"{date_str}%",)
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
    now = datetime.now()
    total = calculate_daily_total(now)
    
    console.print(Panel(Align.center(
        f"{T('total_time_today')} ([cyan]{now.strftime('%d/%m/%Y')}[/cyan])\n[bold green]{format_duration(total)}[/bold green] 📅", vertical="middle"), 
        title=T('daily_summary'), border_style="green", box=box.DOUBLE, padding=(1, 5)))

@app.command(name="DB")
def show_db_path():
    """Show database path."""
    console.print(Panel(f"[bold]{T('database_path')}:[/bold]\n[blue]{DB_PATH}[/blue] 📂", title="Configuration", border_style="blue", box=box.ROUNDED))

@app.command(name="BACKUP")
def backup_db():
    """Backup the database."""
    if not DB_PATH.exists():
        console.print(Panel(f"[bold red]{T('database_exist_error')}[/bold red]", border_style="red"))
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_name = f"{DB_NAME}_{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
    shutil.copy(DB_PATH, backup_path)
    console.print(Panel(f"{T('backup_created')}: [bold green]{backup_name}[/bold green]\n{T('location')}: [blue]{backup_path}[/blue] 💾", 
                      title="Backup Success", border_style="green", box=box.ROUNDED))

@app.command(name="TIME-SELECT")
def time_select(date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show total time specific date."""
    init_db()
    target_date = parse_date(date_str)
    total = calculate_daily_total(target_date)
    console.print(Panel(Align.center(
        f"{T('total_time_on')} [cyan]{date_str}[/cyan]\n[bold magenta]{format_duration(total)}[/bold magenta] 🗓️", vertical="middle"), 
        title=T('historical_data'), border_style="magenta", box=box.ROUNDED))

@app.command(name="TIME-RANGE")
def time_range(start_date_str: str = typer.Argument(..., metavar="dd/mm/yyyy"), end_date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show total time in date range."""
    init_db()
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    total_duration = timedelta()
    current_date = start_date
    while current_date <= end_date:
        total_duration += calculate_daily_total(current_date)
        current_date += timedelta(days=1)
        
    console.print(Panel(Align.center(
        f"Range: [cyan]{start_date_str}[/cyan] - [cyan]{end_date_str}[/cyan]\n"
        f"{T('total_time')}: [bold orange1]{format_duration(total_duration)}[/bold orange1] 📊", vertical="middle"),
        title=T('range_summary'), border_style="orange1", box=box.ROUNDED, padding=(1, 5)))

@app.command(name="INIT-TIME")
def init_time():
    """Show first start time today."""
    init_db()
    today_str = get_today_str()
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT timestamp FROM events WHERE timestamp LIKE ? AND event_type='START' ORDER BY timestamp ASC LIMIT 1",
        (f"{today_str}%",)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        first_time = datetime.fromisoformat(row['timestamp'])
        console.print(Panel(Align.center(f"{T('first_start_today')}:\n[bold cyan]{first_time.strftime('%H:%M:%S')}[/bold cyan] 🌅", vertical="middle"), 
                          title="Start Time", border_style="cyan", box=box.ROUNDED))
    else:
        console.print(Panel(Align.center(f"[dim]{T('no_sessions_today')}[/dim]", vertical="middle"), title="Start Time", border_style="dim"))

@app.command(name="INIT-TIME_WHEN")
def init_time_when(date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show first start time on specific date."""
    init_db()
    target_date = parse_date(date_str)
    date_iso_prefix = target_date.strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT timestamp FROM events WHERE timestamp LIKE ? AND event_type='START' ORDER BY timestamp ASC LIMIT 1",
        (f"{date_iso_prefix}%",)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        first_time = datetime.fromisoformat(row['timestamp'])
        console.print(Panel(Align.center(f"{T('first_start_on')} [cyan]{date_str}[/cyan]:\n[bold cyan]{first_time.strftime('%H:%M:%S')}[/bold cyan] 🗓️", vertical="middle"), 
                          title="Historical Start Time", border_style="cyan", box=box.ROUNDED))
    else:
        console.print(Panel(f"[dim]{T('no_sessions_found')} {date_str}.[/dim]", title="Historical Start Time", border_style="dim"))


@app.command(name="CLEAR-ALL")
def clear_all():
    """Clear all database data."""
    if not DB_PATH.exists():
        console.print(Panel(f"[yellow]{T('database_empty')}[/yellow]", border_style="yellow"))
        return
        
    confirm = typer.confirm(T('clear_confirmation'))
    if not confirm:
        console.print(T('aborted'))
        raise typer.Abort()
        
    conn = get_db_connection()
    conn.execute("DELETE FROM events")
    conn.commit()
    conn.close()
    console.print(Panel(f"[bold red]{T('database_cleared')}[/bold red]", title="Warning", border_style="red", box=box.HEAVY))

@app.command(name="LANG")
def show_lang():
    """Show current language."""
    init_db()
    lang = get_language()
    console.print(Panel(Align.center(f"{T('language_current')}: [bold cyan]{lang}[/bold cyan] 🌍", vertical="middle"), 
                      title="Configuration", border_style="blue", box=box.ROUNDED))

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
            console.print(Panel(f"[bold green]{new_lang_text} {code}![/bold green]", border_style="green"))
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
        console.print(Panel(f"[bold green]{new_lang_text} {choice}![/bold green]", border_style="green"))
    else:
        console.print(f"[red]Invalid code. Available: {', '.join(TRANSLATIONS.keys())}[/red]")


# --- AI Commands ---

@app.command(name="AI-CONFIG")
def ai_config():
    """Configure AI Provider and Key."""
    init_db()
    console.print(Panel(f"[bold]{T('ai_config_menu')}[/bold]", border_style="blue"))
    
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
        console.print(Panel(f"[bold green]{T('ai_key_saved')} {provider}![/bold green]", border_style="green"))

@app.command(name="AI-GEN-ASK")
def ai_gen_ask(question: str):
    """Ask AI with full context."""
    init_db()
    
    # helper to get ai
    provider = get_config("ai_provider")
    api_key = get_config("ai_api_key")
    
    if not provider or not api_key:
        console.print(Panel(f"[yellow]AI not configured. Run 'work AI-CONFIG' first.[/yellow]", border_style="yellow"))
        return

    from ai_handler import AIHandler
    
    # Loading
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
            
            console.print(Panel(response, title=f"🤖 {provider} Response", border_style="magenta", box=box.ROUNDED))
            
        except Exception as e:
            console.print(Panel(f"[bold red]{T('ai_error')}: {e}[/bold red]", border_style="red"))

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
            
            console.print(Panel(response, title=f"🤖 {provider} Response ({start_date_str} - {end_date_str})", border_style="magenta", box=box.ROUNDED))

        except Exception as e:
            console.print(Panel(f"[bold red]{T('ai_error')}: {e}[/bold red]", border_style="red"))


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
                session_desc = ev.get('description', '') or ''
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

@app.command(name="EXPORT-CSV")
def export_csv(start_date_str: str, end_date_str: str):
    """Export work history to CSV."""
    init_db()
    import csv
    
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
        
        filename = f"work_history_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.csv"
        file_path = os.getcwd() + "/" + filename
        
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([T('header_date'), T('header_start'), T('header_end'), T('header_duration'), T('header_desc')])
            for s in sessions:
                writer.writerow([s['date'], s['start'], s['end'], s['duration_str'], s['description']])
                
        console.print(Panel(f"{T('export_csv_success')}:\n[blue]{file_path}[/blue] 📊", border_style="green"))

    except Exception as e:
        console.print(Panel(f"[bold red]Error: {e}[/bold red]", border_style="red"))

@app.command(name="EXPORT-PDF")
def export_pdf(start_date_str: str, end_date_str: str):
    """Export work history to PDF."""
    init_db()
    from xhtml2pdf import pisa
    
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
        total_sessions = len(sessions)
        total_duration = sum([s['duration'] for s in sessions], timedelta())
        
        # HTML Template
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
        
        filename = f"work_report_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.pdf"
        file_path = os.getcwd() + "/" + filename
        
        with open(file_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html, dest=pdf_file)
            
        if pisa_status.err:
            console.print(Panel(f"[bold red]PDF Generation Error[/bold red]", border_style="red"))
        else:
            console.print(Panel(f"{T('export_pdf_success')}:\n[blue]{file_path}[/blue] 📄", border_style="green"))

    except Exception as e:
        console.print(Panel(f"[bold red]Error: {e}[/bold red]", border_style="red"))


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
        console.print(Panel(f"[bold red]{T('backup_not_found')}: {filename}[/bold red]", border_style="red"))
        return
        
    if typer.confirm(f"{T('backup_restore_confirm')} '{filename}'?", abort=True):
        import shutil
        try:
            # Close existing connections if possible? 
            # In this script execution, we haven't opened yet unless init_db called.
            # We overwrite DB_PATH
            shutil.copy(backup_path, DB_PATH)
            console.print(Panel(f"[bold green]{T('backup_restored')}[/bold green]", border_style="green"))
        except Exception as e:
            console.print(Panel(f"[bold red]Restore Error: {e}[/bold red]", border_style="red"))

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
         console.print("[red]Invalid Frequency. Use: DAILY, MONTHLY, NEVER, CUSTOM[/red]")
         return
         
    set_config("backup_freq", freq)
    if freq == "CUSTOM":
        set_config("backup_interval", str(interval))
        
    console.print(Panel(f"[bold green]{T('backup_config_updated')} {freq}[/bold green]", border_style="green"))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Working_Code Time Tracker
    """
    # Always check auto-backup on any run (or only main?)
    # Running on any command ensures we don't miss it if user uses it daily.
    # But we need DB ready.
    if DB_PATH.exists():
        try:
            # We assume DB is accessible. 
            # We need to initialize config table lookup if not using get_config wrapper that connects.
            # get_config does internal connection.
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
