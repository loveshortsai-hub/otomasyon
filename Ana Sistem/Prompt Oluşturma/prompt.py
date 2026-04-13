# -*- coding: utf-8 -*-
from google import genai
from google.genai import types
import os
import re
import time
from pathlib import Path
import shutil
import json
# ================================
# MERKEZI KONTROL SİSTEMİ
# ================================
import os, time, sys

# Merkezi kontrol klasörü - Tüm kontrol dosyaları burada
CONTROL_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma\.control"
os.makedirs(CONTROL_DIR, exist_ok=True)

PAUSE_FLAG = os.path.join(CONTROL_DIR, "PAUSE.flag")
STOP_FLAG = os.path.join(CONTROL_DIR, "STOP.flag")

def stop_istegi_var_mi():
    return os.path.exists(STOP_FLAG)

def bekle_pause_varsa(pause_flag_path=None):
    """PAUSE.flag varsa güvenli noktada bekler. pause_flag_path verilirse onu kullanır."""
    flag_path = pause_flag_path or PAUSE_FLAG
    paused_logged = False
    while os.path.exists(flag_path):
        # STOP, pause içindeyken de çalışsın
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
    """Güvenli noktada STOP.flag kontrolü."""
    if stop_istegi_var_mi():
        print("[STOP] Bitirme isteği alındı. Güvenli çıkış yapılıyor...")
        sys.exit(0)

# Geriye dönük uyumluluk (mevcut kodların çoğu pause_flag değişkeni kullanıyor)
pause_flag = PAUSE_FLAG


# ============ YOLLAR VE AYARLAR ============
# Ana Kök Dizin
ROOT_PATH = r"C:\Users\User\Desktop\Otomasyon"

# === MERKEZI KONTROL SİSTEMİ ===
# PAUSE_FLAG ve STOP_FLAG zaten yukarıda tanımlandı
STATE_FILE = os.path.join(CONTROL_DIR, "STATE.json")

# Sistem Dosyalarının Olduğu Yer
SYSTEM_PATH = os.path.join(ROOT_PATH, r"Ana Sistem\Prompt Oluşturma")

# Girdi Kaynakları
VIDEO_SOURCE_ROOT = os.path.join(ROOT_PATH, "İndirilen Video")
ADDED_VIDEO_SOURCE_ROOT = os.path.join(ROOT_PATH, "Eklenen Video")
LINK_SOURCE_FILE = os.path.join(ROOT_PATH, "Video Prompt Link.txt")
FALLBACK_LINK_SOURCE_FILE = os.path.join(ROOT_PATH, "İndirilecek Video.txt")
PROMPT_SOURCE_MODE_FILE = os.path.join(CONTROL_DIR, "prompt_source_mode.txt")
PROMPT_SOURCE_LINK = "link"
PROMPT_SOURCE_ADDED_VIDEO = "added_video"
PROMPT_SOURCE_DOWNLOADED_VIDEO = "downloaded_video"

# Çıktı Yeri
PROMPT_EXPORT_ROOT = os.path.join(ROOT_PATH, "Prompt")

# Sistem Dosyaları
ISTEM_FILE = os.path.join(SYSTEM_PATH, "istem.txt")
APP_BASE_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma"
SETTINGS_CANDIDATES = [
    os.path.join(APP_BASE_DIR, ".control", "settings.local.json"),
    os.path.join(APP_BASE_DIR, "settings.local.json"),
]

# ============ GLOBAL DEĞİŞKENLER (CACHE) ============
# Tüm state verisini tutar
STATE_CACHE = None
# Klasör isimlendirme performans sayacı
NEXT_ID_COUNTER = None 

# ============ API KEY KONTROLÜ ============
# Öncelik sırası:
# 1. app.py Ayarlar bölümündeki merkezi settings.local.json (gemini_api_key)
# 2. Ortam değişkeni GEMINI_API_KEY
# Düz metin api_key.txt artık bilinçli olarak desteklenmiyor.

