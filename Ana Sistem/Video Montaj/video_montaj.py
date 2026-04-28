from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip, ImageClip, CompositeVideoClip
import json
import os
import glob
import re
import random

# PIL uyumluluk düzeltmesi
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

# ==================== AYARLAR ====================
# NOT: Video format seçimi program başlangıcında sorulacak
# NOT: Müzik ayarları muzik/ses_seviyesi.txt dosyasından okunur
#      Varsayılan: %15
# ==================================================

# Görsel Analiz çıktı klasörü (analiz.py tarafından oluşturulan ses dosyaları burada)
gorsel_analiz_dir = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Analiz"

# ----------------------------------------------------------------
# DOSYA YOLU AYARLARI
# ----------------------------------------------------------------

# 1. Ana Çalışma Klasörü (Script ve Eklerin olduğu yer)
ana_klasor = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj"

# 2. Videoların Bulunduğu Kaynak Klasör
video_klasor = r"C:\Users\User\Desktop\Otomasyon\Video\Video"

# --- Klon Videoların Bulunduğu Klasör ---
klon_video_klasor = r"C:\Users\User\Desktop\Otomasyon\Klon Video"

# 3. Montaj Çıktı Klasörü
# İstenilen yol: C:\Users\User\Desktop\Otomasyon\Video\Montaj
montaj_klasor = r"C:\Users\User\Desktop\Otomasyon\Video\Montaj"

# 4. Ek Klasörü (Logo, Çerçeve, Ses Efekti ve Müzik burada)
ek_klasor = os.path.join(ana_klasor, "ek")

# Görsel klasörü 'ek' klasörünün içinde
gorsel_klasor = os.path.join(ek_klasor, "görsel")

# Müzik klasörü
muzik_klasor = os.path.join(ek_klasor, "muzik")

# Alt klasörler
cerceve_klasor = os.path.join(ek_klasor, "çerçeve")
logo_klasor = os.path.join(ek_klasor, "logo")
video_overlay_klasor = os.path.join(ek_klasor, "video overlay")
ses_efekti_klasor = os.path.join(ek_klasor, "ses efekti")

# Klasörleri oluştur
os.makedirs(montaj_klasor, exist_ok=True)
os.makedirs(gorsel_klasor, exist_ok=True)
os.makedirs(muzik_klasor, exist_ok=True)
os.makedirs(cerceve_klasor, exist_ok=True)
os.makedirs(logo_klasor, exist_ok=True)
os.makedirs(video_overlay_klasor, exist_ok=True)
os.makedirs(ses_efekti_klasor, exist_ok=True)

# ----------------------------------------------------------------

def video_format_sec():
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

def video_boyutunu_ayarla(clip, video_format="shorts"):
    if video_format == "shorts":
        hedef_genislik = 1080
        hedef_yukseklik = 1920
        format_adi = "YouTube Shorts (Dikey)"
    else:
        hedef_genislik = 1920
        hedef_yukseklik = 1080
        format_adi = "Normal YouTube (Yatay)"
    
    video_genislik, video_yukseklik = clip.size
    print(f"      Orijinal: {video_genislik}x{video_yukseklik}")
    clip_resized = clip.resize(newsize=(hedef_genislik, hedef_yukseklik))
    print(f"      Sonuç: {clip_resized.size[0]}x{clip_resized.size[1]} ({format_adi})")
    
    return clip_resized

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


def muzik_ses_seviyesi_oku():
    return _ses_txt_degerini_oku(os.path.join(muzik_klasor, "ses_seviyesi.txt"), 0.15, "Müzik")


def ses_efekti_seviyesi_oku():
    return _ses_txt_degerini_oku(os.path.join(ses_efekti_klasor, "ses_seviyesi.txt"), 0.15, "Ses efekti") 
    try:
        with open(ses_seviyesi_dosyasi, 'r', encoding='utf-8') as f:
            icerik = f.read().strip()
        icerik = icerik.replace('%', '').strip()
        deger = float(icerik)
        if deger > 1:
            deger = deger / 100
        deger = max(0.0, min(1.0, deger))
        print(f"   📄 Ses seviyesi dosyadan okundu: %{int(deger * 100)}")
        return deger
    except Exception as e:
        print(f"   ⚠️ Ses seviyesi okunamadı, varsayılan kullanılıyor: %15")
        return 0.15

