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
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.align import Align
from rich.traceback import install
from pathlib import Path
from typing import Optional

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

def check_db_permissions():
    """Ensure we have write permissions to the database directory."""
    if not DB_PATH.parent.exists():
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
             console.print(f"[{ERROR_STYLE}]CRITICAL ERROR:[/{ERROR_STYLE}] Cannot create data directory at {DB_PATH.parent}")
             console.print("Please check file permissions or run with appropriate privileges.")
             sys.exit(1)
             
    if DB_PATH.exists() and not os.access(DB_PATH, os.W_OK):
        console.print(f"[{ERROR_STYLE}]CRITICAL ERROR:[/{ERROR_STYLE}] Database at {DB_PATH} is not writable.")
        console.print("Please check file owners and permissions.")
        sys.exit(1)

def get_db_connection():
    check_db_permissions()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10) # 10s timeout to handle potential locks
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError as e:
        console.print(f"[{ERROR_STYLE}]Database Error:[/{ERROR_STYLE}] {e}")
        console.print(f"[{WARNING_STYLE}]Hint:[/{WARNING_STYLE}] The database might be locked by another process or permissions are denied.")
        raise typer.Exit(code=1)

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        console.print(f"[{ERROR_STYLE}]Error:[/{ERROR_STYLE}] Invalid date format. Please use [{WARNING_STYLE}]dd/mm/yyyy[/{WARNING_STYLE}].")
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

@app.command(name="ON")
def start_timer():
    """Start the timer."""
    init_db()
    conn = get_db_connection()
    if get_active_session_start(conn):
        console.print(Panel(Align.center("[bold yellow]Timer is already running![/bold yellow] ⏳", vertical="middle"), 
                          title="Info", border_style="yellow", box=box.ROUNDED, padding=(1, 2)))
        conn.close()
        return

    now = datetime.now()
    conn.execute("INSERT INTO events (timestamp, event_type) VALUES (?, ?)", (now.isoformat(), 'START'))
    conn.commit()
    conn.close()
    
    console.print(Panel(Align.center(f"[bold green]TIMER STARTED[/bold green]\nTime: [cyan]{now.strftime('%H:%M:%S')}[/cyan] 🚀", vertical="middle"), 
                      title="Success", border_style="green", box=box.HEAVY, padding=(1, 5)))

@app.command(name="OFF")
def stop_timer():
    """Stop the timer."""
    init_db()
    conn = get_db_connection()
    start_time = get_active_session_start(conn)
    if not start_time:
        console.print(Panel(Align.center("[bold yellow]Timer is NOT running![/bold yellow] 🛑", vertical="middle"), 
                          title="Info", border_style="yellow", box=box.ROUNDED, padding=(1, 2)))
        conn.close()
        return

    now = datetime.now()
    duration = calculate_duration(start_time, now)
    conn.execute("INSERT INTO events (timestamp, event_type) VALUES (?, ?)", (now.isoformat(), 'STOP'))
    conn.commit()
    conn.close()
    
    text = Text()
    text.append("TIMER STOPPED\n", style="bold red")
    text.append(f"Stopped at: {now.strftime('%H:%M:%S')}\n", style="dim white")
    text.append(f"Duration:   {format_duration(duration)}", style="bold white")
    
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
        console.print(Panel(Align.center(f"Current Session:\n[bold cyan]{format_duration(duration)}[/bold cyan] ⏱️", vertical="middle"), 
                          title="Active Timer", border_style="cyan", box=box.ROUNDED, padding=(1, 4)))
    else:
        console.print(Panel(Align.center("[dim]Timer is inactive.[/dim] 💤", vertical="middle"), title="Status", border_style="dim", box=box.ROUNDED))

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
        f"Total Time Today ([cyan]{now.strftime('%d/%m/%Y')}[/cyan])\n[bold green]{format_duration(total)}[/bold green] 📅", vertical="middle"), 
        title="Daily Summary", border_style="green", box=box.DOUBLE, padding=(1, 5)))

@app.command(name="DB")
def show_db_path():
    """Show database path."""
    console.print(Panel(f"[bold]Database Path:[/bold]\n[blue]{DB_PATH}[/blue] 📂", title="Configuration", border_style="blue", box=box.ROUNDED))

