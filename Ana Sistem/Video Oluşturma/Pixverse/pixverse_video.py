from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
import time
import os
import glob
import sys
import json
import re
import pyautogui  # Artık kullanılmıyor, kaldırılabilir
import pyperclip  # Artık kullanılmıyor, kaldırılabilir
# ================================
# MERKEZI KONTROL SİSTEMİ
# ================================
import os, time, sys

# Merkezi kontrol klasörü - Tüm kontrol dosyaları burada
CONTROL_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma\.control"
os.makedirs(CONTROL_DIR, exist_ok=True)

PAUSE_FLAG = os.path.join(CONTROL_DIR, "PAUSE.flag")
STOP_FLAG = os.path.join(CONTROL_DIR, "STOP.flag")
STATE_FILE = os.path.join(CONTROL_DIR, "STATE.json")

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
state_path = STATE_FILE


# Dosya yolları
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
KAYIT_DOSYA = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Pixverse\kayıt.txt"
VIDEO_ANA_KLASOR = r"C:\Users\User\Desktop\Otomasyon\Video\Video"
GORSEL_ANA_KLASOR = r"C:\Users\User\Desktop\Otomasyon\Görsel\Klon Görsel"
PROMPT_ANA_KLASOR = r"C:\Users\User\Desktop\Otomasyon\Prompt"
VIDEO_AYARLARI_DOSYA = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Pixverse\video_boyutu_süresi_ses.txt"

# ================================
def state_yukle():
    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if not isinstance(data, dict):
                    return {}
                return data
    except Exception as e:
        print(f"[WARN] STATE.json okunamadı: {e}")
    return {}

def state_kaydet(state: dict):
    try:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] STATE.json yazılamadı: {e}")

def kayit_bilgilerini_oku():
    try:
        with open(KAYIT_DOSYA, 'r', encoding='utf-8') as f:
            satirlar = f.readlines()
            email = satirlar[0].strip() if len(satirlar) > 0 else ""
            sifre = satirlar[1].strip() if len(satirlar) > 1 else ""
            return email, sifre
    except Exception as e:
        print(f"Dosya okuma hatası: {e}")
        return None, None

