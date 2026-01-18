import typer
import sqlite3
import shutil
import os
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from pathlib import Path
from typing import Optional

# Configuration
DB_NAME = "working_code.db"
SCRIPT_DIR = Path(__file__).parent.absolute()
DB_PATH = SCRIPT_DIR / DB_NAME

app = typer.Typer(help="Visual Time Tracker for Terminal", add_completion=False)
console = Console()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
        console.print(f"[bold red]Error:[/bold red] Invalid date format. Please use [yellow]dd/mm/yyyy[/yellow].")
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

@app.command(name="ON")
def start_timer():
    """Start the timer."""
    init_db()
    conn = get_db_connection()
    if get_active_session_start(conn):
        console.print(Panel("[bold yellow]Timer is already running![/bold yellow] ⏳", title="Info", border_style="yellow"))
        conn.close()
        return

    now = datetime.now()
    conn.execute("INSERT INTO events (timestamp, event_type) VALUES (?, ?)", (now.isoformat(), 'START'))
    conn.commit()
    conn.close()
    console.print(Panel(f"[bold green]Timer STARTED[/bold green] at [cyan]{now.strftime('%H:%M:%S')}[/cyan] 🚀", title="Success", border_style="green"))

@app.command(name="OFF")
def stop_timer():
    """Stop the timer."""
    init_db()
    conn = get_db_connection()
    start_time = get_active_session_start(conn)
    if not start_time:
        console.print(Panel("[bold yellow]Timer is NOT running![/bold yellow] 🛑", title="Info", border_style="yellow"))
        conn.close()
        return

    now = datetime.now()
    duration = calculate_duration(start_time, now)
    conn.execute("INSERT INTO events (timestamp, event_type) VALUES (?, ?)", (now.isoformat(), 'STOP'))
    conn.commit()
    conn.close()
    
    console.print(Panel(
        f"[bold red]Timer STOPPED[/bold red] at [cyan]{now.strftime('%H:%M:%S')}[/cyan]\n"
        f"Session Duration: [bold white]{format_duration(duration)}[/bold white] ✅", 
        title="Success", border_style="red"
    ))

@app.command(name="TIME")
def current_time():
    """Show current session time."""
    init_db()
    conn = get_db_connection()
    start_time = get_active_session_start(conn)
    conn.close()

    if start_time:
        duration = calculate_duration(start_time, datetime.now())
        console.print(Panel(f"Current Session: [bold cyan]{format_duration(duration)}[/bold cyan] ⏱️", title="Status", border_style="cyan"))
    else:
        console.print(Panel("[dim]Timer is inactive.[/dim] 💤", title="Status", border_style="dim"))

def calculate_daily_total(target_date: datetime) -> timedelta:
    conn = get_db_connection()
    # Filter events for this specific day
    # Events are stored in ISO format: YYYY-MM-DDTHH:MM:SS.mmmmmm
    # We can match the date string prefix
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

    # Handle case where session is still active TODAY
    # Note: If session started yesterday and matches today's query? 
    # The query filters strictly by date string.
    # If a session spans across midnight, this simple logic splits strictly by START time date.
    # User requirement is "simple", so we stick to start time attribution or current time integration.
    # If the session is currently active and started TODAY:
    if session_start:
        # Check if the session is essentially currently active (last event was start)
        # We need to verify if this 'session_start' corresponds to the *latest* state of DB
        # But for 'daily total', if we have a dangling start for that day, and today is that day, we add "now - start"
        if target_date.date() == datetime.now().date():
             total_duration += (datetime.now() - session_start)
    
    return total_duration

@app.command(name="TIME-TODAY")
def time_today():
    """Show total time worked today."""
    init_db()
    now = datetime.now()
    total = calculate_daily_total(now)
    console.print(Panel(f"Total Time Today ([cyan]{now.strftime('%d/%m/%Y')}[/cyan]): [bold green]{format_duration(total)}[/bold green] 📅", title="Daily Summary", border_style="green"))

