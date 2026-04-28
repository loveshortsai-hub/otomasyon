from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ANA_SISTEM_DIR = SCRIPT_DIR.parent
if str(ANA_SISTEM_DIR) not in sys.path:
    sys.path.insert(0, str(ANA_SISTEM_DIR))

from transition_utils import clear_image_files, list_image_files, load_transition_state, standardize_output_image


BASE_DIR = Path(r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma")
CONTROL_DIR = BASE_DIR / ".control"
SETTINGS_PATH = CONTROL_DIR / "settings.local.json"
STATE_PATH = CONTROL_DIR / "batch_state.json"
GORSEL_PROMPT_DIR = Path(r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Prompt")
GORSEL_OUTPUT_DIR = Path(r"C:\Users\User\Desktop\Otomasyon\Görsel\Görseller")

MODEL_MAP = {
    "Nano Banana 2": "gemini-3.1-flash",
    "Nano Banana Pro": "gemini-3.0",
    "Nano Banana": "gemini-2.5-flash",
    "Seedream 5.0 Lite": "seedream-5.0-lite",
    "Seedream 4.5": "seedream-4.5",
    "Seedream 4.0": "seedream-4.0",
    "Kling O3": "kling-image-o3",
    "Kling 3.0": "kling-image-v3",
    "Qwen Image": "qwen-image",
    "GPT Image 2": "gpt-image-2.0",
    "CPT Image 2": "gpt-image-2.0",
    "gpt-image-2.0": "gpt-image-2.0",
    "cpt-image-2.0": "gpt-image-2.0",
}

QUALITY_OPTIONS = {
    "qwen-image": ["720p", "1080p"],
    "gpt-image-2.0": ["1080p", "1440p", "2160p"],
    "gemini-3.1-flash": ["512p", "1080p", "1440p", "2160p"],
    "gemini-3.0": ["1080p", "1440p", "2160p"],
    "gemini-2.5-flash": ["1080p"],
    "seedream-5.0-lite": ["1440p", "1800p"],
    "seedream-4.5": ["1440p", "2160p"],
    "seedream-4.0": ["1080p", "1440p", "2160p"],
    "kling-image-o3": ["1080p", "1440p", "2160p"],
    "kling-image-v3": ["1080p", "1440p"],
}

GPT_IMAGE_2_ASPECTS_BY_QUALITY = {
    "1080p": ["1:1", "3:2", "2:3"],
    "1440p": ["1:1", "16:9", "9:16"],
    "2160p": ["16:9", "9:16"],
}


def parse_json_output(raw_text: str) -> dict:
    text = str(raw_text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return {}
    return {}


def load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        print(f"[ERROR] Ayarlar okunamadı: {exc}")
    return {}


def update_batch_state(success: bool):
    if not STATE_PATH.exists():
        return
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            state = {}
        state["gorsel_olustur_last_status"] = "success" if success else "error"
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resolve_quality(model_name: str, requested_quality: str) -> str:
    qualities = QUALITY_OPTIONS.get(model_name, ["1080p"])
    tercih = str(requested_quality or "Standart").strip().lower()
    if tercih == "maksimum":
        return qualities[-1]
    if tercih in {"yüksek", "yuksek"}:
        return qualities[min(len(qualities) - 1, len(qualities) // 2)]
    return qualities[0]


def ratio_to_float(value: str) -> float | None:
    raw = str(value or "").strip()
    if ":" not in raw:
        return None
    try:
        left, right = raw.split(":", 1)
        left_val = float(left)
        right_val = float(right)
        if left_val <= 0 or right_val <= 0:
            return None
        return left_val / right_val
    except Exception:
        return None


def closest_aspect_ratio(requested_aspect: str, candidates: list[str]) -> str:
    requested_value = ratio_to_float(requested_aspect)
    if requested_aspect in candidates:
        return requested_aspect
    if requested_value is None:
        return candidates[0] if candidates else "1:1"
    return min(candidates, key=lambda ratio: abs(requested_value - (ratio_to_float(ratio) or requested_value)))


def resolve_gpt_image_2_settings(requested_quality: str, requested_aspect: str) -> tuple[str, str]:
    tercih = str(requested_quality or "Standart").strip().lower()
    if tercih == "maksimum":
        quality_order = ["2160p", "1440p", "1080p"]
    elif tercih in {"yüksek", "yuksek"}:
        quality_order = ["1440p", "2160p", "1080p"]
    else:
        quality_order = ["1440p", "1080p", "2160p"]

    requested = str(requested_aspect or "16:9").strip()
    for quality in quality_order:
        supported = GPT_IMAGE_2_ASPECTS_BY_QUALITY[quality]
        if requested in supported:
            return quality, requested

    union = []
    for quality in quality_order:
        for ratio in GPT_IMAGE_2_ASPECTS_BY_QUALITY[quality]:
            if ratio not in union:
                union.append(ratio)
    aspect = closest_aspect_ratio(requested, union)
    for quality in quality_order:
        if aspect in GPT_IMAGE_2_ASPECTS_BY_QUALITY[quality]:
            return quality, aspect
    return "1440p", "1:1"


def collect_prompt_folders() -> list[tuple[int, Path]]:
    folders: list[tuple[int, Path]] = []
    if not GORSEL_PROMPT_DIR.exists():
        return folders
    for item in GORSEL_PROMPT_DIR.iterdir():
        if not item.is_dir() or not item.name.startswith("Görsel Prompt"):
            continue
        try:
            number = int(item.name.replace("Görsel Prompt", "").strip())
        except Exception:
            continue
        folders.append((number, item))
    folders.sort(key=lambda item: item[0])
    return folders


def read_prompt(prompt_path: Path) -> str:
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def resolve_prompt_tasks(folder_path: Path, transition_enabled: bool) -> list[tuple[str, str]]:
    if transition_enabled:
        start_prompt = read_prompt(folder_path / "start_prompt.txt")
        end_prompt = read_prompt(folder_path / "end_prompt.txt")
        tasks = []
        if start_prompt:
            tasks.append(("start", start_prompt))
        if end_prompt:
            tasks.append(("end", end_prompt))
        return tasks

    prompt_text = read_prompt(folder_path / "gorsel_prompt.txt")
    return [("frame_0001", prompt_text)] if prompt_text else []


def find_downloaded_image(target_dir: Path, before_paths: set[str]) -> Path | None:
    images = list_image_files(target_dir)
    yeni_dosyalar = [path for path in images if str(path.resolve()) not in before_paths]
    if yeni_dosyalar:
        yeni_dosyalar.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return yeni_dosyalar[0]
    if images:
        images.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return images[0]
    return None


def create_image_and_download(
    pixverse_path: str,
    prompt_text: str,
    px_model: str,
    quality: str,
    aspect_ratio: str,
    target_dir: Path,
    target_stem: str,
) -> Path:
    create_cmd = [
        pixverse_path,
        "create",
        "image",
        "--prompt",
        prompt_text,
        "--model",
        px_model,
        "--quality",
        quality,
        "--aspect-ratio",
        aspect_ratio,
        "--json",
    ]
    create_proc = subprocess.run(create_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output_text = (create_proc.stdout or "") + ("\n" + create_proc.stderr if create_proc.stderr else "")
    if create_proc.returncode != 0:
        raise RuntimeError(output_text.strip() or "PixVerse create image başarısız oldu.")

    data = parse_json_output(output_text)
    asset_id = str(data.get("image_id") or data.get("id") or "").strip()
    if not asset_id:
        raise RuntimeError("PixVerse yanıtında image_id bulunamadı.")

    before_paths = {str(path.resolve()) for path in list_image_files(target_dir)}
    download_cmd = [pixverse_path, "asset", "download", asset_id, "--type", "image", "--dest", str(target_dir), "--json"]
    download_proc = subprocess.run(download_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if download_proc.returncode != 0:
        detail = (download_proc.stdout or "") + ("\n" + download_proc.stderr if download_proc.stderr else "")
        raise RuntimeError(detail.strip() or "PixVerse asset download başarısız oldu.")

    downloaded_file = find_downloaded_image(target_dir, before_paths)
    if downloaded_file is None or not downloaded_file.exists():
        raise RuntimeError("İndirme tamamlandı ancak görsel dosyası bulunamadı.")

    return standardize_output_image(downloaded_file, target_dir, target_stem)


def main():
    print("[INFO] Görsel Oluştur Motoru başlatıldı.")
    time.sleep(1)

    settings = load_settings()
    if not settings:
        sys.exit(1)

    raw_model = str(settings.get("gorsel_model") or "Nano Banana 2").strip()
    px_model = MODEL_MAP.get(raw_model)
    if not px_model:
        print(f"[ERROR] Desteklenmeyen veya tanımlanmamış Görsel Modeli seçildi: {raw_model}")
        print("[INFO] Lütfen ayarlardan PixVerse destekli bir Image modeli seçin.")
        sys.exit(1)

    if not GORSEL_PROMPT_DIR.exists():
        print(f"[ERROR] Görsel Prompt klasörü bulunamadı: {GORSEL_PROMPT_DIR}")
        sys.exit(1)

    prompt_folders = collect_prompt_folders()
    if not prompt_folders:
        print("[ERROR] Görsel Prompt klasöründe işlenecek prompt bulunamadı.")
        sys.exit(1)

    pixverse_path = shutil.which("pixverse") or "pixverse"
    if not shutil.which("pixverse"):
        print("[ERROR] PixVerse komutu bulunamadı. Lütfen PixVerse CLI yüklü olduğundan emin olun.")
        sys.exit(1)

    transition_state = load_transition_state(CONTROL_DIR)
    transition_enabled = bool(transition_state.get("gorsel_olustur_transition_enabled", False))
    requested_aspect_ratio = str(settings.get("gorsel_boyutu", "16:9") or "16:9").strip()
    if px_model == "gpt-image-2.0":
        quality, aspect_ratio = resolve_gpt_image_2_settings(
            settings.get("gorsel_kalitesi", "Standart"),
            requested_aspect_ratio,
        )
    else:
        quality = resolve_quality(px_model, settings.get("gorsel_kalitesi", "Standart"))
        aspect_ratio = requested_aspect_ratio

    GORSEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Seçili Görsel Modeli: {raw_model} -> {px_model}")
    print(f"[INFO] Kalite: {quality}")
    print(f"[INFO] Boyut: {aspect_ratio}")
    if px_model == "gpt-image-2.0" and aspect_ratio != requested_aspect_ratio:
        print(f"[INFO] GPT Image 2 uyumlu oran kullanildi: {requested_aspect_ratio} -> {aspect_ratio}")
    print(f"[INFO] Transition modu: {'Açık' if transition_enabled else 'Kapalı'}")

    failed_any = False

    for number, folder_path in prompt_folders:
        prompt_tasks = resolve_prompt_tasks(folder_path, transition_enabled)
        if transition_enabled:
            if len(prompt_tasks) != 2:
                print(f"[WARNING] #{number} için start/end prompt eksik. Klasör atlanıyor...")
                failed_any = True
                continue
        elif not prompt_tasks:
            print(f"[WARNING] #{number} numaralı prompt dosyası boş veya eksik. Atlanıyor...")
            continue

        target_dir = GORSEL_OUTPUT_DIR / f"Görsel {number}"
        target_dir.mkdir(parents=True, exist_ok=True)
        clear_image_files(target_dir)

        print(f"\n#{number} için görsel üretimi başlatıldı...")
        folder_success = True
        folder_start_time = time.time()

        for target_stem, prompt_text in prompt_tasks:
            label = "Start Frame" if target_stem == "start" else "End Frame" if target_stem == "end" else "Görsel"
            print(f"[INFO] {label} prompt gönderiliyor... ({prompt_text[:40]}...)")
            try:
                saved_path = create_image_and_download(
                    pixverse_path=pixverse_path,
                    prompt_text=prompt_text,
                    px_model=px_model,
                    quality=quality,
                    aspect_ratio=aspect_ratio,
                    target_dir=target_dir,
                    target_stem=target_stem,
                )
                print(f"[OK] {label} kaydedildi: {saved_path.name}")
            except Exception as exc:
                print(f"[ERROR] #{number} {label} oluşturulamadı: {exc}")
                folder_success = False
                failed_any = True
                break

        if not folder_success and transition_enabled:
            clear_image_files(target_dir)
            print(f"[WARN] #{number} için eksik transition çifti temizlendi.")
            continue

        elapsed = round(time.time() - folder_start_time, 1)
        print(f"⏱️ #{number} {elapsed} saniyede tamamlandı.")
        print(f"✅ #{number} Başarılı işlem")

    update_batch_state(not failed_any)
    if failed_any:
        print("\n[ERROR] İşlem bazı hatalarla tamamlandı.")
        sys.exit(1)

    print("\n[SUCCESS] Görsel Oluştur işlemi başarıyla sonlandırıldı.")


if __name__ == "__main__":
    main()
