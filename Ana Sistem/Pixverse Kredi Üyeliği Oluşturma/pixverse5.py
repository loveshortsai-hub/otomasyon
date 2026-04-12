import os
import sys
import time
import logging
import re
import requests
import random
import string
import subprocess
import shutil  # Klasör silmek için eklendi
import signal  # Process sonlandırmak için eklendi
from pathlib import Path
from datetime import datetime

# Subprocess olarak çalışırken stdout satır bazlı flush olsun (canlı log için)
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# --- EKLENEN IMPORTLAR (Tuş kombinasyonları için) ---
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
# ----------------------------------------------------

# -----------------------------
# Ayarlar
# -----------------------------
TIMEOUT = 30
STEP_TIMEOUT = 5
NAME_FILE = "name.txt"
USED_NAMES_FILE = "used_names.txt"
FAILED_NAMES_FILE = "failed_names.txt"

# TempMail.so API Ayarları
TEMPMAIL_SO_BASE_URL     = "https://tempmail-so.p.rapidapi.com"
TEMPMAIL_SO_RAPIDAPI_KEY = "3726f3e100msha9f8b4a07bdec1fp1e901bjsne3631f941eee"
TEMPMAIL_SO_AUTH_TOKEN   = "54A68A9F-902B-AED8-1BC5-E4A7331BF919"

# Sabit şifre
PASSWORD = "0539248574asd"

# Davet kodu
INVITE_CODE = "JR7QAWG8"

# Cloudflare kontrol ayarları
CLOUDFLARE_CHECK_TIMEOUT = 180  # 3 dakika
CLOUDFLARE_CHECK_INTERVAL = 10  # 10 saniye

# Screenshot kaldırıldı

# -----------------------------
# Chrome / Clean Mode Ayarları
# -----------------------------
CLEAN_MODE = False
# ---------------------------------------------------------------------------
# HEADLESS_MODE ayarı:
#   True  → --headless=new (görünmez, pencere yok)
#             ⚠️ TEST SONUCU: Cloudflare Turnstile headless modda GEÇİLEMİYOR!
#             GPU sinyali eksikliği ve gerçek mouse etkileşimi olmadığından
#             CF token üretilemiyor. Yalnızca Cloudflare gerektirmeyen sayfalarda
#             veya gelecekte CF bypass çözümü bulunursa kullanılabilir.
#   False → --window-position=-10000,0 (ekran dışında, görünmez ama aktif)
#             ✅ Cloudflare Turnstile bu modda başarıyla geçilebiliyor.
#             Tavsiye edilen ve varsayılan mod budur.
# ---------------------------------------------------------------------------
HEADLESS_MODE = False  # ← off-screen mod aktif (Cloudflare uyumlu)
DEBUG_PORT = 9222
# Profil klasörünü scriptin olduğu dizinde oluşturur
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_clean_profile")


# Global Process Değişkeni (Kapatırken kullanmak için)
CHROME_PROCESS = None

