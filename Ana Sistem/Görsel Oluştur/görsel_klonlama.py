import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import time
from PIL import Image, ImageOps

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ANA_SISTEM_DIR = os.path.dirname(SCRIPT_DIR)
if ANA_SISTEM_DIR not in sys.path:
    sys.path.insert(0, ANA_SISTEM_DIR)

from transition_utils import (
    clear_image_files,
    load_transition_state,
    resolve_single_image,
    resolve_transition_pair,
    standardize_output_image,
)
CONTROL_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma\.control"
os.makedirs(CONTROL_DIR, exist_ok=True)

PAUSE_FLAG = os.path.join(CONTROL_DIR, "PAUSE.flag")
STOP_FLAG = os.path.join(CONTROL_DIR, "STOP.flag")
RUNNING_PID = os.path.join(CONTROL_DIR, "RUNNING.pid")
SETTINGS_PATH = os.path.join(CONTROL_DIR, "settings.local.json")

ROOT_DIR = r"C:\Users\User\Desktop\Otomasyon"
DEFAULT_INPUT_ANALYZE_DIR = os.path.join(ROOT_DIR, r"Görsel\Görsel Analiz")
DEFAULT_INPUT_CREATE_DIR = os.path.join(ROOT_DIR, r"Görsel\Görseller")
DEFAULT_OUTPUT_DIR = os.path.join(ROOT_DIR, r"Görsel\Klon Görsel")
DEFAULT_PROMPT_PATH = os.path.join(ROOT_DIR, r"Ana Sistem\Görsel Oluştur\Görsel Düzelt.txt")

SUPPORTED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")
COMMON_ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "5:4", "4:5", "3:2", "2:3", "21:9"]
DEFAULT_MODEL_NAME = "Kling O3"
DEFAULT_TIMEOUT_SECONDS = 420
HEARTBEAT_SECONDS = 10
TEMP_PANEL_DIR = os.path.join(CONTROL_DIR, "tmp_kling_o3_panels")
TEMP_REFERENCE_PANEL_DIR = os.path.join(CONTROL_DIR, "tmp_reference_panels")
PIXVERSE_VIDEO_REFERENCE_MAX_SIDE = 1920

PIXVERSE_IMAGE_MODELS = {
    "Qwen Image": {
        "cli": "qwen-image",
        "qualities": ["720p", "1080p"],
        "supports_auto_ratio": False,
        "aspect_ratios": COMMON_ASPECT_RATIOS,
    },
    "GPT Image 2": {
        "cli": "gpt-image-2.0",
        "qualities": ["1080p", "1440p", "2160p"],
        "supports_auto_ratio": False,
        "aspect_ratios": ["1:1", "16:9", "9:16", "3:2", "2:3"],
        "quality_aspect_ratios": {
            "1080p": ["1:1", "3:2", "2:3"],
            "1440p": ["1:1", "16:9", "9:16"],
            "2160p": ["16:9", "9:16"],
        },
    },
    "Nano Banana 2": {
        "cli": "gemini-3.1-flash",
        "qualities": ["512p", "1080p", "1440p", "2160p"],
        "supports_auto_ratio": True,
        "aspect_ratios": ["auto"] + COMMON_ASPECT_RATIOS,
    },
    "Nano Banana Pro": {
        "cli": "gemini-3.0",
        "qualities": ["1080p", "1440p", "2160p"],
        "supports_auto_ratio": True,
        "aspect_ratios": ["auto"] + COMMON_ASPECT_RATIOS,
    },
    "Nano Banana": {
        "cli": "gemini-2.5-flash",
        "qualities": ["1080p"],
        "supports_auto_ratio": True,
        "aspect_ratios": ["auto"] + COMMON_ASPECT_RATIOS,
    },
    "Seedream 5.0 Lite": {
        "cli": "seedream-5.0-lite",
        "qualities": ["1440p", "1800p"],
        "supports_auto_ratio": True,
        "aspect_ratios": ["auto"] + COMMON_ASPECT_RATIOS,
    },
    "Seedream 4.5": {
        "cli": "seedream-4.5",
        "qualities": ["1440p", "2160p"],
        "supports_auto_ratio": True,
        "aspect_ratios": ["auto"] + COMMON_ASPECT_RATIOS,
    },
    "Seedream 4.0": {
        "cli": "seedream-4.0",
        "qualities": ["1080p", "1440p", "2160p"],
        "supports_auto_ratio": True,
        "aspect_ratios": ["auto"] + COMMON_ASPECT_RATIOS,
    },
    "Kling O3": {
        "cli": "kling-image-o3",
        "qualities": ["1080p", "1440p", "2160p"],
        "supports_auto_ratio": False,
        "aspect_ratios": COMMON_ASPECT_RATIOS,
    },
}


def stop_istegi_var_mi() -> bool:
    return os.path.exists(STOP_FLAG)


