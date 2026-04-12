import os
import time
import re
from PIL import Image
from google import genai
from google.genai import types

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



# --- AYARLAR ---
# API Key öncelik sırası:
# 1. app.py Ayarlar bölümündeki merkezi settings.local.json (gemini_api_key)
# 2. Ortam değişkeni GEMINI_API_KEY
# 3. Aşağıdaki satırı aktif ederek tek başına çalıştırabilirsiniz:
# API_KEY = "buraya-key-girin"
API_KEY = None  # app.py'den otomatik okunur

MODEL_NAME = "gemini-3-pro-image-preview"

# --- DOSYA YOLLARI YAPILANDIRMASI ---

# 1. Scriptin ve Text Dosyasının Olduğu Klasör
CALISMA_DIZINI = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluştur"

# 2. Resimlerin Okunacağı ve Kaydedileceği Ana Kök Dizin
GORSEL_KOK_DIZIN = r"C:\Users\User\Desktop\Otomasyon\Görsel"

# --- DETAYLI YOLLAR ---
# Prompt Dosyası (Scriptin yanında)
TEXT_DOSYASI = os.path.join(CALISMA_DIZINI, "Görsel Düzelt.txt")

# Giriş Klasörü: settings.local.json'dan okunur (gorsel_klonla_kaynak).
# Varsayılan: Görsel Analiz  |  Alternatif: Görseller (Görsel Oluştur çıktısı)
def _giris_klasoru_oku():
    try:
        import json as _json
        _settings_path = os.path.join(CONTROL_DIR, "settings.local.json")
        if os.path.exists(_settings_path):
            with open(_settings_path, "r", encoding="utf-8") as _sf:
                _s = _json.load(_sf)
            kaynak = _s.get("gorsel_klonla_kaynak", "gorsel_analiz")
            if kaynak == "gorsel_olustur":
                return _s.get("gorsel_olustur_dir", os.path.join(GORSEL_KOK_DIZIN, "Görseller"))
            else:
                return _s.get("gorsel_analiz_dir", os.path.join(GORSEL_KOK_DIZIN, "Görsel Analiz"))
    except Exception:
        pass
    return os.path.join(GORSEL_KOK_DIZIN, "Görsel Analiz")

GIRIS_ANA_KLASOR = _giris_klasoru_oku()

# Çıktı Klasörü (Görsel/Klon Görsel)
CIKIS_ANA_KLASOR = os.path.join(GORSEL_KOK_DIZIN, "Klon Görsel")

DESTEKLENEN_UZANTILAR = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')

# Referans Görsel Klasörü
# app.py tarafından Görsel Düzelt.txt'nin yanına kaydedilir: .../Görsel Oluştur/referans/
REFERANS_KLASORU = os.path.join(CALISMA_DIZINI, "referans")


def klasordeki_ilk_gorseli_bul(klasor_yolu):
    """
    Klasördeki ilk görsel dosyasını dosya adına bakmaksızın döndürür.
    Desteklenen formatlar: jpg, jpeg, png, webp, bmp, gif
    """
    try:
        dosyalar = sorted(os.listdir(klasor_yolu), key=lambda s: [
            int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)
        ])
        for dosya in dosyalar:
            if dosya.lower().endswith(DESTEKLENEN_UZANTILAR):
                return os.path.join(klasor_yolu, dosya)
    except Exception:
        pass
    return None


def referans_gorsel_bul(gorsel_no: int):
    """
    Referans klasöründen belirli numaralı görselin yolunu döndürür.
    Dosya adı formatı: ref_<no>.<ext>  (örn: ref_1.png, ref_2.jpg)
    Yoksa None döndürür.
    """
    if not os.path.isdir(REFERANS_KLASORU):
        return None
    try:
        for fname in sorted(os.listdir(REFERANS_KLASORU)):
            if fname.lower().endswith(DESTEKLENEN_UZANTILAR):
                m = re.match(rf"ref_{gorsel_no}(\..+)$", fname)
                if m:
                    return os.path.join(REFERANS_KLASORU, fname)
    except Exception:
        pass
    return None

