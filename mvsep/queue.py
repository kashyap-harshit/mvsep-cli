"""Batch directory scanner, sequential queue manager, and state persistence."""

import os
import sys
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from mvsep.client import MVSepClient
from mvsep.downloader import StemDownloader

console = Console()

SUPPORTED_AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".aiff", ".aif", ".wma"
}


def scan_audio_files(path: Union[str, Path], recursive: bool = False) -> List[Path]:
    """Discover all supported audio files in a directory or validate single file."""
    p = Path(path).resolve()
    if p.is_file():
        if p.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
            return [p]
        raise ValueError(f"File '{p.name}' is not a recognized audio format ({', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))})")

    if not p.is_dir():
        raise FileNotFoundError(f"Path not found: {path}")

    files: List[Path] = []
    if recursive:
        for root, _, filenames in os.walk(p):
            for fn in filenames:
                fp = Path(root) / fn
                if fp.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS and not fn.startswith("."):
                    files.append(fp)
    else:
        for item in sorted(p.iterdir()):
            if item.is_file() and item.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS and not item.name.startswith("."):
                files.append(item)

    return sorted(files)


def load_queue_state(state_file: Path) -> Dict[str, Any]:
    """Load state file if it exists."""
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"version": 1, "created_at": time.time(), "items": {}}


def save_queue_state(state_file: Path, state_data: Dict[str, Any]) -> None:
    """Save queue state file atomically."""
    temp_file = state_file.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
        temp_file.replace(state_file)
    except Exception:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def format_seconds(seconds: Optional[int]) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    if seconds is None or seconds < 0:
        return ""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"


