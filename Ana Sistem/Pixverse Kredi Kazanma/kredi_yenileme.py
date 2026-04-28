from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import sys
import time

# Dosya yollari
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
KAYIT_DOSYA = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Pixverse Kredi Kazanma\kayıt.txt"

KREDI_KAZAN_SELECTORS = [
    (By.XPATH, "//button[.//span[contains(normalize-space(), 'Earn Credits')]]"),
    (By.XPATH, "//button[.//div[contains(normalize-space(), 'Earn Credits')]]"),
    (By.XPATH, "//button[contains(normalize-space(), 'Earn Credits')]"),
    (By.XPATH, "//button[.//span[contains(normalize-space(), 'Kredi Kazan')]]"),
    (By.XPATH, "//button[.//div[contains(normalize-space(), 'Kredi Kazan')]]"),
    (By.XPATH, "//button[contains(normalize-space(), 'Kredi Kazan')]"),
]

ANA_SAYFA_GOSTERGELERI = KREDI_KAZAN_SELECTORS + [
    (By.XPATH, "//button[contains(normalize-space(), 'Home')]"),
    (By.XPATH, "//button[contains(normalize-space(), 'API Platform')]"),
    (By.XPATH, "//button[contains(normalize-space(), 'Personal')]"),
    (By.XPATH, "//button[contains(normalize-space(), 'Kişisel')]"),
]

DAVET_ENGELI_SELECTORS = [
    (By.XPATH, "//button[contains(., 'Arkadaş davet et')]"),
    (By.XPATH, "//button[contains(., 'Invite Friends')]"),
    (By.XPATH, "//button[contains(., 'Invite friends')]"),
]

ODUL_TALEP_SELECTORS = [
    (By.XPATH, "//button[contains(., 'Ödül Talep Et')]"),
    (By.XPATH, "//button[contains(., 'Claim Reward')]"),
    (By.XPATH, "//button[contains(., 'Get Reward')]"),
]

TAMAM_SELECTORS = [
    (By.XPATH, "//div[@role='dialog']//button[.//*[normalize-space()='Tamam']]"),
    (By.XPATH, "//div[@role='dialog']//button[.//*[normalize-space()='OK']]"),
    (By.XPATH, "//div[@role='dialog']//button[normalize-space()='Tamam']"),
    (By.XPATH, "//div[@role='dialog']//button[normalize-space()='OK']"),
]

KREDI_BAKIYE_SELECTORS = [
    (By.CSS_SELECTOR, "span.text-text-credit"),
    (By.XPATH, "//span[contains(@class, 'text-text-credit')]"),
]

POPUP_KAPAT_SELECTORS = [
    (By.XPATH, "//div[@role='dialog']//button[contains(@class, 'absolute') and contains(@class, 'right-4')]"),
    (By.XPATH, "//div[@role='dialog']//button[@aria-label='Close']"),
]


def kayit_bilgilerini_oku():
    try:
        with open(KAYIT_DOSYA, "r", encoding="utf-8") as f:
            satirlar = f.readlines()
            email = satirlar[0].strip() if len(satirlar) > 0 else ""
            sifre = satirlar[1].strip() if len(satirlar) > 1 else ""
            return email, sifre
    except Exception as e:
        print(f"Dosya okuma hatasi: {e}")
        return None, None


def ilk_uygun_elemani_bul(driver, selectors, timeout=20, clickable=True, aciklama="Eleman"):
    son_hata = None
    bitis = time.time() + timeout
    condition = EC.element_to_be_clickable if clickable else EC.presence_of_element_located

    while time.time() < bitis:
        for by, selector in selectors:
            kalan = max(1, min(3, int(bitis - time.time())))
            try:
                return WebDriverWait(driver, kalan).until(condition((by, selector)))
            except Exception as exc:
                son_hata = exc
        time.sleep(0.3)

    raise RuntimeError(f"{aciklama} bulunamadi veya hazir hale gelmedi.") from son_hata


def herhangi_biri_var_mi(driver, selectors, timeout=3, gorunur_olmali=True):
    bitis = time.time() + timeout

    while time.time() < bitis:
        for by, selector in selectors:
            try:
                elemanlar = driver.find_elements(by, selector)
                for eleman in elemanlar:
                    if not gorunur_olmali or eleman.is_displayed():
                        return True
            except Exception:
                pass
        time.sleep(0.25)

    return False


def popup_kapatmayi_dene(driver):
    for by, selector in POPUP_KAPAT_SELECTORS:
        try:
            popup_kapat_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((by, selector))
            )
            driver.execute_script("arguments[0].click();", popup_kapat_btn)
            print("Popup kapatildi.")
            time.sleep(1)
            return
        except Exception:
            continue


