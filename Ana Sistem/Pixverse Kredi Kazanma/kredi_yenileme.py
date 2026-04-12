from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import time

# Dosya yolları
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
KAYIT_DOSYA = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Pixverse Kredi Kazanma\kayıt.txt"

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

def pixverse_giris():
    email, sifre = kayit_bilgilerini_oku()
    
    if not email or not sifre:
        print("Email veya şifre bulunamadı!")
        return None
    
    print(f"Email: {email}")
    print(f"Şifre: {'*' * len(sifre)}")
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = CHROME_PATH
    
    # --- HEADLESS TARAYICI AYARLARI ---
    # Tarayıcıyı görünmez (headless) modda başlatır.
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080")
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    
    # Şifre kaydetme özelliklerini devre dışı bırak
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service()
    service.log_path = "NUL"
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Anti-detection script
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'tr', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            """
        })
        
        print("Chrome HEADLESS (arkaplan) modda başlatıldı.")
        driver.get("https://app.pixverse.ai/login")
        
        wait = WebDriverWait(driver, 30)
        
        # Login işlemleri
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="E-posta veya Kullanıcı Adı"]'))).send_keys(email)
        time.sleep(1)
        driver.find_element(By.CSS_SELECTOR, 'input[type="password"][placeholder="Şifre"]').send_keys(sifre)
        time.sleep(1)
        
        giris_btn = driver.find_element(By.XPATH, '//button[.//div[text()="Giriş"]]')
        giris_btn.click()
        print("Giriş butonuna tıklandı...")
        
        # Ana sayfa yüklenmesini bekle
        print("Ana sayfa yüklenmesi bekleniyor (/home)...")
        try:
            WebDriverWait(driver, 60).until(EC.url_contains("/home"))
            print("Ana sayfa başarıyla yüklendi!")
            time.sleep(3)
        except Exception:
            print("ZAMAN AŞIMI: Sayfa yüklenemedi veya giriş yapılamadı.")
            driver.quit()
            return None
        
        # Popup kapatma
        try:
            popup_kapat_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@role="dialog"]//button[contains(@class, "absolute") and contains(@class, "right-4")]'))
            )
            popup_kapat_btn.click()
            print("Popup kapatıldı.")
            time.sleep(1)
        except:
            pass
            
        return driver
        
    except Exception as e:
        print(f"Başlatma hatası: {e}")
        if driver:
            driver.quit()
        return None

def kredi_topla_ve_kapat(driver):
    wait = WebDriverWait(driver, 20)
    
    print("\n--- Kredi Toplama İşlemi Başlıyor ---")
    
    try:
        # 1. Kredi Kazan Butonu
        print("'Kredi Kazan' butonu aranıyor...")
        kredi_kazan_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, 
            '//button[.//span[contains(text(), "Kredi Kazan")]]'
        )))
        driver.execute_script("arguments[0].click();", kredi_kazan_btn)
        print("Tıklandı: Kredi Kazan")
        time.sleep(3)
        
        # --- KONTROL: Arkadaş Davet Etme Engeli ---
        print("Buton durumu kontrol ediliyor...")
        try:
            davet_btn = WebDriverWait(driver, 4).until(
                EC.visibility_of_element_located((
                    By.XPATH, 
                    '//button[.//div[contains(text(), "Arkadaş davet et")]]'
                ))
            )
            if davet_btn:
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("UYARI: Yeterli Davet Yok - İşlem İptal")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                driver.quit()
                return 
        except:
            print("Engel yok, 'Ödül Talep Et' aşamasına geçiliyor.")
            pass

        # 2. Ödül Talep Et Butonu
        print("'Ödül Talep Et' butonu aranıyor...")
        odul_talep_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, 
            '//button[.//div[contains(text(), "Ödül Talep Et")]]'
        )))
        
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", odul_talep_btn)
        time.sleep(1)
        odul_talep_btn.click()
        print(f"Tıklandı: {odul_talep_btn.text}")
        
        print("Bekleniyor (4 saniye)...")
        time.sleep(4)
        
        # 3. Tamam Butonu
        print("'Tamam' butonu aranıyor...")
        tamam_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, 
            '//div[@role="dialog"]//button[.//div[text()="Tamam"]]'
        )))
        tamam_btn.click()
        print("Tıklandı: Tamam")
        time.sleep(2)
        
        # 4. Sayfayı Yenileme ve Son Kontrol
        print("Bakiye güncellemesi için sayfa yenileniyor...")
        driver.refresh()
        
        # Sayfanın tekrar yüklenmesini bekle
        WebDriverWait(driver, 30).until(EC.url_contains("/home"))
        time.sleep(5)
        
        print("Güncel bakiye okunuyor...")
        son_kredi_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.text-text-credit'))
        )
        son_kredi = son_kredi_element.text.strip()
        
        print("\n==============================")
        print(f"GÜNCEL KREDİ: {son_kredi}")
        print("==============================\n")
        
        print("İşlem başarıyla tamamlandı. Tarayıcı kapatılıyor.")
        driver.quit()
        
    except Exception as e:
        print(f"İşlem sırasında hata: {e}")
        driver.quit()

if __name__ == "__main__":
    active_driver = pixverse_giris()
    
    if active_driver:
        kredi_topla_ve_kapat(active_driver)
    else:
        print("Giriş başarısız olduğu için işlem sonlandırıldı.")