def muzik_ekle(video_clip):
    muzik_dosyalari = []
    for uzanti in ['*.mp3', '*.wav', '*.m4a', '*.aac', '*.ogg']:
        muzik_dosyalari.extend(glob.glob(os.path.join(muzik_klasor, uzanti)))
    
    if not muzik_dosyalari:
        print("\n⚠️ Müzik klasöründe müzik bulunamadı, müzik eklenmedi")
        return video_clip
    
    MUZIK_HACMI = muzik_ses_seviyesi_oku()
    MUZIK_FADE_IN = 2.0
    MUZIK_FADE_OUT = 2.0
    
    secilen_muzik = random.choice(muzik_dosyalari)
    print(f"\n🎵 Arka plan müziği: {os.path.basename(secilen_muzik)}")
    
    try:
        muzik_clip = AudioFileClip(secilen_muzik)
        video_suresi = video_clip.duration
        
        if muzik_clip.duration > video_suresi:
            muzik_clip = muzik_clip.subclip(0, video_suresi)
            print(f"   ✂️ Müzik kesildi: {video_suresi:.1f}s")
        elif muzik_clip.duration < video_suresi:
            tekrar_sayisi = int(video_suresi / muzik_clip.duration) + 1
            muzik_parcalari = [muzik_clip] * tekrar_sayisi
            from moviepy.audio.AudioClip import concatenate_audioclips
            muzik_clip = concatenate_audioclips(muzik_parcalari)
            muzik_clip = muzik_clip.subclip(0, video_suresi)
            print(f"   🔁 Müzik tekrarlandı: {video_suresi:.1f}s")
        
        muzik_clip = muzik_clip.volumex(MUZIK_HACMI)
        
        if MUZIK_FADE_IN > 0:
            muzik_clip = muzik_clip.audio_fadein(MUZIK_FADE_IN)
        if MUZIK_FADE_OUT > 0:
            muzik_clip = muzik_clip.audio_fadeout(MUZIK_FADE_OUT)
        
        print(f"   📊 Müzik ses seviyesi: %{int(MUZIK_HACMI * 100)}")
        print(f"   🎚️ Fade In: {MUZIK_FADE_IN}s, Fade Out: {MUZIK_FADE_OUT}s")
        
        if video_clip.audio is not None:
            yeni_ses = CompositeAudioClip([video_clip.audio, muzik_clip])
            video_clip = video_clip.set_audio(yeni_ses)
            print(f"   ✅ Müzik arka plana eklendi (video sesi korundu)")
        else:
            video_clip = video_clip.set_audio(muzik_clip)
            print(f"   ✅ Müzik eklendi (video sessiz)")
        
        return video_clip
    except Exception as e:
        print(f"   ❌ Müzik eklenirken hata: {e}")
        return video_clip

def orijinal_ses_seviyesi_oku():
    return _ses_txt_degerini_oku(os.path.join(ek_klasor, "orijinal_ses_seviyesi.txt"), 1.0, "Orijinal ses")


def video_ses_seviyesi_oku():
    return _ses_txt_degerini_oku(os.path.join(ek_klasor, "video_ses_seviyesi.txt"), 1.0, "Video ses")


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
    json_yolu = os.path.join(ek_klasor, "orijinal_ses_kaynaklari.json")
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
            # Görsel ise atla
            if video_mu_listesi is not None and idx < len(video_mu_listesi):
                if not video_mu_listesi[idx]:
                    yeni_clips.append(video_clip)
                    continue

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