def _api_key_oku():
    # 1. settings.local.json'dan oku (app.py ile entegrasyon)
    for _settings_path in SETTINGS_CANDIDATES:
        try:
            if os.path.exists(_settings_path):
                with open(_settings_path, "r", encoding="utf-8") as _f:
                    _data = json.load(_f)
                _key = _data.get("gemini_api_key", "").strip()
                if _key:
                    return _key
        except Exception:
            pass
    # 2. Ortam değişkeni
    _key = os.getenv("GEMINI_API_KEY", "").strip()
    if _key:
        return _key
    return None

api_key = _api_key_oku()
if not api_key:
    print("CRITICAL ERROR: Gemini API Key bulunamadı!")
    print("  -> app.py Ayarlar bölümünden Gemini API Key girin veya GEMINI_API_KEY tanımlayın.")
    exit(1)

client = genai.Client(api_key=api_key)

# ============ PAUSE & STATE FONKSİYONLARI ============

def guvenli_uyku(saniye):
    """
    time.sleep yerine kullanılır.
    Belirtilen süreyi 0.1 saniyelik parçalar halinde bekler.
    Her parçada PAUSE kontrolü yapar.
    """
    bitis_zamani = time.time() + saniye
    while time.time() < bitis_zamani:
        bekle_pause_varsa(PAUSE_FLAG)
        stop_kontrol_noktasinda_cik()
        time.sleep(0.1)

def state_yukle():
    """
    STATE dosyasını yükler. 
    processed -> Set (Hız için)
    mapping -> Dict (Çakışma önlemek için)
    """
    global STATE_CACHE
    
    if STATE_CACHE is not None:
        return STATE_CACHE

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                processed_set = set(data.get("processed", []))
                mapping_dict = data.get("mapping", {})
                
                STATE_CACHE = data 
                STATE_CACHE["processed"] = processed_set
                STATE_CACHE["mapping"] = mapping_dict
                
        except Exception:
            STATE_CACHE = {"processed": set(), "mapping": {}}
    else:
        STATE_CACHE = {"processed": set(), "mapping": {}}
    
    return STATE_CACHE

def state_kaydet(item_id, folder_name):
    """
    İşlenen öğeyi ATOMİK olarak kaydeder.
    Kullanıcı pause yapmış olsa bile önce kaydeder,
    veri kaybı/gecikmesi olmaz.
    """
    global STATE_CACHE
    
    if STATE_CACHE is None:
        state_yukle()
    
    # RAM güncelle
    STATE_CACHE["processed"].add(item_id)
    STATE_CACHE["mapping"][item_id] = folder_name
        
    temp_file = STATE_FILE + ".tmp"
    
    try:
        # Shallow copy & Sort
        save_data = STATE_CACHE.copy()
        save_data["processed"] = sorted(list(STATE_CACHE["processed"]))
        
        # --- ATOMIC WRITE ---
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
            
        os.replace(temp_file, STATE_FILE)
        # --------------------
        
        print("   (State güncellendi ve kaydedildi)")
    except Exception as e:
        print(f"   (State kaydetme hatası: {e})")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

def get_processed_status(item_id):
    """
    Öğenin durumunu ve atanmış klasör adını döndürür.
    Return: (is_processed: bool, existing_folder: str|None)
    """
    data = state_yukle()
    processed = item_id in data["processed"]
    folder = data["mapping"].get(item_id)
    return processed, folder