# Chrome Exe Yolu
if os.path.exists(r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
elif os.path.exists(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
    CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
else:
    CHROME_PATH = "chrome.exe"

# -----------------------------
# Yardımcı Fonksiyonlar
# -----------------------------
def runtime_path(filename: str) -> str:
    """Dosya yolunu belirler"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def ensure_dir(path: str):
    """Klasör yoksa oluşturur"""
    Path(path).mkdir(parents=True, exist_ok=True)

def init_logger():
    """Logger'ı başlatır"""
    # Her emit sonrası mutlaka flush yapan handler (canlı log için kritik)
    class FlushingStreamHandler(logging.StreamHandler):
        def emit(self, record):
            super().emit(record)
            try:
                self.stream.flush()
            except Exception:
                pass

    handlers = [FlushingStreamHandler(sys.stdout)]
    
    try:
        log_file = runtime_path("bot.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    pass
                handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
            except PermissionError:
                timestamp = int(time.time())
                new_log_file = runtime_path(f"bot_{timestamp}.log")
                handlers.append(logging.FileHandler(new_log_file, encoding='utf-8'))
                print(f"⚠️ bot.log açık olduğu için yeni dosya kullanılıyor: bot_{timestamp}.log")
        else:
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    except Exception as e:
        print(f"⚠️ Log dosyası oluşturulamadı, sadece console'a yazılacak: {e}")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers
    )

def ts():
    """Timestamp döndürür"""
    return datetime.now().strftime("%H:%M:%S")

def check_pause():
    """pause.txt dosyasını kontrol eder ve gerekirse bekler"""
    pause_file = runtime_path("pause.txt")
    if os.path.exists(pause_file):
        with open(pause_file, "r") as f:
            status = f.read().strip().lower()
        _pause_logged = False
        while status == "pause":
            if not _pause_logged:
                logging.info("[!] Bot duraklatıldı. Devam etmek için 'resume' bekleniyor...")
                _pause_logged = True
            time.sleep(2)
            with open(pause_file, "r") as f:
                status = f.read().strip().lower()
        if _pause_logged:
            logging.info("[✓] Bot devam ediyor.")

def generate_random_usernames(count=120):
    """Rastgele kullanıcı adları üretir ve name.txt'ye yazar"""
    first_names = [
        "zeynep", "fatma", "buse", "elif", "ayse", "merve", "selin", "deniz",
        "ceren", "ece", "tugba", "gamze", "derya", "esra", "pinar", "sibel",
        "ozge", "melis", "irem", "defne", "yagmur", "asli", "hazal", "nisa",
        "betul", "kubra", "sevgi", "hilal", "gizem", "cansu", "busra", "damla",
        "ebru", "ilknur", "gulsen", "hande", "ipek", "jale", "kezban", "leyla",
        "muge", "nalan", "oya", "pelin", "reyhan", "seda", "tugce", "umut",
        "vildan", "yasemin", "zara", "ada", "beren", "cemre", "dilan", "eylul",
        "feray", "gonca", "havin", "irmak", "julide", "kardelen", "lale", "mine",
    ]
    last_names = [
        "keskin", "cetin", "gunes", "yilmaz", "kaya", "demir", "sahin", "ozturk",
        "arslan", "dogan", "kilic", "aydin", "ozkan", "polat", "korkmaz", "celik",
        "aksoy", "bulut", "erdogan", "tekin", "ucar", "koc", "tas", "kurt",
        "ozer", "acar", "basar", "cinar", "duran", "erdem", "firat", "guler",
        "inal", "kaplan", "mutlu", "orhan", "sari", "turan", "uzun", "vardar",
    ]
    usernames = []
    used = set()
    while len(usernames) < count:
        first = random.choice(first_names)
        last = random.choice(last_names)
        num = random.randint(1, 999)
        name = f"{first}{last}{num}"
        if name not in used:
            used.add(name)
            usernames.append(name)
    # name.txt'ye yaz
    path = runtime_path(NAME_FILE)
    with open(path, "w", encoding="utf-8") as f:
        for u in usernames:
            f.write(u + "\n")
    logging.info(f"🎲 {count} adet rastgele kullanıcı adı üretildi ve name.txt'ye yazıldı.")
    return usernames


def ensure_names_exist():
    """name.txt boşsa veya yoksa 120 rastgele kullanıcı adı üretir"""
    path = runtime_path(NAME_FILE)
    if not os.path.exists(path):
        logging.info("📝 name.txt bulunamadı, yeni kullanıcı adları üretiliyor...")
        generate_random_usernames(120)
        return
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    if not lines:
        logging.info("📝 name.txt boş, yeni kullanıcı adları üretiliyor...")
        generate_random_usernames(120)


def get_next_username():
    """name.txt'den ilk kullanıcı adını alır"""
    try:
        path = runtime_path(NAME_FILE)
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if not lines:
            logging.info("⚠️ name.txt boş, yeni kullanıcı adları üretiliyor...")
            generate_random_usernames(120)
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            if not lines:
                logging.error("❌ Kullanıcı adı üretilemedi!")
                return None
            
        return lines[0]
    except Exception as e:
        logging.error(f"❌ Kullanıcı adı okuma hatası: {e}")
        return None

def remove_username_from_file(username):
    """Kullanıcı adını name.txt'den siler"""
    try:
        name_path = runtime_path(NAME_FILE)
        with open(name_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if username in lines:
            lines.remove(username)
            logging.info(f"🗑️ '{username}' name.txt'den silindi.")
        
        with open(name_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
                
    except Exception as e:
        logging.error(f"❌ Kullanıcı adı silme hatası: {e}")

def save_used_username(username, email):
    """Başarılı kullanıcı adını used_names.txt'ye kaydeder"""
    try:
        used_path = runtime_path(USED_NAMES_FILE)
        with open(used_path, "a", encoding="utf-8") as f:
            f.write(f"{username} | {email}\n")
        logging.info(f"💾 '{username}' used_names.txt'ye kaydedildi.")
    except Exception as e:
        logging.error(f"❌ Başarılı kullanıcı adı kaydetme hatası: {e}")

def save_failed_username(username, reason=""):
    """Başarısız kullanıcı adını failed_names.txt'ye kaydeder"""
    try:
        failed_path = runtime_path(FAILED_NAMES_FILE)
        with open(failed_path, "a", encoding="utf-8") as f:
            f.write(f"{username} | {reason}\n")
        logging.info(f"📝 '{username}' failed_names.txt'ye kaydedildi. Sebep: {reason}")
    except Exception as e:
        logging.error(f"❌ Başarısız kullanıcı adı kaydetme hatası: {e}")

# take_screenshot kaldırıldı

def is_button_enabled(driver, button_element):
    """Butonun aktif olup olmadığını kontrol eder"""
    try:
        is_disabled = button_element.get_attribute("disabled")
        if is_disabled:
            logging.debug("🔍 Buton disabled attribute'ü var")
            return False
        
        aria_disabled = button_element.get_attribute("aria-disabled")
        if aria_disabled == "true":
            logging.debug("🔍 Buton aria-disabled=true")
            return False
        
        button_classes = button_element.get_attribute("class") or ""
        if "disabled" in button_classes.lower():
            logging.debug("🔍 Buton class'ında disabled var")
            return False
        
        opacity = driver.execute_script("return window.getComputedStyle(arguments[0]).opacity;", button_element)
        if opacity and float(opacity) < 0.5:
            logging.debug(f"🔍 Buton opacity düşük: {opacity}")
            return False
        
        pointer_events = driver.execute_script("return window.getComputedStyle(arguments[0]).pointerEvents;", button_element)
        if pointer_events == "none":
            logging.debug("🔍 Buton pointer-events: none")
            return False

        logging.debug("✅ Buton aktif görünüyor")
        return True
    except Exception as e:
        logging.warning(f"⚠️ Buton aktiflik kontrolü hatası: {e}")
        return False


# -----------------------------
# Tarayıcı Temizleme ve Kapatma
# -----------------------------
def force_close_browser(driver=None):
    """Tarayıcıyı ve subprocess'i zorla kapatır"""
    global CHROME_PROCESS

    # 1. Önce Selenium driver'ı kapatmaya çalış
    if driver:
        try:
            driver.quit()
        except Exception:
            pass

    # 2. Subprocess ile açılan Chrome'u kapat
    chrome_pid = None
    if CHROME_PROCESS:
        chrome_pid = CHROME_PROCESS.pid
        try:
            logging.info("🔌 Chrome işlemi sonlandırılıyor...")
            CHROME_PROCESS.terminate()
            try:
                CHROME_PROCESS.wait(timeout=5)
            except subprocess.TimeoutExpired:
                CHROME_PROCESS.kill()
                CHROME_PROCESS.wait(timeout=3)
        except Exception as e:
            logging.error(f"⚠️ Process kapatma hatası: {e}")
        finally:
            CHROME_PROCESS = None

    # 3. PID bazlı taskkill — kritik: port/başlık filtresi yerine doğrudan PID ile
    if chrome_pid:
        try:
            subprocess.run(
                f"taskkill /F /PID {chrome_pid}",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    # 4. Port 9222'yi kullanan tüm chrome.exe süreçlerini temizle (ek güvence)
    try:
        # netstat üzerinden port 9222'yi kullanan PID'i bul ve öldür
        result = subprocess.run(
            f"netstat -ano | findstr :{DEBUG_PORT}",
            shell=True, capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts:
                pid_str = parts[-1]
                if pid_str.isdigit() and pid_str != '0':
                    subprocess.run(
                        f"taskkill /F /PID {pid_str}",
                        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
    except Exception:
        pass

    # Port'un serbest kalması için bekle
    time.sleep(3)

def clean_profile_data():
    """Chrome profil klasörünü siler (Veri kalıntısını önlemek için)"""
    if os.path.exists(USER_DATA_DIR):
        try:
            logging.info("🧹 Eski profil verileri temizleniyor...")
            shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
            # Kısa bir bekleme, dosya sistemi yetişsin
            time.sleep(1)
            logging.info("✅ Profil temizlendi.")
        except Exception as e:
            logging.warning(f"⚠️ Profil temizleme hatası: {e}")

# -----------------------------
# Cloudflare Kontrolü
# -----------------------------
def check_cloudflare_turnstile(driver):
    """Cloudflare Turnstile durumunu kontrol eder"""
    try:
        el = driver.find_element(By.NAME, "cf-turnstile-response")
        val = el.get_attribute("value") or ""
        if len(val) > 50:
            return "SUCCESS", len(val)
        return "PENDING", 0
    except:
        return "NOT_FOUND", 0

def wait_for_cloudflare(driver, max_retry=3):
    """Cloudflare onayını bekler, gerekirse sayfayı yeniler"""
    # Bu fonksiyon giriş kısmında (ilk sayfa yüklenişi) kullanılıyor.
    # Kayıt formundaki özel mantık register_pixverse içinde tanımlı.
    
    for retry in range(1, max_retry + 1):
        logging.info(f"{'='*60}")
        logging.info(f"☁️ CLOUDFLARE KONTROL - DENEME {retry}/{max_retry}")
        logging.info(f"{'='*60}")
        
        start_time = time.time()
        round_no = 0
        
        while True:
            elapsed = int(time.time() - start_time)
            
            if elapsed > CLOUDFLARE_CHECK_TIMEOUT:
                logging.warning(f"⏰ [{ts()}] Cloudflare timeout ({CLOUDFLARE_CHECK_TIMEOUT}s)")
                break
            
            round_no += 1
            status, token_len = check_cloudflare_turnstile(driver)
            
            logging.info(
                f"[{ts()}] Kontrol #{round_no} | "
                f"{elapsed}s | {status} | token_len={token_len}"
            )
            
            if status == "SUCCESS":
                logging.info(f"[{ts()}] ✅ CLOUDFLARE ONAYLANDI")
                return True
            
            if status == "NOT_FOUND":
                logging.debug(f"[{ts()}] Cloudflare elementi bulunamadı (henüz yüklenmemiş olabilir)")
            
            time.sleep(CLOUDFLARE_CHECK_INTERVAL)
        
        # Timeout oldu ve son deneme değilse sayfayı yenile
        if retry < max_retry:
            logging.info(f"🔄 Cloudflare onaylanamadı, sayfa yenileniyor...")
            driver.refresh()
            time.sleep(15)  # Sayfa yüklenmesi için bekle
        else:
            logging.error(f"❌ Cloudflare {max_retry} denemede onaylanamadı!")
            return False
    
    return False

# -----------------------------
# TempMail.so Fonksiyonları
# -----------------------------
def _tempmail_so_headers():
    """TempMail.so için gerekli auth header'larını döndürür"""
    return {
        "x-rapidapi-key":  TEMPMAIL_SO_RAPIDAPI_KEY,
        "x-rapidapi-host": "tempmail-so.p.rapidapi.com",
        "Authorization":   f"Bearer {TEMPMAIL_SO_AUTH_TOKEN}",
        "Content-Type":    "application/json"
    }

def create_temp_email():
    """TempMail.so ile geçici mail adresi oluşturur"""
    try:
        logging.info("📧 TempMail.so ile geçici mail oluşturuluyor...")
        headers = _tempmail_so_headers()

        # 1. Domain listesini al
        logging.debug("🔍 Domain alınıyor...")
        domains_response = requests.get(
            f"{TEMPMAIL_SO_BASE_URL}/domains",
            headers=headers
        )
        if domains_response.status_code != 200:
            logging.error(f"❌ Domain alınamadı: {domains_response.status_code} - {domains_response.text}")
            return None, None, None

        domains_data = domains_response.json()
        logging.info(f"📦 Domains API ham yanıtı: {domains_data}")
        domain_list = domains_data.get("data", [])
        if not domain_list:
            logging.error(f"❌ Kullanılabilir domain yok. Ham yanıt: {domains_data}")
            return None, None, None

        PREFERRED_DOMAIN = "draughtier.com"
        available = [d["domain"] for d in domain_list]
        if PREFERRED_DOMAIN in available:
            domain = PREFERRED_DOMAIN
        else:
            logging.warning(f"⚠️ {PREFERRED_DOMAIN} bulunamadı, ilk domain kullanılıyor.")
            domain = available[0]
        logging.info(f"✅ Domain alındı: {domain}")

        # 2. Random kullanıcı adı üret
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"{username}@{domain}"
        logging.info(f"📝 Email oluşturulacak: {email}")

        # 3. Inbox oluştur (JSON body)
        inbox_response = requests.post(
            f"{TEMPMAIL_SO_BASE_URL}/inboxes",
            headers=headers,
            json={
                "name":     username,
                "domain":   domain,
                "lifespan": 1800  # Ücretsiz plan max: 1800 saniye (30 dakika)
            }
        )

        if inbox_response.status_code != 200:
            logging.error(f"❌ Inbox oluşturulamadı: {inbox_response.status_code} - {inbox_response.text}")
            return None, None, None

        inbox_data = inbox_response.json()
        logging.info(f"📦 Inbox API yanıtı: {inbox_data}")

        data = inbox_data.get("data", {})
        if isinstance(data, dict):
            inbox_id = data.get("id") or data.get("name") or data.get("address") or data.get("email")
        else:
            inbox_id = None

        if not inbox_id:
            logging.error(f"❌ Inbox ID alınamadı. Tam yanıt: {inbox_data}")
            return None, None, None

        logging.info(f"✅ Geçici mail hazır: {email} | Inbox ID: {inbox_id}")
        return email, inbox_id, inbox_id

    except Exception as e:
        logging.error(f"❌ Geçici mail oluşturma hatası: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None, None, None


def wait_for_verification_email(inbox_id, timeout=60):
    """TempMail.so'dan doğrulama kodunu bekler ve alır"""
    try:
        headers = _tempmail_so_headers()

        logging.info(f"⏳ Doğrulama maili bekleniyor (timeout: {timeout}s)...")

        start_time = time.time()
        check_count = 0

        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = int(time.time() - start_time)
            logging.info(f"📬 Mail kontrolü #{check_count} (geçen süre: {elapsed}s)")

            try:
                mails_response = requests.get(
                    f"{TEMPMAIL_SO_BASE_URL}/inboxes/{inbox_id}/mails",
                    headers=headers
                )

                if mails_response.status_code != 200:
                    logging.warning(f"⚠️ Mesaj kontrol hatası: {mails_response.status_code}")
                    time.sleep(3)
                    continue

                mails_data = mails_response.json()
                mails = mails_data.get("data", [])

                if mails and len(mails) > 0:
                    latest = mails[0]
                    mail_id = latest["id"]

                    logging.info("✅ Mail geldi!")
                    logging.info(f"📧 Konu: {latest.get('subject', 'Konu yok')}")
                    logging.info(f"👤 Gönderen: {latest.get('from', 'Bilinmiyor')}")

                    logging.debug("🔍 Mail içeriği alınıyor...")
                    detail_response = requests.get(
                        f"{TEMPMAIL_SO_BASE_URL}/inboxes/{inbox_id}/mails/{mail_id}",
                        headers=headers
                    )

                    if detail_response.status_code != 200:
                        logging.warning("⚠️ Mesaj detayı alınamadı")
                        time.sleep(3)
                        continue

                    detail = detail_response.json().get("data", {})

                    text_body = str(detail.get("textContent") or "")
                    html_body = str(detail.get("htmlContent") or "")

                    # HTML tag'lerini ve renk kodlarını temizle
                    clean_html = re.sub(r'<[^>]+>', ' ', html_body)
                    clean_html = re.sub(r'#[0-9a-fA-F]{6}', ' ', clean_html)

                    email_body_text = text_body
                    email_body_full = text_body + " " + clean_html

                    logging.info(f"📄 Mail içeriği uzunluğu: textContent={len(text_body)}, htmlContent={len(html_body)}")
                    logging.debug("🔍 Doğrulama kodu aranıyor...")

                    # Yöntem 1-3: Önce textContent, sonra tam içerik
                    for search_body, label in [(email_body_text, "textContent"), (email_body_full, "tam içerik")]:
                        match = re.search(r'Your PixVerse verification code is[\s:]*(\d{6})', search_body, re.IGNORECASE)
                        if match:
                            code = match.group(1)
                            logging.info(f"✅ Doğrulama kodu bulundu (Yöntem 1 - {label}): {code}")
                            return code

                        match = re.search(r'verification code is[\s:]*(\d{6})', search_body, re.IGNORECASE)
                        if match:
                            code = match.group(1)
                            logging.info(f"✅ Doğrulama kodu bulundu (Yöntem 2 - {label}): {code}")
                            return code

                        match = re.search(r'code[\s:]+(\d{6})', search_body, re.IGNORECASE)
                        if match:
                            code = match.group(1)
                            logging.info(f"✅ Doğrulama kodu bulundu (Yöntem 3 - {label}): {code}")
                            return code

                    # Yöntem 4: Tüm 6 haneli sayılar (sadece textContent)
                    search_for_all = email_body_text if email_body_text else email_body_full
                    matches = re.findall(r'\b(\d{6})\b', search_for_all)

                    if matches:
                        logging.info(f"🔢 Bulunan tüm 6 haneli kodlar: {matches}")
                        filtered_codes = []
                        for code in matches:
                            if len(set(code)) == 1:
                                continue
                            if code == (code[:2] * 3):
                                continue
                            if code in ['123456', '234567', '345678', '456789', '654321', '765432']:
                                continue
                            filtered_codes.append(code)

                        if filtered_codes:
                            code = filtered_codes[0]
                            logging.info(f"✅ Filtrelenmiş kod bulundu: {code}")
                            return code
                        else:
                            code = matches[0]
                            logging.warning(f"⚠️ Filtre sonrası kod kalmadı, ilk kod kullanılıyor: {code}")
                            return code

                    logging.error("❌ Mail içinde doğrulama kodu bulunamadı!")
                    return None

                time.sleep(3)

            except Exception as e:
                logging.warning(f"⚠️ Mesaj kontrol sırasında hata: {e}")
                time.sleep(3)
                continue

        logging.error(f"❌ {timeout} saniye içinde mail gelmedi.")
        return None

    except Exception as e:
        logging.error(f"❌ Mail bekleme hatası: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None

# -----------------------------
# Selenium Fonksiyonları
# -----------------------------
def init_driver():
    """Chrome'u subprocess ile başlatır ve Selenium ile bağlanır (Güncellendi)"""
    global CHROME_PROCESS
    check_pause()
    
    logging.info("="*60)
    if HEADLESS_MODE:
        logging.info("🕶️ HEADLESS MODE: Chrome görünmez (headless=new) başlatılıyor")
    elif CLEAN_MODE:
        logging.info("🧼 CLEAN MODE: Temiz Chrome Başlatılıyor (Ekran Dışı Mod)")
    else:
        logging.info("🚀 SUBPROCESS İLE CHROME BAŞLATILIYOR (Ekran Dışı Mod)")
    logging.info("="*60)
    
    # Profil klasörünü oluştur
    ensure_dir(USER_DATA_DIR)
    
    # Chrome Preferences dosyasına şifre kaydetme ve translate ayarlarını yaz
    try:
        import json as _json
        default_dir = os.path.join(USER_DATA_DIR, "Default")
        ensure_dir(default_dir)
        prefs_path = os.path.join(default_dir, "Preferences")
        prefs_data = {}
        if os.path.exists(prefs_path):
            try:
                with open(prefs_path, "r", encoding="utf-8") as pf:
                    prefs_data = _json.load(pf)
            except Exception:
                prefs_data = {}
        # Şifre kaydetme popup'ını devre dışı bırak
        prefs_data.setdefault("credentials_enable_service", False)
        prefs_data.setdefault("profile", {})
        prefs_data["profile"]["password_manager_enabled"] = False
        # Google Translate'ı devre dışı bırak
        prefs_data.setdefault("translate", {})
        prefs_data["translate"]["enabled"] = False
        prefs_data.setdefault("translate_blocked_languages", ["tr", "en"])
        with open(prefs_path, "w", encoding="utf-8") as pf:
            _json.dump(prefs_data, pf, ensure_ascii=False)
    except Exception as e:
        logging.debug(f"Preferences dosyası yazılamadı: {e}")
    
    # Chrome subprocess komutu
    cmd_command = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--window-size=1920,1080",
        "--no-first-run",
        "--no-default-browser-check",
        # --- Google Translate ve Şifre Kaydetme Popup'larını Devre Dışı Bırak ---
        "--disable-translate",
        "--disable-features=CalculateNativeWinOcclusion,TranslateUI",
        "--disable-popup-blocking",
        "--disable-save-password-bubble",
        "--lang=tr",
        # --- ARKA PLAN PERFORMANS AYARLARI ---
        "--disable-renderer-backgrounding",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        # --- HEADLESS / OFFSCREEN MODU ---
    ]
    if HEADLESS_MODE:
        # --headless=new: Cloudflare'e karşı daha az iz bırakan Chrome headless modu
        cmd_command += [
            "--headless=new",
            "--hide-scrollbars",
            "--mute-audio",
            "--disable-gpu",                    # headless'ta gerekli olabilir
            "--disable-software-rasterizer",    # GPU hatalarını önler
            "--disable-dev-shm-usage",          # bellek sorunlarını önler
        ]
    else:
        # Ekran dışında konumlandır (görünmez ama aktif — Cloudflare için daha güvenli)
        cmd_command += [
            "--window-position=-10000,0",
            "--mute-audio",   # Tarayıcı sesini tamamen kapat
        ]
    
    try:
        logging.info(f"📂 Profil klasörü: {USER_DATA_DIR}")
        logging.info(f"🔌 Debug portu: {DEBUG_PORT}")
        logging.info("⚙️ Chrome subprocess ile başlatılıyor...")
        
        # Chrome'u subprocess ile başlat ve process objesini sakla
        CHROME_PROCESS = subprocess.Popen(cmd_command, 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        # Tarayıcının açılması için bekle
        logging.info("⏳ Tarayıcı başlatılıyor (5 saniye)...")
        time.sleep(5)
        
        # Selenium seçenekleri
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
        
        # Selenium'u çalışan tarayıcıya bağla
        logging.info("🔗 Selenium mevcut tarayıcıya bağlanıyor...")
        driver = webdriver.Chrome(options=chrome_options)

        # --- KAPSAMLI ANTI-DETECTION + GOOGLE TRANSLATE GİZLEME ---
        # Cloudflare Turnstile headless tespitine karşı kritik maskeler uygulanıyor.
        # Headless Chrome'un bıraktığı izler: navigator.webdriver, eksik plugins,
        # permissions farklılığı, chrome objesi eksikliği, User-Agent'taki "HeadlessChrome".
        try:
            # Önce User-Agent'ı güncelle: "HeadlessChrome" ifadesini gerçek Chrome UA'ya çevir
            current_ua = driver.execute_script("return navigator.userAgent;")
            clean_ua = current_ua.replace("HeadlessChrome", "Chrome")
            driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": clean_ua,
                "acceptLanguage": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "platform": "Win32"
            })
            logging.info(f"🔧 User-Agent güncellendi: {clean_ua[:80]}...")
        except Exception as ua_e:
            logging.debug(f"User-Agent override hatası: {ua_e}")

        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    // 1. navigator.webdriver'ı kaldır
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

                    // 2. navigator.plugins — headless'ta boş gelir, gerçek liste simüle et
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => {
                            const arr = [1, 2, 3, 4, 5];
                            arr.__proto__ = PluginArray.prototype;
                            return arr;
                        }
                    });

                    // 3. navigator.languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['tr-TR', 'tr', 'en-US', 'en']
                    });

                    // 4. Notification.permission — headless'ta 'denied' gelir
                    const origPermissions = navigator.permissions.query.bind(navigator.permissions);
                    navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications'
                            ? Promise.resolve({ state: Notification.permission })
                            : origPermissions(parameters)
                    );

                    // 5. chrome nesnesi — headless'ta eksik gelir
                    if (!window.chrome) {
                        window.chrome = { runtime: {} };
                    }

                    // 6. Google Translate barını gizle
                    var style = document.createElement('style');
                    style.textContent = '.goog-te-banner-frame, #goog-gt-tt, .goog-te-balloon-frame, .skiptranslate { display: none !important; } body { top: 0 !important; }';
                    document.head.appendChild(style);
                """
            })
            logging.info("🛡️ Anti-detection CDP scripti enjekte edildi.")
        except Exception as cdp_e:
            logging.warning(f"⚠️ Anti-detection CDP script hatası: {cdp_e}")
        # -----------------------------------------------------------
        
        logging.info("✅ Selenium başarıyla bağlandı!")
        logging.info("="*60)
        
        return driver
        
    except Exception as e:
        logging.error(f"❌ Tarayıcı başlatma hatası: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise e

# -----------------------------
# Kayıt İşlemleri
# -----------------------------
def register_pixverse(driver, username, email):
    """Kayıt işlemini gerçekleştirir (Güncellenmiş 2xTab+Space Mantığı ile)"""
    check_pause()
    
    try:
        logging.info(f"{'='*60}")
        logging.info(f"🌐 KAYIT SAYFASI AÇILIYOR")
        logging.info(f"{'='*60}")
        
        # Sayfayı aç
        driver.get("https://app.pixverse.ai/register")
        logging.info("⏳ Sayfa yüklenmesi için 15 saniye bekleniyor...")
        time.sleep(15)
        
        check_pause()
        
        # Kullanıcı adı alanını bul ve doldur
        logging.info(f"🔍 Kullanıcı adı giriliyor: {username}")
        username_selectors = [
            # HTML'e özel aria-required selector (en güvenilir)
            (By.CSS_SELECTOR, "input[aria-required='true'][placeholder='Kullanıcı adı'][type='text']"),
            # Class-based selector
            (By.CSS_SELECTOR, "input.flex-1.w-full.bg-transparent[placeholder='Kullanıcı adı']"),
            # Genel selectors (yedek)
            (By.CSS_SELECTOR, "input[placeholder='Kullanıcı adı']"),
            (By.XPATH, "//input[@placeholder='Kullanıcı adı' and @aria-required='true']"),
            (By.XPATH, "//input[@placeholder='Kullanıcı adı']")
        ]
        
        username_filled = False
        for idx, (by, selector) in enumerate(username_selectors, 1):
            try:
                logging.debug(f"🔍 Kullanıcı adı alanı deneniyor (selector #{idx})...")
                username_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                
                # Elemente scroll ve görünür olmasını bekle
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", username_field)
                time.sleep(0.5)
                
                # Tıklayarak focus al
                username_field.click()
                time.sleep(0.5)
                
                # CTRL+A ile tümünü seç ve temizle
                username_field.send_keys(Keys.CONTROL + "a")
                time.sleep(0.2)
                username_field.send_keys(Keys.DELETE)
                time.sleep(0.3)
                
                # send_keys ile karakter karakter yaz
                logging.debug(f"⌨️ Kullanıcı adı karakter karakter yazılıyor: {username}")
                for char in username:
                    username_field.send_keys(char)
                    time.sleep(0.05)
                
                time.sleep(0.5)
                
                # Değeri kontrol et (3 deneme)
                written_value = ""
                for attempt in range(3):
                    written_value = username_field.get_attribute("value")
                    if written_value == username:
                        logging.info(f"✅ Kullanıcı adı başarıyla yazıldı ve doğrulandı: {username}")
                        username_filled = True
                        break
                    else:
                        logging.debug(f"🔄 Doğrulama denemesi {attempt + 1}/3 - Beklenen: {username}, Yazılan: '{written_value}'")
                        time.sleep(0.3)
                
                if username_filled:
                    break
                else:
                    logging.warning(f"⚠️ Kullanıcı adı doğrulanamadı (selector #{idx}). Beklenen: {username}, Yazılan: '{written_value}'")
                    continue
                    
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not username_filled:
            logging.error("❌ Kullanıcı adı alanı bulunamadı veya doldurulamadı!")
            return False
        
        check_pause()
        
        # E-posta alanını bul ve doldur
        logging.info(f"📧 E-posta giriliyor: {email}")
        email_selectors = [
            # HTML'e özel aria-required selector (en güvenilir)
            (By.CSS_SELECTOR, "input[aria-required='true'][placeholder='E-posta'][type='text']"),
            # Class-based selector
            (By.CSS_SELECTOR, "input.flex-1.w-full.bg-transparent[placeholder='E-posta']"),
            # Genel selectors (yedek)
            (By.CSS_SELECTOR, "input[placeholder='E-posta']"),
            (By.XPATH, "//input[@placeholder='E-posta' and @aria-required='true']"),
            (By.XPATH, "//input[@placeholder='E-posta']")
        ]
        
        email_filled = False
        for idx, (by, selector) in enumerate(email_selectors, 1):
            try:
                logging.debug(f"🔍 E-posta alanı deneniyor (selector #{idx})...")
                email_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                
                # Elemente scroll ve görünür olmasını bekle
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", email_field)
                time.sleep(0.5)
                
                # Tıklayarak focus al
                email_field.click()
                time.sleep(0.5)
                
                # CTRL+A ile tümünü seç ve temizle
                email_field.send_keys(Keys.CONTROL + "a")
                time.sleep(0.2)
                email_field.send_keys(Keys.DELETE)
                time.sleep(0.3)
                
                # send_keys ile karakter karakter yaz
                logging.debug(f"⌨️ E-posta karakter karakter yazılıyor: {email}")
                for char in email:
                    email_field.send_keys(char)
                    time.sleep(0.05)
                
                time.sleep(0.5)
                
                # Değeri kontrol et (3 deneme)
                written_value = ""
                for attempt in range(3):
                    written_value = email_field.get_attribute("value")
                    if written_value == email:
                        logging.info(f"✅ E-posta başarıyla yazıldı ve doğrulandı: {email}")
                        email_filled = True
                        break
                    else:
                        logging.debug(f"🔄 Doğrulama denemesi {attempt + 1}/3 - Beklenen: {email}, Yazılan: '{written_value}'")
                        time.sleep(0.3)
                
                if email_filled:
                    break
                else:
                    logging.warning(f"⚠️ E-posta doğrulanamadı (selector #{idx}). Beklenen: {email}, Yazılan: '{written_value}'")
                    continue
                    
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not email_filled:
            logging.error("❌ E-posta alanı bulunamadı veya doldurulamadı!")
            return False
        
        check_pause()
        
        # Şifre alanını bul ve doldur
        logging.info(f"🔒 Şifre giriliyor...")
        password_selectors = [
            # HTML'e özel aria-required selector (en güvenilir)
            (By.CSS_SELECTOR, "input[aria-required='true'][placeholder='Şifre'][type='password']"),
            # Class-based selector
            (By.CSS_SELECTOR, "input.flex-1.w-full.bg-transparent[placeholder='Şifre'][type='password']"),
            # Genel selectors (yedek)
            (By.CSS_SELECTOR, "input[placeholder='Şifre'][type='password']"),
            (By.XPATH, "//input[@placeholder='Şifre' and @type='password' and @aria-required='true']"),
            (By.XPATH, "//input[@placeholder='Şifre' and @type='password']")
        ]
        
        password_filled = False
        for idx, (by, selector) in enumerate(password_selectors, 1):
            try:
                logging.debug(f"🔍 Şifre alanı deneniyor (selector #{idx})...")
                password_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                
                # Elemente scroll ve görünür olmasını bekle
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", password_field)
                time.sleep(0.5)
                
                # Tıklayarak focus al
                password_field.click()
                time.sleep(0.5)
                
                # CTRL+A ile tümünü seç ve temizle
                password_field.send_keys(Keys.CONTROL + "a")
                time.sleep(0.2)
                password_field.send_keys(Keys.DELETE)
                time.sleep(0.3)
                
                # send_keys ile karakter karakter yaz
                logging.debug(f"⌨️ Şifre karakter karakter yazılıyor ({len(PASSWORD)} karakter)")
                for char in PASSWORD:
                    password_field.send_keys(char)
                    time.sleep(0.05)
                
                time.sleep(0.5)
                
                # Değeri kontrol et (3 deneme - şifre alanında uzunluk kontrolü)
                written_value = ""
                for attempt in range(3):
                    written_value = password_field.get_attribute("value")
                    if len(written_value) == len(PASSWORD):
                        logging.info(f"✅ Şifre başarıyla yazıldı ve doğrulandı ({len(PASSWORD)} karakter)")
                        password_filled = True
                        break
                    else:
                        logging.debug(f"🔄 Doğrulama denemesi {attempt + 1}/3 - Beklenen uzunluk: {len(PASSWORD)}, Yazılan: {len(written_value)}")
                        time.sleep(0.3)
                
                if password_filled:
                    break
                else:
                    logging.warning(f"⚠️ Şifre uzunluğu doğrulanamadı (selector #{idx}). Beklenen: {len(PASSWORD)}, Yazılan: {len(written_value)}")
                    continue
                    
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not password_filled:
            logging.error("❌ Şifre alanı bulunamadı veya doldurulamadı!")
            return False
        
        check_pause()
        
        # Şifre onay alanını bul ve doldur (SAF SEND_KEYS YÖNTEMİ)
        logging.info("🔒 Şifre onay giriliyor (send_keys yöntemi ile)...")
        confirm_selectors = [
            # HTML'e özel aria-required selector (en güvenilir)
            (By.CSS_SELECTOR, "input[aria-required='true'][placeholder='Şifreyi onayla'][type='password']"),
            # Class-based selector
            (By.CSS_SELECTOR, "input.flex-1.w-full.bg-transparent[placeholder='Şifreyi onayla'][type='password']"),
            # Genel selectors (yedek)
            (By.CSS_SELECTOR, "input[placeholder='Şifreyi onayla']"),
            (By.XPATH, "//input[@placeholder='Şifreyi onayla' and @type='password' and @aria-required='true']"),
            (By.XPATH, "//input[@placeholder='Şifreyi onayla']")
        ]
        
        confirm_filled = False
        for idx, (by, selector) in enumerate(confirm_selectors, 1):
            try:
                logging.debug(f"🔍 Şifre onay alanı deneniyor (selector #{idx})...")
                confirm_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                
                # Elemente scroll ve görünür olmasını bekle
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", confirm_field)
                time.sleep(0.5)
                
                # Tıklayarak focus al
                confirm_field.click()
                time.sleep(0.5)
                
                # CTRL+A ile tümünü seç ve temizle
                confirm_field.send_keys(Keys.CONTROL + "a")
                time.sleep(0.2)
                confirm_field.send_keys(Keys.DELETE)
                time.sleep(0.3)
                
                # send_keys ile karakter karakter yaz
                logging.debug(f"⌨️ Şifre onay karakter karakter yazılıyor ({len(PASSWORD)} karakter)")
                for char in PASSWORD:
                    confirm_field.send_keys(char)
                    time.sleep(0.05)
                
                time.sleep(0.5)
                
                # Değeri kontrol et (3 deneme - şifre alanında uzunluk kontrolü)
                written_value = ""
                for attempt in range(3):
                    written_value = confirm_field.get_attribute("value")
                    if len(written_value) == len(PASSWORD):
                        logging.info(f"✅ Şifre onay başarıyla yazıldı ve doğrulandı ({len(PASSWORD)} karakter)")
                        confirm_filled = True
                        break
                    else:
                        logging.debug(f"🔄 Doğrulama denemesi {attempt + 1}/3 - Beklenen uzunluk: {len(PASSWORD)}, Yazılan: {len(written_value)}")
                        time.sleep(0.3)
                
                if confirm_filled:
                    break
                else:
                    logging.warning(f"⚠️ Şifre onay uzunluğu doğrulanamadı (selector #{idx}). Beklenen: {len(PASSWORD)}, Yazılan: {len(written_value)}")
                    continue
                    
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not confirm_filled:
            logging.error("❌ Şifre onay alanı bulunamadı veya doldurulamadı!")
            return False
        
        check_pause()
        time.sleep(1)

        # ----------------------------------------------------------------------
        # ÖZEL CLOUDFLARE VE TAB+TAB+SPACE MANTIĞI
        # ----------------------------------------------------------------------
        logging.info("☁️ Cloudflare durumu ve özel 2xTAB+SPACE mantığı kontrol ediliyor...")
        
        # 1. KONTROL: Formu doldurduktan sonra hemen kontrol et
        status, _ = check_cloudflare_turnstile(driver)
        
        # Eğer ONAYLI DEĞİLSE -> 1. Deneme
        if status != "SUCCESS":
            logging.info("⚠️ Cloudflare henüz onaylanmamış. Yöntem 1 uygulanıyor: 2xTAB + SPACE")
            
            # ActionChains ile 2 kere Tab, 1 kere Space
            try:
                actions = ActionChains(driver)
                actions.send_keys(Keys.TAB).send_keys(Keys.TAB).send_keys(Keys.SPACE).perform()
                logging.info("⌨️  Tuş kombinasyonu gönderildi: TAB -> TAB -> SPACE")
            except Exception as e:
                logging.error(f"⚠️ Tuş gönderme hatası: {e}")
            
            logging.info("⏳ 20 saniye bekleniyor...")
            time.sleep(20)
            
            # 2. KONTROL: 20 saniye bekledikten sonra kontrol et
            status, _ = check_cloudflare_turnstile(driver)
            
            # Eğer HALA ONAYLI DEĞİLSE -> 2. Deneme (Input'a tıkla + Kombinasyon)
            if status != "SUCCESS":
                logging.info("⚠️ Cloudflare hala onaylanmadı. Yöntem 2 (2. Deneme) uygulanıyor...")
                logging.info("🖱️ 'Şifreyi onayla' kutusuna tıklanıyor...")
                
                try:
                    # Şifreyi onayla kutusuna tekrar tıkla (Elementi tekrar bulalım stale olmasın)
                    confirm_field_retry = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Şifreyi onayla']")
                    confirm_field_retry.click()
                    time.sleep(1)
                    
                    # Tekrar 2xTab + Space
                    logging.info("⌨️  Tuş kombinasyonu tekrar gönderiliyor: TAB -> TAB -> SPACE")
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.TAB).send_keys(Keys.TAB).send_keys(Keys.SPACE).perform()
                    
                    logging.info("⏳ 20 saniye daha bekleniyor...")
                    time.sleep(20)
                    
                    # 3. KONTROL: Son kez kontrol et
                    status, _ = check_cloudflare_turnstile(driver)
                    
                    # Eğer HALA ONAYLI DEĞİLSE -> Ekran görüntüsü al, kapat ve yeniden başlat
                    if status != "SUCCESS":
                        logging.error("❌ Cloudflare 2. denemeden sonra da onaylanmadı! İşlem iptal ediliyor.")
                        # Ekran görüntüsü al
                        return False # Bu False, main_flow'da tarayıcının kapatılıp döngünün baştan başlamasını sağlar
                        
                except Exception as e:
                    logging.error(f"❌ 2. Deneme sırasında hata oluştu: {e}")
                    # Ekran görüntüsü al
                    return False

        logging.info("✅ Cloudflare onaylı (veya onaylandı). Devam ediliyor...")
        # ----------------------------------------------------------------------

        # "Devam et" butonunu bul ve tıkla
        logging.info("🔍 Devam et butonu aranıyor...")
        continue_selectors = [
            (By.XPATH, "//button[contains(., 'Devam et')]"),
            (By.CSS_SELECTOR, "button.bg-button-primary-normal"),
            (By.XPATH, "//button[@type='button' and contains(@class, 'bg-button-primary-normal')]"),
            (By.XPATH, "//div[text()='Devam et']/ancestor::button")
        ]
        
        continue_clicked = False
        for idx, (by, selector) in enumerate(continue_selectors, 1):
            try:
                logging.debug(f"🔍 Devam et butonu aranıyor (selector #{idx})...")
                continue_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", continue_button)
                time.sleep(0.5)
                
                # Buton aktiflik kontrolü
                logging.debug("🔍 Buton aktiflik durumu kontrol ediliyor...")
                if not is_button_enabled(driver, continue_button):
                    logging.warning(f"⚠️ Devam et butonu aktif değil")
                    logging.warning("⚠️ CAPTCHA onaylanmamış olabilir veya form eksik!")
                    return False
                
                # Buton aktifse tıkla
                logging.info("✅ Buton aktif, tıklanıyor...")
                continue_button.click()
                logging.info(f"✅ Devam et butonu tıklandı")
                continue_clicked = True
                break
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not continue_clicked:
            logging.error("❌ Devam et butonu bulunamadı veya tıklanamadı!")
            return False
        
        # Başarılı
        logging.info("✅ Kayıt formu gönderildi!")
        logging.info("⏳ Sayfanın yüklenmesi bekleniyor...")
        time.sleep(5)
        
        # Doğrulama sayfasına geçiş kontrolü
        logging.debug("🔍 Doğrulama sayfası kontrol ediliyor...")
        try:
            verification_page = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Doğrulama kodu']"))
            )
            logging.info("✅ Doğrulama sayfasına başarıyla geçildi!")
            return True
        except TimeoutException:
            logging.error("❌ Doğrulama sayfasına geçilemedi! (Kullanıcı adı kullanımda olabilir veya başka hata)")
            return False
        
    except Exception as e:
        logging.error(f"❌ Kayıt işlemi hatası: {e}")
        import traceback
        logging.debug(traceback.format_exc())
        return False

def enter_verification_code(driver, code, username):
    """Doğrulama kodunu girer, Tab+Space ile Cloudflare'i tıklar ve onayını bekler"""
    check_pause()
    
    logging.info(f"{'='*60}")
    logging.info(f"🔐 DOĞRULAMA KODU GİRİŞİ")
    logging.info(f"{'='*60}")
    
    try:
        # ADIM 1: Doğrulama kodunu bul ve gir
        logging.info(f"🔍 Doğrulama kodu giriliyor: {code}")
        code_input_selectors = [
            (By.CSS_SELECTOR, "input[placeholder='Doğrulama kodu']"),
            (By.XPATH, "//input[@placeholder='Doğrulama kodu']"),
            (By.CSS_SELECTOR, "input[type='text'][placeholder='Doğrulama kodu']")
        ]
        
        code_input = None
        code_filled = False
        for idx, (by, selector) in enumerate(code_input_selectors, 1):
            try:
                logging.debug(f"🔍 Doğrulama kodu alanı aranıyor (selector #{idx})...")
                code_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", code_input)
                time.sleep(0.5)
                
                code_input.clear()
                code_input.send_keys(code)
                
                logging.info(f"✅ Doğrulama kodu girildi: {code}")
                code_filled = True
                break
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not code_filled:
            logging.error("❌ Doğrulama kodu alanı bulunamadı!")
            return False
        
        check_pause()
        
        # ADIM 2: Cloudflare kontrolü ve Tab+Space ile tıklama (3 deneme)
        logging.info("☁️ Kod girildi, şimdi Cloudflare onayı kontrol ediliyor...")
        time.sleep(1)
        
        max_attempts = 3
        cloudflare_passed = False
        
        for attempt in range(1, max_attempts + 1):
            logging.info(f"{'='*60}")
            logging.info(f"☁️ CLOUDFLARE KONTROL - DENEME {attempt}/{max_attempts}")
            logging.info(f"{'='*60}")
            
            # Cloudflare durumunu kontrol et
            status, token = check_cloudflare_turnstile(driver)
            
            if status == "SUCCESS":
                logging.info("✅ Cloudflare zaten onaylı! Devam ediliyor...")
                cloudflare_passed = True
                break
            
            # Onaylı değilse Tab + Space yap
            logging.info(f"⚠️ Cloudflare henüz onaylanmamış. Tab + Space işlemi yapılıyor...")
            
            try:
                # Doğrulama kodu alanına tıkla (focus al)
                if code_input:
                    code_input.click()
                    time.sleep(0.5)
                
                # Tab + Space
                actions = ActionChains(driver)
                actions.send_keys(Keys.TAB).send_keys(Keys.SPACE).perform()
                logging.info("⌨️ Tuş kombinasyonu gönderildi: TAB -> SPACE")
            except Exception as e:
                logging.error(f"⚠️ Tuş gönderme hatası: {e}")
            
            # 20 saniye bekle
            logging.info("⏳ 20 saniye bekleniyor...")
            time.sleep(20)
            
            # Tekrar kontrol et
            status, token = check_cloudflare_turnstile(driver)
            
            if status == "SUCCESS":
                logging.info("✅ Cloudflare onaylandı!")
                cloudflare_passed = True
                break
            else:
                if attempt < max_attempts:
                    logging.warning(f"⚠️ Cloudflare hala onaylanmadı. {attempt + 1}. denemeye geçiliyor...")
                else:
                    logging.error("❌ Cloudflare 3 denemede de onaylanamadı!")
        
        if not cloudflare_passed:
            logging.error("❌ Cloudflare onayı alınamadı! İşlem iptal ediliyor.")
            return False
        
        logging.info("✅ Cloudflare onayı alındı, butona basılıyor...")
        
        # ADIM 3: "Devam et" butonunu tıkla
        logging.info("🔍 Devam et butonu aranıyor...")
        continue_selectors = [
            (By.XPATH, "//button[contains(., 'Devam et')]"),
            (By.CSS_SELECTOR, "button.bg-button-primary-normal"),
            (By.XPATH, "//div[text()='Devam et']/ancestor::button")
        ]
        
        continue_clicked = False
        for idx, (by, selector) in enumerate(continue_selectors, 1):
            try:
                logging.debug(f"🔍 Devam et butonu aranıyor (selector #{idx})...")
                continue_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", continue_button)
                time.sleep(0.5)

                # Cloudflare geçildiği için butonun aktif olmasını bekleyelim
                if not is_button_enabled(driver, continue_button):
                    logging.warning("⚠️ Buton hala pasif görünüyor, 2 saniye daha bekleniyor...")
                    time.sleep(2)
                
                continue_button.click()
                logging.info("✅ Devam et butonu tıklandı")
                continue_clicked = True
                break
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not continue_clicked:
            logging.error("❌ Devam et butonu bulunamadı!")
            return False
        
        logging.info("⏳ Sayfa geçişi bekleniyor...")
        time.sleep(5)
        
        # --- POPUP / EK PENCERE KAPATMA KONTROLLERİ ---
        logging.info("🔍 Popup kontrol ediliyor...")
        try:
            # İlk popup kontrolü (mevcut mantık)
            popup_kapat_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@role="dialog"]//button[contains(@class, "absolute") and contains(@class, "right-4")]'))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", popup_kapat_btn)
            time.sleep(0.3)
            try:
                popup_kapat_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", popup_kapat_btn)
            logging.info("✅ İlk popup bulundu ve kapatıldı.")
            time.sleep(2)
        except Exception:
            logging.info("ℹ️ İlk popup çıkmadı veya zaten kapalı, devam ediliyor.")

        logging.info("🔍 Ek pencere kontrolü yapılıyor (Ad Master)...")
        try:
            # Kullanıcının paylaştığı pencere HTML'ine göre X butonu kontrolü
            # "Ad Master" veya "C1" gibi farklı içerikli popup'ları da yakalar
            # data-state="open" olan herhangi bir dialog'daki absolute-right-6-top-6 butonunu hedefler
            extra_window_close_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[@role='dialog' and @data-state='open']//button[@type='button' and contains(@class, 'group/button') and contains(@class, 'absolute') and contains(@class, 'right-6') and contains(@class, 'top-6')]"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", extra_window_close_btn)
            time.sleep(0.3)
            try:
                extra_window_close_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", extra_window_close_btn)
            logging.info("✅ Ek pencere (Ad Master / C1 vb.) bulundu ve kapatıldı.")
            time.sleep(2)
        except Exception:
            logging.info("ℹ️ Ek pencere açık değil, devam ediliyor.")
        # -----------------------------------------------
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Doğrulama işlemi hatası: {e}")
        import traceback
        logging.debug(traceback.format_exc())
        return False

def complete_invite_process(driver):
    """Davet kodu sürecini tamamlar"""
    check_pause()
    
    logging.info(f"{'='*60}")
    logging.info(f"🎁 DAVET KODU SÜRECİ")
    logging.info(f"{'='*60}")
    
    try:
        # "Kredi Kazan" butonunu tıkla
        logging.info("🔍 Kredi Kazan butonu aranıyor...")
        credit_selectors = [
            (By.XPATH, "//span[contains(text(), 'Kredi Kazan')]"),
            (By.XPATH, "//div[contains(text(), 'Kredi Kazan')]"),
            (By.XPATH, "//button[contains(., 'Kredi Kazan')]")
        ]
        
        credit_clicked = False
        for idx, (by, selector) in enumerate(credit_selectors, 1):
            try:
                logging.debug(f"🔍 Kredi Kazan butonu aranıyor (selector #{idx})...")
                credit_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", credit_button)
                time.sleep(0.5)
                credit_button.click()
                logging.info("✅ Kredi Kazan butonu tıklandı")
                credit_clicked = True
                break
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not credit_clicked:
            logging.error("❌ Kredi Kazan butonu bulunamadı!")
            return False
        
        time.sleep(2)
        check_pause()
        
        # Sayfayı kaydır
        logging.info("📜 Sayfa kaydırılıyor...")
        driver.execute_script("window.scrollBy(0, 300);")
        time.sleep(1)
        check_pause()
        
        # "Başla" butonunu bul ve tıkla
        logging.info("🔍 Başla butonu aranıyor...")
        start_clicked = False
        
        try:
            logging.debug("🔍 Arkadaşlardan Ödüller bölümü aranıyor...")
            friend_rewards_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Arkadaşlardan Ödüller')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", friend_rewards_element)
            time.sleep(0.5)
            logging.info("✅ Arkadaşlardan Ödüller bölümü bulundu")
            
            logging.debug("🔍 Başla butonu aranıyor...")
            start_button = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//span[contains(text(), 'Arkadaşlardan Ödüller')]/ancestor::div[contains(@class, 'h-[72px]')]//button[contains(@class, 'bg-button-primary-normal')]"
                ))
            )
            
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", start_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", start_button)
            
            logging.info("✅ Başla butonu tıklandı")
            start_clicked = True
            
        except Exception as e:
            logging.warning(f"⚠️ Başla butonu bulma hatası: {e}")
        
        if not start_clicked:
            logging.error("❌ Başla butonu bulunamadı!")
            return False
        
        time.sleep(2)
        check_pause()
        
        # Davet kodunu gir
        logging.info(f"🔍 Davet kodu giriliyor: {INVITE_CODE}")
        invite_code_selectors = [
            (By.CSS_SELECTOR, "input[placeholder='Davet Kodu']"),
            (By.XPATH, "//input[@placeholder='Davet Kodu']"),
            (By.CSS_SELECTOR, "input[type='text'][placeholder='Davet Kodu']")
        ]
        
        invite_code_filled = False
        for idx, (by, selector) in enumerate(invite_code_selectors, 1):
            try:
                logging.debug(f"🔍 Davet kodu alanı aranıyor (selector #{idx})...")
                invite_code_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", invite_code_input)
                time.sleep(0.5)
                
                invite_code_input.clear()
                invite_code_input.send_keys(INVITE_CODE)
                
                logging.info(f"✅ Davet kodu yazıldı: {INVITE_CODE}")
                invite_code_filled = True
                break
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not invite_code_filled:
            logging.error("❌ Davet kodu alanı bulunamadı!")
            return False
        
        check_pause()
        
        # "Onayla" butonunu tıkla
        logging.info("🔍 Onayla butonu aranıyor...")
        confirm_selectors = [
            (By.XPATH, "//div[text()='Onayla']/ancestor::button"),
            (By.XPATH, "//button[contains(., 'Onayla')]"),
            (By.CSS_SELECTOR, "button.bg-button-primary-normal")
        ]
        
        confirm_clicked = False
        for idx, (by, selector) in enumerate(confirm_selectors, 1):
            try:
                logging.debug(f"🔍 Onayla butonu aranıyor (selector #{idx})...")
                confirm_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", confirm_button)
                time.sleep(0.5)
                confirm_button.click()
                logging.info("✅ Onayla butonu tıklandı")
                confirm_clicked = True
                break
            except Exception as e:
                logging.debug(f"⚠️ Selector #{idx} başarısız: {e}")
                continue
        
        if not confirm_clicked:
            logging.error("❌ Onayla butonu bulunamadı!")
            return False
        
        logging.info("⏳ Onay işlemi bekleniyor...")
        time.sleep(2)
        
        # --- EKLENEN KISIM: "TAMAM" BUTONUNA TIKLAMA ---
        logging.info("🔍 Kredi kazanıldı popup'ı ('Tamam') bekleniyor...")
        try:
            tamam_selectors = [
                (By.XPATH, "//div[text()='Tamam']/ancestor::button"),
                (By.XPATH, "//button[contains(., 'Tamam')]"),
                (By.XPATH, "//div[contains(text(), 'Kredi Kazanıldı')]/following::button[contains(., 'Tamam')]")
            ]
            
            tamam_clicked = False
            for by, selector in tamam_selectors:
                try:
                    tamam_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    driver.execute_script("arguments[0].click();", tamam_button)
                    logging.info("✅ 'Tamam' butonu tıklandı, popup kapatıldı.")
                    tamam_clicked = True
                    break
                except:
                    continue
            
            if not tamam_clicked:
                logging.warning("⚠️ 'Tamam' butonu çıkmadı veya bulunamadı (önemli olmayabilir).")
                
        except Exception as e:
            logging.warning(f"⚠️ Popup kapatma sırasında hata: {e}")
        # ----------------------------------------------------
        
        time.sleep(3)
        logging.info("✅ Davet kodu süreci tamamlandı!")
        return True
        
    except Exception as e:
        logging.error(f"❌ Davet kodu süreci hatası: {e}")
        import traceback
        logging.debug(traceback.format_exc())
        return False

