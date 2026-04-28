import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
ANA_SISTEM_DIR = SCRIPT_DIR.parent
OTOMASYON_DIR = ANA_SISTEM_DIR.parent
CONTROL_DIR = ANA_SISTEM_DIR / "Otomasyon Çalıştırma" / ".control"
CONTROL_DIR.mkdir(parents=True, exist_ok=True)
PREPARED_INPUTS_DIR = OTOMASYON_DIR / ".cache" / "video_klonla_inputs"
PREPARED_INPUTS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = CONTROL_DIR / "settings.local.json"
RUNTIME_FILE = CONTROL_DIR / "video_klonla_runtime.json"
PAUSE_FLAG = CONTROL_DIR / "PAUSE.flag"
STOP_FLAG = CONTROL_DIR / "STOP.flag"

DEFAULT_MODEL = "v5.6"
DEFAULT_QUALITY = "720p"
POLL_INTERVAL_SECONDS = 15
MAX_REFERENCE_IMAGE_EDGE = 1920
COMPACT_REFERENCE_IMAGE_EDGE = 1280
CREATE_TIMEOUT_SECONDS = 600
WAIT_TIMEOUT_SECONDS = 900
PREPARED_IMAGE_JPEG_QUALITY = 6
RETRY_PREPARED_IMAGE_JPEG_QUALITY = 10


class UserFacingError(Exception):
    def __init__(
        self,
        status: str,
        reason: str,
        detail: str = "",
        result: str = "Video Başarısız",
    ):
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.detail = detail
        self.result = result


def strip_ansi(text: str) -> str:
    cleaned = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text or "")
    return "\n".join((line.split("\r")[-1] if "\r" in line else line) for line in cleaned.split("\n"))


def normalize_error_detail(detail: Any) -> str:
    if detail is None:
        return ""
    if isinstance(detail, (dict, list)):
        try:
            return json.dumps(detail, ensure_ascii=False)
        except Exception:
            return str(detail)
    return str(detail)


def sanitize_token(value: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip())
    cleaned = cleaned.strip("._-")
    return cleaned or fallback


def is_credit_error_text(detail: Any) -> bool:
    text = strip_ansi(normalize_error_detail(detail))
    if not text:
        return False
    return bool(
        re.search(
            r"all\s*credits?.*used\s*up|credits?.*have\s*been\s*used|purchase\s*credits|"
            r"upgrade\s+your\s+membership|50043\b|insufficient.*credit|credit.*balance|"
            r"kredi.*yetersiz|payment.*required|402\b",
            text,
            re.IGNORECASE,
        )
    )