def get_next_folder_name(target_root, current_mapping):
    """
    Klasör isimlendirmesi için optimize edilmiş fonksiyon.
    Diski sadece İLK çalışmada tarar, sonra sayaç kullanır.
    O(1) performans sağlar.
    """
    global NEXT_ID_COUNTER
    
    # Henüz sayaç başlatılmadıysa (Script ilk açıldığında)
    if NEXT_ID_COUNTER is None:
        max_id = 0
        
        # 1. Mapping'deki en büyük numarayı bul
        for name in current_mapping.values():
            m = re.match(r"Video Prompt (\d+)", name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        
        # 2. Diskteki mevcut klasörleri kontrol et
        if os.path.exists(target_root):
            for d in os.listdir(target_root):
                if d.startswith("Video Prompt ") and os.path.isdir(os.path.join(target_root, d)):
                    m = re.match(r"Video Prompt (\d+)", d)
                    if m:
                        max_id = max(max_id, int(m.group(1)))
        
        NEXT_ID_COUNTER = max_id + 1
    
    # Sayaçtan değer ver ve artır
    folder_name = f"Video Prompt {NEXT_ID_COUNTER}"
    NEXT_ID_COUNTER += 1
    return folder_name



def prompt_kaynak_modu_oku():
    try:
        if os.path.exists(PROMPT_SOURCE_MODE_FILE):
            with open(PROMPT_SOURCE_MODE_FILE, "r", encoding="utf-8") as f:
                raw = f.read().strip().lower()
            if raw in {PROMPT_SOURCE_LINK, "youtube", "manual"}:
                return PROMPT_SOURCE_LINK
            if raw in {PROMPT_SOURCE_ADDED_VIDEO, "video", "eklenen_video", "eklenen video"}:
                return PROMPT_SOURCE_ADDED_VIDEO
            if raw in {PROMPT_SOURCE_DOWNLOADED_VIDEO, "download", "indirilen_video", "indirilen video"}:
                return PROMPT_SOURCE_DOWNLOADED_VIDEO
    except Exception:
        pass
    return "auto"


def kaynak_klasorunden_videolari_topla(kok_yol):
    videolar = []
    if os.path.exists(kok_yol):
        alt_klasorler = sorted(os.listdir(kok_yol), key=lambda x: (int(re.sub(r'\D', '', x)) if re.sub(r'\D', '', x) else 0, x.lower()))
        for klasor_adi in alt_klasorler:
            tam_yol = os.path.join(kok_yol, klasor_adi)
            if os.path.isdir(tam_yol):
                dosyalar = [f for f in os.listdir(tam_yol) if f.lower().endswith(('.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v'))]
                dosyalar.sort(key=lambda x: (int(re.sub(r'\D', '', x)) if re.sub(r'\D', '', x) else 0, x.lower()))
                if dosyalar:
                    videolar.append(os.path.join(tam_yol, dosyalar[0]))
    return videolar


def prompt_linklerini_oku():
    for aday in (LINK_SOURCE_FILE, FALLBACK_LINK_SOURCE_FILE):
        if not aday or not os.path.exists(aday):
            continue
        raw_links = oku(aday)
        if not raw_links:
            continue
        lines = [line.strip() for line in raw_links.splitlines() if line.strip().lower().startswith("http")]
        if lines:
            return lines
    return []

# ============ YARDIMCI FONKSİYONLAR ============
def oku(dosya):
    try:
        with open(dosya, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return None

def yaz(dosya, içerik):
    # Yazma işlemi kritik olduğu için öncesinde bekletilebilir
    bekle_pause_varsa(PAUSE_FLAG)
    stop_kontrol_noktasinda_cik()
    os.makedirs(os.path.dirname(dosya), exist_ok=True)
    with open(dosya, "w", encoding="utf-8") as f:
        f.write(str(içerik).strip())

def bölüm_çek(metin, no):
    pattern = rf"{no}-\s*(.*?)(?=\n\d+-|$)"
    m = re.search(pattern, metin, re.DOTALL)
    return m.group(1).strip() if m else None

def yerel_video_yükle(yol):
    dosya_yolu = Path(yol)
    print(f"Video yükleniyor → {dosya_yolu.name}")
    
    bekle_pause_varsa(PAUSE_FLAG)
    stop_kontrol_noktasinda_cik()

    temp_file_path = None
    try:
        temp_dir = os.path.join(SYSTEM_PATH, "temp_upload")
        os.makedirs(temp_dir, exist_ok=True)
        
        uzanti = dosya_yolu.suffix.lower()
        temp_file_path = os.path.join(temp_dir, f"upload_temp_{int(time.time())}{uzanti}")
        shutil.copy2(dosya_yolu, temp_file_path)
        
        mime_types = {'.mp4': 'video/mp4', '.mov': 'video/quicktime', 
                      '.mkv': 'video/x-matroska', '.webm': 'video/webm', '.avi': 'video/x-msvideo'}
        mime_type = mime_types.get(uzanti, 'video/mp4')
        
        bekle_pause_varsa(PAUSE_FLAG)
        stop_kontrol_noktasinda_cik()

        upload_config = types.UploadFileConfig(mime_type=mime_type)
        uploaded_file = client.files.upload(file=temp_file_path, config=upload_config)
        
        while uploaded_file.state.name == "PROCESSING":
            print("   İşleniyor... (3 sn)")
            guvenli_uyku(3) 
            uploaded_file = client.files.get(name=uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            raise Exception("Google API tarafında işleme başarısız oldu.")
        
        print("✓ Yüklendi!")
        return uploaded_file
    except Exception as e:
        print(f"✗ Yükleme hatası: {e}")
        return None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass

# ============ ANALİZ MOTORU ============
def videoyu_analiz_et(video_uri, folder_name, istem_tam):
    """
    Video analizini TEK geçişte yapar.
    Başarılı olursa True, hata olursa False döndürür.
    """
    hedef_klasör = os.path.join(PROMPT_EXPORT_ROOT, folder_name)
    prompt_cikis_yolu = os.path.join(hedef_klasör, "prompt.txt")

    print("\n" + "="*60)
    print("   ANALİZ BAŞLIYOR (Tek Geçiş)")
    print("="*60)

    print(f"\n{'='*60}")
    print(f"  ADIM 1/1: Video + İstem → prompt.txt")
    print(f"{'='*60}")

    try:
        bekle_pause_varsa(PAUSE_FLAG)
        stop_kontrol_noktasinda_cik()

        resp = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=[istem_tam, types.Part.from_uri(file_uri=video_uri, mime_type="video/mp4")]
        )
        cevap = resp.text
        print(f"✓ Analiz tamamlandı!")

        yaz(prompt_cikis_yolu, cevap)
        print(f"✓ Kaydedildi → {folder_name} → prompt.txt")

        return True

    except Exception as e:
        print(f"✗ Analiz Hatası: {e}")
        return False

# ============ ANA AKIŞ ============
def main():
    global NEXT_ID_COUNTER
    
    os.system('cls' if os.name == 'nt' else 'clear') 
    print("="*60)
    print("   OTOMATİK VİDEO ANALİZ SİSTEMİ")
    print(f"   Kaynak: {ROOT_PATH}")
    print(f"   State : {STATE_FILE} (Double Safety Rollback)")
    print("="*60)

    istem_tam = oku(ISTEM_FILE)
    if not istem_tam:
        print("CRITICAL: istem.txt bulunamadı!")
        return
    
    print("✓ Gemini API Hazır.")
    
    # Cache yükle ve state_data referansını al
    state_data = state_yukle()
    
    # ---------------------------------------------------------
    # KAYNAKLARI TOPLA
    # ---------------------------------------------------------
    kaynak_modu = prompt_kaynak_modu_oku()

    indirilen_videolar = kaynak_klasorunden_videolari_topla(VIDEO_SOURCE_ROOT) if kaynak_modu in ("auto", PROMPT_SOURCE_DOWNLOADED_VIDEO) else []
    eklenen_videolar = kaynak_klasorunden_videolari_topla(ADDED_VIDEO_SOURCE_ROOT) if kaynak_modu in ("auto", PROMPT_SOURCE_ADDED_VIDEO) else []
    linkler = prompt_linklerini_oku() if kaynak_modu in ("auto", PROMPT_SOURCE_LINK) else []

    try:
        selection_path = os.path.join(CONTROL_DIR, "prompt_input_selection.json")
        if os.path.exists(selection_path):
            with open(selection_path, "r", encoding="utf-8") as f:
                sel_data = json.load(f)
            if sel_data.get("mode") == "custom":
                selected = sel_data.get("selected_items", {})
                
                _ori_links = list(linkler)
                _ori_down = list(indirilen_videolar)
                _ori_add = list(eklenen_videolar)
                
                if isinstance(selected.get("links"), list):
                    sel_links = set(selected["links"])
                    linkler = [lnk for lnk in linkler if lnk in sel_links]
                if isinstance(selected.get("downloaded_videos"), list):
                    sel_down = set(selected["downloaded_videos"])
                    indirilen_videolar = [vid for vid in indirilen_videolar if os.path.basename(vid) in sel_down]
                if isinstance(selected.get("added_videos"), list):
                    sel_add = set(selected["added_videos"])
                    eklenen_videolar = [vid for vid in eklenen_videolar if os.path.basename(vid) in sel_add]
                
                if (len(_ori_links) + len(_ori_down) + len(_ori_add)) > 0 and (len(linkler) + len(indirilen_videolar) + len(eklenen_videolar)) == 0:
                    print(f"⚠ Özel seçim dosyaları bulunamadı. Ayar atlanıp ekli olan tüm içerikler işleniyor...")
                    linkler = _ori_links
                    indirilen_videolar = _ori_down
                    eklenen_videolar = _ori_add
                else:
                    print(f"✓ Özel Seçim Modu Aktif (Seçili öğeler işleniyor)")
    except Exception as e:
        print(f"⚠ Prompt seçim filtresi uygulanırken hata: {e}")

    yerel_videolar = indirilen_videolar + eklenen_videolar

    toplam_islem = len(yerel_videolar) + len(linkler)
    print(f"✓ Aktif kaynak modu: {kaynak_modu}")
    print(
        f"✓ Toplam İşlenecek Görev: {toplam_islem} "
        f"(İndirilen: {len(indirilen_videolar)} | Eklenen: {len(eklenen_videolar)} | Link: {len(linkler)})"
    )
    
    global_process_counter = 1
    basarili = 0
    basarisiz = 0
    atlandi = 0
    
    # ---------------------------------------------------------
    # 1. YEREL VİDEOLARI İŞLE
    # ---------------------------------------------------------
    for video_dosya_yolu in yerel_videolar:
        bekle_pause_varsa(PAUSE_FLAG)
        stop_kontrol_noktasinda_cik()

        is_done, stored_folder_name = get_processed_status(video_dosya_yolu)
        
        yeni_id_uretildi = False 

        if stored_folder_name:
            folder_name = stored_folder_name
        else:
            folder_name = get_next_folder_name(PROMPT_EXPORT_ROOT, state_data["mapping"])
            state_data["mapping"][video_dosya_yolu] = folder_name
            yeni_id_uretildi = True

        if is_done:
            print(f"⚠ [ATLANDI] Daha önce işlenmiş: {folder_name} ({os.path.basename(video_dosya_yolu)})")
            global_process_counter += 1
            atlandi += 1
            continue

        print("\n\n")
        print("#"*60)
        print(f"   İŞLEM {global_process_counter}/{toplam_islem}: YEREL VİDEO")
        print(f"   HEDEF: {folder_name}")
        print("#"*60)
        
        uploaded_obj = yerel_video_yükle(video_dosya_yolu)
        if uploaded_obj:
            basari = videoyu_analiz_et(uploaded_obj.uri, folder_name, istem_tam)
            
            if basari:
                state_kaydet(video_dosya_yolu, folder_name)
                basarili += 1
            else:
                # KRİTİK ROLLBACK: Global Cache'den sil
                if STATE_CACHE and video_dosya_yolu in STATE_CACHE["mapping"]:
                    del STATE_CACHE["mapping"][video_dosya_yolu]
                
                if video_dosya_yolu in state_data["mapping"]:
                    del state_data["mapping"][video_dosya_yolu]
                
                if yeni_id_uretildi and NEXT_ID_COUNTER is not None:
                    NEXT_ID_COUNTER -= 1
                    
                hedef_klasor_yolu = os.path.join(PROMPT_EXPORT_ROOT, folder_name)
                if os.path.exists(hedef_klasor_yolu):
                    try:
                        shutil.rmtree(hedef_klasor_yolu)
                        print(f"   (Temizlik: Başarısız klasör silindi -> {folder_name})")
                    except Exception as e:
                        print(f"   (Temizlik Hatası: {e})")
                    
                print(f"⚠ [HATA] İşlem başarısız oldu. Mapping temizlendi.")
                basarisiz += 1
            
            try:
                client.files.delete(name=uploaded_obj.name)
                print("✓ API geçici dosyası temizlendi.")
            except:
                pass
            global_process_counter += 1
        else:
            # Yükleme başarısızsa mapping'den sil
            if STATE_CACHE and video_dosya_yolu in STATE_CACHE["mapping"]:
                 del STATE_CACHE["mapping"][video_dosya_yolu]
            if video_dosya_yolu in state_data["mapping"]:
                 del state_data["mapping"][video_dosya_yolu]
                 
            if yeni_id_uretildi and NEXT_ID_COUNTER is not None:
                 NEXT_ID_COUNTER -= 1
            print("⚠ Video yüklenemediği için atlandı.")

    # ---------------------------------------------------------
    # 2. LİNKLERİ İŞLE
    # ---------------------------------------------------------
    for link in linkler:
        bekle_pause_varsa(PAUSE_FLAG)
        stop_kontrol_noktasinda_cik()

        is_done, stored_folder_name = get_processed_status(link)
        
        yeni_id_uretildi = False

        if stored_folder_name:
            folder_name = stored_folder_name
        else:
            folder_name = get_next_folder_name(PROMPT_EXPORT_ROOT, state_data["mapping"])
            state_data["mapping"][link] = folder_name
            yeni_id_uretildi = True
        
        if is_done:
            print(f"⚠ [ATLANDI] Daha önce işlenmiş: {folder_name} (Link)")
            global_process_counter += 1
            atlandi += 1
            continue
        
        print("\n\n")
        print("#"*60)
        print(f"   İŞLEM {global_process_counter}/{toplam_islem}: LİNK ANALİZİ")
        print(f"   HEDEF: {folder_name}")
        print("#"*60)
        
        print(f"Video Linki Alındı → {link}")
        
        basari = videoyu_analiz_et(link, folder_name, istem_tam)
        
        if basari:
            state_kaydet(link, folder_name)
            basarili += 1
        else:
            # KRİTİK ROLLBACK
            if STATE_CACHE and link in STATE_CACHE["mapping"]:
                del STATE_CACHE["mapping"][link]
            
            if link in state_data["mapping"]:
                del state_data["mapping"][link]
            
            if yeni_id_uretildi and NEXT_ID_COUNTER is not None:
                NEXT_ID_COUNTER -= 1

            hedef_klasor_yolu = os.path.join(PROMPT_EXPORT_ROOT, folder_name)
            if os.path.exists(hedef_klasor_yolu):
                try:
                    shutil.rmtree(hedef_klasor_yolu)
                    print(f"   (Temizlik: Başarısız klasör silindi -> {folder_name})")
                except Exception as e:
                    print(f"   (Temizlik Hatası: {e})")

            print(f"⚠ [HATA] İşlem başarısız oldu. Mapping temizlendi.")
            basarisiz += 1
        
        global_process_counter += 1

    print("\n\n")
    print("="*60)
    print("   ✅ TÜM İŞLEMLER TAMAMLANDI")
    print(f"   📂 Çıktılar: {PROMPT_EXPORT_ROOT}")
    print("="*60)
    print(f"Başarılı: {basarili}")
    print(f"Başarısız: {basarisiz}")
    if atlandi > 0:
        print(f"Atlandı (Zaten Mevcut): {atlandi}")
    print("="*60)

if __name__ == "__main__":
    main()
