import json
import re
from pathlib import Path
from typing import Any


def _normalize_source_mode(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"link", "youtube", "manual"}:
        return "link"
    if raw in {"downloaded_video", "download", "indirilen_video", "indirilen video"}:
        return "downloaded_video"
    if raw in {"added_video", "video", "eklenen_video", "eklenen video"}:
        return "added_video"
    if raw in {"auto", "otomatik"}:
        return "auto"
    return raw


def _normalize_folder_name(value: Any) -> str:
    return str(value or "").strip().casefold()


def _extract_prompt_folder_no(folder_name: Any) -> int:
    match = re.search(r"(\d+)\s*$", str(folder_name or "").strip())
    if not match:
        return 0
    try:
        return int(match.group(1))
    except Exception:
        return 0


def _parse_duration_value(value: Any) -> int:
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except Exception:
            return 0
    match = re.search(r"(\d+)", str(value or "").strip())
    if not match:
        return 0
    try:
        return int(match.group(1))
    except Exception:
        return 0


def load_video_settings_override_state(control_dir: Path) -> dict:
    state_path = Path(control_dir) / "video_settings_overrides.json"
    if not state_path.exists():
        return {"mode": "single", "source_mode": "auto", "entries": []}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"mode": "single", "source_mode": "auto", "entries": []}
    if not isinstance(data, dict):
        return {"mode": "single", "source_mode": "auto", "entries": []}
    entries = data.get("entries")
    if not isinstance(entries, list):
        entries = []
    return {
        "mode": "per_video" if str(data.get("mode") or "").strip().lower() == "per_video" else "single",
        "source_mode": _normalize_source_mode(data.get("source_mode")),
        "entries": [item for item in entries if isinstance(item, dict)],
    }


def _match_override_entry(prompt_folder: str, override_state: dict) -> dict | None:
    entries = (override_state or {}).get("entries", [])
    if not isinstance(entries, list) or not prompt_folder:
        return None

    normalized_folder = _normalize_folder_name(prompt_folder)
    folder_no = _extract_prompt_folder_no(prompt_folder)

    for entry in entries:
        if _normalize_folder_name(entry.get("prompt_folder")) == normalized_folder:
            return entry

    if folder_no > 0:
        for entry in entries:
            try:
                entry_source_no = int(entry.get("source_no") or 0)
            except Exception:
                entry_source_no = 0
            if entry_source_no == folder_no:
                return entry

    return None


def resolve_prompt_video_settings(prompt_folder: str, base_settings: dict, override_state: dict | None = None) -> tuple[dict, dict | None]:
    resolved = dict(base_settings or {})
    state = override_state if isinstance(override_state, dict) else {}
    if str(state.get("mode") or "").strip().lower() != "per_video":
        return resolved, None

    entry = _match_override_entry(prompt_folder, state)
    if not isinstance(entry, dict):
        return resolved, None

    settings = entry.get("settings")
    if not isinstance(settings, dict):
        return resolved, entry

    for key in ("aspect_ratio", "ses", "quality", "model"):
        value = settings.get(key)
        if value not in (None, ""):
            resolved[key] = value

    duration_value = _parse_duration_value(settings.get("duration"))
    if duration_value > 0:
        resolved["duration"] = duration_value

    return resolved, entry