# -----------------------------
# Ana Akış
# -----------------------------
MAX_ISLEM = 60  # Maksimum işlem sayısı

def main_flow():
    """Ana bot akışı"""
    init_logger()
    
    # name.txt boşsa veya yoksa 120 rastgele kullanıcı adı üret
    ensure_names_exist()
    
    logging.info("🚀 BOT BAŞLATILDI")
    logging.info(f"{'='*60}")
    logging.info(f"📊 Maksimum işlem sayısı: {MAX_ISLEM}")
    
    driver = None
    loop_count = 0
    
    try:
        while loop_count < MAX_ISLEM:
            check_pause()
            
            loop_count += 1
            logging.info(f"\n{'='*60}")
            logging.info(f"🔄 DÖNGÜ #{loop_count} BAŞLIYOR")
            logging.info(f"{'='*60}\n")
            
            # --- YENİ EKLENEN: Her döngüde temiz başlangıç ---
            logging.info("🧼 Temiz başlangıç yapılıyor...")
            force_close_browser(driver)  # Varsa eski tarayıcıyı zorla kapat
            driver = None
            clean_profile_data()         # Profil dosyasını sil
            # -------------------------------------------------
            
            # Kullanıcı adını al
            logging.info("📋 Kullanıcı adı alınıyor...")
            username = get_next_username()
            if not username:
                logging.error("❌ Kullanıcı adı alınamadı! name.txt dosyası boş olabilir.")
                break
            
            logging.info(f"👤 İşlenecek kullanıcı adı: {username}")
            
            # Geçici mail oluştur
            logging.info("\n--- GEÇİCİ MAİL OLUŞTURMA ---")
            temp_email, inbox_id, _ = create_temp_email()
            if not temp_email:
                logging.error("❌ Geçici mail oluşturulamadı!")
                save_failed_username(username, "Temp mail oluşturulamadı")
                remove_username_from_file(username)
                continue
            
            logging.info(f"📧 Kullanılacak mail: {temp_email}\n")
            
            # Driver'ı başlat (Profil silindiği için temiz açılacak)
            logging.info("--- TARAYICI BAŞLATMA ---")
            try:
                driver = init_driver()
            except Exception as e:
                logging.error("❌ Tarayıcı başlatılamadı, döngü atlanıyor.")
                force_close_browser(None)  # Yarım açılan Chrome'u kapat
                driver = None
                continue
            
            check_pause()
            
            # Kayıt ol
            logging.info("\n--- KAYIT ---")
            if not register_pixverse(driver, username, temp_email):
                logging.error(f"❌ '{username}' için kayıt başarısız! (İsim kullanılıyor, Cloudflare hatası veya Tab+Space başarısız)")
                save_failed_username(username, "Kayıt başarısız/İsim dolu/Cloudflare")
                remove_username_from_file(username)
                force_close_browser(driver)
                driver = None
                continue
            
            check_pause()
            
            # Doğrulama mailini bekle ve kodu al
            logging.info("\n--- DOĞRULAMA MAİLİ BEKLEME ---")
            verification_code = wait_for_verification_email(inbox_id)
            if not verification_code:
                logging.error(f"❌ '{username}' için doğrulama kodu alınamadı!")
                save_failed_username(username, "Doğrulama kodu gelmedi")
                remove_username_from_file(username)
                force_close_browser(driver)
                driver = None
                continue
            
            check_pause()
            
            # Doğrulama kodunu gir
            logging.info("\n--- DOĞRULAMA KODU GİRİŞİ ---")
            if not enter_verification_code(driver, verification_code, username):
                logging.error(f"❌ '{username}' için doğrulama kodu girilemedi veya Cloudflare geçilemedi!")
                save_failed_username(username, "Doğrulama/Cloudflare hatası")
                remove_username_from_file(username)
                force_close_browser(driver)
                driver = None
                continue
            
            check_pause()
            
            # Davet kodu sürecini tamamla
            logging.info("\n--- DAVET KODU İŞLEMLERİ ---")
            if not complete_invite_process(driver):
                logging.error(f"❌ '{username}' için davet kodu süreci başarısız!")
                save_failed_username(username, "Davet kodu süreci başarısız")
                remove_username_from_file(username)
                force_close_browser(driver)
                driver = None
                continue
            
            # Başarılı - kullanıcı adını kaydet ve sil
            logging.info(f"\n{'='*60}")
            logging.info(f"🎉🎉🎉 BAŞARILI! '{username}' tamamlandı! 🎉🎉🎉")
            logging.info(f"{'='*60}\n")
            save_used_username(username, temp_email)
            remove_username_from_file(username)
            
            # Döngü sonu temizlik (Tarayıcıyı kapat)
            force_close_browser(driver)
            driver = None
            
            # Kısa bekleme
            logging.info("⏳ Sonraki döngü için 3 saniye bekleniyor...\n")
            time.sleep(3)
            
        # 60 işlem tamamlandı
        logging.info(f"\n{'='*60}")
        logging.info(f"✅ {MAX_ISLEM} işlem tamamlandı! Bot durduruluyor.")
        logging.info(f"{'='*60}")
            
    except KeyboardInterrupt:
        logging.info("\n⛔ Bot kullanıcı tarafından durduruldu.")
    except Exception as e:
        logging.error(f"\n❌ Bot ana döngüsünde beklenmedik hata: {e}")
        import traceback
        logging.error(traceback.format_exc())
    finally:
        force_close_browser(driver)
        logging.info(f"\n📊 Toplam işlem sayısı: {loop_count}/{MAX_ISLEM}")

# -----------------------------
# Main
# -----------------------------
def main():
    """Ana başlangıç fonksiyonu"""
    print("="*60)
    print("🤖 KAYIT BOTU - CLOUDFLARE KONTROLLÜ")
    print("="*60)
    print("📋 Kontrol dosyaları:")
    print("  - pause.txt: 'pause' yazarak botu duraklat")
    print("  - pause.txt: 'resume' yazarak devam ettir")
    print("  - name.txt: İşlenecek kullanıcı adları")
    print("  - used_names.txt: Başarılı kayıtlar")
    print("  - failed_names.txt: Başarısız kayıtlar")
    print("="*60)
    print("☁️  Cloudflare Ayarları:")
    print(f"  - Timeout: {CLOUDFLARE_CHECK_TIMEOUT} saniye")
    print(f"  - Kontrol Aralığı: {CLOUDFLARE_CHECK_INTERVAL} saniye")
    print(f"  - Maksimum Deneme: 3")
    print("="*60)
    print()
    
    # İlk çalıştırmada pause durumunu temizle
    pause_file = runtime_path("pause.txt")
    if os.path.exists(pause_file):
        with open(pause_file, "w") as f:
            f.write("resume")
    
    main_flow()

if __name__ == "__main__":
    main()