def prompt_klasorlerini_listele():
    """Prompt ana klasöründeki Video Prompt klasörlerini listeler"""
    try:
        klasorler = []
        if not os.path.exists(PROMPT_ANA_KLASOR):
            print(f"HATA: Prompt klasörü bulunamadı: {PROMPT_ANA_KLASOR}")
            return []
        
        # Klasör içindeki tüm öğeleri al
        for item in os.listdir(PROMPT_ANA_KLASOR):
            item_path = os.path.join(PROMPT_ANA_KLASOR, item)
            # Sadece klasörleri ve "Video Prompt" ile başlayanları al
            if os.path.isdir(item_path) and item.startswith("Video Prompt"):
                # prompt.txt dosyası var mı kontrol et
                prompt_dosya = os.path.join(item_path, "prompt.txt")
                if os.path.exists(prompt_dosya):
                    klasorler.append(item)
                else:
                    print(f"UYARI: '{item}' klasöründe prompt.txt dosyası bulunamadı, atlanıyor.")
        
        # Klasörleri sayısal sıraya göre sırala (Video Prompt 1, Video Prompt 2, ...)
        klasorler.sort(key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
        
        print(f"\nToplam {len(klasorler)} adet Video Prompt klasörü bulundu:")
        for klasor in klasorler:
            print(f"  - {klasor}")
        
        return klasorler
    except Exception as e:
        print(f"Klasör listeleme hatası: {e}")
        return []

def _normalize_prompt_name(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


def _calculate_contiguous_done_count(prompt_klasorleri, done_list):
    done_norm = {_normalize_prompt_name(x) for x in (done_list or []) if str(x).strip()}
    count = 0
    for klasor in prompt_klasorleri or []:
        if _normalize_prompt_name(klasor) in done_norm:
            count += 1
        else:
            break
    return count


def gorsel_bul(prompt_klasor_adi: str) -> Optional[Path]:
    try:
        prompt_numara = ''.join(filter(str.isdigit, prompt_klasor_adi))
        if not prompt_numara:
            return None

        # Hardcoded fallback logic that ignores REFERENCE_IMAGE_ROOT if it's pointing to the wrong place
        # 1. Klon Görsel
        klasor_secenekleri = [
            REFERENCE_IMAGE_ROOT / f"Klon Görsel {prompt_numara}",
            REFERENCE_IMAGE_ROOT / f"Görsel {prompt_numara}",
            OTOMASYON_DIR / "Görsel" / "Klon Görsel" / f"Klon Görsel {prompt_numara}",
            OTOMASYON_DIR / "Görsel" / "Görseller" / f"Görsel {prompt_numara}",
            OTOMASYON_DIR / "Prompt" / f"Video Prompt {prompt_numara}" # sometimes images are moved here!
        ]

        bulunan_klasor = None
        for k in klasor_secenekleri:
            if k.exists() and k.is_dir():
                bulunan_klasor = k
                break

        if not bulunan_klasor:
            print(f"Referans görsel klasörü bulunamadı (Tüm hedefler tarandı).")
            return None

        preferred = bulunan_klasor / "frame_0001.png"
        if preferred.exists():
            print(f"✓ Görsel bulundu: {preferred}")
            return preferred

        image_files = [
            p for p in bulunan_klasor.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ]
        if image_files:
            image_files.sort(key=lambda p: p.name.lower())
            print(f"✓ Görsel bulundu: {image_files[0]}")
            return image_files[0]

        print(f"Klasör bulundu ama içinde resim yok: {bulunan_klasor}")
        return None
    except Exception as e:
        print(f"Görsel arama hatası: {e}")
        return None

def prompt_oku(prompt_klasor_adi):
    """Belirtilen Video Prompt klasöründeki prompt.txt dosyasını okur"""
    try:
        prompt_dosya_yolu = os.path.join(PROMPT_ANA_KLASOR, prompt_klasor_adi, "prompt.txt")
        with open(prompt_dosya_yolu, 'r', encoding='utf-8') as f:
            prompt_metni = f.read().strip()
            print(f"✓ Prompt okundu: {len(prompt_metni)} karakter")
            return prompt_metni
    except Exception as e:
        print(f"Prompt dosyası okuma hatası: {e}")
        return None

def video_kayit_klasoru_olustur(prompt_klasor_adi):
    """
    Sıradaki video klasör ismini belirler (Video 1, Video 2...).
    DİKKAT: Artık klasörü burada OLUŞTURMUYOR, sadece yolu döndürüyor.
    Klasör oluşturma işlemi video başarıyla üretildikten sonra yapılacak.
    """
    try:
        # Ana video klasörünün varlığını kontrol et, yoksa sadece ana klasörü oluştur
        if not os.path.exists(VIDEO_ANA_KLASOR):
            os.makedirs(VIDEO_ANA_KLASOR, exist_ok=True)
            print(f"Ana Video klasörü oluşturuldu: {VIDEO_ANA_KLASOR}")

        # Mevcut klasörleri tara ve en büyük numarayı bul
        en_buyuk_numara = 0
        mevcut_ogeler = os.listdir(VIDEO_ANA_KLASOR)
        
        for oge in mevcut_ogeler:
            tam_yol = os.path.join(VIDEO_ANA_KLASOR, oge)
            if os.path.isdir(tam_yol) and oge.startswith("Video "):
                try:
                    # "Video 5" -> 5 sayısını al
                    numara_str = oge.split("Video ")[1]
                    if numara_str.isdigit():
                        numara = int(numara_str)
                        if numara > en_buyuk_numara:
                            en_buyuk_numara = numara
                except:
                    continue
        
        # Yeni numara = En büyük + 1
        yeni_numara = en_buyuk_numara + 1
        yeni_klasor_adi = f"Video {yeni_numara}"
        yeni_klasor_yolu = os.path.join(VIDEO_ANA_KLASOR, yeni_klasor_adi)
        
        print(f"✓ Hedef klasör yolu belirlendi: {yeni_klasor_yolu}")
        
        return yeni_klasor_yolu
        
    except Exception as e:
        print(f"Video klasörü belirleme hatası: {e}")
        return None

def video_ayarlarini_oku():
    """video_boyutu_süresi_ses.txt dosyasından ayarları okur"""
    try:
        with open(VIDEO_AYARLARI_DOSYA, 'r', encoding='utf-8') as f:
            satirlar = f.readlines()
            
            en_boy_orani = satirlar[0].strip() if len(satirlar) > 0 else "16:9"
            sure = satirlar[1].strip() if len(satirlar) > 1 else "5s"
            ses = satirlar[2].strip().lower() if len(satirlar) > 2 else "kapalı"
            
            print(f"Video ayarları okundu:")
            print(f"  En Boy Oranı: {en_boy_orani}")
            print(f"  Süre: {sure}")
            print(f"  Ses: {ses}")
            
            return en_boy_orani, sure, ses
    except Exception as e:
        print(f"Video ayarları dosyası okuma hatası: {e}")
        print("Varsayılan ayarlar kullanılıyor: 16:9, 5s, kapalı")
        return "16:9", "5s", "kapalı"


def pixverse_video_olustur(driver, wait, prompt_metni, gorsel_yolu, video_kayit_klasoru, en_boy_orani, sure, ses):
    """Tek bir video oluşturma işlemini gerçekleştirir"""
    try:
        # Ana sayfada işlem yapılıyor (login sonrası zaten buradayız)
        if "app.pixverse.ai/home" not in driver.current_url:
            driver.get("https://app.pixverse.ai/home")
            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()
            time.sleep(5)
        
        print("✓ Ana sayfada işlem yapılıyor: https://app.pixverse.ai/home")
        
        # ============================================
        # 1️⃣ AYAR PANELİNİ AÇ → EN BOY + SÜRE SEÇ
        # Alt bardaki "360P | 16:9 | 5s" trigger'ına tıkla
        # ============================================
        try:
            print(f"\n=== Ayarlar Paneli Açılıyor ===")
            
            # Alt bardaki span'a (360P/16:9/5s) tıkla → popover açılır
            ayar_trigger = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    '//div[contains(@class,"shrink-0") and contains(@class,"justify-center")]'
                    '//span[contains(@class,"text-xs") and contains(@class,"select-none")]'
                ))
            )
            driver.execute_script("arguments[0].click();", ayar_trigger)
            print("✓ Ayarlar paneli trigger'ına tıklandı")
            time.sleep(2)
            
            # Popover'ın açıldığını doğrula (video-maker-popover class'lı div bekleniyor)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.video-maker-popover'))
            )
            print("✓ Ayarlar paneli açıldı")
            
        except Exception as e:
            print(f"⚠ Ayarlar paneli açılamadı: {e}")
        
        # ============================================
        # EN BOY ORANI — popover içinden seç
        # ============================================
        try:
            print(f"\n=== En Boy Oranı Ayarı: {en_boy_orani} ===")
            
            en_boy_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f'//div[contains(@class,"video-maker-popover")]'
                    f'//div[contains(@class,"cursor-pointer") and contains(@class,"h-16")]'
                    f'//div[text()="{en_boy_orani}"]'
                ))
            )
            parent_btn = en_boy_btn.find_element(
                By.XPATH, './ancestor::div[contains(@class,"cursor-pointer") and contains(@class,"h-16")][1]'
            )
            driver.execute_script("arguments[0].click();", parent_btn)
            print(f"✓ En Boy Oranı '{en_boy_orani}' seçildi")
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠ En boy oranı '{en_boy_orani}' seçilemedi — varsayılan ayar kullanılacak: {e}")
        
        # ============================================
        # SÜRE — popover içinden seç
        # ============================================
        try:
            print(f"\n=== Süre Ayarı: {sure} ===")
            
            sure_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f'//div[contains(@class,"video-maker-popover")]'
                    f'//div[contains(@class,"h-9") and contains(@class,"cursor-pointer") and text()="{sure}"]'
                ))
            )
            driver.execute_script("arguments[0].click();", sure_btn)
            print(f"✓ Süre '{sure}' seçildi")
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠ Süre '{sure}' seçilemedi — varsayılan süre kullanılacak: {e}")
        
        # Popover kapat — body'e ESC gönder
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
        except:
            pass
        
        # ============================================
        # 2️⃣ SES AYARI
        # ============================================
        try:
            print(f"\n=== Ses Ayarı: {ses} ===")
            
            # Ses switch butonunu bul
            ses_switch = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[role="switch"]'))
            )
            
            # Mevcut durumu kontrol et
            mevcut = ses_switch.get_attribute("aria-checked") == "true"
            hedef = (ses == "açık")
            
            print(f"Mevcut ses durumu: {'açık' if mevcut else 'kapalı'}, Hedef: {ses}")
            
            # Gerekirse değiştir
            if mevcut != hedef:
                driver.execute_script("arguments[0].scrollIntoView(true);", ses_switch)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", ses_switch)
                print(f"✓ Ses '{ses}' olarak ayarlandı")
                time.sleep(2)
            else:
                print(f"✓ Ses zaten '{ses}' durumunda")
                
        except Exception as e:
            print("Ses ayarı yapılamadı — mevcut durum devam ediyor.")
        
        # ============================================
        # PANELİ KAPAT: Prompt alanına tıkla
        # ============================================
        try:
            textarea_kapat = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    'textarea[placeholder="Oluşturmak istediğiniz içeriği açıklayın"]'
                ))
            )
            driver.execute_script("arguments[0].click();", textarea_kapat)
            time.sleep(1)
        except:
            pass
        
        # ============================================
        # 3️⃣ GÖRSEL YÜKLEME (VARSA)
        # ============================================
        if gorsel_yolu and os.path.exists(gorsel_yolu):
            print(f"\n=== Görsel Yükleme ===")
            print(f"Görsel dosya yolu: {gorsel_yolu}")
            
            MAX_DENEME = 3
            gorsel_yuklendi = False
            
            for deneme in range(1, MAX_DENEME + 1):
                if deneme > 1:
                    print(f"\n🔄 Görsel yükleme tekrar deneniyor... (Deneme {deneme}/{MAX_DENEME})")
                    # Önceki denemeden açık kalan modalı kapat
                    try:
                        driver.execute_script("""
                            var btns = document.getElementsByTagName('button');
                            for (var i = 0; i < btns.length; i++) {
                                var paths = btns[i].getElementsByTagName('path');
                                for (var j = 0; j < paths.length; j++) {
                                    var d = paths[j].getAttribute('d') || '';
                                    if (d.indexOf('m5 5 14 14') !== -1) { btns[i].click(); return; }
                                }
                            }
                        """)
                        time.sleep(1.5)
                    except:
                        pass
                
                try:
                    # ADIM 1: Alt bardaki görsel ikonuna tıkla → Modal açılır
                    print("1️⃣ Görsel yükleme ikonuna tıklanıyor...")
                    gorsel_alani = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            '//div[contains(@class,"bg-white-80") and contains(@class,"w-18") '
                            'and contains(@class,"h-18") and contains(@class,"cursor-pointer")]'
                        ))
                    )
                    driver.execute_script("arguments[0].click();", gorsel_alani)
                    print("✓ Görsel yükleme ikonuna tıklandı, modal bekleniyor...")
                    time.sleep(2)
                    
                    # ADIM 2: Modal içindeki gizli file input'a direkt send_keys
                    print("2️⃣ Modal içindeki file input'a görsel gönderiliyor...")
                    file_input = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR,
                            '#image_text-customer_img_path input[type="file"]'
                        ))
                    )
                    driver.execute_script("arguments[0].style.display = 'block';", file_input)
                    time.sleep(0.3)
                    file_input.send_keys(gorsel_yolu)
                    print(f"✓ Görsel dosyası gönderildi: {os.path.basename(gorsel_yolu)}")
                    time.sleep(3)
                    
                    # ADIM 3: Yükleme tamamlanana kadar bekle, zaman aşımı hatası izle
                    print("3️⃣ Yükleme tamamlanana kadar bekleniyor...")
                    yukleme_hatasi = False
                    for kontrol in range(60):
                        bekle_pause_varsa(pause_flag)
                        stop_kontrol_noktasinda_cik()
                        # Zaman aşımı popup kontrolü
                        try:
                            hata_popup = driver.find_elements(
                                By.XPATH,
                                '//*[contains(text(),"zaman aşımı") or contains(text(),"zaman aşımına") '
                                'or contains(text(),"timeout") or contains(text(),"tekrar deneyin") '
                                'or contains(text(),"Yükleme zaman")]'
                            )
                            if hata_popup:
                                print(f"⚠ Yükleme zaman aşımı hatası! (Deneme {deneme}/{MAX_DENEME})")
                                yukleme_hatasi = True
                                break
                        except:
                            pass
                        try:
                            progress = driver.find_elements(By.CSS_SELECTOR, 'svg.ant-progress-circle')
                            if progress:
                                print(f"   Yükleniyor... ({kontrol + 1}s)")
                                time.sleep(1)
                            else:
                                print("✓ Görsel yükleme tamamlandı")
                                break
                        except:
                            break
                    
                    if yukleme_hatasi:
                        # Modalı kapat ve tekrar dene
                        driver.execute_script("""
                            var btns = document.getElementsByTagName('button');
                            for (var i = 0; i < btns.length; i++) {
                                var paths = btns[i].getElementsByTagName('path');
                                for (var j = 0; j < paths.length; j++) {
                                    var d = paths[j].getAttribute('d') || '';
                                    if (d.indexOf('m5 5 14 14') !== -1) { btns[i].click(); return; }
                                }
                            }
                        """)
                        time.sleep(2)
                        continue
                    
                    time.sleep(2)
                    
                    # ADIM 4: Görsel penceresini kapat (X butonu)
                    print("4️⃣ Görsel penceresi kapatılıyor...")
                    try:
                        kapandi = driver.execute_script("""
                            var btns = document.getElementsByTagName('button');
                            for (var i = 0; i < btns.length; i++) {
                                var paths = btns[i].getElementsByTagName('path');
                                for (var j = 0; j < paths.length; j++) {
                                    var d = paths[j].getAttribute('d') || '';
                                    if (d.indexOf('m5 5 14 14') !== -1) {
                                        btns[i].click();
                                        return 'tamam';
                                    }
                                }
                            }
                            return 'bulunamadi';
                        """)
                        if kapandi == 'tamam':
                            print("✓ Görsel penceresi kapatıldı (JS ile)")
                        else:
                            print("⚠ X buton bulunamadı, ESC ile kapatılıyor...")
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(1.5)
                    except Exception as e4:
                        print(f"⚠ X buton hatası, ESC ile kapatılıyor: {e4}")
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(1.5)
                    
                    # ADIM 5: Görsel penceresini tekrar aç
                    print("5️⃣ Görsel penceresi tekrar açılıyor...")
                    gorsel_alani2 = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            '//div[contains(@class,"bg-white-80") and contains(@class,"w-18") '
                            'and contains(@class,"h-18") and contains(@class,"cursor-pointer")]'
                        ))
                    )
                    driver.execute_script("arguments[0].click();", gorsel_alani2)
                    print("✓ Görsel penceresi tekrar açıldı")
                    time.sleep(2)
                    
                    # ADIM 6: "Yüklendi" tabına tıkla
                    print("6️⃣ 'Yüklendi' tabına geçiliyor...")
                    try:
                        yuklendi_tab = WebDriverWait(driver, 8).until(
                            EC.element_to_be_clickable((
                                By.XPATH,
                                '//button[@role="tab" and contains(.,"Yüklendi")]'
                            ))
                        )
                        driver.execute_script("arguments[0].click();", yuklendi_tab)
                        print("✓ 'Yüklendi' tabına tıklandı")
                        time.sleep(1.5)
                    except:
                        print("  'Yüklendi' tabı zaten aktif")
                    
                    # ADIM 7: Grid'deki en son yüklenen görsele tıkla
                    # JS .click() React synthetic event'i tetiklemez → JS ile elementi BUL,
                    # Python tarafında ActionChains ile TIKLA
                    print("7️⃣ Yüklenen görsel grid'den seçiliyor...")
                    gorsel_secildi = False
                    try:
                        # 2 saniye bekle - tab geçişi sonrası render tamamlansın
                        time.sleep(2)
                        
                        # JS: elementi bul ve DÖNDÜR (tıklama yok) → ActionChains ile tıkla
                        hedef_elem = driver.execute_script(r"""
                            var panels = document.querySelectorAll('[role="tabpanel"]:not([data-hidden])');
                            for (var i = 0; i < panels.length; i++) {
                                var items = [];
                                var imgs = panels[i].querySelectorAll('img');
                                for (var j = 0; j < imgs.length; j++) {
                                    var src = imgs[j].getAttribute('src') || '';
                                    if (src.indexOf('upload%2F') === -1 && src.indexOf('upload/') === -1) continue;
                                    var el = imgs[j].parentElement;
                                    while (el && el !== panels[i]) {
                                        if ((el.className || '').indexOf('cursor-pointer') !== -1) {
                                            var wrapper = el.closest('[style*="position: absolute"]') || el;
                                            var st = wrapper.getAttribute('style') || '';
                                            var tyMatch = st.match(/translateY\((\d+)/);
                                            var lxMatch = st.match(/left:\s*(\d+)/);
                                            var ty = tyMatch ? parseFloat(tyMatch[1]) : 9999;
                                            var lx = lxMatch ? parseFloat(lxMatch[1]) : 9999;
                                            items.push({el: el, ty: ty, lx: lx});
                                            break;
                                        }
                                        el = el.parentElement;
                                    }
                                }
                                if (items.length === 0) continue;
                                items.sort(function(a, b) {
                                    if (a.ty !== b.ty) return a.ty - b.ty;
                                    return a.lx - b.lx;
                                });
                                // Elementi döndür - Python ActionChains ile tıklasın
                                return items[0].el;
                            }
                            return null;
                        """)
                        
                        if hedef_elem:
                            # scroll into view + ActionChains gerçek mouse click
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", hedef_elem)
                            time.sleep(0.5)
                            ActionChains(driver).move_to_element(hedef_elem).click().perform()
                            print("✓ En son görsele tıklandı (ActionChains)")
                            gorsel_secildi = True
                        else:
                            # Yedek: XPath ile bul
                            print("⚠ Görsel JS ile bulunamadı, XPath deneniyor...")
                            gorsel_elems = driver.find_elements(
                                By.XPATH,
                                '//div[contains(@class,"aspect-video") and contains(@class,"cursor-pointer")]'
                                '[.//img[contains(@src,"upload%2F")]]'
                            )
                            if gorsel_elems:
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", gorsel_elems[0])
                                time.sleep(0.5)
                                ActionChains(driver).move_to_element(gorsel_elems[0]).click().perform()
                                print(f"✓ Görsel tıklandı (XPath yedek, {len(gorsel_elems)} bulundu)")
                                gorsel_secildi = True
                            else:
                                print("⚠ Yüklendi tabında görsel bulunamadı")
                    except Exception as e7:
                        print(f"⚠ Görsel seçim hatası: {e7}")
                    
                    time.sleep(1)
                    
                    # ADIM 8: Onayla butonu aktif olana kadar bekle → tıkla
                    print("8️⃣ 'Onayla' butonu aktif olana kadar bekleniyor...")
                    onayla_aktif = False
                    onayla_btn = None
                    for _ in range(20):
                        try:
                            btn = driver.find_element(
                                By.XPATH,
                                '//button[.//div[text()="Onayla"] '
                                'and not(contains(@class,"opacity-50")) '
                                'and not(contains(@class,"cursor-not-allowed"))]'
                            )
                            onayla_btn = btn
                            onayla_aktif = True
                            break
                        except:
                            time.sleep(0.5)
                    
                    if onayla_aktif and onayla_btn:
                        print("✓ 'Onayla' butonu aktif, tıklanıyor...")
                        ActionChains(driver).move_to_element(onayla_btn).click().perform()
                    else:
                        print("⚠ Onayla aktif bulunamadı, JS ile zorla tıklanıyor...")
                        driver.execute_script("""
                            var btns = document.querySelectorAll('button');
                            for (var b of btns) {
                                if (b.textContent.trim().includes('Onayla')) { b.click(); break; }
                            }
                        """)
                    
                    print("✓ 'Onayla' butonuna tıklandı, modal kapanıyor...")
                    
                    # ADIM 9: Modal overlay'in kapanmasını bekle
                    print("9️⃣ Modal overlay kapanana kadar bekleniyor...")
                    try:
                        WebDriverWait(driver, 15).until(
                            EC.invisibility_of_element_located((
                                By.XPATH,
                                '//div[contains(@class,"fixed") and contains(@class,"inset-0") and contains(@class,"bg-black")]'
                            ))
                        )
                        print("✓ Modal kapandı")
                    except:
                        print("⚠ Modal kapanma beklenemedi, 4 saniye bekleniyor...")
                        time.sleep(4)
                    
                    print(f"✓✓✓ Görsel yükleme başarıyla tamamlandı! (Deneme {deneme}/{MAX_DENEME})")
                    gorsel_yuklendi = True
                    break  # Başarılı → döngüden çık
                    
                except Exception as e:
                    print(f"HATA (Deneme {deneme}/{MAX_DENEME}): {e}")
                    # Modal açıksa kapat
                    try:
                        driver.execute_script("""
                            var btns = document.getElementsByTagName('button');
                            for (var i = 0; i < btns.length; i++) {
                                var paths = btns[i].getElementsByTagName('path');
                                for (var j = 0; j < paths.length; j++) {
                                    if ((paths[j].getAttribute('d') || '').indexOf('m5 5 14 14') !== -1) {
                                        btns[i].click(); return;
                                    }
                                }
                            }
                        """)
                        time.sleep(1.5)
                    except:
                        try:
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(1.5)
                        except:
                            pass
                    if deneme < MAX_DENEME:
                        print(f"   3sn sonra tekrar denenecek...")
                        time.sleep(3)
            
            if not gorsel_yuklendi:
                print(f"\n⚠⚠⚠ GÖRSEL YÜKLENEMEDİ! {MAX_DENEME} deneme başarısız.")
                print("   Görsel olmadan prompt ile devam ediliyor...")
        
        else:
            print(f"\n=== Görsel Yok ===")
            print("Görsel bulunamadı, sadece prompt ile devam ediliyor...")
        
        # ============================================
        # 5️⃣ PROMPT YAZMA
        # ============================================
        try:
            print("\n=== Prompt Yazma ===")
            
            # Önce herhangi bir overlay/modal kapandığından emin ol
            try:
                WebDriverWait(driver, 8).until(
                    EC.invisibility_of_element_located((
                        By.XPATH,
                        '//div[contains(@class,"fixed") and contains(@class,"inset-0") and contains(@style,"pointer-events: auto")]'
                    ))
                )
            except:
                pass
            time.sleep(1)
            
            textarea = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'textarea[placeholder="Oluşturmak istediğiniz içeriği açıklayın"]')
                )
            )
            
            # JS ile tıkla (overlay engelini aşmak için)
            driver.execute_script("arguments[0].click();", textarea)
            driver.execute_script("arguments[0].focus();", textarea)
            time.sleep(0.5)
            
            print("Prompt yazılıyor...")
            textarea.send_keys(prompt_metni)
            print(f"✓ Prompt başarıyla yazıldı: {prompt_metni[:50]}...")
            time.sleep(1)
            
        except Exception as e:
            print(f"Prompt yazma hatası: {e}")
            raise Exception("Prompt yazılamadı")
        
        # ============================================
        # 6️⃣ OLUŞTUR BUTONUNA TIKLA
        # ============================================
        try:
            print("\n=== Oluştur Butonu Tetikleniyor ===")
            
            # Yöntem 1: Direkt buton tıklama (öncelikli)
            yontem1_basarili = False
            try:
                print("Yöntem 1: Oluştur butonuna direkt tıklanıyor...")
                
                olustur_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        '//button[@type="button" and contains(@class, "bg-create")]//span[text()="Oluştur"]/ancestor::button'
                    ))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", olustur_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", olustur_btn)
                
                print("✓ Oluştur butonu tıklandı! (Direkt tıklama ile)")
                time.sleep(2)

                # ============================================
                # ADIM 1: HATA KONTROLÜ (Hassas İçerik)
                # ============================================
                try:
                    sensitive_toast = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((
                            By.XPATH,
                            '//*[contains(text(), "sensitive information") or contains(text(), "Please re-enter")]'
                        ))
                    )
                    print("\n" + "!"*60)
                    print("HATA: Prompt içerik üretme politikalarına uygun değil!")
                    print("(Hassas içerik uyarısı alındı - 'sensitive information')")
                    print("BU İŞLEM İPTAL EDİLİYOR, SIRADAKİNE GEÇİLECEK...")
                    print("!"*60)
                    raise Exception("HATA: Prompt içerik politikalarına uygun değil (sensitive information)")
                except Exception as sens_err:
                    if "HATA: Prompt içerik politikalarına uygun değil" in str(sens_err):
                        raise
                    pass

                # ============================================
                # ADIM 2: HATA KONTROLÜ (Prompt Uzunluğu)
                # ============================================
                try:
                    error_toast = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((
                            By.XPATH, 
                            '//div[contains(text(), "cannot exceed 2048 characters")]'
                        ))
                    )
                    # Hata bulundu → Bu işlemi iptal et, sonrakine geç
                    print("\n" + "!"*60)
                    print(f"HATA: Prompt çok uzun! ({len(prompt_metni)} karakter)")
                    print("UYARI: Prompt uzunluğunu 2048 karaktere düşürün.")
                    print("BU İŞLEM İPTAL EDİLİYOR, SIRADAKİNE GEÇİLECEK...")
                    print("!"*60)
                    raise Exception(f"HATA: Prompt çok uzun! ({len(prompt_metni)} karakter)")
                    
                except Exception as prompt_err:
                    if "HATA: Prompt çok uzun" in str(prompt_err):
                        raise
                    pass
                
                # ============================================
                # ADIM 3: VİDEO BAŞLATMA KONTROLÜ
                # ============================================
                time.sleep(2)
                try:
                    progress_check = driver.find_elements(
                        By.CSS_SELECTOR,
                        'div.text-xl.text-text-white-primary.font-semibold.text-center, svg.ant-progress-circle'
                    )
                    if progress_check:
                        print("✓ Video oluşturma süreci başladı! (Yöntem 1 başarılı)")
                        yontem1_basarili = True
                    else:
                        print("⚠ Video başlamadı, Yöntem 2 deneniyor...")
                except:
                    print("⚠ Video kontrol hatası, Yöntem 2 deneniyor...")
                
                if not yontem1_basarili:
                    raise Exception("Yöntem 1: Video başlamadı")
                    
            except Exception as e1:
                # Prompt uzunluk hatası ise direkt yukarı fırlat
                if "HATA: Prompt çok uzun" in str(e1):
                    raise
                # Hassas içerik hatası ise direkt yukarı fırlat
                if "HATA: Prompt içerik politikalarına uygun değil" in str(e1):
                    raise
                
                print(f"Yöntem 1 tamamlanamadı: {e1}")
                
                # ============================================
                # YÖNTEM 2: HTML SELECTOR ile TIKLAYoksa
                # ============================================
                try:
                    print("\nYöntem 2: HTML selector ile deneniyor...")
                    
                    olustur_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((
                            By.CSS_SELECTOR,
                            'button.bg-create[type="button"]'
                        ))
                    )
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", olustur_button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", olustur_button)
                    print("✓ Oluştur butonu tıklandı! (HTML selector ile)")
                    time.sleep(2)

                    # HATA KONTROLÜ (Hassas İçerik)
                    try:
                        sensitive_toast2 = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((
                                By.XPATH,
                                '//*[contains(text(), "sensitive information") or contains(text(), "Please re-enter")]'
                            ))
                        )
                        print("\n" + "!"*60)
                        print("HATA: Prompt içerik üretme politikalarına uygun değil!")
                        print("(Hassas içerik uyarısı alındı - 'sensitive information')")
                        print("BU İŞLEM İPTAL EDİLİYOR, SIRADAKİNE GEÇİLECEK...")
                        print("!"*60)
                        raise Exception("HATA: Prompt içerik politikalarına uygun değil (sensitive information)")
                    except Exception as sens_err2:
                        if "HATA: Prompt içerik politikalarına uygun değil" in str(sens_err2):
                            raise
                        pass

                    # HATA KONTROLÜ (Prompt Uzunluğu)
                    try:
                        error_toast = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((
                                By.XPATH, 
                                '//div[contains(text(), "cannot exceed 2048 characters")]'
                            ))
                        )
                        print("\n" + "!"*60)
                        print(f"HATA: Prompt çok uzun! ({len(prompt_metni)} karakter)")
                        print("UYARI: Prompt uzunluğunu 2048 karaktere düşürün.")
                        print("BU İŞLEM İPTAL EDİLİYOR, SIRADAKİNE GEÇİLECEK...")
                        print("!"*60)
                        raise Exception(f"HATA: Prompt çok uzun! ({len(prompt_metni)} karakter)")
                        
                    except Exception as prompt_err:
                        if "HATA: Prompt çok uzun" in str(prompt_err):
                            raise
                        pass
                    
                    time.sleep(2)
                    try:
                        progress_check = driver.find_elements(
                            By.CSS_SELECTOR,
                            'div.text-xl.text-text-white-primary.font-semibold.text-center, svg.ant-progress-circle'
                        )
                        if progress_check:
                            print("✓ Video oluşturma süreci başladı! (Yöntem 2 başarılı)")
                        else:
                            raise Exception("HATA: Oluştur butonuna tıklandı ama video başlamadı")
                    except Exception as vid_err:
                        raise Exception(f"Video kontrol hatası: {vid_err}")
                    
                except Exception as e2:
                    if "HATA: Prompt çok uzun" in str(e2):
                        raise
                    if "HATA: Prompt içerik politikalarına uygun değil" in str(e2):
                        raise
                    print(f"✗ Yöntem 2 başarısız: {e2}")
                    raise Exception(f"Video başlatılamadı: {e2}")
                    
        except Exception as e:
            # Buradaki raise dışarıya (main loop'a) fırlatılır
            raise
        
        # Video oluşma sürecini takip et
        print("\n=== Video oluşturuluyor... ===")
        max_bekleme = 300
        bekleme_sayaci = 0
        son_progress = ""
        video_hazir = False
        progress_basladi = False
        
        onceki_video_sayisi = len(driver.find_elements(By.CSS_SELECTOR, 'video[src*=".mp4"]'))
        
        while bekleme_sayaci < max_bekleme:
            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()
            try:
                progress_elements = driver.find_elements(By.CSS_SELECTOR, 'div.text-xl.text-text-white-primary.font-semibold.text-center')
                
                if progress_elements:
                    progress_text = progress_elements[0].text.strip()
                    
                    if not progress_basladi and "%" in progress_text:
                        progress_basladi = True
                        print("Video oluşturma başladı!")
                    
                    if progress_text != son_progress:
                        print(f"Video oluşuyor: {progress_text}")
                        son_progress = progress_text
                    
                    if "100%" in progress_text:
                        print("Video %100'e ulaştı, video elementi bekleniyor...")
                        time.sleep(8)
                        
                        guncel_video_sayisi = len(driver.find_elements(By.CSS_SELECTOR, 'video[src*=".mp4"]'))
                        if guncel_video_sayisi > onceki_video_sayisi:
                            print(f"✓ YENİ video oluşturuldu! (Önceki: {onceki_video_sayisi}, Şimdi: {guncel_video_sayisi})")
                            video_hazir = True
                            break
                    
                    time.sleep(3)
                    bekleme_sayaci += 3
                else:
                    if progress_basladi:
                        guncel_video_sayisi = len(driver.find_elements(By.CSS_SELECTOR, 'video[src*=".mp4"]'))
                        if guncel_video_sayisi > onceki_video_sayisi:
                            print(f"✓ YENİ video oluşturuldu! (Önceki: {onceki_video_sayisi}, Şimdi: {guncel_video_sayisi})")
                            video_hazir = True
                            break
                    
                    time.sleep(3)
                    bekleme_sayaci += 3
                        
            except Exception as e:
                time.sleep(5)
                bekleme_sayaci += 5
        
        if not video_hazir:
            raise Exception("HATA: Zaman aşımı, video oluşmadı")
        
        # ============================================
        # 7️⃣ KLASÖR OLUŞTURMA VE İNDİRME AYARI (YENİ)
        # ============================================
        print(f"\n✓ Video başarılı, kayıt klasörü şimdi oluşturuluyor: {video_kayit_klasoru}")
        try:
            if not os.path.exists(video_kayit_klasoru):
                os.makedirs(video_kayit_klasoru, exist_ok=True)
            
            driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": video_kayit_klasoru
            })
            time.sleep(1)
            
        except Exception as e:
            raise Exception(f"Klasör/İndirme yolu hatası: {e}")

        # Video indirme işlemi
        print("\n=== Video indirme işlemi başlıyor ===")
        time.sleep(5)
        
        try:
            video_elements = WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'video[src*=".mp4"]'))
            )
            
            if len(video_elements) > 0:
                en_yeni_video = video_elements[0]
                
                parent_container = driver.execute_script(
                    """
                    var video = arguments[0];
                    var parent = video.closest('div.cursor-pointer');
                    if (!parent) {
                        parent = video.closest('div[class*="cursor"]') || video.parentElement;
                    }
                    return parent;
                    """, 
                    en_yeni_video
                )
                
                if parent_container:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", parent_container)
                    time.sleep(2)
                    driver.execute_script("arguments[0].click();", parent_container)
                else:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", en_yeni_video)
                    time.sleep(2)
                    driver.execute_script("arguments[0].click();", en_yeni_video)
                
                print("✓ Video detay sayfası açıldı")
                time.sleep(8)
            else:
                raise Exception("HATA: Video elementi bulunamadı!")
                
        except Exception as e:
            raise Exception(f"Video detay açma hatası: {e}")
        
        onceki_dosyalar = sorted(glob.glob(os.path.join(video_kayit_klasoru, "*.mp4")), key=os.path.getctime)
        onceki_en_yeni = onceki_dosyalar[-1] if onceki_dosyalar else None
        
        # İndir butonunu bul ve tıkla
        try:
            download_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, 
                    '//button[.//span[contains(text(), "İndir")] or .//div[contains(text(), "İndir")] or contains(text(), "İndir") or contains(text(), "Download")]'))
            )
            
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", download_button)
            time.sleep(2)
            driver.execute_script("arguments[0].click();", download_button)
            print("✓ İndir butonu tıklandı!")
            
        except Exception as e:
            raise Exception(f"İndir butonu bulunamadı veya tıklanamadı: {e}")
        
        # İndirmenin tamamlanmasını bekle
        print("\nVideo indiriliyor...")
        bekleme = 0
        max_indirme_bekleme = 180
        
        while bekleme < max_indirme_bekleme:
            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()
            current_files = sorted(glob.glob(os.path.join(video_kayit_klasoru, "*.mp4")), key=os.path.getctime)
            yeni_dosya = None
            
            for f in current_files[::-1]:
                if onceki_en_yeni is None or os.path.getctime(f) > os.path.getctime(onceki_en_yeni):
                    yeni_dosya = f
                    break
            
            if yeni_dosya:
                print(f"✓✓✓ BAŞARI! Video indirildi: {os.path.basename(yeni_dosya)}")
                return True
            
            time.sleep(5)
            bekleme += 5
        
        raise Exception("HATA: İndirme zaman aşımına uğradı")
        
    except Exception as e:
        # Hata mesajını üst fonksiyona ilet
        print(f"Genel Hata (Video Oluşturma): {e}")
        raise e


