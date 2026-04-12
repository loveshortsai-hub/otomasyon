import os
import json
import glob
import re
import random
from datetime import datetime
from itertools import permutations

# MoviePy import - Hem eski hem yeni versiyonlarla uyumlu
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, AudioFileClip, CompositeAudioClip
except ImportError:
    try:
        from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip, AudioFileClip, CompositeAudioClip
    except ImportError:
        print("HATA: MoviePy kurulamadı!")
        print("Lütfen şu komutu çalıştırın: pip install moviepy==1.0.3")
        input("Çıkmak için Enter'a basın...")
        exit(1)

# PIL uyumluluk düzeltmesi
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

# ==================== AYARLAR ====================
# VARİYASYON LİMİTLERİ
LIMIT_IKILI = 10      
LIMIT_UCLU = 20       
LIMIT_DORTLU = 20     
LIMIT_BESLI = 20      
LIMIT_ALTILI = 20     
LIMIT_YEDILI = 20     
LIMIT_SEKIZLI = 20    
LIMIT_DOKUZLU = 20    
LIMIT_ONLU = 20
LIMIT_ONBIRLI = 20
LIMIT_ONIKILI = 20
LIMIT_ONUCLU = 20
LIMIT_ONDORTLU = 20
LIMIT_ONBESLI = 20
LIMIT_ONALTILI = 20
LIMIT_ONYEDILI = 20
LIMIT_ONSEKIZLI = 20
LIMIT_ONDOKUZLU = 20
LIMIT_YIRMILI = 20

# ==================================================

# Görsel Analiz çıktı klasörü (analiz.py tarafından oluşturulan ses dosyaları burada)
gorsel_analiz_dir = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Analiz"

# 1. Ana Script Yolu
ana_klasor = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Toplu Video Montaj"

# 2. Videoların Aranacağı Kaynak Ana Yollar
# GÜNCELLENEN KISIM BURASI:
video_kaynak_ana_yol = r"C:\Users\User\Desktop\Otomasyon\Video\Video"
klon_video_kaynak_ana_yol = r"C:\Users\User\Desktop\Otomasyon\Klon Video"

# 3. Çıktı Klasörü
toplu_montaj_klasor = r"C:\Users\User\Desktop\Otomasyon\Video\Toplu Montaj"

# 4. Materyal ve Ek Dosyaların Bulunduğu Yol
materyal_ana_yol = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek"

# Alt Klasör Tanımlamaları
muzik_klasor = os.path.join(materyal_ana_yol, "muzik")
cerceve_klasor = os.path.join(materyal_ana_yol, "çerçeve")
logo_klasor = os.path.join(materyal_ana_yol, "logo")
video_overlay_klasor = os.path.join(materyal_ana_yol, "video overlay")
ses_efekti_klasor = os.path.join(materyal_ana_yol, "ses efekti")

# Dosya Tanımlamaları
baslik_dosyasi = os.path.join(materyal_ana_yol, "başlık.txt")
log_dosyasi = os.path.join(ana_klasor, "log.txt")

# Klasörleri oluştur
os.makedirs(toplu_montaj_klasor, exist_ok=True)
os.makedirs(muzik_klasor, exist_ok=True)
os.makedirs(cerceve_klasor, exist_ok=True)
os.makedirs(logo_klasor, exist_ok=True)
os.makedirs(video_overlay_klasor, exist_ok=True)
os.makedirs(ses_efekti_klasor, exist_ok=True)

def video_format_sec():
    """Kullanıcıdan video formatını sor"""
    print("\n" + "="*80)
    print("VİDEO FORMAT SEÇİMİ")
    print("="*80)
    print("\n📐 Hangi formatta video oluşturmak istersiniz?")
    print("  [Y] Yatay - 1920x1080 (Normal YouTube)")
    print("  [D] Dikey - 1080x1920 (YouTube Shorts)")
    
    while True:
        secim = input("\n👉 Seçiminiz (Y/D): ").strip().upper()
        if secim in ['Y', 'YATAY']:
            print("\n✅ YATAY format seçildi (1920x1080)")
            return "normal"
        elif secim in ['D', 'DIKEY', 'DKEY']:
            print("\n✅ DİKEY format seçildi (1080x1920)")
            return "shorts"
        else:
            print("⚠️ Geçersiz seçim! Lütfen Y veya D yazın.")

def log_hatasi_kaydet(hata_mesaji, adim=""):
    try:
        with open(log_dosyasi, 'a', encoding='utf-8') as log:
            zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"[{zaman}] {adim} HATA\n")
            log.write(f"Hata Mesajı: {hata_mesaji}\n")
            log.write("-" * 80 + "\n")
        print(f"Hata log'a kaydedildi: {log_dosyasi}")
    except Exception as e:
        print(f"Log yazma hatası: {e}")

def video_boyutunu_ayarla(clip, video_format="shorts"):
    """Videoyu seçilen formata uyarla"""
    if video_format == "shorts":
        hedef_genislik = 1080
        hedef_yukseklik = 1920
        format_adi = "YouTube Shorts (Dikey)"
    else:  # normal
        hedef_genislik = 1920
        hedef_yukseklik = 1080
        format_adi = "Normal YouTube (Yatay)"
    
    video_genislik, video_yukseklik = clip.size
    print(f"      Orijinal: {video_genislik}x{video_yukseklik}")
    
    # Direkt olarak hedef boyuta resize et
    clip_resized = clip.resize(newsize=(hedef_genislik, hedef_yukseklik))
    
    print(f"      Sonuç: {clip_resized.size[0]}x{clip_resized.size[1]} ({format_adi})")
    print(f"      ✓ Hazır! Süre: {clip_resized.duration:.1f}s\n")
    return clip_resized

def ses_seviyesi_oku():
    """muzik/ses_seviyesi.txt dosyasından ses seviyesini oku"""
    ses_dosyasi = os.path.join(muzik_klasor, "ses_seviyesi.txt")
    try:
        if os.path.exists(ses_dosyasi):
            with open(ses_dosyasi, 'r', encoding='utf-8') as f:
                icerik = f.read().strip()
                icerik = icerik.replace('%', '').strip()
                seviye = int(icerik)
                seviye = max(0, min(100, seviye))
                return seviye / 100.0
    except Exception as e:
        pass
    return 0.15

def muzik_ekle(video_clip):
    """Video'ya arka plan müziği ekle"""
    muzik_dosyalari = []
    for uzanti in ['*.mp3', '*.wav', '*.m4a', '*.aac', '*.ogg']:
        muzik_dosyalari.extend(glob.glob(os.path.join(muzik_klasor, uzanti)))
    
    if not muzik_dosyalari:
        print("\n⚠️  Müzik klasöründe müzik bulunamadı")
        return video_clip
    
    secilen_muzik = random.choice(muzik_dosyalari)
    try:
        muzik_hacmi = ses_seviyesi_oku()
        print(f"\n🎵 Müzik: {os.path.basename(secilen_muzik)}")
        print(f"   📊 Ses seviyesi: %{int(muzik_hacmi * 100)}")
        
        muzik_clip = AudioFileClip(secilen_muzik)
        video_suresi = video_clip.duration
        
        if muzik_clip.duration > video_suresi:
            muzik_clip = muzik_clip.subclip(0, video_suresi)
        elif muzik_clip.duration < video_suresi:
            from moviepy.audio.AudioClip import concatenate_audioclips
            tekrar_sayisi = int(video_suresi / muzik_clip.duration) + 1
            muzik_clip = concatenate_audioclips([muzik_clip] * tekrar_sayisi)
            muzik_clip = muzik_clip.subclip(0, video_suresi)
        
        muzik_clip = muzik_clip.volumex(muzik_hacmi)
        muzik_clip = muzik_clip.audio_fadein(2.0).audio_fadeout(2.0)
        
        if video_clip.audio is not None:
            yeni_ses = CompositeAudioClip([video_clip.audio, muzik_clip])
            video_clip = video_clip.set_audio(yeni_ses)
        else:
            video_clip = video_clip.set_audio(muzik_clip)
        
        print(f"   ✅ Müzik eklendi")
        return video_clip
    except Exception as e:
        print(f"   ❌ Müzik hatası: {e}")
        return video_clip

def cerceve_dosyalari_getir():
    """Çerçeve klasöründeki dosyaları sıralı listele"""
    cerceve_dosyalari = []
    for uzanti in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.mp4', '*.avi', '*.mov', '*.webm']:
        cerceve_dosyalari.extend(glob.glob(os.path.join(cerceve_klasor, uzanti)))
    
    if not cerceve_dosyalari:
        return []
    
    def numaraya_gore_siralama(dosya):
        basename = os.path.basename(dosya)
        match = re.match(r'(\d+)', basename)
        return int(match.group(1)) if match else float('inf')
    return sorted(cerceve_dosyalari, key=numaraya_gore_siralama)

def cerceve_ekle(video_clips):
    """Video clip'lere çerçeve ekle"""
    cerceve_dosyalari = cerceve_dosyalari_getir()
    if not cerceve_dosyalari:
        return video_clips
    
    try:
        from moviepy.editor import ImageClip, CompositeVideoClip
        yeni_clips = []
        
        if len(cerceve_dosyalari) == 1:
            cerceve_dosya = cerceve_dosyalari[0]
            cerceve_uzanti = os.path.splitext(cerceve_dosya)[1].lower()
            for video_clip in video_clips:
                try:
                    if cerceve_uzanti in ['.png', '.jpg', '.jpeg', '.gif']:
                        cerceve_clip = ImageClip(cerceve_dosya).set_duration(video_clip.duration)
                    else:
                        cerceve_clip = VideoFileClip(cerceve_dosya)
                        if cerceve_clip.duration < video_clip.duration:
                            tekrar = int(video_clip.duration / cerceve_clip.duration) + 1
                            cerceve_clip = concatenate_videoclips([cerceve_clip] * tekrar).subclip(0, video_clip.duration)
                        else:
                            cerceve_clip = cerceve_clip.subclip(0, video_clip.duration)
                    cerceve_clip = cerceve_clip.resize(newsize=(video_clip.w, video_clip.h))
                    yeni_clip = CompositeVideoClip([video_clip, cerceve_clip.set_position("center")])
                    yeni_clips.append(yeni_clip)
                except:
                    yeni_clips.append(video_clip)
        else:
            for idx, video_clip in enumerate(video_clips):
                if idx < len(cerceve_dosyalari):
                    cerceve_dosya = cerceve_dosyalari[idx]
                    cerceve_uzanti = os.path.splitext(cerceve_dosya)[1].lower()
                    try:
                        if cerceve_uzanti in ['.png', '.jpg', '.jpeg', '.gif']:
                            cerceve_clip = ImageClip(cerceve_dosya).set_duration(video_clip.duration)
                        else:
                            cerceve_clip = VideoFileClip(cerceve_dosya)
                            if cerceve_clip.duration < video_clip.duration:
                                tekrar = int(video_clip.duration / cerceve_clip.duration) + 1
                                cerceve_clip = concatenate_videoclips([cerceve_clip] * tekrar).subclip(0, video_clip.duration)
                            else:
                                cerceve_clip = cerceve_clip.subclip(0, video_clip.duration)
                        cerceve_clip = cerceve_clip.resize(newsize=(video_clip.w, video_clip.h))
                        yeni_clip = CompositeVideoClip([video_clip, cerceve_clip.set_position("center")])
                        yeni_clips.append(yeni_clip)
                    except:
                        yeni_clips.append(video_clip)
                else:
                    yeni_clips.append(video_clip)
        return yeni_clips
    except:
        return video_clips

def logo_dosyalari_getir():
    """Logo klasöründeki dosyaları sıralı listele"""
    logo_dosyalari = []
    for uzanti in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.mp4', '*.avi', '*.mov']:
        logo_dosyalari.extend(glob.glob(os.path.join(logo_klasor, uzanti)))
    if not logo_dosyalari:
        return []
    def numaraya_gore_siralama(dosya):
        basename = os.path.basename(dosya)
        match = re.match(r'(\d+)', basename)
        return int(match.group(1)) if match else float('inf')
    return sorted(logo_dosyalari, key=numaraya_gore_siralama)

