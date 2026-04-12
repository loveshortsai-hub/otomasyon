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
import re
import shutil

# --- DOSYA YOLLARI ---
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ANA_OTOMASYON_YOLU = r"C:\Users\User\Desktop\Otomasyon"

# Giriş ve Prompt Dosyaları
KAYIT_DOSYA = os.path.join(ANA_OTOMASYON_YOLU, r"Ana Sistem\Klonlama\kayıt.txt")
DUZENLEME_DOSYA = os.path.join(ANA_OTOMASYON_YOLU, r"Ana Sistem\Klonlama\düzenleme.txt")

# Kaynak Klasörler
KAYNAK_VIDEO_ANA_KLASOR = os.path.join(ANA_OTOMASYON_YOLU, "İndirilen Video")
KAYNAK_GORSEL_ANA_KLASOR = os.path.join(ANA_OTOMASYON_YOLU, r"Görsel\Klon Görsel")

# Çıktı Klasörü
CIKTI_ANA_KLASOR = os.path.join(ANA_OTOMASYON_YOLU, "Klon Video")

# Geçici İndirme Klasörü
GECICI_INDIRME_KLASORU = os.path.join(ANA_OTOMASYON_YOLU, "Temp_Download")

def kayit_bilgilerini_oku():
    try:
        if not os.path.exists(KAYIT_DOSYA):
            return None, None
        with open(KAYIT_DOSYA, 'r', encoding='utf-8') as f:
            satirlar = f.readlines()
            email = satirlar[0].strip() if len(satirlar) > 0 else ""
            sifre = satirlar[1].strip() if len(satirlar) > 1 else ""
            return email, sifre
    except:
        return None, None

def promptlari_oku():
    promptlar = {}
    try:
        if not os.path.exists(DUZENLEME_DOSYA):
            return promptlar 
        with open(DUZENLEME_DOSYA, 'r', encoding='utf-8') as f:
            for satir in f:
                satir = satir.strip()
                match = re.search(r"Video\s+(\d+)\s*:\s*(.*)", satir, re.IGNORECASE)
                if match:
                    promptlar[int(match.group(1))] = match.group(2).strip()
        return promptlar
    except:
        return promptlar

def islenecek_videolari_bul():
    video_listesi = []
    if not os.path.exists(KAYNAK_VIDEO_ANA_KLASOR):
        print(f"HATA: Video kaynak klasörü yok: {KAYNAK_VIDEO_ANA_KLASOR}")
        return []

    klasorler = os.listdir(KAYNAK_VIDEO_ANA_KLASOR)
    for klasor in klasorler:
        tam_yol = os.path.join(KAYNAK_VIDEO_ANA_KLASOR, klasor)
        if os.path.isdir(tam_yol) and "Video" in klasor:
            numara_match = re.search(r"Video\s+(\d+)", klasor, re.IGNORECASE)
            if numara_match:
                video_no = int(numara_match.group(1))
                video_dosyalari = glob.glob(os.path.join(tam_yol, "*.mp4"))
                if video_dosyalari:
                    video_listesi.append({
                        'no': video_no,
                        'path': video_dosyalari[0],
                        'folder_name': klasor
                    })
    video_listesi.sort(key=lambda x: x['no'])
    return video_listesi

def gorsel_bul_by_id(video_no):
    """
    Klon Görsel X klasöründeki görseli bulur.
    """
    hedef_klasor_adi = f"Klon Görsel {video_no}"
    hedef_yol = os.path.join(KAYNAK_GORSEL_ANA_KLASOR, hedef_klasor_adi)
    if os.path.exists(hedef_yol):
        uzantilar = ['*.png', '*.jpg', '*.jpeg', '*.webp']
        for uzanti in uzantilar:
            bulunanlar = glob.glob(os.path.join(hedef_yol, uzanti))
            if bulunanlar:
                return bulunanlar[0]
    return None