def video_ses_ayarla(video_clips, video_mu_listesi=None):
    """Montajlanacak videonun kendi sesini kısma/kapatma."""
    ses_seviyesi = video_ses_seviyesi_oku()
    if ses_seviyesi >= 1.0:
        return video_clips  # Değişiklik yok

    print(f"\n🔇 Video ses seviyesi ayarlanıyor: %{int(ses_seviyesi * 100)}")
    try:
        yeni_clips = []
        for idx, video_clip in enumerate(video_clips):
            # Görsel ise atla
            if video_mu_listesi is not None and idx < len(video_mu_listesi):
                if not video_mu_listesi[idx]:
                    yeni_clips.append(video_clip)
                    continue

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
    ses_efekti_dosyalari = []
    for uzanti in ['*.mp3', '*.wav', '*.m4a', '*.aac', '*.ogg']:
        ses_efekti_dosyalari.extend(glob.glob(os.path.join(ses_efekti_klasor, uzanti)))
    
    if not ses_efekti_dosyalari:
        print("\n⚠️ Ses efekti klasöründe dosya bulunamadı")
        return video_clips
    
    print(f"\n📊 Ses efekti ekleniyor: {len(ses_efekti_dosyalari)} dosya bulundu")
    ses_seviyesi = ses_efekti_seviyesi_oku()
    print(f"   📊 Ses efekti seviyesi: %{int(ses_seviyesi * 100)}")
    
    ses_efekti_map = {}
    for ses_dosya in ses_efekti_dosyalari:
        basename = os.path.basename(ses_dosya)
        match = re.search(r'(\d+)', basename)
        if match:
            numara = match.group(1)
            ses_efekti_map[numara] = ses_dosya
    
    try:
        yeni_clips = []
        eklenen_sayisi = 0
        
        for idx, (video_clip, video_dosya) in enumerate(zip(video_clips, video_dosya_isimleri)):
            video_basename = os.path.basename(video_dosya)
            match = re.search(r'(\d+)', video_basename)
            
            video_numara = None
            if match:
                video_numara = match.group(1)
            else:
                parent_folder = os.path.basename(os.path.dirname(video_dosya))
                match_folder = re.search(r'(\d+)', parent_folder)
                if match_folder:
                    video_numara = match_folder.group(1)

            if video_numara:
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
                        
                        print(f"   ✓ Video {video_numara}: {os.path.basename(ses_efekti_dosya)}")
                        eklenen_sayisi += 1
                    except Exception as e:
                        print(f"   ⚠️ Video {video_numara}: Ses efekti eklenemedi - {e}")
                else:
                    print(f"   ⊖ Video {video_numara}: Eşleşen ses efekti yok")
            
            yeni_clips.append(video_clip)
        
        print(f"   ✅ Toplam {eklenen_sayisi} videoya ses efekti eklendi")
        return yeni_clips
    except Exception as e:
        print(f"   ❌ Ses efekti hatası: {e}")
        return video_clips

def kullanicidan_video_sec(mp4_dosyalar, gorsel_dosyalari):
    """
    Videoları sıralı index ([0], [1]...) şeklinde listeler ve seçtirir.
    Önce Video Klasörü, Sonra Klon Video Klasörü.
    """
    print("\n" + "="*80)
    print("HANGİ VİDEOLAR/GÖRSELLER HANGİ SIRAYLA BİRLEŞTİRİLSİN?")
    print("="*80)
    
    video_map = {}
    gorsel_map = {}
    
    # --- GÜNCELLENEN KISIM: Sıralı İndexleme (0, 1, 2...) ---
    print("\n📋 Mevcut videolar (Önce Normal Videolar, Sonra Klon Videolar):")
    for idx, dosya in enumerate(mp4_dosyalar):
        key = str(idx)
        video_map[key] = dosya
        
        # Klasör adını ve dosya adını al
        klasor_adi = os.path.basename(os.path.dirname(dosya))
        dosya_adi = os.path.basename(dosya)
        
        # Kullanıcının istediği formatta göster: [0] Video 1\Dosya_Adi.mp4
        print(f"  [{key}] {klasor_adi}\\{dosya_adi}")
            
    print("\n🖼️ Mevcut görseller:")
    for dosya in gorsel_dosyalari:
        num = akilli_siralama(dosya)
        key = f"G{num}" if num != float('inf') else "G999"
        
        if key in gorsel_map:
            sayac = 2
            while f"{key}_{sayac}" in gorsel_map:
                sayac += 1
            key = f"{key}_{sayac}"
            
        gorsel_map[key] = dosya
        klasor_adi = os.path.basename(os.path.dirname(dosya))
        print(f"  [{key}] Görsel ({klasor_adi}/{os.path.basename(dosya)}) - 5sn")
    
    print("\n📝 KULLANIM:")
    print("  • Tüm videoları birleştirmek için: t veya T")
    print("  • İstediğiniz sırayla: 0,1,2 veya 0 1 2 (Listede köşeli parantez içindeki numaraları yazın)")
    print("  • Video + Görsel örnek: 0,G1 (İlk sıradaki video + G1 Görseli)")
    print("  • Efektler için harf ekleyin: M (müzik), C (çerçeve), L (logo), V (video), S (ses), O (orijinal ses)")
    print("    Örnek: '0,1,2,m,c' - Video 0, 1 ve 2 birleştir + müzik + çerçeve")
    
    while True:
        secim = input("\n👉 Seçiminiz: ").strip().upper()
        
        if not secim:
            print("❌ Lütfen bir seçim yapın!")
            continue
        
        muzik_ekle = 'M' in secim
        cerceve_ekle = 'C' in secim
        logo_ekle = 'L' in secim
        video_ekle = 'V' in secim
        ses_efekti_ekle = 'S' in secim
        orijinal_ses_ekle_flag = 'O' in secim
        secim_temiz = secim.replace('M', '').replace('C', '').replace('L', '').replace('V', '').replace('S', '').replace('O', '').replace(',', ' ').replace(';', ' ').replace('.', ' ').strip()
        
        secilen_dosyalar = []
        video_mu = []
        
        if secim_temiz in ['T', 'TAMAMI', 'TAMAMINI', 'HEPSİ', 'HEPSI', '']:
            # Sıralı anahtarları (0, 1, 2...) sırasıyla ekle
            sirali_keys = sorted(video_map.keys(), key=lambda x: int(x))
            for k in sirali_keys:
                secilen_dosyalar.append(video_map[k])
                video_mu.append(True)
                
            return {
                'dosyalar': secilen_dosyalar,
                'video_mu': video_mu,
                'muzik': muzik_ekle,
                'cerceve': cerceve_ekle,
                'logo': logo_ekle,
                'video_overlay': video_ekle,
                'ses_efekti': ses_efekti_ekle,
                'orijinal_ses': orijinal_ses_ekle_flag
            }
        
        gecersiz_bulundu = False
        for s in secim_temiz.split():
            if s in video_map:
                secilen_dosyalar.append(video_map[s])
                video_mu.append(True)
            elif s in gorsel_map:
                secilen_dosyalar.append(gorsel_map[s])
                video_mu.append(False)
            else:
                print(f"⚠️ '[{s}]' listede bulunamadı!")
                gecersiz_bulundu = True
        
        if gecersiz_bulundu and not secilen_dosyalar:
            continue
            
        if secilen_dosyalar:
            return {
                'dosyalar': secilen_dosyalar,
                'video_mu': video_mu,
                'muzik': muzik_ekle,
                'cerceve': cerceve_ekle,
                'logo': logo_ekle,
                'video_overlay': video_ekle,
                'ses_efekti': ses_efekti_ekle,
                'orijinal_ses': orijinal_ses_ekle_flag
            }
        else:
            print("❌ Geçerli bir seçim yapın!")