def logo_ekle(video_clips):
    """Video clip'lere logo ekle"""
    logo_dosyalari = logo_dosyalari_getir()
    if not logo_dosyalari:
        return video_clips
    try:
        from moviepy.editor import ImageClip, CompositeVideoClip
        yeni_clips = []
        if len(logo_dosyalari) == 1:
            logo_dosya = logo_dosyalari[0]
            logo_uzanti = os.path.splitext(logo_dosya)[1].lower()
            for video_clip in video_clips:
                try:
                    if logo_uzanti in ['.png', '.jpg', '.jpeg', '.gif']:
                        logo_clip = ImageClip(logo_dosya).set_duration(video_clip.duration)
                    else:
                        logo_clip = VideoFileClip(logo_dosya)
                        if logo_clip.duration < video_clip.duration:
                            tekrar = int(video_clip.duration / logo_clip.duration) + 1
                            logo_clip = concatenate_videoclips([logo_clip] * tekrar).subclip(0, video_clip.duration)
                        else:
                            logo_clip = logo_clip.subclip(0, video_clip.duration)
                    logo_clip = logo_clip.resize(newsize=(video_clip.w, video_clip.h))
                    yeni_clip = CompositeVideoClip([video_clip, logo_clip.set_position("center")])
                    yeni_clips.append(yeni_clip)
                except:
                    yeni_clips.append(video_clip)
        else:
            for idx, video_clip in enumerate(video_clips):
                if idx < len(logo_dosyalari):
                    logo_dosya = logo_dosyalari[idx]
                    logo_uzanti = os.path.splitext(logo_dosya)[1].lower()
                    try:
                        if logo_uzanti in ['.png', '.jpg', '.jpeg', '.gif']:
                            logo_clip = ImageClip(logo_dosya).set_duration(video_clip.duration)
                        else:
                            logo_clip = VideoFileClip(logo_dosya)
                            if logo_clip.duration < video_clip.duration:
                                tekrar = int(video_clip.duration / logo_clip.duration) + 1
                                logo_clip = concatenate_videoclips([logo_clip] * tekrar).subclip(0, video_clip.duration)
                            else:
                                logo_clip = logo_clip.subclip(0, video_clip.duration)
                        logo_clip = logo_clip.resize(newsize=(video_clip.w, video_clip.h))
                        yeni_clip = CompositeVideoClip([video_clip, logo_clip.set_position("center")])
                        yeni_clips.append(yeni_clip)
                    except:
                        yeni_clips.append(video_clip)
                else:
                    yeni_clips.append(video_clip)
        return yeni_clips
    except:
        return video_clips

def video_overlay_dosyalari_getir():
    """Video overlay dosyalarını listele"""
    overlay_dosyalari = []
    for uzanti in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.mp4', '*.avi', '*.mov']:
        overlay_dosyalari.extend(glob.glob(os.path.join(video_overlay_klasor, uzanti)))
    if not overlay_dosyalari:
        return []
    def numaraya_gore_siralama(dosya):
        basename = os.path.basename(dosya)
        match = re.match(r'(\d+)', basename)
        return int(match.group(1)) if match else float('inf')
    return sorted(overlay_dosyalari, key=numaraya_gore_siralama)

def video_overlay_ekle(video_clips):
    """Video clip'lere overlay ekle"""
    overlay_dosyalari = video_overlay_dosyalari_getir()
    if not overlay_dosyalari:
        return video_clips
    try:
        from moviepy.editor import ImageClip, CompositeVideoClip
        yeni_clips = []
        if len(overlay_dosyalari) == 1:
            overlay_dosya = overlay_dosyalari[0]
            overlay_uzanti = os.path.splitext(overlay_dosya)[1].lower()
            toplam_sure = sum([clip.duration for clip in video_clips])
            try:
                if overlay_uzanti in ['.png', '.jpg', '.jpeg', '.gif']:
                    overlay_clip = ImageClip(overlay_dosya).set_duration(toplam_sure)
                    overlay_clip = overlay_clip.resize(newsize=(video_clips[0].w, video_clips[0].h))
                else:
                    overlay_clip = VideoFileClip(overlay_dosya, has_mask=True)
                    if overlay_clip.mask is None:
                        overlay_clip = VideoFileClip(overlay_dosya)
                    if overlay_clip.duration < toplam_sure:
                        tekrar = int(toplam_sure / overlay_clip.duration) + 1
                        overlay_clip = concatenate_videoclips([overlay_clip] * tekrar)
                    overlay_clip = overlay_clip.subclip(0, toplam_sure)
                    overlay_clip = overlay_clip.resize(newsize=(video_clips[0].w, video_clips[0].h))
                gecen_sure = 0
                for video_clip in video_clips:
                    try:
                        overlay_parcasi = overlay_clip.subclip(gecen_sure, gecen_sure + video_clip.duration)
                        yeni_clip = CompositeVideoClip([video_clip, overlay_parcasi.set_position("center")])
                        yeni_clips.append(yeni_clip)
                        gecen_sure += video_clip.duration
                    except:
                        yeni_clips.append(video_clip)
                        gecen_sure += video_clip.duration
            except:
                return video_clips
        else:
            for idx, video_clip in enumerate(video_clips):
                if idx < len(overlay_dosyalari):
                    overlay_dosya = overlay_dosyalari[idx]
                    overlay_uzanti = os.path.splitext(overlay_dosya)[1].lower()
                    try:
                        if overlay_uzanti in ['.png', '.jpg', '.jpeg', '.gif']:
                            overlay_clip = ImageClip(overlay_dosya).set_duration(video_clip.duration)
                        else:
                            overlay_clip = VideoFileClip(overlay_dosya, has_mask=True)
                            if overlay_clip.mask is None:
                                overlay_clip = VideoFileClip(overlay_dosya)
                            if overlay_clip.duration < video_clip.duration:
                                tekrar = int(video_clip.duration / overlay_clip.duration) + 1
                                overlay_clip = concatenate_videoclips([overlay_clip] * tekrar).subclip(0, video_clip.duration)
                            else:
                                overlay_clip = overlay_clip.subclip(0, video_clip.duration)
                        overlay_clip = overlay_clip.resize(newsize=(video_clip.w, video_clip.h))
                        yeni_clip = CompositeVideoClip([video_clip, overlay_clip.set_position("center")])
                        yeni_clips.append(yeni_clip)
                    except:
                        yeni_clips.append(video_clip)
                else:
                    yeni_clips.append(video_clip)
        return yeni_clips
    except:
        return video_clips

def _ses_txt_degerini_oku(path, default=0.15, label="Ses"):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            icerik = f.read().strip()
        icerik = icerik.replace('%', '').strip()
        deger = float(icerik)
        if deger > 1:
            deger = deger / 100
        deger = max(0.0, min(1.0, deger))
        print(f"   📄 {label} seviyesi dosyadan okundu: %{int(deger * 100)}")
        return deger
    except Exception:
        print(f"   ⚠️ {label} seviyesi okunamadı, varsayılan kullanılıyor: %{int(default * 100)}")
        return default


def orijinal_ses_seviyesi_oku():
    return _ses_txt_degerini_oku(os.path.join(materyal_ana_yol, "orijinal_ses_seviyesi.txt"), 1.0, "Orijinal ses")


def video_ses_seviyesi_oku_toplu():
    return _ses_txt_degerini_oku(os.path.join(materyal_ana_yol, "video_ses_seviyesi.txt"), 1.0, "Video ses")


def _video_numarasi_bul(dosya_yolu):
    """Video dosya yolundan numara çıkarır (Video 1 -> 1, Klon Video 2 -> 2 vb.)"""
    klasor_adi = os.path.basename(os.path.dirname(dosya_yolu))
    match = re.search(r'(\d+)', klasor_adi)
    if match:
        return match.group(1)
    dosya_adi = os.path.basename(dosya_yolu)
    match2 = re.search(r'(\d+)', dosya_adi)
    if match2:
        return match2.group(1)
    return None


def _orijinal_ses_dosyasi_bul(video_dosya):
    """Görsel Analiz klasöründen ilgili videonun orijinal ses dosyasını bulur."""
    numara = _video_numarasi_bul(video_dosya)
    if not numara:
        return None
    hedef_klasor_adi = f"Video Görsel Analiz {numara}"
    ses_yolu = os.path.join(gorsel_analiz_dir, hedef_klasor_adi, "ses", "audio.mp3")
    if os.path.exists(ses_yolu):
        return ses_yolu
    return None

