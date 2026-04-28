from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageOps


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
TRANSITION_STATE_FILENAME = "transition_state.json"
STANDARD_SINGLE_IMAGE_NAME = "frame_0001.png"
STANDARD_START_IMAGE_NAME = "start.png"
STANDARD_END_IMAGE_NAME = "end.png"

DEFAULT_TRANSITION_STATE = {
    "video_mode": "normal",
    "gorsel_analiz_transition_enabled": False,
    "gorsel_olustur_transition_enabled": False,
    "gorsel_klonla_transition_enabled": False,
}


def transition_state_path(control_dir: str | Path) -> Path:
    return Path(control_dir) / TRANSITION_STATE_FILENAME


def default_transition_state() -> dict:
    return dict(DEFAULT_TRANSITION_STATE)


def normalize_video_mode(value: str | None) -> str:
    raw = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    if raw in {
        "transition",
        "start end frame",
        "start end",
        "start/end",
        "start end frame transition",
        "start/end frame",
    }:
        return "transition"
    return "normal"


def load_transition_state(control_dir: str | Path) -> dict:
    state = default_transition_state()
    path = transition_state_path(control_dir)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                state["video_mode"] = normalize_video_mode(data.get("video_mode"))
                for key in (
                    "gorsel_analiz_transition_enabled",
                    "gorsel_olustur_transition_enabled",
                    "gorsel_klonla_transition_enabled",
                ):
                    if key in data:
                        state[key] = bool(data.get(key))
    except Exception:
        pass
    return state


