import os
from datetime import datetime

def log_message(message, level="INFO"):
    """Prints a formatted log message to the console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def format_date_for_api(date_str):
    """Converts DD-MM-YYYY to DDMMYYYY for XTS API."""
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return dt.strftime("%d%m%Y")
    except ValueError:
        log_message(f"Invalid date format: {date_str}. Expected DD-MM-YYYY", "ERROR")
        return None

def clear_screen():
    """Clears the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Prints a professional banner for the client demo."""
    banner = """
    ================================================
    XTS API Backtesting Project - Time Based Strategy
    ================================================
    """
    print(banner)