def pixverse_ana_sayfayi_bekle(driver, timeout=75):
    print("Ana sayfa yuklenmesi bekleniyor (/, /home, Earn Credits)...")
    son_url = ""
    bitis = time.time() + timeout

    while time.time() < bitis:
        try:
            current_url = driver.current_url
        except Exception:
            current_url = ""

        if current_url and current_url != son_url:
            print(f"Guncel URL: {current_url}")
            son_url = current_url

        app_icinde = "app.pixverse.ai" in current_url and "/login" not in current_url
        normalized_url = current_url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        kok_url = normalized_url == "https://app.pixverse.ai"
        home_url = "/home" in current_url

        if app_icinde and herhangi_biri_var_mi(driver, ANA_SAYFA_GOSTERGELERI, timeout=1):
            print("Ana sayfa dogrulandi: PixVerse uygulama arayuzu gorundu.")
            return True

        if app_icinde and (kok_url or home_url):
            try:
                ready_state = driver.execute_script("return document.readyState")
            except Exception:
                ready_state = ""
            if ready_state == "complete":
                print("Ana sayfa dogrulandi: URL ve dokuman hazir.")
                return True

        time.sleep(1)

    try:
        son_url = driver.current_url
    except Exception:
        pass
    print(f"ZAMAN ASIMI: Ana sayfa dogrulanamadi. Son URL: {son_url}")
    return False


def elemani_tikla(driver, element, etiket):
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
        element,
    )
    time.sleep(0.5)
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)
    print(f"Tiklandi: {etiket}")


def pixverse_giris():
    email, sifre = kayit_bilgilerini_oku()

    if not email or not sifre:
        print("Email veya sifre bulunamadi!")
        return None

    print(f"Email: {email}")
    print(f"Sifre: {'*' * len(sifre)}")

    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = CHROME_PATH

    # Tarayiciyi gorunmez (headless) modda baslatmak isterseniz satiri acin.
    # chrome_options.add_argument("--headless=new")
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

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service()
    service.log_path = "NUL"

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'tr', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            """
        })

        print("Chrome tarayicisi baslatildi.")
        driver.get("https://app.pixverse.ai/login")

        wait = WebDriverWait(driver, 30)

        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[placeholder="E-posta veya Kullanıcı Adı"]')
            )
        ).send_keys(email)
        time.sleep(1)
        driver.find_element(
            By.CSS_SELECTOR,
            'input[type="password"][placeholder="Şifre"]',
        ).send_keys(sifre)
        time.sleep(1)

        giris_btn = driver.find_element(By.XPATH, '//button[.//div[text()="Giriş"]]')
        giris_btn.click()
        print("Giris butonuna tiklandi...")

        if not pixverse_ana_sayfayi_bekle(driver):
            driver.quit()
            return None

        popup_kapatmayi_dene(driver)
        time.sleep(1)
        return driver

    except Exception as e:
        print(f"Baslatma hatasi: {e}")
        if driver:
            driver.quit()
        return None


def kredi_topla_ve_kapat(driver):
    print("\n--- Kredi Toplama Islemi Basliyor ---")

    try:
        print("'Kredi Kazan / Earn Credits' butonu araniyor...")
        kredi_kazan_btn = ilk_uygun_elemani_bul(
            driver,
            KREDI_KAZAN_SELECTORS,
            timeout=30,
            clickable=True,
            aciklama="Kredi Kazan butonu",
        )
        elemani_tikla(driver, kredi_kazan_btn, "Kredi Kazan / Earn Credits")
        time.sleep(3)

        print("Buton durumu kontrol ediliyor...")
        if herhangi_biri_var_mi(driver, DAVET_ENGELI_SELECTORS, timeout=4):
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("UYARI: Yeterli davet yok - islem iptal edildi")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            return False

        print("Engel yok, odul talep et asamasina geciliyor.")

        print("'Odul Talep Et / Claim Reward' butonu araniyor...")
        odul_talep_btn = ilk_uygun_elemani_bul(
            driver,
            ODUL_TALEP_SELECTORS,
            timeout=20,
            clickable=True,
            aciklama="Odul Talep Et butonu",
        )
        elemani_tikla(driver, odul_talep_btn, "Odul Talep Et / Claim Reward")

        print("Bekleniyor (4 saniye)...")
        time.sleep(4)

        print("'Tamam / OK' butonu araniyor...")
        tamam_btn = ilk_uygun_elemani_bul(
            driver,
            TAMAM_SELECTORS,
            timeout=15,
            clickable=True,
            aciklama="Tamam butonu",
        )
        elemani_tikla(driver, tamam_btn, "Tamam / OK")
        time.sleep(2)

        print("Bakiye guncellemesi icin sayfa yenileniyor...")
        driver.refresh()

        if not pixverse_ana_sayfayi_bekle(driver, timeout=45):
            return False

        print("Guncel bakiye okunuyor...")
        son_kredi_element = ilk_uygun_elemani_bul(
            driver,
            KREDI_BAKIYE_SELECTORS,
            timeout=15,
            clickable=False,
            aciklama="Kredi gostergesi",
        )
        son_kredi = son_kredi_element.text.strip()

        print("\n==============================")
        print(f"GUNCEL KREDI: {son_kredi}")
        print("==============================\n")

        print("Islem basariyla tamamlandi. Tarayici kapatiliyor.")
        return True

    except Exception as e:
        print(f"Islem sirasinda hata: {e}")
        return False
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    active_driver = pixverse_giris()

    if not active_driver:
        print("Giris basarisiz oldugu icin islem sonlandirildi.")
        sys.exit(1)

    basarili = kredi_topla_ve_kapat(active_driver)
    sys.exit(0 if basarili else 1)
