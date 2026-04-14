import sys
import os
import json
import time

def main():
    print("[INFO] Görsel Oluştur Motoru başlatıldı.")
    time.sleep(1)
    
    base_dir = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Otomasyon Çalıştırma"
    cnt_dir = os.path.join(base_dir, ".control")
    settings_path = os.path.join(cnt_dir, "settings.local.json")
    
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        print(f"[ERROR] Ayarlar okunamadı: {e}")
        sys.exit(1)
        
    secili_model = settings.get("gorsel_model", "Nano Banana 2")
    print(f"[INFO] Seçili Görsel Modeli: {secili_model}")
    
    # Model isimlerini PixVerse image modellerine dönüştürme (Mapping)
    model_map = {
        "Nano Banana 2": "gemini-3.1-flash",
        "Nano Banana Pro": "gemini-3.0",
        "Nano Banana": "gemini-2.5-flash",
        "Seedream 5.0 Lite": "seedream-5.0-lite",
        "Seedream 4.5": "seedream-4.5",
        "Seedream 4.0": "seedream-4.0",
        "Kling O3": "kling-image-o3",
        "Kling 3.0": "kling-image-v3",
        "Qwen Image": "qwen-image"
    }
    
    px_model = model_map.get(secili_model)
    if not px_model:
        print(f"[ERROR] Desteklenmeyen veya tanımlanmamış Görsel Modeli seçildi: {secili_model}")
        print("[INFO] Lütfen ayarlardan PixVerse destekli bir Image modeli seçin.")
        sys.exit(1)
        
    Gorsel_Prompt_Dir = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Prompt"
    Gorsel_Olusturma_Dir = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görseller"
    
    if not os.path.exists(Gorsel_Prompt_Dir):
         print(f"[ERROR] Görsel Prompt klasörü bulunamadı: {Gorsel_Prompt_Dir}")
         sys.exit(1)
    
    # Prompt numaralarını bul ve sırayla çalıştır
    prompt_folders = []
    for f in os.listdir(Gorsel_Prompt_Dir):
        p = os.path.join(Gorsel_Prompt_Dir, f)
        if os.path.isdir(p) and f.startswith("Görsel Prompt"):
             try:
                 num = int(f.replace("Görsel Prompt", "").strip())
                 prompt_folders.append((num, p))
             except: pass
    
    prompt_folders.sort(key=lambda x: x[0])
    
    if not prompt_folders:
        print("[ERROR] Görsel Prompt klasörünün içinde (Görsel Prompt X) hiçbir prompt dosyası bulunamadı.")
        sys.exit(1)
        
    os.makedirs(Gorsel_Olusturma_Dir, exist_ok=True)
    import subprocess
    import shutil
    
    node_path = shutil.which("node") or "node"
    pixverse_path = shutil.which("pixverse") or "pixverse"
    
    if not shutil.which("pixverse"):
        print("[ERROR] PixVerse komutu bulunamadı! Lütfen PixVerse CLI yüklü olduğundan emin olun.")
        sys.exit(1)
        
    quality_options = {
        "qwen-image": ["720p", "1080p"],
        "gemini-3.1-flash": ["512p", "1080p", "1440p", "2160p"],
        "gemini-3.0": ["1080p", "1440p", "2160p"],
        "gemini-2.5-flash": ["1080p"],
        "seedream-5.0-lite": ["1440p", "1800p"],
        "seedream-4.5": ["1440p", "2160p"],
        "seedream-4.0": ["1080p", "1440p", "2160p"],
        "kling-image-o3": ["1080p", "1440p", "2160p"],
        "kling-image-v3": ["1080p", "1440p"],
    }

    kalite_seviyesi = str(settings.get("gorsel_kalitesi", "Standart") or "Standart").strip().lower()
    mevcut_qualities = quality_options.get(px_model, ["1080p"])
    if kalite_seviyesi == "maksimum":
        secili_quality = mevcut_qualities[-1]
    elif kalite_seviyesi in {"yüksek", "yuksek"}:
        secili_quality = mevcut_qualities[min(len(mevcut_qualities) - 1, len(mevcut_qualities) // 2)]
    else:
        secili_quality = mevcut_qualities[0]

    failed_any = False
    
    for num, folder_path in prompt_folders:
        prompt_txt_file = os.path.join(folder_path, "gorsel_prompt.txt")
        if not os.path.exists(prompt_txt_file):
            print(f"[WARNING] #{num} numaralı prompt dosyası bulunamadı, atlanıyor...")
            continue
            
        try:
            with open(prompt_txt_file, "r", encoding="utf-8") as f:
                prompt_text = f.read().strip()
        except:
            print(f"[ERROR] #{num} Prompt dosyası okunamadı.")
            failed_any = True
            continue
            
        if not prompt_text:
            print(f"[WARNING] #{num} Prompt boş, atlanıyor...")
            continue
            
        print(f"\n#{num} Prompt gönderildi... ({prompt_text[:20]}...) ")
        
        # 1. Create Image
        boyut = settings.get("gorsel_boyutu", "16:9")
        cmd_create = [
            pixverse_path,
            "create",
            "image",
            "--prompt",
            prompt_text,
            "--model",
            px_model,
            "--quality",
            secili_quality,
            "--aspect-ratio",
            boyut,
            "--json",
        ]
        try:
            start_time = time.time()
            proc = subprocess.run(cmd_create, capture_output=True, text=True)
            output = proc.stdout if proc.stdout else ""
            if proc.stderr: output += "\n" + proc.stderr
            
            json_str = output
            if "{" in output and "}" in output:
                json_str = output[output.find("{"):output.rfind("}")+1]
                
            try:
                data = json.loads(json_str)
                asset_id = data.get("image_id") or data.get("id")
            except:
                print(f"❌ #{num} Başarısız işlem (JSON okunamadı)")
                failed_any = True
                continue
                
            if not asset_id:
               print(f"❌ #{num} Başarısız işlem (Asset ID yok)")
               failed_any = True
               continue
               
            print(f"Görsel oluşturuluyor...")
            
            # 2. Download Image (PixVerse asset download)
            hedef_klasor = os.path.join(Gorsel_Olusturma_Dir, f"Görsel {num}")
            os.makedirs(hedef_klasor, exist_ok=True)
            cmd_dl = [pixverse_path, "asset", "download", str(asset_id), "--type", "image", "--dest", hedef_klasor]
            
            # capture_output=True eklenerek ekrana basılan yüzdeler gizlenmiştir:
            dl_proc = subprocess.run(cmd_dl, capture_output=True, text=True)
            
            if dl_proc.returncode != 0:
                print(f"❌ #{num} Başarısız işlem (İndirme başarısız)")
                failed_any = True
            else:
                elapsed = round(time.time() - start_time, 1)
                print(f"⏱️ Görsel {elapsed} saniyede oluşturuldu.")
                print(f"✅ #{num} Başarılı işlem")
                
        except Exception as e:
            print(f"[ERROR] Beklenmeyen Hata: {str(e)}")
            failed_any = True
            
    # Durum kaydet
    state_path = os.path.join(cnt_dir, "batch_state.json")
    basarili_mi = not failed_any
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            state["gorsel_olustur_last_status"] = "success" if basarili_mi else "error"
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except: pass
        
    if basarili_mi:
        print("\n[SUCCESS] Görsel Oluştur işlemi başarıyla sonlandırıldı.")
    else:
        print("\n[ERROR] İşlem bazı hatalarla veya tamamen başarısız olarak sonlandırıldı.")
        sys.exit(1)

if __name__ == "__main__":
    main()
