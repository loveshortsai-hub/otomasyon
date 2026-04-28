import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Optional

# Windows konsol encoding sorununu önle
import sys as _sys
if hasattr(_sys.stdout, 'reconfigure'):
    try:
        _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


SCRIPT_DIR = Path(__file__).resolve().parent
ANA_SISTEM_DIR = SCRIPT_DIR.parent.parent
OTOMASYON_DIR = ANA_SISTEM_DIR.parent
VIDEO_OLUSTURMA_DIR = SCRIPT_DIR.parent
if str(ANA_SISTEM_DIR) not in sys.path:
    sys.path.insert(0, str(ANA_SISTEM_DIR))
if str(VIDEO_OLUSTURMA_DIR) not in sys.path:
    sys.path.insert(0, str(VIDEO_OLUSTURMA_DIR))

from pixverse_reference_image import ReferenceImagePreparationError, prepare_reference_image_for_upload
from pixverse_prompt_utils import build_prompt_variants, extract_json_error_text, first_meaningful_line, is_sensitive_info_error_message
from transition_utils import load_transition_state, normalize_video_mode, resolve_visual_inputs_for_prompt
from video_settings_override import load_video_settings_override_state, resolve_prompt_video_settings
CONTROL_DIR = ANA_SISTEM_DIR / "Otomasyon Çalıştırma" / ".control"
CONTROL_DIR.mkdir(parents=True, exist_ok=True)

PAUSE_FLAG = CONTROL_DIR / "PAUSE.flag"
STOP_FLAG = CONTROL_DIR / "STOP.flag"
STATE_FILE = CONTROL_DIR / "STATE.json"
DONE_FILE = CONTROL_DIR / "DONE.json"
FAILED_FILE = CONTROL_DIR / "FAILED.json"

SETTINGS_FILE = CONTROL_DIR / "settings.local.json"
_sets = {}
if SETTINGS_FILE.exists():
    try:
        import json
        with open(SETTINGS_FILE, "r", encoding="utf-8") as _f:
            _sets = json.load(_f)
    except:
        pass

PROMPT_ROOT = Path(_sets.get("prompt_dir", OTOMASYON_DIR / "Prompt"))
VIDEO_ROOT = OTOMASYON_DIR / "Video" / "Video"
REFERENCE_IMAGE_ROOT = Path(_sets.get("gorsel_klonlama_dir", OTOMASYON_DIR / "Görsel" / "Klon Görsel"))


VIDEO_SETTINGS_FILE = SCRIPT_DIR / "video_boyutu_süresi_ses.txt"
ACCOUNT_FILE = SCRIPT_DIR / "kayıt.txt"

PROMPT_FILE = "prompt.txt"
OUTPUT_META_FILE = "video_result.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
AUTH_ERROR_CODES = {10003}
POLL_INTERVAL_SECONDS = 30
SUPPORTED_DURATIONS = {3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}
SUPPORTED_QUALITIES = ["720p"]
SUPPORTED_ASPECT_RATIOS = ["16:9", "9:16", "1:1"]
DEFAULT_MODEL = "kling-3.0-standard"
DEFAULT_QUALITY = "720p"
MODEL_LABEL = "Kling 3.0"
FORCE_AUDIO_OFF = False
FORCE_MULTI_SHOT_OFF = True
SUBMIT_MAX_RETRIES = 3          # Görsel yükleme zaman aşımında toplam deneme sayısı
SUBMIT_RETRY_WAIT_SECONDS = 12  # Denemeler arası bekleme süresi (sn)
WAIT_TIMEOUT_SECONDS = 400      # İlk bekleme eşiği (PixVerse CLI timeout)
WAIT_MAX_SECONDS = 600          # Süreç ne olursa olsun mutlak üst sınır
DOWNLOAD_TIMEOUT_SECONDS = 180  # İndirme asılı kalırsa prompt başarısız sayılır


class ConfigError(Exception):
    pass


class UserFacingError(Exception):
    def __init__(
        self,
        status: str,
        reason: str,
        detail: str = "",
        duration: Optional[int] = None,
        result: str = "Video Başarısız",
    ):
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.detail = detail
        self.duration = duration
        self.result = result


def strip_ansi(text: str) -> str:
    # ANSI kaçış kodlarını temizle
    cleaned = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text or "")
    # \r (carriage return) ile oluşan terminal animasyon kalıntılarını temizle:
    # CLI progress animasyonları \r kullanır; pipe'a yönlendirildiğinde tüm
    # "çerçeveler" art arda yazılır. Her satırda yalnızca son segment kalır.
    lines = cleaned.split("\n")
    clean_lines = []
    for line in lines:
        parts = line.split("\r")
        clean_lines.append(parts[-1] if parts else line)
    return "\n".join(clean_lines)


def resolve_binary(name: str) -> str:
    candidates = [name]
    if os.name == "nt":
        candidates = [name, f"{name}.cmd", f"{name}.exe", f"{name}.bat"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    raise EnvironmentError(f"'{name}' bulunamadı. Kurulu olduğundan ve PATH içinde olduğundan emin ol.")


def prepare_command(cmd):
    if not cmd:
        return []
    resolved = list(cmd)
    first = resolved[0]
    if isinstance(first, str) and not any(sep in first for sep in ("/", "\\", ":")):
        try:
            resolved[0] = resolve_binary(first)
        except Exception:
            pass
    return [str(x) for x in resolved]


def run_command(cmd, check=False, capture_output=True, text=True, cwd=None, timeout=None):
    prepared_cmd = prepare_command(cmd)
    try:
        kwargs = {
            "capture_output": capture_output,
            "text": text,
            "shell": False,
            "cwd": str(cwd) if cwd else None,
        }
        if text:
            kwargs["encoding"] = "utf-8"
            kwargs["errors"] = "replace"
        if timeout is not None:
            kwargs["timeout"] = timeout
        result = subprocess.run(prepared_cmd, **kwargs)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            "Komut çalıştırılamadı: "
            + " ".join(prepared_cmd)
            + "\nMuhtemel sebep: PATH içinde görünmüyor veya .cmd/.exe olarak çözümlenemedi."
        ) from e

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Komut başarısız oldu: {' '.join(prepared_cmd)}\n"
            f"Çıkış kodu: {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    return result