def _orijinal_ses_kaynaklarini_oku():
    json_yolu = os.path.join(materyal_ana_yol, "orijinal_ses_kaynaklari.json")
    if not os.path.exists(json_yolu):
        return []
    try:
        with open(json_yolu, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except Exception as e:
        print(f"   ⚠️ Orijinal ses kaynak listesi okunamadı: {e}")
    return []


def _orijinal_ses_kaynagini_yukle(video_dosya):
    ses_dosyasi = _orijinal_ses_dosyasi_bul(video_dosya)
    if ses_dosyasi and os.path.exists(ses_dosyasi):
        return AudioFileClip(ses_dosyasi), os.path.basename(ses_dosyasi)

    try:
        video_clip = VideoFileClip(video_dosya)
        if video_clip.audio is not None:
            return video_clip.audio, os.path.basename(video_dosya)
    except Exception:
        pass
    return None, None


def _orijinal_ses_playlist_olustur(kaynak_video_yollari, hedef_sure, ses_seviyesi):
    if hedef_sure <= 0:
        return None

    kaynak_audiolar = []
    for video_yolu in kaynak_video_yollari or []:
        audio_clip, ad = _orijinal_ses_kaynagini_yukle(video_yolu)
        if audio_clip is None or getattr(audio_clip, 'duration', 0) <= 0:
            print(f"   ⊖ Kaynak ses bulunamadı: {os.path.basename(video_yolu)}")
            continue
        kaynak_audiolar.append((audio_clip, ad or os.path.basename(video_yolu)))

    if not kaynak_audiolar:
        return None

    from moviepy.audio.AudioClip import concatenate_audioclips

    parcali = []
    kalan = float(hedef_sure)
    tur = 0
    while kalan > 0 and kaynak_audiolar:
        tur += 1
        for audio_clip, ad in kaynak_audiolar:
            if kalan <= 0:
                break
            parca_sure = min(float(getattr(audio_clip, 'duration', 0) or 0), kalan)
            if parca_sure <= 0:
                continue
            parcali.append(audio_clip.subclip(0, parca_sure))
            kalan -= parca_sure

    if not parcali:
        return None

    playlist = concatenate_audioclips(parcali).subclip(0, hedef_sure)
    playlist = playlist.volumex(ses_seviyesi)
    return playlist


def _cliplere_orijinal_ses_playlist_uygula(video_clips, playlist_audio):
    yeni_clips = []
    gecen_sure = 0.0
    for idx, video_clip in enumerate(video_clips, start=1):
        bitis = gecen_sure + float(video_clip.duration)
        try:
            audio_parcasi = playlist_audio.subclip(gecen_sure, bitis)
            if video_clip.audio is not None:
                yeni_ses = CompositeAudioClip([video_clip.audio, audio_parcasi])
                video_clip = video_clip.set_audio(yeni_ses)
            else:
                video_clip = video_clip.set_audio(audio_parcasi)
            print(f"   ✓ Clip {idx}: Özel orijinal ses sırası uygulandı")
        except Exception as e:
            print(f"   ⚠️ Clip {idx}: Özel orijinal ses uygulanamadı - {e}")
        yeni_clips.append(video_clip)
        gecen_sure = bitis
    return yeni_clips


    hedef_klasor_adi = f"Video Görsel Analiz {numara}"
    ses_yolu = os.path.join(gorsel_analiz_dir, hedef_klasor_adi, "ses", "audio.mp3")
    if os.path.exists(ses_yolu):
        return ses_yolu
    return None


def orijinal_ses_ekle(video_clips, video_dosya_isimleri, video_mu_listesi=None):
    """Görsel Analiz'den çıkarılan orijinal sesi video clip'lere ekler."""
    print(f"\n🔊 Orijinal video sesi ekleniyor...")
    ses_seviyesi = orijinal_ses_seviyesi_oku()
    print(f"   📊 Orijinal ses seviyesi: %{int(ses_seviyesi * 100)}")

    try:
        ozel_kaynaklar = _orijinal_ses_kaynaklarini_oku()
        toplam_sure = sum(float(getattr(clip, 'duration', 0) or 0) for clip in (video_clips or []))
        if ozel_kaynaklar:
            print("   🎼 Özel orijinal ses sırası aktif:")
            for idx, yol in enumerate(ozel_kaynaklar, start=1):
                print(f"      [{idx}] {os.path.basename(os.path.dirname(yol))}/{os.path.basename(yol)}")
            playlist_audio = _orijinal_ses_playlist_olustur(ozel_kaynaklar, toplam_sure, ses_seviyesi)
            if playlist_audio is not None:
                print(f"   ✅ Özel orijinal ses sırası toplam {toplam_sure:.1f}s için hazırlandı")
                return _cliplere_orijinal_ses_playlist_uygula(video_clips, playlist_audio)
            print("   ⚠️ Özel orijinal ses sırası uygulanamadı, mevcut davranışa dönülüyor...")

        yeni_clips = []
        eklenen_sayisi = 0

        for idx, (video_clip, video_dosya) in enumerate(zip(video_clips, video_dosya_isimleri)):
            ses_dosyasi = _orijinal_ses_dosyasi_bul(video_dosya)
            if ses_dosyasi:
                try:
                    orijinal_audio = AudioFileClip(ses_dosyasi)
                    if orijinal_audio.duration > video_clip.duration:
                        orijinal_audio = orijinal_audio.subclip(0, video_clip.duration)
                    elif orijinal_audio.duration < video_clip.duration:
                        from moviepy.audio.AudioClip import concatenate_audioclips
                        tekrar_sayisi = int(video_clip.duration / orijinal_audio.duration) + 1
                        orijinal_audio = concatenate_audioclips([orijinal_audio] * tekrar_sayisi)
                        orijinal_audio = orijinal_audio.subclip(0, video_clip.duration)

                    orijinal_audio = orijinal_audio.volumex(ses_seviyesi)

                    if video_clip.audio is not None:
                        yeni_ses = CompositeAudioClip([video_clip.audio, orijinal_audio])
                        video_clip = video_clip.set_audio(yeni_ses)
                    else:
                        video_clip = video_clip.set_audio(orijinal_audio)

                    numara = _video_numarasi_bul(video_dosya)
                    print(f"   ✓ Video {numara or idx+1}: Orijinal ses eklendi ({os.path.basename(ses_dosyasi)})")
                    eklenen_sayisi += 1
                except Exception as e:
                    numara = _video_numarasi_bul(video_dosya)
                    print(f"   ⚠️ Video {numara or idx+1}: Orijinal ses eklenemedi - {e}")
            else:
                numara = _video_numarasi_bul(video_dosya)
                print(f"   ⊖ Video {numara or idx+1}: Orijinal ses dosyası bulunamadı")

            yeni_clips.append(video_clip)

        print(f"   ✅ Toplam {eklenen_sayisi} videoya orijinal ses eklendi")
        return yeni_clips
    except Exception as e:
        print(f"   ❌ Orijinal ses hatası: {e}")
        return video_clips


def video_ses_ayarla(video_clips):
    """Montajlanacak videonun kendi sesini kısma/kapatma."""
    ses_seviyesi = video_ses_seviyesi_oku_toplu()
    if ses_seviyesi >= 1.0:
        return video_clips  # Değişiklik yok

    print(f"\n🔇 Video ses seviyesi ayarlanıyor: %{int(ses_seviyesi * 100)}")
    try:
        yeni_clips = []
        for idx, video_clip in enumerate(video_clips):
            if video_clip.audio is not None:
                if ses_seviyesi <= 0:
                    video_clip = video_clip.set_audio(None)
                    print(f"   🔇 Clip {idx+1}: Ses tamamen kapatıldı")
                else:
                    video_clip = video_clip.set_audio(video_clip.audio.volumex(ses_seviyesi))
                    print(f"   🔉 Clip {idx+1}: Ses %{int(ses_seviyesi * 100)} seviyesine ayarlandı")
            yeni_clips.append(video_clip)
        return yeni_clips
    except Exception as e:
        print(f"   ❌ Video ses ayarlama hatası: {e}")
        return video_clips


def ses_efekti_ekle(video_clips, video_dosya_isimleri):
    """Ses efekti ekle"""
    ses_efekti_dosyalari = []
    for uzanti in ['*.mp3', '*.wav', '*.m4a', '*.aac', '*.ogg']:
        ses_efekti_dosyalari.extend(glob.glob(os.path.join(ses_efekti_klasor, uzanti)))
    if not ses_efekti_dosyalari:
        return video_clips
    
    ses_seviyesi = ses_seviyesi_oku()
    ses_efekti_map = {}
    for ses_dosya in ses_efekti_dosyalari:
        basename = os.path.basename(ses_dosya)
        match = re.match(r'(\d+)', basename)
        if match:
            numara = match.group(1)
            ses_efekti_map[numara] = ses_dosya
    
    try:
        yeni_clips = []
        for video_clip, video_dosya in zip(video_clips, video_dosya_isimleri):
            video_basename = os.path.basename(video_dosya)
            match = re.match(r'(\d+)', video_basename)
            if match:
                video_numara = match.group(1)
                if video_numara in ses_efekti_map:
                    ses_efekti_dosya = ses_efekti_map[video_numara]
                    try:
                        ses_efekti_clip = AudioFileClip(ses_efekti_dosya)
                        if ses_efekti_clip.duration > video_clip.duration:
                            ses_efekti_clip = ses_efekti_clip.subclip(0, video_clip.duration)
                        elif ses_efekti_clip.duration < video_clip.duration:
                            from moviepy.audio.AudioClip import concatenate_audioclips
                            tekrar_sayisi = int(video_clip.duration / ses_efekti_clip.duration) + 1
                            ses_efekti_clip = concatenate_audioclips([ses_efekti_clip] * tekrar_sayisi)
                            ses_efekti_clip = ses_efekti_clip.subclip(0, video_clip.duration)
                        ses_efekti_clip = ses_efekti_clip.volumex(ses_seviyesi)
                        if video_clip.audio is not None:
                            yeni_ses = CompositeAudioClip([video_clip.audio, ses_efekti_clip])
                            video_clip = video_clip.set_audio(yeni_ses)
                        else:
                            video_clip = video_clip.set_audio(ses_efekti_clip)
                    except:
                        pass
            yeni_clips.append(video_clip)
        return yeni_clips
    except:
        return video_clips

def basliklari_al():
    if not os.path.exists(baslik_dosyasi):
        print(f"Hata: {baslik_dosyasi} bulunamadı!")
        return []
    with open(baslik_dosyasi, 'r', encoding='utf-8') as f:
        basliklar = [line.strip() for line in f if line.strip()]
    if not basliklar:
        print("Başlık.txt boş!")
        return []
    return basliklar

def kullanicidan_varyasyon_sec(indirilen_sayisi):
    """
    Kullanıcıdan hangi varyasyon gruplarını üretmek istediğini sor
    (Genişletildi: 2'den 20'ye kadar)
    """
    print("\n" + "="*80)
    print("HANGİ VARYASYON GRUPLARI ÜRETİLSİN?")
    print("="*80)
    
    # Mevcut seçenekleri göster
    print("\nMevcut seçenekler:")
    secenekler = []
    
    # Seçenekleri dinamik olarak ekle
    if indirilen_sayisi >= 2:
        print("  [2] İkili varyasyonlar")
        secenekler.append(2)
    if indirilen_sayisi >= 3:
        print("  [3] Üçlü varyasyonlar")
        secenekler.append(3)
    if indirilen_sayisi >= 4:
        print("  [4] Dörtlü varyasyonlar")
        secenekler.append(4)
    if indirilen_sayisi >= 5:
        print("  [5] Beşli varyasyonlar")
        secenekler.append(5)
    if indirilen_sayisi >= 6:
        print("  [6] Altılı varyasyonlar")
        secenekler.append(6)
    if indirilen_sayisi >= 7:
        print("  [7] Yedili varyasyonlar")
        secenekler.append(7)
    if indirilen_sayisi >= 8:
        print("  [8] Sekizli varyasyonlar")
        secenekler.append(8)
    if indirilen_sayisi >= 9:
        print("  [9] Dokuzlu varyasyonlar")
        secenekler.append(9)
    if indirilen_sayisi >= 10:
        print("  [10] Onlu varyasyonlar")
        secenekler.append(10)
    if indirilen_sayisi >= 11:
        print("  [11] On Birli varyasyonlar")
        secenekler.append(11)
    if indirilen_sayisi >= 12:
        print("  [12] On İkili varyasyonlar")
        secenekler.append(12)
    if indirilen_sayisi >= 13:
        print("  [13] On Üçlü varyasyonlar")
        secenekler.append(13)
    if indirilen_sayisi >= 14:
        print("  [14] On Dörtlü varyasyonlar")
        secenekler.append(14)
    if indirilen_sayisi >= 15:
        print("  [15] On Beşli varyasyonlar")
        secenekler.append(15)
    if indirilen_sayisi >= 16:
        print("  [16] On Altılı varyasyonlar")
        secenekler.append(16)
    if indirilen_sayisi >= 17:
        print("  [17] On Yedili varyasyonlar")
        secenekler.append(17)
    if indirilen_sayisi >= 18:
        print("  [18] On Sekizli varyasyonlar")
        secenekler.append(18)
    if indirilen_sayisi >= 19:
        print("  [19] On Dokuzlu varyasyonlar")
        secenekler.append(19)
    if indirilen_sayisi >= 20:
        print("  [20] Yirmili varyasyonlar")
        secenekler.append(20)
    
    print("\n📝 KULLANIM:")
    print("  • Tamamını üretmek için: t veya T")
    print("  • Tek grup için: 2 veya 3 veya ... veya 20")
    print("  • Birden fazla grup için: 2,3 veya 2,5 veya 3,4,5,10,15,20")
    print("  • Efektler için harf ekleyin: M (müzik), C (çerçeve), L (logo), V (video), S (ses), O (orijinal ses)")
    print("    Örnek: '2,3,m' veya 't,m' veya '10,15,20,m,c,l,v,s'")
    
    while True:
        secim = input("\n👉 Seçiminiz: ").strip().upper()
        
        if not secim:
            print("❌ Lütfen bir seçim yapın!")
            continue
        
        # Efekt kontrolü
        muzik_ekle = 'M' in secim
        cerceve_ekle = 'C' in secim
        logo_ekle = 'L' in secim
        video_ekle = 'V' in secim
        ses_efekti_ekle = 'S' in secim
        orijinal_ses_ekle_flag = 'O' in secim
        
        # Harfleri ve ayıraçları temizle
        secim = secim.replace('M', '').replace('C', '').replace('L', '').replace('V', '').replace('S', '').replace('O', '').replace(',', ' ').replace(';', ' ').strip()
        
        # Return yapısı için temel dictionary
        result = {
            'ikili': False, 'uclu': False, 'dortlu': False, 'besli': False,
            'altili': False, 'yedili': False, 'sekizli': False, 'dokuzlu': False, 'onlu': False,
            'onbirli': False, 'onikili': False, 'onuclu': False, 'ondortlu': False, 'onbesli': False,
            'onaltili': False, 'onyedili': False, 'onsekizli': False, 'ondokuzlu': False, 'yirmili': False,
            'muzik': muzik_ekle, 'cerceve': cerceve_ekle, 'logo': logo_ekle,
            'video_overlay': video_ekle, 'ses_efekti': ses_efekti_ekle,
            'orijinal_ses': orijinal_ses_ekle_flag
        }
        
        # "T" veya "TAMAMI" -> Hepsini seç
        if secim in ['T', 'TAMAMI', 'TAMAMINI', 'HEPSİ', 'HEPSI', '']:
            if not secim and not (muzik_ekle or cerceve_ekle or logo_ekle or video_ekle or ses_efekti_ekle):
                print("❌ Geçerli bir seçim yapın!")
                continue
            
            # Tüm mevcut seçenekleri True yap
            result['ikili'] = indirilen_sayisi >= 2
            result['uclu'] = indirilen_sayisi >= 3
            result['dortlu'] = indirilen_sayisi >= 4
            result['besli'] = indirilen_sayisi >= 5
            result['altili'] = indirilen_sayisi >= 6
            result['yedili'] = indirilen_sayisi >= 7
            result['sekizli'] = indirilen_sayisi >= 8
            result['dokuzlu'] = indirilen_sayisi >= 9
            result['onlu'] = indirilen_sayisi >= 10
            result['onbirli'] = indirilen_sayisi >= 11
            result['onikili'] = indirilen_sayisi >= 12
            result['onuclu'] = indirilen_sayisi >= 13
            result['ondortlu'] = indirilen_sayisi >= 14
            result['onbesli'] = indirilen_sayisi >= 15
            result['onaltili'] = indirilen_sayisi >= 16
            result['onyedili'] = indirilen_sayisi >= 17
            result['onsekizli'] = indirilen_sayisi >= 18
            result['ondokuzlu'] = indirilen_sayisi >= 19
            result['yirmili'] = indirilen_sayisi >= 20
            return result
        
        # Sayıları ayıkla
        secim = secim.replace(',', ' ').replace(';', ' ')
        secilen_sayilar = []
        
        for s in secim.split():
            try:
                sayi = int(s)
                if sayi in secenekler:
                    secilen_sayilar.append(sayi)
                else:
                    print(f"⚠️ {sayi} geçerli bir seçenek değil!")
            except ValueError:
                print(f"⚠️ '{s}' geçerli bir sayı değil!")
        
        if secilen_sayilar:
            if 2 in secilen_sayilar: result['ikili'] = True
            if 3 in secilen_sayilar: result['uclu'] = True
            if 4 in secilen_sayilar: result['dortlu'] = True
            if 5 in secilen_sayilar: result['besli'] = True
            if 6 in secilen_sayilar: result['altili'] = True
            if 7 in secilen_sayilar: result['yedili'] = True
            if 8 in secilen_sayilar: result['sekizli'] = True
            if 9 in secilen_sayilar: result['dokuzlu'] = True
            if 10 in secilen_sayilar: result['onlu'] = True
            if 11 in secilen_sayilar: result['onbirli'] = True
            if 12 in secilen_sayilar: result['onikili'] = True
            if 13 in secilen_sayilar: result['onuclu'] = True
            if 14 in secilen_sayilar: result['ondortlu'] = True
            if 15 in secilen_sayilar: result['onbesli'] = True
            if 16 in secilen_sayilar: result['onaltili'] = True
            if 17 in secilen_sayilar: result['onyedili'] = True
            if 18 in secilen_sayilar: result['onsekizli'] = True
            if 19 in secilen_sayilar: result['ondokuzlu'] = True
            if 20 in secilen_sayilar: result['yirmili'] = True
            return result
        elif muzik_ekle or cerceve_ekle or logo_ekle or video_ekle or ses_efekti_ekle or orijinal_ses_ekle_flag:
             # Sadece efekt seçildiyse hepsi + efekt
            result['ikili'] = indirilen_sayisi >= 2
            result['uclu'] = indirilen_sayisi >= 3
            result['dortlu'] = indirilen_sayisi >= 4
            result['besli'] = indirilen_sayisi >= 5
            result['altili'] = indirilen_sayisi >= 6
            result['yedili'] = indirilen_sayisi >= 7
            result['sekizli'] = indirilen_sayisi >= 8
            result['dokuzlu'] = indirilen_sayisi >= 9
            result['onlu'] = indirilen_sayisi >= 10
            result['onbirli'] = indirilen_sayisi >= 11
            result['onikili'] = indirilen_sayisi >= 12
            result['onuclu'] = indirilen_sayisi >= 13
            result['ondortlu'] = indirilen_sayisi >= 14
            result['onbesli'] = indirilen_sayisi >= 15
            result['onaltili'] = indirilen_sayisi >= 16
            result['onyedili'] = indirilen_sayisi >= 17
            result['onsekizli'] = indirilen_sayisi >= 18
            result['ondokuzlu'] = indirilen_sayisi >= 19
            result['yirmili'] = indirilen_sayisi >= 20
            return result
        else:
            print("❌ Geçerli bir seçim yapın!")

def varyasyonlari_olustur(indirilen_sayisi, secimler):
    """
    İndirilen video sayısına göre MINIMUM BENZERLIK SISTEMI varyasyonlarını oluştur
    """
    tum_varyasyonlar = []
    
    # ========================== 2 VIDEO ==========================
    if indirilen_sayisi == 2:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [1,0]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")
    
    # ========================== 3 VIDEO ==========================
    elif indirilen_sayisi == 3:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,0], [1,2], [0,2], [2,1], [1,0]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")
            
        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [2,0,1], [1,2,0], [0,2,1], [2,1,0], [1,0,2]]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")
            
    # ========================== 4 VIDEO ==========================
    elif indirilen_sayisi == 4:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [0,2], [1,3], [0,3], [1,2], [2,0], [3,1], [2,1], [3,0]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")
            
        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,2,1], [0,2,3], [1,3,0], [2,0,1], [3,1,2],
                          [0,3,1], [2,1,3], [1,0,3], [3,0,2], [2,3,0], [1,2,0],
                          [0,1,3], [2,3,1], [1,0,2], [3,2,0], [0,3,2], [1,3,2],
                          [2,0,3], [3,1,0]]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")
            
        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [3,2,1,0], [0,2,1,3], [3,1,2,0], [0,3,2,1], [1,2,3,0],
                            [2,0,3,1], [1,3,0,2], [2,1,0,3], [3,0,1,2], [0,1,3,2], [2,3,0,1],
                            [1,0,2,3], [3,2,0,1], [0,2,3,1], [1,3,2,0], [2,0,1,3], [3,1,0,2],
                            [1,2,0,3], [2,3,1,0]]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

    # ========================== 5 VIDEO ==========================
    elif indirilen_sayisi == 5:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,0], [1,4], [3,2], [0,2], [4,3], [1,0], [2,4], [3,1]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")
            
        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,0], [2,3,1], [4,0,3], [1,2,4], [0,3,2], [4,1,0], [2,4,3],
                          [3,0,1], [1,4,2], [0,2,4], [3,1,4], [2,0,3], [4,3,1], [1,0,4], [0,4,3],
                          [2,1,0], [3,2,4], [4,2,1], [1,3,0]]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")
            
        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,3,2,1], [0,2,4,1], [3,1,4,0], [2,4,3,0], [1,0,3,2], [4,2,1,3],
                            [0,3,1,4], [2,1,0,4], [3,4,2,0], [1,2,3,4], [0,4,2,3], [3,0,4,1], [2,3,0,1],
                            [4,1,3,2], [0,1,4,3], [3,2,1,4], [1,4,0,2], [2,0,1,3], [4,0,3,1]]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")
            
        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [4,3,2,1,0], [0,2,4,1,3], [3,1,4,2,0], [2,4,1,3,0],
                           [1,3,0,2,4], [4,0,3,1,2], [2,1,4,0,3], [3,2,0,4,1], [1,4,3,0,2]]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")

    # ========================== 6 VIDEO ==========================
    elif indirilen_sayisi == 6:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [0,3], [1,4], [2,5], [3,4], [5,0], [1,2], [4,0]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")
            
        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [0,3,4], [1,2,5], [2,4,0], [5,1,3], [0,2,5], [3,1,4],
                          [4,5,1], [2,0,3], [1,4,2], [5,3,0], [0,4,1], [2,5,3], [4,0,5], [1,3,2],
                          [3,5,4], [0,5,2], [2,1,4], [5,4,0]]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")
        
        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,0,2], [1,3,4,5], [2,4,1,0], [3,5,2,4], [0,2,5,1], [4,1,3,0],
                            [5,0,4,2], [1,4,0,3], [2,5,1,4], [3,0,5,2], [4,2,3,1], [0,3,1,5], [5,1,2,0],
                            [2,4,5,3], [1,0,4,2], [3,2,0,4], [5,3,1,0], [0,4,3,5], [2,1,5,4]]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")
        
        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,4,3,2,1], [0,2,4,1,5], [3,5,1,4,0], [2,4,5,0,3], [1,3,0,5,2],
                           [4,0,3,2,5], [5,2,1,4,3], [0,5,3,1,4], [2,1,4,3,0], [3,4,0,2,1], [1,5,2,0,4],
                           [4,3,5,1,2], [0,4,1,5,3], [5,0,2,3,1], [2,3,4,0,5], [1,2,5,4,0], [3,1,0,4,5],
                           [4,5,3,0,2], [0,3,2,5,4]]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")
        
        if secimler['altili']:
            print("\n🎬 Altılı varyasyonlar oluşturuluyor...")
            altili_liste = [[0,1,2,3,4,5], [5,4,3,2,1,0], [0,2,4,1,3,5], [3,5,1,4,0,2], [2,4,0,5,3,1],
                            [1,3,5,0,2,4], [4,0,3,5,2,1], [5,2,1,3,4,0], [0,4,2,1,5,3], [3,1,5,4,0,2]]
            for perm in altili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(altili_liste)} altılı varyasyon eklendi")

    # ========================== 7 VIDEO ==========================
    elif indirilen_sayisi == 7:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [6,0], [1,4], [3,6], [5,2], [0,3], [4,6], [2,1]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")
            
        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [6,0,3], [1,4,6], [2,5,0], [4,6,1], [5,2,3], [0,5,4],
                          [3,1,6], [2,4,0], [6,5,2], [1,3,5], [4,0,2], [5,6,3], [0,4,1], [2,6,5],
                          [3,0,4], [1,5,6], [6,2,1], [4,3,0]]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,6,0], [1,3,5,2], [6,2,4,1], [0,4,3,5], [2,6,1,4], [5,0,6,3],
                            [3,5,0,2], [1,6,4,0], [4,2,5,6], [0,3,6,1], [5,1,2,4], [2,4,0,6], [6,5,3,1],
                            [1,0,5,3], [3,4,1,6], [0,6,2,5], [4,1,3,2], [5,3,4,0], [2,0,6,4]]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,6,0,2,1], [3,5,4,6,0], [1,4,6,2,5], [2,0,5,1,6], [6,3,1,4,2],
                           [4,5,0,3,1], [0,6,2,4,5], [5,1,3,0,6], [2,4,6,5,3], [1,3,5,2,0], [6,0,4,1,3],
                           [3,2,1,5,4], [4,6,3,0,2], [0,5,6,4,1], [5,2,0,6,3], [1,6,4,3,5], [2,3,5,1,0],
                           [6,4,2,0,5], [3,0,1,6,4]]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")

        if secimler['altili']:
            print("\n🎬 Altılı varyasyonlar oluşturuluyor...")
            altili_liste = [[0,1,2,3,4,5], [6,5,4,3,2,1], [0,2,4,6,1,3], [5,3,1,4,6,0], [2,5,0,6,3,4],
                            [1,4,6,2,5,0], [3,0,5,1,4,6], [6,2,3,5,0,1], [4,6,1,0,2,5], [5,1,3,4,6,2]]
            for perm in altili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(altili_liste)} altılı varyasyon eklendi")

        if secimler['yedili']:
            print("\n🎬 Yedili varyasyonlar oluşturuluyor...")
            yedili_liste = [[0,1,2,3,4,5,6], [6,5,4,3,2,1,0], [0,2,4,6,1,3,5], [5,3,1,4,6,0,2], [2,5,0,3,6,4,1],
                            [1,4,6,2,5,3,0], [3,0,5,1,4,2,6], [6,2,3,5,0,4,1], [4,6,1,0,3,5,2], [5,1,3,6,2,0,4]]
            for perm in yedili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(yedili_liste)} yedili varyasyon eklendi")

    # ========================== 8 VIDEO ==========================
    elif indirilen_sayisi == 8:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [6,7], [0,4], [1,5], [2,6], [3,7], [0,2], [4,6]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")

        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [6,7,0], [1,3,6], [4,2,7], [5,6,1], [7,0,4], [2,5,3],
                          [6,4,1], [0,5,7], [3,6,2], [1,7,4], [5,0,3], [2,4,6], [7,1,5], [4,3,0],
                          [6,0,5], [1,2,7], [3,5,4], [7,6,2]]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,6,7], [0,2,4,6], [1,3,5,7], [0,4,1,5], [2,6,3,7], [0,3,6,1],
                            [4,7,2,5], [1,5,3,0], [6,2,7,4], [0,5,2,7], [3,1,6,4], [5,3,4,2], [7,0,1,6],
                            [2,4,7,1], [6,5,0,3], [1,6,4,0], [3,2,5,6], [4,0,7,3], [5,7,1,2]]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,6,7,0,1], [2,4,6,1,5], [7,3,5,0,6], [1,5,3,7,2], [4,0,6,2,7],
                           [6,3,1,4,0], [5,7,4,2,3], [0,6,5,1,4], [2,1,7,5,6], [3,4,0,6,5], [7,2,6,4,1],
                           [1,4,7,3,0], [5,0,2,6,3], [4,6,3,5,7], [0,3,5,2,1], [6,1,4,7,5], [2,7,0,4,6],
                           [3,5,1,0,2], [7,4,6,3,1]]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")
        
        if secimler['altili']:
            print("\n🎬 Altılı varyasyonlar oluşturuluyor...")
            altili_liste = [[0,1,2,3,4,5], [6,7,0,2,4,1], [3,5,6,1,7,0], [4,0,5,7,2,6], [1,6,3,4,0,7],
                            [5,2,7,0,6,3], [7,4,1,5,3,2], [0,5,4,6,1,2], [2,3,6,7,5,4], [6,0,7,1,4,3]]
            for perm in altili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(altili_liste)} altılı varyasyon eklendi")

        if secimler['yedili']:
            print("\n🎬 Yedili varyasyonlar oluşturuluyor...")
            yedili_liste = [[0,1,2,3,4,5,6], [7,6,5,4,3,2,1], [0,2,4,6,1,3,5], [7,5,3,1,6,4,0], [2,4,7,0,5,1,6],
                            [3,6,1,5,0,7,2], [5,0,6,2,7,3,4], [1,7,4,6,2,0,5], [4,3,5,7,1,6,0], [6,1,0,4,3,5,7]]
            for perm in yedili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(yedili_liste)} yedili varyasyon eklendi")

        if secimler['sekizli']:
            print("\n🎬 Sekizli varyasyonlar oluşturuluyor...")
            sekizli_liste = [[0,1,2,3,4,5,6,7], [7,6,5,4,3,2,1,0], [0,2,4,6,1,3,5,7], [7,5,3,1,6,4,2,0], [2,4,6,0,5,7,1,3],
                             [3,6,1,5,0,4,7,2], [5,0,7,2,6,3,1,4], [1,7,4,6,2,5,0,3], [4,3,5,7,0,2,6,1], [6,1,3,0,7,4,2,5]]
            for perm in sekizli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(sekizli_liste)} sekizli varyasyon eklendi")

    # ========================== 9 VIDEO ==========================
    elif indirilen_sayisi == 9:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [6,7], [8,0], [1,4], [3,6], [5,8], [7,2], [0,5]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")

        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [6,7,8], [0,3,6], [1,4,7], [2,5,8], [0,4,8], [1,5,6],
                          [2,3,7], [4,6,0], [5,7,1], [8,2,4], [3,1,5], [6,8,2], [7,0,3], [1,8,4],
                          [0,7,5], [2,6,1], [4,3,8], [5,0,6]]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,6,7], [8,0,2,4], [1,3,5,7], [6,8,1,3], [0,4,6,2], [5,7,0,8],
                            [2,6,4,1], [3,8,5,0], [7,1,6,4], [0,5,3,8], [2,7,1,6], [4,0,7,5], [8,3,2,1],
                            [1,6,8,4], [5,2,0,7], [3,4,1,6], [6,0,5,3], [7,8,4,2], [1,2,8,5]]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,6,7,8,0], [1,3,5,7,2], [8,4,6,1,5], [2,7,0,4,6], [3,8,1,5,0],
                           [6,2,4,8,3], [0,5,7,2,1], [4,1,8,3,6], [7,3,0,5,4], [1,6,4,0,8], [5,0,3,6,2],
                           [8,2,5,1,7], [3,7,6,4,0], [0,4,2,8,5], [6,1,7,3,4], [2,8,0,6,1], [5,3,4,7,8],
                           [1,7,5,2,0], [4,6,3,0,7]]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")

        if secimler['altili']:
            print("\n🎬 Altılı varyasyonlar oluşturuluyor...")
            altili_liste = [[0,1,2,3,4,5], [6,7,8,0,2,4], [1,5,3,7,6,0], [8,4,6,1,5,2], [3,0,7,4,8,1],
                            [5,2,1,6,0,7], [7,6,4,2,3,8], [0,8,5,7,1,3], [4,3,0,5,6,2], [2,1,8,4,7,6]]
            for perm in altili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(altili_liste)} altılı varyasyon eklendi")

        if secimler['yedili']:
            print("\n🎬 Yedili varyasyonlar oluşturuluyor...")
            yedili_liste = [[0,1,2,3,4,5,6], [7,8,0,2,4,6,1], [3,5,7,1,8,0,4], [6,2,4,8,3,7,0], [1,6,0,5,7,2,8],
                            [5,3,8,1,6,4,2], [0,7,4,6,2,1,5], [8,1,5,3,0,6,7], [2,4,6,0,5,8,3], [7,0,3,5,1,4,6]]
            for perm in yedili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(yedili_liste)} yedili varyasyon eklendi")
            
        if secimler['sekizli']:
            print("\n🎬 Sekizli varyasyonlar oluşturuluyor...")
            sekizli_liste = [[0,1,2,3,4,5,6,7], [8,7,6,5,4,3,2,1], [0,2,4,6,8,1,3,5], [7,5,3,1,6,4,2,0], [8,0,5,2,7,4,1,6],
                             [3,6,1,8,4,7,0,5], [5,3,7,0,6,2,8,4], [1,8,4,7,3,6,0,2], [6,2,0,5,1,8,7,3], [4,7,5,1,0,3,6,8]]
            for perm in sekizli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(sekizli_liste)} sekizli varyasyon eklendi")
            
        if secimler['dokuzlu']:
            print("\n🎬 Dokuzlu varyasyonlar oluşturuluyor...")
            dokuzlu_liste = [[0,1,2,3,4,5,6,7,8], [8,7,6,5,4,3,2,1,0], [0,3,6,1,4,7,2,5,8], [8,5,2,7,4,1,6,3,0], [1,4,7,0,3,6,8,2,5],
                             [5,8,2,6,0,4,1,7,3], [3,0,5,1,7,2,8,4,6], [6,2,8,4,1,5,0,7,3], [7,4,1,6,3,0,5,8,2], [2,6,3,8,5,1,4,0,7]]
            for perm in dokuzlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dokuzlu_liste)} dokuzlu varyasyon eklendi")

    # ========================== 10 VIDEO ==========================
    elif indirilen_sayisi == 10:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [6,7], [8,9], [0,5], [1,6], [2,7], [3,8], [4,9]]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")

        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [6,7,8], [9,0,3], [1,4,7], [2,5,8], [6,9,1], [0,4,8],
                          [3,7,2], [5,9,4], [1,6,0], [8,3,5], [2,9,7], [4,0,6], [7,1,9], [5,8,3],
                          [0,6,4], [9,2,1], [3,5,7], [8,4,6]]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,6,7], [8,9,0,2], [1,3,5,7], [9,4,6,1], [0,5,8,3], [2,7,4,9],
                            [6,1,3,8], [5,9,2,4], [7,0,6,5], [3,8,1,4], [9,2,7,0], [4,6,9,1], [0,7,5,2],
                            [8,3,0,6], [1,9,4,7], [5,2,8,6], [3,6,1,9], [7,4,0,8], [2,5,3,1]]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,6,7,8,9], [0,2,4,6,8], [1,3,5,7,9], [0,5,1,6,2], [7,3,8,4,9],
                           [2,6,9,1,5], [4,0,7,3,8], [9,5,2,6,1], [3,8,0,4,7], [1,7,4,9,5], [6,2,8,3,0],
                           [5,9,3,7,2], [0,4,1,8,6], [9,6,4,1,3], [2,7,5,0,8], [8,1,6,4,0], [3,9,7,2,5],
                           [4,8,0,9,6], [7,5,1,3,2]]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")
            
        if secimler['altili']:
            print("\n🎬 Altılı varyasyonlar oluşturuluyor...")
            altili_liste = [[0,1,2,3,4,5], [6,7,8,9,0,2], [4,6,1,3,5,7], [9,8,5,2,6,0], [1,4,7,0,8,3],
                            [5,9,2,6,1,4], [3,0,8,5,7,9], [7,2,4,1,9,6], [0,6,3,8,2,5], [8,5,9,4,0,1]]
            for perm in altili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(altili_liste)} altılı varyasyon eklendi")
            
        if secimler['yedili']:
            print("\n🎬 Yedili varyasyonlar oluşturuluyor...")
            yedili_liste = [[0,1,2,3,4,5,6], [7,8,9,0,2,4,6], [1,3,5,7,9,2,0], [8,6,4,1,5,3,7], [9,0,7,2,6,8,4],
                            [3,5,1,8,0,6,9], [4,9,6,3,7,1,2], [0,8,4,6,1,5,3], [5,2,9,7,3,0,8], [6,4,0,9,5,2,1]]
            for perm in yedili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(yedili_liste)} yedili varyasyon eklendi")
            
        if secimler['sekizli']:
            print("\n🎬 Sekizli varyasyonlar oluşturuluyor...")
            sekizli_liste = [[0,1,2,3,4,5,6,7], [8,9,0,2,4,6,1,3], [5,7,9,1,3,8,0,4], [6,4,8,5,2,7,9,1], [0,3,7,9,6,2,5,8],
                             [1,6,4,0,8,3,7,2], [9,5,2,6,1,4,0,7], [3,8,1,5,7,0,9,6], [7,2,6,4,9,1,8,5], [4,0,5,8,3,6,2,9]]
            for perm in sekizli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(sekizli_liste)} sekizli varyasyon eklendi")
            
        if secimler['dokuzlu']:
            print("\n🎬 Dokuzlu varyasyonlar oluşturuluyor...")
            dokuzlu_liste = [[0,1,2,3,4,5,6,7,8], [9,8,7,6,5,4,3,2,1], [0,2,4,6,8,1,3,5,7], [9,7,5,3,1,8,6,4,2], [0,5,1,6,2,7,3,8,4],
                             [9,4,8,3,7,2,6,1,5], [1,3,7,0,4,9,5,2,8], [6,9,2,5,8,0,4,7,1], [3,8,4,1,6,5,0,9,7], [7,1,9,4,0,6,8,2,5]]
            for perm in dokuzlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dokuzlu_liste)} dokuzlu varyasyon eklendi")
            
        if secimler['onlu']:
            print("\n🎬 Onlu varyasyonlar oluşturuluyor...")
            onlu_liste = [[0,1,2,3,4,5,6,7,8,9], [10,11,12,13,14,15,16,17,18,19], [0,2,4,6,8,10,12,14,16,18], [1,3,5,7,9,11,13,15,17,19], [0,5,10,15,4,9,14,19,8,13],
                          [2,7,12,17,6,11,16,1,10,15], [0,10,4,14,8,18,2,12,6,16], [1,11,5,15,9,19,3,13,7,17], [0,8,16,4,12,2,10,18,6,14], [1,9,17,5,13,3,11,19,7,15]][:LIMIT_ONLU]
            for perm in onlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onlu_liste)} onlu varyasyon eklendi")

    # ========================== 11 VIDEO ==========================
    elif indirilen_sayisi == 11:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [6,7], [8,9], [10,0], [1,4], [3,6], [5,8], [7,10]][:LIMIT_IKILI]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")

        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [6,7,8], [9,10,0], [2,4,6], [8,1,3], [5,7,9], [0,6,10],
                          [4,8,2], [1,5,9], [3,7,0], [10,4,8], [6,2,1], [9,5,3], [7,0,4], [1,10,6],
                          [8,3,5], [2,9,7], [4,1,0], [10,5,8]][:LIMIT_UCLU]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,6,7], [8,9,10,0], [2,4,6,8], [1,3,5,7], [9,0,10,4],
                            [6,2,8,1], [3,9,5,10], [7,4,0,6], [1,8,3,9], [5,2,10,7], [0,6,4,1],
                            [9,3,7,2], [8,10,5,0], [4,1,6,9], [2,7,3,8], [10,5,1,4], [6,0,9,3],
                            [7,2,4,10], [1,8,5,6]][:LIMIT_DORTLU]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,6,7,8,9], [10,0,2,4,6], [8,1,3,5,7], [9,4,6,1,3], [0,5,10,2,7],
                           [4,8,1,9,6], [3,7,0,5,10], [2,6,9,4,1], [8,3,5,0,7], [10,4,2,8,6], [1,9,7,3,5],
                           [6,0,4,10,2], [5,1,8,7,9], [3,6,10,1,4], [9,2,5,8,0], [7,4,1,6,3], [10,8,0,9,5],
                           [2,7,3,1,6], [4,9,5,2,10]][:LIMIT_BESLI]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")
            
        if secimler['altili']:
            print("\n🎬 Altılı varyasyonlar oluşturuluyor...")
            altili_liste = [[0,1,2,3,4,5], [6,7,8,9,10,0], [2,4,6,8,10,1], [3,5,7,9,0,4], [6,1,8,3,10,5],
                            [2,7,4,9,1,6], [8,0,5,3,7,2], [10,6,1,4,9,8], [5,3,0,7,2,10], [4,9,6,1,8,3]][:LIMIT_ALTILI]
            for perm in altili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(altili_liste)} altılı varyasyon eklendi")
            
        if secimler['yedili']:
            print("\n🎬 Yedili varyasyonlar oluşturuluyor...")
            yedili_liste = [[0,1,2,3,4,5,6], [7,8,9,10,0,2,4], [6,1,3,5,7,9,10], [8,0,6,2,10,4,1],
                            [3,7,5,9,1,6,8], [10,4,2,8,6,0,5], [1,9,7,3,0,10,2], [5,6,4,1,8,3,7],
                            [9,2,10,5,7,4,0], [6,8,1,0,3,9,5]][:LIMIT_YEDILI]
            for perm in yedili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(yedili_liste)} yedili varyasyon eklendi")
            
        if secimler['sekizli']:
            print("\n🎬 Sekizli varyasyonlar oluşturuluyor...")
            sekizli_liste = [[0,1,2,3,4,5,6,7], [8,9,10,0,2,4,6,1], [3,5,7,9,10,8,2,4], [6,1,8,3,0,5,9,7],
                             [10,4,2,7,5,1,8,6], [0,9,3,6,10,4,1,5], [7,2,8,5,1,9,3,0], [4,10,6,2,9,7,0,8],
                             [1,5,9,4,8,3,10,6], [2,7,0,10,5,6,4,1]][:LIMIT_SEKIZLI]
            for perm in sekizli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(sekizli_liste)} sekizli varyasyon eklendi")
            
        if secimler['dokuzlu']:
            print("\n🎬 Dokuzlu varyasyonlar oluşturuluyor...")
            dokuzlu_liste = [[0,1,2,3,4,5,6,7,8], [9,10,0,2,4,6,8,1,3], [5,7,9,10,2,4,6,0,8],
                             [1,3,8,5,10,7,9,2,4], [6,0,4,8,1,9,5,3,7], [10,2,7,3,6,1,0,8,5],
                             [4,9,5,1,8,0,3,10,6], [7,3,10,6,2,9,4,5,1], [8,1,6,4,0,7,10,2,9],
                             [5,10,3,9,7,2,6,1,0]][:LIMIT_DOKUZLU]
            for perm in dokuzlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dokuzlu_liste)} dokuzlu varyasyon eklendi")
            
        if secimler['onlu']:
            print("\n🎬 Onlu varyasyonlar oluşturuluyor...")
            onlu_liste = [[0,1,2,3,4,5,6,7,8,9], [10,9,8,7,6,5,4,3,2,1], [0,2,4,6,8,10,1,3,5,7], [9,7,5,3,1,8,6,4,2,0], 
                          [0,5,10,2,7,3,8,4,9,1], [6,1,9,4,0,5,10,3,8,2], [7,2,6,10,5,1,4,9,3,8], [3,8,1,6,0,9,5,10,7,4],
                          [10,4,9,2,7,6,1,8,3,5], [5,0,8,3,1,4,9,7,2,6]][:LIMIT_ONLU]
            for perm in onlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onlu_liste)} onlu varyasyon eklendi")

        if secimler['onbirli']:
            print("\n🎬 On Birli varyasyonlar oluşturuluyor...")
            onbirli_liste = [[0,1,2,3,4,5,6,7,8,9,10], [11,12,13,14,15,16,17,18,19,0,2], [4,6,8,10,12,14,16,18,1,3,5], [7,9,11,13,15,17,19,4,6,8,10], [0,10,2,12,4,14,6,16,8,18,1],
                            [11,3,13,5,15,7,17,9,19,0,12], [2,14,4,16,6,18,8,1,10,3,13], [5,15,7,17,9,19,11,0,12,2,14], [4,16,6,0,8,10,18,3,13,5,15], [7,17,9,1,11,3,19,6,16,8,0]][:LIMIT_ONBIRLI]
            for perm in onbirli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onbirli_liste)} on birli varyasyon eklendi")


    # ========================== 12 VIDEO ==========================
    elif indirilen_sayisi == 12:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [6,7], [8,9], [10,11], [0,6], [1,7], [2,8], [3,9]][:LIMIT_IKILI]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")

        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [6,7,8], [9,10,11], [0,4,8], [1,5,9], [2,6,10], [3,7,11],
                          [0,3,6], [9,1,4], [7,10,2], [5,8,11], [0,5,10], [3,8,1], [6,11,4], [9,2,7],
                          [1,6,11], [4,9,2], [7,0,5], [10,3,8]][:LIMIT_UCLU]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,6,7], [8,9,10,11], [0,4,8,1], [5,2,9,6], [3,10,7,11], [0,5,10,3],
                            [8,1,4,9], [2,11,6,7], [0,6,1,7], [2,8,3,9], [4,10,5,11], [0,7,2,9], [4,11,6,1],
                            [8,3,10,5], [1,6,11,4], [9,2,7,0], [3,5,8,10], [6,9,4,1], [11,7,2,5]][:LIMIT_DORTLU]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,6,7,8,9], [10,11,0,2,4], [6,8,1,3,5], [7,9,11,4,6], [0,8,2,10,5],
                           [1,9,3,11,7], [4,6,0,8,10], [2,5,7,1,9], [3,11,6,4,8], [0,7,10,2,5], [1,8,11,3,6],
                           [4,9,0,7,2], [5,10,1,8,3], [6,11,4,9,0], [7,2,5,10,1], [8,3,6,11,4], [9,0,7,2,5],
                           [10,1,8,3,6], [11,4,9,0,7]][:LIMIT_BESLI]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")
            
        if secimler['altili']:
            print("\n🎬 Altılı varyasyonlar oluşturuluyor...")
            altili_liste = [[0,1,2,3,4,5], [6,7,8,9,10,11], [0,2,4,6,8,10], [1,3,5,7,9,11], [0,6,1,7,2,8],
                            [3,9,4,10,5,11], [0,4,8,2,6,10], [1,5,9,3,7,11], [0,5,10,1,6,11], [2,7,3,8,4,9]][:LIMIT_ALTILI]
            for perm in altili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(altili_liste)} altılı varyasyon eklendi")
            
        if secimler['yedili']:
            print("\n🎬 Yedili varyasyonlar oluşturuluyor...")
            yedili_liste = [[0,1,2,3,4,5,6], [7,8,9,10,11,0,2], [4,6,8,10,1,3,5], [7,9,11,2,4,6,8], [0,10,3,5,7,9,11],
                            [1,4,8,0,6,2,10], [3,7,11,5,9,1,4], [6,0,8,2,10,4,7], [9,1,5,11,3,8,0], [2,6,10,4,7,9,5]][:LIMIT_YEDILI]
            for perm in yedili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(yedili_liste)} yedili varyasyon eklendi")
            
        if secimler['sekizli']:
            print("\n🎬 Sekizli varyasyonlar oluşturuluyor...")
            sekizli_liste = [[0,1,2,3,4,5,6,7], [8,9,10,11,0,2,4,6], [1,3,5,7,9,11,8,10], [2,4,6,0,8,10,1,3],
                             [5,7,9,11,2,4,6,8], [0,8,1,9,2,10,3,11], [4,6,5,7,0,8,1,9], [2,10,3,11,4,6,5,7],
                             [0,9,1,10,2,11,3,8], [4,5,6,7,8,9,10,0]][:LIMIT_SEKIZLI]
            for perm in sekizli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(sekizli_liste)} sekizli varyasyon eklendi")
            
        if secimler['dokuzlu']:
            print("\n🎬 Dokuzlu varyasyonlar oluşturuluyor...")
            dokuzlu_liste = [[0,1,2,3,4,5,6,7,8], [9,10,11,0,2,4,6,8,1], [3,5,7,9,11,4,6,8,10], [2,0,10,5,7,9,11,1,3],
                             [6,8,1,4,0,10,2,9,7], [5,11,3,8,6,1,4,0,10], [9,2,7,0,5,11,3,8,6], [1,4,10,9,2,7,0,5,11],
                             [3,8,6,1,4,10,9,2,7], [0,5,11,3,8,6,1,4,10]][:LIMIT_DOKUZLU]
            for perm in dokuzlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dokuzlu_liste)} dokuzlu varyasyon eklendi")
            
        if secimler['onlu']:
            print("\n🎬 Onlu varyasyonlar oluşturuluyor...")
            onlu_liste = [[0,1,2,3,4,5,6,7,8,9], [10,11,0,2,4,6,8,1,3,5], [7,9,11,4,6,8,10,2,5,0], [3,1,7,9,11,5,0,4,8,2],
                          [6,10,3,1,7,9,11,5,0,4], [8,2,6,10,3,1,7,9,11,5], [0,4,8,2,6,10,3,1,7,9], [11,5,0,4,8,2,6,10,3,1],
                          [7,9,11,5,0,4,8,2,6,10], [3,1,7,9,11,5,0,4,8,2]][:LIMIT_ONLU]
            for perm in onlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onlu_liste)} onlu varyasyon eklendi")

        if secimler['onbirli']:
            print("\n🎬 On Birli varyasyonlar oluşturuluyor...")
            onbirli_liste = [[0,1,2,3,4,5,6,7,8,9,10], [11,10,9,8,7,6,5,4,3,2,1], [0,2,4,6,8,10,1,3,5,7,9], [11,9,7,5,3,1,10,8,6,4,2],
                            [0,6,1,7,2,8,3,9,4,10,5], [11,5,10,4,9,3,8,2,7,1,6], [0,5,10,2,7,1,6,11,4,9,3], [8,3,9,4,10,5,0,6,1,7,2],
                            [11,7,2,8,3,9,4,10,5,0,6], [1,6,11,5,10,4,9,3,8,2,7]][:LIMIT_ONBIRLI]
            for perm in onbirli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onbirli_liste)} on birli varyasyon eklendi")

        if secimler['onikili']:
            print("\n🎬 On İkili varyasyonlar oluşturuluyor...")
            onikili_liste = [[0,1,2,3,4,5,6,7,8,9,10,11], [12,13,14,15,16,17,18,19,0,2,4,6], [8,10,12,14,16,18,1,3,5,7,9,11], [13,15,17,19,4,6,8,10,12,0,2,14], [16,18,1,3,5,7,9,11,13,15,17,19],
                            [0,6,12,18,4,10,16,2,8,14,1,7], [13,19,5,11,17,3,9,15,0,6,12,18], [4,10,16,2,8,14,1,7,13,19,5,11], [17,3,9,15,0,6,12,18,4,10,16,2], [8,14,1,7,13,19,5,11,17,3,9,15]][:LIMIT_ONIKILI]
            for perm in onikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onikili_liste)} on ikili varyasyon eklendi")


    # ========================== 13 VIDEO ==========================
    elif indirilen_sayisi == 13:
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [6,7], [8,9], [10,11], [12,0], [1,6], [3,8], [5,10]][:LIMIT_IKILI]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")

        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [6,7,8], [9,10,11], [12,0,3], [6,1,4], [7,2,5], [8,3,9],
                          [10,4,0], [11,5,1], [12,6,2], [0,7,3], [4,8,10], [1,9,11], [5,12,6], [2,0,7],
                          [3,4,8], [9,5,1], [10,6,2], [11,7,12]][:LIMIT_UCLU]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,6,7], [8,9,10,11], [12,0,4,8], [1,5,9,2], [6,10,3,7], [11,12,0,5],
                            [9,1,4,10], [2,6,11,3], [7,12,8,0], [4,1,9,5], [2,10,6,12], [0,3,7,11], [8,4,12,1],
                            [9,6,2,5], [10,7,3,0], [11,8,4,12], [1,9,6,2], [5,10,7,3], [0,11,8,4]][:LIMIT_DORTLU]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,6,7,8,9], [10,11,12,0,2], [4,6,8,1,3], [5,7,9,11,12], [0,10,4,8,2],
                           [6,1,11,5,9], [3,12,7,2,10], [4,8,0,6,1], [11,5,9,3,12], [7,2,10,4,8], [0,6,1,11,5],
                           [9,3,12,7,2], [10,4,8,0,6], [1,11,5,9,3], [12,7,2,10,4], [8,0,6,1,11], [5,9,3,12,7],
                           [2,10,4,8,0], [6,1,11,5,9]][:LIMIT_BESLI]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")
            
        if secimler['altili']:
            print("\n🎬 Altılı varyasyonlar oluşturuluyor...")
            altili_liste = [[0,1,2,3,4,5], [6,7,8,9,10,11], [12,0,2,4,6,8], [10,1,3,5,7,9], [11,12,4,6,8,10],
                            [0,2,5,7,9,11], [1,3,6,8,10,12], [0,4,7,9,11,2], [5,8,10,12,1,3], [6,9,11,0,2,4]][:LIMIT_ALTILI]
            for perm in altili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(altili_liste)} altılı varyasyon eklendi")
            
        if secimler['yedili']:
            print("\n🎬 Yedili varyasyonlar oluşturuluyor...")
            yedili_liste = [[0,1,2,3,4,5,6], [7,8,9,10,11,12,0], [2,4,6,8,10,12,1], [3,5,7,9,11,0,4],
                            [6,8,10,12,2,5,7], [9,11,0,3,6,8,10], [1,4,7,9,11,12,2], [5,8,10,0,3,6,9],
                            [11,1,4,7,12,2,5], [8,0,3,6,9,11,4]][:LIMIT_YEDILI]
            for perm in yedili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(yedili_liste)} yedili varyasyon eklendi")
            
        if secimler['sekizli']:
            print("\n🎬 Sekizli varyasyonlar oluşturuluyor...")
            sekizli_liste = [[0,1,2,3,4,5,6,7], [8,9,10,11,12,0,2,4], [6,8,10,12,1,3,5,7], [9,11,0,2,4,6,8,10],
                             [12,1,3,5,7,9,11,0], [2,4,6,8,10,12,1,3], [5,7,9,11,0,2,4,6], [8,10,12,1,3,5,7,9],
                             [11,0,2,4,6,8,10,12], [1,3,5,7,9,11,0,2]][:LIMIT_SEKIZLI]
            for perm in sekizli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(sekizli_liste)} sekizli varyasyon eklendi")
            
        if secimler['dokuzlu']:
            print("\n🎬 Dokuzlu varyasyonlar oluşturuluyor...")
            dokuzlu_liste = [[0,1,2,3,4,5,6,7,8], [9,10,11,12,0,2,4,6,8], [1,3,5,7,9,11,12,4,6], [8,10,0,2,5,7,9,11,1],
                             [3,6,8,10,12,2,4,7,9], [11,1,3,5,8,0,6,10,12], [2,4,7,9,11,1,3,6,8], [0,5,10,12,2,4,7,9,11],
                             [1,3,6,8,0,5,10,12,2], [4,7,9,11,1,3,6,8,0]][:LIMIT_DOKUZLU]
            for perm in dokuzlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dokuzlu_liste)} dokuzlu varyasyon eklendi")
            
        if secimler['onlu']:
            print("\n🎬 Onlu varyasyonlar oluşturuluyor...")
            onlu_liste = [[0,1,2,3,4,5,6,7,8,9], [10,11,12,0,2,4,6,8,1,3], [5,7,9,11,12,2,4,6,8,10], 
                          [0,3,5,7,9,11,1,4,6,8], [10,12,2,4,7,9,0,3,5,11], [1,6,8,10,0,2,5,7,9,12],
                          [3,4,6,8,11,1,0,2,10,5], [7,9,12,3,6,8,0,4,1,11], [2,5,10,7,1,4,9,6,12,3],
                          [8,0,11,5,2,10,7,3,4,9]][:LIMIT_ONLU]
            for perm in onlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onlu_liste)} onlu varyasyon eklendi")

        if secimler['onbirli']:
            print("\n🎬 On Birli varyasyonlar oluşturuluyor...")
            onbirli_liste = [[0,1,2,3,4,5,6,7,8,9,10], [11,12,0,2,4,6,8,10,1,3,5], [7,9,11,12,4,6,8,10,0,2,5],
                            [3,1,7,9,11,5,0,4,8,10,2], [6,12,3,1,7,9,11,5,0,4,8], [10,2,6,12,3,1,7,9,11,5,0],
                            [4,8,10,2,6,12,3,1,7,9,11], [5,0,4,8,10,2,6,12,3,1,7], [9,11,5,0,4,8,10,2,6,12,3],
                            [1,7,9,11,5,0,4,8,10,2,6]][:LIMIT_ONBIRLI]
            for perm in onbirli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onbirli_liste)} on birli varyasyon eklendi")

        if secimler['onikili']:
            print("\n🎬 On İkili varyasyonlar oluşturuluyor...")
            onikili_liste = [[0,1,2,3,4,5,6,7,8,9,10,11], [12,11,10,9,8,7,6,5,4,3,2,1], [0,2,4,6,8,10,12,1,3,5,7,9],
                            [11,9,7,5,3,1,10,8,6,4,2,0], [12,0,6,1,7,2,8,3,9,4,10,5], [11,5,10,4,9,3,8,2,7,1,6,0],
                            [12,6,0,5,10,4,9,3,8,2,7,1], [11,1,7,0,6,12,5,10,4,9,3,8], [2,8,1,7,0,6,11,5,10,4,9,3],
                            [12,3,9,2,8,1,7,0,6,11,5,10]][:LIMIT_ONIKILI]
            for perm in onikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onikili_liste)} on ikili varyasyon eklendi")

        if secimler['onuclu']:
            print("\n🎬 On Üçlü varyasyonlar oluşturuluyor...")
            onuclu_liste = [[0,1,2,3,4,5,6,7,8,9,10,11,12], [13,14,15,16,17,18,19,0,2,4,6,8,10], [1,3,5,7,9,11,13,15,17,19,4,6,12], [14,16,18,2,5,7,9,11,13,0,3,8,15], [10,17,0,6,12,1,7,13,2,8,14,3,9],
                            [15,4,19,5,10,0,16,11,6,1,17,12,7], [2,13,8,3,18,14,9,4,19,5,0,15,10], [6,11,16,1,12,7,2,17,13,8,3,0,18], [14,19,4,9,5,10,15,0,6,11,1,16,12], [7,2,13,8,3,14,9,4,19,5,10,0,15]][:LIMIT_ONUCLU]
            for perm in onuclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(onuclu_liste)} on üçlü varyasyon eklendi")


    # ========================== 14 VIDEO ==========================
    elif indirilen_sayisi == 14:
        # 14 video için sadece temel varyasyonlar (txt'den alınabilir, şimdilik basit)
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[0,1], [2,3], [4,5], [6,7], [8,9], [10,11], [12,13], [0,7], [1,8], [2,9]][:LIMIT_IKILI]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")

        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[0,1,2], [3,4,5], [6,7,8], [9,10,11], [12,13,0], [3,1,4], [7,2,5], [8,6,9],
                          [10,4,11], [0,5,12], [1,6,13], [2,7,3], [4,8,9], [5,10,11], [6,12,0], [7,13,1],
                          [8,2,3], [9,4,5], [10,6,7], [11,8,9]][:LIMIT_UCLU]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        if secimler['dortlu']:
            print("\n🎬 Dörtlü varyasyonlar oluşturuluyor...")
            dortlu_liste = [[0,1,2,3], [4,5,6,7], [8,9,10,11], [12,13,0,2], [4,6,8,10], [1,3,5,7],
                            [9,11,13,0], [2,4,6,8], [10,12,1,3], [5,7,9,11], [13,0,2,4], [6,8,10,12],
                            [1,3,5,7], [9,11,13,0], [2,4,6,8], [10,12,1,3], [5,7,9,11], [13,0,2,4],
                            [6,8,10,12], [1,3,5,7]][:LIMIT_DORTLU]
            for perm in dortlu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(dortlu_liste)} dörtlü varyasyon eklendi")

        if secimler['besli']:
            print("\n🎬 Beşli varyasyonlar oluşturuluyor...")
            besli_liste = [[0,1,2,3,4], [5,6,7,8,9], [10,11,12,13,0], [2,4,6,8,10], [12,1,3,5,7], 
                           [9,11,13,4,6], [0,8,2,10,5], [12,1,7,3,9], [11,4,13,6,0], [8,2,10,5,12],
                           [1,7,3,9,11], [4,13,6,0,8], [2,10,5,12,1], [7,3,9,11,4], [13,6,0,8,2],
                           [10,5,12,1,7], [3,9,11,4,13], [6,0,8,2,10], [5,12,1,7,3], [9,11,4,13,6]][:LIMIT_BESLI]
            for perm in besli_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(besli_liste)} beşli varyasyon eklendi")

        # Diğer varyasyonlar (altili, yedili vs.) basit şablon ile
        for var_type in ['altili', 'yedili', 'sekizli', 'dokuzlu', 'onlu', 'onbirli', 'onikili', 'onuclu', 'ondortlu']:
            if secimler.get(var_type):
                var_len = {'altili':6, 'yedili':7, 'sekizli':8, 'dokuzlu':9, 'onlu':10, 'onbirli':11, 'onikili':12, 'onuclu':13, 'ondortlu':14}[var_type]
                print(f"\n🎬 {var_type.capitalize()} varyasyonlar oluşturuluyor...")
                temp_list = [list(range(var_len))]  # Basit sıralı varyasyon
                temp_list.append(list(reversed(range(var_len))))  # Ters sıralı
                # Birkaç daha ekle
                for _ in range(8):
                    temp_list.append([i for i in range(var_len)])
                for perm in temp_list[:eval(f'LIMIT_{var_type.upper()}')]:
                    tum_varyasyonlar.append(list(perm))
                print(f"   ✓ {len(temp_list)} {var_type} varyasyon eklendi")

    # ========================== 15-20 VIDEO ==========================
    elif indirilen_sayisi >= 15 and indirilen_sayisi <= 20:
        # 15-20 video için basit şablon bazlı varyasyonlar
        print(f"\n📹 {indirilen_sayisi} video için varyasyonlar oluşturuluyor...")
        
        if secimler['ikili']:
            print("\n🎬 İkili varyasyonlar oluşturuluyor...")
            ikili_liste = [[i, i+1] for i in range(0, min(10*2, indirilen_sayisi-1), 2)][:LIMIT_IKILI]
            for perm in ikili_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(ikili_liste)} ikili varyasyon eklendi")

        if secimler['uclu']:
            print("\n🎬 Üçlü varyasyonlar oluşturuluyor...")
            uclu_liste = [[i, i+1, i+2] for i in range(0, min(20*3, indirilen_sayisi-2), 3)][:LIMIT_UCLU]
            for perm in uclu_liste: tum_varyasyonlar.append(list(perm))
            print(f"   ✓ {len(uclu_liste)} üçlü varyasyon eklendi")

        # Diğer varyasyon tipleri için basit şablon
        for var_type in ['dortlu', 'besli', 'altili', 'yedili', 'sekizli', 'dokuzlu', 'onlu', 
                         'onbirli', 'onikili', 'onuclu', 'ondortlu', 'onbesli', 'onaltili', 
                         'onyedili', 'onsekizli', 'ondokuzlu', 'yirmili']:
            if secimler.get(var_type):
                var_len = {'dortlu':4, 'besli':5, 'altili':6, 'yedili':7, 'sekizli':8, 'dokuzlu':9, 
                          'onlu':10, 'onbirli':11, 'onikili':12, 'onuclu':13, 'ondortlu':14, 
                          'onbesli':15, 'onaltili':16, 'onyedili':17, 'onsekizli':18, 
                          'ondokuzlu':19, 'yirmili':20}[var_type]
                
                if var_len > indirilen_sayisi:
                    continue
                    
                print(f"\n🎬 {var_type.capitalize()} varyasyonlar oluşturuluyor...")
                temp_list = []
                
                # Sıralı
                temp_list.append(list(range(var_len)))
                # Ters sıralı
                temp_list.append(list(reversed(range(var_len))))
                # Çift-tek ayrı
                temp_list.append([i for i in range(0, var_len*2, 2) if i < indirilen_sayisi][:var_len])
                temp_list.append([i for i in range(1, var_len*2, 2) if i < indirilen_sayisi][:var_len])
                
                # Karışık desenler ekle
                import random
                for _ in range(16):
                    perm = list(range(indirilen_sayisi))
                    random.shuffle(perm)
                    temp_list.append(perm[:var_len])
                
                # Limiti uygula
                limit_name = f'LIMIT_{var_type.upper()}'
                temp_list = temp_list[:eval(limit_name)]
                
                for perm in temp_list:
                    tum_varyasyonlar.append(list(perm))
                print(f"   ✓ {len(temp_list)} {var_type} varyasyon eklendi")

    # Diğer durumlar için hata
    else:
        print(f"\n⚠️ {indirilen_sayisi} video için varyasyon tanımlanmamış!")
        print("Lütfen 2 ile 20 arasında video kullanın.")
        return []
    
    return tum_varyasyonlar