@app.command(name="BACKUP")
def backup_db():
    """Backup the database."""
    if not DB_PATH.exists():
        console.print(Panel("[bold red]Database does not exist yet![/bold red]", border_style="red"))
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_name = f"{DB_NAME}_{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
    shutil.copy(DB_PATH, backup_path)
    console.print(Panel(f"Backup created: [bold green]{backup_name}[/bold green]\nLocation: [blue]{backup_path}[/blue] 💾", 
                      title="Backup Success", border_style="green", box=box.ROUNDED))

@app.command(name="TIME-SELECT")
def time_select(date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show total time specific date."""
    init_db()
    target_date = parse_date(date_str)
    total = calculate_daily_total(target_date)
    console.print(Panel(Align.center(
        f"Total Time on [cyan]{date_str}[/cyan]\n[bold magenta]{format_duration(total)}[/bold magenta] 🗓️", vertical="middle"), 
        title="Historical Data", border_style="magenta", box=box.ROUNDED))

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
        f"Range: [cyan]{start_date_str}[/cyan] to [cyan]{end_date_str}[/cyan]\n"
        f"Total Time: [bold orange1]{format_duration(total_duration)}[/bold orange1] 📊", vertical="middle"),
        title="Range Summary", border_style="orange1", box=box.ROUNDED, padding=(1, 5)))

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
        console.print(Panel(Align.center(f"First Start Today:\n[bold cyan]{first_time.strftime('%H:%M:%S')}[/bold cyan] 🌅", vertical="middle"), 
                          title="Start Time", border_style="cyan", box=box.ROUNDED))
    else:
        console.print(Panel(Align.center("[dim]No sessions started today.[/dim]", vertical="middle"), title="Start Time", border_style="dim"))

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
        console.print(Panel(Align.center(f"First Start on [cyan]{date_str}[/cyan]:\n[bold cyan]{first_time.strftime('%H:%M:%S')}[/bold cyan] 🗓️", vertical="middle"), 
                          title="Historical Start Time", border_style="cyan", box=box.ROUNDED))
    else:
        console.print(Panel(f"[dim]No sessions found on {date_str}.[/dim]", title="Historical Start Time", border_style="dim"))


@app.command(name="CLEAR-ALL")
def clear_all():
    """Clear all database data."""
    if not DB_PATH.exists():
        console.print(Panel("[yellow]Database empty.[/yellow]", border_style="yellow"))
        return
        
    confirm = typer.confirm("Are you sure you want to delete ALL tracking data? (Backups are safe)")
    if not confirm:
        console.print("Aborted.")
        raise typer.Abort()
        
    conn = get_db_connection()
    conn.execute("DELETE FROM events")
    conn.commit()
    conn.close()
    console.print(Panel("[bold red]Database CLEARED.[/bold red] 🗑️", title="Warning", border_style="red", box=box.HEAVY))

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Working_Code Time Tracker
    """
    if ctx.invoked_subcommand is None:
        # Custom Help
        print_banner("Visual Time Tracker")
        
        table = Table(box=box.ROUNDED, header_style="bold magenta", border_style="bright_blue", show_lines=True)
        table.add_column("Command", style="cyan bold", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Usage", style="dim italic")

        table.add_row("ON", "Start the timer", "work ON")
        table.add_row("OFF", "Stop the timer", "work OFF")
        table.add_row("TIME", "Current session duration", "work TIME")
        table.add_row("TIME-TODAY", "Total time worked today", "work TIME-TODAY")
        table.add_row("DB", "Show database path", "work DB")
        table.add_row("BACKUP", "Backup database", "work BACKUP")
        table.add_row("TIME-SELECT", "Time for specific day", "work TIME-SELECT dd/mm/yyyy")
        table.add_row("TIME-RANGE", "Time for date range", "work TIME-RANGE d1/m1... d2/m2...")
        table.add_row("INIT-TIME", "First start time today", "work INIT-TIME")
        table.add_row("INIT-TIME_WHEN", "First start on specific day", "work INIT-TIME_WHEN dd/mm/yyyy")
        table.add_row("CLEAR-ALL", "Clear all data", "work CLEAR-ALL")
        
        console.print(table)
        console.print(Align.center("[dim]Use 'work [COMMAND] --help' for more info.[/dim]"))

if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        console.print(Panel(f"[bold red]An unexpected error occurred:[/bold red]\n{e}", title="System Error", border_style="red"))
        # In debug mode (optional), you might want to raise e to see the stack trace
        # raise e