def cerceve_dosyalari_getir():
    cerceve_dosyalari = []
    for uzanti in ['*.png', '*.jpg', '*.jpeg', '*.gif']:
        cerceve_dosyalari.extend(glob.glob(os.path.join(cerceve_klasor, uzanti)))
    for uzanti in ['*.mp4', '*.avi', '*.mov', '*.webm']:
        cerceve_dosyalari.extend(glob.glob(os.path.join(cerceve_klasor, uzanti)))
    
    if not cerceve_dosyalari: return []
    
    def numaraya_gore_siralama(dosya):
        basename = os.path.basename(dosya)
        match = re.search(r'(\d+)', basename)
        return int(match.group(1)) if match else float('inf')
    return sorted(cerceve_dosyalari, key=numaraya_gore_siralama)

def cerceve_ekle(video_clips):
    cerceve_dosyalari = cerceve_dosyalari_getir()
    if not cerceve_dosyalari:
        print("\n⚠️ Çerçeve klasöründe dosya bulunamadı")
        return video_clips
    
    print(f"\n🖼️ Çerçeve ekleniyor: {len(cerceve_dosyalari)} dosya bulundu")
    try:
        yeni_clips = []
        if len(cerceve_dosyalari) == 1:
            cerceve_dosya = cerceve_dosyalari[0]
            print(f"   📌 Tek çerçeve: {os.path.basename(cerceve_dosya)}")
            cerceve_uzanti = os.path.splitext(cerceve_dosya)[1].lower()
            for idx, video_clip in enumerate(video_clips, 1):
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
                    print(f"   ✓ Video {idx}: Çerçeve eklendi")
                except Exception as e:
                    print(f"   ⚠️ Video {idx}: Hata - {e}")
                    yeni_clips.append(video_clip)
        else:
            print(f"   📌 Çoklu çerçeve: {len(cerceve_dosyalari)} çerçeve")
            for idx, video_clip in enumerate(video_clips, 1):
                if idx - 1 < len(cerceve_dosyalari):
                    cerceve_dosya = cerceve_dosyalari[idx - 1]
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
                        print(f"   ✓ Video {idx}: {os.path.basename(cerceve_dosya)}")
                    except Exception as e:
                        print(f"   ⚠️ Video {idx}: Hata - {e}")
                        yeni_clips.append(video_clip)
                else:
                    print(f"   ⊖ Video {idx}: Çerçeve yok")
                    yeni_clips.append(video_clip)
        return yeni_clips
    except Exception as e:
        print(f"   ❌ Çerçeve hatası: {e}")
        return video_clips

