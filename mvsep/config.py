"""Configuration management for mvsep-cli."""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mvsep"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_token": "",
    "default_model": 63,          # BS Roformer SW (6 stems)
    "default_format": "mp3",       # mp3, wav, flac
    "output_dir": "./output",
    "output_template": "%(title)s/%(stem)s.%(ext)s",
    "poll_interval": 5,            # seconds between status checks
}


def get_config_path() -> Path:
    return CONFIG_FILE


def load_config() -> Dict[str, Any]:
    """Load configuration from file and environment variables."""
    config = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass

    # Environment variables override config file
    env_token = os.environ.get("MVSEP_API_TOKEN")
    if env_token:
        config["api_token"] = env_token

    env_model = os.environ.get("MVSEP_DEFAULT_MODEL")
    if env_model:
        try:
            config["default_model"] = int(env_model)
        except ValueError:
            config["default_model"] = env_model

    env_format = os.environ.get("MVSEP_DEFAULT_FORMAT")
    if env_format:
        config["default_format"] = env_format

    env_output = os.environ.get("MVSEP_OUTPUT_DIR")
    if env_output:
        config["output_dir"] = env_output

    return config


def save_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Save or update configuration file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current = load_config()
    current.update(updates)

    # Don't persist environment overrides if different
    to_save = dict(current)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, indent=2)

    return current


def get_token(cli_token: Optional[str] = None) -> Optional[str]:
    """Retrieve API token from CLI arg, environment, or config file."""
    if cli_token:
        return cli_token
    config = load_config()
    token = config.get("api_token")
    return token.strip() if token else None


def set_token(token: str) -> None:
    """Store API token in configuration."""
    save_config({"api_token": token.strip()})
