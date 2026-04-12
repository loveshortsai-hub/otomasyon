# -*- coding: utf-8 -*-
import yt_dlp
import os
import subprocess
import shutil
import time
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

RUNNING_PID = os.path.join(CONTROL_DIR, "RUNNING.pid")

def stop_istegi_var_mi():
    return os.path.exists(STOP_FLAG)

def pid_kaydet():
    """Bu script'in PID'ini RUNNING.pid'e yaz - app.py tarafından kill için kullanılır"""
    try:
        with open(RUNNING_PID, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

def pid_sil():
    """RUNNING.pid dosyasını temizle"""
    try:
        if os.path.exists(RUNNING_PID):
            os.remove(RUNNING_PID)
    except Exception:
        pass

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

PROXY_ENV_KEYS = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy",
)


# === PAUSE FLAG CONTROL ===

# --- DOSYA YOLLARI ---
# Ana indirme klasörü
ana_indirme_klasoru = r"C:\Users\User\Desktop\Otomasyon\İndirilen Video"

# Geçici dosyaların tutulacağı klasör
temp_klasoru = r"C:\Users\User\Desktop\Otomasyon\İndirilen Video\temp"

# Linklerin bulunduğu TXT dosyası
txt_dosyasi = r"C:\Users\User\Desktop\Otomasyon\İndirilecek Video.txt"

# Klasörler yoksa oluştur
os.makedirs(ana_indirme_klasoru, exist_ok=True)
os.makedirs(temp_klasoru, exist_ok=True)
# ---------------------

def kutuphane_guncelle():
    """yt-dlp kütüphanesini güncelle"""
    print("🔄 İndirme motoru (yt-dlp) güncelleniyor...")
    try:
        # === PAUSE FLAG CONTROL ===
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()
        # === PAUSE FLAG CONTROL ===
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-U', 'yt-dlp', '--quiet'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=temiz_ag_ortami(),
        )
        if result.returncode == 0:
            print("✅ Güncelleme kontrolü tamam.")
        else:
            print("⚠️ Güncelleme kontrolü yapılamadı.")
    except Exception as e:
        print(f"⚠️ Güncelleme kontrolü yapılamadı: {e}")

def ffmpeg_kurulu_mu():
    """FFmpeg kontrolü"""
    try:
        # === PAUSE FLAG CONTROL ===
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()
        # === PAUSE FLAG CONTROL ===
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def video_donustur(giris_dosyasi, cikis_dosyasi):
    """Videoyu Adobe Premiere/AI uyumlu MP4 formatına dönüştür"""
    try:
        komut = [
            'ffmpeg',
            '-i', giris_dosyasi,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-loglevel', 'quiet',
            '-stats',
            '-y',
            cikis_dosyasi
        ]

        print("  📦 FFmpeg ile dönüştürülüyor...")

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # === PAUSE FLAG CONTROL ===
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()
        # === PAUSE FLAG CONTROL ===
        result = subprocess.run(
            komut,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )

        if result.returncode == 0 and os.path.exists(cikis_dosyasi):
            print("  ✅ Dönüştürme başarılı!")
            return True
        else:
            print(f"  ❌ FFmpeg hatası!")
            return False
    except Exception as e:
        print(f"  ❌ Dönüştürme hatası: {e}")
        return False

def platform_belirle(url):
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
        return 'tiktok'
    else:
        return 'bilinmiyor'

def format_sec(platform):
    if platform == 'youtube':
        return 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
    else:
        return 'best'


def temiz_ag_ortami():
    env = os.environ.copy()
    for key in PROXY_ENV_KEYS:
        if key in env:
            env[key] = ""
    return env


def yt_dlp_cache_dir():
    cache_dir = os.path.join(CONTROL_DIR, "yt-dlp-cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def yt_dlp_komutu(platform, outtmpl, url):
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--proxy", "",
        "--no-progress",
        "--no-playlist",
        "--restrict-filenames",
        "--cache-dir", yt_dlp_cache_dir(),
        "-f", format_sec(platform),
        "-o", outtmpl,
    ]

    if platform == "youtube":
        node_path = shutil.which("node")
        if node_path:
            cmd += ["--js-runtimes", f"node:{node_path}", "--remote-components", "ejs:github"]

    if platform == "tiktok":
        cmd += [
            "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "--add-header", "Accept-Language:en-us,en;q=0.5",
            "--add-header", "Sec-Fetch-Mode:navigate",
        ]

    cmd.append(url)
    return cmd