def extract_image_resolution_limit_message(detail: Any) -> str:
    text = strip_ansi(normalize_error_detail(detail))
    if not text:
        return ""
    match = re.search(
        r"image resolution\s*(\d+)x(\d+)\s*exceeds limit\s*(\d+)x(\d+)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""
    cur_w, cur_h, limit_w, limit_h = match.groups()
    return (
        f"Referans görsel boyutu çok büyük ({cur_w}x{cur_h}). "
        f"Motion Control en fazla {limit_w}x{limit_h} kabul ediyor."
    )


def extract_input_access_timeout_message(detail: Any) -> str:
    text = strip_ansi(normalize_error_detail(detail))
    if not text:
        return ""
    match = re.search(
        r'Failed to access\s+"?([^"]+?)"?\s*:\s*Response timeout for\s*(\d+)ms',
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""
    failed_path, timeout_ms = match.groups()
    failed_name = os.path.basename(failed_path.strip().strip("\"'").rstrip("\\/")) or "referans_gorsel"
    timeout_seconds = max(1, int(timeout_ms) // 1000) if str(timeout_ms).isdigit() else 60
    return f"Referans görsel yükleme zaman aşımı: {failed_name} ({timeout_seconds} sn)"


def is_input_access_timeout_text(detail: Any) -> bool:
    return bool(extract_input_access_timeout_message(detail))


def get_user_facing_reason(detail: Any, fallback: str = "İşlem tamamlanamadı") -> str:
    if is_credit_error_text(detail):
        return "Kredi yetersiz"
    image_limit_message = extract_image_resolution_limit_message(detail)
    if image_limit_message:
        return image_limit_message
    input_timeout_message = extract_input_access_timeout_message(detail)
    if input_timeout_message:
        return input_timeout_message
    return fallback


def resolve_binary(name: str) -> str:
    candidates = [name, f"{name}.cmd", f"{name}.exe", f"{name}.bat"] if os.name == "nt" else [name]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    raise FileNotFoundError(f"'{name}' bulunamadı")


def run_command(cmd, cwd=None, check=False, capture_output=True):
    cmd = [resolve_binary(cmd[0])] + [str(x) for x in cmd[1:]]
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Komut başarısız: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def start_process(cmd, cwd=None):
    cmd = [resolve_binary(cmd[0])] + [str(x) for x in cmd[1:]]
    return subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def parse_json_from_output(output: str) -> dict:
    clean = strip_ansi(output).strip()
    if not clean:
        raise ValueError("Boş çıktı")
    try:
        return json.loads(clean)
    except Exception:
        pass
    match = re.search(r"(\{.*\})", clean, flags=re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError(clean[:300])


def read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
    except Exception:
        pass
    return default


def get_settings() -> dict:
    return read_json(SETTINGS_FILE, {}) if SETTINGS_FILE.exists() else {}


def wait_pause():
    logged = False
    while PAUSE_FLAG.exists():
        if STOP_FLAG.exists():
            raise SystemExit(0)
        if not logged:
            print("[PAUSE] Duraklatıldı.")
            logged = True
        time.sleep(0.3)
    if logged:
        print("[PAUSE] Devam ediliyor...")


def stop_check():
    if STOP_FLAG.exists():
        print("[STOP] Bitirme isteği alındı.")
        raise SystemExit(0)


def ensure_logged_in():
    status = run_command(["pixverse", "auth", "status"])
    info = run_command(["pixverse", "account", "info"])
    if status.returncode == 0 and info.returncode == 0:
        print("Giriş yapıldı")
        return
    print("PixVerse girişi gerekiyor. Tarayıcı açılabilir...")
    login = run_command(["pixverse", "auth", "login"], capture_output=False)
    if login.returncode != 0:
        raise RuntimeError("PixVerse giriş işlemi başarısız oldu.")
    print("Giriş yapıldı")


def next_output_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    max_index = 0
    for item in root.iterdir():
        if item.is_dir() and item.name.startswith("Video "):
            try:
                max_index = max(max_index, int(item.name.split("Video ", 1)[1]))
            except Exception:
                pass
    return root / f"Video {max_index + 1 if max_index else 1}"


def download_asset(video_id: Any, out_dir: Path) -> Optional[dict]:
    result = run_command(["pixverse", "asset", "download", str(video_id), "--json"], cwd=out_dir)
    if result.returncode != 0:
        raise UserFacingError("Video indirme", "Video indirilemedi", strip_ansi(result.stderr or result.stdout)[:180])
    try:
        return parse_json_from_output(result.stdout)
    except Exception:
        return None


def probe_image_dimensions(image_path: str) -> tuple[int, int]:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            image_path,
        ]
    )
    if result.returncode != 0:
        return 0, 0
    match = re.search(r"(\d+)\s*x\s*(\d+)", strip_ansi(result.stdout or result.stderr))
    if not match:
        return 0, 0
    return int(match.group(1)), int(match.group(2))


def fit_dimensions_to_limit(width: int, height: int, max_edge: int) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        return width, height
    scale = min(max_edge / float(width), max_edge / float(height), 1.0)
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


def prepare_reference_image_for_cli(
    image_path: str,
    out_dir: Path,
    max_edge: int = MAX_REFERENCE_IMAGE_EDGE,
    quality: int = PREPARED_IMAGE_JPEG_QUALITY,
    variant: str = "prepared",
) -> str:
    width, height = probe_image_dimensions(image_path)
    if width <= 0 or height <= 0:
        print("! Referans görsel boyutu okunamadı, orijinal dosya kullanılacak")
        return image_path

    target_w, target_h = fit_dimensions_to_limit(width, height, max_edge)
    prepared_dir = PREPARED_INPUTS_DIR / sanitize_token(out_dir.name, "video")
    prepared_dir.mkdir(parents=True, exist_ok=True)
    prepared_path = prepared_dir / f"reference_{variant}_{target_w}x{target_h}.jpg"

    if (target_w, target_h) != (width, height):
        print(
            "[INFO] Referans görsel Motion Control limiti için küçültülüyor: "
            f"{width}x{height} -> {target_w}x{target_h}"
        )
    else:
        print(f"[INFO] Referans görsel PixVerse için optimize ediliyor: {width}x{height}")

    vf_parts = []
    if (target_w, target_h) != (width, height):
        vf_parts.append(f"scale={target_w}:{target_h}:flags=lanczos")
    vf_parts.append("format=yuvj420p")

    result = run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            image_path,
            "-vf",
            ",".join(vf_parts),
            "-frames:v",
            "1",
            "-map_metadata",
            "-1",
            "-q:v",
            str(quality),
            str(prepared_path),
        ],
        cwd=prepared_dir,
    )
    if result.returncode != 0:
        detail = strip_ansi(result.stderr or result.stdout)[:220]
        if (target_w, target_h) == (width, height):
            print(f"! Referans görsel optimize edilemedi, orijinal dosya kullanılacak: {detail}")
            return image_path
        raise UserFacingError("Referans görsel hazırlama", "Referans görsel otomatik küçültülemedi", detail)

    size_kb = max(1, int(round(prepared_path.stat().st_size / 1024.0)))
    print(f"✓ Referans görsel hazırlandı: {prepared_path} ({size_kb} KB)")
    return str(prepared_path)