def natural_sort_key(s):
    """
    Klasörleri insan mantığına göre sıralamak için (Örn: 1, 2, 10).
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]

def promptlari_oku(dosya_yolu):
    """
    Text dosyasını okur ve {1: "Kedi...", 2: "Adam..."} şeklinde sözlüğe çevirir.
    """
    promptlar = {}
    print(f"📄 Prompt Dosyası Okunuyor: {dosya_yolu}")
    
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # "Görsel 1: Metin" yapısını Regex ile yakala
            match = re.match(r"Görsel\s+(\d+)\s*:\s*(.*)", line, re.IGNORECASE)
            if match:
                gorsel_no = int(match.group(1))
                prompt_text = match.group(2).strip()
                promptlar[gorsel_no] = prompt_text
            
        print(f"✅ Toplam {len(promptlar)} adet özel istem (prompt) bulundu.")
        return promptlar
    
    except FileNotFoundError:
        print(f"❌ HATA: Prompt dosyası bulunamadı -> {dosya_yolu}")
        return {}
    except Exception as e:
        print(f"❌ HATA: Dosya okunurken hata oluştu -> {e}")
        return {}

def dosya_okuma_ve_gonderme():
    print("--- GOOGLE GEN AI KLASÖR BAZLI İŞLEME ---")
    print(f"📂 Çalışma Dizini: {CALISMA_DIZINI}")

    pid_kaydet()
    # === PAUSE/STOP CHECK ===
    bekle_pause_varsa(pause_flag)
    stop_kontrol_noktasinda_cik()
    # === PAUSE/STOP CHECK ===

    # 1. Promptları Yükle
    bekle_pause_varsa(pause_flag)
    stop_kontrol_noktasinda_cik()

    prompt_sozlugu = promptlari_oku(TEXT_DOSYASI)
    if not prompt_sozlugu:
        print("⚠️ HATA: Promptlar yüklenemediği için işlem durduruluyor.")
        return

    # 2. Giriş Klasörünü Kontrol Et
    bekle_pause_varsa(pause_flag)
    stop_kontrol_noktasinda_cik()

    if not os.path.exists(GIRIS_ANA_KLASOR):
        print(f"❌ HATA: Giriş görsel klasörü bulunamadı -> {GIRIS_ANA_KLASOR}")
        return

    # 3. Alt Klasörleri Bul ve Sırala (Video Görsel Analiz 1, 2...)
    try:
        alt_klasorler = [d for d in os.listdir(GIRIS_ANA_KLASOR) 
                         if os.path.isdir(os.path.join(GIRIS_ANA_KLASOR, d))]
    except FileNotFoundError:
        print("❌ HATA: Klasör listelenemedi.")
        return

    # Doğru sıralama (1, 2, 3... 10)
    alt_klasorler.sort(key=natural_sort_key)

    toplam_klasor = len(alt_klasorler)
    print(f"📂 İşlenecek Klasör Sayısı: {toplam_klasor}\n")

    # 4. İstemciyi Başlat
    try:
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()

        # Merkezi API Key okuma
        _kullanilacak_key = API_KEY
        if not _kullanilacak_key:
            try:
                import json as _json
                _app_dir = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma"
                _settings_path = os.path.join(_app_dir, ".control", "settings.local.json")
                if os.path.exists(_settings_path):
                    with open(_settings_path, "r", encoding="utf-8") as _sf:
                        _sdata = _json.load(_sf)
                    _kullanilacak_key = _sdata.get("gemini_api_key", "").strip()
            except Exception:
                pass
        if not _kullanilacak_key:
            _kullanilacak_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not _kullanilacak_key:
            print("❌ HATA: Gemini API Key bulunamadı!")
            print("  -> app.py Ayarlar bölümünden Gemini API Key girin.")
            return
        client = genai.Client(api_key=_kullanilacak_key)
    except Exception as e:
        print(f"❌ API Bağlantı Hatası: {e}")
        return

    # --- DÖNGÜ BAŞLANGICI ---
    basarili = 0
    basarisiz = 0
    atlandi = 0

    for index, klasor_adi in enumerate(alt_klasorler, start=1):
        # === PAUSE/STOP CHECK ===
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()
        # === PAUSE/STOP CHECK ===
        full_klasor_yolu = os.path.join(GIRIS_ANA_KLASOR, klasor_adi)
        
        print(f"➡️ [{index}/{toplam_klasor}] Klasör: {klasor_adi}")

        # Klasördeki ilk görseli dosya adına bakmaksızın bul
        hedef_gorsel_yolu = klasordeki_ilk_gorseli_bul(full_klasor_yolu)

        # Görsel var mı kontrol et
        if not hedef_gorsel_yolu:
            print(f"   ⚠️ Atlanıyor: Desteklenen görsel dosyası bulunamadı ({klasor_adi})")
            atlandi += 1
            continue
        
        print(f"   🖼️ Görsel bulundu: {os.path.basename(hedef_gorsel_yolu)}")

        # Bu index (sıra numarası) için özel prompt var mı?
        aktif_prompt = prompt_sozlugu.get(index)
        
        if not aktif_prompt:
            print(f"   ⚠️ Atlanıyor: 'Görsel {index}' için text dosyasında satır bulunamadı.")
            atlandi += 1
            continue

        print(f"   📝 Prompt: {aktif_prompt}")

        # Çıktı Klasörünü Hazırla: "Klon Görsel/Klon Görsel 1"
        hedef_klon_klasor = os.path.join(CIKIS_ANA_KLASOR, f"Klon Görsel {index}")
        if not os.path.exists(hedef_klon_klasor):
            os.makedirs(hedef_klon_klasor)

        # --- API İŞLEMİ ---
        try:
            chat = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )

            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()

            img_input = Image.open(hedef_gorsel_yolu)

            # Referans görsel var mı kontrol et
            referans_yolu = referans_gorsel_bul(index)

            # API'ye Gönder
            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()

            if referans_yolu:
                print(f"   📌 Referans görsel kullanılıyor: {os.path.basename(referans_yolu)}")
                ref_img = Image.open(referans_yolu)
                # Ana görsel + referans görsel + prompt
                response = chat.send_message([aktif_prompt, img_input, ref_img])
            else:
                # Sadece ana görsel + prompt (eski davranış)
                response = chat.send_message([aktif_prompt, img_input])

            # Yanıtı Kaydet
            gorsel_kaydedildi = False
            if response.parts:
                for part in response.parts:
                    image = None
                    try:
                        image = part.as_image()
                    except:
                        if part.inline_data:
                            image = Image.open(part.inline_data)

                    if image:
                        cikti_dosya_adi = os.path.join(hedef_klon_klasor, "frame_0001.png")
                        image.save(cikti_dosya_adi)
                        print(f"   ✅ Kaydedildi: {cikti_dosya_adi}")
                        gorsel_kaydedildi = True
            
            if gorsel_kaydedildi:
                basarili += 1
            else:
                print(f"   ⚠️ Uyarı: Model resim üretmedi.")
                basarisiz += 1

            # Hata almamak için kısa bekleme
            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()
            time.sleep(3)

        except Exception as e:
            print(f"   ❌ Hata oluştu: {str(e)}")
            basarisiz += 1
            continue

    print("\n" + "=" * 60)
    print("🏁 TÜM İŞLEMLER TAMAMLANDI!")
    print("=" * 60)
    print(f"Başarılı: {basarili}")
    print(f"Başarısız: {basarisiz}")
    if atlandi > 0:
        print(f"Atlandı (Görsel/Prompt Yok): {atlandi}")
    print("=" * 60)

if __name__ == "__main__":
    dosya_okuma_ve_gonderme()