def tarayici_yeniden_baslat(mevcut_driver, email, sifre):
    """Mevcut tarayıcıyı kapat → Yeni tarayıcı aç → Giriş yap → driver döndür"""
    print("\n=== Tarayıcı Yeniden Başlatılıyor (Temiz Sayfa İçin) ===")
    
    # 1. Mevcut tarayıcıyı kapat
    try:
        mevcut_driver.quit()
        print("✓ Eski tarayıcı kapatıldı")
    except:
        pass
    time.sleep(2)
    
    # 2. Yeni Chrome başlat
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = CHROME_PATH
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    service = Service()
    service.log_path = "NUL"
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'tr', 'en'] });
        """
    })
    print("✓ Yeni Chrome başlatıldı")
    
    # 3. Giriş yap
    driver.get("https://app.pixverse.ai/login")
    wait = WebDriverWait(driver, 20)
    
    email_input = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, 'input[placeholder="E-posta veya Kullanıcı Adı"]'
    )))
    email_input.clear()
    email_input.send_keys(email)
    time.sleep(0.5)
    
    sifre_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"][placeholder="Şifre"]')
    sifre_input.clear()
    sifre_input.send_keys(sifre)
    time.sleep(0.5)
    
    giris_btn = driver.find_element(By.XPATH, '//button[.//div[text()="Giriş"]]')
    giris_btn.click()
    time.sleep(8)
    
    # 4. Popup kapat
    try:
        popup_kapat = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.XPATH, '//div[@role="dialog"]//button[contains(@class,"absolute") and contains(@class,"right-4")]'
            ))
        )
        popup_kapat.click()
        time.sleep(2)
    except:
        pass
    
    print("✓ Giriş tamamlandı, temiz tarayıcı hazır!")
    return driver, wait


def pixverse_giris():
    """Ana işlem fonksiyonu - tüm prompt klasörlerini işler"""
    
    # Başarısız işlemleri takip eden liste
    basarisiz_islemler = []
    
    email, sifre = kayit_bilgilerini_oku()
    
    if not email or not sifre:
        print("Email veya şifre bulunamadı!")
        return
    
    print(f"Email: {email}")
    print(f"Şifre: {'*' * len(sifre)}")
    
    # Prompt klasörlerini listele
    prompt_klasorleri = prompt_klasorlerini_listele()
    
    if not prompt_klasorleri:
        print("\nHATA: İşlenecek Video Prompt klasörü bulunamadı!")
        return

    # === PAUSE + STATE (kaldığı yerden devam) ===
    bekle_pause_varsa(pause_flag)
    stop_kontrol_noktasinda_cik()
    state = state_yukle()
    
    # DÜZELTME: pixverse_video için özel bir state alanı kullanalım ki diğer işlemlerle karışmasın
    pixverse_state = state.get("pixverse_state", {})
    done = pixverse_state.get("done", [])
    if not isinstance(done, list):
        done = []

    # Done listesini mevcut prompt klasörleriyle hizala.
    # Böylece yalnızca gerçekten tamamlanan klasörler korunur.
    done_norm = {_normalize_prompt_name(x) for x in done if str(x).strip()}
    done = [klasor for klasor in prompt_klasorleri if _normalize_prompt_name(klasor) in done_norm]

    # Önceki oturumda tamamlanan videolar done listesinde mevcut.
    # basarili_islemler bu listeden başlatılır ki devam senaryosunda
    # final raporda toplam başarılı sayısı doğru görünsün.
    basarili_islemler = list(done)
    if basarili_islemler:
        print(f"[INFO] Önceki oturumdan {len(basarili_islemler)} tamamlanmış video yüklendi: {', '.join(basarili_islemler)}")

    # last_success değeri tek başına güvenilir değil.
    # Video Prompt 1 başarısız, Video Prompt 2 başarılı olduğunda kayıt 2 olarak kalabiliyor
    # ve retry sırasında başarısız öğe de yanlışlıkla atlanıyor.
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

    start_index = contiguous_done_count + 1  # 1-based, sadece kesintisiz başarı zinciri kadar ilerle

    
    # Video ayarlarını oku
    en_boy_orani, sure, ses = video_ayarlarini_oku()
    
    # Chrome ayarları
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = CHROME_PATH
    chrome_options.add_argument("--headless=new")  # CDP sayesinde headless çalışır
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    service = Service()
    service.log_path = "NUL"
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'tr', 'en'] });
            """
        })
        
        print("\nChrome başlatıldı")
        
        # Giriş işlemi
        driver.get("https://app.pixverse.ai/login")
        print("Login sayfası açıldı")
        
        wait = WebDriverWait(driver, 20)
        
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="E-posta veya Kullanıcı Adı"]')))
        email_input.clear()
        email_input.send_keys(email)
        time.sleep(1)
        
        sifre_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"][placeholder="Şifre"]')
        sifre_input.clear()
        sifre_input.send_keys(sifre)
        time.sleep(1)
        
        giris_button = driver.find_element(By.XPATH, '//button[.//div[text()="Giriş"]]')
        giris_button.click()
        
        time.sleep(8)
        print("Giriş işlemi tamamlandı!")
        
        # Popup kapatma
        try:
            popup_kapat_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@role="dialog"]//button[contains(@class, "absolute") and contains(@class, "right-4")]'))
            )
            popup_kapat_btn.click()
            time.sleep(2)
        except:
            pass
        
        # Döngü başlangıcı
        for i, prompt_klasor in enumerate(prompt_klasorleri, 1):
            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()
            # STATE.json: tamamlananları atla
            if (prompt_klasor in done) or (i < start_index):
                print(f"ATLANIYOR: {prompt_klasor} (Zaten tamamlanmış)")
                continue

            print("\n" + "="*70)
            print(f"İŞLEM {i}/{len(prompt_klasorleri)}: {prompt_klasor}")
            print("="*70)
            
            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()
            prompt_metni = prompt_oku(prompt_klasor)
            if not prompt_metni:
                basarisiz_islemler.append(f"{prompt_klasor} ( HATA: Prompt dosyası okunamadı )")
                continue
            
            gorsel_yolu = gorsel_bul(prompt_klasor)
            
            video_kayit_klasoru = video_kayit_klasoru_olustur(prompt_klasor)
            if not video_kayit_klasoru:
                basarisiz_islemler.append(f"{prompt_klasor} ( HATA: Klasör yolu belirlenemedi )")
                continue
            
            try:
                # 2. işlemden itibaren: tarayıcıyı kapat → yeni tarayıcı aç → giriş yap
                if i > 1 or (i == 1 and start_index > 1):
                    driver, wait = tarayici_yeniden_baslat(driver, email, sifre)
                
                # Her yeni video işleminde ana sayfayı tazele
                driver.get("https://app.pixverse.ai/home")
                time.sleep(5)
                
                # Video oluşturma fonksiyonunu çağır
                basari_durumu = pixverse_video_olustur(
                    driver, wait, prompt_metni, gorsel_yolu, 
                    video_kayit_klasoru, en_boy_orani, sure, ses
                )
                
                if basari_durumu:
                    print(f"✓✓✓ '{prompt_klasor}' için video başarıyla oluşturuldu!")
                    basarili_islemler.append(prompt_klasor)
                    
                    # DÜZELTME: STATE.json güncelle (başarılı işlem sonrası)
                    # pixverse_state alanını güncelleyip ana state içine gömüyoruz
                    if prompt_klasor not in done:
                        done.append(prompt_klasor)

                    pixverse_state["done"] = done
                    pixverse_state["last_success"] = _calculate_contiguous_done_count(prompt_klasorleri, done)
                    state["pixverse_state"] = pixverse_state
                    state_kaydet(state)

                
            except Exception as e:
                # Hata mesajını string'e çevir
                hata_mesaji = str(e)
                print(f"✗✗✗ '{prompt_klasor}' başarısız oldu!")
                print(f"Sebep: {hata_mesaji}")
                
                # Listeye ekle: Klasör Adı ( HATA: ... )
                basarisiz_islemler.append(f"{prompt_klasor} ( {hata_mesaji} )")
            
            # Bekleme
            if i < len(prompt_klasorleri):
                print(f"\nBir sonraki işleme geçiliyor... (5 saniye bekleniyor)")
                time.sleep(5)
        
        # ======================================================================
        # SONUÇ RAPORU (İstenilen Format)
        # ======================================================================
        print("\n" + "="*70)
        print("TÜM İŞLEMLER TAMAMLANDI!")
        print("="*70)
        print(f"Toplam İşlem: {len(prompt_klasorleri)}")
        
        # Başarılıları yazdır
        basarili_str = " - ".join(basarili_islemler) if basarili_islemler else "Yok"
        print(f"Başarılı: {len(basarili_islemler)} - {basarili_str}")
        
        # Başarısızları yazdır
        basarisiz_str = " - ".join(basarisiz_islemler) if basarisiz_islemler else "Yok"
        print(f"Başarısız: {len(basarisiz_islemler)} - {basarisiz_str}")
        
        print("="*70)
        
    except Exception as e:
        print(f"Genel sistem hatası: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            if driver:
                time.sleep(3)
                driver.quit()
                print("\nTarayıcı kapatıldı")
        except:
            pass

if __name__ == "__main__":
    pixverse_giris()