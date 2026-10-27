"""Console display and rich rendering for mvsep-cli."""

from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()
err_console = Console(stderr=True)


def print_banner() -> None:
    text = Text("mvsep-cli", style="bold magenta")
    text.append(" - Audio separation & batch downloader (mvsep.com)", style="dim")
    console.print(text)


def print_models_table(models: List[Dict[str, Any]], query: Optional[str] = None) -> None:
    table = Table(
        title=f"MVSep Separation Models ({len(models)} available)" if not query else f"Models matching '{query}' ({len(models)} found)",
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("ID", justify="right", style="bold yellow", width=6)
    table.add_column("Model Name", style="bold white", min_width=25)
    table.add_column("Stems / Details", style="green")
    table.add_column("Description", style="dim")

    for m in models:
        mid = str(m.get("render_id", ""))
        name = m.get("name", "")

        # Extract stems in parentheses if present, e.g. "BS Roformer SW (vocals, bass, drums, ...)"
        stems = ""
        if "(" in name and ")" in name:
            parts = name.split("(", 1)
            main_name = parts[0].strip()
            stems = parts[1].rstrip(")").strip()
        else:
            main_name = name

        desc = m.get("short_description") or ""
        # Truncate long descriptions
        if len(desc) > 90:
            desc = desc[:87] + "..."

        table.add_row(mid, main_name, stems, desc)

    console.print(table)


def print_account_info(user_data: Dict[str, Any]) -> None:
    name = user_data.get("name", "Unknown")
    email = user_data.get("email", "Unknown")
    minutes = user_data.get("premium_minutes", 0)
    premium_enabled = "Yes" if user_data.get("premium_enabled") else "No"
    long_names = "Yes" if user_data.get("long_filenames_enabled") else "No"

    panel_content = Text()
    panel_content.append(f"Name:             ", style="bold cyan")
    panel_content.append(f"{name}\n")
    panel_content.append(f"Email:            ", style="bold cyan")
    panel_content.append(f"{email}\n")
    panel_content.append(f"Premium Credits:  ", style="bold cyan")
    panel_content.append(f"{minutes} minutes\n", style="bold green" if minutes > 0 else "yellow")
    panel_content.append(f"Premium Enabled:  ", style="bold cyan")
    panel_content.append(f"{premium_enabled}\n")
    panel_content.append(f"Long Filenames:   ", style="bold cyan")
    panel_content.append(f"{long_names}\n")

    console.print(Panel(panel_content, title="[bold]MVSep Account Info[/bold]", expand=False))
