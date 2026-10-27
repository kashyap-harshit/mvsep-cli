# mvsep-cli (`mvsep` / `mvsep-dl`)

A command-line tool inspired by `yt-dlp` for [mvsep.com](https://mvsep.com) that automates audio stem separation, sequential batch folder processing for free accounts, queue/ETA tracking, and stem downloads.

---

## Features

- **Sequential Batch Folder Processing**: Point to any folder containing audio files (`.wav`, `.mp3`, `.flac`, `.m4a`, etc.) and `mvsep` separates them one-by-one to adhere to the free account limit (1 concurrent job).
- **Interruption & Resume Protection**: Tracks batch progress in a state file (`.mvsep_queue.json`). If interrupted by `Ctrl+C` or a network drop, rerun `mvsep <folder>` or `mvsep resume` to continue right where you left off without re-uploading completed tracks.
- **Direct Separation Result Downloader**: Pass any result URL (e.g. `https://mvsep.com/result/<hash>`) or task hash to download all stems anonymously without needing an account or API token.
- **Live Queue & ETA Tracking**: Displays real-time queue position (e.g., *"Number 22 of 112 in queue"*) and countdown estimates in terminal.
- **120+ Separation Models**: Supports all models available on MVSep (BS Roformer, Demucs v4, MelBand Roformer, MDX23C, etc.) with fuzzy search via `mvsep --list-models`.
- **Flexible Stem Filtering**: Download only the stems you need (e.g. `--stems vocals,instrumental` or `--stems vocals`).
- **Rich Output Formatting**: Beautiful progress bars for downloads with speed, ETA, and customizable path templates (`%(title)s/%(stem)s.%(ext)s`).

---

## Installation

```bash
# In the repository directory:
pip install -e .
```

This installs both `mvsep` and `mvsep-dl` commands.

---

## Quick Start

### 1. Authenticate (Free Account)

Free accounts on [mvsep.com](https://mvsep.com) have an API token (with 1 concurrent job limit). You can save your token in one command:

```bash
# Option A: Interactive login with your MVSep email and password
mvsep login

# Option B: Manually save your API key (found at https://mvsep.com/api)
mvsep config set api_token <YOUR_TOKEN>

# Option C: Environment variable
export MVSEP_API_TOKEN="your_token_here"
```

Check your account and remaining credits anytime:
```bash
mvsep whoami
```

---

## Usage Examples

### Batch Process a Folder of Audio Files (One-by-One)

Point `mvsep` to a directory. It will scan for all supported audio files and process each sequentially:

```bash
# Process all audio files in a folder with default model (BS Roformer SW 6-stem):
mvsep ./my_album/

# Process with a specific model (e.g., Demucs 4-stem):
mvsep ./my_album/ --model 20

# Output as 16-bit FLAC instead of MP3:
mvsep ./my_album/ --format flac

# Scan subfolders recursively:
mvsep ./music/ --recursive
```

### Download from an Existing Separation URL or Hash

If you or someone else already ran a separation on the website:

```bash
# Download all stems:
mvsep https://mvsep.com/result/20261027133636-909ae99d45-nowhere-man.wav

# Download only vocals stem:
mvsep https://mvsep.com/result/20261027133636-909ae99d45-nowhere-man.wav --stems vocals
```

### Separate a Single Audio File

```bash
mvsep "song.wav" --model "BS Roformer" --format wav
```

### List and Search Separation Models

```bash
# List all 124+ available models:
mvsep --list-models

# Search models by name (e.g., Roformer, Demucs, MDX):
mvsep --list-models roformer
```

---

## CLI Reference

```
usage: mvsep [-h] [-v] [-m MODEL] [-f FORMAT] [-o OUTPUT]
             [--output-template OUTPUT_TEMPLATE] [-s STEMS] [-r]
             [-L [LIST_MODELS]] [--dry-run] [--token TOKEN]
             [--poll-interval POLL_INTERVAL]
             [inputs ...] {login,whoami,models,config,resume} ...

Options:
  -m, --model MODEL          Model ID or name substring (default: 63 - BS Roformer SW)
  -f, --format FORMAT        Output format: mp3 (default), wav, flac
  -o, --output DIR           Output destination folder (default: ./output)
  --output-template TEMPLATE Output path template (default: %(title)s/%(stem)s.%(ext)s)
  -s, --stems STEMS          Comma-separated stem filters (e.g. vocals,instrumental)
  -r, --recursive            Recursively search input directories for audio files
  -L, --list-models [QUERY]  List or search available models
  --dry-run                  Scan and show files without uploading
  --token TOKEN              MVSep API token override
  --poll-interval SECS       Status poll interval in seconds (default: 5)

Subcommands:
  login                      Log in to mvsep.com to save your API token
  whoami                     Display current account info and credits
  models [QUERY]             Search and view separation models
  config {get,set,path}      Manage configuration settings
  resume [DIR]               Resume an interrupted batch run
```

---

## Output Path Templating

You can customize where and how stems are saved using `--output-template`:

- `%(title)s` - Input audio file title (without extension)
- `%(stem)s` - Stem identifier (`vocals`, `drums`, `bass`, `guitar`, `piano`, `instrum`, `other`)
- `%(ext)s` - Output file extension (`mp3`, `wav`, `flac`)
- `%(id)s` - MVSep separation task hash
- `%(model)s` - Name of the separation model used

Example:
```bash
mvsep ./songs/ --output-template "%(title)s - %(stem)s.%(ext)s"
```

---

## License

MIT
