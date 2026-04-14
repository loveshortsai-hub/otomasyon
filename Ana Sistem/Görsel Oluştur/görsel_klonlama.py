import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import time
from PIL import Image


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

PIXVERSE_IMAGE_MODELS = {
    "Qwen Image": {
        "cli": "qwen-image",
        "qualities": ["720p", "1080p"],
        "supports_auto_ratio": False,
        "aspect_ratios": COMMON_ASPECT_RATIOS,
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


def kalite_coz(kalite_tercihi: str, model_adi: str) -> str:
    qualities = list(PIXVERSE_IMAGE_MODELS[model_adi]["qualities"])
    if not qualities:
        return "1080p"

    tercih = str(kalite_tercihi or "").strip().lower()
    if tercih == "maksimum":
        return qualities[-1]
    if tercih == "yüksek" or tercih == "yuksek":
        return qualities[min(len(qualities) - 1, len(qualities) // 2)]
    return qualities[0]


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


def dosyadan_promptlari_oku(prompt_path: str) -> dict[int, str]:
    prompts = {}
    print(f"📄 Prompt Dosyası Okunuyor: {prompt_path}")

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r"Görsel\s+(\d+)\s*:\s*(.*)", line.strip(), re.IGNORECASE)
                if match:
                    prompts[int(match.group(1))] = match.group(2).strip()
        print(f"✅ Toplam {len(prompts)} adet özel istem (prompt) bulundu.")
        return prompts
    except FileNotFoundError:
        print(f"❌ HATA: Prompt dosyası bulunamadı -> {prompt_path}")
        return {}
    except Exception as exc:
        print(f"❌ HATA: Dosya okunurken hata oluştu -> {exc}")
        return {}


def klasordeki_ilk_gorseli_bul(klasor_yolu: str) -> str | None:
    try:
        dosyalar = sorted(os.listdir(klasor_yolu), key=natural_sort_key)
        for dosya in dosyalar:
            if dosya.lower().endswith(SUPPORTED_IMAGE_EXTS):
                return os.path.join(klasor_yolu, dosya)
    except Exception:
        pass
    return None


def referans_gorsel_bul(referans_klasoru: str, gorsel_no: int) -> str | None:
    if not os.path.isdir(referans_klasoru):
        return None
    try:
        for fname in sorted(os.listdir(referans_klasoru), key=natural_sort_key):
            if not fname.lower().endswith(SUPPORTED_IMAGE_EXTS):
                continue
            if re.match(rf"ref_{gorsel_no}(\..+)$", fname, re.IGNORECASE):
                return os.path.join(referans_klasoru, fname)
    except Exception:
        pass
    return None


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


def hedef_klasor_hazirla(target_dir: str):
    os.makedirs(target_dir, exist_ok=True)
    for name in os.listdir(target_dir):
        if name.lower().endswith(SUPPORTED_IMAGE_EXTS):
            try:
                os.remove(os.path.join(target_dir, name))
            except Exception:
                pass


def mevcut_klon_gorseli(target_dir: str) -> str | None:
    return klasordeki_ilk_gorseli_bul(target_dir)


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


def standart_dosya_adina_cevir(target_dir: str, image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower() or ".png"
    hedef = os.path.join(target_dir, f"frame_0001{ext}")
    if os.path.abspath(image_path) != os.path.abspath(hedef):
        if os.path.exists(hedef):
            try:
                os.remove(hedef)
            except Exception:
                pass
        os.replace(image_path, hedef)
    return hedef


def gorsel_indirmeyi_dene(
    pixverse_exe: str,
    asset_id: str,
    target_dir: str,
    toplam_timeout: int = 180,
    deneme_araligi: int = 10,
) -> str:
    hedef_klasor_hazirla(target_dir)
    son_hata = "GÃ¶rsel indirilemedi."
    son_deneme = time.time() + max(toplam_timeout, deneme_araligi)
    deneme_no = 0

    while time.time() <= son_deneme:
        deneme_no += 1
        try:
            rc, stdout, stderr = komut_calistir(
                [pixverse_exe, "asset", "download", asset_id, "--type", "image", "--dest", target_dir, "--json"],
                f"OluÅŸturulan gÃ¶rsel indiriliyor... (deneme {deneme_no})",
                90,
            )
            if rc == 0:
                indirilen_dosya = yeni_indirilen_gorseli_bul(target_dir)
                if indirilen_dosya and os.path.isfile(indirilen_dosya):
                    return indirilen_dosya
                son_hata = "Ä°ndirme tamamlandÄ± ancak Ã§Ä±ktÄ± gÃ¶rseli bulunamadÄ±."
            else:
                son_hata = komut_hatasini_coz(stdout, stderr)
        except Exception as exc:
            son_hata = str(exc).strip() or "GÃ¶rsel indirilemedi."

        if time.time() + deneme_araligi > son_deneme:
            break

        print(f"[WARN] GÃ¶rsel henÃ¼z indirilebilir deÄŸil. {deneme_araligi} sn sonra tekrar denenecek...")
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
    kalite = kalite_coz(kalite_tercihi, model_name)
    boyut_fallback = str(boyut_tercihi or "16:9").strip()

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

        mevcut_klon = mevcut_klon_gorseli(hedef_klon_klasor) if os.path.isdir(hedef_klon_klasor) else None
        if mevcut_klon:
            print(f"[SKIP] Zaten klonlanmış çıktı bulundu: {os.path.basename(mevcut_klon)}")
            atlandi.append(etiket)
            continue

        hedef_gorsel_yolu = klasordeki_ilk_gorseli_bul(full_klasor_yolu)
        if not hedef_gorsel_yolu:
            print(f"⚠️ Atlanıyor: Desteklenen görsel dosyası bulunamadı ({klasor_adi})")
            atlandi.append(etiket)
            continue

        aktif_prompt = str(prompts.get(index) or "").strip()
        if not aktif_prompt:
            print(f"⚠️ Atlanıyor: 'Görsel {index}' için text dosyasında satır bulunamadı.")
            atlandi.append(etiket)
            continue

        referans_yolu = referans_gorsel_bul(referans_root, index)
        aspect_ratio = aspect_ratio_coz(hedef_gorsel_yolu, boyut_fallback, model_name)

        print(f"🖼️ Kaynak görsel: {os.path.basename(hedef_gorsel_yolu)}")
        print(f"📝 Prompt: {aktif_prompt}")
        print(f"🎛️ Model: {model_name}")
        print(f"🎚️ Kalite: {kalite}")
        print(f"📐 Oran: {aspect_ratio}")
        if referans_yolu:
            print(f"📎 Referans görsel kullanılıyor: {os.path.basename(referans_yolu)}")
        create_timeout_seconds = 300 if model_name == "Kling O3" else 120

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
            "--no-wait",
            "--json",
        ]

        komut.extend(["--image", hedef_gorsel_yolu])
        if referans_yolu:
            komut.extend(["--images", referans_yolu])

        try:
            rc, stdout, stderr = komut_calistir(
                komut,
                "PixVerse create image isteği gönderiliyor...",
                create_timeout_seconds,
            )
            if rc != 0:
                raise RuntimeError(komut_hatasini_coz(stdout, stderr))

            data = parse_json_output(stdout or stderr)
            asset_id = str(data.get("image_id") or data.get("id") or "").strip()
            if not asset_id:
                raise RuntimeError("PixVerse yanıtında image_id bulunamadı.")
            print(f"[INFO] PixVerse iş kimliği: {asset_id}")

            rc, stdout, stderr = komut_calistir(
                [pixverse_exe, "task", "wait", asset_id, "--type", "image", "--timeout", str(DEFAULT_TIMEOUT_SECONDS), "--json"],
                "PixVerse görseli oluşturuyor...",
                DEFAULT_TIMEOUT_SECONDS + 30,
            )
            wait_hata = ""
            if rc != 0:
                wait_hata = komut_hatasini_coz(stdout, stderr)
                print(f"[WARN] PixVerse wait adımı hata döndü. İndirme ile kontrol edilecek -> {wait_hata}")

            indirilen_dosya = gorsel_indirmeyi_dene(
                pixverse_exe,
                asset_id,
                hedef_klon_klasor,
                toplam_timeout=240 if model_name == "Kling O3" else 180,
            )

            standart_yol = standart_dosya_adina_cevir(hedef_klon_klasor, indirilen_dosya)
            if wait_hata:
                print(f"[INFO] PixVerse görseli wait hatasına rağmen başarıyla indirildi: {wait_hata}")
            print(f"✅ Kaydedildi: {standart_yol}")
            basarili.append(etiket)
        except Exception as exc:
            detay = str(exc).strip() or "İşlem Başarısız"
            print(f"❌ Hata oluştu: {detay}")
            basarisiz.append((etiket, detay))

    print("\n" + "=" * 60)
    print("TÜM İŞLEMLER TAMAMLANDI")
    print("=" * 60)
    print(f"Başarılı: {len(basarili)} - {ozet_satiri_uret(basarili)}")
    print(f"Başarısız: {len(basarisiz)} - {failure_satiri_uret(basarisiz)}")
    print(f"Atlandı (Zaten mevcut): {len(atlandi)} - {ozet_satiri_uret(atlandi)}")
    print("=" * 60)


if __name__ == "__main__":
    main()