def pid_kaydet():
    try:
        with open(RUNNING_PID, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def pid_sil():
    try:
        if os.path.exists(RUNNING_PID):
            os.remove(RUNNING_PID)
    except Exception:
        pass


atexit.register(pid_sil)


def bekle_pause_varsa():
    paused_logged = False
    while os.path.exists(PAUSE_FLAG):
        if stop_istegi_var_mi():
            print("[STOP] Pause sırasında stop alındı. Güvenli çıkış yapılıyor...")
            sys.exit(0)

        if not paused_logged:
            print("[PAUSE] Duraklatıldı. Devam için PAUSE.flag silinmeli.")
            paused_logged = True

        time.sleep(0.2)

    if paused_logged:
        print("[PAUSE] Devam ediliyor...")


def stop_kontrol_noktasinda_cik():
    if stop_istegi_var_mi():
        print("[STOP] Bitirme isteği alındı. Güvenli çıkış yapılıyor...")
        sys.exit(0)


def natural_sort_key(value: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", str(value or ""))]


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


def normalize_image_model(value: str, default_model: str = DEFAULT_MODEL_NAME) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "qwen image": "Qwen Image",
        "qwen-image": "Qwen Image",
        "qwenimage": "Qwen Image",
        "gpt image 2": "GPT Image 2",
        "gptimage2": "GPT Image 2",
        "gpt-image-2": "GPT Image 2",
        "gpt-image-2.0": "GPT Image 2",
        "cpt image 2": "GPT Image 2",
        "cptimage2": "GPT Image 2",
        "cpt-image-2": "GPT Image 2",
        "cpt-image-2.0": "GPT Image 2",
        "nano banana 2": "Nano Banana 2",
        "nanobanana2": "Nano Banana 2",
        "gemini-3.1-flash": "Nano Banana 2",
        "nano banana pro": "Nano Banana Pro",
        "nanobananapro": "Nano Banana Pro",
        "gemini-3.0": "Nano Banana Pro",
        "nano banana": "Nano Banana",
        "nanobanana": "Nano Banana",
        "gemini-2.5-flash": "Nano Banana",
        "seedream 5.0 lite": "Seedream 5.0 Lite",
        "seedream5.0lite": "Seedream 5.0 Lite",
        "seedream-5.0-lite": "Seedream 5.0 Lite",
        "seedream 4.5": "Seedream 4.5",
        "seedream4.5": "Seedream 4.5",
        "seedream-4.5": "Seedream 4.5",
        "seedream 4.0": "Seedream 4.0",
        "seedream4.0": "Seedream 4.0",
        "seedream-4.0": "Seedream 4.0",
        "kling o3": "Kling O3",
        "klingo3": "Kling O3",
        "kling-image-o3": "Kling O3",
        "kling 3.0": "Kling O3",
        "kling3.0": "Kling O3",
        "kling30": "Kling O3",
        "kling-image-v3": "Kling O3",
    }
    return aliases.get(raw, default_model if default_model in PIXVERSE_IMAGE_MODELS else DEFAULT_MODEL_NAME)


def kling_o3_panel_gerekli_mi(model_adi: str, referans_yolu: str | None) -> bool:
    return model_adi == "Kling O3" and bool(referans_yolu)


def kling_o3_panel_gorseli_olustur(kaynak_yolu: str, referans_yolu: str, index: int) -> str:
    os.makedirs(TEMP_PANEL_DIR, exist_ok=True)

    with Image.open(kaynak_yolu) as ana_img, Image.open(referans_yolu) as ref_img:
        ana = ana_img.convert("RGB")
        ref = ref_img.convert("RGB")

        hedef_yukseklik = max(ana.height, ref.height, 1024)

        def resize_keep_ratio(img: Image.Image, target_height: int) -> Image.Image:
            ratio = target_height / max(img.height, 1)
            target_width = max(1, int(img.width * ratio))
            sonuc = img.resize((target_width, target_height), Image.LANCZOS)
            max_panel_width = int(target_height * 0.95)
            if sonuc.width > max_panel_width:
                oran = max_panel_width / max(sonuc.width, 1)
                yeni_boyut = (
                    max(1, int(sonuc.width * oran)),
                    max(1, int(sonuc.height * oran)),
                )
                sonuc = sonuc.resize(yeni_boyut, Image.LANCZOS)
            return sonuc

        ana_r = resize_keep_ratio(ana, hedef_yukseklik)
        ref_r = resize_keep_ratio(ref, hedef_yukseklik)

        padding = max(24, hedef_yukseklik // 32)
        canvas_width = ana_r.width + ref_r.width + (padding * 3)
        canvas_height = max(ana_r.height, ref_r.height) + (padding * 2)
        canvas = Image.new("RGB", (canvas_width, canvas_height), (18, 22, 32))

        ana_y = padding + max(0, (canvas_height - (padding * 2) - ana_r.height) // 2)
        ref_y = padding + max(0, (canvas_height - (padding * 2) - ref_r.height) // 2)
        canvas.paste(ana_r, (padding, ana_y))
        canvas.paste(ref_r, (padding * 2 + ana_r.width, ref_y))

        panel_yolu = os.path.join(TEMP_PANEL_DIR, f"kling_o3_panel_{index}.png")
        canvas.save(panel_yolu, format="PNG")
        return panel_yolu


def kalite_coz(kalite_tercihi: str, model_adi: str, aspect_ratio: str | None = None) -> str:
    model_info = PIXVERSE_IMAGE_MODELS[model_adi]
    qualities = list(model_info["qualities"])
    if not qualities:
        return "1080p"

    tercih = str(kalite_tercihi or "").strip().lower()
    if tercih == "maksimum":
        quality_order = list(reversed(qualities))
    elif tercih == "yüksek" or tercih == "yuksek":
        midpoint = qualities[min(len(qualities) - 1, len(qualities) // 2)]
        quality_order = [midpoint] + [q for q in qualities if q != midpoint]
    else:
        quality_order = qualities

    by_quality = model_info.get("quality_aspect_ratios")
    if by_quality and aspect_ratio:
        for quality in quality_order:
            if aspect_ratio in by_quality.get(quality, []):
                return quality
    return quality_order[0]


def oran_to_float(value: str) -> float | None:
    raw = str(value or "").strip().lower()
    if raw == "auto":
        return None
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


def aspect_ratio_coz(image_path: str, fallback_ratio: str, model_adi: str) -> str:
    model_info = PIXVERSE_IMAGE_MODELS[model_adi]
    if model_info.get("supports_auto_ratio"):
        return "auto"

    supported = [ratio for ratio in model_info.get("aspect_ratios", []) if ":" in ratio]
    if not supported:
        return fallback_ratio or "1:1"

    fallback = str(fallback_ratio or "").strip()
    if fallback in supported:
        return fallback

    try:
        with Image.open(image_path) as img:
            width, height = img.size
        if width > 0 and height > 0:
            target = width / height
            best_ratio = min(
                supported,
                key=lambda ratio: abs(target - (oran_to_float(ratio) or target)),
            )
            return best_ratio
    except Exception:
        pass

    return supported[0]


def dosyadan_promptlari_oku(prompt_path: str) -> dict[int, str | dict[str, str]]:
    prompts = {}
    print(f"📄 Prompt Dosyası Okunuyor: {prompt_path}")

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip()
                pair_match = re.match(r"Görsel\s+(\d+)\s+(Start|End)\s*:\s*(.*)", clean_line, re.IGNORECASE)
                if pair_match:
                    prompt_no = int(pair_match.group(1))
                    frame_name = "start" if pair_match.group(2).strip().lower() == "start" else "end"
                    mevcut = prompts.get(prompt_no, "")
                    if not isinstance(mevcut, dict):
                        mevcut = {"shared": str(mevcut or "").strip(), "start": "", "end": ""}
                    mevcut[frame_name] = pair_match.group(3).strip()
                    prompts[prompt_no] = mevcut
                    continue
                match = re.match(r"Görsel\s+(\d+)\s*:\s*(.*)", clean_line, re.IGNORECASE)
                if match:
                    prompt_no = int(match.group(1))
                    prompt_text = match.group(2).strip()
                    mevcut = prompts.get(prompt_no, "")
                    if isinstance(mevcut, dict):
                        mevcut["shared"] = prompt_text
                        prompts[prompt_no] = mevcut
                    else:
                        prompts[prompt_no] = prompt_text
        print(f"✅ Toplam {len(prompts)} adet özel istem (prompt) bulundu.")
        return prompts
    except FileNotFoundError:
        print(f"❌ HATA: Prompt dosyası bulunamadı -> {prompt_path}")
        return {}
    except Exception as exc:
        print(f"❌ HATA: Dosya okunurken hata oluştu -> {exc}")
        return {}


def clone_prompt_has_value(value, require_transition_pair: bool = False) -> bool:
    if isinstance(value, dict):
        shared = str(value.get("shared") or "").strip()
        start = str(value.get("start") or "").strip()
        end = str(value.get("end") or "").strip()
        if require_transition_pair:
            return bool((start or shared) and (end or shared))
        return bool(shared or start or end)
    return bool(str(value or "").strip())


def clone_prompt_for_frame(value, frame_name: str) -> str:
    if isinstance(value, dict):
        shared = str(value.get("shared") or "").strip()
        start = str(value.get("start") or "").strip()
        end = str(value.get("end") or "").strip()
        if str(frame_name or "").strip().lower() == "start":
            return start or shared
        if str(frame_name or "").strip().lower() == "end":
            return end or shared
        return shared or start or end
    return str(value or "").strip()


def klasordeki_ilk_gorseli_bul(klasor_yolu: str) -> str | None:
    try:
        dosyalar = sorted(os.listdir(klasor_yolu), key=natural_sort_key)
        for dosya in dosyalar:
            if dosya.lower().endswith(SUPPORTED_IMAGE_EXTS):
                return os.path.join(klasor_yolu, dosya)
    except Exception:
        pass
    return None


def normalize_reference_slot(frame_name: str | None = None) -> str:
    raw = str(frame_name or "").strip().lower()
    if raw == "start":
        return "start"
    if raw == "end":
        return "end"
    return ""


def referans_gorsellerini_bul(referans_klasoru: str, gorsel_no: int, frame_name: str | None = None) -> list[str]:
    if not os.path.isdir(referans_klasoru):
        return []
    bulunan = []
    slot = normalize_reference_slot(frame_name)
    if slot:
        pattern = rf"^ref_{gorsel_no}_{slot}(?:__\d+)?\.(?:jpg|jpeg|png|webp|bmp|gif)$"
    else:
        pattern = rf"^ref_{gorsel_no}(?:__\d+)?\.(?:jpg|jpeg|png|webp|bmp|gif)$"
    try:
        for fname in sorted(os.listdir(referans_klasoru), key=natural_sort_key):
            if not fname.lower().endswith(SUPPORTED_IMAGE_EXTS):
                continue
            if re.match(pattern, fname, re.IGNORECASE):
                bulunan.append(os.path.join(referans_klasoru, fname))
    except Exception:
        return []
    return bulunan


def referans_gorsel_bul(referans_klasoru: str, gorsel_no: int, frame_name: str | None = None) -> str | None:
    bulunan = referans_gorsellerini_bul(referans_klasoru, gorsel_no, frame_name)
    return bulunan[0] if bulunan else None


def referans_paneli_olustur(referans_yollari: list[str], gorsel_no: int, frame_name: str | None = None) -> str:
    os.makedirs(TEMP_REFERENCE_PANEL_DIR, exist_ok=True)

    adet = len(referans_yollari)
    sutun = 1 if adet <= 2 else 2
    karo_boyutu = 640 if adet <= 2 else (560 if adet <= 4 else 480)
    bosluk = max(18, karo_boyutu // 18)
    satir = (adet + sutun - 1) // sutun

    canvas_width = (sutun * karo_boyutu) + ((sutun + 1) * bosluk)
    canvas_height = (satir * karo_boyutu) + ((satir + 1) * bosluk)
    canvas = Image.new("RGB", (canvas_width, canvas_height), (18, 22, 32))

    for index, referans_yolu in enumerate(referans_yollari):
        satir_no = index // sutun
        sutun_no = index % sutun
        x = bosluk + (sutun_no * (karo_boyutu + bosluk))
        y = bosluk + (satir_no * (karo_boyutu + bosluk))

        with Image.open(referans_yolu) as img:
            rgba = img.convert("RGBA")
            alt = Image.new("RGBA", rgba.size, (18, 22, 32, 255))
            alt.alpha_composite(rgba)
            duz = alt.convert("RGB")

        ic_boyut = max(1, karo_boyutu - (bosluk * 2))
        oran = min(ic_boyut / max(duz.width, 1), ic_boyut / max(duz.height, 1))
        yeni_boyut = (
            max(1, int(duz.width * oran)),
            max(1, int(duz.height * oran)),
        )
        kucuk = duz.resize(yeni_boyut, Image.LANCZOS)

        karo = Image.new("RGB", (karo_boyutu, karo_boyutu), (28, 33, 45))
        paste_x = max(0, (karo_boyutu - kucuk.width) // 2)
        paste_y = max(0, (karo_boyutu - kucuk.height) // 2)
        karo.paste(kucuk, (paste_x, paste_y))
        canvas.paste(karo, (x, y))

    max_kenar = 1800
    if max(canvas.size) > max_kenar:
        oran = max_kenar / max(canvas.size)
        yeni_tuval_boyutu = (
            max(1, int(canvas.width * oran)),
            max(1, int(canvas.height * oran)),
        )
        canvas = canvas.resize(yeni_tuval_boyutu, Image.LANCZOS)

    slot = normalize_reference_slot(frame_name)
    suffix = f"_{slot}" if slot else ""
    panel_yolu = os.path.join(TEMP_REFERENCE_PANEL_DIR, f"ref_panel_{gorsel_no}{suffix}.jpg")
    canvas.save(panel_yolu, format="JPEG", quality=92, optimize=True)
    return panel_yolu


def referans_gorselini_hazirla(referans_klasoru: str, gorsel_no: int, frame_name: str | None = None) -> tuple[str | None, int]:
    referans_yollari = referans_gorsellerini_bul(referans_klasoru, gorsel_no, frame_name)
    if not referans_yollari:
        return None, 0
    if len(referans_yollari) == 1:
        return referans_yollari[0], 1
    return referans_paneli_olustur(referans_yollari, gorsel_no, frame_name), len(referans_yollari)


def ayarlari_oku() -> dict:
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def pixverse_exe_bul() -> str | None:
    return shutil.which("pixverse") or None


def aktif_giris_klasoru_oku(settings: dict) -> str:
    kaynak = str(settings.get("gorsel_klonla_kaynak", "gorsel_analiz") or "").strip()
    if kaynak == "gorsel_olustur":
        return str(settings.get("gorsel_olustur_dir") or DEFAULT_INPUT_CREATE_DIR).strip()
    return str(settings.get("gorsel_analiz_dir") or DEFAULT_INPUT_ANALYZE_DIR).strip()


def hedef_cikti_klasoru_oku(settings: dict) -> str:
    return str(settings.get("klon_gorsel_dir") or DEFAULT_OUTPUT_DIR).strip()


def prompt_dosyasi_yolu_oku(settings: dict) -> str:
    return str(settings.get("gorsel_duzelt_txt") or DEFAULT_PROMPT_PATH).strip()


def referans_klasoru_oku(prompt_path: str) -> str:
    if prompt_path:
        return os.path.join(os.path.dirname(prompt_path), "referans")
    return os.path.join(os.path.dirname(DEFAULT_PROMPT_PATH), "referans")


def hedef_klasor_hazirla(target_dir: str, clear_existing: bool = True):
    os.makedirs(target_dir, exist_ok=True)
    if not clear_existing:
        return
    clear_image_files(target_dir)


def mevcut_klon_gorseli(target_dir: str) -> str | None:
    resolved = resolve_single_image(target_dir)
    return str(resolved) if resolved else None


def mevcut_transition_klon_gorselleri(target_dir: str) -> tuple[str | None, str | None]:
    start_image, end_image = resolve_transition_pair(target_dir)
    return (str(start_image) if start_image else None, str(end_image) if end_image else None)


def alt_klasorleri_listele(root_dir: str) -> list[str]:
    try:
        klasorler = [name for name in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, name))]
    except FileNotFoundError:
        return []
    klasorler.sort(key=natural_sort_key)
    return klasorler


def process_terminate(proc: subprocess.Popen | None):
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
    except Exception:
        pass


def komut_calistir(cmd: list[str], bekleme_mesaji: str, timeout_seconds: int) -> tuple[int, str, str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    print(f"   {bekleme_mesaji}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )

    baslangic = time.time()
    sonraki_bildirim = HEARTBEAT_SECONDS
    pause_bildirildi = False

    while proc.poll() is None:
        if stop_istegi_var_mi():
            process_terminate(proc)
            print("[STOP] Bitirme isteği alındı. Güvenli çıkış yapılıyor...")
            sys.exit(0)

        if os.path.exists(PAUSE_FLAG):
            if not pause_bildirildi:
                print("[PAUSE] PixVerse işlemi tamamlanınca duraklatma uygulanacak.")
                pause_bildirildi = True
        elif pause_bildirildi:
            print("[PAUSE] Devam ediliyor...")
            pause_bildirildi = False

        gecen = time.time() - baslangic
        if gecen >= sonraki_bildirim:
            print(f"   ... Bekleniyor ({int(gecen)} sn)")
            sonraki_bildirim += HEARTBEAT_SECONDS

        if timeout_seconds and gecen >= timeout_seconds:
            process_terminate(proc)
            raise TimeoutError(f"{bekleme_mesaji} zaman aşımına uğradı ({timeout_seconds} sn).")

        time.sleep(1)

    stdout, stderr = proc.communicate()
    return proc.returncode, stdout or "", stderr or ""


def pixverse_auth_dogrula(pixverse_exe: str) -> tuple[bool, str]:
    try:
        rc, stdout, stderr = komut_calistir(
            [pixverse_exe, "auth", "status", "--json"],
            "PixVerse oturumu doğrulanıyor...",
            30,
        )
    except Exception as exc:
        return False, str(exc)

    if rc != 0:
        detail = (stderr or stdout or "").strip()
        return False, detail or "PixVerse auth status başarısız."

    data = parse_json_output(stdout)
    if not data.get("authenticated"):
        return False, "PixVerse kimlik doğrulaması gerekli."

    email = str(data.get("email") or "").strip()
    credits = data.get("credits")
    if email:
        print(f"[INFO] PixVerse oturumu hazır: {email}")
    if credits is not None:
        print(f"[INFO] Kullanılabilir kredi: {credits}")
    return True, ""


def komut_hatasini_coz(stdout: str, stderr: str) -> str:
    data = parse_json_output(f"{stdout}\n{stderr}")
    for key in ("error", "message", "detail"):
        value = str(data.get(key) or "").strip()
        if value:
            return value

    merged = "\n".join(part.strip() for part in [stdout, stderr] if str(part or "").strip()).strip()
    if not merged:
        return "İşlem Başarısız"
    last_line = merged.splitlines()[-1].strip()
    return last_line or "İşlem Başarısız"


def hata_retry_icin_uygun_mu(detay: str) -> bool:
    mesaj = str(detay or "").strip().lower()
    if not mesaj:
        return True

    kalici_hata_kelimeleri = [
        "generation failed",
        "image generation failed",
        "status: 8",
        "unsupported",
        "invalid",
        "bad request",
        "supports up to",
        "reference image",
        "prompt violates",
        "safety",
    ]
    if any(kelime in mesaj for kelime in kalici_hata_kelimeleri):
        return False

    gecici_hata_kelimeleri = [
        "deadline exceeded",
        "timed out",
        "timeout",
        "try again later",
        "still processing",
        "still generating",
        "resource not ready",
        "not ready",
        "temporarily unavailable",
        "processing",
        "pending",
    ]
    return any(kelime in mesaj for kelime in gecici_hata_kelimeleri)


def yeni_indirilen_gorseli_bul(target_dir: str) -> str | None:
    adaylar = []
    try:
        for name in os.listdir(target_dir):
            if name.lower().endswith(SUPPORTED_IMAGE_EXTS):
                full_path = os.path.join(target_dir, name)
                adaylar.append((os.path.getmtime(full_path), full_path))
    except Exception:
        return None

    if not adaylar:
        return None
    adaylar.sort(key=lambda item: item[0], reverse=True)
    return adaylar[0][1]


def pixverse_video_icin_gorseli_normalize_et(image_path: str) -> str:
    try:
        with Image.open(image_path) as img:
            duzeltilmis = ImageOps.exif_transpose(img)
            width, height = duzeltilmis.size
            if width <= PIXVERSE_VIDEO_REFERENCE_MAX_SIDE and height <= PIXVERSE_VIDEO_REFERENCE_MAX_SIDE:
                return image_path

            oran = min(
                PIXVERSE_VIDEO_REFERENCE_MAX_SIDE / max(width, 1),
                PIXVERSE_VIDEO_REFERENCE_MAX_SIDE / max(height, 1),
            )
            yeni_boyut = (
                max(1, int(width * oran)),
                max(1, int(height * oran)),
            )
            kucuk = duzeltilmis.resize(yeni_boyut, Image.LANCZOS)

            ext = os.path.splitext(image_path)[1].lower()
            kaydet_format = "PNG"
            kaydet_kwargs: dict = {"optimize": True}

            if ext in {".jpg", ".jpeg"}:
                kaydet_format = "JPEG"
                kaydet_kwargs = {"quality": 92, "optimize": True}
                if kucuk.mode != "RGB":
                    kucuk = kucuk.convert("RGB")
            elif ext == ".webp":
                kaydet_format = "WEBP"
                kaydet_kwargs = {"quality": 92, "method": 6}

            kucuk.save(image_path, format=kaydet_format, **kaydet_kwargs)
            print(
                f"[INFO] PixVerse video limiti nedeniyle referans görsel küçültüldü: "
                f"{width}x{height} -> {yeni_boyut[0]}x{yeni_boyut[1]}"
            )
    except Exception as exc:
        print(f"[WARN] Referans görsel boyutu normalize edilemedi: {exc}")
    return image_path


def standart_dosya_adina_cevir(target_dir: str, image_path: str, target_stem: str = "frame_0001") -> str:
    hedef = standardize_output_image(image_path, target_dir, target_stem)
    hedef = pixverse_video_icin_gorseli_normalize_et(str(hedef))
    return hedef


def gorsel_indirmeyi_dene(
    pixverse_exe: str,
    asset_id: str,
    target_dir: str,
    toplam_timeout: int = 180,
    deneme_araligi: int = 10,
    clear_target: bool = True,
) -> str:
    hedef_klasor_hazirla(target_dir, clear_existing=clear_target)
    son_hata = "Görsel indirilemedi."
    son_deneme = time.time() + max(toplam_timeout, deneme_araligi)
    deneme_no = 0

    while time.time() <= son_deneme:
        deneme_no += 1
        try:
            rc, stdout, stderr = komut_calistir(
                [pixverse_exe, "asset", "download", asset_id, "--type", "image", "--dest", target_dir, "--json"],
                f"Oluşturulan görsel indiriliyor... (deneme {deneme_no})",
                90,
            )
            if rc == 0:
                indirilen_dosya = yeni_indirilen_gorseli_bul(target_dir)
                if indirilen_dosya and os.path.isfile(indirilen_dosya):
                    return indirilen_dosya
                son_hata = "İndirme tamamlandı ancak çıktı görseli bulunamadı."
            else:
                son_hata = komut_hatasini_coz(stdout, stderr)
        except Exception as exc:
            son_hata = str(exc).strip() or "Görsel indirilemedi."

        if not hata_retry_icin_uygun_mu(son_hata):
            raise RuntimeError(son_hata)

        if time.time() + deneme_araligi > son_deneme:
            break

        print(f"[WARN] Görsel henüz indirilebilir değil. {deneme_araligi} sn sonra tekrar denenecek...")
        time.sleep(deneme_araligi)

    raise RuntimeError(son_hata)


def ozet_satiri_uret(items: list[str]) -> str:
    return " | ".join(items) if items else "Yok"


def failure_satiri_uret(items: list[tuple[str, str]]) -> str:
    if not items:
        return "Yok"
    return " | ".join(f"{name} ({detail})" for name, detail in items)


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 60)
    print("   PIXVERSE CLI GÖRSEL KLONLAMA SİSTEMİ")
    print("=" * 60)

    pid_kaydet()
    bekle_pause_varsa()
    stop_kontrol_noktasinda_cik()

    settings = ayarlari_oku()
    prompt_path = prompt_dosyasi_yolu_oku(settings)
    input_root = aktif_giris_klasoru_oku(settings)
    output_root = hedef_cikti_klasoru_oku(settings)
    referans_root = referans_klasoru_oku(prompt_path)

    raw_model_name = settings.get("gorsel_klonlama_model") or settings.get("gorsel_model")
    model_name = normalize_image_model(
        raw_model_name,
        DEFAULT_MODEL_NAME,
    )
    if model_name not in PIXVERSE_IMAGE_MODELS:
        print(f"❌ HATA: Desteklenmeyen görsel klonlama modeli -> {model_name}")
        sys.exit(1)

    if str(raw_model_name or "").strip().lower() in {"kling 3.0", "kling3.0", "kling30", "kling-image-v3"}:
        print("[INFO] Kling 3.0, Gorsel Klonla icin kaldirildi. Otomatik olarak Kling O3 kullanilacak.")

    model_info = PIXVERSE_IMAGE_MODELS[model_name]
    kalite_tercihi = settings.get("gorsel_klonlama_kalitesi") or settings.get("gorsel_kalitesi", "Standart")
    boyut_tercihi = settings.get("gorsel_klonlama_boyutu") or settings.get("gorsel_boyutu", "16:9")
    boyut_fallback = str(boyut_tercihi or "16:9").strip()
    kalite_onizleme = kalite_coz(kalite_tercihi, model_name, boyut_fallback)
    transition_state = load_transition_state(CONTROL_DIR)
    transition_enabled = bool(transition_state.get("gorsel_klonla_transition_enabled", False))

    pixverse_exe = pixverse_exe_bul()
    if not pixverse_exe:
        print("❌ HATA: PixVerse CLI bulunamadı.")
        print("  -> Lütfen 'pixverse' komutunun sistemde kurulu ve erişilebilir olduğundan emin olun.")
        sys.exit(1)

    auth_ok, auth_detail = pixverse_auth_dogrula(pixverse_exe)
    if not auth_ok:
        print(f"❌ HATA: PixVerse oturumu doğrulanamadı -> {auth_detail}")
        sys.exit(1)

    prompts = dosyadan_promptlari_oku(prompt_path)
    if not prompts:
        print("⚠️ HATA: Promptlar yüklenemediği için işlem durduruluyor.")
        sys.exit(1)

    if not os.path.isdir(input_root):
        print(f"❌ HATA: Giriş görsel klasörü bulunamadı -> {input_root}")
        sys.exit(1)

    klasorler = alt_klasorleri_listele(input_root)
    if not klasorler:
        print(f"❌ HATA: İşlenecek klasör bulunamadı -> {input_root}")
        sys.exit(1)

    os.makedirs(output_root, exist_ok=True)

    print(f"[INFO] Kaynak klasör: {input_root}")
    print(f"[INFO] Çıktı klasör: {output_root}")
    print(f"[INFO] Model: {model_name} ({model_info['cli']})")
    print(f"[INFO] Kalite: {kalite}")
    print(f"[INFO] Referans klasörü: {referans_root}")
    print(f"[INFO] İşlenecek klasör sayısı: {len(klasorler)}")
    print(f"[INFO] Transition modu: {'Açık' if transition_enabled else 'Kapalı'}")

    basarili = []
    basarisiz = []
    atlandi = []

    for index, klasor_adi in enumerate(klasorler, start=1):
        bekle_pause_varsa()
        stop_kontrol_noktasinda_cik()

        full_klasor_yolu = os.path.join(input_root, klasor_adi)
        etiket = f"Görsel {index}"
        hedef_klon_klasor = os.path.join(output_root, f"Klon Görsel {index}")

        print(f"\n============================================================")
        print(f"İŞLEM {index}/{len(klasorler)}: {etiket}")
        print(f"KAYNAK KLASÖR: {klasor_adi}")
        print("============================================================")

        if transition_enabled and os.path.isdir(hedef_klon_klasor):
            mevcut_start, mevcut_end = mevcut_transition_klon_gorselleri(hedef_klon_klasor)
            if mevcut_start and mevcut_end:
                print(
                    "[SKIP] Zaten klonlanmış transition çıktısı bulundu: "
                    f"{os.path.basename(mevcut_start)}, {os.path.basename(mevcut_end)}"
                )
                atlandi.append(etiket)
                continue
            if mevcut_start or mevcut_end:
                print("[WARN] Eksik transition çıktısı bulundu. Klasör temizlenip yeniden oluşturulacak.")
                clear_image_files(hedef_klon_klasor)
        else:
            mevcut_klon = mevcut_klon_gorseli(hedef_klon_klasor) if os.path.isdir(hedef_klon_klasor) else None
            if mevcut_klon:
                print(f"[SKIP] Zaten klonlanmış çıktı bulundu: {os.path.basename(mevcut_klon)}")
                atlandi.append(etiket)
                continue

        if transition_enabled:
            kaynak_start, kaynak_end = resolve_transition_pair(full_klasor_yolu)
            if not (kaynak_start and kaynak_end):
                print(f"⚠️ Atlanıyor: start.png / end.png çifti bulunamadı ({klasor_adi})")
                atlandi.append(etiket)
                continue
            kaynak_gorseller = [("start", str(kaynak_start)), ("end", str(kaynak_end))]
        else:
            hedef_gorsel = resolve_single_image(full_klasor_yolu)
            if hedef_gorsel is None:
                print(f"⚠️ Atlanıyor: Desteklenen görsel dosyası bulunamadı ({klasor_adi})")
                atlandi.append(etiket)
                continue
            kaynak_gorseller = [("frame_0001", str(hedef_gorsel))]

        prompt_entry = prompts.get(index)
        if not clone_prompt_has_value(prompt_entry, require_transition_pair=transition_enabled):
            print(f"⚠️ Atlanıyor: 'Görsel {index}' için gerekli düzeltme promptu bulunamadı.")
            atlandi.append(etiket)
            continue

        print(f"🎛️ Model: {model_name}")
        print(f"🎚️ Kalite: {kalite_onizleme}")
        islem_basarili = True
        kaydedilen_yollar = []

        for kaynak_index, (target_stem, hedef_gorsel_yolu) in enumerate(kaynak_gorseller, start=1):
            aktif_prompt = clone_prompt_for_frame(prompt_entry, target_stem if transition_enabled else "default")
            referans_yolu, referans_adedi = referans_gorselini_hazirla(
                referans_root,
                index,
                target_stem if transition_enabled else None,
            )
            aspect_ratio = aspect_ratio_coz(hedef_gorsel_yolu, boyut_fallback, model_name)
            kalite = kalite_coz(kalite_tercihi, model_name, aspect_ratio)
            kling_o3_panel_modu = kling_o3_panel_gerekli_mi(model_name, referans_yolu)
            gonderilecek_gorsel = hedef_gorsel_yolu
            kare_etiketi = "Start Frame" if target_stem == "start" else "End Frame" if target_stem == "end" else "Görsel"

            if not aktif_prompt:
                detay = f"{kare_etiketi} için prompt bulunamadı"
                print(f"❌ {detay}")
                islem_basarili = False
                basarisiz.append((f"{etiket} - {kare_etiketi}", detay))
                break

            print(f"🖼️ {kare_etiketi}: {os.path.basename(hedef_gorsel_yolu)}")
            print(f"📝 {kare_etiketi} Prompt: {aktif_prompt}")
            print(f"📐 Oran: {aspect_ratio}")
            if model_info.get("cli") == "gpt-image-2.0" and kalite != kalite_onizleme:
                print(f"[INFO] GPT Image 2 uyumlu kalite kullanildi: {kalite_onizleme} -> {kalite}")
            if referans_yolu:
                if referans_adedi > 1:
                    print(f"📎 {kare_etiketi} için {referans_adedi} referans görsel tek panelde birleştirildi: {os.path.basename(referans_yolu)}")
                else:
                    print(f"📎 {kare_etiketi} için referans görsel kullanılıyor: {os.path.basename(referans_yolu)}")
            if kling_o3_panel_modu:
                panel_index = (index * 10) + kaynak_index
                gonderilecek_gorsel = kling_o3_panel_gorseli_olustur(hedef_gorsel_yolu, referans_yolu, panel_index)
                print(f"[INFO] Kling O3 panel modu aktif: {os.path.basename(gonderilecek_gorsel)}")

            kling_o3_ic_bekleme = model_name == "Kling O3"
            create_timeout_seconds = DEFAULT_TIMEOUT_SECONDS + 60 if kling_o3_ic_bekleme else 120
            komut = [
                pixverse_exe,
                "create",
                "image",
                "--prompt",
                aktif_prompt,
                "--model",
                model_info["cli"],
                "--quality",
                kalite,
                "--aspect-ratio",
                aspect_ratio,
                "--count",
                "1",
            ]
            if kling_o3_ic_bekleme:
                komut.extend(["--timeout", str(DEFAULT_TIMEOUT_SECONDS)])
            else:
                komut.append("--no-wait")
            komut.append("--json")
            komut.extend(["--image", gonderilecek_gorsel])
            if referans_yolu and not kling_o3_panel_modu:
                komut.extend(["--images", referans_yolu])

            try:
                rc, stdout, stderr = komut_calistir(
                    komut,
                    f"PixVerse create image isteği gönderiliyor... ({kare_etiketi})",
                    create_timeout_seconds,
                )
                if rc != 0:
                    raise RuntimeError(komut_hatasini_coz(stdout, stderr))

                data = parse_json_output(stdout or stderr)
                asset_id = str(data.get("image_id") or data.get("id") or "").strip()
                if not asset_id:
                    raise RuntimeError("PixVerse yanıtında image_id bulunamadı.")
                print(f"[INFO] PixVerse iş kimliği ({kare_etiketi}): {asset_id}")

                wait_hata = ""
                if not kling_o3_ic_bekleme:
                    rc, stdout, stderr = komut_calistir(
                        [pixverse_exe, "task", "wait", asset_id, "--type", "image", "--timeout", str(DEFAULT_TIMEOUT_SECONDS), "--json"],
                        f"PixVerse görseli oluşturuyor... ({kare_etiketi})",
                        DEFAULT_TIMEOUT_SECONDS + 30,
                    )
                    if rc != 0:
                        wait_hata = komut_hatasini_coz(stdout, stderr)
                        if not hata_retry_icin_uygun_mu(wait_hata):
                            raise RuntimeError(wait_hata)
                        print(f"[WARN] PixVerse wait adımı geçici hata döndü. İndirme ile kontrol edilecek -> {wait_hata}")

                indirilen_dosya = gorsel_indirmeyi_dene(
                    pixverse_exe,
                    asset_id,
                    hedef_klon_klasor,
                    toplam_timeout=240 if model_name == "Kling O3" else 180,
                    clear_target=(kaynak_index == 1),
                )

                standart_yol = standart_dosya_adina_cevir(hedef_klon_klasor, indirilen_dosya, target_stem=target_stem)
                kaydedilen_yollar.append(standart_yol)
                if wait_hata:
                    print(f"[INFO] PixVerse görseli wait hatasına rağmen başarıyla indirildi: {wait_hata}")
                print(f"✅ {kare_etiketi} kaydedildi: {standart_yol}")
            except Exception as exc:
                detay = str(exc).strip() or "İşlem Başarısız"
                print(f"❌ {kare_etiketi} oluşturulamadı: {detay}")
                islem_basarili = False
                basarisiz.append((f"{etiket} - {kare_etiketi}", detay))
                break

        if islem_basarili:
            basarili.append(etiket)
        elif transition_enabled:
            clear_image_files(hedef_klon_klasor)
            print(f"[WARN] Eksik transition çıktısı temizlendi: {hedef_klon_klasor}")

    print("\n" + "=" * 60)
    print("TÜM İŞLEMLER TAMAMLANDI")
    print("=" * 60)
    print(f"Başarılı: {len(basarili)} - {ozet_satiri_uret(basarili)}")
    print(f"Başarısız: {len(basarisiz)} - {failure_satiri_uret(basarisiz)}")
    print(f"Atlandı (Zaten mevcut): {len(atlandi)} - {ozet_satiri_uret(atlandi)}")
    print("=" * 60)


if __name__ == "__main__":
    main()

