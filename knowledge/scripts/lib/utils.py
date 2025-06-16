"""
Utility functions for Knowledge CLI
"""
import sys
from typing import List, Optional
import asyncio
from datetime import datetime


def print_success(message: str):
    """Print success message in green"""
    print(f"\033[92m✓ {message}\033[0m")


def print_error(message: str):
    """Print error message in red"""
    print(f"\033[91m✗ {message}\033[0m", file=sys.stderr)


def print_info(message: str):
    """Print info message in blue"""
    print(f"\033[94mℹ {message}\033[0m")


def print_warning(message: str):
    """Print warning message in yellow"""
    print(f"\033[93m⚠ {message}\033[0m")


def print_table(headers: List[str], rows: List[List[str]], title: Optional[str] = None):
    """Print a formatted table"""
    if title:
        print(f"\n{title}")
        print("=" * 80)
    
    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        width = len(header)
        for row in rows:
            if i < len(row):
                width = max(width, len(str(row[i])))
        col_widths.append(width + 2)
    
    # Print headers
    header_line = ""
    for i, header in enumerate(headers):
        header_line += header.ljust(col_widths[i])
    print(header_line)
    print("-" * sum(col_widths))
    
    # Print rows
    for row in rows:
        row_line = ""
        for i, cell in enumerate(row):
            if i < len(col_widths):
                row_line += str(cell).ljust(col_widths[i])
        print(row_line)
    
    print()


class ProgressBar:
    """Simple progress bar for async operations"""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()
        
    def update(self, count: int = 1):
        """Update progress"""
        self.current += count
        self._display()
    
    def _display(self):
        """Display progress bar"""
        if self.total == 0:
            percent = 100
        else:
            percent = (self.current / self.total) * 100
        
        bar_length = 40
        filled_length = int(bar_length * self.current // max(self.total, 1))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed if elapsed > 0 else 0
        
        sys.stdout.write(f'\r{self.description}: |{bar}| {percent:.1f}% ({self.current}/{self.total}) [{rate:.1f}/s]')
        sys.stdout.flush()
        
        if self.current >= self.total:
            print()  # New line when complete


def format_size(size_bytes: int) -> str:
    """Format byte size as human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"