def wait_for_completion(video_id: Any, out_dir: Path) -> dict:
    process = start_process(
        ["pixverse", "task", "wait", str(video_id), "--timeout", str(WAIT_TIMEOUT_SECONDS), "--json"],
        cwd=out_dir,
    )
    start = time.monotonic()
    next_log = POLL_INTERVAL_SECONDS
    print(f"Durum: video üretimi başlatıldı | görev ID: {video_id}")
    print("Durum: video oluşturuluyor | sonuç bekleniyor")
    while True:
        wait_pause()
        stop_check()
        rc = process.poll()
        elapsed = int(time.monotonic() - start)
        if rc is not None:
            stdout, stderr = process.communicate()
            if rc != 0:
                raise UserFacingError("Video oluşturma bekleme", "İşlem tamamlanamadı", strip_ansi(stderr or stdout)[:220])
            data = parse_json_from_output(stdout)
            print(f"Durum: video oluşturma tamamlandı | {elapsed} sn sürdü")
            return data
        if elapsed >= next_log:
            print(f"Durum: oluşturuluyor | {elapsed} sn geçti")
            next_log += POLL_INTERVAL_SECONDS
        time.sleep(1)


def build_cmd(image: str, video: str, model: str, quality: str, no_wait: bool) -> list:
    cmd = [
        "pixverse",
        "create",
        "motion-control",
        "--image",
        image,
        "--video",
        video,
        "--model",
        model,
        "--quality",
        quality,
        "--timeout",
        str(CREATE_TIMEOUT_SECONDS),
        "--json",
    ]
    if no_wait:
        cmd.append("--no-wait")
    return cmd


def submit_motion_control_request(image: str, video: str, model: str, quality: str, out_dir: Path) -> dict:
    cmd = build_cmd(image, video, model, quality, no_wait=True)
    print("Komut gönderiliyor: motion-control")
    result = run_command(cmd, cwd=out_dir)
    if result.returncode != 0:
        detail = strip_ansi(result.stderr or result.stdout)[:260]
        raise UserFacingError("Prompt gönderme", get_user_facing_reason(detail), detail)
    data = parse_json_from_output(result.stdout)
    if data.get("error"):
        detail = normalize_error_detail(data.get("error"))[:260]
        raise UserFacingError("Prompt gönderme", get_user_facing_reason(detail), detail)
    return data


