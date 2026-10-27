"""Download manager with Rich progress bars and path formatting."""

import os
import re
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.console import Console

console = Console()


def extract_stem_name(filename: str) -> str:
    """Extract standard stem identifier from filename (e.g. vocals, drums, bass, etc.)."""
    base = os.path.splitext(filename)[0]
    # Common separators
    for part in reversed(base.split("_")):
        cleaned = part.strip().lower()
        if cleaned in ["vocals", "instrum", "instrumental", "bass", "drums", "guitar", "piano", "other", "lead", "back"]:
            return cleaned
    return base


def format_output_path(
    template: str,
    output_dir: Path,
    title: str,
    stem: str,
    ext: str,
    task_hash: str = "",
    model: str = "",
) -> Path:
    """Resolve output template like %(title)s/%(stem)s.%(ext)s."""
    ext = ext.lstrip(".")
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title).strip()
    safe_stem = re.sub(r'[\\/*?:"<>|]', "_", stem).strip()

    mapping = {
        "%(title)s": safe_title,
        "%(stem)s": safe_stem,
        "%(ext)s": ext,
        "%(id)s": task_hash,
        "%(model)s": re.sub(r'[\\/*?:"<>|]', "_", model),
    }

    resolved = template
    for key, val in mapping.items():
        resolved = resolved.replace(key, val)

    full_path = output_dir / resolved
    return full_path


class StemDownloader:
    def __init__(self, output_dir: Union[str, Path] = "./output", template: str = "%(title)s/%(stem)s.%(ext)s"):
        self.output_dir = Path(output_dir)
        self.template = template

    def filter_files(self, files: List[Dict[str, Any]], stem_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Filter stems by name if specified."""
        if not stem_filter:
            return files

        normalized_filter = [s.strip().lower() for s in stem_filter if s.strip()]
        if not normalized_filter:
            return files

        matched = []
        for f in files:
            fname = f.get("download") or f.get("url", "")
            stem = extract_stem_name(fname)
            for target in normalized_filter:
                if target in stem or target in fname.lower():
                    matched.append(f)
                    break
        return matched

    def download_file(self, url: str, target_path: Path, progress: Optional[Progress] = None, task_id: Optional[Any] = None) -> bool:
        """Download a single file directly with streaming and progress updates."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        headers = {"User-Agent": "mvsep-cli/0.1"}

        resp = requests.get(url, headers=headers, stream=True, timeout=(10, 60))
        resp.raise_for_status()

        total_bytes = int(resp.headers.get("content-length", 0))
        if progress and task_id is not None and total_bytes > 0:
            progress.update(task_id, total=total_bytes)

        temp_path = target_path.with_suffix(target_path.suffix + ".part")
        try:
            with open(temp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        if progress and task_id is not None:
                            progress.update(task_id, advance=len(chunk))
            # Move part file to final file
            if temp_path.exists():
                temp_path.replace(target_path)
            return True
        except Exception:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise

    def download_stems(
        self,
        files: List[Dict[str, Any]],
        title: str,
        task_hash: str = "",
        model: str = "",
        stem_filter: Optional[List[str]] = None,
    ) -> List[Path]:
        """Download all selected stem files with a rich progress bar."""
        to_download = self.filter_files(files, stem_filter)
        if not to_download:
            console.print("[yellow]No files matched the stem filter.[/yellow]")
            return []

        downloaded_paths = []
        with Progress(
            TextColumn("[bold cyan]{task.fields[filename]}", justify="left"),
            BarColumn(bar_width=35),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            for item in to_download:
                url = item.get("url")
                filename = item.get("download") or os.path.basename(url)
                stem = extract_stem_name(filename)
                ext = os.path.splitext(filename)[1] or ".mp3"

                dest_path = format_output_path(
                    template=self.template,
                    output_dir=self.output_dir,
                    title=title,
                    stem=stem,
                    ext=ext,
                    task_hash=task_hash,
                    model=model,
                )

                if dest_path.exists() and dest_path.stat().st_size > 0:
                    console.print(f"[dim]• Already exists: {dest_path}[/dim]")
                    downloaded_paths.append(dest_path)
                    continue

                task_id = progress.add_task("download", filename=filename, total=None)
                try:
                    self.download_file(url, dest_path, progress=progress, task_id=task_id)
                    downloaded_paths.append(dest_path)
                except Exception as e:
                    console.print(f"[bold red]Failed to download {filename}: {e}[/bold red]")
                finally:
                    progress.remove_task(task_id)

        return downloaded_paths
