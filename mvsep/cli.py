"""Command-line interface for mvsep-cli."""

import os
import sys
import argparse
import getpass
from pathlib import Path
from typing import List, Optional

from mvsep import __version__
from mvsep.config import (
    load_config,
    save_config,
    get_token,
    set_token,
    get_config_path,
)
from mvsep.models import (
    get_algorithms,
    resolve_model,
    parse_format,
    CODE_TO_FORMAT,
)
from mvsep.client import MVSepClient
from mvsep.downloader import StemDownloader
from mvsep.queue import (
    scan_audio_files,
    BatchQueueRunner,
    load_queue_state,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from mvsep.display import (
    console,
    err_console,
    print_banner,
    print_models_table,
    print_account_info,
)


def handle_login(args: argparse.Namespace) -> int:
    """Perform interactive login and store API token."""
    print_banner()
    console.print("\n[bold]Log in to MVSep[/bold] (https://mvsep.com)")
    console.print("[dim]Your credentials are used to obtain your API key via https://mvsep.com/api/app/login.[/dim]\n")

    email = args.email or input("Email: ").strip()
    if not email:
        console.print("[red]Email cannot be empty.[/red]")
        return 1

    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
    if not password:
        console.print("[red]Password cannot be empty.[/red]")
        return 1

    client = MVSepClient()
    try:
        console.print("[dim]Authenticating...[/dim]")
        user_data = client.login(email=email, password=password)
        token = user_data.get("api_token")
        if token:
            set_token(token)
            console.print(f"[bold green]✓ Successfully logged in as {user_data.get('name', email)}![/bold green]")
            console.print(f"[dim]API token saved to {get_config_path()}[/dim]")
            print_account_info(user_data)
            return 0
        else:
            console.print("[red]Login succeeded but no API token was returned.[/red]")
            return 1
    except Exception as e:
        console.print(f"[bold red]Login failed: {e}[/bold red]")
        return 1


def handle_whoami(args: argparse.Namespace) -> int:
    """Display authenticated user info and credits."""
    token = get_token(args.token)
    if not token:
        console.print("[yellow]Not logged in. No API token found.[/yellow]")
        console.print("[dim]Run 'mvsep login' or set MVSEP_API_TOKEN to authenticate.[/dim]")
        return 1

    client = MVSepClient(api_token=token)
    try:
        user_data = client.get_user_info()
        print_account_info(user_data)
        return 0
    except Exception as e:
        console.print(f"[bold red]Failed to fetch account info: {e}[/bold red]")
        return 1


def handle_list_models(query: Optional[str] = None) -> int:
    """Display available algorithms table."""
    try:
        algorithms = get_algorithms()
        if query:
            q = query.strip().lower()
            filtered = []
            for alg in algorithms:
                name = alg.get("name", "").lower()
                desc = alg.get("short_description", "").lower()
                mid = str(alg.get("render_id", ""))
                if q == mid or q in name or q in desc:
                    filtered.append(alg)
            if not filtered:
                console.print(f"[yellow]No models found matching '{query}'.[/yellow]")
                return 1
            print_models_table(filtered, query=query)
        else:
            print_models_table(algorithms)
        return 0
    except Exception as e:
        console.print(f"[bold red]Error fetching models: {e}[/bold red]")
        return 1


def handle_config(args: argparse.Namespace) -> int:
    """Manage configuration settings."""
    if args.action == "path":
        console.print(str(get_config_path()))
        return 0
    elif args.action == "get":
        cfg = load_config()
        if args.key:
            val = cfg.get(args.key)
            if val is not None:
                console.print(str(val))
            else:
                console.print(f"[yellow]Key '{args.key}' not found in configuration.[/yellow]")
                return 1
        else:
            for k, v in sorted(cfg.items()):
                # Mask token
                if k == "api_token" and v:
                    display_v = v[:4] + "..." + v[-4:] if len(v) > 8 else "***"
                else:
                    display_v = v
                console.print(f"[cyan]{k}[/cyan] = {display_v}")
        return 0
    elif args.action == "set":
        if not args.key or args.val is None:
            console.print("[red]Usage: mvsep config set <key> <value>[/red]")
            return 1
        key = args.key
        val: Any = args.val
        if key in ["default_model", "poll_interval"]:
            try:
                val = int(val)
            except ValueError:
                pass
        save_config({key: val})
        console.print(f"[green]✓ Set {key} = {val}[/green]")
        return 0
    return 0


def handle_download_url(
    client: MVSepClient,
    downloader: StemDownloader,
    target: str,
    stem_filter: Optional[List[str]] = None,
    poll_interval: int = 5,
) -> int:
    """Handle downloading an existing separation URL or hash."""
    task_hash = client.extract_hash(target)
    console.print(f"[bold cyan]Connecting to MVSep task: {task_hash}[/bold cyan]")

    runner = BatchQueueRunner(
        client=client,
        downloader=downloader,
        poll_interval=poll_interval,
        stem_filter=stem_filter,
    )

    try:
        info = runner.poll_until_done(task_hash=task_hash, display_name=task_hash)
        files = info.get("files", [])
        if not files:
            console.print("[bold red]No stems available for this separation task.[/bold red]")
            return 1

        title = task_hash
        input_file = info.get("input_file", {})
        if input_file and input_file.get("download"):
            title = Path(input_file["download"]).stem

        console.print(f"[bold green]Downloading {len(files)} stem(s) for '{title}'...[/bold green]")
        downloaded = downloader.download_stems(
            files=files,
            title=title,
            task_hash=task_hash,
            model=info.get("algorithm", ""),
            stem_filter=stem_filter,
        )
        console.print(f"[bold green]✓ Successfully downloaded {len(downloaded)} stem(s) to {downloader.output_dir}[/bold green]")
        return 0
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        return 1


def create_main_parser(config: dict) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mvsep",
        description="yt-dlp style CLI for mvsep.com audio separation & batch downloads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Batch process a folder of audio files one-by-one:
  mvsep ./my_songs/

  # Separate a single file with BS Roformer:
  mvsep song.wav --model 63 --format mp3

  # Download from an existing separation result URL or hash:
  mvsep https://mvsep.com/result/20261027133636-909ae99d45-nowhere-man.wav

  # List all available AI models:
  mvsep --list-models

  # Search models:
  mvsep --list-models roformer

  # Download only vocal and instrumental stems:
  mvsep ./music/ --stems vocals,instrumental

  # Log in to save your free API token:
  mvsep login
        """,
    )

    parser.add_argument("inputs", nargs="*", help="Audio files, directories, or mvsep.com result URLs")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-m", "--model", default=config.get("default_model", 63), help="Separation model ID or name (default: 63)")
    parser.add_argument("-f", "--format", default=config.get("default_format", "mp3"), help="Output format: mp3, wav, flac (default: mp3)")
    parser.add_argument("-o", "--output", default=config.get("output_dir", "./output"), help="Output directory (default: ./output)")
    parser.add_argument("--output-template", default=config.get("output_template", "%(title)s/%(stem)s.%(ext)s"), help="Output path template (default: %(title)s/%(stem)s.%(ext)s)")
    parser.add_argument("-s", "--stems", help="Comma-separated stems to download (e.g. vocals,instrumental)")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively scan directories for audio files")
    parser.add_argument("-L", "--list-models", nargs="?", const="", help="List or search available models")
    parser.add_argument("--dry-run", action="store_true", help="Scan and list files without uploading")
    parser.add_argument("--token", help="MVSep API token (overrides config)")
    parser.add_argument("--poll-interval", type=int, default=config.get("poll_interval", 5), help="Status poll interval in seconds (default: 5)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    config = load_config()

    SUBCOMMANDS = {"login", "whoami", "models", "config", "resume"}
    if argv and argv[0] in SUBCOMMANDS:
        sub_name = argv[0]
        sub_args = argv[1:]

        if sub_name == "login":
            sub_p = argparse.ArgumentParser(prog="mvsep login", description="Log in to mvsep.com")
            sub_p.add_argument("-e", "--email", help="Account email")
            sub_p.add_argument("-p", "--password", help="Account password")
            p_args = sub_p.parse_args(sub_args)
            return handle_login(p_args)

        elif sub_name == "whoami":
            sub_p = argparse.ArgumentParser(prog="mvsep whoami", description="Display account info and credits")
            sub_p.add_argument("--token", help="MVSep API token")
            p_args = sub_p.parse_args(sub_args)
            return handle_whoami(p_args)

        elif sub_name == "models":
            sub_p = argparse.ArgumentParser(prog="mvsep models", description="Search models")
            sub_p.add_argument("query", nargs="?", default="", help="Search query")
            p_args = sub_p.parse_args(sub_args)
            return handle_list_models(p_args.query)

        elif sub_name == "config":
            sub_p = argparse.ArgumentParser(prog="mvsep config", description="View or set configuration")
            sub_p.add_argument("action", choices=["get", "set", "path"], help="Action")
            sub_p.add_argument("key", nargs="?", help="Key")
            sub_p.add_argument("val", nargs="?", help="Value")
            p_args = sub_p.parse_args(sub_args)
            return handle_config(p_args)

        elif sub_name == "resume":
            sub_p = argparse.ArgumentParser(prog="mvsep resume", description="Resume interrupted batch run")
            sub_p.add_argument("path", nargs="?", default=".", help="Directory")
            p_args = sub_p.parse_args(sub_args)
            argv = [p_args.path]

    parser = create_main_parser(config)
    args = parser.parse_args(argv)

    # Handle --list-models flag
    if args.list_models is not None:
        return handle_list_models(args.list_models)

    if not args.inputs:
        parser.print_help()
        return 0

    # Parse format code
    try:
        format_code = parse_format(args.format)
    except ValueError as e:
        console.print(f"[bold red]{e}[/bold red]")
        return 1

    # Resolve model
    try:
        model_obj = resolve_model(args.model)
        sep_type = model_obj["render_id"]
        model_name = model_obj.get("name", str(sep_type))
    except Exception as e:
        console.print(f"[bold red]{e}[/bold red]")
        return 1

    # Parse stems filter
    stem_filter = [s.strip() for s in args.stems.split(",")] if args.stems else None

    # Prepare client and downloader
    token = get_token(args.token)
    client = MVSepClient(api_token=token)
    downloader = StemDownloader(output_dir=args.output, template=args.output_template)

    # Check if first input is a URL or hash
    first_arg = args.inputs[0].strip()
    if (
        first_arg.startswith("http://")
        or first_arg.startswith("https://")
        or (len(first_arg) > 30 and "-" in first_arg and "." in first_arg and not Path(first_arg).exists())
    ):
        if "mvsep.com/result/" in first_arg or not first_arg.startswith("http"):
            return handle_download_url(
                client=client,
                downloader=downloader,
                target=first_arg,
                stem_filter=stem_filter,
                poll_interval=args.poll_interval,
            )

    # Batch or file inputs
    # For uploading files, API token is needed
    if not token and not args.dry_run:
        console.print("[bold yellow]Warning: No MVSep API token found.[/bold yellow]")
        console.print(
            "Free accounts have an API token allowing 1 concurrent separation job at a time.\n"
            "Please log in or provide your token:\n"
            "  1. Run [bold cyan]mvsep login[/bold cyan] with your mvsep.com account credentials\n"
            "  2. Or get your token from https://mvsep.com/api and run: [bold cyan]mvsep config set api_token <TOKEN>[/bold cyan]\n"
            "  3. Or pass [bold cyan]--token <TOKEN>[/bold cyan] / set [bold cyan]MVSEP_API_TOKEN[/bold cyan] in your environment.\n"
        )
        return 1

    # Discover files across all inputs
    all_files: List[Path] = []
    for inp in args.inputs:
        try:
            files = scan_audio_files(inp, recursive=args.recursive)
            all_files.extend(files)
        except Exception as e:
            console.print(f"[bold red]Error reading input '{inp}': {e}[/bold red]")
            return 1

    # Remove duplicates preserving order
    seen = set()
    unique_files: List[Path] = []
    for f in all_files:
        resolved = str(f.resolve())
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(f)

    if not unique_files:
        console.print(f"[yellow]No audio files ({', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}) found in specified inputs.[/yellow]")
        return 0

    console.print(f"[bold]Model:[/bold] {model_name} (ID: {sep_type})")
    console.print(f"[bold]Output Format:[/bold] {CODE_TO_FORMAT.get(format_code, 'mp3')} | [bold]Destination:[/bold] {args.output}")

    runner = BatchQueueRunner(
        client=client,
        downloader=downloader,
        sep_type=sep_type,
        output_format=format_code,
        model_name=model_name,
        poll_interval=args.poll_interval,
        stem_filter=stem_filter,
    )

    stats = runner.run(unique_files, dry_run=args.dry_run)

    # Summary
    console.print("\n[bold]Batch Summary:[/bold]")
    console.print(f"  • Total files:     {stats['total']}")
    console.print(f"  • Completed:       [green]{stats['completed']}[/green]")
    console.print(f"  • Skipped (prior): [dim]{stats['skipped']}[/dim]")
    console.print(f"  • Failed:          [red]{stats['failed']}[/red]" if stats['failed'] > 0 else f"  • Failed:          0")

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
