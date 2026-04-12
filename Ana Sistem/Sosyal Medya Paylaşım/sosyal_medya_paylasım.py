import json
import os
import re
import sys
import time
import traceback
import datetime
import threading

try:
    import requests
except ImportError:
    import subprocess as _sp
    _sp.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests


# ============================================================
# BUFFER API TABANLI SOSYAL MEDYA PAYLAŞIM SİSTEMİ (v5)
# ============================================================
# Bu script, Buffer GraphQL API kullanarak sosyal medya
# paylaşımlarını gerçekleştirir. Selenium/tarayıcı otomasyonu
# yerine doğrudan API çağrıları kullanır.
#
# v5 Değişiklikleri:
#   - URL doğrulama retry mantığı iyileştirildi:
#     * Yükleme başarılı + doğrulama başarısız durumunda dosya
#       tekrar yüklenmez, aynı URL birkaç kez daha doğrulanır
#     * Doğrulama denemeleri arası artan bekleme süresi (5s, 10s, 15s)
#     * Tüm doğrulama denemeleri başarısız olursa farklı servise geçer
#   - catbox.moe hata mesajları kısaltıldı:
#     * 'Connection aborted', 'RemoteDisconnected' pattern'leri eklendi
#   - Gereksiz yeniden yükleme önlendi (3 dakikaya varan zaman kaybı giderildi)
#   - Log mesajları daha temiz ve bilgilendirici
#
# Önceki sürüm değişiklikleri (v4):
#   - Video yükleme servis önceliği: uguu.se birincil (DNS güvenilir)
#   - litterbox.catbox.moe DNS erişim testi eklendi (hızlı atlama)
#   - "Zaten tamamlandı" durumu için açık ve temiz log mesajları
#   - URL doğrulama hata mesajları kısaltıldı (ham exception gizlendi)
#   - Özet bölümünde "zaten tamamlandı" ayrı kategori olarak gösteriliyor
#   - Log mesajları genel olarak daha okunabilir hale getirildi
#
# Önceki sürüm değişiklikleri (v3):
#   - Video yükleme güvenilirliği artırıldı (URL doğrulama eklendi)
#   - Çoklu video paylaşımında rate limiting koruması eklendi
#   - TikTok status='error' durumu artık başarısız olarak işaretleniyor
#   - Toplu hesap modunda video yükleme önbelleği düzeltildi
#   - Platform bazlı retry mekanizması eklendi
#   - Videolar arası bekleme süresi eklendi (rate limiting koruması)
#
# Gereksinimler:
#   - Buffer API Token (hesap ayarlarından alınır)
#   - Buffer hesabına bağlı sosyal medya kanalları
#
# Desteklenen platformlar: YouTube, TikTok, Instagram
# ============================================================


BUFFER_API_URL = "https://api.buffer.com"

# Platform sıralama ve eşleştirme
PLATFORM_ORDER = ["Youtube", "Tiktok", "Instagram"]
PLATFORM_KEY_MAP = {"Youtube": "youtube", "Tiktok": "tiktok", "Instagram": "instagram"}
PLATFORM_SERVICE_MAP = {
    "Youtube": "youtube",
    "Tiktok": "tiktok",
    "Instagram": "instagram",
}

# YouTube kategori ID'leri (en yaygın olanlar)
YOUTUBE_CATEGORIES = {
    "film": "1",
    "autos": "2",
    "music": "10",
    "pets": "15",
    "sports": "17",
    "travel": "19",
    "gaming": "20",
    "people": "22",
    "comedy": "23",
    "entertainment": "24",
    "news": "25",
    "howto": "26",
    "education": "27",
    "science": "28",
}
DEFAULT_YOUTUBE_CATEGORY_ID = "22"  # People & Blogs

# Çoklu video paylaşımı için bekleme süreleri (saniye)
INTER_VIDEO_DELAY = 10       # Videolar arası bekleme süresi
INTER_PLATFORM_DELAY = 3     # Platformlar arası bekleme süresi
POST_UPLOAD_DELAY = 5        # Yükleme sonrası Buffer'ın videoyu işlemesi için bekleme
MAX_PLATFORM_RETRIES = 2     # Platform bazlı maksimum yeniden deneme sayısı

# v5: URL doğrulama retry ayarları
URL_VERIFY_MAX_RETRIES = 3       # Aynı URL için maksimum doğrulama denemesi
URL_VERIFY_BASE_WAIT = 5         # İlk doğrulama bekleme süresi (saniye)
URL_VERIFY_WAIT_INCREMENT = 5    # Her denemede eklenen bekleme süresi (5s, 10s, 15s)


class StopRequested(Exception):
    pass


class BufferAPIError(Exception):
    """Buffer API hatası."""
    pass


class PastScheduleError(Exception):
    """Geçmiş tarihli zamanlama hatası.

    Kullanıcının belirlediği zamanlama saati geçmişte kaldığında
    fırlatılır.  Bu durumda paylaşım yapılmamalı ve işlem
    başarısız olarak loglanmalıdır.
    """
    pass


# ============================================================
# DOSYA / YARDIMCI FONKSİYONLAR
# ============================================================

def read_file_content(full_path):
    if not os.path.exists(full_path):
        return None
    encodings = ["utf-8", "cp1254", "latin-1"]
    for enc in encodings:
        try:
            with open(full_path, "r", encoding=enc) as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            continue
    return None


def get_config_path():
    return r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım"


