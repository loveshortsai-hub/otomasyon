from google import genai
import os
import re
import json

# ============ CONFIGURATION ============
BASE_SYS_PATH = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Prompt Oluşturma"
PROMPTS_ROOT_PATH = r"C:\Users\User\Desktop\Otomasyon\Prompt"

CORRECTION_FILE = os.path.join(BASE_SYS_PATH, "düzeltme.txt")
APP_BASE_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma"
SETTINGS_CANDIDATES = [
    os.path.join(APP_BASE_DIR, ".control", "settings.local.json"),
    os.path.join(APP_BASE_DIR, "settings.local.json"),
]

# ============ API KEY ============
def load_api_key():
    for settings_path in SETTINGS_CANDIDATES:
        try:
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                api_key = str(data.get("gemini_api_key", "")).strip()
                if api_key:
                    print(f"✅ API key ayarlardan yüklendi: {settings_path}")
                    return api_key
        except Exception:
            pass

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        print("✅ API key ortam değişkeninden yüklendi: GEMINI_API_KEY")
        return api_key

    return None

api_key = load_api_key()

if not api_key:
    print("❌ HATA: GEMINI_API_KEY bulunamadı!")
    print("   SEÇENEK 1: app.py Ayarlar bölümüne Gemini API Key gir")
    print("   SEÇENEK 2: setx GEMINI_API_KEY your_key_here")
    exit(1)

client = genai.Client(api_key=api_key)
print(f"✅ Gemini API Client başlatıldı")

# ============ HELPER FUNCTIONS ============
def read_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Dosya bulunamadı: {filepath}")
        return None

def write_file(filepath, content):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Dosyaya kaydedildi: {filepath}")
    except Exception as e:
        print(f"❌ Dosya yazma hatası: {e}")

def refine_prompt_with_gemini(prompt_text, correction_text):
    try:
        combined_prompt = f"""Aşağıda mevcut bir prompt ve düzeltme talimatları verilmektedir. 
Lütfen bu promptu düzeltme talimatlarına göre iyileştir ve daha iyi hale getir.

=== MEVCUT PROMPT ===
{prompt_text}

=== DÜZELTME TALİMATLARI ===
{correction_text}

=== İSTENEN ===
Yukarıdaki düzeltme talimatlarını dikkate alarak, mevcut promptu iyileştir ve sadece 
düzeltilmiş promptu döndür. Açıklama veya ek metin ekleme, sadece düzeltilmiş promptu ver."""
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[combined_prompt]
        )
        return response.text
    except Exception as e:
        print(f"❌ Gemini hatası: {e}")
        return None