def varyasyon_klasorler_olustur_ve_montaj(VIDEO_FORMAT):
    # Ana MP4'leri listele (Video 1, Video 2... klasörlerini tarayarak)
    mp4_dosyalar = []
    
    # 1. Normal Videoları Tara
    if os.path.exists(video_kaynak_ana_yol):
        tum_klasorler = os.listdir(video_kaynak_ana_yol)
        hedef_klasorler = []
        for isim in tum_klasorler:
            tam_yol = os.path.join(video_kaynak_ana_yol, isim)
            if os.path.isdir(tam_yol) and re.match(r'^Video \d+$', isim):
                hedef_klasorler.append(tam_yol)
        
        def klasor_numarasi(k_yolu):
            isim = os.path.basename(k_yolu)
            match = re.search(r'\d+', isim)
            return int(match.group()) if match else 0
            
        hedef_klasorler.sort(key=klasor_numarasi)
        
        for k in hedef_klasorler:
            videolar = glob.glob(os.path.join(k, '*.mp4'))
            # Klasör içindeki videoları da isme göre sıralayalım ki tutarlı olsun
            videolar.sort() 
            mp4_dosyalar.extend(videolar)
            
    # 2. Klon Videoları Tara ve Ekle (Append)
    if os.path.exists(klon_video_kaynak_ana_yol):
        tum_klasorler_klon = os.listdir(klon_video_kaynak_ana_yol)
        hedef_klasorler_klon = []
        for isim in tum_klasorler_klon:
            tam_yol = os.path.join(klon_video_kaynak_ana_yol, isim)
            # Regex: "Klon Video 1", "Klon Video 2" gibi klasörleri bul
            if os.path.isdir(tam_yol) and re.match(r'^Klon Video \d+$', isim):
                hedef_klasorler_klon.append(tam_yol)
        
        def klon_klasor_numarasi(k_yolu):
            isim = os.path.basename(k_yolu)
            match = re.search(r'\d+', isim)
            return int(match.group()) if match else 0
            
        hedef_klasorler_klon.sort(key=klon_klasor_numarasi)
        
        for k in hedef_klasorler_klon:
            videolar = glob.glob(os.path.join(k, '*.mp4'))
            videolar.sort()
            mp4_dosyalar.extend(videolar)

    # ÖNEMLİ: Burada `sorted(list(set(mp4_dosyalar)))` YAPILMAMALI.
    # Çünkü bu işlem "Önce Video klasörleri, Sonra Klon klasörleri" sırasını bozar.
    # Sadece duplicate varsa temizlemek için, sırayı koruyan bir yöntem:
    mp4_dosyalar = list(dict.fromkeys(mp4_dosyalar))
    
    indirilen_sayisi = len(mp4_dosyalar)
    
    if indirilen_sayisi == 0:
        print("Hata: Kaynak klasörlerde MP4 bulunamadı!")
        return False
    
    if indirilen_sayisi < 2:
        print("Hata: En az 2 video gerekli!")
        return False
    
    print(f"\n{'='*80}")
    print(f"📹 Toplam {indirilen_sayisi} adet kaynak video bulundu")
    print(f"{'='*80}")
    
    for idx, dosya in enumerate(mp4_dosyalar):
        # Dosya yolunu kısaltarak göster (Video 1\video.mp4 gibi)
        # Eğer Klon klasöründen geliyorsa parent klasör adını da gösterir
        parent = os.path.basename(os.path.dirname(dosya))
        filename = os.path.basename(dosya)
        kisa_yol = os.path.join(parent, filename)
        print(f"  [{idx}] {kisa_yol}")
    
    secimler = kullanicidan_varyasyon_sec(indirilen_sayisi)
    varyasyonlar = varyasyonlari_olustur(indirilen_sayisi, secimler)
    
    print(f"\n{'='*80}")
    print(f"📊 TOPLAM {len(varyasyonlar)} VARYASYON OLUŞTURULACAK")
    print(f"{'='*80}")
    
    basliklar = basliklari_al()
    if len(basliklar) == 0:
        return False
    
    basarili_montaj = 0
    
    for v_idx, varyasyon in enumerate(varyasyonlar, 1):
        klasor_adi = f"Video {v_idx}"
        alt_klasor = os.path.join(toplu_montaj_klasor, klasor_adi)
        os.makedirs(alt_klasor, exist_ok=True)
        
        varyasyon_tipi = f"{len(varyasyon)}'li"
        print(f"\n{'─'*80}")
        print(f"🎬 [{v_idx}/{len(varyasyonlar)}] {klasor_adi} - {varyasyon_tipi} Varyasyon")
        print(f"📋 Sıralama: {varyasyon}")
        print(f"🎞️  Videolar: {[os.path.basename(mp4_dosyalar[idx]) for idx in varyasyon]}")
        
        sirali_videolar = [mp4_dosyalar[idx] for idx in varyasyon]
        clips = []
        toplam_sure = 0
        original_clips = []
        
        for idx, dosya in enumerate(sirali_videolar, 1):
            try:
                print(f"   [{idx}/{len(sirali_videolar)}] İşleniyor: {os.path.basename(dosya)}")
                clip = VideoFileClip(dosya)
                original_clips.append(clip)
                clip_ayarli = video_boyutunu_ayarla(clip, VIDEO_FORMAT)
                clips.append(clip_ayarli)
                toplam_sure += clip_ayarli.duration
            except Exception as e:
                print(f"   ✗ Hata (atlandı): {e}\n")
                log_hatasi_kaydet(str(e), f"Montaj {klasor_adi}")
        
        if not clips:
            print(f"   ⚠️ {klasor_adi} için yüklenebilen video yok, atlanıyor...")
            continue
        
        try:
            if secimler.get('cerceve', False): clips = cerceve_ekle(clips)
            if secimler.get('logo', False): clips = logo_ekle(clips)
            if secimler.get('ses_efekti', False): clips = ses_efekti_ekle(clips, sirali_videolar)
            if secimler.get('video_overlay', False): clips = video_overlay_ekle(clips)

            # Video ses seviyesi ayarla (orijinal ses eklenecekse videonun kendi sesini kıs/kapat)
            clips = video_ses_ayarla(clips)

            # Orijinal video sesi ekle (Görsel Analiz'den çıkarılan ses)
            if secimler.get('orijinal_ses', False): clips = orijinal_ses_ekle(clips, sirali_videolar)
            
            final_clip = concatenate_videoclips(clips, method="compose")
            
            if secimler.get('muzik', False): final_clip = muzik_ekle(final_clip)
            
            baslik_idx = (v_idx - 1) % len(basliklar)
            guvenli_baslik = re.sub(r'[^\w\s-]', '', basliklar[baslik_idx]).strip().replace(' ', '_')[:100]
            cikti = os.path.join(alt_klasor, f"{guvenli_baslik}.mp4")
            
            print(f"   💾 Montaj yapılıyor...")
            final_clip.write_videofile(
                cikti, 
                codec='libx264', 
                audio_codec='aac', 
                temp_audiofile='temp.m4a', 
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            final_clip.close()
            for clip in clips:
                try: clip.close()
                except: pass
            for clip in original_clips:
                try: clip.close()
                except: pass
            
            print(f"   ✅ {klasor_adi} tamamlandı! (Süre: {toplam_sure:.1f}s)")
            print(f"   💾 Kaydedildi: {cikti}")
            basarili_montaj += 1
            
        except Exception as e:
            print(f"   ❌ Montaj hatası: {e}")
            log_hatasi_kaydet(str(e), f"Montaj {klasor_adi}")
            for clip in clips:
                try: clip.close()
                except: pass
            for clip in original_clips:
                try: clip.close()
                except: pass
    
    print(f"\n{'='*80}")
    print(f"🎉 MONTAJ TAMAMLANDI!")
    print(f"✅ Başarılı: {basarili_montaj}/{len(varyasyonlar)}")
    print(f"❌ Başarısız: {len(varyasyonlar) - basarili_montaj}/{len(varyasyonlar)}")
    print(f"{'='*80}")
    return True

# Ana işlem
print("=" * 80)
print("🎬 GELİŞMİŞ VARYASYONLU MONTAJ BOTU")
print("=" * 80)
print("📌 Sistem: İkili ... Yirmili varyasyonlar (2-20 Video)")
print(f"⚙️  Limitler: İkili={LIMIT_IKILI}, Üçlü={LIMIT_UCLU}, Dörtlü={LIMIT_DORTLU}, Beşli={LIMIT_BESLI}")
print(f"             Altılı={LIMIT_ALTILI}, Yedili={LIMIT_YEDILI}, Sekizli={LIMIT_SEKIZLI}")
print(f"             Dokuzlu={LIMIT_DOKUZLU}, Onlu={LIMIT_ONLU}, On Birli={LIMIT_ONBIRLI}")
print(f"             On İkili={LIMIT_ONIKILI}, ..., Yirmili={LIMIT_YIRMILI}")
print("=" * 80)

VIDEO_FORMAT = video_format_sec()
varyasyon_montaj_yap = varyasyon_klasorler_olustur_ve_montaj(VIDEO_FORMAT)

if not varyasyon_montaj_yap:
    print("\n❌ İşlem başarısız!")
else:
    print("\n✅ Tüm işlemler başarıyla tamamlandı!")

input("\nÇıkmak için Enter'a basın...")