class BatchQueueRunner:
    def __init__(
        self,
        client: MVSepClient,
        downloader: StemDownloader,
        sep_type: int = 63,
        output_format: int = 0,
        model_name: str = "",
        poll_interval: int = 5,
        stem_filter: Optional[List[str]] = None,
        state_file: Optional[Path] = None,
    ):
        self.client = client
        self.downloader = downloader
        self.sep_type = sep_type
        self.output_format = output_format
        self.model_name = model_name
        self.poll_interval = poll_interval
        self.stem_filter = stem_filter
        self.state_file = state_file

    def poll_until_done(self, task_hash: str, display_name: str) -> Dict[str, Any]:
        """Poll task until complete, showing live status, queue position, and ETA."""
        with Live(console=console, refresh_per_second=4, transient=True) as live:
            start_time = time.time()
            consecutive_errors = 0

            while True:
                try:
                    info = self.client.get_status(task_hash)
                    consecutive_errors = 0
                except Exception as e:
                    consecutive_errors += 1
                    if consecutive_errors > 10:
                        raise RuntimeError(f"Network error polling status: {e}")
                    time.sleep(self.poll_interval)
                    continue

                status = info.get("status", "waiting")
                stage = info.get("stage", "queue")
                queue_label = info.get("queue_label", "")
                eta = info.get("eta")

                # Build live status line
                txt = Text()
                txt.append("• ", style="bold cyan")
                txt.append(f"{display_name}: ", style="bold white")

                if status == "done":
                    txt.append("Separation complete! Preparing download...", style="bold green")
                    live.update(txt)
                    break
                elif status in ["failed", "error"]:
                    txt.append(f"Separation failed ({status})", style="bold red")
                    live.update(txt)
                    raise RuntimeError(f"Separation job {task_hash} failed on server.")
                else:
                    # Status is waiting, processing, etc.
                    stage_label = "In Queue" if stage == "queue" else "Separating Audio"
                    txt.append(f"[{stage_label}] ", style="bold yellow")
                    if queue_label:
                        txt.append(f"{queue_label} ", style="cyan")
                    if eta:
                        txt.append(f"(ETA: {format_seconds(eta)}) ", style="green")

                    elapsed = int(time.time() - start_time)
                    txt.append(f"[elapsed: {format_seconds(elapsed)}]", style="dim")

                    spinner = Spinner("dots", text=txt)
                    live.update(spinner)

                time.sleep(self.poll_interval)

        return info

    def run(self, files: List[Path], dry_run: bool = False) -> Dict[str, Any]:
        """Execute sequential processing for all files in the batch."""
        if not files:
            console.print("[yellow]No files to process.[/yellow]")
            return {"total": 0, "completed": 0, "failed": 0, "skipped": 0}

        # Resolve state file location (default to current directory .mvsep_queue.json)
        state_path = self.state_file or (Path.cwd() / ".mvsep_queue.json")
        state = load_queue_state(state_path)
        items = state.setdefault("items", {})

        total = len(files)
        console.print(f"\n[bold green]Found {total} audio file(s) for sequential separation.[/bold green]")
        if dry_run:
            for idx, fp in enumerate(files, 1):
                console.print(f"  [dim]{idx}/{total}[/dim] {fp.name}")
            console.print("[yellow]Dry-run mode: No files were uploaded or processed.[/yellow]")
            return {"total": total, "completed": 0, "failed": 0, "skipped": 0}

        stats = {"total": total, "completed": 0, "failed": 0, "skipped": 0}

        try:
            for idx, filepath in enumerate(files, 1):
                key = str(filepath.resolve())
                title = filepath.stem
                item_state = items.setdefault(key, {
                    "path": key,
                    "title": title,
                    "status": "pending",
                    "task_hash": None,
                    "downloaded": [],
                })

                # Check if already completed
                if item_state.get("status") == "completed":
                    # Verify output files still exist
                    existing = [Path(p) for p in item_state.get("downloaded", []) if Path(p).exists()]
                    if existing:
                        console.print(f"[{idx}/{total}] [dim]Skipping (already done): {filepath.name}[/dim]")
                        stats["skipped"] += 1
                        continue

                console.print(f"\n[bold cyan][{idx}/{total}] Processing: {filepath.name}[/bold cyan]")

                task_hash = item_state.get("task_hash")

                # Step 1: Upload / Create separation if not already uploaded
                if not task_hash:
                    console.print(f"  [dim]Uploading {filepath.name}...[/dim]")
                    try:
                        task_hash = self.client.create_separation(
                            filepath=str(filepath),
                            sep_type=self.sep_type,
                            output_format=self.output_format,
                        )
                        item_state["task_hash"] = task_hash
                        item_state["status"] = "uploaded"
                        save_queue_state(state_path, state)
                        console.print(f"  [green]✓ Uploaded. Task hash: {task_hash}[/green]")
                    except Exception as e:
                        console.print(f"  [bold red]✗ Upload failed: {e}[/bold red]")
                        item_state["status"] = "failed"
                        item_state["error"] = str(e)
                        save_queue_state(state_path, state)
                        stats["failed"] += 1
                        continue
                else:
                    console.print(f"  [cyan]Resuming existing task: {task_hash}[/cyan]")

                # Step 2: Poll status until separation is done
                try:
                    result_info = self.poll_until_done(task_hash, display_name=title)
                except Exception as e:
                    console.print(f"  [bold red]✗ Processing error: {e}[/bold red]")
                    item_state["status"] = "failed"
                    item_state["error"] = str(e)
                    save_queue_state(state_path, state)
                    stats["failed"] += 1
                    continue

                # Step 3: Download stems
                files_to_download = result_info.get("files", [])
                if not files_to_download:
                    console.print(f"  [bold yellow]No stem files found in completion response for {task_hash}[/bold yellow]")
                    item_state["status"] = "failed"
                    save_queue_state(state_path, state)
                    stats["failed"] += 1
                    continue

                console.print(f"  [bold green]Downloading {len(files_to_download)} stem(s)...[/bold green]")
                downloaded = self.downloader.download_stems(
                    files=files_to_download,
                    title=title,
                    task_hash=task_hash,
                    model=result_info.get("algorithm") or self.model_name,
                    stem_filter=self.stem_filter,
                )

                item_state["status"] = "completed"
                item_state["downloaded"] = [str(p) for p in downloaded]
                save_queue_state(state_path, state)
                stats["completed"] += 1
                console.print(f"  [bold green]✓ Done: {filepath.name}[/bold green]")

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Batch run interrupted by user. Progress saved.[/bold yellow]")
            console.print(f"[dim]You can resume anytime by re-running the command or 'mvsep resume'.[/dim]")
            save_queue_state(state_path, state)
            return stats

        return stats