def pixverse_islem():
    email, sifre = kayit_bilgilerini_oku()
    if not email or not sifre:
        print("Kayıt bilgileri eksik.")
        return

    videolar = islenecek_videolari_bul()
    if not videolar:
        print("İşlenecek video bulunamadı!")
        return
    
    print(f"Toplam {len(videolar)} adet video işlenecek.")
    tum_promptlar = promptlari_oku()

    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = CHROME_PATH
    #chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--log-level=3")
    
    # Geçici indirme klasörü
    os.makedirs(GECICI_INDIRME_KLASORU, exist_ok=True)
    prefs = {
        "download.default_directory": GECICI_INDIRME_KLASORU,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(log_path="NUL")
    driver = None

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
        })

        print("Tarayıcı açıldı, giriş yapılıyor...")
        driver.get("https://app.pixverse.ai/login")
        wait = WebDriverWait(driver, 20)
        
        # Giriş İşlemleri
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="E-posta veya Kullanıcı Adı"]'))).send_keys(email)
        driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(sifre)
        time.sleep(1)
        driver.find_element(By.XPATH, '//button[.//div[text()="Giriş"]]').click()
        time.sleep(8)
        print("Giriş başarılı.")
        
        # Popup Kapatma
        try:
            popup = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//div[@role="dialog"]//button[contains(@class, "absolute")]')))
            popup.click()
            time.sleep(1)
        except:
            pass

        # --- DÖNGÜ BAŞLANGICI ---
        for index, video_data in enumerate(videolar):
            video_no = video_data['no']
            video_path = video_data['path']
            
            print(f"\n------------------------------------------------")
            print(f"İŞLEM BAŞLIYOR: Video {video_no}")
            
            try:
                driver.get("https://app.pixverse.ai/create/modify")
                time.sleep(5)
                
                # --- Video Yükleme ---
                file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#modify-customer_video_path input[type="file"]')))
                file_input.send_keys(video_path)
                print("Video yükleniyor...")
                
                try:
                    # Video yüklenene kadar bekle
                    WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.XPATH, '//h4[contains(text(), "Videoyu Düzenle")]')))
                    print("Video panele yüklendi.")
                except:
                    print("HATA: Video yüklenemedi (Zaman aşımı), bu video atlanıyor.")
                    continue
                
                # =================================================================
                # ✅ YENİ GÖRSEL YÜKLEME KODU (SENİN VERDİĞİN DETAYLI KOD)
                # =================================================================
                gorsel_yolu = gorsel_bul_by_id(video_no)

                if gorsel_yolu:
                    print(f"\n=== GÖRSEL BULUNDU: {os.path.basename(gorsel_yolu)} ===")
                    print("Görsel yükleme işlemi başlatılıyor...")

                    try:
                        # @ butonuna tıklama
                        print("@ butonuna tıklanıyor...")
                        at_button = wait.until(EC.element_to_be_clickable((
                            By.XPATH,
                            '//div[contains(@class, "w-8") and contains(@class, "h-8") and contains(@class, "cursor-pointer")]//span[text()="@"]'
                        )))
                        driver.execute_script("arguments[0].click();", at_button)
                        print("@ butonuna tıklandı")
                        time.sleep(3)

                        # Görsel sekmesine geçme
                        print("Görsel sekmesine tıklanıyor...")
                        gorsel_span = wait.until(EC.presence_of_element_located((
                            By.XPATH, '//span[@class="text-xs" and text()="Görsel"]'
                        )))

                        gorsel_button = driver.execute_script(
                            "return arguments[0].closest('button[role=\"tab\"]');",
                            gorsel_span
                        )

                        if gorsel_button:
                            actions = ActionChains(driver)
                            actions.move_to_element(gorsel_button).pause(0.5).click().perform()
                            time.sleep(2)

                            if gorsel_button.get_attribute("aria-selected") != "true":
                                driver.execute_script("arguments[0].click();", gorsel_button)
                                time.sleep(2)

                        time.sleep(2)

                        # Görsel yükleme input alanı
                        print("Görsel tab'ındaki file input bulunuyor...")
                        file_input_gorsel = wait.until(EC.presence_of_element_located((
                            By.XPATH,
                            '//div[@role="tabpanel" and @data-state="active"]//input[@type="file"][@accept="image/png,image/jpeg,image/webp"]'
                        )))

                        file_input_gorsel.send_keys(gorsel_yolu)
                        print(f"Görsel dosyası seçildi: {os.path.basename(gorsel_yolu)}")

                        # Görsel yüklenmesini bekleme
                        print("Görselin yüklenmesi bekleniyor (Max 50 saniye)...")
                        try:
                            upload_wait = WebDriverWait(driver, 50)
                            uploaded_img = upload_wait.until(
                                EC.presence_of_element_located((
                                    By.XPATH,
                                    '//img[contains(@src, "media.pixverse.ai/upload") and contains(@class, "w-8")]'
                                ))
                            )
                            print("Görsel başarıyla yüklendi!")
                            time.sleep(2)

                        except Exception:
                            # Burada return yaparsak döngü biter, o yüzden raise yapıp videoyu atlıyoruz
                            raise Exception("ZAMAN AŞIMI: Görsel yüklenemedi!")

                        # Yüklenen görseli seçme
                        print("Yüklenen görsel seçiliyor...")
                        try:
                            uploaded_image_container = wait.until(EC.presence_of_element_located((
                                By.XPATH,
                                '//div[contains(@class, "flex") and contains(@class, "items-center") and contains(@class, "gap-3") and contains(@class, "cursor-pointer") and .//img[contains(@src, "media.pixverse.ai/upload")]]'
                            )))

                            driver.execute_script("arguments[0].scrollIntoView({behavior: \"smooth\", block: \"center\"});", uploaded_image_container)
                            time.sleep(1)

                            try:
                                uploaded_image_container.click()
                            except:
                                driver.execute_script("arguments[0].click();", uploaded_image_container)

                            time.sleep(2)
                            print("Görsel seçimi yapıldı.")

                        except Exception:
                            # Alternatif görsel tıklama
                            print("Seçim hatası, alternatif deneniyor...")
                            try:
                                img_element = driver.find_element(
                                    By.XPATH,
                                    '//img[contains(@src, "media.pixverse.ai/upload") and contains(@class, "w-8")]'
                                )
                                driver.execute_script("arguments[0].click();", img_element)
                                print("Alternatif seçim yapıldı.")
                                time.sleep(2)
                            except:
                                pass

                        print("=== GÖRSEL YÜKLEME TAMAMLANDI ===\n")

                    except Exception as e:
                        print(f"Görsel yükleme hatası: {e}")
                        print("Bu video için işleme devam edilemiyor, sonraki videoya geçiliyor.")
                        continue # Hata olursa bu videoyu atla
                else:
                    print("\n=== GÖRSEL BULUNAMADI, görsel olmadan devam ediliyor... ===\n")
                # =================================================================

                # --- Prompt Girişi ---
                prompt_text = tum_promptlar.get(video_no, "Make changes.")
                editor = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.tiptap.ProseMirror')))
                driver.execute_script("arguments[0].scrollIntoView(true);", editor)
                
                if gorsel_yolu:
                    editor.send_keys(Keys.CONTROL + Keys.END)
                    time.sleep(0.5)
                    editor.send_keys(" ")
                else:
                    editor.send_keys(Keys.CONTROL + "a")
                    time.sleep(0.5)
                    editor.send_keys(Keys.DELETE)
                
                for char in prompt_text:
                    editor.send_keys(char)
                time.sleep(1)

                # --- Create Tıklama ---
                print("Create butonu tetiklendi")
                actions = ActionChains(driver)
                actions.send_keys(Keys.TAB).perform()
                time.sleep(1)
                actions.send_keys(Keys.ENTER).perform()
                
                # --- Video Oluşumunu Takip Etme ---
                print("Video oluşması bekleniyor...")
                max_bekleme = 600
                bekleme_sayaci = 0
                son_progress = ""
                yuzde_100_oldu = False
                progress_basladi_mi = False

                while bekleme_sayaci < max_bekleme:
                    try:
                        progress_elements = driver.find_elements(By.XPATH, '//div[contains(text(), "%")]')
                        
                        if progress_elements:
                            progress_text = progress_elements[0].text.strip()
                            if not progress_basladi_mi:
                                progress_basladi_mi = True
                                print("Progress takibi başladı")
                            if progress_text != son_progress:
                                print(f"Video oluşuyor: {progress_text}")
                                son_progress = progress_text
                            if "100%" in progress_text:
                                yuzde_100_oldu = True
                            time.sleep(3)
                            bekleme_sayaci += 3
                        else:
                            if progress_basladi_mi:
                                video_elements = driver.find_elements(By.CSS_SELECTOR, 'video[src*=".mp4"]')
                                if video_elements:
                                    print("Video hazır!")
                                    yuzde_100_oldu = True
                                    break
                                else:
                                    time.sleep(5)
                                    bekleme_sayaci += 5
                            else:
                                time.sleep(5)
                                bekleme_sayaci += 5
                    except:
                        time.sleep(10)
                        bekleme_sayaci += 10
                
                if not yuzde_100_oldu:
                    print("Zaman aşımı: Video oluşturulamadı.")
                    continue

                # --- İndirme İşlemi ---
                print("\n=== İndirme başlıyor ===")
                time.sleep(8)
                
                INDIRME_KLASORU = GECICI_INDIRME_KLASORU 

                # Video sekmesine geç
                try:
                    if "modify" in driver.current_url:
                        video_tab = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, '//div[text()="Video"]'))
                        )
                        video_tab.click()
                        print("Video sekmesine geçildi")
                        time.sleep(10)
                except:
                    pass

                # Video detayına tıkla
                try:
                    video_containers = WebDriverWait(driver, 40).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'video[src*=".mp4"]'))
                    )
                    if len(video_containers) > 0:
                        en_yeni_video = video_containers[0]
                        parent_container = driver.execute_script(
                            "return arguments[0].closest('div.cursor-pointer') || arguments[0].parentElement;", 
                            en_yeni_video
                        )
                        if parent_container:
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", parent_container)
                            time.sleep(2)
                            driver.execute_script("arguments[0].click();", parent_container)
                        else:
                            driver.execute_script("arguments[0].click();", en_yeni_video)
                        
                        print("Video detay sayfası açıldı")
                        time.sleep(12)
                except Exception as e:
                    print(f"Video açma hatası: {e}")
                    continue 

                # Önceki dosyaları listele
                onceki_dosyalar = sorted(glob.glob(os.path.join(INDIRME_KLASORU, "*.mp4")), key=os.path.getctime)
                onceki_en_yeni = onceki_dosyalar[-1] if onceki_dosyalar else None

                # İndirme butonuna tıkla
                try:
                    download_button = WebDriverWait(driver, 40).until(
                        EC.element_to_be_clickable((By.XPATH, 
                            '//button[.//span[text()="İndir"] or .//div[text()="İndir"] or .//text()[contains(., "İndir")] or .//text()[contains(., "Download")]]'))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", download_button)
                    time.sleep(2)
                    driver.execute_script("arguments[0].click();", download_button)
                    print("Download butonu tıklandı!")
                except:
                    print("Download butonu bulunamadı!")
                    continue 

                # Yeni dosya inene kadar bekle
                print("İndirme bekleniyor...")
                bekleme = 0
                yeni_dosya = None
                
                while bekleme < 180:
                    current_files = sorted(glob.glob(os.path.join(INDIRME_KLASORU, "*.mp4")), key=os.path.getctime)
                    yeni_dosya = None
                    for f in current_files[::-1]:
                        if onceki_en_yeni is None or os.path.getctime(f) > os.path.getctime(onceki_en_yeni):
                            yeni_dosya = f
                            break
                    if yeni_dosya:
                        print(f"Başarı! Dosya indirildi: {os.path.basename(yeni_dosya)}")
                        break
                    time.sleep(6)
                    bekleme += 6
                else:
                    print("UYARI: İndirme tamamlanmadı.")

                # Dosyayı Taşıma
                if yeni_dosya:
                    try:
                        hedef_klasor = os.path.join(CIKTI_ANA_KLASOR, f"Klon Video {video_no}")
                        os.makedirs(hedef_klasor, exist_ok=True)
                        
                        hedef_dosya_ismi = f"Klon_Video_{video_no}.mp4"
                        hedef_tam_yol = os.path.join(hedef_klasor, hedef_dosya_ismi)
                        
                        if yeni_dosya.endswith(".crdownload"):
                             time.sleep(10)

                        shutil.move(yeni_dosya, hedef_tam_yol)
                        print(f"✅ VİDEO KAYDEDİLDİ: {hedef_tam_yol}")
                    except Exception as e:
                        print(f"Taşıma hatası: {e}")

            except Exception as e:
                print(f"Video {video_no} döngü hatası: {e}")
                continue

    except Exception as e:
        print(f"Sistem hatası: {e}")
    finally:
        if driver:
            driver.quit()
        try:
            if os.path.exists(GECICI_INDIRME_KLASORU):
                shutil.rmtree(GECICI_INDIRME_KLASORU)
        except:
            pass

if __name__ == "__main__":
    pixverse_islem()