@app.command(name="DB")
def show_db_path():
    """Show database path."""
    console.print(Panel(f"[bold]Database Path:[/bold]\n[blue]{DB_PATH}[/blue] 📂", title="Configuration", border_style="blue"))

@app.command(name="BACKUP")
def backup_db():
    """Backup the database."""
    if not DB_PATH.exists():
        console.print(Panel("[bold red]Database does not exist yet![/bold red]", border_style="red"))
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_name = f"{DB_NAME}_{timestamp}"
    backup_path = SCRIPT_DIR / backup_name
    shutil.copy(DB_PATH, backup_path)
    console.print(Panel(f"Backup created: [bold green]{backup_name}[/bold green] 💾", title="Backup Success", border_style="green"))

@app.command(name="TIME-SELECT")
def time_select(date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show total time specific date."""
    init_db()
    target_date = parse_date(date_str)
    total = calculate_daily_total(target_date)
    console.print(Panel(f"Total Time on [cyan]{date_str}[/cyan]: [bold magenta]{format_duration(total)}[/bold magenta] 🗓️", title="Historical Data", border_style="magenta"))

@app.command(name="TIME-RANGE")
def time_range(start_date_str: str = typer.Argument(..., metavar="dd/mm/yyyy"), end_date_str: str = typer.Argument(..., metavar="dd/mm/yyyy")):
    """Show total time in date range."""
    init_db()
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    # Needs to be inclusive, so iterate through days
    total_duration = timedelta()
    current_date = start_date
    while current_date <= end_date:
        total_duration += calculate_daily_total(current_date)
        current_date += timedelta(days=1)
        
    console.print(Panel(
        f"Range: [cyan]{start_date_str}[/cyan] to [cyan]{end_date_str}[/cyan]\n"
        f"Total Time: [bold orange1]{format_duration(total_duration)}[/bold orange1] 📊",
        title="Range Summary", border_style="orange1"
    ))

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
        console.print(Panel(f"First Start Today: [bold cyan]{first_time.strftime('%H:%M:%S')}[/bold cyan] 🌅", title="Start Time", border_style="cyan"))
    else:
        console.print(Panel("[dim]No sessions started today.[/dim]", title="Start Time", border_style="dim"))

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
        console.print(Panel(f"First Start on [cyan]{date_str}[/cyan]: [bold cyan]{first_time.strftime('%H:%M:%S')}[/bold cyan] 🗓️", title="Historical Start Time", border_style="cyan"))
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
    console.print(Panel("[bold red]Database CLEARED.[/bold red] 🗑️", title="Warning", border_style="red"))

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Working_Code Time Tracker
    """
    if ctx.invoked_subcommand is None:
        # Custom Help
        table = Table(title="Working_Code Commands", box=box.ROUNDED, header_style="bold magenta")
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Usage", style="dim")

        table.add_row("ON", "Start the timer", "Working_Code.py ON")
        table.add_row("OFF", "Stop the timer", "Working_Code.py OFF")
        table.add_row("TIME", "Current session duration", "Working_Code.py TIME")
        table.add_row("TIME-TODAY", "Total time worked today", "Working_Code.py TIME-TODAY")
        table.add_row("DB", "Show database path", "Working_Code.py DB")
        table.add_row("BACKUP", "Backup database", "Working_Code.py BACKUP")
        table.add_row("TIME-SELECT", "Time for specific day", "Working_Code.py TIME-SELECT dd/mm/yyyy")
        table.add_row("TIME-RANGE", "Time for date range", "Working_Code.py TIME-RANGE d1/m1/y1 d2/m2/y2")
        table.add_row("INIT-TIME", "First start time today", "Working_Code.py INIT-TIME")
        table.add_row("INIT-TIME_WHEN", "First start on specific day", "Working_Code.py INIT-TIME_WHEN dd/mm/yyyy")
        table.add_row("CLEAR-ALL", "Clear all data", "Working_Code.py CLEAR-ALL")
        
        console.print(Panel(table, title="Welcome to Working_Code ⚡", border_style="blue"))

if __name__ == "__main__":
    app()
