<div align="center">

# 🎵 mvsep-cli

**The `yt-dlp` for [mvsep.com](https://mvsep.com)**

*Unattended sequential batch audio stem separation, real-time queue tracking, and stem downloads without the browser headaches.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Why mvsep-cli?](#-why-mvsep-cli-web-ui-vs-cli) •
[Installation](#-installation) •
[Quick Start](#-quick-start) •
[Usage Examples](#-usage-examples) •
[CLI Reference](#-cli-reference) •
[Supported Models](#-supported-models)

---

</div>

## 💡 Why mvsep-cli? (Web UI vs. CLI)

[mvsep.com](https://mvsep.com) is one of the best platforms for AI audio separation, offering over 120+ state-of-the-art models (BS Roformer, Demucs, MelBand Roformer, MDX23C). However, using the free web interface for collections or albums is exhausting:

- **Free accounts are restricted to 1 concurrent separation job.** On the website, this forces you to manually babysit your browser: upload song #1, stare at the queue, wait for processing, manually click download links for each stem, and only then upload song #2.
- **Browser Captchas:** The web submission form frequently triggers Cloudflare Turnstile anti-bot challenges.
- **Disorganized Downloads:** Stems get dumped directly into your browser's cluttered `Downloads/` directory with confusing names.

### ⚡ Feature Comparison

| Feature | MVSep Web UI | `mvsep-cli` |
| :--- | :---: | :---: |
| **Batch Folder Processing (Free Tier)** | ❌ Manual (sit & click one-by-one) | ✅ **Fully automated sequential queue** |
| **Captcha Challenges** | ⚠️ Cloudflare Turnstile blocks | ⚡ **Zero captchas** (uses official API) |
| **Interruption & Crash Recovery** | ❌ Start over from scratch | ✅ **Persistent state (`.mvsep_queue.json`)** |
| **Stem Downloads** | 🐌 Wait for zip or click 6+ buttons | 🚀 **Fast streaming with progress bars** |
| **Selective Stem Extraction** | ❌ Full zip download required | ✅ **`--stems vocals,instrumental`** |
| **Output Organization** | ❌ Flat clutter in `Downloads/` | ✅ **Automatic `output/<track>/<stem>.<ext>`** |
| **Anonymous Result Downloading** | ❌ Web browser navigation only | ✅ **Paste result URL & download instantly** |
| **Headless / Automation Support** | ❌ Requires browser GUI | ✅ **SSH, VPS, Docker, cron & scripts** |

> **Bottom Line:** Point `mvsep-cli` to an album folder, walk away or go to sleep, and return to an organized directory of high-quality separated stems.

---

## 🖥️ Terminal Experience

```
$ mvsep ./my_album/ --model 63 --format flac

Model: BS Roformer SW (vocals, bass, drums, guitar, piano, other) (ID: 63)
Output Format: flac | Destination: ./output

Found 8 audio file(s) for sequential separation.

[1/8] Processing: 01 - Nowhere Man.wav
  ✓ Uploaded. Task hash: 20261027133636-909ae99d45-nowhere-man.wav
  • Nowhere Man: [In Queue] Number 14 of 112 in the queue (ETA: 01m 24s) [elapsed: 00m 32s]
  Separation complete! Preparing download...
  Downloading 6 stem(s)...
  vocals.flac       ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 24.1 MB 4.2 MB/s 00:00
  bass.flac         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 18.5 MB 5.1 MB/s 00:00
  drums.flac        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 21.0 MB 4.8 MB/s 00:00
  guitar.flac       ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 19.3 MB 4.9 MB/s 00:00
  piano.flac        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 17.8 MB 4.6 MB/s 00:00
  other.flac        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 20.4 MB 5.0 MB/s 00:00
  ✓ Done: 01 - Nowhere Man.wav

[2/8] Processing: 02 - In My Life.wav
  ...
```

---

## 📦 Installation

### Option 1: Using `pip` or `pipx` (Recommended)

```bash
# Install with pip:
pip install mvsep-cli

# Or install in an isolated environment with pipx:
pipx install mvsep-cli
```

### Option 2: From Source

```bash
git clone https://github.com/your-username/mvsep-cli.git
cd mvsep-cli
pip install -e .
```

This installs both the `mvsep` and `mvsep-dl` commands in your PATH.

---

## 🚀 Quick Start

### 1. Authenticate (One-Time Setup)

MVSep offers free API tokens to all registered users (allowing 1 concurrent separation at a time). Authenticate in one step:

```bash
mvsep login
```
*Enter your mvsep.com account email and password. Your API token is fetched and securely stored in `~/.config/mvsep/config.json`.*

*(Alternatively, copy your API key from [mvsep.com/api](https://mvsep.com/api) and run `mvsep config set api_token YOUR_TOKEN` or set `export MVSEP_API_TOKEN="YOUR_TOKEN"`).*

Verify your account status and credits anytime:
```bash
mvsep whoami
```

### 2. Batch Separate a Folder of Songs

Point `mvsep` to any directory containing audio files (`.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`, etc.):

```bash
mvsep ./music/
```

`mvsep-cli` will sequentially process every track one-by-one and download stems into `./output/<track_title>/`.

### 3. Download from an Existing Result URL

If a separation was already created on the website, you can download all stems directly and anonymously (no login needed):

```bash
mvsep https://mvsep.com/result/20261027133636-909ae99d45-nowhere-man.wav
```

---

## 🛠️ Usage Examples

### Filter Specific Stems
Download only vocals and instrumental, ignoring drums, bass, and piano:
```bash
mvsep ./my_songs/ --stems vocals,instrumental
```

### Choose an Audio Separation Model
By default, `mvsep-cli` uses **BS Roformer SW** (ID `63`, 6-stem). You can pick any of the 120+ models by ID or name substring:
```bash
# Use Demucs v4 (4 stems: vocals, drums, bass, other):
mvsep song.wav --model 20

# Search models by name:
mvsep song.wav --model "MelBand Roformer"
```

### Choose Output Audio Format
Support for MP3 (320 kbps), 16-bit WAV, or lossless FLAC:
```bash
mvsep ./album/ --format flac
```

### Custom Output Directory & Naming
Organize your stems with custom path templates:
```bash
mvsep ./album/ -o ./stems/ --output-template "%(title)s - %(stem)s.%(ext)s"
```

Available template variables:
- `%(title)s` - Original track title (without extension)
- `%(stem)s` - Stem name (`vocals`, `drums`, `bass`, `guitar`, `piano`, etc.)
- `%(ext)s` - File extension (`mp3`, `wav`, `flac`)
- `%(id)s` - MVSep task hash
- `%(model)s` - Model name

### Preview Files with Dry-Run
Check what files will be detected without uploading:
```bash
mvsep ./my_songs/ --dry-run
```

### Search and List Available AI Models
```bash
# List all 124+ separation algorithms:
mvsep --list-models

# Search for specific architectures:
mvsep --list-models roformer
mvsep --list-models demucs
```

### Resume an Interrupted Batch
If you cancel a batch with `Ctrl+C` or lose internet connection, rerun the same command or:
```bash
mvsep resume ./my_songs/
```
It reads `.mvsep_queue.json`, checks which songs were already downloaded, and seamlessly continues with the remaining files.

---

## 📖 CLI Reference

```
usage: mvsep [-h] [-v] [-m MODEL] [-f FORMAT] [-o OUTPUT]
             [--output-template TEMPLATE] [-s STEMS] [-r]
             [-L [QUERY]] [--dry-run] [--token TOKEN]
             [--poll-interval SECONDS]
             [inputs ...] {login,whoami,models,config,resume} ...

Positional Arguments:
  inputs                     Audio files, directories, or result URLs

Options:
  -h, --help                 Show help message and exit
  -v, --version              Show program version
  -m, --model MODEL          Model ID or name (default: 63 - BS Roformer SW)
  -f, --format FORMAT        Output format: mp3 (default), wav, flac
  -o, --output DIR           Output destination folder (default: ./output)
  --output-template TEMPLATE Path template (default: %(title)s/%(stem)s.%(ext)s)
  -s, --stems STEMS          Filter comma-separated stems (e.g. vocals,drums)
  -r, --recursive            Recursively scan directories for audio files
  -L, --list-models [QUERY]  List or search available models
  --dry-run                  Scan files and print plan without uploading
  --token TOKEN              Override MVSep API token
  --poll-interval SECONDS    Polling interval in seconds (default: 5)

Subcommands:
  login                      Log in to mvsep.com to save your API token
  whoami                     Display current account info and credits
  models [QUERY]             Search and view separation models
  config {get,set,path}      Manage configuration settings
  resume [DIR]               Resume an interrupted batch run
```

---

## 🧠 Popular Separation Models

MVSep hosts the world's leading separation models. Run `mvsep --list-models` to explore them all:

| ID | Model Name | Stems Produced | Best For |
| :---: | :--- | :--- | :--- |
| **63** | **BS Roformer SW** *(Default)* | Vocals, Bass, Drums, Guitar, Piano, Other | Ultimate all-in-one 6-stem separation |
| **20** | **Demucs4 HT** | Vocals, Drums, Bass, Other | Balanced, high-fidelity 4-stem extraction |
| **40** | **BS Roformer** | Vocals, Instrumental | Pristine isolated vocal extraction |
| **48** | **MelBand Roformer** | Vocals, Instrumental | Top-tier 2-stem vocal/backing isolation |
| **25** | **MDX23C** | Vocals, Instrumental | Fast, competitive 2-stem separation |
| **30** | **Ensemble All-In** | Up to 8 stems | Multi-model consensus ensemble |

---

## ⚙️ Configuration File

Configuration is saved in `~/.config/mvsep/config.json` (or `%APPDATA%\mvsep\config.json` on Windows):

```json
{
  "api_token": "your_api_token_here",
  "default_model": 63,
  "default_format": "mp3",
  "output_dir": "./output",
  "output_template": "%(title)s/%(stem)s.%(ext)s",
  "poll_interval": 5
}
```

Manage configuration directly from the CLI:
```bash
mvsep config get
mvsep config set default_format flac
mvsep config set default_model 20
```

---

## ❓ Frequently Asked Questions

<details>
<summary><b>Is an MVSep account required?</b></summary>
To upload files and create new separations, yes. Free accounts come with an API key with 1 concurrent job limit. To download stems from existing result URLs (e.g. <code>mvsep https://mvsep.com/result/...</code>), no account or token is required.
</details>

<details>
<summary><b>How does mvsep-cli handle rate limits?</b></summary>
Free accounts have a limit of 1 concurrent separation job. <code>mvsep-cli</code> honors this by waiting for each separation to finish and download before dispatching the next track. If a rate limit (HTTP 429) occurs, it automatically applies backoff retry intervals.
</details>

<details>
<summary><b>Can I run this on a headless Linux server or VPS?</b></summary>
Yes! <code>mvsep-cli</code> has zero GUI or browser automation dependencies. It runs smoothly on minimal Linux distributions, Docker containers, and SSH sessions.
</details>

<details>
<summary><b>Where are my separated audio files saved?</b></summary>
By default, files are saved in <code>./output/<track_title>/<stem>.<ext></code>. You can customize the folder with <code>-o /path/to/folder</code> and the file naming pattern with <code>--output-template</code>.
</details>

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check out [CONTRIBUTING.md](CONTRIBUTING.md) and open an issue or pull request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

*Disclaimer: `mvsep-cli` is an independent open-source tool and is not officially affiliated with or endorsed by mvsep.com.*
