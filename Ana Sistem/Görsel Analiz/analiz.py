import subprocess
import os
from pathlib import Path
import time

# ================================
# MERKEZI KONTROL SİSTEMİ
# (app.py ile uyumlu: .control/PAUSE.flag + STOP.flag)
# ================================
import sys
import atexit

CONTROL_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma\.control"
os.makedirs(CONTROL_DIR, exist_ok=True)

PAUSE_FLAG = os.path.join(CONTROL_DIR, "PAUSE.flag")
STOP_FLAG  = os.path.join(CONTROL_DIR, "STOP.flag")
RUNNING_PID = os.path.join(CONTROL_DIR, "RUNNING.pid")

def stop_istegi_var_mi() -> bool:
    return os.path.exists(STOP_FLAG)

def pid_kaydet():
    # Bu script'in PID'ini RUNNING.pid'e yazar (app.py kill için kullanır).
    try:
        with open(RUNNING_PID, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

def pid_sil():
    # RUNNING.pid dosyasını temizler.
    try:
        if os.path.exists(RUNNING_PID):
            os.remove(RUNNING_PID)
    except Exception:
        pass

atexit.register(pid_sil)

def bekle_pause_varsa(pause_flag_path=None):
    # PAUSE.flag varsa güvenli noktada bekler. pause_flag_path verilirse onu kullanır.
    flag_path = pause_flag_path or PAUSE_FLAG
    paused_logged = False
    while os.path.exists(flag_path):
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
    # Güvenli noktada STOP.flag kontrolü.
    if stop_istegi_var_mi():
        print("[STOP] Bitirme isteği alındı. Güvenli çıkış yapılıyor...")
        sys.exit(0)

# Geriye dönük uyumluluk (bazı kodlar pause_flag değişkeni kullanabilir)
pause_flag = PAUSE_FLAG



# =============================================================================
# YAPILANDIRMA VE DOSYA YOLLARI
# =============================================================================

# Girdilerin olduğu ana klasörler (İçinde "Video 1", "Video 2" vb. klasörler var)
indirilen_video_kok = r"C:\Users\User\Desktop\Otomasyon\İndirilen Video"
eklenen_video_kok = r"C:\Users\User\Desktop\Otomasyon\Eklenen Video"
PROMPT_SOURCE_MODE_FILE = os.path.join(CONTROL_DIR, "prompt_source_mode.txt")
PROMPT_SOURCE_LINK = "link"
PROMPT_SOURCE_ADDED_VIDEO = "added_video"

# Çıktıların kaydedileceği ana klasör
analiz_cikti_kok = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Analiz"

# İşlenecek video uzantıları
VIDEO_EXTENSIONS = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.flv', '*.wmv', '*.webm']

# FFmpeg ayarları
FPS_RATE = "2"    # Saniyede kaç kare (2 = 0.5 saniyede bir)
IMG_QUALITY = "2" # 1-31 (Düşük sayı = Yüksek kalite)


def prompt_kaynak_modunu_normalize_et(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in {PROMPT_SOURCE_LINK, "youtube", "manual"}:
        return PROMPT_SOURCE_LINK
    if raw in {PROMPT_SOURCE_ADDED_VIDEO, "video", "eklenen_video", "eklenen video"}:
        return PROMPT_SOURCE_ADDED_VIDEO
    return "auto"


def prompt_kaynak_modunu_oku() -> str:
    try:
        if os.path.exists(PROMPT_SOURCE_MODE_FILE):
            with open(PROMPT_SOURCE_MODE_FILE, "r", encoding="utf-8") as f:
                return prompt_kaynak_modunu_normalize_et(f.read().strip())
    except Exception:
        pass
    return "auto"


def video_klasorlerini_listele(root_path: str):
    if not root_path or not os.path.isdir(root_path):
        return []
    try:
        return sorted([f for f in Path(root_path).iterdir() if f.is_dir()], key=lambda x: x.name)
    except Exception:
        return []


def aktif_kaynaklari_getir():
    mode = prompt_kaynak_modunu_oku()
    if mode == PROMPT_SOURCE_ADDED_VIDEO:
        return [("Eklenen Video", eklenen_video_kok)]
    if mode == PROMPT_SOURCE_LINK:
        return [("İndirilen Video", indirilen_video_kok)]
    return [("İndirilen Video", indirilen_video_kok), ("Eklenen Video", eklenen_video_kok)]


def islenecek_klasorleri_getir():
    birlesik = []
    gorulenler = set()

    for kaynak_etiketi, kok_yol in aktif_kaynaklari_getir():
        for klasor in video_klasorlerini_listele(kok_yol):
            anahtar = klasor.name.casefold().strip()
            if not anahtar:
                continue
            if anahtar in gorulenler:
                print(f"⚠️ Aynı klasör adı birden fazla kaynakta bulundu, ilk eşleşme korunuyor: {klasor.name} ({kaynak_etiketi})")
                continue
            gorulenler.add(anahtar)
            birlesik.append({
                "source_label": kaynak_etiketi,
                "root_path": kok_yol,
                "folder_path": klasor,
                "folder_name": klasor.name,
            })
    return birlesik

# =============================================================================
# İŞLEM BAŞLANGICI
# =============================================================================

# Ana çıktı klasörünü oluştur (yoksa)
os.makedirs(analiz_cikti_kok, exist_ok=True)

# === PAUSE/STOP CHECK ===
bekle_pause_varsa(pause_flag)
stop_kontrol_noktasinda_cik()
# === PAUSE/STOP CHECK ===

pid_kaydet()

# === PAUSE/STOP CHECK ===
bekle_pause_varsa(pause_flag)
stop_kontrol_noktasinda_cik()
# === PAUSE/STOP CHECK ===

print("=" * 70)
print(f"📂 Hedef Klasör:  {analiz_cikti_kok}")
for kaynak_etiketi, kok_yol in aktif_kaynaklari_getir():
    print(f"📂 Kaynak ({kaynak_etiketi}): {kok_yol}")
print("=" * 70)
print("\n🔍 Klasörler taranıyor ve analiz başlıyor...\n")

# Aktif prompt kaynağına göre işlenecek klasörleri bul
# === PAUSE/STOP CHECK ===
bekle_pause_varsa(pause_flag)
stop_kontrol_noktasinda_cik()
# === PAUSE/STOP CHECK ===

alt_klasorler = islenecek_klasorleri_getir()

if not alt_klasorler:
    print("❌ İşlenecek alt klasör (Video 1, Video 2 vb.) bulunamadı!")
    print(f"   • Kaynak modu: {prompt_kaynak_modunu_oku()}")
    exit()

# Toplam işlenecek klasör sayısı
toplam_is = len(alt_klasorler)

basarili = 0
basarisiz = 0
atlandi = 0

# -----------------------------------------------------------------------------
# DÖNGÜ: Her bir klasörü (Video 1, Video 2...) sırayla işle
# -----------------------------------------------------------------------------
for index, klasor_bilgisi in enumerate(alt_klasorler, 1):
    # === PAUSE/STOP CHECK ===
    bekle_pause_varsa(pause_flag)
    stop_kontrol_noktasinda_cik()
    # === PAUSE/STOP CHECK ===
    klasor_yolu = klasor_bilgisi["folder_path"]
    klasor_adi = klasor_bilgisi["folder_name"]  # Örn: "Video 1"
    kaynak_etiketi = klasor_bilgisi["source_label"]

    print(f"\n🎬 [{index}/{toplam_is}] KLASÖR İŞLENİYOR: {klasor_adi} | Kaynak: {kaynak_etiketi}")
    print("-" * 60)

    # 1. Videoyu Bul
    # ----------------
    video_dosyasi = None
    for ext in VIDEO_EXTENSIONS:
        bulunanlar = list(klasor_yolu.glob(ext))
        if bulunanlar:
            video_dosyasi = bulunanlar[0] # İlk bulduğunu al
            break
    
    if not video_dosyasi:
        print(f"   ⚠️  Bu klasörde ({klasor_adi}) uygun video dosyası bulunamadı. Geçiliyor...")
        atlandi += 1
        continue

    print(f"   📹 Video Tespit Edildi: {video_dosyasi.name}")

    # 2. Çıktı Yollarını Ayarla
    # -------------------------
    # "Video 1" ismini "Video Görsel Analiz 1" olarak değiştir
    # Eğer isimde "Video" geçiyorsa değiştirir, geçmiyorsa sonuna ekler.
    if "Video" in klasor_adi:
        hedef_klasor_adi = klasor_adi.replace("Video", "Video Görsel Analiz")
    else:
        hedef_klasor_adi = f"{klasor_adi} Görsel Analiz"
    
    # Hedef yol: .../Görsel Analiz/Video Görsel Analiz 1/
    hedef_yol = os.path.join(analiz_cikti_kok, hedef_klasor_adi)
    
    # Ses dosyası yolu: .../Video Görsel Analiz 1/ses/
    hedef_ses_yol = os.path.join(hedef_yol, "ses")
    
    # Klasörleri oluştur
    os.makedirs(hedef_yol, exist_ok=True)
    os.makedirs(hedef_ses_yol, exist_ok=True)

    # Dosya çıktı şablonları
    img_output_pattern = os.path.join(hedef_yol, "frame_%04d.jpg")
    audio_output_file = os.path.join(hedef_ses_yol, "audio.mp3")

    # 3. Görsel Analiz (Frame Çıkarma)
    # --------------------------------
    print(f"   🔄 Frame çıkarma işlemi başlatılıyor...")
    
    frame_basarili = False
    ffmpeg_video_komut = [
        "ffmpeg",
        "-i", str(video_dosyasi),
        "-vf", f"fps={FPS_RATE}",
        "-q:v", IMG_QUALITY,
        "-y",
        img_output_pattern
    ]

    try:
        # === PAUSE/STOP CHECK ===
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()
        # === PAUSE/STOP CHECK ===
        subprocess.run(ffmpeg_video_komut, capture_output=True, check=True)
        print("   ✅ Frame çıkarma tamamlandı.")
        frame_basarili = True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Frame çıkarma hatası! (Hata kodu: {e.returncode})")
    except FileNotFoundError:
        print("   ❌ FFmpeg yüklü değil veya bulunamadı!")
        exit()

    # 4. Ses Analizi (Ses Çıkarma)
    # ----------------------------
    print(f"   🎵 Ses çıkarma işlemi başlatılıyor...")

    ffmpeg_audio_komut = [
        "ffmpeg",
        "-i", str(video_dosyasi),
        "-q:a", "0",
        "-map", "a",
        "-y",
        audio_output_file
    ]

    try:
        # === PAUSE/STOP CHECK ===
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()
        # === PAUSE/STOP CHECK ===
        subprocess.run(ffmpeg_audio_komut, capture_output=True, check=True)
        print("   ✅ Ses dosyası oluşturuldu.")
    except subprocess.CalledProcessError:
        print("   ⚠️  Ses çıkarma başarısız oldu (Videoda ses kanalı olmayabilir).")

    # 5. İşlem Sonu Özeti
    # -------------------
    olusan_resimler = len(list(Path(hedef_yol).glob("*.jpg")))
    olusan_ses = 1 if os.path.exists(audio_output_file) else 0
    
    print(f"\n   📊 {hedef_klasor_adi} Tamamlandı:")
    print(f"      • Konum: {hedef_yol}")
    print(f"      • Görsel: {olusan_resimler} adet")
    print(f"      • Ses: {'Var' if olusan_ses else 'Yok'}")

    if frame_basarili and olusan_resimler > 0:
        basarili += 1
    else:
        basarisiz += 1

print("\n" + "=" * 70)
print("✅ TÜM İŞLEMLER TAMAMLANDI!")
print("=" * 70)
print(f"Başarılı: {basarili}")
print(f"Başarısız: {basarisiz}")
if atlandi > 0:
    print(f"Atlandı (Video Yok): {atlandi}")
print("=" * 70)