def get_shared_control_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(current_dir), "Otomasyon Çalıştırma", ".control"),
        os.path.join(current_dir, ".control"),
        os.path.join(os.getcwd(), ".control"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
            return path
    os.makedirs(candidates[0], exist_ok=True)
    return candidates[0]


CONTROL_DIR = get_shared_control_dir()
PAUSE_FLAG = os.path.join(CONTROL_DIR, "PAUSE.flag")
STOP_FLAG = os.path.join(CONTROL_DIR, "STOP.flag")
STATE_FILE = os.path.join(CONTROL_DIR, "SOCIAL_MEDIA_STATE.json")
DONE_FILE = os.path.join(CONTROL_DIR, "SOCIAL_MEDIA_DONE.json")
FAILED_FILE = os.path.join(CONTROL_DIR, "SOCIAL_MEDIA_FAILED.json")


# ============================================================
# JSON STATE YÖNETİMİ (Resume / Pause / Stop)
# ============================================================

def _load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(default, list) and isinstance(data, list):
                return data
            if isinstance(default, dict) and isinstance(data, dict):
                return data
    except Exception:
        pass
    return default


def _save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as exc:
        print(f"[WARN] State dosyası yazılamadı: {os.path.basename(path)} ({exc})")
        return False


def clear_resume_state():
    for path in (STATE_FILE, DONE_FILE, FAILED_FILE):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def load_resume_state():
    state = _load_json(
        STATE_FILE,
        {
            "done_platforms": [],
            "failed_platforms": {},
            "active_platforms": [],
            "last_platform": "",
            "updated_at": "",
        },
    )
    done = _load_json(DONE_FILE, [])
    failed = _load_json(FAILED_FILE, {})
    state["done_platforms"] = [str(x) for x in done if str(x).strip()]
    state["failed_platforms"] = {str(k): str(v) for k, v in failed.items()}
    return state


def save_resume_state(state):
    state = dict(state or {})
    state["done_platforms"] = [str(x) for x in state.get("done_platforms", []) if str(x).strip()]
    state["failed_platforms"] = {str(k): str(v) for k, v in state.get("failed_platforms", {}).items()}
    state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_json(STATE_FILE, state)
    _save_json(DONE_FILE, state.get("done_platforms", []))
    _save_json(FAILED_FILE, state.get("failed_platforms", {}))


def update_resume_state(platform_name=None, success=None, detail=""):
    state = load_resume_state()
    done = list(state.get("done_platforms", []))
    failed = dict(state.get("failed_platforms", {}))

    if platform_name:
        if success is True:
            if platform_name not in done:
                done.append(platform_name)
            failed.pop(platform_name, None)
            state["last_platform"] = platform_name
        elif success is False:
            failed[platform_name] = str(detail or "Başarısız")
            if platform_name in done:
                done.remove(platform_name)
            state["last_platform"] = platform_name

    state["done_platforms"] = done
    state["failed_platforms"] = failed
    save_resume_state(state)


def check_flag_state():
    pause_logged = False
    while os.path.exists(PAUSE_FLAG):
        if os.path.exists(STOP_FLAG):
            print("[WARN] STOP.flag algılandı. İşlem güvenli şekilde sonlandırılıyor.")
            raise StopRequested()
        if not pause_logged:
            print("[INFO] PAUSE.flag algılandı. İşlem duraklatıldı.")
            pause_logged = True
        time.sleep(1)

    if pause_logged:
        print("[INFO] Duraklatma kaldırıldı. İşlem devam ediyor.")

    if os.path.exists(STOP_FLAG):
        print("[WARN] STOP.flag algılandı. İşlem güvenli şekilde sonlandırılıyor.")
        raise StopRequested()


def controlled_sleep(seconds):
    end_time = time.time() + max(0.0, float(seconds))
    while time.time() < end_time:
        check_flag_state()
        time.sleep(min(0.5, max(0.0, end_time - time.time())))


# ============================================================
# HATA MESAJI KISA FORMATLAYICI
# ============================================================

def _shorten_exception(exc_text):
    """Ham Python exception mesajlarını kısa ve okunabilir hale getirir.

    Örnek:
      Girdi:  "HTTPSConnectionPool(host='litter.catbox.moe', port=443):
               Max retries exceeded with url: /o5zfz0.mp4 (Caused by
               NameResolutionError(...))"
      Çıktı:  "litter.catbox.moe DNS çözümlenemedi"
    """
    raw = str(exc_text or "").strip()
    if not raw:
        return "Bilinmeyen hata"

    # DNS çözümleme hatası
    if re.search(r'NameResolutionError|getaddrinfo failed|Name or service not known', raw, re.IGNORECASE):
        host_match = re.search(r"host='([^']+)'", raw)
        host = host_match.group(1) if host_match else "sunucu"
        return f"{host} DNS çözümlenemedi"

    # Bağlantı zaman aşımı
    if re.search(r'ConnectTimeoutError|connect timeout|connection timed out', raw, re.IGNORECASE):
        host_match = re.search(r"host='([^']+)'", raw)
        host = host_match.group(1) if host_match else "sunucu"
        return f"{host} bağlantı zaman aşımı"

    # Bağlantı reddedildi
    if re.search(r'ConnectionRefusedError|Connection refused', raw, re.IGNORECASE):
        host_match = re.search(r"host='([^']+)'", raw)
        host = host_match.group(1) if host_match else "sunucu"
        return f"{host} bağlantı reddedildi"

    # v5: Connection aborted / RemoteDisconnected (catbox.moe sorunu)
    if re.search(r'Connection aborted|RemoteDisconnected|Remote end closed', raw, re.IGNORECASE):
        host_match = re.search(r"host='([^']+)'", raw)
        if not host_match:
            # URL'den host çıkarmayı dene
            url_match = re.search(r'https?://([^/\s]+)', raw)
            host = url_match.group(1) if url_match else "sunucu"
        else:
            host = host_match.group(1)
        return f"{host} bağlantı kesildi (sunucu yanıt vermedi)"

    # Max retries exceeded (genel)
    if re.search(r'Max retries exceeded', raw, re.IGNORECASE):
        host_match = re.search(r"host='([^']+)'", raw)
        host = host_match.group(1) if host_match else "sunucu"
        return f"{host} erişilemedi (bağlantı hatası)"

    # SSL hatası
    if re.search(r'SSLError|SSL.*certificate', raw, re.IGNORECASE):
        return "SSL sertifika hatası"

    # Zaten kısa bir mesajsa olduğu gibi döndür
    if len(raw) <= 80 and "\n" not in raw:
        return raw

    # Uzun mesajları kısalt
    first_line = raw.split("\n")[0].strip()
    if len(first_line) > 80:
        first_line = first_line[:77] + "..."
    return first_line if first_line else "Bilinmeyen hata"


# ============================================================
# VİDEO YÜKLEME SERVİSİ (Public URL Oluşturma)
# ============================================================

class VideoUploader:
    """Video dosyalarını ücretsiz dosya paylaşım servislerine yükler.

    Buffer API, video için internetten erişilebilir bir URL gerektirir.
    URL'nin doğru Content-Type (video/mp4) ve Content-Length header'ları
    döndürmesi zorunludur. Yerel IP adresleri (192.168.x.x) Buffer
    sunucularından erişilemez.

    Desteklenen servisler (öncelik sırasıyla):
    1. uguu.se        — 128MB limit, 3 saat geçici, doğru Content-Type/Length
    2. litterbox      — 200MB limit, 72 saat geçici (DNS sorunu olabilir)
    3. catbox.moe     — 200MB limit, kalıcı URL (Content-Length sorunlu olabilir)

    v5 İyileştirmeleri:
    - URL doğrulama başarısız olduğunda dosya yeniden yüklenmez,
      aynı URL artan bekleme süreleriyle tekrar doğrulanır
    - Tüm doğrulama denemeleri başarısız olursa farklı servise geçer
    - catbox.moe hata mesajları kısaltıldı
    - Gereksiz yeniden yükleme önlendi (~3 dakika zaman tasarrufu)
    """

    _upload_cache = {}
    _cache_lock = threading.Lock()
    _last_upload_time = 0
    _litterbox_available = None  # v4: DNS erişim durumu önbelleği

    @classmethod
    def upload_video(cls, video_path, max_retries=2, force_new=False):
        """Video dosyasını yükler ve public URL döndürür."""
        abs_path = os.path.abspath(video_path)

        # Önbellekteki URL'nin erişilebilirliğini doğrula
        if not force_new:
            with cls._cache_lock:
                if abs_path in cls._upload_cache:
                    cached_url = cls._upload_cache[abs_path]
                    if cls._verify_url_accessible(cached_url):
                        print(f"[INFO] Video URL önbellekten alındı ve doğrulandı: {cached_url[:80]}...")
                        return cached_url
                    else:
                        print(f"[WARN] Önbellekteki URL artık erişilebilir değil, yeniden yükleniyor...")
                        del cls._upload_cache[abs_path]

        if not os.path.exists(abs_path):
            print(f"[ERROR] Video dosyası bulunamadı: {abs_path}")
            return None

        file_size = os.path.getsize(abs_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"[INFO] Video yükleniyor: {os.path.basename(abs_path)} ({file_size_mb:.1f} MB)")

        if file_size_mb > 200:
            print(f"[ERROR] Video dosyası çok büyük ({file_size_mb:.1f} MB). Maksimum 200 MB desteklenir.")
            return None

        # Rate limiting koruması - ardışık yüklemeler arası bekleme
        now = time.time()
        elapsed = now - cls._last_upload_time
        if elapsed < 5 and cls._last_upload_time > 0:
            wait_time = 5 - elapsed
            print(f"[INFO] Rate limiting koruması: {wait_time:.1f}s bekleniyor...")
            controlled_sleep(wait_time)

        # v4: Servis listesini oluştur (erişilebilirliğe göre)
        upload_methods = cls._build_upload_methods(file_size_mb)

        for service_name, upload_func in upload_methods:
            try:
                check_flag_state()
                print(f"[INFO] {service_name} servisine yükleniyor...")
                url = upload_func(abs_path)
                if url:
                    # v5: Yükleme başarılı — URL doğrulamayı retry ile yap
                    verified = cls._verify_url_with_retry(url, service_name)
                    if verified:
                        print(f"[OK] Video yüklendi: {url}")
                        with cls._cache_lock:
                            cls._upload_cache[abs_path] = url
                        cls._last_upload_time = time.time()
                        return url
                    else:
                        print(f"[WARN] {service_name} URL doğrulanamadı, farklı servis deneniyor...")
                        continue
            except StopRequested:
                raise
            except Exception as e:
                short_err = _shorten_exception(str(e))
                print(f"[WARN] {service_name} yükleme hatası: {short_err}")
                controlled_sleep(3)

        print("[ERROR] Video hiçbir servise yüklenemedi.")
        return None

    @classmethod
    def _verify_url_with_retry(cls, url, service_name):
        """v5: URL doğrulamasını artan bekleme süreleriyle tekrar dener.

        Yükleme başarılı olduktan sonra download domain'i geçici olarak
        erişilemez olabilir. Bu durumda dosyayı tekrar yüklemek yerine
        aynı URL'yi birkaç kez daha doğrulamayı dener.

        Bekleme süreleri: 0s (ilk deneme), 5s, 10s, 15s
        Toplam maksimum bekleme: ~30s (9+ yükleme denemesi yerine)
        """
        for attempt in range(URL_VERIFY_MAX_RETRIES + 1):
            check_flag_state()

            if attempt > 0:
                wait_time = URL_VERIFY_BASE_WAIT + (attempt - 1) * URL_VERIFY_WAIT_INCREMENT
                print(f"[INFO] URL doğrulama bekleniyor ({wait_time}s)... (deneme {attempt + 1}/{URL_VERIFY_MAX_RETRIES + 1})")
                controlled_sleep(wait_time)
            else:
                print(f"[INFO] URL doğrulanıyor...")

            if cls._verify_url_accessible(url):
                if attempt > 0:
                    print(f"[OK] URL doğrulama başarılı (deneme {attempt + 1})")
                return True

        # Tüm denemeler başarısız
        print(f"[WARN] {service_name}: {URL_VERIFY_MAX_RETRIES + 1} doğrulama denemesi başarısız")
        return False

    @classmethod
    def _build_upload_methods(cls, file_size_mb):
        """v4: Erişilebilir servislerin listesini oluşturur.

        litterbox.catbox.moe DNS sorunu yaşayabilir. Bu durumda
        servisi listeye dahil etmeden hızlıca atlar.
        """
        methods = []

        # 1. uguu.se — birincil (DNS güvenilir, 3 saat URL süresi)
        if file_size_mb <= 100:
            methods.append(("uguu.se", cls._upload_uguu))

        # 2. litterbox — DNS erişim testi ile (72 saat URL süresi)
        if cls._is_litterbox_available():
            methods.append(("litterbox.catbox.moe", cls._upload_litterbox))
        else:
            print(f"[INFO] litterbox.catbox.moe erişilemez durumda, atlanıyor.")

        # 3. catbox.moe — yedek (kalıcı URL)
        methods.append(("catbox.moe", cls._upload_catbox))

        # uguu.se boyut aşımı durumunda listeye eklenmemişse ve
        # litterbox da erişilemezse, en az catbox kalsın
        if not methods:
            methods.append(("catbox.moe", cls._upload_catbox))

        return methods

    @classmethod
    def _is_litterbox_available(cls):
        """v4: litterbox.catbox.moe DNS erişim testi.

        DNS çözümlemesi yaparak servisin erişilebilir olup olmadığını
        kontrol eder. Sonucu 5 dakika önbelleğe alır.
        """
        import socket

        # Önbellek kontrolü (5 dakika geçerli)
        if cls._litterbox_available is not None:
            cache_time = getattr(cls, '_litterbox_check_time', 0)
            if time.time() - cache_time < 300:
                return cls._litterbox_available

        try:
            socket.setdefaulttimeout(5)
            socket.getaddrinfo("litter.catbox.moe", 443)
            cls._litterbox_available = True
        except (socket.gaierror, socket.timeout, OSError):
            cls._litterbox_available = False
        finally:
            socket.setdefaulttimeout(None)

        cls._litterbox_check_time = time.time()
        return cls._litterbox_available

    @staticmethod
    def _verify_url_accessible(url, timeout=30):
        """URL'nin erişilebilir olduğunu ve doğru Content-Type döndürdüğünü doğrular."""
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)

            if resp.status_code == 405:
                resp = requests.get(url, timeout=timeout, stream=True, allow_redirects=True)
                resp.close()

            if resp.status_code != 200:
                print(f"[WARN] URL doğrulama: HTTP {resp.status_code}")
                return False

            content_type = resp.headers.get("Content-Type", "").lower()
            content_length = resp.headers.get("Content-Length", "")

            # Content-Length kontrolü (Buffer API sıfır uzunluk reddeder)
            try:
                cl = int(content_length) if content_length else -1
                if cl == 0:
                    print(f"[WARN] URL doğrulama: Content-Length 0")
                    return False
            except (ValueError, TypeError):
                pass

            return True

        except requests.exceptions.Timeout:
            print(f"[WARN] URL doğrulama: Zaman aşımı")
            return False
        except Exception as e:
            short_err = _shorten_exception(str(e))
            print(f"[WARN] URL doğrulama hatası: {short_err}")
            return False

    @classmethod
    def invalidate_cache(cls, video_path=None):
        """Belirli bir video veya tüm önbelleği temizler."""
        with cls._cache_lock:
            if video_path:
                abs_path = os.path.abspath(video_path)
                cls._upload_cache.pop(abs_path, None)
            else:
                cls._upload_cache.clear()

    @staticmethod
    def _upload_uguu(video_path):
        """uguu.se — 128MB limit, 3 saat geçici, doğru Content-Type/Length."""
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        if file_size_mb > 100:
            raise Exception(f"Dosya boyutu ({file_size_mb:.1f} MB) uguu.se limiti (100 MB) aşıyor")
        with open(video_path, "rb") as f:
            resp = requests.post(
                "https://uguu.se/upload",
                files={"files[]": (os.path.basename(video_path), f, "video/mp4")},
                timeout=600,
            )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("files"):
                url = data["files"][0].get("url", "")
                if url:
                    return url
        raise Exception(f"uguu.se yanıt hatası: {resp.status_code}")

    @staticmethod
    def _upload_catbox(video_path):
        """catbox.moe — 200MB limit, kalıcı URL."""
        with open(video_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (os.path.basename(video_path), f)},
                timeout=600,
            )
        if resp.status_code == 200 and resp.text.strip().startswith("https://"):
            return resp.text.strip()
        raise Exception(f"catbox.moe yanıt hatası: {resp.status_code}")

    @staticmethod
    def _upload_litterbox(video_path):
        """litterbox.catbox.moe — 200MB limit, 72 saat geçici."""
        with open(video_path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": (os.path.basename(video_path), f, "video/mp4")},
                timeout=600,
            )
        if resp.status_code == 200 and resp.text.strip().startswith("https://"):
            return resp.text.strip()
        raise Exception(f"litterbox yanıt hatası: {resp.status_code}")

    @staticmethod
    def _upload_tmpfiles(video_path):
        """tmpfiles.org — geçici URL. Bu servis artık kullanılmıyor."""
        with open(video_path, "rb") as f:
            resp = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": (os.path.basename(video_path), f)},
                timeout=600,
            )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                url = data.get("data", {}).get("url", "")
                if url:
                    url = url.replace("http://", "https://")
                    url = url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
                    return url
        raise Exception(f"tmpfiles yanıt hatası: {resp.status_code}")

    @classmethod
    def clear_cache(cls):
        with cls._cache_lock:
            cls._upload_cache.clear()
        cls._last_upload_time = 0
        cls._litterbox_available = None