def parse_correction_file(correction_path):
    """
    düzeltme.txt'yi oku ve her Prompt N için talimat bloğunu döndür.
    Dönüş: {1: "tam talimat metni", 2: "tam talimat metni", ...}
    Boş/eksik promptlar atlanır.
    """
    result = {}
    if not os.path.exists(correction_path):
        print(f"❌ düzeltme.txt bulunamadı: {correction_path}")
        return result

    content = read_file(correction_path)
    if not content:
        return result

    # Her "Prompt N:" bloğunu ayır
    blocks = re.split(r'(?=Prompt\s+\d+\s*:)', content, flags=re.IGNORECASE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m = re.match(r'Prompt\s+(\d+)\s*:', block, re.IGNORECASE)
        if not m:
            continue
        no = int(m.group(1))
        # Bloğun tamamı talimat metni
        result[no] = block
    return result

def get_sorted_prompt_folders():
    """Prompt klasörlerini klasör adındaki GERÇEK numaraya göre döndür.
    Örnek: 'Video Prompt 1' → {1: 'Video Prompt 1'}, 'Video Prompt 3' → {3: 'Video Prompt 3'}
    Böylece Video Prompt 2 silinmiş olsa bile Prompt 3 doğru eşleşir."""
    if not os.path.isdir(PROMPTS_ROOT_PATH):
        print(f"❌ Prompt klasörü bulunamadı: {PROMPTS_ROOT_PATH}")
        return {}

    result = {}
    for folder in os.listdir(PROMPTS_ROOT_PATH):
        klasor_yolu = os.path.join(PROMPTS_ROOT_PATH, folder)
        if not os.path.isdir(klasor_yolu):
            continue
        # Klasör adının sonundaki numarayı al (örn: "Video Prompt 3" → 3)
        m = re.search(r'(\d+)\s*$', folder)
        if m:
            result[int(m.group(1))] = folder
        else:
            # Numara yoksa sıradaki boş slota koy (fallback)
            idx = max(result.keys(), default=0) + 1
            result[idx] = folder

    return result

# ============ MAIN PIPELINE ============
def run_pipeline():
    print("=" * 70)
    print("🔧 TOPLU PROMPT DÜZELTME PİPELİNE BAŞLANIYOR")
    print("=" * 70)

    # 1. düzeltme.txt'yi parse et — hangi prompt no için ne talimat var?
    print("\n[ADIM 1] düzeltme.txt okunuyor ve parse ediliyor...")
    correction_map = parse_correction_file(CORRECTION_FILE)

    if not correction_map:
        print("❌ düzeltme.txt boş veya hiç Prompt bloğu bulunamadı!")
        return

    # Sadece gerçek talimat içerenleri say (başlık satırı + sablon dışında bir şey varsa)
    aktif = {no: txt for no, txt in correction_map.items()}
    print(f"✅ {len(aktif)} adet Prompt bloğu bulundu: {sorted(aktif.keys())}")

    # 2. Prompt klasörlerini al ve eşleştir
    print("\n[ADIM 2] Prompt klasörleri taranıyor...")
    folder_map = get_sorted_prompt_folders()

    if not folder_map:
        print("❌ Hiçbir prompt klasörü bulunamadı!")
        return

    print(f"✅ {len(folder_map)} klasör bulundu.")

    # 3. İşlenecek dosyaları belirle: düzeltme.txt'deki her Prompt N → N. klasör
    todo = []
    for no, correction_text in sorted(aktif.items()):
        if no not in folder_map:
            print(f"⚠️ Prompt {no} için klasör bulunamadı (toplam {len(folder_map)} klasör var), atlanıyor.")
            continue
        folder_name = folder_map[no]
        prompt_path = os.path.join(PROMPTS_ROOT_PATH, folder_name, "prompt.txt")
        if not os.path.exists(prompt_path):
            print(f"⚠️ {folder_name}/prompt.txt bulunamadı, atlanıyor.")
            continue
        todo.append((no, folder_name, prompt_path, correction_text))

    if not todo:
        print("❌ İşlenecek dosya bulunamadı!")
        return

    total = len(todo)
    print(f"\n🚀 Toplam {total} adet prompt işlenecek...\n")

    basarili = 0
    basarisiz = 0

    for index, (no, folder_name, prompt_path, correction_text) in enumerate(todo, 1):
        print(f"🔄 [{index}/{total}] İşleniyor: {folder_name} (Prompt {no})")

        prompt_text = read_file(prompt_path)
        if not prompt_text:
            print(f"   ⚠️ HATA: prompt.txt okunamadı, atlanıyor.")
            basarisiz += 1
            continue

        print(f"   ⏳ Gemini'ye gönderiliyor...")
        refined_prompt = refine_prompt_with_gemini(prompt_text, correction_text)

        if not refined_prompt:
            print(f"   ❌ {folder_name} için düzeltme başarısız oldu!")
            basarisiz += 1
            continue

        write_file(prompt_path, refined_prompt)
        print(f"   ✅ {folder_name} tamamlandı!\n")
        basarili += 1

    print("=" * 70)
    print(f"✅ Başarılı: {basarili} | ❌ Başarısız: {basarisiz}")
    print("✅✅✅ TÜM İŞLEMLER TAMAMLANDI! ✅✅✅")
    print("=" * 70)

# ============ EXECUTE ============
if __name__ == "__main__":
    run_pipeline()