def filtrele_yt_dlp_loglari(raw_output):
    out = []
    for line in str(raw_output or "").splitlines():
        clean = line.strip()
        if not clean:
            continue
        if clean.startswith(("[youtube]", "[info]", "[download]", "[hlsnative]", "[Merger]", "[FixupM3u8]", "WARNING:", "ERROR:")):
            out.append(clean)
    return out


def hata_detayi_coz(platform, raw_output):
    text = str(raw_output or "").strip()
    low = text.lower()

    if ("sign in to confirm you" in low and "not a bot" in low) or "cookies-from-browser" in low or "--cookies" in low:
        return "YouTube doğrulaması gerekiyor (cookies/çerez gerekli)."
    if "unable to connect to proxy" in low or "proxyerror" in low:
        return "Proxy bağlantısı kurulamadı."
    if "http error 429" in low or "too many requests" in low:
        return "YouTube hız limiti / bot koruması tetiklendi."
    if "no supported javascript runtime" in low or "remote component challenge solver script" in low or "js challenge" in low:
        return "JavaScript challenge çözülemedi."
    if "video unavailable" in low:
        return "Video kullanılamıyor."
    if "unable to download webpage" in low or "unable to download api page" in low:
        return "Video sayfasına erişilemedi."
    if "unsupported url" in low or "desteklenmiyor" in low:
        return "URL desteklenmiyor."

    if platform == "youtube":
        return "YouTube videosu indirilemedi."
    if platform == "tiktok":
        return "TikTok videosu indirilemedi."
    if platform == "instagram":
        return "Instagram videosu indirilemedi."
    return "Video indirilemedi."


def temp_dosyadan_baslik_al(dosya_yolu, prefix):
    ad = os.path.splitext(os.path.basename(dosya_yolu))[0]
    if ad.startswith(prefix):
        ad = ad[len(prefix):]
    ad = ad.strip(" _-.")
    return ad or "video"

def temizlik_yap():
    """Temp klasörünü sil"""
    try:
        # === PAUSE FLAG CONTROL ===
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()
        # === PAUSE FLAG CONTROL ===
        if os.path.exists(temp_klasoru):
            shutil.rmtree(temp_klasoru)
            print("\n🧹 Geçici dosyalar temizlendi.")
    except:
        pass