def logo_dosyalari_getir():
    logo_dosyalari = []
    for uzanti in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.mp4', '*.avi', '*.mov', '*.webm']:
        logo_dosyalari.extend(glob.glob(os.path.join(logo_klasor, uzanti)))
    if not logo_dosyalari: return []
    def numaraya_gore_siralama(dosya):
        basename = os.path.basename(dosya)
        match = re.search(r'(\d+)', basename)
        return int(match.group(1)) if match else float('inf')
    return sorted(logo_dosyalari, key=numaraya_gore_siralama)

def video_overlay_dosyalari_getir():
    video_dosyalari = []
    for uzanti in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.mp4', '*.avi', '*.mov', '*.webm']:
        video_dosyalari.extend(glob.glob(os.path.join(video_overlay_klasor, uzanti)))
    if not video_dosyalari: return []
    def numaraya_gore_siralama(dosya):
        basename = os.path.basename(dosya)
        match = re.search(r'(\d+)', basename)
        return int(match.group(1)) if match else float('inf')
    return sorted(video_dosyalari, key=numaraya_gore_siralama)

def logo_ekle(video_clips):
    logo_dosyalari = logo_dosyalari_getir()
    if not logo_dosyalari:
        print("\n⚠️ Logo klasöründe dosya bulunamadı")
        return video_clips
    
    print(f"\n🏷️ Logo ekleniyor: {len(logo_dosyalari)} dosya")
    try:
        yeni_clips = []
        if len(logo_dosyalari) == 1:
            logo_dosya = logo_dosyalari[0]
            print(f"   📌 Tek logo: {os.path.basename(logo_dosya)}")
            logo_uzanti = os.path.splitext(logo_dosya)[1].lower()
            for idx, video_clip in enumerate(video_clips, 1):
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
                    print(f"   ✓ Video {idx}: Logo eklendi")
                except Exception as e:
                    print(f"   ⚠️ Video {idx}: {e}")
                    yeni_clips.append(video_clip)
        else:
            print(f"   📌 Çoklu logo: {len(logo_dosyalari)} logo")
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
                        print(f"   ✓ Video {idx+1}: {os.path.basename(logo_dosya)}")
                    except Exception as e:
                        print(f"   ⚠️ Video {idx+1}: {e}")
                        yeni_clips.append(video_clip)
                else:
                    print(f"   ⊖ Video {idx+1}: Logo yok")
                    yeni_clips.append(video_clip)
        return yeni_clips
    except Exception as e:
        print(f"   ❌ Logo hatası: {e}")
        return video_clips

def video_overlay_ekle(video_clips, is_video_list=None):
    overlay_dosyalari = video_overlay_dosyalari_getir()
    if not overlay_dosyalari:
        print("\n⚠️ Video overlay klasöründe dosya bulunamadı")
        return video_clips
    print(f"\n🎥 Video overlay ekleniyor: {len(overlay_dosyalari)} dosya")
    
    try:
        yeni_clips = []
        if len(overlay_dosyalari) == 1:
            overlay_dosya = overlay_dosyalari[0]
            print(f"   📌 Tek overlay: {os.path.basename(overlay_dosya)}")
            overlay_uzanti = os.path.splitext(overlay_dosya)[1].lower()
            try:
                if overlay_uzanti in ['.png', '.jpg', '.jpeg', '.gif']:
                    base_overlay = ImageClip(overlay_dosya)
                    is_overlay_video_file = False
                else:
                    base_overlay = VideoFileClip(overlay_dosya, has_mask=True)
                    if base_overlay.mask is None:
                        base_overlay = VideoFileClip(overlay_dosya)
                    is_overlay_video_file = True
                
                for idx, video_clip in enumerate(video_clips):
                    if is_video_list is not None and idx < len(is_video_list):
                        if not is_video_list[idx]:
                            print(f"   ⊘ Clip {idx+1}: Görsel olduğu için overlay EKLENMEDİ.")
                            yeni_clips.append(video_clip)
                            continue

                    try:
                        current_overlay = base_overlay.copy() if hasattr(base_overlay, 'copy') else base_overlay
                        if is_overlay_video_file:
                            if current_overlay.duration > video_clip.duration:
                                current_overlay = current_overlay.subclip(0, video_clip.duration)
                            print(f"   ✓ Video {idx+1}: Overlay eklendi")
                        else:
                            current_overlay = current_overlay.set_duration(video_clip.duration)
                            print(f"   ✓ Video {idx+1}: Görsel overlay eklendi")

                        current_overlay = current_overlay.resize(newsize=(video_clip.w, video_clip.h))
                        yeni_clip = CompositeVideoClip([video_clip, current_overlay.set_position("center")])
                        yeni_clips.append(yeni_clip)
                    except Exception as e:
                        print(f"   ⚠️ Video {idx+1}: {e}")
                        yeni_clips.append(video_clip)

            except Exception as e:
                print(f"   ❌ Overlay yükleme hatası: {e}")
                return video_clips
        else:
            print(f"   📌 Çoklu overlay: {len(overlay_dosyalari)} overlay")
            for idx, video_clip in enumerate(video_clips):
                if is_video_list is not None and idx < len(is_video_list):
                    if not is_video_list[idx]:
                        print(f"   ⊘ Clip {idx+1}: Görsel olduğu için overlay EKLENMEDİ.")
                        yeni_clips.append(video_clip)
                        continue

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
                            if overlay_clip.duration > video_clip.duration:
                                overlay_clip = overlay_clip.subclip(0, video_clip.duration)
                        
                        overlay_clip = overlay_clip.resize(newsize=(video_clip.w, video_clip.h))
                        yeni_clip = CompositeVideoClip([video_clip, overlay_clip.set_position("center")])
                        yeni_clips.append(yeni_clip)
                        print(f"   ✓ Video {idx+1}: {os.path.basename(overlay_dosya)}")
                    except Exception as e:
                        print(f"   ⚠️ Video {idx+1}: {e}")
                        yeni_clips.append(video_clip)
                else:
                    print(f"   ⊖ Video {idx+1}: Overlay yok")
                    yeni_clips.append(video_clip)
        return yeni_clips
    except Exception as e:
        print(f"   ❌ Overlay hatası: {e}")
        return video_clips