def save_transition_state(control_dir: str | Path, updates: dict | None = None) -> dict:
    state = load_transition_state(control_dir)
    if isinstance(updates, dict):
        if "video_mode" in updates:
            state["video_mode"] = normalize_video_mode(updates.get("video_mode"))
        for key in (
            "gorsel_analiz_transition_enabled",
            "gorsel_olustur_transition_enabled",
            "gorsel_klonla_transition_enabled",
        ):
            if key in updates:
                state[key] = bool(updates.get(key))
    state["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    path = transition_state_path(control_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state


def is_video_transition_enabled(control_dir: str | Path) -> bool:
    return load_transition_state(control_dir).get("video_mode") == "transition"


def is_section_transition_enabled(control_dir: str | Path, section_key: str) -> bool:
    return bool(load_transition_state(control_dir).get(section_key, False))


def video_model_supports_transition(model_name: str | None) -> bool:
    return str(model_name or "").strip().casefold() not in {"grok", "happy horse 1.0"}


def natural_sort_key(value: str | Path):
    text = os.path.basename(str(value or "")).strip()
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def list_image_files(folder_path: str | Path) -> list[Path]:
    folder = Path(folder_path)
    if not folder.is_dir():
        return []
    try:
        items = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    except Exception:
        return []
    return sorted(items, key=lambda p: natural_sort_key(p.name))


def find_named_image(folder_path: str | Path, stem_name: str) -> Optional[Path]:
    stem = str(stem_name or "").strip().casefold()
    if not stem:
        return None
    exact_png = Path(folder_path) / f"{stem}.png"
    if exact_png.exists():
        return exact_png
    for image_path in list_image_files(folder_path):
        if image_path.stem.casefold() == stem:
            return image_path
    return None


def resolve_single_image(folder_path: str | Path) -> Optional[Path]:
    for preferred_stem in ("frame_0001", "start"):
        preferred = find_named_image(folder_path, preferred_stem)
        if preferred is not None:
            return preferred
    images = list_image_files(folder_path)
    return images[0] if images else None


def resolve_transition_pair(folder_path: str | Path) -> tuple[Optional[Path], Optional[Path]]:
    start_image = find_named_image(folder_path, "start")
    end_image = find_named_image(folder_path, "end")
    if start_image is not None and end_image is not None:
        return start_image, end_image
    return None, None


def extract_numeric_hint(value: str | Path) -> int:
    match = re.search(r"(\d+)", str(value or ""))
    return int(match.group(1)) if match else 0


def build_candidate_image_folders(
    prompt_folder_name: str,
    reference_image_root: str | Path,
    automation_dir: str | Path,
) -> list[Path]:
    prompt_number = extract_numeric_hint(prompt_folder_name)
    if prompt_number <= 0:
        return []

    root = Path(reference_image_root) if str(reference_image_root or "").strip() else None
    otomasyon_root = Path(automation_dir)
    candidates: list[Path] = []
    seen: set[str] = set()

    def _append(path_value: Path | None):
        if path_value is None:
            return
        key = str(path_value).casefold()
        if key in seen:
            return
        seen.add(key)
        candidates.append(path_value)

    _append(root / f"Klon Görsel {prompt_number}" if root else None)
    _append(root / f"Görsel {prompt_number}" if root else None)
    _append(root / f"Video Görsel Analiz {prompt_number}" if root else None)
    _append(otomasyon_root / "Görsel" / "Klon Görsel" / f"Klon Görsel {prompt_number}")
    _append(otomasyon_root / "Görsel" / "Görseller" / f"Görsel {prompt_number}")
    _append(otomasyon_root / "Görsel" / "Görsel Analiz" / f"Video Görsel Analiz {prompt_number}")
    _append(otomasyon_root / "Prompt" / f"Video Prompt {prompt_number}")

    return candidates


def resolve_visual_inputs_for_prompt(
    prompt_folder_name: str,
    reference_image_root: str | Path,
    automation_dir: str | Path,
    video_mode: str,
) -> dict:
    mode = normalize_video_mode(video_mode)
    searched_folders = build_candidate_image_folders(prompt_folder_name, reference_image_root, automation_dir)
    first_existing_folder = next((folder for folder in searched_folders if folder.exists() and folder.is_dir()), None)

    if mode == "transition":
        for folder in searched_folders:
            start_image, end_image = resolve_transition_pair(folder)
            if start_image is not None and end_image is not None:
                return {
                    "mode": "transition",
                    "source_folder": folder,
                    "reference_image": None,
                    "start_image": start_image,
                    "end_image": end_image,
                    "searched_folders": [str(item) for item in searched_folders],
                }
        return {
            "mode": "transition",
            "source_folder": first_existing_folder,
            "reference_image": None,
            "start_image": None,
            "end_image": None,
            "searched_folders": [str(item) for item in searched_folders],
        }

    for folder in searched_folders:
        image_path = resolve_single_image(folder)
        if image_path is not None:
            return {
                "mode": "normal",
                "source_folder": folder,
                "reference_image": image_path,
                "start_image": None,
                "end_image": None,
                "searched_folders": [str(item) for item in searched_folders],
            }

    return {
        "mode": "normal",
        "source_folder": first_existing_folder,
        "reference_image": None,
        "start_image": None,
        "end_image": None,
        "searched_folders": [str(item) for item in searched_folders],
    }


def clear_image_files(folder_path: str | Path, keep_names: Iterable[str] | None = None):
    folder = Path(folder_path)
    if not folder.is_dir():
        return
    keep = {str(name or "").strip().casefold() for name in (keep_names or []) if str(name or "").strip()}
    for image_path in list_image_files(folder):
        if image_path.name.casefold() in keep:
            continue
        try:
            image_path.unlink()
        except Exception:
            pass


def _prepared_image_for_png(source_path: str | Path) -> Image.Image:
    with Image.open(source_path) as img:
        prepared = ImageOps.exif_transpose(img)
        if prepared.mode == "P":
            if "transparency" in prepared.info:
                prepared = prepared.convert("RGBA")
            else:
                prepared = prepared.convert("RGB")
        elif prepared.mode not in {"RGB", "RGBA"}:
            prepared = prepared.convert("RGBA" if "A" in prepared.mode else "RGB")
        return prepared.copy()


def standardize_output_image(
    source_path: str | Path,
    target_dir: str | Path,
    target_stem: str,
) -> Path:
    source = Path(source_path)
    target = Path(target_dir) / f"{str(target_stem or '').strip()}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    prepared = _prepared_image_for_png(source)
    try:
        prepared.save(target, format="PNG", optimize=True)
    finally:
        prepared.close()
    if source.exists():
        try:
            if source.resolve() != target.resolve():
                source.unlink()
        except Exception:
            pass
    return target


def replace_folder_images_with_standard_images(
    folder_path: str | Path,
    image_mapping: Iterable[tuple[str, str | Path]],
) -> list[Path]:
    staged_images: list[tuple[str, Image.Image]] = []
    for target_stem, source_path in image_mapping:
        if not source_path:
            continue
        staged_images.append((str(target_stem or "").strip(), _prepared_image_for_png(source_path)))

    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)
    clear_image_files(folder)

    saved_paths: list[Path] = []
    try:
        for target_stem, prepared in staged_images:
            target = folder / f"{target_stem}.png"
            prepared.save(target, format="PNG", optimize=True)
            saved_paths.append(target)
    finally:
        for _, prepared in staged_images:
            try:
                prepared.close()
            except Exception:
                pass
    return saved_paths