def toplu_video_indir():
    print(f"📂 Kaynak Dosya: {txt_dosyasi}")

    if not os.path.exists(txt_dosyasi):
        print(f"❌ Hata: TXT dosyası bulunamadı!")
        return

    try:
        with open(txt_dosyasi, 'r', encoding='utf-8') as f:
            url_listesi = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
    except Exception as e:
        print(f"Dosya okuma hatası: {e}")
        return

    if not url_listesi:
        print("⚠️ TXT dosyasında link yok.")
        return

    print(f"\nToplam {len(url_listesi)} video işlenecek...")

    basarili = 0
    basarisiz = 0
    atlandi = 0
    basarili_ogeler = []
    basarisiz_ogeler = []
    atlanan_ogeler = []

    # === MERKEZI KONTROL SİSTEMİ ===
    # STATE + DONE + FAILED dosyaları artık merkezi klasörde
    STATE_FILE = os.path.join(CONTROL_DIR, "STATE.json")
    DONE_FILE = os.path.join(CONTROL_DIR, "DONE.json")
    FAILED_FILE = os.path.join(CONTROL_DIR, "FAILED.json")
    
    state_path = STATE_FILE
    done_path = DONE_FILE
    failed_path = FAILED_FILE

    state = {"last_successful_index": -1}
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f) or state
        except Exception:
            # Bozuksa sıfırla (dosya asla bozulmasın diye atomik yazacağız)
            state = {"last_successful_index": -1}

    done_urls = set()
    if os.path.exists(done_path):
        try:
            with open(done_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if isinstance(data, dict) and isinstance(data.get("done_urls"), list):
                    done_urls = set(data.get("done_urls"))
        except Exception:
            done_urls = set()

    failed = {}
    if os.path.exists(failed_path):
        try:
            with open(failed_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if isinstance(data, dict) and isinstance(data.get("failed"), dict):
                    failed = data.get("failed")
        except Exception:
            failed = {}

    start_index = int(state.get("last_successful_index", -1)) + 1

    def _atomic_write_json(path, obj):
        # 🛡️ Atomik kayıt + fsync: elektrik kesilse bile dosya bozulmaz.
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    # === PAUSE FLAG CONTROL ===
    # Başarısız linkleri FAILED.json'a yaz + STATE ilerlet (restart'ta aynı linkte takılmasın)
    def _mark_failed(url, index, reason):
        key = str(url)
        prev = failed.get(key, {}) if isinstance(failed, dict) else {}
        try_count = int(prev.get("count", 0)) + 1
        failed[key] = {"count": try_count, "last_index": index, "reason": str(reason)[:200]}
        _atomic_write_json(failed_path, {"failed": failed})
        # Başarısız işlemlerde STATE ilerletilmez ki sonraki çalışmada tekrar denenebilsin.
    # === PAUSE FLAG CONTROL ===

    # Mevcut klasörlere bakıp bir sonraki Video numarasını bul (restart sonrası çakışma olmasın)
    # Hem klasör sayısına hem STATE.json'daki last_successful_index'e bakarak en yüksek değeri al
    max_no = 0
    try:
        for name in os.listdir(ana_indirme_klasoru):
            if name.startswith("Video "):
                tail = name.replace("Video ", "").strip()
                if tail.isdigit():
                    max_no = max(max_no, int(tail))
    except Exception:
        pass

    # STATE'den kaç video başarıyla tamamlandıysa onu da hesaba kat
    # (klasör var ama STATE ileride ise STATE'i baz al)
    state_based_no = int(state.get("last_successful_index", -1)) + 1
    # Klasör sayısı ile STATE'den hangisi büyükse onu kullan
    autonumber = max(max_no, state_based_no) + 1 if max_no > 0 else state_based_no + 1
    if autonumber < 1:
        autonumber = 1
    # === PAUSE FLAG CONTROL ===

    ffmpeg_var = ffmpeg_kurulu_mu()

    for i, url in enumerate(url_listesi):
        # === PAUSE FLAG CONTROL ===
        bekle_pause_varsa(pause_flag)
        stop_kontrol_noktasinda_cik()

        # STATE üzerinden skip (İptal edildi: Sadece DONE dosyasına bakılacak böylece başarısız olanlar tekrar dönecek)
        # if i < start_index:
        #     atlandi += 1
        #     continue

        # === PAUSE FLAG CONTROL ===
        # Tutarlı log için: liste sırası (display_no) ve toplam
        display_no = i + 1
        total_count = len(url_listesi)
        # === PAUSE FLAG CONTROL ===

        # DONE list üzerinden skip (yanlış skip riskini sıfırlamak için)
        if url in done_urls:
            print(f"\n--- [{display_no}/{total_count}] SKIP (DONE) ---")
            # Bu URL zaten tamamlandıysa state'i ileri al (restart'ta tekrar gezmesin)
            state["last_successful_index"] = i
            _atomic_write_json(state_path, state)
            atlandi += 1
            atlanan_ogeler.append(f"Video {display_no}")
            continue
        # === PAUSE FLAG CONTROL ===

        platform = platform_belirle(url)

        if platform == 'bilinmiyor':
            # === PAUSE FLAG CONTROL ===
            print(f"\n--- [{display_no}/{total_count}] ATLANDI (Desteklenmiyor) ---")
            # === PAUSE FLAG CONTROL ===
            # Desteklenmeyen URL'yi DONE/STATE'e yaz (restart'ta tekrar tekrar gelmesin)
            done_urls.add(url)
            _atomic_write_json(done_path, {"done_urls": sorted(done_urls)})
            state["last_successful_index"] = i
            _atomic_write_json(state_path, state)
            continue

        temp_prefix = f"temp_{autonumber:03d}__"
        temp_dosya = os.path.join(temp_klasoru, f'{temp_prefix}%(title).80s.%(ext)s')

        # === PAUSE FLAG CONTROL ===
        # Aynı prefix'li eski dosyalar kalırsa yanlış eşleşme olmasın diye temizle
        try:
            prefix = f"temp_{autonumber:03d}"
            if os.path.exists(temp_klasoru):
                for _f in os.listdir(temp_klasoru):
                    if _f.startswith(prefix):
                        try:
                            os.remove(os.path.join(temp_klasoru, _f))
                        except Exception:
                            pass
        except Exception:
            pass
        # === PAUSE FLAG CONTROL ===

        try:
            print(f"\n👉 İşleniyor [{display_no}/{total_count}] (Video {autonumber}): {url}")
            print("   ⬇️ İndiriliyor...")

            cmd = yt_dlp_komutu(platform, temp_dosya, url)

            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # === PAUSE FLAG CONTROL ===
            bekle_pause_varsa(pause_flag)
            stop_kontrol_noktasinda_cik()
            # === PAUSE FLAG CONTROL ===
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=temiz_ag_ortami(),
                startupinfo=startupinfo,
            )

            raw_output = "\n".join(part for part in [result.stdout, result.stderr] if part)
            for log_line in filtrele_yt_dlp_loglari(raw_output):
                print(f"   {log_line}")

            if result.returncode != 0:
                hata = hata_detayi_coz(platform, raw_output)
                print(f"   ❌ {hata}")
                basarisiz += 1
                basarisiz_ogeler.append(f"Video {autonumber} ({hata})")
                # === PAUSE FLAG CONTROL ===
                _mark_failed(url, i, hata)
                # === PAUSE FLAG CONTROL ===
                continue

            # İndirilen dosyayı bul (temp içinde)
            indirilen_dosya = None
            for dosya in os.listdir(temp_klasoru):
                if dosya.startswith(temp_prefix):
                    indirilen_dosya = os.path.join(temp_klasoru, dosya)
                    break

            # Dosya boyutu kontrolü
            if indirilen_dosya and os.path.getsize(indirilen_dosya) == 0:
                print("   ❌ Dosya boş indi.")
                os.remove(indirilen_dosya)
                basarisiz += 1
                basarisiz_ogeler.append(f"Video {autonumber} (Dosya boş indi)")
                # === PAUSE FLAG CONTROL ===
                _mark_failed(url, i, "Dosya boş indi")
                # === PAUSE FLAG CONTROL ===
                continue

            if not indirilen_dosya:
                print("   ❌ İndirilen dosya bulunamadı.")
                basarisiz += 1
                basarisiz_ogeler.append(f"Video {autonumber} (İndirilen dosya bulunamadı)")
                # === PAUSE FLAG CONTROL ===
                _mark_failed(url, i, "İndirilen dosya bulunamadı")
                # === PAUSE FLAG CONTROL ===
                continue

            baslik = temp_dosyadan_baslik_al(indirilen_dosya, temp_prefix)
            print(f"   Başlık: {baslik}")

            # --- YENİ KLASÖR YAPISI ---
            # Her video için "Video 1", "Video 2" klasörü oluştur
            hedef_klasor = os.path.join(ana_indirme_klasoru, f"Video {autonumber}")
            os.makedirs(hedef_klasor, exist_ok=True)

            # Dosya ismi temizliği
            temiz_baslik = "".join(c for c in baslik if c.isalnum() or c in (' ', '-', '_')).strip()
            if len(temiz_baslik) > 50:
                temiz_baslik = temiz_baslik[:50]

            # Hedef dosya yolu (Video X klasörünün içi)
            hedef_dosya = os.path.join(hedef_klasor, f"{temiz_baslik}.mp4")

            if indirilen_dosya and ffmpeg_var:
                # === PAUSE FLAG CONTROL ===
                bekle_pause_varsa(pause_flag)
                stop_kontrol_noktasinda_cik()
                # === PAUSE FLAG CONTROL ===
                if video_donustur(indirilen_dosya, hedef_dosya):
                    # === PAUSE FLAG CONTROL ===
                    bekle_pause_varsa(pause_flag)
                    stop_kontrol_noktasinda_cik()
                    # === PAUSE FLAG CONTROL ===
                    
                    # ✅ DONE.flag artık merkezi DONE.json'da tutuluyor (video klasörlerinde dosya oluşmuyor)

                    # DONE list (URL bazlı, yanlış skip riskini sıfırlar)
                    done_urls.add(url)
                    _atomic_write_json(done_path, {"done_urls": sorted(done_urls)})

                    # STATE (son başarılı index)
                    state["last_successful_index"] = i
                    _atomic_write_json(state_path, state)

                    print(f"   ✅ Kaydedildi: Video {autonumber} Klasörü")
                    basarili += 1
                    basarili_ogeler.append(f"Video {autonumber}")
                    autonumber += 1
                else:
                    print("   ⚠️ Dönüştürme başarısız.")
                    basarisiz += 1
                    basarisiz_ogeler.append(f"Video {autonumber} (FFmpeg dönüştürme başarısız)")
                    # === PAUSE FLAG CONTROL ===
                    _mark_failed(url, i, "FFmpeg dönüştürme başarısız")
                    # === PAUSE FLAG CONTROL ===
            elif indirilen_dosya:
                # Dönüştürmeden taşı
                # === PAUSE FLAG CONTROL ===
                bekle_pause_varsa(pause_flag)
                stop_kontrol_noktasinda_cik()
                # === PAUSE FLAG CONTROL ===
                shutil.move(indirilen_dosya, hedef_dosya)

                # === PAUSE FLAG CONTROL ===
                bekle_pause_varsa(pause_flag)
                stop_kontrol_noktasinda_cik()
                # === PAUSE FLAG CONTROL ===
                
                # ✅ DONE.flag artık merkezi DONE.json'da tutuluyor (video klasörlerinde dosya oluşmuyor)

                # DONE list (URL bazlı, yanlış skip riskini sıfırlar)
                done_urls.add(url)
                _atomic_write_json(done_path, {"done_urls": sorted(done_urls)})

                # STATE (son başarılı index)
                state["last_successful_index"] = i
                _atomic_write_json(state_path, state)

                print(f"   ✅ Taşındı (Dönüştürülmedi): Video {autonumber}")
                basarili += 1
                basarili_ogeler.append(f"Video {autonumber}")
                autonumber += 1
            else:
                print("   ❌ Dosya bulunamadı.")
                basarisiz += 1
                basarisiz_ogeler.append(f"Video {autonumber} (Dosya bulunamadı)")
                # === PAUSE FLAG CONTROL ===
                _mark_failed(url, i, "Dosya bulunamadı")
                # === PAUSE FLAG CONTROL ===

        except Exception as e:
            hata = hata_detayi_coz(platform, str(e))
            print(f"   ❌ Hata: {hata}")
            basarisiz += 1
            basarisiz_ogeler.append(f"Video {autonumber} ({hata})")
            # === PAUSE FLAG CONTROL ===
            _mark_failed(url, i, hata)
            # === PAUSE FLAG CONTROL ===

    temizlik_yap()

    print("\n" + "=" * 60)
    print(f"İŞLEMLER TAMAMLANDI")
    print(f"Başarılı: {basarili} - {' | '.join(basarili_ogeler) if basarili_ogeler else 'Yok'}")
    print(f"Başarısız: {basarisiz} - {' | '.join(basarisiz_ogeler) if basarisiz_ogeler else 'Yok'}")
    print(f"Atlandı (Zaten Mevcut): {atlandi} - {' | '.join(atlanan_ogeler) if atlanan_ogeler else 'Yok'}")
    print("=" * 60)

if __name__ == "__main__":
    pid_kaydet()  # PID'i kaydet - app.py bu PID ile process'i öldürebilir
    print("=" * 60)
    print("🎬 OTOMATİK VIDEO İNDİRİCİ 🎬")
    print("=" * 60)
    kutuphane_guncelle()
    toplu_video_indir()
    pid_sil()  # Temiz çıkışta PID dosyasını sil
    print("\nÇıkış yapılıyor (5 sn)...")
    # === PAUSE FLAG CONTROL ===
    bekle_pause_varsa(pause_flag)
    stop_kontrol_noktasinda_cik()
    # === PAUSE FLAG CONTROL ===
    time.sleep(5)
