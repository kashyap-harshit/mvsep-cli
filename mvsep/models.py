"""Algorithm models and format registry for mvsep-cli."""

import os
import json
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "mvsep"
ALGORITHMS_CACHE = CACHE_DIR / "algorithms.json"

# Output format mappings for MVSep API
# 0 = mp3 (320kbps), 1 = wav (16-bit), 2 = flac (16-bit)
FORMAT_TO_CODE = {
    "mp3": 0,
    "wav": 1,
    "flac": 2,
}

CODE_TO_FORMAT = {
    0: "mp3",
    1: "wav",
    2: "flac",
}

# Popular fallback algorithms in case offline or API down
FALLBACK_ALGORITHMS = [
    {
        "render_id": 63,
        "name": "BS Roformer SW (vocals, bass, drums, guitar, piano, other)",
        "algorithm_group_id": 22,
        "short_description": "BS Roformer SW model, which generates 6 stems at once with superior quality.",
        "algorithm_fields": []
    },
    {
        "render_id": 20,
        "name": "Demucs4 HT (vocals, drums, bass, other)",
        "algorithm_group_id": 22,
        "short_description": "Demucs v4 Hybrid Transformer for 4 stems separation.",
        "algorithm_fields": [{"name": "add_opt1", "label": "Model type"}]
    },
    {
        "render_id": 26,
        "name": "Ensemble (vocals, instrum)",
        "algorithm_group_id": 23,
        "short_description": "Ensemble model combining best vocal/instrumental separation models.",
        "algorithm_fields": [{"name": "add_opt1", "label": "Model 1"}, {"name": "add_opt2", "label": "Model 2"}]
    },
    {
        "render_id": 40,
        "name": "BS Roformer (vocals, instrumental)",
        "algorithm_group_id": 21,
        "short_description": "Band-Split Roformer for vocal extraction.",
        "algorithm_fields": []
    },
    {
        "render_id": 48,
        "name": "MelBand Roformer (vocals, instrumental)",
        "algorithm_group_id": 21,
        "short_description": "MelBand Roformer model for 2 stems (vocals and instrumental).",
        "algorithm_fields": []
    },
    {
        "render_id": 25,
        "name": "MDX23C (vocals, instrumental)",
        "algorithm_group_id": 21,
        "short_description": "MDX-Net 2023 Challenge winner.",
        "algorithm_fields": []
    },
    {
        "render_id": 30,
        "name": "Ensemble All-In (vocals, bass, drums, piano, guitar, lead/back vocals, other)",
        "algorithm_group_id": 23,
        "short_description": "Large ensemble generating up to 8 stems.",
        "algorithm_fields": []
    }
]


def parse_format(fmt: Union[str, int]) -> int:
    """Normalize format name to API code integer."""
    if isinstance(fmt, int):
        if fmt in CODE_TO_FORMAT:
            return fmt
        raise ValueError(f"Unknown format code: {fmt}. Valid codes are 0 (mp3), 1 (wav), 2 (flac)")

    cleaned = fmt.lower().strip().lstrip(".")
    if cleaned in FORMAT_TO_CODE:
        return FORMAT_TO_CODE[cleaned]
    try:
        code = int(cleaned)
        if code in CODE_TO_FORMAT:
            return code
    except ValueError:
        pass
    raise ValueError(f"Unknown audio format '{fmt}'. Supported: mp3, wav, flac")


def get_algorithms(force_refresh: bool = False, timeout: int = 10) -> List[Dict[str, Any]]:
    """Retrieve full list of algorithms, caching locally."""
    if not force_refresh and ALGORITHMS_CACHE.exists():
        try:
            with open(ALGORITHMS_CACHE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass

    # Fetch from API
    try:
        url = "https://mvsep.com/api/app/algorithms"
        headers = {"User-Agent": "mvsep-cli/0.1"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                with open(ALGORITHMS_CACHE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return data
    except Exception:
        pass

    # If cache exists (even if stale), use it
    if ALGORITHMS_CACHE.exists():
        try:
            with open(ALGORITHMS_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return FALLBACK_ALGORITHMS


def resolve_model(query: Union[str, int], algorithms: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Find a model by exact ID or fuzzy substring match."""
    if algorithms is None:
        algorithms = get_algorithms()

    # If query is int or string of digits, match render_id
    try:
        target_id = int(str(query).strip())
        for alg in algorithms:
            if alg.get("render_id") == target_id:
                return alg
    except ValueError:
        pass

    # Substring search (case-insensitive)
    q = str(query).strip().lower()
    matches = []
    for alg in algorithms:
        name = alg.get("name", "").lower()
        desc = alg.get("short_description", "").lower()
        if q == name:
            return alg
        if q in name:
            matches.append(alg)
        elif q in desc:
            matches.append(alg)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Prefer shortest name match if multiple
        matches.sort(key=lambda a: len(a.get("name", "")))
        return matches[0]

    raise ValueError(f"No separation model found matching '{query}'. Use 'mvsep --list-models' to view available models.")