def normalize_input_item(raw: dict) -> dict:
    return {
        "name": str(raw.get("name") or raw.get("folder_name") or "").strip(),
        "video": str(raw.get("video") or raw.get("video_path") or "").strip(),
        "image": str(raw.get("image") or raw.get("image_path") or "").strip(),
        "model": str(raw.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "quality": str(raw.get("quality") or DEFAULT_QUALITY).strip() or DEFAULT_QUALITY,
    }


def collect_runtime_items(runtime: dict) -> list[dict]:
    items = []
    for raw in runtime.get("items", []) or []:
        item = normalize_input_item(raw)
        if item["video"] and item["image"]:
            items.append(item)
    if items:
        return items
    single = normalize_input_item(runtime)
    return [single] if single["video"] and single["image"] else []


def process_item(item: dict, out_root: Path, auto_download: bool) -> bool:
    out_dir = next_output_dir(out_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nİŞLEM: {item.get('name') or os.path.basename(item['video'])}")
    print(f"✓ Referans video bulundu: {item['video']}")
    print(f"✓ Referans görsel bulundu: {item['image']}")

    prepared_image = prepare_reference_image_for_cli(item["image"], out_dir)
    try:
        data = submit_motion_control_request(prepared_image, item["video"], item["model"], item["quality"], out_dir)
    except UserFacingError as exc:
        if is_input_access_timeout_text(exc.detail):
            print("[WARN] PixVerse referans görsele zamanında erişemedi.")
            print("[INFO] Daha hafif bir JPG kopyası hazırlanıyor ve Motion Control otomatik tekrar denenecek...")
            compact_image = prepare_reference_image_for_cli(
                item["image"],
                out_dir,
                max_edge=COMPACT_REFERENCE_IMAGE_EDGE,
                quality=RETRY_PREPARED_IMAGE_JPEG_QUALITY,
                variant="compact",
            )
            data = submit_motion_control_request(compact_image, item["video"], item["model"], item["quality"], out_dir)
        else:
            raise

    video_id = data.get("video_id") or data.get("task_id")
    if auto_download and video_id:
        print(f"Durum: görev alındı | ID: {video_id}")
        final = wait_for_completion(video_id, out_dir)
        if final.get("error"):
            detail = normalize_error_detail(final.get("error"))[:260]
            raise UserFacingError("Video oluşturma", get_user_facing_reason(detail), detail)
        download_asset(video_id, out_dir)
        meta = final
    else:
        meta = data

    with open(out_dir / "video_result.json", "w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2)
    print("✓ Motion Control tamamlandı")
    return True


def main():
    parser = argparse.ArgumentParser(description="PixVerse Motion Control runner")
    parser.add_argument("--config", default=str(RUNTIME_FILE))
    parser.add_argument("--video")
    parser.add_argument("--image")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--quality", default=DEFAULT_QUALITY)
    parser.add_argument("--output-root")
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    runtime = read_json(Path(args.config), {})
    if args.video:
        runtime["video"] = args.video
    if args.image:
        runtime["image"] = args.image
    if args.model:
        runtime["model"] = args.model
    if args.quality:
        runtime["quality"] = args.quality

    items = collect_runtime_items(runtime)
    if not items:
        print("HATA: İşlenecek video/görsel bulunamadı.")
        raise SystemExit(1)

    output_root = Path(
        args.output_root
        or runtime.get("output_root")
        or settings.get("klon_video_dir")
        or settings.get("video_klonla_dir")
        or settings.get("video_output_dir")
        or (OTOMASYON_DIR / "Video" / "Video")
    )

    ensure_logged_in()

    ok_count = 0
    fail_count = 0
    for item in items:
        try:
            wait_pause()
            stop_check()
            process_item(item, output_root, auto_download=not args.no_download)
            ok_count += 1
        except UserFacingError as error:
            fail_count += 1
            print(f"\nHATA DURUMU: {error.status}")
            print(f"SEBEP      : {error.reason}")
            if error.detail:
                print(f"DETAY      : {error.detail}")
            print(f"SONUÇ      : {error.result}")
        except SystemExit:
            raise
        except Exception as error:
            fail_count += 1
            print("\nHATA DURUMU: Beklenmeyen hata")
            print("SEBEP      : İşlem tamamlanamadı")
            print(f"DETAY      : {str(error)[:220]}")
            print("SONUÇ      : Video Başarısız")

    print("\nTÜM İŞLEMLER TAMAMLANDI!")
    print(f"Başarılı: {ok_count}")
    print(f"Başarısız: {fail_count}")
    raise SystemExit(0 if ok_count > 0 and fail_count == 0 else (2 if ok_count > 0 else 1))


if __name__ == "__main__":
    main()