# ============================================================
# VİDEO URL ÇÖZÜMLEME
# ============================================================

def resolve_video_url(video_path, force_new=False):
    """Video dosyası için public URL oluşturur."""
    if not video_path:
        return None

    if not os.path.exists(video_path):
        print(f"[WARN] Video dosyası bulunamadı: {video_path}")
        return None

    return VideoUploader.upload_video(video_path, force_new=force_new)


# ============================================================
# BUFFER API İSTEMCİSİ (GraphQL)
# ============================================================

class BufferAPIClient:
    """Buffer GraphQL API istemcisi."""

    def __init__(self, api_token):
        self.api_token = api_token
        self.api_url = BUFFER_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}",
        })
        self._organization_id = None
        self._channels_cache = None

    def _execute_query(self, query, variables=None, operation_name=None):
        """GraphQL sorgusu çalıştırır."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        try:
            response = self.session.post(self.api_url, json=payload, timeout=120)
        except requests.exceptions.Timeout:
            raise BufferAPIError("API isteği zaman aşımına uğradı (120s)")
        except requests.exceptions.ConnectionError:
            raise BufferAPIError("Buffer API'ye bağlanılamadı. İnternet bağlantınızı kontrol edin.")
        except Exception as e:
            raise BufferAPIError(f"API isteği başarısız: {e}")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            raise BufferAPIError(f"Rate limit aşıldı. {retry_after} saniye sonra tekrar deneyin.")

        if response.status_code != 200:
            raise BufferAPIError(f"API HTTP hatası: {response.status_code} - {response.text[:500]}")

        try:
            result = response.json()
        except Exception:
            raise BufferAPIError(f"API yanıtı JSON olarak ayrıştırılamadı: {response.text[:200]}")

        if "errors" in result and result["errors"]:
            error_messages = "; ".join(e.get("message", "Bilinmeyen hata") for e in result["errors"])
            raise BufferAPIError(f"GraphQL hatası: {error_messages}")

        return result.get("data", {})

    def verify_token(self):
        """API token'ın geçerli olup olmadığını kontrol eder."""
        query = """
        query VerifyToken {
          account {
            organizations {
              id
              name
            }
          }
        }
        """
        try:
            data = self._execute_query(query)
            orgs = data.get("account", {}).get("organizations", [])
            if orgs:
                self._organization_id = orgs[0]["id"]
                print(f"[OK] API Token doğrulandı. Organizasyon: {orgs[0].get('name', 'N/A')} (ID: {self._organization_id})")
                return True
            else:
                print("[ERROR] Hesapta organizasyon bulunamadı.")
                return False
        except BufferAPIError as e:
            print(f"[ERROR] Token doğrulama başarısız: {e}")
            return False

    def get_organization_id(self):
        if self._organization_id:
            return self._organization_id
        self.verify_token()
        return self._organization_id

    def get_channels(self, force_refresh=False):
        """Tüm kanalları getirir."""
        if self._channels_cache and not force_refresh:
            return self._channels_cache

        org_id = self.get_organization_id()
        if not org_id:
            raise BufferAPIError("Organizasyon ID'si alınamadı.")

        query = """
        query GetChannels($input: ChannelsInput!) {
          channels(input: $input) {
            id
            name
            displayName
            service
            avatar
            isQueuePaused
          }
        }
        """
        variables = {
            "input": {
                "organizationId": org_id,
                "filter": {"isLocked": False}
            }
        }

        data = self._execute_query(query, variables)
        channels = data.get("channels", [])
        self._channels_cache = channels
        return channels

    def get_channel_by_service(self, service_name):
        """Belirtilen servis adına göre kanal bulur."""
        channels = self.get_channels()
        service_lower = service_name.lower()
        for ch in channels:
            if ch.get("service", "").lower() == service_lower:
                return ch
        return None

    def create_post(self, channel_id, text, mode="shareNow", due_at=None,
                    scheduling_type="automatic", assets=None, metadata=None):
        """Gönderi oluşturur (tüm platformlar için tek fonksiyon)."""
        query = """
        mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess {
              post {
                id
                text
                status
              }
            }
            ... on MutationError {
              message
            }
          }
        }
        """
        input_data = {
            "text": text or "",
            "channelId": channel_id,
            "schedulingType": scheduling_type,
            "mode": mode,
        }
        if due_at:
            input_data["dueAt"] = due_at
        if assets:
            input_data["assets"] = assets
        if metadata:
            input_data["metadata"] = metadata

        data = self._execute_query(query, {"input": input_data})
        result = data.get("createPost", {})

        if "message" in result and result.get("message"):
            raise BufferAPIError(f"Gönderi hatası: {result['message']}")

        post = result.get("post", {})
        post_status = post.get("status", "")

        # status='error' durumunu başarısız olarak işaretle
        if post_status == "error":
            post_id = post.get("id", "N/A")
            raise BufferAPIError(
                f"Gönderi oluşturuldu ama platform tarafından reddedildi (Post ID: {post_id}). "
                f"Video URL erişim sorunu veya format uyumsuzluğu olabilir."
            )

        return post