# başlık.txt dosyasını oku
baslik_dosyasi = os.path.join(ek_klasor, "başlık.txt")
if not os.path.exists(baslik_dosyasi):
    print(f"Hata: '{baslik_dosyasi}' dosyası bulunamadı! Lütfen ek klasöründe başlık.txt oluşturun.")
    input("Çıkmak için Enter'a basın...")
    exit()

with open(baslik_dosyasi, 'r', encoding='utf-8') as f:
    baslik = f.read().strip()

if not baslik:
    print("Hata: başlık.txt boş! Lütfen başlık yazın.")
    input("Çıkmak için Enter'a basın...")
    exit()

guvenli_baslik = baslik.replace(' ', '_').replace('/', '_').replace('\\', '_')[:100]

# --- YENİ KLASÖR MANTIĞI ---
# Montaj klasörünü ve sıralı "Video X" klasörlerini kontrol et
video_sayac = 1
while True:
    hedef_klasor = os.path.join(montaj_klasor, f"Video {video_sayac}")
    if not os.path.exists(hedef_klasor):
        cikti_dosyasi_klasoru = hedef_klasor
        # BURADAKİ os.makedirs SATIRI SİLİNDİ
        # Klasörü hemen oluşturmuyoruz, sadece ismi rezerve ediyoruz.
        break
    video_sayac += 1

cikti_dosyasi = os.path.join(cikti_dosyasi_klasoru, f"{guvenli_baslik}.mp4")

# ----------------------------------------------------------------
# VİDEO BULMA VE SIRALAMA (GÜNCELLENDİ)
# ----------------------------------------------------------------

def akilli_siralama(dosya_yolu):
    """
    Kullanıcı talebine göre: Klasör ismine (Video 1, Video 3 vb.) KESİN öncelik ver.
    """
    klasor_adi = os.path.basename(os.path.dirname(dosya_yolu))
    match_klasor = re.search(r'(\d+)', klasor_adi)
    if match_klasor:
        return int(match_klasor.group(1))
    
    dosya_adi = os.path.basename(dosya_yolu)
    match_dosya = re.search(r'(\d+)', dosya_adi)
    if match_dosya:
        return int(match_dosya.group(1))
        
    return float('inf')

# --- GÜNCELLENEN KISIM: HEM VİDEO HEM KLON VİDEO TARAMA ---
mp4_dosyalar_video = []
if os.path.exists(video_klasor):
    # Ana Video klasöründeki "Video N" klasörlerini tara
    for item in os.listdir(video_klasor):
        item_full_path = os.path.join(video_klasor, item)
        if os.path.isdir(item_full_path) and re.match(r'^Video \d+$', item, re.IGNORECASE):
            mp4s_in_folder = glob.glob(os.path.join(item_full_path, '*.mp4'))
            mp4_dosyalar_video.extend(mp4s_in_folder)

# Önce kendi içinde sırala (Video 1, Video 2...)
mp4_dosyalar_video.sort(key=akilli_siralama)

