from __future__ import annotations

from rich.console import Console
from rich.theme import Theme
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn

_theme = Theme(
    {
        "info": "cyan",
        "warn": "yellow",
        "error": "bold red",
        "success": "bold green",
        "dim": "dim",
    }
)

console = Console(theme=_theme)
err_console = Console(theme=_theme, stderr=True)


def info(msg: str) -> None:
    console.print(f"[info]{{}}[/info]".format(msg))


def warn(msg: str) -> None:
    console.print(f"[warn]{{}}[/warn]".format(msg))


def error(msg: str) -> None:
    err_console.print(f"[error]{{}}[/error]".format(msg))


def success(msg: str) -> None:
    console.print(f"[success]{{}}[/success]".format(msg))


def make_progress(transient: bool = False) -> Progress:
    """Create a configured Rich Progress instance.

    Set transient=True to auto-clear after completion.
    """
    return Progress(
        SpinnerColumn(style="info"),
        TextColumn("[dim]{task.description}[/dim]"),
        BarColumn(bar_width=None),
        TextColumn("[cyan]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("|"),
        TimeRemainingColumn(),
        console=console,
        transient=transient,
    )