# ============================================================
# KONFİGÜRASYON OKUMA (Mevcut dosya formatı ile uyumlu)
# ============================================================

def natural_sort_key(value):
    text = os.path.basename(str(value or ""))
    parts = re.split(r"(\d+)", text)
    out = []
    for part in parts:
        if part.isdigit():
            out.append(int(part))
        else:
            out.append(part.lower())
    return out


def get_video_root_path():
    kaynak_txt = os.path.join(get_config_path(), "video_kaynak.txt")
    content = read_file_content(kaynak_txt)
    if content and os.path.isdir(content):
        return content
    return r"C:\Users\User\Desktop\Otomasyon\Video\Video"


def get_video_files():
    video_root = get_video_root_path()
    valid_extensions = (".mp4", ".mov", ".avi", ".mkv", ".webm")

    if not os.path.isdir(video_root):
        return []

    files = []
    try:
        entries = os.listdir(video_root)
        subdirs = sorted(
            [os.path.join(video_root, e) for e in entries if os.path.isdir(os.path.join(video_root, e))],
            key=natural_sort_key,
        )

        if subdirs:
            for subdir in subdirs:
                try:
                    for file_name in sorted(os.listdir(subdir), key=natural_sort_key):
                        if file_name.lower().endswith(valid_extensions):
                            files.append(os.path.join(subdir, file_name))
                except Exception:
                    continue
            return files

        for file_name in entries:
            if file_name.lower().endswith(valid_extensions):
                files.append(os.path.join(video_root, file_name))
    except Exception:
        return []
    return sorted(files, key=natural_sort_key)


def parse_account_line(line):
    raw = str(line or "").strip()
    if not raw:
        return None

    # Pipe-separated extended format: "API Token: xxx | Seçili: Evet | Ad: HesapAdı"
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|")]
        token_value = ""
        email_value = ""
        password_value = ""
        selected = True  # Varsayılan: seçili
        for part in parts:
            part_low = part.casefold()
            if part_low.startswith(("api token:", "token:", "api_token:", "buffer_token:")):
                token_value = part.split(":", 1)[1].strip()
            elif part_low.startswith(("se\u00e7ili:", "secili:", "selected:")):
                val = part.split(":", 1)[1].strip().casefold()
                selected = val in ("evet", "yes", "true", "1", "+", "a\u00e7\u0131k", "acik", "on")
            elif part_low.startswith(("ad:", "name:", "hesap ad\u0131:", "hesap adi:")):
                email_value = part.split(":", 1)[1].strip()
            elif part_low.startswith(("email:",)):
                email_value = part.split(":", 1)[1].strip()
            elif part_low.startswith(("password:", "\u015fifre:", "sifre:")):
                password_value = part.split(":", 1)[1].strip()
        if token_value:
            return {"token": token_value, "email": email_value, "password": "", "selected": selected}
        if email_value and password_value:
            return {"email": email_value, "password": password_value, "token": "", "selected": selected}
        return None

    if "," not in raw or len(raw) > 100:
        return {"token": raw, "email": "", "password": "", "selected": True}
    email, password = raw.split(",", 1)
    email = email.strip()
    password = password.strip()
    if not email or not password:
        return None
    return {"email": email, "password": password, "token": "", "selected": True}


def parse_account_config(raw_text):
    cfg = {"mode": "single", "loop_accounts": False, "accounts": [], "raw": str(raw_text or "")}
    raw = str(raw_text or "").strip()
    if not raw:
        return cfg

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    mode = None
    loop_accounts = False
    accounts = []

    for line in lines:
        low = line.casefold()
        if low.startswith(("hesap modu:", "mod:", "mode:")):
            mode = "bulk" if any(k in low for k in ("toplu", "bulk", "çoklu", "coklu")) else "single"
            continue
        if low.startswith(("hesap döngü:", "hesap dongu:", "döngü:", "dongu:", "loop:")):
            loop_accounts = any(k in low for k in ("evet", "açık", "acik", "on", "true", "1", "+"))
            continue
        if low.startswith(("hesaplar", "accounts")):
            continue
        # Eski format: "API Token: xxx" (pipe içermeyen)
        if low.startswith(("api token:", "token:", "api_token:", "buffer_token:")) and "|" not in line:
            token_value = line.split(":", 1)[1].strip()
            if token_value:
                accounts.append({"token": token_value, "email": "", "password": "", "selected": True})
            continue
        parsed = parse_account_line(line)
        if parsed:
            accounts.append(parsed)

    if not accounts:
        legacy = parse_account_line(raw)
        if legacy:
            accounts = [legacy]

    if mode is None:
        mode = "bulk" if len(accounts) > 1 else "single"

    cfg["mode"] = mode
    cfg["loop_accounts"] = bool(loop_accounts)
    # Her hesabın selected bilgisini koru (yoksa varsayılan True)
    for acc in accounts:
        if "selected" not in acc:
            acc["selected"] = True
    cfg["accounts"] = accounts
    return cfg


def load_account_config():
    path = os.path.join(get_config_path(), "hesap.txt")
    raw = read_file_content(path) or ""
    return parse_account_config(raw)


def get_api_token_from_account(account):
    """Hesap bilgisinden API token'ı çıkarır."""
    token = str(account.get("token", "") or "").strip()
    if token:
        return token
    password = str(account.get("password", "") or "").strip()
    return password


PUBLISH_NOW_MARKER = "__HEMEN_PAYLAS__"


def normalize_publish_mode(value):
    raw = str(value or "").strip().lower()
    if raw in {
        "hemen paylaş", "hemen paylas", "şimdi paylaş", "simdi paylaş", "simdi paylas", "şimdi paylas",
        "hemen", "simdi", "şimdi", "now", "publish_now", "publish-now", "immediate", "direct",
        PUBLISH_NOW_MARKER.lower(), "hemen_paylas", "simdi_paylas"
    }:
        return "publish_now"
    return "schedule"


def parse_schedule_text(raw_text):
    raw = str(raw_text or "").strip()
    if not raw:
        return "", ""
    if normalize_publish_mode(raw) == "publish_now":
        return "", ""
    if "," in raw:
        gun, saat = raw.split(",", 1)
        return gun.strip(), saat.strip()
    return "", raw.strip()


def parse_numbered_blocks(raw_text):
    raw = str(raw_text or "").strip()
    if not re.search(r"(?im)^###\s*Video\s+\d+\s*$", raw):
        return {}
    pattern = re.compile(r"(?im)^###\s*Video\s+(\d+)\s*$")
    matches = list(pattern.finditer(raw))
    out = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        out[int(match.group(1))] = raw[start:end].strip()
    return out


def parse_platform_block(raw_text):
    out = {"youtube": False, "tiktok": False, "instagram": False}
    selected = True  # Varsayılan: seçili
    for line in str(raw_text or "").splitlines():
        low = line.strip().lower()
        if low.startswith(("se\u00e7ili:", "secili:", "selected:")):
            val = line.split(":", 1)[1].strip().lower()
            selected = val in ("evet", "yes", "true", "1", "+", "a\u00e7\u0131k", "acik", "on")
        elif "youtube" in low:
            out["youtube"] = "+" in line
        elif "tiktok" in low:
            out["tiktok"] = "+" in line
        elif "instagram" in low:
            out["instagram"] = "+" in line
    out["_selected"] = selected
    return out


def check_platform_active(platform_name):
    path = os.path.join(get_config_path(), "paylasılacak_sosyal_medyalar.txt")
    content = read_file_content(path)
    if not content:
        return False
    lines = content.split("\n")
    for line in lines:
        if platform_name.lower() in line.lower() and "+" in line:
            return True
    return False


def get_selected_platforms():
    return [name for name in PLATFORM_ORDER if check_platform_active(name)]


def get_selected_platforms_from_flags(secimler):
    secimler = dict(secimler or {})
    return [name for name in PLATFORM_ORDER if bool(secimler.get(PLATFORM_KEY_MAP[name]))]


def get_runtime_config_paths():
    base = get_config_path()
    return {
        "baslik": os.path.join(base, "başlık.txt"),
        "aciklama": os.path.join(base, "açıklama.txt"),
        "platform": os.path.join(base, "paylasılacak_sosyal_medyalar.txt"),
        "zamanlama": os.path.join(base, "paylaşım_zamanlama.txt"),
    }


def get_publish_mode_from_schedule_raw(raw_text):
    raw = str(raw_text or "").strip()
    if not raw:
        return "schedule"
    return normalize_publish_mode(raw)


