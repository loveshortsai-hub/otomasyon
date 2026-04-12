import os, json, time, sys, subprocess, shutil, glob, re, textwrap
import streamlit as st
import streamlit.components.v1 as _st_components
try:
    from google import genai as _genai
    _GENAI_OK = True
except ImportError:
    _GENAI_OK = False

st.set_page_config(page_title="Otomasyon Paneli", layout="wide")

# ==========================================
# 1. AYARLAR VE VERİ YÖNETİMİ
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTROL_DIR = os.path.join(BASE_DIR, ".control")
os.makedirs(CONTROL_DIR, exist_ok=True)
SETTINGS_PATH = os.path.join(CONTROL_DIR, "settings.local.json")
LEGACY_SETTINGS_PATH = os.path.join(BASE_DIR, "settings.local.json")

if not os.path.exists(SETTINGS_PATH) and os.path.exists(LEGACY_SETTINGS_PATH):
    try:
        shutil.move(LEGACY_SETTINGS_PATH, SETTINGS_PATH)
    except Exception:
        try:
            shutil.copy2(LEGACY_SETTINGS_PATH, SETTINGS_PATH)
        except Exception:
            pass

SORA2_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Sora 2\pixverse_sora2.py"
V56_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Pixverse\pixverse_v56.py"
VEO31_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Veo\pixverse_veo31.py"
GROK_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Grok\pixverse_grok.py"
C1_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Pixverse C1\pixverse_c1.py"
VIDEO_MODEL_OPTIONS = ["Sora 2", "Veo 3.1 Standard", "Grok", "PixVerse V6", "PixVerse Cinematic"]

DEFAULT_SETTINGS = {
    "links_file": r"C:\Users\User\Desktop\Otomasyon\İndirilecek Video.txt",
    "download_dir": r"C:\\Users\\User\\Desktop\\Otomasyon\\İndirilen Video",
    "added_video_dir": r"C:\\Users\\User\\Desktop\\Otomasyon\\Eklenen Video",
    "prompt_dir": r"C:\\Users\\User\\Desktop\\Otomasyon\\Prompt",
    "video_output_dir": r"C:\\Users\\User\\Desktop\\Otomasyon\\Video\\Video",
    "video_prompt_links_file": r"C:\\Users\\User\\Desktop\\Otomasyon\\Video Prompt Link.txt",
    "video_indir_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video İndirme\video_indir.py",
    "youtube_link_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Youtube Link\youtube_link.py",
    "prompt_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Prompt Oluşturma\prompt.py",
    "video_model": "Sora 2",
    "sora2_script": SORA2_SCRIPT_DEFAULT,
    "v56_script": V56_SCRIPT_DEFAULT,
    "veo31_script": VEO31_SCRIPT_DEFAULT,
    "grok_script": GROK_SCRIPT_DEFAULT,
    "c1_script": C1_SCRIPT_DEFAULT,
    "pixverse_script": SORA2_SCRIPT_DEFAULT,
    "nano_banana2_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana2.py",
    "nano_banana_pro_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana_pro.py",
    "nano_banana_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana.py",
    "seedream_50_lite_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\seedream_5.0-lite.py",
    "seedream_45_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\seedream_4.5.py",
    "qwen_image_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\qwen_image.py",
    "gorsel_olustur_dir": r"C:\Users\User\Desktop\Otomasyon\Görsel\Görseller",
    "analiz_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Analiz\analiz.py",
    "gorsel_klonlama_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluştur\görsel_klonlama.py",
    "gorsel_analiz_dir": r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Analiz",
    "klon_gorsel_dir": r"C:\Users\User\Desktop\Otomasyon\Görsel\Klon Görsel",
    "gorsel_duzelt_txt": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluştur\Görsel Düzelt.txt",
    "gemini_api_key": "",
    "prompt_duzeltme_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Prompt Oluşturma\prompt_düzeltme.py",
    "prompt_duzeltme_txt": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Prompt Oluşturma\düzeltme.txt",
    "video_montaj_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\video_montaj.py",
    "video_montaj_output_dir": r"C:\Users\User\Desktop\Otomasyon\Video\Montaj",
    "klon_video_dir": r"C:\Users\User\Desktop\Otomasyon\Klon Video",
    "video_montaj_gorsel_dir": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\görsel",
    "toplu_video_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Toplu Video Montaj\toplu_video.py",
    "toplu_video_output_dir": r"C:\Users\User\Desktop\Otomasyon\Video\Toplu Montaj",
    "toplu_video_materyal_dir": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek",
    "sosyal_medya_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım\sosyal_medya_paylasım.py",
    "sosyal_medya_dir": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım",
    "sosyal_medya_video_dir": r"C:\Users\User\Desktop\Otomasyon\Video\Video",
    "sosyal_medya_aciklama_txt": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım\açıklama.txt",
    "sosyal_medya_baslik_txt": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım\başlık.txt",
    "sosyal_medya_platform_txt": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım\paylasılacak_sosyal_medyalar.txt",
    "sosyal_medya_zamanlama_txt": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım\paylaşım_zamanlama.txt",
}

def _normalize_video_model(model_value, pixverse_script_path=""):
    value = str(model_value or "").strip().lower()
    if value in {"sora 2", "sora2", "sora-2"}:
        return "Sora 2"
    if value in {"pixverse v6", "pixversev6", "v6", "pixverse v5.6", "v5.6", "v56", "pixverse", "pixverse video", "pv"}:
        return "PixVerse V6"
    if value in {"pixverse cinematik", "pixversecinematik", "pixverse c1", "pixverse-c1", "c1", "cinematik", "pixverse cinematic", "cinematic"}:
        return "PixVerse Cinematic"
    if value in {"veo 3.1 standard", "veo-3.1-standard", "veo31", "veo 3.1"}:
        return "Veo 3.1 Standard"
    if value in {"grok", "grok imagine", "grok-imagine"}:
        return "Grok"
    if value in {"nano banana 2", "nanobanana2"}: return "Nano Banana 2"
    if value in {"nano banana pro", "nanobananapro"}: return "Nano Banana Pro"
    if value in {"nano banana", "nanobanana"}: return "Nano Banana"
    if value in {"seedream 5.0 lite", "seedream5.0lite"}: return "Seedream 5.0 Lite"
    if value in {"seedream 4.5", "seedream4.5"}: return "Seedream 4.5"
    if value in {"qwen image", "qwenimage"}: return "Qwen Image"

    script_name = os.path.basename(str(pixverse_script_path or "")).strip().lower()
    if script_name == "pixverse_sora2.py":
        return "Sora 2"
    if script_name in {"pixverse_v56.py", "pixverse_v6.py"}:
        return "PixVerse V6"
    if script_name == "pixverse_c1.py":
        return "PixVerse Cinematic"
    if script_name == "pixverse_veo31.py":
        return "Veo 3.1 Standard"
    if script_name == "pixverse_grok.py":
        return "Grok"
    if script_name == "nano_banana2.py": return "Nano Banana 2"
    if script_name == "nano_banana_pro.py": return "Nano Banana Pro"
    if script_name == "nano_banana.py": return "Nano Banana"
    if script_name == "seedream_5.0-lite.py": return "Seedream 5.0 Lite"
    if script_name == "seedream_4.5.py": return "Seedream 4.5"
    if script_name == "qwen_image.py": return "Qwen Image"
    return DEFAULT_SETTINGS["video_model"]


def get_active_video_script(settings: dict) -> str:
    model_name = _normalize_video_model(
        settings.get("video_model"),
        settings.get("pixverse_script", ""),
    )
    if model_name == "PixVerse V6":
        return (settings.get("v56_script") or V56_SCRIPT_DEFAULT).strip()
    if model_name == "PixVerse Cinematic":
        return (settings.get("c1_script") or C1_SCRIPT_DEFAULT).strip()
    if model_name == "Veo 3.1 Standard":
        return (settings.get("veo31_script") or VEO31_SCRIPT_DEFAULT).strip()
    if model_name == "Grok":
        return (settings.get("grok_script") or GROK_SCRIPT_DEFAULT).strip()
    if model_name == "Nano Banana 2": return settings.get("nano_banana2_script", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana2.py").strip()
    if model_name == "Nano Banana Pro": return settings.get("nano_banana_pro_script", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana_pro.py").strip()
    if model_name == "Nano Banana": return settings.get("nano_banana_script", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana.py").strip()
    if model_name == "Seedream 5.0 Lite": return settings.get("seedream_50_lite_script", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\seedream_5.0-lite.py").strip()
    if model_name == "Seedream 4.5": return settings.get("seedream_45_script", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\seedream_4.5.py").strip()
    if model_name == "Qwen Image": return settings.get("qwen_image_script", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\qwen_image.py").strip()
    return (settings.get("sora2_script") or SORA2_SCRIPT_DEFAULT).strip()


def get_active_video_model(settings: dict | None = None) -> str:
    src = settings if isinstance(settings, dict) else st.session_state.get("settings", {})
    return _normalize_video_model(
        src.get("video_model"),
        src.get("pixverse_script", ""),
    )


def get_video_generation_title(settings: dict | None = None) -> str:
    return f"{get_active_video_model(settings)} Video Üret"


def get_video_generation_label(settings: dict | None = None, emoji: bool = True) -> str:
    text = get_video_generation_title(settings)
    return f"🎬 {text}" if emoji else text


def get_video_generation_action_name(settings: dict | None = None) -> str:
    return f"{get_active_video_model(settings)} Video Üretme"


def get_video_generation_loading_text(settings: dict | None = None) -> str:
    return f"{get_active_video_model(settings)} Video Üretiliyor..."


def get_video_generation_canvas_subtitle(settings: dict | None = None) -> str:
    return f"{get_active_video_model(settings)} ile video oluştur"


def load_settings():
    out = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_PATH):
        try:
            data = json.load(open(SETTINGS_PATH, "r", encoding="utf-8"))
            if isinstance(data, dict):
                out.update(data)
        except Exception:
            pass

    out["video_model"] = _normalize_video_model(
        out.get("video_model"),
        out.get("pixverse_script", ""),
    )
    out["sora2_script"] = SORA2_SCRIPT_DEFAULT
    out["v56_script"] = V56_SCRIPT_DEFAULT
    out["veo31_script"] = VEO31_SCRIPT_DEFAULT
    out["grok_script"] = GROK_SCRIPT_DEFAULT
    out["c1_script"] = C1_SCRIPT_DEFAULT
    out["pixverse_script"] = get_active_video_script(out)
    return out


def save_settings(s: dict):
    data = dict(s or {})
    data["video_model"] = _normalize_video_model(
        data.get("video_model"),
        data.get("pixverse_script", ""),
    )
    data["sora2_script"] = SORA2_SCRIPT_DEFAULT
    data["v56_script"] = V56_SCRIPT_DEFAULT
    data["veo31_script"] = VEO31_SCRIPT_DEFAULT
    data["grok_script"] = GROK_SCRIPT_DEFAULT
    data["c1_script"] = C1_SCRIPT_DEFAULT
    data["pixverse_script"] = get_active_video_script(data)
    json.dump(data, open(SETTINGS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

if "settings" not in st.session_state: st.session_state.settings = load_settings()
if "status" not in st.session_state: st.session_state.status = {"input":"idle","youtube_link":"idle","download":"idle","analyze":"idle","pixverse":"idle","gorsel_analiz":"idle","gorsel_klonlama":"idle","gorsel_olustur":"idle","prompt_duzeltme":"idle","video_montaj":"idle","toplu_video":"idle","sosyal_medya":"idle","kredi_kazan":"idle","kredi_cek":"idle"}
if "logs" not in st.session_state: st.session_state.logs =[]
if "ui_placeholders" not in st.session_state: st.session_state.ui_placeholders = {}

# Motor Durumları
if "batch_mode" not in st.session_state: st.session_state.batch_mode = False
if "batch_step" not in st.session_state: st.session_state.batch_step = 0
if "batch_queue" not in st.session_state: st.session_state.batch_queue = []
if "batch_queue_idx" not in st.session_state: st.session_state.batch_queue_idx = 0
# Ek İşlemler → Tümünü Çalıştır seçimleri
if "ek_batch_secimler" not in st.session_state:
    st.session_state.ek_batch_secimler = {"video_indir": True, "gorsel_analiz": False, "gorsel_klonla": False, "gorsel_olustur": False, "prompt_duzeltme": False, "video_montaj": False, "toplu_video": False, "sosyal_medya": False}
if "controls_unlocked" not in st.session_state: st.session_state.controls_unlocked = False
if "batch_paused" not in st.session_state: st.session_state.batch_paused = False
if "batch_finish_requested" not in st.session_state: st.session_state.batch_finish_requested = False
if "batch_resume_queue" not in st.session_state: st.session_state.batch_resume_queue = []
if "batch_resume_idx" not in st.session_state: st.session_state.batch_resume_idx = 0
if "batch_resume_reason" not in st.session_state: st.session_state.batch_resume_reason = ""
if "batch_pixverse_retry_targets" not in st.session_state: st.session_state.batch_pixverse_retry_targets = []
if "durum_ozeti_suppress" not in st.session_state: st.session_state.durum_ozeti_suppress = False

if "single_paused" not in st.session_state: st.session_state.single_paused = False
if "single_finish_requested" not in st.session_state: st.session_state.single_finish_requested = False
if "single_mode" not in st.session_state: st.session_state.single_mode = False
if "single_step" not in st.session_state: st.session_state.single_step = None
if "youtube_link_args" not in st.session_state: st.session_state.youtube_link_args = []
if "link_canvas_source" not in st.session_state: st.session_state.link_canvas_source = "none"

# Arkaplan Motor Durumları
if "bg_proc" not in st.session_state: st.session_state.bg_proc = None
if "bg_owner" not in st.session_state: st.session_state.bg_owner = None
if "bg_node_key" not in st.session_state: st.session_state.bg_node_key = None
if "bg_log_path" not in st.session_state: st.session_state.bg_log_path = None
if "bg_log_pos" not in st.session_state: st.session_state.bg_log_pos = 0
if "bg_log_start_index" not in st.session_state: st.session_state.bg_log_start_index = 0
if "bg_log_fh" not in st.session_state: st.session_state.bg_log_fh = None
if "bg_last_result" not in st.session_state: st.session_state.bg_last_result = None

# Dialog Durumları ve Hizalama Hafızası
if "ek_dialog_open" not in st.session_state: st.session_state.ek_dialog_open = None
if "file_manager_trigger" not in st.session_state: st.session_state.file_manager_trigger = False
if "lightbox_gorsel" not in st.session_state: st.session_state.lightbox_gorsel = None
if "_ek_dialog_return_align" not in st.session_state: st.session_state._ek_dialog_return_align = "left"
if "last_dialog_align" not in st.session_state: st.session_state.last_dialog_align = "center"
if "durum_ozeti" not in st.session_state: st.session_state.durum_ozeti = {"hatali": [], "basarili": [], "kismi": [], "son_guncelleme": None}
if "durum_ozeti_dialog_open" not in st.session_state: st.session_state.durum_ozeti_dialog_open = False
if "video_montaj_format" not in st.session_state: st.session_state.video_montaj_format = "D"
if "video_montaj_selection_text" not in st.session_state: st.session_state.video_montaj_selection_text = ""
if "video_montaj_source_mode" not in st.session_state: st.session_state.video_montaj_source_mode = "Mevcut Videolar"
if "toplu_video_format" not in st.session_state: st.session_state.toplu_video_format = "D"
if "toplu_video_selection_text" not in st.session_state: st.session_state.toplu_video_selection_text = "T"
if "toplu_video_source_selection_text" not in st.session_state: st.session_state.toplu_video_source_selection_text = "T"
if "toplu_video_source_mode" not in st.session_state: st.session_state.toplu_video_source_mode = "Mevcut Videolar"
if "tv_muzik_seviyesi" not in st.session_state: st.session_state.tv_muzik_seviyesi = "15"
if "tv_ses_efekti_seviyesi" not in st.session_state: st.session_state.tv_ses_efekti_seviyesi = "15"
if "tv_baslik" not in st.session_state: st.session_state.tv_baslik = ""
if "tv_orijinal_ses_seviyesi" not in st.session_state: st.session_state.tv_orijinal_ses_seviyesi = "100"
if "tv_video_ses_seviyesi" not in st.session_state: st.session_state.tv_video_ses_seviyesi = "100"
if "vm_orijinal_ses_kaynak_sirasi" not in st.session_state: st.session_state.vm_orijinal_ses_kaynak_sirasi = ""
if "tv_orijinal_ses_kaynak_sirasi" not in st.session_state: st.session_state.tv_orijinal_ses_kaynak_sirasi = ""
if "sm_video_kaynak_secim" not in st.session_state: st.session_state.sm_video_kaynak_secim = "Link"
if "kredi_kazan_running" not in st.session_state: st.session_state.kredi_kazan_running = False
if "kredi_kazan_paused" not in st.session_state: st.session_state.kredi_kazan_paused = False
if "kredi_kazan_finish" not in st.session_state: st.session_state.kredi_kazan_finish = False
if "kredi_kazan_start_ts" not in st.session_state: st.session_state.kredi_kazan_start_ts = 0.0
if "kredi_cek_running" not in st.session_state: st.session_state.kredi_cek_running = False
if "kredi_cek_paused" not in st.session_state: st.session_state.kredi_cek_paused = False
if "kredi_cek_finish" not in st.session_state: st.session_state.kredi_cek_finish = False
if "kredi_cek_start_ts" not in st.session_state: st.session_state.kredi_cek_start_ts = 0.0
if "video_bolum_sureler" not in st.session_state: st.session_state.video_bolum_sureler = []
if "video_bolum_temp_path" not in st.session_state: st.session_state.video_bolum_temp_path = None
if "video_bolum_temp_name" not in st.session_state: st.session_state.video_bolum_temp_name = None
if "video_bolum_saved_notice" not in st.session_state: st.session_state.video_bolum_saved_notice = None
if "pixverse_prompt_override_meta" not in st.session_state: st.session_state.pixverse_prompt_override_meta = None
if "go_mode_val" not in st.session_state: st.session_state["go_mode_val"] = "Görsel"
if "go_motion_prompt_saved" not in st.session_state: st.session_state["go_motion_prompt_saved"] = False

GORSEL_HAREKET_PROMPT_DIR = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Hareklendirme Prompt"
GORSEL_HAREKET_REFERANS_DIR = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görseller"


def _has_saved_gorsel_motion_prompts() -> bool:
    try:
        if not os.path.isdir(GORSEL_HAREKET_PROMPT_DIR):
            return False
        for name in os.listdir(GORSEL_HAREKET_PROMPT_DIR):
            folder_path = os.path.join(GORSEL_HAREKET_PROMPT_DIR, name)
            prompt_path = os.path.join(folder_path, "prompt.txt")
            if not (os.path.isdir(folder_path) and name.startswith("Video Prompt") and os.path.exists(prompt_path)):
                continue
            with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
                if f.read().strip():
                    return True
    except Exception:
        return False
    return False


def _gorsel_motion_sort_key(value: str):
    text = str(value or "").strip()
    match = re.search(r"(\d+)", text)
    if match:
        return (0, int(match.group(1)), text.casefold())
    return (1, text.casefold())


def _list_saved_gorsel_motion_prompt_entries() -> list:
    out = []
    try:
        if not os.path.isdir(GORSEL_HAREKET_PROMPT_DIR):
            return out
        for idx, name in enumerate(os.listdir(GORSEL_HAREKET_PROMPT_DIR), start=1):
            folder_path = os.path.join(GORSEL_HAREKET_PROMPT_DIR, name)
            prompt_path = os.path.join(folder_path, "prompt.txt")
            if not (os.path.isdir(folder_path) and name.startswith("Video Prompt") and os.path.exists(prompt_path)):
                continue
            try:
                with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
                    prompt_text = f.read().strip()
            except Exception:
                prompt_text = ""
            if not prompt_text:
                continue
            match = re.search(r"(\d+)", name)
            prompt_no = int(match.group(1)) if match else idx
            out.append({
                "folder_name": name,
                "folder_path": folder_path,
                "prompt_path": prompt_path,
                "prompt_no": prompt_no,
            })
        out.sort(key=lambda item: _gorsel_motion_sort_key(item.get("folder_name", "")))
    except Exception:
        return []
    return out


def _list_gorsel_olustur_reference_image_entries() -> list:
    out = []
    supported_exts = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    try:
        if not os.path.isdir(GORSEL_HAREKET_REFERANS_DIR):
            return out
        for idx, name in enumerate(os.listdir(GORSEL_HAREKET_REFERANS_DIR), start=1):
            folder_path = os.path.join(GORSEL_HAREKET_REFERANS_DIR, name)
            if not os.path.isdir(folder_path):
                continue
            match = re.search(r"(\d+)", name)
            gorsel_no = int(match.group(1)) if match else idx
            image_files = []
            for fname in os.listdir(folder_path):
                full_path = os.path.join(folder_path, fname)
                if os.path.isfile(full_path) and fname.lower().endswith(supported_exts):
                    image_files.append(full_path)
            if not image_files:
                continue
            image_files.sort(key=lambda p: _gorsel_motion_sort_key(os.path.basename(p)))
            out.append({
                "folder_name": name,
                "folder_path": folder_path,
                "gorsel_no": gorsel_no,
                "path": image_files[0],
            })
        out.sort(key=lambda item: (int(item.get("gorsel_no", 0) or 0), _gorsel_motion_sort_key(item.get("folder_name", ""))))
    except Exception:
        return []
    return out


def _should_use_gorsel_motion_prompts() -> bool:
    return (
        bool(st.session_state.get("go_motion_prompt_saved", False))
        and str(st.session_state.get("go_mode_val", "")).strip() == "Görsel"
        and _has_saved_gorsel_motion_prompts()
    )


def _recover_stale_pixverse_prompt_override_state():
    settings_obj = st.session_state.get("settings", {})
    if not isinstance(settings_obj, dict):
        return

    prompt_dir = str(settings_obj.get("prompt_dir") or "").strip()
    if not prompt_dir:
        return

    norm_prompt_dir = os.path.abspath(prompt_dir)
    norm_control_dir = os.path.abspath(CONTROL_DIR)
    if not norm_prompt_dir.startswith(norm_control_dir):
        return

    folder_name = os.path.basename(os.path.dirname(norm_prompt_dir)) if os.path.basename(norm_prompt_dir).lower() == "prompt" else os.path.basename(norm_prompt_dir)
    if "pixverse_prompt_override_" not in folder_name.lower():
        return

    settings_obj = dict(settings_obj)
    settings_obj["prompt_dir"] = DEFAULT_SETTINGS.get("prompt_dir", prompt_dir)
    st.session_state.settings = settings_obj
    save_settings(settings_obj)

    try:
        temp_root = norm_prompt_dir
        if os.path.basename(norm_prompt_dir).lower() == "prompt":
            temp_root = os.path.dirname(norm_prompt_dir)
        shutil.rmtree(temp_root, ignore_errors=True)
    except Exception:
        pass


_recover_stale_pixverse_prompt_override_state()


def _sm_normalize_kaynak_secim(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Link"
    if raw in ("Link", "Video", "🎞️ Video Ekle", "🎬 Toplu Video Montaj", "🎞️ Video Montaj", "🖼️ Görsel Oluştur"):
        return raw
    if raw == "Video/Link":
        return "Link"

    low = raw.lower()
    if "görsel oluştur" in low or "gorsel olustur" in low:
        return "🖼️ Görsel Oluştur"
    if "toplu" in low and "montaj" in low:
        return "🎬 Toplu Video Montaj"
    if ("ekle" in low and "video" in low) or "eklenen" in low:
        return "🎞️ Video Ekle"
    if "montaj" in low:
        return "🎞️ Video Montaj"
    if "link" in low:
        return "Link"
    if "video" in low:
        return "Video"
    return "Link"


def _normalize_toplu_video_source_mode(value: str) -> str:
    raw = str(value or "").strip()
    if raw == "Eklenen Video":
        return "Eklenen Video"
    if raw == "Görsel Oluştur":
        return "Görsel Oluştur"
    return "Mevcut Videolar"

def clear_dialog_states():
    """Herhangi bir ana menü tuşuna basıldığında asılı kalmış diyalogları sıfırlar."""
    st.session_state.ek_dialog_open = None
    st.session_state.file_manager_trigger = False
    st.session_state.lightbox_gorsel = None
    st.session_state.durum_ozeti_dialog_open = False

# ==========================================
# 2. TEMEL YARDIMCI FONKSİYONLAR (CORE HELPERS)
# ==========================================
def log(line: str):
    timestamp = time.strftime('%H:%M:%S')
    st.session_state.logs.append(f"[{timestamp}] {line.rstrip()}")
    if len(st.session_state.logs) > 1000:
        st.session_state.logs = st.session_state.logs[-1000:]

def any_running():
    return any(v == "running" for v in st.session_state.status.values())

def is_ui_locked():
    is_batch = st.session_state.get("batch_mode", False)
    is_paused = (is_batch and st.session_state.get("batch_paused", False)) or \
                (not is_batch and st.session_state.get("single_paused", False))
    return (is_batch or any_running()) and not is_paused


def _strip_log_prefix(line: str) -> str:
    return re.sub(r'^\[\d{2}:\d{2}:\d{2}\]\s*', '', (line or '')).strip()

def _detect_partial_status(logs_snapshot: list, node_key: str = None) -> str:
    basarili = basarisiz = atlandi = None
    toplam_skip = 0

    # Kritik hata kalıpları — bu satırlardan herhangi biri varsa direkt "error"
    HATA_KALIPLARI = [
        r'TXT dosyas[iı]nda link yok',
        r'CRITICAL\s+ERROR',
        r'CRITICAL:\s+istem\.txt',
        r'\[ERROR\]\s+Script bulunamad',
        r'indirilecek.*video.*yok',
        r'kaynak.*dosya.*bulunamad[iı]',
        r'İ[şs]lenecek\s+Video\s+Prompt\s+klas[öo]r[üu]\s+bulunamad[iı]',
        r'Toplam\s+0\s+adet\s+Video\s+Prompt\s+klas[öo]r[üu]\s+bulundu',
        # 0 görev tespit kalıpları — sadece toplam 0 ise
        r'Toplam\s+İ[şs]lenecek\s+G[öo]rev\s*:\s*0(?!\s*\()',
        r'Hi[çc]bir.*i[şs]lem.*yap[iı]lmad[iı]',
        r'Hi[çc]bir.*video.*bulunamad[iı]',
        # Geçmiş tarih hatası — zamanlama saati geçmişte kalmış
        r'Ge[çc]mi[şs]\s*tarih\s*tespit\s*edildi',
        r'Ge[çc]mi[şs]\s*zamana\s*payla[şs][iı]m\s*yap[iı]lamaz',
    ]
    PARTIAL_KALIPLARI = [
        r'G[ÖO]RSEL\s+Y[ÜU]KLENEMED[İI]',
        r'g[öo]rsel\s+olmadan\s+prompt\s+ile\s+devam\s+ediliyor',
    ]
    NODE_FATAL_KALIPLARI = {
        "video_montaj": [
            r'^Hata\s*:',
            r'İ[şs]lem\s+ba[şs]ar[iı]s[iı]z',
            r'En\s+az\s+2\s+video\s+gerekli',
            r'Minimum\s*2\s+video',
            r'uygun\s+video\s+bulunamad[iı]',
            r'montaj\s+oluşturulamad[iı]',
        ],
        "toplu_video": [
            r'^Hata\s*:',
            r'İ[şs]lem\s+ba[şs]ar[iı]s[iı]z',
            r'En\s+az\s+2\s+video\s+gerekli',
            r'Minimum\s*2\s+video',
            r'uygun\s+video\s+bulunamad[iı]',
            r'montaj\s+oluşturulamad[iı]',
        ],
    }

    tum_tamamlandi = False
    partial_warning = False
    for line in logs_snapshot:
        clean = _strip_log_prefix(line)
        if not clean:
            continue

        for kalip in HATA_KALIPLARI:
            if re.search(kalip, clean, re.IGNORECASE):
                return "error"

        for kalip in NODE_FATAL_KALIPLARI.get(node_key, []):
            if re.search(kalip, clean, re.IGNORECASE):
                return "error"

        if re.search(r'TÜM\s+İ[Şş]LEMLER\s+TAMAMLANDI|TUM\s+ISLEMLER\s+TAMAMLANDI', clean, re.IGNORECASE):
            tum_tamamlandi = True

        for kalip in PARTIAL_KALIPLARI:
            if re.search(kalip, clean, re.IGNORECASE):
                partial_warning = True
                break

        if basarili is None:
            m = re.search(r'Ba[şs]ar[iı]l[iı]\s*[:\-]\s*(\d+)', clean, re.IGNORECASE)
            if m: basarili = int(m.group(1))
        if basarisiz is None:
            m2 = re.search(r'Ba[şs]ar[iı]s[iı]z\s*[:\-]\s*(\d+)', clean, re.IGNORECASE)
            if m2: basarisiz = int(m2.group(1))
        if atlandi is None:
            m3 = re.search(r'atland[iı]\s*(?:\(zaten mevcut\))?\s*[:\-]\s*(\d+)', clean, re.IGNORECASE)
            if m3: atlandi = int(m3.group(1))
        if re.search(r'\[SKIP\]|SKIP\s*\(DONE\)|SKIP\s*\(ATLANDI\)', clean, re.IGNORECASE):
            toplam_skip += 1

    if basarili is None and basarisiz is None:
        return "partial" if partial_warning else ("ok" if tum_tamamlandi else "ok")

    basarili = basarili or 0
    basarisiz = basarisiz or 0
    atlandi = atlandi if atlandi is not None else toplam_skip

    if tum_tamamlandi and basarili > 0 and basarisiz == 0:
        return "partial" if partial_warning else "ok"
    if tum_tamamlandi and basarili > 0 and basarisiz > 0:
        return "partial"

    if basarili == 0 and basarisiz == 0 and atlandi == 0:
        return "error"
    if basarili == 0 and basarisiz == 0:
        return "partial" if atlandi > 0 or partial_warning else "ok"
    if basarili == 0 and basarisiz > 0:
        return "error"
    if basarili > 0 and basarisiz > 0:
        return "partial"
    if basarili > 0 and partial_warning:
        return "partial"
    return "ok"


# ==========================================
# 2b. DURUM ÖZETİ YARDIMCI FONKSİYONLARI
# ==========================================
_DURUM_ISLEM_ETIKETLERI = {
    "input": "Link Doğrulama",
    "youtube_link": "YouTube Link Toplama",
    "download": "Video İndirme",
    "gorsel_analiz": "Görsel Analiz",
    "gorsel_klonlama": "Görsel Klonlama",
    "gorsel_olustur": "Görsel Oluştur",
    "analyze": "Prompt Oluşturma",
    "prompt_duzeltme": "Prompt Düzeltme",
    "video_montaj": "Video Montaj",
    "toplu_video": "Toplu Video Montaj",
    "sosyal_medya": "Sosyal Medya Paylaşım",
    "kredi_kazan": "Video Üretme Kredisi Kazan",
    "kredi_cek": "Üretilen Kredileri Çek",
}


def get_durum_islem_etiketi(node_key: str) -> str:
    if node_key == "pixverse":
        return get_video_generation_action_name()
    return _DURUM_ISLEM_ETIKETLERI.get(node_key, node_key)

def _normalize_hata_detay(raw_text: str) -> str:
    text = _strip_log_prefix(raw_text)
    text = re.sub(r'^[\s\-–—:;]+', '', text).strip()
    text = re.sub(r'^\[(ERROR|INFO|WARN|WARNING|DEBUG)\]\s*', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'^(HATA DURUMU|HATA|ERROR|SEBEP|DETAY|SONUÇ)\s*[:\-]?\s*', '', text, flags=re.IGNORECASE).strip()

    m_missing_file = re.search(r'dosya\s+bulunamad[^:]*:\s*(.+)', text, re.IGNORECASE)
    if m_missing_file:
        missing_path = m_missing_file.group(1).strip().strip('"\'')
        missing_name = os.path.basename(missing_path.rstrip("\\/")) if missing_path else ""
        return f"Dosya Bulunamadı: {missing_name or missing_path}" if (missing_name or missing_path) else "Dosya Bulunamadı"

    if re.search(r'gerekli\s+komut\s+veya\s+dosya\s+bulunamad', text, re.IGNORECASE):
        return "Gerekli Komut veya Dosya Bulunamadı"

    hata_kaliplari = [
        # Sosyal medya - sayfa yükleme / kanal seçme / buton hataları
        (r'Sayfa\s*y[üu]klenemedi|page.*load.*fail|loading.*spinner|sayfa.*tak[ıi]l', 'Sayfa Yüklenemedi'),
        (r'sayfa.*a[çc][ıi]lamad[ıi]', 'Sayfa Açılamadı'),
        (r'Youtube\s*kanal[ıi]\s*se[çc]ilemedi', 'Youtube Kanalı Seçilemedi'),
        (r'Tiktok\s*kanal[ıi]\s*se[çc]ilemedi', 'Tiktok Kanalı Seçilemedi'),
        (r'Instagram\s*kanal[ıi]\s*se[çc]ilemedi', 'Instagram Kanalı Seçilemedi'),
        (r'kanal[ıi]?\s*se[çc]ilemedi|sosyal\s*medya.*se[çc]ilemedi', 'Sosyal Medya Kanalı Seçilemedi'),
        (r'Yeni\s*g[öo]nderi\s*butonu\s*t[ıi]klanamad[ıi]|queue-header-create-post.*Unable', 'Yeni Gönderi Butonu Tıklanamadı'),
        (r'Zamanla\s*butonu.*t[ıi]klanamad[ıi]|Schedule\s*Post.*t[ıi]klanamad[ıi]|Schedule\s*Post.*Pasif', 'Zamanla Butonu Tıklanamadı'),
        (r'Hemen\s*paylaş.*butonu.*t[ıi]klanamad[ıi]|Publish\s*Now.*t[ıi]klanamad[ıi]|Publish\s*Now.*Pasif', 'Hemen Paylaş Butonu Tıklanamadı'),
        (r'g[öo]nder.*buton.*t[ıi]klanamad[ıi]', 'Gönder Butonu Tıklanamadı'),
        (r'Video\s*y[üu]klenemedi|video.*upload.*fail', 'Video Yüklenemedi'),
        (r'Video\s*y[üu]kleme\s*zaman\s*a[şs][ıi]m[ıi]', 'Video Yükleme Zaman Aşımı'),
        (r'Hesap\s*bilgisi\s*eksik', 'Hesap Bilgisi Eksik'),
        (r'Ge[çc]mi[şs]\s*tarih', 'Geçmiş Tarih Seçildi'),
        (r'Giri[şs].*yap[ıi]lamad[ıi]|login.*fail|oturum.*a[çc][ıi]lamad[ıi]', 'Giriş Yapılamadı'),
        # Genel hatalar
        (r'prompt.*uzun|prompt.*too.*long|exceeds.*max.*length|cannot exceed.*characters|character.*limit', 'Prompt Uzun'),
        (r'sign in to confirm you.?re not a bot|cookies-from-browser|--cookies\b|youtube.*cookies|çerez', 'YouTube Doğrulaması Gerekli'),
        (r'unable to connect to proxy|proxyerror|proxy.*bağlan', 'Proxy Bağlantı Hatası'),
        (r'http error 429|too many requests|429\b', 'Hız Limiti / Bot Koruması'),
        (r'javascript runtime|js challenge|remote component challenge solver', 'JavaScript Challenge Çözülemedi'),
        (r'video erişilemedi|video unavailable', 'Video Erişilemedi'),
        (r'g[öo]rsel\s+y[üu]klenemedi|image.*upload.*fail|upload.*failed', 'Görsel Yüklenemedi'),
        (r'g[öo]rsel\s+bulunamad[ıi]', 'Görsel Bulunamadı'),
        (r'chromedriver.*only supports chrome version|only supports chrome version|current browser version is|session not created: cannot connect to chrome|cannot connect to chrome', 'ChromeDriver Sürüm Uyumsuzluğu'),
        (r'chrome\s*ba[şs]lat[ıi]lamad[ıi]|taray[ıi]c[ıi].*ba[şs]lat[ıi]lamad[ıi]', 'Tarayıcı Başlatılamadı'),
        (r'zaman\s*a[sş][iı]m[iı]|timeout|timed?\s*out', 'Zaman Aşımı'),
        (r'api.*key.*invalid|authentication|unauthorized|401', 'API Yetkilendirme Hatası'),
        (r'rate.*limit|too.*many.*requests|429', 'Hız Limiti Aşıldı'),
        (r'connection.*error|network|bağlantı.*hata', 'Bağlantı Hatası'),
        (r'İ[şs]lenecek\s+Video\s+Prompt\s+klas[öo]r[üu]\s+bulunamad[iı]|Toplam\s+0\s+adet\s+Video\s+Prompt\s+klas[öo]r[üu]\s+bulundu', 'Video Prompt Bulunamadı'),
        (r'dosya.*bulunamad|file.*not.*found|script.*bulunamad', 'Dosya Bulunamadı'),
        (r'TXT dosyas[iı]nda link yok|indirilecek.*video.*yok', 'Veri Bulunamadı'),
        (r'en\s+az\s+2\s+video\s+gerekli|min(?:imum)?\s*2\s+video', 'En Az 2 Video Gerekli'),
        (r'montaj\s+oluşturulamad[iı]', 'Montaj Oluşturulamadı'),
        (r'i[şs]lem\s+ba[şs]ar[iı]s[iı]z|operation failed', 'İşlem Başarısız'),
        (r'Unable to locate element|no such element|NoSuchElementException', 'Sayfa Öğesi Bulunamadı'),
        (r'element.*not.*clickable|ElementNotInteractableException', 'Sayfa Öğesine Tıklanamadı'),
        (r'CRITICAL', 'Kritik Hata'),
        (r'quota.*exceeded|kota', 'Kota Aşıldı'),
        (r'memory|bellek', 'Bellek Hatası'),
        (r'permission|izin|erişim', 'Erişim Hatası'),
        (r'politika|policy|sensitive information|Please re-enter', 'İçerik Politikası'),
    ]
    for kalip, aciklama in hata_kaliplari:
        if re.search(kalip, text, re.IGNORECASE):
            return aciklama
    return text[:80] if text else 'Başarısız'


def _is_separator_line(text: str) -> bool:
    """Sadece ayırıcı karakterlerden oluşan satır mı? (===, ---, ###, boş)"""
    stripped = re.sub(r'[\s\=\-\#\*\_\~]', '', text)
    return len(stripped) == 0


def _is_non_actionable_log_line(text: str) -> bool:
    clean = _strip_log_prefix(text)
    if not clean or _is_separator_line(clean):
        return True

    non_actionable_patterns = [
        r"Çıkmak\s+için\s+Enter",
        r"Devam\s+etmek\s+için",
        r"Seçiminiz",
        r"Çıkış\s+yapılıyor",
        r"Geçici\s+dosyalar\s+temizlendi",
        r"^İŞLEMLER\s+TAMAMLANDI$",
        r"^Başarılı\s*:\s*\d+(\s*-\s*.+)?$",
        r"^Başarısız\s*:\s*\d+(\s*-\s*.+)?$",
        r"^Atlandı.*:\s*\d+(\s*-\s*.+)?$",
        r"^\[[YDNMTCLS0-9, /]+\]$",
        r"^\[ERROR\]\s+.+hata ile sonlandı\s+\(kod:\s*\d+(?:,\s*neden:\s*.+)?\)$",
        r"^\[INFO\]\s+Video üretim hatası -> .+ tekrar başlanacak\.?$",
    ]
    return any(re.search(kalip, clean, re.IGNORECASE) for kalip in non_actionable_patterns)


def _detect_hata_detay(logs_snapshot: list, node_key: str) -> str:
    """Log satırlarından tekil hata detayını tespit eder."""
    # analyze (Prompt Oluştur) için özel özet çıkarımı
    if node_key == "analyze":
        basarili = 0; basarisiz = 0; atlandi = 0
        for line in (logs_snapshot or []):
            clean = _strip_log_prefix(line)
            m_b = re.match(r'Ba[sş]ar[iı]l[iı]\s*:\s*(\d+)', clean)
            if m_b: basarili = int(m_b.group(1)); continue
            m_f = re.match(r'Ba[sş]ar[iı]s[iı]z\s*:\s*(\d+)', clean)
            if m_f: basarisiz = int(m_f.group(1)); continue
            m_a = re.match(r'Atland[iı].*?:\s*(\d+)', clean)
            if m_a: atlandi = int(m_a.group(1)); continue
        parts = []
        if basarili > 0: parts.append(f"{basarili} başarılı")
        if basarisiz > 0: parts.append(f"{basarisiz} başarısız")
        if atlandi > 0: parts.append(f"{atlandi} atlandı")
        if parts:
            return ", ".join(parts)

    etiketli_hata_kaliplari = [
        r'^\s*SEBEP\s*:',
        r'^\s*DETAY\s*:',
    ]

    oncelikli_hata_kaliplari = [
        r'En\s+az\s+2\s+video\s+gerekli',
        r'^Hata\s*:',
        r'\[ERROR\]',
        r'CRITICAL',
        r'İ[şs]lem\s+ba[şs]ar[iı]s[iı]z',
        r'İ[şs]lenecek\s+Video\s+Prompt\s+klas[öo]r[üu]\s+bulunamad[iı]',
        r'Toplam\s+0\s+adet\s+Video\s+Prompt\s+klas[öo]r[üu]\s+bulundu',
        r'bulunamad[iı]',
        r'yetersiz',
        r'timeout',
        r'unauthorized',
        r'429',
    ]

    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        if _is_non_actionable_log_line(clean):
            continue
        if any(re.search(kalip, clean, re.IGNORECASE) for kalip in etiketli_hata_kaliplari):
            detay = _normalize_hata_detay(clean)
            if detay and detay != 'Başarısız' and not _is_separator_line(detay):
                return detay

    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        if _is_non_actionable_log_line(clean):
            continue
        if any(re.search(kalip, clean, re.IGNORECASE) for kalip in oncelikli_hata_kaliplari):
            detay = _normalize_hata_detay(clean)
            if detay and detay != 'Başarısız' and not _is_separator_line(detay):
                return detay

    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        if _is_non_actionable_log_line(clean):
            continue
        detay = _normalize_hata_detay(clean)
        if detay and detay != 'Başarısız' and not _is_separator_line(detay):
            return detay
    return 'Başarısız'


def _detect_prompt_numarasi(logs_snapshot: list) -> str:
    """Log satırlarından hangi prompt/video/görselde işlem olduğunu tespit eder."""
    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        m0 = re.search(r'İŞLEM\s+\d+/\d+\s*:\s*(.+)$', clean, re.IGNORECASE)
        if m0:
            return m0.group(1).strip()
        m = re.search(r'[Pp]rompt\s*(\d+)', clean)
        if m: return f"Prompt {m.group(1)}"
        m2 = re.search(r'[Vv]ideo\s*(\d+)', clean)
        if m2: return f"Video {m2.group(1)}"
        m3 = re.search(r'[Gg][oö]rsel\s*(\d+)', clean)
        if m3: return f"Görsel {m3.group(1)}"
        m4 = re.search(r'#(\d+)', clean)
        if m4: return f"#{m4.group(1)}"
    return None

def _detect_pixverse_error_type(logs_snapshot: list) -> str:
    """
    Pixverse hatasının tipini log satırlarından tespit eder.
    Dönüş: 'prompt' | 'credit' | 'other'
    - 'prompt'  → Prompt çok uzun / karakter limiti aşıldı → Prompt Düzelt'e geri dön
    - 'credit'  → Kredi/kota yetersiz → doğrudan Video Üret'ten tekrar dene
    - 'other'   → Diğer hatalar → Video Üret'ten tekrar dene
    """
    PROMPT_KALIPLARI = [
        r'prompt.*uzun',            # "Prompt çok uzun", "prompt uzun"
        r'çok\s+uzun',              # "çok uzun"
        r'too\s+long',              # "too long"
        r'prompt.*too.*long',
        r'exceeds.*max.*length',
        r'cannot exceed.*characters',
        r'character.*limit',
        r'HATA.*[Pp]rompt.*karakter',   # "HATA: Prompt çok uzun! (3389 karakter)"
        r'chars?\s*exceeds',
        r'karakter.*s[iı]n[iı]r|karakter.*a[şs]',  # "karakter sınırı aşıldı"
        r'uzun.*karakter|karakter.*uzun',
    ]
    # Bilgi amaçlı satırları hariç tutmak için kullanılan kalıplar
    # (ör. "Prompt okundu: 1738 karakter" gibi satırlar hata değil)
    INFO_EXCLUDE_PATTERNS = [
        r'[Pp]rompt\s+okundu',
        r'\u2713',                     # ✓ işareti
        r'\[OK\]',
        r'\[INFO\].*okundu',
    ]
    KREDI_KALIPLARI = [
        r'kredi.*yetersiz|insufficient.*credit|not.*enough.*credit',
        r'quota.*exceeded|kota.*a[şs][ıi]ld[ıi]',
        r'balance.*insufficient|insufficient.*balance',
        r'payment.*required|402\b',
        r'credit.*balance|krediniz.*yetersiz',
        r'all\s*credits.*used\s*up|credits.*have.*been.*used|purchase\s*credits',
        r'Yetersiz Video Üretme Kredisi|kredinizi yenileyin',
    ]
    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        # Bilgi satırlarını atla — hata tespitinde yanlış pozitif üretirler
        if any(re.search(ep, clean, re.IGNORECASE) for ep in INFO_EXCLUDE_PATTERNS):
            continue
        # Sadece hata/uyarı içeren satırlara bak
        is_error_line = bool(re.search(r'ba[şs]ar[iı]s[iı]z|error|hata|fail|warn|SEBEP|DETAY', clean, re.IGNORECASE))
        if not is_error_line:
            continue
        for kalip in PROMPT_KALIPLARI:
            if re.search(kalip, clean, re.IGNORECASE):
                return "prompt"
        for kalip in KREDI_KALIPLARI:
            if re.search(kalip, clean, re.IGNORECASE):
                return "credit"
    return "other"


def _detect_gorsel_klonlama_error_type(logs_snapshot: list) -> str:
    """
    Görsel klonlama hatasının tipini tespit eder.
    Dönüş: 'api' | 'other'
    - 'api'   → API anahtarı/bağlantı/rate-limit hatası → Görsel Klonla'dan tekrar dene
    - 'other' → Diğer hatalar (görsel bulunamadı vb.) → Görsel Analiz'den baştan başla
    """
    API_KALIPLARI = [
        r'api.*key.*invalid|authentication|unauthorized|401\b',
        r'api.*hata[sı]?|api.*error',
        r'rate.*limit|too.*many.*requests|429\b',
        r'connection.*error|network.*error|bağlantı.*hata',
        r'request.*failed|istek.*başarısız',
        r'http.*error|ssl.*error',
    ]
    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        for kalip in API_KALIPLARI:
            if re.search(kalip, clean, re.IGNORECASE):
                return "api"
    return "other"


def _extract_summary_line(logs_snapshot: list, label_regex: str) -> str:
    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        if re.search(rf'^{label_regex}\s*:', clean, re.IGNORECASE):
            return clean
    return ""

def _extract_named_success_entries(logs_snapshot: list) -> list:
    line = _extract_summary_line(logs_snapshot, r'Ba[şs]ar[iı]l[iı]')
    if not line:
        return []
    m = re.search(r'Ba[şs]ar[iı]l[iı]\s*:\s*\d+\s*-\s*(.+)$', line, re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1).strip()
    if re.fullmatch(r'Yok', raw, re.IGNORECASE):
        return []
    # ' | ' (yeni format) veya ' - ' (eski format) ayırıcısını destekle
    sep = ' | ' if ' | ' in raw else ' - '
    return [p.strip() for p in raw.split(sep) if p.strip() and not re.fullmatch(r'Yok', p.strip(), re.IGNORECASE)]

def _split_summary_items(raw: str) -> list:
    """Parantez dengesini dikkate alarak öğeleri parçalar.

    Yeni format ' | ' ayırıcısı kullanır (sosyal_medya_paylasim v6+).
    Eski format ' - ' ayırıcısı da geriye dönük desteklenir.
    ' | ' varsa öncelikli olarak kullanılır.
    """
    # Yeni format: ' | ' ayırıcısı — parantez içinde ' | ' olmaz
    if ' | ' in raw:
        return [p.strip() for p in raw.split(' | ') if p.strip()]

    # Eski format: ' - ' ayırıcısı — parantez dengesini koru
    items = []
    current = []
    depth = 0
    parts = raw.split(' - ')
    for part in parts:
        current.append(part)
        depth += part.count('(') - part.count(')')
        if depth <= 0:
            items.append(' - '.join(current))
            current = []
            depth = 0
    if current:
        items.append(' - '.join(current))
    return items


def _extract_named_failure_entries(logs_snapshot: list) -> list:
    line = _extract_summary_line(logs_snapshot, r'Ba[şs]ar[iı]s[iı]z')
    if not line:
        return []
    m = re.search(r'Ba[şs]ar[iı]s[iı]z\s*:\s*\d+\s*-\s*(.+)$', line, re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1).strip()
    if re.fullmatch(r'Yok', raw, re.IGNORECASE):
        return []

    items = _split_summary_items(raw)

    out = []
    for part in items:
        part = part.strip()
        if not part:
            continue
        mm = re.match(r'(.+?)\s*\(\s*(.+)\s*\)\s*$', part)
        source = mm.group(1).strip() if mm else part
        raw_detay = mm.group(2).strip() if mm else 'Başarısız'
        out.append({
            "source": source,
            "raw_detay": raw_detay,
            "detay": _normalize_hata_detay(raw_detay),
        })
    return out

def _extract_pixverse_partial_entries(logs_snapshot: list) -> list:
    out = []
    seen = set()
    current_item = None

    for line in logs_snapshot or []:
        clean = _strip_log_prefix(line)

        m = re.search(r'İŞLEM\s+\d+/\d+\s*:\s*(.+)$', clean, re.IGNORECASE)
        if m:
            current_item = m.group(1).strip()
            continue

        if re.search(r'G[ÖO]RSEL\s+Y[ÜU]KLENEMED[İI]', clean, re.IGNORECASE):
            src = current_item or "Bilinmeyen Öğe"
            key = (src, 'Görsel Yüklenemedi')
            if key not in seen:
                seen.add(key)
                out.append({"source": src, "detay": 'Görsel Yüklenemedi'})
    return out

def _durum_ozeti_normalize_islem_adi(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').strip()).casefold()


def _durum_ozeti_ekle_ve_tasima_yap(kategori: str, islem: str, detay: str, zaman: str, aliases: list = None):
    """Aynı işlemi eski kategorilerden kaldırıp yeni kategoriye taşır."""
    ozet = st.session_state.durum_ozeti
    ozet.setdefault("hatali", [])
    ozet.setdefault("basarili", [])
    ozet.setdefault("kismi", [])

    adaylar = {_durum_ozeti_normalize_islem_adi(islem)}
    for alias in aliases or []:
        norm_alias = _durum_ozeti_normalize_islem_adi(alias)
        if norm_alias:
            adaylar.add(norm_alias)

    for key in ("hatali", "kismi", "basarili"):
        ozet[key] = [
            item for item in ozet.get(key, [])
            if _durum_ozeti_normalize_islem_adi(item.get("islem", "")) not in adaylar
        ]

    ozet[kategori].append({"islem": islem, "detay": detay, "zaman": zaman})


def durum_ozeti_guncelle(node_key: str, status: str, logs_snapshot: list = None):
    """Bir işlem tamamlandığında durum özetini günceller.

    Aynı işlem yeniden denendiğinde eski hata/kısmi kayıtlarını silip son sonucu gösterir.
    Böylece örneğin 'Video Üretme (Video Prompt 1)' önce hatalı, sonra başarılı olduysa
    durum özeti öğeyi Hatalı İşlemler'den çıkarıp Başarılı İşlemler'e taşır.
    """
    ozet = st.session_state.durum_ozeti
    ozet.setdefault("hatali", [])
    ozet.setdefault("basarili", [])
    ozet.setdefault("kismi", [])

    etiket = get_durum_islem_etiketi(node_key)
    zaman = time.strftime('%H:%M:%S')
    logs_snapshot = logs_snapshot or []

    # Sosyal medya paylaşımı için video bazlı gruplandırma yap.
    # Örnek çıktı:
    #   Sosyal Medya Paylaşım (Video 1)    Başarısız
    #     Youtube, TikTok, Instagram       Geçmiş Tarih Seçildi
    #   Sosyal Medya Paylaşım (Video 2)    Başarısız
    #     Youtube                          Geçmiş Tarih Seçildi
    #     Tiktok, Instagram                İşlem Başarısız
    if node_key == "sosyal_medya" and logs_snapshot:
        basarili_ogeler = _extract_named_success_entries(logs_snapshot)
        hatali_ogeler = _extract_named_failure_entries(logs_snapshot)

        hatali_kaynaklar = {item["source"] for item in hatali_ogeler}
        basarili_ogeler = [
            item for item in basarili_ogeler
            if item not in hatali_kaynaklar
        ]

        if basarili_ogeler or hatali_ogeler:
            # Önce eski sosyal medya kayıtlarını temizle
            for key in ("hatali", "kismi", "basarili"):
                ozet[key] = [
                    item for item in ozet.get(key, [])
                    if not item.get("islem", "").startswith(etiket)
                ]

            # --- Başarılı öğeleri video bazlı grupla ---
            # source format: "Video 1 - Youtube" → video="Video 1", platform="Youtube"
            from collections import OrderedDict
            basarili_video_grp = OrderedDict()
            for item in basarili_ogeler:
                parts = item.split(' - ', 1)
                if len(parts) == 2:
                    video_lbl, platform = parts[0].strip(), parts[1].strip()
                else:
                    video_lbl, platform = item.strip(), ""
                basarili_video_grp.setdefault(video_lbl, []).append(platform)

            for video_lbl, platforms in basarili_video_grp.items():
                islem_adi = f"{etiket} ({video_lbl})"
                platform_str = ", ".join(p for p in platforms if p)
                detay_str = f"Tamamlandı ({platform_str})" if platform_str else "Tamamlandı"
                ozet["basarili"].append({"islem": islem_adi, "detay": detay_str, "zaman": zaman})

            # --- Hatalı öğeleri video bazlı grupla ---
            # Önce video → {detay → [platformlar]} şeklinde grupla
            hatali_video_grp = OrderedDict()
            for item in hatali_ogeler:
                parts = item["source"].split(' - ', 1)
                if len(parts) == 2:
                    video_lbl, platform = parts[0].strip(), parts[1].strip()
                else:
                    video_lbl, platform = item["source"].strip(), ""
                detay = item["detay"]
                hatali_video_grp.setdefault(video_lbl, OrderedDict())
                hatali_video_grp[video_lbl].setdefault(detay, []).append(platform)

            for video_lbl, detay_map in hatali_video_grp.items():
                # Ana satır: Video başlığı + "Başarısız"
                islem_adi = f"{etiket} ({video_lbl})"
                ozet["hatali"].append({"islem": islem_adi, "detay": "Başarısız", "zaman": zaman})
                # Alt satırlar: Aynı hataya sahip platformlar virgülle birleştirilir
                for detay, platforms in detay_map.items():
                    platform_str = ", ".join(p for p in platforms if p)
                    if platform_str:
                        alt_islem = f"\u2003\u2003{platform_str}"
                    else:
                        alt_islem = f"\u2003\u2003Tüm Platformlar"
                    ozet["hatali"].append({"islem": alt_islem, "detay": detay, "zaman": zaman})

            ozet["son_guncelleme"] = zaman
            return

    if node_key == "pixverse" and logs_snapshot:
        basarili_ogeler = _extract_named_success_entries(logs_snapshot)
        hatali_ogeler = _extract_named_failure_entries(logs_snapshot)
        kismi_ogeler = _extract_pixverse_partial_entries(logs_snapshot)

        hatali_kaynaklar = {item["source"] for item in hatali_ogeler}
        kismi_kaynaklar = {item["source"] for item in kismi_ogeler}

        basarili_ogeler = [
            item for item in basarili_ogeler
            if item not in kismi_kaynaklar and item not in hatali_kaynaklar
        ]
        kismi_ogeler = [
            item for item in kismi_ogeler
            if item["source"] not in hatali_kaynaklar
        ]

        if basarili_ogeler or hatali_ogeler or kismi_ogeler:
            for item in basarili_ogeler:
                islem_adi = f"{etiket} ({item})"
                _durum_ozeti_ekle_ve_tasima_yap(
                    "basarili",
                    islem_adi,
                    "Tamamlandı",
                    zaman
                )

            for item in kismi_ogeler:
                islem_adi = f"{etiket} ({item['source']})"
                _durum_ozeti_ekle_ve_tasima_yap(
                    "kismi",
                    islem_adi,
                    item["detay"],
                    zaman
                )

            for item in hatali_ogeler:
                islem_adi = f"{etiket} ({item['source']})"
                _durum_ozeti_ekle_ve_tasima_yap(
                    "hatali",
                    islem_adi,
                    item["detay"],
                    zaman
                )

            ozet["son_guncelleme"] = zaman
            return

    if node_key == "download" and logs_snapshot:
        basarili_ogeler = _extract_named_success_entries(logs_snapshot)
        hatali_ogeler = _extract_named_failure_entries(logs_snapshot)

        hatali_kaynaklar = {item["source"] for item in hatali_ogeler}
        basarili_ogeler = [item for item in basarili_ogeler if item not in hatali_kaynaklar]

        if basarili_ogeler or hatali_ogeler:
            for item in basarili_ogeler:
                islem_adi = f"{etiket} ({item})"
                _durum_ozeti_ekle_ve_tasima_yap(
                    "basarili",
                    islem_adi,
                    "Tamamlandı",
                    zaman
                )

            for item in hatali_ogeler:
                islem_adi = f"{etiket} ({item['source']})"
                _durum_ozeti_ekle_ve_tasima_yap(
                    "hatali",
                    islem_adi,
                    item["detay"],
                    zaman
                )

            ozet["son_guncelleme"] = zaman
            return

    if status == "ok":
        _durum_ozeti_ekle_ve_tasima_yap(
            "basarili",
            etiket,
            "Tamamlandı",
            zaman
        )

    elif status == "partial":
        detay = "Kısmi Tamamlandı"
        if logs_snapshot:
            detay = _detect_hata_detay(logs_snapshot, node_key)
            if detay == "Başarısız":
                detay = "Kısmi Tamamlandı"

        _durum_ozeti_ekle_ve_tasima_yap(
            "kismi",
            etiket,
            detay,
            zaman
        )

    elif status == "error":
        hata_detay = "Başarısız"
        numara = None

        if logs_snapshot:
            hata_detay = _detect_hata_detay(logs_snapshot, node_key)
            numara = _detect_prompt_numarasi(logs_snapshot)

        hata_etiket = f"{etiket} ({numara})" if numara else etiket

        _durum_ozeti_ekle_ve_tasima_yap(
            "hatali",
            hata_etiket,
            hata_detay,
            zaman,
            aliases=[etiket]
        )

    ozet["son_guncelleme"] = zaman

def durum_ozeti_sifirla():
    """Durum özetini sıfırlar."""
    st.session_state.durum_ozeti = {"hatali": [], "basarili": [], "kismi": [], "son_guncelleme": None}

CONTROL_DIR = os.path.join(BASE_DIR, ".control")
os.makedirs(CONTROL_DIR, exist_ok=True)
PAUSE_FLAG = os.path.join(CONTROL_DIR, "PAUSE.flag")
STOP_FLAG  = os.path.join(CONTROL_DIR, "STOP.flag")
STATE_FILE = os.path.join(CONTROL_DIR, "STATE.json")
DONE_FILE  = os.path.join(CONTROL_DIR, "DONE.json")
FAILED_FILE= os.path.join(CONTROL_DIR, "FAILED.json")

def create_pause_flag():
    try:
        with open(PAUSE_FLAG, "w", encoding="utf-8") as f: f.write("")
        log("[INFO] PAUSE.flag oluşturuldu - Scriptler duraklatıldı")
    except Exception as e: log(f"[ERROR] PAUSE.flag oluşturulamadı: {e}")

def remove_pause_flag():
    try:
        if os.path.exists(PAUSE_FLAG): os.remove(PAUSE_FLAG); log("[INFO] PAUSE.flag silindi - Scriptler devam edecek")
    except Exception as e: log(f"[ERROR] PAUSE.flag silinemedi: {e}")

def create_stop_flag():
    try:
        with open(STOP_FLAG, "w", encoding="utf-8") as f: f.write("")
        log("[INFO] STOP.flag oluşturuldu - Scriptler sonlandırılacak")
    except Exception as e: log(f"[ERROR] STOP.flag oluşturulamadı: {e}")

def remove_stop_flag():
    try:
        if os.path.exists(STOP_FLAG): os.remove(STOP_FLAG); log("[INFO] STOP.flag silindi")
    except Exception as e: log(f"[ERROR] STOP.flag silinemedi: {e}")

def cleanup_flags():
    remove_pause_flag(); remove_stop_flag()

def _get_prompt_temp_upload_dir() -> str:
    settings_obj = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    prompt_script = str(settings_obj.get("prompt_script") or DEFAULT_SETTINGS.get("prompt_script") or "").strip()
    prompt_script_dir = os.path.dirname(prompt_script) if prompt_script else ""
    if prompt_script_dir:
        return os.path.join(prompt_script_dir, "temp_upload")
    return r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Prompt Oluşturma\temp_upload"



def cleanup_runtime_temp_files() -> list:
    cleaned = []

    def _remove_file_if_exists(path: str, label: str):
        try:
            if path and _is_safe_path(path) and os.path.isfile(path):
                os.remove(path)
                cleaned.append(label)
        except Exception as e:
            log(f"[WARN] Geçici dosya silinemedi: {path} -> {e}")

    def _remove_tree_if_exists(path: str, label: str):
        try:
            if path and _is_safe_path(path) and os.path.exists(path):
                shutil.rmtree(path, ignore_errors=False)
                cleaned.append(label)
        except Exception as e:
            log(f"[WARN] Geçici klasör silinemedi: {path} -> {e}")

    temp_audio_targets = [
        (os.path.join(BASE_DIR, "temp.m4a"), "temp.m4a"),
        (os.path.join(BASE_DIR, "temp-audio.m4a"), "temp-audio.m4a"),
        (os.path.join(CONTROL_DIR, "temp.m4a"), ".control\\temp.m4a"),
        (os.path.join(CONTROL_DIR, "temp-audio.m4a"), ".control\\temp-audio.m4a"),
    ]
    for temp_path, label in temp_audio_targets:
        _remove_file_if_exists(temp_path, label)

    split_dir = os.path.join(CONTROL_DIR, "_temp_video_split")
    _remove_tree_if_exists(split_dir, ".control\\_temp_video_split")

    prompt_temp_upload_dir = _get_prompt_temp_upload_dir()
    _remove_tree_if_exists(prompt_temp_upload_dir, "Prompt Oluşturma\\temp_upload")

    temp_video_path = st.session_state.get("video_bolum_temp_path")
    if temp_video_path:
        try:
            if os.path.abspath(str(temp_video_path)).startswith(os.path.abspath(split_dir)):
                st.session_state.video_bolum_temp_path = None
                st.session_state.video_bolum_temp_name = None
        except Exception:
            st.session_state.video_bolum_temp_path = None
            st.session_state.video_bolum_temp_name = None

    return cleaned



def cleanup_state_files():
    try:
        files_cleaned = []
        # 1. State dosyaları
        for fpath, fname in [(STATE_FILE, "STATE.json"), (DONE_FILE, "DONE.json"), (FAILED_FILE, "FAILED.json")]:
            if os.path.exists(fpath):
                os.remove(fpath)
                files_cleaned.append(fname)
        # 2. .control klasöründeki tüm geçici dosyalar (.log, .tmp, .exit, .pid, .node)
        if os.path.isdir(CONTROL_DIR):
            for fname in os.listdir(CONTROL_DIR):
                if fname.endswith(('.log', '.tmp', '.exit', '.pid', '.node')):
                    try:
                        os.remove(os.path.join(CONTROL_DIR, fname))
                        files_cleaned.append(fname)
                    except Exception:
                        pass
        # 3. Runtime geçici dosya/klasörleri
        try:
            runtime_cleaned = cleanup_runtime_temp_files()
            files_cleaned.extend([x for x in runtime_cleaned if x not in files_cleaned])
        except Exception:
            pass
        try:
            sm_cleaned = cleanup_social_media_state_files(clear_saved_plan=False, preserve_accounts=True)
            files_cleaned.extend([x for x in sm_cleaned if x not in files_cleaned])
        except Exception:
            pass
        if files_cleaned:
            log(f"[OK] .control klasörü ve geçici çalışma dosyaları temizlendi: {len(files_cleaned)} öğe silindi")
            log("[INFO] Tüm videolar ve linkler yeniden işlenecek")
        else:
            log("[INFO] .control klasörü ve geçici çalışma alanı zaten temiz")
    except Exception as e: log(f"[ERROR] Temizlik sırasında hata: {e}")


def _normalize_retry_target_name(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("\\", "/").split("/")[-1]
    text = os.path.splitext(text)[0]
    text = re.sub(r'[._\-]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


_ITEM_MATCH_KEYS = {
    "name", "source", "prompt", "prompt_name", "video_prompt", "title", "label",
    "item", "file", "path", "filename", "folder", "id", "key"
}


def _retry_target_matches(value, targets_norm: set) -> bool:
    norm = _normalize_retry_target_name(value)
    if not norm:
        return False

    for target in targets_norm:
        if not target:
            continue
        if norm == target or norm in target or target in norm:
            return True

    m_norm = re.search(r'(?:video\s*prompt|prompt|video)\s*(\d+)', norm, re.IGNORECASE)
    if not m_norm:
        return False

    for target in targets_norm:
        m_target = re.search(r'(?:video\s*prompt|prompt|video)\s*(\d+)', target, re.IGNORECASE)
        if m_target and m_target.group(1) == m_norm.group(1):
            return True
    return False


def _json_item_matches_retry_targets(item, targets_norm: set) -> bool:
    if isinstance(item, (str, int, float)):
        return _retry_target_matches(item, targets_norm)

    if isinstance(item, dict):
        for key, value in item.items():
            if str(key).strip().lower() in _ITEM_MATCH_KEYS and _json_item_matches_retry_targets(value, targets_norm):
                return True
        return False

    if isinstance(item, list):
        return any(_json_item_matches_retry_targets(v, targets_norm) for v in item)

    return False


def _prune_retry_targets_from_json(data, targets_norm: set):
    if isinstance(data, list):
        out = []
        changed = False
        for item in data:
            if isinstance(item, (str, int, float)):
                if _retry_target_matches(item, targets_norm):
                    changed = True
                    continue
                out.append(item)
                continue

            if isinstance(item, dict) and _json_item_matches_retry_targets(item, targets_norm):
                changed = True
                continue

            new_item, item_changed = _prune_retry_targets_from_json(item, targets_norm)
            changed = changed or item_changed
            out.append(new_item)
        return out, changed

    if isinstance(data, dict):
        out = {}
        changed = False
        for key, value in data.items():
            if _retry_target_matches(key, targets_norm):
                changed = True
                continue

            if isinstance(value, (dict, list)):
                new_value, sub_changed = _prune_retry_targets_from_json(value, targets_norm)
                out[key] = new_value
                changed = changed or sub_changed
            else:
                out[key] = value
        return out, changed

    return data, False


def _load_json_safe(path: str):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log(f"[WARN] JSON okunamadı: {os.path.basename(path)} ({e})")
    return None


def _write_json_safe(path: str, data) -> bool:
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log(f"[WARN] JSON yazılamadı: {os.path.basename(path)} ({e})")
        return False


def _recalculate_pixverse_last_success_in_state(data):
    """pixverse_state.done listesinden kesintisiz başarı uzunluğunu yeniden hesaplar."""
    if not isinstance(data, dict):
        return data, False

    pixverse_state = data.get('pixverse_state')
    if not isinstance(pixverse_state, dict):
        return data, False

    done = pixverse_state.get('done', [])
    if not isinstance(done, list):
        done = []

    done_set = {str(x).strip() for x in done if str(x).strip()}

    def _prompt_no(value):
        m = re.search(r'(?:video\s*prompt|prompt|video)\s*(\d+)', str(value or ''), re.IGNORECASE)
        return int(m.group(1)) if m else None

    nums = sorted({n for n in (_prompt_no(x) for x in done_set) if n is not None})
    contiguous = 0
    for num in nums:
        if num == contiguous + 1:
            contiguous = num
        elif num > contiguous + 1:
            break

    prev_last_success = pixverse_state.get('last_success', 0)
    try:
        prev_last_success = int(prev_last_success or 0)
    except Exception:
        prev_last_success = 0

    pixverse_state['done'] = done
    pixverse_state['last_success'] = contiguous
    data['pixverse_state'] = pixverse_state
    return data, (prev_last_success != contiguous)


def _set_batch_pixverse_retry_targets(logs_snapshot: list):
    targets = []
    seen = set()

    for item in _extract_named_failure_entries(logs_snapshot or []):
        source = (item.get('source') or '').strip()
        norm = _normalize_retry_target_name(source)
        if source and norm and norm not in seen:
            seen.add(norm)
            targets.append(source)

    if not targets:
        fallback = _detect_prompt_numarasi(logs_snapshot or [])
        norm = _normalize_retry_target_name(fallback)
        if fallback and norm:
            targets = [fallback]

    st.session_state.batch_pixverse_retry_targets = targets


def _reset_pixverse_retry_state_if_needed():
    raw_targets = st.session_state.get('batch_pixverse_retry_targets', []) or []
    targets_norm = {_normalize_retry_target_name(x) for x in raw_targets if _normalize_retry_target_name(x)}
    if not targets_norm:
        return False

    changed_files = []
    for path in (DONE_FILE, STATE_FILE, FAILED_FILE):
        data = _load_json_safe(path)
        if data is None:
            continue
        new_data, changed = _prune_retry_targets_from_json(data, targets_norm)
        if path == STATE_FILE and isinstance(new_data, dict):
            new_data, last_success_changed = _recalculate_pixverse_last_success_in_state(new_data)
            changed = changed or last_success_changed
        if changed and _write_json_safe(path, new_data):
            changed_files.append(os.path.basename(path))

    joined_targets = ', '.join(raw_targets)
    if changed_files:
        log(f"[INFO] Retry öncesi temizlendi: {', '.join(changed_files)} → {joined_targets}")
    else:
        log(f"[INFO] Retry hedefi bulundu ama state içinde eşleşme yok: {joined_targets}")

    st.session_state.batch_pixverse_retry_targets = []
    return bool(changed_files)

# ==========================================
# 3. BACKGROUND SCRIPT MOTORU
# ==========================================
def _bg_clear():
    try:
        fh = st.session_state.get("bg_log_fh")
        if fh: fh.close()
    except: pass
    st.session_state.bg_log_fh = None
    st.session_state.bg_proc = None
    st.session_state.bg_owner = None
    st.session_state.bg_node_key = None
    st.session_state.bg_log_path = None
    st.session_state.bg_log_pos = 0
    st.session_state.bg_log_start_index = 0
    st.session_state.bg_terminated_by_user = False
    st.session_state.bg_terminated_node_key = None

def bg_is_running() -> bool:
    return st.session_state.get("bg_proc") is not None

def bg_start(owner: str, node_key: str, script_path: str, args=None) -> bool:
    args = args or[]
    if bg_is_running(): return False
    py = sys.executable
    if not os.path.exists(script_path):
        st.session_state.status[node_key] = "error"
        log(f"[ERROR] Script bulunamadi: {script_path}")
        return False

    st.session_state.bg_last_result = None
    st.session_state.status[node_key] = "running"
    cmd =[py, "-u", script_path] + args
    log(f"[INFO] Calistiriliyor: {os.path.basename(script_path)}")
    log("=" * 60)

    log_start_index = len(st.session_state.logs)
    os.makedirs(CONTROL_DIR, exist_ok=True)
    log_path = os.path.join(CONTROL_DIR, f"RUN_{owner}_{node_key}.log")

    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        env['PYTHONUNBUFFERED'] = '1'
        proc_cwd = None
        if node_key in ("video_montaj", "toplu_video"):
            proc_cwd = CONTROL_DIR
        f = open(log_path, "w", encoding="utf-8", errors="replace")
        st.session_state.bg_log_fh = f
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, encoding='utf-8', errors='replace', env=env, cwd=proc_cwd)
        st.session_state.bg_proc = proc
        st.session_state.bg_owner = owner
        st.session_state.bg_node_key = node_key
        st.session_state.bg_log_path = log_path
        st.session_state.bg_log_pos = 0
        st.session_state.bg_log_start_index = log_start_index
        return True
    except Exception as e:
        st.session_state.status[node_key] = "error"
        log(f"[EXCEPTION] {node_key}: {str(e)}")
        _bg_clear()
        return False

def bg_terminate() -> bool:
    proc = st.session_state.get("bg_proc")
    if proc is None: return False
    node_key = st.session_state.get("bg_node_key")
    pid = getattr(proc, "pid", None)
    st.session_state.bg_terminated_by_user = True
    st.session_state.bg_terminated_node_key = node_key
    log(f"[WARN] İşlem anında kesiliyor (PID: {pid})... Lütfen bekleyin.")

    try:
        if os.name == "nt" and pid:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except Exception:
            try: proc.kill()
            except Exception: pass
    except Exception as e:
        log(f"[WARN] İşlem sonlandırma hatası: {e}")
        return False
    return True

def _read_text_file_safe(path: str) -> str:
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception:
        pass
    return ""


def _is_verbose_social_log_line(text: str) -> bool:
    clean = _strip_log_prefix(text)
    if not clean:
        return False

    noisy_patterns = [
        r'^Stacktrace:?$',
        r'^selenium\.common\.exceptions\.',
        r'^https://www\.selenium\.dev/documentation/webdriver/troubleshooting/errors',
        r'^File "[A-Za-z]:\\.*sosyal_medya_paylas[ıi]m\.py"',
        r'^driver\s*=\s*uc\.Chrome',
        r'^undetected_chromedriver',
        r'^Current browser version is\s*\d+',
        r'^from session not created:',
        r'^session not created: cannot connect to chrome',
        r'^cannot connect to chrome at 127\.0\.0\.1',
        r'^\[0x[0-9A-Fa-f]+\]$',
        # Selenium verbose hata detayları
        r'^\(Session info:',
        r'Session info:\s*chrome=',
        r'^Message:\s*no such element',
        r'^Message:\s*Unable to locate element',
        r'^\{"method":"xpath"',
        r'^For documentation on this error',
        r'^please visit:',
        r'KERNEL32!BaseThreadInitThunk',
        r'ntdll!Rtl',
        r'^documentation on this error',
    ]
    return any(re.search(pattern, clean, re.IGNORECASE) for pattern in noisy_patterns)


def _split_nonempty_lines(text: str) -> list:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _write_lines_to_file(path: str, lines: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def _save_links_to_path(path: str, text: str, append: bool = False) -> dict:
    path = (path or "").strip()
    if not path:
        raise ValueError("Link dosya yolu boş.")

    existing_lines = _split_nonempty_lines(_read_text_file_safe(path)) if append else []
    incoming_lines = _split_nonempty_lines(text)

    if append:
        seen = set(existing_lines)
        added_lines = []
        for line in incoming_lines:
            if line not in seen:
                seen.add(line)
                added_lines.append(line)
        final_lines = existing_lines + added_lines
    else:
        added_lines = incoming_lines
        final_lines = incoming_lines

    _write_lines_to_file(path, final_lines)
    return {
        "mode": "append" if append else "overwrite",
        "path": path,
        "existing": len(existing_lines),
        "incoming": len(incoming_lines),
        "added": len(added_lines),
        "total": len(final_lines),
    }


def _cleanup_file_quiet(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


_VIDEO_OUTPUT_META_FILE = "video_result.json"


def _extract_trailing_number(value: str):
    m = re.search(r'(\d+)\s*$', str(value or '').strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _list_generated_video_dirs(video_root: str) -> list:
    out = []
    root = str(video_root or '').strip()
    if not root or not os.path.isdir(root):
        return out

    for name in os.listdir(root):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if not re.match(r'^Video\s+\d+$', name, re.IGNORECASE):
            continue

        meta_path = os.path.join(path, _VIDEO_OUTPUT_META_FILE)
        meta = _load_json_safe(meta_path) if os.path.exists(meta_path) else {}
        if not isinstance(meta, dict):
            meta = {}

        prompt_name = str(meta.get('prompt_folder') or meta.get('prompt_name') or meta.get('source') or '').strip()
        try:
            item_count = sum(1 for _ in os.scandir(path))
        except Exception:
            item_count = 0
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            mtime = 0.0

        out.append({
            'name': name,
            'path': path,
            'folder_no': _extract_trailing_number(name),
            'prompt_name': prompt_name,
            'prompt_no': _extract_trailing_number(prompt_name),
            'has_meta': os.path.exists(meta_path),
            'item_count': item_count,
            'mtime': mtime,
        })

    return out


def _choose_best_video_dir_entry(current: dict | None, candidate: dict) -> dict:
    if current is None:
        return candidate

    current_key = (
        1 if current.get('has_meta') else 0,
        int(current.get('item_count') or 0),
        float(current.get('mtime') or 0.0),
    )
    candidate_key = (
        1 if candidate.get('has_meta') else 0,
        int(candidate.get('item_count') or 0),
        float(candidate.get('mtime') or 0.0),
    )
    return candidate if candidate_key >= current_key else current


def _normalize_generated_video_output_dirs_after_pixverse() -> dict:
    settings_obj = st.session_state.get('settings', {}) if isinstance(st.session_state.get('settings', {}), dict) else {}
    video_root = str(settings_obj.get('video_output_dir') or '').strip()
    result = {
        'video_root': video_root,
        'removed_empty': [],
        'renamed': [],
        'duplicates': [],
        'errors': [],
    }

    if not video_root or not os.path.isdir(video_root):
        return result

    entries = _list_generated_video_dirs(video_root)
    if not entries:
        return result

    # 1) Başarısız işlemlerden kalan gerçekten boş klasörleri temizle.
    for entry in list(entries):
        if int(entry.get('item_count') or 0) != 0:
            continue
        try:
            shutil.rmtree(entry['path'], ignore_errors=False)
            result['removed_empty'].append(entry['name'])
        except Exception as e:
            result['errors'].append(f"{entry['name']} silinemedi: {e}")

    entries = [e for e in _list_generated_video_dirs(video_root) if e.get('prompt_no') is not None]
    if not entries:
        return result

    stamp = int(time.time() * 1000)
    managed_entries = []

    # 2) Başarılı klasörleri geçici isimlere taşı; böylece hedef slotlar serbest kalır.
    for idx, entry in enumerate(entries, start=1):
        temp_name = f"__video_norm_tmp__{stamp}_{idx}"
        temp_path = os.path.join(video_root, temp_name)
        try:
            os.replace(entry['path'], temp_path)
            moved = dict(entry)
            moved['original_name'] = entry['name']
            moved['temp_name'] = temp_name
            moved['path'] = temp_path
            managed_entries.append(moved)
        except Exception as e:
            result['errors'].append(f"{entry['name']} geçici klasöre taşınamadı: {e}")

    if not managed_entries:
        return result

    winners = {}
    duplicates = []
    for entry in managed_entries:
        prompt_no = entry.get('prompt_no')
        best = _choose_best_video_dir_entry(winners.get(prompt_no), entry)
        if best is entry:
            old = winners.get(prompt_no)
            if old is not None:
                duplicates.append(old)
            winners[prompt_no] = entry
        else:
            duplicates.append(entry)

    # 3) Kazanan klasörleri doğru Video N slotuna yerleştir.
    for prompt_no in sorted(winners):
        entry = winners[prompt_no]
        target_name = f"Video {prompt_no}"
        target_path = os.path.join(video_root, target_name)
        if os.path.exists(target_path):
            backup_name = f"{target_name}__eski__{stamp}"
            backup_path = os.path.join(video_root, backup_name)
            try:
                os.replace(target_path, backup_path)
                result['duplicates'].append(backup_name)
            except Exception as e:
                result['errors'].append(f"{target_name} çakışma klasörü yedeklenemedi: {e}")
                continue
        try:
            os.replace(entry['path'], target_path)
            if entry.get('original_name') != target_name:
                result['renamed'].append((entry.get('original_name'), target_name))
        except Exception as e:
            result['errors'].append(f"{entry.get('original_name')} → {target_name} taşınamadı: {e}")
            fallback_path = os.path.join(video_root, entry.get('original_name') or os.path.basename(entry['path']))
            if not os.path.exists(fallback_path):
                try:
                    os.replace(entry['path'], fallback_path)
                except Exception:
                    pass

    # 4) Aynı prompttan birden fazla başarılı klasör varsa geri kalanları koru ama yedek olarak ayır.
    for idx, entry in enumerate(duplicates, start=1):
        if not os.path.exists(entry['path']):
            continue
        fallback_name = entry.get('original_name') or f"Video Yedek {idx}"
        fallback_path = os.path.join(video_root, fallback_name)
        if os.path.exists(fallback_path):
            fallback_name = f"{fallback_name}__yedek__{stamp}_{idx}"
            fallback_path = os.path.join(video_root, fallback_name)
        try:
            os.replace(entry['path'], fallback_path)
            result['duplicates'].append(fallback_name)
        except Exception as e:
            result['errors'].append(f"Tekrarlayan çıktı klasörü korunamadı: {e}")

    return result


def _log_generated_video_output_dir_fix(summary: dict):
    if not isinstance(summary, dict):
        return

    removed = summary.get('removed_empty') or []
    renamed = summary.get('renamed') or []
    errors = summary.get('errors') or []

    if removed:
        log(f"[INFO] Boş başarısız video klasörleri temizlendi: {', '.join(removed)}")

    if renamed:
        rename_text = ', '.join(f"{src}→{dst}" for src, dst in renamed)
        log(f"[INFO] Üretilen videolar doğru klasörlere yerleştirildi: {rename_text}")

    for err in errors[:5]:
        log(f"[WARN] Video klasör düzenleme uyarısı: {err}")


def _prepare_youtube_link_output(append_mode: bool = False) -> str:
    target_path = (st.session_state.settings.get("links_file") or "").strip()
    if append_mode:
        temp_path = os.path.join(CONTROL_DIR, f"youtube_links_append_{int(time.time() * 1000)}.txt")
        st.session_state["youtube_link_pending_output_merge"] = {
            "enabled": True,
            "temp_output": temp_path,
            "target_output": target_path,
        }
        return temp_path

    st.session_state["youtube_link_pending_output_merge"] = {
        "enabled": False,
        "temp_output": target_path,
        "target_output": target_path,
    }
    return target_path


def _finalize_pending_youtube_link_output(success: bool):
    meta = st.session_state.pop("youtube_link_pending_output_merge", None)
    if not isinstance(meta, dict):
        return

    enabled = bool(meta.get("enabled"))
    temp_output = (meta.get("temp_output") or "").strip()
    target_output = (meta.get("target_output") or "").strip()

    try:
        if enabled and success:
            new_text = _read_text_file_safe(temp_output)
            result = _save_links_to_path(target_output, new_text, append=True)
            if result.get("added", 0) > 0:
                log(f"[OK] YouTube linkleri mevcut listenin devamına eklendi: +{result['added']} yeni link")
            else:
                log("[WARN] Yeni YouTube linki bulunamadı; mevcut liste değişmedi.")
    except Exception as e:
        log(f"[ERROR] YouTube linklerini mevcut listenin devamına ekleme hatası: {e}")
    finally:
        if enabled and temp_output and os.path.abspath(temp_output) != os.path.abspath(target_output or temp_output):
            _cleanup_file_quiet(temp_output)


def _get_next_added_video_index() -> int:
    max_no = 0
    for entry in _list_added_video_entries():
        try:
            max_no = max(max_no, int(entry.get("no") or 0))
        except Exception:
            pass
    return max_no + 1 if max_no > 0 else 1


def _cleanup_pixverse_prompt_override():
    meta = st.session_state.get("pixverse_prompt_override_meta")
    if not isinstance(meta, dict):
        st.session_state.pixverse_prompt_override_meta = None
        return

    if meta.get("is_gorsel_override"):
        orig_dir = meta.get("original_settings_prompt_dir")
        orig_ref = meta.get("original_settings_ref_dir")
        if orig_dir is not None:
            st.session_state.settings["prompt_dir"] = orig_dir
        if orig_ref is not None:
            st.session_state.settings["gorsel_klonlama_dir"] = orig_ref
        save_settings(st.session_state.settings)
        st.session_state.pixverse_prompt_override_meta = None
        return

    original_prompt_dir = (meta.get("original_prompt_dir") or "").strip()
    stash_dir = (meta.get("stash_dir") or "").strip()
    moved_folders = meta.get("moved_folders") or []

    for folder_name in moved_folders:
        name = str(folder_name or "").strip()
        if not name:
            continue
        src = os.path.join(stash_dir, name) if stash_dir else ""
        dst = os.path.join(original_prompt_dir, name) if original_prompt_dir else ""
        try:
            if src and dst and os.path.exists(src) and not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
        except Exception as e:
            log(f"[WARN] Prompt klasörü geri taşınamadı ({name}): {e}")

    if stash_dir:
        try:
            shutil.rmtree(stash_dir, ignore_errors=True)
        except Exception:
            pass

    st.session_state.pixverse_prompt_override_meta = None


def bg_tick():
    proc = st.session_state.get("bg_proc")
    if proc is None: return

    node_key = st.session_state.get("bg_node_key")
    owner = st.session_state.get("bg_owner")
    log_path = st.session_state.get("bg_log_path")
    pos = int(st.session_state.get("bg_log_pos", 0) or 0)

    if log_path and os.path.exists(log_path):
        try:
            # Log dosyasına yazılan verinin diske ulaştığından emin ol (buffer flush)
            fh = st.session_state.get("bg_log_fh")
            if fh and not fh.closed:
                try:
                    fh.flush()
                except Exception:
                    pass
            with open(log_path, "r", encoding="utf-8", errors="replace") as rf:
                rf.seek(pos)
                data = rf.read()
                st.session_state.bg_log_pos = rf.tell()
            if data:
                for ln in data.splitlines(): log(ln)
        except Exception as e: log(f"[WARN] Log okunamadi: {e}")

    rc = proc.poll()
    if rc is None: return

    if log_path and os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as rf:
                rf.seek(int(st.session_state.get("bg_log_pos", 0) or 0))
                data = rf.read()
                st.session_state.bg_log_pos = rf.tell()
            if data:
                for ln in data.splitlines(): log(ln)
        except Exception: pass

    terminated_by_user = bool(st.session_state.get("bg_terminated_by_user", False))
    youtube_append_success = False

    if terminated_by_user:
        if not (st.session_state.get("single_paused", False) or st.session_state.get("batch_paused", False)):
            st.session_state.status[node_key] = "idle"
        _nk_lbl = get_durum_islem_etiketi(node_key)
        log(f"[WARN] {_nk_lbl} kullanıcı eylemiyle durduruldu/kapatıldı.")
    else:
        _nk_lbl = get_durum_islem_etiketi(node_key)
        if rc == 0:
            current_run_logs = st.session_state.logs[st.session_state.get("bg_log_start_index", 0):]
            if node_key == "pixverse":
                _pixverse_dir_fix = _normalize_generated_video_output_dirs_after_pixverse()
                _log_generated_video_output_dir_fix(_pixverse_dir_fix)
            real_status = _detect_partial_status(current_run_logs, node_key)
            st.session_state.status[node_key] = real_status
            youtube_append_success = real_status in ("ok", "partial")
            if real_status == "ok":
                if node_key != "youtube_link":
                    log(f"[OK] {_nk_lbl} başarıyla tamamlandı.")
            elif real_status == "partial":
                recent = " ".join(current_run_logs)
                if re.search(r'\[SKIP\]|SKIP\s*\(DONE\)|Atland[iı]\s*\(Zaten|zaten.*i[şs]lendi|tüm.*url.*tamamland', recent, re.IGNORECASE):
                    log(f"[WARN] {_nk_lbl}: Tüm öğeler zaten mevcut / atlandı. Yeni işlem yapılmadı.")
                else: log(f"[WARN] {_nk_lbl} kısmen tamamlandı (bazı ögeler başarısız).")
            else: log(f"[ERROR] {_nk_lbl} tüm ögeler başarısız oldu.")
            if node_key == "youtube_link":
                _finalize_pending_youtube_link_output(youtube_append_success)
            # Durum özetini güncelle
            durum_ozeti_guncelle(node_key, real_status, current_run_logs)
        else:
            st.session_state.status[node_key] = "error"
            _err_logs = st.session_state.logs[st.session_state.get("bg_log_start_index", 0):]
            hata_detay = _detect_hata_detay(_err_logs, node_key) if _err_logs else "Başarısız"
            if hata_detay and hata_detay != "Başarısız":
                log(f"[ERROR] {_nk_lbl} hata ile sonlandı (kod: {rc}, neden: {hata_detay})")
            else:
                log(f"[ERROR] {_nk_lbl} hata ile sonlandı (kod: {rc})")
            if node_key == "youtube_link":
                _finalize_pending_youtube_link_output(False)
            # Durum özetini güncelle (hata kodu ile sonlanma)
            if node_key == "pixverse":
                _pixverse_dir_fix = _normalize_generated_video_output_dirs_after_pixverse()
                _log_generated_video_output_dir_fix(_pixverse_dir_fix)
            durum_ozeti_guncelle(node_key, "error", _err_logs)

    if terminated_by_user and node_key == "youtube_link":
        _finalize_pending_youtube_link_output(False)

    if node_key == "pixverse":
        _cleanup_pixverse_prompt_override()

    st.session_state.bg_last_result = {"owner": owner, "node_key": node_key, "status": st.session_state.status.get(node_key), "success": st.session_state.status.get(node_key) in ("ok", "partial"), "rc": rc, "terminated_by_user": terminated_by_user}
    _bg_clear()

# LOG AKIŞI ÇAĞRISI
bg_tick()


# --- EARLY BOOTSTRAP VIDEO HELPERS ---
# Not: Streamlit scripti yukarıdan aşağıya çalıştığı için, batch/single start fonksiyonları
# bu yardımcılar henüz aşağıda tanımlanmadan çağrılabiliyor. Bu erken tanımlar NameError
# zincirini önler; dosyanın alt kısmındaki tam sürümler daha sonra bunların üzerine yazılabilir.

if "_video_montaj_sort_key" not in globals():
    def _video_montaj_sort_key(value: str):
        parts = re.split(r'(\d+)', str(value or ''))
        return [int(p) if p.isdigit() else p.casefold() for p in parts]


if "_read_links_count" not in globals():
    def _read_links_count() -> int:
        links_file = st.session_state.settings.get("links_file", "")
        if not links_file or not os.path.exists(links_file):
            return 0
        try:
            with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
                return len([ln for ln in f.read().splitlines() if ln.strip()])
        except Exception:
            return 0


def _bootstrap_is_supported_video_name(name: str) -> bool:
    return str(name or "").lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm"))


if "_list_download_video_entries" not in globals():
    def _list_download_video_entries() -> list:
        root = (st.session_state.settings.get("download_dir") or "").strip()
        if not root or not os.path.isdir(root):
            return []

        out = []
        try:
            klasorler = [k for k in os.listdir(root) if os.path.isdir(os.path.join(root, k))]
        except Exception:
            return []

        klasorler.sort(key=_video_montaj_sort_key)
        for idx, klasor_adi in enumerate(klasorler, start=1):
            klasor_yolu = os.path.join(root, klasor_adi)
            try:
                videolar = [
                    f for f in os.listdir(klasor_yolu)
                    if os.path.isfile(os.path.join(klasor_yolu, f)) and _bootstrap_is_supported_video_name(f)
                ]
            except Exception:
                videolar = []

            if not videolar:
                continue

            videolar.sort(key=_video_montaj_sort_key)
            video_adi = videolar[0]
            match = re.search(r'(\d+)\s*$', klasor_adi)
            no = int(match.group(1)) if match else idx
            out.append({
                "no": no,
                "folder_name": klasor_adi,
                "folder_path": klasor_yolu,
                "video_name": video_adi,
                "video_path": os.path.join(klasor_yolu, video_adi),
                "source_kind": "download",
            })
        return out


if "_list_toplu_video_added_source_items" not in globals():
    def _bootstrap_list_added_video_entries() -> list:
        root = (st.session_state.settings.get("added_video_dir") or "").strip()
        if not root or not os.path.isdir(root):
            return []

        out = []
        try:
            klasorler = [k for k in os.listdir(root) if os.path.isdir(os.path.join(root, k))]
        except Exception:
            return []

        klasorler.sort(key=_video_montaj_sort_key)
        for idx, klasor_adi in enumerate(klasorler, start=1):
            klasor_yolu = os.path.join(root, klasor_adi)
            try:
                videolar = [
                    f for f in os.listdir(klasor_yolu)
                    if os.path.isfile(os.path.join(klasor_yolu, f)) and _bootstrap_is_supported_video_name(f)
                ]
            except Exception:
                videolar = []

            if not videolar:
                continue

            videolar.sort(key=_video_montaj_sort_key)
            video_adi = videolar[0]
            match = re.search(r'(\d+)\s*$', klasor_adi)
            no = int(match.group(1)) if match else idx
            out.append({
                "no": no,
                "folder_name": klasor_adi,
                "folder_path": klasor_yolu,
                "video_name": video_adi,
                "video_path": os.path.join(klasor_yolu, video_adi),
            })
        return out

    def _list_toplu_video_added_source_items() -> list:
        items = []
        for idx, entry in enumerate(_bootstrap_list_added_video_entries(), start=1):
            items.append({
                "token": str(idx),
                "script_token": str(idx - 1),
                "label": f"[{idx}] Eklenen Video {entry.get('no', idx)}",
                "path": entry.get("video_path", ""),
                "exists": True,
                "expected": False,
                "video_no": int(entry.get("no", idx) or idx),
                "source_kind": "added_video",
            })
        return items


if "_list_video_montaj_assets" not in globals():
    def _list_video_montaj_assets():
        s = st.session_state.settings
        video_root = s.get("video_output_dir", "")
        klon_root = s.get("klon_video_dir", "")
        gorsel_root = s.get("video_montaj_gorsel_dir", "")
        link_count = _read_links_count()

        normal_by_no = {}
        if video_root and os.path.isdir(video_root):
            for item in os.listdir(video_root):
                item_path = os.path.join(video_root, item)
                if not os.path.isdir(item_path):
                    continue

                m = re.match(r'^Video\s+(\d+)$', item, re.IGNORECASE)
                if not m:
                    continue

                video_no = int(m.group(1))
                media_files = []
                for fname in os.listdir(item_path):
                    if _bootstrap_is_supported_video_name(fname):
                        media_files.append(os.path.join(item_path, fname))

                media_files.sort(key=lambda p: _video_montaj_sort_key(os.path.basename(p)))
                if media_files:
                    normal_by_no[video_no] = {
                        "folder_name": item,
                        "path": media_files[0],
                        "exists": True,
                        "video_no": video_no,
                        "source_kind": "video_output",
                    }

        download_by_no = {}
        for entry in _list_download_video_entries():
            try:
                video_no = int(entry.get("no") or 0)
            except Exception:
                video_no = 0
            if video_no <= 0:
                continue
            download_by_no[video_no] = {
                "folder_name": entry.get("folder_name") or f"Video {video_no}",
                "path": entry.get("video_path") or "",
                "exists": bool(entry.get("video_path")),
                "video_no": video_no,
                "source_kind": "download",
            }

        klon_items = []
        if klon_root and os.path.isdir(klon_root):
            for item in os.listdir(klon_root):
                item_path = os.path.join(klon_root, item)
                if not os.path.isdir(item_path):
                    continue

                m = re.match(r'^Klon\s+Video\s+(\d+)$', item, re.IGNORECASE)
                if not m:
                    continue

                clone_no = int(m.group(1))
                media_files = []
                for fname in os.listdir(item_path):
                    if _bootstrap_is_supported_video_name(fname):
                        media_files.append(os.path.join(item_path, fname))

                media_files.sort(key=lambda p: _video_montaj_sort_key(os.path.basename(p)))
                if media_files:
                    klon_items.append({
                        "folder_name": item,
                        "path": media_files[0],
                        "exists": True,
                        "clone_no": clone_no,
                    })

        klon_items.sort(key=lambda x: x["clone_no"])

        all_videos = []
        display_no = 1

        for video_no in range(1, link_count + 1):
            if video_no in normal_by_no:
                entry = normal_by_no[video_no]
                all_videos.append({
                    "token": str(display_no),
                    "script_token": str(display_no - 1),
                    "label": f"[{display_no}] Video {video_no}",
                    "path": entry["path"],
                    "exists": True,
                    "expected": False,
                    "video_no": video_no,
                    "source_kind": entry.get("source_kind", "video_output"),
                })
            elif video_no in download_by_no:
                entry = download_by_no[video_no]
                all_videos.append({
                    "token": str(display_no),
                    "script_token": str(display_no - 1),
                    "label": f"[{display_no}] İndirilen Video {video_no}",
                    "path": entry["path"],
                    "exists": True,
                    "expected": False,
                    "video_no": video_no,
                    "source_kind": "download",
                })
            else:
                all_videos.append({
                    "token": str(display_no),
                    "script_token": str(display_no - 1),
                    "label": f"[{display_no}] Link Video {video_no}",
                    "path": "",
                    "exists": False,
                    "expected": True,
                    "video_no": video_no,
                })
            display_no += 1

        extra_normal_nos = sorted(set(
            [n for n in normal_by_no.keys() if n > link_count] +
            [n for n in download_by_no.keys() if n > link_count]
        ))
        for video_no in extra_normal_nos:
            entry = normal_by_no.get(video_no) or download_by_no.get(video_no)
            if not entry:
                continue
            label_prefix = "İndirilen Video" if entry.get("source_kind") == "download" else "Video"
            all_videos.append({
                "token": str(display_no),
                "script_token": str(display_no - 1),
                "label": f"[{display_no}] {label_prefix} {video_no}",
                "path": entry["path"],
                "exists": True,
                "expected": False,
                "video_no": video_no,
                "source_kind": entry.get("source_kind", "video_output"),
            })
            display_no += 1

        for entry in klon_items:
            all_videos.append({
                "token": str(display_no),
                "script_token": str(display_no - 1),
                "label": f"[{display_no}] Klon Video {entry['clone_no']}",
                "path": entry["path"],
                "exists": True,
                "expected": False,
                "clone_no": entry["clone_no"],
                "source_kind": "clone",
            })
            display_no += 1

        all_images = []
        if gorsel_root and os.path.isdir(gorsel_root):
            image_files = []
            for fname in os.listdir(gorsel_root):
                if fname.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
                    image_files.append(os.path.join(gorsel_root, fname))

            image_files.sort(key=lambda p: _video_montaj_sort_key(os.path.basename(p)))

            for idx, full_path in enumerate(image_files, start=1):
                token = f"G{idx}"
                all_images.append({
                    "token": token,
                    "label": f"[{token}] {os.path.basename(full_path)}",
                    "path": full_path,
                })

        return {"videos": all_videos, "images": all_images}


if "_remap_numeric_selection_text" not in globals():
    def _remap_numeric_selection_text(text_value: str, token_remap: dict) -> str:
        raw = (text_value or "").strip()
        if not raw or not token_remap:
            return raw
        if raw.upper() == "T":
            return raw

        parts = [p.strip() for p in re.split(r'[\s,;]+', raw) if p.strip()]
        if not parts:
            return raw

        out = []
        for part in parts:
            upper = part.upper()
            if re.fullmatch(r'\d+', upper):
                mapped = token_remap.get(str(int(upper)))
                if mapped and mapped not in out:
                    out.append(mapped)
            else:
                if upper not in out:
                    out.append(upper)
        return ",".join(out) if out else "T"


if "_prepare_mevcut_video_runner_dirs" not in globals():
    def _prepare_mevcut_video_runner_dirs(video_items: list, temp_prefix: str = "video_montaj") -> tuple[str, str, dict]:
        existing_items = []
        token_remap = {}
        next_token = 1

        for item in (video_items or []):
            token = str(item.get("token") or "").strip()
            path = (item.get("path") or "").strip()
            if not token or not item.get("exists") or not path or not os.path.isfile(path):
                continue
            token_remap[token] = str(next_token)
            next_token += 1
            existing_items.append(item)

        has_download_source = any((item.get("source_kind") == "download") for item in existing_items)
        if not has_download_source:
            return "", "", token_remap

        temp_root = os.path.join(CONTROL_DIR, f"{temp_prefix}_sources_{int(time.time() * 1000)}")
        normal_root = os.path.join(temp_root, "video")
        clone_root = os.path.join(temp_root, "klon_video")
        os.makedirs(normal_root, exist_ok=True)
        os.makedirs(clone_root, exist_ok=True)

        normal_index = 1
        clone_index = 1
        copied_count = 0

        for item in existing_items:
            src_path = (item.get("path") or "").strip()
            if not src_path or not os.path.isfile(src_path):
                continue

            is_clone = item.get("source_kind") == "clone" or ("clone_no" in item)
            if is_clone:
                folder_name = f"Klon Video {clone_index}"
                target_root = clone_root
                clone_index += 1
            else:
                folder_name = f"Video {normal_index}"
                target_root = normal_root
                normal_index += 1

            dst_dir = os.path.join(target_root, folder_name)
            os.makedirs(dst_dir, exist_ok=True)
            dst_path = os.path.join(dst_dir, os.path.basename(src_path))
            try:
                shutil.copy2(src_path, dst_path)
                copied_count += 1
            except Exception as e:
                log(f"[WARN] Geçici montaj kaynağı hazırlanamadı: {src_path} -> {e}")

        if copied_count:
            log(f"[INFO] İndirilen videolar montaj kaynağına dahil edildi: {copied_count} dosya hazırlandı.")
        return normal_root, clone_root, token_remap


if "_orijinal_ses_kaynak_sirasi_to_paths" not in globals():
    def _bootstrap_orijinal_ses_kaynak_sirasi_normalize(value: str) -> str:
        raw = (value or "").strip().upper()
        if not raw:
            return ""
        parts = [p.strip() for p in re.split(r'[\s,;]+', raw) if p.strip()]
        if not parts:
            return ""
        if any(p == "T" for p in parts):
            return "T"
        out = []
        for p in parts:
            if re.fullmatch(r'\d+', p):
                out.append(str(int(p)))
        return ",".join(out)

    def _orijinal_ses_kaynak_sirasi_to_paths(text_value: str, video_items: list) -> list:
        token_to_path = {}
        tum_yollar = []
        for item in (video_items or []):
            token = str(item.get("token") or "").strip()
            path = (item.get("path") or "").strip()
            if not token or not path or not item.get("exists", True):
                continue
            token_to_path[token] = path
            tum_yollar.append(path)

        normalized = _bootstrap_orijinal_ses_kaynak_sirasi_normalize(text_value)
        if not normalized:
            return []
        if normalized == "T":
            return tum_yollar

        out = []
        for part in normalized.split(","):
            path = token_to_path.get(part)
            if path:
                out.append(path)
        return out


# --- VIDEO MONTAJ EARLY BOOTSTRAP ---
if "start_video_montaj_bg" not in globals():

    def _vm_bootstrap_ui_to_script_selection(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return "T"

        parts = [p.strip() for p in re.split(r'[\s,]+', raw) if p.strip()]
        if not parts:
            return "T"

        numeric_parts = [p for p in parts if re.fullmatch(r'\d+', p)]
        already_zero_based = any(p == "0" for p in numeric_parts)

        out = []
        for p in parts:
            up = p.upper()

            if up in {"T", "M", "C", "L", "V", "S", "O"}:
                out.append(up)
            elif re.fullmatch(r'G\d+(?:_\d+)?', up):
                out.append(up)
            elif re.fullmatch(r'\d+', p):
                n = int(p)
                if already_zero_based:
                    out.append(str(n))
                else:
                    out.append(str(max(0, n - 1)))
            else:
                out.append(p)

        return ",".join(out)


    def _vm_bootstrap_preset_oku() -> dict:
        preset_path = os.path.join(CONTROL_DIR, "video_montaj_preset.json")
        if not os.path.exists(preset_path):
            return {}
        try:
            with open(preset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}


    def _vm_bootstrap_write_config(payload: dict) -> str:
        os.makedirs(CONTROL_DIR, exist_ok=True)
        path = os.path.join(CONTROL_DIR, f"video_montaj_config_{int(time.time() * 1000)}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path


    def _vm_bootstrap_ensure_runner() -> str:
        runner_path = os.path.join(CONTROL_DIR, "video_montaj_runner.py")

        runner_lines = [
            "import builtins",
            "import json",
            "import os",
            "import re",
            "import sys",
            "import traceback",
            "",
            "def patch_assignment(text, pattern, replacement):",
            "    new_text, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.MULTILINE)",
            "    if count == 0:",
            "        print(f'[WARN] Değiştirilemedi: {pattern}')",
            "    return new_text",
            "",
            "def main():",
            "    if len(sys.argv) < 2:",
            "        raise RuntimeError('Video montaj yapılandırma dosyası verilmedi.')",
            "",
            "    config_path = sys.argv[1]",
            "    with open(config_path, 'r', encoding='utf-8') as f:",
            "        cfg = json.load(f)",
            "",
            "    script_path = cfg['script_path']",
            "    with open(script_path, 'r', encoding='utf-8', errors='replace') as f:",
            "        source = f.read()",
            "",
            '    source = patch_assignment(source, r\'^ana_klasor\\s*=.*$\', f"ana_klasor = {cfg[\'ana_klasor\']!r}")',
            '    source = patch_assignment(source, r\'^video_klasor\\s*=.*$\', f"video_klasor = {cfg[\'video_klasor\']!r}")',
            '    source = patch_assignment(source, r\'^klon_video_klasor\\s*=.*$\', f"klon_video_klasor = {cfg[\'klon_video_klasor\']!r}")',
            '    source = patch_assignment(source, r\'^montaj_klasor\\s*=.*$\', f"montaj_klasor = {cfg[\'montaj_klasor\']!r}")',
            '    source = patch_assignment(source, r\'^gorsel_klasor\\s*=.*$\', f"gorsel_klasor = {cfg[\'gorsel_klasor\']!r}")',
            "",
            "    # Orijinal ses ve video ses seviyesi dosyalarını yaz",
            "    ek_klasor = os.path.join(os.path.dirname(cfg['script_path']), 'ek')",
            "    os.makedirs(ek_klasor, exist_ok=True)",
            "    orijinal_ses_sev = cfg.get('orijinal_ses_seviyesi', '100')",
            "    video_ses_sev = cfg.get('video_ses_seviyesi', '100')",
            "    with open(os.path.join(ek_klasor, 'orijinal_ses_seviyesi.txt'), 'w', encoding='utf-8') as _f: _f.write(str(orijinal_ses_sev))",
            "    with open(os.path.join(ek_klasor, 'video_ses_seviyesi.txt'), 'w', encoding='utf-8') as _f: _f.write(str(video_ses_sev))",
            "    with open(os.path.join(ek_klasor, 'orijinal_ses_kaynaklari.json'), 'w', encoding='utf-8') as _f: json.dump(cfg.get('orijinal_ses_kaynaklari') or [], _f, ensure_ascii=False, indent=2)",
            "",
            "    answers = iter([",
            "        cfg.get('format_choice', 'D'),",
            "        cfg.get('selection_text', 'T'),",
            "        ''",
            "    ])",
            "",
            "    original_input = builtins.input",
            "",
            "    def fake_input(prompt=''):",
            "        if prompt:",
            "            print(prompt, end='')",
            "        try:",
            "            answer = next(answers)",
            "        except StopIteration:",
            "            answer = ''",
            "        print(answer)",
            "        return answer",
            "",
            "    builtins.input = fake_input",
            "    glb = {'__name__': '__main__', '__file__': script_path}",
            "",
            "    try:",
            "        exec(compile(source, script_path, 'exec'), glb, glb)",
            "    except SystemExit as e:",
            "        code = e.code if isinstance(e.code, int) else 0",
            "        raise SystemExit(code)",
            "    finally:",
            "        builtins.input = original_input",
            "",
            "if __name__ == '__main__':",
            "    try:",
            "        main()",
            "    except Exception as exc:",
            "        print(f'[ERROR] Video Montaj wrapper hatası: {exc}')",
            "        traceback.print_exc()",
            "        raise",
            "",
        ]

        runner_code = "\n".join(runner_lines)

        current = ""
        if os.path.exists(runner_path):
            with open(runner_path, "r", encoding="utf-8", errors="ignore") as f:
                current = f.read()

        if current != runner_code:
            with open(runner_path, "w", encoding="utf-8") as f:
                f.write(runner_code)

        return runner_path


    def start_video_montaj_bg(owner: str = "single") -> bool:
        s = st.session_state.settings
        script_path = (s.get("video_montaj_script") or "").strip()

        if not script_path or not os.path.exists(script_path):
            st.session_state.status["video_montaj"] = "error"
            log(f"[ERROR] Video Montaj script bulunamadı: {script_path}")
            return False

        preset = _vm_bootstrap_preset_oku() if owner == "batch" else {}

        raw_selection = ""
        raw_format = ""
        raw_source_mode = "Mevcut Videolar"
        raw_orijinal_ses_kaynak_sirasi = ""

        if owner == "batch":
            raw_selection = (preset.get("selection_text") or "").strip()
            raw_format = (preset.get("format_choice") or "").strip()
            raw_source_mode = preset.get("source_mode", st.session_state.get("video_montaj_source_mode", "Mevcut Videolar"))
            raw_orijinal_ses_kaynak_sirasi = preset.get("orijinal_ses_kaynak_sirasi", st.session_state.get("vm_orijinal_ses_kaynak_sirasi", ""))

            if not raw_selection:
                raw_selection = (st.session_state.get("video_montaj_selection_text") or "").strip()
            if not raw_format:
                raw_format = (st.session_state.get("video_montaj_format") or "D").strip()
        else:
            raw_selection = (st.session_state.get("video_montaj_selection_text") or "").strip()
            raw_format = (st.session_state.get("video_montaj_format") or "D").strip()
            raw_source_mode = st.session_state.get("video_montaj_source_mode", "Mevcut Videolar")
            raw_orijinal_ses_kaynak_sirasi = st.session_state.get("vm_orijinal_ses_kaynak_sirasi", "")

        source_mode = _normalize_toplu_video_source_mode(raw_source_mode)
        # Batch modunda Eklenen Video seçiliyse Mevcut Videolar'a dön
        format_choice = (raw_format or "D").strip().upper()
        format_choice = "D" if format_choice.startswith("D") else "Y"

        # Kaynak moduna göre video klasörü belirle
        if source_mode == "Eklenen Video":
            video_klasor = s.get("added_video_dir", "")
            klon_video_klasor = ""
            source_video_items = _list_toplu_video_added_source_items()
            selection_text = _vm_bootstrap_ui_to_script_selection(raw_selection or "T")
        elif source_mode == "Görsel Oluştur":
            video_klasor = s.get("video_output_dir", "")
            klon_video_klasor = ""
            source_video_items = _list_video_montaj_assets().get("gorsel_olustur_videos", [])
            temp_video_klasor, temp_klon_video_klasor, token_remap = _prepare_mevcut_video_runner_dirs(
                source_video_items,
                temp_prefix="video_montaj_gorsel_olustur",
                force_copy=True,
            )
            if temp_video_klasor:
                video_klasor = temp_video_klasor
                klon_video_klasor = temp_klon_video_klasor
            remapped_selection_text = _remap_numeric_selection_text(raw_selection or "T", token_remap)
            selection_text = _vm_bootstrap_ui_to_script_selection(remapped_selection_text or "T")
        else:
            video_klasor = s.get("video_output_dir", "")
            klon_video_klasor = s.get("klon_video_dir", "")
            source_video_items = _list_video_montaj_assets().get("videos", [])
            temp_video_klasor, temp_klon_video_klasor, token_remap = _prepare_mevcut_video_runner_dirs(
                source_video_items,
                temp_prefix="video_montaj",
                force_copy=True,
            )
            if temp_video_klasor:
                video_klasor = temp_video_klasor
                klon_video_klasor = temp_klon_video_klasor
            remapped_selection_text = _remap_numeric_selection_text(raw_selection or "T", token_remap)
            selection_text = _vm_bootstrap_ui_to_script_selection(remapped_selection_text or "T")

        orijinal_ses_kaynaklari = _orijinal_ses_kaynak_sirasi_to_paths(raw_orijinal_ses_kaynak_sirasi, source_video_items)

        # Orijinal ses ve video ses seviyelerini al
        if owner == "batch":
            orijinal_ses_sev = preset.get("orijinal_ses_seviyesi", st.session_state.get("vm_orijinal_ses_seviyesi", "100"))
            video_ses_sev = preset.get("video_ses_seviyesi", st.session_state.get("vm_video_ses_seviyesi", "100"))
        else:
            orijinal_ses_sev = st.session_state.get("vm_orijinal_ses_seviyesi", "100")
            video_ses_sev = st.session_state.get("vm_video_ses_seviyesi", "100")

        config_payload = {
            "script_path": script_path,
            "ana_klasor": os.path.dirname(script_path),
            "video_klasor": video_klasor,
            "klon_video_klasor": klon_video_klasor,
            "montaj_klasor": s.get("video_montaj_output_dir", ""),
            "gorsel_klasor": s.get("video_montaj_gorsel_dir", ""),
            "format_choice": format_choice,
            "selection_text": selection_text,
            "orijinal_ses_seviyesi": str(orijinal_ses_sev).strip() or "100",
            "video_ses_seviyesi": str(video_ses_sev).strip() or "100",
            "orijinal_ses_kaynaklari": orijinal_ses_kaynaklari,
        }

        runner_path = _vm_bootstrap_ensure_runner()
        config_path = _vm_bootstrap_write_config(config_payload)
        return bg_start(owner, "video_montaj", runner_path, args=[config_path])


# --- TOPLU VIDEO EARLY BOOTSTRAP ---
if "start_toplu_video_bg" not in globals():

    def _tv_bootstrap_normalize_selection(text: str) -> str:
        raw = (text or "").strip().upper()
        if not raw:
            return "T"
        parts = [p.strip() for p in re.split(r'[\s,;]+', raw) if p.strip()]
        if not parts:
            return "T"
        out = []
        for p in parts:
            if p in {"T", "M", "C", "L", "V", "S", "O"} or re.fullmatch(r'\d+', p):
                out.append(p)
        return ",".join(out) if out else "T"


    def _tv_bootstrap_source_text_to_indices(text: str) -> list:
        raw = (text or "").strip().upper()
        if not raw or raw == "T":
            return []
        parts = [p.strip() for p in re.split(r'[\s,;]+', raw) if p.strip()]
        numeric_parts = [p for p in parts if re.fullmatch(r'\d+', p)]
        already_zero_based = any(p == "0" for p in numeric_parts)
        out = []
        for p in numeric_parts:
            n = int(p)
            idx = n if already_zero_based else max(0, n - 1)
            if idx not in out:
                out.append(idx)
        return out


    def _tv_bootstrap_get_materyal_paths(settings_obj: dict) -> dict:
        materyal_dir = ((settings_obj or {}).get("toplu_video_materyal_dir") or DEFAULT_SETTINGS.get("toplu_video_materyal_dir") or "").strip()
        return {
            "ana": materyal_dir,
            "muzik_ses": os.path.join(materyal_dir, "muzik", "ses_seviyesi.txt"),
            "ses_efekti_ses": os.path.join(materyal_dir, "ses efekti", "ses_seviyesi.txt"),
            "baslik": os.path.join(materyal_dir, "başlık.txt"),
            "orijinal_ses_kaynaklari": os.path.join(materyal_dir, "orijinal_ses_kaynaklari.json"),
        }


    def _tv_bootstrap_read_text_file(path: str, default: str = "") -> str:
        try:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read().strip()
        except Exception:
            pass
        return default


    def _tv_bootstrap_normalize_percent_text(value: str, default_percent: int = 15) -> str:
        raw = str(value or "").strip().replace("%", "")
        if not raw:
            return str(default_percent)
        try:
            num = float(raw.replace(",", "."))
            if num <= 1:
                num = num * 100
            num = max(0, min(100, int(round(num))))
            return str(num)
        except Exception:
            return str(default_percent)


    def _tv_bootstrap_preset_oku() -> dict:
        preset_path = os.path.join(CONTROL_DIR, "toplu_video_preset.json")
        if not os.path.exists(preset_path):
            return {}
        try:
            with open(preset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}


    def _tv_bootstrap_write_config(payload: dict) -> str:
        os.makedirs(CONTROL_DIR, exist_ok=True)
        path = os.path.join(CONTROL_DIR, f"toplu_video_config_{int(time.time() * 1000)}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def _tv_bootstrap_ensure_runner() -> str:
        runner_path = os.path.join(CONTROL_DIR, "toplu_video_runner.py")
        runner_code = textwrap.dedent('\nimport builtins\nimport json\nimport os\nimport re\nimport sys\nimport traceback\n\n\ndef patch_assignment(text, pattern, replacement):\n    new_text, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.MULTILINE)\n    if count == 0:\n        print(f"[WARN] Değiştirilemedi: {pattern}")\n    return new_text\n\n\ndef write_text_file(path, value):\n    os.makedirs(os.path.dirname(path), exist_ok=True)\n    with open(path, "w", encoding="utf-8") as f:\n        f.write(str(value or "").strip())\n\n\ndef main():\n    if len(sys.argv) < 2:\n        raise RuntimeError("Toplu video yapılandırma dosyası verilmedi.")\n\n    config_path = sys.argv[1]\n    with open(config_path, "r", encoding="utf-8") as f:\n        cfg = json.load(f)\n\n    script_path = cfg["script_path"]\n    with open(script_path, "r", encoding="utf-8", errors="replace") as f:\n        source = f.read()\n\n    source = patch_assignment(source, r"^ana_klasor\\s*=.*$", f"ana_klasor = {cfg[\'ana_klasor\']!r}")\n    source = patch_assignment(source, r"^video_kaynak_ana_yol\\s*=.*$", f"video_kaynak_ana_yol = {cfg[\'video_kaynak_ana_yol\']!r}")\n    source = patch_assignment(source, r"^klon_video_kaynak_ana_yol\\s*=.*$", f"klon_video_kaynak_ana_yol = {cfg[\'klon_video_kaynak_ana_yol\']!r}")\n    source = patch_assignment(source, r"^toplu_montaj_klasor\\s*=.*$", f"toplu_montaj_klasor = {cfg[\'toplu_montaj_klasor\']!r}")\n    source = patch_assignment(source, r"^materyal_ana_yol\\s*=.*$", f"materyal_ana_yol = {cfg[\'materyal_ana_yol\']!r}")\n\n    materyal_ana_yol = cfg["materyal_ana_yol"]\n    write_text_file(os.path.join(materyal_ana_yol, "muzik", "ses_seviyesi.txt"), cfg.get("muzik_seviyesi", "15"))\n    write_text_file(os.path.join(materyal_ana_yol, "ses efekti", "ses_seviyesi.txt"), cfg.get("ses_efekti_seviyesi", "15"))\n    write_text_file(os.path.join(materyal_ana_yol, "başlık.txt"), cfg.get("baslik", ""))\n    write_text_file(os.path.join(materyal_ana_yol, "orijinal_ses_seviyesi.txt"), cfg.get("orijinal_ses_seviyesi", "100"))\n    write_text_file(os.path.join(materyal_ana_yol, "video_ses_seviyesi.txt"), cfg.get("video_ses_seviyesi", "100"))\n    with open(os.path.join(materyal_ana_yol, "orijinal_ses_kaynaklari.json"), "w", encoding="utf-8") as f:\n        json.dump(cfg.get("orijinal_ses_kaynaklari") or [], f, ensure_ascii=False, indent=2)\n\n    if "def ses_efekti_seviyesi_oku():" not in source:\n        marker = "def muzik_ekle(video_clip):"\n        helper = (\n            "def ses_efekti_seviyesi_oku():\\n"\n            "    \\"ses efekti/ses_seviyesi.txt dosyasından ses seviyesini oku\\"\\n"\n            "    ses_dosyasi = os.path.join(ses_efekti_klasor, \'ses_seviyesi.txt\')\\n"\n            "    try:\\n"\n            "        if os.path.exists(ses_dosyasi):\\n"\n            "            with open(ses_dosyasi, \'r\', encoding=\'utf-8\') as f:\\n"\n            "                icerik = f.read().strip()\\n"\n            "                icerik = icerik.replace(\'%\', \'\').strip()\\n"\n            "                seviye = int(icerik)\\n"\n            "                seviye = max(0, min(100, seviye))\\n"\n            "                return seviye / 100.0\\n"\n            "    except Exception:\\n"\n            "        pass\\n"\n            "    return 0.15\\n\\n"\n        )\n        if marker in source:\n            source = source.replace(marker, helper + marker, 1)\n\n    source = source.replace("    ses_seviyesi = ses_seviyesi_oku()\\n", "    ses_seviyesi = ses_efekti_seviyesi_oku()\\n", 1)\n\n    selected_source_indices = []\n    for value in (cfg.get("selected_source_indices") or []):\n        try:\n            idx = int(value)\n        except Exception:\n            continue\n        if idx not in selected_source_indices:\n            selected_source_indices.append(idx)\n\n    if selected_source_indices:\n        marker = "mp4_dosyalar = list(dict.fromkeys(mp4_dosyalar))"\n        injection = (\n            "mp4_dosyalar = list(dict.fromkeys(mp4_dosyalar))\\n"\n            + "    selected_source_indices = " + repr(selected_source_indices) + "\\n"\n            + "    if selected_source_indices:\\n"\n            + "        filtered_videos = []\\n"\n            + "        for _idx, _path in enumerate(mp4_dosyalar):\\n"\n            + "            if _idx in selected_source_indices:\\n"\n            + "                filtered_videos.append(_path)\\n"\n            + "        mp4_dosyalar = filtered_videos\\n"\n            + "        print(\'\\n[INFO] App seçimine göre kaynak videolar filtrelendi.\')\\n"\n            + "        print(\'[INFO] Seçilen indeksler: \' + \',\'.join(str(x) for x in selected_source_indices))\\n"\n        )\n        if marker in source:\n            source = source.replace(marker, injection, 1)\n\n    answers = iter([\n        cfg.get("format_choice", "D"),\n        cfg.get("selection_text", "T"),\n        "",\n    ])\n\n    original_input = builtins.input\n\n    def fake_input(prompt=""):\n        if prompt:\n            print(prompt, end="")\n        try:\n            answer = next(answers)\n        except StopIteration:\n            answer = ""\n        print(answer)\n        return answer\n\n    builtins.input = fake_input\n    glb = {"__name__": "__main__", "__file__": script_path}\n\n    try:\n        exec(compile(source, script_path, "exec"), glb, glb)\n    except SystemExit as e:\n        code = e.code if isinstance(e.code, int) else 0\n        raise SystemExit(code)\n    finally:\n        builtins.input = original_input\n\n\nif __name__ == "__main__":\n    try:\n        main()\n    except Exception as exc:\n        print(f"[ERROR] Toplu Video wrapper hatası: {exc}")\n        traceback.print_exc()\n        raise\n')
        current = ""
        if os.path.exists(runner_path):
            with open(runner_path, "r", encoding="utf-8", errors="ignore") as f:
                current = f.read()
        if current != runner_code:
            with open(runner_path, "w", encoding="utf-8") as f:
                f.write(runner_code)
        return runner_path

    def start_toplu_video_bg(owner: str = "single") -> bool:
        s = st.session_state.settings
        script_path = (s.get("toplu_video_script") or "").strip()

        if not script_path or not os.path.exists(script_path):
            st.session_state.status["toplu_video"] = "error"
            log(f"[ERROR] Toplu Video script bulunamadı: {script_path}")
            return False

        preset = _tv_bootstrap_preset_oku() if owner == "batch" else {}
        materyal_paths = _tv_bootstrap_get_materyal_paths(st.session_state.settings)

        if owner == "batch":
            raw_selection = (preset.get("selection_text") or st.session_state.get("toplu_video_selection_text") or "T").strip()
            raw_format = (preset.get("format_choice") or st.session_state.get("toplu_video_format") or "D").strip()
            raw_source_selection = (preset.get("source_selection_text") or st.session_state.get("toplu_video_source_selection_text") or "T").strip()
            raw_source_mode = preset.get("source_mode", st.session_state.get("toplu_video_source_mode", "Mevcut Videolar"))
            raw_muzik_seviyesi = preset.get("muzik_seviyesi", st.session_state.get("tv_muzik_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["muzik_ses"], "15")))
            raw_ses_efekti_seviyesi = preset.get("ses_efekti_seviyesi", st.session_state.get("tv_ses_efekti_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["ses_efekti_ses"], "15")))
            raw_orijinal_ses_seviyesi = preset.get("orijinal_ses_seviyesi", st.session_state.get("tv_orijinal_ses_seviyesi", "100"))
            raw_video_ses_seviyesi = preset.get("video_ses_seviyesi", st.session_state.get("tv_video_ses_seviyesi", "100"))
            raw_orijinal_ses_kaynak_sirasi = preset.get("orijinal_ses_kaynak_sirasi", st.session_state.get("tv_orijinal_ses_kaynak_sirasi", ""))
            raw_baslik = preset.get("baslik", st.session_state.get("tv_baslik", _tv_bootstrap_read_text_file(materyal_paths["baslik"], "")))
        else:
            raw_selection = (st.session_state.get("toplu_video_selection_text") or "T").strip()
            raw_format = (st.session_state.get("toplu_video_format") or "D").strip()
            raw_source_selection = (st.session_state.get("toplu_video_source_selection_text") or "T").strip()
            raw_source_mode = st.session_state.get("toplu_video_source_mode", "Mevcut Videolar")
            raw_muzik_seviyesi = st.session_state.get("tv_muzik_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["muzik_ses"], "15"))
            raw_ses_efekti_seviyesi = st.session_state.get("tv_ses_efekti_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["ses_efekti_ses"], "15"))
            raw_orijinal_ses_seviyesi = st.session_state.get("tv_orijinal_ses_seviyesi", "100")
            raw_video_ses_seviyesi = st.session_state.get("tv_video_ses_seviyesi", "100")
            raw_orijinal_ses_kaynak_sirasi = st.session_state.get("tv_orijinal_ses_kaynak_sirasi", "")
            raw_baslik = st.session_state.get("tv_baslik", _tv_bootstrap_read_text_file(materyal_paths["baslik"], ""))

        source_mode = _normalize_toplu_video_source_mode(raw_source_mode)
        selection_text = _tv_bootstrap_normalize_selection(raw_selection or "T")
        format_choice = (raw_format or "D").strip().upper()
        format_choice = "D" if format_choice.startswith("D") else "Y"
        if source_mode == "Eklenen Video":
            source_video_items = _list_toplu_video_added_source_items()
            remapped_source_selection = (raw_source_selection or "T").strip().upper() or "T"
        elif source_mode == "Görsel Oluştur":
            source_video_items = _list_video_montaj_assets().get("gorsel_olustur_videos", [])
            temp_video_kaynak_ana_yol, temp_klon_video_kaynak_ana_yol, token_remap = _prepare_mevcut_video_runner_dirs(
                source_video_items,
                temp_prefix="toplu_video_gorsel_olustur",
                force_copy=True,
            )
            remapped_source_selection = _remap_numeric_selection_text((raw_source_selection or "T").strip().upper() or "T", token_remap)
        else:
            source_video_items = _list_video_montaj_assets().get("videos", [])
            temp_video_kaynak_ana_yol, temp_klon_video_kaynak_ana_yol, token_remap = _prepare_mevcut_video_runner_dirs(
                source_video_items,
                temp_prefix="toplu_video",
                force_copy=True,
            )
            remapped_source_selection = _remap_numeric_selection_text((raw_source_selection or "T").strip().upper() or "T", token_remap)
        selected_source_indices = _tv_bootstrap_source_text_to_indices(remapped_source_selection or "T")
        orijinal_ses_kaynaklari = _orijinal_ses_kaynak_sirasi_to_paths(raw_orijinal_ses_kaynak_sirasi, source_video_items)
        muzik_seviyesi = _tv_bootstrap_normalize_percent_text(raw_muzik_seviyesi, 15)
        ses_efekti_seviyesi = _tv_bootstrap_normalize_percent_text(raw_ses_efekti_seviyesi, 15)
        orijinal_ses_seviyesi = _tv_bootstrap_normalize_percent_text(raw_orijinal_ses_seviyesi, 100)
        video_ses_seviyesi_val = _tv_bootstrap_normalize_percent_text(raw_video_ses_seviyesi, 100)
        baslik = (raw_baslik or "").strip()

        if source_mode == "Eklenen Video":
            video_kaynak_ana_yol = s.get("added_video_dir", "")
            klon_video_kaynak_ana_yol = ""
        elif source_mode == "Görsel Oluştur":
            video_kaynak_ana_yol = temp_video_kaynak_ana_yol or s.get("video_output_dir", "")
            klon_video_kaynak_ana_yol = ""
        else:
            video_kaynak_ana_yol = temp_video_kaynak_ana_yol or s.get("video_output_dir", "")
            klon_video_kaynak_ana_yol = temp_klon_video_kaynak_ana_yol or s.get("klon_video_dir", "")

        config_payload = {
            "script_path": script_path,
            "ana_klasor": os.path.dirname(script_path),
            "video_kaynak_ana_yol": video_kaynak_ana_yol,
            "klon_video_kaynak_ana_yol": klon_video_kaynak_ana_yol,
            "toplu_montaj_klasor": s.get("toplu_video_output_dir", ""),
            "materyal_ana_yol": s.get("toplu_video_materyal_dir", ""),
            "format_choice": format_choice,
            "selection_text": selection_text,
            "source_mode": source_mode,
            "source_selection_text": (raw_source_selection or "T").strip().upper() or "T",
            "selected_source_indices": selected_source_indices,
            "muzik_seviyesi": muzik_seviyesi,
            "ses_efekti_seviyesi": ses_efekti_seviyesi,
            "orijinal_ses_seviyesi": orijinal_ses_seviyesi,
            "video_ses_seviyesi": video_ses_seviyesi_val,
            "orijinal_ses_kaynaklari": orijinal_ses_kaynaklari,
            "baslik": baslik,
        }

        runner_path = _tv_bootstrap_ensure_runner()
        config_path = _tv_bootstrap_write_config(config_payload)
        return bg_start(owner, "toplu_video", runner_path, args=[config_path])

# --- PIXVERSE EARLY BOOTSTRAP ---
if "start_pixverse_bg" not in globals():

    def _video_prompt_selection_state_path() -> str:
        return os.path.join(CONTROL_DIR, "video_prompt_selection.json")

    def _list_video_prompt_entries(prompt_dir: str | None = None) -> list:
        root = (prompt_dir or st.session_state.settings.get("prompt_dir", "") or "").strip()
        if not root or not os.path.isdir(root):
            return []
        out = []
        try:
            for folder_name in os.listdir(root):
                folder_path = os.path.join(root, folder_name)
                prompt_path = os.path.join(folder_path, "prompt.txt")
                if not (os.path.isdir(folder_path) and os.path.exists(prompt_path)):
                    continue
                prompt_text = ""
                try:
                    with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
                        prompt_text = f.read().strip()
                except Exception:
                    prompt_text = ""
                out.append({
                    "folder_name": folder_name,
                    "folder_path": folder_path,
                    "prompt_path": prompt_path,
                    "prompt_preview": (prompt_text[:140] + "\u2026") if len(prompt_text) > 140 else prompt_text,
                })
        except Exception:
            return []
        def _bootstrap_natural_sort_key(s): return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
        out.sort(key=lambda item: _bootstrap_natural_sort_key(item.get("folder_name", "")))
        return out

    def _video_prompt_selection_load(available_prompt_names: list | None = None) -> dict:
        state = {"mode": "all", "selected_prompt_folders": []}
        state_path = _video_prompt_selection_state_path()
        try:
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    mode = str(data.get("mode") or "all").strip().lower()
                    selected = data.get("selected_prompt_folders") or []
                    if mode in {"all", "custom"}:
                        state["mode"] = mode
                    if isinstance(selected, list):
                        temiz = []
                        for item in selected:
                            name = str(item or "").strip()
                            if name and name not in temiz:
                                temiz.append(name)
                        state["selected_prompt_folders"] = temiz
        except Exception:
            pass
        if isinstance(available_prompt_names, list):
            mevcut = [str(name or "").strip() for name in available_prompt_names if str(name or "").strip()]
            if not mevcut:
                return {"mode": "all", "selected_prompt_folders": []}
            secili = [name for name in state.get("selected_prompt_folders", []) if name in mevcut]
            if state.get("mode") != "custom" or not secili or len(secili) >= len(mevcut):
                return {"mode": "all", "selected_prompt_folders": []}
            return {"mode": "custom", "selected_prompt_folders": secili}
        return state

    def _prepare_pixverse_prompt_override_if_needed() -> bool:
        if st.session_state.get("pixverse_prompt_override_meta"):
            return True
        current_settings = dict(st.session_state.get("settings", {}) or {})
        original_prompt_dir = (current_settings.get("prompt_dir") or "").strip()
        prompt_entries = _list_video_prompt_entries(original_prompt_dir)
        available_names = [item.get("folder_name", "") for item in prompt_entries]
        secim = _video_prompt_selection_load(available_names)
        selected_names = secim.get("selected_prompt_folders", [])
        if secim.get("mode") != "custom" or not selected_names:
            return True
        selected_entries = [item for item in prompt_entries if item.get("folder_name") in selected_names]
        if not selected_entries:
            return True

        temp_root = os.path.join(CONTROL_DIR, f"pixverse_prompt_override_{int(time.time() * 1000)}")
        stash_dir = os.path.join(temp_root, "stash")
        moved_folders = []
        selected_set = {item.get("folder_name", "") for item in selected_entries}

        try:
            os.makedirs(stash_dir, exist_ok=True)
            for item in prompt_entries:
                folder_name = item.get("folder_name", "")
                if folder_name in selected_set:
                    continue
                src = item.get("folder_path", "")
                dst = os.path.join(stash_dir, folder_name)
                if not src or not os.path.isdir(src):
                    continue
                shutil.move(src, dst)
                moved_folders.append(folder_name)

            st.session_state.pixverse_prompt_override_meta = {
                "original_prompt_dir": original_prompt_dir,
                "temp_root": temp_root,
                "stash_dir": stash_dir,
                "moved_folders": moved_folders,
                "selected_prompt_folders": [item.get("folder_name", "") for item in selected_entries],
            }
            log(f"[INFO] Video üretimi için seçili promptlar hazırlandı: {', '.join(item.get('folder_name', '') for item in selected_entries)}")
            return True
        except Exception as e:
            st.session_state.pixverse_prompt_override_meta = {
                "original_prompt_dir": original_prompt_dir,
                "temp_root": temp_root,
                "stash_dir": stash_dir,
                "moved_folders": moved_folders,
            }
            _cleanup_pixverse_prompt_override()
            log(f"[ERROR] Seçili promptlar hazırlanamadı: {e}")
            return False

    def start_pixverse_bg(owner: str) -> bool:
        overridden = False
        extra_args = []
        if _should_use_gorsel_motion_prompts():
            overridden = True
            extra_args = ["--prompt-dir", GORSEL_HAREKET_PROMPT_DIR, "--ref-image-dir", GORSEL_HAREKET_REFERANS_DIR]
            st.session_state.pixverse_prompt_override_meta = {
                "is_gorsel_override": True,
                "original_settings_prompt_dir": st.session_state.settings.get("prompt_dir", ""),
                "original_settings_ref_dir": st.session_state.settings.get("gorsel_klonlama_dir", "")
            }
            # settings.local.json'a dogrudan yaz (script modul-level okumasi icin)
            try:
                _s = dict(st.session_state.settings)
                _s["prompt_dir"] = GORSEL_HAREKET_PROMPT_DIR
                _s["gorsel_klonlama_dir"] = GORSEL_HAREKET_REFERANS_DIR
                import json as _json
                with open(SETTINGS_PATH, "r", encoding="utf-8") as _rf:
                    _current = _json.load(_rf)
                _current["prompt_dir"] = GORSEL_HAREKET_PROMPT_DIR
                _current["gorsel_klonlama_dir"] = GORSEL_HAREKET_REFERANS_DIR
                with open(SETTINGS_PATH, "w", encoding="utf-8") as _wf:
                    _json.dump(_current, _wf, ensure_ascii=False, indent=2)
                log(f"[INFO] Görsel hareketlendirme promptları aktif. PROMPT_ROOT override: {GORSEL_HAREKET_PROMPT_DIR}")
            except Exception as _e:
                log(f"[WARN] settings.json prompt_dir yazilamadi: {_e}")

        if not overridden:
            if not _prepare_pixverse_prompt_override_if_needed():
                st.session_state.status["pixverse"] = "error"
                return False

        ok = bg_start(owner, "pixverse", get_active_video_script(st.session_state.settings), args=extra_args)
        if not ok:
            _cleanup_pixverse_prompt_override()
        return ok

# ==========================================
# AKIŞ MOTORLARI — UI bloğu dışında çalışır
# ==========================================
def _get_batch_scripts():
    s = st.session_state.settings
    return {
        "download":         s.get("video_indir_script", ""),
        "gorsel_analiz":    s.get("analiz_script", ""),
        "gorsel_klonlama":  s.get("gorsel_klonlama_script", ""),
        "gorsel_olustur":   s.get("gorsel_olustur_motor", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluştur\gorsel_olustur_motoru.py"),
        "analyze":          s.get("prompt_script", ""),
        "pixverse":         get_active_video_script(s),
        "prompt_duzeltme":  s.get("prompt_duzeltme_script", ""),
        "sosyal_medya":     s.get("sosyal_medya_script", ""),
    }
BATCH_SCRIPTS = _get_batch_scripts()


# ==========================================
# PROMPT OLUŞTUR — ERKEN YARDIMCILAR
# (Tekli/batch akış motoru bu fonksiyonu tanımlanmadan çağırdığı için
# burada erken tanımlanır. Aşağıda daha geniş yardımcı blok yeniden
# tanımlansa da bu sürüm NameError oluşmasını engeller.)
# ==========================================
def _early_normalize_prompt_source_mode(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"link", "youtube", "manual"}:
        return "link"
    if raw in {"added_video", "video", "eklenen_video", "eklenen video"}:
        return "added_video"
    if raw in {"downloaded_video", "download", "indirilen_video", "indirilen video"}:
        return "downloaded_video"
    return "auto"


def _early_write_prompt_source_mode(mode: str):
    try:
        prompt_source_mode_file = os.path.join(CONTROL_DIR, "prompt_source_mode.txt")
        os.makedirs(os.path.dirname(prompt_source_mode_file), exist_ok=True)
        with open(prompt_source_mode_file, "w", encoding="utf-8") as f:
            f.write(_early_normalize_prompt_source_mode(mode))
    except Exception:
        pass


def _early_count_prompt_links() -> int:
    settings_obj = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    candidate_paths = [
        str(settings_obj.get("video_prompt_links_file") or "").strip(),
        str(settings_obj.get("links_file") or "").strip(),
    ]
    for link_path in candidate_paths:
        if not link_path or not os.path.exists(link_path):
            continue
        try:
            with open(link_path, "r", encoding="utf-8", errors="ignore") as f:
                return len([ln for ln in f.read().splitlines() if str(ln).strip()])
        except Exception:
            continue
    return 0


def _early_count_videos_in_root(root_path: str) -> int:
    root = str(root_path or "").strip()
    if not root or not os.path.isdir(root):
        return 0

    supported_exts = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")
    count = 0
    try:
        klasorler = [k for k in os.listdir(root) if os.path.isdir(os.path.join(root, k))]
    except Exception:
        return 0

    def _sort_key(value: str):
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(value or ''))]

    klasorler.sort(key=_sort_key)
    for klasor_adi in klasorler:
        klasor_yolu = os.path.join(root, klasor_adi)
        try:
            videolar = [
                f for f in os.listdir(klasor_yolu)
                if os.path.isfile(os.path.join(klasor_yolu, f)) and str(f).lower().endswith(supported_exts)
            ]
        except Exception:
            videolar = []
        if videolar:
            count += 1
    return count


def _early_get_effective_prompt_source_mode() -> str:
    canvas_source = st.session_state.get("link_canvas_source", "none")
    if canvas_source == "added_video":
        return "added_video"
    if canvas_source in ("youtube", "manual"):
        return "link"

    prompt_source_mode_file = os.path.join(CONTROL_DIR, "prompt_source_mode.txt")
    try:
        if os.path.exists(prompt_source_mode_file):
            with open(prompt_source_mode_file, "r", encoding="utf-8") as f:
                file_mode = _early_normalize_prompt_source_mode(f.read().strip())
            if file_mode != "auto":
                return file_mode
    except Exception:
        pass

    settings_obj = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    link_count = _early_count_prompt_links()
    added_count = _early_count_videos_in_root(settings_obj.get("added_video_dir", ""))

    if link_count and not added_count:
        return "link"
    if added_count and not link_count:
        return "added_video"
    if link_count:
        return "link"
    if added_count:
        return "added_video"
    return "auto"


def _early_get_prompt_runtime_source_mode() -> str:
    mode = _early_get_effective_prompt_source_mode()
    if mode == "added_video":
        return "added_video"

    settings_obj = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    download_count = _early_count_videos_in_root(settings_obj.get("download_dir", ""))
    link_count = _early_count_prompt_links()

    if download_count > 0:
        return "downloaded_video"
    if link_count > 0:
        return "link"
    return mode


def _prepare_prompt_source_for_analyze(owner: str | None = None) -> str:
    runtime_mode = _early_get_prompt_runtime_source_mode()
    _early_write_prompt_source_mode(runtime_mode)

    owner_label = "Tekli işlem" if owner == "single" else ("Tümünü Çalıştır" if owner == "batch" else "İşlem")
    if runtime_mode == "added_video":
        log(f"[INFO] {owner_label}: Prompt Oluştur kaynağı → Eklenen Video")
    elif runtime_mode == "downloaded_video":
        log(f"[INFO] {owner_label}: Prompt Oluştur kaynağı → İndirilen Video")
    elif runtime_mode == "link":
        log(f"[INFO] {owner_label}: İndirilen video bulunamadı → Prompt Oluştur linkten devam edecek")
    else:
        log(f"[INFO] {owner_label}: Prompt Oluştur için uygun kaynak bulunamadı")

    return runtime_mode


def start_analyze_bg(owner: str) -> bool:
    _prepare_prompt_source_for_analyze(owner)
    return bg_start(owner, "analyze", st.session_state.settings["prompt_script"])

if st.session_state.get("batch_mode", False):
    queue   = st.session_state.get("batch_queue", [])
    q_idx   = st.session_state.get("batch_queue_idx", 0)

    # Bitir isteği: tüm çalışanları idle'a çek
    if st.session_state.get("batch_finish_requested", False) and not bg_is_running():
        for k in queue:
            if st.session_state.status.get(k) == "running": st.session_state.status[k] = "idle"
        st.session_state.batch_mode = False; st.session_state.batch_queue_idx = 0
        st.session_state.batch_finish_requested = False; st.session_state.batch_paused = False
        st.session_state.controls_unlocked = False; cleanup_flags(); st.rerun()

    # Tamamlanan adımı işle
    res = st.session_state.get("bg_last_result")
    if res and res.get("owner") == "batch":
        node, success = res.get("node_key"), bool(res.get("success"))
        node_status = res.get("status", "ok")
        st.session_state.bg_last_result = None

        # Rollback tablosu — bağımlılığa göre nereden tekrar başlanmalı
        _pd_in_q = "prompt_duzeltme" in queue
        ROLLBACK_START = {
            "download":        "download",
            "gorsel_analiz":   "gorsel_analiz",
            "gorsel_klonlama": "gorsel_analiz",
            "analyze":         "analyze",
            "prompt_duzeltme": "analyze",
            # pixverse partial → pixverse'den tekrar dene (script zaten tamamlananları atlar)
            # pixverse error → prompt_duzeltme varsa oraya, yoksa analyze'e
            "pixverse":        "pixverse",   # partial için; error için aşağıda override edilir
            "video_montaj":    "video_montaj",
            "toplu_video":     "toplu_video",
        }

        def _save_resume(node_key, rollback_node):
            try:
                rollback_idx = queue.index(rollback_node)
            except ValueError:
                try:
                    rollback_idx = queue.index(node_key)
                except ValueError:
                    rollback_idx = q_idx
            st.session_state.batch_resume_queue = list(queue)
            st.session_state.batch_resume_idx = rollback_idx

        def _stop_batch_with_resume(rollback_node):
            _save_resume(node, rollback_node)
            st.session_state.batch_mode = False; st.session_state.batch_queue_idx = 0; cleanup_flags()
            st.session_state.durum_ozeti_suppress = False  # Batch bitti → özeti göster
            if st.session_state.get("batch_finish_requested", False): st.session_state.batch_finish_requested = False
            ozet = st.session_state.durum_ozeti
            if len(ozet.get("hatali",[])) + len(ozet.get("basarili",[])) + len(ozet.get("kismi",[])) > 0:
                st.session_state.last_dialog_align = "center"
                st.session_state.durum_ozeti_dialog_open = True

        if success:
            st.session_state.status[node] = node_status

            # pixverse kısmi tamamlandı → batch DURDUR, video_montaj'a geçme
            # Kullanıcı düzeltme yapıp Devam Et'e basacak; pixverse skript zaten olanları atlar
            if node == "pixverse" and node_status == "partial":
                cur_logs_partial = list(st.session_state.logs)
                px_err_partial = _detect_pixverse_error_type(cur_logs_partial)
                if px_err_partial == "prompt":
                    # Prompt çok uzun → Prompt Düzelt'e geri dön
                    _partial_rollback = "prompt_duzeltme"
                    st.session_state.batch_resume_reason = "⚠️ Prompt çok uzun (kısmi hata) — Prompt Düzelt'ten başlanacak."
                    log("[INFO] Kısmi hata: Prompt uzunluk sorunu tespit edildi → Prompt Düzelt'ten başlanacak.")
                    if _partial_rollback not in queue:
                        pv_pos = queue.index("pixverse") if "pixverse" in queue else len(queue)
                        queue.insert(pv_pos, "prompt_duzeltme")
                        st.session_state.batch_queue = list(queue)
                elif px_err_partial == "credit":
                    _partial_rollback = "pixverse"
                    st.session_state.batch_resume_reason = f"⚠️ Kredi yetersiz (kısmi hata) — {get_video_generation_label(emoji=False)} adımından tekrar denenecek."
                    log(f"[INFO] Kısmi hata: Kredi yetersiz → {get_video_generation_label(emoji=False)} adımından tekrar başlanacak.")
                else:
                    _partial_rollback = "pixverse"
                    st.session_state.batch_resume_reason = f"⚠️ Bazı videolar üretilemedi — {get_video_generation_label(emoji=False)} adımından tekrar denenecek."
                    log(f"[INFO] Kısmi hata: Bazı videolar üretilemedi → {get_video_generation_label(emoji=False)} adımından tekrar başlanacak.")
                _set_batch_pixverse_retry_targets(cur_logs_partial)
                _stop_batch_with_resume(_partial_rollback)
                st.rerun()

            # Diğer kısmi adımlar için resume kaydet ama devam et
            if node_status == "partial":
                _save_resume(node, ROLLBACK_START.get(node, node))

            st.session_state.batch_queue_idx = q_idx + 1
            # Kuyruk bitti mi?
            if st.session_state.batch_queue_idx >= len(queue):
                st.session_state.batch_mode = False; st.session_state.batch_queue_idx = 0; cleanup_flags()
                st.session_state.durum_ozeti_suppress = False  # Batch bitti → özeti göster
                ozet = st.session_state.durum_ozeti
                has_issues = len(ozet.get("hatali",[])) + len(ozet.get("kismi",[])) > 0
                if not has_issues:
                    st.session_state.batch_resume_queue = []; st.session_state.batch_resume_idx = 0
                if len(ozet.get("hatali",[])) + len(ozet.get("basarili",[])) + len(ozet.get("kismi",[])) > 0:
                    st.session_state.last_dialog_align = "center"
                    st.session_state.durum_ozeti_dialog_open = True
                st.rerun()
            elif st.session_state.get("batch_finish_requested", False):
                st.session_state.batch_mode = False; st.session_state.durum_ozeti_suppress = False; cleanup_flags(); st.rerun()
            elif not st.session_state.get("batch_paused", False):
                new_idx = st.session_state.batch_queue_idx
                if new_idx < len(queue):
                    next_node = queue[new_idx]
                    next_script = _get_batch_scripts().get(next_node)
                    # video_montaj / toplu_video → sadece pixverse tam başarılıysa çalıştır
                    if next_node in ("video_montaj", "toplu_video"):
                        if node_status == "partial":
                            _save_resume(next_node, next_node)
                            st.session_state.batch_mode = False; cleanup_flags()
                        else:
                            st.session_state.status[next_node] = "running"
                            if next_node == "video_montaj":
                                start_video_montaj_bg("batch")
                            else:
                                start_toplu_video_bg("batch")
                    elif next_script:
                        st.session_state.status[next_node] = "running"
                        if next_node == "pixverse":
                            _reset_pixverse_retry_state_if_needed()
                        if not (start_analyze_bg("batch") if next_node == "analyze" else bg_start("batch", next_node, next_script)):
                            st.session_state.batch_mode = False; st.session_state.batch_queue_idx = 0; cleanup_flags()
                    else:
                        st.session_state.batch_queue_idx = new_idx + 1
                else:
                    st.session_state.batch_mode = False; st.session_state.batch_queue_idx = 0; cleanup_flags()
                st.rerun()
            else:
                st.rerun()
        else:
            st.session_state.status[node] = "error"
            cur_logs = list(st.session_state.logs)

            if node == "pixverse":
                # Hata tipine göre rollback noktasını belirle
                _set_batch_pixverse_retry_targets(cur_logs)
                px_err = _detect_pixverse_error_type(cur_logs)
                if px_err == "prompt":
                    # Prompt çok uzun → Prompt Düzelt'e geri dön
                    rollback_node = "prompt_duzeltme"
                    _resume_reason = "⚠️ Prompt çok uzun — Prompt Düzelt'ten başlanacak."
                    log("[INFO] Prompt uzunluk hatası tespit edildi → Prompt Düzelt'ten başlanacak.")
                    # prompt_duzeltme kuyruğa dahil değilse pixverse'den önce ekle
                    if rollback_node not in queue:
                        pv_pos = queue.index("pixverse") if "pixverse" in queue else len(queue)
                        queue.insert(pv_pos, "prompt_duzeltme")
                        st.session_state.batch_queue = list(queue)
                elif px_err == "credit":
                    # Kredi yetersiz → Video Üret'ten tekrar dene
                    rollback_node = "pixverse"
                    _resume_reason = f"⚠️ Kredi yetersiz — {get_video_generation_label(emoji=False)} adımından tekrar denenecek."
                    log(f"[INFO] Kredi hatası tespit edildi → {get_video_generation_label(emoji=False)} adımından tekrar başlanacak.")
                else:
                    # Diğer hatalar (API hatası, zaman aşımı vb.) → doğrudan Video Üret'ten tekrar dene
                    rollback_node = "pixverse"
                    _resume_reason = f"⚠️ Video üretim hatası — {get_video_generation_label(emoji=False)} adımından tekrar denenecek."
                    log(f"[INFO] Video üretim hatası → {get_video_generation_label(emoji=False)} adımından tekrar başlanacak.")

            elif node == "gorsel_klonlama":
                # API hatası ise Görsel Klonla'dan, değilse Görsel Analiz'den başla
                gk_err = _detect_gorsel_klonlama_error_type(cur_logs)
                if gk_err == "api":
                    rollback_node = "gorsel_klonlama"
                    _resume_reason = "⚠️ API hatası — Görsel Klonla'dan tekrar denenecek."
                    log("[INFO] API hatası tespit edildi → Görsel Klonla'dan tekrar başlanacak.")
                else:
                    rollback_node = ROLLBACK_START.get("gorsel_klonlama", "gorsel_analiz")
                    _resume_reason = "⚠️ Görsel klonlama hatası — Görsel Analiz'den baştan başlanacak."
                    log("[INFO] Görsel klonlama hatası → Görsel Analiz'den baştan başlanacak.")

            else:
                rollback_node = ROLLBACK_START.get(node, node)
                _resume_reason = ""

            st.session_state.batch_resume_reason = _resume_reason
            _stop_batch_with_resume(rollback_node)
            st.rerun()

    # Sonraki adımı başlat — sadece yeni batch başlangıcında veya resume'da (result işleme yukarıda halletti)
    if not bg_is_running() and not st.session_state.get("batch_paused", False) and not st.session_state.get("batch_finish_requested", False) and not res:
        q_idx = st.session_state.get("batch_queue_idx", 0)
        if q_idx < len(queue):
            node_key = queue[q_idx]
            script   = _get_batch_scripts().get(node_key)
            if node_key == "video_montaj":
                st.session_state.status[node_key] = "running"
                start_video_montaj_bg("batch"); st.rerun()
            elif node_key == "toplu_video":
                st.session_state.status[node_key] = "running"
                start_toplu_video_bg("batch"); st.rerun()
            elif script:
                st.session_state.status[node_key] = "running"
                if node_key == "pixverse":
                    _reset_pixverse_retry_state_if_needed()
                    _started_ok = start_pixverse_bg("batch")
                else:
                    _started_ok = start_analyze_bg("batch") if node_key == "analyze" else bg_start("batch", node_key, script)
                if not _started_ok:
                    st.session_state.batch_mode = False; st.session_state.batch_queue_idx = 0; cleanup_flags()
                st.rerun()
            else:
                st.session_state.batch_queue_idx = q_idx + 1; st.rerun()
        else:
            st.session_state.batch_mode = False; st.session_state.batch_queue_idx = 0; cleanup_flags(); st.rerun()

is_single_active = (st.session_state.get("single_mode", False) or st.session_state.get("single_paused", False) or st.session_state.get("single_finish_requested", False))
if is_single_active and not st.session_state.get("batch_mode", False):
    # Tekli işlem aktifken durum özeti panelini kapat ve gizle.
    # Böylece başarısız işlem sonrası yeniden denemede panel göz kırpmaz.
    st.session_state.durum_ozeti_suppress = True
    st.session_state.durum_ozeti_dialog_open = False

    if st.session_state.get("single_finish_requested", False) and not bg_is_running():
        _step = st.session_state.get("single_step") or st.session_state.get("_paused_step")
        if _step and st.session_state.status.get(_step) == "running": st.session_state.status[_step] = "idle"
        st.session_state.single_mode = False; st.session_state.single_step = None; st.session_state.single_finish_requested = False
        st.session_state.single_paused = False; st.session_state.bg_last_result = None
        st.session_state.durum_ozeti_suppress = False
        if "_paused_step" in st.session_state: del st.session_state["_paused_step"]
        cleanup_flags(); st.rerun()

    res = st.session_state.get("bg_last_result")
    if res and res.get("owner") == "single":
        st.session_state.bg_last_result = None; st.session_state.single_mode = False; st.session_state.single_step = None
        st.session_state.durum_ozeti_suppress = False
        if st.session_state.get("single_finish_requested", False): st.session_state.single_finish_requested = False; cleanup_flags()
        st.rerun()

    if not st.session_state.get("single_paused", False) and not st.session_state.get("single_finish_requested", False):
        if not bg_is_running():
            step = st.session_state.get("single_step")
            _single_started = False
            if step == "youtube_link": _single_started = bg_start("single", "youtube_link", st.session_state.settings["youtube_link_script"], args=st.session_state.get("youtube_link_args", []))
            elif step == "download": _single_started = bg_start("single", "download", st.session_state.settings["video_indir_script"])
            elif step == "analyze": _single_started = start_analyze_bg("single")
            elif step == "pixverse": _single_started = start_pixverse_bg("single")
            elif step == "gorsel_analiz": _single_started = bg_start("single", "gorsel_analiz", st.session_state.settings["analiz_script"])
            elif step == "gorsel_klonlama": _single_started = bg_start("single", "gorsel_klonlama", st.session_state.settings["gorsel_klonlama_script"])
            elif step == "gorsel_olustur": _single_started = bg_start("single", "gorsel_olustur", st.session_state.settings.get("gorsel_olustur_motor", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluştur\gorsel_olustur_motoru.py"))
            elif step == "prompt_duzeltme": _single_started = bg_start("single", "prompt_duzeltme", st.session_state.settings["prompt_duzeltme_script"])
            elif step == "video_montaj": _single_started = start_video_montaj_bg("single")
            elif step == "toplu_video": _single_started = start_toplu_video_bg("single")
            elif step == "sosyal_medya": _single_started = bg_start("single", "sosyal_medya", st.session_state.settings["sosyal_medya_script"])
            if step and not _single_started:
                st.session_state.single_mode = False; st.session_state.single_step = None
                st.session_state.durum_ozeti_suppress = False
            if step:
                st.rerun()


# ==========================================
# 4. GÖRSEL ARAYÜZ (CSS VE YARDIMCILAR)
# ==========================================
st.markdown("""
<style>
header {visibility: hidden;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

@keyframes neonMove {
  0% { background-position: 0% 0%, 100% 100%; }
  33% { background-position: 100% 10%, 0% 90%; }
  66% { background-position: 10% 100%, 90% 0%; }
  100% { background-position: 0% 0%, 100% 100%; }
}

.stApp {
  background: #0b0f17;
  background-image: 
    radial-gradient(circle at 20% 30%, rgba(0, 242, 255, 0.06) 0%, transparent 40%),
    radial-gradient(circle at 80% 70%, rgba(255, 0, 255, 0.06) 0%, transparent 40%),
    radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px);
  background-size: 200% 200%, 200% 200%, 22px 22px;
  background-attachment: fixed;
  animation: neonMove 15s linear infinite;
}

.workflow-canvas-card {
  border: 1px solid rgba(255,255,255,0.10) !important;
  background: rgba(255,255,255,0.03) !important;
  border-radius: 18px !important;
  padding: 12px !important;
  margin-bottom: 10px !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
}
.block-container { padding-top: 12px !important; padding-bottom: 10px !important; max-width: 1800px; }

/* Topbar */
.topbar { position: sticky; top: 0; z-index: 999; backdrop-filter: blur(10px); background: rgba(11, 15, 23, 0.55); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 12px 14px; margin-bottom: 16px; display:flex; justify-content: space-between; align-items:center; }
.brand { font-size: 24px; font-weight: 900; color: #e9ecf5; letter-spacing: 0.2px; }
.sub { font-size: 12px; color: rgba(233,236,245,0.65); margin-top: 2px; }
.badges { display:flex; gap:10px; align-items:center; }
.badge { border: 1px solid rgba(255,255,255,0.10); background: rgba(255,255,255,0.04); padding: 8px 12px; border-radius: 12px; color: rgba(233,236,245,0.92); font-weight: 700; font-size: 12px; }

.card { border: 1px solid rgba(255,255,255,0.10); background: rgba(255,255,255,0.03); border-radius: 18px; padding: 16px; margin-bottom: 14px; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
.top-column-strip { width: 100%; height: 30px; border: 1px solid rgba(255,255,255,0.10); background: rgba(255,255,255,0.025); border-radius: 999px; margin: 0 0 12px 0; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
.right-panel-strip { height: 6px; border: 1px solid rgba(255,255,255,0.10); background: rgba(255,255,255,0.025); border-radius: 999px; margin: 2px 0 8px 0; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
.right-panel-title { display:flex; align-items:center; gap:8px; font-size: 21px; font-weight: 800; color: #f8fafc; margin: 0 0 4px 0; line-height: 1.12; }
.right-panel-subtitle { font-size: 12px; font-weight: 700; color: rgba(233,236,245,0.92); margin: 0 0 6px 0; line-height: 1.12; }

/* LOG STYLE */
.log-wrapper { background: #0a0e15; border: 1px solid rgba(255,255,255,0.12); border-radius: 12px; padding: 12px; height: 210px; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column-reverse; }
.log-line { font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.5; color: #e0e0e0; margin: 1px 0; white-space: pre-wrap; word-wrap: break-word; }
.log-wrapper::-webkit-scrollbar { width: 8px; }
.log-wrapper::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); border-radius: 4px; }
.log-wrapper::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }

.log-ok { color: #4ade80; }
.log-error { color: #f87171; }
.log-info { color: #60a5fa; }
.log-warn { color: #fbbf24; }

/* BUTTON STYLES */
.stButton > button { border-radius: 12px !important; border: 1px solid rgba(255,255,255,0.14) !important; background: rgba(255,255,255,0.06) !important; color: #eef2ff !important; padding: 14px 20px !important; font-weight: 800 !important; font-size: 15px !important; transition: all .15s ease; width: 100%; }
.stButton > button:hover { background: rgba(255,255,255,0.10) !important; transform: translateY(-1px); box-shadow: 0 4px 15px rgba(99, 102, 241, 0.2); border-color: rgba(99, 102, 241, 0.4) !important; }

.btn-primary button { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; }
.btn-success button { background: linear-gradient(135deg, #10b981, #059669) !important; }
.btn-warning button { background: linear-gradient(135deg, #f59e0b, #d97706) !important; }
.btn-danger button { background: linear-gradient(135deg, #ef4444, #dc2626) !important; }
.btn-info button { background: linear-gradient(135deg, #3b82f6, #2563eb) !important; }
.btn-purple button { background: linear-gradient(135deg, #a855f7, #7c3aed) !important; }
.btn-teal button { background: linear-gradient(135deg, #14b8a6, #0d9488) !important; }

.stButton > button:disabled { opacity: 0.35 !important; filter: grayscale(1) !important; cursor: not-allowed !important; transform: none !important; box-shadow: none !important; }

.btn-primary button:disabled,
.btn-success button:disabled,
.btn-warning button:disabled,
.btn-danger button:disabled,
.btn-info button:disabled,
.btn-purple button:disabled,
.btn-teal button:disabled {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
}

/* LOADING */
.loader-container { display: flex; align-items: center; gap: 12px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 12px 15px; width: 100%; animation: pulse-border 1.5s infinite; }
@keyframes pulse-border { 0% { border-color: rgba(99, 102, 241, 0.3); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.2); } 50% { border-color: rgba(99, 102, 241, 0.7); box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1); } 100% { border-color: rgba(99, 102, 241, 0.3); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.2); } }
.spinner { width: 20px; height: 20px; border: 3px solid rgba(255,255,255,0.1); border-radius: 50%; border-top-color: #6366f1; animation: spin 1s ease-in-out infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loader-text { font-size: 14px; font-weight: 600; color: #e0e7ff; }

/* KONTROL PANELİ */
.control-panel-title { font-size: 13px; font-weight: 700; color: rgba(233,236,245,0.75); margin-bottom: 8px; letter-spacing: 0.3px; }
.control-panel-badge-batch { display: inline-block; background: rgba(99,102,241,0.25); border: 1px solid rgba(99,102,241,0.5); color: #a5b4fc; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 20px; margin-left: 6px; }
.control-panel-badge-single { display: inline-block; background: rgba(16,185,129,0.20); border: 1px solid rgba(16,185,129,0.45); color: #6ee7b7; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 20px; margin-left: 6px; }

/* Dialog (Modal) Styles */
div[data-testid="stModal"] { background: rgba(0, 0, 0, 0.75) !important; backdrop-filter: blur(8px) !important; -webkit-backdrop-filter: blur(8px) !important; }
div[data-testid="stModal"] > div:first-child { background: transparent !important; }
div[data-testid="stDialog"] { display: flex !important; align-items: flex-start !important; padding-top: 30px !important; }
div[data-testid="stDialog"] > div { max-width: 500px !important; width: 32vw !important; min-width: 420px !important; max-height: calc(100vh - 80px) !important; border-radius: 18px !important; border: 1px solid rgba(255,255,255,0.13) !important; box-shadow: 0 24px 64px rgba(0,0,0,0.70), 0 0 0 1px rgba(255,255,255,0.05) !important; overflow-y: auto !important; overflow-x: hidden !important; }
div[data-testid="stDialog"] > div > div { background: #111118 !important; border: none !important; border-radius: 18px !important; padding: 16px 20px !important; }
div[data-testid="stDialog"] > div > div > div:first-child { border-bottom: 1px solid rgba(255,255,255,0.08) !important; padding-bottom: 10px !important; margin-bottom: 8px !important; }
div[data-testid="stDialog"] button[aria-label="Close"] { display: flex !important; align-items: center !important; justify-content: center !important; width: 28px !important; height: 28px !important; border-radius: 8px !important; background: transparent !important; border: none !important; color: #94a3b8 !important; opacity: 1 !important; }

div[data-testid="stDialog"] > div::-webkit-scrollbar { width: 5px; }
div[data-testid="stDialog"] > div::-webkit-scrollbar-track { background: transparent; }
div[data-testid="stDialog"] > div::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 3px; }
div[data-testid="stDialog"] > div::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.20); }
div[data-testid="stDialog"] .stButton > button { width: 100% !important; }
div[data-testid="stDialog"] .stButton > button { font-size: 13px !important; padding: 8px 6px !important; display: flex !important; align-items: center !important; justify-content: center !important; line-height: 1.2 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
.lightbox-caption { text-align: center; color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 600; margin-bottom: 8px; padding: 4px 14px; background: rgba(255,255,255,0.08); border-radius: 16px; display: inline-block; }
div[data-testid="stDialog"] img { max-height: 70vh !important; max-width: 100% !important; object-fit: contain !important; display: block !important; margin: 0 auto !important; border-radius: 6px; }

/* Sekme Stilleri */
div[data-baseweb="tab-list"] { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 4px; }
div[data-baseweb="tab"] { background: transparent; border-radius: 8px; padding: 8px 16px; margin: 0 4px; }
div[aria-selected="true"] { background: rgba(99,102,241,0.2) !important; border: 1px solid rgba(99,102,241,0.4) !important; color: #e0e7ff !important; font-weight: 700; }

/* AÇILIR MENÜ (SELECTBOX) TIKLAMA HASSASİYETİ DÜZELTMESİ */
div[data-testid="stSelectbox"] input {
    caret-color: transparent !important;
    cursor: pointer !important;
}
</style>
""", unsafe_allow_html=True)

# Göz kırpma (flicker) olmaması için Dialog hizalama CSS'ini anında dinamik yüklüyoruz.
# Durum Özeti açılacaksa her zaman merkeze al (last_dialog_align ne olursa olsun)
_eff_align = "center" if st.session_state.get("durum_ozeti_dialog_open", False) else st.session_state.last_dialog_align

if _eff_align == "left":
    st.markdown('<style>div[data-testid="stDialog"] { justify-content: flex-start !important; padding-left: 2.5% !important; padding-right: 0 !important; }</style>', unsafe_allow_html=True)
elif _eff_align == "right":
    st.markdown('<style>div[data-testid="stDialog"] { justify-content: flex-end !important; padding-right: 2.5% !important; padding-left: 0 !important; }</style>', unsafe_allow_html=True)
else:
    st.markdown('<style>div[data-testid="stDialog"] { justify-content: center !important; align-items: center !important; padding: 0 !important; padding-top: 0 !important; }</style>', unsafe_allow_html=True)

# Veri isleme yardımcıları
# --- LOADER HTML HELPER FIX ---
def get_loader_html(label: str) -> str:
    safe_label = str(label or "İşlem çalışıyor...")
    return f"""
    <div class="loader-container">
        <div class="spinner"></div>
        <div class="loader-text">{safe_label}</div>
    </div>
    """

def render_dialog_single_controls(step_match: str | None = None, prefix: str = "dlg_ctrl"):
    is_kredi = step_match in ["kredi_kazan", "kredi_cek"]
    if st.session_state.get("batch_mode", False) and not is_kredi: return

    kredi_pause_key = None
    kredi_finish_key = None
    kredi_running_key = None

    if is_kredi:
        kredi_running_key = f"{step_match}_running"
        kredi_pause_key = f"{step_match}_paused"
        kredi_finish_key = f"{step_match}_finish"
        _kr_running = st.session_state.get(kredi_running_key, False) or (bg_is_running() and st.session_state.get("bg_node_key") == step_match)
        if not _kr_running:
            return
        step = step_match
        is_active = True
        is_paused = st.session_state.get(kredi_pause_key, False)
    else:
        step = st.session_state.get("_paused_step") or st.session_state.get("single_step")
        if step_match and step != step_match: return
        is_active = (any_running() or st.session_state.get("single_mode", False) or st.session_state.get("single_paused", False) or st.session_state.get("single_finish_requested", False))
        if not is_active: return
        is_paused = st.session_state.get("single_paused", False)

    label = {"youtube_link":"📺 YouTube Link Toplama","download":"⬇️ Video İndiriliyor","gorsel_analiz":"🖼️ Görsel Analiz","gorsel_klonlama":"🎨 Görsel Klonlama","analyze":"📄 Analiz & Prompt","pixverse":get_video_generation_label(),"gorsel_olustur":"🚀 Görsel Oluştur","prompt_duzeltme":"✏️ Prompt Düzeltme","video_montaj":"🎥️ Video Montaj","toplu_video":"🎬 Toplu Video Montaj","sosyal_medya":"🌐 Sosyal Medya Paylaşım","kredi_kazan":"🎰 Video Üretme Kredisi Kazan","kredi_cek":"📥 Üretilen Kredileri Çek"}.get(step, "İşlem")
    is_really_running = bg_is_running()

    if is_kredi and is_paused:
        status_text = f"⏸️ Duraklatıldı - {label}"
    elif is_paused and is_really_running:
        status_text = f"⏳ Durduruluyor... (Lütfen bekleyin) - {label}"
    elif is_paused:
        status_text = f"⏸️ Duraklatıldı - {label}"
    else:
        status_text = f"▶️ Çalışıyor - {label}"

    if is_paused and (is_kredi or not is_really_running):
        st.markdown(f'<div class="loader-container"><div class="loader-text">{status_text}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(get_loader_html(status_text), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        _pause_disabled = is_paused if is_kredi else (is_paused or not is_really_running)
        if st.button("⏸️ Durdur", key=f"{prefix}_pause", use_container_width=True, disabled=_pause_disabled):
            if is_kredi:
                st.session_state[kredi_pause_key] = True
                _kr_script = KREDI_YENILEME_SCRIPT if step == "kredi_cek" else PIXVERSE5_SCRIPT
                try:
                    with open(os.path.join(os.path.dirname(_kr_script), "pause.txt"), "w", encoding="utf-8") as pf:
                        pf.write("pause")
                except Exception:
                    pass
            else:
                st.session_state.single_paused = True; create_stop_flag(); st.session_state.single_mode = False; st.session_state["_paused_step"] = step
                try: bg_terminate()
                except: pass
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        _resume_disabled = (not is_paused) if is_kredi else (not is_paused or is_really_running)
        if st.button("▶️ Devam Ettir", key=f"{prefix}_resume", use_container_width=True, disabled=_resume_disabled):
            if is_kredi:
                st.session_state[kredi_pause_key] = False
                _kr_script = KREDI_YENILEME_SCRIPT if step == "kredi_cek" else PIXVERSE5_SCRIPT
                try:
                    with open(os.path.join(os.path.dirname(_kr_script), "pause.txt"), "w", encoding="utf-8") as pf:
                        pf.write("resume")
                except Exception:
                    pass
            else:
                st.session_state.single_paused = False; cleanup_flags(); st.session_state.bg_last_result = None
                st.session_state.single_step = st.session_state.pop("_paused_step", step); st.session_state.single_mode = True
                st.session_state.status[st.session_state.single_step] = "running"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
        if st.button("⏹️ Bitir", key=f"{prefix}_finish", use_container_width=True):
            if is_kredi:
                st.session_state[kredi_finish_key] = True
                st.session_state[kredi_pause_key] = False
                st.session_state[kredi_running_key] = False
                st.session_state.kredi_kazan_running = False
                st.session_state.kredi_cek_running = False
                try: bg_terminate()
                except: pass
            else:
                st.session_state.single_finish_requested = True; create_stop_flag(); remove_pause_flag()
                try: bg_terminate()
                except: pass
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- RENDER LOGS HTML SAFE FIX ---
def render_logs_html() -> str:
    logs = st.session_state.get("logs", []) or []

    if not logs:
        return '<div class="log-line log-info">Henüz işlem başlatılmadı...</div>'

    html_lines = []
    for line in reversed(logs[-500:]):
        if _is_verbose_social_log_line(line):
            continue

        safe = (
            str(line)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        css_class = "log-line"
        upper = safe.upper()

        if "[ERROR]" in upper or "HATA" in upper:
            css_class += " log-error"
        elif "[OK]" in upper:
            css_class += " log-ok"
        elif "[WARN]" in upper or "[UYARI]" in upper:
            css_class += " log-warn"
        elif "[INFO]" in upper:
            css_class += " log-info"

        html_lines.append(f'<div class="{css_class}">{safe}</div>')

    if not html_lines:
        return '<div class="log-line log-info">Gösterilecek özet log bulunamadı...</div>'

    return f'<div class="log-wrapper">{"".join(html_lines)}</div>'

def save_links(text: str, append: bool = False, path: str | None = None):
    target_path = (path or st.session_state.settings["links_file"]).strip()
    result = _save_links_to_path(target_path, text, append=append)
    if append:
        if result.get("added", 0) > 0:
            log(f"[OK] Link listesi mevcut listenin devamına kaydedildi: +{result['added']} yeni link ({target_path})")
        else:
            log(f"[WARN] Yeni link bulunamadı; mevcut link listesi değişmedi: {target_path}")
    else:
        log(f"[OK] Link listesi kaydedildi: {target_path}")

def set_link_canvas_source(source: str):
    st.session_state.link_canvas_source = source
    if source in ("youtube", "manual", "added_video"):
        st.session_state.go_motion_prompt_saved = False

def reset_link_canvas_states():
    st.session_state.status["input"] = "idle"
    st.session_state.status["youtube_link"] = "idle"
    st.session_state.link_canvas_source = "none"

def get_link_canvas_status(status_map: dict) -> str:
    source = st.session_state.get("link_canvas_source", "none")
    youtube_st = status_map.get("youtube_link", "idle")
    input_st = status_map.get("input", "idle")
    active_order = ("running", "paused", "error", "partial", "ok")

    if youtube_st in ("running", "paused"):
        return youtube_st
    if input_st in ("running", "paused"):
        return input_st

    if source == "youtube" and youtube_st in active_order:
        return youtube_st
    if source == "manual" and input_st in active_order:
        return input_st
    if source == "added_video" and input_st in active_order:
        return input_st

    for cand in ("error", "partial", "ok"):
        if input_st == cand:
            return cand
        if youtube_st == cand:
            return cand
    return "idle"

def get_link_canvas_subtitle(status_map: dict) -> str:
    source = st.session_state.get("link_canvas_source", "none")
    youtube_st = status_map.get("youtube_link", "idle")
    input_st = status_map.get("input", "idle")
    if youtube_st in ("running", "paused") or source == "youtube":
        return "YouTube'dan Liste Oluştur"
    if input_st in ("running", "paused") or source == "manual":
        return "Video Listesi Ekle"
    if input_st in ("running", "paused") or source == "added_video":
        return "Video Ekle"
    return "YouTube listesi oluştur / video link ekle / video ekle"


PROMPT_SOURCE_MODE_FILE = os.path.join(CONTROL_DIR, "prompt_source_mode.txt")
PROMPT_SOURCE_LINK = "link"
PROMPT_SOURCE_ADDED_VIDEO = "added_video"
PROMPT_SOURCE_DOWNLOADED_VIDEO = "downloaded_video"
SUPPORTED_VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")


def _normalize_prompt_source_mode(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in {PROMPT_SOURCE_LINK, "youtube", "manual"}:
        return PROMPT_SOURCE_LINK
    if raw in {PROMPT_SOURCE_ADDED_VIDEO, "video", "eklenen_video", "eklenen video"}:
        return PROMPT_SOURCE_ADDED_VIDEO
    if raw in {PROMPT_SOURCE_DOWNLOADED_VIDEO, "download", "indirilen_video", "indirilen video"}:
        return PROMPT_SOURCE_DOWNLOADED_VIDEO
    return "auto"


def _write_prompt_source_mode(mode: str):
    mode = _normalize_prompt_source_mode(mode)
    try:
        os.makedirs(os.path.dirname(PROMPT_SOURCE_MODE_FILE), exist_ok=True)
        with open(PROMPT_SOURCE_MODE_FILE, "w", encoding="utf-8") as f:
            f.write(mode)
    except Exception:
        pass


def _read_prompt_source_mode() -> str:
    try:
        if os.path.exists(PROMPT_SOURCE_MODE_FILE):
            with open(PROMPT_SOURCE_MODE_FILE, "r", encoding="utf-8") as f:
                return _normalize_prompt_source_mode(f.read().strip())
    except Exception:
        pass
    return "auto"


def _get_added_video_dir() -> str:
    return (st.session_state.settings.get("added_video_dir") or r"C:\Users\User\Desktop\Otomasyon\Eklenen Video").strip()


def _video_file_sort_key(value: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(value or ''))]


def _is_supported_video_name(name: str) -> bool:
    return str(name or '').lower().endswith(SUPPORTED_VIDEO_EXTS)


def _get_video_duration_seconds(video_path: str) -> float:
    """ffprobe ile videonun süresini saniye cinsinden döndürür."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _format_duration(seconds: float) -> str:
    """Saniyeyi okunabilir formata çevirir (ör: 1dk 30sn)."""
    if seconds <= 0:
        return "0sn"
    m = int(seconds) // 60
    s = int(seconds) % 60
    if m > 0 and s > 0:
        return f"{m}dk {s}sn"
    if m > 0:
        return f"{m}dk"
    return f"{s}sn"


def _format_mmss(seconds: float) -> str:
    """Saniyeyi M:SS formatına çevirir (ör: 1:30)."""
    if seconds <= 0:
        return "0:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def _parse_mmss(text: str) -> float:
    """M:SS veya SS formatını saniyeye çevirir. Hatalıysa -1 döner."""
    text = (text or "").strip().replace(",", ".")
    if not text:
        return -1
    if ":" in text:
        parts = text.split(":")
        if len(parts) != 2:
            return -1
        try:
            m = int(parts[0])
            s = float(parts[1])
            return m * 60 + s
        except (ValueError, TypeError):
            return -1
    try:
        return float(text)
    except (ValueError, TypeError):
        return -1


def _split_video_by_segments(video_path: str, segments: list, output_dir: str, baslangic_no: int = 1) -> list:
    """Videoyu belirlenen süre segmentlerine göre böler.
    segments: [(start_sec, end_sec), ...]
    Her segment Video N klasörüne kaydedilir.
    Dönen liste: [{"no": N, "folder": path, "video": path}, ...]
    """
    results = []
    ext = os.path.splitext(video_path)[1] or ".mp4"
    for idx, (start, end) in enumerate(segments):
        video_no = baslangic_no + idx
        klasor = os.path.join(output_dir, f"Video {video_no}")
        os.makedirs(klasor, exist_ok=True)
        out_name = f"bolum_{video_no}{ext}"
        out_path = os.path.join(klasor, out_name)
        duration = end - start
        try:
            # Re-encode ile bölme: -ss input seeking (hızlı + doğru keyframe),
            # video ve ses yeniden encode edilerek donuk görüntü sorunu önlenir.
            subprocess.run(
                ["ffmpeg", "-y",
                 "-ss", str(start),
                 "-i", video_path,
                 "-t", str(duration),
                 "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                 "-c:a", "aac", "-b:a", "192k",
                 "-avoid_negative_ts", "make_zero",
                 "-movflags", "+faststart",
                 out_path],
                capture_output=True, text=True, timeout=600,
            )
            if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
                results.append({"no": video_no, "folder": klasor, "video": out_path})
        except Exception:
            pass
    return results


def _list_added_video_entries() -> list:
    root = _get_added_video_dir()
    if not root or not os.path.isdir(root):
        return []

    out = []
    try:
        klasorler = [k for k in os.listdir(root) if os.path.isdir(os.path.join(root, k))]
    except Exception:
        return []

    klasorler.sort(key=_video_file_sort_key)
    for idx, klasor_adi in enumerate(klasorler, start=1):
        klasor_yolu = os.path.join(root, klasor_adi)
        try:
            videolar = [f for f in os.listdir(klasor_yolu) if os.path.isfile(os.path.join(klasor_yolu, f)) and _is_supported_video_name(f)]
        except Exception:
            videolar = []
        if not videolar:
            continue
        videolar.sort(key=_video_file_sort_key)
        video_adi = videolar[0]
        match = re.search(r'(\d+)\s*$', klasor_adi)
        no = int(match.group(1)) if match else idx
        out.append({
            "no": no,
            "folder_name": klasor_adi,
            "folder_path": klasor_yolu,
            "video_name": video_adi,
            "video_path": os.path.join(klasor_yolu, video_adi),
        })
    return out


def _count_added_videos() -> int:
    return len(_list_added_video_entries())


def _list_download_video_entries() -> list:
    root = (st.session_state.settings.get("download_dir") or "").strip()
    if not root or not os.path.isdir(root):
        return []

    out = []
    try:
        klasorler = [k for k in os.listdir(root) if os.path.isdir(os.path.join(root, k))]
    except Exception:
        return []

    klasorler.sort(key=_video_file_sort_key)
    for idx, klasor_adi in enumerate(klasorler, start=1):
        klasor_yolu = os.path.join(root, klasor_adi)
        try:
            videolar = [
                f for f in os.listdir(klasor_yolu)
                if os.path.isfile(os.path.join(klasor_yolu, f)) and _is_supported_video_name(f)
            ]
        except Exception:
            videolar = []
        if not videolar:
            continue
        videolar.sort(key=_video_file_sort_key)
        video_adi = videolar[0]
        match = re.search(r'(\d+)\s*$', klasor_adi)
        no = int(match.group(1)) if match else idx
        out.append({
            "no": no,
            "folder_name": klasor_adi,
            "folder_path": klasor_yolu,
            "video_name": video_adi,
            "video_path": os.path.join(klasor_yolu, video_adi),
            "source_kind": "download",
        })
    return out


def _count_download_videos() -> int:
    return len(_list_download_video_entries())


def _list_gorsel_analiz_source_entries() -> list:
    mode = _get_effective_prompt_source_mode()
    if mode == PROMPT_SOURCE_ADDED_VIDEO:
        return _list_added_video_entries()
    return _list_download_video_entries()


def _get_gorsel_analiz_source_label() -> str:
    if _get_effective_prompt_source_mode() == PROMPT_SOURCE_ADDED_VIDEO:
        return "🎞️ Video Ekle"
    return "⬇️ İndirilen Video"


def _list_toplu_video_added_source_items() -> list:
    items = []
    for idx, entry in enumerate(_list_added_video_entries(), start=1):
        items.append({
            "token": str(idx),
            "script_token": str(idx - 1),
            "label": f"[{idx}] Eklenen Video {entry.get('no', idx)}",
            "path": entry.get("video_path", ""),
            "exists": True,
            "expected": False,
            "video_no": int(entry.get("no", idx) or idx),
            "source_kind": "added_video",
        })
    return items


def _count_prompt_links() -> int:
    links_file = st.session_state.settings.get("links_file", "")
    if not links_file or not os.path.exists(links_file):
        return 0
    try:
        with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
            return len([ln for ln in f.read().splitlines() if ln.strip()])
    except Exception:
        return 0


def _get_effective_prompt_source_mode() -> str:
    canvas_source = st.session_state.get("link_canvas_source", "none")
    if canvas_source == "added_video":
        return PROMPT_SOURCE_ADDED_VIDEO
    if canvas_source in ("youtube", "manual"):
        return PROMPT_SOURCE_LINK

    file_mode = _read_prompt_source_mode()
    if file_mode != "auto":
        return file_mode

    link_count = _count_prompt_links()
    added_count = _count_added_videos()
    if link_count and not added_count:
        return PROMPT_SOURCE_LINK
    if added_count and not link_count:
        return PROMPT_SOURCE_ADDED_VIDEO
    if link_count:
        return PROMPT_SOURCE_LINK
    if added_count:
        return PROMPT_SOURCE_ADDED_VIDEO
    return "auto"


def _get_prompt_runtime_source_mode() -> str:
    mode = _get_effective_prompt_source_mode()
    if mode == PROMPT_SOURCE_ADDED_VIDEO:
        return PROMPT_SOURCE_ADDED_VIDEO

    download_count = _count_download_videos()
    link_count = _count_prompt_links()

    if download_count > 0:
        return PROMPT_SOURCE_DOWNLOADED_VIDEO
    if link_count > 0:
        return PROMPT_SOURCE_LINK
    return mode


def _prepare_prompt_source_for_analyze(owner: str | None = None) -> str:
    runtime_mode = _get_prompt_runtime_source_mode()
    _write_prompt_source_mode(runtime_mode)

    owner_label = "Tekli işlem" if owner == "single" else ("Tümünü Çalıştır" if owner == "batch" else "İşlem")
    if runtime_mode == PROMPT_SOURCE_ADDED_VIDEO:
        log(f"[INFO] {owner_label}: Prompt Oluştur kaynağı → Eklenen Video")
    elif runtime_mode == PROMPT_SOURCE_DOWNLOADED_VIDEO:
        log(f"[INFO] {owner_label}: Prompt Oluştur kaynağı → İndirilen Video")
    elif runtime_mode == PROMPT_SOURCE_LINK:
        log(f"[INFO] {owner_label}: İndirilen video bulunamadı → Prompt Oluştur linkten devam edecek")
    else:
        log(f"[INFO] {owner_label}: Prompt Oluştur için uygun kaynak bulunamadı")

    return runtime_mode


def start_analyze_bg(owner: str) -> bool:
    _prepare_prompt_source_for_analyze(owner)
    return bg_start(owner, "analyze", st.session_state.settings["prompt_script"])


def _get_prompt_input_count() -> int:
    mode = _get_prompt_runtime_source_mode()
    download_count = _count_download_videos()
    link_count = _count_prompt_links()
    added_count = _count_added_videos()
    if mode == PROMPT_SOURCE_ADDED_VIDEO:
        return added_count
    if mode == PROMPT_SOURCE_DOWNLOADED_VIDEO:
        return download_count
    if mode == PROMPT_SOURCE_LINK:
        return link_count
    return max(download_count, link_count, added_count)


def _get_prompt_input_label() -> str:
    mode = _get_prompt_runtime_source_mode()
    if mode == PROMPT_SOURCE_ADDED_VIDEO:
        return "Eklenen Video"
    if mode == PROMPT_SOURCE_DOWNLOADED_VIDEO:
        return "İndirilen Video"
    if mode == PROMPT_SOURCE_LINK:
        return "Link"
    return "Kaynak"


def _purge_prompt_state_for_prefix(prefix: str):
    prefix = str(prefix or '').strip().lower().rstrip('\\/')
    if not prefix:
        return

    prompt_dir = (st.session_state.settings.get("prompt_dir") or "").strip()
    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    mapping = data.get("mapping") if isinstance(data, dict) else {}
    processed = data.get("processed") if isinstance(data, dict) else []
    if not isinstance(mapping, dict):
        mapping = {}
    if not isinstance(processed, list):
        processed = []

    silinecek_anahtarlar = []
    silinecek_klasorler = set()
    for key, folder_name in list(mapping.items()):
        norm_key = str(key or '').strip().lower().rstrip('\\/')
        if norm_key.startswith(prefix):
            silinecek_anahtarlar.append(key)
            if folder_name:
                silinecek_klasorler.add(str(folder_name))

    if not silinecek_anahtarlar:
        return

    for key in silinecek_anahtarlar:
        mapping.pop(key, None)
    processed = [item for item in processed if item not in silinecek_anahtarlar]
    data["mapping"] = mapping
    data["processed"] = processed

    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    for folder_name in silinecek_klasorler:
        try:
            if prompt_dir:
                folder_path = os.path.join(prompt_dir, folder_name)
                if os.path.isdir(folder_path):
                    shutil.rmtree(folder_path)
        except Exception:
            pass

def natural_sort_key(s): return[int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
def get_gorsel_analiz_klasorleri():
    g_dir = st.session_state.settings.get("gorsel_analiz_dir", "")
    if not g_dir or not os.path.isdir(g_dir): return []
    try:
        klasorler =[d for d in os.listdir(g_dir) if os.path.isdir(os.path.join(g_dir, d))]
        klasorler.sort(key=natural_sort_key); return klasorler
    except Exception: return[]

def get_klasor_gorselleri(klasor_adi):
    k_yol = os.path.join(st.session_state.settings.get("gorsel_analiz_dir", ""), klasor_adi)
    if not os.path.isdir(k_yol): return[]
    try:
        gorseller =[f for f in os.listdir(k_yol) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]
        gorseller.sort(key=natural_sort_key); return gorseller
    except Exception: return[]

def gorsel_sec_ve_diger_sil(klasor_adi, secilen_gorsel):
    k_yol = os.path.join(st.session_state.settings.get("gorsel_analiz_dir", ""), klasor_adi)
    if not os.path.isdir(k_yol): return False
    silinen = 0
    try:
        for f in os.listdir(k_yol):
            d_yol = os.path.join(k_yol, f)
            if not os.path.isdir(d_yol) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')) and f != secilen_gorsel:
                os.remove(d_yol); silinen += 1
        log(f"[OK] {klasor_adi}: '{secilen_gorsel}' tutuldu, {silinen} görsel silindi."); return True
    except Exception as e: log(f"[ERROR] Görsel silme hatası: {e}"); return False

def gorsel_duzelt_oku():
    path = st.session_state.settings.get("gorsel_duzelt_txt", "")
    res = {}
    if not path or not os.path.exists(path): return res
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r"Görsel\s+(\d+)\s*:\s*(.*)", line.strip(), re.IGNORECASE)
                if match: res[int(match.group(1))] = match.group(2).strip()
    except Exception: pass
    return res

def gorsel_duzelt_kaydet(data: dict):
    path = st.session_state.settings.get("gorsel_duzelt_txt", "")
    if not path: return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            for no in sorted(data.keys()): f.write(f"Görsel {no}: {data[no]}\n")
        log(f"[OK] Görsel Düzelt.txt kaydedildi."); return True
    except Exception: return False

def gorsel_duzelt_sil():
    path = st.session_state.settings.get("gorsel_duzelt_txt", "")
    if not path: return False
    try:
        with open(path, 'w', encoding='utf-8') as f: f.write("")
        log("[OK] Görsel Düzelt temizlendi."); return True
    except Exception: return False


def _gorsel_referans_klasoru() -> str:
    """Referans görsellerin kaydedileceği klasör yolunu döndürür."""
    gorsel_duzelt_txt = st.session_state.settings.get("gorsel_duzelt_txt", "")
    if gorsel_duzelt_txt:
        return os.path.join(os.path.dirname(gorsel_duzelt_txt), "referans")
    return ""


def gorsel_referans_kaydet(gorsel_no: int, uploaded_file) -> bool:
    """Yüklenen referans görseli klasöre kaydeder. Daha önce aynı numara için görsel varsa siler."""
    klasor = _gorsel_referans_klasoru()
    if not klasor:
        return False
    try:
        os.makedirs(klasor, exist_ok=True)
        # Mevcut referans görselini sil
        for fname in os.listdir(klasor):
            if fname.startswith(f"ref_{gorsel_no}_") or fname == f"ref_{gorsel_no}.png":
                try:
                    os.remove(os.path.join(klasor, fname))
                except Exception:
                    pass
        ext = os.path.splitext(getattr(uploaded_file, "name", "") or "img.png")[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
            ext = ".png"
        dosya_adi = f"ref_{gorsel_no}{ext}"
        with open(os.path.join(klasor, dosya_adi), "wb") as f:
            f.write(uploaded_file.getbuffer())
        log(f"[OK] Referans görsel kaydedildi: {dosya_adi}")
        return True
    except Exception as e:
        log(f"[ERROR] Referans görsel kaydedilemedi: {e}")
        return False


def gorsel_referans_sil(gorsel_no: int) -> bool:
    """Belirli görsel numarasının referans görselini siler."""
    klasor = _gorsel_referans_klasoru()
    if not klasor or not os.path.isdir(klasor):
        return False
    try:
        for fname in os.listdir(klasor):
            if fname.startswith(f"ref_{gorsel_no}_") or re.match(rf"ref_{gorsel_no}\\..+", fname):
                try:
                    os.remove(os.path.join(klasor, fname))
                except Exception:
                    pass
        return True
    except Exception:
        return False


def gorsel_referans_tumunu_sil() -> bool:
    """Tüm referans görselleri siler."""
    klasor = _gorsel_referans_klasoru()
    if not klasor or not os.path.isdir(klasor):
        return True
    try:
        shutil.rmtree(klasor, ignore_errors=True)
        log("[OK] Tüm referans görseller silindi.")
        return True
    except Exception:
        return False


def gorsel_referans_yolu(gorsel_no: int) -> str:
    """Belirli görsel numarasının referans görsel yolunu döndürür (yoksa boş string)."""
    klasor = _gorsel_referans_klasoru()
    if not klasor or not os.path.isdir(klasor):
        return ""
    try:
        for fname in os.listdir(klasor):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                m = re.match(rf"ref_{gorsel_no}(\..+)$", fname)
                if m:
                    return os.path.join(klasor, fname)
    except Exception:
        pass
    return ""

def prompt_duzeltme_oku():
    """düzeltme.txt dosyasını oku — her Prompt N bloğundaki kullanıcı ek metnini döndür."""
    path = st.session_state.settings.get("prompt_duzeltme_txt", "")
    res = {}
    if not path or not os.path.exists(path): return res
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content_txt = f.read()
        blocks = re.split(r'(?=Prompt\s+\d+\s*:)', content_txt, flags=re.IGNORECASE)
        for block in blocks:
            # İlk satırdan Prompt N: Değiştirilmesi Gereken: <değer> al
            first_line = block.strip().splitlines()[0] if block.strip() else ""
            m_no = re.match(r'Prompt\s+(\d+)\s*:\s*Değiştirilmesi Gereken\s*:\s*(.*)', first_line, re.IGNORECASE)
            if not m_no: continue
            no = int(m_no.group(1))
            res[no] = m_no.group(2).strip()
    except Exception: pass
    return res

_PROMPT_DUZELTME_SABLON = """Düzeltilmesi Gereken Dil: Tamamen ingilizce.
Değiştirilmesi Gereken Kalite: Gerçek hayatta gerçekleşiyormuş gibi olacak. Animasyon tarzı olmayacak.
SINGLE FIXED CAMERA ANGLE. DO NOT ADD ALTERNATE ANGLES.
Integrate a cinematic timeline into the editing process.
Şablon yapısını bozmadan düzeltmeyi yap. Aynı şekilde çıktı ver."""

def prompt_duzeltme_kaydet(data: dict):
    """data = {1: kullanıcı_metni, ...}  →  düzeltme.txt'ye tam formatı yaz."""
    path = st.session_state.settings.get("prompt_duzeltme_txt", "")
    if not path: return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lines = []
        for no in sorted(data.keys()):
            if not str(data[no]).strip():  # Boş olanları atla
                continue
            lines.append(f"Prompt {no}: Değiştirilmesi Gereken: {data[no]}")
            lines.append(_PROMPT_DUZELTME_SABLON)
            lines.append("")
        with open(path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines).strip() + "\n")
        log(f"[OK] düzeltme.txt kaydedildi."); return True
    except Exception as e: log(f"[ERROR] düzeltme.txt kaydedilemedi: {e}"); return False


def gorsel_klonlama_notlarini_prompta_aktar(data: dict):
    """Görsel klonlama notlarını aynı sıra ile Prompt Düzeltme alanına yansıtır."""
    try:
        mevcut_data = {int(no): str(val or "").strip() for no, val in prompt_duzeltme_oku().items()}
        guncel_data = {int(no): str(val or "").strip() for no, val in (data or {}).items()}

        for no in sorted(guncel_data.keys()):
            yeni_deger = guncel_data.get(no, "")
            if yeni_deger:
                mevcut_data[no] = yeni_deger
            else:
                mevcut_data.pop(no, None)
            st.session_state.pop(f"pdzt_{no}", None)

        ok = prompt_duzeltme_kaydet(mevcut_data)
        if ok:
            log("[OK] Görsel Klonlama düzeltmeleri Prompt Düzeltme alanına aktarıldı.")
        return ok
    except Exception as e:
        log(f"[ERROR] Görsel Klonlama notları Prompt Düzeltme alanına aktarılamadı: {e}")
        return False



def sosyal_medya_yol_bilgisi():
    s = st.session_state.settings
    root = (s.get("sosyal_medya_dir") or r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım").strip()
    return {
        "dir": root,
        "script": (s.get("sosyal_medya_script") or os.path.join(root, "sosyal_medya_paylasım.py")).strip(),
        "aciklama": (s.get("sosyal_medya_aciklama_txt") or os.path.join(root, "açıklama.txt")).strip(),
        "baslik": (s.get("sosyal_medya_baslik_txt") or os.path.join(root, "başlık.txt")).strip(),
        "platform": (s.get("sosyal_medya_platform_txt") or os.path.join(root, "paylasılacak_sosyal_medyalar.txt")).strip(),
        "zamanlama": (s.get("sosyal_medya_zamanlama_txt") or os.path.join(root, "paylaşım_zamanlama.txt")).strip(),
        "hesap": os.path.join(root, "hesap.txt"),
        "video_kaynak": os.path.join(root, "video_kaynak.txt"),
        "kaynak_secim": os.path.join(root, "video_kaynak_secim.txt"),
    }

def sosyal_medya_read_text(path: str, default: str = "") -> str:
    if not path:
        return default
    encodings = ("utf-8", "cp1254", "latin-1")
    for enc in encodings:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding=enc, errors="ignore") as f:
                    return f.read().strip()
        except Exception:
            continue
    return default


def sosyal_medya_write_text(path: str, value: str) -> bool:
    if not path:
        return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(value or "").strip())
        return True
    except Exception as e:
        log(f"[ERROR] Sosyal medya TXT kaydedilemedi: {e}")
        return False


def sosyal_medya_ensure_files(sync_source_selection: bool = False):
    yollar = sosyal_medya_yol_bilgisi()
    try:
        os.makedirs(yollar["dir"], exist_ok=True)
        for key in ("aciklama", "baslik", "platform", "zamanlama", "hesap"):
            path = yollar.get(key, "")
            if path:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if not os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("")

        # kaynak_secim.txt sadece açıkça istenirse session_state'e yüklenir.
        # Aksi halde dialog açıkken her rerun'da kayıtlı değer tekrar okunup
        # kullanıcının ekranda yeni seçtiği kaynak geri ezilebiliyor.
        # Bu da Video / Toplu Video Montaj / Video Montaj geçişlerinde
        # sürekli rerun-blink döngüsü oluşturuyor.
        if sync_source_selection:
            kaynak_secim_path = yollar.get("kaynak_secim", "")
            if kaynak_secim_path and os.path.exists(kaynak_secim_path):
                try:
                    with open(kaynak_secim_path, "r", encoding="utf-8") as f:
                        kayitli_secim = _sm_normalize_kaynak_secim(f.read().strip())
                    if st.session_state.get("sm_video_kaynak_secim") != kayitli_secim:
                        st.session_state["sm_video_kaynak_secim"] = kayitli_secim
                except Exception:
                    pass

        # video_kaynak.txt: seçili kaynağa göre uygun klasörü yaz
        video_kaynak_path = yollar.get("video_kaynak", "")
        if video_kaynak_path:
            kaynak_secim = _sm_normalize_kaynak_secim(st.session_state.get("sm_video_kaynak_secim", "Link"))
            if kaynak_secim == "🎬 Toplu Video Montaj":
                video_dir = (st.session_state.settings.get("toplu_video_output_dir") or "").strip()
                if not video_dir:
                    video_dir = r"C:\Users\User\Desktop\Otomasyon\Video\Toplu Montaj"
            elif kaynak_secim == "🖼️ Görsel Oluştur":
                video_dir = (st.session_state.settings.get("video_output_dir") or "").strip()
                if not video_dir:
                    video_dir = r"C:\Users\User\Desktop\Otomasyon\Video\Video"
            elif kaynak_secim == "🎞️ Video Ekle":
                video_dir = (st.session_state.settings.get("added_video_dir") or "").strip()
                if not video_dir:
                    video_dir = r"C:\Users\User\Desktop\Otomasyon\Eklenen Video"
            elif kaynak_secim == "🎞️ Video Montaj":
                video_dir = (st.session_state.settings.get("video_montaj_output_dir") or "").strip()
                if not video_dir:
                    video_dir = r"C:\Users\User\Desktop\Otomasyon\Video\Montaj"
            elif kaynak_secim == "Link":
                video_dir = (st.session_state.settings.get("download_dir") or "").strip()
                if not video_dir:
                    video_dir = r"C:\Users\User\Desktop\Otomasyon\İndirilen Video"
            else:
                video_dir = (st.session_state.settings.get("sosyal_medya_video_dir") or "").strip()
                if not video_dir:
                    video_dir = r"C:\Users\User\Desktop\Otomasyon\Video\Video"
            os.makedirs(os.path.dirname(video_kaynak_path), exist_ok=True)
            with open(video_kaynak_path, "w", encoding="utf-8") as f:
                f.write(video_dir)
    except Exception:
        pass
    return yollar



def sosyal_medya_platform_metnini_coz(raw: str) -> dict:
    out = {"youtube": False, "tiktok": False, "instagram": False}
    selected = True  # Varsayılan: seçili
    for line in str(raw or "").splitlines():
        low = line.strip().lower()
        if low.startswith(("seçili:", "secili:", "selected:")):
            val = line.split(":", 1)[1].strip().lower()
            selected = val in ("evet", "yes", "true", "1", "+", "açık", "acik", "on")
        elif "youtube" in low:
            out["youtube"] = "+" in line
        elif "tiktok" in low:
            out["tiktok"] = "+" in line
        elif "instagram" in low:
            out["instagram"] = "+" in line
    out["_selected"] = selected
    return out


def sosyal_medya_platform_secimlerini_oku() -> dict:
    yollar = sosyal_medya_yol_bilgisi()
    raw = sosyal_medya_read_text(yollar["platform"], "")
    return sosyal_medya_platform_metnini_coz(raw)


def sosyal_medya_platform_secimlerini_yaz(secimler: dict, path: str | None = None) -> bool:
    lines = [
        f"Youtube {'+' if secimler.get('youtube') else '-'}",
        f"Tiktok {'+' if secimler.get('tiktok') else '-'}",
        f"Instagram {'+' if secimler.get('instagram') else '-'}",
    ]
    hedef = path or sosyal_medya_yol_bilgisi()["platform"]
    return sosyal_medya_write_text(hedef, "\n".join(lines))


def sosyal_medya_saat_12_to_24(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    match_24 = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", raw)
    if match_24:
        saat = int(match_24.group(1))
        dakika = int(match_24.group(2))
        return f"{saat:02d}:{dakika:02d}"

    match_12 = re.fullmatch(r"(1[0-2]|0?[1-9]):([0-5]\d)\s*([AaPp][Mm])", raw)
    if not match_12:
        return raw

    saat = int(match_12.group(1))
    dakika = int(match_12.group(2))
    meridiem = match_12.group(3).upper()
    if meridiem == "AM":
        if saat == 12:
            saat = 0
    else:
        if saat != 12:
            saat += 12
    return f"{saat:02d}:{dakika:02d}"


def sosyal_medya_saat_24_to_12(value: str) -> tuple[bool, str]:
    raw = str(value or "").strip()
    if not raw:
        return True, ""

    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", raw)
    if not match:
        return False, ""

    saat = int(match.group(1))
    dakika = int(match.group(2))
    meridiem = "AM" if saat < 12 else "PM"
    saat_12 = saat % 12
    if saat_12 == 0:
        saat_12 = 12
    return True, f"{saat_12}:{dakika:02d} {meridiem}"


_SM_PUBLISH_NOW_MARKER = "__HEMEN_PAYLAS__"


def sosyal_medya_publish_mode_normalize(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw in {
        "hemen paylaş", "hemen paylas", "şimdi paylaş", "simdi paylaş", "simdi paylas", "şimdi paylas",
        "hemen", "simdi", "şimdi", "now", "publish_now", "publish-now", "immediate", "direct",
        _SM_PUBLISH_NOW_MARKER.lower(), "hemen_paylas", "simdi_paylas"
    }:
        return "publish_now"
    return "schedule"


def sosyal_medya_publish_mode_from_schedule_raw(raw_text: str) -> str:
    raw = str(raw_text or "").strip()
    if not raw:
        return "schedule"
    return sosyal_medya_publish_mode_normalize(raw)


def sosyal_medya_zamanlama_metnini_coz(raw_text: str) -> tuple[str, str]:
    raw = str(raw_text or "").strip()
    if not raw:
        return "", ""
    if sosyal_medya_publish_mode_from_schedule_raw(raw) == "publish_now":
        return "", ""
    if "," in raw:
        gun, saat = raw.split(",", 1)
        return gun.strip(), sosyal_medya_saat_12_to_24(saat.strip())
    return "", sosyal_medya_saat_12_to_24(raw.strip())


def sosyal_medya_zamanlama_oku() -> tuple[str, str]:
    return sosyal_medya_zamanlama_metnini_coz(sosyal_medya_read_text(sosyal_medya_yol_bilgisi()["zamanlama"], ""))


def sosyal_medya_parse_numbered_blocks(raw_text: str) -> dict[int, str]:
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


def sosyal_medya_link_numaralari() -> set[int]:
    links_file = (st.session_state.settings.get("links_file") or "").strip()
    if not links_file or not os.path.exists(links_file):
        return set()
    try:
        with open(links_file, "r", encoding="utf-8") as f:
            link_sayisi = len([l for l in f.read().splitlines() if l.strip()])
        return set(range(1, link_sayisi + 1))
    except Exception:
        return set()


def sosyal_medya_indirilen_video_numaralari() -> set[int]:
    return {int(item.get("no")) for item in _list_download_video_entries() if str(item.get("no", "")).isdigit()}


def sosyal_medya_link_kaynak_haritasi() -> dict[int, str]:
    """Link akışında hangi numaranın link, hangisinin indirilen video olduğunu döndürür.

    - Link eklendiyse ama henüz indirilmediyse → "Link"
    - İndirme tamamlandıysa aynı sıra numarası → "İndirilen Video"

    Böylece Link akışı, Video akışıyla karışmadan aynı numaralar üzerinden devam eder.
    """
    kaynak_map = {int(no): "Link" for no in sosyal_medya_link_numaralari()}
    for no in sosyal_medya_indirilen_video_numaralari():
        kaynak_map[int(no)] = "İndirilen Video"
    return dict(sorted(kaynak_map.items()))


def sosyal_medya_video_numaralari() -> set[int]:
    video_root = (st.session_state.settings.get("sosyal_medya_video_dir") or st.session_state.settings.get("video_output_dir") or "").strip()
    if not video_root or not os.path.isdir(video_root):
        return set()

    valid_ext = (".mp4", ".mov", ".avi", ".mkv", ".webm")
    nums = set()
    try:
        entries = sorted(os.listdir(video_root), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", x)])
    except Exception:
        return set()

    subdirs = [e for e in entries if os.path.isdir(os.path.join(video_root, e))]
    if subdirs:
        for idx, name in enumerate(subdirs, start=1):
            m = re.search(r"(\d+)\s*$", name)
            nums.add(int(m.group(1)) if m else idx)
        return nums

    file_list = [e for e in entries if os.path.isfile(os.path.join(video_root, e)) and e.lower().endswith(valid_ext)]
    for idx, name in enumerate(file_list, start=1):
        m = re.search(r"(\d+)\s*$", os.path.splitext(name)[0])
        nums.add(int(m.group(1)) if m else idx)
    return nums


def _sm_klasorden_video_numaralari(video_root: str) -> set[int]:
    """Belirtilen klasördeki video dosyalarının numaralarını döndürür."""
    if not video_root or not os.path.isdir(video_root):
        return set()
    valid_ext = (".mp4", ".mov", ".avi", ".mkv", ".webm")
    nums = set()
    try:
        entries = sorted(os.listdir(video_root), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", x)])
    except Exception:
        return set()
    subdirs = [e for e in entries if os.path.isdir(os.path.join(video_root, e))]
    if subdirs:
        for idx, name in enumerate(subdirs, start=1):
            m = re.search(r"(\d+)\s*$", name)
            nums.add(int(m.group(1)) if m else idx)
        return nums
    file_list = [e for e in entries if os.path.isfile(os.path.join(video_root, e)) and e.lower().endswith(valid_ext)]
    for idx, name in enumerate(file_list, start=1):
        m = re.search(r"(\d+)\s*$", os.path.splitext(name)[0])
        nums.add(int(m.group(1)) if m else idx)
    return nums


def sosyal_medya_eklenen_video_numaralari() -> set[int]:
    return {int(item.get("no")) for item in _list_added_video_entries() if str(item.get("no", "")).isdigit()}


def sosyal_medya_toplu_video_numaralari() -> set[int]:
    """Toplu Video Montaj çıktı klasöründeki mevcut videolardan veya kaydedilmiş preset'ten üretilecek video numaralarını döndürür."""
    toplu_dir = (st.session_state.settings.get("toplu_video_output_dir") or "").strip()
    # Önce mevcut videoları kontrol et
    if toplu_dir:
        nums = _sm_klasorden_video_numaralari(toplu_dir)
        if nums:
            return nums
    # Klasörde video yoksa → preset'ten hesapla
    try:
        preset_path = os.path.join(CONTROL_DIR, "toplu_video_preset.json")
        if os.path.exists(preset_path):
            with open(preset_path, "r", encoding="utf-8") as fp:
                preset = json.load(fp)
            if isinstance(preset, dict) and preset:
                source_mode = _normalize_toplu_video_source_mode(preset.get("source_mode") or "Mevcut Videolar")
                if source_mode == "Eklenen Video":
                    toplam_kaynak = _count_added_videos()
                elif source_mode == "Görsel Oluştur":
                    toplam_kaynak = len(_list_saved_gorsel_motion_prompt_entries())
                else:
                    links_file = (st.session_state.settings.get("links_file") or "").strip()
                    toplam_kaynak = 0
                    if links_file and os.path.exists(links_file):
                        try:
                            with open(links_file, "r", encoding="utf-8") as lf:
                                toplam_kaynak = len([l for l in lf.read().splitlines() if l.strip()])
                        except Exception:
                            pass
                if toplam_kaynak >= 2:
                    kaynak_secim = (preset.get("source_selection_text") or "T").strip().upper()
                    if kaynak_secim == "T":
                        efektif_kaynak_sayisi = toplam_kaynak
                    else:
                        parcalar = [p.strip() for p in re.split(r'[\s,;]+', kaynak_secim) if p.strip() and p.strip().isdigit()]
                        efektif_kaynak_sayisi = len(parcalar) if parcalar else toplam_kaynak
                    efektif_kaynak_sayisi = max(2, min(efektif_kaynak_sayisi, 20))
                    secim_metni = (preset.get("selection_text") or "T").strip()
                    try:
                        uretilecek = _toplu_video_hesapla_uretilecek_video_sayisi(efektif_kaynak_sayisi, secim_metni)
                        if uretilecek and uretilecek > 0:
                            return set(range(1, uretilecek + 1))
                    except Exception:
                        pass
    except Exception:
        pass
    return set()


def sosyal_medya_video_montaj_numaralari() -> set[int]:
    """Video Montaj çıktı klasöründeki mevcut videoların numaralarını döndürür.
    Klasörde video yoksa, kaydedilmiş preset üzerinden üretilecek 1 adet video numarası döndürülür."""
    montaj_dir = (st.session_state.settings.get("video_montaj_output_dir") or "").strip()
    if montaj_dir:
        nums = _sm_klasorden_video_numaralari(montaj_dir)
        if nums:
            return nums
    # Klasörde video yoksa preset'ten hesapla
    try:
        preset_path = os.path.join(CONTROL_DIR, "video_montaj_preset.json")
        if os.path.exists(preset_path):
            with open(preset_path, "r", encoding="utf-8") as fp:
                preset = json.load(fp)
            if isinstance(preset, dict) and preset:
                return {1}
    except Exception:
        pass
    return set()


def sosyal_medya_gorsel_olustur_numaralari() -> set[int]:
    """Görsel Oluştur hareketlendirme promptlarından üretilecek video numaralarını döndürür."""
    nums = set()
    try:
        for idx, entry in enumerate(_list_saved_gorsel_motion_prompt_entries(), start=1):
            try:
                prompt_no = int(entry.get("prompt_no") or idx)
            except Exception:
                prompt_no = idx
            if prompt_no > 0:
                nums.add(prompt_no)
    except Exception:
        return set()
    return nums


def sosyal_medya_konfig_oku() -> dict:
    yollar = sosyal_medya_ensure_files()
    baslik_raw = sosyal_medya_read_text(yollar["baslik"], "")
    aciklama_raw = sosyal_medya_read_text(yollar["aciklama"], "")
    platform_raw = sosyal_medya_read_text(yollar["platform"], "")
    zamanlama_raw = sosyal_medya_read_text(yollar["zamanlama"], "")

    baslik_blocks = sosyal_medya_parse_numbered_blocks(baslik_raw)
    aciklama_blocks = sosyal_medya_parse_numbered_blocks(aciklama_raw)
    platform_blocks = sosyal_medya_parse_numbered_blocks(platform_raw)
    zamanlama_blocks = sosyal_medya_parse_numbered_blocks(zamanlama_raw)

    global_publish_mode = sosyal_medya_publish_mode_from_schedule_raw(zamanlama_raw)
    global_gun, global_saat = sosyal_medya_zamanlama_metnini_coz(zamanlama_raw)
    _global_platform_parsed = sosyal_medya_platform_metnini_coz(platform_raw if not platform_blocks else "")
    _global_platform_parsed.pop("_selected", None)  # global modda selected kullanılmaz
    global_cfg = {
        "baslik": baslik_raw if not baslik_blocks else "",
        "aciklama": aciklama_raw if not aciklama_blocks else "",
        "secimler": _global_platform_parsed,
        "publish_mode": global_publish_mode if not zamanlama_blocks else "schedule",
        "gun": global_gun if not zamanlama_blocks else "",
        "saat": global_saat if not zamanlama_blocks else "",
    }

    if not any([baslik_blocks, aciklama_blocks, platform_blocks, zamanlama_blocks]):
        return {"mode": "global", "global": global_cfg, "items": {}}

    nums = set()
    nums.update(baslik_blocks.keys())
    nums.update(aciklama_blocks.keys())
    nums.update(platform_blocks.keys())
    nums.update(zamanlama_blocks.keys())

    items = {}
    for no in sorted(nums):
        raw_schedule = zamanlama_blocks.get(no, "")
        gun_i, saat_i = sosyal_medya_zamanlama_metnini_coz(raw_schedule)
        _platform_parsed = sosyal_medya_platform_metnini_coz(platform_blocks.get(no, ""))
        _item_selected = _platform_parsed.pop("_selected", True)
        items[no] = {
            "baslik": baslik_blocks.get(no, ""),
            "aciklama": aciklama_blocks.get(no, ""),
            "secimler": _platform_parsed,
            "publish_mode": sosyal_medya_publish_mode_from_schedule_raw(raw_schedule),
            "gun": gun_i,
            "saat": saat_i,
            "selected": _item_selected,
        }

    return {"mode": "per_item", "global": global_cfg, "items": items}


def sosyal_medya_item_dolu_mu(item_cfg: dict) -> bool:
    cfg = dict(item_cfg or {})
    if str(cfg.get("baslik", "") or "").strip():
        return True
    if str(cfg.get("aciklama", "") or "").strip():
        return True
    if sosyal_medya_publish_mode_normalize(cfg.get("publish_mode")) == "publish_now":
        return True
    if str(cfg.get("gun", "") or "").strip():
        return True
    if str(cfg.get("saat", "") or "").strip():
        return True
    secimler = dict(cfg.get("secimler") or {})
    return any(bool(secimler.get(k)) for k in ("youtube", "tiktok", "instagram"))


def sosyal_medya_build_numbered_text(items: dict, field_name: str) -> str:
    blocks = []
    for no in sorted(int(k) for k in (items or {}).keys()):
        cfg = dict((items or {}).get(no) or {})
        if field_name == "platform":
            value = "\n".join([
                f"Youtube {'+' if cfg.get('secimler', {}).get('youtube') else '-'}",
                f"Tiktok {'+' if cfg.get('secimler', {}).get('tiktok') else '-'}",
                f"Instagram {'+' if cfg.get('secimler', {}).get('instagram') else '-'}",
            ]).strip()
        elif field_name == "zamanlama":
            publish_mode = sosyal_medya_publish_mode_normalize(cfg.get("publish_mode"))
            gun_text = str(cfg.get("gun", "") or "").strip()
            saat_text = str(cfg.get("saat", "") or "").strip()
            if publish_mode == "publish_now":
                value = _SM_PUBLISH_NOW_MARKER
            else:
                kayit_saat = ""
                if saat_text:
                    ok_saat, kayit_saat = sosyal_medya_saat_24_to_12(saat_text)
                    if not ok_saat:
                        raise ValueError(f"Video {no} için saat formatı geçersiz")
                value = ",".join([x for x in [gun_text, kayit_saat] if x]).strip(",")
        else:
            value = str(cfg.get(field_name, "") or "").strip()
        # Seçili bilgisini sadece platform dosyasına ekle (tek yerde tutmak yeterli)
        if field_name == "platform":
            sel = "Evet" if cfg.get("selected", True) else "Hayır"
            value = f"Seçili: {sel}\n{value}"
        blocks.append(f"### Video {no}\n{value}".rstrip())
    return "\n\n".join(blocks).strip()


def sosyal_medya_kaydet(aciklama: str, baslik: str, secimler: dict, gun: str, saat: str, publish_mode: str = "schedule") -> bool:
    yollar = sosyal_medya_ensure_files()
    publish_mode = sosyal_medya_publish_mode_normalize(publish_mode)
    gun_text = str(gun or "").strip()
    saat_text = str(saat or "").strip()

    if publish_mode == "publish_now":
        zamanlama = _SM_PUBLISH_NOW_MARKER
    else:
        if saat_text:
            ok_saat, kayit_saat = sosyal_medya_saat_24_to_12(saat_text)
            if not ok_saat:
                st.session_state["sm_error_notice"] = "Saat formatı geçersiz. Lütfen 24 saat formatında HH:MM girin. Örnek: 20:00"
                return False
        else:
            kayit_saat = ""
        zamanlama = ",".join([x for x in [gun_text, kayit_saat] if x])

    st.session_state.pop("sm_error_notice", None)
    ok_list = [
        sosyal_medya_write_text(yollar["aciklama"], aciklama),
        sosyal_medya_write_text(yollar["baslik"], baslik),
        sosyal_medya_platform_secimlerini_yaz(secimler, yollar["platform"]),
        sosyal_medya_write_text(yollar["zamanlama"], zamanlama),
    ]
    if all(ok_list):
        log("[OK] Sosyal medya paylaşım dosyaları kaydedildi.")
        return True
    return False


def sosyal_medya_kaydet_per_item(item_payload: dict) -> bool:
    yollar = sosyal_medya_ensure_files()
    temiz = {}
    for raw_no, cfg in (item_payload or {}).items():
        no = int(raw_no)
        data = dict(cfg or {})
        publish_mode = sosyal_medya_publish_mode_normalize(data.get("publish_mode"))
        saat_text = str(data.get("saat", "") or "").strip()
        if publish_mode != "publish_now" and saat_text:
            ok_saat, _ = sosyal_medya_saat_24_to_12(saat_text)
            if not ok_saat:
                st.session_state["sm_error_notice"] = f"Video {no} için saat formatı geçersiz. Lütfen 24 saat formatında HH:MM girin."
                return False
        temiz[no] = {
            "baslik": str(data.get("baslik", "") or "").strip(),
            "aciklama": str(data.get("aciklama", "") or "").strip(),
            "secimler": dict(data.get("secimler") or {}),
            "publish_mode": publish_mode,
            "gun": "" if publish_mode == "publish_now" else str(data.get("gun", "") or "").strip(),
            "saat": "" if publish_mode == "publish_now" else saat_text,
            "selected": bool(data.get("selected", True)),
        }

    st.session_state.pop("sm_error_notice", None)
    try:
        baslik_text = sosyal_medya_build_numbered_text(temiz, "baslik")
        aciklama_text = sosyal_medya_build_numbered_text(temiz, "aciklama")
        platform_text = sosyal_medya_build_numbered_text(temiz, "platform")
        zamanlama_text = sosyal_medya_build_numbered_text(temiz, "zamanlama")
    except ValueError as exc:
        st.session_state["sm_error_notice"] = str(exc)
        return False

    ok_list = [
        sosyal_medya_write_text(yollar["baslik"], baslik_text),
        sosyal_medya_write_text(yollar["aciklama"], aciklama_text),
        sosyal_medya_write_text(yollar["platform"], platform_text),
        sosyal_medya_write_text(yollar["zamanlama"], zamanlama_text),
    ]
    # Kaynak seçimini de kaydet
    kaynak_secim_path = yollar.get("kaynak_secim", "")
    if kaynak_secim_path:
        secim = _sm_normalize_kaynak_secim(st.session_state.get("sm_video_kaynak_secim", "Link"))
        sosyal_medya_write_text(kaynak_secim_path, secim)
    if all(ok_list):
        log("[OK] Sosyal medya paylaşım dosyaları video/link bazlı kaydedildi.")
        return True
    return False

def _sosyal_medya_hesap_satirini_coz(line: str):
    """Hesap satırını parse eder.
    Yeni format: API Token: xxx | Seçili: Evet/Hayır | Ad: HesapAdı
    Eski format: sadece API Token veya email,password (geriye uyumluluk)
    """
    raw = str(line or "").strip()
    if not raw:
        return None
    low = raw.casefold()

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

    # 'API Token: xxx' formatı (eski — geriye uyumluluk, varsayılan seçili)
    if low.startswith(("api token:", "token:", "api_token:", "buffer_token:")):
        token_value = raw.split(":", 1)[1].strip()
        if token_value:
            return {"token": token_value, "email": "", "password": "", "selected": True}
        return None
    # Virgül yoksa — tek başına token
    if "," not in raw:
        if len(raw) >= 20:  # Token genellikle uzundur
            return {"token": raw, "email": "", "password": "", "selected": True}
        return None
    # Eski format: email,password
    email, password = raw.split(",", 1)
    email = email.strip()
    password = password.strip()
    if not email or not password:
        return None
    return {"email": email, "password": password, "token": "", "selected": True}


def sosyal_medya_hesap_konfig_oku() -> dict:
    yollar = sosyal_medya_ensure_files()
    raw = sosyal_medya_read_text(yollar.get("hesap", ""), "")
    cfg = {"mode": "single", "loop_accounts": False, "accounts": [], "raw": raw}
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
        parsed = _sosyal_medya_hesap_satirini_coz(line)
        if parsed:
            accounts.append(parsed)

    if not accounts:
        legacy = _sosyal_medya_hesap_satirini_coz(raw)
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


def sosyal_medya_hesap_konfig_kaydet(mode: str, accounts: list, loop_accounts: bool = False) -> bool:
    """Hesap ayarlarını dosyaya kaydeder.
    Yeni format: API Token: xxx | Seçili: Evet/Hayır | Ad: HesapAdı
    Eski format: email,password (geriye uyumluluk)
    """
    yollar = sosyal_medya_ensure_files()
    temiz_hesaplar = []
    for item in (accounts or []):
        token = str((item or {}).get("token", "") or "").strip()
        email = str((item or {}).get("email", "") or "").strip()
        password = str((item or {}).get("password", "") or "").strip()
        selected = bool((item or {}).get("selected", True))
        if token:
            temiz_hesaplar.append({"token": token, "email": email, "password": "", "selected": selected})
        elif email and password:
            temiz_hesaplar.append({"token": "", "email": email, "password": password, "selected": selected})

    parts = [f"Hesap Modu: {'Toplu Hesap' if str(mode) == 'bulk' else 'Tek Hesap'}"]
    parts.append(f"Hesap Döngü: {'Açık' if bool(loop_accounts) else 'Kapalı'}")
    parts.append("Hesaplar:")
    for item in temiz_hesaplar:
        secili_str = "Evet" if item.get("selected", True) else "Hayır"
        if item.get("token"):
            line_parts = [f"API Token: {item['token']}", f"Seçili: {secili_str}"]
            if item.get("email"):
                line_parts.append(f"Ad: {item['email']}")
            parts.append(" | ".join(line_parts))
        elif item.get("email") and item.get("password"):
            parts.append(f"{item['email']},{item['password']}")
    ok = sosyal_medya_write_text(yollar.get("hesap", ""), "\n".join(parts).strip())
    if ok:
        log("[OK] Sosyal medya hesap ayarları kaydedildi.")
    return ok


def sosyal_medya_temizle(clear_legacy: bool = True, preserve_accounts: bool = True) -> bool:
    yollar = sosyal_medya_ensure_files()
    ok_list = []
    for key in ("aciklama", "baslik", "platform", "zamanlama", "video_kaynak", "kaynak_secim"):
        hedef = yollar.get(key, "")
        if hedef:
            ok_list.append(sosyal_medya_write_text(hedef, ""))

    if not preserve_accounts and yollar.get("hesap"):
        ok_list.append(sosyal_medya_write_text(yollar.get("hesap", ""), ""))

    if clear_legacy:
        legacy_candidates = [
            os.path.join(yollar.get("dir", ""), "ozel_paylasim_ayarlari.json"),
            os.path.join(yollar.get("dir", ""), "özel_paylasim_ayarlari.json"),
        ]
        for legacy_path in legacy_candidates:
            try:
                if legacy_path and os.path.exists(legacy_path):
                    os.remove(legacy_path)
                    log(f"[INFO] Eski sosyal medya ayar dosyası silindi: {os.path.basename(legacy_path)}")
            except Exception as e:
                log(f"[WARN] Eski sosyal medya ayar dosyası silinemedi: {e}")
                ok_list.append(False)

    if not ok_list or all(ok_list):
        log("[OK] Sosyal medya paylaşım planı temizlendi.")
        return True
    return False


def cleanup_social_media_state_files(clear_saved_plan: bool = False, preserve_accounts: bool = True):
    cleaned = []
    try:
        for fname in ("SOCIAL_MEDIA_STATE.json", "SOCIAL_MEDIA_DONE.json", "SOCIAL_MEDIA_FAILED.json"):
            fpath = os.path.join(CONTROL_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
                cleaned.append(fname)
    except Exception as e:
        log(f"[WARN] Sosyal medya state dosyaları temizlenemedi: {e}")

    if clear_saved_plan:
        try:
            if sosyal_medya_temizle(clear_legacy=True, preserve_accounts=preserve_accounts):
                cleaned.append("social_media_saved_plan")
        except Exception as e:
            log(f"[WARN] Sosyal medya planı temizlenemedi: {e}")

    if cleaned:
        log(f"[OK] Sosyal medya temizliği tamamlandı: {', '.join(cleaned)}")
    return cleaned


def _sm_apply_rows_to_widget_state(rows: list | None = None):
    hazir = list(rows or [])
    if not hazir:
        hazir = [{"token": "", "email": "", "password": "", "selected": False}]

    onceki_sayi = int(st.session_state.get("sm_account_widget_count", 0) or 0)
    st.session_state["sm_accounts_rows"] = hazir

    for idx, row in enumerate(hazir, start=1):
        mevcut = dict(row or {})
        st.session_state[f"sm_account_selected_{idx}"] = bool(mevcut.get("selected", False))
        st.session_state[f"sm_account_token_{idx}"] = str(mevcut.get("token", "") or "")
        st.session_state[f"sm_account_email_{idx}"] = str(mevcut.get("email", "") or "")

    for idx in range(len(hazir) + 1, onceki_sayi + 1):
        st.session_state.pop(f"sm_account_selected_{idx}", None)
        st.session_state.pop(f"sm_account_token_{idx}", None)
        st.session_state.pop(f"sm_account_email_{idx}", None)

    st.session_state["sm_account_widget_count"] = len(hazir)


def _sm_apply_pending_account_ui_state():
    pending = st.session_state.pop("sm_pending_account_ui", None)
    if not isinstance(pending, dict):
        return

    if "rows" in pending:
        _sm_apply_rows_to_widget_state(pending.get("rows") or [])
    if "hesap_modu" in pending:
        st.session_state["sm_hesap_modu"] = pending.get("hesap_modu") or "Tek Hesap"
    if "hesap_dongu" in pending:
        st.session_state["sm_hesap_dongu"] = bool(pending.get("hesap_dongu", False))
    if "select_all" in pending:
        st.session_state["sm_select_all_accounts"] = bool(pending.get("select_all", False))
        st.session_state["sm_select_all_accounts_prev"] = bool(pending.get("select_all", False))
    if "single_token" in pending:
        st.session_state["sm_single_token"] = str(pending.get("single_token", "") or "")


def _sm_schedule_account_ui_reset(*, rows=None, hesap_modu=None, hesap_dongu=None, select_all=None, single_token=None, single_email=None, single_password=None):
    pending = {}
    if rows is not None:
        pending["rows"] = list(rows or [])
    if hesap_modu is not None:
        pending["hesap_modu"] = hesap_modu
    if hesap_dongu is not None:
        pending["hesap_dongu"] = bool(hesap_dongu)
    if select_all is not None:
        pending["select_all"] = bool(select_all)
    if single_token is not None:
        pending["single_token"] = str(single_token or "")
    if single_email is not None:
        pending["single_email"] = str(single_email or "")
    if single_password is not None:
        pending["single_password"] = str(single_password or "")
    st.session_state["sm_pending_account_ui"] = pending


def _sm_apply_pending_form_ui_state():
    pending = st.session_state.pop("sm_pending_form_ui", None)
    if not isinstance(pending, dict):
        return

    if pending.get("clear_item_keys"):
        for key in list(st.session_state.keys()):
            if str(key).startswith("sm_item_"):
                st.session_state.pop(key, None)

    if "ayar_modu" in pending:
        st.session_state["sm_ayar_modu"] = pending.get("ayar_modu") or "Genel"
    if "video_kaynak_secim" in pending:
        st.session_state["sm_video_kaynak_secim"] = _sm_normalize_kaynak_secim(pending.get("video_kaynak_secim") or "Link")
    if "kaynak_radio" in pending:
        st.session_state["sm_kaynak_radio"] = _sm_normalize_kaynak_secim(pending.get("kaynak_radio") or "Link")
    if "baslik" in pending:
        st.session_state["sm_baslik_txt"] = str(pending.get("baslik", "") or "")
    if "aciklama" in pending:
        st.session_state["sm_aciklama_txt"] = str(pending.get("aciklama", "") or "")
    if "platform_secimler" in pending:
        secimler = dict(pending.get("platform_secimler") or {})
        st.session_state["sm_platform_youtube"] = bool(secimler.get("youtube", False))
        st.session_state["sm_platform_tiktok"] = bool(secimler.get("tiktok", False))
        st.session_state["sm_platform_instagram"] = bool(secimler.get("instagram", False))
    if "publish_mode" in pending:
        st.session_state["sm_publish_mode"] = "Hemen Paylaş" if sosyal_medya_publish_mode_normalize(pending.get("publish_mode")) == "publish_now" else "Zamanla"
    if "gun" in pending:
        st.session_state["sm_zaman_gun"] = str(pending.get("gun", "") or "")
    if "saat" in pending:
        st.session_state["sm_zaman_saat"] = str(pending.get("saat", "") or "")
    if pending.get("drop_loaded"):
        st.session_state.pop("sm_video_kaynak_secim_loaded", None)


def _sm_schedule_form_ui_reset(*, ayar_modu=None, video_kaynak_secim=None, kaynak_radio=None, baslik=None, aciklama=None, platform_secimler=None, publish_mode=None, gun=None, saat=None, clear_item_keys=False, drop_loaded=False):
    pending = {}
    if ayar_modu is not None:
        pending["ayar_modu"] = ayar_modu
    if video_kaynak_secim is not None:
        pending["video_kaynak_secim"] = video_kaynak_secim
    if kaynak_radio is not None:
        pending["kaynak_radio"] = kaynak_radio
    if baslik is not None:
        pending["baslik"] = baslik
    if aciklama is not None:
        pending["aciklama"] = aciklama
    if platform_secimler is not None:
        pending["platform_secimler"] = dict(platform_secimler or {})
    if publish_mode is not None:
        pending["publish_mode"] = publish_mode
    if gun is not None:
        pending["gun"] = gun
    if saat is not None:
        pending["saat"] = saat
    if clear_item_keys:
        pending["clear_item_keys"] = True
    if drop_loaded:
        pending["drop_loaded"] = True
    st.session_state["sm_pending_form_ui"] = pending


def _sm_accounts_state_init(force: bool = False):
    cfg = sosyal_medya_hesap_konfig_oku()
    cfg_rows = [{"token": x.get("token", ""), "email": x.get("email", ""), "password": x.get("password", ""), "selected": bool(x.get("selected", True))} for x in (cfg.get("accounts") or [])]
    current_rows = list(st.session_state.get("sm_accounts_rows", []) or [])

    def _rows_have_saved_account(rows: list | None) -> bool:
        for row in (rows or []):
            token = str((row or {}).get("token", "") or "").strip()
            email = str((row or {}).get("email", "") or "").strip()
            password = str((row or {}).get("password", "") or "").strip()
            if token or email or password:
                return True
        return False

    should_refresh_rows = force or "sm_accounts_rows" not in st.session_state
    if not should_refresh_rows:
        if (not _rows_have_saved_account(current_rows)) and _rows_have_saved_account(cfg_rows):
            should_refresh_rows = True

    if should_refresh_rows:
        _sm_apply_rows_to_widget_state(cfg_rows)
        current_rows = list(st.session_state.get("sm_accounts_rows", []) or [])
    else:
        # Dialog kapatılıp açıldığında widget key'leri yok edilir ama sm_accounts_rows
        # session_state'de kalır. Widget key'leri yoksa senkronize et.
        _needs_widget_sync = False
        for _wi in range(1, len(current_rows) + 1):
            if f"sm_account_token_{_wi}" not in st.session_state:
                _needs_widget_sync = True
                break
        if _needs_widget_sync:
            # Dosyada güncel veri varsa onu kullan, yoksa mevcut rows'u senkronize et
            if cfg_rows and _rows_have_saved_account(cfg_rows):
                _sm_apply_rows_to_widget_state(cfg_rows)
                current_rows = list(st.session_state.get("sm_accounts_rows", []) or [])
            elif _rows_have_saved_account(current_rows):
                _sm_apply_rows_to_widget_state(current_rows)

    should_refresh_mode = force or "sm_hesap_modu" not in st.session_state
    if not should_refresh_mode:
        if (not _rows_have_saved_account(current_rows)) and _rows_have_saved_account(cfg_rows):
            should_refresh_mode = True
    if should_refresh_mode:
        st.session_state["sm_hesap_modu"] = "Toplu Hesap" if cfg.get("mode") == "bulk" else "Tek Hesap"

    should_refresh_loop = force or "sm_hesap_dongu" not in st.session_state
    if not should_refresh_loop:
        if (not _rows_have_saved_account(current_rows)) and _rows_have_saved_account(cfg_rows):
            should_refresh_loop = True
    if should_refresh_loop:
        st.session_state["sm_hesap_dongu"] = bool(cfg.get("loop_accounts", False))

    if force or "sm_select_all_accounts" not in st.session_state:
        st.session_state["sm_select_all_accounts"] = False
    if force or "sm_select_all_accounts_prev" not in st.session_state:
        st.session_state["sm_select_all_accounts_prev"] = False
    if force or "sm_account_widget_count" not in st.session_state:
        st.session_state["sm_account_widget_count"] = len(st.session_state.get("sm_accounts_rows", []) or [])
    if force or "sm_last_hesap_mode_rendered" not in st.session_state:
        st.session_state["sm_last_hesap_mode_rendered"] = st.session_state.get("sm_hesap_modu", "Tek Hesap")

    ilk_hesap = dict((st.session_state.get("sm_accounts_rows") or [{}])[0] or {})
    should_refresh_single = force or "sm_single_token" not in st.session_state
    if not should_refresh_single:
        single_token = str(st.session_state.get("sm_single_token", "") or "").strip()
        first_token = str(ilk_hesap.get("token", "") or "").strip()
        if not single_token and first_token:
            should_refresh_single = True
    if should_refresh_single:
        st.session_state["sm_single_token"] = str(ilk_hesap.get("token", "") or "")

    _sm_apply_pending_account_ui_state()


def _sm_collect_accounts_from_rows() -> tuple[list, list]:
    rows = list(st.session_state.get("sm_accounts_rows", []) or [])
    temiz = []
    invalid = []
    for idx, row in enumerate(rows, start=1):
        token = str((row or {}).get("token", "") or "").strip()
        email = str((row or {}).get("email", "") or "").strip()
        password = str((row or {}).get("password", "") or "").strip()
        selected = bool((row or {}).get("selected", True))
        # Token varsa geçerli hesap
        if token:
            temiz.append({"token": token, "email": email, "password": "", "selected": selected})
            continue
        # Token yoksa boş satır kontrolü
        if not token and not email and not password:
            continue
        # Eski format: email + password gerekli
        if not token and (not email or not password):
            invalid.append(idx)
            continue
        temiz.append({"token": "", "email": email, "password": password, "selected": selected})
    return temiz, invalid


def _sm_delete_selected_accounts() -> int:
    rows = list(st.session_state.get("sm_accounts_rows", []) or [])
    kalan = [row for row in rows if not bool((row or {}).get("selected", False))]
    silinen = len(rows) - len(kalan)
    if not kalan:
        kalan = [{"token": "", "email": "", "password": "", "selected": False}]
    ilk = dict(kalan[0] if kalan else {"token": "", "email": "", "password": ""})
    _sm_schedule_account_ui_reset(
        rows=kalan,
        select_all=False,
        single_token=ilk.get("token", ""),
    )
    st.session_state["sm_accounts_rows"] = kalan
    st.session_state["sm_select_all_accounts_prev"] = False
    return silinen


def _is_safe_path(path: str) -> bool:
    try:
        return os.path.abspath(path).startswith(os.path.abspath(r"C:\Users\User\Desktop\Otomasyon"))
    except: return False

def _list_entries(dir_path: str):
    if not dir_path or not os.path.isdir(dir_path): return []
    out =[(n, os.path.join(dir_path, n), os.path.isdir(os.path.join(dir_path, n))) for n in os.listdir(dir_path)]
    out.sort(key=lambda x: (not x[2], x[0].lower())); return out

def _list_media_files_clean(dir_path: str):
    if not dir_path or not os.path.isdir(dir_path): return []
    out = []
    medyalar = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.jpg', '.jpeg', '.png', '.bmp', '.webp')
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.lower().endswith(medyalar):
                tam_yol = os.path.join(root, f)
                rel_yol = os.path.relpath(tam_yol, dir_path)
                parcalar = rel_yol.replace(os.sep, "/").split("/")
                isim = parcalar[0] if len(parcalar) > 1 else os.path.splitext(f)[0]
                if len(isim) > 40: isim = isim[:37] + "..."
                out.append((isim, tam_yol, False, root != dir_path))
    out.sort(key=lambda x: natural_sort_key(x[0]))
    
    ham = [e[0] for e in out]
    etiketler = []
    sayici = {}
    for item in out:
        e = item[0]
        if ham.count(e) > 1:
            sayici[e] = sayici.get(e, 0) + 1
            e = f"{e} ({sayici[e]})"
        etiketler.append((e, item[1], item[2]))
    return etiketler

def _delete_path(target_path: str):
    if not _is_safe_path(target_path): return False
    try:
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        elif os.path.exists(target_path):
            parent = os.path.dirname(target_path)
            os.remove(target_path)
            if parent and os.path.basename(parent).startswith(("Görsel ", "Video ", "Prompt ")):
                try:
                    if not os.listdir(parent): os.rmdir(parent)
                except: pass
        return True
    except: return False

def reset_txt_file(txt_path: str):
    if not _is_safe_path(txt_path): return False
    try:
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        with open(txt_path, "w", encoding="utf-8") as f: f.write("")
        return True
    except: return False


def clean_all_targets():
    s = st.session_state.settings

    def _safe_delete_children(folder_path: str):
        if not folder_path:
            return
        try:
            if os.path.isdir(folder_path):
                for name in os.listdir(folder_path):
                    full = os.path.join(folder_path, name)
                    try:
                        _delete_path(full)
                    except Exception as e:
                        log(f"[WARN] Silinemedi: {full} -> {e}")
        except Exception as e:
            log(f"[WARN] Klasör temizlenemedi: {folder_path} -> {e}")

    # Ana klasörler
    targets = [
        s.get("download_dir"),
        s.get("added_video_dir"),
        s.get("prompt_dir"),
        s.get("video_montaj_output_dir"),
        s.get("toplu_video_output_dir"),
        s.get("video_output_dir"),
        s.get("gorsel_analiz_dir"),
        s.get("klon_gorsel_dir"),
        s.get("gorsel_olustur_dir"),
        r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Prompt",
        r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Hareklendirme Prompt",
    ]

    for folder in targets:
        _safe_delete_children(folder)

    # Spesifik Dosyalar ve Klasörlerin temizliği (Görsellerin bırakıp içi boş olan prompt klasör kalıntılarını silmek için)
    _safe_delete_children(r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Prompt Oluşturma\temp_upload")

    # TXT / preset dosyaları
    txt_targets = [
        s.get("links_file"),
        s.get("video_prompt_links_file"),
        s.get("gorsel_duzelt_txt"),
        s.get("prompt_duzeltme_txt"),
        PROMPT_SOURCE_MODE_FILE,
        os.path.join(CONTROL_DIR, "video_montaj_preset.json"),
        os.path.join(CONTROL_DIR, "toplu_video_preset.json"),
        os.path.join(CONTROL_DIR, "prompt_input_selection.json"),
    ]

    for path in txt_targets:
        try:
            if path and os.path.exists(path):
                reset_txt_file(path)
        except Exception as e:
            log(f"[WARN] TXT sıfırlanamadı: {path} -> {e}")

    # Durum özetini temizle
    try:
        durum_ozeti_sifirla()
    except Exception:
        pass

    # Control dosyalarını temizle
    try:
        cleanup_state_files()
    except Exception:
        pass

    # Oturum verilerini sifirla (Görsel Oluşturma vb.)
    keys_to_del = [k for k in st.session_state.keys() if k.startswith(("go_gp", "go_gs", "go_vp", "go_vs", "go_vid"))]
    for k in keys_to_del:
        del st.session_state[k]
    st.session_state.go_gorsel_count = 1
    st.session_state.go_vid_count = 1

    log("[OK] Toplu temizlik tamamlandı.")

def save_youtube_link_config(payload: dict) -> str:
    """YouTube link toplama için geçici JSON yapılandırma dosyası oluşturur."""
    os.makedirs(CONTROL_DIR, exist_ok=True)
    config_path = os.path.join(CONTROL_DIR, f"youtube_link_config_{int(time.time() * 1000)}.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return config_path


def _video_montaj_sort_key(value: str):
    parts = re.split(r'(\d+)', str(value or ''))
    return [int(p) if p.isdigit() else p.casefold() for p in parts]


def _read_links_count() -> int:
    links_file = st.session_state.settings.get("links_file", "")
    if not links_file or not os.path.exists(links_file):
        return 0
    try:
        with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
            return len([ln for ln in f.read().splitlines() if ln.strip()])
    except Exception:
        return 0


def _list_video_montaj_assets():
    s = st.session_state.settings
    video_root = s.get("video_output_dir", "")
    klon_root = s.get("klon_video_dir", "")
    gorsel_root = s.get("video_montaj_gorsel_dir", "")
    link_count = _read_links_count()
    motion_prompt_entries = _list_saved_gorsel_motion_prompt_entries()

    normal_by_no = {}
    if video_root and os.path.isdir(video_root):
        for item in os.listdir(video_root):
            item_path = os.path.join(video_root, item)
            if not os.path.isdir(item_path):
                continue

            m = re.match(r'^Video\s+(\d+)$', item, re.IGNORECASE)
            if not m:
                continue

            video_no = int(m.group(1))
            media_files = []
            for fname in os.listdir(item_path):
                if fname.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                    media_files.append(os.path.join(item_path, fname))

            media_files.sort(key=lambda p: _video_montaj_sort_key(os.path.basename(p)))
            if media_files:
                normal_by_no[video_no] = {
                    "folder_name": item,
                    "path": media_files[0],
                    "exists": True,
                    "video_no": video_no,
                    "source_kind": "video_output",
                }

    download_by_no = {}
    for entry in _list_download_video_entries():
        try:
            video_no = int(entry.get("no") or 0)
        except Exception:
            video_no = 0
        if video_no <= 0:
            continue
        download_by_no[video_no] = {
            "folder_name": entry.get("folder_name") or f"Video {video_no}",
            "path": entry.get("video_path") or "",
            "exists": bool(entry.get("video_path")),
            "video_no": video_no,
            "source_kind": "download",
        }

    klon_items = []
    if klon_root and os.path.isdir(klon_root):
        for item in os.listdir(klon_root):
            item_path = os.path.join(klon_root, item)
            if not os.path.isdir(item_path):
                continue

            m = re.match(r'^Klon\s+Video\s+(\d+)$', item, re.IGNORECASE)
            if not m:
                continue

            clone_no = int(m.group(1))
            media_files = []
            for fname in os.listdir(item_path):
                if fname.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                    media_files.append(os.path.join(item_path, fname))

            media_files.sort(key=lambda p: _video_montaj_sort_key(os.path.basename(p)))
            if media_files:
                klon_items.append({
                    "folder_name": item,
                    "path": media_files[0],
                    "exists": True,
                    "clone_no": clone_no,
                })

    klon_items.sort(key=lambda x: x["clone_no"])

    all_videos = []
    display_no = 1

    for video_no in range(1, link_count + 1):
        if video_no in normal_by_no:
            entry = normal_by_no[video_no]
            all_videos.append({
                "token": str(display_no),
                "script_token": str(display_no - 1),
                "label": f"[{display_no}] Video {video_no}",
                "path": entry["path"],
                "exists": True,
                "expected": False,
                "video_no": video_no,
                "source_kind": entry.get("source_kind", "video_output"),
            })
        elif video_no in download_by_no:
            entry = download_by_no[video_no]
            all_videos.append({
                "token": str(display_no),
                "script_token": str(display_no - 1),
                "label": f"[{display_no}] İndirilen Video {video_no}",
                "path": entry["path"],
                "exists": True,
                "expected": False,
                "video_no": video_no,
                "source_kind": "download",
            })
        else:
            all_videos.append({
                "token": str(display_no),
                "script_token": str(display_no - 1),
                "label": f"[{display_no}] Link Video {video_no}",
                "path": "",
                "exists": False,
                "expected": True,
                "video_no": video_no,
                "source_kind": "link",
            })
        display_no += 1

    extra_video_nos = sorted(
        n for n in (set(normal_by_no.keys()) | set(download_by_no.keys()))
        if n > link_count
    )
    for video_no in extra_video_nos:
        entry = normal_by_no.get(video_no) or download_by_no.get(video_no)
        if not entry:
            continue
        label_prefix = "İndirilen Video" if entry.get("source_kind") == "download" else "Video"
        all_videos.append({
            "token": str(display_no),
            "script_token": str(display_no - 1),
            "label": f"[{display_no}] {label_prefix} {video_no}",
            "path": entry["path"],
            "exists": True,
            "expected": False,
            "video_no": video_no,
            "source_kind": entry.get("source_kind", "video_output"),
        })
        display_no += 1

    for entry in klon_items:
        all_videos.append({
            "token": str(display_no),
            "script_token": str(display_no - 1),
            "label": f"[{display_no}] Klon Video {entry['clone_no']}",
            "path": entry["path"],
            "exists": True,
            "expected": False,
            "clone_no": entry["clone_no"],
            "source_kind": "clone",
        })
        display_no += 1

    motion_videos = []
    for idx, entry in enumerate(motion_prompt_entries, start=1):
        try:
            prompt_no = int(entry.get("prompt_no") or idx)
        except Exception:
            prompt_no = idx
        actual_entry = normal_by_no.get(prompt_no)
        motion_videos.append({
            "token": str(idx),
            "script_token": str(idx - 1),
            "label": f"[{idx}] Görsel Hareketlendirme {prompt_no}",
            "path": (actual_entry or {}).get("path", ""),
            "exists": bool(actual_entry and actual_entry.get("path")),
            "expected": not bool(actual_entry and actual_entry.get("path")),
            "video_no": prompt_no,
            "prompt_no": prompt_no,
            "motion_prompt_path": entry.get("prompt_path", ""),
            "source_kind": "gorsel_motion",
        })

    all_images = []

    if gorsel_root and os.path.isdir(gorsel_root):
        image_files = []
        for fname in os.listdir(gorsel_root):
            if fname.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
                image_files.append(os.path.join(gorsel_root, fname))

        image_files.sort(key=lambda p: _video_montaj_sort_key(os.path.basename(p)))

        for idx, full_path in enumerate(image_files, start=1):
            token = f"G{idx}"
            all_images.append({
                "token": token,
                "label": f"[{token}] {os.path.basename(full_path)}",
                "path": full_path,
            })

    gorsel_olustur_images = []
    for idx, entry in enumerate(_list_gorsel_olustur_reference_image_entries(), start=1):
        full_path = (entry.get("path") or "").strip()
        if not full_path or not os.path.isfile(full_path):
            continue
        gorsel_no = entry.get("gorsel_no")
        if gorsel_no:
            label_text = f"Olusturulan Gorsel {gorsel_no} - {os.path.basename(full_path)}"
        else:
            label_text = f"Olusturulan Gorsel - {os.path.basename(full_path)}"
        token = f"G{idx}"
        gorsel_olustur_images.append({
            "token": token,
            "label": f"[{token}] {label_text}",
            "path": full_path,
        })

    return {
        "videos": all_videos,
        "gorsel_olustur_videos": motion_videos,
        "images": all_images,
        "gorsel_olustur_images": gorsel_olustur_images,
    }


def _build_existing_video_token_remap(video_items: list) -> dict:
    remap = {}
    next_token = 1
    for item in (video_items or []):
        token = str(item.get("token") or "").strip()
        path = (item.get("path") or "").strip()
        if not token or not item.get("exists") or not path or not os.path.isfile(path):
            continue
        remap[token] = str(next_token)
        next_token += 1
    return remap


def _remap_numeric_selection_text(text_value: str, token_remap: dict) -> str:
    raw = (text_value or "").strip()
    if not raw or not token_remap:
        return raw
    if raw.upper() == "T":
        return raw

    parts = [p.strip() for p in re.split(r'[\s,;]+', raw) if p.strip()]
    if not parts:
        return raw

    out = []
    for part in parts:
        upper = part.upper()
        if re.fullmatch(r'\d+', upper):
            mapped = token_remap.get(str(int(upper)))
            if mapped and mapped not in out:
                out.append(mapped)
        else:
            if upper not in out:
                out.append(upper)
    return ",".join(out) if out else "T"


def _prepare_mevcut_video_runner_dirs(video_items: list, temp_prefix: str = "video_montaj", force_copy: bool = False) -> tuple[str, str, dict]:
    existing_items = []
    for item in (video_items or []):
        path = (item.get("path") or "").strip()
        if not item.get("exists") or not path or not os.path.isfile(path):
            continue
        existing_items.append(item)

    token_remap = _build_existing_video_token_remap(video_items)
    has_download_source = any((item.get("source_kind") == "download") for item in existing_items)
    if not existing_items:
        return "", "", token_remap
    if not force_copy and not has_download_source:
        return "", "", token_remap

    temp_root = os.path.join(CONTROL_DIR, f"{temp_prefix}_sources_{int(time.time() * 1000)}")
    normal_root = os.path.join(temp_root, "video")
    clone_root = os.path.join(temp_root, "klon_video")
    os.makedirs(normal_root, exist_ok=True)
    os.makedirs(clone_root, exist_ok=True)

    normal_index = 1
    clone_index = 1
    copied_count = 0

    for item in existing_items:
        src_path = (item.get("path") or "").strip()
        if not src_path or not os.path.isfile(src_path):
            continue

        is_clone = item.get("source_kind") == "clone" or ("clone_no" in item)
        if is_clone:
            folder_name = f"Klon Video {clone_index}"
            target_root = clone_root
            clone_index += 1
        else:
            folder_name = f"Video {normal_index}"
            target_root = normal_root
            normal_index += 1

        dst_dir = os.path.join(target_root, folder_name)
        os.makedirs(dst_dir, exist_ok=True)
        dst_path = os.path.join(dst_dir, os.path.basename(src_path))
        try:
            shutil.copy2(src_path, dst_path)
            copied_count += 1
        except Exception as e:
            log(f"[WARN] Geçici montaj kaynağı hazırlanamadı: {src_path} -> {e}")

    if copied_count:
        if force_copy and not has_download_source:
            log(f"[INFO] Montaj kaynagi secime gore hazirlandi: {copied_count} dosya gecici kaynak klasorune kopyalandi.")
        else:
            log(f"[INFO] İndirilen videolar montaj kaynağına dahil edildi: {copied_count} dosya hazırlandı.")
    return normal_root, clone_root, token_remap


def _video_montaj_secim_metni_uret(secili_tokenler, muzik=False, cerceve=False, logo=False, video_overlay=False, ses_efekti=False, orijinal_ses=False, custom_text=''):
    custom_text = (custom_text or '').strip()
    if custom_text:
        parts = [p.strip() for p in re.split(r'[\s,]+', custom_text) if p.strip()]
        norm = []
        for p in parts:
            up = p.upper()
            if up in {"T", "M", "C", "L", "V", "S", "O"} or re.fullmatch(r'G\d+(?:_\d+)?', up):
                norm.append(up)
            else:
                norm.append(p)
        return ",".join(norm)

    temel = ",".join(secili_tokenler) if secili_tokenler else "T"
    ekler = []
    if muzik:
        ekler.append("M")
    if cerceve:
        ekler.append("C")
    if logo:
        ekler.append("L")
    if video_overlay:
        ekler.append("V")
    if ses_efekti:
        ekler.append("S")
    if orijinal_ses:
        ekler.append("O")

    if ekler:
        return temel + "," + ",".join(ekler)
    return temel


def _video_montaj_ui_to_script_selection(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "T"

    parts = [p.strip() for p in re.split(r'[\s,]+', raw) if p.strip()]
    if not parts:
        return "T"

    numeric_parts = [p for p in parts if re.fullmatch(r'\d+', p)]
    already_zero_based = any(p == "0" for p in numeric_parts)

    out = []
    for p in parts:
        up = p.upper()

        if up in {"T", "M", "C", "L", "V", "S", "O"}:
            out.append(up)
        elif re.fullmatch(r'G\d+(?:_\d+)?', up):
            out.append(up)
        elif re.fullmatch(r'\d+', p):
            n = int(p)
            if already_zero_based:
                out.append(str(n))
            else:
                out.append(str(max(0, n - 1)))
        else:
            out.append(p)

    return ",".join(out)


def _orijinal_ses_kaynak_sirasi_normalize(value: str) -> str:
    raw = (value or "").strip().upper()
    if not raw:
        return ""
    parts = [p.strip() for p in re.split(r'[\s,;]+', raw) if p.strip()]
    if not parts:
        return ""
    if any(p == "T" for p in parts):
        return "T"
    out = []
    for p in parts:
        if re.fullmatch(r'\d+', p):
            out.append(str(int(p)))
    return ",".join(out)


def _orijinal_ses_kaynak_sirasi_to_paths(text_value: str, video_items: list) -> list:
    token_to_path = {}
    tum_yollar = []
    for item in (video_items or []):
        token = str(item.get("token") or "").strip()
        path = (item.get("path") or "").strip()
        if not token or not path or not item.get("exists", True):
            continue
        token_to_path[token] = path
        tum_yollar.append(path)

    normalized = _orijinal_ses_kaynak_sirasi_normalize(text_value)
    if not normalized:
        return []
    if normalized == "T":
        return tum_yollar

    out = []
    for part in normalized.split(","):
        path = token_to_path.get(part)
        if path:
            out.append(path)
    return out


def _orijinal_ses_kaynak_sirasi_preview(text_value: str, video_items: list) -> list:
    token_to_label = {}
    tum_etiketler = []
    for item in (video_items or []):
        token = str(item.get("token") or "").strip()
        label = (item.get("label") or token).strip()
        if not token:
            continue
        temiz_label = re.sub(r'^\[(.*?)\]\s*', '', label).strip() or label
        token_to_label[token] = temiz_label
        tum_etiketler.append(temiz_label)

    normalized = _orijinal_ses_kaynak_sirasi_normalize(text_value)
    if not normalized:
        return []
    if normalized == "T":
        return tum_etiketler

    out = []
    for part in normalized.split(","):
        label = token_to_label.get(part)
        if label:
            out.append(label)
    return out

VIDEO_MONTAJ_PRESET_FILE = os.path.join(CONTROL_DIR, "video_montaj_preset.json")
VIDEO_MONTAJ_MUZIK_SES_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\muzik\ses_seviyesi.txt"
VIDEO_MONTAJ_SES_EFEKTI_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\ses efekti\ses_seviyesi.txt"
VIDEO_MONTAJ_BASLIK_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\başlık.txt"
VIDEO_MONTAJ_ORIJINAL_SES_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\orijinal_ses_seviyesi.txt"
VIDEO_MONTAJ_VIDEO_SES_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\video_ses_seviyesi.txt"
VIDEO_MONTAJ_ORIJINAL_SES_KAYNAKLARI_JSON = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\orijinal_ses_kaynaklari.json"
VIDEO_MONTAJ_MUZIK_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\muzik"
VIDEO_MONTAJ_CERCEVE_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\çerçeve"
VIDEO_MONTAJ_LOGO_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\logo"
VIDEO_MONTAJ_VIDEO_OVERLAY_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\video overlay"
VIDEO_MONTAJ_SES_EFEKTI_DIR = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\ses efekti"
VIDEO_MONTAJ_YEDEK_ROOT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\yedek"


def _vm_read_text_file(path: str, default: str = "") -> str:
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
    except Exception:
        pass
    return default


def _vm_write_text_file(path: str, value: str) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write((value or "").strip())
        return True
    except Exception as e:
        log(f"[ERROR] TXT yazılamadı: {path} -> {e}")
        return False


def _vm_normalize_percent_text(value: str, default_percent: int = 15) -> str:
    raw = str(value or "").strip().replace("%", "")
    if not raw:
        return str(default_percent)
    try:
        num = float(raw.replace(",", "."))
        if num <= 1:
            num = num * 100
        num = max(0, min(100, int(round(num))))
        return str(num)
    except Exception:
        return str(default_percent)



def _vm_asset_categories() -> dict:
    s = st.session_state.settings
    return {
        "gorsel": {
            "label": "🖼️ Görseller",
            "dir": s.get("video_montaj_gorsel_dir", ""),
            "backup_dir": os.path.join(VIDEO_MONTAJ_YEDEK_ROOT, "görsel"),
            "types": ["png", "jpg", "jpeg", "gif", "bmp", "webp"],
        },
        "muzik": {
            "label": "🎵 Müzik",
            "dir": VIDEO_MONTAJ_MUZIK_DIR,
            "backup_dir": os.path.join(VIDEO_MONTAJ_YEDEK_ROOT, "muzik"),
            "types": ["mp3", "wav", "m4a", "aac", "ogg"],
        },
        "cerceve": {
            "label": "🖼️ Çerçeve",
            "dir": VIDEO_MONTAJ_CERCEVE_DIR,
            "backup_dir": os.path.join(VIDEO_MONTAJ_YEDEK_ROOT, "çerçeve"),
            "types": ["png", "jpg", "jpeg", "gif", "mp4", "avi", "mov", "webm"],
        },
        "logo": {
            "label": "🏷️ Logo",
            "dir": VIDEO_MONTAJ_LOGO_DIR,
            "backup_dir": os.path.join(VIDEO_MONTAJ_YEDEK_ROOT, "logo"),
            "types": ["png", "jpg", "jpeg", "gif", "mp4", "avi", "mov", "webm"],
        },
        "video_overlay": {
            "label": "🎥 Video Overlay",
            "dir": VIDEO_MONTAJ_VIDEO_OVERLAY_DIR,
            "backup_dir": os.path.join(VIDEO_MONTAJ_YEDEK_ROOT, "video overlay"),
            "types": ["png", "jpg", "jpeg", "gif", "mp4", "avi", "mov", "webm"],
        },
        "ses_efekti": {
            "label": "🔊 Ses Efekti",
            "dir": VIDEO_MONTAJ_SES_EFEKTI_DIR,
            "backup_dir": os.path.join(VIDEO_MONTAJ_YEDEK_ROOT, "ses efekti"),
            "types": ["mp3", "wav", "m4a", "aac", "ogg"],
        },
    }

def _vm_ensure_dir(path: str):
    if path:
        os.makedirs(path, exist_ok=True)


def _vm_list_asset_files(cat_key: str) -> list:
    cats = _vm_asset_categories()
    meta = cats.get(cat_key, {})
    path = meta.get("dir", "")
    exts = tuple("." + x.lower() for x in meta.get("types", []))

    if not path or not os.path.isdir(path):
        return []

    items = []
    try:
        for name in os.listdir(path):
            full = os.path.join(path, name)
            if os.path.isfile(full) and name.lower().endswith(exts):
                items.append({
                    "name": name,
                    "path": full,
                    "size_kb": max(1, int(round(os.path.getsize(full) / 1024))),
                })
    except Exception:
        return []

    items.sort(key=lambda x: natural_sort_key(x["name"]))
    return items


def _vm_unique_dst_path(dst_dir: str, file_name: str) -> str:
    _vm_ensure_dir(dst_dir)
    base, ext = os.path.splitext(file_name)
    candidate = os.path.join(dst_dir, file_name)
    i = 2
    while os.path.exists(candidate):
        candidate = os.path.join(dst_dir, f"{base}_{i}{ext}")
        i += 1
    return candidate


def _vm_add_uploaded_files(cat_key: str, uploaded_files) -> int:
    cats = _vm_asset_categories()
    meta = cats.get(cat_key, {})
    dst_dir = meta.get("dir", "")
    if not dst_dir:
        return 0

    _vm_ensure_dir(dst_dir)
    added = 0

    for uf in uploaded_files or []:
        try:
            dst = _vm_unique_dst_path(dst_dir, uf.name)
            with open(dst, "wb") as f:
                f.write(uf.getbuffer())
            added += 1
        except Exception as e:
            log(f"[ERROR] Dosya eklenemedi: {uf.name} -> {e}")

    if added:
        log(f"[OK] {meta.get('label', cat_key)} kategorisine {added} dosya eklendi.")
    return added


def _vm_delete_asset(cat_key: str, file_name: str) -> bool:
    files = _vm_list_asset_files(cat_key)
    match = next((x for x in files if x["name"] == file_name), None)
    if not match:
        return False
    try:
        os.remove(match["path"])
        log(f"[OK] Dosya silindi: {file_name}")
        return True
    except Exception as e:
        log(f"[ERROR] Dosya silinemedi: {file_name} -> {e}")
        return False


def _vm_move_asset(src_cat: str, file_name: str, target_mode: str) -> bool:
    cats = _vm_asset_categories()
    src_meta = cats.get(src_cat, {})
    src_files = _vm_list_asset_files(src_cat)
    match = next((x for x in src_files if x["name"] == file_name), None)
    if not match:
        return False

    if target_mode == "backup":
        dst_dir = src_meta.get("backup_dir", "")
        target_label = "🗃️ Yedek Klasör"
    elif target_mode == "downloads":
        dst_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        target_label = "⬇️ İndirilenler"
    else:
        return False

    if not dst_dir:
        return False

    try:
        _vm_ensure_dir(dst_dir)
        dst = _vm_unique_dst_path(dst_dir, file_name)
        shutil.move(match["path"], dst)
        log(f"[OK] Dosya taşındı: {file_name} → {target_label}")
        return True
    except Exception as e:
        log(f"[ERROR] Dosya taşınamadı: {file_name} -> {e}")
        return False

def _vm_list_backup_files(cat_key: str) -> list:
    cats = _vm_asset_categories()
    meta = cats.get(cat_key, {})
    path = meta.get("backup_dir", "")
    exts = tuple("." + x.lower() for x in meta.get("types", []))

    if not path or not os.path.isdir(path):
        return []

    items = []
    try:
        for name in os.listdir(path):
            full = os.path.join(path, name)
            if os.path.isfile(full) and name.lower().endswith(exts):
                items.append({
                    "name": name,
                    "path": full,
                    "size_kb": max(1, int(round(os.path.getsize(full) / 1024))),
                })
    except Exception:
        return []

    items.sort(key=lambda x: natural_sort_key(x["name"]))
    return items


def _vm_restore_asset(cat_key: str, file_name: str) -> bool:
    cats = _vm_asset_categories()
    meta = cats.get(cat_key, {})
    backup_files = _vm_list_backup_files(cat_key)
    match = next((x for x in backup_files if x["name"] == file_name), None)
    if not match:
        return False

    dst_dir = meta.get("dir", "")
    if not dst_dir:
        return False

    try:
        _vm_ensure_dir(dst_dir)
        dst = _vm_unique_dst_path(dst_dir, file_name)
        shutil.move(match["path"], dst)
        log(f"[OK] Yedekten geri alındı: {file_name} → {meta.get('label', cat_key)}")
        return True
    except Exception as e:
        log(f"[ERROR] Yedekten geri alınamadı: {file_name} -> {e}")
        return False

def render_vm_asset_manager():
    st.markdown("---")
    st.markdown("**🗂️ Montaj Dosya Yönetimi**")

    cats = _vm_asset_categories()
    order = ["gorsel", "muzik", "cerceve", "logo", "video_overlay", "ses_efekti"]
    tabs = st.tabs([cats[k]["label"] for k in order])

    for cat_key, tab in zip(order, tabs):
        meta = cats[cat_key]
        with tab:
            _vm_ensure_dir(meta["dir"])
            _vm_ensure_dir(meta.get("backup_dir", ""))

            # UI için placeholder'lar (flash olmadan güncelleme için)
            ph_status = st.empty()
            ph_list = st.empty()

            def _refresh_ui_vars(ck):
                f = _vm_list_asset_files(ck)
                b = _vm_list_backup_files(ck)
                ph_status.caption(f"Ana klasörde dosya: {len(f)} | Yedekte dosya: {len(b)}")
                if f:
                    ph_list.markdown(
                        "<div style='max-height:170px; overflow-y:auto; padding:8px 10px; border:1px solid rgba(255,255,255,0.08); border-radius:10px; background:rgba(255,255,255,0.02)'>"
                        + "".join(f"<div style='padding:4px 0; font-size:13px;'>• {i['name']} <span style='opacity:.65'>({i['size_kb']} KB)</span></div>" for i in f)
                        + "</div>",
                        unsafe_allow_html=True
                    )
                else:
                    ph_list.info("Bu kategoride ana klasörde dosya bulunamadı.")
                return f, b

            def _cb_vm_sil(ck, m_key, a_key):
                sel = st.session_state.get(m_key, [])
                if not sel:
                    st.session_state[f"vm_warn_{ck}"] = "Silmek için bir dosya seçin."
                    return
                count = 0
                for f_name in sel:
                    if _vm_delete_asset(ck, f_name):
                        count += 1
                if count > 0:
                    st.session_state[m_key] = []
                    st.session_state[a_key] = False
                    st.session_state[f"vm_msg_{ck}"] = f"🗑️ {count} dosya silindi."

            def _cb_vm_tasi(ck, m_key, a_key, t_key):
                sel = st.session_state.get(m_key, [])
                t_mode = st.session_state.get(t_key, "backup")
                if not sel:
                    st.session_state[f"vm_warn_{ck}"] = "Taşımak için bir dosya seçin."
                    return
                count = 0
                for f_name in sel:
                    if _vm_move_asset(ck, f_name, t_mode):
                        count += 1
                if count > 0:
                    st.session_state[m_key] = []
                    st.session_state[a_key] = False
                    st.session_state[f"vm_msg_{ck}"] = f"📦 {count} dosya taşındı."

            def _cb_vm_restore(ck, m_key, a_key):
                sel = st.session_state.get(m_key, [])
                if not sel:
                    st.session_state[f"vm_warn_{ck}"] = "Geri almak için yedek klasörden bir dosya seçin."
                    return
                count = 0
                for f_name in sel:
                    if _vm_restore_asset(ck, f_name):
                        count += 1
                if count > 0:
                    st.session_state[m_key] = []
                    st.session_state[a_key] = False
                    st.session_state[f"vm_msg_{ck}"] = f"↩️ {count} dosya geri alındı."

            # İlk yükleme
            files, backup_files = _refresh_ui_vars(cat_key)

            uploads = st.file_uploader(
                f"{meta['label']} için dosya ekle",
                type=meta["types"],
                accept_multiple_files=True,
                key=f"vm_upload_{cat_key}"
            )

            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button(f"➕ {meta['label']} Dosyası Ekle", key=f"vm_add_btn_{cat_key}", use_container_width=True):
                if uploads:
                    _vm_add_uploaded_files(cat_key, uploads)
                    msg = st.empty()
                    msg.success(f"✅ {len(uploads)} dosya eklendi.")
                    st.session_state.pop(f"vm_files_cache_{cat_key}", None)
                    files, backup_files = _refresh_ui_vars(cat_key)
                    time.sleep(2)
                    msg.empty()
                else:
                    st.warning("Önce eklenecek dosya seçin.")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Callback mesajlarını göster
            if f"vm_msg_{cat_key}" in st.session_state:
                st.success(st.session_state.pop(f"vm_msg_{cat_key}"))
            if f"vm_warn_{cat_key}" in st.session_state:
                st.warning(st.session_state.pop(f"vm_warn_{cat_key}"))

            st.markdown("---")
            all_file_names = [x["name"] for x in files]
            sel_col1, sel_col2 = st.columns([0.7, 0.3])
            
            multi_key = f"vm_asset_sel_multi_{cat_key}"
            all_key = f"vm_all_{cat_key}"
            
            if multi_key not in st.session_state:
                st.session_state[multi_key] = []

            def _toggle_all_files(ck=cat_key, names=all_file_names):
                if st.session_state.get(f"vm_all_{ck}"):
                    st.session_state[f"vm_asset_sel_multi_{ck}"] = names
                else:
                    st.session_state[f"vm_asset_sel_multi_{ck}"] = []

            with sel_col2:
                st.checkbox("Tümünü Seç", key=all_key, on_change=_toggle_all_files)
            with sel_col1:
                selected_files = st.multiselect(
                    f"{meta['label']} dosya seçin",
                    options=all_file_names,
                    key=multi_key,
                    placeholder="Dosya seçin"
                )

            if files:
                st.markdown(
                    "<div style='max-height:170px; overflow-y:auto; padding:8px 10px; border:1px solid rgba(255,255,255,0.08); border-radius:10px; background:rgba(255,255,255,0.02)'>"
                    + "".join(
                        f"<div style='padding:4px 0; font-size:13px;'>• {f['name']} <span style='opacity:.65'>({f['size_kb']} KB)</span></div>"
                        for f in files
                    )
                    + "</div>",
                    unsafe_allow_html=True
                )
            else:
                st.info("Bu kategoride ana klasörde dosya bulunamadı.")

            st.markdown("---")
            c1, c2 = st.columns(2)

            with c1:
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                st.button(
                    "🗑️ Sil", 
                    key=f"vm_delete_btn_{cat_key}", 
                    use_container_width=True,
                    on_click=_cb_vm_sil,
                    args=(cat_key, multi_key, all_key)
                )
                st.markdown('</div>', unsafe_allow_html=True)

            with c2:
                target_mode_key = f"vm_move_target_{cat_key}"
                st.selectbox(
                    "Taşıma hedefi",
                    options=["backup", "downloads"],
                    key=target_mode_key,
                    format_func=lambda k: "🗃️ Yedek Klasör" if k == "backup" else "⬇️ İndirilenler"
                )
                st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
                st.button(
                    "📦 Taşı", 
                    key=f"vm_move_btn_{cat_key}", 
                    use_container_width=True,
                    on_click=_cb_vm_tasi,
                    args=(cat_key, multi_key, all_key, target_mode_key)
                )
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("---")
            all_backup_names = [x["name"] for x in backup_files]
            bsel_col1, bsel_col2 = st.columns([0.7, 0.3])

            bmulti_key = f"vm_backup_sel_multi_{cat_key}"
            ball_key = f"vm_all_backup_{cat_key}"

            if bmulti_key not in st.session_state:
                st.session_state[bmulti_key] = []

            def _toggle_all_backup(ck=cat_key, names=all_backup_names):
                if st.session_state.get(f"vm_all_backup_{ck}"):
                    st.session_state[f"vm_backup_sel_multi_{ck}"] = names
                else:
                    st.session_state[f"vm_backup_sel_multi_{ck}"] = []

            with bsel_col2:
                st.checkbox("Tümünü Seç", key=ball_key, on_change=_toggle_all_backup)
            with bsel_col1:
                selected_backup_files = st.multiselect(
                    f"{meta['label']} yedekten geri alınacak dosya",
                    options=all_backup_names,
                    key=bmulti_key,
                    placeholder="Yedekten dosya seçin"
                )

            if backup_files:
                st.markdown(
                    "<div style='max-height:170px; overflow-y:auto; padding:8px 10px; border:1px solid rgba(255,255,255,0.08); border-radius:10px; background:rgba(255,255,255,0.02)'>"
                    + "".join(
                        f"<div style='padding:4px 0; font-size:13px;'>↩ {f['name']} <span style='opacity:.65'>({f['size_kb']} KB)</span></div>"
                        for f in backup_files
                    )
                    + "</div>",
                    unsafe_allow_html=True
                )
            else:
                st.info("Bu kategorinin yedek klasöründe dosya bulunamadı.")

            st.markdown('<div class="btn-info">', unsafe_allow_html=True)
            st.button(
                "↩️ Ana Klasöre Geri Al", 
                key=f"vm_restore_btn_{cat_key}", 
                use_container_width=True,
                on_click=_cb_vm_restore,
                args=(cat_key, bmulti_key, ball_key)
            )
            st.markdown('</div>', unsafe_allow_html=True)

# --- VIDEO MONTAJ PRESET SAFE BOOTSTRAP ---
VIDEO_MONTAJ_PRESET_FILE = os.path.join(CONTROL_DIR, "video_montaj_preset.json")
VIDEO_MONTAJ_MUZIK_SES_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\muzik\ses_seviyesi.txt"
VIDEO_MONTAJ_SES_EFEKTI_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\ses efekti\ses_seviyesi.txt"
VIDEO_MONTAJ_BASLIK_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\başlık.txt"

if "_vm_read_text_file" not in globals():
    def _vm_read_text_file(path: str, default: str = "") -> str:
        try:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read().strip()
        except Exception:
            pass
        return default

if "_vm_write_text_file" not in globals():
    def _vm_write_text_file(path: str, value: str) -> bool:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write((value or "").strip())
            return True
        except Exception as e:
            try:
                log(f"[ERROR] TXT yazılamadı: {path} -> {e}")
            except Exception:
                pass
            return False

if "_vm_normalize_percent_text" not in globals():
    def _vm_normalize_percent_text(value: str, default_percent: int = 15) -> str:
        raw = str(value or "").strip().replace("%", "")
        if not raw:
            return str(default_percent)
        try:
            num = float(raw.replace(",", "."))
            if num <= 1:
                num = num * 100
            num = max(0, min(100, int(round(num))))
            return str(num)
        except Exception:
            return str(default_percent)

if "video_montaj_preset_oku" not in globals():
    def video_montaj_preset_oku() -> dict:
        if not os.path.exists(VIDEO_MONTAJ_PRESET_FILE):
            return {}
        try:
            with open(VIDEO_MONTAJ_PRESET_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

if "video_montaj_preset_kaydet" not in globals():
    def video_montaj_preset_kaydet(selection_text: str, format_choice: str, muzik_seviyesi: str = "", ses_efekti_seviyesi: str = "", baslik: str = "", source_mode: str = "Mevcut Videolar", orijinal_ses_seviyesi: str = "", video_ses_seviyesi: str = "", orijinal_ses_kaynak_sirasi: str = "") -> bool:
        try:
            os.makedirs(CONTROL_DIR, exist_ok=True)

            muzik_seviyesi = _vm_normalize_percent_text(muzik_seviyesi, 15)
            ses_efekti_seviyesi = _vm_normalize_percent_text(ses_efekti_seviyesi, 15)
            orijinal_ses_seviyesi = _vm_normalize_percent_text(orijinal_ses_seviyesi, 100)
            video_ses_seviyesi = _vm_normalize_percent_text(video_ses_seviyesi, 100)
            baslik = (baslik or "").strip()
            orijinal_ses_kaynak_sirasi = _orijinal_ses_kaynak_sirasi_normalize(orijinal_ses_kaynak_sirasi)

            payload = {
                "selection_text": (selection_text or "").strip() or "T",
                "format_choice": "D" if str(format_choice or "D").strip().upper().startswith("D") else "Y",
                "muzik_seviyesi": muzik_seviyesi,
                "ses_efekti_seviyesi": ses_efekti_seviyesi,
                "orijinal_ses_seviyesi": orijinal_ses_seviyesi,
                "video_ses_seviyesi": video_ses_seviyesi,
                "baslik": baslik,
                "source_mode": _normalize_toplu_video_source_mode(source_mode),
                "orijinal_ses_kaynak_sirasi": orijinal_ses_kaynak_sirasi,
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            with open(VIDEO_MONTAJ_PRESET_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            _vm_write_text_file(VIDEO_MONTAJ_MUZIK_SES_TXT, muzik_seviyesi)
            _vm_write_text_file(VIDEO_MONTAJ_SES_EFEKTI_TXT, ses_efekti_seviyesi)
            _vm_write_text_file(VIDEO_MONTAJ_ORIJINAL_SES_TXT, orijinal_ses_seviyesi)
            _vm_write_text_file(VIDEO_MONTAJ_VIDEO_SES_TXT, video_ses_seviyesi)
            _vm_write_text_file(VIDEO_MONTAJ_BASLIK_TXT, baslik)
            with open(VIDEO_MONTAJ_ORIJINAL_SES_KAYNAKLARI_JSON, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

            try:
                log("[OK] Video Montaj ayarları kaydedildi.")
            except Exception:
                pass
            return True
        except Exception as e:
            try:
                log(f"[ERROR] Video Montaj ayarları kaydedilemedi: {e}")
            except Exception:
                pass
            return False

if "video_montaj_preset_sil" not in globals():
    def video_montaj_preset_sil() -> bool:
        try:
            if os.path.exists(VIDEO_MONTAJ_PRESET_FILE):
                os.remove(VIDEO_MONTAJ_PRESET_FILE)
                try:
                    log("[OK] Video Montaj kayıtlı ayarları temizlendi.")
                except Exception:
                    pass
            return True
        except Exception as e:
            try:
                log(f"[ERROR] Video Montaj kayıtlı ayarları temizlenemedi: {e}")
            except Exception:
                pass
            return False

# --- VIDEO MONTAJ PRESET HARD FIX BOOTSTRAP ---
VIDEO_MONTAJ_PRESET_FILE = os.path.join(CONTROL_DIR, "video_montaj_preset.json")
VIDEO_MONTAJ_MUZIK_SES_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\muzik\ses_seviyesi.txt"
VIDEO_MONTAJ_SES_EFEKTI_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\ses efekti\ses_seviyesi.txt"
VIDEO_MONTAJ_BASLIK_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\başlık.txt"
VIDEO_MONTAJ_ORIJINAL_SES_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\orijinal_ses_seviyesi.txt"
VIDEO_MONTAJ_VIDEO_SES_TXT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\video_ses_seviyesi.txt"
VIDEO_MONTAJ_ORIJINAL_SES_KAYNAKLARI_JSON = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Montaj\ek\orijinal_ses_kaynaklari.json"

if "_vm_read_text_file" not in globals():
    def _vm_read_text_file(path: str, default: str = "") -> str:
        try:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read().strip()
        except Exception:
            pass
        return default

if "_vm_write_text_file" not in globals():
    def _vm_write_text_file(path: str, value: str) -> bool:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write((value or "").strip())
            return True
        except Exception:
            return False

if "_vm_normalize_percent_text" not in globals():
    def _vm_normalize_percent_text(value: str, default_percent: int = 15) -> str:
        raw = str(value or "").strip().replace("%", "")
        if not raw:
            return str(default_percent)
        try:
            num = float(raw.replace(",", "."))
            if num <= 1:
                num = num * 100
            num = max(0, min(100, int(round(num))))
            return str(num)
        except Exception:
            return str(default_percent)

if "video_montaj_preset_oku" not in globals():
    def video_montaj_preset_oku() -> dict:
        if not os.path.exists(VIDEO_MONTAJ_PRESET_FILE):
            return {}
        try:
            with open(VIDEO_MONTAJ_PRESET_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

if "video_montaj_preset_kaydet" not in globals():
    def video_montaj_preset_kaydet(selection_text: str, format_choice: str, muzik_seviyesi: str = "", ses_efekti_seviyesi: str = "", baslik: str = "", source_mode: str = "Mevcut Videolar", orijinal_ses_seviyesi: str = "", video_ses_seviyesi: str = "", orijinal_ses_kaynak_sirasi: str = "") -> bool:
        try:
            os.makedirs(CONTROL_DIR, exist_ok=True)

            muzik_seviyesi = _vm_normalize_percent_text(muzik_seviyesi, 15)
            ses_efekti_seviyesi = _vm_normalize_percent_text(ses_efekti_seviyesi, 15)
            orijinal_ses_seviyesi = _vm_normalize_percent_text(orijinal_ses_seviyesi, 100)
            video_ses_seviyesi = _vm_normalize_percent_text(video_ses_seviyesi, 100)
            baslik = (baslik or "").strip()
            orijinal_ses_kaynak_sirasi = _orijinal_ses_kaynak_sirasi_normalize(orijinal_ses_kaynak_sirasi)

            payload = {
                "selection_text": (selection_text or "").strip() or "T",
                "format_choice": "D" if str(format_choice or "D").strip().upper().startswith("D") else "Y",
                "muzik_seviyesi": muzik_seviyesi,
                "ses_efekti_seviyesi": ses_efekti_seviyesi,
                "orijinal_ses_seviyesi": orijinal_ses_seviyesi,
                "video_ses_seviyesi": video_ses_seviyesi,
                "baslik": baslik,
                "source_mode": _normalize_toplu_video_source_mode(source_mode),
                "orijinal_ses_kaynak_sirasi": orijinal_ses_kaynak_sirasi,
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            with open(VIDEO_MONTAJ_PRESET_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            _vm_write_text_file(VIDEO_MONTAJ_MUZIK_SES_TXT, muzik_seviyesi)
            _vm_write_text_file(VIDEO_MONTAJ_SES_EFEKTI_TXT, ses_efekti_seviyesi)
            _vm_write_text_file(VIDEO_MONTAJ_ORIJINAL_SES_TXT, orijinal_ses_seviyesi)
            _vm_write_text_file(VIDEO_MONTAJ_VIDEO_SES_TXT, video_ses_seviyesi)
            _vm_write_text_file(VIDEO_MONTAJ_BASLIK_TXT, baslik)
            with open(VIDEO_MONTAJ_ORIJINAL_SES_KAYNAKLARI_JSON, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

if "video_montaj_preset_sil" not in globals():
    def video_montaj_preset_sil() -> bool:
        try:
            if os.path.exists(VIDEO_MONTAJ_PRESET_FILE):
                os.remove(VIDEO_MONTAJ_PRESET_FILE)
            return True
        except Exception:
            return False


def _toplu_video_source_secim_metni_uret(secili_tokenler, custom_text=''):
    custom_text = (custom_text or '').strip()
    if custom_text:
        parts = [p.strip().upper() for p in re.split(r'[\s,;]+', custom_text) if p.strip()]
        if not parts:
            return "T"
        out = []
        for p in parts:
            if p == "T":
                return "T"
            if re.fullmatch(r'\d+', p):
                val = str(int(p))
                if val not in out:
                    out.append(val)
        return ",".join(out) if out else "T"

    return ",".join(secili_tokenler) if secili_tokenler else "T"


def _toplu_video_source_secim_to_tokens(text_value: str, video_items: list) -> list:
    all_tokens = [str(item.get("token")) for item in (video_items or [])]
    raw = (text_value or "").strip().upper()
    if not raw or raw == "T":
        return all_tokens

    out = []
    for part in re.split(r'[\s,;]+', raw):
        if not part:
            continue
        if part == "T":
            return all_tokens
        if re.fullmatch(r'\d+', part):
            val = str(int(part))
            if val in all_tokens and val not in out:
                out.append(val)
    return out


def _toplu_video_source_secim_to_script_indices(text_value: str, video_items: list) -> list:
    token_to_index = {}
    for item in (video_items or []):
        token = str(item.get("token"))
        script_token = item.get("script_token")
        try:
            token_to_index[token] = int(script_token)
        except Exception:
            try:
                token_to_index[token] = max(0, int(token) - 1)
            except Exception:
                continue

    out = []
    for token in _toplu_video_source_secim_to_tokens(text_value, video_items):
        idx = token_to_index.get(str(token))
        if idx is not None and idx not in out:
            out.append(idx)
    return out


def _toplu_video_count_selected_existing(text_value: str, video_items: list) -> int:
    selected_tokens = set(_toplu_video_source_secim_to_tokens(text_value, video_items))
    return sum(1 for item in (video_items or []) if str(item.get("token")) in selected_tokens and item.get("exists"))


def _toplu_video_count_selected_entries(text_value: str, video_items: list) -> int:
    return len(_toplu_video_source_secim_to_tokens(text_value, video_items))


TOPLU_VIDEO_PRESET_FILE = os.path.join(CONTROL_DIR, "toplu_video_preset.json")

if "_toplu_video_get_materyal_paths" not in globals():
    def _toplu_video_get_materyal_paths() -> dict:
        materyal_dir = (st.session_state.settings.get("toplu_video_materyal_dir") or DEFAULT_SETTINGS.get("toplu_video_materyal_dir") or "").strip()
        return {
            "ana": materyal_dir,
            "muzik_ses": os.path.join(materyal_dir, "muzik", "ses_seviyesi.txt"),
            "ses_efekti_ses": os.path.join(materyal_dir, "ses efekti", "ses_seviyesi.txt"),
            "baslik": os.path.join(materyal_dir, "başlık.txt"),
            "orijinal_ses_kaynaklari": os.path.join(materyal_dir, "orijinal_ses_kaynaklari.json"),
        }

if "toplu_video_preset_oku" not in globals():
    def toplu_video_preset_oku() -> dict:
        try:
            if os.path.exists(TOPLU_VIDEO_PRESET_FILE):
                with open(TOPLU_VIDEO_PRESET_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

if "toplu_video_preset_kaydet" not in globals():
    def toplu_video_preset_kaydet(selection_text: str, format_choice: str, source_selection_text: str = "T", muzik_seviyesi: str = "", ses_efekti_seviyesi: str = "", baslik: str = "", source_mode: str = "Mevcut Videolar", orijinal_ses_seviyesi: str = "", video_ses_seviyesi: str = "", orijinal_ses_kaynak_sirasi: str = "") -> bool:
        try:
            os.makedirs(os.path.dirname(TOPLU_VIDEO_PRESET_FILE), exist_ok=True)
            muzik_seviyesi = _vm_normalize_percent_text(muzik_seviyesi, 15)
            ses_efekti_seviyesi = _vm_normalize_percent_text(ses_efekti_seviyesi, 15)
            orijinal_ses_seviyesi = _vm_normalize_percent_text(orijinal_ses_seviyesi, 100)
            video_ses_seviyesi = _vm_normalize_percent_text(video_ses_seviyesi, 100)
            baslik = (baslik or "").strip()
            orijinal_ses_kaynak_sirasi = _orijinal_ses_kaynak_sirasi_normalize(orijinal_ses_kaynak_sirasi)
            payload = {
                "selection_text": (selection_text or "T").strip(),
                "format_choice": (format_choice or "D").strip().upper(),
                "source_selection_text": (source_selection_text or "T").strip().upper() or "T",
                "source_mode": _normalize_toplu_video_source_mode(source_mode),
                "muzik_seviyesi": muzik_seviyesi,
                "ses_efekti_seviyesi": ses_efekti_seviyesi,
                "orijinal_ses_seviyesi": orijinal_ses_seviyesi,
                "video_ses_seviyesi": video_ses_seviyesi,
                "baslik": baslik,
                "orijinal_ses_kaynak_sirasi": orijinal_ses_kaynak_sirasi,
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(TOPLU_VIDEO_PRESET_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            materyal_paths = _tv_bootstrap_get_materyal_paths(st.session_state.settings)
            _vm_write_text_file(materyal_paths["muzik_ses"], muzik_seviyesi)
            _vm_write_text_file(materyal_paths["ses_efekti_ses"], ses_efekti_seviyesi)
            _vm_write_text_file(os.path.join(materyal_paths["ana"], "orijinal_ses_seviyesi.txt"), orijinal_ses_seviyesi)
            _vm_write_text_file(os.path.join(materyal_paths["ana"], "video_ses_seviyesi.txt"), video_ses_seviyesi)
            _vm_write_text_file(materyal_paths["baslik"], baslik)
            with open(materyal_paths["orijinal_ses_kaynaklari"], "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

if "toplu_video_preset_sil" not in globals():
    def toplu_video_preset_sil() -> bool:
        try:
            if os.path.exists(TOPLU_VIDEO_PRESET_FILE):
                os.remove(TOPLU_VIDEO_PRESET_FILE)
            return True
        except Exception:
            return False


_TOPLU_VIDEO_VARYASYON_ADET_TABLOSU = {
    2: {2: 2},
    3: {2: 6, 3: 6},
    4: {2: 10, 3: 20, 4: 20},
    5: {2: 10, 3: 20, 4: 20, 5: 10},
    6: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10},
    7: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10, 7: 10},
    8: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10, 7: 10, 8: 10},
    9: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10, 7: 10, 8: 10, 9: 10},
    10: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10, 7: 10, 8: 10, 9: 10, 10: 10},
    11: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10, 7: 10, 8: 10, 9: 10, 10: 10, 11: 10},
    12: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10, 7: 10, 8: 10, 9: 10, 10: 10, 11: 10, 12: 10},
    13: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10, 7: 10, 8: 10, 9: 10, 10: 10, 11: 10, 12: 10, 13: 10},
    14: {2: 10, 3: 20, 4: 20, 5: 20, 6: 10, 7: 10, 8: 10, 9: 10, 10: 10, 11: 10, 12: 10, 13: 10, 14: 10},
    15: {2: 7, 3: 5, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 20, 10: 20, 11: 20, 12: 20, 13: 20, 14: 20, 15: 20},
    16: {2: 8, 3: 5, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 20, 10: 20, 11: 20, 12: 20, 13: 20, 14: 20, 15: 20, 16: 20},
    17: {2: 8, 3: 5, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 20, 10: 20, 11: 20, 12: 20, 13: 20, 14: 20, 15: 20, 16: 20, 17: 20},
    18: {2: 9, 3: 6, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 20, 10: 20, 11: 20, 12: 20, 13: 20, 14: 20, 15: 20, 16: 20, 17: 20, 18: 20},
    19: {2: 9, 3: 6, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 20, 10: 20, 11: 20, 12: 20, 13: 20, 14: 20, 15: 20, 16: 20, 17: 20, 18: 20, 19: 20},
    20: {2: 10, 3: 6, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 20, 10: 20, 11: 20, 12: 20, 13: 20, 14: 20, 15: 20, 16: 20, 17: 20, 18: 20, 19: 20, 20: 20},
}

def _toplu_video_secimden_grup_listesi(secim_metni: str, kaynak_sayisi: int) -> list:
    if kaynak_sayisi < 2:
        return []

    tokenler = [
        p.strip().upper()
        for p in re.split(r'[\s,;]+', (secim_metni or '').strip().upper())
        if p.strip()
    ]
    if not tokenler:
        return []

    max_grup = min(kaynak_sayisi, 20)
    if "T" in tokenler or "TAMAMI" in tokenler:
        return list(range(2, max_grup + 1))

    gruplar = []
    for token in tokenler:
        if token.isdigit():
            grup = int(token)
            if 2 <= grup <= max_grup:
                gruplar.append(grup)
    return sorted(set(gruplar))

def _toplu_video_hesapla_uretilecek_video_sayisi(kaynak_sayisi: int, secim_metni: str):
    tablo = _TOPLU_VIDEO_VARYASYON_ADET_TABLOSU.get(kaynak_sayisi)
    if tablo is None:
        return None

    secili_gruplar = _toplu_video_secimden_grup_listesi(secim_metni, kaynak_sayisi)
    if not secili_gruplar:
        return 0

    return sum(tablo.get(grup, 0) for grup in secili_gruplar)

@st.dialog("🎬 Toplu Video Montaj", width="large")
def toplu_video_dialog():
    s = st.session_state.settings
    st.caption("Formatı, kaynak videoları ve varyasyon gruplarını seçin. Mevcut videoların yanında 🎞️ Video Ekle ile yüklediğiniz videoları da Toplu Video Montaj kaynağı olarak kullanabilirsiniz.")

    if not st.session_state.get("_tv_preset_loaded", False):
        preset = globals().get("toplu_video_preset_oku", lambda: {})()
        materyal_paths = _tv_bootstrap_get_materyal_paths(st.session_state.settings)
        if preset:
            st.session_state.toplu_video_selection_text = preset.get("selection_text", st.session_state.get("toplu_video_selection_text", "T"))
            st.session_state.toplu_video_format = preset.get("format_choice", st.session_state.get("toplu_video_format", "D"))
            st.session_state.toplu_video_source_selection_text = preset.get("source_selection_text", st.session_state.get("toplu_video_source_selection_text", "T"))
            st.session_state["toplu_video_source_mode"] = _normalize_toplu_video_source_mode(preset.get("source_mode", st.session_state.get("toplu_video_source_mode", "Mevcut Videolar")))
            st.session_state["tv_muzik_seviyesi"] = preset.get("muzik_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["muzik_ses"], "15"))
            st.session_state["tv_ses_efekti_seviyesi"] = preset.get("ses_efekti_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["ses_efekti_ses"], "15"))
            st.session_state["tv_orijinal_ses_seviyesi"] = preset.get("orijinal_ses_seviyesi", "100")
            st.session_state["tv_video_ses_seviyesi"] = preset.get("video_ses_seviyesi", "100")
            st.session_state["tv_orijinal_ses_kaynak_sirasi"] = preset.get("orijinal_ses_kaynak_sirasi", st.session_state.get("tv_orijinal_ses_kaynak_sirasi", ""))
            st.session_state["tv_baslik"] = preset.get("baslik", _tv_bootstrap_read_text_file(materyal_paths["baslik"], ""))
        else:
            st.session_state.setdefault("toplu_video_source_mode", "Mevcut Videolar")
            st.session_state.setdefault("tv_muzik_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["muzik_ses"], "15"))
            st.session_state.setdefault("tv_ses_efekti_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["ses_efekti_ses"], "15"))
            st.session_state.setdefault("tv_orijinal_ses_seviyesi", "100")
            st.session_state.setdefault("tv_video_ses_seviyesi", "100")
            st.session_state.setdefault("tv_orijinal_ses_kaynak_sirasi", "")
            st.session_state.setdefault("tv_baslik", _tv_bootstrap_read_text_file(materyal_paths["baslik"], ""))
        st.session_state["_tv_preset_loaded"] = True

    assets = _list_video_montaj_assets()
    is_batch = st.session_state.get("batch_mode", False)
    is_running = any_running()

    mevcut_format = st.session_state.get("toplu_video_format", "D")
    fmt_label = st.radio(
        "📐 Video Format Seçimi",
        ["Yatay - 1920x1080 (Normal YouTube)", "Dikey - 1080x1920 (YouTube Shorts)"],
        index=0 if mevcut_format == "Y" else 1,
        key="tv_format_radio",
        horizontal=True,
    )

    tv_source_options = ["Mevcut Videolar", "Eklenen Video", "Görsel Oluştur"]
    tv_current_source_mode = _normalize_toplu_video_source_mode(st.session_state.get("toplu_video_source_mode", "Mevcut Videolar"))
    kaynak_modu = st.radio(
        "📂 Kaynak Türü",
        tv_source_options,
        index=tv_source_options.index(tv_current_source_mode) if tv_current_source_mode in tv_source_options else 0,
        key="tv_source_mode_radio",
        horizontal=True,
    )
    st.session_state.toplu_video_source_mode = _normalize_toplu_video_source_mode(kaynak_modu)

    if st.session_state.toplu_video_source_mode == "Eklenen Video":
        video_items = _list_toplu_video_added_source_items()
        kaynak_baslik = "**🎞️ Video Ekle kaynakları:**"
        kaynak_bilgi = "Bu modda 🎞️ Video Ekle bölümüne yüklediğiniz videolar Toplu Video Montaj için kaynak olarak kullanılır."
    elif st.session_state.toplu_video_source_mode == "Görsel Oluştur":
        video_items = assets.get("gorsel_olustur_videos", [])
        kaynak_baslik = "**🖼️ Görsel Oluştur kaynakları:**"
        kaynak_bilgi = "Bu modda Görsel Oluştur ekranında kaydettiğiniz hareketlendirme promptlarından oluşan videolar kaynak olarak kullanılır."
    else:
        video_items = assets.get("videos", [])
        kaynak_baslik = "**🎬 Kaynak videolar (Önce Normal / İndirilen Videolar, Sonra Klon Videolar):**"
        kaynak_bilgi = "Bu modda mevcut normal, indirilen ve klon videolar kullanılır."

    has_existing_source_video = any(item.get("exists") for item in video_items)

    st.markdown("---")
    st.markdown(kaynak_baslik)
    st.caption(kaynak_bilgi)
    if st.session_state.toplu_video_source_mode == "Görsel Oluştur" and video_items and not has_existing_source_video:
        st.info("Kayitli hareketlendirme promptlari kaynak listesine eklendi. Tumunu Calistir akisinda once bu videolar uretilir, sonra Toplu Video Montaj bu ciktilari kullanir.")
    tv_pick_prefix = f"tv_pick_{st.session_state.toplu_video_source_mode}"
    onceki_kaynak_text = (st.session_state.get("toplu_video_source_selection_text", "T") or "T").strip().upper() or "T"
    onceki_kaynak_tokenleri = set(_toplu_video_source_secim_to_tokens(onceki_kaynak_text, video_items))
    if video_items:
        for item in video_items:
            st.checkbox(
                item["label"],
                key=f"{tv_pick_prefix}_{item['token']}",
                value=(str(item["token"]) in onceki_kaynak_tokenleri) or (onceki_kaynak_text == "T"),
            )
    else:
        st.info("Toplu montaj için uygun video bulunamadı.")

    secili_video_tokenleri = [item["token"] for item in video_items if st.session_state.get(f"{tv_pick_prefix}_{item['token']}", False)]
    tum_video_tokenleri = [item["token"] for item in video_items]
    tum_videolar_secili = bool(tum_video_tokenleri) and (set(secili_video_tokenleri) == set(tum_video_tokenleri))
    checkbox_kaynak_secim_metni = "T" if tum_videolar_secili else (_toplu_video_source_secim_metni_uret(secili_video_tokenleri) if secili_video_tokenleri else "T")

    kaynak_secim_metni = checkbox_kaynak_secim_metni
    secili_kaynak_girdisi_sayisi = _toplu_video_count_selected_entries(kaynak_secim_metni, video_items)
    secili_mevcut_video_sayisi = _toplu_video_count_selected_existing(kaynak_secim_metni, video_items)

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("🗂️ Montaj Dosya Yönetimi", key="tv_asset_manager_open_btn", use_container_width=True):
        st.session_state.ek_dialog_open = "tv_asset_manager"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**🎛️ Varyasyon Grupları:**")
    secenekler = list(range(2, min(secili_kaynak_girdisi_sayisi, 20) + 1))
    onceki_secim = {
        p.strip().upper()
        for p in re.split(r'[\s,;]+', st.session_state.get("toplu_video_selection_text", "T") or "T")
        if p.strip()
    }
    cols = st.columns(5)
    secili_gruplar = []
    for idx, grup in enumerate(secenekler):
        with cols[idx % 5]:
            vars_key = f"tv_group_{grup}"
            default_val = str(grup) in onceki_secim
            secili = st.checkbox(f"{grup}'li", key=vars_key, value=default_val)
            if secili:
                secili_gruplar.append(str(grup))

    if not secenekler:
        st.caption("En az 2 kaynak girişi seçildiğinde varyasyon grupları burada görünür.")

    st.markdown("---")
    st.markdown("**\u2728 Eklemeler:**")
    t1, t2, t3 = st.columns(3)
    with t1:
        muzik = st.checkbox("🎵 Müzik", key="tv_fx_m", value="M" in onceki_secim)
    with t2:
        cerceve = st.checkbox("🖼️ Çerçeve", key="tv_fx_c", value="C" in onceki_secim)
    with t3:
        logo = st.checkbox("🏷️ Logo", key="tv_fx_l", value="L" in onceki_secim)
    t4, t5, t6 = st.columns(3)
    with t4:
        overlay = st.checkbox("🎥 Video", key="tv_fx_v", value="V" in onceki_secim)
    with t5:
        ses = st.checkbox("🔊 Ses Efekti", key="tv_fx_s", value="S" in onceki_secim)
    with t6:
        orijinal_ses = st.checkbox("🎤 Orijinal Ses", key="tv_fx_o", value="O" in onceki_secim)

    st.markdown("---")
    a1, a2 = st.columns(2)
    with a1:
        st.text_input("🎵 M\u00fczik Ses Seviyesi (%)", key="tv_muzik_seviyesi", placeholder="\u00d6rn: 15")
    with a2:
        st.text_input("🔊 Ses Efekti Ses Seviyesi (%)", key="tv_ses_efekti_seviyesi", placeholder="\u00d6rn: 25")

    b1, b2 = st.columns(2)
    with b1:
        st.text_input("🎤 Orijinal Ses Seviyesi (%)", key="tv_orijinal_ses_seviyesi", placeholder="\u00d6rn: 100")
    with b2:
        st.text_input("🔇 Video Ses Seviyesi (%)", key="tv_video_ses_seviyesi", placeholder="\u00d6rn: 100 (0=kapat)")

    st.text_input("🎼 Orijinal Ses Kaynak Sırası (isteğe bağlı)", key="tv_orijinal_ses_kaynak_sirasi", placeholder="Örn: 2 veya 1,3 veya T")
    _tv_orijinal_ses_preview = _orijinal_ses_kaynak_sirasi_preview(st.session_state.get("tv_orijinal_ses_kaynak_sirasi", ""), video_items)
    if orijinal_ses:
        if _tv_orijinal_ses_preview:
            st.caption("🎧 Seçilen orijinal ses kaynakları: " + " → ".join(_tv_orijinal_ses_preview))
        else:
            st.caption("🎧 Boş bırakılırsa mevcut davranış korunur. T yazarsanız tüm kaynak videoların sesi listedeki sırayla kullanılır.")

    st.text_input("🏷\ufe0f Montaj Ba\u015fl\u0131\u011f\u0131", key="tv_baslik", placeholder="\u00c7\u0131kt\u0131 video ba\u015fl\u0131\u011f\u0131")

    st.markdown("---")
    custom_text = st.text_input(
        "🔢 Özel Varyasyon Seçimi (isteğe bağlı)",
        key="tv_custom_override",
        value="" if st.session_state.get("toplu_video_selection_text", "T") == "T" else st.session_state.get("toplu_video_selection_text", "T"),
        placeholder="\u00d6rn: 2,3,5,M,C veya T,M,L",
    ).strip().upper()

    if custom_text:
        parts = [p.strip() for p in re.split(r'[\s,;]+', custom_text) if p.strip()]
        secim_metni = ",".join(parts) if parts else "T"
    else:
        temel = ",".join(secili_gruplar) if secili_gruplar else "T"
        ekler = []
        if muzik:
            ekler.append("M")
        if cerceve:
            ekler.append("C")
        if logo:
            ekler.append("L")
        if overlay:
            ekler.append("V")
        if ses:
            ekler.append("S")
        if orijinal_ses:
            ekler.append("O")
        secim_metni = temel + ("," + ",".join(ekler) if ekler else "")

    st.markdown("**📝 Oluşacak varyasyon seçimi:**")
    st.code(secim_metni, language="text")

    uretilecek_video_sayisi = _toplu_video_hesapla_uretilecek_video_sayisi(
        secili_kaynak_girdisi_sayisi,
        secim_metni,
    )
    if uretilecek_video_sayisi is None:
        st.warning("Toplu Video scripti 2 ile 20 arası kaynak video sayısını destekliyor. Bu yüzden üretilecek video sayısı burada hesaplanamadı.")
    else:
        st.caption(f"📊 Bu seçimle üretilecek toplam video sayısı: {uretilecek_video_sayisi}")

    st.session_state.toplu_video_source_selection_text = kaynak_secim_metni
    st.session_state.toplu_video_selection_text = secim_metni
    st.session_state.toplu_video_format = "D" if fmt_label.startswith("Dikey") else "Y"

    st.markdown("---")
    a1, a2 = st.columns(2)
    with a1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("💾 Kaydet", key="tv_save_btn", use_container_width=True):
            if globals().get("toplu_video_preset_kaydet", lambda *args, **kwargs: False)(
                secim_metni,
                "D" if fmt_label.startswith("Dikey") else "Y",
                kaynak_secim_metni,
                st.session_state.get("tv_muzik_seviyesi", "15"),
                st.session_state.get("tv_ses_efekti_seviyesi", "15"),
                st.session_state.get("tv_baslik", ""),
                st.session_state.get("toplu_video_source_mode", "Mevcut Videolar"),
                st.session_state.get("tv_orijinal_ses_seviyesi", "100"),
                st.session_state.get("tv_video_ses_seviyesi", "100"),
                st.session_state.get("tv_orijinal_ses_kaynak_sirasi", ""),
            ):
                st.session_state["tv_saved"] = True
            st.session_state.ek_dialog_open = "toplu_video"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with a2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("🗑️ Kayıt Temizle", key="tv_clear_saved_btn", use_container_width=True):
            globals().get("toplu_video_preset_sil", lambda *args, **kwargs: False)()
            st.session_state.pop("tv_saved", None)
            st.session_state.ek_dialog_open = "toplu_video"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("tv_saved"):
        _tv_ph = st.empty()
        _tv_ph.success("Kaydedildi! Toplu Video ayarı kaydedildi.")
        time.sleep(2.5)
        _tv_ph.empty()
        st.session_state.pop("tv_saved", None)

    st.markdown("---")
    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.button(
        "🚀 Toplu Video Montajını Başlat",
        key="tv_start_btn",
        use_container_width=True,
        disabled=is_batch or is_running or (secili_mevcut_video_sayisi < 2),
    ):
        st.session_state.toplu_video_format = "D" if fmt_label.startswith("Dikey") else "Y"
        st.session_state.toplu_video_selection_text = secim_metni
        st.session_state.toplu_video_source_selection_text = kaynak_secim_metni
        # Tekli kontrol butonlarının görünmesi için tekli işlem state'i başlatma anında işaretlenmeli.
        st.session_state.single_paused = False
        st.session_state.single_finish_requested = False
        st.session_state.single_mode = True
        st.session_state.single_step = "toplu_video"
        cleanup_flags()
        # Widget key'lerini bu noktada yeniden yazmıyoruz; Streamlit aynı çalıştırmada
        # widget oluşturulduktan sonra aynı session_state anahtarının değiştirilmesine izin vermiyor.
        # Gerekli normalizasyon zaten start_toplu_video_bg() içinde yapılıyor.
        if start_toplu_video_bg("single"):
            st.session_state.status["toplu_video"] = "running"
        else:
            st.session_state.single_mode = False
            st.session_state.single_step = None
        st.session_state.ek_dialog_open = "toplu_video"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    globals().get("render_dialog_single_controls", lambda **kwargs: None)(step_match="toplu_video", prefix="dlg_toplu_video")

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="bck_tv", use_container_width=True):
        st.session_state.ek_dialog_open = "menu"
        st.session_state["_tv_preset_loaded"] = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("🎞️ Video Montaj", width="large")
def video_montaj_dialog():
    st.caption("Video formatını seçin, mevcut videoları / görselleri işaretleyin ve montajı başlatın.")

    if not st.session_state.get("_vm_preset_loaded", False):
        preset = globals().get("video_montaj_preset_oku", lambda: {})()
        if preset:
            st.session_state.video_montaj_selection_text = preset.get("selection_text", st.session_state.get("video_montaj_selection_text", ""))
            st.session_state.video_montaj_format = preset.get("format_choice", st.session_state.get("video_montaj_format", "D"))
            st.session_state["vm_custom_override"] = preset.get("selection_text", "")
            st.session_state["vm_muzik_seviyesi"] = preset.get("muzik_seviyesi", _vm_read_text_file(VIDEO_MONTAJ_MUZIK_SES_TXT, "15"))
            st.session_state["vm_ses_efekti_seviyesi"] = preset.get("ses_efekti_seviyesi", _vm_read_text_file(VIDEO_MONTAJ_SES_EFEKTI_TXT, "15"))
            st.session_state["vm_orijinal_ses_seviyesi"] = preset.get("orijinal_ses_seviyesi", _vm_read_text_file(VIDEO_MONTAJ_ORIJINAL_SES_TXT, "100"))
            st.session_state["vm_video_ses_seviyesi"] = preset.get("video_ses_seviyesi", _vm_read_text_file(VIDEO_MONTAJ_VIDEO_SES_TXT, "100"))
            st.session_state["vm_orijinal_ses_kaynak_sirasi"] = preset.get("orijinal_ses_kaynak_sirasi", st.session_state.get("vm_orijinal_ses_kaynak_sirasi", ""))
            st.session_state["vm_baslik"] = preset.get("baslik", _vm_read_text_file(VIDEO_MONTAJ_BASLIK_TXT, ""))
            st.session_state["video_montaj_source_mode"] = _normalize_toplu_video_source_mode(preset.get("source_mode", st.session_state.get("video_montaj_source_mode", "Mevcut Videolar")))
        else:
            st.session_state.setdefault("vm_muzik_seviyesi", _vm_read_text_file(VIDEO_MONTAJ_MUZIK_SES_TXT, "15"))
            st.session_state.setdefault("vm_ses_efekti_seviyesi", _vm_read_text_file(VIDEO_MONTAJ_SES_EFEKTI_TXT, "15"))
            st.session_state.setdefault("vm_orijinal_ses_seviyesi", _vm_read_text_file(VIDEO_MONTAJ_ORIJINAL_SES_TXT, "100"))
            st.session_state.setdefault("vm_video_ses_seviyesi", _vm_read_text_file(VIDEO_MONTAJ_VIDEO_SES_TXT, "100"))
            st.session_state.setdefault("vm_orijinal_ses_kaynak_sirasi", "")
            st.session_state.setdefault("vm_baslik", _vm_read_text_file(VIDEO_MONTAJ_BASLIK_TXT, ""))
            st.session_state.setdefault("video_montaj_source_mode", "Mevcut Videolar")
        st.session_state["_vm_preset_loaded"] = True

    # Kaynak modu seçimi: Mevcut Videolar, Eklenen Video veya Görsel Oluştur
    vm_source_options = ["Mevcut Videolar", "Eklenen Video", "Görsel Oluştur"]
    vm_current_source_mode = _normalize_toplu_video_source_mode(st.session_state.get("video_montaj_source_mode", "Mevcut Videolar"))
    vm_kaynak_modu = st.radio(
        "📂 Kaynak Türü",
        vm_source_options,
        index=vm_source_options.index(vm_current_source_mode) if vm_current_source_mode in vm_source_options else 0,
        key="vm_source_mode_radio",
        horizontal=True,
    )
    st.session_state.video_montaj_source_mode = _normalize_toplu_video_source_mode(vm_kaynak_modu)

    if st.session_state.video_montaj_source_mode == "Eklenen Video":
        added_video_items = _list_toplu_video_added_source_items()
        video_items = added_video_items
        image_items = []
        has_real_video_items = any(item.get("exists", False) for item in video_items)
    elif st.session_state.video_montaj_source_mode == "Görsel Oluştur":
        assets = _list_video_montaj_assets()
        video_items = assets.get("gorsel_olustur_videos", [])
        image_items = assets.get("gorsel_olustur_images", [])
        has_real_video_items = any(item.get("exists", False) for item in video_items)
    else:
        assets = _list_video_montaj_assets()
        video_items = assets["videos"]
        image_items = assets["images"]
        has_real_video_items = any(item.get("exists", False) for item in video_items)

    is_batch = st.session_state.get("batch_mode", False)
    is_running = any_running()

    mevcut_format = st.session_state.get("video_montaj_format", "D")
    fmt_label = st.radio(
        "📐 Video Format Seçimi",
        ["Yatay - 1920x1080 (Normal YouTube)", "Dikey - 1080x1920 (YouTube Shorts)"],
        index=0 if mevcut_format == "Y" else 1,
        key="vm_format_radio",
        horizontal=True,
    )

    st.markdown("---")
    if st.session_state.video_montaj_source_mode == "Eklenen Video":
        st.markdown("**🎬 Eklenen Videolar:**")
        st.caption("Bu modda 🎬 Video Ekle bölümüne yüklediğiniz videolar Video Montaj için kaynak olarak kullanılır.")
    elif st.session_state.video_montaj_source_mode == "Görsel Oluştur":
        st.markdown("**🖼️ Görsel Oluştur kaynakları:**")
        st.caption("Bu modda Görsel Oluştur ekranında kaydettiğiniz hareketlendirme promptları ve oluşturulan görseller kaynak olarak kullanılır.")
    else:
        st.markdown("**🎬 Mevcut videolar (Önce Normal / İndirilen Videolar, Sonra Klon Videolar):**")
        st.caption("Bu modda mevcut, indirilen ve klon videolar Video Montaj için kaynak olarak kullanılır.")
    if st.session_state.video_montaj_source_mode == "Görsel Oluştur" and video_items and not has_real_video_items:
        st.info("Kayitli hareketlendirme promptlari kaynak listesine eklendi. Tumunu Calistir akisinda once bu videolar uretilir, sonra Video Montaj bu ciktilari kullanir.")
    vm_pick_prefix = f"vm_pick_{st.session_state.video_montaj_source_mode}"
    if video_items:
        for item in video_items:
            st.checkbox(item["label"], key=f"{vm_pick_prefix}_{item['token']}")
    else:
        st.info("Montaj için uygun video bulunamadı.")

    if st.session_state.video_montaj_source_mode != "Eklenen Video":
        if st.session_state.video_montaj_source_mode == "Görsel Oluştur":
            st.markdown("**🖼️ Oluşturulan görseller:**")
        else:
            st.markdown("**🖼️ Mevcut görseller:**")
        if image_items:
            for item in image_items:
                st.checkbox(item["label"], key=f"{vm_pick_prefix}_{item['token']}")
        else:
            st.caption("Görsel bulunamadı.")

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("🗂️ Montaj Dosya Yönetimi", key="vm_asset_manager_open_btn", use_container_width=True):
        st.session_state.ek_dialog_open = "vm_asset_manager"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**✨ Eklemeler:**")
    e1, e2, e3 = st.columns(3)
    with e1:
        muzik = st.checkbox("🎵 Müzik", key="vm_fx_m")
    with e2:
        cerceve = st.checkbox("🖼️ Çerçeve", key="vm_fx_c")
    with e3:
        logo = st.checkbox("🏷️ Logo", key="vm_fx_l")
    e4, e5, e6 = st.columns(3)
    with e4:
        overlay = st.checkbox("🎥 Video", key="vm_fx_v")
    with e5:
        ses = st.checkbox("🔊 Ses Efekti", key="vm_fx_s")
    with e6:
        orijinal_ses = st.checkbox("🎤 Orijinal Ses", key="vm_fx_o")

    st.markdown("---")
    a1, a2 = st.columns(2)
    with a1:
        st.text_input("🎵 Müzik Ses Seviyesi (%)", key="vm_muzik_seviyesi", placeholder="Örn: 15")
    with a2:
        st.text_input("🔊 Ses Efekti Ses Seviyesi (%)", key="vm_ses_efekti_seviyesi", placeholder="Örn: 25")

    b1, b2 = st.columns(2)
    with b1:
        st.text_input("🎤 Orijinal Ses Seviyesi (%)", key="vm_orijinal_ses_seviyesi", placeholder="Örn: 100")
    with b2:
        st.text_input("🔇 Video Ses Seviyesi (%)", key="vm_video_ses_seviyesi", placeholder="Örn: 100 (0=kapat)")

    st.text_input("🎼 Orijinal Ses Kaynak Sırası (isteğe bağlı)", key="vm_orijinal_ses_kaynak_sirasi", placeholder="Örn: 2 veya 1,3 veya T")
    _vm_orijinal_ses_preview = _orijinal_ses_kaynak_sirasi_preview(st.session_state.get("vm_orijinal_ses_kaynak_sirasi", ""), video_items)
    if orijinal_ses:
        if _vm_orijinal_ses_preview:
            st.caption("🎧 Seçilen orijinal ses kaynakları: " + " → ".join(_vm_orijinal_ses_preview))
        else:
            st.caption("🎧 Boş bırakılırsa mevcut davranış korunur. T yazarsanız tüm videoların sesi listedeki sırayla kullanılır.")

    st.text_input("🏷️ Montaj Başlığı", key="vm_baslik", placeholder="Çıktı video başlığı")

    secili_video_tokenleri = []
    for item in video_items:
        if st.session_state.get(f"{vm_pick_prefix}_{item['token']}", False):
            secili_video_tokenleri.append(item["token"])

    secili_gorsel_tokenleri = []
    for item in image_items:
        if st.session_state.get(f"{vm_pick_prefix}_{item['token']}", False):
            secili_gorsel_tokenleri.append(item["token"])

    tum_video_tokenleri = [item["token"] for item in video_items]

    custom_text = st.text_input(
        "🔢 Özel Sıralama (isteğe bağlı)",
        key="vm_custom_override",
        placeholder="Örn: 1,2,G1,M,C veya sadece T",
    )

    custom_text = (custom_text or "").strip()

    if custom_text:
        secim_metni = _video_montaj_secim_metni_uret(
            [],
            muzik=muzik,
            cerceve=cerceve,
            logo=logo,
            video_overlay=overlay,
            ses_efekti=ses,
            orijinal_ses=orijinal_ses,
            custom_text=custom_text
        )
    else:
        tum_videolar_secili = bool(tum_video_tokenleri) and (set(secili_video_tokenleri) == set(tum_video_tokenleri))
        if tum_videolar_secili and not secili_gorsel_tokenleri:
            temel = "T"
        else:
            temel_tokenler = secili_video_tokenleri + secili_gorsel_tokenleri
            temel = ",".join(temel_tokenler) if temel_tokenler else "T"

        ekler = []
        if muzik: ekler.append("M")
        if cerceve: ekler.append("C")
        if logo: ekler.append("L")
        if overlay: ekler.append("V")
        if ses: ekler.append("S")
        if orijinal_ses: ekler.append("O")

        secim_metni = temel + ("," + ",".join(ekler) if ekler else "")

    st.markdown("**📝 Oluşacak seçim:**")
    st.code(secim_metni, language="text")

    st.session_state.video_montaj_selection_text = secim_metni
    st.session_state.video_montaj_format = "D" if fmt_label.startswith("Dikey") else "Y"

    st.markdown("---")
    s1, s2 = st.columns(2)

    with s1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("💾 Kaydet", key="vm_save_btn", use_container_width=True):
            ok = globals().get("video_montaj_preset_kaydet", lambda *args, **kwargs: False)(
                secim_metni,
                "D" if fmt_label.startswith("Dikey") else "Y",
                st.session_state.get("vm_muzik_seviyesi", "15"),
                st.session_state.get("vm_ses_efekti_seviyesi", "15"),
                st.session_state.get("vm_baslik", ""),
                st.session_state.get("video_montaj_source_mode", "Mevcut Videolar"),
                st.session_state.get("vm_orijinal_ses_seviyesi", "100"),
                st.session_state.get("vm_video_ses_seviyesi", "100"),
                st.session_state.get("vm_orijinal_ses_kaynak_sirasi", ""),
            )
            if ok:
                st.session_state["vm_saved"] = True
            st.session_state.ek_dialog_open = "video_montaj"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with s2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("🗑️ Kayıt Temizle", key="vm_clear_saved_btn", use_container_width=True):
            globals().get("video_montaj_preset_sil", lambda *args, **kwargs: False)()
            st.session_state.pop("vm_saved", None)
            st.session_state.ek_dialog_open = "video_montaj"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("vm_saved"):
        _vm_ph = st.empty()
        _vm_ph.success("Kaydedildi! Video Montaj ayarı kaydedildi.")
        time.sleep(2.5)
        _vm_ph.empty()
        st.session_state.pop("vm_saved", None)

    st.markdown("---")
    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.button(
        "🚀 Video Montajı Başlat",
        key="vm_start_btn",
        use_container_width=True,
        disabled=is_batch or is_running or (not has_real_video_items),
    ):
        st.session_state.video_montaj_format = "D" if fmt_label.startswith("Dikey") else "Y"
        st.session_state.video_montaj_selection_text = secim_metni
        # Tekli kontrol butonlarının görünmesi için tekli işlem state'i başlatma anında işaretlenmeli.
        st.session_state.single_paused = False
        st.session_state.single_finish_requested = False
        st.session_state.single_mode = True
        st.session_state.single_step = "video_montaj"
        cleanup_flags()
        if start_video_montaj_bg("single"):
            st.session_state.status["video_montaj"] = "running"
        else:
            st.session_state.single_mode = False
            st.session_state.single_step = None
        st.session_state.ek_dialog_open = "video_montaj"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    globals().get("render_dialog_single_controls", lambda **kwargs: None)(step_match="video_montaj", prefix="dlg_video_montaj")

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="bck_vm", use_container_width=True):
        st.session_state.ek_dialog_open = "menu"
        st.session_state["_vm_preset_loaded"] = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("🗂️ Montaj Dosya Yönetimi", width="large")
def vm_asset_manager_dialog():
    st.caption("Montaj dosyalarını ekleyin, silin veya başka kategoriye taşıyın.")

    render_vm_asset_manager()

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="vm_asset_manager_back_btn", use_container_width=True):
        st.session_state.ek_dialog_open = "video_montaj"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


@st.dialog("🗂️ Toplu Video Montaj Dosya Yönetimi", width="large")
def tv_asset_manager_dialog():
    st.caption("Toplu Video Montaj dosyalarını ekleyin, silin veya başka kategoriye taşıyın.")

    render_vm_asset_manager()

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="tv_asset_manager_back_btn", use_container_width=True):
        st.session_state.ek_dialog_open = "toplu_video"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


@st.dialog("🗂️ Dosya Yöneticisi", width="large")
def dosya_yoneticisi_dialog():
    tab1, tab2, tab3 = st.tabs(["🔍 İncele & Seçerek Sil", "🧹 Toplu Temizlik", "📦 Ekle & Çıkar"])
    
    with tab1:
        st.caption("Ürettiğiniz medyaları izleyin/görüntüleyin ve beğenmediklerinizi silin.")
        s = st.session_state.settings
        
        kategoriler = {
            "🎬 Toplu Montaj Videoları": s.get("toplu_video_output_dir"),
            "🎞️ Montaj Videoları":      s.get("video_montaj_output_dir"),
            "🎬 Üretilen Videolar":      s.get("video_output_dir"),
            "📝 Promptlar":              s.get("prompt_dir"),
            "🖼️ Oluşturulan Görseller": s.get("gorsel_olustur_dir"),
            "🎨 Klon Görseller":        s.get("klon_gorsel_dir"),
            "🖼️ Görsel Analiz":         s.get("gorsel_analiz_dir"),
            "⬇️ İndirilen Videolar":    s.get("download_dir"),
            "🎞️ Eklenen Videolar":     s.get("added_video_dir")
        }
        
        secilen_kategori = st.selectbox("Kategori Seçin:", list(kategoriler.keys()), key="fileman_cat")
        # Kategori değişince dosya index'ini sıfırla
        if st.session_state.get("fileman_cat_prev") != secilen_kategori:
            st.session_state["fileman_cat_prev"] = secilen_kategori
            st.session_state["fileman_file_idx"] = 0
        hedef_klasor = kategoriler[secilen_kategori]

        # Promptlar kategorisi: klasör başına 1 prompt.txt göster
        if secilen_kategori == "📝 Promptlar":
            if hedef_klasor and os.path.exists(hedef_klasor):
                # "Video Prompt 1", "Video Prompt 2" ... klasörlerini bul
                prompt_girisleri = []
                for klasor_adi in os.listdir(hedef_klasor):
                    klasor_yolu = os.path.join(hedef_klasor, klasor_adi)
                    if os.path.isdir(klasor_yolu):
                        txt_yolu = os.path.join(klasor_yolu, "prompt.txt")
                        if os.path.exists(txt_yolu):
                            prompt_girisleri.append((klasor_adi, txt_yolu))
                prompt_girisleri.sort(key=lambda x: natural_sort_key(x[0]))

                if prompt_girisleri:
                    etiketler = [kadi for kadi, _ in prompt_girisleri]  # Gerçek klasör adı, silme sonrası kaymaz
                    mevcut_idx = st.session_state.get("fileman_file_idx", 0)
                    if mevcut_idx >= len(prompt_girisleri):
                        mevcut_idx = 0

                    secilen_etiket = st.selectbox(
                        f"Prompt Seçin: ({len(prompt_girisleri)} prompt)",
                        options=etiketler,
                        index=mevcut_idx,
                        key="fileman_file_sel"
                    )
                    yeni_idx = etiketler.index(secilen_etiket)
                    st.session_state["fileman_file_idx"] = yeni_idx

                    klasor_adi, txt_yolu = prompt_girisleri[yeni_idx]
                    st.markdown("---")
                    # Klasör adını başlık olarak göster (Video Prompt 1 vb.)
                    st.markdown(f"**📁 {klasor_adi}**")

                    # Yenile + Kopyala butonları
                    _rb1, _rb2, _rb3 = st.columns([0.22, 0.28, 0.5])
                    with _rb1:
                        if st.button("🔄 Yenile", key=f"btn_reload_{yeni_idx}", use_container_width=True):
                            st.session_state.pop(f"prompt_edit_{yeni_idx}", None)
                            # widget_ver artır → Streamlit text_area'yı sıfırdan render eder → diskten okur
                            ver = st.session_state.get(f"prompt_widget_ver_{yeni_idx}", 0)
                            st.session_state[f"prompt_widget_ver_{yeni_idx}"] = ver + 1
                            st.session_state.pop(f"prompt_bildirim_{yeni_idx}", None)
                            st.rerun()
                    with _rb2:
                        _kopya_aktif = st.session_state.get(f"prompt_kopya_goster_{yeni_idx}", False)
                        _kopya_label = "✖ Kopyalamayı Kapat" if _kopya_aktif else "📋 Kopyala"
                        if st.button(_kopya_label, key=f"btn_kopya_{yeni_idx}", use_container_width=True):
                            st.session_state[f"prompt_kopya_goster_{yeni_idx}"] = not _kopya_aktif
                            st.rerun()

                    try:
                        with open(txt_yolu, "r", encoding="utf-8") as f:
                            icerik = f.read()
                        # Düzenleme alanı — session_state'de editlenmiş değer varsa onu göster
                        edit_key = f"prompt_edit_{yeni_idx}"
                        # widget_ver: Geri Al / Yenile basıldığında artar → Streamlit farklı key görür → widget sıfırlanır
                        widget_ver = st.session_state.get(f"prompt_widget_ver_{yeni_idx}", 0)
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = icerik
                        duzenlenen = st.text_area(
                            "📄 prompt.txt içeriği (orijinal):",
                            value=st.session_state[edit_key],
                            height=280,
                            key=f"prompt_preview_area_{yeni_idx}_v{widget_ver}"
                        )
                        st.session_state[edit_key] = duzenlenen

                        # ── Kopyala alanı: st.code ile yerleşik kopyalama butonu
                        if st.session_state.get(f"prompt_kopya_goster_{yeni_idx}", False):
                            st.markdown("**📋 Kopyalamak için aşağıdaki metni kullanın:**")
                            st.code(duzenlenen, language=None)

                    except Exception as e:
                        st.error(f"Dosya okunamadı: {e}")
                        icerik = ""
                        duzenlenen = ""

                    # Kaydet + Geri Al + Türkçeye Çevir + Sil butonları
                    ceviri_key = f"prompt_ceviri_{yeni_idx}"
                    bildirim_key = f"prompt_bildirim_{yeni_idx}"
                    c_save, c_reload2, c_tr, c_del = st.columns(4)
                    with c_save:
                        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                        if st.button("💾 Kaydet", use_container_width=True, key=f"btn_kaydet_{yeni_idx}"):
                            try:
                                with open(txt_yolu, "w", encoding="utf-8") as f:
                                    f.write(duzenlenen)
                                # edit_key'i kaydedilen değerle güncelle (rerun olmadan state sync)
                                st.session_state[f"prompt_edit_{yeni_idx}"] = duzenlenen
                                st.session_state[bildirim_key] = ("ok", "✅ Kaydedildi!")
                            except Exception as e:
                                st.session_state[bildirim_key] = ("error", f"❌ Kaydedilemedi: {e}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c_reload2:
                        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
                        if st.button("↺ Geri Al", use_container_width=True, key=f"btn_geral_{yeni_idx}"):
                            st.session_state.pop(f"prompt_edit_{yeni_idx}", None)
                            ver = st.session_state.get(f"prompt_widget_ver_{yeni_idx}", 0)
                            st.session_state[f"prompt_widget_ver_{yeni_idx}"] = ver + 1
                            st.session_state[bildirim_key] = ("ok", "↺ Orijinal içeriğe döndürüldü.")
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c_tr:
                        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
                        _ceviri_yukleniyor = st.session_state.get(f"ceviri_yukleniyor_{yeni_idx}", False)
                        if st.button("🇹🇷 Çevir", use_container_width=True, key=f"btn_cevir_{yeni_idx}", disabled=_ceviri_yukleniyor):
                            api_key = st.session_state.settings.get("gemini_api_key", "").strip()
                            if not api_key:
                                st.session_state[bildirim_key] = ("warn", "⚠️ Çeviri için Ayarlar'dan Gemini API Key girin.")
                            elif not _GENAI_OK:
                                st.session_state[bildirim_key] = ("error", "❌ google-genai paketi yüklü değil.")
                            else:
                                st.session_state[f"ceviri_yukleniyor_{yeni_idx}"] = True
                                st.session_state[f"ceviri_metin_{yeni_idx}"] = st.session_state.get(f"prompt_edit_{yeni_idx}", duzenlenen)
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c_del:
                        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                        if st.button("🗑️ Sil", use_container_width=True, key="fileman_del"):
                            try:
                                import shutil as _shutil
                                _shutil.rmtree(os.path.dirname(txt_yolu))
                                new_idx = max(0, yeni_idx - 1)
                                st.session_state["fileman_file_idx"] = new_idx
                                st.session_state.pop(ceviri_key, None)
                                st.session_state.pop(f"prompt_edit_{yeni_idx}", None)
                                st.session_state.pop(f"prompt_widget_ver_{yeni_idx}", None)
                                st.session_state.pop(bildirim_key, None)
                                st.session_state.ek_dialog_open = "dosya_yoneticisi"
                                st.rerun()
                            except Exception as e:
                                st.session_state[bildirim_key] = ("error", f"❌ Silinemedi: {e}")
                        st.markdown('</div>', unsafe_allow_html=True)

                    # ── Çeviri işlemi (buton bloğu DIŞINDA — buton çoğalmasını önler)
                    if st.session_state.get(f"ceviri_yukleniyor_{yeni_idx}", False):
                        with st.spinner("Çevriliyor..."):
                            try:
                                api_key = st.session_state.settings.get("gemini_api_key", "").strip()
                                client_tr = _genai.Client(api_key=api_key)
                                metin_cevrilecek = st.session_state.pop(f"ceviri_metin_{yeni_idx}", duzenlenen)
                                resp_tr = client_tr.models.generate_content(
                                    model="gemini-2.0-flash",
                                    contents=f"Aşağıdaki İngilizce prompt metnini Türkçeye çevir. Sadece çeviriyi yaz, başka hiçbir şey ekleme:\n\n{metin_cevrilecek}"
                                )
                                st.session_state[ceviri_key] = resp_tr.text
                                st.session_state[bildirim_key] = ("ok", "✅ Çeviri tamamlandı.")
                            except Exception as ex:
                                st.session_state[bildirim_key] = ("error", f"❌ Çeviri hatası: {ex}")
                        del st.session_state[f"ceviri_yukleniyor_{yeni_idx}"]
                        st.rerun()

                    # İşlem bildirimi — göster ve state'i temizle (bir sonraki render'da kaybolur)
                    bildirim = st.session_state.get(bildirim_key)
                    if bildirim and bildirim[0] not in ("copy_pending",):
                        tip, mesaj = bildirim
                        st.session_state.pop(bildirim_key, None)
                        # Sadece Kaydedildi mesajını göster; çeviri/geri al bildirimleri sessiz geçer
                        _goster = tip in ("error", "warn") or (tip == "ok" and "Kaydedildi" in mesaj)
                        if _goster:
                            _bildirim_ph = st.empty()
                            if tip == "ok":
                                _bildirim_ph.success(mesaj)
                            elif tip == "error":
                                _bildirim_ph.error(mesaj)
                            elif tip == "warn":
                                _bildirim_ph.warning(mesaj)
                            time.sleep(2.5)
                            _bildirim_ph.empty()

                    # Çeviri varsa göster + kapatma butonu
                    if st.session_state.get(ceviri_key):
                        st.markdown("---")
                        col_ceviri_title, col_ceviri_kapat = st.columns([0.8, 0.2])
                        with col_ceviri_title:
                            st.markdown("**🇹🇷 Türkçe Çeviri:**")
                        with col_ceviri_kapat:
                            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                            if st.button("✖ Kapat", use_container_width=True, key=f"btn_ceviri_kapat_{yeni_idx}"):
                                st.session_state.pop(ceviri_key, None)
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        st.text_area("", value=st.session_state[ceviri_key], height=280, key=f"prompt_ceviri_area_{yeni_idx}", label_visibility="collapsed")
                else:
                    st.info("Henüz oluşturulmuş prompt bulunamadı.")
            else:
                st.warning("Prompt klasörü yolu geçersiz veya ayarlanmamış.")

        # Medya kategorileri: video / görsel
        else:
            if hedef_klasor and os.path.exists(hedef_klasor):
                dosyalar = []
                for root, _, files in os.walk(hedef_klasor):
                    for file in files:
                        if file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                            tam_yol = os.path.join(root, file)
                            rel_yol = os.path.relpath(tam_yol, hedef_klasor)
                            dosyalar.append((rel_yol, tam_yol))
                
                dosyalar.sort(key=lambda x: natural_sort_key(x[0]))
                
                if dosyalar:
                    # Her dosya = bir öğe; alt klasör adı kullanılmaz.
                    # "Oluşturulan Görseller" → Görsel 1, Görsel 2, ...
                    # "Klon Görseller"        → Görsel 1, Görsel 2, ...
                    # "Üretilen Videolar"     → Video 1, Video 2, ...
                    # Diğerleri              → dosya adı
                    _is_gorsel_cat = secilen_kategori in ("🖼️ Oluşturulan Görseller", "🎨 Klon Görseller")
                    _is_video_cat  = secilen_kategori in ("🎬 Üretilen Videolar",) or "Video" in secilen_kategori

                    etiketler = []
                    for idx, (rel_yol, _) in enumerate(dosyalar, start=1):
                        if _is_gorsel_cat:
                            etiketler.append(f"Görsel {idx}")
                        elif _is_video_cat:
                            etiketler.append(f"Video {idx}")
                        else:
                            isim = os.path.splitext(os.path.basename(rel_yol))[0]
                            etiketler.append(isim[:37] + "..." if len(isim) > 40 else isim)


                    mevcut_idx = st.session_state.get("fileman_file_idx", 0)
                    if mevcut_idx >= len(dosyalar):
                        mevcut_idx = 0

                    secilen_etiket = st.selectbox(
                        f"Dosya Seçin: ({len(dosyalar)} dosya)",
                        options=etiketler,
                        index=mevcut_idx,
                        key="fileman_file_sel"
                    )
                    yeni_idx = etiketler.index(secilen_etiket)
                    st.session_state["fileman_file_idx"] = yeni_idx

                    secilen_dosya_rel, secilen_dosya_tam = dosyalar[yeni_idx]
                    ext = os.path.splitext(secilen_dosya_tam)[1].lower()

                    st.markdown("---")
                    try:
                        if ext in ['.mp4', '.mov', '.avi', '.mkv']: st.video(secilen_dosya_tam)
                        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']: st.image(secilen_dosya_tam, use_container_width=True)
                    except Exception: st.error("Önizleme yüklenemedi.")

                    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                    if st.button(f"🗑️ '{os.path.basename(secilen_dosya_rel)}' Sil", use_container_width=True, key="fileman_del"):
                        try:
                            ust_klasor = os.path.dirname(secilen_dosya_tam)
                            silinen_klasor_adi = os.path.basename(ust_klasor)
                            
                            # Her zaman sadece spesifik dosyayı sil
                            if os.path.exists(secilen_dosya_tam):
                                os.remove(secilen_dosya_tam)
                            
                            # Eğer dosya silindikten sonra ebeveyn klasör güvenliyse ve tamamen boşaldıysa temizle
                            if ust_klasor != hedef_klasor and os.path.isdir(ust_klasor):
                                try:
                                    if not os.listdir(ust_klasor):
                                        os.rmdir(ust_klasor)
                                except: pass

                            # Görsel Analiz + Klon Görsel session state'lerini temizle
                            if secilen_kategori in ("🖼️ Görsel Analiz", "🎨 Klon Görseller"):
                                for k in list(st.session_state.keys()):
                                    if k in ("gorsel_analiz_klasor_sec",) or k.startswith(f"sel_{silinen_klasor_adi}"):
                                        del st.session_state[k]
                            st.session_state["fileman_file_idx"] = max(0, yeni_idx - 1)
                            st.session_state.ek_dialog_open = "dosya_yoneticisi"
                            st.success("Dosya silindi!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Silinemedi: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else: st.info("Bu klasörde desteklenen medya dosyası bulunamadı.")
            else: st.warning("Klasör yolu geçersiz veya ayarlanmamış.")

    with tab2:
        st.caption("Klasörleri ve TXT dosyalarını topluca temizler.")
        mode = st.radio("Mod",["🧩 Tekli Dosya Temizle", "🗑️ Tüm Dosyaları Temizle"], horizontal=True, key="cleaner_mode_radio")
        if mode.startswith("🧩"):
            s = st.session_state.settings
            # Sıralama: İncele & Seçerek Sil ile aynı
            montaj_entries = _list_entries(s.get("video_montaj_output_dir"))
            pick_montaj = st.multiselect("🎞️ Montaj Videoları", [e[0] for e in montaj_entries])
            video_entries = _list_media_files_clean(s.get("video_output_dir"))
            pick_video = st.multiselect("🎬 Üretilen Videolar", [e[0] for e in video_entries])
            prompt_entries = _list_entries(s.get("prompt_dir"))
            pick_prompt = st.multiselect("📝 Promptlar", [e[0] for e in prompt_entries])
            gorsel_olustur_entries = _list_media_files_clean(s.get("gorsel_olustur_dir"))
            pick_gorsel_olustur = st.multiselect("🖼️ Oluşturulan Görseller", [e[0] for e in gorsel_olustur_entries])
            klon_entries = _list_media_files_clean(s.get("klon_gorsel_dir"))
            pick_klon = st.multiselect("🎨 Klon Görseller", [e[0] for e in klon_entries])
            gorsel_analiz_entries = _list_media_files_clean(s.get("gorsel_analiz_dir"))
            pick_gorsel_analiz = st.multiselect("🖼️ Görsel Analiz", [e[0] for e in gorsel_analiz_entries])
            indir_entries = _list_entries(s.get("download_dir"))
            pick_indir = st.multiselect("⬇️ İndirilen Videolar", [e[0] for e in indir_entries])

            # ── Görsel Klonlama TXT
            gorsel_duzelt_data = gorsel_duzelt_oku()
            gorsel_duzelt_options = [f"Görsel {no}: \"{val}\"" for no, val in sorted(gorsel_duzelt_data.items())]
            pick_gorsel_duzelt = st.multiselect("🎨 Görsel Klonlama TXT", gorsel_duzelt_options)

            # ── Prompt Düzeltme TXT
            prompt_duzelt_data = prompt_duzeltme_oku()
            prompt_duzelt_options = [f"Prompt Düzeltme {no}" for no in sorted(prompt_duzelt_data.keys())]
            pick_prompt_duzelt = st.multiselect("✏️ Prompt Düzeltme TXT", prompt_duzelt_options)

            # ── Video Link Listesi TXT
            links_file_path = s.get("links_file", "")
            video_link_options = []
            if links_file_path and os.path.exists(links_file_path):
                try:
                    with open(links_file_path, "r", encoding="utf-8") as f:
                        video_link_options = [f"İndirilecek Video Link {i+1}" for i, l in enumerate(f.read().splitlines()) if l.strip()]
                except Exception: pass
            pick_video_links = st.multiselect("📎 Video Link Listesi TXT", video_link_options)

            # ── Eklenen Videolar
            added_video_entries = _list_entries(s.get("added_video_dir"))
            pick_added_video = st.multiselect("🎞️ Eklenen Videolar", [e[0] for e in added_video_entries])

            st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
            if st.button("🗑️ Seçilenleri Temizle", use_container_width=True):
                for n in pick_montaj: _delete_path({name: p for name, p, _ in montaj_entries}.get(n, ""))
                for n in pick_video: _delete_path({name: p for name, p, _ in video_entries}.get(n, ""))
                for n in pick_prompt: _delete_path({name: p for name, p, _ in prompt_entries}.get(n, ""))
                for n in pick_gorsel_olustur: _delete_path({name: p for name, p, _ in gorsel_olustur_entries}.get(n, ""))
                for n in pick_klon: _delete_path({name: p for name, p, _ in klon_entries}.get(n, ""))
                for n in pick_gorsel_analiz: _delete_path({name: p for name, p, _ in gorsel_analiz_entries}.get(n, ""))
                for n in pick_indir: _delete_path({name: p for name, p, _ in indir_entries}.get(n, ""))
                for n in pick_added_video: _delete_path({name: p for name, p, _ in added_video_entries}.get(n, ""))

                # Görsel Düzelt.txt'den seçili satırları sil
                if pick_gorsel_duzelt:
                    secili_nolar = set()
                    for item in pick_gorsel_duzelt:
                        m = re.match(r"Görsel (\d+):", item)
                        if m: secili_nolar.add(int(m.group(1)))
                    yeni_data = {no: val for no, val in gorsel_duzelt_data.items() if no not in secili_nolar}
                    gorsel_duzelt_kaydet(yeni_data)

                # İndirilecek Video.txt'den seçili linkleri sil
                if pick_video_links and links_file_path and os.path.exists(links_file_path):
                    try:
                        with open(links_file_path, "r", encoding="utf-8") as f:
                            all_links = [l for l in f.read().splitlines() if l.strip()]
                        secili_indeksler = set()
                        for item in pick_video_links:
                            m = re.match(r"İndirilecek Video Link (\d+)", item)
                            if m: secili_indeksler.add(int(m.group(1)) - 1)
                        kalan_links = [l for i, l in enumerate(all_links) if i not in secili_indeksler]
                        with open(links_file_path, "w", encoding="utf-8") as f:
                            f.write("\n".join(kalan_links) + ("\n" if kalan_links else ""))
                    except Exception as e:
                        st.error(f"Link silinemedi: {e}")

                # düzeltme.txt'den seçili Prompt bloklarını sil
                if pick_prompt_duzelt:
                    secili_nolar = set()
                    for item in pick_prompt_duzelt:
                        m = re.match(r"Prompt Düzeltme (\d+)", item)
                        if m: secili_nolar.add(int(m.group(1)))
                    yeni_data = {no: val for no, val in prompt_duzelt_data.items() if no not in secili_nolar}
                    prompt_duzeltme_kaydet(yeni_data)

                st.success("Seçili öğeler silindi.")
                st.session_state.ek_dialog_open = "dosya_yoneticisi"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            conf = st.checkbox("Evet, her şeyi sil")
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("🔥 Hepsini Temizle", use_container_width=True, disabled=not conf):
                clean_all_targets()
                log("[OK] Tüm dosyalar temizlendi.")
                st.session_state["dosya_yoneticisi_temizlendi_notice"] = "✅ Tüm dosyalar başarıyla temizlendi."
                st.session_state.ek_dialog_open = "dosya_yoneticisi"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.get("dosya_yoneticisi_temizlendi_notice"):
                st.success(st.session_state.pop("dosya_yoneticisi_temizlendi_notice"))
            
    with tab3:
        st.caption("Üretilen dosyaları dışarı çıkarın veya dışarıdan sisteme dosya ekleyin.")
        s = st.session_state.settings

        _ec_kategoriler = {
            "🎬 Üretilen Videolar": {"dir": s.get("video_output_dir", ""), "tip": "video", "prefix": "Video"},
            "🎬 Toplu Montaj Videoları": {"dir": s.get("toplu_video_output_dir", ""), "tip": "video", "prefix": "Toplu Montaj"},
            "🎞️ Montaj Videoları": {"dir": s.get("video_montaj_output_dir", ""), "tip": "video", "prefix": "Montaj"},
            "⬇️ İndirilen Videolar": {"dir": s.get("download_dir", ""), "tip": "video", "prefix": "Video"},
            "🖼️ Oluşturulan Görseller": {"dir": s.get("gorsel_olustur_dir", ""), "tip": "gorsel", "prefix": "Görsel"},
            "🎨 Klon Görseller": {"dir": s.get("klon_gorsel_dir", ""), "tip": "gorsel", "prefix": "Klon Görsel"},
            "🖼️ Görsel Analiz": {"dir": s.get("gorsel_analiz_dir", ""), "tip": "gorsel", "prefix": "Video Görsel Analiz"},
            "📝 Promptlar": {"dir": s.get("prompt_dir", ""), "tip": "prompt", "prefix": "Video Prompt"},
        }

        _ec_secilen = st.selectbox("Kategori Seçin:", list(_ec_kategoriler.keys()), key="ec_kategori")
        _ec_info = _ec_kategoriler[_ec_secilen]
        _ec_hedef = _ec_info["dir"]
        _ec_tip = _ec_info["tip"]
        _ec_prefix = _ec_info["prefix"]

        _ec_islem = st.radio("İşlem:", ["📤 Çıkar (Kopyala)", "📥 Ekle"], horizontal=True, key="ec_islem")

        # ── ÇIKAR (Kopyala) ──
        if _ec_islem.startswith("📤"):
            st.markdown("**Seçili kategorideki tüm desteklenen medya dosyalarını kopyalayın.**")
            if _ec_hedef and os.path.exists(_ec_hedef):
                _ec_medya_dosyalari = _list_media_files_clean(_ec_hedef)
                _ec_secenekler_mapper = {g: t for g, t, _ in _ec_medya_dosyalari}
                
                if _ec_secenekler_mapper:
                    _ec_secenekler = ["Tümü"] + list(_ec_secenekler_mapper.keys())
                    _ec_secim = st.multiselect("Çıkarılacak öğeleri seçin:", _ec_secenekler, default=["Tümü"], key="ec_cikar_secim")

                    # ── Hedef klasör seçimi (tkinter native pencere) ──
                    st.markdown("**📁 Hedef klasör seçin:**")
                    _ec_yol_ph = st.empty()
                    
                    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
                    if st.button("📂 Klasör Seç", use_container_width=True, key="ec_cikar_klasor_sec_btn"):
                        try:
                            import tkinter as tk
                            from tkinter import filedialog
                            _tk_root = tk.Tk()
                            _tk_root.withdraw()
                            _tk_root.attributes("-topmost", True)
                            _secilen = filedialog.askdirectory(title="Hedef Klasör Seçin", initialdir=st.session_state.get("ec_secili_hedef_yol", os.path.join(os.path.expanduser("~"), "Desktop")))
                            _tk_root.destroy()
                            if _secilen:
                                st.session_state["ec_secili_hedef_yol"] = _secilen
                        except Exception as e:
                            st.error(f"Klasör seçici açılamadı: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)

                    _ec_hedef_yol = st.session_state.get("ec_secili_hedef_yol", os.path.join(os.path.expanduser("~"), "Desktop"))
                    _ec_yol_ph.text_input("", value=_ec_hedef_yol, disabled=True, label_visibility="collapsed")

                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                    if st.button("📤 Kopyala", use_container_width=True, key="ec_cikar_btn"):
                        if not _ec_hedef_yol or not _ec_hedef_yol.strip():
                            st.error("Hedef klasör yolu boş olamaz!")
                        else:
                            try:
                                hedef_ana = os.path.join(_ec_hedef_yol.strip(), _ec_secilen.split(" ", 1)[-1].strip())
                                os.makedirs(hedef_ana, exist_ok=True)
                                kopyalanan = 0
                                if "Tümü" in _ec_secim:
                                    _ec_kopyala_listesi = _ec_medya_dosyalari
                                else:
                                    _ec_kopyala_listesi = [(l, p, d) for l, p, d in _ec_medya_dosyalari if l in _ec_secim]
                                for medya_etiketi, dosya_yolu, is_dir in _ec_kopyala_listesi:
                                    if not os.path.isfile(dosya_yolu): continue
                                    ext = os.path.splitext(dosya_yolu)[1]
                                    temiz_ad = "".join(c for c in medya_etiketi if c.isalnum() or c in (' ', '_', '-')).strip()
                                    hedef_dosya = os.path.join(hedef_ana, f"{temiz_ad}{ext}")
                                    sayac = 1
                                    while os.path.exists(hedef_dosya):
                                        hedef_dosya = os.path.join(hedef_ana, f"{temiz_ad}_{sayac}{ext}")
                                        sayac += 1
                                    shutil.copy2(dosya_yolu, hedef_dosya)
                                    kopyalanan += 1
                                st.success(f"✅ {kopyalanan} öğe '{hedef_ana}' konumuna kopyalandı!")
                                log(f"[INFO] Çıkar: {kopyalanan} öğe '{hedef_ana}' konumuna kopyalandı.")
                            except Exception as e:
                                st.error(f"❌ Kopyalama hatası: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("Bu kategoride henüz öğe bulunmuyor.")
            else:
                st.warning("Klasör yolu geçersiz veya mevcut değil.")

        # ── EKLE ──
        else:
            st.markdown("**Dışarıdan dosya seçerek sisteme ekleyin.**")

            if _ec_tip == "video":
                _ec_uzantilar = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
                _ec_aciklama = "Video dosyası seçin (.mp4, .mov, .avi, .mkv, .webm)"
                _ec_st_type = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm"]
            elif _ec_tip == "gorsel":
                _ec_uzantilar = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
                _ec_aciklama = "Görsel dosyası seçin (.jpg, .png, .bmp, .webp)"
                _ec_st_type = ["image/jpeg", "image/png", "image/bmp", "image/webp"]
            else:  # prompt
                _ec_uzantilar = [".txt"]
                _ec_aciklama = "Prompt dosyası seçin (.txt)"
                _ec_st_type = ["text/plain"]

            _ec_yuklenen = st.file_uploader(_ec_aciklama, type=[u.lstrip(".") for u in _ec_uzantilar], accept_multiple_files=True, key="ec_ekle_upload")

            # Alternatif: dosya seçici penceresiyle ekle
            st.markdown("**veya** dosya seçici ile seçin:")
            _ec_ekle_yol_ph = st.empty()
            
            st.markdown('<div class="btn-info">', unsafe_allow_html=True)
            if st.button("📂 Dosya Seç", use_container_width=True, key="ec_ekle_dosya_sec_btn"):
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    _tk_root = tk.Tk()
                    _tk_root.withdraw()
                    _tk_root.attributes("-topmost", True)
                    if _ec_tip == "video":
                        _filetypes = [("Video Dosyaları", "*.mp4 *.mov *.avi *.mkv *.webm"), ("Tüm Dosyalar", "*.*")]
                    elif _ec_tip == "gorsel":
                        _filetypes = [("Görsel Dosyaları", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Tüm Dosyalar", "*.*")]
                    else:
                        _filetypes = [("Metin Dosyaları", "*.txt"), ("Tüm Dosyalar", "*.*")]
                    _secilen_dosyalar = filedialog.askopenfilenames(title="Dosya Seçin", filetypes=_filetypes)
                    _tk_root.destroy()
                    if _secilen_dosyalar:
                        st.session_state["ec_secili_kaynak_yol"] = ";".join(_secilen_dosyalar)
                except Exception as e:
                    st.error(f"Dosya seçici açılamadı: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

            _ec_kaynak_yol = st.session_state.get("ec_secili_kaynak_yol", "")
            _ec_ekle_yol_ph.text_input("", value=_ec_kaynak_yol, disabled=True, label_visibility="collapsed", placeholder="Dosya veya klasör seçin...")

            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("📥 Ekle & Kaydet", use_container_width=True, key="ec_ekle_btn"):
                if not _ec_hedef:
                    st.error("Hedef klasör ayarlanmamış!")
                else:
                    try:
                        os.makedirs(_ec_hedef, exist_ok=True)
                        eklenen = 0

                        def _ec_sonraki_klasor_no(hedef_dir, prefix):
                            """Mevcut klasörlere bakarak bir sonraki numarayı bulur."""
                            mevcut_nolar = []
                            if os.path.exists(hedef_dir):
                                for item in os.listdir(hedef_dir):
                                    if os.path.isdir(os.path.join(hedef_dir, item)):
                                        m = re.match(rf"^{re.escape(prefix)}\s+(\d+)$", item)
                                        if m:
                                            mevcut_nolar.append(int(m.group(1)))
                            return max(mevcut_nolar, default=0) + 1

                        # Streamlit file_uploader'dan gelen dosyalar
                        if _ec_yuklenen:
                            for dosya in _ec_yuklenen:
                                no = _ec_sonraki_klasor_no(_ec_hedef, _ec_prefix)
                                yeni_klasor = os.path.join(_ec_hedef, f"{_ec_prefix} {no}")
                                os.makedirs(yeni_klasor, exist_ok=True)
                                if _ec_tip == "prompt":
                                    hedef_dosya = os.path.join(yeni_klasor, "prompt.txt")
                                else:
                                    hedef_dosya = os.path.join(yeni_klasor, dosya.name)
                                with open(hedef_dosya, "wb") as f:
                                    f.write(dosya.getbuffer())
                                eklenen += 1

                        # Dosya seçici ile seçilen dosyaları ekleme (;-separated yollar)
                        if _ec_kaynak_yol and _ec_kaynak_yol.strip():
                            _ec_kaynak_listesi = [p.strip() for p in _ec_kaynak_yol.split(";") if p.strip()]
                            for kaynak in _ec_kaynak_listesi:
                                if os.path.isfile(kaynak):
                                    ext = os.path.splitext(kaynak)[1].lower()
                                    if ext in _ec_uzantilar:
                                        no = _ec_sonraki_klasor_no(_ec_hedef, _ec_prefix)
                                        yeni_klasor = os.path.join(_ec_hedef, f"{_ec_prefix} {no}")
                                        os.makedirs(yeni_klasor, exist_ok=True)
                                        if _ec_tip == "prompt":
                                            hedef_dosya = os.path.join(yeni_klasor, "prompt.txt")
                                        else:
                                            hedef_dosya = os.path.join(yeni_klasor, os.path.basename(kaynak))
                                        shutil.copy2(kaynak, hedef_dosya)
                                        eklenen += 1
                                elif os.path.isdir(kaynak):
                                    for dosya_adi in sorted(os.listdir(kaynak)):
                                        dosya_yolu = os.path.join(kaynak, dosya_adi)
                                        if os.path.isfile(dosya_yolu):
                                            ext = os.path.splitext(dosya_adi)[1].lower()
                                            if ext in _ec_uzantilar:
                                                no = _ec_sonraki_klasor_no(_ec_hedef, _ec_prefix)
                                                yeni_klasor = os.path.join(_ec_hedef, f"{_ec_prefix} {no}")
                                                os.makedirs(yeni_klasor, exist_ok=True)
                                                if _ec_tip == "prompt":
                                                    hedef_dosya = os.path.join(yeni_klasor, "prompt.txt")
                                                else:
                                                    hedef_dosya = os.path.join(yeni_klasor, dosya_adi)
                                                shutil.copy2(dosya_yolu, hedef_dosya)
                                                eklenen += 1
                            if eklenen == 0 and _ec_kaynak_listesi:
                                st.warning("Seçilen dosyalar arasında uygun uzantılı dosya bulunamadı.")

                        if eklenen > 0:
                            st.success(f"✅ {eklenen} dosya '{_ec_prefix} N' klasörlerine eklendi!")
                            log(f"[INFO] Ekle: {eklenen} dosya '{_ec_hedef}' altına eklendi.")
                        elif not _ec_yuklenen and not (_ec_kaynak_yol and _ec_kaynak_yol.strip()):
                            st.warning("Lütfen dosya yükleyin veya kaynak yolu girin.")
                    except Exception as e:
                        st.error(f"❌ Ekleme hatası: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("❌ Kapat", use_container_width=True, key="close_fileman"):
        st.session_state.ek_dialog_open = None
        clear_dialog_states()
        st.rerun()

def render_durum_ozeti_modal():
    """Durum özetini mevcut görünümü koruyarak parent DOM'a overlay olarak enjekte eder."""
    ozet = st.session_state.durum_ozeti
    hatali = ozet.get("hatali", [])
    kismi = ozet.get("kismi", [])
    basarili = ozet.get("basarili", [])

    hatali_html = ""
    if hatali:
        rows = "".join([
            f'<div class="do-row do-row-err"><span class="do-lbl">{item["islem"]}</span>'
            f'<span class="do-badge do-badge-err">{item.get("detay", "Başarısız")}</span></div>'
            for item in hatali
        ])
        hatali_html = (
            '<div class="do-sec">'
            '<div class="do-sec-title do-title-red"><span class="do-dot do-dot-red"></span>Hatalı İşlemler</div>'
            + rows + '</div>'
        )

    kismi_html = ""
    if kismi:
        rows = "".join([
            f'<div class="do-row do-row-partial"><span class="do-lbl">{item["islem"]}</span>'
            f'<span class="do-badge do-badge-partial">{item.get("detay", "Kısmi Tamamlandı")}</span></div>'
            for item in kismi
        ])
        kismi_html = (
            '<div class="do-sec">'
            '<div class="do-sec-title do-title-orange"><span class="do-dot do-dot-orange"></span>Kısmi Tamamlananlar</div>'
            + rows + '</div>'
        )

    basarili_html = ""
    if basarili:
        rows = "".join([
            f'<div class="do-row do-row-ok"><span class="do-lbl">{item["islem"]}</span>'
            f'<span class="do-badge do-badge-ok">{item.get("detay", "Tamamlandı")}</span></div>'
            for item in basarili
        ])
        basarili_html = (
            '<div class="do-sec">'
            '<div class="do-sec-title do-title-green"><span class="do-dot do-dot-green"></span>Başarılı İşlemler</div>'
            + rows + '</div>'
        )

    bos_html = ""
    if not hatali and not kismi and not basarili:
        bos_html = '<div style="padding:24px 0;text-align:center;color:rgba(255,255,255,0.35);font-size:13px;">⏳ Henüz tamamlanmış işlem bulunmuyor.</div>'

    css_text = """
#do-style-anchor{}
#do-overlay{
  position:fixed;inset:0;z-index:99999;
  background:rgba(0,0,0,0.40);
  display:flex;align-items:center;justify-content:center;
  animation:do-fade 0.15s ease;
}
@keyframes do-fade{from{opacity:0}to{opacity:1}}
#do-modal{
  background:#111118;
  border:1px solid rgba(255,255,255,0.13);
  border-radius:18px;
  width:480px;max-width:92vw;
  max-height:82vh;
  overflow:hidden;
  display:flex;flex-direction:column;
  box-shadow:0 24px 64px rgba(0,0,0,0.80);
  animation:do-up 0.18s ease;
}
@keyframes do-up{from{transform:translateY(14px);opacity:0}to{transform:translateY(0);opacity:1}}
#do-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;
  border-bottom:1px solid rgba(255,255,255,0.08);
  background:rgba(255,255,255,0.025);
  flex-shrink:0;
}
#do-title{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:700;color:#f1f5f9;}
#do-xbtn{
  width:28px;height:28px;border-radius:8px;border:none;
  background:transparent;color:#64748b;font-size:15px;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
}
#do-xbtn:hover{background:rgba(255,255,255,0.08);color:#f1f5f9;}
#do-body{padding:20px;overflow-y:auto;flex:1;}
#do-body::-webkit-scrollbar{width:4px;}
#do-body::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.12);border-radius:99px;}
.do-sec{margin-bottom:18px;}
.do-sec:last-child{margin-bottom:0;}
.do-sec-title{display:flex;align-items:center;gap:6px;font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase;margin-bottom:8px;}
.do-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;}
.do-dot-red{background:#ef4444;}.do-title-red{color:#ef4444;}
.do-dot-orange{background:#f59e0b;}.do-title-orange{color:#f59e0b;}
.do-dot-green{background:#22c55e;}.do-title-green{color:#22c55e;}
.do-row{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-radius:12px;margin-bottom:7px;}
.do-row:last-child{margin-bottom:0;}
.do-lbl{font-size:13px;color:#e0e0e0;}
.do-badge{font-size:10px;font-family:monospace;white-space:nowrap;}
.do-row-err{background:rgba(239,68,68,0.05);border:1px solid rgba(239,68,68,0.20);}
.do-badge-err{color:rgba(255,255,255,0.45);}
.do-row-partial{background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.22);}
.do-badge-partial{color:rgba(251,191,36,0.9);}
.do-row-ok{background:rgba(34,197,94,0.05);border:1px solid rgba(34,197,94,0.12);}
.do-badge-ok{color:rgba(34,197,94,0.75);}
#do-footer{
  padding:14px 20px;
  border-top:1px solid rgba(255,255,255,0.07);
  background:rgba(255,255,255,0.02);
  flex-shrink:0;
}
#do-kapat{
  width:100%;padding:10px;
  background:rgba(99,102,241,0.20);
  color:#818cf8;
  border:1px solid rgba(99,102,241,0.28);
  border-radius:12px;
  font-size:14px;font-weight:700;
  cursor:pointer;font-family:inherit;
}
#do-kapat:hover{background:rgba(99,102,241,0.35);color:#c7d2fe;}
"""

    overlay_html = f"""
<div id="do-overlay">
  <div id="do-modal">
    <div id="do-header">
      <div id="do-title">🔄 İşlem Detayları</div>
      <button id="do-xbtn" type="button">✕</button>
    </div>
    <div id="do-body">
      {bos_html}{hatali_html}{kismi_html}{basarili_html}
    </div>
    <div id="do-footer">
      <button id="do-kapat" type="button">Kapat</button>
    </div>
  </div>
</div>
"""

    bridge_script = f"""
<script>
(function(){{
  var pdoc = window.parent.document;
  var cssText = {json.dumps(css_text)};
  var overlayHtml = {json.dumps(overlay_html)};

  function hideKapatGizliBtn() {{
    try {{
      var btns = pdoc.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {{
        if (btns[i].innerText && btns[i].innerText.trim() === 'kapat_gizli') {{
          var wrapper = btns[i].closest('[data-testid=\"stButton\"]');
          if (wrapper) wrapper.style.display = 'none';
          btns[i].style.display = 'none';
        }}
      }}
    }} catch(e) {{}}
  }}

  function tryClickHidden() {{
    try {{
      var btns = pdoc.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {{
        if (btns[i].innerText && btns[i].innerText.trim() === 'kapat_gizli') {{
          btns[i].click();
          return true;
        }}
      }}
    }} catch(e) {{}}
    return false;
  }}

  function removeInjectedModal() {{
    try {{
      var ov = pdoc.getElementById('do-overlay');
      if (ov) ov.remove();
      var stl = pdoc.getElementById('do-style');
      if (stl) stl.remove();
    }} catch(e) {{}}
  }}

  function handleKapat() {{
    removeInjectedModal();
    tryClickHidden();
  }}

  hideKapatGizliBtn();
  setTimeout(hideKapatGizliBtn, 40);
  setTimeout(hideKapatGizliBtn, 180);

  removeInjectedModal();

  var styleEl = pdoc.createElement('style');
  styleEl.id = 'do-style';
  styleEl.textContent = cssText;
  pdoc.head.appendChild(styleEl);

  var tmp = pdoc.createElement('div');
  tmp.innerHTML = overlayHtml;
  if (tmp.firstElementChild) {{
    pdoc.body.appendChild(tmp.firstElementChild);
  }}

  var overlay = pdoc.getElementById('do-overlay');
  var kapatBtn = pdoc.getElementById('do-kapat');
  var xBtn = pdoc.getElementById('do-xbtn');

  if (overlay) {{
    overlay.addEventListener('click', function(e) {{
      if (e.target === overlay) handleKapat();
    }});
  }}
  if (kapatBtn) {{
    kapatBtn.addEventListener('click', function(e) {{
      e.preventDefault();
      handleKapat();
    }});
  }}
  if (xBtn) {{
    xBtn.addEventListener('click', function(e) {{
      e.preventDefault();
      handleKapat();
    }});
  }}

  try {{
    if (pdoc._doEscHandler) pdoc.removeEventListener('keydown', pdoc._doEscHandler);
  }} catch(e) {{}}
  pdoc._doEscHandler = function(e) {{
    if (e.key === 'Escape') handleKapat();
  }};
  pdoc.addEventListener('keydown', pdoc._doEscHandler);
}})();
</script>
"""

    with st.sidebar:
        _st_components.html(bridge_script, height=0)
        if st.button("kapat_gizli", key="do_kapat_hidden"):
            st.session_state.durum_ozeti_dialog_open = False
            st.rerun()

@st.dialog("📂 Ek İşlemler", width="small")
def ek_islemler_menu_dialog():
    secs = st.session_state.ek_batch_secimler
    is_batch = st.session_state.get("batch_mode", False)
    is_running = any_running()

    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("📺 YouTube'dan Liste Oluştur", key="dlg_btn_youtube_link", use_container_width=True, disabled=is_ui_locked()):
        st.session_state.ek_dialog_open = "youtube_link"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
    if st.button("📎 Video Listesi Ekle", key="dlg_btn_video_listesi", use_container_width=True, disabled=is_ui_locked()):
        st.session_state.ek_dialog_open = "video_listesi"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("🎞️ Video Ekle", key="dlg_btn_video_ekle", use_container_width=True, disabled=is_ui_locked()):
        st.session_state.ek_dialog_open = "video_ekle"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("☑️ İşaretlenenler **Tümünü Çalıştır**'a dahil edilir")

    c_chk, c_btn = st.columns([0.12, 0.88])
    with c_chk:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["video_indir"] = st.checkbox("Video İndir seçimi", value=secs.get("video_indir", True), key="chk_video_indir", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("⬇️ Video İndir", key="dlg_btn_video_indir", use_container_width=True, disabled=is_batch or is_running):
            st.session_state.ek_dialog_open = "menu"
            st.session_state.single_paused = False
            st.session_state.single_finish_requested = False
            st.session_state.single_mode = True
            st.session_state.single_step = "download"
            cleanup_flags()
            st.session_state.status["download"] = "running"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    c_chk2, c_btn2 = st.columns([0.12, 0.88])
    with c_chk2:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["gorsel_analiz"] = st.checkbox("Görsel Analiz seçimi", value=secs.get("gorsel_analiz", False), key="chk_gorsel_analiz", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn2:
        st.markdown('<div class="btn-teal">', unsafe_allow_html=True)
        if st.button("🖼️ Görsel Analiz", key="dlg_btn_gorsel_analiz", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "gorsel_analiz"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    c_chk3, c_btn3 = st.columns([0.12, 0.88])
    with c_chk3:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["gorsel_klonla"] = st.checkbox("Görsel Klonla seçimi", value=secs.get("gorsel_klonla", False), key="chk_gorsel_klonla", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn3:
        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
        if st.button("🎨 Görsel Klonla", key="dlg_btn_gorsel_klonla", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "gorsel_klonla"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    c_chk4, c_btn4 = st.columns([0.12, 0.88])
    with c_chk4:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["prompt_duzeltme"] = st.checkbox("Prompt Düzeltme seçimi", value=secs.get("prompt_duzeltme", False), key="chk_prompt_duzeltme", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn4:
        st.markdown('<div class="btn-purple">', unsafe_allow_html=True)
        if st.button("✏️ Prompt Düzeltme", key="dlg_btn_prompt_duzeltme", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "prompt_duzeltme"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    c_chk_go, c_btn_go = st.columns([0.12, 0.88])
    with c_chk_go:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["gorsel_olustur"] = st.checkbox("Görsel Oluştur seçimi", value=secs.get("gorsel_olustur", False), key="chk_gorsel_olustur", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn_go:
        st.markdown('<div class="btn-teal">', unsafe_allow_html=True)
        if st.button("🖼️ Görsel Oluştur", key="dlg_btn_gorsel_olustur", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "gorsel_olustur"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    c_chk5, c_btn5 = st.columns([0.12, 0.88])
    with c_chk5:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["video_montaj"] = st.checkbox("Video Montaj seçimi", value=secs.get("video_montaj", False), key="chk_video_montaj", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn5:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("🎞️ Video Montaj", key="dlg_btn_video_montaj", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "video_montaj"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    c_chk6, c_btn6 = st.columns([0.12, 0.88])
    with c_chk6:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["toplu_video"] = st.checkbox("Toplu Video seçimi", value=secs.get("toplu_video", False), key="chk_toplu_video", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn6:
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        if st.button("🎬 Toplu Video Montaj", key="dlg_btn_toplu_video", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "toplu_video"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    c_chk7, c_btn7 = st.columns([0.12, 0.88])
    with c_chk7:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["sosyal_medya"] = st.checkbox("Sosyal Medya Paylaşım seçimi", value=secs.get("sosyal_medya", False), key="chk_sosyal_medya", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn7:
        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
        if st.button("🌐 Sosyal Medya Paylaşım", key="dlg_btn_sosyal_medya", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "sosyal_medya"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="btn-purple">', unsafe_allow_html=True)
    if st.button("✏️ Prompt Ayarları", key="dlg_btn_prompt_ayar", use_container_width=True, disabled=is_ui_locked()):
        st.session_state.ek_dialog_open = "prompt_ayarlari"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="btn-purple">', unsafe_allow_html=True)
    if st.button("🎬 Video Ayarları", key="dlg_btn_video_ayar", use_container_width=True, disabled=is_ui_locked()):
        st.session_state.ek_dialog_open = "video_ayarlari"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("💳 Video Üretme Kredisi", key="dlg_btn_kredi", use_container_width=True, disabled=is_running):
        st.session_state.ek_dialog_open = "kredi"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    globals().get("render_dialog_single_controls", lambda **kwargs: None)(step_match="download", prefix="dlg_menu")
    if st.button("❌ Pencereyi Kapat", key="close_dlg_menu", use_container_width=True):
        clear_dialog_states()
        st.rerun()


# --- PATCH_YOUTUBE_LINK_DIALOG_STABLE_V2 ---
@st.dialog("📺 YouTube'dan Liste Oluştur", width="large")
def youtube_link_dialog():
    st.caption("YouTube kanal / sayfa linklerini alt alta girin. Video türüne ve seçim türüne göre linkler otomatik olarak kaydedilir.")

    if "dlg_youtube_link_input_multi" not in st.session_state:
        st.session_state["dlg_youtube_link_input_multi"] = st.session_state.get("youtube_link_input_multi", "")
    if "dlg_youtube_link_video_type" not in st.session_state:
        st.session_state["dlg_youtube_link_video_type"] = st.session_state.get("youtube_link_video_type", "Video")
    if "dlg_youtube_link_mode" not in st.session_state:
        st.session_state["dlg_youtube_link_mode"] = st.session_state.get("youtube_link_mode", "En popüler videolar")

    yt_links_text = st.text_area(
        "YouTube kanal / sayfa linkleri:",
        height=120,
        key="dlg_youtube_link_input_multi",
        placeholder="Her satıra bir kanal / sayfa linki girin",
    )

    kanal_linkleri = [line.strip() for line in (yt_links_text or "").splitlines() if line.strip()]

    yt_video_type = st.selectbox(
        "Video Türü:",
        options=["Video", "Shorts Video"],
        key="dlg_youtube_link_video_type",
    )

    yt_mode = st.selectbox(
        "Seçim Türü:",
        options=["En popüler videolar", "En yeni videolar"],
        key="dlg_youtube_link_mode",
    )

    st.session_state.youtube_link_input_multi = yt_links_text or ""
    st.session_state.youtube_link_video_type = yt_video_type
    st.session_state.youtube_link_mode = yt_mode

    kanal_sayilari = []
    if kanal_linkleri:
        st.markdown("---")
        st.caption("Her kanal / sayfa için kaç video alınacağını seçin.")
        for idx, _link in enumerate(kanal_linkleri, start=1):
            sayi_key = f"dlg_youtube_count_{idx}"
            mevcut_deger = int(st.session_state.get(sayi_key, 1) or 1)
            kanal_sayilari.append(
                st.number_input(
                    f"{idx}. link için video sayısı",
                    min_value=1,
                    max_value=50,
                    value=mevcut_deger,
                    step=1,
                    key=sayi_key,
                )
            )
    else:
        st.info("Önce en az bir YouTube kanal / sayfa linki girin.")

    aktif_count_keys = {f"dlg_youtube_count_{idx}" for idx in range(1, len(kanal_linkleri) + 1)}
    for key in list(st.session_state.keys()):
        if key.startswith("dlg_youtube_count_") and key not in aktif_count_keys:
            try:
                del st.session_state[key]
            except Exception:
                pass

    st.caption("Linkleri Oluştur mevcut link listesini yeniler. Devamına Ekle ise yeni üretilen linkleri mevcut listenin sonuna ekler.")

    def _start_youtube_link_run(append_mode: bool = False):
        if not kanal_linkleri:
            st.error("Lütfen en az bir YouTube kanal / sayfa linki girin.")
            return

        secim_modu = "popular" if yt_mode == "En popüler videolar" else "recent"
        video_turu = "video" if yt_video_type == "Video" else "shorts"
        output_path = _prepare_youtube_link_output(append_mode=append_mode)

        config_payload = {
            "output": output_path,
            "mode": secim_modu,
            "video_type": video_turu,
            "entries": [
                {"url": link, "count": int(kanal_sayilari[idx - 1])}
                for idx, link in enumerate(kanal_linkleri, start=1)
            ],
        }

        config_path = save_youtube_link_config(config_payload)
        st.session_state.youtube_link_args = ["--config", config_path]
        _write_prompt_source_mode(PROMPT_SOURCE_LINK)
        set_link_canvas_source("youtube")
        st.session_state.status["input"] = "idle"
        st.session_state.ek_dialog_open = "youtube_link"
        st.session_state.single_paused = False
        st.session_state.single_finish_requested = False
        st.session_state.single_mode = True
        st.session_state.single_step = "youtube_link"
        cleanup_flags()
        st.session_state.status["youtube_link"] = "running"
        st.rerun()

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button(
            "🚀 Linkleri Oluştur",
            key="dlg_run_youtube_link",
            use_container_width=True,
            disabled=st.session_state.get("batch_mode", False) or any_running()
        ):
            _start_youtube_link_run(append_mode=False)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
        if st.button(
            "➕ Devamına Ekle",
            key="dlg_run_youtube_link_append",
            use_container_width=True,
            disabled=st.session_state.get("batch_mode", False) or any_running()
        ):
            _start_youtube_link_run(append_mode=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("⬅️ Geri", key="dlg_back_youtube_link", use_container_width=True):
            st.session_state.ek_dialog_open = "menu"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
# --- PATCH_MISSING_EK_DIALOGS_V1 ---
if "_patch_dir_has_items" not in globals():
    def _patch_dir_has_items(path: str) -> bool:
        try:
            if not path or not os.path.isdir(path):
                return False
            return any(os.path.exists(os.path.join(path, name)) for name in os.listdir(path))
        except Exception:
            return False

if "_patch_read_text" not in globals():
    def _patch_read_text(path: str) -> str:
        try:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except Exception:
            pass
        return ""

if "_patch_write_text" not in globals():
    def _patch_write_text(path: str, text: str) -> bool:
        try:
            if not path:
                return False
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception as e:
            try:
                log(f"[ERROR] Dosya yazılamadı: {e}")
            except Exception:
                pass
            return False

if "video_listesi_dialog" not in globals():
    @st.dialog("📎 Video Listesi Ekle", width="large")
    def video_listesi_dialog():
        links_path = st.session_state.settings.get("links_file", "")
        varsayilan = _patch_read_text(links_path)

        st.caption("Video linklerini alt alta ekleyin. Kaydet mevcut listeyi yeniler, Devamına Kaydet ise yeni linkleri mevcut listenin sonuna ekler.")
        text = st.text_area(
            "Video linkleri:",
            value=varsayilan,
            height=280,
            key="dlg_video_listesi_text_patch",
            placeholder="Her satıra bir video linki girin"
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("💾 Kaydet", key="dlg_video_listesi_save_patch", use_container_width=True):
                save_links(text, append=False)
                _write_prompt_source_mode(PROMPT_SOURCE_LINK)
                set_link_canvas_source("manual")
                st.session_state.status["youtube_link"] = "idle"
                st.session_state.status["input"] = "ok" if (text or "").strip() else "idle"
                st.session_state.ek_dialog_open = "video_listesi"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
            if st.button("➕ Devamına Kaydet", key="dlg_video_listesi_append_patch", use_container_width=True):
                save_links(text, append=True)
                _write_prompt_source_mode(PROMPT_SOURCE_LINK)
                set_link_canvas_source("manual")
                st.session_state.status["youtube_link"] = "idle"
                st.session_state.status["input"] = "ok" if (text or "").strip() else "idle"
                st.session_state.ek_dialog_open = "video_listesi"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="btn-info">', unsafe_allow_html=True)
            if st.button("⬅️ Geri", key="dlg_video_listesi_back_patch", use_container_width=True):
                st.session_state.ek_dialog_open = "menu"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


    @st.dialog("🎞️ Video Ekle", width="large")
    def video_ekle_dialog():
        hedef_root = _get_added_video_dir()
        mevcutlar = _list_added_video_entries()

        st.caption("Bilgisayarınızdan videoları seçin. Ekle mevcut Eklenen Video içeriğini yeniler, Devamına Ekle ise yeni videoları mevcutların sonuna Video 1, Video 2, Video 3... sırasını bozmadan ekler.")
        st.info(f"Hedef klasör: {hedef_root} | Mevcut eklenen video: {len(mevcutlar)}")
        st.caption("Not: Ekle baştan yazar, Devamına Ekle ise mevcut videoları koruyup yeni seçtiklerinizi devamına ekler.")

        secilenler = st.file_uploader(
            "Videoları seçin:",
            type=["mp4", "mov", "mkv", "webm", "avi", "m4v"],
            accept_multiple_files=True,
            key="dlg_video_ekle_files",
        )

        if secilenler:
            st.markdown("**Seçilen videolar:**")
            for idx, up in enumerate(secilenler, start=1):
                st.caption(f"{idx}. {getattr(up, 'name', f'Video {idx}')}")
        elif mevcutlar:
            st.markdown("**Klasördeki mevcut videolar:**")
            for item in mevcutlar:
                st.caption(f"{item['no']}. {item['folder_name']} → {item['video_name']}")

        def _kaydet_secilen_videolar(append_mode: bool = False):
            if not secilenler:
                st.error("Lütfen en az bir video seçin.")
                return

            try:
                os.makedirs(hedef_root, exist_ok=True)
                if append_mode:
                    baslangic_no = _get_next_added_video_index()
                else:
                    for name in os.listdir(hedef_root):
                        path = os.path.join(hedef_root, name)
                        if os.path.isdir(path):
                            shutil.rmtree(path, ignore_errors=True)
                        else:
                            try:
                                os.remove(path)
                            except Exception:
                                pass
                    _purge_prompt_state_for_prefix(hedef_root)
                    baslangic_no = 1

                for offset, up in enumerate(secilenler):
                    video_no = baslangic_no + offset
                    klasor = os.path.join(hedef_root, f"Video {video_no}")
                    os.makedirs(klasor, exist_ok=True)
                    dosya_adi = os.path.basename(str(getattr(up, "name", "") or f"video_{video_no}.mp4"))
                    if not _is_supported_video_name(dosya_adi):
                        kok, ext = os.path.splitext(dosya_adi)
                        dosya_adi = (kok or f"video_{video_no}") + (ext if ext else ".mp4")
                    with open(os.path.join(klasor, dosya_adi), "wb") as f:
                        f.write(up.getbuffer())

                _write_prompt_source_mode(PROMPT_SOURCE_ADDED_VIDEO)
                set_link_canvas_source("added_video")
                st.session_state.status["youtube_link"] = "idle"
                st.session_state.status["input"] = "ok"
                if append_mode:
                    son_no = baslangic_no + len(secilenler) - 1
                    st.session_state["video_ekle_saved_notice"] = f"Kaydedildi! {len(secilenler)} video mevcut listenin devamına eklendi (Video {baslangic_no}-Video {son_no})."
                else:
                    st.session_state["video_ekle_saved_notice"] = f"Kaydedildi! {len(secilenler)} video Eklenen Video klasörüne aktarıldı."
                st.session_state.ek_dialog_open = "video_ekle"
                st.rerun()
            except Exception as e:
                st.error(f"Video ekleme sırasında hata oluştu: {e}")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("➕ Ekle", key="dlg_video_ekle_save", use_container_width=True):
                _kaydet_secilen_videolar(append_mode=False)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
            if st.button("📎 Devamına Ekle", key="dlg_video_ekle_append", use_container_width=True):
                _kaydet_secilen_videolar(append_mode=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="btn-info">', unsafe_allow_html=True)
            if st.button("⬅️ Geri", key="dlg_video_ekle_back", use_container_width=True):
                st.session_state.ek_dialog_open = "menu"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Başarı bildirimi — butonların hemen altında göster
        if st.session_state.get("video_ekle_saved_notice"):
            st.success(st.session_state.pop("video_ekle_saved_notice"))

        st.markdown("---")
        st.markdown('<div class="btn-purple">', unsafe_allow_html=True)
        if st.button("✂️ Videoyu Bölümlerine Ayır", key="dlg_video_ekle_bolumle", use_container_width=True):
            if not secilenler or len(secilenler) != 1:
                st.error("Bölümlerine ayırmak için lütfen tek bir video seçin.")
            else:
                up = secilenler[0]
                temp_dir = os.path.join(CONTROL_DIR, "_temp_video_split")
                os.makedirs(temp_dir, exist_ok=True)
                dosya_adi = os.path.basename(str(getattr(up, "name", "") or "video.mp4"))
                temp_path = os.path.join(temp_dir, dosya_adi)
                with open(temp_path, "wb") as f:
                    f.write(up.getbuffer())
                st.session_state.video_bolum_temp_path = temp_path
                st.session_state.video_bolum_temp_name = dosya_adi
                st.session_state.video_bolum_sureler = []
                st.session_state.ek_dialog_open = "video_bolumle"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


@st.dialog("✂️ Videoyu Bölümlerine Ayır", width="large")
def video_bolumlerine_ayir_dialog():
    hedef_root = _get_added_video_dir()
    temp_path = st.session_state.get("video_bolum_temp_path")
    temp_name = st.session_state.get("video_bolum_temp_name", "video.mp4")

    # Başarı bildirimi
    if st.session_state.get("video_bolum_saved_notice"):
        _vb_ph = st.empty()
        _vb_ph.success(st.session_state.get("video_bolum_saved_notice"))
        time.sleep(2.5)
        _vb_ph.empty()
        st.session_state.pop("video_bolum_saved_notice", None)

    if not temp_path or not os.path.isfile(temp_path):
        st.error("Bölümlenecek video bulunamadı. Lütfen önce Video Ekle bölümünden bir video seçin.")
        if st.button("⬅️ Geri", key="dlg_bolum_geri_hata", use_container_width=True):
            st.session_state.ek_dialog_open = "video_ekle"
            st.rerun()
        return

    # Video süresini al
    video_suresi = _get_video_duration_seconds(temp_path)
    if video_suresi <= 0:
        st.error("Video süresi okunamadı. Lütfen geçerli bir video dosyası seçin.")
        if st.button("⬅️ Geri", key="dlg_bolum_geri_sure_hata", use_container_width=True):
            st.session_state.ek_dialog_open = "video_ekle"
            st.rerun()
        return

    st.caption(f"Seçilen video: **{temp_name}** | Toplam süre: **{_format_duration(video_suresi)}** ({video_suresi:.1f} saniye) | **{_format_mmss(video_suresi)}**")
    st.info(f"Hedef klasör: {hedef_root}")

    # Video önizleme
    try:
        st.video(temp_path)
    except Exception:
        st.warning("Önizleme yüklenemedi.")

    st.caption("Videoyu istediğiniz zaman aralıklarında bölümlerine ayırın. Her bölüm ayrı bir Video klasörüne kaydedilir.")

    # ---- Süre Seçenekleri: Otomatik bölme ----
    st.markdown("---")
    st.markdown("**⏱️ Otomatik Bölme Seçenekleri:**")
    st.caption("Bir süre seçin, video otomatik olarak o süre aralıklarında bölünecektir. Sonrasında manuel düzeltme yapabilirsiniz.")
    _sure_secenekleri = [5, 8, 10, 15, 20]
    _sure_cols = st.columns(len(_sure_secenekleri))
    for _si, _sure_sn in enumerate(_sure_secenekleri):
        with _sure_cols[_si]:
            if st.button(f"{_sure_sn}sn", key=f"dlg_otomatik_bol_{_sure_sn}", use_container_width=True):
                import math as _math
                _oto_n = _math.ceil(video_suresi / _sure_sn)
                if _oto_n < 2:
                    _oto_n = 2
                # Önce tüm eski key'leri temizle
                for _old_i in range(50):
                    for _sfx in ("_baslangic", "_bitis"):
                        _old_key = f"dlg_bolum{_sfx}_{_old_i}"
                        if _old_key in st.session_state:
                            del st.session_state[_old_key]
                # Yeni değerleri session state'e yaz
                _cursor = 0.0
                for _new_i in range(_oto_n):
                    _s = round(_cursor, 1)
                    _e = round(min(_cursor + _sure_sn, video_suresi), 1)
                    if _new_i == _oto_n - 1:
                        _e = round(video_suresi, 1)
                    st.session_state[f"dlg_bolum_baslangic_{_new_i}"] = _format_mmss(_s)
                    st.session_state[f"dlg_bolum_bitis_{_new_i}"] = _format_mmss(_e)
                    _cursor = _e
                st.session_state["dlg_bolum_sayisi"] = _oto_n
                st.session_state["_bolum_sayisi_prev"] = _oto_n
                st.session_state["_bolum_sure_secim"] = _sure_sn
                st.rerun()

    # ---- Bölüm sayısı seçimi ----
    st.markdown("---")
    # İlk açılışta varsayılan değeri session state üzerinden ata (value parametresi yerine)
    if "dlg_bolum_sayisi" not in st.session_state:
        st.session_state["dlg_bolum_sayisi"] = 2
    bolum_sayisi = st.number_input(
        "Kaç bölüme ayırmak istiyorsunuz?",
        min_value=2, max_value=50, step=1,
        key="dlg_bolum_sayisi",
    )
    n = int(bolum_sayisi)

    # Eşit dağıtım hesapla
    esit_sure = video_suresi / n

    # İlk açılış veya bölüm sayısı değişikliğinde session state'e
    # varsayılan değerleri yaz (widget oluşturulmadan ÖNCE)
    _prev_bolum = st.session_state.get("_bolum_sayisi_prev", None)
    _needs_init = (_prev_bolum is None) or (n != _prev_bolum)
    if _needs_init:
        # Önce tüm eski key'leri temizle (0..49)
        for _old_i in range(50):
            for _sfx in ("_baslangic", "_bitis"):
                _old_key = f"dlg_bolum{_sfx}_{_old_i}"
                if _old_key in st.session_state:
                    del st.session_state[_old_key]
        # Yeni eşit dağıtım değerlerini session state'e yaz
        for _new_i in range(n):
            _s = round(esit_sure * _new_i, 1)
            _e = round(esit_sure * (_new_i + 1), 1) if _new_i < n - 1 else round(video_suresi, 1)
            st.session_state[f"dlg_bolum_baslangic_{_new_i}"] = _format_mmss(_s)
            st.session_state[f"dlg_bolum_bitis_{_new_i}"] = _format_mmss(_e)
        st.session_state["_bolum_sayisi_prev"] = n
        st.session_state.pop("_bolum_sure_secim", None)
        # İlk açılış değilse (bölüm sayısı değişti) rerun yap
        if _prev_bolum is not None:
            st.rerun()
    st.session_state["_bolum_sayisi_prev"] = n

    st.markdown("---")
    st.markdown("**Bölüm Zaman Aralıklarını Belirleyin (Başlangıç — Bitiş):**")
    st.caption("Format: M:SS (orn: 1:30) veya saniye (orn: 90). Bir bölümü değiştirdiğinizde sonraki bölümler otomatik güncellenir.")

    # Önce tüm widget'ları oluştur ve değerlerini oku
    segments_raw = []  # [(baslangic_str, bitis_str), ...]
    for i in range(n):
        st.markdown(f"**Bölüm {i + 1}:**")
        col_s, col_e = st.columns(2)
        with col_s:
            baslangic_str = st.text_input(
                f"Başlangıç",
                key=f"dlg_bolum_baslangic_{i}",
                help=f"Bölüm {i+1} başlangıç zamanı (M:SS veya saniye)",
            )
        with col_e:
            bitis_str = st.text_input(
                f"Bitiş",
                key=f"dlg_bolum_bitis_{i}",
                help=f"Bölüm {i+1} bitiş zamanı (M:SS veya saniye)",
            )
        segments_raw.append((baslangic_str, bitis_str))

    # Widget'lardan okunan değerleri parse et
    segments_parsed = []
    for bs, es in segments_raw:
        segments_parsed.append((_parse_mmss(bs), _parse_mmss(es)))

    # Otomatik güncelleme: Bir bölümün bitişi değiştirildiğinde
    # sonraki bölümlerin başlangıç/bitiş değerlerini kalan süreye göre yeniden dağıt
    _needs_rerun = False
    for i in range(n - 1):
        cur_start, cur_end = segments_parsed[i]
        next_start, next_end = segments_parsed[i + 1]
        # Eğer mevcut bölümün bitişi geçerliyse ve sonraki bölümün başlangıcı farklıysa
        if cur_end >= 0 and next_start >= 0 and abs(cur_end - next_start) > 0.05:
            # Sonraki bölümleri yeniden dağıt
            kalan_sure = video_suresi - cur_end
            kalan_bolum = n - (i + 1)
            if kalan_bolum > 0 and kalan_sure > 0:
                bolum_basi = kalan_sure / kalan_bolum
                _cursor = cur_end
                for j in range(i + 1, n):
                    _s = round(_cursor, 1)
                    _e = round(_cursor + bolum_basi, 1) if j < n - 1 else round(video_suresi, 1)
                    _e = min(_e, round(video_suresi, 1))
                    st.session_state[f"dlg_bolum_baslangic_{j}"] = _format_mmss(_s)
                    st.session_state[f"dlg_bolum_bitis_{j}"] = _format_mmss(_e)
                    _cursor = _e
                _needs_rerun = True
            break  # İlk farkı bulduktan sonra dur, rerun yapacak

    if _needs_rerun:
        st.rerun()

    # Validasyon
    segments_input = []
    has_error = False
    for i, (start_sec, end_sec) in enumerate(segments_parsed):
        if start_sec < 0 or end_sec < 0:
            st.error(f"Bölüm {i+1}: Geçersiz zaman formatı. M:SS (orn: 1:30) veya saniye (orn: 90) girin.")
            has_error = True
            segments_input.append((0, 0))
        elif end_sec <= start_sec:
            st.error(f"Bölüm {i+1}: Bitiş zamanı ({_format_mmss(end_sec)}) başlangıçtan ({_format_mmss(start_sec)}) büyük olmalıdır.")
            has_error = True
            segments_input.append((start_sec, end_sec))
        elif end_sec > video_suresi + 0.5:
            st.error(f"Bölüm {i+1}: Bitiş zamanı ({_format_mmss(end_sec)}) video süresini ({_format_mmss(video_suresi)}) aşıyor.")
            has_error = True
            segments_input.append((start_sec, end_sec))
        else:
            segments_input.append((start_sec, min(end_sec, video_suresi)))

    # Çakışma kontrolü
    if not has_error and len(segments_input) > 1:
        toplam_girilen = sum(max(0, e - s) for s, e in segments_input)
        if toplam_girilen > video_suresi + 0.5:
            st.error(f"Toplam: {_format_duration(toplam_girilen)} ({_format_mmss(toplam_girilen)}) — Bölümler çakışıyor veya video süresini aşıyor!")
            has_error = True

    # Toplam süre kontrolü ve bilgi gösterimi
    toplam_girilen = sum(max(0, e - s) for s, e in segments_input)
    fark = video_suresi - toplam_girilen

    st.markdown("---")
    if has_error:
        st.error("Yukarıdaki hataları düzeltin. Hatalar giderilmeden bölme işlemi yapılamaz.")
    elif abs(fark) < 0.5:
        st.success(f"Toplam: {_format_duration(toplam_girilen)} ({_format_mmss(toplam_girilen)}) — Video süresiyle uyumlu.")
    elif fark > 0:
        st.warning(f"Toplam: {_format_duration(toplam_girilen)} ({_format_mmss(toplam_girilen)}) — Kalan {_format_duration(fark)} kapsam dışı kalacak.")
    else:
        st.error(f"Toplam: {_format_duration(toplam_girilen)} ({_format_mmss(toplam_girilen)}) — Bölümler çakışıyor veya video süresini aşıyor!")
        has_error = True

    # Önizleme tablosu - widget'lardan okunan gerçek değerlerle
    st.markdown("**Bölüm Önizleme:**")
    preview_data = []
    for i, (s_sec, e_sec) in enumerate(segments_input):
        dur = max(0, e_sec - s_sec)
        preview_data.append({
            "Bölüm": f"Video {i + 1}",
            "Başlangıç": _format_mmss(s_sec),
            "Bitiş": _format_mmss(e_sec),
            "Süre": _format_duration(dur),
        })
    st.table(preview_data)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        # Hata varsa buton her zaman devre dışı
        bolumle_disabled = has_error
        if st.button("✂️ Böl ve Kaydet", key="dlg_bolum_kaydet", use_container_width=True, disabled=bolumle_disabled):
            # Çift kontrol: hata varsa kesinlikle çalışmasın
            if has_error:
                st.error("Hatalar giderilmeden bölme işlemi yapılamaz!")
            else:
                try:
                    # Geçerli segmentleri filtrele
                    segments = [(s, e) for s, e in segments_input if e > s]

                    if not segments:
                        st.error("Geçerli bölüm bulunamadı.")
                    else:
                        # Mevcut Eklenen Video klasörünü temizle
                        os.makedirs(hedef_root, exist_ok=True)
                        for name in os.listdir(hedef_root):
                            path = os.path.join(hedef_root, name)
                            if os.path.isdir(path):
                                shutil.rmtree(path, ignore_errors=True)
                            else:
                                try:
                                    os.remove(path)
                                except Exception:
                                    pass
                        _purge_prompt_state_for_prefix(hedef_root)

                        # İlerleme göstergesi ile videoyu böl
                        _bolum_progress_bar = st.progress(0, text="✂️ Video bölünmeye hazırlanıyor...")
                        _bolum_status_text = st.empty()
                        toplam_bolum = len(segments)
                        sonuclar = []
                        ext = os.path.splitext(temp_path)[1] or ".mp4"

                        for _b_idx, (_b_start, _b_end) in enumerate(segments):
                            video_no = 1 + _b_idx
                            _ilerleme = (_b_idx) / toplam_bolum
                            _bolum_progress_bar.progress(_ilerleme, text=f"✂️ Bölüm {video_no}/{toplam_bolum} kesiliyor... ({_format_mmss(_b_start)} → {_format_mmss(_b_end)})")
                            _bolum_status_text.info(f"⏳ Video {video_no} işleniyor: {_format_mmss(_b_start)} - {_format_mmss(_b_end)} ({_format_duration(_b_end - _b_start)})")

                            klasor = os.path.join(hedef_root, f"Video {video_no}")
                            os.makedirs(klasor, exist_ok=True)
                            out_name = f"bolum_{video_no}{ext}"
                            out_path = os.path.join(klasor, out_name)
                            duration = _b_end - _b_start
                            try:
                                subprocess.run(
                                    ["ffmpeg", "-y",
                                     "-ss", str(_b_start),
                                     "-i", temp_path,
                                     "-t", str(duration),
                                     "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                                     "-c:a", "aac", "-b:a", "192k",
                                     "-avoid_negative_ts", "make_zero",
                                     "-movflags", "+faststart",
                                     out_path],
                                    capture_output=True, text=True, timeout=600,
                                )
                                if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
                                    sonuclar.append({"no": video_no, "folder": klasor, "video": out_path})
                            except Exception:
                                pass

                        _bolum_progress_bar.progress(1.0, text="✅ Tüm bölümler başarıyla kesildi!")
                        _bolum_status_text.success(f"✅ {len(sonuclar)}/{toplam_bolum} bölüm başarıyla kaydedildi.")
                        time.sleep(1.5)

                        if sonuclar:
                            _write_prompt_source_mode(PROMPT_SOURCE_ADDED_VIDEO)
                            set_link_canvas_source("added_video")
                            st.session_state.status["youtube_link"] = "idle"
                            st.session_state.status["input"] = "ok"
                            st.session_state["video_bolum_saved_notice"] = (
                                f"Video {len(sonuclar)} bölüme ayrıldı ve Eklenen Video klasörüne kaydedildi "
                                f"(Video 1 - Video {len(sonuclar)})."
                            )
                            st.session_state["video_ekle_saved_notice"] = (
                                f"Video {len(sonuclar)} bölüme ayrılarak kaydedildi "
                                f"(Video 1 - Video {len(sonuclar)})."
                            )
                            # Geçici dosyayı temizle
                            try:
                                os.remove(temp_path)
                            except Exception:
                                pass
                            st.session_state.video_bolum_temp_path = None
                            st.session_state.video_bolum_temp_name = None
                            st.session_state.ek_dialog_open = "video_ekle"
                            st.rerun()
                        else:
                            st.error("Video bölme işlemi başarısız oldu. ffmpeg yüklü olduğundan emin olun.")
                except Exception as e:
                    st.error(f"Video bölme sırasında hata oluştu: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("⬅️ Geri", key="dlg_bolum_geri", use_container_width=True):
            try:
                if temp_path and os.path.isfile(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            st.session_state.video_bolum_temp_path = None
            st.session_state.video_bolum_temp_name = None
            st.session_state.ek_dialog_open = "video_ekle"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


@st.dialog("🔍 Görsel Önizleme", width="large")
def gorsel_lightbox_dialog(gorsel_path, gorsel_adi):
    if os.path.isfile(gorsel_path):
        st.markdown(f'<div style="text-align:center;"><span class="lightbox-caption">{gorsel_adi}</span></div>', unsafe_allow_html=True)
        st.image(gorsel_path, use_container_width=True)
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri (Görsel Seçimine Dön)", key="lightbox_geri_btn", use_container_width=True):
        st.session_state.last_dialog_align = st.session_state.get("_ek_dialog_return_align", "left")
        st.session_state.ek_dialog_open = st.session_state.get("_ek_dialog_return", "gorsel_analiz")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("🖼️ Görsel Analiz", width="large")
def gorsel_analiz_dialog():
    kaynak_videolar = _list_gorsel_analiz_source_entries()
    kaynak_etiketi = _get_gorsel_analiz_source_label()

    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.button(
        "📸 Videodan Görsel Çıkart (İşlemi Başlat)",
        key="dlg_gorsel_analiz_start_patch",
        use_container_width=True,
        disabled=st.session_state.get("batch_mode", False) or any_running() or (not kaynak_videolar)
    ):
        st.session_state.ek_dialog_open = "gorsel_analiz"
        st.session_state.single_paused = False
        st.session_state.single_finish_requested = False
        st.session_state.single_mode = True
        st.session_state.bg_last_result = None
        st.session_state.single_step = "gorsel_analiz"
        cleanup_flags()
        st.session_state.status["gorsel_analiz"] = "running"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    render_dialog_single_controls(step_match="gorsel_analiz", prefix="dlg_gorsel_analiz")
    st.markdown("---")

    klasorler = get_gorsel_analiz_klasorleri()
    if klasorler:
        idx = klasorler.index(st.session_state.get("gorsel_analiz_klasor_sec")) if st.session_state.get("gorsel_analiz_klasor_sec") in klasorler else 0
        secilen = st.selectbox("Klasör Seçin:", options=klasorler, index=idx)
        if secilen:
            st.session_state.gorsel_analiz_klasor_sec = secilen
            gorseller = get_klasor_gorselleri(secilen)
            if gorseller:
                sel_key = f"sel_{secilen}"
                if sel_key not in st.session_state: st.session_state[sel_key] = gorseller[0]
                cols_per_row = 4
                for r in range(0, len(gorseller), cols_per_row):
                    row_gorseller = gorseller[r:r+cols_per_row]
                    cols = st.columns(cols_per_row)
                    for i, g_adi in enumerate(row_gorseller):
                        with cols[i]:
                            g_yol = os.path.join(st.session_state.settings.get("gorsel_analiz_dir", ""), secilen, g_adi)
                            try: st.image(g_yol, use_container_width=True)
                            except: st.text(g_adi)
                            b1, b2 = st.columns(2)
                            with b1:
                                if st.button("🔍", key=f"zm_{secilen}_{g_adi}"):
                                    st.session_state.lightbox_gorsel = {"path": g_yol, "adi": g_adi}; st.session_state._ek_dialog_return = "gorsel_analiz"; st.rerun()
                            with b2:
                                if st.button("✅" if st.session_state.get(sel_key) == g_adi else "☐", key=f"sl_{secilen}_{g_adi}"):
                                    st.session_state[sel_key] = g_adi; st.rerun()
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                    if st.button("💾 Kaydet (Diğerlerini Sil)", use_container_width=True):
                        if st.session_state.get(sel_key): 
                            gorsel_sec_ve_diger_sil(secilen, st.session_state[sel_key])
                            st.session_state.ek_dialog_open = "gorsel_analiz"
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
                    if st.button("⬅️ Geri", key="bck1", use_container_width=True): st.session_state.ek_dialog_open = "menu"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        if not kaynak_videolar:
            st.warning(f"{kaynak_etiketi} kaynağında işlenecek video bulunamadı.")
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("⬅️ Geri", key="bck2", use_container_width=True): st.session_state.ek_dialog_open = "menu"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("🎨 Görsel Klonla", width="large")
def gorsel_klonla_dialog():
    gorsel_analiz_dir  = st.session_state.settings.get("gorsel_analiz_dir", "")
    gorsel_olustur_dir = st.session_state.settings.get("gorsel_olustur_dir", "")
    links_file         = st.session_state.settings.get("links_file", "")

    # ── Kaynak Seçimi ──────────────────────────────────────────
    mevcut_kaynak = st.session_state.settings.get("gorsel_klonla_kaynak", "gorsel_analiz")
    secenekler    = ["🖼️ Görsel Analiz", "✨ Görsel Oluştur"]
    secili_idx    = 1 if mevcut_kaynak == "gorsel_olustur" else 0
    secim = st.radio(
        "Kaynak Seçin:",
        secenekler,
        index=secili_idx,
        horizontal=True,
        key="gklonla_kaynak_radio",
        help="Hangi görseller üzerinde klonlama yapılacak?"
    )
    yeni_kaynak = "gorsel_olustur" if secim == "✨ Görsel Oluştur" else "gorsel_analiz"
    if yeni_kaynak != mevcut_kaynak:
        st.session_state.settings["gorsel_klonla_kaynak"] = yeni_kaynak
        save_settings(st.session_state.settings)
        st.session_state.ek_dialog_open = "gorsel_klonla"
        st.rerun()

    # Seçime göre aktif dizin ve klasörler
    if yeni_kaynak == "gorsel_olustur":
        aktif_dir = gorsel_olustur_dir
        # Görsel Oluştur klasörleri: "Görsel 1", "Görsel 2" ...
        if aktif_dir and os.path.isdir(aktif_dir):
            aktif_klasorler = sorted(
                [d for d in os.listdir(aktif_dir) if os.path.isdir(os.path.join(aktif_dir, d))],
                key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)]
            )
        else:
            aktif_klasorler = []
    else:
        aktif_dir = gorsel_analiz_dir
        aktif_klasorler = get_gorsel_analiz_klasorleri()

    # Görsel sayısını aktif kaynaktan al
    gorsel_sayisi = len(aktif_klasorler)

    st.markdown("---")

    # Aktif prompt kaynağına göre sayıyı belirle (Link veya Eklenen Video)
    video_sayisi = _get_prompt_input_count()

    # Görsel analiz klasörlerini al (thumbnail için, olmasa da çalışır)
    klasorler = aktif_klasorler

    # Sayı: gorsel_olustur seçiliyse klasör sayısını, yoksa video sayısını kullan
    if yeni_kaynak == "gorsel_olustur":
        efektif_sayisi = gorsel_sayisi
        if efektif_sayisi == 0:
            st.warning("Görsel Oluştur klasöründe henüz görsel bulunamadı. Önce Görsel Oluştur ile görsel üretin.")
    else:
        efektif_sayisi = video_sayisi
        if efektif_sayisi == 0:
            st.warning("Önce YouTube'dan Liste Oluştur, Video Listesi Ekle veya Video Ekle bölümünden kaynak ekleyin.")

    if efektif_sayisi > 0:
        mevcut_data = gorsel_duzelt_oku()
        duzelt_inputs = {}

        # Doluluk özeti
        dolu = sum(1 for i in range(1, efektif_sayisi+1) if mevcut_data.get(i, "").strip())
        bos  = efektif_sayisi - dolu
        renk = "limegreen" if bos == 0 else ("orange" if dolu > 0 else "tomato")
        kaynak_etiketi = "Görsel Oluştur" if yeni_kaynak == "gorsel_olustur" else "Görsel Analiz"
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 14px;margin-bottom:12px;">'
            f'🎨 <b>Görsel Klonlama Düzeltmeleri</b> &nbsp;|&nbsp; Kaynak: {kaynak_etiketi} &nbsp;|&nbsp; {efektif_sayisi} görsel &nbsp;|&nbsp; '
            f'<span style="color:limegreen">✅ {dolu} dolu</span> &nbsp;|&nbsp; '
            f'<span style="color:{renk}">⬜ {bos} boş</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.caption("Her görsel için Görsel Klonlama sırasında uygulanacak değişikliği yazın.")
        st.markdown(
            '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.25);'
            'border-radius:8px;padding:8px 12px;margin-bottom:10px;font-size:12px;color:rgba(255,255,255,0.75);">'
            '💡 <b>Referans Görsel (isteğe bağlı):</b> Her görsel için bir referans görsel yükleyebilirsiniz. '
            'Örneğin <em>"1. Görseldeki karakteri 2. Görseldeki karakterle değiştir"</em> gibi bir istemle '
            'hem ana görsel hem referans görsel birlikte modele gönderilir.'
            '</div>',
            unsafe_allow_html=True
        )

        for i in range(1, efektif_sayisi + 1):
            # Thumbnail: aktif kaynaktan klasör varsa göster
            klasor_adi = klasorler[i-1] if i-1 < len(klasorler) else None
            gorsel_yol = None
            if klasor_adi:
                gorseller = [
                    f for f in sorted(os.listdir(os.path.join(aktif_dir, klasor_adi)))
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"))
                ] if aktif_dir and os.path.isdir(os.path.join(aktif_dir, klasor_adi)) else []
                if gorseller:
                    sel_key  = f"sel_{klasor_adi}"
                    secili_g = st.session_state.get(sel_key, gorseller[0])
                    gorsel_yol = os.path.join(aktif_dir, klasor_adi, secili_g)

            mevcut_deger  = mevcut_data.get(i, "")
            doluluk_icon  = "✅" if mevcut_deger.strip() else "⬜"
            etiket        = klasor_adi if klasor_adi else f"Görsel {i}"

            # Mevcut referans görsel yolunu kontrol et
            mevcut_ref_yol = gorsel_referans_yolu(i)
            ref_var = bool(mevcut_ref_yol and os.path.isfile(mevcut_ref_yol))

            if gorsel_yol and os.path.isfile(gorsel_yol):
                col_img, col_inp = st.columns([0.18, 0.82])
                with col_img:
                    try: st.image(gorsel_yol, use_container_width=True)
                    except: st.caption("📷")
                with col_inp:
                    st.markdown(
                        f'<div style="font-size:12px;color:rgba(255,255,255,0.55);margin-bottom:2px;">'
                        f'{doluluk_icon} <b>#{i}</b> — {etiket}</div>',
                        unsafe_allow_html=True
                    )
                    duzelt_inputs[i] = st.text_input(
                        label=f"#{i}", value=mevcut_deger,
                        placeholder="Örn: Kadın yerine adam olarak değiştir",
                        key=f"dzt_{i}", label_visibility="collapsed"
                    )
                    # Referans görsel satırı
                    ref_col_up, ref_col_prev = st.columns([0.65, 0.35])
                    with ref_col_up:
                        ref_up = st.file_uploader(
                            f"📎 #{i} Referans Görsel",
                            type=["jpg", "jpeg", "png", "bmp", "webp"],
                            key=f"ref_up_{i}",
                            label_visibility="collapsed",
                            help="Bu görsel değişiklik için referans olarak kullanılır (isteğe bağlı)"
                        )
                        if ref_up is not None:
                            gorsel_referans_kaydet(i, ref_up)
                            st.session_state[f"ref_saved_{i}"] = True
                        _ref_label = f"📎 Referans #{i}"
                        if ref_var:
                            _ref_label += " ✅"
                        st.caption(_ref_label)
                    with ref_col_prev:
                        if ref_var:
                            try:
                                st.image(mevcut_ref_yol, use_container_width=True)
                            except Exception:
                                st.caption("📷 ref")
                            if st.button("🗑️", key=f"ref_sil_{i}",
                                         help="Referans görseli sil"):
                                gorsel_referans_sil(i)
                                st.rerun()
                        else:
                            st.caption("Referans yok")
            else:
                st.markdown(
                    f'<div style="font-size:12px;color:rgba(255,255,255,0.55);margin-bottom:2px;">'
                    f'{doluluk_icon} <b>#{i}</b> — {etiket}</div>',
                    unsafe_allow_html=True
                )
                duzelt_inputs[i] = st.text_input(
                    label=f"#{i}", value=mevcut_deger,
                    placeholder="Örn: Kadın yerine adam olarak değiştir",
                    key=f"dzt_{i}", label_visibility="collapsed"
                )
                # Referans görsel satırı (thumbnail olmayan durum)
                ref_col_up, ref_col_prev = st.columns([0.65, 0.35])
                with ref_col_up:
                    ref_up = st.file_uploader(
                        f"📎 #{i} Referans Görsel",
                        type=["jpg", "jpeg", "png", "bmp", "webp"],
                        key=f"ref_up_{i}",
                        label_visibility="collapsed",
                        help="Bu görsel değişiklik için referans olarak kullanılır (isteğe bağlı)"
                    )
                    if ref_up is not None:
                        gorsel_referans_kaydet(i, ref_up)
                        st.session_state[f"ref_saved_{i}"] = True
                    _ref_label = f"📎 Referans #{i}"
                    if ref_var:
                        _ref_label += " ✅"
                    st.caption(_ref_label)
                with ref_col_prev:
                    if ref_var:
                        try:
                            st.image(mevcut_ref_yol, use_container_width=True)
                        except Exception:
                            st.caption("📷 ref")
                        if st.button("🗑️", key=f"ref_sil_{i}",
                                     help="Referans görseli sil"):
                            gorsel_referans_sil(i)
                            st.rerun()
                    else:
                        st.caption("Referans yok")
            st.markdown('<hr style="margin:6px 0;border-color:rgba(255,255,255,0.07);">', unsafe_allow_html=True)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("💾 Kaydet", use_container_width=True):
                kaydet_data = {no: (v or "").strip() for no, v in duzelt_inputs.items()}
                gorsel_kaydet_ok = gorsel_duzelt_kaydet(kaydet_data)
                prompta_aktar_ok = gorsel_klonlama_notlarini_prompta_aktar(kaydet_data) if gorsel_kaydet_ok else False
                st.session_state.g_saved = bool(gorsel_kaydet_ok)
                st.session_state["gklonla_saved"] = bool(gorsel_kaydet_ok)
                st.session_state["gklonla_prompt_sync_ok"] = bool(gorsel_kaydet_ok and prompta_aktar_ok)
                st.session_state.ek_dialog_open = "gorsel_klonla"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("🗑️ Temizle", use_container_width=True):
                gorsel_duzelt_sil()
                gorsel_referans_tumunu_sil()
                st.session_state.g_saved = False
                st.session_state.pop("gklonla_saved", None)
                st.session_state.ek_dialog_open = "gorsel_klonla"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("gklonla_saved"):
            _gklonla_ph = st.empty()
            if st.session_state.get("gklonla_prompt_sync_ok"):
                _gklonla_ph.success("Kaydedildi! Görsel Klonla notları Prompt Düzeltme alanına da aktarıldı.")
            else:
                _gklonla_ph.success("Kaydedildi! Artık Tümünü Çalıştır'ı başlatabilirsiniz.")
            time.sleep(2.5)
            _gklonla_ph.empty()
            st.session_state.pop("gklonla_saved", None)
            st.session_state.pop("gklonla_prompt_sync_ok", None)

        st.markdown("---")
        can_start = st.session_state.get("g_saved", False) or dolu > 0
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("🚀 Görselleri Klonla", use_container_width=True, disabled=st.session_state.get("batch_mode", False) or any_running() or (not can_start)):
            st.session_state.ek_dialog_open = "gorsel_klonla"
            st.session_state.single_paused = False; st.session_state.single_finish_requested = False
            st.session_state.single_mode = True; st.session_state.single_step = "gorsel_klonlama"
            cleanup_flags(); st.session_state.status["gorsel_klonlama"] = "running"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        render_dialog_single_controls(step_match="gorsel_klonlama", prefix="dlg_gorsel_klonlama")

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="bck3", use_container_width=True): st.session_state.ek_dialog_open = "menu"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("✏️ Prompt Düzeltme", width="large")
def prompt_duzeltme_dialog():
    # 1. Aktif prompt kaynağına göre giriş sayısını oku → başlangıç numaraları
    link_numaralari = set(range(1, _get_prompt_input_count() + 1))

    # 2. Prompt klasörlerinden GERÇEK numaraları çek (Video Prompt 1, Video Prompt 3 → {1, 3})
    prompt_dir = st.session_state.settings.get("prompt_dir", "")
    prompt_numaralari = set()
    if prompt_dir and os.path.isdir(prompt_dir):
        try:
            for d in os.listdir(prompt_dir):
                klasor_yolu = os.path.join(prompt_dir, d)
                if os.path.isdir(klasor_yolu) and os.path.exists(os.path.join(klasor_yolu, "prompt.txt")):
                    m = re.search(r'(\d+)\s*$', d)
                    if m:
                        prompt_numaralari.add(int(m.group(1)))
        except Exception: pass

    # 3. Birleştir: link numaraları VEYA prompt numaraları olan her şeyi göster
    tum_numaralar = sorted(link_numaralari | prompt_numaralari)

    if not tum_numaralar:
        st.warning("Henüz kaynak veya prompt bulunamadı.")
    else:
        mevcut_data = prompt_duzeltme_oku()
        duzelt_inputs = {}

        # Sadece aktif olanları say
        aktif_numaralar = prompt_numaralari if prompt_numaralari else link_numaralari
        dolu = sum(1 for i in aktif_numaralar if mevcut_data.get(i, "").strip())
        bos  = len(aktif_numaralar) - dolu
        renk = "limegreen" if bos == 0 else ("orange" if dolu > 0 else "tomato")
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 14px;margin-bottom:12px;">'
            f'✏️ <b>Prompt Düzeltme Talimatları</b> &nbsp;|&nbsp; {len(aktif_numaralar)} aktif &nbsp;|&nbsp; '
            f'<span style="color:limegreen">✅ {dolu} dolu</span> &nbsp;|&nbsp; '
            f'<span style="color:{renk}">⬜ {bos} boş</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.caption("Her prompt için uygulanacak ek düzeltme talimatını yazın. Sabit şablon (dil, kalite, kamera vb.) otomatik eklenir.")

        for i in tum_numaralar:
            mevcut_deger = mevcut_data.get(i, "")
            # Prompt oluşturulmuş ama silinmiş → link var, prompt klasörü yok
            prompt_silindi = (prompt_numaralari and i not in prompt_numaralari and i in link_numaralari)
            doluluk_icon = "✅" if mevcut_deger.strip() else "⬜"

            if prompt_silindi:
                st.markdown(
                    f'<div style="font-size:12px;color:rgba(255,255,255,0.25);margin-bottom:2px;text-decoration:line-through;">'
                    f'🗑️ <b>Prompt {i}</b> — silindi</div>',
                    unsafe_allow_html=True
                )
                duzelt_inputs[i] = st.text_input(
                    label=f"Prompt {i}", value="",
                    placeholder="(Bu prompt silindi)",
                    key=f"pdzt_{i}", label_visibility="collapsed",
                    disabled=True
                )
            else:
                st.markdown(
                    f'<div style="font-size:12px;color:rgba(255,255,255,0.55);margin-bottom:2px;">'
                    f'{doluluk_icon} <b>Prompt {i}</b></div>',
                    unsafe_allow_html=True
                )
                duzelt_inputs[i] = st.text_input(
                    label=f"Prompt {i}", value=mevcut_deger,
                    placeholder="Örn: Kadın yerine erkek olacak, gece sahnesi olsun",
                    key=f"pdzt_{i}", label_visibility="collapsed"
                )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("💾 Kaydet", key="pdzt_kaydet", use_container_width=True):
                kaydet_data = {i: v for i, v in duzelt_inputs.items()
                               if not (prompt_numaralari and i not in prompt_numaralari and i in link_numaralari)}
                prompt_duzeltme_kaydet(kaydet_data)
                st.session_state["pdzt_saved"] = True
                st.session_state.ek_dialog_open = "prompt_duzeltme"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("🗑️ Temizle", key="pdzt_temizle", use_container_width=True):
                prompt_duzeltme_kaydet({i: "" for i in aktif_numaralar})
                st.session_state.pop("pdzt_saved", None)
                st.session_state.ek_dialog_open = "prompt_duzeltme"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("pdzt_saved"):
            _pdzt_ph = st.empty()
            _pdzt_ph.success("Kaydedildi! Sabit şablon her prompt için otomatik eklendi.")
            time.sleep(2.5)
            _pdzt_ph.empty()
            st.session_state.pop("pdzt_saved", None)

        st.markdown("---")
        can_start = st.session_state.get("pdzt_saved", False) or dolu > 0
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("🚀 Promptları Düzelt", use_container_width=True,
                     disabled=st.session_state.get("batch_mode", False) or any_running() or (not can_start)):
            st.session_state.ek_dialog_open = "prompt_duzeltme"
            st.session_state.single_paused = False; st.session_state.single_finish_requested = False
            st.session_state.single_mode = True; st.session_state.single_step = "prompt_duzeltme"
            cleanup_flags(); st.session_state.status["prompt_duzeltme"] = "running"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        render_dialog_single_controls(step_match="prompt_duzeltme", prefix="dlg_prompt_duzeltme")

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="bck_pdzt", use_container_width=True):
        st.session_state.ek_dialog_open = "menu"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)



@st.dialog("🌐 Sosyal Medya Paylaşım", width="large")
def sosyal_medya_dialog():
    yollar = sosyal_medya_ensure_files()
    script_path = (yollar.get("script") or "").strip()
    script_exists = bool(script_path and os.path.exists(script_path))

    _sm_accounts_state_init()
    _sm_apply_pending_form_ui_state()

    if st.session_state.get("sm_hesap_modu") != st.session_state.get("sm_last_hesap_mode_rendered"):
        rows_for_mode = list(st.session_state.get("sm_accounts_rows", []) or [])
        if st.session_state.get("sm_hesap_modu") == "Tek Hesap":
            first_row = dict(rows_for_mode[0] if rows_for_mode else {"token": "", "email": "", "password": ""})
            st.session_state["sm_single_token"] = str(first_row.get("token", "") or "")
        else:
            # Toplu Hesap moduna geçerken dosyadan hesapları tekrar yükle (hesap kaybolma sorununu önler)
            cfg = sosyal_medya_hesap_konfig_oku()
            cfg_rows = [{"token": x.get("token", ""), "email": x.get("email", ""), "password": x.get("password", ""), "selected": bool(x.get("selected", True))} for x in (cfg.get("accounts") or [])]
            tek_token = str(st.session_state.get("sm_single_token", "") or "")
            if cfg_rows:
                rows_for_mode = cfg_rows
            elif not rows_for_mode:
                rows_for_mode = [{"token": "", "email": "", "password": "", "selected": True}]
            first_row = dict(rows_for_mode[0] if rows_for_mode else {"token": "", "email": "", "password": "", "selected": True})
            if tek_token and not first_row.get("token"):
                first_row["token"] = tek_token
            rows_for_mode[0] = first_row
            _sm_apply_rows_to_widget_state(rows_for_mode)
        st.session_state["sm_last_hesap_mode_rendered"] = st.session_state.get("sm_hesap_modu")

    cfg = sosyal_medya_konfig_oku()
    global_defaults = dict(cfg.get("global") or {})
    item_defaults = dict(cfg.get("items") or {})

    if "sm_ayar_modu" not in st.session_state:
        st.session_state["sm_ayar_modu"] = "Video/Link Bazlı" if cfg.get("mode") == "per_item" else "Genel"

    if st.session_state.get("sm_saved_notice"):
        _sm_ph = st.empty()
        _sm_ph.success("Kaydedildi! Tümünü Çalıştır sırasında Sosyal Medya Paylaşım bu ayarla çalışacak.")
        time.sleep(2.2)
        _sm_ph.empty()
        st.session_state.pop("sm_saved_notice", None)

    if st.session_state.get("sm_error_notice"):
        st.error(st.session_state.get("sm_error_notice"))

    st.caption("Buffer API tabanlı sosyal medya paylaşım ayarlarını buradan yönetin. Bu ekranda genel paylaşım ayarı veya video/link bazlı özel paylaşım planı kaydedebilirsiniz.")

    st.markdown("### 🔑 Buffer API Token")
    st.caption("Buffer API Token'larınızı buradan yönetin. Token almak için: Buffer Ayarlar > API Settings bölümüne gidin. İlk satırdaki token Tek Hesap modunda kullanılır.")

    hesap_modu = st.radio(
        "Hesap Modu",
        ["Tek Hesap", "Toplu Hesap"],
        key="sm_hesap_modu",
        horizontal=True,
    )
    toplu_hesap_modu = hesap_modu == "Toplu Hesap"

    rows = list(st.session_state.get("sm_accounts_rows", []) or [])
    if not rows:
        rows = [{"token": "", "email": "", "password": "", "selected": False}]
    st.session_state["sm_accounts_rows"] = rows

    if not toplu_hesap_modu:
        first = dict(rows[0] if rows else {"token": "", "email": "", "password": ""})
        # Tek Hesap alanlarını her rerun'da rows[0] ile yeniden ezmeyelim.
        if "sm_single_token" not in st.session_state:
            st.session_state["sm_single_token"] = str(first.get("token", "") or "")
        tek_token = st.text_input("Buffer API Token", key="sm_single_token", type="password", help="Buffer hesabınızın API Token'ını girin. Token almak için: https://publish.buffer.com/settings/api")
        rows[0] = {"token": tek_token, "email": "", "password": "", "selected": False}
        st.session_state["sm_accounts_rows"] = rows
        st.caption("Tek Hesap modunda yalnızca ilk satırdaki API Token kullanılır. Bu alanı değiştirirseniz toplu hesap listesindeki ilk token da güncellenmiş olur.")
        hesap_loop = False
    else:
        secim_cols = st.columns([1.6, 1.3, 1.35])
        with secim_cols[0]:
            select_all = st.checkbox("Tüm hesapları seç", key="sm_select_all_accounts")
        with secim_cols[1]:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("➕ Hesap Ekle", key="sm_add_account_row", use_container_width=True):
                rows.append({"token": "", "email": "", "password": "", "selected": False})
                st.session_state["sm_accounts_rows"] = rows
                _sm_schedule_account_ui_reset(rows=rows)
                st.session_state.ek_dialog_open = "sosyal_medya"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with secim_cols[2]:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("🗑️ Hesabı Sil", key="sm_delete_account_rows", use_container_width=True):
                silinen = _sm_delete_selected_accounts()
                if silinen <= 0:
                    st.session_state["sm_error_notice"] = "Silmek için en az 1 hesap seçin."
                else:
                    st.session_state.pop("sm_error_notice", None)
                st.session_state.ek_dialog_open = "sosyal_medya"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        prev_select_all = bool(st.session_state.get("sm_select_all_accounts_prev", False))
        if bool(select_all) != prev_select_all:
            for row in rows:
                row["selected"] = bool(select_all)
            st.session_state["sm_select_all_accounts_prev"] = bool(select_all)

        st.markdown(
            "<div style='background:rgba(255,255,255,0.045);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:12px 14px;margin:8px 0 14px 0;line-height:1.6;'>"
            "İlk satırdaki hesap <b>Tek Hesap</b> modunda kullanılacak hesaptır. "
            "Toplu paylaşımda <b>seçili hesaplarda</b> her video ayrı ayrı paylaşılır. "
            "<b>Hesap döngüsü</b> açılırsa videolar seçili hesaplara sırayla dağıtılır. "
            "Hiç hesap seçmeden kaydederseniz tüm geçerli hesaplar kullanılır."
            "</div>",
            unsafe_allow_html=True,
        )

        header_cols = st.columns([0.7, 0.85, 3.0, 2.05])
        with header_cols[0]:
            st.markdown("<div style='font-size:12px;opacity:.78;padding:4px 0 6px 2px;white-space:nowrap;'>Seç</div>", unsafe_allow_html=True)
        with header_cols[1]:
            st.markdown("<div style='font-size:12px;opacity:.78;padding:4px 0 6px 2px;white-space:nowrap;'>Hesap</div>", unsafe_allow_html=True)
        with header_cols[2]:
            st.markdown("<div style='font-size:12px;opacity:.78;padding:4px 0 6px 2px;white-space:nowrap;'>Buffer API Token</div>", unsafe_allow_html=True)
        with header_cols[3]:
            st.markdown("<div style='font-size:12px;opacity:.78;padding:4px 0 6px 2px;white-space:nowrap;'>Hesap Adı (isteğe bağlı)</div>", unsafe_allow_html=True)

        updated_rows = []
        for idx, row in enumerate(rows, start=1):
            row_cols = st.columns([0.7, 0.85, 3.0, 2.05])
            with row_cols[0]:
                secili = st.checkbox("Seç", key=f"sm_account_selected_{idx}", label_visibility="collapsed")
            with row_cols[1]:
                badge_bg = "rgba(255,255,255,0.08)" if idx == 1 else "rgba(255,255,255,0.045)"
                badge_border = "rgba(255,255,255,0.16)" if idx == 1 else "rgba(255,255,255,0.10)"
                st.markdown(
                    f"<div style='height:38px;display:flex;align-items:center;justify-content:center;border-radius:10px;background:{badge_bg};border:1px solid {badge_border};white-space:nowrap;font-weight:700;'>{{idx}}</div>".format(idx=idx),
                    unsafe_allow_html=True,
                )
            with row_cols[2]:
                token = st.text_input(f"Hesap {idx} API Token", key=f"sm_account_token_{idx}", type="password", label_visibility="collapsed", placeholder="Buffer API Token")
            with row_cols[3]:
                email = st.text_input(f"Hesap {idx} Adı", key=f"sm_account_email_{idx}", label_visibility="collapsed", placeholder="Hesap adı (isteğe bağlı)")
            updated_rows.append({"token": token, "email": email, "password": "", "selected": secili})
        rows = updated_rows
        st.session_state["sm_accounts_rows"] = rows
        hesap_loop = st.checkbox(
            "Videoları hesaplar arasında sırayla dağıt (döngü)",
            key="sm_hesap_dongu",
            help="Kapalıysa her video seçili tüm hesaplarda paylaşılır. Açıkysa videolar seçili hesaplara sırayla dağıtılır.",
        )
        aktif_hesaplar, invalid_rows = _sm_collect_accounts_from_rows()
        if invalid_rows:
            st.warning(f"Eksik bilgi olan hesap satırları: {', '.join(str(x) for x in invalid_rows)}. API Token girilmeli.")
        secili_hesap_sayisi = sum(1 for h in aktif_hesaplar if h.get("selected", True))
        toplam_hesap_sayisi = len(aktif_hesaplar)
        if secili_hesap_sayisi == toplam_hesap_sayisi:
            if hesap_loop:
                st.caption(f"Kaydedilecek geçerli hesap sayısı: {toplam_hesap_sayisi} (tümü seçili — videolar sırayla dağıtılacak)")
            else:
                st.caption(f"Kaydedilecek geçerli hesap sayısı: {toplam_hesap_sayisi} (tümü seçili — her video tüm seçili hesaplarda paylaşılacak)")
        elif secili_hesap_sayisi == 0:
            if hesap_loop:
                st.caption(f"Kaydedilecek geçerli hesap sayısı: {toplam_hesap_sayisi} (hiçbiri seçili değil — tüm hesaplar kullanılacak, videolar sırayla dağıtılacak)")
            else:
                st.caption(f"Kaydedilecek geçerli hesap sayısı: {toplam_hesap_sayisi} (hiçbiri seçili değil — her video tüm hesaplarda paylaşılacak)")
        else:
            if hesap_loop:
                st.caption(f"Kaydedilecek geçerli hesap sayısı: {toplam_hesap_sayisi} · Seçili: {secili_hesap_sayisi} (yalnızca seçili hesaplar kullanılacak, videolar sırayla dağıtılacak)")
            else:
                st.caption(f"Kaydedilecek geçerli hesap sayısı: {toplam_hesap_sayisi} · Seçili: {secili_hesap_sayisi} (her video yalnızca seçili hesaplarda paylaşılacak)")

    st.markdown("---")
    st.markdown("### ⚙️ Paylaşım Ayar Modu")
    st.caption("Genel mod tek ayarı tüm videolara uygular. Video/Link Bazlı mod ise her link veya video için ayrı başlık, açıklama, platform ve zaman kaydeder.")
    ayar_modu = st.radio(
        "Paylaşım Ayar Modu",
        ["Genel", "Video/Link Bazlı"],
        key="sm_ayar_modu",
        horizontal=True,
    )

    item_payload = {}
    aktif_numaralar = []
    dolu = 0

    if ayar_modu == "Genel":
        baslik_default = str(global_defaults.get("baslik", "") or "")
        aciklama_default = str(global_defaults.get("aciklama", "") or "")
        platform_default = dict(global_defaults.get("secimler") or {"youtube": False, "tiktok": False, "instagram": False})
        global_publish_mode = "Hemen Paylaş" if sosyal_medya_publish_mode_normalize(global_defaults.get("publish_mode")) == "publish_now" else "Zamanla"
        gun_default = str(global_defaults.get("gun", "") or "")
        saat_default = str(global_defaults.get("saat", "") or "")

        st.markdown("### 🏷️ Video Başlık")
        baslik = st.text_area(
            "Video Başlık",
            value=baslik_default,
            height=100,
            key="sm_baslik_txt",
            placeholder="YouTube başlığı / TikTok-Instagram açıklama metni",
            label_visibility="collapsed",
        )

        st.markdown("### 📄 Video Açıklama")
        aciklama = st.text_area(
            "Video Açıklama",
            value=aciklama_default,
            height=140,
            key="sm_aciklama_txt",
            placeholder="YouTube açıklaması buraya yazılır. Boş bırakılabilir.",
            label_visibility="collapsed",
        )

        st.markdown("### 🌐 Paylaşılacak Sosyal Medyalar")
        c1, c2, c3 = st.columns(3)
        with c1:
            sm_youtube = st.checkbox("YouTube", value=platform_default.get("youtube", False), key="sm_platform_youtube")
        with c2:
            sm_tiktok = st.checkbox("TikTok", value=platform_default.get("tiktok", False), key="sm_platform_tiktok")
        with c3:
            sm_instagram = st.checkbox("Instagram", value=platform_default.get("instagram", False), key="sm_platform_instagram")

        st.markdown("### 🕒 Paylaşım Şekli")
        sm_publish_mode = st.radio(
            "Paylaşım Şekli",
            ["Zamanla", "Hemen Paylaş"],
            index=0 if global_publish_mode == "Zamanla" else 1,
            key="sm_publish_mode",
            horizontal=True,
            label_visibility="collapsed",
        )
        if sm_publish_mode == "Hemen Paylaş":
            sm_gun = ""
            sm_saat = ""
            st.caption("Hemen Paylaş seçildiğinde zamanlama kullanılmaz. Kaydedilen plan yükleme tamamlanınca doğrudan paylaşım akışına geçer.")
        else:
            c4, c5 = st.columns(2)
            with c4:
                sm_gun = st.text_input("Gün", value=gun_default, key="sm_zaman_gun", placeholder="Örn: 22")
            with c5:
                sm_saat = st.text_input("Saat", value=saat_default, key="sm_zaman_saat", placeholder="Örn: 20:00")
            st.caption("Ekranda 24 saat formatı kullanılır. Kaydedildiğinde txt içine İngilizce 12 saat formatında yazılır. Örnek: 22,8:00 PM")

        def _save_social_settings():
            return sosyal_medya_kaydet(
                aciklama=aciklama,
                baslik=baslik,
                secimler={"youtube": sm_youtube, "tiktok": sm_tiktok, "instagram": sm_instagram},
                gun=sm_gun,
                saat=sm_saat,
                publish_mode=sm_publish_mode,
            )
    else:
        # --- Kaynak Seçimi ---
        st.markdown("### 📂 Video Kaynağı Seçimi")
        st.caption("Kaynağı ayrı ayrı seçin: Link, Video, 🖼️ Görsel Oluştur, 🎞️ Video Ekle, 🎬 Toplu Video Montaj veya 🎞️ Video Montaj. Böylece tüm video türlerinin ayarları birbirine karışmaz.")

        # Kaynak seçimini dosyadan başlatma (ilk açılışta)
        _kaynak_secim_path = sosyal_medya_yol_bilgisi().get("kaynak_secim", "")
        if "sm_video_kaynak_secim_loaded" not in st.session_state:
            if _kaynak_secim_path and os.path.exists(_kaynak_secim_path):
                try:
                    with open(_kaynak_secim_path, "r", encoding="utf-8") as _f:
                        _kayitli = _sm_normalize_kaynak_secim(_f.read().strip())
                    st.session_state["sm_video_kaynak_secim"] = _kayitli
                except Exception:
                    pass
            st.session_state["sm_video_kaynak_secim_loaded"] = True

        _kaynak_secenekler = ["Link", "Video", "🖼️ Görsel Oluştur", "🎞️ Video Ekle", "🎬 Toplu Video Montaj", "🎞️ Video Montaj"]
        _mevcut_kaynak = _sm_normalize_kaynak_secim(st.session_state.get("sm_video_kaynak_secim", "Link"))
        if _mevcut_kaynak not in _kaynak_secenekler:
            _mevcut_kaynak = "Link"

        kaynak_secim = st.radio(
            "Kaynak",
            _kaynak_secenekler,
            index=_kaynak_secenekler.index(_mevcut_kaynak),
            key="sm_kaynak_radio",
            horizontal=True,
            label_visibility="collapsed",
        )
        if kaynak_secim != _sm_normalize_kaynak_secim(st.session_state.get("sm_video_kaynak_secim")):
            # Rerun yerine sadece state güncelle (Streamlit radio zaten rerun tetikler)
            st.session_state["sm_video_kaynak_secim"] = kaynak_secim

        # --- Kaynağa göre numaraları belirle ---
        if kaynak_secim == "🎬 Toplu Video Montaj":
            aktif_video_numaralari = sosyal_medya_toplu_video_numaralari()
            _kaynak_bilgi_etiketi = "🎬 Toplu Video Montaj"
            _kaynak_aciklama = "Toplu Video Montaj çıktı klasöründeki mevcut videolar veya kaydedilen preset ile üretilecek video sayısı baz alınıyor."
            if not aktif_video_numaralari:
                st.info("Toplu Video Montaj çıktı klasöründe video bulunamadı ve kayıtlı preset de yok. Önce 🎬 Toplu Video Montaj bölümünden ayarları kaydedin.")
        elif kaynak_secim == "🖼️ Görsel Oluştur":
            aktif_video_numaralari = sosyal_medya_gorsel_olustur_numaralari()
            _kaynak_bilgi_etiketi = "🖼️ Görsel Oluştur"
            _kaynak_aciklama = "Görsel Oluştur ekranında kaydettiğiniz hareketlendirme promptlarından üretilecek videolar baz alınıyor."
            if not aktif_video_numaralari:
                st.info("Görsel Oluştur için kaydedilmiş hareketlendirme promptu bulunamadı. Önce 🖼️ Görsel Oluştur bölümünden promptları kaydedin.")
        elif kaynak_secim == "🎞️ Video Ekle":
            aktif_video_numaralari = sosyal_medya_eklenen_video_numaralari()
            _kaynak_bilgi_etiketi = "🎞️ Video Ekle"
            _kaynak_aciklama = "🎞️ Video Ekle bölümüne yüklediğiniz videolar baz alınıyor."
            if not aktif_video_numaralari:
                st.info("Eklenen Video klasöründe video bulunamadı. Önce 🎞️ Video Ekle bölümünden video yükleyin.")
        elif kaynak_secim == "🎞️ Video Montaj":
            aktif_video_numaralari = sosyal_medya_video_montaj_numaralari()
            _kaynak_bilgi_etiketi = "🎞️ Video Montaj"
            _kaynak_aciklama = "Video Montaj çıktı klasöründeki mevcut videolar veya kaydedilen preset ile üretilecek 1 adet video baz alınıyor."
            if not aktif_video_numaralari:
                st.info("Video Montaj çıktı klasöründe video bulunamadı ve kayıtlı preset de yok. Önce 🎞️ Video Montaj bölümünden ayarları kaydedin.")
        elif kaynak_secim == "Link":
            _link_kaynak_haritasi = sosyal_medya_link_kaynak_haritasi()
            aktif_video_numaralari = set(_link_kaynak_haritasi.keys())
            _kaynak_bilgi_etiketi = "Link / İndirilen Video"
            _kaynak_aciklama = "Link eklendiyse Link, link indirildiyse aynı sıra numarası İndirilen Video olarak gösterilir. Bu akış Video bölümüyle karışmaz."
            if not aktif_video_numaralari:
                st.info("Ne link ne de indirilen video bulundu. Önce link ekleyin veya video indirin.")
        else:
            aktif_video_numaralari = sosyal_medya_video_numaralari()
            _kaynak_bilgi_etiketi = "Video"
            _kaynak_aciklama = "Sosyal Medya Video klasöründeki mevcut videolar baz alınıyor."
            if not aktif_video_numaralari:
                st.info("Sosyal Medya Video klasöründe video bulunamadı. Önce video ekleyin veya üretin.")

        aktif_numara_seti = set(aktif_video_numaralari)
        aktif_numaralar = sorted(aktif_numara_seti)
        oge_etiketi = "Kaynak" if kaynak_secim == "Link" else "Video"

        if not aktif_numaralar:
            st.warning(f"Henüz kaynak bulunamadı. {_kaynak_aciklama}")
        else:
            dolu = sum(1 for i in aktif_numaralar if sosyal_medya_item_dolu_mu(item_defaults.get(i, {})))
            bos = len(aktif_numaralar) - dolu
            renk = "limegreen" if bos == 0 else ("orange" if dolu > 0 else "tomato")
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 14px;margin-bottom:12px;">'
                f'🌐 <b>{_kaynak_bilgi_etiketi} Bazlı Sosyal Medya Ayarları</b> &nbsp;|&nbsp; {len(aktif_numaralar)} aktif &nbsp;|&nbsp; '
                f'<span style="color:limegreen">✅ {dolu} dolu</span> &nbsp;|&nbsp; '
                f'<span style="color:{renk}">⬜ {bos} boş</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"Kaynak: {_kaynak_bilgi_etiketi} — {_kaynak_aciklama}")
            st.caption("Her kaynak için ayrı başlık, açıklama, paylaşılacak sosyal medya ve paylaşım zamanı girebilirsiniz. Bu mod dosyalara '### Video N' bloklarıyla kaydedilir.")

            # ── Tümünü Seç / Kaldır checkbox'u ──
            _tum_secili_varsayilan = all(
                bool((item_defaults.get(_n) or {}).get("selected", True))
                for _n in aktif_numaralar
            ) if aktif_numaralar else True
            _sm_item_source_sig = f"{kaynak_secim}|{','.join(str(_n) for _n in aktif_numaralar)}"
            if (
                st.session_state.get("_sm_item_source_sig") != _sm_item_source_sig
                or "sm_item_select_all" not in st.session_state
            ):
                st.session_state["sm_item_select_all"] = _tum_secili_varsayilan
                st.session_state["_sm_item_select_all_prev"] = _tum_secili_varsayilan
                st.session_state["_sm_item_source_sig"] = _sm_item_source_sig

            tum_video_secili = st.checkbox(
                f"Tüm {oge_etiketi.lower()}ları seç",
                key="sm_item_select_all",
            )
            # Tümünü seç değiştiğinde bireysel seçimleri güncelle
            if st.session_state.get("_sm_item_select_all_prev") is not None and st.session_state.get("_sm_item_select_all_prev") != tum_video_secili:
                for _ii in aktif_numaralar:
                    st.session_state[f"sm_item_selected_{_ii}"] = tum_video_secili
            st.session_state["_sm_item_select_all_prev"] = tum_video_secili

            _secili_video_sayisi = 0

            for i in aktif_numaralar:
                item_cfg = dict(item_defaults.get(i) or {})
                item_baslik = item_cfg.get("baslik", "")
                item_aciklama = item_cfg.get("aciklama", "")
                item_secimler = item_cfg.get("secimler") or {"youtube": False, "tiktok": False, "instagram": False}
                item_publish_mode = "Hemen Paylaş" if sosyal_medya_publish_mode_normalize(item_cfg.get("publish_mode")) == "publish_now" else "Zamanla"
                item_gun = item_cfg.get("gun", "")
                item_saat = item_cfg.get("saat", "")
                item_selected_default = bool(item_cfg.get("selected", True))
                doluluk_icon = "✅" if sosyal_medya_item_dolu_mu(item_cfg) else "⬜"

                if kaynak_secim == "🎬 Toplu Video Montaj":
                    kaynak_etiketi = "🎬 Toplu Video Montaj"
                    oge_etiketi_i = "Video"
                elif kaynak_secim == "🖼️ Görsel Oluştur":
                    kaynak_etiketi = "🖼️ Görsel Oluştur"
                    oge_etiketi_i = "Video"
                elif kaynak_secim == "🎞️ Video Ekle":
                    kaynak_etiketi = "🎞️ Video Ekle"
                    oge_etiketi_i = "Video"
                elif kaynak_secim == "🎞️ Video Montaj":
                    kaynak_etiketi = "🎞️ Video Montaj"
                    oge_etiketi_i = "Video"
                elif kaynak_secim == "Link":
                    oge_etiketi_i = (_link_kaynak_haritasi.get(i) if '_link_kaynak_haritasi' in locals() else None) or "Link"
                    kaynak_etiketi = oge_etiketi_i
                else:
                    kaynak_etiketi = "Video"
                    oge_etiketi_i = "Video"

                # ── Seçim checkbox'u + Expander ──
                _item_selected_key = f"sm_item_selected_{i}"
                if _item_selected_key not in st.session_state:
                    st.session_state[_item_selected_key] = item_selected_default

                _sel_col, _exp_col = st.columns([0.06, 0.94])
                with _sel_col:
                    item_selected_i = st.checkbox(
                        f"Seç {i}",
                        key=_item_selected_key,
                        label_visibility="collapsed",
                    )
                if item_selected_i:
                    _secili_video_sayisi += 1

                with _exp_col:
                  with st.expander(f"{doluluk_icon} {oge_etiketi_i} {i}", expanded=False):
                    st.caption(f"Kaynak: {kaynak_etiketi}")

                    st.markdown(f"#### 🏷️ {oge_etiketi_i} Başlık")
                    baslik_i = st.text_area(
                        f"{oge_etiketi_i} {i} Başlık",
                        value=item_baslik,
                        height=90,
                        key=f"sm_item_baslik_{i}",
                        placeholder=f"Bu {oge_etiketi_i.lower()} için başlık",
                        label_visibility="collapsed",
                    )

                    st.markdown(f"#### 📄 {oge_etiketi_i} Açıklama")
                    aciklama_i = st.text_area(
                        f"{oge_etiketi_i} {i} Açıklama",
                        value=item_aciklama,
                        height=130,
                        key=f"sm_item_aciklama_{i}",
                        placeholder=f"Bu {oge_etiketi_i.lower()} için açıklama",
                        label_visibility="collapsed",
                    )

                    st.markdown("#### 🌐 Paylaşılacak Sosyal Medyalar")
                    cc1, cc2, cc3 = st.columns(3)
                    with cc1:
                        youtube_i = st.checkbox("YouTube", value=item_secimler.get("youtube", False), key=f"sm_item_youtube_{i}")
                    with cc2:
                        tiktok_i = st.checkbox("TikTok", value=item_secimler.get("tiktok", False), key=f"sm_item_tiktok_{i}")
                    with cc3:
                        instagram_i = st.checkbox("Instagram", value=item_secimler.get("instagram", False), key=f"sm_item_instagram_{i}")

                    st.markdown("#### 🕒 Paylaşım Şekli")
                    publish_mode_i = st.radio(
                        f"{oge_etiketi_i} {i} Paylaşım Şekli",
                        ["Zamanla", "Hemen Paylaş"],
                        index=0 if item_publish_mode == "Zamanla" else 1,
                        key=f"sm_item_publish_mode_{i}",
                        horizontal=True,
                        label_visibility="collapsed",
                    )
                    if publish_mode_i == "Hemen Paylaş":
                        gun_i = ""
                        saat_i = ""
                        st.caption("Hemen Paylaş seçildiğinde zamanlama kullanılmaz; yükleme tamamlanınca doğrudan paylaşım butonuna basılır.")
                    else:
                        cc4, cc5 = st.columns(2)
                        with cc4:
                            gun_i = st.text_input("Gün", value=item_gun, key=f"sm_item_gun_{i}", placeholder="Örn: 22")
                        with cc5:
                            saat_i = st.text_input("Saat", value=item_saat, key=f"sm_item_saat_{i}", placeholder="Örn: 20:00")

                    item_payload[i] = {
                        "baslik": baslik_i,
                        "aciklama": aciklama_i,
                        "secimler": {"youtube": youtube_i, "tiktok": tiktok_i, "instagram": instagram_i},
                        "publish_mode": publish_mode_i,
                        "gun": gun_i,
                        "saat": saat_i,
                        "selected": item_selected_i,
                    }

            # Seçili video sayısı bilgisi
            _secim_caption_etiketi = "kaynak" if kaynak_secim == "Link" else oge_etiketi.lower()
            if _secili_video_sayisi == len(aktif_numaralar):
                st.caption(f"✅ Tüm {_secim_caption_etiketi}lar seçili ({_secili_video_sayisi}/{len(aktif_numaralar)}) — Zamanla seçildiğinde ekranda 24 saat formatı kullanılır. Kaydedildiğinde txt içine İngilizce 12 saat formatında yazılır.")
            elif _secili_video_sayisi == 0:
                st.caption(f"⚠️ Hiçbir {_secim_caption_etiketi} seçili değil — Paylaşım yapılmayacak. Lütfen en az bir {_secim_caption_etiketi} seçin.")
            else:
                st.caption(f"📌 {_secili_video_sayisi}/{len(aktif_numaralar)} {_secim_caption_etiketi} seçili — Sadece seçili olanlar paylaşılacak. Zamanla seçildiğinde 24 saat formatı kullanılır.")

        def _save_social_settings():
            if not aktif_numaralar:
                st.session_state["sm_error_notice"] = "Önce kaynak seçin ve ilgili bölümden video/link ekleyin."
                return False
            return sosyal_medya_kaydet_per_item(item_payload)

    def _save_account_settings(require_account: bool = False):
        hesaplar, invalid_rows = _sm_collect_accounts_from_rows()
        if invalid_rows:
            st.session_state["sm_error_notice"] = f"Eksik bilgi olan hesap satırları var: {', '.join(str(x) for x in invalid_rows)}"
            return False
        if require_account and not hesaplar:
            st.session_state["sm_error_notice"] = "En az 1 geçerli hesap girin."
            return False

        kayit_modu = "bulk" if toplu_hesap_modu else "single"
        hesap_dongu_aktif = bool(hesap_loop) if toplu_hesap_modu else False
        ok = sosyal_medya_hesap_konfig_kaydet(
            kayit_modu,
            hesaplar,
            hesap_dongu_aktif,
        )
        if ok:
            visible_rows = [
                {"token": item.get("token", ""), "email": item.get("email", ""), "password": "", "selected": bool(item.get("selected", True))}
                for item in hesaplar
            ]
            if not visible_rows:
                visible_rows = [{"token": "", "email": "", "password": "", "selected": False}]

            ilk_kayit = dict(visible_rows[0] if visible_rows else {"token": "", "email": "", "password": ""})
            st.session_state["sm_accounts_rows"] = visible_rows
            st.session_state["sm_select_all_accounts_prev"] = False
            st.session_state["sm_last_hesap_mode_rendered"] = "Toplu Hesap" if toplu_hesap_modu else "Tek Hesap"
            _sm_schedule_account_ui_reset(
                rows=visible_rows,
                hesap_modu="Toplu Hesap" if toplu_hesap_modu else "Tek Hesap",
                hesap_dongu=hesap_dongu_aktif,
                select_all=False,
                single_token=ilk_kayit.get("token", ""),
            )
        return ok

    save_cols = st.columns(2)
    with save_cols[0]:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("💾 Kaydet", key="sm_save_btn", use_container_width=True):
            ok_hesap = _save_account_settings(require_account=False)
            ok = ok_hesap and _save_social_settings()
            if ok:
                st.session_state.pop("sm_error_notice", None)
                st.session_state["sm_saved_notice"] = True
                st.session_state.ek_dialog_open = "sosyal_medya"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with save_cols[1]:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("🗑️ Temizle", key="sm_clear_btn", use_container_width=True):
            mevcut_hesap_satirlari = []
            for row in list(st.session_state.get("sm_accounts_rows", []) or []):
                mevcut_hesap_satirlari.append({
                    "token": str((row or {}).get("token", "") or ""),
                    "email": str((row or {}).get("email", "") or ""),
                    "password": "",
                    "selected": True,  # Temizle: hesap seçimlerini sıfırla (tümü seçili yap)
                })
            if not mevcut_hesap_satirlari:
                mevcut_hesap_satirlari = [{"token": "", "email": "", "password": "", "selected": False}]

            _sm_schedule_account_ui_reset(
                rows=mevcut_hesap_satirlari,
                hesap_modu=st.session_state.get("sm_hesap_modu", "Tek Hesap"),
                hesap_dongu=bool(st.session_state.get("sm_hesap_dongu", False)),
                select_all=True,  # Temizle: tüm hesaplar seçili olarak sıfırlanır
                single_token=st.session_state.get("sm_single_token", ""),
            )
            _sm_schedule_form_ui_reset(
                ayar_modu="Genel",
                video_kaynak_secim="Link",
                kaynak_radio="Link",
                baslik="",
                aciklama="",
                platform_secimler={"youtube": False, "tiktok": False, "instagram": False},
                publish_mode="schedule",
                gun="",
                saat="",
                clear_item_keys=True,
                drop_loaded=True,
            )
            st.session_state["sm_accounts_rows"] = mevcut_hesap_satirlari
            st.session_state["sm_select_all_accounts_prev"] = True
            ok = sosyal_medya_temizle(clear_legacy=True, preserve_accounts=True)
            if ok:
                cleanup_social_media_state_files(clear_saved_plan=False, preserve_accounts=True)
                st.session_state.pop("sm_error_notice", None)
                st.session_state["sm_saved_notice"] = True
                st.session_state.ek_dialog_open = "sosyal_medya"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if not script_exists:
        st.warning("Sosyal medya script yolu geçersiz. Ayarlar bölümünden sosyal medya script yolunu kontrol edin.")

    st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
    if st.button("🚀 Paylaşımı Başlat", key="sm_start_btn", use_container_width=True, disabled=st.session_state.get("batch_mode", False) or any_running() or (not script_exists)):
        ok_hesap = _save_account_settings(require_account=True)
        ok = ok_hesap and _save_social_settings()
        if ok:
            st.session_state.pop("sm_error_notice", None)
            st.session_state.ek_dialog_open = "sosyal_medya"
            st.session_state.single_paused = False
            st.session_state.single_finish_requested = False
            st.session_state.single_mode = True
            st.session_state.single_step = "sosyal_medya"
            cleanup_flags()
            st.session_state.status["sosyal_medya"] = "running"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    render_dialog_single_controls(step_match="sosyal_medya", prefix="dlg_sosyal_medya")

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="bck_sosyal_medya", use_container_width=True):
        st.session_state.ek_dialog_open = "menu"
        st.session_state.pop("sm_video_kaynak_secim_loaded", None)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---- VİDEO AYARLARI DIALOG ----
# Her modelin script klasoründeki video_boyutu_süresi_ses.txt dosyasını okuyup yazan dialog.
# Format (satır bazında): aspect_ratio / süre / ses / quality / model

_VIDEO_AYAR_MODEL_HARITA = {
    "Sora 2": {
        "script_key": "sora2_script",
        "default_model": "sora-2",
        "models": ["sora-2", "sora-2-pro"],
        "quality_map": {
            "sora-2": ["720p"],
            "sora-2-pro": ["720p", "1080p"],
        },
        "durations": [4, 8, 12],
        "ses": True,
    },
    "PixVerse V6": {
        "script_key": "v56_script",
        "default_model": "v6",
        "models": ["v6"],
        "quality_map": {
            "v6": ["360p", "540p", "720p", "1080p"],
        },
        "durations": list(range(1, 16)),
        "ses": True,
    },
    "Veo 3.1 Standard": {
        "script_key": "veo31_script",
        "default_model": "veo-3.1-standard",
        "models": ["veo-3.1-standard"],
        "quality_map": {
            "veo-3.1-standard": ["360p", "540p", "720p", "1080p"],
        },
        "durations": [4, 6, 8],
        "ses": True,
    },
    "Grok": {
        "script_key": "grok_script",
        "default_model": "grok-imagine",
        "models": ["grok-imagine"],
        "quality_map": {
            "grok-imagine": ["360p", "540p", "720p"],
        },
        "durations": [5, 8, 10, 15],
        "ses": True,
    },
    "PixVerse Cinematic": {
        "script_key": "c1_script",
        "default_model": "pixverse-c1",
        "models": ["pixverse-c1"],
        "quality_map": {
            "pixverse-c1": ["360p", "540p", "720p", "1080p"],
        },
        "durations": list(range(1, 16)),
        "ses": True,
    },
}

def _prompt_input_selection_state_path() -> str:
    return os.path.join(CONTROL_DIR, "prompt_input_selection.json")

def _list_prompt_input_entries() -> dict:
    s = st.session_state.settings
    result = {"links": [], "downloaded_videos": [], "added_videos": []}
    
    links_file = s.get("links_file", "")
    if os.path.exists(links_file):
        try:
            with open(links_file, "r", encoding="utf-8") as f:
                result["links"] = [l.strip() for l in f.readlines() if l.strip().lower().startswith("http")]
        except Exception:
            pass
            
    ddir = s.get("download_dir", "")
    if os.path.exists(ddir):
        try:
            for subdir in os.listdir(ddir):
                subpath = os.path.join(ddir, subdir)
                if os.path.isdir(subpath):
                    vids = [f for f in os.listdir(subpath) if f.lower().endswith(('.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v'))]
                    if vids: result["downloaded_videos"].append(vids[0])
        except Exception:
            pass
            
    adir = s.get("added_video_dir", "")
    if os.path.exists(adir):
        try:
            for subdir in os.listdir(adir):
                subpath = os.path.join(adir, subdir)
                if os.path.isdir(subpath):
                    vids = [f for f in os.listdir(subpath) if f.lower().endswith(('.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v'))]
                    if vids: result["added_videos"].append(vids[0])
        except Exception:
            pass
            
    return result

def _prompt_input_selection_load() -> dict:
    state = {"mode": "all", "selected_items": {"links": [], "downloaded_videos": [], "added_videos": []}}
    state_path = _prompt_input_selection_state_path()
    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                mode = str(data.get("mode") or "all").strip().lower()
                if mode in {"all", "custom"}:
                    state["mode"] = mode
                selected = data.get("selected_items")
                if isinstance(selected, dict):
                    if isinstance(selected.get("links"), list):
                        state["selected_items"]["links"] = selected["links"]
                    if isinstance(selected.get("downloaded_videos"), list):
                        state["selected_items"]["downloaded_videos"] = selected["downloaded_videos"]
                    if isinstance(selected.get("added_videos"), list):
                        state["selected_items"]["added_videos"] = selected["added_videos"]
    except Exception:
        pass
    return state

def _prompt_input_selection_save(mode: str, selected_items: dict) -> bool:
    payload = {
        "mode": mode,
        "selected_items": selected_items,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(_prompt_input_selection_state_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

@st.dialog("✏️ Prompt Ayarları", width="large")
def prompt_ayarlari_dialog():
    st.markdown("Prompt üretilecek olan hedefleri tek tek veya toplu olarak seçebilirsiniz.")
    entries = _list_prompt_input_entries()
    current_state = _prompt_input_selection_load()
    
    tumunu_uret = st.checkbox("Tüm girdiler için üret", value=(current_state.get("mode") != "custom"), key="pa_select_all")
    
    st.markdown("#### 🔗 Prompt Üretilecek Linkler")
    secili_linkler = st.multiselect(
        "Linkleri seçin",
        options=entries["links"],
        default=entries["links"] if tumunu_uret else [x for x in current_state["selected_items"]["links"] if x in entries["links"]],
        disabled=tumunu_uret,
        format_func=lambda x: f"Link {entries['links'].index(x) + 1}",
        key="pa_links"
    )
    
    st.markdown("#### 📥 Prompt Üretilecek İndirilen Videolar")
    secili_indirilen = st.multiselect(
        "İndirilen videoları seçin",
        options=entries["downloaded_videos"],
        default=entries["downloaded_videos"] if tumunu_uret else [x for x in current_state["selected_items"]["downloaded_videos"] if x in entries["downloaded_videos"]],
        disabled=tumunu_uret,
        format_func=lambda x: f"İndirilen Video {entries['downloaded_videos'].index(x) + 1}",
        key="pa_down"
    )
    
    st.markdown("#### 🎞️ Prompt Üretilecek Eklenen Videolar")
    secili_eklenen = st.multiselect(
        "Eklenen videoları seçin",
        options=entries["added_videos"],
        default=entries["added_videos"] if tumunu_uret else [x for x in current_state["selected_items"]["added_videos"] if x in entries["added_videos"]],
        disabled=tumunu_uret,
        format_func=lambda x: f"Eklenen Video {entries['added_videos'].index(x) + 1}",
        key="pa_add"
    )
    
    st.markdown("---")
    cols = st.columns(2)
    with cols[0]:
        if st.button("İptal / Geri Dön", use_container_width=True):
            st.session_state.ek_dialog_open = "menu"
            st.rerun()
    with cols[1]:
        if st.button("Kaydet", type="primary", use_container_width=True):
            new_mode = "all" if tumunu_uret else "custom"
            _prompt_input_selection_save(new_mode, {
                "links": secili_linkler,
                "downloaded_videos": secili_indirilen,
                "added_videos": secili_eklenen
            })
            st.success("Ayarlar kaydedildi!")
            time.sleep(0.7)
            st.session_state.ek_dialog_open = "prompt_ayarlari"
            st.rerun()


def _video_prompt_selection_state_path() -> str:
    return os.path.join(CONTROL_DIR, "video_prompt_selection.json")


def _list_video_prompt_entries(prompt_dir: str | None = None) -> list:
    root = (prompt_dir or st.session_state.settings.get("prompt_dir", "") or "").strip()
    if not root or not os.path.isdir(root):
        return []

    out = []
    try:
        for folder_name in os.listdir(root):
            folder_path = os.path.join(root, folder_name)
            prompt_path = os.path.join(folder_path, "prompt.txt")
            if not (os.path.isdir(folder_path) and os.path.exists(prompt_path)):
                continue

            prompt_text = ""
            try:
                with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
                    prompt_text = f.read().strip()
            except Exception:
                prompt_text = ""

            out.append({
                "folder_name": folder_name,
                "folder_path": folder_path,
                "prompt_path": prompt_path,
                "prompt_preview": (prompt_text[:140] + "…") if len(prompt_text) > 140 else prompt_text,
            })
    except Exception:
        return []

    out.sort(key=lambda item: natural_sort_key(item.get("folder_name", "")))
    return out


def _video_prompt_selection_load(available_prompt_names: list | None = None) -> dict:
    state = {"mode": "all", "selected_prompt_folders": []}
    state_path = _video_prompt_selection_state_path()

    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                mode = str(data.get("mode") or "all").strip().lower()
                selected = data.get("selected_prompt_folders") or []
                if mode in {"all", "custom"}:
                    state["mode"] = mode
                if isinstance(selected, list):
                    temiz = []
                    for item in selected:
                        name = str(item or "").strip()
                        if name and name not in temiz:
                            temiz.append(name)
                    state["selected_prompt_folders"] = temiz
    except Exception:
        pass

    if isinstance(available_prompt_names, list):
        mevcut = [str(name or "").strip() for name in available_prompt_names if str(name or "").strip()]
        if not mevcut:
            return {"mode": "all", "selected_prompt_folders": []}

        secili = [name for name in state.get("selected_prompt_folders", []) if name in mevcut]
        if state.get("mode") != "custom" or not secili or len(secili) >= len(mevcut):
            return {"mode": "all", "selected_prompt_folders": []}
        return {"mode": "custom", "selected_prompt_folders": secili}

    return state


def _video_prompt_selection_save(selected_prompt_folders: list, available_prompt_names: list | None = None) -> dict:
    available = [str(name or "").strip() for name in (available_prompt_names or []) if str(name or "").strip()]
    selected = []
    for item in (selected_prompt_folders or []):
        name = str(item or "").strip()
        if not name:
            continue
        if available and name not in available:
            continue
        if name not in selected:
            selected.append(name)

    if not available or not selected or len(selected) >= len(available):
        payload = {
            "mode": "all",
            "selected_prompt_folders": [],
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    else:
        payload = {
            "mode": "custom",
            "selected_prompt_folders": selected,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    try:
        with open(_video_prompt_selection_state_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return payload


def _prepare_pixverse_prompt_override_if_needed() -> bool:
    if st.session_state.get("pixverse_prompt_override_meta"):
        return True

    current_settings = dict(st.session_state.get("settings", {}) or {})
    original_prompt_dir = (current_settings.get("prompt_dir") or "").strip()
    prompt_entries = _list_video_prompt_entries(original_prompt_dir)
    available_names = [item.get("folder_name", "") for item in prompt_entries]

    secim = _video_prompt_selection_load(available_names)
    selected_names = secim.get("selected_prompt_folders", [])

    if secim.get("mode") != "custom" or not selected_names:
        return True

    selected_entries = [item for item in prompt_entries if item.get("folder_name") in selected_names]
    if not selected_entries:
        return True

    temp_root = os.path.join(CONTROL_DIR, f"pixverse_prompt_override_{int(time.time() * 1000)}")
    stash_dir = os.path.join(temp_root, "stash")
    moved_folders = []
    selected_set = {item.get("folder_name", "") for item in selected_entries}

    try:
        os.makedirs(stash_dir, exist_ok=True)
        for item in prompt_entries:
            folder_name = item.get("folder_name", "")
            if folder_name in selected_set:
                continue
            src = item.get("folder_path", "")
            dst = os.path.join(stash_dir, folder_name)
            if not src or not os.path.isdir(src):
                continue
            shutil.move(src, dst)
            moved_folders.append(folder_name)

        st.session_state.pixverse_prompt_override_meta = {
            "original_prompt_dir": original_prompt_dir,
            "temp_root": temp_root,
            "stash_dir": stash_dir,
            "moved_folders": moved_folders,
            "selected_prompt_folders": [item.get("folder_name", "") for item in selected_entries],
        }
        log(f"[INFO] Video üretimi için seçili promptlar hazırlandı: {', '.join(item.get('folder_name', '') for item in selected_entries)}")
        return True
    except Exception as e:
        st.session_state.pixverse_prompt_override_meta = {
            "original_prompt_dir": original_prompt_dir,
            "temp_root": temp_root,
            "stash_dir": stash_dir,
            "moved_folders": moved_folders,
        }
        _cleanup_pixverse_prompt_override()
        log(f"[ERROR] Seçili promptlar hazırlanamadı: {e}")
        return False


def _cleanup_pixverse_prompt_override():
    meta = st.session_state.get("pixverse_prompt_override_meta")
    if not isinstance(meta, dict):
        st.session_state.pixverse_prompt_override_meta = None
        return

    if meta.get("is_gorsel_override"):
        orig_dir = meta.get("original_settings_prompt_dir")
        orig_ref = meta.get("original_settings_ref_dir")
        if orig_dir is not None:
            st.session_state.settings["prompt_dir"] = orig_dir
        if orig_ref is not None:
            st.session_state.settings["gorsel_klonlama_dir"] = orig_ref
        save_settings(st.session_state.settings)
        st.session_state.pixverse_prompt_override_meta = None
        return

    original_prompt_dir = (meta.get("original_prompt_dir") or "").strip()
    stash_dir = (meta.get("stash_dir") or "").strip()
    moved_folders = meta.get("moved_folders") or []

    for folder_name in moved_folders:
        name = str(folder_name or "").strip()
        if not name:
            continue
        src = os.path.join(stash_dir, name) if stash_dir else ""
        dst = os.path.join(original_prompt_dir, name) if original_prompt_dir else ""
        try:
            if src and dst and os.path.exists(src) and not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
        except Exception as e:
            log(f"[WARN] Prompt klasörü geri taşınamadı ({name}): {e}")

    temp_root = (meta.get("temp_root") or "").strip()
    if temp_root:
        try:
            shutil.rmtree(temp_root, ignore_errors=True)
        except Exception:
            pass

    st.session_state.pixverse_prompt_override_meta = None


def start_pixverse_bg(owner: str) -> bool:
    overridden = False
    extra_args = []
    if _should_use_gorsel_motion_prompts():
        overridden = True
        extra_args = ["--prompt-dir", GORSEL_HAREKET_PROMPT_DIR, "--ref-image-dir", GORSEL_HAREKET_REFERANS_DIR]
        st.session_state.pixverse_prompt_override_meta = {
            "is_gorsel_override": True,
            "original_settings_prompt_dir": st.session_state.settings.get("prompt_dir", ""),
            "original_settings_ref_dir": st.session_state.settings.get("gorsel_klonlama_dir", "")
        }
        # settings.local.json'a dogrudan yaz (script modul-level okumasi icin)
        try:
            import json as _json
            with open(SETTINGS_PATH, "r", encoding="utf-8") as _rf:
                _current = _json.load(_rf)
            _current["prompt_dir"] = GORSEL_HAREKET_PROMPT_DIR
            _current["gorsel_klonlama_dir"] = GORSEL_HAREKET_REFERANS_DIR
            with open(SETTINGS_PATH, "w", encoding="utf-8") as _wf:
                _json.dump(_current, _wf, ensure_ascii=False, indent=2)
            log(f"[INFO] Görsel hareketlendirme promptları aktif. PROMPT_ROOT override: {GORSEL_HAREKET_PROMPT_DIR}")
        except Exception as _e:
            log(f"[WARN] settings.json prompt_dir yazilamadi: {_e}")
        
    if not overridden:
        if not _prepare_pixverse_prompt_override_if_needed():
            st.session_state.status["pixverse"] = "error"
            return False

    ok = bg_start(owner, "pixverse", get_active_video_script(st.session_state.settings), args=extra_args)
    if not ok:
        _cleanup_pixverse_prompt_override()
    return ok


def _video_ayar_txt_yolu(model_adi: str) -> str:
    """Model adına göre video_boyutu_süresi_ses.txt dosyasının tam yolunu döndürür."""
    harita = _VIDEO_AYAR_MODEL_HARITA.get(model_adi)
    if not harita:
        return ""
    s = st.session_state.settings
    script_path = s.get(harita["script_key"], "")
    if not script_path:
        return ""
    return os.path.join(os.path.dirname(script_path), "video_boyutu_s\u00fcresi_ses.txt")

def _video_ayar_oku(txt_path: str) -> dict:
    """video_boyutu_süresi_ses.txt dosyasını okur ve dict döndürür."""
    result = {"aspect_ratio": "16:9", "duration": "", "ses": "kapalı", "quality": "", "model": ""}
    if not txt_path or not os.path.exists(txt_path):
        return result
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if len(lines) >= 1: result["aspect_ratio"] = lines[0]
        if len(lines) >= 2: result["duration"] = lines[1]
        if len(lines) >= 3: result["ses"] = lines[2]
        if len(lines) >= 4: result["quality"] = lines[3]
        if len(lines) >= 5: result["model"] = lines[4]
    except Exception:
        pass
    return result

def _video_ayar_kaydet(txt_path: str, aspect_ratio: str, duration: str, ses: str, quality: str, model: str) -> bool:
    """video_boyutu_süresi_ses.txt dosyasına ayarları yazar."""
    try:
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"{aspect_ratio}\n{duration}\n{ses}\n{quality}\n{model}\n")
        return True
    except Exception:
        return False

@st.dialog("🎬 Video Ayarları", width="large")
def video_ayarlari_dialog():
    st.markdown("Üretilecek promptları seçip ardından model, video boyutu, süresi, kalite ve ses ayarlarını yapın.")

    prompt_entries = _list_video_prompt_entries()
    prompt_options = [item.get("folder_name", "") for item in prompt_entries]
    secili_prompt_state = _video_prompt_selection_load(prompt_options)

    st.markdown("#### 📝 Üretilecek Promptlar")

    if prompt_options:
        tumunu_uret = st.checkbox(
            "Tüm promptları üret",
            value=(secili_prompt_state.get("mode") != "custom"),
            key="va_prompt_select_all",
        )
        varsayilan_secili = prompt_options if tumunu_uret else secili_prompt_state.get("selected_prompt_folders", [])
        secili_promptlar = st.multiselect(
            "İstediğiniz promptları seçin",
            options=prompt_options,
            default=varsayilan_secili,
            key="va_prompt_selection",
            disabled=tumunu_uret,
        )
        secili_sayi = len(prompt_options) if tumunu_uret else len(secili_promptlar)
        st.caption(f"Toplam {len(prompt_options)} prompt bulundu. Kaydettiğinizde {secili_sayi} prompt için video üretilecek.")
    else:
        tumunu_uret = True
        secili_promptlar = []
        st.info("Henüz prompt klasörü bulunamadı. Video üretimi başladığında sistem mevcut promptları kullanır.")

    st.markdown("---")

    model_secenekleri = list(_VIDEO_AYAR_MODEL_HARITA.keys())
    aktif_model = get_active_video_model()
    default_idx = model_secenekleri.index(aktif_model) if aktif_model in model_secenekleri else 0
    secilen_model = st.selectbox("🎬 Model Seçimi", model_secenekleri, index=default_idx, key="va_model_sec")

    harita = _VIDEO_AYAR_MODEL_HARITA[secilen_model]
    txt_path = _video_ayar_txt_yolu(secilen_model)
    mevcut = _video_ayar_oku(txt_path)

    alt_modeller = harita["models"]
    if len(alt_modeller) > 1:
        mevcut_alt = mevcut.get("model", harita["default_model"])
        alt_idx = alt_modeller.index(mevcut_alt) if mevcut_alt in alt_modeller else 0
        secilen_alt_model = st.selectbox("📌 Alt Model", alt_modeller, index=alt_idx, key="va_alt_model")
    else:
        secilen_alt_model = alt_modeller[0]

    kalite_listesi = harita["quality_map"].get(secilen_alt_model, ["720p"])
    mevcut_kalite = mevcut.get("quality", kalite_listesi[-1])
    kalite_idx = kalite_listesi.index(mevcut_kalite) if mevcut_kalite in kalite_listesi else len(kalite_listesi) - 1
    secilen_kalite = st.selectbox("🎯 Kalite", kalite_listesi, index=kalite_idx, key="va_kalite")

    boyut_secenekleri = ["16:9", "9:16"]
    mevcut_boyut = mevcut.get("aspect_ratio", "16:9")
    boyut_idx = boyut_secenekleri.index(mevcut_boyut) if mevcut_boyut in boyut_secenekleri else 0
    secilen_boyut = st.selectbox("📏 Video Boyutu", boyut_secenekleri, index=boyut_idx, key="va_boyut")

    sureler = harita["durations"]
    sure_etiketleri = [f"{s}s" for s in sureler]
    mevcut_sure_raw = mevcut.get("duration", "")
    mevcut_sure_int = int(re.sub(r'[^0-9]', '', mevcut_sure_raw)) if re.sub(r'[^0-9]', '', mevcut_sure_raw) else sureler[0]
    sure_idx = sureler.index(mevcut_sure_int) if mevcut_sure_int in sureler else 0
    secilen_sure = st.selectbox("⏱️ Video Süresi", sure_etiketleri, index=sure_idx, key="va_sure")
    secilen_sure_int = sureler[sure_etiketleri.index(secilen_sure)]

    if harita.get("ses", False):
        ses_secenekleri = ["açık", "kapalı"]
        mevcut_ses = mevcut.get("ses", "kapalı").lower()
        ses_idx = ses_secenekleri.index(mevcut_ses) if mevcut_ses in ses_secenekleri else 1
        secilen_ses = st.selectbox("🔊 Ses", ses_secenekleri, index=ses_idx, key="va_ses")
    else:
        secilen_ses = "kapalı"

    kisit = harita.get("kisitlar", "")
    if kisit:
        st.info(f"⚠️ {kisit}")

    _v56_kisit_hatasi = False

    st.markdown("---")
    c_save, c_back = st.columns(2)
    with c_save:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("💾 Kaydet", use_container_width=True, key="va_kaydet", disabled=_v56_kisit_hatasi):
            if not tumunu_uret and not secili_promptlar:
                st.error("❌ En az 1 prompt seçin veya 'Tüm promptları üret' seçeneğini açın.")
            elif txt_path:
                ok = _video_ayar_kaydet(txt_path, secilen_boyut, f"{secilen_sure_int}s", secilen_ses, secilen_kalite, secilen_alt_model)
                if ok:
                    kayit = _video_prompt_selection_save(
                        prompt_options if tumunu_uret else secili_promptlar,
                        prompt_options,
                    )
                    if kayit.get("mode") == "custom":
                        secim_ozeti = ", ".join(kayit.get("selected_prompt_folders", []))
                        log(f"[INFO] Seçili promptlar kaydedildi: {secim_ozeti}")
                    else:
                        log("[INFO] Video üretimi tüm promptlar için ayarlandı.")
                    log(f"[INFO] Video ayarları kaydedildi: {secilen_model} → {secilen_boyut}, {secilen_sure_int}s, {secilen_kalite}, ses={secilen_ses}, model={secilen_alt_model}")
                    st.success("✅ Ayarlar kaydedildi! Video Üret dediğinizde seçtiğiniz promptlar kullanılacak.")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("❌ Ayarlar kaydedilemedi!")
            else:
                st.error("❌ Script yolu bulunamadı!")
        st.markdown('</div>', unsafe_allow_html=True)
    with c_back:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("⬅️ Geri", key="bck_video_ayar", use_container_width=True):
            st.session_state.ek_dialog_open = "menu"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ---- VİDEO ÜRETME KREDİSİ DIALOG ----
PIXVERSE5_SCRIPT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Pixverse Kredi Üyeliği Oluşturma\pixverse5.py"
KREDI_YENILEME_SCRIPT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Pixverse Kredi Kazanma\kredi_yenileme.py"

@st.dialog("💳 Video Üretme Kredisi", width="large")
def kredi_dialog():
    if bg_is_running():
        _bg_n = st.session_state.get("bg_node_key")
        if _bg_n == "kredi_kazan":
            st.session_state.kredi_kazan_running = True
            st.session_state.ek_dialog_open = "kredi"
        elif _bg_n == "kredi_cek":
            st.session_state.kredi_cek_running = True
            st.session_state.ek_dialog_open = "kredi"

    is_running = any_running()
    kredi_is_running = st.session_state.get("kredi_kazan_running", False) or st.session_state.get("kredi_cek_running", False)
    aktif_kredi_step = None
    if st.session_state.get("kredi_kazan_running", False) or (bg_is_running() and st.session_state.get("bg_node_key") == "kredi_kazan"):
        aktif_kredi_step = "kredi_kazan"
    elif st.session_state.get("kredi_cek_running", False) or (bg_is_running() and st.session_state.get("bg_node_key") == "kredi_cek"):
        aktif_kredi_step = "kredi_cek"

    kc1, kc2 = st.columns(2)
    with kc1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.session_state.get("kredi_kazan_running", False):
            st.button("⏳ Kredi Kazanılıyor...", use_container_width=True, disabled=True, key="dlg_kredi_kazan_busy")
        else:
            if st.button("🎰 Video Üretme Kredisi Kazan", use_container_width=True, disabled=kredi_is_running or is_running, key="dlg_kredi_kazan_btn"):
                st.session_state.kredi_kazan_running = True
                st.session_state.kredi_kazan_paused = False
                st.session_state.kredi_kazan_finish = False
                st.session_state.kredi_cek_running = False
                st.session_state.kredi_cek_paused = False
                st.session_state.kredi_cek_finish = False
                st.session_state.kredi_kazan_start_ts = time.time()
                st.session_state.bg_last_result = None
                st.session_state.ek_dialog_open = "kredi"
                if os.path.exists(PIXVERSE5_SCRIPT):
                    script_dir = os.path.dirname(PIXVERSE5_SCRIPT)
                    pause_file = os.path.join(script_dir, "pause.txt")
                    try:
                        with open(pause_file, "w") as pf:
                            pf.write("resume")
                    except Exception:
                        pass
                    bg_start("kredi_kazan", "kredi_kazan", PIXVERSE5_SCRIPT)
                    log("[INFO] Video Üretme Kredisi Kazan işlemi başlatıldı.")
                else:
                    log(f"[ERROR] pixverse5.py bulunamadı: {PIXVERSE5_SCRIPT}")
                    st.session_state.kredi_kazan_running = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with kc2:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.session_state.get("kredi_cek_running", False):
            st.button("⏳ Krediler Çekiliyor...", use_container_width=True, disabled=True, key="dlg_kredi_cek_busy")
        else:
            if st.button("📥 Üretilen Kredileri Çek", use_container_width=True, disabled=kredi_is_running or is_running, key="dlg_kredi_cek_btn"):
                st.session_state.kredi_cek_running = True
                st.session_state.kredi_cek_paused = False
                st.session_state.kredi_cek_finish = False
                st.session_state.kredi_kazan_running = False
                st.session_state.kredi_kazan_paused = False
                st.session_state.kredi_kazan_finish = False
                st.session_state.kredi_cek_start_ts = time.time()
                st.session_state.bg_last_result = None
                st.session_state.ek_dialog_open = "kredi"
                if os.path.exists(KREDI_YENILEME_SCRIPT):
                    bg_start("kredi_cek", "kredi_cek", KREDI_YENILEME_SCRIPT)
                    log("[INFO] Üretilen Kredileri Çek işlemi başlatıldı.")
                else:
                    log(f"[ERROR] kredi_yenileme.py bulunamadı: {KREDI_YENILEME_SCRIPT}")
                    st.session_state.kredi_cek_running = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Kredi Kazan veya Çek işlemi çalışıyorsa kontrol butonlarını başlıksız göster
    if aktif_kredi_step:
        st.markdown('<hr style="margin:10px 0 6px 0;border-color:rgba(255,255,255,0.10);">', unsafe_allow_html=True)
        render_dialog_single_controls(step_match=aktif_kredi_step, prefix=f"dlg_{aktif_kredi_step}")

    st.markdown("""<hr style="margin:10px 0 6px 0;border-color:rgba(255,255,255,0.10);">""", unsafe_allow_html=True)




def _do_unlock():
    clear_dialog_states()
    st.session_state.controls_unlocked = True

def _do_lock():
    clear_dialog_states()
    st.session_state.controls_unlocked = False

def render_control_panel():
    is_batch = st.session_state.get("batch_mode", False)
    is_running = any_running()
    
    # Kredi kazanılma sürecindeyken bu panel görünmemeli (dialog içinde kendi kontrolleri var)
    if st.session_state.get("kredi_kazan_running", False) or st.session_state.get("kredi_cek_running", False):
        return
        
    # Batch modda single state'leri sıfırla
    if is_batch:
        for k in ("single_mode", "single_paused", "single_finish_requested"):
            if st.session_state.get(k): st.session_state[k] = False
            
    is_single_active = (not is_batch) and (is_running or st.session_state.get("single_mode", False) or st.session_state.get("single_paused", False) or st.session_state.get("single_finish_requested", False))
    if not is_batch and not is_single_active: return

    badge = '<span class="control-panel-badge-batch">Toplu İşlem</span>' if is_batch else '<span class="control-panel-badge-single">Tekli İşlem</span>'
    st.markdown(f'<hr style="margin:10px 0 6px 0;border-color:rgba(255,255,255,0.10);"><div class="control-panel-title">🎮 İşlem Kontrol Paneli {badge}</div>', unsafe_allow_html=True)

    controls_enabled = True
    if is_batch:
        controls_enabled = st.session_state.get("controls_unlocked", False)
        # Tek sabit key — sadece label ve callback değişir (key değişmez → layout kararlı)
        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
        _lock_label = "🔒 Kontrolleri Kilitle" if controls_enabled else "🔓 Kontrolleri Aç"
        _lock_cb    = _do_lock if controls_enabled else _do_unlock
        st.button(_lock_label, key="toggle_controls", use_container_width=True, on_click=_lock_cb)
        st.markdown("</div>", unsafe_allow_html=True)

    paused_key = "batch_paused" if is_batch else "single_paused"
    is_paused = st.session_state.get(paused_key, False)
        
    is_really_running = bg_is_running()

    # 3 kontrol butonu — her zaman render edilir (element sayısı sabit → göz kırpma yok)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        disabled_pause = (not controls_enabled) or is_paused or (not is_really_running and not is_batch)
        def _do_pause():
            clear_dialog_states()
            st.session_state[paused_key] = True
            if not is_batch:
                create_stop_flag(); st.session_state.single_mode = False; st.session_state["_paused_step"] = st.session_state.get("single_step")
                try: bg_terminate()
                except: pass
            else:
                create_pause_flag()
                log("[INFO] Toplu işlem duraklatıldı. İşlem uykuda bekleyecek veya mevcut adım bitince duracak.")
        st.button("⏸️ Durdur", key="ctrl_pause", use_container_width=True, disabled=disabled_pause, on_click=_do_pause)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        disabled_devam = (not controls_enabled) or (not is_paused) or (is_really_running and not is_batch)
        def _do_resume():
            clear_dialog_states()
            st.session_state[paused_key] = False
            if not is_batch:
                cleanup_flags(); st.session_state.bg_last_result = None
                st.session_state.single_step = st.session_state.pop("_paused_step", "pixverse")
                st.session_state.single_mode = True; st.session_state.single_finish_requested = False; st.session_state.status[st.session_state.single_step] = "running"
            else:
                remove_pause_flag()
                log("[INFO] Toplu işlem devam ettiriliyor...")
        st.button("▶️ Devam Ettir", key="ctrl_resume", use_container_width=True, disabled=disabled_devam, on_click=_do_resume)
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
        def _do_finish():
            clear_dialog_states()
            finish_key = "batch_finish_requested" if is_batch else "single_finish_requested"
            st.session_state[finish_key] = True
            create_stop_flag(); remove_pause_flag()
            try: bg_terminate()
            except: pass
        st.button("⏹️ Bitir", key="ctrl_finish", use_container_width=True, disabled=(not controls_enabled), on_click=_do_finish)
        st.markdown('</div>', unsafe_allow_html=True)

# --- STEP BUTTON & LOADER SAFE FIX ---
if "get_loader_html" not in globals():
    def get_loader_html(text="İşlem yapılıyor."):
        return f'<div class="loader-container"><div class="spinner"></div><div class="loader-text">{text}</div></div>'

if "render_step_button" not in globals():
    def render_step_button(key, label, btn_class_html, loading_text):
        placeholder = st.empty()
        st.session_state.ui_placeholders[key] = placeholder
        current_status = st.session_state.status.get(key, "idle")
        is_batch = st.session_state.get("batch_mode", False)
        running = any_running()

        if current_status == "running":
            placeholder.markdown(get_loader_html(loading_text), unsafe_allow_html=True)
            return False

        disabled = is_batch or running or current_status in ["ok"]
        effective_class = btn_class_html
        if current_status == "partial":
            effective_class = "btn-warning"

        with placeholder.container():
            st.markdown(f'<div class="{effective_class}">', unsafe_allow_html=True)
            display_label = label
            if current_status == "error":
                display_label = f"↺ {label} (Başarısız)"
            elif current_status == "partial":
                display_label = f"↺ {label} (Kısmi/Atlandı)"

            clicked = st.button(
                display_label,
                key=f"btn_{key}",
                use_container_width=True,
                disabled=disabled,
                on_click=clear_dialog_states
            )
            st.markdown('</div>', unsafe_allow_html=True)

        return clicked

left_col, middle_col, right_col = st.columns([1.0, 2.4, 1.4], gap="medium")
with left_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("### 🎮 İşlem Kontrolleri")
    # Ek İşlemler butonu: download çalışıyorsa yükleme göstergesi göster
    _ek_running_step = st.session_state.get("bg_node_key") if bg_is_running() else None
    _ek_islem_labels = {
        "youtube_link": "📺 YouTube linkleri hazırlanıyor...",
        "download": "⬇️ Video İndiriliyor...",
        "gorsel_analiz": "🖼️ Görsel Analiz Yapılıyor...",
        "gorsel_klonlama": "🎨 Görsel Klonlanıyor...",
        "gorsel_olustur": f"🖼️ {st.session_state.settings.get('gorsel_model', 'Nano Banana 2')} Görsel Oluşturuluyor...",
        "prompt_duzeltme": "✏️ Prompt Düzeltiliyor...",
        "video_montaj": "🎞️ Video Montaj Yapılıyor...",
        "toplu_video": "🎬 Toplu Video Montaj Yapılıyor...",
        "kredi_kazan": "🎰 Video Üretme Kredisi Kazanılıyor...",
        "kredi_cek": "📥 Krediler Çekiliyor...",
    }
    _is_paused_state = st.session_state.get("batch_paused", False) or st.session_state.get("single_paused", False)
    # Kredi işlemleri de aktif saymak: panel yanip sönmesin
    _is_kredi_running = st.session_state.get("kredi_kazan_running", False) or st.session_state.get("kredi_cek_running", False)
    _ek_aktif = (_ek_running_step in _ek_islem_labels and not _is_paused_state) or _is_kredi_running
    _ek_slot = st.empty()
    if _ek_aktif:
        if _is_kredi_running and _ek_running_step not in _ek_islem_labels:
            # Kredi işlemi çalışıyor ama bg_node_key farklı — doğru metni göster
            _kredi_loader_text = (
                "🎰 Video Üretme Kredisi Kazanılıyor..."
                if st.session_state.get("kredi_kazan_running", False)
                else "📥 Krediler Çekiliyor..."
            )
            _ek_slot.markdown(get_loader_html(_kredi_loader_text), unsafe_allow_html=True)
        else:
            _ek_slot.markdown(get_loader_html(_ek_islem_labels.get(_ek_running_step, "İşlem yapılıyor...")), unsafe_allow_html=True)
    else:
        with _ek_slot.container():
            st.markdown('<div class="btn-purple">', unsafe_allow_html=True)
            if st.button("📂 Ek İşlemler", key="btn_ek_islemler_open", use_container_width=True, disabled=is_ui_locked()):
                clear_dialog_states()
                st.session_state.last_dialog_align = "left"
                st.session_state.ek_dialog_open = "menu"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    if render_step_button("analyze", "📝 Prompt Oluştur", "btn-info", "Prompt Oluşturuluyor..."):
        st.session_state.single_paused = False; st.session_state.single_finish_requested = False; st.session_state.single_mode = True
        st.session_state.bg_last_result = None; st.session_state.single_step = "analyze"
        cleanup_flags(); st.session_state.status["analyze"] = "running"; st.rerun()

    if render_step_button("pixverse", get_video_generation_label(), "btn-warning", get_video_generation_loading_text()):
        st.session_state.single_paused = False; st.session_state.single_finish_requested = False; st.session_state.single_mode = True
        st.session_state.bg_last_result = None; st.session_state.single_step = "pixverse"
        cleanup_flags(); st.session_state.status["pixverse"] = "running"; st.rerun()

    st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
    if st.button("⚡ Tümünü Çalıştır", key="run_all", use_container_width=True, disabled=st.session_state.get("batch_mode", False) or any_running() or st.session_state.get("single_mode", False), on_click=clear_dialog_states):
        # Seçimlere göre sıralı kuyruk oluştur
        secs = st.session_state.ek_batch_secimler
        queue = []
        aktif_prompt_kaynagi = _get_prompt_runtime_source_mode()
        gorsel_motion_prompt_aktif = secs.get("gorsel_olustur", False) and _should_use_gorsel_motion_prompts()
        if secs.get("video_indir", True) and not gorsel_motion_prompt_aktif and aktif_prompt_kaynagi == PROMPT_SOURCE_LINK and _count_prompt_links() > 0:    queue.append("download")
        if secs.get("gorsel_analiz", False): queue.append("gorsel_analiz")
        if secs.get("gorsel_klonla", False): queue.append("gorsel_klonlama")
        skip_analyze = gorsel_motion_prompt_aktif
        if not skip_analyze:
            queue.append("analyze")                                              # Prompt oluştur
            if secs.get("prompt_duzeltme", False): queue.append("prompt_duzeltme")  # Sonra düzelt
            
        if secs.get("gorsel_olustur", False): queue.append("gorsel_olustur")
            
        queue.append("pixverse")             # Video üret
        if secs.get("video_montaj", False): queue.append("video_montaj")  # Sonra montaj
        if secs.get("toplu_video", False): queue.append("toplu_video")    # Sonra toplu montaj
        if secs.get("sosyal_medya", False): queue.append("sosyal_medya")  # Son adım sosyal medya paylaşımı
        st.session_state.batch_queue = queue
        st.session_state.batch_queue_idx = 0
        st.session_state.batch_mode = True; st.session_state.controls_unlocked = False
        st.session_state.batch_paused = False; st.session_state.batch_finish_requested = False
        st.session_state.batch_resume_queue = []; st.session_state.batch_resume_idx = 0
        st.session_state.batch_pixverse_retry_targets = []
        # Önceki tekli işlem state'lerini temizle (çift kontrol görünümünü engelle)
        st.session_state.single_mode = False; st.session_state.single_paused = False
        st.session_state.single_finish_requested = False; st.session_state.single_step = None
        if "_paused_step" in st.session_state: del st.session_state["_paused_step"]
        st.session_state.ek_dialog_open = None  # Açık dialog varsa kapat
        durum_ozeti_sifirla()  # Yeni toplu işlem başlatılırken özeti sıfırla
        st.session_state.durum_ozeti_suppress = True
        cleanup_flags(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── KALDIĞI YERDEN DEVAM ET butonu ──
    _resume_q = st.session_state.get("batch_resume_queue", [])
    _resume_i = st.session_state.get("batch_resume_idx", 0)
    _can_resume = (
        bool(_resume_q)
        and _resume_i < len(_resume_q)
        and not st.session_state.get("batch_mode", False)
        and not any_running()
        and not st.session_state.get("single_mode", False)
    )
    if _can_resume:
        _STEP_LABELS = {
            "download": "⬇️ Video İndir", "gorsel_analiz": "🖼️ Görsel Analiz",
            "gorsel_klonlama": "🎨 Görsel Klonla", "analyze": "📝 Prompt Oluştur",
            "prompt_duzeltme": "✏️ Prompt Düzelt", "pixverse": get_video_generation_label(),
            "video_montaj": "🎞️ Video Montaj", "toplu_video": "🎬 Toplu Video", "sosyal_medya": "🌐 Sosyal Medya Paylaşım",
        }
        _resume_step_label = _STEP_LABELS.get(_resume_q[_resume_i], "?")
        _resume_reason_text = st.session_state.get("batch_resume_reason", "")
        _resume_info_line = (
            f'<br><span style="color:#f87171;font-size:10.5px;">{_resume_reason_text}</span>'
            if _resume_reason_text else ""
        )
        st.markdown(
            f'<div style="background:rgba(234,179,8,0.08);border:1px solid rgba(234,179,8,0.35);'
            f'border-radius:10px;padding:9px 13px;margin-top:10px;margin-bottom:4px;'
            f'font-size:11px;color:#fbbf24;">'
            f'⚠️ Önceki işlem yarım kaldı. Devam adımı: <b>{_resume_step_label}</b>'
            f'{_resume_info_line}'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
        if st.button("▶️ Kaldığı Yerden Devam Et", key="run_resume", use_container_width=True, on_click=clear_dialog_states):
            st.session_state.batch_queue = list(_resume_q)
            st.session_state.batch_queue_idx = _resume_i
            st.session_state.batch_mode = True; st.session_state.controls_unlocked = False
            st.session_state.batch_paused = False; st.session_state.batch_finish_requested = False
            st.session_state.single_mode = False; st.session_state.single_paused = False
            st.session_state.single_finish_requested = False; st.session_state.single_step = None
            if "_paused_step" in st.session_state: del st.session_state["_paused_step"]
            st.session_state.ek_dialog_open = None
            st.session_state.durum_ozeti_dialog_open = False
            st.session_state.last_dialog_align = "center"
            # Resume bilgisi eski UI'yı tekrar tetiklemesin; gerekirse hata olduğunda yeniden yazılacak
            st.session_state.batch_resume_queue = []
            st.session_state.batch_resume_idx = 0
            st.session_state.batch_resume_reason = ""
            # Devam adımı ve sonrakilerinin statüsünü sıfırla (temiz başlangıç)
            for _rk in _resume_q[_resume_i:]:
                st.session_state.status[_rk] = "idle"
            durum_ozeti_sifirla()  # Önceki özeti temizle — yeni çalışma başlıyor
            st.session_state.durum_ozeti_suppress = True
            cleanup_flags(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    render_control_panel()

    # ── DURUM ÖZETİ PANELİ ──
    _durum_ozeti_slot = st.empty()
    ozet = st.session_state.durum_ozeti
    _hatali_sayi = len(ozet.get("hatali", []))
    _kismi_sayi = len(ozet.get("kismi", []))
    _basarili_sayi = len(ozet.get("basarili", []))
    _toplam = _hatali_sayi + _kismi_sayi + _basarili_sayi
    _is_running = (
        any_running()
        or st.session_state.get('batch_mode', False)
        or st.session_state.get('single_mode', False)
        or st.session_state.get('batch_paused', False)
        or st.session_state.get('single_paused', False)
        or bg_is_running()
        or st.session_state.get('durum_ozeti_suppress', False)
    )
    _show_durum_ozeti = (_toplam > 0 and not _is_running)

    if _show_durum_ozeti:
        # Sayac bilgisi
        _sayac_html = ''
        if _hatali_sayi > 0:
            _sayac_html += (f'<div style="display:flex;align-items:center;gap:5px;">'
               f'<div style="width:8px;height:8px;border-radius:50%;background:#ef4444;"></div>'
               f'<span style="font-size:10px;font-weight:500;color:#94a3b8;">Hatalı: <span style="color:#ffffff;font-weight:700;">{_hatali_sayi}</span></span>'
               f'</div>')
        if _kismi_sayi > 0:
            _sayac_html += (f'<div style="display:flex;align-items:center;gap:5px;">'
               f'<div style="width:8px;height:8px;border-radius:50%;background:#f59e0b;"></div>'
               f'<span style="font-size:10px;font-weight:500;color:#94a3b8;">Kısmi: <span style="color:#ffffff;font-weight:700;">{_kismi_sayi}</span></span>'
               f'</div>')
        _sayac_html += (f'<div style="display:flex;align-items:center;gap:5px;">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:#22c55e;"></div>'
            f'<span style="font-size:10px;font-weight:500;color:#94a3b8;">Başarılı: <span style="color:#ffffff;font-weight:700;">{_basarili_sayi}</span></span>'
            f'</div>')

        def _open_durum_ozeti():
            clear_dialog_states()
            st.session_state.last_dialog_align = "center"
            st.session_state.durum_ozeti_dialog_open = True

        with _durum_ozeti_slot.container():
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.10);'
                f'border-left:3px solid #3b82f6;border-radius:12px;padding:14px 16px;margin-top:12px;">'
                f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">'
                f'<span style="font-size:13px;">📊</span>'
                f'<span style="font-size:11px;font-weight:800;color:rgba(233,236,245,0.75);text-transform:uppercase;letter-spacing:1.5px;">Durum Özeti</span>'
                f'</div>'
                f'<div style="display:flex;align-items:center;gap:16px;">'
                f'{_sayac_html}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button("📊 Durum Özeti", key="btn_durum_ozeti_ac", use_container_width=True, on_click=_open_durum_ozeti):
                st.rerun()
    else:
        _durum_ozeti_slot.empty()

st.markdown("</div>", unsafe_allow_html=True)


with middle_col:
    st.markdown('<div class="card workflow-canvas-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Workflow Canvas")

    stt = st.session_state.status.copy()
    if st.session_state.get("batch_paused", False) or st.session_state.get("single_paused", False):
        stt = {k: ("paused" if v == "running" else v) for k, v in stt.items()}

    secs  = st.session_state.get("ek_batch_secimler", {})
    # Checkbox seçili olmasa bile işlem aktif çalışıyorsa gerçek durumu göster
    _ACTIVE_STS = ("running", "ok", "error", "partial", "paused")
    ga_st = stt["gorsel_analiz"]   if (secs.get("gorsel_analiz")   or stt["gorsel_analiz"]   in _ACTIVE_STS) else "idle"
    gk_st = stt["gorsel_klonlama"] if (secs.get("gorsel_klonla")   or stt["gorsel_klonlama"] in _ACTIVE_STS) else "idle"
    pd_st = stt["prompt_duzeltme"] if (secs.get("prompt_duzeltme") or stt["prompt_duzeltme"] in _ACTIVE_STS) else "idle"

    def _shared_montaj_canvas_state():
        vm_selected = bool(secs.get("video_montaj"))
        tv_selected = bool(secs.get("toplu_video"))
        vm_status = stt.get("video_montaj", "idle")
        tv_status = stt.get("toplu_video", "idle")

        if tv_status == "running":
            return "toplu_video", "running"
        if vm_status == "running":
            return "video_montaj", "running"
        if tv_status == "paused":
            return "toplu_video", "paused"
        if vm_status == "paused":
            return "video_montaj", "paused"
        if tv_status in _ACTIVE_STS and tv_status != "idle":
            return "toplu_video", tv_status
        if vm_status in _ACTIVE_STS and vm_status != "idle":
            return "video_montaj", vm_status
        if tv_selected and not vm_selected:
            return "toplu_video", "idle"
        return "video_montaj", (vm_status if (vm_selected or vm_status in _ACTIVE_STS) else "idle")

    montaj_canvas_mode, vm_st = _shared_montaj_canvas_state()

    _STATUS = {
        "idle":    {"dot":"#475569","ibg":"rgba(71,85,105,0.20)","badge":"rgba(71,85,105,0.20)","lbl":"Bekliyor"},
        "running": {"dot":"#38bdf8","ibg":"rgba(56,189,248,0.18)","badge":"rgba(56,189,248,0.18)","lbl":"Calisıyor..."},
        "ok":      {"dot":"#4ade80","ibg":"rgba(34,197,94,0.18)","badge":"rgba(34,197,94,0.18)","lbl":"Tamamlandı"},
        "error":   {"dot":"#f87171","ibg":"rgba(239,68,68,0.18)","badge":"rgba(239,68,68,0.18)","lbl":"Basarısız"},
        "partial": {"dot":"#fb923c","ibg":"rgba(249,115,22,0.18)","badge":"rgba(249,115,22,0.18)","lbl":"Kısmi"},
        "paused":  {"dot":"#fbbf24","ibg":"rgba(234,179,8,0.18)","badge":"rgba(234,179,8,0.18)","lbl":"Duraklatıldı"},
    }
    
    go_st = stt.get("gorsel_olustur", "idle")
    if secs.get("gorsel_olustur") or go_st in _ACTIVE_STS:
        go_st = go_st
    else:
        go_st = "idle"
        
    _TOP = {"input":"#22c55e","download":"#3b82f6","gorsel_analiz":"#eab308",
            "gorsel_klonlama":"#a855f7","analyze":"#6366f1","prompt_duzeltme":"#ef4444","gorsel_olustur":"rainbow","pixverse":"#f1f5f9","video_montaj":"#00FFFF","sosyal_medya":"#FF007F"}
    _EMJ = {"input":"📎","download":"⬇️","gorsel_analiz":"🖼️","gorsel_klonlama":"🎨",
            "analyze":"📝","prompt_duzeltme":"✏️","gorsel_olustur":"🖼️","pixverse":"🎬","video_montaj":"🎞️","sosyal_medya":"🌐"}
    _TTL = {"input":"Kaynak","download":"Video Indir","gorsel_analiz":"Gorsel Analiz",
            "gorsel_klonlama":"Gorsel Klonla","analyze":"Prompt Olustur","prompt_duzeltme":"Prompt Duzelt","gorsel_olustur":"Gorsel Olustur","pixverse":get_video_generation_title().replace("Ü", "U").replace("ü", "u").replace("Ş", "S").replace("ş", "s").replace("İ", "I").replace("ı", "i").replace("Ö", "O").replace("ö", "o").replace("Ç", "C").replace("ç", "c"),"video_montaj":"Video Montaj","sosyal_medya":"Sosyal Medya Paylasim"}
    _TTL2= {"input":"Kaynak","download":"Video İndir","gorsel_analiz":"Görsel Analiz",
            "gorsel_klonlama":"Görsel Klonla","analyze":"Prompt Oluştur","prompt_duzeltme":"Prompt Düzelt","gorsel_olustur":f"{st.session_state.settings.get('gorsel_model', 'Nano Banana 2')} Görsel Oluştur","pixverse":get_video_generation_title(),"video_montaj":"Video Montaj","sosyal_medya":"Sosyal Medya Paylaşım"}
    _SUB = {"input":get_link_canvas_subtitle(stt),"download":"Sunucuya indir","gorsel_analiz":"Görselleri analiz et",
            "gorsel_klonlama":"Görseli klonla","analyze":"Prompt & Analiz","prompt_duzeltme":"Promptu düzelt","gorsel_olustur":"Görsel ve Hareketlendirme üret","pixverse":get_video_generation_canvas_subtitle(),"video_montaj":"Videoları birleştir","sosyal_medya":"Paylaşımı planla ve yayınla"}
    _STS = {"input":get_link_canvas_status(stt),"download":stt["download"],"gorsel_analiz":ga_st,
            "gorsel_klonlama":gk_st,"analyze":stt["analyze"],"prompt_duzeltme":pd_st,"gorsel_olustur":go_st,"pixverse":stt["pixverse"],"video_montaj":vm_st,
            "sosyal_medya":(stt["sosyal_medya"] if (secs.get("sosyal_medya") or stt["sosyal_medya"] in _ACTIVE_STS) else "idle")}

    if montaj_canvas_mode == "toplu_video":
        _EMJ["video_montaj"] = "🎬"
        _TTL["video_montaj"] = "Toplu Video Montaj"
        _TTL2["video_montaj"] = "Toplu Video Montaj"
        _SUB["video_montaj"] = "Toplu varyasyon montajı oluştur"

    _DIS = {
        "gorsel_analiz":  not secs.get("gorsel_analiz")  and stt["gorsel_analiz"]   not in _ACTIVE_STS,
        "gorsel_klonlama":not secs.get("gorsel_klonla")  and stt["gorsel_klonlama"] not in _ACTIVE_STS,
        "prompt_duzeltme":not secs.get("prompt_duzeltme")and stt["prompt_duzeltme"] not in _ACTIVE_STS,
        "gorsel_olustur": not secs.get("gorsel_olustur") and go_st not in _ACTIVE_STS,
        "video_montaj":   not (secs.get("video_montaj") or secs.get("toplu_video")) and stt["video_montaj"] not in _ACTIVE_STS and stt["toplu_video"] not in _ACTIVE_STS,
        "toplu_video":    not secs.get("toplu_video")    and stt["toplu_video"]     not in _ACTIVE_STS,
        "sosyal_medya":   not secs.get("sosyal_medya")   and stt["sosyal_medya"]    not in _ACTIVE_STS,
    }

    # --- Dosya doluluğu kontrolü ---
    def _txt_dolu(path):
        """TXT dosyasında en az 1 satırlık içerik var mı?"""
        try:
            if not path or not os.path.exists(path): return False
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return any(line.strip() for line in f)
        except Exception: return False

    def _klasor_dolu(path):
        """Klasörde en az 1 dosya var mı?"""
        try:
            if not path or not os.path.exists(path): return False
            return any(os.path.isfile(os.path.join(path, f)) for f in os.listdir(path))
        except Exception: return False

    cfg = st.session_state.settings
    prompt_canvas_mode = _get_effective_prompt_source_mode()
    if prompt_canvas_mode == PROMPT_SOURCE_ADDED_VIDEO:
        analyze_ready = _klasor_dolu(cfg.get("added_video_dir", ""))
    elif prompt_canvas_mode == PROMPT_SOURCE_LINK:
        # Link kaydedildi diye Prompt Oluştur kartı otomatik aktif/parlak görünmesin.
        # İşlem yine çalışır; bu sadece Workflow Canvas görünürlüğünü düzeltir.
        analyze_ready = False
    else:
        analyze_ready = _klasor_dolu(cfg.get("download_dir", "")) or _klasor_dolu(cfg.get("added_video_dir", ""))
    _READY = {
        "input":          _txt_dolu(cfg.get("links_file", "")) or _klasor_dolu(cfg.get("added_video_dir", "")),
        "download":       _txt_dolu(cfg.get("links_file", "")),
        "gorsel_analiz":  _klasor_dolu(cfg.get("gorsel_analiz_dir", "")),
        "gorsel_klonlama":_klasor_dolu(cfg.get("gorsel_analiz_dir", "")),
        "analyze":        analyze_ready,
        "prompt_duzeltme":_klasor_dolu(cfg.get("prompt_dir", "")) and _txt_dolu(cfg.get("prompt_duzeltme_txt", "")),
        "gorsel_olustur": _klasor_dolu(cfg.get("prompt_dir", "")) or _txt_dolu(cfg.get("video_prompt_links_file", "")),
        "pixverse":       _klasor_dolu(cfg.get("prompt_dir", "")) or _txt_dolu(cfg.get("video_prompt_links_file", "")),
        "video_montaj":   _klasor_dolu(cfg.get("video_output_dir", "")) or _klasor_dolu(cfg.get("klon_video_dir", "")),
        "toplu_video":    _klasor_dolu(cfg.get("video_output_dir", "")) or _klasor_dolu(cfg.get("klon_video_dir", "")),
        "sosyal_medya":   _klasor_dolu(cfg.get("video_montaj_output_dir", "")) or _klasor_dolu(cfg.get("toplu_video_output_dir", "")) or _klasor_dolu(cfg.get("video_output_dir", "")),
    }

    def _nd(nid):
        s = _STS[nid]; sc = _STATUS.get(s, _STATUS["idle"])
        dis = _DIS.get(nid, False); 
        ready = _READY.get(nid, False)
        # Pasif: ya seçili değil ya da dosyası boş (ve henüz çalışmamış)
        # input ve download için: status idle ise her zaman pasif göster (sıfırlama sonrası)
        force_dim = nid in ("input", "download") and s == "idle"
        not_ready_dim = (not ready and s in ("idle",)) or force_dim
        op = "0.28" if dis else ("0.45" if not_ready_dim else "1")
        top = _TOP[nid]; running = (s == "running")
        top_strip = ""
        if top == "rainbow":
            top_strip = '<div style="position:absolute; top:-1px; left:0; width:100%; height:3px; background:linear-gradient(to right, red, orange, yellow, #4ade80, #38bdf8, #a855f7); border-radius:14px 14px 0 0;"></div>'
            border_css = "border-top:0px;"
        else:
            border_css = f"border-top:2.5px solid {top};"

        p1 = "animation:wfpulse 1.8s ease-in-out infinite;" if running else ""
        p2 = "animation:dotpulse 1.2s ease-in-out infinite;" if running else ""
        # Köşe durum noktası: işlem durumuna göre renk
        _DOT_CLR = {
            "idle":    ("#334155", "none"),
            "running": ("#38bdf8", "0 0 7px rgba(56,189,248,0.7)"),
            "ok":      ("#4ade80", "0 0 7px rgba(74,222,128,0.7)"),
            "error":   ("#f87171", "0 0 7px rgba(248,113,113,0.7)"),
            "partial": ("#fb923c", "0 0 7px rgba(251,146,60,0.7)"),
            "paused":  ("#fbbf24", "0 0 7px rgba(251,191,36,0.7)"),
        }
        dot_c, dot_shadow = _DOT_CLR.get(s, _DOT_CLR["idle"])
        dot_anim = "animation:dotpulse 1.2s ease-in-out infinite;" if s == "running" else ""
        ready_dot = (
            f'<div style="position:absolute;top:10px;right:10px;width:9px;height:9px;border-radius:50%;'
            f'background:{dot_c};box-shadow:{dot_shadow};{dot_anim}"></div>'
        )
        r  = (
            f'<div style="position:relative;background:rgba(15,23,42,0.82);border:1px solid rgba(255,255,255,0.08);' +
            f'{border_css}border-radius:14px;padding:14px 13px 12px;overflow:hidden;' +
            f'opacity:{op};box-shadow:0 4px 18px rgba(0,0,0,0.4);min-height:96px;{p1}">' +
            top_strip +
            ready_dot +
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:5px;">' +
            f'<div style="width:36px;height:36px;border-radius:9px;background:{sc["ibg"]};' +
            f'display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0;">{_EMJ[nid]}</div>' +
            f'<span style="font-size:13.5px;font-weight:700;color:#f1f5f9;">{_TTL2[nid]}</span></div>' +
            f'<div style="font-size:10.5px;color:#64748b;font-family:monospace;margin:3px 0 7px 46px;">{_SUB[nid]}</div>' +
            f'<div style="display:inline-flex;align-items:center;gap:5px;background:{sc["badge"]};' +
            f'border-radius:20px;padding:3px 9px;margin-left:46px;">' +
            f'<div style="width:6px;height:6px;border-radius:50%;background:{sc["dot"]};{p2}"></div>' +
            f'<span style="font-size:10px;font-weight:600;color:{sc["dot"]};">{sc["lbl"]}</span>' +
            f'</div></div>'
        )
        return r

    def _diarr(color, active=True, visible=True, direction="right-to-left"):
        """Çapraz ok yardımcı çizimi."""
        if not visible:
            return f'<div style="height:42px;"></div>'
        defs = ""
        if color == "rainbow":
            defs = '<defs><linearGradient id="rbw"><stop offset="0%" stop-color="red"/><stop offset="50%" stop-color="green"/><stop offset="100%" stop-color="blue"/></linearGradient></defs>'
            c = "url(#rbw)" if active else "#2d3748"
        else:
            c = color if active else "#2d3748"
        ds = "stroke-dasharray:8,6;animation:dash-flow 8s linear infinite;" if active else "stroke-dasharray:5,5;opacity:0.25;"
        x1, x2 = ("56%", "44%") if direction == "right-to-left" else ("44%", "56%")
        return (
            f'<div style="width:100%;height:42px;overflow:visible;">'
            f'<svg width="100%" height="42" style="overflow:visible;display:block">{defs}'
            f'<line x1="{x1}" y1="0" x2="{x2}" y2="42" stroke="{c}" stroke-width="2.5" stroke-linecap="round" '
            f'style="{ds}"/></svg></div>'
        )

    def _harr(color, active=True, visible=True, direction="left-to-right"):
        if not visible:
            return f'<div style="min-height:82px;"></div>'
        if color == "rainbow":
            # CSS mask ile kesik cizgi - SVG gradient stroke horizontal cizgide calismiyor
            rbw_grad = "linear-gradient(to right, #ff0000, #ff8800, #ffff00, #4ade80, #38bdf8, #a855f7)"
            if active:
                mask = "repeating-linear-gradient(to right, black 0px, black 10px, transparent 10px, transparent 18px)"
                anim = "animation:dash-mask-h 0.8s linear infinite;"
                op = "1"
            else:
                mask = "repeating-linear-gradient(to right, black 0px, black 6px, transparent 6px, transparent 12px)"
                anim = ""
                op = "0.25"
            return (
                f'<div style="display:flex;align-items:center;justify-content:center;min-height:82px;padding:0 6px;">'
                f'<div style="width:100%;height:3px;background:{rbw_grad};opacity:{op};border-radius:2px;'
                f"-webkit-mask-image:{mask};mask-image:{mask};{anim}\"></div></div>"
            )
        c = color if active else "#2d3748"
        ds = "stroke-dasharray:8,6;animation:dash-flow 8s linear infinite;" if active else "stroke-dasharray:5,5;opacity:0.25;"
        x1, x2 = ("0", "100%") if direction == "left-to-right" else ("100%", "0")
        return (
            f'<div style="display:flex;align-items:center;justify-content:center;min-height:82px;padding:0 6px;">' +
            f'<svg width="100%" height="14" style="overflow:visible;display:block">' +
            f'<line x1="{x1}" y1="7" x2="{x2}" y2="7" stroke="{c}" stroke-width="2.5" stroke-linecap="round" ' +
            f'style="{ds}"/></svg></div>'
        )

    def _varr(color, active=True, visible=True):
        if not visible:
            return f'<div style="height:34px;"></div>'
        if color == "rainbow":
            # CSS mask ile dikey kesik cizgi
            rbw_grad = "linear-gradient(to bottom, #ff0000, #ff8800, #ffff00, #4ade80, #38bdf8, #a855f7)"
            if active:
                mask = "repeating-linear-gradient(to bottom, black 0px, black 10px, transparent 10px, transparent 18px)"
                anim = "animation:dash-mask-v 0.8s linear infinite;"
                op = "1"
            else:
                mask = "repeating-linear-gradient(to bottom, black 0px, black 6px, transparent 6px, transparent 12px)"
                anim = ""
                op = "0.25"
            return (
                f'<div style="display:flex;justify-content:center;">'
                f'<div style="width:3px;height:34px;background:{rbw_grad};opacity:{op};border-radius:2px;'
                f"-webkit-mask-image:{mask};mask-image:{mask};{anim}\"></div></div>"
            )
        c = color if active else "#2d3748"
        ds = "stroke-dasharray:6,5;animation:dash-flow 8s linear infinite;" if active else "stroke-dasharray:5,5;opacity:0.25;"
        return (
            f'<div style="display:flex;justify-content:center;">' +
            f'<svg width="20" height="34" viewBox="0 0 20 34" xmlns="http://www.w3.org/2000/svg" style="overflow:visible">' +
            f'<line x1="10" y1="2" x2="10" y2="32" stroke="{c}" stroke-width="2.5" stroke-linecap="round" ' +
            f'style="{ds}"/></svg></div>'
        )

    def _diag_to_center_arr(color, active=True, visible=True, source="left"):
        if not visible:
            return f'<div style="height:42px;"></div>'
        c = color if active else "#2d3748"
        ds = "stroke-dasharray:8,6;animation:dash-flow 8s linear infinite;" if active else "stroke-dasharray:5,5;opacity:0.25;"
        x1 = "22%" if source == "left" else "78%"
        return (
            f'<div style="width:100%;height:42px;overflow:visible;">'
            f'<svg width="100%" height="42" style="overflow:visible;display:block">'
            f'<line x1="{x1}" y1="0" x2="50%" y2="42" stroke="{c}" stroke-width="2.5" stroke-linecap="round" '
            f'style="{ds}"/></svg></div>'
        )

    # Batch modunda hangi adımın aktif olduğunu belirle
    batch_on  = st.session_state.get("batch_mode", False)
    batch_q   = st.session_state.get("batch_queue", [])
    batch_idx = st.session_state.get("batch_queue_idx", 0)

    # Şu an çalışan adım (running durumundaki node)
    running_step = next((k for k, v in _STS.items() if v == "running"), None)
    # Bir önceki tamamlanan adım (ok durumundaki en son node)
    done_steps = [k for k, v in _STS.items() if v in ("ok", "partial")]

    def _edge_active(from_node, to_node):
        """Kenar aktif: from tamamlandı VE to çalışıyor ya da tamamlandı."""
        if not batch_on:
            return False
        from_done = _STS.get(from_node) in ("ok", "partial")
        to_started = _STS.get(to_node) in ("running", "ok", "partial")
        return from_done and to_started

    def _edge_visible(from_node, to_node):
        """Bu kenar görünür mü? Sadece batch modunda ilgili sırada görünür."""
        if not batch_on:
            return False
        # Her iki node da batch kuyruğunda olmalı veya her ikisi de sabit adımlar
        q_set = set(batch_q)
        fn_in = from_node in q_set or from_node == "input"
        tn_in = to_node in q_set or to_node == "input"
        return fn_in and tn_in

    st.markdown(
        "<style>"
        "@keyframes wfpulse{0%,100%{box-shadow:0 4px 18px rgba(0,0,0,0.4)}50%{box-shadow:0 0 0 5px rgba(56,189,248,0.1),0 4px 18px rgba(0,0,0,0.4)}}"
        "@keyframes dotpulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.25;transform:scale(0.4)}}"
        "@keyframes dash-flow{from{stroke-dashoffset:300}to{stroke-dashoffset:0}}"
        "@keyframes dash-mask-h{from{-webkit-mask-position-x:-28px;mask-position-x:-28px}to{-webkit-mask-position-x:0px;mask-position-x:0px}}"
        "@keyframes dash-mask-v{from{-webkit-mask-position-y:-28px;mask-position-y:-28px}to{-webkit-mask-position-y:0px;mask-position-y:0px}}"
        ".wf-spacer{margin-top:10px;margin-bottom:10px;}"
        "</style>",
        unsafe_allow_html=True
    )

    # Kenar görünürlük ve aktiflik hesapla
    # input → download (yatay)
    e_h1_vis = _edge_visible("input", "download")
    e_h1_act = _edge_active("input", "download")
    # download → gorsel_analiz (çapraz, Görsel Analiz aktifse)
    e_v1_vis = batch_on and "download" in batch_q and "gorsel_analiz" in batch_q
    e_v1_act = _edge_active("download", "gorsel_analiz")
    # download → gorsel_klonlama (düz aşağı sağ kolonda, sadece Görsel Klonla aktifse Görsel Analiz yoksa)
    e_v1b_vis = batch_on and "download" in batch_q and "gorsel_klonlama" in batch_q and "gorsel_analiz" not in batch_q
    e_v1b_act = _edge_active("download", "gorsel_klonlama")
    # gorsel_analiz → gorsel_klonlama (yatay)
    e_h2_vis = _edge_visible("gorsel_analiz", "gorsel_klonlama")
    e_h2_act = _edge_active("gorsel_analiz", "gorsel_klonlama")
    # gorsel_analiz → analyze (düz aşağı sol kolonda, Görsel Analiz aktifse)
    e_v2_vis = batch_on and "gorsel_analiz" in batch_q and "analyze" in batch_q
    e_v2_act = _edge_active("gorsel_analiz", "analyze")
    # gorsel_klonlama → analyze (çapraz, sadece Görsel Klonla aktifse Görsel Analiz yoksa)
    e_v2b_vis = batch_on and "gorsel_klonlama" in batch_q and "analyze" in batch_q
    e_v2b_act = _edge_active("gorsel_klonlama", "analyze")
    
    # analyze → prompt_duzeltme (yatay)
    e_h3_vis = _edge_visible("analyze", "prompt_duzeltme")
    e_h3_act = _edge_active("analyze", "prompt_duzeltme")
    
    # Row 3 to Row 4 Connections
    has_go = "gorsel_olustur" in batch_q
    has_pd = "prompt_duzeltme" in batch_q
    
    # Right to Left diag: Prompt Düzeltme (R) -> Görsel Oluştur (L)
    e_v3_rl_vis = batch_on and has_pd and has_go
    e_v3_rl_act = _edge_active("prompt_duzeltme", "gorsel_olustur")
    
    # Left to R diag: Analyze (L) -> Pixverse (R)
    e_v3_lr_vis = batch_on and not has_pd and not has_go and ("pixverse" in batch_q)
    e_v3_lr_act = _edge_active("analyze", "pixverse")
    
    # Left vertical: Analyze (L) -> Görsel Oluştur (L)
    e_v3_lv_vis = batch_on and not has_pd and has_go
    e_v3_lv_act = _edge_active("analyze", "gorsel_olustur")
    
    # Right vertical: Prompt Düzeltme (R) -> Pixverse (R)
    e_v3_rv_vis = batch_on and has_pd and not has_go and ("pixverse" in batch_q)
    e_v3_rv_act = _edge_active("prompt_duzeltme", "pixverse")

    # Row 4 to Row 5 Connections — tanımlar önce gelsin (e_h4_vis'te kullanılıyor)
    e_h4_targets = [n for n in ("video_montaj", "toplu_video") if n in batch_q]
    has_vm = bool(e_h4_targets)
    has_pv = "pixverse" in batch_q
    has_sm = "sosyal_medya" in batch_q

    # Row 4 (gorsel_olustur -> pixverse)
    # gorsel_olustur seciliyse pixverse her zaman hemen ardindan calisir,
    # bu yuzden sadece gorsel_olustur ve pixverse kuyrukta olsa yeter
    e_h4_vis = batch_on and has_go and has_pv
    e_h4_act = _edge_active("gorsel_olustur", "pixverse")

    # Right vertical: Pixverse (R) -> Montaj (R)
    e_v4_rv_vis = batch_on and has_pv and has_vm
    e_v4_rv_act = _edge_active("pixverse", "video_montaj") or _edge_active("pixverse", "toplu_video")
    
    # Right to Left diag: Video Montaj (R) -> Sosyal Medya (L)
    e_v4_rl_vis = batch_on and has_vm and has_sm
    e_v4_rl_act = _edge_active("video_montaj", "sosyal_medya") or _edge_active("toplu_video", "sosyal_medya")

    # Right to Left diag: Pixverse (R) -> Sosyal Medya (L) (if no montaj)
    e_v4_rl_pv_vis = batch_on and has_pv and not has_vm and has_sm
    e_v4_rl_pv_act = _edge_active("pixverse", "sosyal_medya")

    # Left vertical: Görsel Oluştur (L) -> Sosyal Medya (L) (if no pixverse and no montaj)
    e_v4_lv_vis = batch_on and has_go and not has_pv and not has_vm and has_sm
    e_v4_lv_act = _edge_active("gorsel_olustur", "sosyal_medya")

    # --- Render Row 1 ---
    c1, ca, c2 = st.columns([1, 0.28, 1])
    with c1: st.markdown(_nd("input"), unsafe_allow_html=True)
    with ca: st.markdown(_harr("#22c55e", e_h1_act, e_h1_vis), unsafe_allow_html=True)
    with c2: st.markdown(_nd("download"), unsafe_allow_html=True)

    # --- Arrows Row 1 to 2 ---
    if e_v1b_vis:
        _, _, _rv1 = st.columns([1, 0.28, 1])
        with _rv1: st.markdown(_varr("#3b82f6", e_v1b_act, e_v1b_vis), unsafe_allow_html=True)
    else:
        st.markdown(_diarr("#3b82f6", e_v1_act, e_v1_vis), unsafe_allow_html=True)

    # --- Render Row 2 ---
    c1, ca, c2 = st.columns([1, 0.28, 1])
    with c1: st.markdown(_nd("gorsel_analiz"), unsafe_allow_html=True)
    with ca: st.markdown(_harr("#eab308", e_h2_act, e_h2_vis), unsafe_allow_html=True)
    with c2: st.markdown(_nd("gorsel_klonlama"), unsafe_allow_html=True)

    # --- Arrows Row 2 to 3 ---
    if e_v2b_vis:
        st.markdown(_diarr("#a855f7", e_v2b_act, e_v2b_vis), unsafe_allow_html=True)
    else:
        lv, _, _ = st.columns([1, 0.28, 1])
        with lv: st.markdown(_varr("#a855f7", e_v2_act, e_v2_vis), unsafe_allow_html=True)

    # --- Render Row 3 ---
    c1, ca, c2 = st.columns([1, 0.28, 1])
    with c1: st.markdown(_nd("analyze"), unsafe_allow_html=True)
    with ca: st.markdown(_harr("#6366f1", e_h3_act, e_h3_vis), unsafe_allow_html=True)
    with c2: st.markdown(_nd("prompt_duzeltme"), unsafe_allow_html=True)

    # --- Arrows Row 3 to 4 ---
    if e_v3_rl_vis:
        st.markdown(_diarr("#ef4444", e_v3_rl_act, e_v3_rl_vis, direction="right-to-left"), unsafe_allow_html=True)
    elif e_v3_lr_vis:
        st.markdown(_diarr("#6366f1", e_v3_lr_act, e_v3_lr_vis, direction="left-to-right"), unsafe_allow_html=True)
    elif e_v3_rv_vis:
        _, _, rv3 = st.columns([1, 0.28, 1])
        with rv3: st.markdown(_varr("#ef4444", e_v3_rv_act, e_v3_rv_vis), unsafe_allow_html=True)
    else:
        lv3, _, _ = st.columns([1, 0.28, 1])
        with lv3: st.markdown(_varr("#6366f1", e_v3_lv_act, e_v3_lv_vis), unsafe_allow_html=True)

    # --- Render Row 4 ---
    c1, ca, c2 = st.columns([1, 0.28, 1])
    with c1: st.markdown(_nd("gorsel_olustur"), unsafe_allow_html=True)
    with ca: st.markdown(_harr("rainbow", e_h4_act, e_h4_vis), unsafe_allow_html=True)
    with c2: st.markdown(_nd("pixverse"), unsafe_allow_html=True)

    # --- Arrows Row 4 to 5 ---
    if e_v4_rl_vis:
        color = _TOP["video_montaj"] if "video_montaj" in batch_q else _TOP["toplu_video"] if "toplu_video" in batch_q else "#00FFFF"
        st.markdown(_diarr(color, e_v4_rl_act, e_v4_rl_vis, direction="right-to-left"), unsafe_allow_html=True)
    elif e_v4_rl_pv_vis:
        st.markdown(_diarr(_TOP["pixverse"], e_v4_rl_pv_act, e_v4_rl_pv_vis, direction="right-to-left"), unsafe_allow_html=True)
    elif e_v4_rv_vis:
        _, _, rv4 = st.columns([1, 0.28, 1])
        with rv4: st.markdown(_varr(_TOP["pixverse"], e_v4_rv_act, e_v4_rv_vis), unsafe_allow_html=True)
    else:
        lv4, _, _ = st.columns([1, 0.28, 1])
        with lv4: st.markdown(_varr("rainbow", e_v4_lv_act, e_v4_lv_vis), unsafe_allow_html=True)

    # --- Render Row 5 ---
    c1, ca, c2 = st.columns([1, 0.28, 1])
    with c1: st.markdown(_nd("sosyal_medya"), unsafe_allow_html=True)
    # The middle column handles empty layout spacer to push Montaj to the right. 
    with c2: st.markdown(_nd("video_montaj"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="top-column-strip"></div>', unsafe_allow_html=True)
    with st.expander("⚙️ Ayarlar", expanded=False):
        s = st.session_state.settings.copy()
        s["video_model"] = _normalize_video_model(s.get("video_model"), s.get("pixverse_script", ""))
        s["links_file"] = st.text_input("Link TXT:", s["links_file"], on_change=clear_dialog_states)
        s["download_dir"] = st.text_input("İndirme:", s["download_dir"], on_change=clear_dialog_states)
        s["youtube_link_script"] = st.text_input("📺 YouTube Link Script:", s.get("youtube_link_script",""), on_change=clear_dialog_states)
        s["gemini_api_key"] = st.text_input("🔑 Gemini API Key (Çeviri için):", s.get("gemini_api_key",""), type="password", on_change=clear_dialog_states)
        s["prompt_duzeltme_script"] = st.text_input("✏️ Prompt Düzeltme Script:", s.get("prompt_duzeltme_script",""), on_change=clear_dialog_states)
        s["prompt_duzeltme_txt"] = st.text_input("✏️ düzeltme.txt Yolu:", s.get("prompt_duzeltme_txt",""), on_change=clear_dialog_states)
        s["video_montaj_script"] = st.text_input("🎞️ Video Montaj Script:", s.get("video_montaj_script",""), on_change=clear_dialog_states)
        s["video_montaj_output_dir"] = st.text_input("🎞️ Yapılan Videolar Klasörü:", s.get("video_montaj_output_dir",""), on_change=clear_dialog_states)
        s["toplu_video_script"] = st.text_input("🎬 Toplu Video Script:", s.get("toplu_video_script",""), on_change=clear_dialog_states)
        s["toplu_video_output_dir"] = st.text_input("🎬 Toplu Video Çıktı Klasörü:", s.get("toplu_video_output_dir",""), on_change=clear_dialog_states)
        s["toplu_video_materyal_dir"] = st.text_input("🧩 Toplu Video Materyal Klasörü:", s.get("toplu_video_materyal_dir",""), on_change=clear_dialog_states)
        s["klon_video_dir"] = st.text_input("🎬 Klon Video Klasörü:", s.get("klon_video_dir",""), on_change=clear_dialog_states)
        s["video_montaj_gorsel_dir"] = st.text_input("🖼️ Montaj Görsel Klasörü:", s.get("video_montaj_gorsel_dir",""), on_change=clear_dialog_states)
        s["sosyal_medya_script"] = st.text_input("🌐 Sosyal Medya Script:", s.get("sosyal_medya_script",""), on_change=clear_dialog_states)
        s["sosyal_medya_dir"] = st.text_input("🌐 Sosyal Medya Klasörü:", s.get("sosyal_medya_dir",""), on_change=clear_dialog_states)
        s["sosyal_medya_video_dir"] = st.text_input("🎬 Sosyal Medya Video Klasörü:", s.get("sosyal_medya_video_dir",""), on_change=clear_dialog_states)
        s["sosyal_medya_aciklama_txt"] = st.text_input("📄 açıklama.txt Yolu:", s.get("sosyal_medya_aciklama_txt",""), on_change=clear_dialog_states)
        s["sosyal_medya_baslik_txt"] = st.text_input("🏷️ başlık.txt Yolu:", s.get("sosyal_medya_baslik_txt",""), on_change=clear_dialog_states)
        s["sosyal_medya_platform_txt"] = st.text_input("🌐 paylasılacak_sosyal_medyalar.txt Yolu:", s.get("sosyal_medya_platform_txt",""), on_change=clear_dialog_states)
        s["sosyal_medya_zamanlama_txt"] = st.text_input("🕒 paylaşım_zamanlama.txt Yolu:", s.get("sosyal_medya_zamanlama_txt",""), on_change=clear_dialog_states)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("Kaydet", use_container_width=True, on_click=clear_dialog_states): st.session_state.settings = s; save_settings(s); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
            if st.button("Sıfırla", use_container_width=True, on_click=clear_dialog_states): st.session_state.settings = DEFAULT_SETTINGS.copy(); save_settings(st.session_state.settings); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="right-panel-strip"></div>', unsafe_allow_html=True)
    st.markdown('<div class="right-panel-title">🎬 Model Seçimi</div>', unsafe_allow_html=True)
    st.markdown('<div class="right-panel-subtitle"></div>', unsafe_allow_html=True)
    current_settings = st.session_state.settings.copy()
    current_settings["video_model"] = _normalize_video_model(
        current_settings.get("video_model"),
        current_settings.get("pixverse_script", ""),
    )
    current_model = current_settings["video_model"]
    selected_model = st.selectbox(
        "",
        VIDEO_MODEL_OPTIONS,
        index=VIDEO_MODEL_OPTIONS.index(current_model) if current_model in VIDEO_MODEL_OPTIONS else 0,
        key="video_model_selector_below_settings",
        on_change=clear_dialog_states,
        label_visibility="collapsed",
    )
    if selected_model != current_model:
        current_settings["video_model"] = selected_model
        current_settings["pixverse_script"] = get_active_video_script(current_settings)
        st.session_state.settings = current_settings
        save_settings(current_settings)
        st.rerun()

    st.markdown('<div class="right-panel-strip"></div>', unsafe_allow_html=True)
    with st.expander("📋 Canlı Log", expanded=True):
        st.markdown(render_logs_html(), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ Temizle", use_container_width=True, on_click=clear_dialog_states): st.session_state.logs =[]; st.rerun()
        with c2:
            if st.button("🔄 Yenile", use_container_width=True, on_click=clear_dialog_states): st.rerun()

    st.markdown('<div class="right-panel-strip"></div>', unsafe_allow_html=True)
    st.markdown('<div class="right-panel-title">🚀 Toplu İşlemler</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("🗂️ Dosya Yöneticisi", use_container_width=True, disabled=is_ui_locked(), on_click=clear_dialog_states): 
            st.session_state.last_dialog_align = "right"
            st.session_state.ek_dialog_open = "dosya_yoneticisi"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("🧹 Sıfırla", use_container_width=True, on_click=clear_dialog_states):
            try: bg_terminate()
            except: pass
            for k in st.session_state.status: st.session_state.status[k] = "idle"
            st.session_state.logs =[]; st.session_state.batch_mode = False; st.session_state.batch_step = 0
            st.session_state.batch_queue = []; st.session_state.batch_queue_idx = 0
            st.session_state.single_mode = False; st.session_state.single_step = None; st.session_state.ek_dialog_open = None
            st.session_state.single_paused = False; st.session_state.batch_paused = False
            st.session_state.single_finish_requested = False; st.session_state.batch_finish_requested = False
            st.session_state.bg_last_result = None; st.session_state.file_manager_trigger = False
            st.session_state.batch_resume_queue = []; st.session_state.batch_resume_idx = 0
            st.session_state.batch_resume_reason = ""
            st.session_state.durum_ozeti_suppress = False
            if "_paused_step" in st.session_state: del st.session_state["_paused_step"]
            st.session_state.pop("graph_config", None)
            durum_ozeti_sifirla()  # Durum özetini de sıfırla
            cleanup_flags(); cleanup_state_files(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- VIDEO ÜRETME KREDİSİ — state temizleme ----
    # Grace period: başlatmadan hemen sonra bg_is_running() kısa süre False dönse bile state'i silme
    _kredi_kazan_start_ts = st.session_state.get("kredi_kazan_start_ts", 0.0)
    _kredi_cek_start_ts = st.session_state.get("kredi_cek_start_ts", 0.0)
    _kredi_kazan_grace_ok = (time.time() - _kredi_kazan_start_ts) > 10  # 10 saniye grace period
    _kredi_cek_grace_ok = (time.time() - _kredi_cek_start_ts) > 10
    if st.session_state.get("kredi_kazan_running", False) and not bg_is_running() and _kredi_kazan_grace_ok:
        st.session_state.kredi_kazan_running = False
        st.session_state.kredi_kazan_paused = False
        if not st.session_state.get("kredi_kazan_finish", False):
            log("[INFO] Kredi kazanma işlemi tamamlandı.")
        st.session_state.kredi_kazan_finish = False
    if st.session_state.get("kredi_cek_running", False) and not bg_is_running() and _kredi_cek_grace_ok:
        st.session_state.kredi_cek_running = False
        st.session_state.kredi_cek_paused = False
        if not st.session_state.get("kredi_cek_finish", False):
            log("[INFO] Kredi çekme işlemi tamamlandı.")
        st.session_state.kredi_cek_finish = False


# --- PATCH_DIALOG_ROUTER_V1 ---

@st.dialog("🖼️ Görsel Oluştur", width="large")
def gorsel_olustur_dialog():
    st.subheader("Görsel Oluştur & Hareketlendir")
    mode_idx = 0 if st.session_state.get("go_mode_val", "Görsel") == "Video" else 1
    mode = st.radio("İşlem Modu", ["Video", "Görsel"], horizontal=True, index=mode_idx, key="go_mode_widget")
    if mode != st.session_state.get("go_mode_val"):
        st.session_state["go_mode_val"] = mode
    
    gorsel_models = ["Nano Banana 2", "Nano Banana Pro", "Nano Banana", "Seedream 5.0 Lite", "Seedream 4.5", "Qwen Image"]
    current_gm = st.session_state.settings.get("gorsel_model", "Nano Banana 2")
    if current_gm not in gorsel_models:
        current_gm = "Nano Banana 2"
    
    secili_model = st.selectbox("Görsel Modeli", gorsel_models, index=gorsel_models.index(current_gm))
    if secili_model != current_gm:
        st.session_state.settings["gorsel_model"] = secili_model
        save_settings(st.session_state.settings)
        st.rerun()
    
    stiller = ["Yok", "Gerçekçi", "Sinematik", "Cartoon", "2D", "Pixel Art", "Anime"]
    
    import os
    if mode == "Görsel":
        if "go_gorsel_count" not in st.session_state:
            st.session_state.go_gorsel_count = 1
        
        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
        with c1:
            st.write("Görsellerinizi ve hareketlendirme promptlarını girin.")
        with c2:
            if st.button("➕ Görsel Ekle", use_container_width=True):
                st.session_state.go_gorsel_count += 1
                st.session_state.ek_dialog_open = "gorsel_olustur"
                st.rerun()
        with c3:
            if st.button("➖ Sil (Azalt)", use_container_width=True):
                if st.session_state.go_gorsel_count > 1:
                    st.session_state.go_gorsel_count -= 1
                    st.session_state.ek_dialog_open = "gorsel_olustur"
                    st.rerun()
        
        for i in range(st.session_state.go_gorsel_count):
            with st.expander(f"Görsel {i+1}", expanded=True):
                v_gp = st.text_area("Görsel Oluşturma Promptu", value=st.session_state.get(f"go_gp_val_{i}", ""), key=f"go_gp_{i}")
                if v_gp != st.session_state.get(f"go_gp_val_{i}", ""): st.session_state[f"go_gp_val_{i}"] = v_gp
                
                s_gs = st.selectbox("Görsel Türü", stiller, index=stiller.index(st.session_state.get(f"go_gs_val_{i}", "Yok")) if st.session_state.get(f"go_gs_val_{i}", "Yok") in stiller else 0, key=f"go_gs_{i}")
                if s_gs != st.session_state.get(f"go_gs_val_{i}", "Yok"): st.session_state[f"go_gs_val_{i}"] = s_gs
                
                st.markdown("---")
                v_vp = st.text_area("Video Üret (Hareketlendirme) Promptu", value=st.session_state.get(f"go_vp_val_{i}", ""), key=f"go_vp_{i}")
                if v_vp != st.session_state.get(f"go_vp_val_{i}", ""): st.session_state[f"go_vp_val_{i}"] = v_vp
                
                s_vs = st.selectbox("Hareketlendirme Türü", stiller, index=stiller.index(st.session_state.get(f"go_vs_val_{i}", "Yok")) if st.session_state.get(f"go_vs_val_{i}", "Yok") in stiller else 0, key=f"go_vs_{i}")
                if s_vs != st.session_state.get(f"go_vs_val_{i}", "Yok"): st.session_state[f"go_vs_val_{i}"] = s_vs
                
    else:
        st.info("Bu modda İndirilecek Linkler, Eklenen Videolar ve İndirilen Videolar ile bağlantılı prompt girilir.")
        entries = _list_prompt_input_entries()
        active_items = []
        
        # Eğer indirilen videolar varsa, linkler zaten indirilmiştir. Çifte işlemi önlemek için linkleri gizliyoruz.
        if entries.get("downloaded_videos"):
            for i, vd in enumerate(entries.get("downloaded_videos", [])):
                active_items.append({"tip": "İndirilen Video", "ad": vd, "index": i + 1})
        else:
            for i, link in enumerate(entries.get("links", [])):
                active_items.append({"tip": "Link", "ad": link, "index": i + 1})
                
        for i, va in enumerate(entries.get("added_videos", [])):
            active_items.append({"tip": "Eklenen Video", "ad": va, "index": i + 1})
            
        st.session_state.go_vid_count = len(active_items)
        
        if not active_items:
            st.warning("⚠️ Hiçbir şey ekli değil! Kaynak (Link, İndirilen veya Eklenen Video) eklenene kadar prompt giremezsiniz.")
        else:
            for i, item in enumerate(active_items):
                baslik = f"{item['tip']} {item['index']}"
                with st.expander(baslik, expanded=True):
                    v_vid_gp = st.text_area("Görsel Oluşturma Promptu", value=st.session_state.get(f"go_vid_gp_val_{i}", ""), key=f"go_vid_gp_{i}")
                    if v_vid_gp != st.session_state.get(f"go_vid_gp_val_{i}", ""): st.session_state[f"go_vid_gp_val_{i}"] = v_vid_gp
                    
                    s_vid_gs = st.selectbox("Görsel Türü", stiller, index=stiller.index(st.session_state.get(f"go_vid_gs_val_{i}", "Yok")) if st.session_state.get(f"go_vid_gs_val_{i}", "Yok") in stiller else 0, key=f"go_vid_gs_{i}")
                    if s_vid_gs != st.session_state.get(f"go_vid_gs_val_{i}", "Yok"): st.session_state[f"go_vid_gs_val_{i}"] = s_vid_gs

    st.markdown("---")
    kaliteler = ["Standart", "Yüksek", "Maksimum"]
    boyutlar = ["16:9", "9:16", "1:1", "4:3", "3:4"]
    
    mevcut_kalite = st.session_state.settings.get("gorsel_kalitesi", "Standart")
    mevcut_boyut = st.session_state.settings.get("gorsel_boyutu", "16:9")
    
    k_idx = kaliteler.index(mevcut_kalite) if mevcut_kalite in kaliteler else 0
    b_idx = boyutlar.index(mevcut_boyut) if mevcut_boyut in boyutlar else 0
    
    c3, c4 = st.columns(2)
    with c3:
        st.selectbox("Görsel Kalitesi", kaliteler, index=k_idx, key="go_kalite")
    with c4:
        st.selectbox("Görsel Boyutu", boyutlar, index=b_idx, key="go_boyut")
        
    st.markdown("---")
    
    s1, s2 = st.columns(2)
    with s1:
        st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
        if st.button("💾 Kaydet", use_container_width=True):
            st.success("Tüm promptlar ilgili klasörlere başarıyla kaydedildi.")
            # Modeli kaydet (ki run edince arka planda doğru modeli okusun)
            st.session_state.settings["gorsel_model"] = secili_model
            save_settings(st.session_state.settings)
            
            import time
            
            gorsel_prompt_dir = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Prompt"
            video_prompt_dir  = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Hareklendirme Prompt"
            os.makedirs(gorsel_prompt_dir, exist_ok=True)
            os.makedirs(video_prompt_dir, exist_ok=True)
            
            count = st.session_state.go_gorsel_count if mode == "Görsel" else st.session_state.go_vid_count
            prefix = "go" if mode == "Görsel" else "go_vid"
            has_motion_prompt = False
            
            for i in range(count):
                g_p = st.session_state.get(f"{prefix}_gp_{i}", "").strip()
                g_s = st.session_state.get(f"{prefix}_gs_{i}", "Yok")
                if prefix == "go":
                    v_p = st.session_state.get(f"{prefix}_vp_{i}", "").strip()
                    v_s = st.session_state.get(f"{prefix}_vs_{i}", "Yok")
                    if v_p:
                        has_motion_prompt = True
                else:
                    v_p = ""
                    v_s = "Yok"
                
                # Subfolders
                gp_sub = os.path.join(gorsel_prompt_dir, f"Görsel Prompt {i+1}")
                vp_sub = os.path.join(video_prompt_dir, f"Video Prompt {i+1}")
                os.makedirs(gp_sub, exist_ok=True)
                
                # Read templates
                base_t_dir = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma"
                
                def get_full_prompt(raw_text, style):
                    if style != "Yok":
                        t_path = os.path.join(base_t_dir, f"{style}.txt")
                        if os.path.exists(t_path):
                            with open(t_path, "r", encoding="utf-8") as f:
                                t_content = f.read().strip()
                            return f"{raw_text}, {t_content}" if raw_text else t_content
                    return raw_text
                    
                final_g_p = get_full_prompt(g_p, g_s)
                final_v_p = get_full_prompt(v_p, v_s)
                
                with open(os.path.join(gp_sub, "gorsel_prompt.txt"), "w", encoding="utf-8") as f:
                    f.write(final_g_p)
                    
                if not v_p:
                    if os.path.exists(vp_sub): shutil.rmtree(vp_sub)
                else:
                    os.makedirs(vp_sub, exist_ok=True)
                    with open(os.path.join(vp_sub, "prompt.txt"), "w", encoding="utf-8") as f:
                        f.write(final_v_p)
            
            st.session_state["go_motion_prompt_saved"] = bool(mode == "Görsel" and has_motion_prompt)
            if mode == "Görsel" and has_motion_prompt:
                log("[INFO] Görsel hareketlendirme promptları kaydedildi. Video Üret görsel prompt klasörünü kullanacak.")
            else:
                log("[INFO] Görsel hareketlendirme promptu aktif değil. Video Üret standart Prompt klasörünü kullanacak.")
                         
            st.session_state["go_saved"] = True
            st.session_state.ek_dialog_open = "gorsel_olustur"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with s2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("🗑️ Temizle", use_container_width=True):
            keys_to_del = [k for k in st.session_state.keys() if k.startswith(("go_gp", "go_gs", "go_vp", "go_vs", "go_vid"))]
            for k in keys_to_del:
                del st.session_state[k]
            st.session_state.go_gorsel_count = 1
            st.session_state.go_vid_count = 1
            st.session_state.ek_dialog_open = "gorsel_olustur"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    if st.session_state.get("go_saved", False):
        _go_ph = st.empty()
        _go_ph.success("Kaydedildi! Promptlar ilgili klasörlere başarıyla yazdırıldı.")
        import time
        time.sleep(2.0)
        _go_ph.empty()
        st.session_state.pop("go_saved", None)

    st.markdown("---")
    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.button("🚀 Görsel Oluştur", use_container_width=True):
        st.session_state.settings["gorsel_model"] = secili_model
        st.session_state.settings["gorsel_boyutu"] = st.session_state.get("go_boyut", "16:9")
        st.session_state.settings["gorsel_kalitesi"] = st.session_state.get("go_kalite", "Standart")
        save_settings(st.session_state.settings)
        
        st.session_state.single_paused = False
        st.session_state.single_finish_requested = False
        st.session_state.single_mode = True
        st.session_state.bg_last_result = None
        st.session_state.single_step = "gorsel_olustur"
        cleanup_flags()
        st.session_state.status["gorsel_olustur"] = "running"
        st.session_state.ek_dialog_open = "gorsel_olustur"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    render_dialog_single_controls(step_match="gorsel_olustur", prefix="dlg_gorsel_olustur")

    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", use_container_width=True):
        st.session_state.ek_dialog_open = "menu"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def _patch_render_pending_dialogs():
    if st.session_state.get("durum_ozeti_dialog_open", False):
        st.session_state.durum_ozeti_dialog_open = False
        st.session_state.last_dialog_align = "center"
        render_durum_ozeti_modal()

    elif st.session_state.lightbox_gorsel is not None:
        _lb = st.session_state.lightbox_gorsel; st.session_state.lightbox_gorsel = None
        st.session_state.last_dialog_align = "center"
        gorsel_lightbox_dialog(_lb["path"], _lb["adi"])

    elif st.session_state.get("file_manager_trigger", False):
        st.session_state.file_manager_trigger = False
        dosya_yoneticisi_dialog()


    else:
        hedef = st.session_state.get("ek_dialog_open")
        if hedef:
            # Sadece arka planda islem yoksa (boştaysa) None yap.
            # Bu durum dialog'un, saniyede bir olan yenilemelerde kapanip acilmasini / yanip sonmesini engeller.
            _running_now = (
                st.session_state.get("single_mode", False)
                or st.session_state.get("batch_mode", False)
                or st.session_state.get("kredi_kazan_running", False)
                or st.session_state.get("kredi_cek_running", False)
            )
            if not _running_now:
                st.session_state.ek_dialog_open = None
        if hedef == "menu":
            ek_islemler_menu_dialog()
        elif hedef == "youtube_link":
            youtube_link_dialog()
        elif hedef == "video_listesi":
            video_listesi_dialog()
        elif hedef == "video_ekle":
            video_ekle_dialog()
        elif hedef == "video_bolumle":
            video_bolumlerine_ayir_dialog()
        elif hedef == "gorsel_analiz":
            st.session_state.last_dialog_align = "left"
            gorsel_analiz_dialog()
        elif hedef == "gorsel_klonla":
            gorsel_klonla_dialog()
        elif hedef == "prompt_duzeltme":
            prompt_duzeltme_dialog()
        elif hedef == "gorsel_olustur":
            gorsel_olustur_dialog()
        elif hedef == "video_montaj":
            video_montaj_dialog()
        elif hedef == "toplu_video":
            toplu_video_dialog()
        elif hedef == "sosyal_medya":
            sosyal_medya_dialog()
        elif hedef == "vm_asset_manager":
            vm_asset_manager_dialog()
        elif hedef == "tv_asset_manager":
            tv_asset_manager_dialog()
        elif hedef == "video_ayarlari":
            video_ayarlari_dialog()
        elif hedef == "prompt_ayarlari":
            prompt_ayarlari_dialog()
        elif hedef == "kredi":
            kredi_dialog()
        elif hedef == "dosya_yoneticisi":
            st.session_state.last_dialog_align = "right"
            dosya_yoneticisi_dialog()

_patch_render_pending_dialogs()

_is_any_paused = (
    st.session_state.get("batch_paused", False) or
    st.session_state.get("single_paused", False) or
    st.session_state.get("kredi_kazan_paused", False)
)

if bg_is_running() and not _is_any_paused:
    time.sleep(1)
    st.rerun()