mp4_dosyalar_klon = []
if os.path.exists(klon_video_klasor):
    # Klon Video klasöründeki "Klon Video N" veya "Video N" klasörlerini tara
    for item in os.listdir(klon_video_klasor):
        item_full_path = os.path.join(klon_video_klasor, item)
        # "Klon Video 1", "Video 1" vb. formatlar
        if os.path.isdir(item_full_path) and re.match(r'^(?:Klon\s+)?Video \d+$', item, re.IGNORECASE):
            mp4s_in_folder = glob.glob(os.path.join(item_full_path, '*.mp4'))
            mp4_dosyalar_klon.extend(mp4s_in_folder)

# Önce kendi içinde sırala (Klon Video 1, Klon Video 2...)
mp4_dosyalar_klon.sort(key=akilli_siralama)

# Listeleri birleştir: Önce Normal Videolar, Sonra Klon Videolar
mp4_dosyalar = mp4_dosyalar_video + mp4_dosyalar_klon

# Görsel dosyalarını bul
gorsel_dosyalari = []
for uzanti in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']:
    gorsel_dosyalari.extend(glob.glob(os.path.join(gorsel_klasor, uzanti)))

gorsel_dosyalari = sorted(gorsel_dosyalari, key=akilli_siralama)

# Eğer hiçbir klasörde video yoksa en baştan sonlandır
if not mp4_dosyalar:
    print(f"\nHata: Hiçbir MP4 dosyası bulunamadı!")
    print(f"  Kontrol edilen yerler:")
    print(f"  - {video_klasor} (Video N klasörleri)")
    print(f"  - {klon_video_klasor} (Klon Video N klasörleri)")
    input("Çıkmak için Enter'a basın...")
    exit()

# ----------------------------------------------------------------

# Video formatını kullanıcıdan al
VIDEO_FORMAT = video_format_sec()

print(f"\n{'='*80}")
print(f"📹 Toplam {len(mp4_dosyalar)} adet video tespit edildi.")
if gorsel_dosyalari:
    print(f"🖼️ Toplam {len(gorsel_dosyalari)} adet görsel tespit edildi.")
print(f"{'='*80}")

# KULLANICIDAN DİNAMİK LİSTELEME İLE SEÇİM AL
secimler = kullanicidan_video_sec(mp4_dosyalar, gorsel_dosyalari)

# Yeni fonksiyondan dönen direkt dosyalar
secilen_dosyalar = secimler['dosyalar']
video_mu = secimler['video_mu']

print(f"\n{'='*80}")
print(f"✅ SEÇİLEN DOSYALAR ({len(secilen_dosyalar)} adet)")
print(f"{'='*80}")
for idx, (dosya, is_video) in enumerate(zip(secilen_dosyalar, video_mu)):
    tip = "📹 Video" if is_video else "🖼️ Görsel (5s)"
    klasor_ismi = os.path.basename(os.path.dirname(dosya))
    print(f"  [{idx+1}] {tip}: {klasor_ismi}/{os.path.basename(dosya)}")

if secimler['muzik']: print("\n🎵 Müzik eklenecek")
else: print("\n⊖ Müzik eklenmeyecek")

if secimler['cerceve']: print("🖼️ Çerçeve eklenecek")
else: print("⊖ Çerçeve eklenmeyecek")

if secimler['logo']: print("🏷️ Logo eklenecek")
else: print("⊖ Logo eklenmeyecek")

if secimler['video_overlay']: print("🎥 Video overlay eklenecek")
else: print("⊖ Video overlay eklenmeyecek")

if secimler['ses_efekti']: print("📊 Ses efekti eklenecek")
else: print("⊖ Ses efekti eklenmeyecek")

if secimler.get('orijinal_ses'): print("🔊 Orijinal video sesi eklenecek")
else: print("⊖ Orijinal video sesi eklenmeyecek")

clips = []
original_clips = []
toplam_sure = 0

VIDEO_FPS = 30 
ISTENEN_KARE = 5  
GORSEL_SURESI = ISTENEN_KARE / VIDEO_FPS  

print("\n" + "="*80)
if VIDEO_FORMAT == "shorts":
    print("VİDEOLAR VE GÖRSELLER 1080x1920 (YouTube Shorts - DİKEY) FORMATINA DÖNÜŞTÜRÜLÜYOR")
else:
    print("VİDEOLAR VE GÖRSELLER 1920x1080 (Normal YouTube - YATAY) FORMATINA DÖNÜŞTÜRÜLÜYOR")
print("="*80 + "\n")