def load_social_media_config():
    paths = get_runtime_config_paths()
    baslik_raw = read_file_content(paths["baslik"]) or ""
    aciklama_raw = read_file_content(paths["aciklama"]) or ""
    platform_raw = read_file_content(paths["platform"]) or ""
    zamanlama_raw = read_file_content(paths["zamanlama"]) or ""

    baslik_blocks = parse_numbered_blocks(baslik_raw)
    aciklama_blocks = parse_numbered_blocks(aciklama_raw)
    platform_blocks = parse_numbered_blocks(platform_raw)
    zamanlama_blocks = parse_numbered_blocks(zamanlama_raw)

    has_per_item = any([baslik_blocks, aciklama_blocks, platform_blocks, zamanlama_blocks])
    if not has_per_item:
        gun, saat = parse_schedule_text(zamanlama_raw)
        _global_plat = parse_platform_block(platform_raw)
        _global_plat.pop("_selected", None)  # global modda selected kullanılmaz
        return {
            "mode": "global",
            "global": {
                "baslik": baslik_raw,
                "aciklama": aciklama_raw,
                "secimler": _global_plat,
                "publish_mode": get_publish_mode_from_schedule_raw(zamanlama_raw),
                "gun": gun,
                "saat": saat,
            },
            "items": {},
        }

    nums = set()
    nums.update(baslik_blocks.keys())
    nums.update(aciklama_blocks.keys())
    nums.update(platform_blocks.keys())
    nums.update(zamanlama_blocks.keys())

    items = {}
    for no in sorted(nums):
        raw_schedule = zamanlama_blocks.get(no, "")
        gun, saat = parse_schedule_text(raw_schedule)
        _plat_parsed = parse_platform_block(platform_blocks.get(no, ""))
        _item_selected = _plat_parsed.pop("_selected", True)
        items[no] = {
            "baslik": baslik_blocks.get(no, ""),
            "aciklama": aciklama_blocks.get(no, ""),
            "secimler": _plat_parsed,
            "publish_mode": get_publish_mode_from_schedule_raw(raw_schedule),
            "gun": gun,
            "saat": saat,
            "selected": _item_selected,
        }

    return {
        "mode": "per_item",
        "global": {},
        "items": items,
    }


def build_video_number_map(video_files):
    number_map = {}
    for idx, path in enumerate(video_files, start=1):
        candidates = [
            os.path.basename(os.path.dirname(path)),
            os.path.splitext(os.path.basename(path))[0],
        ]
        found_no = None
        for text in candidates:
            m = re.search(r"(\d+)\s*$", str(text or ""))
            if m:
                found_no = int(m.group(1))
                break
        if found_no is None:
            found_no = idx
        number_map.setdefault(found_no, path)
    return number_map


def resolve_video_path(item_no, video_files, number_map):
    item_no = int(item_no)
    if item_no in number_map:
        return number_map[item_no]
    if 1 <= item_no <= len(video_files):
        return video_files[item_no - 1]
    return None


def build_item_jobs():
    cfg = load_social_media_config()
    video_files = get_video_files()
    number_map = build_video_number_map(video_files)
    jobs = []

    if cfg.get("mode") == "per_item":
        _skipped_unselected = []
        for item_no in sorted((cfg.get("items") or {}).keys()):
            settings = dict(cfg["items"].get(item_no) or {})
            # Seçili olmayan videoları atla
            if not settings.get("selected", True):
                _skipped_unselected.append(item_no)
                continue
            jobs.append({
                "item_no": item_no,
                "video_no": item_no,
                "video_label": f"Video {item_no}",
                "video_path": resolve_video_path(item_no, video_files, number_map),
                "settings": settings,
                "platforms": get_selected_platforms_from_flags(settings.get("secimler") or {}),
            })
        if _skipped_unselected:
            print(f"[INFO] Se\u00e7ili olmayan videolar atland\u0131: {', '.join(f'Video {n}' for n in _skipped_unselected)}")
    else:
        global_settings = dict(cfg.get("global") or {})
        global_platforms = get_selected_platforms_from_flags(global_settings.get("secimler") or {})
        for idx, path in enumerate(video_files, start=1):
            jobs.append({
                "item_no": idx,
                "video_no": idx,
                "video_label": f"Video {idx}",
                "video_path": path,
                "settings": dict(global_settings),
                "platforms": list(global_platforms),
            })

    return jobs


def assign_accounts_to_jobs(jobs, account_cfg):
    mode = str((account_cfg or {}).get("mode", "single") or "single").strip().lower()
    raw_accounts = list((account_cfg or {}).get("accounts") or [])
    loop_accounts = bool((account_cfg or {}).get("loop_accounts", False))
    assigned = []
    skipped_jobs = []

    if not raw_accounts:
        return assigned, skipped_jobs

    all_accounts = []
    for original_index, account in enumerate(raw_accounts, start=1):
        acc = dict(account or {})
        acc["_source_index"] = original_index
        all_accounts.append(acc)

    # Toplu hesap modunda: seçili hesapları filtrele
    if mode == "bulk":
        selected_accounts = [acc for acc in all_accounts if acc.get("selected", True)]
        # Hiçbiri seçili değilse tüm hesapları kullan (geriye uyumluluk)
        if not selected_accounts:
            selected_accounts = all_accounts
        accounts = selected_accounts
        secili_sayisi = len(accounts)
        toplam_sayisi = len(all_accounts)
        if secili_sayisi < toplam_sayisi:
            print(f"[INFO] Seçili hesap sayısı: {secili_sayisi}/{toplam_sayisi} (yalnızca seçili hesaplarda paylaşım yapılacak)")
        else:
            print(f"[INFO] Tüm hesaplar seçili: {toplam_sayisi}")
    else:
        accounts = all_accounts

    fanout_all_accounts = mode == "bulk" and not loop_accounts and len(accounts) > 1

    if fanout_all_accounts:
        print(f"[INFO] Toplu hesap paylaşımı: Her video {len(accounts)} seçili hesapta ayrı ayrı paylaşılacak.")
        for job in jobs:
            for account in accounts:
                item = dict(job)
                item["account"] = account
                item["account_index"] = int(account.get("_source_index") or 0) or 1
                item["use_account_suffix"] = True
                assigned.append(item)
        return assigned, skipped_jobs

    if mode == "bulk" and loop_accounts and accounts:
        print(f"[INFO] Toplu hesap paylaşımı: Videolar seçili hesaplara sırayla dağıtılacak (döngü açık).")

    for idx, job in enumerate(jobs):
        if mode == "bulk":
            if idx < len(accounts):
                account = accounts[idx]
            elif loop_accounts and accounts:
                account = accounts[idx % len(accounts)]
            else:
                skipped_jobs.append(job)
                continue
        else:
            account = accounts[0]

        item = dict(job)
        item["account"] = account
        item["account_index"] = int(account.get("_source_index") or 0) or ((idx % len(accounts)) + 1 if mode == "bulk" and accounts else 1)
        item["use_account_suffix"] = False
        assigned.append(item)

    return assigned, skipped_jobs


def get_account_slot_label(account=None, fallback_index=None):
    account = dict(account or {})
    raw_index = account.get("_source_index") or fallback_index or account.get("account_index")
    try:
        index = int(raw_index)
    except Exception:
        index = 0
    return f"Hesap {index}" if index > 0 else "Hesap"


def get_account_display_label(account=None, fallback_index=None):
    base_label = get_account_slot_label(account, fallback_index)
    account_name = str((account or {}).get("email", "") or "").strip()
    if account_name:
        return f"{base_label}: {account_name}"
    return base_label


def get_job_account_slot(job):
    if not bool((job or {}).get("use_account_suffix")):
        return ""
    return get_account_slot_label((job or {}).get("account"), (job or {}).get("account_index"))


def get_job_account_display(job):
    if not bool((job or {}).get("use_account_suffix")):
        return ""
    return get_account_display_label((job or {}).get("account"), (job or {}).get("account_index"))


def build_task_key(video_no, platform_name, account_slot=""):
    parts = [f"Video {int(video_no)}", str(platform_name or "").strip()]
    account_slot = str(account_slot or "").strip()
    if account_slot:
        parts.append(account_slot)
    return "::".join(parts)


def build_task_key_for_job(job, platform_name):
    return build_task_key(job.get("video_no"), platform_name, get_job_account_slot(job))


def task_key_to_label(task_key):
    text = str(task_key or "").strip()
    if "::" not in text:
        return text
    parts = text.split("::")
    item_label = parts[0].strip()
    platform_name = parts[1].strip() if len(parts) > 1 else ""
    account_slot = parts[2].strip() if len(parts) > 2 else ""
    if account_slot:
        return f"{item_label} ({account_slot}) - {platform_name}"
    return f"{item_label} - {platform_name}"


# ============================================================
# ZAMANLAMA HESAPLAMA
# ============================================================

# Türkiye saat dilimi ofseti (UTC+3)
_TURKEY_UTC_OFFSET = datetime.timedelta(hours=3)