def start_process(cmd, cwd=None):
    prepared_cmd = prepare_command(cmd)
    try:
        return subprocess.Popen(
            prepared_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd) if cwd else None,
            shell=False,
        )
    except FileNotFoundError as e:
        raise FileNotFoundError(
            "Komut çalıştırılamadı: "
            + " ".join(prepared_cmd)
            + "\nMuhtemel sebep: PATH içinde görünmüyor veya .cmd/.exe olarak çözümlenemedi."
        ) from e


def parse_json_from_output(output: str) -> dict:
    clean = strip_ansi((output or "")).strip()
    if not clean:
        raise ValueError("Boş çıktı")
    try:
        return json.loads(clean)
    except Exception:
        pass
    # JSON nesnesi içeren satırı ara
    match = re.search(r"(\{.*\})", clean, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Yedek: CLI bazen --json yerine düz metin çıktı verir.
    # "✅ Generation Task Created! video_id: 123, trace_id: abc-..." kalıbını yakala.
    task_match = re.search(r"video_id[:\s]+(\d+)", clean, re.IGNORECASE)
    if task_match:
        result: dict = {"video_id": task_match.group(1)}
        trace_match = re.search(r"trace_id[:\s]+([a-f0-9\-]+)", clean, re.IGNORECASE)
        if trace_match:
            result["trace_id"] = trace_match.group(1)
        return result
    task_id_match = re.search(r"task_id[:\s]+(\d+)", clean, re.IGNORECASE)
    if task_id_match:
        return {"task_id": task_id_match.group(1)}
    # Hata mesajını kısalt — ham CLI çıktısının tamamını log'a dökmemek için
    display = (clean[:300] + "...") if len(clean) > 300 else clean
    # Sadece ilk anlamlı satırı göster
    first_line = next((ln.strip() for ln in display.splitlines() if ln.strip()), display)
    raise ValueError(f"JSON çıktı ayrıştırılamadı: {first_line}")


def parse_cli_json_safely(text: str) -> dict:
    try:
        return parse_json_from_output(text)
    except Exception:
        return {}


def stop_istegi_var_mi() -> bool:
    return STOP_FLAG.exists()


def bekle_pause_varsa():
    paused_logged = False
    while PAUSE_FLAG.exists():
        if stop_istegi_var_mi():
            print("[STOP] Pause sırasında stop alındı. Güvenli çıkış yapılıyor...")
            raise SystemExit(0)
        if not paused_logged:
            print("[PAUSE] Duraklatıldı. Devam için PAUSE.flag silinmeli.")
            paused_logged = True
        time.sleep(0.2)
    if paused_logged:
        print("[PAUSE] Devam ediliyor...")


def stop_kontrol_noktasinda_cik():
    if stop_istegi_var_mi():
        print("[STOP] Bitirme isteği alındı. Güvenli çıkış yapılıyor...")
        raise SystemExit(0)


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {path}")
    return path.read_text(encoding="utf-8-sig").strip()


def read_json_file(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
    except Exception as e:
        print(f"[WARN] JSON okunamadı: {path.name} ({e})")
    return default


def write_json_file(path: Path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] JSON yazılamadı: {path.name} ({e})")


def state_yukle() -> dict:
    data = read_json_file(STATE_FILE, {})
    return data if isinstance(data, dict) else {}


def state_kaydet(state: dict):
    write_json_file(STATE_FILE, state)


def _normalize_prompt_name(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _calculate_contiguous_done_count(prompt_klasorleri, done_list) -> int:
    done_norm = {_normalize_prompt_name(x) for x in (done_list or []) if str(x).strip()}
    count = 0
    for klasor in prompt_klasorleri or []:
        if _normalize_prompt_name(klasor) in done_norm:
            count += 1
        else:
            break
    return count


def prompt_klasorlerini_listele() -> list[str]:
    try:
        klasorler = []
        if not PROMPT_ROOT.exists():
            print(f"HATA: Prompt klasörü bulunamadı: {PROMPT_ROOT}")
            return []

        for item in PROMPT_ROOT.iterdir():
            if item.is_dir() and item.name.startswith("Video Prompt"):
                prompt_file = item / PROMPT_FILE
                if prompt_file.exists():
                    klasorler.append(item.name)
                else:
                    print(f"UYARI: '{item.name}' klasöründe prompt.txt dosyası bulunamadı, atlanıyor.")

        klasorler.sort(key=lambda x: int("".join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)

        print(f"\nToplam {len(klasorler)} adet Video Prompt klasörü bulundu:")
        for klasor in klasorler:
            print(f"  - {klasor}")
        return klasorler
    except Exception as e:
        print(f"Klasör listeleme hatası: {e}")
        return []


def prompt_oku(prompt_klasor_adi: str) -> str:
    try:
        prompt_dosya_yolu = PROMPT_ROOT / prompt_klasor_adi / PROMPT_FILE
        raw = read_text_file(prompt_dosya_yolu)
        if not raw:
            raise ConfigError("prompt.txt bos")

        prompt_varyantlari = build_prompt_variants(raw)
        if not prompt_varyantlari:
            raise ConfigError("prompt.txt iceriginden gecerli prompt cikartilamadi")

        secilen_varyant = prompt_varyantlari[0]
        print(f"Prompt okundu [{secilen_varyant['label']}]: {len(secilen_varyant['prompt'])} karakter")
        for alternatif in prompt_varyantlari[1:]:
            print(f"[INFO] Alternatif prompt hazir: {alternatif['label']} ({len(alternatif['prompt'])} karakter)")
        return raw
    except Exception as e:
        print(f"Prompt dosyasi okuma hatasi: {e}")
        return None


def gorsel_bul(prompt_klasor_adi: str) -> Optional[Path]:
    try:
        visual_inputs = resolve_visual_inputs(prompt_klasor_adi)
        reference_image = visual_inputs.get("reference_image")
        if reference_image:
            reference_path = Path(reference_image)
            print(f"✓ Görsel bulundu: {reference_path}")
            return reference_path
        source_folder = visual_inputs.get("source_folder")
        if source_folder:
            print(f"Referans görsel klasörü bulundu ama tekli görsel çözülemedi: {source_folder}")
        else:
            print("Referans görsel klasörü bulunamadı (Tüm hedefler tarandı).")
        return None
    except Exception as e:
        print(f"Görsel arama hatası: {e}")
        return None


def resolve_visual_inputs(prompt_klasor_adi: str) -> dict:
    try:
        transition_state = load_transition_state(CONTROL_DIR)
        video_mode = normalize_video_mode(transition_state.get("video_mode"))
    except Exception:
        video_mode = "normal"
    return resolve_visual_inputs_for_prompt(
        prompt_klasor_adi,
        REFERENCE_IMAGE_ROOT,
        OTOMASYON_DIR,
        video_mode,
    )


def video_kayit_klasoru_olustur(prompt_klasor_adi: str) -> Optional[Path]:
    try:
        VIDEO_ROOT.mkdir(parents=True, exist_ok=True)
        en_buyuk_numara = 0
        for oge in VIDEO_ROOT.iterdir():
            if oge.is_dir() and oge.name.startswith("Video "):
                try:
                    numara = int(oge.name.split("Video ", 1)[1])
                    en_buyuk_numara = max(en_buyuk_numara, numara)
                except Exception:
                    continue
        yeni_klasor = VIDEO_ROOT / f"Video {en_buyuk_numara + 1}"
        print(f"✓ Hedef klasör yolu belirlendi: {yeni_klasor}")
        return yeni_klasor
    except Exception as e:
        print(f"Video klasörü belirleme hatası: {e}")
        return None


def parse_duration(value: str) -> int:
    normalized = str(value or "").strip().lower().replace(" ", "")
    match = re.fullmatch(r"(\d+)s", normalized)
    if not match:
        raise ConfigError(f"Süre biçimi hatalı: {value}.")

    duration = int(match.group(1))
    if duration in SUPPORTED_DURATIONS:
        return duration

    supported_text = ", ".join(str(x) for x in sorted(SUPPORTED_DURATIONS))
    raise ConfigError(f"Süre yalnızca şu değerlerden biri olabilir: {supported_text}. Gelen: {value}")


def read_video_settings() -> dict:
    lines = [line.strip() for line in read_text_file(VIDEO_SETTINGS_FILE).splitlines() if line.strip()]
    if len(lines) < 2:
        raise ConfigError("video_boyutu_süresi_ses.txt en az 2 satır içermeli: boyut ve süre")

    aspect_ratio = lines[0]
    duration = parse_duration(lines[1])
    ses = lines[2].lower() if len(lines) > 2 else "kapalı"
    quality = lines[3] if len(lines) > 3 else DEFAULT_QUALITY
    model = lines[4] if len(lines) > 4 else DEFAULT_MODEL

    if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        raise ConfigError(f"Boyut yalnızca şu değerlerden biri olabilir: {', '.join(SUPPORTED_ASPECT_RATIOS)}")

    return {
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "ses": ses,
        "quality": quality,
        "model": model,
    }


def mask_email(email: str) -> str:
    email = (email or "").strip()
    if "@" not in email:
        return "(geçersiz e-posta biçimi)"
    name, domain = email.split("@", 1)
    masked = name[:2] + "*" * max(0, len(name) - 2) if len(name) > 2 else name[:1] + "*" * max(0, len(name) - 1)
    return f"{masked}@{domain}"


def read_account() -> dict:
    try:
        lines = [line.strip() for line in read_text_file(ACCOUNT_FILE).splitlines() if line.strip()]
    except FileNotFoundError:
        return {"email_masked": "", "password_present": False}
    email = lines[0] if len(lines) >= 1 else ""
    password_present = len(lines) >= 2 and bool(lines[1])
    return {"email_masked": mask_email(email) if email else "", "password_present": password_present}


def show_account_context(account_info: dict):
    print("\n=== Klasörden Okunan Hesap Bilgisi ===")
    print(f"E-posta: {account_info.get('email_masked') or '(kayıt.txt içinde e-posta yok)'}")
    print(f"Şifre satırı mevcut mu: {'Evet' if account_info.get('password_present') else 'Hayır'}")
    print("Not: Resmi PixVerse CLI giriş yöntemi tarayıcı tabanlı OAuth'tur; kayıt.txt yalnızca bilgi amaçlı okunur.")
    print("======================================\n")


def normalize_flag_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    replacements = {
        "\u0131": "i",
        "\u00e7": "c",
        "\u011f": "g",
        "\u00f6": "o",
        "\u015f": "s",
        "\u00fc": "u",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if ch.isascii())


def resolve_generation_flags(settings: dict) -> dict:
    requested_audio = normalize_flag_text(settings.get("ses", "kapali")) in (
        "acik", "evet", "yes", "true", "on"
    )
    return {
        "requested_audio": requested_audio,
        "audio": requested_audio,
        "multi_shot": False if FORCE_MULTI_SHOT_OFF else True,
    }


def validate_model_options(model: str, quality: str, duration: int, aspect_ratio: str):
    if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        raise ConfigError(f"Boyut yalnızca şu değerlerden biri olabilir: {', '.join(SUPPORTED_ASPECT_RATIOS)}")
    if quality not in SUPPORTED_QUALITIES:
        raise ConfigError(f"{model} için quality yalnızca şu değerlerden biri olabilir: {', '.join(SUPPORTED_QUALITIES)}")
    if duration not in SUPPORTED_DURATIONS:
        raise ConfigError(f"{model} için duration yalnızca şu değerlerden biri olabilir: {', '.join(str(x) for x in sorted(SUPPORTED_DURATIONS))}")
    if model != DEFAULT_MODEL:
        raise ConfigError(f"Model yalnızca {DEFAULT_MODEL} olabilir.")


def auth_files_dir() -> Path:
    return Path.home() / ".pixverse"


def clear_local_auth_cache():
    auth_dir = auth_files_dir()
    if auth_dir.exists():
        shutil.rmtree(auth_dir, ignore_errors=True)
        print(f"Eski yerel oturum klasörü temizlendi: {auth_dir}")


def is_auth_valid(verbose: bool = False) -> bool:
    status = run_command(["pixverse", "auth", "status"], check=False)
    info = run_command(["pixverse", "account", "info"], check=False)
    if verbose:
        print(f"auth status çıkış kodu: {status.returncode}")
        if status.stdout.strip():
            print(strip_ansi(status.stdout).strip())
        if status.stderr.strip():
            print(strip_ansi(status.stderr).strip())
        print(f"account info çıkış kodu: {info.returncode}")
        if info.stdout.strip():
            print(strip_ansi(info.stdout).strip())
        if info.stderr.strip():
            print(strip_ansi(info.stderr).strip())
    return status.returncode == 0 and info.returncode == 0


def ensure_logged_in(force_relogin: bool = False):
    if force_relogin:
        clear_local_auth_cache()

    if is_auth_valid(verbose=False):
        print("Giriş yapıldı")
        return

    print("PixVerse girişi gerekiyor. Tarayıcıda yetkilendirme açılıyor...")
    login = run_command(["pixverse", "auth", "login"], check=False, capture_output=False)
    if login.returncode != 0:
        raise RuntimeError("PixVerse giriş işlemi başarısız oldu.")
    if not is_auth_valid(verbose=False):
        raise RuntimeError("Giriş sonrası oturum doğrulanamadı.")
    print("Giriş yapıldı")


def build_video_command(
    prompt: str,
    model: str,
    quality: str,
    duration: int,
    aspect_ratio: str,
    reference_image: Optional[Path] = None,
    no_wait: bool = False,
    audio: bool = False,
    multi_shot: bool = False,
) -> list:
    cmd = [
        "pixverse", "create", "video",
        "--prompt", prompt,
    ]
    if reference_image is not None:
        cmd.extend(["--image", str(reference_image)])
    cmd.extend([
        "--model", model,
        "--quality", quality,
        "--aspect-ratio", aspect_ratio,
        "--duration", str(duration),
    ])
    # Audio flag follows the saved user setting directly.
    # Multi-shot stays explicit because these wrappers keep it disabled.
    cmd.append("--audio" if audio else "--no-audio")
    cmd.append("--multi-shot" if multi_shot else "--no-multi-shot")
    cmd.append("--json")
    if no_wait:
        cmd.append("--no-wait")
    return cmd

def build_transition_command(
    prompt: str,
    model: str,
    quality: str,
    duration: int,
    start_image: Path,
    end_image: Path,
    no_wait: bool = False,
    audio: bool = False,
) -> list:
    cmd = [
        "pixverse", "create", "transition",
        "--images", str(start_image), str(end_image),
        "--prompt", prompt,
        "--model", model,
        "--quality", quality,
        "--duration", str(duration),
    ]
    cmd.append("--audio" if audio else "--no-audio")
    cmd.append("--json")
    if no_wait:
        cmd.append("--no-wait")
    return cmd


def response_has_auth_error(stdout: str) -> bool:
    try:
        data = parse_json_from_output(stdout)
        error_text = str(data.get("error") or "")
        return data.get("code") in AUTH_ERROR_CODES or "not login" in error_text.lower()
    except Exception:
        return False


def build_user_error(stage: str, stdout: str = "", stderr: str = "", return_code: Optional[int] = None, elapsed: Optional[int] = None):
    clean_stdout = strip_ansi(stdout or "").strip()
    clean_stderr = strip_ansi(stderr or "").strip()
    joined = f"{clean_stdout}\n{clean_stderr}".strip()
    data = parse_cli_json_safely(clean_stdout) or parse_cli_json_safely(clean_stderr)
    error_text = extract_json_error_text(data)
    error_code = data.get("code")
    haystack = f"{error_text}\n{joined}".lower()
    stage_lc = (stage or "").casefold()

    if error_code in AUTH_ERROR_CODES or "not logged in" in haystack or "user is not login" in haystack:
        return UserFacingError(
            status=stage,
            reason="Oturum gecersiz veya suresi dolmus",
            detail="Tekrar giris yapilmali.",
            result="Video Basarisiz",
        )

    if error_code == 400018 or "cannot exceed" in haystack or "prompt too long" in haystack or ("character" in haystack and "limit" in haystack):
        return UserFacingError(
            status=stage,
            reason="Prompt karakter siniri asildi",
            detail="PixVerse tarafindan prompt uzunlugu reddedildi.",
            result="Video Basarisiz",
        )

    if any(p in haystack for p in ["insufficient credit", "not enough credit", "credit balance", "payment required", "quota exceeded", "insufficient balance", "all credits have been used up", "credits have been used", "purchase credits"]):
        return UserFacingError(
            status=stage,
            reason="Yetersiz Video Uretme Kredisi (Kredinizi Yenileyin)",
            detail="Video uretme krediniz tukendi. Lutfen kredinizi yenileyerek tekrar deneyin.",
            result="Video Basarisiz",
        )

    if (
        "responsetimeouterror" in haystack
        or "response timeout for" in haystack
        or ("response timeout" in haystack and ("oss" in haystack or "ali" in haystack or "ms" in haystack))
    ):
        return UserFacingError(
            status=stage,
            reason="Referans Gorsel Yukleme Zaman Asimi",
            detail="Gorsel bulut depolama alanina yuklenirken baglanti zaman asimina ugradi.",
            result="Video Basarisiz",
        )

    timeout_match = re.search(r"polling timed out after\s+(\d+)s", haystack, flags=re.IGNORECASE)
    if timeout_match:
        seconds = int(timeout_match.group(1))
        return UserFacingError(
            status=stage,
            reason="Beklenen surede olusturulamadi",
            detail=f"{seconds} saniye icinde tamamlanmis sonuc alinamadi.",
            duration=seconds,
            result="Video Basarisiz",
        )

    generation_failed_match = re.search(r"video generation failed\s*\(status:\s*(\d+)", haystack, flags=re.IGNORECASE)
    if generation_failed_match:
        failed_status = generation_failed_match.group(1)
        detail = "Video olusturulamadi (Bazi aksakliklar olmus olabilir)"
        if failed_status == "7":
            detail = "Video olusturulamadi (Icerik kontrolune takilmis olabilir)"
        return UserFacingError(
            status=stage,
            reason="Islem tamamlanamadi",
            detail=detail,
            duration=elapsed,
            result="Video Basarisiz",
        )

    if "assertion failed" in haystack:
        return UserFacingError(
            status=stage,
            reason="PixVerse CLI ic hatasi olustu",
            detail="Komut satiri tarafinda beklenmeyen bir hata olustu.",
            result="Video Basarisiz",
        )

    if is_sensitive_info_error_message(haystack):
        return UserFacingError(
            status=stage,
            reason="Prompt hassas bilgi nedeniyle reddedildi",
            detail=error_text or first_meaningful_line(clean_stderr) or first_meaningful_line(clean_stdout) or "PixVerse promptta hassas bilgi algiladi.",
            result="Video Basarisiz",
        )

    if "video indirme" in stage_lc:
        return UserFacingError(
            status=stage,
            reason="Video indirilemedi",
            detail="Video olusturuldu ancak indirme tamamlanamadi.",
            result="Indirme Basarisiz",
        )

    if "sonuc" in stage_lc:
        return UserFacingError(
            status=stage,
            reason="Sonuc verisi okunamadi",
            detail="Olusturma bitti ancak sonuc bilgisi cozumlenemedi.",
            duration=elapsed,
            result="Video Durumu Belirsiz",
        )

    generic_detail = error_text or first_meaningful_line(clean_stderr) or first_meaningful_line(clean_stdout)
    if not generic_detail:
        if any(str(value or "").strip() in {"{}", "{", "}"} for value in (clean_stdout, clean_stderr)):
            generic_detail = "CLI bos hata yaniti dondurdu. Bu genelde prompt ya da referans gorsel PixVerse tarafinda reddedildiginde gorulur."
        else:
            generic_detail = "Beklenmeyen bir hata olustu."

    return UserFacingError(
        status=stage,
        reason="Islem tamamlanamadi",
        detail=generic_detail[:180],
        duration=elapsed,
        result="Video Basarisiz",
    )


def print_user_error(err: UserFacingError):
    print("")
    print(f"HATA DURUMU: {err.status}")
    print(f"SEBEP      : {err.reason}")
    if err.duration is not None:
        print(f"SÜRE       : {err.duration} sn")
    if err.detail:
        print(f"DETAY      : {err.detail}")
    print(f"SONUÇ      : {err.result}")


def _is_upload_timeout_error(err: UserFacingError) -> bool:
    """Görsel yükleme zaman aşımı hatası mı?"""
    return "zaman aşımı" in (err.reason or "").lower()


def submit_generation(cmd, output_dir: Path) -> dict:
    last_err: Optional[UserFacingError] = None

    for attempt in range(1, SUBMIT_MAX_RETRIES + 1):
        result = run_command(cmd, check=False, cwd=output_dir)
        if response_has_auth_error(result.stdout):
            print("Oturum yenileniyor...")
            ensure_logged_in(force_relogin=True)
            result = run_command(cmd, check=False, cwd=output_dir)

        if result.returncode != 0 or response_has_auth_error(result.stdout):
            err = build_user_error(
                stage="Prompt gönderme",
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
            if _is_upload_timeout_error(err) and attempt < SUBMIT_MAX_RETRIES:
                print(f"[WARN] Görsel yükleme zaman aşımı (Deneme {attempt}/{SUBMIT_MAX_RETRIES}). {SUBMIT_RETRY_WAIT_SECONDS} sn sonra tekrar deneniyor...")
                time.sleep(SUBMIT_RETRY_WAIT_SECONDS)
                last_err = err
                continue
            raise err

        try:
            return parse_json_from_output(result.stdout)
        except ValueError:
            err = build_user_error(
                stage="Prompt gönderme",
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
            if _is_upload_timeout_error(err) and attempt < SUBMIT_MAX_RETRIES:
                print(f"[WARN] Görsel yükleme zaman aşımı (Deneme {attempt}/{SUBMIT_MAX_RETRIES}). {SUBMIT_RETRY_WAIT_SECONDS} sn sonra tekrar deneniyor...")
                time.sleep(SUBMIT_RETRY_WAIT_SECONDS)
                last_err = err
                continue
            raise err

    raise last_err


def _terminate_subprocess(process: subprocess.Popen):
    try:
        process.terminate()
        process.wait(timeout=2)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _make_wait_timeout_error(elapsed: Optional[int] = None) -> UserFacingError:
    duration = WAIT_MAX_SECONDS if elapsed is None else max(1, int(elapsed))
    return UserFacingError(
        status="Video oluşturma bekleme",
        reason="Beklenen sürede oluşturulamadı",
        detail=f"{WAIT_MAX_SECONDS} saniye içinde tamamlanmış sonuç alınamadı.",
        duration=duration,
        result="Video Başarısız",
    )


def _is_wait_timeout_error(err: UserFacingError) -> bool:
    return "beklenen sürede oluşturulamadı" in (err.reason or "").casefold()


def _start_wait_process(task_or_video_id: Any, output_dir: Path, timeout_seconds: int) -> subprocess.Popen:
    timeout_value = max(1, int(timeout_seconds))
    return start_process(
        ["pixverse", "task", "wait", str(task_or_video_id), "--json", "--timeout", str(timeout_value)],
        cwd=output_dir,
    )


def wait_for_completion(task_or_video_id: Optional[Any], output_dir: Path) -> dict:
    if task_or_video_id is None or str(task_or_video_id).strip() == "":
        raise UserFacingError(
            status="Video oluşturma bekleme",
            reason="Görev kimliği alınamadı",
            detail="Bekleme işlemi başlatılamadı.",
            result="Video Başarısız",
        )

    process = _start_wait_process(task_or_video_id, output_dir, WAIT_TIMEOUT_SECONDS)
    print("Video oluşturuluyor")

    start_time = time.monotonic()
    next_log_at = POLL_INTERVAL_SECONDS
    soft_timeout_logged = False
    wait_timeout_retry_used = False

    while True:
        bekle_pause_varsa()
        if stop_istegi_var_mi():
            _terminate_subprocess(process)
            print("[STOP] Video oluşturma beklemesi sonlandırıldı.")
            raise SystemExit(0)

        elapsed = int(time.monotonic() - start_time)
        if not soft_timeout_logged and elapsed >= WAIT_TIMEOUT_SECONDS:
            soft_timeout_logged = True
            if WAIT_MAX_SECONDS > WAIT_TIMEOUT_SECONDS:
                print(
                    f"[WARN] Video oluşturma {WAIT_TIMEOUT_SECONDS} sn'yi geçti. "
                    f"{WAIT_MAX_SECONDS} sn'ye kadar ek süre bekleniyor..."
                )

        if elapsed >= WAIT_MAX_SECONDS:
            _terminate_subprocess(process)
            raise _make_wait_timeout_error(elapsed)

        return_code = process.poll()
        if return_code is not None:
            stdout, stderr = process.communicate()
            if return_code != 0:
                err = build_user_error(
                    stage="Video oluşturma bekleme",
                    stdout=stdout,
                    stderr=stderr,
                    return_code=return_code,
                    elapsed=elapsed,
                )
                remaining = WAIT_MAX_SECONDS - elapsed
                if _is_wait_timeout_error(err) and not wait_timeout_retry_used and remaining > 0:
                    wait_timeout_retry_used = True
                    print(
                        f"[WARN] Bekleme {elapsed} sn sonunda tamamlanmadı. "
                        f"Son {remaining} sn için tekrar kontrol ediliyor..."
                    )
                    process = _start_wait_process(task_or_video_id, output_dir, remaining)
                    continue
                if _is_wait_timeout_error(err) and elapsed >= WAIT_MAX_SECONDS:
                    raise _make_wait_timeout_error(elapsed)
                raise err
            try:
                data = parse_json_from_output(stdout)
            except Exception:
                raise build_user_error(
                    stage="Video oluşturma sonucu",
                    stdout=stdout,
                    stderr=stderr,
                    return_code=return_code,
                    elapsed=elapsed,
                )
            print(f"Durum: video oluşturma tamamlandı | {elapsed} sn sürdü")
            return data

        if elapsed >= next_log_at:
            print(f"Durum: oluşturuluyor | {elapsed} sn geçti")
            next_log_at += POLL_INTERVAL_SECONDS

        time.sleep(1)

def download_asset_if_possible(video_id: Optional[Any], output_dir: Path) -> Optional[dict]:
    if video_id is None or str(video_id).strip() == "":
        return None
    bekle_pause_varsa()
    stop_kontrol_noktasinda_cik()
    print("Video indiriliyor...")
    try:
        result = run_command(
            ["pixverse", "asset", "download", str(video_id), "--json"],
            check=False,
            cwd=output_dir,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise UserFacingError(
            status="Video indirme",
            reason="Video indirme zaman aşımı",
            detail=f"İndirme {DOWNLOAD_TIMEOUT_SECONDS} saniye içinde tamamlanamadı.",
            duration=DOWNLOAD_TIMEOUT_SECONDS,
            result="İndirme Başarısız",
        )
    if result.returncode != 0:
        raise build_user_error(
            stage="Video indirme",
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
        )
    print("Video indirildi")
    try:
        return parse_json_from_output(result.stdout)
    except Exception:
        return {"raw_output": strip_ansi(result.stdout).strip()}

def generate_video_for_prompt(
    prompt_klasor_adi: str,
    prompt: str,
    settings: dict,
    reference_image: Optional[Path],
    output_dir: Path,
    auto_download: bool = True,
    visual_inputs: Optional[dict] = None,
) -> dict:
    validate_model_options(settings["model"], settings["quality"], settings["duration"], settings["aspect_ratio"])

    output_dir.mkdir(parents=True, exist_ok=True)

    visual_payload = visual_inputs if isinstance(visual_inputs, dict) else {}
    generation_mode = normalize_video_mode(visual_payload.get("mode") or "normal")
    start_image_raw = visual_payload.get("start_image")
    end_image_raw = visual_payload.get("end_image")
    start_image = Path(start_image_raw) if start_image_raw else None
    end_image = Path(end_image_raw) if end_image_raw else None
    prepared_reference_image = reference_image
    prepared_start_image = start_image
    prepared_end_image = end_image

    if generation_mode == "transition":
        if not (start_image and end_image):
            raise UserFacingError(
                status="Referans gorsel",
                reason="Start End Frame bulunamadi",
                detail="Transition modu aktif ancak start.png ve end.png gerekli.",
                result="Video Basarisiz",
            )
        try:
            prepared_start_image = prepare_reference_image_for_upload(start_image, output_dir)
            prepared_end_image = prepare_reference_image_for_upload(end_image, output_dir)
        except ReferenceImagePreparationError as exc:
            raise UserFacingError(
                status="Referans gorsel hazirlama",
                reason="Transition frame'ler PixVerse icin hazirlanamadi",
                detail=str(exc),
                result="Video Basarisiz",
            ) from exc
        print(f"Start frame bulundu: {start_image}")
        print(f"End frame bulundu: {end_image}")
        if prepared_start_image != start_image:
            print(f"[INFO] Start frame PixVerse icin hazirlandi: {prepared_start_image}")
        if prepared_end_image != end_image:
            print(f"[INFO] End frame PixVerse icin hazirlandi: {prepared_end_image}")
    elif reference_image:
        try:
            prepared_reference_image = prepare_reference_image_for_upload(reference_image, output_dir)
        except ReferenceImagePreparationError as exc:
            raise UserFacingError(
                status="Referans gorsel hazirlama",
                reason="Referans gorsel PixVerse icin hazirlanamadi",
                detail=str(exc),
                result="Video Basarisiz",
            ) from exc
        print(f"Referans gorsel bulundu: {reference_image}")
        if prepared_reference_image != reference_image:
            print(f"[INFO] Referans gorsel PixVerse icin hazirlandi: {prepared_reference_image}")
    else:
        print("Referans gorsel bulunamadi; yalniz metin prompt ile denenecek.")

    flags = resolve_generation_flags(settings)
    print(f"Ses ayari: {'acik' if flags['audio'] else 'kapali'} (--{'audio' if flags['audio'] else 'no-audio'} gonderilecek)")
    print(f"Multi-shot ayari: {'acik' if flags['multi_shot'] else 'kapali'} (--{'multi-shot' if flags['multi_shot'] else 'no-multi-shot'} gonderilecek)")

    prompt_varyantlari = build_prompt_variants(prompt)
    if not prompt_varyantlari:
        raise UserFacingError(
            status="Prompt hazirlama",
            reason="Prompt olusturulamadi",
            detail="prompt.txt iceriginden gecerli bir prompt cikartilamadi.",
            result="Video Basarisiz",
        )

    submit_data = None
    used_prompt_variant = prompt_varyantlari[0]
    last_submit_error: Optional[UserFacingError] = None

    for index, varyant in enumerate(prompt_varyantlari, start=1):
        print(f"Prompt varyanti: {varyant['label']} ({len(varyant['prompt'])} karakter)")
        if index > 1:
            print("[WARN] Onceki prompt varyanti reddedildi, alternatif varyant deneniyor...")

        if generation_mode == "transition":
            print(
                "Komut ozeti: "
                f"model={settings['model']}, quality={settings['quality']}, duration={settings['duration']}s, "
                f"transition=start+end, audio={'acik' if flags['audio'] else 'kapali'}"
            )
            submit_cmd = build_transition_command(
                varyant["prompt"],
                settings["model"],
                settings["quality"],
                settings["duration"],
                prepared_start_image,
                prepared_end_image,
                no_wait=True,
                audio=flags["audio"],
            )
        else:
            print(
                "Komut ozeti: "
                f"model={settings['model']}, quality={settings['quality']}, "
                f"aspect_ratio={settings['aspect_ratio']}, duration={settings['duration']}s, "
                f"image={'var' if prepared_reference_image else 'yok'}"
            )
            submit_cmd = build_video_command(
                varyant["prompt"],
                settings["model"],
                settings["quality"],
                settings["duration"],
                settings["aspect_ratio"],
                prepared_reference_image,
                no_wait=True,
                audio=flags["audio"],
                multi_shot=flags["multi_shot"],
            )
        bekle_pause_varsa()
        stop_kontrol_noktasinda_cik()
        print("Prompt gonderildi")
        try:
            submit_data = submit_generation(submit_cmd, output_dir)
            used_prompt_variant = varyant
            break
        except UserFacingError as exc:
            last_submit_error = exc
            next_variant = prompt_varyantlari[index] if index < len(prompt_varyantlari) else None
            can_retry = (
                next_variant is not None
                and (
                    is_sensitive_info_error_message(exc.reason)
                    or is_sensitive_info_error_message(exc.detail)
                )
            )
            if can_retry:
                print(f"[WARN] PixVerse promptta hassas bilgi algiladi. Siradaki varyant denenecek: {next_variant['label']}.")
                continue
            raise

    if submit_data is None:
        raise last_submit_error or UserFacingError(
            status="Prompt gonderme",
            reason="Islem tamamlanamadi",
            detail="Prompt PixVerse'e gonderilemedi.",
            result="Video Basarisiz",
        )

    task_id = submit_data.get("task_id") or submit_data.get("video_id") or submit_data.get("id")
    wait_result = wait_for_completion(task_id, output_dir)
    video_id = wait_result.get("video_id") or wait_result.get("id") or task_id

    download_result = None
    if auto_download:
        download_result = download_asset_if_possible(video_id, output_dir)

    final_meta = {
        "prompt_folder": prompt_klasor_adi,
        "output_dir": str(output_dir),
        "model": settings["model"],
        "quality": settings["quality"],
        "settings": settings,
        "generation_mode": generation_mode,
        "reference_image": str(reference_image) if reference_image else None,
        "prepared_reference_image": str(prepared_reference_image) if prepared_reference_image else None,
        "start_image": str(start_image) if start_image else None,
        "end_image": str(end_image) if end_image else None,
        "prepared_start_image": str(prepared_start_image) if prepared_start_image else None,
        "prepared_end_image": str(prepared_end_image) if prepared_end_image else None,
        "prompt_variant": used_prompt_variant["name"],
        "prompt_length": len(used_prompt_variant["prompt"]),
        "submit_result": submit_data,
        "wait_result": wait_result,
        "download_result": download_result,
        "searched_folders": visual_payload.get("searched_folders"),
        "source_folder": str(visual_payload.get("source_folder")) if visual_payload.get("source_folder") else None,
    }
    meta_path = output_dir / OUTPUT_META_FILE
    meta_path.write_text(json.dumps(final_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return final_meta


def update_tracking_files(prompt_klasorleri: list[str], done: list[str], failed_entries: list[dict], state: dict):
    pixverse_state = state.setdefault("pixverse_state", {})
    pixverse_state["done"] = list(done)
    pixverse_state["failed"] = list(failed_entries)
    pixverse_state["last_success"] = _calculate_contiguous_done_count(prompt_klasorleri, done)
    state["pixverse_state"] = pixverse_state
    state_kaydet(state)
    write_json_file(DONE_FILE, list(done))
    write_json_file(FAILED_FILE, list(failed_entries))


def kling_30_toplu(auto_download: bool = True, force_relogin: bool = False):
    basarisiz_islemler: list[str] = []
    basarili_islemler: list[str] = []
    failed_entries: list[dict] = []

    account_info = read_account()
    show_account_context(account_info)

    prompt_klasorleri = prompt_klasorlerini_listele()
    if not prompt_klasorleri:
        print("\nHATA: İşlenecek Video Prompt klasörü bulunamadı!")
        return

    bekle_pause_varsa()
    stop_kontrol_noktasinda_cik()

    state = state_yukle()
    pixverse_state = state.get("pixverse_state", {}) if isinstance(state.get("pixverse_state", {}), dict) else {}
    done = pixverse_state.get("done", [])
    if not isinstance(done, list):
        done = []

    done_norm = {_normalize_prompt_name(x) for x in done if str(x).strip()}
    done = [klasor for klasor in prompt_klasorleri if _normalize_prompt_name(klasor) in done_norm]
    basarili_islemler = list(done)
    if basarili_islemler:
        print(f"[INFO] Önceki oturumdan {len(basarili_islemler)} tamamlanmış video yüklendi: {', '.join(basarili_islemler)}")

    saved_failed = pixverse_state.get("failed", [])
    if isinstance(saved_failed, list):
        for item in saved_failed:
            if isinstance(item, dict) and item.get("source"):
                failed_entries.append({"source": str(item.get("source")), "detay": str(item.get("detay") or "Başarısız")})

    contiguous_done_count = _calculate_contiguous_done_count(prompt_klasorleri, done)
    try:
        saved_last_success = int(pixverse_state.get("last_success", 0) or 0)
    except Exception:
        saved_last_success = 0

    if saved_last_success != contiguous_done_count:
        pixverse_state["last_success"] = contiguous_done_count
        pixverse_state["done"] = done
        state["pixverse_state"] = pixverse_state
        state_kaydet(state)
        print(f"[INFO] pixverse_state düzeltildi: last_success={contiguous_done_count}")

    start_index = contiguous_done_count + 1

    settings = read_video_settings()
    print("Video ayarları okundu:")
    print(f"  Model: {settings['model']}")
    print(f"  Kalite: {settings['quality']}")
    print(f"  En Boy Oranı: {settings['aspect_ratio']}")
    print(f"  Süre: {settings['duration']}s")
    print(f"  Ses: {settings['ses']} (Kling 3.0 CLI'da uygulanacak)")
    override_state = load_video_settings_override_state(CONTROL_DIR)
    if str(override_state.get("mode") or "").strip().lower() == "per_video":
        print(f"[INFO] Video bazlı ayar override aktif: {len(override_state.get('entries', []))} kayıt")

    ensure_logged_in(force_relogin=force_relogin)

    for i, prompt_klasor in enumerate(prompt_klasorleri, start=1):
        bekle_pause_varsa()
        stop_kontrol_noktasinda_cik()

        if (prompt_klasor in done) or (i < start_index):
            print(f"ATLANIYOR: {prompt_klasor} (Zaten tamamlanmış)")
            continue

        print("\n" + "=" * 70)
        print(f"İŞLEM {i}/{len(prompt_klasorleri)}: {prompt_klasor}")
        print("=" * 70)

        prompt_metni = prompt_oku(prompt_klasor)
        if not prompt_metni:
            hata_mesaji = "HATA: Prompt dosyası okunamadı"
            basarisiz_islemler.append(f"{prompt_klasor} ( {hata_mesaji} )")
            failed_entries = [x for x in failed_entries if x.get("source") != prompt_klasor]
            failed_entries.append({"source": prompt_klasor, "detay": "Prompt dosyası okunamadı"})
            update_tracking_files(prompt_klasorleri, done, failed_entries, state)
            continue

        video_kayit_klasoru = video_kayit_klasoru_olustur(prompt_klasor)
        if not video_kayit_klasoru:
            hata_mesaji = "HATA: Klasör yolu belirlenemedi"
            basarisiz_islemler.append(f"{prompt_klasor} ( {hata_mesaji} )")
            failed_entries = [x for x in failed_entries if x.get("source") != prompt_klasor]
            failed_entries.append({"source": prompt_klasor, "detay": "Klasör yolu belirlenemedi"})
            update_tracking_files(prompt_klasorleri, done, failed_entries, state)
            continue

        visual_inputs = resolve_visual_inputs(prompt_klasor)
        gorsel_yolu = visual_inputs.get("reference_image")
        prompt_settings, override_entry = resolve_prompt_video_settings(prompt_klasor, settings, override_state)
        if override_entry:
            print(
                f"[INFO] {prompt_klasor} için özel video ayarı uygulanıyor: "
                f"{prompt_settings.get('aspect_ratio')} / {prompt_settings.get('duration')}s / "
                f"{prompt_settings.get('quality')} / ses={prompt_settings.get('ses')}"
            )

        try:
            result = generate_video_for_prompt(
                prompt_klasor_adi=prompt_klasor,
                prompt=prompt_metni,
                settings=prompt_settings,
                reference_image=gorsel_yolu,
                output_dir=video_kayit_klasoru,
                auto_download=auto_download,
                visual_inputs=visual_inputs,
            )
            print(f"✓✓✓ '{prompt_klasor}' için video başarıyla oluşturuldu!")
            if prompt_klasor not in basarili_islemler:
                basarili_islemler.append(prompt_klasor)
            if prompt_klasor not in done:
                done.append(prompt_klasor)
            failed_entries = [x for x in failed_entries if x.get("source") != prompt_klasor]
            update_tracking_files(prompt_klasorleri, done, failed_entries, state)
            print(f"Bilgi dosyası: {Path(result['output_dir']) / OUTPUT_META_FILE}")
        except SystemExit:
            raise
        except UserFacingError as e:
            hata_mesaji = f"HATA: {e.reason}"
            if e.detail:
                hata_mesaji += f" | {e.detail}"
            print(f"✗✗✗ '{prompt_klasor}' başarısız oldu!")
            print_user_error(e)
            basarisiz_islemler.append(f"{prompt_klasor} ( {hata_mesaji} )")
            failed_entries = [x for x in failed_entries if x.get("source") != prompt_klasor]
            failed_entries.append({"source": prompt_klasor, "detay": e.reason})
            update_tracking_files(prompt_klasorleri, done, failed_entries, state)
        except Exception as e:
            hata_mesaji = str(e).strip() or "Beklenmeyen hata"
            print(f"✗✗✗ '{prompt_klasor}' başarısız oldu!")
            print(f"Sebep: {hata_mesaji}")
            basarisiz_islemler.append(f"{prompt_klasor} ( {hata_mesaji} )")
            failed_entries = [x for x in failed_entries if x.get("source") != prompt_klasor]
            failed_entries.append({"source": prompt_klasor, "detay": hata_mesaji[:180]})
            update_tracking_files(prompt_klasorleri, done, failed_entries, state)

        if i < len(prompt_klasorleri):
            print("\nBir sonraki işleme geçiliyor... (2 saniye bekleniyor)")
            time.sleep(2)

    print("\n" + "=" * 70)
    print("TÜM İŞLEMLER TAMAMLANDI!")
    print("=" * 70)
    print(f"Toplam İşlem: {len(prompt_klasorleri)}")
    basarili_str = " - ".join(basarili_islemler) if basarili_islemler else "Yok"
    print(f"Başarılı: {len(basarili_islemler)} - {basarili_str}")
    basarisiz_str = " - ".join(basarisiz_islemler) if basarisiz_islemler else "Yok"
    print(f"Başarısız: {len(basarisiz_islemler)} - {basarisiz_str}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Kling 3.0 - app.py ile entegre toplu sürüm")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--force-relogin", action="store_true", help="Başlamadan önce yerel PixVerse oturumunu temizleyip yeniden giriş ister")
    parser.add_argument("--prompt-dir", default="", help="Prompt klasör yolu (override)")
    parser.add_argument("--ref-image-dir", default="", help="Referans görsel klasör yolu (override)")
    args = parser.parse_args()

    # Komut satırı argümanları PROMPT_ROOT ve REFERENCE_IMAGE_ROOT'u override eder
    if args.prompt_dir:
        global PROMPT_ROOT
        PROMPT_ROOT = Path(args.prompt_dir)
        print(f"[INFO] PROMPT_ROOT override: {PROMPT_ROOT}")
    if args.ref_image_dir:
        global REFERENCE_IMAGE_ROOT
        REFERENCE_IMAGE_ROOT = Path(args.ref_image_dir)
        print(f"[INFO] REFERENCE_IMAGE_ROOT override: {REFERENCE_IMAGE_ROOT}")

    try:
        node_path = resolve_binary("node")
        pixverse_path = resolve_binary("pixverse")
        print(f"Node bulundu: {node_path}")
        print(f"PixVerse CLI bulundu: {pixverse_path}")
        kling_30_toplu(auto_download=not args.no_download, force_relogin=args.force_relogin)
    except SystemExit:
        raise
    except ConfigError as e:
        print_user_error(UserFacingError(
            status="Ayar kontrolü",
            reason="Dosya içeriği uygun değil",
            detail=str(e),
            result="İşlem Başlatılamadı",
        ))
        sys.exit(1)
    except FileNotFoundError as e:
        print_user_error(UserFacingError(
            status="Kurulum kontrolü",
            reason="Gerekli komut veya dosya bulunamadı",
            detail=str(e).splitlines()[0],
            result="İşlem Başlatılamadı",
        ))
        sys.exit(1)
    except UserFacingError as e:
        print_user_error(e)
        sys.exit(1)
    except Exception as e:
        print_user_error(UserFacingError(
            status="Genel işlem",
            reason="Beklenmeyen bir hata oluştu",
            detail=str(e)[:180] if str(e).strip() else "İşlem tamamlanamadı.",
            result="Video Başarısız",
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