for idx, (dosya, is_video) in enumerate(zip(secilen_dosyalar, video_mu), 1):
    try:
        tip = "Video" if is_video else "Görsel"
        klasor_ismi = os.path.basename(os.path.dirname(dosya)) if is_video else ""
        dosya_gosterim = f"{klasor_ismi}/{os.path.basename(dosya)}" if is_video else os.path.basename(dosya)
        
        print(f"[{idx}/{len(secilen_dosyalar)}] İşleniyor ({tip}): {dosya_gosterim}")
        
        if is_video:
            clip = VideoFileClip(dosya)
            original_clips.append(clip)
            clip_ayarli = video_boyutunu_ayarla(clip, VIDEO_FORMAT)
            clips.append(clip_ayarli)
            toplam_sure += clip_ayarli.duration
            print(f"      ✓ Hazır! Süre: {clip_ayarli.duration:.1f}s\n")
        else:
            clip = ImageClip(dosya).set_duration(GORSEL_SURESI)
            original_clips.append(clip)
            
            if VIDEO_FORMAT == "shorts":
                hedef_genislik, hedef_yukseklik = 1080, 1920
            else:
                hedef_genislik, hedef_yukseklik = 1920, 1080
            
            print(f"      Orijinal: {clip.size[0]}x{clip.size[1]}")
            clip_ayarli = clip.resize(newsize=(hedef_genislik, hedef_yukseklik))
            print(f"      Sonuç: {clip_ayarli.size[0]}x{clip_ayarli.size[1]}")
            
            clips.append(clip_ayarli)
            toplam_sure += GORSEL_SURESI
            print(f"      ✓ Hazır! Süre: {GORSEL_SURESI:.1f}s\n")
        
    except Exception as e:
        print(f"      ✗ Hata (atlandı): {e}\n")

if not clips:
    print("Hiç video yüklenemedi!")
    exit()

print("\n" + "="*80)
print("BİRLEŞTİRME BAŞLIYOR...")
print("="*80)

if secimler['cerceve']: clips = cerceve_ekle(clips)
if secimler['logo']: clips = logo_ekle(clips)

if secimler['ses_efekti']:
    video_clips_only = [clip for clip, is_vid in zip(clips, video_mu) if is_vid]
    video_dosya_isimleri_only = [dosya for dosya, is_vid in zip(secilen_dosyalar, video_mu) if is_vid]
    
    if video_clips_only:
        video_clips_with_sound = ses_efekti_ekle(video_clips_only, video_dosya_isimleri_only)
        video_idx = 0
        for i, is_vid in enumerate(video_mu):
            if is_vid:
                clips[i] = video_clips_with_sound[video_idx]
                video_idx += 1

if secimler['video_overlay']:
    clips = video_overlay_ekle(clips, video_mu)

# Video ses seviyesi ayarla (orijinal ses eklenecekse videonun kendi sesini kıs/kapat)
clips = video_ses_ayarla(clips, video_mu)

# Orijinal video sesi ekle (Görsel Analiz'den çıkarılan ses)
if secimler.get('orijinal_ses'):
    clips = orijinal_ses_ekle(clips, secilen_dosyalar, video_mu)

final_clip = concatenate_videoclips(clips, method="compose")

if secimler['muzik']:
    final_clip = muzik_ekle(final_clip)

# --- KAYDETMEDEN ÖNCE KLASÖRÜ OLUŞTUR (BURASI ÖNEMLİ) ---
# İşlemler başarıyla bittiğinde, klasörü burada oluşturuyoruz.
os.makedirs(os.path.dirname(cikti_dosyasi), exist_ok=True)

print(f"\n📹 Video kaydediliyor: {cikti_dosyasi}")
final_clip.write_videofile(cikti_dosyasi, fps=30, codec='libx264', audio_codec='aac', temp_audiofile='temp-audio.m4a', remove_temp=True)

final_clip.close()
for clip in clips:
    try: clip.close()
    except: pass
for clip in original_clips:
    try: clip.close()
    except: pass

print("\n" + "="*80)
print("✅ BİRLEŞTİRME TAMAMLANDI!")
print("="*80)
print(f"📁 Çıktı: {cikti_dosyasi}")
print(f"⏱️ Toplam süre: {toplam_sure:.1f} saniye")
if VIDEO_FORMAT == "shorts":
    print(f"📐 Boyut: 1080x1920 (YouTube Shorts - Dikey)")
else:
    print(f"📐 Boyut: 1920x1080 (Normal YouTube - Yatay)")
print("="*80)

input("Çıkmak için Enter'a basın...")