def compute_due_at(gun, saat):
    """Gün ve saat bilgisinden ISO 8601 UTC tarih oluşturur.

    Kullanıcı Türkiye saati (UTC+3) girer.  Buffer API 'Z' sonekli
    tarihleri UTC olarak yorumlar, bu yüzden yerel saati UTC'ye
    çevirmemiz gerekir.  Örnek: 14:00 TR → 11:00 UTC.

    Eğer belirlenen zaman geçmişte kalmışsa PastScheduleError fırlatır.
    Böylece geçmiş zamanlı paylaşımlar sessizce başarılı gösterilmez,
    kullanıcı uyarılır ve düzeltme şansı verilir.
    """
    if not gun and not saat:
        return None

    # Türkiye yerel zamanını hesapla (karşılaştırma için)
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    now_local = now_utc + _TURKEY_UTC_OFFSET

    try:
        gun_no = int(gun) if gun else now_local.day
    except ValueError:
        gun_no = now_local.day

    hour = 12
    minute = 0
    if saat:
        saat = saat.strip()
        try:
            saat_obj = datetime.datetime.strptime(saat, "%I:%M %p")
            hour = saat_obj.hour
            minute = saat_obj.minute
        except ValueError:
            try:
                saat_obj = datetime.datetime.strptime(saat, "%H:%M")
                hour = saat_obj.hour
                minute = saat_obj.minute
            except ValueError:
                pass

    # Hedef zamanı Türkiye yerel saatinde oluştur
    try:
        target_local = now_local.replace(day=gun_no, hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return None

    # --- GEÇMİŞ ZAMAN KONTROLÜ ---
    # Hedef zaman geçmişte ise paylaşımı ENGELLE ve hata fırlat.
    # Eski davranış: sessizce sonraki aya atıyordu ve Buffer API
    # geçmiş tarihi kabul edip başarılı gösteriyordu.
    if target_local <= now_local:
        gecen_sure = now_local - target_local
        gecen_dk = int(gecen_sure.total_seconds() // 60)
        hedef_str = f"{gun_no:02d}/{now_local.month:02d} {hour:02d}:{minute:02d}"
        simdi_str = f"{now_local.day:02d}/{now_local.month:02d} {now_local.hour:02d}:{now_local.minute:02d}"
        print(f"[ERROR] Geçmiş tarih tespit edildi!")
        print(f"[ERROR] Hedef zaman: {hedef_str} TR | Şu an: {simdi_str} TR | Geçen süre: {gecen_dk} dakika")
        print(f"[ERROR] Geçmiş zamana paylaşım yapılamaz. Lütfen zamanlama ayarlarını düzeltin.")
        raise PastScheduleError(
            f"Geçmiş tarih seçildi: {hedef_str} TR (geçen süre: {gecen_dk} dk). "
            f"Şu anki saat: {simdi_str} TR. Lütfen zamanlama ayarlarını güncelleyin."
        )

    # Türkiye yerel saatini UTC'ye çevir (UTC+3 → UTC: 3 saat çıkar)
    target_utc = target_local - _TURKEY_UTC_OFFSET
    print(f"[INFO] Zamanlama: {hour:02d}:{minute:02d} TR (UTC+3) → {target_utc.strftime('%H:%M')} UTC")
    return target_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def is_schedule_in_past(gun, saat):
    if not gun:
        return False
    try:
        gun_no = int(gun)
        now = datetime.datetime.now()
        if gun_no < now.day:
            return True
        if gun_no == now.day and saat:
            try:
                saat_obj = datetime.datetime.strptime(saat.strip(), "%I:%M %p")
                saat_bugun = now.replace(
                    hour=saat_obj.hour, minute=saat_obj.minute,
                    second=0, microsecond=0
                )
                return saat_bugun <= now.replace(second=0, microsecond=0)
            except Exception:
                return False
        return False
    except Exception:
        return False


# ============================================================
# HATA MESAJI DÖNÜŞTÜRÜCÜ
# ============================================================

_ERROR_PATTERNS = [
    (r'rate.?limit|429|too many', "Rate limit aşıldı"),
    (r'zero content.?length', "Video URL Content-Length hatası (servis uyumsuz)"),
    (r'unsupported content.?type', "Video URL Content-Type hatası (video/mp4 değil)"),
    (r'video.*url.*invalid|video.*erişilemedi|video.*validation.*timed', "Video URL'si erişilemedi"),
    (r'video.*url.*returned', "Video URL doğrulama hatası"),
    (r'video.*url.*not.*accessible|unable to co', "Video URL erişim hatası (servis erişilemedi)"),
    (r'publicly accessible', "Video URL herkese açık değil"),
    (r'platform tarafından reddedildi', "Platform video'yu reddetti (format/URL sorunu)"),
    (r'attached media.*issue|media.*link.*attachment', "Medya eki sorunu (TikTok format/boyut)"),
    (r'Invalid post.*require', "Geçersiz gönderi - eksik zorunlu alan"),
    (r'Invalid post', "Geçersiz gönderi formatı"),
    (r'require.*title', "Başlık zorunlu"),
    (r'require.*category', "Kategori zorunlu"),
    (r'require.*type', "Gönderi tipi zorunlu"),
    (r'require.*video', "Video zorunlu"),
    (r'require.*image', "Görsel/video zorunlu"),
    (r'token.*invalid|unauthorized|401', "API Token geçersiz"),
    (r'UNAUTHENTICATED|Access token is not valid', "API Token geçersiz"),
    (r'channel.*not.*found|kanal.*bulunamad', "Kanal bulunamadı"),
    (r'organization.*not.*found', "Organizasyon bulunamadı"),
    (r'timeout|zaman.*aşım', "Zaman aşımı"),
    (r'connection.*error|bağlantı.*hata', "Bağlantı hatası"),
    (r'graphql.*hata|mutation.*error', "API sorgu hatası"),
    (r'limit.*reached|limit.*aşıldı', "Paylaşım limiti aşıldı"),
    (r'hesap.*bilgi.*eksik', "Hesap bilgisi eksik"),
    (r'ge[çc]mi[şs]\s*tarih', "Geçmiş tarih seçildi"),
    (r'video.*bulunamad', "Video dosyası bulunamadı"),
    (r'video.*yüklenemedi', "Video yüklenemedi"),
]


def sanitize_detail(text):
    raw = str(text or "").strip()
    if not raw:
        return "Başarısız"

    if len(raw) <= 50 and "\n" not in raw:
        return raw

    for pattern, short_msg in _ERROR_PATTERNS:
        if re.search(pattern, raw, re.IGNORECASE):
            return short_msg

    first_line = raw.split("\n")[0].strip()
    if len(first_line) > 60:
        first_line = first_line[:57] + "..."
    return first_line if first_line else "Başarısız"


# ============================================================
# PAYLAŞIM MODU HESAPLAMA (Ortak)
# ============================================================

def compute_share_mode(settings):
    """Paylaşım modu ve zamanlama bilgisini hesaplar.

    PastScheduleError fırlatılabilir — geçmiş zamanlı zamanlama
    tespit edildiğinde çağıran fonksiyon bunu yakalamalıdır.
    """
    publish_mode = normalize_publish_mode((settings or {}).get("publish_mode", "schedule"))
    gun = str((settings or {}).get("gun", "") or "").strip()
    saat = str((settings or {}).get("saat", "") or "").strip()

    if publish_mode == "publish_now":
        print("[INFO] Paylaşım modu: Hemen Paylaş")
        return "shareNow", None

    # compute_due_at geçmiş tarih tespit ederse PastScheduleError fırlatır.
    # Bu hatayı yukarı iletiyoruz ki platform işlemcileri yakalasın.
    due_at = compute_due_at(gun, saat)
    if due_at:
        print(f"[INFO] Paylaşım modu: Zamanla ({due_at})")
        return "customScheduled", due_at

    print("[INFO] Zamanlama bilgisi bulunamadı, Hemen Paylaş olarak devam ediliyor.")
    return "shareNow", None


# ============================================================
# PLATFORM İŞLEMCİLERİ (Buffer API)
# ============================================================

def process_youtube(client, video_path, video_url, settings):
    """YouTube platformu için gönderi oluşturur."""
    print("\n--- YOUTUBE İŞLEMİ BAŞLIYOR ---")
    try:
        check_flag_state()

        channel = client.get_channel_by_service("youtube")
        if not channel:
            return False, "YouTube kanalı bulunamadı. Buffer hesabınıza YouTube kanalı bağlayın."

        channel_id = channel["id"]
        channel_name = channel.get("displayName") or channel.get("name", "YouTube")
        print(f"[INFO] YouTube kanalı: {channel_name}")

        if channel.get("isQueuePaused"):
            print(f"[WARN] YouTube kanalı kuyruğu duraklatılmış: {channel_name}")

        title_text = str((settings or {}).get("baslik", "") or "").strip()
        description_text = str((settings or {}).get("aciklama", "") or "").strip()
        yt_title = title_text if title_text else os.path.splitext(os.path.basename(video_path))[0]
        post_text = description_text if description_text else ""

        if not video_url:
            return False, "Video URL'si oluşturulamadı. Video dosyası yüklenemedi."

        mode, due_at = compute_share_mode(settings)
        check_flag_state()

        metadata = {
            "youtube": {
                "title": yt_title,
                "categoryId": DEFAULT_YOUTUBE_CATEGORY_ID,
                "privacy": "public",
                "madeForKids": False,
            }
        }

        assets = {"videos": [{"url": video_url}]}

        post = client.create_post(
            channel_id=channel_id,
            text=post_text,
            mode=mode,
            due_at=due_at,
            assets=assets,
            metadata=metadata,
        )

        post_id = post.get("id", "N/A")
        print(f">>> YOUTUBE PAYLAŞIM BAŞARILI! Post ID: {post_id} <<<")
        return True, ""

    except StopRequested:
        raise
    except PastScheduleError as e:
        print(f">>> YOUTUBE PAYLAŞIM BAŞARISIZ! Geçmiş tarih. <<<")
        return False, sanitize_detail(str(e))
    except BufferAPIError as e:
        return False, sanitize_detail(str(e))
    except Exception as e:
        return False, sanitize_detail(str(e))


def process_tiktok(client, video_path, video_url, settings):
    """TikTok platformu için gönderi oluşturur."""
    print("\n--- TIKTOK İŞLEMİ BAŞLIYOR ---")
    try:
        check_flag_state()

        channel = client.get_channel_by_service("tiktok")
        if not channel:
            return False, "TikTok kanalı bulunamadı. Buffer hesabınıza TikTok kanalı bağlayın."

        channel_id = channel["id"]
        channel_name = channel.get("displayName") or channel.get("name", "TikTok")
        print(f"[INFO] TikTok kanalı: {channel_name}")

        title_text = str((settings or {}).get("baslik", "") or "").strip()
        description_text = str((settings or {}).get("aciklama", "") or "").strip()
        caption_text = title_text or description_text
        if not caption_text:
            caption_text = os.path.splitext(os.path.basename(video_path))[0]

        if not video_url:
            return False, "Video URL'si oluşturulamadı. Video dosyası yüklenemedi."

        # TikTok için video URL erişilebilirliğini tekrar doğrula
        if not VideoUploader._verify_url_accessible(video_url):
            print(f"[WARN] Video URL erişilebilir değil, yeniden yükleniyor...")
            VideoUploader.invalidate_cache(video_path)
            new_url = resolve_video_url(video_path, force_new=True)
            if new_url:
                video_url = new_url
            else:
                return False, "Video URL yeniden oluşturulamadı. TikTok için erişilebilir URL gerekli."

        mode, due_at = compute_share_mode(settings)
        check_flag_state()

        metadata = {"tiktok": {"title": caption_text}}
        assets = {"videos": [{"url": video_url}]}

        # TikTok paylaşımı öncesi kısa bekleme
        print(f"[INFO] TikTok video işleme bekleniyor ({POST_UPLOAD_DELAY}s)...")
        controlled_sleep(POST_UPLOAD_DELAY)

        post = client.create_post(
            channel_id=channel_id,
            text=caption_text,
            mode=mode,
            due_at=due_at,
            assets=assets,
            metadata=metadata,
        )

        post_id = post.get("id", "N/A")
        print(f">>> TIKTOK PAYLAŞIM BAŞARILI! Post ID: {post_id} <<<")
        return True, ""

    except StopRequested:
        raise
    except PastScheduleError as e:
        print(f">>> TIKTOK PAYLAŞIM BAŞARISIZ! Geçmiş tarih. <<<")
        return False, sanitize_detail(str(e))
    except BufferAPIError as e:
        return False, sanitize_detail(str(e))
    except Exception as e:
        return False, sanitize_detail(str(e))


def process_instagram(client, video_path, video_url, settings):
    """Instagram platformu için gönderi oluşturur."""
    print("\n--- INSTAGRAM İŞLEMİ BAŞLIYOR ---")
    try:
        check_flag_state()

        channel = client.get_channel_by_service("instagram")
        if not channel:
            return False, "Instagram kanalı bulunamadı. Buffer hesabınıza Instagram kanalı bağlayın."

        channel_id = channel["id"]
        channel_name = channel.get("displayName") or channel.get("name", "Instagram")
        print(f"[INFO] Instagram kanalı: {channel_name}")

        title_text = str((settings or {}).get("baslik", "") or "").strip()
        description_text = str((settings or {}).get("aciklama", "") or "").strip()
        caption_text = title_text or description_text
        if not caption_text:
            caption_text = os.path.splitext(os.path.basename(video_path))[0]

        if not video_url:
            return False, "Video URL'si oluşturulamadı. Video dosyası yüklenemedi."

        mode, due_at = compute_share_mode(settings)
        check_flag_state()

        metadata = {
            "instagram": {
                "type": "reel",
                "shouldShareToFeed": True,
            }
        }

        assets = {"videos": [{"url": video_url}]}

        post = client.create_post(
            channel_id=channel_id,
            text=caption_text,
            mode=mode,
            due_at=due_at,
            assets=assets,
            metadata=metadata,
        )

        post_id = post.get("id", "N/A")
        print(f">>> INSTAGRAM PAYLAŞIM BAŞARILI! Post ID: {post_id} <<<")
        return True, ""

    except StopRequested:
        raise
    except PastScheduleError as e:
        print(f">>> INSTAGRAM PAYLAŞIM BAŞARISIZ! Geçmiş tarih. <<<")
        return False, sanitize_detail(str(e))
    except BufferAPIError as e:
        return False, sanitize_detail(str(e))
    except Exception as e:
        return False, sanitize_detail(str(e))


# ============================================================
# ÖZET YAZDIRMA
# ============================================================

def print_summary(success_list, failed_map, skipped_list, already_done_list=None):
    """v4: Özet yazdırma — 'zaten tamamlandı' ayrı kategori olarak gösteriliyor.

    v6: Öğe ayırıcısı ' | ' olarak değiştirildi.
    Eski ' - ' ayırıcısı 'Video 1 - Youtube' gibi task_label'larla
    çakışıyordu ve app.py tarafında parse hatalarına yol açıyordu.
    """
    already_done_list = already_done_list or []

    ok_line = " | ".join(success_list) if success_list else "Yok"
    fail_line = " | ".join([f"{k} ({v})" for k, v in failed_map.items()]) if failed_map else "Yok"
    skip_line = " | ".join(skipped_list) if skipped_list else "Yok"
    done_line = " | ".join(already_done_list) if already_done_list else ""

    print("=" * 60)
    print(f"Başarılı: {len(success_list)} - {ok_line}")
    print(f"Başarısız: {len(failed_map)} - {fail_line}")

    if already_done_list:
        print(f"Önceden Tamamlanmış: {len(already_done_list)} - {done_line}")
        if skipped_list:
            print(f"Atlandı: {len(skipped_list)} - {skip_line}")
    else:
        print(f"Atlandı: {len(skipped_list)} - {skip_line}")

    total_ok = len(success_list) + len(already_done_list)
    total_all = total_ok + len(failed_map)
    if total_ok > 0 and not failed_map:
        print("TÜM İŞLEMLER TAMAMLANDI")


def prepare_resume_state(active_task_keys):
    state = load_resume_state()
    done_set = [p for p in state.get("done_platforms", []) if p in active_task_keys]
    failed_map = {k: v for k, v in state.get("failed_platforms", {}).items() if k in active_task_keys}
    state["active_platforms"] = list(active_task_keys)
    state["done_platforms"] = done_set
    state["failed_platforms"] = failed_map
    save_resume_state(state)
    return state


# ============================================================
# ANA BOT FONKSİYONU
# ============================================================

def start_bot():
    success_list = []
    failed_map = {}
    skipped_list = []
    already_done_list = []  # v4: Önceden tamamlanmış işlemler ayrı listede

    try:
        check_flag_state()

        # ── Hesap bilgilerini yükle ──
        account_cfg = load_account_config()
        accounts = list(account_cfg.get("accounts") or [])
        if not accounts:
            print("HATA: hesap.txt okunamadı veya geçerli hesap bulunamadı.")
            print("[INFO] Buffer API Token'ınızı hesap.txt dosyasına ekleyin.")
            print("[INFO] Format: API Token: YOUR_TOKEN_HERE")
            print_summary(success_list, failed_map, skipped_list, already_done_list)
            return 0

        # ── İş öğelerini oluştur ──
        jobs = build_item_jobs()
        if not jobs:
            print(f"HATA: Video dosyası bulunamadı! Kontrol edilen klasör: {get_video_root_path()}")
            print_summary(success_list, failed_map, skipped_list, already_done_list)
            return 0

        secili_platform_sayisi = sum(len(job.get("platforms") or []) for job in jobs)
        if secili_platform_sayisi <= 0:
            print("HATA: Paylaşım için seçili sosyal medya platformu bulunamadı.")
            print_summary(success_list, failed_map, skipped_list, already_done_list)
            return 0

        # ── Hesapları işlere ata ──
        assigned_jobs, skipped_jobs = assign_accounts_to_jobs(jobs, account_cfg)
        for job in skipped_jobs:
            skipped_list.append(f"{job.get('video_label', 'Video')} (hesap atanamadı)")

        if not assigned_jobs:
            print("HATA: Paylaşım yapılabilecek atanmış hesap bulunamadı.")
            print_summary(success_list, failed_map, skipped_list, already_done_list)
            return 0

        # ── Resume state hazırla ──
        runnable_task_keys = []
        for job in assigned_jobs:
            if not job.get("video_path"):
                continue
            for platform_name in job.get("platforms", []):
                runnable_task_keys.append(build_task_key_for_job(job, platform_name))

        state = prepare_resume_state(runnable_task_keys)
        done_set = set(state.get("done_platforms", []))
        failed_map.update({
            task_key_to_label(k): sanitize_detail(v)
            for k, v in state.get("failed_platforms", {}).items()
            if k not in done_set
        })

        # ── Bilgi yazdır ──
        print(f"[INFO] Hesap modu: {'Toplu Hesap' if account_cfg.get('mode') == 'bulk' else 'Tek Hesap'}")
        print(f"[INFO] Geçerli hesap sayısı: {len(accounts)}")
        if account_cfg.get("mode") == "bulk":
            print(f"[INFO] Hesap döngüsü: {'Açık' if account_cfg.get('loop_accounts') else 'Kapalı'}")
        print(f"[INFO] Toplam iş öğesi sayısı: {len(jobs)}")
        print(f"[INFO] Toplam atanmış paylaşım görevi: {len(assigned_jobs)}")
        print(f"[INFO] Paylaşım yöntemi: Buffer API (GraphQL)")

        cfg = load_social_media_config()
        print(f"[INFO] Sosyal medya ayar modu: {'Video/Link Bazlı' if cfg.get('mode') == 'per_item' else 'Genel'}")
        if skipped_jobs:
            print(f"[WARN] Hesap atanamayan video sayısı: {len(skipped_jobs)}")

        # v4: Önceden tamamlanmış işlemleri başlangıçta bildir
        if done_set:
            done_labels = [task_key_to_label(k) for k in sorted(done_set)]
            print(f"\n[INFO] Önceden tamamlanmış {len(done_set)} işlem tespit edildi:")
            for label in done_labels:
                print(f"  [SKIP] {label} (daha önce başarıyla paylaşıldı)")
            print(f"[INFO] Bu işlemler tekrar yapılmayacak (spam koruması).")
            print(f"[INFO] Sıfırlamak için Durum Özeti > Sıfırla butonunu kullanın.\n")

        # ── Platform işlemcileri ──
        handlers = {
            "Youtube": process_youtube,
            "Tiktok": process_tiktok,
            "Instagram": process_instagram,
        }

        # ── API istemci önbelleği (hesap başına) ──
        api_clients = {}
        current_token = ""
        last_video_identity = None

        for job in assigned_jobs:
            check_flag_state()
            account = dict(job.get("account") or {})
            api_token = get_api_token_from_account(account)
            video_label = job.get("video_label", "Video")
            account_log_label = get_job_account_display(job)
            video_path = job.get("video_path")
            settings = dict(job.get("settings") or {})
            pending_platforms = []
            already_done = []

            if not video_path or not os.path.exists(video_path):
                skipped_list.append(f"{video_label} (video bulunamadı)")
                continue

            if not job.get("platforms"):
                skipped_list.append(f"{video_label} (platform seçilmedi)")
                continue

            if not api_token:
                for platform_name in job.get("platforms", []):
                    task_key = build_task_key_for_job(job, platform_name)
                    failed_map[task_key_to_label(task_key)] = "API Token eksik"
                continue

            for platform_name in job.get("platforms", []):
                task_key = build_task_key_for_job(job, platform_name)
                if task_key in done_set:
                    already_done.append(platform_name)
                else:
                    pending_platforms.append(platform_name)

            # v4: "Zaten tamamlandı" bilgisini ayrı listeye ekle (skipped_list yerine)
            for platform_name in already_done:
                already_done_list.append(task_key_to_label(build_task_key_for_job(job, platform_name)))

            if not pending_platforms:
                # v4: Tüm platformlar zaten tamamlanmışsa bilgi ver
                if already_done:
                    skip_target = f"{video_label} ({account_log_label})" if account_log_label else video_label
                    print(f"[SKIP] {skip_target}: Tüm platformlar daha önce tamamlanmış, atlanıyor.")
                continue

            # Çoklu video paylaşımında videolar arası bekleme süresi
            current_video_identity = os.path.abspath(video_path)
            if last_video_identity and current_video_identity != last_video_identity:
                print(f"\n[INFO] Sonraki video için {INTER_VIDEO_DELAY}s bekleniyor...")
                controlled_sleep(INTER_VIDEO_DELAY)

            # ── API istemcisi oluştur veya önbellekten al ──
            if api_token != current_token:
                if api_token not in api_clients:
                    if account_log_label:
                        print(f"\n[INFO] Buffer API bağlantısı kuruluyor... ({account_log_label})")
                    else:
                        print(f"\n[INFO] Buffer API bağlantısı kuruluyor...")
                    client = BufferAPIClient(api_token)
                    if not client.verify_token():
                        for platform_name in pending_platforms:
                            task_key = build_task_key_for_job(job, platform_name)
                            task_label = task_key_to_label(task_key)
                            failed_map[task_label] = "API Token geçersiz"
                            update_resume_state(task_key, False, "API Token geçersiz")
                        continue
                    api_clients[api_token] = client
                current_token = api_token

            client = api_clients[api_token]

            # ── Video URL'sini çözümle (dosyayı public servise yükle) ──
            print(f"\n[INFO] {video_label} için video hazırlanıyor...")
            if account_log_label:
                print(f"[INFO] Hedef hesap: {account_log_label}")
            print(f"[INFO] Video: {os.path.basename(video_path)}")

            video_url = resolve_video_url(video_path)

            if not video_url:
                print(f"[WARN] Video yükleme başarısız, tekrar deneniyor...")
                controlled_sleep(5)
                video_url = resolve_video_url(video_path, force_new=True)

            if not video_url:
                for platform_name in pending_platforms:
                    task_key = build_task_key_for_job(job, platform_name)
                    task_label = task_key_to_label(task_key)
                    failed_map[task_label] = "Video yüklenemedi"
                    update_resume_state(task_key, False, "Video yüklenemedi")
                last_video_identity = current_video_identity
                continue

            print(f"[INFO] Video URL: {video_url}")
            queue_target = f"{video_label} ({account_log_label})" if account_log_label else video_label
            print(f"[INFO] İşlem kuyruğu: {queue_target} -> {', '.join(pending_platforms)}")

            for platform_name in pending_platforms:
                check_flag_state()
                task_key = build_task_key_for_job(job, platform_name)
                task_label = task_key_to_label(task_key)
                handler = handlers.get(platform_name)

                if not handler:
                    failed_map[task_label] = f"Desteklenmeyen platform: {platform_name}"
                    update_resume_state(task_key, False, f"Desteklenmeyen platform: {platform_name}")
                    continue

                # Platform bazlı retry mekanizması
                ok = False
                detail = ""
                for retry in range(MAX_PLATFORM_RETRIES + 1):
                    try:
                        ok, detail = handler(client, video_path, video_url, settings)
                    except StopRequested:
                        raise
                    except Exception as e:
                        ok = False
                        detail = sanitize_detail(str(e))

                    if ok:
                        break

                    # Geçmiş tarih hatasında retry yapmak anlamsız — hemen çık
                    if "geçmiş tarih" in detail.lower():
                        break

                    if retry < MAX_PLATFORM_RETRIES:
                        if any(kw in detail.lower() for kw in ["url", "erişim", "accessible", "media", "attachment"]):
                            print(f"[WARN] {task_label} başarısız (deneme {retry + 1}): {detail}")
                            print(f"[INFO] Video URL yeniden oluşturuluyor...")
                            VideoUploader.invalidate_cache(video_path)
                            controlled_sleep(5)
                            new_url = resolve_video_url(video_path, force_new=True)
                            if new_url:
                                video_url = new_url
                                print(f"[INFO] Yeni Video URL: {video_url[:80]}...")
                            else:
                                print(f"[WARN] Yeni URL oluşturulamadı, mevcut URL ile tekrar deneniyor...")
                        else:
                            print(f"[WARN] {task_label} başarısız (deneme {retry + 1}): {detail}")
                            controlled_sleep(INTER_PLATFORM_DELAY)

                if ok:
                    print(f"[OK] {task_label} tamamlandı.")
                    success_list.append(task_label)
                    failed_map.pop(task_label, None)
                    update_resume_state(task_key, True, "")
                    done_set.add(task_key)
                else:
                    detail = sanitize_detail(detail)
                    print(f"[ERROR] {task_label} başarısız: {detail}")
                    failed_map[task_label] = detail
                    update_resume_state(task_key, False, detail)

                    # Geçmiş tarih hatasında aynı video’nun kalan platformlarını da
                    # başarısız olarak işaretle — hepsi aynı zamanlama ayarını kullanıyor.
                    if "geçmiş tarih" in detail.lower():
                        remaining_idx = pending_platforms.index(platform_name) + 1
                        for skip_platform in pending_platforms[remaining_idx:]:
                            skip_key = build_task_key_for_job(job, skip_platform)
                            skip_label = task_key_to_label(skip_key)
                            print(f"[ERROR] {skip_label} başarısız: {detail} (aynı zamanlama)")
                            failed_map[skip_label] = detail
                            update_resume_state(skip_key, False, detail)
                        break  # Bu video için kalan platformları atla

                # Platformlar arası bekleme süresi
                controlled_sleep(INTER_PLATFORM_DELAY)

            last_video_identity = current_video_identity

        if skipped_jobs:
            kalan = len(skipped_jobs)
            print(f"[WARN] Kısmi Tamamlandı - Paylaşılmayan kalan video sayısı: {kalan}")

        print_summary(success_list, failed_map, skipped_list, already_done_list)

        if not failed_map:
            clear_resume_state()
        return 0

    except StopRequested:
        print("[WARN] İşlem kullanıcı tarafından durduruldu. Kayıtlı durum korunuyor.")
        print_summary(success_list, failed_map, skipped_list, already_done_list)
        return 0
    except Exception as e:
        print(f"Genel Hata: {sanitize_detail(str(e))}")
        traceback.print_exc()
        print_summary(success_list, failed_map, skipped_list, already_done_list)
        return 0
    finally:
        # Video yükleme önbelleğini temizle
        VideoUploader.clear_cache()


if __name__ == "__main__":
    sys.exit(start_bot())
