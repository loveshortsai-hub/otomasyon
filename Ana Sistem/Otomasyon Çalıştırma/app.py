import importlib.util
import os, json, time, sys, subprocess, shutil, glob, re, textwrap
import streamlit as st
import streamlit.components.v1 as _st_components
try:
    from google import genai as _genai
    _GENAI_OK = True
except ImportError:
    _GENAI_OK = False

st.set_page_config(page_title="Otomasyon Paneli", layout="wide")

def _reset_complex_dialog_lazy_state(dialog_key: str | None = None) -> None:
    target = str(dialog_key or "").strip()
    reset_all = not target

    if reset_all or target in {"toplu_video", "tv_asset_manager"}:
        st.session_state.pop("_tv_preset_loaded", None)

    if reset_all or target in {"video_montaj", "vm_asset_manager"}:
        st.session_state.pop("_vm_preset_loaded", None)

    if reset_all or target == "sosyal_medya":
        st.session_state.pop("sm_video_kaynak_secim_loaded", None)
        st.session_state.pop("sm_last_hesap_mode_rendered", None)

def _keep_ek_dialog_open_on_rerun(dialog_key: str | None) -> bool:
    if dialog_key in {"video_ekle", "video_bolumle"}:
        return True
    return st.session_state.get("_ek_dialog_keepalive") == dialog_key


def _request_ek_dialog_open(dialog_key: str) -> None:
    _reset_complex_dialog_lazy_state(dialog_key)
    st.session_state.ek_dialog_open = dialog_key
    st.session_state._ek_dialog_keepalive = dialog_key


def _reset_video_bolum_temp(remove_file: bool = False):
    temp_path = st.session_state.get("video_bolum_temp_path")
    if remove_file and temp_path:
        try:
            split_dir = os.path.abspath(os.path.join(CONTROL_DIR, "_temp_video_split"))
            temp_abs = os.path.abspath(str(temp_path))
            if temp_abs.startswith(split_dir) and os.path.isfile(temp_abs):
                os.remove(temp_abs)
        except Exception:
            pass
    st.session_state.video_bolum_temp_path = None
    st.session_state.video_bolum_temp_name = None
    st.session_state.video_bolum_source_kind = "file"
    st.session_state.video_bolum_source_no = None
    st.session_state.video_bolum_source_url = ""
    st.session_state.video_bolum_source_title = ""
    st.session_state.video_bolum_source_duration = 0.0
    st.session_state.video_bolum_preview_url = ""
    st.session_state.pop("_dlg_bolum_pending_updates", None)
    st.session_state.pop("_bolum_sayisi_prev", None)
    st.session_state.pop("_bolum_sure_secim", None)
    st.session_state.pop("_video_bolum_init_token", None)
    st.session_state.pop("dlg_bolum_playback_rate", None)
    st.session_state.pop("dlg_bolum_sayisi", None)
    for _old_i in range(50):
        st.session_state.pop(f"dlg_bolum_baslangic_{_old_i}", None)
        st.session_state.pop(f"dlg_bolum_bitis_{_old_i}", None)


def _handle_ek_dialog_dismiss():
    current_dialog = st.session_state.get("ek_dialog_open")
    if current_dialog == "video_bolumle":
        _reset_video_bolum_temp(remove_file=True)
    _reset_complex_dialog_lazy_state(current_dialog)
    st.session_state.pop("_ek_dialog_keepalive", None)
    st.session_state.ek_dialog_open = None


# ==========================================
# 1. AYARLAR VE VERİ YÖNETİMİ
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANA_SISTEM_ROOT = os.path.dirname(BASE_DIR)
if ANA_SISTEM_ROOT not in sys.path:
    sys.path.insert(0, ANA_SISTEM_ROOT)

from transition_utils import (
    normalize_video_mode as _normalize_transition_video_mode,
    load_transition_state as _load_transition_state_file,
    save_transition_state as _save_transition_state_file,
    is_video_transition_enabled as _is_video_transition_enabled_file,
    video_model_supports_transition,
    resolve_transition_pair,
    resolve_single_image,
    replace_folder_images_with_standard_images,
)

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
KLING30_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Kling 3.0\kling_30.py"
KLINGO3_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Kling O3\kling_o3.py"
SEEDANCE20_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Seedance 2.0\seedance 2.0.py"
HAPPY_HORSE_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Happy Horse 1.0\happy_horse_1.0.py"
V56_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Pixverse\pixverse_v56.py"
VEO31_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Veo\pixverse_veo31.py"
GROK_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Grok\pixverse_grok.py"
C1_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Oluşturma\Pixverse C1\pixverse_c1.py"
MODIFY_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Klonla\modify.py"
MOTION_CONTROL_SCRIPT_DEFAULT = r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Video Klonla\motion_control.py"
VIDEO_KLONLA_CONTROL_PATH = os.path.join(CONTROL_DIR, "video_klonla_state.json")
VIDEO_KLONLA_RUNTIME_PATH = os.path.join(CONTROL_DIR, "video_klonla_runtime.json")
VIDEO_KLONLA_UPLOAD_DIR = os.path.join(CONTROL_DIR, "video_klonla_uploads")
VIDEO_MODEL_OPTIONS = ["Happy Horse 1.0", "Sora 2", "Kling 3.0", "Kling O3", "Seedance 2.0", "Veo 3.1 Standard", "Grok", "PixVerse V6", "PixVerse Cinematic"]
PIXVERSE_IMAGE_MODEL_OPTIONS = [
    "Qwen Image",
    "GPT Image 2",
    "Nano Banana 2",
    "Nano Banana Pro",
    "Nano Banana",
    "Seedream 5.0 Lite",
    "Seedream 4.5",
    "Seedream 4.0",
    "Kling O3",
    "Kling 3.0",
]
PIXVERSE_IMAGE_QUALITY_OPTIONS = ["Standart", "Yüksek", "Maksimum"]
PIXVERSE_IMAGE_ASPECT_RATIO_OPTIONS = ["16:9", "9:16", "1:1", "4:3", "3:4"]
PIXVERSE_IMAGE_CLONE_MODEL_OPTIONS = [
    "Qwen Image",
    "GPT Image 2",
    "Nano Banana 2",
    "Nano Banana Pro",
    "Nano Banana",
    "Seedream 5.0 Lite",
    "Seedream 4.5",
    "Seedream 4.0",
    "Kling O3",
]
DEFAULT_GORSEL_MODEL = "Nano Banana 2"
DEFAULT_GORSEL_KLONLAMA_MODEL = "Kling O3"
TRANSLATION_MODEL = "gemini-2.5-flash"
PROMPT_TEMPLATE_PRESETS = [
    {"key": "original", "label": "Orjinal", "filename": "istem.txt"},
    {"key": "realistic", "label": "Gerçekçi", "filename": "photorealistic_real_life.txt"},
    {"key": "cinematic", "label": "Sinematik", "filename": "cinematic.txt"},
    {"key": "animation", "label": "Animasyon", "filename": "cinematic_animation.txt"},
    {"key": "anime", "label": "Anime", "filename": "anime.txt"},
]
PROMPT_TEMPLATE_KEYS = {item["key"] for item in PROMPT_TEMPLATE_PRESETS}


def _normalize_prompt_template_key(value, default_value="original"):
    raw = str(value or "").strip().lower()
    aliases = {
        "original": "original",
        "orjinal": "original",
        "orijinal": "original",
        "istem": "original",
        "istem.txt": "original",
        "realistic": "realistic",
        "gercekci": "realistic",
        "gerçekçi": "realistic",
        "photorealistic": "realistic",
        "photorealistic_real_life": "realistic",
        "photorealistic_real_life.txt": "realistic",
        "cinematic": "cinematic",
        "sinematik": "cinematic",
        "cinematic.txt": "cinematic",
        "animation": "animation",
        "animasyon": "animation",
        "cinematic_animation": "animation",
        "cinematic_animation.txt": "animation",
        "anime": "anime",
        "anime.txt": "anime",
    }
    fallback = default_value if default_value in PROMPT_TEMPLATE_KEYS else "original"
    return aliases.get(raw, fallback)


def _normalize_pixverse_image_model(model_value, default_model=None):
    value = str(model_value or "").strip().lower()
    if value in {"qwen image", "qwen-image", "qwenimage"}:
        return "Qwen Image"
    if value in {"gpt image 2", "gptimage2", "gpt-image-2", "gpt-image-2.0", "cpt image 2", "cptimage2", "cpt-image-2", "cpt-image-2.0"}:
        return "GPT Image 2"
    if value in {"nano banana 2", "nanobanana2", "gemini-3.1-flash"}:
        return "Nano Banana 2"
    if value in {"nano banana pro", "nanobananapro", "gemini-3.0"}:
        return "Nano Banana Pro"
    if value in {"nano banana", "nanobanana", "gemini-2.5-flash"}:
        return "Nano Banana"
    if value in {"seedream 5.0 lite", "seedream5.0lite", "seedream-5.0-lite"}:
        return "Seedream 5.0 Lite"
    if value in {"seedream 4.5", "seedream4.5", "seedream-4.5"}:
        return "Seedream 4.5"
    if value in {"seedream 4.0", "seedream4.0", "seedream-4.0"}:
        return "Seedream 4.0"
    if value in {"kling o3", "klingo3", "kling-image-o3"}:
        return "Kling O3"
    if value in {"kling 3.0", "kling3.0", "kling30", "kling-image-v3"}:
        return "Kling 3.0"
    return default_model or DEFAULT_GORSEL_MODEL


def _normalize_clone_image_model(model_value, default_model=None):
    normalized = _normalize_pixverse_image_model(
        model_value,
        default_model or DEFAULT_GORSEL_KLONLAMA_MODEL,
    )
    if normalized == "Kling 3.0":
        return default_model or DEFAULT_GORSEL_KLONLAMA_MODEL
    if normalized in PIXVERSE_IMAGE_CLONE_MODEL_OPTIONS:
        return normalized
    return default_model or DEFAULT_GORSEL_KLONLAMA_MODEL


def _normalize_image_quality(value, default_value="Standart"):
    normalized = str(value or "").strip().title()
    if normalized in PIXVERSE_IMAGE_QUALITY_OPTIONS:
        return normalized
    return default_value if default_value in PIXVERSE_IMAGE_QUALITY_OPTIONS else PIXVERSE_IMAGE_QUALITY_OPTIONS[0]


def _normalize_image_aspect_ratio(value, default_value="16:9"):
    normalized = str(value or "").strip()
    if normalized in PIXVERSE_IMAGE_ASPECT_RATIO_OPTIONS:
        return normalized
    return default_value if default_value in PIXVERSE_IMAGE_ASPECT_RATIO_OPTIONS else PIXVERSE_IMAGE_ASPECT_RATIO_OPTIONS[0]

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
    "prompt_istem_txt": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Prompt Oluşturma\istem.txt",
    "prompt_template_key": "original",
    "video_model": "Sora 2",
    "sora2_script": SORA2_SCRIPT_DEFAULT,
    "kling30_script": KLING30_SCRIPT_DEFAULT,
    "klingo3_script": KLINGO3_SCRIPT_DEFAULT,
    "seedance20_script": SEEDANCE20_SCRIPT_DEFAULT,
    "happy_horse_script": HAPPY_HORSE_SCRIPT_DEFAULT,
    "v56_script": V56_SCRIPT_DEFAULT,
    "veo31_script": VEO31_SCRIPT_DEFAULT,
    "grok_script": GROK_SCRIPT_DEFAULT,
    "c1_script": C1_SCRIPT_DEFAULT,
    "video_klonla_modify_script": MODIFY_SCRIPT_DEFAULT,
    "video_klonla_motion_script": MOTION_CONTROL_SCRIPT_DEFAULT,
    "video_klonla_dir": r"C:\Users\User\Desktop\Otomasyon\Klon Video",
    "pixverse_script": SORA2_SCRIPT_DEFAULT,
    "nano_banana2_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana2.py",
    "nano_banana_pro_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana_pro.py",
    "nano_banana_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\nano_banana.py",
    "seedream_50_lite_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\seedream_5.0-lite.py",
    "seedream_45_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\seedream_4.5.py",
    "qwen_image_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\qwen_image.py",
    "gpt_image_2_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\gpt_image_2.py",
    "gorsel_olustur_dir": r"C:\Users\User\Desktop\Otomasyon\Görsel\Görseller",
    "analiz_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Analiz\analiz.py",
    "gorsel_klonlama_script": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluştur\görsel_klonlama.py",
    "gorsel_analiz_dir": r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Analiz",
    "klon_gorsel_dir": r"C:\Users\User\Desktop\Otomasyon\Görsel\Klon Görsel",
    "gorsel_duzelt_txt": r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluştur\Görsel Düzelt.txt",
    "gorsel_model": DEFAULT_GORSEL_MODEL,
    "gorsel_klonlama_model": DEFAULT_GORSEL_KLONLAMA_MODEL,
    "gorsel_kalitesi": "Standart",
    "gorsel_boyutu": "16:9",
    "gorsel_klonlama_kalitesi": "Standart",
    "gorsel_klonlama_boyutu": "16:9",
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


def _get_prompt_template_options(settings_obj: dict | None = None) -> list:
    src = settings_obj if isinstance(settings_obj, dict) else st.session_state.get("settings", {})
    prompt_script = str((src or {}).get("prompt_script") or DEFAULT_SETTINGS.get("prompt_script") or "").strip()
    prompt_root = os.path.dirname(prompt_script) if prompt_script else r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Prompt Oluşturma"
    original_path = str((src or {}).get("prompt_istem_txt") or os.path.join(prompt_root, "istem.txt")).strip()

    out = []
    for item in PROMPT_TEMPLATE_PRESETS:
        meta = dict(item)
        meta["path"] = original_path if item["key"] == "original" else os.path.join(prompt_root, item["filename"])
        out.append(meta)
    return out

def _normalize_video_model(model_value, pixverse_script_path=""):
    value = str(model_value or "").strip().lower()
    if value in {"sora 2", "sora2", "sora-2"}:
        return "Sora 2"
    if value in {"kling 3.0", "kling3.0", "kling30", "kling-3.0", "kling 3"}:
        return "Kling 3.0"
    if value in {"kling o3", "klingo3", "kling-o3"}:
        return "Kling O3"
    if value in {"seedance 2.0", "seedance2.0", "seedance20", "seedance-2.0", "seedance 2"}:
        return "Seedance 2.0"
    if value in {"happy horse 1.0", "happyhorse 1.0", "happyhorse-1.0", "happy horse", "happyhorse"}:
        return "Happy Horse 1.0"
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
    if value in {"gpt image 2", "gptimage2", "gpt-image-2", "gpt-image-2.0", "cpt image 2", "cptimage2", "cpt-image-2", "cpt-image-2.0"}: return "GPT Image 2"

    script_name = os.path.basename(str(pixverse_script_path or "")).strip().lower()
    if script_name == "pixverse_sora2.py":
        return "Sora 2"
    if script_name == "kling_30.py":
        return "Kling 3.0"
    if script_name == "kling_o3.py":
        return "Kling O3"
    if script_name in {"seedance 2.0.py", "seedance_2_0.py"}:
        return "Seedance 2.0"
    if script_name in {"happy_horse_1.0.py", "happy_horse_10.py"}:
        return "Happy Horse 1.0"
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
    if script_name in {"gpt_image_2.py", "cpt_image_2.py"}: return "GPT Image 2"
    return DEFAULT_SETTINGS["video_model"]


def get_active_video_script(settings: dict) -> str:
    model_name = _normalize_video_model(
        settings.get("video_model"),
        settings.get("pixverse_script", ""),
    )
    if model_name == "Kling 3.0":
        return (settings.get("kling30_script") or KLING30_SCRIPT_DEFAULT).strip()
    if model_name == "Kling O3":
        return (settings.get("klingo3_script") or KLINGO3_SCRIPT_DEFAULT).strip()
    if model_name == "Seedance 2.0":
        return (settings.get("seedance20_script") or SEEDANCE20_SCRIPT_DEFAULT).strip()
    if model_name == "Happy Horse 1.0":
        return (settings.get("happy_horse_script") or HAPPY_HORSE_SCRIPT_DEFAULT).strip()
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
    if model_name == "GPT Image 2": return settings.get("gpt_image_2_script", r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Görsel Oluşturma\gpt_image_2.py").strip()
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


def get_workflow_video_generation_title(settings: dict | None = None) -> str:
    if _video_klonla_is_active():
        return "Klon Video Üret"
    return get_video_generation_title(settings)


def get_workflow_video_generation_canvas_subtitle(settings: dict | None = None) -> str:
    if _video_klonla_is_active():
        return "Motion Control / Modify ile klon video oluştur"
    return get_video_generation_canvas_subtitle(settings)


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
    out["gorsel_model"] = _normalize_pixverse_image_model(
        out.get("gorsel_model"),
        DEFAULT_GORSEL_MODEL,
    )
    out["gorsel_klonlama_model"] = _normalize_clone_image_model(
        out.get("gorsel_klonlama_model") or out.get("gorsel_model"),
        DEFAULT_GORSEL_KLONLAMA_MODEL,
    )
    out["gorsel_kalitesi"] = _normalize_image_quality(
        out.get("gorsel_kalitesi"),
        "Standart",
    )
    out["gorsel_boyutu"] = _normalize_image_aspect_ratio(
        out.get("gorsel_boyutu"),
        "16:9",
    )
    out["gorsel_klonlama_kalitesi"] = _normalize_image_quality(
        out.get("gorsel_klonlama_kalitesi") or out.get("gorsel_kalitesi"),
        "Standart",
    )
    out["gorsel_klonlama_boyutu"] = _normalize_image_aspect_ratio(
        out.get("gorsel_klonlama_boyutu") or out.get("gorsel_boyutu"),
        "16:9",
    )
    out["prompt_template_key"] = _normalize_prompt_template_key(
        out.get("prompt_template_key"),
        "original",
    )
    out["sora2_script"] = SORA2_SCRIPT_DEFAULT
    out["kling30_script"] = KLING30_SCRIPT_DEFAULT
    out["klingo3_script"] = KLINGO3_SCRIPT_DEFAULT
    out["seedance20_script"] = SEEDANCE20_SCRIPT_DEFAULT
    out["happy_horse_script"] = HAPPY_HORSE_SCRIPT_DEFAULT
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
    data["gorsel_model"] = _normalize_pixverse_image_model(
        data.get("gorsel_model"),
        DEFAULT_GORSEL_MODEL,
    )
    data["gorsel_klonlama_model"] = _normalize_clone_image_model(
        data.get("gorsel_klonlama_model") or data.get("gorsel_model"),
        DEFAULT_GORSEL_KLONLAMA_MODEL,
    )
    data["gorsel_kalitesi"] = _normalize_image_quality(
        data.get("gorsel_kalitesi"),
        "Standart",
    )
    data["gorsel_boyutu"] = _normalize_image_aspect_ratio(
        data.get("gorsel_boyutu"),
        "16:9",
    )
    data["gorsel_klonlama_kalitesi"] = _normalize_image_quality(
        data.get("gorsel_klonlama_kalitesi") or data.get("gorsel_kalitesi"),
        "Standart",
    )
    data["gorsel_klonlama_boyutu"] = _normalize_image_aspect_ratio(
        data.get("gorsel_klonlama_boyutu") or data.get("gorsel_boyutu"),
        "16:9",
    )
    data["prompt_template_key"] = _normalize_prompt_template_key(
        data.get("prompt_template_key"),
        "original",
    )
    data["sora2_script"] = SORA2_SCRIPT_DEFAULT
    data["kling30_script"] = KLING30_SCRIPT_DEFAULT
    data["klingo3_script"] = KLINGO3_SCRIPT_DEFAULT
    data["seedance20_script"] = SEEDANCE20_SCRIPT_DEFAULT
    data["happy_horse_script"] = HAPPY_HORSE_SCRIPT_DEFAULT
    data["v56_script"] = V56_SCRIPT_DEFAULT
    data["veo31_script"] = VEO31_SCRIPT_DEFAULT
    data["grok_script"] = GROK_SCRIPT_DEFAULT
    data["c1_script"] = C1_SCRIPT_DEFAULT
    data["pixverse_script"] = get_active_video_script(data)
    json.dump(data, open(SETTINGS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

if "settings" not in st.session_state: st.session_state.settings = load_settings()
if "status" not in st.session_state: st.session_state.status = {"input":"idle","youtube_link":"idle","download":"idle","analyze":"idle","pixverse":"idle","video_klonla":"idle","gorsel_analiz":"idle","gorsel_klonlama":"idle","gorsel_olustur":"idle","prompt_duzeltme":"idle","video_montaj":"idle","toplu_video":"idle","sosyal_medya":"idle","kredi_kazan":"idle","kredi_cek":"idle"}
if "logs" not in st.session_state: st.session_state.logs =[]
if "ui_placeholders" not in st.session_state: st.session_state.ui_placeholders = {}

# Motor Durumları
if "batch_mode" not in st.session_state: st.session_state.batch_mode = False
if "batch_step" not in st.session_state: st.session_state.batch_step = 0
if "batch_queue" not in st.session_state: st.session_state.batch_queue = []
if "batch_queue_idx" not in st.session_state: st.session_state.batch_queue_idx = 0
# Ek İşlemler → Tümünü Çalıştır seçimleri
if "ek_batch_secimler" not in st.session_state:
    st.session_state.ek_batch_secimler = {"video_indir": False, "gorsel_analiz": False, "gorsel_klonla": False, "gorsel_olustur": False, "video_klonla": False, "prompt_duzeltme": False, "video_montaj": False, "toplu_video": False, "sosyal_medya": False}
BATCH_RUN_MODE_AUTO = "Otomatik Seçim"
BATCH_RUN_MODE_MANUAL = "Manual Seçim"
BATCH_RUN_MODE_STATE_KEY = "batch_run_mode_value"
BATCH_RUN_MODE_WIDGET_KEY = "batch_run_mode_widget"
BATCH_SELECTION_DEFAULTS = {
    "video_indir": False,
    "gorsel_analiz": False,
    "gorsel_klonla": False,
    "gorsel_olustur": False,
    "video_klonla": False,
    "analyze": False,
    "prompt_duzeltme": False,
    "pixverse": False,
    "video_montaj": False,
    "toplu_video": False,
    "sosyal_medya": False,
}
BATCH_SELECTION_QUEUE_MAP = {
    "video_indir": "download",
    "gorsel_analiz": "gorsel_analiz",
    "gorsel_klonla": "gorsel_klonlama",
    "gorsel_olustur": "gorsel_olustur",
    "video_klonla": "video_klonla",
    "analyze": "analyze",
    "prompt_duzeltme": "prompt_duzeltme",
    "pixverse": "pixverse",
    "video_montaj": "video_montaj",
    "toplu_video": "toplu_video",
    "sosyal_medya": "sosyal_medya",
}
BATCH_SELECTION_UI_ORDER = tuple(BATCH_SELECTION_DEFAULTS.keys())
BATCH_SELECTION_LABELS = {
    "video_indir": "Video İndir",
    "gorsel_analiz": "Görsel Analiz",
    "gorsel_klonla": "Görsel Klonla",
    "gorsel_olustur": "Görsel Oluştur",
    "video_klonla": "Video Klonla",
    "analyze": "Prompt Oluştur",
    "prompt_duzeltme": "Prompt Düzeltme",
    "video_montaj": "Video Montaj",
    "toplu_video": "Toplu Video Montaj",
    "sosyal_medya": "Sosyal Medya Paylaşım",
}
if BATCH_RUN_MODE_STATE_KEY not in st.session_state:
    st.session_state[BATCH_RUN_MODE_STATE_KEY] = st.session_state.get("batch_run_mode", BATCH_RUN_MODE_AUTO)
if "batch_manual_selection_order" not in st.session_state:
    st.session_state.batch_manual_selection_order = []


def _get_batch_run_mode() -> str:
    value = st.session_state.get(BATCH_RUN_MODE_STATE_KEY, BATCH_RUN_MODE_AUTO)
    if value not in (BATCH_RUN_MODE_AUTO, BATCH_RUN_MODE_MANUAL):
        value = BATCH_RUN_MODE_AUTO
    st.session_state[BATCH_RUN_MODE_STATE_KEY] = value
    return value


def _sync_batch_run_mode_widget() -> None:
    value = st.session_state.get(BATCH_RUN_MODE_WIDGET_KEY, BATCH_RUN_MODE_AUTO)
    if value not in (BATCH_RUN_MODE_AUTO, BATCH_RUN_MODE_MANUAL):
        value = BATCH_RUN_MODE_AUTO
    st.session_state[BATCH_RUN_MODE_STATE_KEY] = value


def _ensure_batch_selection_state() -> dict:
    secs = st.session_state.get("ek_batch_secimler", {})
    if not isinstance(secs, dict):
        secs = {}
    for key, default_value in BATCH_SELECTION_DEFAULTS.items():
        secs.setdefault(key, default_value)
    st.session_state.ek_batch_secimler = secs

    _get_batch_run_mode()

    order = st.session_state.get("batch_manual_selection_order", [])
    if not isinstance(order, list):
        order = []
    order = [key for key in order if key in BATCH_SELECTION_QUEUE_MAP and secs.get(key, False)]
    for key in BATCH_SELECTION_UI_ORDER:
        if secs.get(key, False) and key not in order:
            order.append(key)
    st.session_state.batch_manual_selection_order = order
    return secs


def _on_batch_selection_change(selection_key: str, widget_key: str) -> None:
    secs = _ensure_batch_selection_state()
    selected = bool(st.session_state.get(widget_key, False))
    secs[selection_key] = selected
    order = [
        key
        for key in st.session_state.get("batch_manual_selection_order", [])
        if key != selection_key and secs.get(key, False)
    ]
    if selected:
        order.append(selection_key)
    st.session_state.batch_manual_selection_order = order


def _batch_selection_checkbox(selection_key: str, label: str, widget_key: str, default_value: bool = False) -> bool:
    secs = _ensure_batch_selection_state()
    selected = st.checkbox(
        label,
        value=bool(secs.get(selection_key, default_value)),
        key=widget_key,
        label_visibility="collapsed",
        on_change=_on_batch_selection_change,
        args=(selection_key, widget_key),
    )
    secs[selection_key] = bool(selected)
    return bool(selected)


def _is_manual_batch_selection() -> bool:
    return _get_batch_run_mode() == BATCH_RUN_MODE_MANUAL


def _build_auto_batch_queue(secs: dict) -> list[str]:
    queue = []
    aktif_prompt_kaynagi = _get_prompt_runtime_source_mode()
    prompt_source = _resolve_video_prompt_source_for_generation()
    gorsel_motion_prompt_aktif = secs.get("gorsel_olustur", False) and prompt_source.get("kind") == "gorsel_motion"
    video_klonla_secili = secs.get("video_klonla", False)
    bolum_plani_var = bool(globals().get("_has_video_bolum_link_plans", lambda: False)())
    if secs.get("video_indir", False) and _count_prompt_links() > 0 and (aktif_prompt_kaynagi == PROMPT_SOURCE_LINK or bolum_plani_var):
        queue.append("download")
    if secs.get("gorsel_analiz", False):
        queue.append("gorsel_analiz")
    if secs.get("gorsel_klonla", False):
        queue.append("gorsel_klonlama")
    if secs.get("gorsel_olustur", False):
        queue.append("gorsel_olustur")

    if video_klonla_secili:
        queue.append("video_klonla")
    else:
        skip_analyze = gorsel_motion_prompt_aktif
        if not skip_analyze:
            queue.append("analyze")
            if secs.get("prompt_duzeltme", False):
                queue.append("prompt_duzeltme")
        queue.append("pixverse")
    if secs.get("video_montaj", False):
        queue.append("video_montaj")
    if secs.get("toplu_video", False):
        queue.append("toplu_video")
    if secs.get("sosyal_medya", False):
        queue.append("sosyal_medya")
    return queue


def _build_manual_batch_queue(secs: dict) -> list[str]:
    _ensure_batch_selection_state()
    queue = []
    for selection_key in st.session_state.get("batch_manual_selection_order", []):
        if not secs.get(selection_key, False):
            continue
        node_key = BATCH_SELECTION_QUEUE_MAP.get(selection_key)
        if node_key and node_key not in queue:
            queue.append(node_key)
    return queue


def _manual_batch_order_text() -> str:
    secs = _ensure_batch_selection_state()
    labels = []
    for selection_key in st.session_state.get("batch_manual_selection_order", []):
        if not secs.get(selection_key, False):
            continue
        if selection_key == "pixverse":
            labels.append(get_video_generation_label(emoji=False))
        else:
            labels.append(BATCH_SELECTION_LABELS.get(selection_key, selection_key))
    return " → ".join(labels)


_ensure_batch_selection_state()
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
if "panel_shutdown_requested" not in st.session_state: st.session_state.panel_shutdown_requested = False

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
if "toplu_video_production_limit" not in st.session_state: st.session_state.toplu_video_production_limit = 0
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
if "video_bolum_source_kind" not in st.session_state: st.session_state.video_bolum_source_kind = "file"
if "video_bolum_source_no" not in st.session_state: st.session_state.video_bolum_source_no = None
if "video_bolum_source_url" not in st.session_state: st.session_state.video_bolum_source_url = ""
if "video_bolum_source_title" not in st.session_state: st.session_state.video_bolum_source_title = ""
if "video_bolum_source_duration" not in st.session_state: st.session_state.video_bolum_source_duration = 0.0
if "video_bolum_preview_url" not in st.session_state: st.session_state.video_bolum_preview_url = ""
if "video_bolum_saved_notice" not in st.session_state: st.session_state.video_bolum_saved_notice = None
if "video_bolum_duzen_modu" not in st.session_state: st.session_state.video_bolum_duzen_modu = "Otomatik"
if "pixverse_prompt_override_meta" not in st.session_state: st.session_state.pixverse_prompt_override_meta = None
if "go_mode_val" not in st.session_state: st.session_state["go_mode_val"] = "Görsel"
if "go_motion_prompt_saved" not in st.session_state: st.session_state["go_motion_prompt_saved"] = False
if "video_klonla_saved" not in st.session_state: st.session_state["video_klonla_saved"] = False
if "video_klonla_mode_val" not in st.session_state: st.session_state["video_klonla_mode_val"] = "Video"
if "video_klonla_model_val" not in st.session_state: st.session_state["video_klonla_model_val"] = "Motion Control"
if "video_klonla_system_images" not in st.session_state: st.session_state["video_klonla_system_images"] = True

GORSEL_HAREKET_PROMPT_DIR = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Hareklendirme Prompt"
GORSEL_HAREKET_REFERANS_DIR = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görseller"
GORSEL_OLUSTUR_STATE_PATH = os.path.join(CONTROL_DIR, "gorsel_olustur_state.json")

def _load_transition_ui_state() -> dict:
    return _load_transition_state_file(CONTROL_DIR)


def _save_transition_ui_state(updates: dict | None = None) -> dict:
    return _save_transition_state_file(CONTROL_DIR, updates or {})


def _is_video_transition_mode() -> bool:
    return _is_video_transition_enabled_file(CONTROL_DIR)


def _is_section_transition_mode(section_key: str) -> bool:
    return bool(_load_transition_ui_state().get(section_key, False))


def _video_mode_option_label(mode_value: str | None) -> str:
    return "Start End Frame (Transition)" if _normalize_transition_video_mode(mode_value) == "transition" else "Normal Video"


def _video_mode_option_value(option_label: str) -> str:
    raw = str(option_label or "").casefold()
    return "transition" if "transition" in raw or "start end" in raw else "normal"


def _get_video_generation_mode_text() -> str:
    return "Transition Video" if _is_video_transition_mode() else "Video"


def _video_klonla_default_state() -> dict:
    return {
        "mode": "Video",
        "clone_model": "Motion Control",
        "modify_prompt": "",
        "selected_videos": [],
        "uploaded_videos": [],
        "selected_image": "",
        "uploaded_image": "",
        "use_system_images": True,
        "system_image_sources": ["gorsel_analiz", "gorsel_klonla", "gorsel_olustur"],
        "motion_model": "v5.6",
        "motion_quality": "720p",
        "modify_model": "v5.5",
        "modify_quality": "720p",
        "modify_keyframe_time": 0,
        "tasks": {},
    }


def _load_video_klonla_state() -> dict:
    state = _video_klonla_default_state()
    try:
        if os.path.exists(VIDEO_KLONLA_CONTROL_PATH):
            with open(VIDEO_KLONLA_CONTROL_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                state.update(data)
    except Exception:
        pass
    if not isinstance(state.get("tasks"), dict):
        state["tasks"] = {}
    return state


def _save_video_klonla_state(data: dict):
    state = _video_klonla_default_state()
    if isinstance(data, dict):
        state.update(data)
    try:
        with open(VIDEO_KLONLA_CONTROL_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"[WARN] Video Klonla durumu kaydedilemedi: {e}")


def _video_klonla_upload_root(kind: str) -> str:
    root = os.path.join(VIDEO_KLONLA_UPLOAD_DIR, kind)
    os.makedirs(root, exist_ok=True)
    return root


def _video_klonla_safe_name(name: str) -> str:
    base = os.path.basename(str(name or "").strip())
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base) or f"file_{int(time.time())}"


def _video_klonla_persist_uploaded_files(uploaded_files, kind: str) -> list[str]:
    saved = []
    if not uploaded_files:
        return saved
    if not isinstance(uploaded_files, (list, tuple)):
        uploaded_files = [uploaded_files]
    root = _video_klonla_upload_root(kind)
    for uf in uploaded_files:
        if uf is None:
            continue
        try:
            safe = _video_klonla_safe_name(getattr(uf, "name", "upload.bin"))
            stem, ext = os.path.splitext(safe)
            target = os.path.join(root, safe)
            sayac = 1
            while os.path.exists(target):
                target = os.path.join(root, f"{stem}_{sayac}{ext}")
                sayac += 1
            with open(target, "wb") as f:
                f.write(uf.getbuffer())
            saved.append(target)
        except Exception as e:
            log(f"[WARN] Video Klonla yüklenen dosya kaydedilemedi: {e}")
    return saved


def _video_klonla_clear_uploads():
    try:
        shutil.rmtree(VIDEO_KLONLA_UPLOAD_DIR, ignore_errors=True)
    except Exception:
        pass


def _video_klonla_existing_paths(paths) -> list[str]:
    out = []
    for p in (paths or []):
        p = str(p or "").strip()
        if p and os.path.exists(p):
            out.append(p)
    return out


def _video_klonla_tasks_dict(state: dict | None) -> dict:
    tasks = (state or {}).get("tasks")
    return tasks if isinstance(tasks, dict) else {}


def _video_klonla_task_key(source_group: str, item_no: int) -> str:
    safe_source = re.sub(r"[^a-z0-9]+", "_", str(source_group or "item").lower()).strip("_") or "item"
    try:
        safe_no = int(item_no or 0)
    except Exception:
        safe_no = 0
    return f"{safe_source}_{safe_no}" if safe_no > 0 else safe_source


def _video_klonla_saved_direct_video_paths(state: dict) -> list[str]:
    direct_paths = _video_klonla_existing_paths((state or {}).get("uploaded_videos"))
    direct_paths += _video_klonla_existing_paths((state or {}).get("selected_videos"))
    return list(dict.fromkeys(p for p in direct_paths if p))


def _video_klonla_local_sort_key(value: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", str(value or ""))]


def _video_klonla_scan_video_entries(root_path: str, source_kind: str = "") -> list[dict]:
    valid_exts = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")
    if not root_path or not os.path.isdir(root_path):
        return []
    try:
        folders = [name for name in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, name))]
    except Exception:
        return []
    folders.sort(key=_video_klonla_local_sort_key)
    out = []
    for idx, folder_name in enumerate(folders, start=1):
        folder_path = os.path.join(root_path, folder_name)
        try:
            videos = [
                name for name in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, name)) and name.lower().endswith(valid_exts)
            ]
        except Exception:
            videos = []
        if not videos:
            continue
        videos.sort(key=_video_klonla_local_sort_key)
        video_name = videos[0]
        match = re.search(r"(\d+)\s*$", folder_name)
        item_no = int(match.group(1)) if match else idx
        out.append({
            "no": item_no,
            "folder_name": folder_name,
            "folder_path": folder_path,
            "video_name": video_name,
            "video_path": os.path.join(folder_path, video_name),
            "source_kind": source_kind,
        })
    return out


def _video_klonla_safe_added_entries() -> list[dict]:
    for fn_name in ("_list_added_video_preview_entries", "_list_added_video_entries"):
        added_fn = globals().get(fn_name)
        if callable(added_fn):
            try:
                return added_fn()
            except Exception:
                pass
    added_root = str((st.session_state.get("settings", {}) or {}).get("added_video_dir") or r"C:\Users\User\Desktop\Otomasyon\Eklenen Video").strip()
    return _video_klonla_scan_video_entries(added_root, "added_video")


def _video_klonla_safe_download_entries() -> list[dict]:
    download_fn = globals().get("_list_download_video_entries")
    if callable(download_fn):
        try:
            return download_fn()
        except Exception:
            pass
    download_root = str((st.session_state.get("settings", {}) or {}).get("download_dir") or r"C:\Users\User\Desktop\Otomasyon\İndirilen Video").strip()
    return _video_klonla_scan_video_entries(download_root, "download")


def _video_klonla_safe_link_source_map() -> dict[int, str]:
    source_map_fn = globals().get("sosyal_medya_link_kaynak_haritasi")
    if callable(source_map_fn):
        try:
            return source_map_fn()
        except Exception:
            pass

    settings_obj = st.session_state.get("settings", {}) or {}
    links_file = str(settings_obj.get("links_file") or "").strip()
    link_count = 0
    if links_file and os.path.exists(links_file):
        try:
            with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
                link_count = len([line for line in f.read().splitlines() if line.strip()])
        except Exception:
            link_count = 0

    placeholder_active_fn = globals().get("_empty_source_placeholder_active")
    if callable(placeholder_active_fn):
        try:
            placeholder_active = bool(placeholder_active_fn())
        except Exception:
            placeholder_active = False
    else:
        placeholder_file = globals().get(
            "EMPTY_SOURCE_PLACEHOLDER_FILE",
            os.path.join(CONTROL_DIR, "empty_source_placeholder.json"),
        )
        placeholder_active = bool(placeholder_file and os.path.exists(str(placeholder_file)))

    if link_count == 0 and placeholder_active:
        return {1: "placeholder_link"}

    source_map = {idx: "Link" for idx in range(1, link_count + 1)}
    for entry in _video_klonla_safe_download_entries():
        try:
            item_no = int(entry.get("no") or 0)
        except Exception:
            item_no = 0
        if item_no > 0:
            source_map[item_no] = "İndirilen Video"
    return dict(sorted(source_map.items()))


def _video_klonla_safe_prompt_runtime_source_mode() -> str:
    runtime_mode_fn = globals().get("_get_prompt_runtime_source_mode")
    if callable(runtime_mode_fn):
        try:
            return runtime_mode_fn()
        except Exception:
            pass

    settings_obj = st.session_state.get("settings", {}) or {}
    mode_path = os.path.join(CONTROL_DIR, "prompt_source_mode.txt")
    file_mode = "auto"
    try:
        if os.path.exists(mode_path):
            with open(mode_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_mode = str(f.read() or "").strip().lower()
            if raw_mode in {"link", "youtube", "manual"}:
                file_mode = "link"
            elif raw_mode in {"added_video", "video", "eklenen_video", "eklenen video"}:
                file_mode = "added_video"
            elif raw_mode in {"downloaded_video", "download", "indirilen_video", "indirilen video"}:
                file_mode = "downloaded_video"
    except Exception:
        file_mode = "auto"

    links_file = str(settings_obj.get("links_file") or "").strip()
    link_count = 0
    if links_file and os.path.exists(links_file):
        try:
            with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
                link_count = len([line for line in f.read().splitlines() if line.strip()])
        except Exception:
            link_count = 0
    added_count = len(_video_klonla_safe_added_entries())
    download_count = len(_video_klonla_safe_download_entries())

    if file_mode == "added_video":
        return "added_video"
    if download_count > 0:
        return "downloaded_video"
    if link_count > 0:
        return "link"
    if added_count > 0:
        return "added_video"
    return file_mode


def _video_klonla_build_task_targets(uploaded_files=None, saved_paths=None) -> list[dict]:
    targets = []

    if uploaded_files:
        if not isinstance(uploaded_files, (list, tuple)):
            uploaded_files = [uploaded_files]
        for idx, raw in enumerate(uploaded_files, start=1):
            file_name = str(getattr(raw, "name", "") or f"Yüklenen Video {idx}").strip()
            targets.append({
                "key": _video_klonla_task_key("direct_video", idx),
                "no": idx,
                "order": idx,
                "label": f"Yüklenen Video {idx}",
                "source_group": "direct_video",
                "source_label": "Yüklenen Video",
                "source_kind": "direct_video",
                "video_path": "",
                "video_name": file_name,
            })
        return targets

    direct_paths = list(dict.fromkeys(p for p in (saved_paths or []) if p))
    if direct_paths:
        for idx, path in enumerate(direct_paths, start=1):
            targets.append({
                "key": _video_klonla_task_key("direct_video", idx),
                "no": idx,
                "order": idx,
                "label": f"Video {idx}",
                "source_group": "direct_video",
                "source_label": "Video",
                "source_kind": "direct_video",
                "video_path": path,
                "video_name": os.path.basename(path),
            })
        return targets

    mode = _video_klonla_safe_prompt_runtime_source_mode()

    if mode == "added_video":
        for idx, entry in enumerate(_video_klonla_safe_added_entries(), start=1):
            try:
                item_no = int(entry.get("no") or idx)
            except Exception:
                item_no = idx
            targets.append({
                "key": _video_klonla_task_key("added_video", item_no),
                "no": item_no,
                "order": idx,
                "label": f"Eklenen Video {item_no}",
                "source_group": "added_video",
                "source_label": "Eklenen Video",
                "source_kind": "added_video",
                "video_path": str(entry.get("video_path") or "").strip(),
                "video_name": str(entry.get("video_name") or "").strip(),
            })
        return targets

    link_map = _video_klonla_safe_link_source_map()
    if mode in {"link", "downloaded_video"} and link_map:
        download_by_no = {}
        for entry in _video_klonla_safe_download_entries():
            try:
                item_no = int(entry.get("no") or 0)
            except Exception:
                item_no = 0
            if item_no > 0:
                download_by_no[item_no] = str(entry.get("video_path") or "").strip()
        for order, item_no in enumerate(sorted(link_map), start=1):
            source_marker = str(link_map.get(item_no) or "").strip()
            is_placeholder_link = source_marker == "placeholder_link"
            label_prefix = "İndirilen Video" if source_marker == "İndirilen Video" else "Link"
            targets.append({
                "key": _video_klonla_task_key("prompt_source", item_no),
                "no": item_no,
                "order": order,
                "label": "Kaynak Bekleniyor" if is_placeholder_link else f"{label_prefix} {item_no}",
                "source_group": "prompt_source",
                "source_label": "Kaynak Bekleniyor" if is_placeholder_link else label_prefix,
                "source_kind": "downloaded_video" if download_by_no.get(item_no) else ("placeholder_link" if is_placeholder_link else "link"),
                "video_path": download_by_no.get(item_no, ""),
                "video_name": os.path.basename(download_by_no.get(item_no, "")) if download_by_no.get(item_no) else "",
                "placeholder": is_placeholder_link,
            })
        return targets

    if mode != "auto":
        return targets

    for idx, entry in enumerate(_list_video_klonla_source_videos(), start=1):
        label = str(entry.get("label") or f"Video {idx}").strip() or f"Video {idx}"
        targets.append({
            "key": _video_klonla_task_key(str(entry.get("source") or "video"), idx),
            "no": idx,
            "order": idx,
            "label": label,
            "source_group": str(entry.get("source") or "video"),
            "source_label": label,
            "source_kind": str(entry.get("source") or "video"),
            "video_path": str(entry.get("path") or "").strip(),
            "video_name": os.path.basename(str(entry.get("path") or "").strip()),
        })
    return targets


def _video_klonla_resolve_task_state(state: dict, target: dict) -> dict:
    base = {
        "modify_prompt": str((state or {}).get("modify_prompt") or "").strip(),
        "selected_image": str((state or {}).get("selected_image") or "").strip(),
        "uploaded_image": str((state or {}).get("uploaded_image") or "").strip(),
        "use_system_images": bool((state or {}).get("use_system_images", True)),
    }
    task_key = str((target or {}).get("key") or "").strip()
    task_state = _video_klonla_tasks_dict(state).get(task_key)
    if isinstance(task_state, dict):
        if "modify_prompt" in task_state:
            base["modify_prompt"] = str(task_state.get("modify_prompt") or "").strip()
        if "selected_image" in task_state:
            base["selected_image"] = str(task_state.get("selected_image") or "").strip()
        if "uploaded_image" in task_state:
            base["uploaded_image"] = str(task_state.get("uploaded_image") or "").strip()
        if "use_system_images" in task_state:
            base["use_system_images"] = bool(task_state.get("use_system_images"))
    for image_key in ("selected_image", "uploaded_image"):
        image_path = str(base.get(image_key) or "").strip()
        base[image_key] = image_path if image_path and os.path.exists(image_path) else ""
    return base


def _video_klonla_is_active() -> bool:
    try:
        stt = st.session_state.get("status", {})
        active = {"running", "ok", "error", "partial", "paused"}
        return (
            st.session_state.get("single_step") == "video_klonla"
            or st.session_state.get("bg_node_key") == "video_klonla"
            or stt.get("video_klonla") in active
        )
    except Exception:
        return False


def _list_video_klonla_source_videos() -> list[dict]:
    items = []
    seen = set()
    try:
        for entry in _list_download_video_entries():
            path = str(entry.get("video_path") or "").strip()
            if path and path not in seen:
                seen.add(path)
                items.append({"label": f"📥 {(entry.get('folder_name') or os.path.basename(path))}", "path": path, "source": "download"})
    except Exception:
        pass
    try:
        added_dir = str(st.session_state.settings.get("added_video_dir") or "").strip()
        if added_dir and os.path.isdir(added_dir):
            for root, _, files in os.walk(added_dir):
                for fname in files:
                    if fname.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")):
                        path = os.path.join(root, fname)
                        if path not in seen:
                            seen.add(path)
                            items.append({"label": f"🎞️ {os.path.relpath(path, added_dir)}", "path": path, "source": "added"})
    except Exception:
        pass
    try:
        assets = _list_video_montaj_assets()
        for entry in assets.get("videos", []):
            path = str(entry.get("path") or "").strip()
            if path and os.path.exists(path) and path not in seen:
                seen.add(path)
                items.append({"label": f"🎬 {entry.get('label') or os.path.basename(path)}", "path": path, "source": entry.get("source_kind") or "video"})
    except Exception:
        pass
    return items


def _list_video_klonla_internal_images() -> list[dict]:
    out = []
    seen = set()
    image_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    source_title_map = {
        "gorsel_analiz": "Görsel Analiz",
        "gorsel_klonla": "Klon Görsel",
        "gorsel_olustur": "Görsel Oluştur",
    }
    source_counts = {k: 0 for k in source_title_map.keys()}
    targets = [
        ("gorsel_analiz", str(st.session_state.settings.get("gorsel_analiz_dir") or "")),
        ("gorsel_klonla", str(st.session_state.settings.get("klon_gorsel_dir") or "")),
        ("gorsel_olustur", str(st.session_state.settings.get("gorsel_olustur_dir") or "")),
    ]
    for source, root in targets:
        if not root or not os.path.isdir(root):
            continue
        try:
            local_paths = []
            for cur_root, _, files in os.walk(root):
                for fname in sorted(files):
                    if fname.lower().endswith(image_exts):
                        local_paths.append(os.path.join(cur_root, fname))
            local_paths.sort(key=lambda p: (_extract_numeric_hint(p), os.path.basename(p).casefold()))
            for path in local_paths:
                if path in seen:
                    continue
                seen.add(path)
                source_counts[source] += 1
                out.append({
                    "label": f"{source_title_map.get(source, source)} {source_counts[source]}",
                    "path": path,
                    "source": source,
                    "preview": path,
                })
        except Exception:
            pass
    return out


def _prioritize_video_klonla_internal_images(entries: list[dict], owner: str = "single") -> list[dict]:
    items = list(entries or [])
    if not items:
        return items
    if owner != "batch":
        base_priority = {"gorsel_klonla": 0, "gorsel_analiz": 1, "gorsel_olustur": 2}
        return sorted(
            items,
            key=lambda item: (
                base_priority.get(item.get("source"), 99),
                _extract_numeric_hint(item.get("path") or item.get("label")),
                str(item.get("label") or "").casefold(),
            ),
        )

    secs = st.session_state.get("ek_batch_secimler", {}) or {}
    source_priority = {"gorsel_klonla": 2, "gorsel_analiz": 3, "gorsel_olustur": 4}
    if secs.get("gorsel_klonla", False):
        source_priority["gorsel_klonla"] = 0
    if secs.get("gorsel_analiz", False) and not secs.get("gorsel_klonla", False):
        source_priority["gorsel_analiz"] = 0
    if secs.get("gorsel_olustur", False) and not secs.get("gorsel_klonla", False) and not secs.get("gorsel_analiz", False):
        source_priority["gorsel_olustur"] = 0

    return sorted(
        items,
        key=lambda item: (
            source_priority.get(item.get("source"), 99),
            _extract_numeric_hint(item.get("path") or item.get("label")),
            str(item.get("label") or "").casefold(),
        ),
    )


def _extract_numeric_hint(text_value: str) -> int:
    m = re.search(r"(\d+)", str(text_value or ''))
    return int(m.group(1)) if m else 0


def _video_klonla_target_no(target: dict | None) -> int:
    try:
        target_no = int((target or {}).get("no") or 0)
    except Exception:
        target_no = 0
    if target_no > 0:
        return target_no
    return _extract_numeric_hint((target or {}).get("label") or (target or {}).get("video_path") or "")


def _video_klonla_batch_planned_image_info(target: dict | None, owner: str = "batch") -> dict | None:
    if owner != "batch":
        return None

    item_no = _video_klonla_target_no(target)
    if item_no <= 0:
        return None

    secs = st.session_state.get("ek_batch_secimler", {}) or {}
    settings_obj = st.session_state.get("settings", {}) or {}
    gorsel_duzelt_data = gorsel_duzelt_oku() if "gorsel_duzelt_oku" in globals() else {}
    get_ga_folders = globals().get("get_gorsel_analiz_klasorleri")
    get_go_refs = globals().get("_list_gorsel_olustur_reference_image_entries")
    gkl_source = str(settings_obj.get("gorsel_klonla_kaynak", "gorsel_analiz") or "gorsel_analiz").strip()

    if secs.get("gorsel_klonla", False):
        prompt_ok = _gorsel_klon_prompt_has_value(
            gorsel_duzelt_data.get(item_no),
            require_transition_pair=_is_section_transition_mode("gorsel_klonla_transition_enabled"),
        )
        if gkl_source == "gorsel_olustur":
            source_ready = bool(secs.get("gorsel_olustur", False) or (callable(get_go_refs) and get_go_refs()))
            source_label = f"Görsel Oluştur {item_no}"
        else:
            source_ready = bool(secs.get("gorsel_analiz", False) or (callable(get_ga_folders) and get_ga_folders()))
            source_label = f"Görsel Analiz {item_no}"
        if prompt_ok and source_ready:
            return {
                "available": True,
                "planned": True,
                "path": "",
                "label": f"Görsel {item_no}",
                "source": "gorsel_klonla",
                "detail": f"Batch sırasında önce {source_label} hazırlanacak, ardından Klon Görsel {item_no} kullanılacak.",
                "expected_source_label": f"Klon Görsel {item_no}",
                "image_no": item_no,
            }

    if secs.get("gorsel_analiz", False):
        return {
            "available": True,
            "planned": True,
            "path": "",
            "label": f"Görsel {item_no}",
            "source": "gorsel_analiz",
            "detail": f"Batch sırasında Görsel Analiz {item_no} oluşturulacak ve bu görevde kullanılacak.",
            "expected_source_label": f"Görsel Analiz {item_no}",
            "image_no": item_no,
        }

    if secs.get("gorsel_olustur", False):
        return {
            "available": True,
            "planned": True,
            "path": "",
            "label": f"Görsel {item_no}",
            "source": "gorsel_olustur",
            "detail": f"Batch sırasında Görsel Oluştur {item_no} hazırlanacak ve bu görevde kullanılacak.",
            "expected_source_label": f"Görsel Oluştur {item_no}",
            "image_no": item_no,
        }

    return None


def _video_klonla_resolve_system_image_info(
    target: dict | None,
    selected_image: str,
    internal_images: list[dict],
    owner: str = "single",
) -> dict:
    item_no = _video_klonla_target_no(target)
    actual_path = _pick_image_for_video(
        str((target or {}).get("video_path") or "").strip(),
        selected_image,
        internal_images,
        item_no,
    )
    if actual_path:
        matched = next((item for item in internal_images if str(item.get("path") or "").strip() == actual_path), None)
        return {
            "available": True,
            "planned": False,
            "path": actual_path,
            "label": str((matched or {}).get("label") or os.path.basename(actual_path)).strip(),
            "source": str((matched or {}).get("source") or "").strip(),
            "detail": "",
            "expected_source_label": str((matched or {}).get("label") or os.path.basename(actual_path)).strip(),
            "image_no": item_no,
        }

    planned_info = _video_klonla_batch_planned_image_info(target, owner=owner)
    if planned_info:
        return planned_info

    return {
        "available": False,
        "planned": False,
        "path": "",
        "label": f"Görsel {item_no}" if item_no > 0 else "Görsel",
        "source": "",
        "detail": "",
        "expected_source_label": "",
        "image_no": item_no,
    }


def _pick_image_for_video(video_path: str, selected_image: str, internal_images: list[dict], item_no: int | None = None) -> str:
    if selected_image and os.path.exists(selected_image):
        return selected_image
    if not internal_images:
        return ""
    try:
        hint = int(item_no or 0)
    except Exception:
        hint = 0
    if hint <= 0:
        hint = _extract_numeric_hint(video_path)
    if hint > 0:
        for item in internal_images:
            if _extract_numeric_hint(item.get("label") or item.get("path")) == hint:
                return item.get("path") or ""
    return internal_images[0].get("path") or ""


def _video_klonla_target_has_saved_config(state: dict, target: dict, internal_images: list[dict]) -> bool:
    clone_model = str((state or {}).get("clone_model") or "Motion Control")
    task_state = _video_klonla_resolve_task_state(state, target)
    return _video_klonla_target_has_config_for_model(clone_model, task_state, target, internal_images)


def _video_klonla_target_has_config_for_model(clone_model: str, task_state: dict, target: dict, internal_images: list[dict]) -> bool:
    if clone_model == "Modify":
        return bool(str(task_state.get("modify_prompt") or "").strip())
    if task_state.get("uploaded_image"):
        return True
    if task_state.get("use_system_images"):
        owner = "batch" if any((st.session_state.get("ek_batch_secimler", {}) or {}).get(k, False) for k in ("gorsel_analiz", "gorsel_klonla", "gorsel_olustur", "video_klonla")) else "single"
        return bool(
            _video_klonla_resolve_system_image_info(
                target,
                str(task_state.get("selected_image") or "").strip(),
                internal_images,
                owner=owner,
            ).get("available")
        )
    return False


def _video_klonla_saved_task_count(state: dict | None = None, owner: str = "batch") -> int:
    state = state or _load_video_klonla_state()
    targets = _video_klonla_build_task_targets(saved_paths=_video_klonla_saved_direct_video_paths(state))
    if not targets:
        clone_model = str(state.get("clone_model") or "Motion Control")
        if clone_model == "Modify":
            return 1 if str(state.get("modify_prompt") or "").strip() else 0
        internal_images = _prioritize_video_klonla_internal_images(_list_video_klonla_internal_images(), owner)
        if str(state.get("uploaded_image") or "").strip() and os.path.exists(str(state.get("uploaded_image") or "").strip()):
            return 1
        if bool(state.get("use_system_images", True)) and internal_images:
            return 1
        return 0

    internal_images = _prioritize_video_klonla_internal_images(_list_video_klonla_internal_images(), owner)
    return sum(1 for target in targets if _video_klonla_target_has_saved_config(state, target, internal_images))


def _collect_video_klonla_runtime_items(owner: str = "single") -> list[dict]:
    state = _load_video_klonla_state()
    items = []
    task_targets = _video_klonla_build_task_targets(saved_paths=_video_klonla_saved_direct_video_paths(state))
    internal_images = _list_video_klonla_internal_images()
    internal_images = _prioritize_video_klonla_internal_images(internal_images, owner)

    for target in task_targets:
        video_path = str(target.get("video_path") or "").strip()
        if not video_path or not os.path.exists(video_path):
            continue
        task_state = _video_klonla_resolve_task_state(state, target)
        if state.get("clone_model") == "Modify":
            prompt = str(task_state.get("modify_prompt") or "").strip()
            if not prompt:
                continue
            items.append({
                "name": str(target.get("label") or os.path.basename(video_path)).strip(),
                "video": video_path,
                "prompt": prompt,
                "model": state.get("modify_model", "v5.5"),
                "quality": state.get("modify_quality", "720p"),
                "keyframe_time": int(state.get("modify_keyframe_time") or 0),
            })
        else:
            image_path = str(task_state.get("uploaded_image") or "").strip()
            if not image_path and task_state.get("use_system_images"):
                image_path = _pick_image_for_video(
                    video_path,
                    str(task_state.get("selected_image") or "").strip(),
                    internal_images,
                    target.get("no"),
                )
            if not image_path:
                continue
            items.append({
                "name": str(target.get("label") or os.path.basename(video_path)).strip(),
                "video": video_path,
                "image": image_path,
                "model": state.get("motion_model", "v5.6"),
                "quality": state.get("motion_quality", "720p"),
            })
    return items


def _video_klonla_has_valid_saved_config() -> bool:
    state = _load_video_klonla_state()
    clone_model = str(state.get("clone_model") or "Motion Control")
    task_targets = _video_klonla_build_task_targets(saved_paths=_video_klonla_saved_direct_video_paths(state))
    internal_images = _prioritize_video_klonla_internal_images(_list_video_klonla_internal_images(), "batch")

    if task_targets:
        return any(_video_klonla_target_has_saved_config(state, target, internal_images) for target in task_targets)

    if clone_model == "Modify":
        return bool(str(state.get("modify_prompt") or "").strip())

    uploaded_image = str(state.get("uploaded_image") or "").strip()
    if uploaded_image and os.path.exists(uploaded_image):
        return True

    if state.get("use_system_images", True):
        return bool(internal_images)
    return False


def _planned_video_klonla_output_count() -> int:
    runtime_items = _collect_video_klonla_runtime_items("batch")
    saved_count = _video_klonla_saved_task_count(owner="batch")
    return max(len(runtime_items), saved_count)


def _build_video_klonla_runtime(owner: str = "single") -> tuple[str, dict]:
    state = _load_video_klonla_state()
    items = _collect_video_klonla_runtime_items(owner)
    runtime = {
        "items": items,
        "output_root": str(st.session_state.settings.get("klon_video_dir") or st.session_state.settings.get("video_klonla_dir") or r"C:\Users\User\Desktop\Otomasyon\Klon Video"),
        "clone_model": state.get("clone_model", "Motion Control"),
        "owner": owner,
    }
    with open(VIDEO_KLONLA_RUNTIME_PATH, "w", encoding="utf-8") as f:
        json.dump(runtime, f, ensure_ascii=False, indent=2)
    return VIDEO_KLONLA_RUNTIME_PATH, runtime


def start_video_klonla_bg(owner: str = "single") -> bool:
    state = _load_video_klonla_state()
    clone_model = str(state.get("clone_model") or "Motion Control")
    script_path = (st.session_state.settings.get("video_klonla_motion_script") or MOTION_CONTROL_SCRIPT_DEFAULT) if clone_model == "Motion Control" else (st.session_state.settings.get("video_klonla_modify_script") or MODIFY_SCRIPT_DEFAULT)
    runtime_path, runtime = _build_video_klonla_runtime(owner)
    if not runtime.get("items"):
        st.session_state.status["video_klonla"] = "error"
        if clone_model == "Modify":
            log("[ERROR] Video Klonla için uygun video + prompt bulunamadı.")
        else:
            log("[ERROR] Video Klonla için uygun video + görsel bulunamadı.")
        return False
        log("[ERROR] Video Klonla için uygun video/görsel/prompt bulunamadı.")
        return False
    return bg_start(owner, "video_klonla", script_path, args=["--config", runtime_path])


def _normalize_gorsel_olustur_mode(value: str) -> str:
    raw = str(value or "").strip()
    low = raw.casefold()
    simplified = (
        low
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("?", "o")
    )
    simplified = re.sub(r"[^a-z]+", "", simplified)
    if simplified.startswith("video"):
        return "Video"
    if simplified.startswith("gorsel"):
        return "Görsel"
    return raw


def _load_gorsel_olustur_state() -> dict:
    state = {"mode": "", "motion_prompt_active": False}
    try:
        if os.path.exists(GORSEL_OLUSTUR_STATE_PATH):
            with open(GORSEL_OLUSTUR_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                mode = _normalize_gorsel_olustur_mode(data.get("mode"))
                if mode:
                    state["mode"] = mode
                state["motion_prompt_active"] = bool(data.get("motion_prompt_active", False))
    except Exception:
        pass
    return state


def _save_gorsel_olustur_state(mode: str, motion_prompt_active: bool):
    payload = {
        "mode": _normalize_gorsel_olustur_mode(mode),
        "motion_prompt_active": bool(motion_prompt_active),
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        os.makedirs(CONTROL_DIR, exist_ok=True)
        with open(GORSEL_OLUSTUR_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"[WARN] Görsel Oluştur durumu kaydedilemedi: {e}")


def _get_gorsel_motion_prompt_runtime_state() -> dict:
    disk_state = _load_gorsel_olustur_state()
    settings_obj = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    mode = _normalize_gorsel_olustur_mode(
        st.session_state.get("go_mode_val")
        or settings_obj.get("gorsel_olustur_mode")
        or disk_state.get("mode")
        or ""
    )
    motion_prompt_active = (
        bool(st.session_state.get("go_motion_prompt_saved", False))
        or bool(settings_obj.get("gorsel_motion_prompt_active", False))
        or bool(disk_state.get("motion_prompt_active", False))
    )
    return {
        "mode": mode,
        "motion_prompt_active": motion_prompt_active,
    }


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
    runtime_state = _get_gorsel_motion_prompt_runtime_state()
    return (
        bool(runtime_state.get("motion_prompt_active", False))
        and str(runtime_state.get("mode", "")).strip() == "Görsel"
        and _has_saved_gorsel_motion_prompts()
    )


def _count_standard_video_prompt_entries(prompt_dir: str | None = None) -> int:
    root = str(prompt_dir or st.session_state.get("settings", {}).get("prompt_dir", "") or "").strip()
    if not root or not os.path.isdir(root):
        return 0
    count = 0
    try:
        for name in os.listdir(root):
            folder_path = os.path.join(root, name)
            prompt_path = os.path.join(folder_path, "prompt.txt")
            if not (os.path.isdir(folder_path) and name.startswith("Video Prompt") and os.path.exists(prompt_path)):
                continue
            try:
                with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
                    if f.read().strip():
                        count += 1
            except Exception:
                continue
    except Exception:
        return 0
    return count


def _resolve_video_prompt_source_for_generation() -> dict:
    runtime_state = _get_gorsel_motion_prompt_runtime_state()
    motion_count = len(_list_saved_gorsel_motion_prompt_entries())
    standard_count = _count_standard_video_prompt_entries()
    mode = str(runtime_state.get("mode", "")).strip()
    motion_active = bool(runtime_state.get("motion_prompt_active", False))

    if motion_active and mode == "Görsel" and motion_count > 0:
        return {
            "kind": "gorsel_motion",
            "prompt_dir": GORSEL_HAREKET_PROMPT_DIR,
            "ref_image_dir": GORSEL_HAREKET_REFERANS_DIR,
            "reason": "state_active",
            "motion_count": motion_count,
            "standard_count": standard_count,
        }

    # Sağlam fallback: Görsel hareketlendirme promptları dolu, standart Prompt boşsa
    # modelden bağımsız olarak hareketlendirme klasörünü kullan.
    if motion_count > 0 and standard_count == 0 and mode != "Video":
        return {
            "kind": "gorsel_motion",
            "prompt_dir": GORSEL_HAREKET_PROMPT_DIR,
            "ref_image_dir": GORSEL_HAREKET_REFERANS_DIR,
            "reason": "fallback_motion_only",
            "motion_count": motion_count,
            "standard_count": standard_count,
        }

    return {
        "kind": "standard",
        "prompt_dir": str(st.session_state.get("settings", {}).get("prompt_dir", "") or "").strip(),
        "ref_image_dir": str(st.session_state.get("settings", {}).get("gorsel_klonlama_dir", "") or "").strip(),
        "reason": "standard_prompt",
        "motion_count": motion_count,
        "standard_count": standard_count,
    }


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
    if raw in ("Link", "Video", "🖼️ Görsel Oluştur", "🎞️ Video Ekle", "🎞️ Video Montaj", "🎬 Toplu Video Montaj", "🎬 Klon Video"):
        return raw
    if raw == "Video/Link":
        return "Link"

    low = raw.lower()
    if "görsel oluştur" in low or "gorsel olustur" in low:
        return "🖼️ Görsel Oluştur"
    if "toplu" in low and "montaj" in low:
        return "🎬 Toplu Video Montaj"
    if "klon" in low and "video" in low:
        return "🎬 Klon Video"
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
    if raw == "Klon Video":
        return "Klon Video"
    if "klon" in raw.lower():
        return "Klon Video"
    return "Mevcut Videolar"


def _toplu_video_uretim_limiti_normalize(value, max_value: int | None = None) -> int:
    try:
        cleaned = str(value or "").strip()
        if not cleaned:
            return 0
        number = int(float(cleaned.replace(",", ".")))
    except Exception:
        return 0
    if number <= 0:
        return 0
    if max_value is not None and max_value > 0:
        number = min(number, int(max_value))
    return max(1, number)


def clear_dialog_states():
    """Herhangi bir ana menü tuşuna basıldığında asılı kalmış diyalogları sıfırlar."""
    _reset_video_bolum_temp(remove_file=True)
    _reset_complex_dialog_lazy_state()
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

VIDEO_BOLUM_PLAN_FILE = os.path.join(CONTROL_DIR, "video_bolum_plan.json")
VIDEO_BOLUM_PREVIEW_CACHE_FILE = os.path.join(CONTROL_DIR, "video_bolum_preview_cache.json")


def _video_bolum_read_json(path: str, default):
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
    except Exception:
        pass
    return default


def _video_bolum_write_json(path: str, data) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception as e:
        try:
            log(f"[WARN] Video bolum plani yazilamadi: {e}")
        except Exception:
            pass
        return False


def _video_bolum_default_plan_state() -> dict:
    return {"items": []}


def _load_video_bolum_plan_state() -> dict:
    data = _video_bolum_read_json(VIDEO_BOLUM_PLAN_FILE, _video_bolum_default_plan_state())
    if not isinstance(data, dict):
        data = _video_bolum_default_plan_state()
    if not isinstance(data.get("items"), list):
        data["items"] = []
    data["items"] = [item for item in data["items"] if isinstance(item, dict)]
    return data


def _save_video_bolum_plan_state(state: dict) -> bool:
    if not isinstance(state, dict):
        state = _video_bolum_default_plan_state()
    if not isinstance(state.get("items"), list):
        state["items"] = []
    return _video_bolum_write_json(VIDEO_BOLUM_PLAN_FILE, state)


def _video_bolum_plan_key(source_no, url: str) -> str:
    try:
        no = int(source_no or 0)
    except Exception:
        no = 0
    return f"link:{no}:{str(url or '').strip()}"


def _normalize_video_bolum_segments(segments: list) -> list[list[float]]:
    out = []
    for item in segments or []:
        try:
            start, end = item
            start = round(float(start), 3)
            end = round(float(end), 3)
        except Exception:
            continue
        if end > start >= 0:
            out.append([start, end])
    return out


def _upsert_video_bolum_link_plan(plan: dict) -> bool:
    if not isinstance(plan, dict):
        return False
    segments = _normalize_video_bolum_segments(plan.get("segments") or [])
    if not segments:
        return False
    plan = dict(plan)
    plan["kind"] = "link"
    plan["segments"] = segments
    plan["key"] = _video_bolum_plan_key(plan.get("source_no"), plan.get("url"))
    plan["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    state = _load_video_bolum_plan_state()
    items = []
    replaced = False
    for item in state.get("items", []):
        if str(item.get("key") or "") == plan["key"]:
            previous = dict(item)
            previous.update(plan)
            for clear_key in ("applied_signature", "applied_outputs", "applied_at", "applied_count"):
                previous.pop(clear_key, None)
            items.append(previous)
            replaced = True
        else:
            items.append(item)
    if not replaced:
        items.append(plan)
    state["items"] = items
    return _save_video_bolum_plan_state(state)


def _video_bolum_plan_for_link(source_no, url: str) -> dict | None:
    key = _video_bolum_plan_key(source_no, url)
    for item in _load_video_bolum_plan_state().get("items", []):
        if str(item.get("key") or "") == key:
            return item
    return None


def _count_video_bolum_link_plans() -> int:
    return len([item for item in _load_video_bolum_plan_state().get("items", []) if item.get("kind") == "link"])


def _read_video_link_entries(path: str | None = None) -> list[dict]:
    settings_obj = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    links_file = str(path or settings_obj.get("links_file") or "").strip()
    if not links_file or not os.path.exists(links_file):
        return []
    try:
        with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
            raw_lines = [line.strip() for line in f.read().splitlines()]
    except Exception:
        return []

    entries = []
    for line in raw_lines:
        if not line or not line.lower().startswith(("http://", "https://")):
            continue
        no = len(entries) + 1
        entries.append({"no": no, "url": line, "label": f"Link Video {no}"})
    return entries


def _video_bolum_shorten_url(url: str, limit: int = 84) -> str:
    text = str(url or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(8, limit - 3)] + "..."


def _video_bolum_detect_platform(url: str) -> str:
    low = str(url or "").lower()
    if "youtube.com" in low or "youtu.be" in low:
        return "youtube"
    if "tiktok.com" in low or "vm.tiktok.com" in low:
        return "tiktok"
    if "instagram.com" in low:
        return "instagram"
    return "generic"


def _resolve_video_bolum_link_preview(url: str) -> dict:
    url = str(url or "").strip()
    fallback = {
        "ok": False,
        "url": url,
        "preview_url": url,
        "title": "",
        "duration": 0.0,
        "error": "",
    }
    if not url:
        fallback["error"] = "Link bos."
        return fallback

    cache = _video_bolum_read_json(VIDEO_BOLUM_PREVIEW_CACHE_FILE, {})
    if not isinstance(cache, dict):
        cache = {}
    cached = cache.get(url)
    try:
        cache_age = time.time() - float((cached or {}).get("cached_at") or 0)
    except Exception:
        cache_age = 999999
    if isinstance(cached, dict) and cached.get("preview_url") and cache_age < 2700:
        out = dict(fallback)
        out.update(cached)
        out["ok"] = bool(out.get("duration", 0) and out.get("preview_url"))
        return out

    try:
        import yt_dlp

        platform = _video_bolum_detect_platform(url)
        fmt = "best[ext=mp4][height<=720]/best[height<=720]/best"
        if platform != "youtube":
            fmt = "best[ext=mp4]/best"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "format": fmt,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if isinstance(info, dict) and isinstance(info.get("entries"), list) and info.get("entries"):
            info = info["entries"][0]
        if not isinstance(info, dict):
            raise RuntimeError("Video bilgisi okunamadi.")

        preview_url = str(info.get("url") or url).strip() or url
        title = str(info.get("title") or info.get("fulltitle") or "").strip()
        try:
            duration = float(info.get("duration") or 0.0)
        except Exception:
            duration = 0.0

        out = {
            "ok": bool(preview_url and duration > 0),
            "url": url,
            "preview_url": preview_url,
            "title": title,
            "duration": duration,
            "platform": platform,
            "cached_at": time.time(),
            "error": "" if duration > 0 else "Video suresi okunamadi.",
        }
        cache[url] = {k: v for k, v in out.items() if k != "ok"}
        _video_bolum_write_json(VIDEO_BOLUM_PREVIEW_CACHE_FILE, cache)
        return out
    except Exception as e:
        fallback["error"] = str(e)
        return fallback


def _video_bolum_added_dir() -> str:
    settings_obj = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    return str(settings_obj.get("added_video_dir") or r"C:\Users\User\Desktop\Otomasyon\Eklenen Video").strip()


def _video_bolum_download_dir() -> str:
    settings_obj = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    return str(settings_obj.get("download_dir") or r"C:\Users\User\Desktop\Otomasyon\İndirilen Video").strip()


def _video_bolum_sort_key(value: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", str(value or ""))]


def _video_bolum_supported_name(name: str) -> bool:
    return str(name or "").lower().endswith((".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"))


def _video_bolum_scan_download_entries() -> list[dict]:
    fn = globals().get("_list_download_video_entries")
    if callable(fn):
        try:
            return list(fn() or [])
        except Exception:
            pass

    root = _video_bolum_download_dir()
    if not root or not os.path.isdir(root):
        return []
    out = []
    try:
        folders = [name for name in os.listdir(root) if os.path.isdir(os.path.join(root, name))]
    except Exception:
        return []
    folders.sort(key=_video_bolum_sort_key)
    for idx, folder_name in enumerate(folders, start=1):
        folder_path = os.path.join(root, folder_name)
        try:
            videos = [name for name in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, name)) and _video_bolum_supported_name(name)]
        except Exception:
            videos = []
        if not videos:
            continue
        videos.sort(key=_video_bolum_sort_key)
        match = re.search(r"(\d+)\s*$", folder_name)
        no = int(match.group(1)) if match else idx
        out.append({
            "no": no,
            "folder_name": folder_name,
            "folder_path": folder_path,
            "video_name": videos[0],
            "video_path": os.path.join(folder_path, videos[0]),
            "source_kind": "download",
        })
    return out


def _video_bolum_download_by_no() -> dict[int, dict]:
    out = {}
    for entry in _video_bolum_scan_download_entries():
        try:
            no = int(entry.get("no") or 0)
        except Exception:
            no = 0
        path = str(entry.get("video_path") or "").strip()
        if no > 0 and path and os.path.isfile(path):
            out[no] = entry
    return out


def _video_bolum_format_seconds(seconds: float) -> str:
    try:
        value = max(0.0, float(seconds))
    except Exception:
        value = 0.0
    return f"{value:.3f}"


def _video_bolum_split_to_added(video_path: str, segments: list, output_dir: str, start_no: int = 1) -> list[dict]:
    results = []
    ext = os.path.splitext(video_path)[1] or ".mp4"
    for idx, (start, end) in enumerate(_normalize_video_bolum_segments(segments)):
        video_no = int(start_no) + idx
        folder = os.path.join(output_dir, f"Video {video_no}")
        os.makedirs(folder, exist_ok=True)
        out_path = os.path.join(folder, f"bolum_{video_no}{ext}")
        duration = max(0.0, float(end) - float(start))
        try:
            completed = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-ss", _video_bolum_format_seconds(start),
                    "-t", _video_bolum_format_seconds(duration),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k",
                    "-avoid_negative_ts", "make_zero",
                    "-movflags", "+faststart",
                    out_path,
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if completed.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
                results.append({"no": video_no, "folder": folder, "video": out_path})
            else:
                log(f"[WARN] Video bolum kesilemedi: Video {video_no}")
        except Exception as e:
            log(f"[WARN] Video bolum kesme hatasi: Video {video_no} -> {e}")
    return results


def _video_bolum_plan_signature(plan: dict, video_path: str) -> str:
    try:
        size = os.path.getsize(video_path)
        mtime = round(os.path.getmtime(video_path), 3)
    except Exception:
        size = 0
        mtime = 0
    segments = _normalize_video_bolum_segments(plan.get("segments") or [])
    return json.dumps(
        {
            "source_no": int(plan.get("source_no") or 0),
            "video_path": os.path.abspath(video_path),
            "size": size,
            "mtime": mtime,
            "segments": segments,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _video_bolum_outputs_exist(plan: dict) -> bool:
    outputs = plan.get("applied_outputs")
    if not isinstance(outputs, list) or not outputs:
        return False
    for output_path in outputs:
        if not output_path or not os.path.isfile(str(output_path)):
            return False
    return True


def _has_video_bolum_link_plans() -> bool:
    current_links = {int(item.get("no") or 0): str(item.get("url") or "").strip() for item in _read_video_link_entries()}
    for plan in _load_video_bolum_plan_state().get("items", []):
        if plan.get("kind") != "link":
            continue
        try:
            source_no = int(plan.get("source_no") or 0)
        except Exception:
            source_no = 0
        if not current_links or current_links.get(source_no) == str(plan.get("url") or "").strip():
            return True
    return False


def _get_active_video_bolum_link_plans() -> list[dict]:
    current_links = {int(item.get("no") or 0): str(item.get("url") or "").strip() for item in _read_video_link_entries()}
    out = []
    for plan in _load_video_bolum_plan_state().get("items", []):
        if plan.get("kind") != "link":
            continue
        try:
            source_no = int(plan.get("source_no") or 0)
        except Exception:
            source_no = 0
        url = str(plan.get("url") or "").strip()
        segments = _normalize_video_bolum_segments(plan.get("segments") or [])
        if source_no <= 0 or not url or not segments:
            continue
        if current_links and current_links.get(source_no) != url:
            continue
        item = dict(plan)
        item["segments"] = segments
        out.append(item)
    out.sort(key=lambda item: (int(item.get("source_no") or 0), str(item.get("url") or "").strip()))
    return out


def _list_planned_added_video_entries() -> list[dict]:
    items = []
    next_video_no = 1
    for plan in _get_active_video_bolum_link_plans():
        try:
            source_no = int(plan.get("source_no") or 0)
        except Exception:
            source_no = 0
        title = str(plan.get("title") or f"Link Video {source_no}").strip()
        for segment_idx, (start_sec, end_sec) in enumerate(plan.get("segments") or [], start=1):
            video_no = next_video_no
            next_video_no += 1
            items.append({
                "no": video_no,
                "folder_name": f"Video {video_no}",
                "folder_path": "",
                "video_name": f"Planlanan Bolum {segment_idx}",
                "video_path": "",
                "exists": False,
                "expected": True,
                "planned": True,
                "source_kind": "added_video_plan",
                "source_no": source_no,
                "source_title": title,
                "segment_no": segment_idx,
                "segment_start": float(start_sec),
                "segment_end": float(end_sec),
            })
    return items


def _list_added_video_preview_entries() -> list:
    actual_entries = _list_added_video_entries()
    if actual_entries:
        return actual_entries
    return _list_planned_added_video_entries()


def _has_pending_video_bolum_plans_needing_download() -> bool:
    state = _load_video_bolum_plan_state()
    download_by_no = _video_bolum_download_by_no()
    current_links = {int(item.get("no") or 0): str(item.get("url") or "").strip() for item in _read_video_link_entries()}
    for plan in state.get("items", []):
        if plan.get("kind") != "link":
            continue
        try:
            source_no = int(plan.get("source_no") or 0)
        except Exception:
            source_no = 0
        if current_links and current_links.get(source_no) != str(plan.get("url") or "").strip():
            continue
        if source_no > 0 and source_no not in download_by_no:
            return True
    return False


def _apply_saved_video_bolum_plans_after_download(owner: str = "batch") -> bool:
    state = _load_video_bolum_plan_state()
    plans = [plan for plan in state.get("items", []) if plan.get("kind") == "link" and _normalize_video_bolum_segments(plan.get("segments") or [])]
    if not plans:
        return False

    download_by_no = _video_bolum_download_by_no()
    current_links = {int(item.get("no") or 0): str(item.get("url") or "").strip() for item in _read_video_link_entries()}
    ready = []
    missing = []
    stale_keys = set()
    for plan in plans:
        try:
            source_no = int(plan.get("source_no") or 0)
        except Exception:
            source_no = 0
        if current_links and current_links.get(source_no) != str(plan.get("url") or "").strip():
            stale_keys.add(str(plan.get("key") or _video_bolum_plan_key(source_no, plan.get("url"))))
            continue
        entry = download_by_no.get(source_no)
        path = str((entry or {}).get("video_path") or "").strip()
        if source_no > 0 and path and os.path.isfile(path):
            ready.append((plan, entry, path))
        else:
            missing.append(source_no)

    if not ready:
        if stale_keys:
            state["items"] = [item for item in state.get("items", []) if str(item.get("key") or "") not in stale_keys]
            _save_video_bolum_plan_state(state)
        if missing:
            log("[WARN] Video bolum planlari var ama indirilen video bulunamadi: " + ", ".join(f"Video {n}" for n in missing if n))
        return False

    all_already_applied = True
    for plan, _entry, path in ready:
        signature = _video_bolum_plan_signature(plan, path)
        if plan.get("applied_signature") != signature or not _video_bolum_outputs_exist(plan):
            all_already_applied = False
            break

    if all_already_applied:
        try:
            writer = globals().get("_write_prompt_source_mode") or globals().get("_early_write_prompt_source_mode")
            if callable(writer):
                writer("added_video")
            st.session_state.link_canvas_source = "added_video"
        except Exception:
            pass
        log("[INFO] Kayitli video bolumleri zaten hazir; Eklenen Video kaynagi kullanilacak.")
        return False

    added_root = _video_bolum_added_dir()
    os.makedirs(added_root, exist_ok=True)
    try:
        for name in os.listdir(added_root):
            path = os.path.join(added_root, name)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except Exception:
                    pass
    except Exception as e:
        log(f"[WARN] Eklenen Video temizlenemedi: {e}")

    ready.sort(key=lambda item: int(item[0].get("source_no") or 0))
    next_no = 1
    applied_total = 0
    updated_by_key = {}
    log(f"[INFO] Kayitli video bolum planlari uygulanıyor: {len(ready)} kaynak")

    for plan, entry, video_path in ready:
        source_no = int(plan.get("source_no") or 0)
        segments = _normalize_video_bolum_segments(plan.get("segments") or [])
        results = _video_bolum_split_to_added(video_path, segments, added_root, start_no=next_no)
        next_no += len(results)
        applied_total += len(results)
        updated = dict(plan)
        updated["applied_signature"] = _video_bolum_plan_signature(plan, video_path)
        updated["applied_outputs"] = [item.get("video") for item in results if item.get("video")]
        updated["applied_count"] = len(results)
        updated["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        updated["download_video_path"] = video_path
        updated["download_video_no"] = source_no
        updated_by_key[str(plan.get("key") or _video_bolum_plan_key(source_no, plan.get("url")))] = updated
        log(f"[OK] Link Video {source_no}: {len(results)}/{len(segments)} bolum Eklenen Video'ya kaydedildi.")

    new_items = []
    for plan in state.get("items", []):
        key = str(plan.get("key") or "")
        if key in stale_keys:
            continue
        new_items.append(updated_by_key.get(key, plan))
    state["items"] = new_items
    _save_video_bolum_plan_state(state)

    if applied_total > 0:
        writer = globals().get("_write_prompt_source_mode") or globals().get("_early_write_prompt_source_mode")
        if callable(writer):
            writer("added_video")
        st.session_state.link_canvas_source = "added_video"
        st.session_state.status["input"] = "ok"
        clear_placeholder = globals().get("_clear_empty_source_placeholder")
        if callable(clear_placeholder):
            clear_placeholder()
        log(f"[OK] Video bolum planlari tamamlandi: {applied_total} bolum hazir.")
        return True

    log("[WARN] Video bolum planlari calisti ama bolum uretilemedi.")
    return False

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
        "gorsel_klonlama": [
            r'Promptlar\s+y[üu]klenemedi.*i[çc]in\s+i[şs]lem\s+durduruluyor',
            r'Giri[şs]\s+g[öo]rsel\s+klas[öo]r[üu]\s+bulunamad[iı]',
            r'Klas[öo]r\s+listelenemedi',
            r'Prompt\s+dosyas[iı]\s+bulunamad[iı]',
            r'Dosya\s+okunurken\s+hata\s+olu[şs]tu',
            r'PixVerse\s+CLI\s+bulunamad[iı]',
            r'PixVerse\s+kimlik\s+do[ğg]rulamas[iı]\s+gerekli',
            r'PixVerse\s+oturumu\s+do[ğg]rulanamad[iı]',
            r'Desteklenmeyen\s+g[öo]rsel\s+klonlama\s+modeli',
        ],
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
    "video_klonla": "Video Klonla",
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
    if node_key == "video_klonla":
        return "Video Klonlama"
    return _DURUM_ISLEM_ETIKETLERI.get(node_key, node_key)

def _normalize_hata_detay(raw_text: str) -> str:
    text = _strip_log_prefix(raw_text)
    text = re.sub(r'^[\s\-–—:;]+', '', text).strip()
    text = re.sub(r'^\[(ERROR|INFO|WARN|WARNING|DEBUG)\]\s*', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'^(HATA DURUMU|HATA|ERROR|SEBEP|DETAY|SONUÇ)\s*[:\-]?\s*', '', text, flags=re.IGNORECASE).strip()

    if text in {"{", "}", "{,", "},", "[]", "{}"}:
        return "BaÅŸarÄ±sÄ±z"

    m_json_error = re.search(r'"?error"?\s*:\s*"([^"]+)"', text, re.IGNORECASE)
    if m_json_error:
        text = m_json_error.group(1).strip()

    if re.search(r'"?code"?\s*:\s*"?(50043)"?', text, re.IGNORECASE):
        return "Kredi Yetersiz"

    m_missing_file = re.search(r'dosya\s+bulunamad[^:]*:\s*(.+)', text, re.IGNORECASE)
    if m_missing_file:
        missing_path = m_missing_file.group(1).strip().strip('"\'')
        missing_name = os.path.basename(missing_path.rstrip("\\/")) if missing_path else ""
        return f"Dosya Bulunamadı: {missing_name or missing_path}" if (missing_name or missing_path) else "Dosya Bulunamadı"

    if re.search(r'gerekli\s+komut\s+veya\s+dosya\s+bulunamad', text, re.IGNORECASE):
        return "Gerekli Komut veya Dosya Bulunamadı"

    m_image_limit = re.search(r'Image resolution\s+(\d+)x(\d+)\s+exceeds\s+limit\s+(\d+)x(\d+)', text, re.IGNORECASE)
    if m_image_limit:
        width, height, limit_w, limit_h = m_image_limit.groups()
        return f"Referans Gorsel Boyutu Cok Buyuk: {width}x{height} > {limit_w}x{limit_h}"

    m_access_timeout = re.search(r'Failed to access\s+"?([^"]+?)"?\s*:\s*Response timeout for\s*(\d+)ms', text, re.IGNORECASE)
    if m_access_timeout:
        image_path, timeout_ms = m_access_timeout.groups()
        image_name = os.path.basename(str(image_path).rstrip("\\/")) or str(image_path).strip()
        try:
            timeout_sn = max(1, int(timeout_ms) // 1000)
        except Exception:
            timeout_sn = 60
        return f"Referans Gorsel Yukleme Zaman Asimi: {image_name} ({timeout_sn} sn)"

    if re.search(r'all\s*credits?\s*have\s*been\s*used\s*up|purchase\s*credits|credits?.*used\s*up|50043\b', text, re.IGNORECASE):
        return "Kredi Yetersiz"

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
        (r'pixverse\s+cli\s+bulunamad[ıi]|pixverse.*komutu\s+bulunamad[ıi]', 'PixVerse CLI Bulunamadı'),
        (r'pixverse.*kimlik.*doğrulama|pixverse.*auth|oturum.*doğrulanamad[ıi]|login.*required', 'PixVerse Giriş Gerekli'),
        (r'desteklenmeyen\s+g[öo]rsel\s+klonlama\s+modeli|desteklenmeyen\s+g[öo]rsel\s+modeli|unsupported.*model', 'Desteklenmeyen Görsel Modeli'),
        (r'credits?.*insufficient|credit.*balance|kredi.*yetersiz|payment.*required|402\b', 'Kredi Yetersiz'),
        (r'chromedriver.*only supports chrome version|only supports chrome version|current browser version is|session not created: cannot connect to chrome|cannot connect to chrome', 'ChromeDriver Sürüm Uyumsuzluğu'),
        (r'chrome\s*ba[şs]lat[ıi]lamad[ıi]|taray[ıi]c[ıi].*ba[şs]lat[ıi]lamad[ıi]', 'Tarayıcı Başlatılamadı'),
        (r'zaman\s*a[sş][iı]m[iı]|timeout|timed?\s*out|deadline.*exceeded', 'Zaman Aşımı'),
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
        r'pixverse.*kimlik.*doğrulama|pixverse.*auth',
        r'oturum.*doğrulanamad[ıi]|login.*required',
        r'desteklenmeyen.*g[öo]rsel.*model',
        r'credits?.*insufficient|kredi.*yetersiz|payment.*required|402\b',
        r'deadline.*exceeded',
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
        if re.search(r'^\s*DETAY\s*:\s*[\{\[]?\s*$', clean, re.IGNORECASE) or clean.strip() in {"{", "}", "[", "]", "{}", "[]"}:
            continue
        if any(re.search(kalip, clean, re.IGNORECASE) for kalip in etiketli_hata_kaliplari):
            detay = _normalize_hata_detay(clean)
            if detay and detay != 'Başarısız' and not _is_separator_line(detay):
                return detay

    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        if _is_non_actionable_log_line(clean):
            continue
        if re.search(r'^\s*DETAY\s*:\s*[\{\[]?\s*$', clean, re.IGNORECASE) or clean.strip() in {"{", "}", "[", "]", "{}", "[]"}:
            continue
        if any(re.search(kalip, clean, re.IGNORECASE) for kalip in oncelikli_hata_kaliplari):
            detay = _normalize_hata_detay(clean)
            if detay and detay != 'Başarısız' and not _is_separator_line(detay):
                return detay

    for line in reversed(logs_snapshot or []):
        clean = _strip_log_prefix(line)
        if _is_non_actionable_log_line(clean):
            continue
        if re.search(r'^\s*DETAY\s*:\s*[\{\[]?\s*$', clean, re.IGNORECASE) or clean.strip() in {"{", "}", "[", "]", "{}", "[]"}:
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
    Dönüş: 'prompt' | 'credit' | 'timeout' | 'other'
    - 'prompt'  → Prompt çok uzun / karakter limiti aşıldı → Prompt Düzelt'e geri dön
    - 'credit'  → Kredi/kota yetersiz → doğrudan Video Üret'ten tekrar dene
    - 'timeout' → Video bekleme / indirme zaman aşımı → Video Üret'ten tekrar dene
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
        r'all\s*credits.*used\s*up|credits.*have.*been.*used|purchase\s*credits|50043\b',
        r'Yetersiz Video Üretme Kredisi|kredinizi yenileyin',
    ]
    TIMEOUT_KALIPLARI = [
        r'beklenen\s+s[üu]rede\s+olu[şs]turulamad[ıi]',
        r'polling\s+timed\s+out',
        r'task.*wait.*timeout',
        r'video\s+indirme\s+zaman\s+a[şs][ıi]m[ıi]',
        r'indirme.*\d+\s*saniye.*tamamlanamad[ıi]',
        r'zaman\s+a[şs][ıi]m[ıi]',
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
        for kalip in TIMEOUT_KALIPLARI:
            if re.search(kalip, clean, re.IGNORECASE):
                return "timeout"
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
        r'pixverse.*kimlik.*doğrulama|pixverse.*auth',
        r'oturum.*doğrulanamadı|login.*required',
        r'credits?.*insufficient|kredi.*yetersiz',
        r'task.*wait.*timeout|deadline.*exceeded|zaman.*aşımı',
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
    _remove_tree_if_exists(VIDEO_KLONLA_UPLOAD_DIR, ".control\\video_klonla_uploads")

    prompt_temp_upload_dir = _get_prompt_temp_upload_dir()
    _remove_tree_if_exists(prompt_temp_upload_dir, "Prompt Oluşturma\\temp_upload")

    temp_video_path = st.session_state.get("video_bolum_temp_path")
    if temp_video_path:
        try:
            if os.path.abspath(str(temp_video_path)).startswith(os.path.abspath(split_dir)):
                st.session_state.video_bolum_temp_path = None
                st.session_state.video_bolum_temp_name = None
                st.session_state.video_bolum_source_kind = "file"
                st.session_state.video_bolum_source_no = None
                st.session_state.video_bolum_source_url = ""
                st.session_state.video_bolum_source_title = ""
                st.session_state.video_bolum_source_duration = 0.0
                st.session_state.video_bolum_preview_url = ""
        except Exception:
            st.session_state.video_bolum_temp_path = None
            st.session_state.video_bolum_temp_name = None
            st.session_state.video_bolum_source_kind = "file"
            st.session_state.video_bolum_source_no = None
            st.session_state.video_bolum_source_url = ""
            st.session_state.video_bolum_source_title = ""
            st.session_state.video_bolum_source_duration = 0.0
            st.session_state.video_bolum_preview_url = ""

    return cleaned



def cleanup_state_files():
    try:
        files_cleaned = []
        # 1. State dosyaları
        for fpath, fname in [
            (STATE_FILE, "STATE.json"),
            (DONE_FILE, "DONE.json"),
            (FAILED_FILE, "FAILED.json"),
            (GORSEL_OLUSTUR_STATE_PATH, "gorsel_olustur_state.json"),
            (VIDEO_KLONLA_CONTROL_PATH, "video_klonla_state.json"),
            (VIDEO_KLONLA_RUNTIME_PATH, "video_klonla_runtime.json"),
            (VIDEO_BOLUM_PLAN_FILE, "video_bolum_plan.json"),
            (VIDEO_BOLUM_PREVIEW_CACHE_FILE, "video_bolum_preview_cache.json"),
        ]:
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

def _schedule_panel_process_shutdown(pid: int, delay_seconds: float = 1.5) -> bool:
    try:
        pid_int = int(pid)
    except Exception:
        return False

    if pid_int <= 0:
        return False

    try:
        if os.name == "nt":
            delay_ms = max(int(float(delay_seconds) * 1000), 1000)
            ps_cmd = (
                f"Start-Sleep -Milliseconds {delay_ms}; "
                f"taskkill /PID {pid_int} /T /F | Out-Null"
            )
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-WindowStyle",
                    "Hidden",
                    "-Command",
                    ps_cmd,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            wait_seconds = max(float(delay_seconds), 1.0)
            subprocess.Popen(
                ["/bin/sh", "-c", f"sleep {wait_seconds:.1f}; kill -TERM {pid_int}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        return True
    except Exception as e:
        log(f"[WARN] Panel kapatma zamanlanamadi: {e}")
        return False

def request_panel_shutdown() -> bool:
    if st.session_state.get("panel_shutdown_requested", False):
        return True

    try:
        bg_terminate()
    except Exception:
        pass

    scheduled = _schedule_panel_process_shutdown(os.getpid(), delay_seconds=1.5)
    if not scheduled:
        log("[WARN] Otomasyon Paneli kapatilamadi.")
        return False

    st.session_state.panel_shutdown_requested = True
    st.session_state.ek_dialog_open = None
    log("[INFO] Otomasyon Paneli kapatiliyor...")
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


def _social_media_compat_sort_key(value: str):
    parts = re.split(r'(\d+)', os.path.basename(str(value or '')))
    return [int(part) if part.isdigit() else part.casefold() for part in parts]


def _probe_video_for_social_media_compat(video_path: str) -> dict:
    out = {
        "ok": False,
        "width": 0,
        "height": 0,
        "video_codec": "",
        "audio_codec": "",
        "pix_fmt": "",
        "has_audio": False,
    }
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "stream=codec_type,codec_name,width,height,pix_fmt",
                "-of", "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return out
        data = json.loads(result.stdout or "{}")
        streams = data.get("streams") or []
        video_stream = next((s for s in streams if str(s.get("codec_type")).lower() == "video"), None)
        audio_stream = next((s for s in streams if str(s.get("codec_type")).lower() == "audio"), None)
        if not isinstance(video_stream, dict):
            return out
        out["width"] = int(video_stream.get("width") or 0)
        out["height"] = int(video_stream.get("height") or 0)
        out["video_codec"] = str(video_stream.get("codec_name") or "").strip().lower()
        out["pix_fmt"] = str(video_stream.get("pix_fmt") or "").strip().lower()
        out["has_audio"] = isinstance(audio_stream, dict)
        out["audio_codec"] = str((audio_stream or {}).get("codec_name") or "").strip().lower()
        out["ok"] = True
    except Exception:
        return out
    return out


def _list_social_media_source_video_candidates(video_root: str) -> list:
    supported_exts = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")
    root = str(video_root or "").strip()
    if not root or not os.path.isdir(root):
        return []

    try:
        entries = os.listdir(root)
    except Exception:
        return []

    subdirs = sorted(
        [os.path.join(root, name) for name in entries if os.path.isdir(os.path.join(root, name))],
        key=_social_media_compat_sort_key,
    )

    out = []
    if subdirs:
        for subdir in subdirs:
            try:
                files = [
                    os.path.join(subdir, name)
                    for name in sorted(os.listdir(subdir), key=_social_media_compat_sort_key)
                    if os.path.isfile(os.path.join(subdir, name))
                    and str(name).lower().endswith(supported_exts)
                ]
            except Exception:
                files = []
            if files:
                out.append(files[0])
        return out

    for name in sorted(entries, key=_social_media_compat_sort_key):
        full = os.path.join(root, name)
        if os.path.isfile(full) and str(name).lower().endswith(supported_exts):
            out.append(full)
    return out


def _normalize_single_video_for_social_media(video_path: str, target_width: int, target_height: int, has_audio: bool) -> tuple[bool, str, str]:
    video_path = str(video_path or "").strip()
    if not video_path or not os.path.isfile(video_path):
        return False, "", "Video dosyası bulunamadı"

    folder = os.path.dirname(video_path)
    stem, ext = os.path.splitext(video_path)
    target_path = stem + ".mp4"
    backup_path = video_path + ".sourcebak"
    temp_path = os.path.join(folder, f"__sm_ready_tmp__{int(time.time() * 1000)}_{os.getpid()}.mp4")

    vf = (
        f"fps=30,"
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1"
    )

    if has_audio:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-movflags", "+faststart",
            temp_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-shortest",
            "-movflags", "+faststart",
            temp_path,
        ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0 or not os.path.isfile(temp_path) or os.path.getsize(temp_path) <= 0:
            stderr = (result.stderr or "").strip().splitlines()
            detail = stderr[-1].strip() if stderr else "ffmpeg dönüştürme hatası"
            _cleanup_file_quiet(temp_path)
            return False, "", detail

        if os.path.abspath(target_path) == os.path.abspath(video_path):
            if os.path.exists(backup_path):
                _cleanup_file_quiet(video_path)
            else:
                os.replace(video_path, backup_path)
            os.replace(temp_path, target_path)
        else:
            if os.path.exists(backup_path):
                _cleanup_file_quiet(video_path)
            else:
                os.replace(video_path, backup_path)
            if os.path.exists(target_path):
                target_backup = target_path + ".sourcebak"
                if os.path.exists(target_backup):
                    _cleanup_file_quiet(target_path)
                else:
                    os.replace(target_path, target_backup)
            os.replace(temp_path, target_path)

        return True, target_path, ""
    except Exception as e:
        _cleanup_file_quiet(temp_path)
        return False, "", str(e)


def _prepare_videos_for_social_media_compat(video_root: str) -> dict:
    summary = {
        "video_root": str(video_root or "").strip(),
        "candidate_count": 0,
        "converted": [],
        "skipped": [],
        "errors": [],
    }
    candidates = _list_social_media_source_video_candidates(video_root)
    summary["candidate_count"] = len(candidates)

    for video_path in candidates:
        probe = _probe_video_for_social_media_compat(video_path)
        width = int(probe.get("width") or 0)
        height = int(probe.get("height") or 0)
        is_portrait = height > width if (width > 0 and height > 0) else True
        target_width, target_height = (1080, 1920) if is_portrait else (1920, 1080)

        ext = os.path.splitext(video_path)[1].strip().lower()
        video_codec = str(probe.get("video_codec") or "").strip().lower()
        audio_codec = str(probe.get("audio_codec") or "").strip().lower()
        pix_fmt = str(probe.get("pix_fmt") or "").strip().lower()
        has_audio = bool(probe.get("has_audio"))

        needs_fix = (
            not probe.get("ok")
            or ext != ".mp4"
            or video_codec != "h264"
            or audio_codec != "aac"
            or not pix_fmt.startswith("yuv420p")
            or width != target_width
            or height != target_height
            or not has_audio
        )

        if not needs_fix:
            summary["skipped"].append(video_path)
            continue

        ok, normalized_path, detail = _normalize_single_video_for_social_media(
            video_path,
            target_width=target_width,
            target_height=target_height,
            has_audio=has_audio,
        )
        if ok and normalized_path:
            summary["converted"].append((video_path, normalized_path))
        else:
            summary["errors"].append(f"{os.path.basename(video_path)}: {detail or 'Dönüştürülemedi'}")

    return summary


def _log_social_media_compat_prep(summary: dict):
    if not isinstance(summary, dict):
        return

    converted = summary.get("converted") or []
    skipped = summary.get("skipped") or []
    errors = summary.get("errors") or []

    if converted:
        labels = ", ".join(os.path.basename(dst) for _, dst in converted[:5])
        extra = "" if len(converted) <= 5 else f" (+{len(converted) - 5})"
        log(f"[INFO] Sosyal medya uyumluluğu için videolar dönüştürüldü: {labels}{extra}")
    elif skipped and summary.get("candidate_count", 0) > 0:
        log("[INFO] Sosyal medya için seçilen videolar zaten uyumlu formatta.")

    for err in errors[:5]:
        log(f"[WARN] Sosyal medya video uyumlulaştırma uyarısı: {err}")


def _resolve_social_media_launch_context_early() -> dict:
    s = st.session_state.get("settings", {}) if isinstance(st.session_state.get("settings", {}), dict) else {}
    sm_dir = (s.get("sosyal_medya_dir") or r"C:\Users\User\Desktop\Otomasyon\Ana Sistem\Sosyal Medya Paylaşım").strip()
    script_path = (s.get("sosyal_medya_script") or os.path.join(sm_dir, "sosyal_medya_paylasım.py")).strip()
    kaynak_secim_path = os.path.join(sm_dir, "video_kaynak_secim.txt")
    video_kaynak_path = os.path.join(sm_dir, "video_kaynak.txt")

    kaynak_secim = ""
    try:
        if os.path.exists(kaynak_secim_path):
            with open(kaynak_secim_path, "r", encoding="utf-8", errors="ignore") as f:
                kaynak_secim = f.read().strip()
    except Exception:
        kaynak_secim = ""

    if not kaynak_secim:
        kaynak_secim = st.session_state.get("sm_video_kaynak_secim", "Link")

    kaynak_secim = _sm_normalize_kaynak_secim(kaynak_secim)

    if kaynak_secim == "🎬 Toplu Video Montaj":
        source_root = (s.get("toplu_video_output_dir") or r"C:\Users\User\Desktop\Otomasyon\Video\Toplu Montaj").strip()
    elif kaynak_secim == "🎬 Klon Video":
        source_root = (s.get("klon_video_dir") or s.get("video_klonla_dir") or r"C:\Users\User\Desktop\Otomasyon\Klon Video").strip()
    elif kaynak_secim == "🖼️ Görsel Oluştur":
        source_root = (s.get("video_output_dir") or r"C:\Users\User\Desktop\Otomasyon\Video\Video").strip()
    elif kaynak_secim == "🎞️ Video Ekle":
        source_root = (s.get("added_video_dir") or r"C:\Users\User\Desktop\Otomasyon\Eklenen Video").strip()
    elif kaynak_secim == "🎞️ Video Montaj":
        source_root = (s.get("video_montaj_output_dir") or r"C:\Users\User\Desktop\Otomasyon\Video\Montaj").strip()
    elif kaynak_secim == "Link":
        source_root = (s.get("download_dir") or r"C:\Users\User\Desktop\Otomasyon\İndirilen Video").strip()
    else:
        source_root = (s.get("sosyal_medya_video_dir") or r"C:\Users\User\Desktop\Otomasyon\Video\Video").strip()

    try:
        os.makedirs(sm_dir, exist_ok=True)
        with open(video_kaynak_path, "w", encoding="utf-8") as f:
            f.write(source_root)
    except Exception:
        pass

    return {
        "script_path": script_path,
        "source_selection": kaynak_secim,
        "source_root": source_root,
        "video_kaynak_path": video_kaynak_path,
    }


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


def _clear_kredi_runtime_state():
    for kredi_step in ("kredi_kazan", "kredi_cek"):
        st.session_state[f"{kredi_step}_running"] = False
        st.session_state[f"{kredi_step}_paused"] = False
        st.session_state[f"{kredi_step}_finish"] = False
        st.session_state[f"{kredi_step}_start_ts"] = 0.0


def _consume_kredi_bg_result():
    res = st.session_state.get("bg_last_result")
    if not res:
        return

    node_key = res.get("node_key")
    owner = res.get("owner")
    if node_key not in ("kredi_kazan", "kredi_cek"):
        return
    if owner not in ("kredi_kazan", "kredi_cek"):
        return

    _clear_kredi_runtime_state()
    st.session_state.bg_last_result = None


_consume_kredi_bg_result()


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
        counter = globals().get("_count_real_prompt_links")
        if callable(counter):
            count = counter(links_file)
        else:
            if not links_file or not os.path.exists(links_file):
                count = 0
            else:
                try:
                    with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
                        count = len([ln for ln in f.read().splitlines() if ln.strip()])
                except Exception:
                    count = 0
        placeholder_active = globals().get("_empty_source_placeholder_active")
        if count == 0 and callable(placeholder_active) and placeholder_active():
            return 1
        return count


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

                m = re.match(r'^(?:Klon\s+)?Video\s+(\d+)$', item, re.IGNORECASE)
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

        parts = [p.strip() for p in re.split(r'[\s,.;]+', raw) if p.strip()]
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
    def _prepare_mevcut_video_runner_dirs(video_items: list, temp_prefix: str = "video_montaj", force_copy: bool = False) -> tuple[str, str, dict]:
        existing_items = []
        token_remap = {}
        next_token = 1

        for item in (video_items or []):
            token = str(item.get("token") or "").strip()
            path = (item.get("path") or "").strip()
            if token and item.get("exists") and path and os.path.isfile(path):
                token_remap[token] = str(next_token)
                next_token += 1
            if not item.get("exists") or not path or not os.path.isfile(path):
                continue
            existing_items.append(item)

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
                log(f"[INFO] Montaj kaynağı seçime göre hazırlandı: {copied_count} dosya geçici kaynak klasörüne kopyalandı.")
            else:
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

    def _vm_bootstrap_split_selection_text(text: str) -> list:
        return [p.strip() for p in re.split(r'[\s,.;]+', text or "") if p.strip()]


    def _vm_bootstrap_ui_to_script_selection(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return "T"

        parts = _vm_bootstrap_split_selection_text(raw)
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
            "            if 'Se' in prompt or 'secim' in prompt.lower():",
            "                raise RuntimeError('Video Montaj beklenmeyen ek secim istedi; kayitli secim gecersiz olabilir.')",
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
        elif source_mode == "Klon Video":
            video_klasor = ""
            klon_video_klasor = s.get("klon_video_dir", "")
            source_video_items = _list_video_montaj_assets().get("clone_videos", [])
            temp_video_klasor, temp_klon_video_klasor, token_remap = _prepare_mevcut_video_runner_dirs(
                source_video_items,
                temp_prefix="video_montaj_klon_video",
                force_copy=True,
            )
            if temp_video_klasor or temp_klon_video_klasor:
                video_klasor = temp_video_klasor
                klon_video_klasor = temp_klon_video_klasor or klon_video_klasor
            remapped_selection_text = _remap_numeric_selection_text(raw_selection or "T", token_remap)
            selection_text = _vm_bootstrap_ui_to_script_selection(remapped_selection_text or "T")
        else:
            video_klasor = s.get("video_output_dir", "")
            klon_video_klasor = ""
            source_video_items = _list_video_montaj_assets().get("videos", [])
            temp_video_klasor, temp_klon_video_klasor, token_remap = _prepare_mevcut_video_runner_dirs(
                source_video_items,
                temp_prefix="video_montaj",
                force_copy=True,
            )
            if temp_video_klasor:
                video_klasor = temp_video_klasor
                klon_video_klasor = temp_klon_video_klasor or ""
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
            raw_production_limit = preset.get("production_limit", preset.get("uretim_limiti", st.session_state.get("toplu_video_production_limit", 0)))
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
            raw_production_limit = st.session_state.get("toplu_video_production_limit", 0)
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
        elif source_mode == "Klon Video":
            source_video_items = _list_video_montaj_assets().get("clone_videos", [])
            temp_video_kaynak_ana_yol, temp_klon_video_kaynak_ana_yol, token_remap = _prepare_mevcut_video_runner_dirs(
                source_video_items,
                temp_prefix="toplu_video_klon_video",
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
        production_limit = _toplu_video_uretim_limiti_normalize(raw_production_limit)
        baslik = (raw_baslik or "").strip()
        try:
            with open(os.path.join(CONTROL_DIR, "toplu_video_runtime_limit.txt"), "w", encoding="utf-8") as f:
                f.write(str(production_limit or 0))
        except Exception as e:
            log(f"[WARN] Toplu Video uretim limiti yazilamadi: {e}")

        if source_mode == "Eklenen Video":
            video_kaynak_ana_yol = s.get("added_video_dir", "")
            klon_video_kaynak_ana_yol = ""
        elif source_mode == "Görsel Oluştur":
            video_kaynak_ana_yol = temp_video_kaynak_ana_yol or s.get("video_output_dir", "")
            klon_video_kaynak_ana_yol = ""
        elif source_mode == "Klon Video":
            video_kaynak_ana_yol = temp_video_kaynak_ana_yol or ""
            klon_video_kaynak_ana_yol = temp_klon_video_kaynak_ana_yol or s.get("klon_video_dir", "")
        else:
            video_kaynak_ana_yol = temp_video_kaynak_ana_yol or s.get("video_output_dir", "")
            klon_video_kaynak_ana_yol = temp_klon_video_kaynak_ana_yol or ""

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
            "production_limit": production_limit,
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


if "start_sosyal_medya_bg" not in globals():

    def start_sosyal_medya_bg(owner: str = "single") -> bool:
        ctx = _resolve_social_media_launch_context_early()
        script_path = (ctx.get("script_path") or "").strip()

        if not script_path or not os.path.exists(script_path):
            st.session_state.status["sosyal_medya"] = "error"
            log(f"[ERROR] Sosyal medya script bulunamadı: {script_path}")
            return False

        source_selection = str(ctx.get("source_selection") or "").strip()
        source_root = str(ctx.get("source_root") or "").strip()

        if source_selection in {"Link", "Video", "🖼️ Görsel Oluştur", "🎬 Klon Video"} and source_root:
            log(f"[INFO] Sosyal medya ön hazırlığı: {source_selection} kaynağı için video uyumluluğu kontrol ediliyor...")
            compat_summary = _prepare_videos_for_social_media_compat(source_root)
            _log_social_media_compat_prep(compat_summary)
            if (
                compat_summary.get("candidate_count", 0) > 0
                and not compat_summary.get("converted")
                and not compat_summary.get("skipped")
                and compat_summary.get("errors")
            ):
                st.session_state.status["sosyal_medya"] = "error"
                log("[ERROR] Sosyal medya için uygun video hazırlanamadı. Paylaşım başlatılmadı.")
                return False

        return bg_start(owner, "sosyal_medya", script_path)

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
        prompt_source = _resolve_video_prompt_source_for_generation()
        if prompt_source.get("kind") == "gorsel_motion":
            overridden = True
            extra_args = ["--prompt-dir", prompt_source.get("prompt_dir", GORSEL_HAREKET_PROMPT_DIR), "--ref-image-dir", prompt_source.get("ref_image_dir", GORSEL_HAREKET_REFERANS_DIR)]
            st.session_state.pixverse_prompt_override_meta = {
                "is_gorsel_override": True,
                "original_settings_prompt_dir": st.session_state.settings.get("prompt_dir", ""),
                "original_settings_ref_dir": st.session_state.settings.get("gorsel_klonlama_dir", "")
            }
            # settings.local.json'a dogrudan yaz (script modul-level okumasi icin)
            try:
                _s = dict(st.session_state.settings)
                _s["prompt_dir"] = prompt_source.get("prompt_dir", GORSEL_HAREKET_PROMPT_DIR)
                _s["gorsel_klonlama_dir"] = prompt_source.get("ref_image_dir", GORSEL_HAREKET_REFERANS_DIR)
                import json as _json
                with open(SETTINGS_PATH, "r", encoding="utf-8") as _rf:
                    _current = _json.load(_rf)
                _current["prompt_dir"] = prompt_source.get("prompt_dir", GORSEL_HAREKET_PROMPT_DIR)
                _current["gorsel_klonlama_dir"] = prompt_source.get("ref_image_dir", GORSEL_HAREKET_REFERANS_DIR)
                with open(SETTINGS_PATH, "w", encoding="utf-8") as _wf:
                    _json.dump(_current, _wf, ensure_ascii=False, indent=2)
                log(f"[INFO] Video prompt kaynağı -> Görsel Hareketlendirme Prompt ({prompt_source.get('reason', 'state_active')})")
                log(f"[INFO] PROMPT_ROOT override: {prompt_source.get('prompt_dir', GORSEL_HAREKET_PROMPT_DIR)}")
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
        "video_klonla":     s.get("video_klonla_motion_script", MOTION_CONTROL_SCRIPT_DEFAULT),
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

            if node == "download":
                try:
                    _apply_saved_video_bolum_plans_after_download("batch")
                except Exception as e:
                    log(f"[WARN] Kayitli video bolum planlari uygulanamadi: {e}")

            # görsel_klonlama kısmi tamamlandı → batch DURDUR
            # Kullanıcı düzenleme yapıp Devam Et'e basacak; aynı adımdan tekrar denenecek.
            if node == "gorsel_klonlama" and node_status == "partial":
                cur_logs_partial = list(st.session_state.logs)
                gk_err_partial = _detect_gorsel_klonlama_error_type(cur_logs_partial)
                if gk_err_partial == "api":
                    st.session_state.batch_resume_reason = "⚠️ API / bağlantı hatası (kısmi sonuç) — Görsel Klonla adımından tekrar denenecek."
                    log("[INFO] Görsel Klonla kısmi hata: API/bağlantı sorunu tespit edildi → Görsel Klonla adımından tekrar başlanacak.")
                else:
                    st.session_state.batch_resume_reason = "⚠️ Bazı görseller klonlanamadı — Görsel Klonla adımından tekrar denenecek."
                    log("[INFO] Görsel Klonla kısmi tamamlandı → batch durduruluyor, Görsel Klonla adımından tekrar başlanacak.")
                _stop_batch_with_resume("gorsel_klonlama")
                st.rerun()

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
                elif px_err_partial == "timeout":
                    _partial_rollback = "pixverse"
                    st.session_state.batch_resume_reason = f"⚠️ Video oluşturma zaman aşımı — {get_video_generation_label(emoji=False)} adımından tekrar denenecek."
                    log(f"[INFO] Kısmi hata: Video oluşturma zaman aşımı → {get_video_generation_label(emoji=False)} adımından tekrar başlanacak.")
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
                        if next_node == "pixverse":
                            _started_ok = start_pixverse_bg("batch")
                        elif next_node == "video_klonla":
                            _started_ok = start_video_klonla_bg("batch")
                        elif next_node == "sosyal_medya":
                            _started_ok = start_sosyal_medya_bg("batch")
                        elif next_node == "analyze":
                            _started_ok = start_analyze_bg("batch")
                        else:
                            _started_ok = bg_start("batch", next_node, next_script)
                        if not _started_ok:
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
                elif px_err == "timeout":
                    # Video bekleme/indirme zaman aşımı → Video Üret'ten tekrar dene
                    rollback_node = "pixverse"
                    _resume_reason = f"⚠️ Video oluşturma zaman aşımı — {get_video_generation_label(emoji=False)} adımından tekrar denenecek."
                    log(f"[INFO] Video oluşturma zaman aşımı tespit edildi → {get_video_generation_label(emoji=False)} adımından tekrar başlanacak.")
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

            elif node == "video_klonla":
                rollback_node = "video_klonla"
                vk_err = _detect_pixverse_error_type(cur_logs)
                vk_detay = _detect_hata_detay(cur_logs, "video_klonla")
                if vk_err == "credit" or vk_detay == "Kredi Yetersiz":
                    _resume_reason = "⚠️ Kredi yetersiz — Video Klonla adımından tekrar denenecek."
                    log("[INFO] Video Klonla kredi hatası tespit edildi → Video Klonla adımından tekrar başlanacak.")
                elif str(vk_detay).startswith("Referans Gorsel Boyutu Cok Buyuk"):
                    _resume_reason = "⚠️ Referans görsel boyutu çok büyük — Video Klonla adımından tekrar denenecek."
                    log("[INFO] Video Klonla referans görsel boyutu hatası tespit edildi → Video Klonla adımından tekrar başlanacak.")
                elif str(vk_detay).startswith("Referans Gorsel Yukleme Zaman Asimi"):
                    _resume_reason = "⚠️ Referans görsel yükleme zaman aşımı — Video Klonla adımından tekrar denenecek."
                    log("[INFO] Video Klonla referans görsel yükleme zaman aşımı tespit edildi → Video Klonla adımından tekrar başlanacak.")
                else:
                    _resume_reason = "⚠️ Video klonlama hatası — Video Klonla adımından tekrar denenecek."
                    log("[INFO] Video Klonla hatası tespit edildi → Video Klonla adımından tekrar başlanacak.")

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
                elif node_key == "video_klonla":
                    _started_ok = start_video_klonla_bg("batch")
                elif node_key == "sosyal_medya":
                    _started_ok = start_sosyal_medya_bg("batch")
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
        if res.get("node_key") == "download" and bool(res.get("success")):
            try:
                _apply_saved_video_bolum_plans_after_download("single")
            except Exception as e:
                log(f"[WARN] Kayitli video bolum planlari uygulanamadi: {e}")
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
            elif step == "video_klonla": _single_started = start_video_klonla_bg("single")
            elif step == "prompt_duzeltme": _single_started = bg_start("single", "prompt_duzeltme", st.session_state.settings["prompt_duzeltme_script"])
            elif step == "video_montaj": _single_started = start_video_montaj_bg("single")
            elif step == "toplu_video": _single_started = start_toplu_video_bg("single")
            elif step == "sosyal_medya": _single_started = start_sosyal_medya_bg("single")
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

.panel-shutdown-notice {
  margin-top: 10px;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(245, 158, 11, 0.34);
  background: rgba(245, 158, 11, 0.18);
  color: #fde68a;
  font-size: 14px;
  line-height: 1.4;
  font-weight: 700;
}

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
    st.markdown('<style>div[data-testid="stDialog"] { justify-content: center !important; align-items: flex-start !important; padding: 0 !important; padding-top: 20px !important; }</style>', unsafe_allow_html=True)

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

    label = {"youtube_link":"📺 YouTube Link Toplama","download":"⬇️ Video İndiriliyor","gorsel_analiz":"🖼️ Görsel Analiz","gorsel_klonlama":"🎨 Görsel Klonlama","analyze":"📄 Analiz & Prompt","pixverse":get_video_generation_label(),"video_klonla":"🎬 Klon Video Üret","gorsel_olustur":"🚀 Görsel Oluştur","prompt_duzeltme":"✏️ Prompt Düzeltme","video_montaj":"🎥️ Video Montaj","toplu_video":"🎬 Toplu Video Montaj","sosyal_medya":"🌐 Sosyal Medya Paylaşım","kredi_kazan":"🎰 Video Üretme Kredisi Kazan","kredi_cek":"📥 Üretilen Kredileri Çek"}.get(step, "İşlem")
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
    if result.get("total", 0) > 0:
        clear_placeholder = globals().get("_clear_empty_source_placeholder")
        if callable(clear_placeholder):
            clear_placeholder()
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
VIDEO_SETTINGS_OVERRIDE_FILE = os.path.join(CONTROL_DIR, "video_settings_overrides.json")
EMPTY_SOURCE_PLACEHOLDER_FILE = os.path.join(CONTROL_DIR, "empty_source_placeholder.json")


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


def _get_video_media_metadata(video_path: str) -> dict:
    """ffprobe ile videonun süre ve çözünürlük bilgisini döndürür."""
    result = {
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "rotate": 0,
    }
    if not video_path or not os.path.isfile(video_path):
        return result
    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-print_format", "json",
                "-select_streams", "v:0",
                "-show_entries", "format=duration:stream=width,height:stream_tags=rotate",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads((probe.stdout or "").strip() or "{}")
        fmt = data.get("format") if isinstance(data, dict) else {}
        streams = data.get("streams") if isinstance(data, dict) else []
        if isinstance(fmt, dict):
            try:
                result["duration"] = float(fmt.get("duration") or 0.0)
            except Exception:
                result["duration"] = 0.0
        stream = streams[0] if isinstance(streams, list) and streams else {}
        if isinstance(stream, dict):
            try:
                result["width"] = int(stream.get("width") or 0)
            except Exception:
                result["width"] = 0
            try:
                result["height"] = int(stream.get("height") or 0)
            except Exception:
                result["height"] = 0
            tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
            try:
                result["rotate"] = int(tags.get("rotate") or 0)
            except Exception:
                result["rotate"] = 0
        if result["rotate"] in {90, 270, -90, -270}:
            result["width"], result["height"] = result["height"], result["width"]
    except Exception:
        pass
    return result


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


def _format_mmss_ms(seconds: float) -> str:
    """Saniyeyi M:SS:mmm formatina cevirir (orn: 0:12:350)."""
    try:
        total_ms = int(round(float(seconds) * 1000))
    except Exception:
        total_ms = 0
    total_ms = max(0, total_ms)
    m = total_ms // 60000
    kalan_ms = total_ms % 60000
    s = kalan_ms // 1000
    ms = kalan_ms % 1000
    return f"{m}:{s:02d}:{ms:03d}"


def _format_duration_ms(seconds: float) -> str:
    """Saniyeyi milisaniye hassasiyetinde okunabilir formata cevirir."""
    try:
        total_ms = int(round(float(seconds) * 1000))
    except Exception:
        total_ms = 0
    total_ms = max(0, total_ms)
    m = total_ms // 60000
    kalan_ms = total_ms % 60000
    s = kalan_ms // 1000
    ms = kalan_ms % 1000
    if m > 0:
        return f"{m}dk {s}sn {ms}ms"
    if s > 0:
        return f"{s}sn {ms}ms"
    return f"{ms}ms"


def _format_ffmpeg_seconds(seconds: float) -> str:
    """ffmpeg'e milisaniye hassasiyetinde saniye degeri verir."""
    try:
        value = max(0.0, float(seconds))
    except Exception:
        value = 0.0
    return f"{value:.3f}"


def _parse_mmss(text: str) -> float:
    """M:SS, M:SS.mmm, M:SS:mmm veya SS formatini saniyeye cevirir."""
    text = (text or "").strip().replace(",", ".")
    if not text:
        return -1
    if ":" in text:
        parts = text.split(":")
        try:
            if len(parts) == 2:
                m = int(parts[0])
                s = float(parts[1])
                value = m * 60 + s
                return round(value, 3) if value >= 0 else -1
            if len(parts) == 3:
                m = int(parts[0])
                s = int(parts[1])
                ms_text = parts[2].strip()
                if not ms_text.isdigit() or len(ms_text) > 3:
                    return -1
                ms = int(ms_text.ljust(3, "0"))
                value = m * 60 + s + (ms / 1000)
                return round(value, 3) if value >= 0 else -1
        except (ValueError, TypeError):
            return -1
        return -1
    try:
        value = float(text)
        return round(value, 3) if value >= 0 else -1
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
            # Re-encode ile milisaniye hassasiyetinde kesim yap.
            subprocess.run(
                ["ffmpeg", "-y",
                 "-i", video_path,
                 "-ss", _format_ffmpeg_seconds(start),
                 "-t", _format_ffmpeg_seconds(duration),
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


def _render_video_bolum_precision_controls() -> None:
    rate_options = ["0.25x", "0.5x", "0.75x", "1x"]
    selected_rate = st.radio(
        "Oynatma hızı",
        rate_options,
        index=rate_options.index(st.session_state.get("dlg_bolum_playback_rate", "0.5x"))
        if st.session_state.get("dlg_bolum_playback_rate", "0.5x") in rate_options else 1,
        horizontal=True,
        key="dlg_bolum_playback_rate",
    )
    try:
        rate_value = float(str(selected_rate).replace("x", ""))
    except Exception:
        rate_value = 0.5

    _st_components.html(
        f"""
        <div style="font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #f4f4f7;">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 12px; border:1px solid rgba(255,255,255,.14); border-radius:8px; background:rgba(255,255,255,.045);">
            <div style="font-size:13px; color:rgba(244,244,247,.72);">Geçerli zaman</div>
            <div id="video-bolum-ms-clock" style="font-size:18px; font-weight:700; font-variant-numeric:tabular-nums;">0:00:000</div>
          </div>
        </div>
        <script>
        (function() {{
          const rate = {rate_value};
          const clock = document.getElementById("video-bolum-ms-clock");
          function findPreviewVideo() {{
            try {{
              const videos = Array.from(window.parent.document.querySelectorAll("video"));
              return videos.length ? videos[videos.length - 1] : null;
            }} catch (err) {{
              return null;
            }}
          }}
          function formatTime(seconds) {{
            const totalMs = Math.max(0, Math.round((seconds || 0) * 1000));
            const minutes = Math.floor(totalMs / 60000);
            const sec = Math.floor((totalMs % 60000) / 1000);
            const ms = totalMs % 1000;
            return `${{minutes}}:${{String(sec).padStart(2, "0")}}:${{String(ms).padStart(3, "0")}}`;
          }}
          function tick() {{
            const video = findPreviewVideo();
            if (video) {{
              if (Math.abs(video.playbackRate - rate) > 0.001) {{
                video.playbackRate = rate;
              }}
              clock.textContent = formatTime(video.currentTime);
            }} else {{
              clock.textContent = "0:00:000";
            }}
            window.requestAnimationFrame(tick);
          }}
          tick();
        }})();
        </script>
        """,
        height=74,
    )


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
    return len(_list_added_video_preview_entries())


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
    for idx, entry in enumerate(_list_added_video_preview_entries(), start=1):
        exists = bool(str(entry.get("video_path") or "").strip())
        planned = bool(entry.get("planned")) and not exists
        label = f"[{idx}] Eklenen Video {entry.get('no', idx)}"
        if planned:
            label += " (planli)"
        items.append({
            "token": str(idx),
            "script_token": str(idx - 1),
            "label": label,
            "path": entry.get("video_path", ""),
            "exists": exists,
            "expected": not exists,
            "video_no": int(entry.get("no", idx) or idx),
            "source_kind": "added_video",
            "planned": planned,
            "source_no": entry.get("source_no"),
            "segment_no": entry.get("segment_no"),
            "segment_start": entry.get("segment_start"),
            "segment_end": entry.get("segment_end"),
            "source_title": entry.get("source_title"),
        })
    return items


def _count_prompt_links() -> int:
    return _count_real_prompt_links()


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
        gorseller.sort(key=lambda name: (0 if str(name).casefold().startswith("start.") else 1 if str(name).casefold().startswith("end.") else 2, natural_sort_key(name))); return gorseller
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

def gorsel_secimini_transition_olarak_kaydet(klasor_adi, start_gorsel, end_gorsel):
    k_yol = os.path.join(st.session_state.settings.get("gorsel_analiz_dir", ""), klasor_adi)
    if not os.path.isdir(k_yol):
        return False
    start_path = os.path.join(k_yol, str(start_gorsel or "").strip())
    end_path = os.path.join(k_yol, str(end_gorsel or "").strip())
    if not (os.path.isfile(start_path) and os.path.isfile(end_path)):
        return False
    if os.path.abspath(start_path) == os.path.abspath(end_path):
        return False
    try:
        saved_paths = replace_folder_images_with_standard_images(
            k_yol,
            [("start", start_path), ("end", end_path)],
        )
        if len(saved_paths) == 2:
            log(f"[OK] {klasor_adi}: Start/End frame kaydedildi -> start.png, end.png")
            return True
    except Exception as e:
        log(f"[ERROR] Transition frame kaydedilemedi: {e}")
    return False


def _normalize_gorsel_klon_prompt_entry(value):
    if isinstance(value, dict):
        shared = str(value.get("shared") or "").strip()
        start = str(value.get("start") or "").strip()
        end = str(value.get("end") or "").strip()
        if shared or start or end:
            return {"shared": shared, "start": start, "end": end}
        return ""
    return str(value or "").strip()


def _gorsel_klon_prompt_has_value(value, require_transition_pair: bool = False) -> bool:
    normalized = _normalize_gorsel_klon_prompt_entry(value)
    if isinstance(normalized, dict):
        shared = str(normalized.get("shared") or "").strip()
        start = str(normalized.get("start") or "").strip()
        end = str(normalized.get("end") or "").strip()
        if require_transition_pair:
            return bool((start or shared) and (end or shared))
        return bool(shared or start or end)
    return bool(str(normalized or "").strip())


def _gorsel_klon_prompt_frame_value(value, frame_name: str) -> str:
    normalized = _normalize_gorsel_klon_prompt_entry(value)
    if isinstance(normalized, dict):
        shared = str(normalized.get("shared") or "").strip()
        start = str(normalized.get("start") or "").strip()
        end = str(normalized.get("end") or "").strip()
        if str(frame_name or "").strip().lower() == "start":
            return start or shared
        if str(frame_name or "").strip().lower() == "end":
            return end or shared
        return shared or start or end
    return str(normalized or "").strip()


def _gorsel_klon_prompt_display_text(value) -> str:
    normalized = _normalize_gorsel_klon_prompt_entry(value)
    if isinstance(normalized, dict):
        shared = str(normalized.get("shared") or "").strip()
        start = str(normalized.get("start") or "").strip()
        end = str(normalized.get("end") or "").strip()
        parts = []
        if shared:
            parts.append(shared)
        if start:
            parts.append(f"Start: {start}")
        if end:
            parts.append(f"End: {end}")
        return " | ".join(parts)
    return str(normalized or "").strip()


def gorsel_duzelt_oku():
    path = st.session_state.settings.get("gorsel_duzelt_txt", "")
    res = {}
    if not path or not os.path.exists(path): return res
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                temiz_satir = line.strip()
                pair_match = re.match(r"Görsel\s+(\d+)\s+(Start|End)\s*:\s*(.*)", temiz_satir, re.IGNORECASE)
                if pair_match:
                    no = int(pair_match.group(1))
                    frame_name = "start" if pair_match.group(2).strip().lower() == "start" else "end"
                    mevcut = _normalize_gorsel_klon_prompt_entry(res.get(no, ""))
                    if not isinstance(mevcut, dict):
                        mevcut = {"shared": str(mevcut or "").strip(), "start": "", "end": ""}
                    mevcut[frame_name] = pair_match.group(3).strip()
                    res[no] = mevcut
                    continue
                match = re.match(r"Görsel\s+(\d+)\s*:\s*(.*)", temiz_satir, re.IGNORECASE)
                if match:
                    no = int(match.group(1))
                    text_value = match.group(2).strip()
                    mevcut = res.get(no, "")
                    if isinstance(mevcut, dict):
                        mevcut = _normalize_gorsel_klon_prompt_entry(mevcut)
                        mevcut["shared"] = text_value
                        res[no] = mevcut
                    else:
                        res[no] = text_value
    except Exception: pass
    return res

def gorsel_duzelt_kaydet(data: dict):
    path = st.session_state.settings.get("gorsel_duzelt_txt", "")
    if not path: return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            for no in sorted(data.keys()):
                value = _normalize_gorsel_klon_prompt_entry(data.get(no, ""))
                if isinstance(value, dict):
                    shared = str(value.get("shared") or "").strip()
                    start = str(value.get("start") or "").strip()
                    end = str(value.get("end") or "").strip()
                    if shared:
                        f.write(f"Görsel {no}: {shared}\n")
                    if start:
                        f.write(f"Görsel {no} Start: {start}\n")
                    if end:
                        f.write(f"Görsel {no} End: {end}\n")
                elif str(value or "").strip():
                    f.write(f"Görsel {no}: {value}\n")
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


def _normalize_gorsel_referans_slot(frame_name: str | None = None) -> str:
    raw = str(frame_name or "").strip().lower()
    if raw == "start":
        return "start"
    if raw == "end":
        return "end"
    return ""


def _gorsel_referans_dosyasi_eslesir(fname: str, gorsel_no: int, frame_name: str | None = None) -> bool:
    slot = _normalize_gorsel_referans_slot(frame_name)
    if slot:
        pattern = rf"^ref_{gorsel_no}_{slot}(?:__\d+)?\.(?:jpg|jpeg|png|bmp|webp|gif)$"
    else:
        pattern = rf"^ref_{gorsel_no}(?:__\d+)?\.(?:jpg|jpeg|png|bmp|webp|gif)$"
    return bool(
        re.match(
            pattern,
            str(fname or "").strip(),
            re.IGNORECASE,
        )
    )


def gorsel_referans_yollari(gorsel_no: int, frame_name: str | None = None) -> list[str]:
    """Belirli görsel numarasına ait tüm referans görsel yollarını döndürür."""
    klasor = _gorsel_referans_klasoru()
    if not klasor or not os.path.isdir(klasor):
        return []
    bulunan = []
    try:
        for fname in sorted(os.listdir(klasor), key=natural_sort_key):
            if _gorsel_referans_dosyasi_eslesir(fname, gorsel_no, frame_name):
                bulunan.append(os.path.join(klasor, fname))
    except Exception:
        return []
    return bulunan


def gorsel_referans_kaydet(gorsel_no: int, uploaded_file, frame_name: str | None = None) -> bool:
    """Yüklenen tek veya çoklu referans görsellerini klasöre kaydeder."""
    klasor = _gorsel_referans_klasoru()
    if not klasor:
        return False
    if uploaded_file is None:
        return False
    uploaded_files = uploaded_file if isinstance(uploaded_file, (list, tuple)) else [uploaded_file]
    uploaded_files = [dosya for dosya in uploaded_files if dosya is not None]
    if not uploaded_files:
        return False
    try:
        os.makedirs(klasor, exist_ok=True)
        slot = _normalize_gorsel_referans_slot(frame_name)
        # Mevcut referans görsellerini sil
        for fname in os.listdir(klasor):
            if _gorsel_referans_dosyasi_eslesir(fname, gorsel_no, frame_name):
                try:
                    os.remove(os.path.join(klasor, fname))
                except Exception:
                    pass
        kaydedilenler = []
        tekli_kayit = len(uploaded_files) == 1
        for sira, dosya in enumerate(uploaded_files, start=1):
            ext = os.path.splitext(getattr(dosya, "name", "") or "img.png")[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
                ext = ".png"
            if tekli_kayit:
                dosya_adi = f"ref_{gorsel_no}_{slot}{ext}" if slot else f"ref_{gorsel_no}{ext}"
            else:
                dosya_adi = f"ref_{gorsel_no}_{slot}__{sira:02d}{ext}" if slot else f"ref_{gorsel_no}__{sira:02d}{ext}"
            with open(os.path.join(klasor, dosya_adi), "wb") as f:
                f.write(dosya.getbuffer())
            kaydedilenler.append(dosya_adi)
        if len(kaydedilenler) == 1:
            log(f"[OK] Referans görsel kaydedildi: {kaydedilenler[0]}")
        else:
            log(f"[OK] {gorsel_no}. görsel için {len(kaydedilenler)} referans görsel kaydedildi.")
        return True
    except Exception as e:
        log(f"[ERROR] Referans görsel kaydedilemedi: {e}")
        return False


def gorsel_referans_sil(gorsel_no: int, frame_name: str | None = None) -> bool:
    """Belirli görsel numarasının referans görselini siler."""
    klasor = _gorsel_referans_klasoru()
    if not klasor or not os.path.isdir(klasor):
        return False
    try:
        for fname in os.listdir(klasor):
            if _gorsel_referans_dosyasi_eslesir(fname, gorsel_no, frame_name):
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
    yollar = gorsel_referans_yollari(gorsel_no)
    return yollar[0] if yollar else ""

def _apply_pending_gklonla_form_ui_state():
    pending = st.session_state.pop("gklonla_pending_form_ui", None)
    if not isinstance(pending, dict):
        return

    clear_text_keys = bool(pending.get("clear_text_keys"))
    clear_ref_keys = bool(pending.get("clear_ref_keys"))
    hedefler = set()
    for value in pending.get("targets") or []:
        try:
            hedefler.add(int(value))
        except Exception:
            continue

    for key in list(st.session_state.keys()):
        match = re.match(r"^(dzt|dzt_start|dzt_end|ref_up|ref_saved|ref_up_start|ref_up_end|ref_saved_start|ref_saved_end)_(\d+)$", str(key))
        if not match:
            continue
        key_tipi = match.group(1)
        key_no = int(match.group(2))
        if hedefler and key_no not in hedefler:
            continue
        if key_tipi in ("dzt", "dzt_start", "dzt_end") and not clear_text_keys:
            continue
        if key_tipi in ("ref_up", "ref_saved", "ref_up_start", "ref_up_end", "ref_saved_start", "ref_saved_end") and not clear_ref_keys:
            continue
        st.session_state.pop(key, None)


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
            display_value = _gorsel_klon_prompt_display_text(yeni_deger)
            if display_value:
                mevcut_data[no] = display_value
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
            elif kaynak_secim == "🎬 Klon Video":
                video_dir = (st.session_state.settings.get("klon_video_dir") or st.session_state.settings.get("video_klonla_dir") or "").strip()
                if not video_dir:
                    video_dir = r"C:\Users\User\Desktop\Otomasyon\Klon Video"
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
        video_root = ""

    valid_ext = (".mp4", ".mov", ".avi", ".mkv", ".webm")
    nums = set()
    if video_root:
        try:
            entries = sorted(os.listdir(video_root), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", x)])
        except Exception:
            entries = []

        subdirs = [e for e in entries if os.path.isdir(os.path.join(video_root, e))]
        if subdirs:
            for idx, name in enumerate(subdirs, start=1):
                m = re.search(r"(\d+)\s*$", name)
                nums.add(int(m.group(1)) if m else idx)
            if nums:
                return nums

        file_list = [e for e in entries if os.path.isfile(os.path.join(video_root, e)) and e.lower().endswith(valid_ext)]
        for idx, name in enumerate(file_list, start=1):
            m = re.search(r"(\d+)\s*$", os.path.splitext(name)[0])
            nums.add(int(m.group(1)) if m else idx)
        if nums:
            return nums

    planned_count = 0
    try:
        planned_count = _count_standard_video_prompt_entries()
        if planned_count <= 0:
            planned_count = _get_prompt_input_count()
    except Exception:
        planned_count = 0
    if planned_count > 0:
        return set(range(1, planned_count + 1))
    return set()


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
    return {int(item.get("no")) for item in _list_added_video_preview_entries() if str(item.get("no", "")).isdigit()}


def sosyal_medya_toplu_video_numaralari() -> set[int]:
    """Toplu Video Montaj çıktı klasöründeki mevcut videolardan veya kaydedilmiş preset'ten üretilecek video numaralarını döndürür."""
    toplu_dir = (st.session_state.settings.get("toplu_video_output_dir") or "").strip()
    saved_production_limit = 0
    try:
        preset_path = os.path.join(CONTROL_DIR, "toplu_video_preset.json")
        if os.path.exists(preset_path):
            with open(preset_path, "r", encoding="utf-8") as fp:
                preset_for_limit = json.load(fp)
            if isinstance(preset_for_limit, dict):
                saved_production_limit = _toplu_video_uretim_limiti_normalize(
                    preset_for_limit.get("production_limit", preset_for_limit.get("uretim_limiti", 0))
                )
    except Exception:
        saved_production_limit = 0
    # Önce mevcut videoları kontrol et
    if toplu_dir:
        nums = _sm_klasorden_video_numaralari(toplu_dir)
        if nums:
            if saved_production_limit > 0:
                return set(sorted(nums)[:saved_production_limit])
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
                elif source_mode == "Klon Video":
                    toplam_kaynak = len(_collect_video_klonla_runtime_items("batch"))
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
                            uretilecek = _toplu_video_uretim_limiti_normalize(
                                preset.get("production_limit", preset.get("uretim_limiti", 0)),
                                uretilecek,
                            ) or uretilecek
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


def sosyal_medya_klon_video_numaralari() -> set[int]:
    planned_count = _planned_video_klonla_output_count()
    if planned_count > 0:
        return set(range(1, planned_count + 1))

    klon_dir = (st.session_state.settings.get("klon_video_dir") or st.session_state.settings.get("video_klonla_dir") or "").strip()
    if klon_dir:
        return _sm_klasorden_video_numaralari(klon_dir)
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


def _sosyal_medya_hesap_stratejisi_normalize(value: str | None = None, *, loop_accounts: bool | None = None, mode: str | None = None, legacy_safe: bool = False) -> str:
    mode_value = str(mode or "").strip().lower()
    if mode_value and mode_value != "bulk":
        return "single"

    raw = str(value or "").strip().casefold()
    if raw:
        if any(key in raw for key in ("tüm hesap", "tum hesap", "fanout", "fan-out", "hepsinde", "all accounts")):
            return "fanout"
        if any(key in raw for key in ("sırayla", "sirayla", "dağıt", "dagit", "round", "round_robin", "round-robin", "döngü", "dongu")):
            return "round_robin"

    # Eski kayıtlarda yalnızca "Hesap Döngü" alanı vardı ve kapalıyken
    # her videoyu tüm hesaplarda çoğaltıyordu. Güvenli göç için eski
    # kayıtları varsayılan olarak sırayla dağıt moduna alıyoruz.
    if loop_accounts is not None:
        if legacy_safe:
            return "round_robin"
        return "round_robin" if bool(loop_accounts) else "fanout"
    return "round_robin"


def sosyal_medya_hesap_konfig_oku() -> dict:
    yollar = sosyal_medya_ensure_files()
    raw = sosyal_medya_read_text(yollar.get("hesap", ""), "")
    cfg = {"mode": "single", "loop_accounts": False, "strategy": "single", "accounts": [], "raw": raw}
    if not raw:
        return cfg

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    mode = None
    loop_accounts = False
    strategy = ""
    accounts = []

    for line in lines:
        low = line.casefold()
        if low.startswith(("hesap modu:", "mod:", "mode:")):
            mode = "bulk" if any(k in low for k in ("toplu", "bulk", "çoklu", "coklu")) else "single"
            continue
        if low.startswith(("paylaşım stratejisi:", "paylasim stratejisi:", "strateji:", "strategy:")):
            strategy = line.split(":", 1)[1].strip()
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

    normalized_strategy = _sosyal_medya_hesap_stratejisi_normalize(
        strategy,
        loop_accounts=loop_accounts,
        mode=mode,
        legacy_safe=True,
    )
    cfg["mode"] = mode
    cfg["strategy"] = normalized_strategy
    cfg["loop_accounts"] = (normalized_strategy == "round_robin") if mode == "bulk" else False
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

    strategy = _sosyal_medya_hesap_stratejisi_normalize(
        None,
        loop_accounts=loop_accounts,
        mode=mode,
    )
    parts = [f"Hesap Modu: {'Toplu Hesap' if str(mode) == 'bulk' else 'Tek Hesap'}"]
    if str(mode) == "bulk":
        strategy_label = "Sırayla Dağıt" if strategy == "round_robin" else "Her Videoyu Tüm Hesaplarda Paylaş"
        parts.append(f"Paylaşım Stratejisi: {strategy_label}")
    parts.append(f"Hesap Döngü: {'Açık' if strategy == 'round_robin' and str(mode) == 'bulk' else 'Kapalı'}")
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
    temiz_defaults = {
        "aciklama": "",
        "baslik": "",
        "platform": "",
        "zamanlama": "",
        "video_kaynak": "",
        "kaynak_secim": "Link",
    }
    for key in ("aciklama", "baslik", "platform", "zamanlama", "video_kaynak", "kaynak_secim"):
        hedef = yollar.get(key, "")
        if hedef:
            ok_list.append(sosyal_medya_write_text(hedef, temiz_defaults.get(key, "")))

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


SOCIAL_MEDIA_OLD_UPLOAD_CLEANUP_DAYS = 30


def _load_sosyal_medya_runtime_module(script_path: str):
    target_path = os.path.abspath(str(script_path or "").strip())
    if not target_path:
        raise FileNotFoundError("Sosyal medya script yolu bulunamadı.")
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Sosyal medya script yolu geçersiz: {target_path}")

    module_name = f"_sosyal_medya_runtime_{abs(hash(target_path))}"
    spec = importlib.util.spec_from_file_location(module_name, target_path)
    if spec is None or spec.loader is None:
        raise ImportError("Sosyal medya modülü yüklenemedi.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sosyal_medya_temizle_eski_yuklemeler(older_than_days: int = SOCIAL_MEDIA_OLD_UPLOAD_CLEANUP_DAYS) -> tuple[bool, str]:
    yollar = sosyal_medya_ensure_files()
    script_path = str(yollar.get("script") or "").strip()

    try:
        module = _load_sosyal_medya_runtime_module(script_path)
    except Exception as e:
        msg = f"Temizleme modülü açılamadı: {e}"
        log(f"[ERROR] {msg}")
        return False, msg

    cleanup_fn = getattr(module, "cleanup_old_storage_uploads", None)
    if not callable(cleanup_fn):
        msg = "Sosyal medya scriptinde R2 temizleme desteği bulunamadı."
        log(f"[ERROR] {msg}")
        return False, msg

    try:
        result = cleanup_fn(older_than_days=older_than_days)
    except Exception as e:
        msg = f"Eski paylaşımlar temizlenemedi: {e}"
        log(f"[ERROR] {msg}")
        return False, msg

    if not isinstance(result, dict):
        msg = "Temizleme sonucu okunamadı."
        log(f"[ERROR] {msg}")
        return False, msg

    errors = [str(item).strip() for item in (result.get("errors") or []) if str(item).strip()]
    for err in errors[:3]:
        log(f"[WARN] R2 temizleme uyarısı: {err}")

    bucket = str(result.get("bucket") or "").strip()
    prefix = str(result.get("prefix") or "").strip()
    deleted = int(result.get("deleted") or 0)
    matched = int(result.get("matched") or 0)
    message = str(result.get("message") or "").strip()
    suffix = []
    if bucket:
        suffix.append(f"bucket={bucket}")
    if prefix:
        suffix.append(f"prefix={prefix}")
    suffix_text = f" ({', '.join(suffix)})" if suffix else ""

    if result.get("ok"):
        if matched == 0:
            log(f"[INFO] R2 eski paylaşım temizliği tamamlandı: {older_than_days} günden eski dosya bulunamadı{suffix_text}")
        elif errors:
            log(f"[WARN] R2 eski paylaşım temizliği kısmen tamamlandı: {deleted}/{matched} dosya silindi{suffix_text}")
        else:
            log(f"[OK] R2 eski paylaşım temizliği tamamlandı: {deleted} dosya silindi{suffix_text}")
        return True, message or "Temizlik tamamlandı."

    msg = message or "Eski paylaşımlar temizlenemedi."
    log(f"[ERROR] {msg}")
    return False, msg


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
        has_saved_accounts = _rows_have_saved_account(cfg_rows)
        default_loop_state = True if not has_saved_accounts else bool(cfg.get("loop_accounts", True))
        st.session_state["sm_hesap_dongu"] = default_loop_state

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

_VIDEO_PREVIEW_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v')
_IMAGE_PREVIEW_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
_MEDIA_PREVIEW_EXTENSIONS = _VIDEO_PREVIEW_EXTENSIONS + _IMAGE_PREVIEW_EXTENSIONS

def _preview_extensions_for_kind(media_kind: str | None = None):
    kind = str(media_kind or "").strip().lower()
    if kind == "video":
        return _VIDEO_PREVIEW_EXTENSIONS
    if kind in ("gorsel", "image"):
        return _IMAGE_PREVIEW_EXTENSIONS
    return _MEDIA_PREVIEW_EXTENSIONS

def _list_media_preview_entries(dir_path: str, media_kind: str | None = None):
    if not dir_path or not os.path.isdir(dir_path):
        return []

    medya_uzantilari = _preview_extensions_for_kind(media_kind)
    entries = []

    for root, _, files in os.walk(dir_path):
        for file_name in files:
            if not file_name.lower().endswith(medya_uzantilari):
                continue

            tam_yol = os.path.join(root, file_name)
            rel_yol = os.path.relpath(tam_yol, dir_path)
            rel_yol_ui = rel_yol.replace(os.sep, "/")
            parcalar = rel_yol_ui.split("/")
            etiket = parcalar[0] if len(parcalar) > 1 else os.path.splitext(file_name)[0]
            if len(etiket) > 40:
                etiket = etiket[:37] + "..."

            entries.append({
                "label_base": etiket,
                "label": etiket,
                "path": tam_yol,
                "rel_path": rel_yol,
                "nested": root != dir_path,
            })

    entries.sort(key=lambda item: natural_sort_key(item["rel_path"].replace(os.sep, "/")))

    toplamlar = {}
    for item in entries:
        base_label = item["label_base"]
        toplamlar[base_label] = toplamlar.get(base_label, 0) + 1

    sayaclar = {}
    for item in entries:
        base_label = item["label_base"]
        if toplamlar.get(base_label, 0) > 1:
            sayaclar[base_label] = sayaclar.get(base_label, 0) + 1
            item["label"] = f"{base_label} ({sayaclar[base_label]})"

    return entries

def _list_media_files_clean(dir_path: str, media_kind: str | None = None):
    return [
        (item["label"], item["path"], False)
        for item in _list_media_preview_entries(dir_path, media_kind)
    ]

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

def reset_txt_file(txt_path: str, default_text: str = ""):
    if not _is_safe_path(txt_path): return False
    try:
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("" if default_text is None else str(default_text))
        return True
    except: return False


def _reset_json_file(json_path: str, payload) -> bool:
    if not _is_safe_path(json_path):
        return False
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _remove_file_if_exists_safe(file_path: str) -> bool:
    if not file_path or not _is_safe_path(file_path):
        return False
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return True
    except Exception:
        return False


def _count_real_prompt_links(path: str | None = None) -> int:
    links_file = (path or st.session_state.settings.get("links_file", "") or "").strip()
    if not links_file or not os.path.exists(links_file):
        return 0
    try:
        with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
            return len([ln for ln in f.read().splitlines() if ln.strip()])
    except Exception:
        return 0


def _safe_count_from_function(function_name: str) -> int:
    fn = globals().get(function_name)
    if not callable(fn):
        return 0
    try:
        return max(0, int(fn() or 0))
    except Exception:
        return 0


def _has_real_video_input_source() -> bool:
    return (
        _count_real_prompt_links() > 0
        or _safe_count_from_function("_count_download_videos") > 0
        or _safe_count_from_function("_count_added_videos") > 0
    )


def _empty_source_placeholder_active() -> bool:
    try:
        return os.path.exists(EMPTY_SOURCE_PLACEHOLDER_FILE) and not _has_real_video_input_source()
    except Exception:
        return False


def _clear_empty_source_placeholder():
    try:
        if os.path.exists(EMPTY_SOURCE_PLACEHOLDER_FILE):
            os.remove(EMPTY_SOURCE_PLACEHOLDER_FILE)
    except Exception:
        pass


def _is_empty_source_placeholder_item(item: dict | None) -> bool:
    return bool((item or {}).get("placeholder"))


def _write_json_payload_safe(path: str, payload: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        try:
            log(f"[WARN] Kontrol JSON yazilamadi: {path} -> {e}")
        except Exception:
            pass
        return False


def _empty_video_montaj_preset_payload() -> dict:
    return {
        "selection_text": "T",
        "format_choice": "D",
        "muzik_seviyesi": "15",
        "ses_efekti_seviyesi": "15",
        "orijinal_ses_seviyesi": "100",
        "video_ses_seviyesi": "100",
        "baslik": "",
        "source_mode": "Mevcut Videolar",
        "orijinal_ses_kaynak_sirasi": "",
        "placeholder": True,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _empty_toplu_video_preset_payload() -> dict:
    payload = _empty_video_montaj_preset_payload()
    payload["source_selection_text"] = "T"
    payload["production_limit"] = 0
    return payload


def _seed_empty_source_placeholder_state():
    settings_obj = st.session_state.get("settings", {}) or {}
    now_text = time.strftime("%Y-%m-%d %H:%M:%S")

    _write_json_payload_safe(
        EMPTY_SOURCE_PLACEHOLDER_FILE,
        {
            "kind": "empty_source_placeholder",
            "source_mode": PROMPT_SOURCE_LINK,
            "created_at": now_text,
        },
    )

    for text_path in (
        settings_obj.get("links_file", ""),
        settings_obj.get("video_prompt_links_file", ""),
    ):
        try:
            if text_path:
                os.makedirs(os.path.dirname(text_path), exist_ok=True)
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write("\n")
        except Exception:
            pass

    _write_prompt_source_mode(PROMPT_SOURCE_LINK)
    st.session_state["link_canvas_source"] = "manual"
    _write_json_payload_safe(
        os.path.join(CONTROL_DIR, "prompt_input_selection.json"),
        {"mode": "all", "selected_items": {"links": [], "downloaded_videos": [], "added_videos": []}, "saved_at": now_text},
    )
    _write_json_payload_safe(
        os.path.join(CONTROL_DIR, "video_prompt_selection.json"),
        {"mode": "all", "selected_prompt_folders": [], "saved_at": now_text},
    )
    _write_json_payload_safe(VIDEO_KLONLA_CONTROL_PATH, _video_klonla_default_state())
    _write_json_payload_safe(os.path.join(CONTROL_DIR, "video_montaj_preset.json"), _empty_video_montaj_preset_payload())
    _write_json_payload_safe(os.path.join(CONTROL_DIR, "toplu_video_preset.json"), _empty_toplu_video_preset_payload())


def _reset_dialog_defaults_after_full_cleanup():
    _reset_complex_dialog_lazy_state()

    st.session_state["sm_video_kaynak_secim"] = "Link"
    st.session_state["toplu_video_source_mode"] = "Mevcut Videolar"
    st.session_state["toplu_video_source_selection_text"] = "T"
    st.session_state["toplu_video_selection_text"] = "T"
    st.session_state["toplu_video_format"] = "D"
    st.session_state["toplu_video_production_limit"] = 0
    st.session_state["tv_muzik_seviyesi"] = "15"
    st.session_state["tv_ses_efekti_seviyesi"] = "15"
    st.session_state["tv_orijinal_ses_seviyesi"] = "100"
    st.session_state["tv_video_ses_seviyesi"] = "100"
    st.session_state["tv_orijinal_ses_kaynak_sirasi"] = ""
    st.session_state["tv_baslik"] = ""
    st.session_state["tv_custom_override"] = ""

    st.session_state["video_montaj_source_mode"] = "Mevcut Videolar"
    st.session_state["video_montaj_selection_text"] = "T"
    st.session_state["video_montaj_format"] = "D"
    st.session_state["vm_custom_override"] = ""
    st.session_state["vm_muzik_seviyesi"] = "15"
    st.session_state["vm_ses_efekti_seviyesi"] = "15"
    st.session_state["vm_orijinal_ses_seviyesi"] = "100"
    st.session_state["vm_video_ses_seviyesi"] = "100"
    st.session_state["vm_orijinal_ses_kaynak_sirasi"] = ""
    st.session_state["vm_baslik"] = ""

    st.session_state["vk_mode_widget"] = "Video"
    st.session_state["vk_model_widget"] = "Motion Control"

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


def _repair_control_state_files():
    prompt_input_default = {
        "mode": "all",
        "selected_items": {"links": [], "downloaded_videos": [], "added_videos": []},
    }

    prompt_source_path = PROMPT_SOURCE_MODE_FILE
    try:
        prompt_source_raw = ""
        if prompt_source_path and os.path.exists(prompt_source_path):
            with open(prompt_source_path, "r", encoding="utf-8", errors="ignore") as f:
                prompt_source_raw = f.read().strip()
        if prompt_source_path and os.path.exists(prompt_source_path) and not prompt_source_raw:
            reset_txt_file(prompt_source_path, "auto")
    except Exception:
        pass

    for preset_path in (
        os.path.join(CONTROL_DIR, "video_montaj_preset.json"),
        os.path.join(CONTROL_DIR, "toplu_video_preset.json"),
    ):
        try:
            if preset_path and os.path.exists(preset_path) and os.path.getsize(preset_path) == 0:
                _remove_file_if_exists_safe(preset_path)
        except Exception:
            pass

    prompt_input_path = os.path.join(CONTROL_DIR, "prompt_input_selection.json")
    try:
        prompt_input_raw = ""
        if os.path.exists(prompt_input_path):
            with open(prompt_input_path, "r", encoding="utf-8", errors="ignore") as f:
                prompt_input_raw = f.read().strip()
        if os.path.exists(prompt_input_path) and not prompt_input_raw:
            _reset_json_file(prompt_input_path, prompt_input_default)
    except Exception:
        pass

    try:
        vk_raw = ""
        if os.path.exists(VIDEO_KLONLA_CONTROL_PATH):
            with open(VIDEO_KLONLA_CONTROL_PATH, "r", encoding="utf-8", errors="ignore") as f:
                vk_raw = f.read().strip()
        if os.path.exists(VIDEO_KLONLA_CONTROL_PATH) and not vk_raw:
            _reset_json_file(VIDEO_KLONLA_CONTROL_PATH, _video_klonla_default_state())
    except Exception:
        pass

    try:
        if _empty_source_placeholder_active() or not _has_real_video_input_source():
            _seed_empty_source_placeholder_state()
        else:
            _clear_empty_source_placeholder()
    except Exception:
        pass


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
        s.get("klon_video_dir"),
        s.get("video_klonla_dir"),
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

    # TXT / state dosyaları
    txt_targets = [
        (s.get("links_file"), "\n"),
        (s.get("video_prompt_links_file"), "\n"),
        (s.get("gorsel_duzelt_txt"), ""),
        (s.get("prompt_duzeltme_txt"), ""),
        (PROMPT_SOURCE_MODE_FILE, "auto"),
    ]
    # istem.txt özellikle hariç tutulur; Dosya Yöneticisi'nden sadece düzenlenebilir.

    for path, default_text in txt_targets:
        try:
            if path:
                reset_txt_file(path, default_text)
        except Exception as e:
            log(f"[WARN] TXT sıfırlanamadı: {path} -> {e}")

    for preset_path in (
        os.path.join(CONTROL_DIR, "video_montaj_preset.json"),
        os.path.join(CONTROL_DIR, "toplu_video_preset.json"),
    ):
        try:
            _remove_file_if_exists_safe(preset_path)
        except Exception as e:
            log(f"[WARN] Preset dosyası temizlenemedi: {preset_path} -> {e}")

    try:
        _reset_json_file(
            os.path.join(CONTROL_DIR, "prompt_input_selection.json"),
            {"mode": "all", "selected_items": {"links": [], "downloaded_videos": [], "added_videos": []}},
        )
    except Exception as e:
        log(f"[WARN] Prompt seçim durumu sıfırlanamadı: {e}")

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

    try:
        cleanup_social_media_state_files(clear_saved_plan=True, preserve_accounts=True)
    except Exception:
        pass

    try:
        _clear_video_settings_overrides(reset_widgets=True)
    except Exception:
        pass
    try:
        _seed_empty_source_placeholder_state()
    except Exception as e:
        log(f"[WARN] Bos kaynak placeholder durumu hazirlanamadi: {e}")

    # Oturum verilerini sifirla (Görsel Oluşturma vb.)
    keys_to_del = [k for k in st.session_state.keys() if k.startswith(("go_gp", "go_gs", "go_vp", "go_vs", "go_vid"))]
    for k in keys_to_del:
        del st.session_state[k]
    st.session_state.go_gorsel_count = 1
    st.session_state.go_vid_count = 1

    _reset_dialog_defaults_after_full_cleanup()

    log("[OK] Toplu temizlik tamamlandı.")


_repair_control_state_files()

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
    count = _count_real_prompt_links(st.session_state.settings.get("links_file", ""))
    if count == 0 and _empty_source_placeholder_active():
        return 1
    return count


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

    klon_actual_by_no = {}
    if klon_root and os.path.isdir(klon_root):
        for item in os.listdir(klon_root):
            item_path = os.path.join(klon_root, item)
            if not os.path.isdir(item_path):
                continue

            m = re.match(r'^(?:Klon\s+)?Video\s+(\d+)$', item, re.IGNORECASE)
            if not m:
                continue

            clone_no = int(m.group(1))
            media_files = []
            for fname in os.listdir(item_path):
                if fname.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                    media_files.append(os.path.join(item_path, fname))

            media_files.sort(key=lambda p: _video_montaj_sort_key(os.path.basename(p)))
            if media_files:
                klon_actual_by_no[clone_no] = {
                    "folder_name": item,
                    "path": media_files[0],
                    "exists": True,
                    "clone_no": clone_no,
                }

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
            is_placeholder_item = _empty_source_placeholder_active() and link_count == 1 and video_no == 1
            all_videos.append({
                "token": str(display_no),
                "script_token": str(display_no - 1),
                "label": "Kaynak Bekleniyor" if is_placeholder_item else f"[{display_no}] Link Video {video_no}",
                "path": "",
                "exists": False,
                "expected": True,
                "video_no": video_no,
                "source_kind": "link",
                "placeholder": is_placeholder_item,
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

    klon_videos = []
    planned_klon_count = _planned_video_klonla_output_count()

    if planned_klon_count > 0:
        for clone_no in range(1, planned_klon_count + 1):
            actual_entry = klon_actual_by_no.get(clone_no)
            klon_videos.append({
                "token": str(clone_no),
                "script_token": str(clone_no - 1),
                "label": f"[{clone_no}] Klon Video {clone_no}",
                "path": (actual_entry or {}).get("path", ""),
                "exists": bool(actual_entry and actual_entry.get("path")),
                "expected": not bool(actual_entry and actual_entry.get("path")),
                "clone_no": clone_no,
                "source_kind": "clone",
            })
    else:
        for display_idx, clone_no in enumerate(sorted(klon_actual_by_no.keys()), start=1):
            actual_entry = klon_actual_by_no.get(clone_no) or {}
            klon_videos.append({
                "token": str(display_idx),
                "script_token": str(display_idx - 1),
                "label": f"[{display_idx}] Klon Video {clone_no}",
                "path": actual_entry.get("path", ""),
                "exists": bool(actual_entry.get("path")),
                "expected": False,
                "clone_no": clone_no,
                "source_kind": "clone",
            })

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
        "clone_videos": klon_videos,
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

    parts = [p.strip() for p in re.split(r'[\s,.;]+', raw) if p.strip()]
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
        parts = [p.strip() for p in re.split(r'[\s,.;]+', custom_text) if p.strip()]
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

    parts = [p.strip() for p in re.split(r'[\s,.;]+', raw) if p.strip()]
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
    def toplu_video_preset_kaydet(selection_text: str, format_choice: str, source_selection_text: str = "T", muzik_seviyesi: str = "", ses_efekti_seviyesi: str = "", baslik: str = "", source_mode: str = "Mevcut Videolar", orijinal_ses_seviyesi: str = "", video_ses_seviyesi: str = "", orijinal_ses_kaynak_sirasi: str = "", production_limit=0) -> bool:
        try:
            os.makedirs(os.path.dirname(TOPLU_VIDEO_PRESET_FILE), exist_ok=True)
            muzik_seviyesi = _vm_normalize_percent_text(muzik_seviyesi, 15)
            ses_efekti_seviyesi = _vm_normalize_percent_text(ses_efekti_seviyesi, 15)
            orijinal_ses_seviyesi = _vm_normalize_percent_text(orijinal_ses_seviyesi, 100)
            video_ses_seviyesi = _vm_normalize_percent_text(video_ses_seviyesi, 100)
            baslik = (baslik or "").strip()
            orijinal_ses_kaynak_sirasi = _orijinal_ses_kaynak_sirasi_normalize(orijinal_ses_kaynak_sirasi)
            production_limit = _toplu_video_uretim_limiti_normalize(production_limit)
            payload = {
                "selection_text": (selection_text or "T").strip(),
                "format_choice": (format_choice or "D").strip().upper(),
                "source_selection_text": (source_selection_text or "T").strip().upper() or "T",
                "source_mode": _normalize_toplu_video_source_mode(source_mode),
                "production_limit": production_limit,
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
            with open(os.path.join(CONTROL_DIR, "toplu_video_runtime_limit.txt"), "w", encoding="utf-8") as f:
                f.write(str(production_limit or 0))

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
            with open(os.path.join(CONTROL_DIR, "toplu_video_runtime_limit.txt"), "w", encoding="utf-8") as f:
                f.write("0")
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
            st.session_state["toplu_video_production_limit"] = _toplu_video_uretim_limiti_normalize(preset.get("production_limit", preset.get("uretim_limiti", 0)))
            st.session_state["tv_muzik_seviyesi"] = preset.get("muzik_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["muzik_ses"], "15"))
            st.session_state["tv_ses_efekti_seviyesi"] = preset.get("ses_efekti_seviyesi", _tv_bootstrap_read_text_file(materyal_paths["ses_efekti_ses"], "15"))
            st.session_state["tv_orijinal_ses_seviyesi"] = preset.get("orijinal_ses_seviyesi", "100")
            st.session_state["tv_video_ses_seviyesi"] = preset.get("video_ses_seviyesi", "100")
            st.session_state["tv_orijinal_ses_kaynak_sirasi"] = preset.get("orijinal_ses_kaynak_sirasi", st.session_state.get("tv_orijinal_ses_kaynak_sirasi", ""))
            st.session_state["tv_baslik"] = preset.get("baslik", _tv_bootstrap_read_text_file(materyal_paths["baslik"], ""))
        else:
            st.session_state.setdefault("toplu_video_source_mode", "Mevcut Videolar")
            st.session_state.setdefault("toplu_video_production_limit", 0)
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

    tv_source_options = ["Mevcut Videolar", "Eklenen Video", "Görsel Oluştur", "Klon Video"]
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
    elif st.session_state.toplu_video_source_mode == "Klon Video":
        video_items = assets.get("clone_videos", [])
        kaynak_baslik = "**🎬 Klon Video kaynakları:**"
        kaynak_bilgi = "Bu modda Video Klonla ekranında kaydettiğiniz görevlerden üretilecek klon videolar kaynak olarak kullanılır."
    else:
        video_items = assets.get("videos", [])
        kaynak_baslik = "**🎬 Kaynak videolar:**"
        kaynak_bilgi = "Bu modda mevcut normal ve indirilen videolar kullanılır."

    has_existing_source_video = any(item.get("exists") for item in video_items)

    st.markdown("---")
    st.markdown(kaynak_baslik)
    st.caption(kaynak_bilgi)
    if st.session_state.toplu_video_source_mode == "Görsel Oluştur" and video_items and not has_existing_source_video:
        st.info("Kayitli hareketlendirme promptlari kaynak listesine eklendi. Tumunu Calistir akisinda once bu videolar uretilir, sonra Toplu Video Montaj bu ciktilari kullanir.")
    elif st.session_state.toplu_video_source_mode == "Klon Video" and video_items and not has_existing_source_video:
        st.info("Kayitli Klon Video gorevleri kaynak listesine eklendi. Tumunu Calistir akisinda once Klon Video uretilir, sonra Toplu Video Montaj bu ciktilari kullanir.")
    elif st.session_state.toplu_video_source_mode == "Eklenen Video" and video_items and not has_existing_source_video:
        st.info("Kayitli bolum planlari kaynak listesine eklendi. Tumunu Calistir akisinda once Video Indir tamamlanir, sonra bu planlar Eklenen Video olarak olusturulur.")
    tv_pick_prefix = f"tv_pick_{st.session_state.toplu_video_source_mode}"
    onceki_kaynak_text = (st.session_state.get("toplu_video_source_selection_text", "T") or "T").strip().upper() or "T"
    onceki_kaynak_tokenleri = set(_toplu_video_source_secim_to_tokens(onceki_kaynak_text, video_items))
    placeholder_items = [item for item in video_items if _is_empty_source_placeholder_item(item)]
    if video_items:
        for item in video_items:
            if _is_empty_source_placeholder_item(item):
                continue
            st.checkbox(
                item["label"],
                key=f"{tv_pick_prefix}_{item['token']}",
                value=(str(item["token"]) in onceki_kaynak_tokenleri) or (onceki_kaynak_text == "T"),
            )
    else:
        st.info("Toplu montaj için uygun video bulunamadı.")
    if placeholder_items:
        st.caption("Kaynak eklendiğinde ilk slot otomatik dolacak.")

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
    uretim_limiti = 0
    if uretilecek_video_sayisi is None:
        st.warning("Toplu Video scripti 2 ile 20 arası kaynak video sayısını destekliyor. Bu yüzden üretilecek video sayısı burada hesaplanamadı.")
    else:
        st.caption(f"📊 Bu seçimle üretilecek toplam video sayısı: {uretilecek_video_sayisi}")
        if uretilecek_video_sayisi > 0:
            varsayilan_limit = _toplu_video_uretim_limiti_normalize(
                st.session_state.get("toplu_video_production_limit", 0),
                uretilecek_video_sayisi,
            ) or int(uretilecek_video_sayisi)
            st.session_state["toplu_video_production_limit"] = varsayilan_limit
            uretim_limiti = int(st.number_input(
                "🎯 Üretilecek Video Sayısı",
                min_value=1,
                max_value=int(uretilecek_video_sayisi),
                value=int(varsayilan_limit),
                step=1,
                key="toplu_video_production_limit",
                help="Toplu Video Montaj bu sayıya ulaşınca işlemi tamamlar. Sosyal Medya Paylaşım bölümü de kaydedilen bu sayıyı baz alır.",
            ))
            st.caption(f"📌 Üretim limiti: {uretim_limiti}/{uretilecek_video_sayisi} video")
        else:
            st.caption("Üretilecek video sayısı 0 olduğu için limit alanı pasif.")

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
                uretim_limiti,
            ):
                st.session_state["tv_saved"] = True
            st.session_state.ek_dialog_open = "toplu_video"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with a2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("🗑️ Kayıt Temizle", key="tv_clear_saved_btn", use_container_width=True):
            globals().get("toplu_video_preset_sil", lambda *args, **kwargs: False)()
            st.session_state["toplu_video_production_limit"] = 0
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
        st.session_state.toplu_video_production_limit = uretim_limiti
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

    # Kaynak modu seçimi: Mevcut Videolar, Eklenen Video, Görsel Oluştur veya Klon Video
    vm_source_options = ["Mevcut Videolar", "Eklenen Video", "Görsel Oluştur", "Klon Video"]
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
    elif st.session_state.video_montaj_source_mode == "Klon Video":
        assets = _list_video_montaj_assets()
        video_items = assets.get("clone_videos", [])
        image_items = assets["images"]
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
    elif st.session_state.video_montaj_source_mode == "Klon Video":
        st.markdown("**🎬 Klon Video kaynakları:**")
        st.caption("Bu modda Video Klonla ekranında kaydettiğiniz görevlerden üretilecek klon videolar kaynak olarak kullanılır.")
    else:
        st.markdown("**🎬 Mevcut videolar:**")
        st.caption("Bu modda mevcut ve indirilen videolar Video Montaj için kaynak olarak kullanılır.")
    if st.session_state.video_montaj_source_mode == "Görsel Oluştur" and video_items and not has_real_video_items:
        st.info("Kayitli hareketlendirme promptlari kaynak listesine eklendi. Tumunu Calistir akisinda once bu videolar uretilir, sonra Video Montaj bu ciktilari kullanir.")
    elif st.session_state.video_montaj_source_mode == "Klon Video" and video_items and not has_real_video_items:
        st.info("Kayitli Klon Video gorevleri kaynak listesine eklendi. Tumunu Calistir akisinda once Klon Video uretilir, sonra Video Montaj bu ciktilari kullanir.")
    elif st.session_state.video_montaj_source_mode == "Eklenen Video" and video_items and not has_real_video_items:
        st.info("Kayitli bolum planlari kaynak listesine eklendi. Tumunu Calistir akisinda once Video Indir tamamlanir, sonra bu planlar Eklenen Video olarak olusturulur.")
    vm_pick_prefix = f"vm_pick_{st.session_state.video_montaj_source_mode}"
    placeholder_items = [item for item in video_items if _is_empty_source_placeholder_item(item)]
    if video_items:
        for item in video_items:
            if _is_empty_source_placeholder_item(item):
                continue
            st.checkbox(item["label"], key=f"{vm_pick_prefix}_{item['token']}")
    else:
        st.info("Montaj için uygun video bulunamadı.")
    if placeholder_items:
        st.caption("Kaynak eklendiğinde ilk slot otomatik dolacak.")

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
    def _rerun_dosya_yoneticisi():
        st.session_state.last_dialog_align = "right"
        st.session_state.ek_dialog_open = "dosya_yoneticisi"
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["🔍 İncele & Seçerek Sil", "🧹 Toplu Temizlik", "📦 Ekle & Çıkar"])
    
    with tab1:
        st.caption("Ürettiğiniz medyaları izleyin/görüntüleyin ve beğenmediklerinizi silin.")
        s = st.session_state.settings
        
        kategoriler = {
            "🎬 Toplu Montaj Videoları": s.get("toplu_video_output_dir"),
            "🎞️ Montaj Videoları":      s.get("video_montaj_output_dir"),
            "🎬 Üretilen Videolar":      s.get("video_output_dir"),
            "🎬 Klon Videolar":         s.get("klon_video_dir") or s.get("video_klonla_dir"),
            "📝 Promptlar":              s.get("prompt_dir"),
            "🖼️ Oluşturulan Görseller": s.get("gorsel_olustur_dir"),
            "🎨 Klon Görseller":        s.get("klon_gorsel_dir"),
            "🖼️ Görsel Analiz":         s.get("gorsel_analiz_dir"),
            "⬇️ İndirilen Videolar":    s.get("download_dir"),
            "🎞️ Eklenen Videolar":     s.get("added_video_dir"),
            "🧾 Prompt İstem":          s.get("prompt_istem_txt") or DEFAULT_SETTINGS.get("prompt_istem_txt", ""),
        }
        
        secilen_kategori = st.selectbox("Kategori Seçin:", list(kategoriler.keys()), key="fileman_cat")
        # Kategori değişince dosya index'ini sıfırla
        if st.session_state.get("fileman_cat_prev") != secilen_kategori:
            st.session_state["fileman_cat_prev"] = secilen_kategori
            st.session_state["fileman_file_idx"] = 0
        hedef_klasor = kategoriler[secilen_kategori]

        if secilen_kategori == "🧾 Prompt İstem":
            txt_yolu = str(hedef_klasor or "").strip()
            if txt_yolu:
                st.markdown("---")
                st.markdown("**📄 istem.txt**")
                st.caption("Bu dosya yalnızca düzenlenir; silme ve toplu temizlik işlemlerine dahil edilmez.")

                _rb1, _rb2, _rb3 = st.columns([0.22, 0.28, 0.5])
                with _rb1:
                    if st.button("🔄 Yenile", key="btn_prompt_istem_reload", use_container_width=True):
                        st.session_state.pop("prompt_istem_edit", None)
                        ver = st.session_state.get("prompt_istem_widget_ver", 0)
                        st.session_state["prompt_istem_widget_ver"] = ver + 1
                        st.session_state.pop("prompt_istem_bildirim", None)
                        _rerun_dosya_yoneticisi()
                with _rb2:
                    _kopya_aktif = st.session_state.get("prompt_istem_kopya_goster", False)
                    _kopya_label = "✖ Kopyalamayı Kapat" if _kopya_aktif else "📋 Kopyala"
                    if st.button(_kopya_label, key="btn_prompt_istem_kopya", use_container_width=True):
                        st.session_state["prompt_istem_kopya_goster"] = not _kopya_aktif
                        _rerun_dosya_yoneticisi()

                try:
                    if os.path.exists(txt_yolu):
                        with open(txt_yolu, "r", encoding="utf-8") as f:
                            icerik = f.read()
                    else:
                        icerik = ""
                    edit_key = "prompt_istem_edit"
                    widget_ver = st.session_state.get("prompt_istem_widget_ver", 0)
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = icerik
                    duzenlenen = st.text_area(
                        "📄 istem.txt içeriği:",
                        value=st.session_state[edit_key],
                        height=280,
                        key=f"prompt_istem_preview_area_v{widget_ver}"
                    )
                    st.session_state[edit_key] = duzenlenen

                    if st.session_state.get("prompt_istem_kopya_goster", False):
                        st.markdown("**📋 Kopyalamak için aşağıdaki metni kullanın:**")
                        st.code(duzenlenen, language=None)
                except Exception as e:
                    st.error(f"Dosya okunamadı: {e}")
                    duzenlenen = ""

                ceviri_key = "prompt_istem_ceviri"
                bildirim_key = "prompt_istem_bildirim"
                c_save, c_reload2, c_tr = st.columns(3)
                with c_save:
                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                    if st.button("💾 Kaydet", use_container_width=True, key="btn_prompt_istem_kaydet"):
                        try:
                            os.makedirs(os.path.dirname(txt_yolu), exist_ok=True)
                            with open(txt_yolu, "w", encoding="utf-8") as f:
                                f.write(duzenlenen)
                            st.session_state["prompt_istem_edit"] = duzenlenen
                            st.session_state[bildirim_key] = ("ok", "✅ Kaydedildi!")
                        except Exception as e:
                            st.session_state[bildirim_key] = ("error", f"❌ Kaydedilemedi: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
                with c_reload2:
                    st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
                    if st.button("↺ Geri Al", use_container_width=True, key="btn_prompt_istem_gerial"):
                        st.session_state.pop("prompt_istem_edit", None)
                        ver = st.session_state.get("prompt_istem_widget_ver", 0)
                        st.session_state["prompt_istem_widget_ver"] = ver + 1
                        st.session_state[bildirim_key] = ("ok", "↺ Orijinal içeriğe döndürüldü.")
                        _rerun_dosya_yoneticisi()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c_tr:
                    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
                    _ceviri_yukleniyor = st.session_state.get("prompt_istem_ceviri_yukleniyor", False)
                    if st.button("🇹🇷 Çevir", use_container_width=True, key="btn_prompt_istem_cevir", disabled=_ceviri_yukleniyor):
                        api_key = st.session_state.settings.get("gemini_api_key", "").strip()
                        if not api_key:
                            st.session_state[bildirim_key] = ("warn", "⚠️ Çeviri için Ayarlar'dan Gemini API Key girin.")
                        elif not _GENAI_OK:
                            st.session_state[bildirim_key] = ("error", "❌ google-genai paketi yüklü değil.")
                        else:
                            st.session_state["prompt_istem_ceviri_yukleniyor"] = True
                            st.session_state["prompt_istem_ceviri_metin"] = st.session_state.get("prompt_istem_edit", duzenlenen)
                            _rerun_dosya_yoneticisi()
                    st.markdown('</div>', unsafe_allow_html=True)

                if st.session_state.get("prompt_istem_ceviri_yukleniyor", False):
                    with st.spinner("Çevriliyor..."):
                        try:
                            api_key = st.session_state.settings.get("gemini_api_key", "").strip()
                            client_tr = _genai.Client(api_key=api_key)
                            metin_cevrilecek = st.session_state.pop("prompt_istem_ceviri_metin", duzenlenen)
                            resp_tr = client_tr.models.generate_content(
                                model=TRANSLATION_MODEL,
                                contents=f"Aşağıdaki İngilizce prompt metnini Türkçeye çevir. Sadece çeviriyi yaz, başka hiçbir şey ekleme:\n\n{metin_cevrilecek}"
                            )
                            st.session_state[ceviri_key] = resp_tr.text
                            st.session_state[bildirim_key] = ("ok", "✅ Çeviri tamamlandı.")
                        except Exception as ex:
                            st.session_state[bildirim_key] = ("error", f"❌ Çeviri hatası: {ex}")
                    del st.session_state["prompt_istem_ceviri_yukleniyor"]
                    _rerun_dosya_yoneticisi()

                bildirim = st.session_state.get(bildirim_key)
                if bildirim and bildirim[0] not in ("copy_pending",):
                    tip, mesaj = bildirim
                    st.session_state.pop(bildirim_key, None)
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

                if st.session_state.get(ceviri_key):
                    st.markdown("---")
                    col_ceviri_title, col_ceviri_kapat = st.columns([0.8, 0.2])
                    with col_ceviri_title:
                        st.markdown("**🇹🇷 Türkçe Çeviri:**")
                    with col_ceviri_kapat:
                        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                        if st.button("✖ Kapat", use_container_width=True, key="btn_prompt_istem_ceviri_kapat"):
                            st.session_state.pop(ceviri_key, None)
                            _rerun_dosya_yoneticisi()
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.text_area("", value=st.session_state[ceviri_key], height=280, key="prompt_istem_ceviri_area", label_visibility="collapsed")
            else:
                st.warning("istem.txt yolu geçersiz veya ayarlanmamış.")

        # Promptlar kategorisi: klasör başına 1 prompt.txt göster
        elif secilen_kategori == "📝 Promptlar":
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
                            _rerun_dosya_yoneticisi()
                    with _rb2:
                        _kopya_aktif = st.session_state.get(f"prompt_kopya_goster_{yeni_idx}", False)
                        _kopya_label = "✖ Kopyalamayı Kapat" if _kopya_aktif else "📋 Kopyala"
                        if st.button(_kopya_label, key=f"btn_kopya_{yeni_idx}", use_container_width=True):
                            st.session_state[f"prompt_kopya_goster_{yeni_idx}"] = not _kopya_aktif
                            _rerun_dosya_yoneticisi()

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
                            _rerun_dosya_yoneticisi()
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
                                _rerun_dosya_yoneticisi()
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
                                _rerun_dosya_yoneticisi()
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
                                    model=TRANSLATION_MODEL,
                                    contents=f"Aşağıdaki İngilizce prompt metnini Türkçeye çevir. Sadece çeviriyi yaz, başka hiçbir şey ekleme:\n\n{metin_cevrilecek}"
                                )
                                st.session_state[ceviri_key] = resp_tr.text
                                st.session_state[bildirim_key] = ("ok", "✅ Çeviri tamamlandı.")
                            except Exception as ex:
                                st.session_state[bildirim_key] = ("error", f"❌ Çeviri hatası: {ex}")
                        del st.session_state[f"ceviri_yukleniyor_{yeni_idx}"]
                        _rerun_dosya_yoneticisi()

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
                                _rerun_dosya_yoneticisi()
                            st.markdown('</div>', unsafe_allow_html=True)
                        st.text_area("", value=st.session_state[ceviri_key], height=280, key=f"prompt_ceviri_area_{yeni_idx}", label_visibility="collapsed")
                else:
                    st.info("Henüz oluşturulmuş prompt bulunamadı.")
            else:
                st.warning("Prompt klasörü yolu geçersiz veya ayarlanmamış.")

        # Medya kategorileri: video / görsel
        else:
            if hedef_klasor and os.path.exists(hedef_klasor):
                medya_tipi = "video" if "Video" in secilen_kategori else "gorsel" if "Görsel" in secilen_kategori else None
                dosyalar = _list_media_preview_entries(hedef_klasor, medya_tipi)
                
                if dosyalar:
                    etiketler = [item["label"] for item in dosyalar]
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

                    secilen_kayit = dosyalar[yeni_idx]
                    secilen_dosya_rel = secilen_kayit["rel_path"]
                    secilen_dosya_tam = secilen_kayit["path"]
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
                            st.success("Dosya silindi!")
                            _rerun_dosya_yoneticisi()
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
            video_entries = _list_media_files_clean(s.get("video_output_dir"), "video")
            pick_video = st.multiselect("🎬 Üretilen Videolar", [e[0] for e in video_entries])
            klon_video_entries = _list_media_files_clean(s.get("klon_video_dir") or s.get("video_klonla_dir"), "video")
            pick_klon_video = st.multiselect("🎬 Klon Videolar", [e[0] for e in klon_video_entries])
            prompt_entries = _list_entries(s.get("prompt_dir"))
            pick_prompt = st.multiselect("📝 Promptlar", [e[0] for e in prompt_entries])
            gorsel_olustur_entries = _list_media_files_clean(s.get("gorsel_olustur_dir"), "gorsel")
            pick_gorsel_olustur = st.multiselect("🖼️ Oluşturulan Görseller", [e[0] for e in gorsel_olustur_entries])
            klon_entries = _list_media_files_clean(s.get("klon_gorsel_dir"), "gorsel")
            pick_klon = st.multiselect("🎨 Klon Görseller", [e[0] for e in klon_entries])
            gorsel_analiz_entries = _list_media_files_clean(s.get("gorsel_analiz_dir"), "gorsel")
            pick_gorsel_analiz = st.multiselect("🖼️ Görsel Analiz", [e[0] for e in gorsel_analiz_entries])
            indir_entries = _list_entries(s.get("download_dir"))
            pick_indir = st.multiselect("⬇️ İndirilen Videolar", [e[0] for e in indir_entries])

            # ── Görsel Klonlama TXT
            gorsel_duzelt_data = gorsel_duzelt_oku()
            gorsel_duzelt_options = [f"Görsel {no}: \"{_gorsel_klon_prompt_display_text(val)}\"" for no, val in sorted(gorsel_duzelt_data.items())]
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
                for n in pick_klon_video: _delete_path({name: p for name, p, _ in klon_video_entries}.get(n, ""))
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
                _rerun_dosya_yoneticisi()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            conf = st.checkbox("Evet, her şeyi sil")
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("🔥 Hepsini Temizle", use_container_width=True, disabled=not conf):
                clean_all_targets()
                log("[OK] Tüm dosyalar temizlendi.")
                st.session_state["dosya_yoneticisi_temizlendi_notice"] = "✅ Tüm dosyalar başarıyla temizlendi."
                _rerun_dosya_yoneticisi()
            st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.get("dosya_yoneticisi_temizlendi_notice"):
                st.success(st.session_state.pop("dosya_yoneticisi_temizlendi_notice"))
            
    with tab3:
        st.caption("Üretilen dosyaları dışarı çıkarın veya dışarıdan sisteme dosya ekleyin.")
        s = st.session_state.settings

        _ec_kategoriler = {
            "🎬 Üretilen Videolar": {"dir": s.get("video_output_dir", ""), "tip": "video", "prefix": "Video"},
            "🎬 Klon Videolar": {"dir": s.get("klon_video_dir", "") or s.get("video_klonla_dir", ""), "tip": "video", "prefix": "Video"},
            "🎬 Toplu Montaj Videoları": {"dir": s.get("toplu_video_output_dir", ""), "tip": "video", "prefix": "Toplu Montaj"},
            "🎞️ Montaj Videoları": {"dir": s.get("video_montaj_output_dir", ""), "tip": "video", "prefix": "Montaj"},
            "🎞️ Eklenen Videolar": {"dir": s.get("added_video_dir", ""), "tip": "video", "prefix": "Video"},
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
                _ec_medya_tipi = _ec_tip if _ec_tip in ("video", "gorsel") else None
                _ec_medya_dosyalari = _list_media_files_clean(_ec_hedef, _ec_medya_tipi)
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
        secs["video_indir"] = _batch_selection_checkbox("video_indir", "Video İndir seçimi", "chk_video_indir")
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
        secs["gorsel_analiz"] = _batch_selection_checkbox("gorsel_analiz", "Görsel Analiz seçimi", "chk_gorsel_analiz")
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
        secs["gorsel_klonla"] = _batch_selection_checkbox("gorsel_klonla", "Görsel Klonla seçimi", "chk_gorsel_klonla")
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
        secs["prompt_duzeltme"] = _batch_selection_checkbox("prompt_duzeltme", "Prompt Düzeltme seçimi", "chk_prompt_duzeltme")
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
        secs["gorsel_olustur"] = _batch_selection_checkbox("gorsel_olustur", "Görsel Oluştur seçimi", "chk_gorsel_olustur")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn_go:
        st.markdown('<div class="btn-teal">', unsafe_allow_html=True)
        if st.button("🖼️ Görsel Oluştur", key="dlg_btn_gorsel_olustur", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "gorsel_olustur"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    c_chk_vk, c_btn_vk = st.columns([0.12, 0.88])
    with c_chk_vk:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["video_klonla"] = _batch_selection_checkbox("video_klonla", "Video Klonla seçimi", "chk_video_klonla")
        st.markdown("</div>", unsafe_allow_html=True)
    with c_btn_vk:
        st.markdown('<div class="btn-teal">', unsafe_allow_html=True)
        if st.button("🎬 Video Klonla", key="dlg_btn_video_klonla", use_container_width=True, disabled=is_ui_locked()):
            st.session_state.ek_dialog_open = "video_klonla"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


    c_chk5, c_btn5 = st.columns([0.12, 0.88])
    with c_chk5:
        st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
        secs["video_montaj"] = _batch_selection_checkbox("video_montaj", "Video Montaj seçimi", "chk_video_montaj")
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
        secs["toplu_video"] = _batch_selection_checkbox("toplu_video", "Toplu Video seçimi", "chk_toplu_video")
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
        secs["sosyal_medya"] = _batch_selection_checkbox("sosyal_medya", "Sosyal Medya Paylaşım seçimi", "chk_sosyal_medya")
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


    @st.dialog("🎞️ Video Ekle", width="large", on_dismiss=_handle_ek_dialog_dismiss)
    def video_ekle_dialog():
        hedef_root = _get_added_video_dir()
        mevcutlar = _list_added_video_entries()
        planli_mevcutlar = _list_planned_added_video_entries() if not mevcutlar else []
        indirilenler = _list_download_video_entries()
        indirilen_harita = {
            str(item.get("video_path") or "").strip(): item
            for item in indirilenler
            if str(item.get("video_path") or "").strip()
        }
        link_girdileri = _read_video_link_entries()
        link_harita = {str(item.get("no")): item for item in link_girdileri}
        kayitli_bolum_plan_sayisi = _count_video_bolum_link_plans()

        st.caption("Bilgisayarınızdan video yükleyebilir veya indirilen videoları doğrudan bu listeye ekleyebilirsiniz. Ekle mevcut Eklenen Video içeriğini yeniler, Devamına Ekle ise yeni videoları mevcutların sonuna Video 1, Video 2, Video 3... sırasını bozmadan ekler.")
        plan_bilgi = f" | Kayitli bolum plani: {len(planli_mevcutlar)}" if planli_mevcutlar else ""
        st.info(f"Hedef klasör: {hedef_root} | Mevcut eklenen video: {len(mevcutlar)} | İndirilen video: {len(indirilenler)}{plan_bilgi}")
        st.caption("Not: Tek video seçerseniz Videoyu Bölümlerine Ayır ile parçalayabilirsiniz. Birden fazla video seçtiğinizde Ekle veya Devamına Ekle ile topluca aktarabilirsiniz.")

        secilenler = st.file_uploader(
            "Videoları seçin:",
            type=["mp4", "mov", "mkv", "webm", "avi", "m4v"],
            accept_multiple_files=True,
            key="dlg_video_ekle_files",
        )

        secili_indirilen_yollar = st.multiselect(
            "📥 İndirilen videolardan ekle:",
            options=list(indirilen_harita.keys()),
            default=[],
            format_func=lambda path: (
                f"İndirilen Video {indirilen_harita[path].get('no', '?')}"
            ) if path in indirilen_harita else os.path.basename(path),
            key="dlg_video_ekle_download_pick",
            disabled=not bool(indirilen_harita),
        )

        if not indirilen_harita:
            st.caption("İndirilen video bulunamadı. Önce ⬇️ Video İndir ile video indirirseniz burada doğrudan seçebilirsiniz.")

        secili_link_no = st.selectbox(
            "🔗 İndirilecek linkten bölüm planı hazırla:",
            options=[""] + list(link_harita.keys()),
            index=0,
            format_func=lambda no: (
                "Link seçin"
                if not no
                else (
                    f"Link Video {link_harita[no].get('no')} - "
                    f"{_video_bolum_shorten_url(link_harita[no].get('url'), 74)}"
                    + (" (plan kayıtlı)" if _video_bolum_plan_for_link(link_harita[no].get("no"), link_harita[no].get("url")) else "")
                )
            ),
            key="dlg_video_ekle_link_bolum_pick",
            disabled=not bool(link_harita),
        )
        if not link_harita:
            st.caption("Link bulunamadı. Önce Video Listesi Ekle bölümünden link ekleyin.")
        elif kayitli_bolum_plan_sayisi:
            st.caption(f"Kayıtlı bölüm planı: {kayitli_bolum_plan_sayisi}. Tümünü Çalıştır sırasında indirme bittikten sonra otomatik uygulanır.")
        if planli_mevcutlar:
            st.info("Kaydedilmiş bölüm planları bulundu. Bu planlar indirme adımından sonra otomatik olarak Eklenen Video klasörüne dönüştürülecek.")

        secili_kaynaklar = []
        for idx, up in enumerate(secilenler or [], start=1):
            dosya_adi = os.path.basename(str(getattr(up, "name", "") or f"video_{idx}.mp4"))
            secili_kaynaklar.append({
                "kind": "upload",
                "name": dosya_adi,
                "uploaded_file": up,
                "display_label": f"Bilgisayardan Yüklendi → {dosya_adi}",
            })

        for yol in secili_indirilen_yollar:
            item = indirilen_harita.get(yol)
            if not item:
                continue
            dosya_adi = os.path.basename(str(item.get("video_name") or os.path.basename(yol) or "video.mp4"))
            secili_kaynaklar.append({
                "kind": "download",
                "name": dosya_adi,
                "video_path": str(item.get("video_path") or "").strip(),
                "source_no": item.get("no"),
                "display_label": f"İndirilen Video {item.get('no', '?')}",
            })

        secili_link_kaynak = None
        if secili_link_no and secili_link_no in link_harita:
            link_item = link_harita[secili_link_no]
            secili_link_kaynak = {
                "kind": "link_plan",
                "name": f"Link Video {link_item.get('no')}",
                "source_no": link_item.get("no"),
                "url": str(link_item.get("url") or "").strip(),
                "display_label": f"Link Video {link_item.get('no')} → {_video_bolum_shorten_url(link_item.get('url'), 92)}",
            }

        if secili_kaynaklar:
            st.markdown("**Seçilen videolar:**")
            for idx, kaynak in enumerate(secili_kaynaklar, start=1):
                st.caption(f"{idx}. {kaynak['display_label']}")
        if secili_link_kaynak:
            st.markdown("**Bölüm planı hazırlanacak link:**")
            st.caption(secili_link_kaynak["display_label"])
        elif mevcutlar:
            st.markdown("**Klasördeki mevcut videolar:**")
            for item in mevcutlar:
                st.caption(f"{item['no']}. {item['folder_name']} → {item['video_name']}")
        elif planli_mevcutlar:
            st.markdown("**Kaydedilmiş bölüm planından oluşacak videolar:**")
            for item in planli_mevcutlar:
                st.caption(
                    f"{item['no']}. Link Video {item.get('source_no', '?')} → Bölüm {item.get('segment_no', '?')} "
                    f"({_format_mmss_ms(item.get('segment_start', 0.0))} - {_format_mmss_ms(item.get('segment_end', 0.0))})"
                )

        def _video_ekle_kaynagi_hedefe_yaz(kaynak: dict, hedef_yol: str):
            if str((kaynak or {}).get("kind") or "") == "download":
                source_path = str((kaynak or {}).get("video_path") or "").strip()
                if not source_path or not os.path.isfile(source_path):
                    raise FileNotFoundError("Seçilen indirilen video bulunamadı.")
                shutil.copy2(source_path, hedef_yol)
                return

            up = (kaynak or {}).get("uploaded_file")
            if up is None:
                raise ValueError("Yüklenen video okunamadı.")
            with open(hedef_yol, "wb") as f:
                f.write(up.getbuffer())

        def _kaydet_secilen_videolar(append_mode: bool = False):
            if not secili_kaynaklar:
                st.error("Lütfen en az bir video seçin veya indirilen videolardan ekleyin.")
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

                for offset, kaynak in enumerate(secili_kaynaklar):
                    video_no = baslangic_no + offset
                    klasor = os.path.join(hedef_root, f"Video {video_no}")
                    os.makedirs(klasor, exist_ok=True)
                    dosya_adi = os.path.basename(str(kaynak.get("name") or f"video_{video_no}.mp4"))
                    if not _is_supported_video_name(dosya_adi):
                        kok, ext = os.path.splitext(dosya_adi)
                        dosya_adi = (kok or f"video_{video_no}") + (ext if ext else ".mp4")
                    hedef_yol = os.path.join(klasor, dosya_adi)
                    _video_ekle_kaynagi_hedefe_yaz(kaynak, hedef_yol)

                _write_prompt_source_mode(PROMPT_SOURCE_ADDED_VIDEO)
                set_link_canvas_source("added_video")
                clear_placeholder = globals().get("_clear_empty_source_placeholder")
                if callable(clear_placeholder):
                    clear_placeholder()
                st.session_state.status["youtube_link"] = "idle"
                st.session_state.status["input"] = "ok"
                if append_mode:
                    son_no = baslangic_no + len(secili_kaynaklar) - 1
                    st.session_state["video_ekle_saved_notice"] = f"Kaydedildi! {len(secili_kaynaklar)} video mevcut listenin devamına eklendi (Video {baslangic_no}-Video {son_no})."
                else:
                    st.session_state["video_ekle_saved_notice"] = f"Kaydedildi! {len(secili_kaynaklar)} video Eklenen Video klasörüne aktarıldı."
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
            bolum_kaynaklari = list(secili_kaynaklar)
            if secili_link_kaynak:
                bolum_kaynaklari.append(secili_link_kaynak)

            if len(bolum_kaynaklari) != 1:
                st.error("Bölümlerine ayırmak için lütfen tek bir video veya tek bir link seçin.")
            else:
                kaynak = bolum_kaynaklari[0]
                if str(kaynak.get("kind") or "") == "link_plan":
                    st.session_state.video_bolum_source_kind = "link"
                    st.session_state.video_bolum_source_no = kaynak.get("source_no")
                    st.session_state.video_bolum_source_url = str(kaynak.get("url") or "").strip()
                    st.session_state.video_bolum_source_title = str(kaynak.get("name") or "").strip()
                    st.session_state.video_bolum_source_duration = 0.0
                    st.session_state.video_bolum_preview_url = ""
                    st.session_state.video_bolum_temp_path = None
                    st.session_state.video_bolum_temp_name = str(kaynak.get("name") or "Link Video")
                    st.session_state.video_bolum_sureler = []
                    st.session_state.pop("_dlg_bolum_pending_updates", None)
                    st.session_state.pop("_bolum_sayisi_prev", None)
                    st.session_state.pop("_bolum_sure_secim", None)
                    st.session_state.pop("_video_bolum_init_token", None)
                    st.session_state.ek_dialog_open = "video_bolumle"
                    st.rerun()

                temp_dir = os.path.join(CONTROL_DIR, "_temp_video_split")
                os.makedirs(temp_dir, exist_ok=True)
                dosya_adi = os.path.basename(str(kaynak.get("name") or "video.mp4"))
                if not _is_supported_video_name(dosya_adi):
                    kok, ext = os.path.splitext(dosya_adi)
                    dosya_adi = (kok or "video") + (ext if ext else ".mp4")
                temp_path = os.path.join(temp_dir, f"{int(time.time() * 1000)}_{dosya_adi}")
                try:
                    _video_ekle_kaynagi_hedefe_yaz(kaynak, temp_path)
                except Exception as e:
                    st.error(f"Bölümleme için video hazırlanamadı: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
                    return
                st.session_state.video_bolum_source_kind = "file"
                st.session_state.video_bolum_source_no = None
                st.session_state.video_bolum_source_url = ""
                st.session_state.video_bolum_source_title = ""
                st.session_state.video_bolum_source_duration = 0.0
                st.session_state.video_bolum_preview_url = ""
                st.session_state.video_bolum_temp_path = temp_path
                st.session_state.video_bolum_temp_name = dosya_adi
                st.session_state.video_bolum_sureler = []
                st.session_state.ek_dialog_open = "video_bolumle"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


@st.dialog("✂️ Videoyu Bölümlerine Ayır", width="large", on_dismiss=_handle_ek_dialog_dismiss)
def video_bolumlerine_ayir_dialog():
    hedef_root = _get_added_video_dir()
    temp_path = st.session_state.get("video_bolum_temp_path")
    temp_name = st.session_state.get("video_bolum_temp_name", "video.mp4")
    source_kind = str(st.session_state.get("video_bolum_source_kind") or "file").strip()
    is_link_source = source_kind == "link"
    source_no = st.session_state.get("video_bolum_source_no")
    source_url = str(st.session_state.get("video_bolum_source_url") or "").strip()
    video_source_token = temp_path or ""

    # Başarı bildirimi
    if st.session_state.get("video_bolum_saved_notice"):
        _vb_ph = st.empty()
        _vb_ph.success(st.session_state.get("video_bolum_saved_notice"))
        time.sleep(2.5)
        _vb_ph.empty()
        st.session_state.pop("video_bolum_saved_notice", None)

    if is_link_source:
        if not source_url:
            st.error("Bölümlenecek link bulunamadı. Lütfen önce Video Ekle bölümünden bir link seçin.")
            if st.button("⬅️ Geri", key="dlg_bolum_geri_link_hata", use_container_width=True):
                st.session_state.ek_dialog_open = "video_ekle"
                st.rerun()
            return

        video_source_token = f"link:{source_no}:{source_url}"
        with st.spinner("Link video bilgisi alınıyor..."):
            preview_info = _resolve_video_bolum_link_preview(source_url)
        preview_url = str(preview_info.get("preview_url") or source_url).strip()
        video_suresi = float(preview_info.get("duration") or 0.0)
        temp_name = str(preview_info.get("title") or st.session_state.get("video_bolum_source_title") or f"Link Video {source_no or ''}").strip() or "Link Video"
        st.session_state.video_bolum_preview_url = preview_url
        st.session_state.video_bolum_source_duration = video_suresi
        st.session_state.video_bolum_source_title = temp_name
    elif not temp_path or not os.path.isfile(temp_path):
        st.error("Bölümlenecek video bulunamadı. Lütfen önce Video Ekle bölümünden bir video seçin.")
        if st.button("⬅️ Geri", key="dlg_bolum_geri_hata", use_container_width=True):
            st.session_state.ek_dialog_open = "video_ekle"
            st.rerun()
        return
    else:
        video_source_token = temp_path
        # Video süresini al
        video_suresi = _get_video_duration_seconds(temp_path)

    if video_suresi <= 0:
        if is_link_source:
            st.error("Linkteki video süresi okunamadı. Önizleme için link bilgisi alınamadığından bölüm planı kaydedilemiyor.")
            hata = _resolve_video_bolum_link_preview(source_url).get("error") if source_url else ""
            if hata:
                st.caption(str(hata))
        else:
            st.error("Video süresi okunamadı. Lütfen geçerli bir video dosyası seçin.")
        if st.button("⬅️ Geri", key="dlg_bolum_geri_sure_hata", use_container_width=True):
            st.session_state.ek_dialog_open = "video_ekle"
            st.rerun()
        return

    kaynak_baslik = f"Link Video {source_no}" if is_link_source else "Seçilen video"
    st.caption(f"{kaynak_baslik}: **{temp_name}** | Toplam süre: **{_format_duration_ms(video_suresi)}** ({video_suresi:.3f} saniye) | **{_format_mmss_ms(video_suresi)}**")
    if is_link_source:
        st.info("Bu link için bölüm zamanları kaydedilecek. Tümünü Çalıştır içinde video indirildikten sonra bu zamanlara göre otomatik kesilecek.")
    else:
        st.info(f"Hedef klasör: {hedef_root}")

    # Video önizleme
    try:
        st.video(preview_url if is_link_source else temp_path)
    except Exception:
        st.warning("Önizleme yüklenemedi.")

    st.markdown("**Yavaş Oynatma ve Milisaniye Takibi:**")
    _render_video_bolum_precision_controls()
    st.caption("Zaman alanları M:SS:mmm veya M:SS.mmm formatını destekler. Örn: 0:12:350, 0:12.350 ya da 12.350 saniye.")

    st.caption("Videoyu istediğiniz zaman aralıklarında bölümlerine ayırın. Her bölüm ayrı bir Video klasörüne kaydedilir.")

    def _clear_bolum_widget_keys():
        for _old_i in range(50):
            st.session_state.pop(f"dlg_bolum_baslangic_{_old_i}", None)
            st.session_state.pop(f"dlg_bolum_bitis_{_old_i}", None)

    def _build_equal_segments(segment_count: int) -> list[tuple[float, float]]:
        segment_count = max(1, int(segment_count))
        esit_sure = video_suresi / segment_count
        segmentler = []
        for _new_i in range(segment_count):
            _s = round(esit_sure * _new_i, 3)
            _e = round(esit_sure * (_new_i + 1), 3) if _new_i < segment_count - 1 else round(video_suresi, 3)
            segmentler.append((_s, _e))
        return segmentler

    def _write_segment_state(segmentler: list[tuple[float, float]]):
        _clear_bolum_widget_keys()
        for _new_i, (_s, _e) in enumerate(segmentler):
            st.session_state[f"dlg_bolum_baslangic_{_new_i}"] = _format_mmss_ms(_s)
            st.session_state[f"dlg_bolum_bitis_{_new_i}"] = _format_mmss_ms(_e)

    def _read_segment_text_state(segment_count: int) -> list[tuple[str, str]]:
        segmentler = []
        for _idx in range(max(0, int(segment_count))):
            segmentler.append((
                str(st.session_state.get(f"dlg_bolum_baslangic_{_idx}") or ""),
                str(st.session_state.get(f"dlg_bolum_bitis_{_idx}") or ""),
            ))
        return segmentler

    def _write_segment_text_state(segmentler: list[tuple[str, str]]):
        _clear_bolum_widget_keys()
        for _new_i, (_bs, _es) in enumerate(segmentler):
            st.session_state[f"dlg_bolum_baslangic_{_new_i}"] = str(_bs or "")
            st.session_state[f"dlg_bolum_bitis_{_new_i}"] = str(_es or "")

    def _build_manual_segments_from_existing(previous_count: int, target_count: int) -> list[tuple[str, str]]:
        hedef = max(1, int(target_count))
        onceki = max(0, int(previous_count or 0))
        korunanlar = _read_segment_text_state(onceki)[:min(onceki, hedef)]
        kalan = hedef - len(korunanlar)
        if kalan <= 0:
            return korunanlar

        son_bitis = 0.0
        for _bs, _es in reversed(korunanlar):
            _parsed_end = _parse_mmss(_es)
            if _parsed_end >= 0:
                son_bitis = min(max(_parsed_end, 0.0), round(video_suresi, 3))
                break

        if son_bitis < video_suresi - 0.001:
            ek_segmentler = []
            kalan_sure = max(0.0, video_suresi - son_bitis)
            parca_sure = kalan_sure / kalan if kalan > 0 else 0.0
            _cursor = son_bitis
            for _idx in range(kalan):
                _s = round(_cursor, 3)
                _e = round(_cursor + parca_sure, 3) if _idx < kalan - 1 else round(video_suresi, 3)
                _e = min(_e, round(video_suresi, 3))
                ek_segmentler.append((_format_mmss_ms(_s), _format_mmss_ms(_e)))
                _cursor = _e
            return korunanlar + ek_segmentler

        ayni_nokta = _format_mmss_ms(son_bitis)
        return korunanlar + [(ayni_nokta, ayni_nokta) for _ in range(kalan)]

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
                if _oto_n < 1:
                    _oto_n = 1
                _cursor = 0.0
                _otomatik_segmentler = []
                for _new_i in range(_oto_n):
                    _s = round(_cursor, 3)
                    _e = round(min(_cursor + _sure_sn, video_suresi), 3)
                    if _new_i == _oto_n - 1:
                        _e = round(video_suresi, 3)
                    _otomatik_segmentler.append((_s, _e))
                    _cursor = _e
                _write_segment_state(_otomatik_segmentler)
                st.session_state["dlg_bolum_sayisi"] = _oto_n
                st.session_state["_bolum_sayisi_prev"] = _oto_n
                st.session_state["_video_bolum_init_token"] = video_source_token
                st.session_state["_bolum_sure_secim"] = _sure_sn
                st.rerun(scope="fragment")

    # ---- Bölüm sayısı seçimi ----
    st.markdown("---")
    _pending_widget_updates = st.session_state.pop("_dlg_bolum_pending_updates", None)
    if isinstance(_pending_widget_updates, dict):
        for _widget_key, _widget_value in _pending_widget_updates.items():
            st.session_state[_widget_key] = _widget_value

    # İlk açılışta varsayılan değeri session state üzerinden ata (value parametresi yerine)
    if "dlg_bolum_sayisi" not in st.session_state:
        st.session_state["dlg_bolum_sayisi"] = 2
    st.markdown("**İşlem Şekli:**")
    bolum_duzen_modu = st.radio(
        "Bölüm düzenleme modu",
        options=["Otomatik", "Manuel"],
        key="video_bolum_duzen_modu",
        horizontal=True,
        label_visibility="collapsed",
    )
    if bolum_duzen_modu == "Otomatik":
        st.caption("Otomatik modda bir bölümün bitişini değiştirdiğinizde sonraki bölümler zincirleme güncellenir.")
    else:
        st.caption("Manuel modda her bölüm bağımsızdır. Aralarda boşluk bırakabilir, tek bir klip seçebilir ve süreleri serbestçe ayarlayabilirsiniz.")
    st.caption("İsterseniz önce üstteki otomatik süre düğmelerinden birini kullanıp ardından burada manuel düzeltme yapabilirsiniz.")

    bolum_sayisi = st.number_input(
        "Kaç bölüme ayırmak istiyorsunuz?",
        min_value=1, max_value=50, step=1,
        key="dlg_bolum_sayisi",
    )
    n = int(bolum_sayisi)

    # İlk açılış veya bölüm sayısı değişikliğinde session state'e
    # varsayılan değerleri yaz (widget oluşturulmadan ÖNCE)
    _prev_bolum = st.session_state.get("_bolum_sayisi_prev", None)
    _prev_init_token = st.session_state.get("_video_bolum_init_token")
    _needs_init = (_prev_bolum is None) or (n != _prev_bolum) or (_prev_init_token != video_source_token)
    if _needs_init:
        if (_prev_bolum is None) or (_prev_init_token != video_source_token):
            _write_segment_state(_build_equal_segments(n))
        elif bolum_duzen_modu == "Manuel" and n != _prev_bolum:
            _write_segment_text_state(_build_manual_segments_from_existing(_prev_bolum, n))
        else:
            _write_segment_state(_build_equal_segments(n))
        st.session_state["_bolum_sayisi_prev"] = n
        st.session_state["_video_bolum_init_token"] = video_source_token
        st.session_state.pop("_bolum_sure_secim", None)
        # İlk açılış değilse (bölüm sayısı değişti) rerun yap
        if _prev_bolum is not None and _prev_init_token == video_source_token:
            st.rerun(scope="fragment")
    st.session_state["_bolum_sayisi_prev"] = n
    st.session_state["_video_bolum_init_token"] = video_source_token

    st.markdown("---")
    st.markdown("**Bölüm Zaman Aralıklarını Belirleyin (Başlangıç — Bitiş):**")
    if bolum_duzen_modu == "Otomatik":
        st.caption("Format: M:SS:mmm (orn: 0:12:350), M:SS.mmm (orn: 0:12.350) veya saniye (orn: 12.350). Bir bölümü değiştirdiğinizde sonraki bölümler otomatik güncellenir.")
    else:
        st.caption("Format: M:SS:mmm (orn: 0:12:350), M:SS.mmm (orn: 0:12.350) veya saniye (orn: 12.350). Manuel modda her bölüm bağımsızdır; aralarda boşluk bırakabilir veya videonun sadece istediğiniz kısmını alabilirsiniz.")

    # Önce tüm widget'ları oluştur ve değerlerini oku
    segments_raw = []  # [(baslangic_str, bitis_str), ...]
    for i in range(n):
        st.markdown(f"**Bölüm {i + 1}:**")
        col_s, col_e = st.columns(2)
        with col_s:
            baslangic_str = st.text_input(
                f"Başlangıç",
                key=f"dlg_bolum_baslangic_{i}",
                help=f"Bölüm {i+1} başlangıç zamanı (M:SS:mmm, M:SS.mmm veya saniye)",
            )
        with col_e:
            bitis_str = st.text_input(
                f"Bitiş",
                key=f"dlg_bolum_bitis_{i}",
                help=f"Bölüm {i+1} bitiş zamanı (M:SS:mmm, M:SS.mmm veya saniye)",
            )
        segments_raw.append((baslangic_str, bitis_str))

    # Widget'lardan okunan değerleri parse et
    segments_parsed = []
    for bs, es in segments_raw:
        segments_parsed.append((_parse_mmss(bs), _parse_mmss(es)))

    if bolum_duzen_modu == "Otomatik":
        # Otomatik güncelleme: Bir bölümün bitişi değiştirildiğinde
        # sonraki bölümlerin başlangıç/bitiş değerlerini kalan süreye göre yeniden dağıt
        _needs_rerun = False
        _pending_segment_updates = {}
        for i in range(n - 1):
            cur_start, cur_end = segments_parsed[i]
            next_start, next_end = segments_parsed[i + 1]
            # Eğer mevcut bölümün bitişi geçerliyse ve sonraki bölümün başlangıcı farklıysa
            if cur_end >= 0 and next_start >= 0 and abs(cur_end - next_start) > 0.001:
                # Sonraki bölümleri yeniden dağıt
                kalan_sure = video_suresi - cur_end
                kalan_bolum = n - (i + 1)
                if kalan_bolum > 0 and kalan_sure > 0:
                    bolum_basi = kalan_sure / kalan_bolum
                    _cursor = cur_end
                    for j in range(i + 1, n):
                        _s = round(_cursor, 3)
                        _e = round(_cursor + bolum_basi, 3) if j < n - 1 else round(video_suresi, 3)
                        _e = min(_e, round(video_suresi, 3))
                        _pending_segment_updates[f"dlg_bolum_baslangic_{j}"] = _format_mmss_ms(_s)
                        _pending_segment_updates[f"dlg_bolum_bitis_{j}"] = _format_mmss_ms(_e)
                        _cursor = _e
                    _needs_rerun = True
                break  # İlk farkı bulduktan sonra dur, rerun yapacak

        if _needs_rerun:
            st.session_state["_dlg_bolum_pending_updates"] = _pending_segment_updates
            st.rerun(scope="fragment")

    # Validasyon
    segments_input = []
    has_error = False
    for i, (start_sec, end_sec) in enumerate(segments_parsed):
        if start_sec < 0 or end_sec < 0:
            st.error(f"Bölüm {i+1}: Geçersiz zaman formatı. M:SS:mmm (örn: 0:12:350), M:SS.mmm (örn: 0:12.350) veya saniye (örn: 12.350) girin.")
            has_error = True
            segments_input.append((0, 0))
        elif end_sec <= start_sec:
            st.error(f"Bölüm {i+1}: Bitiş zamanı ({_format_mmss_ms(end_sec)}) başlangıçtan ({_format_mmss_ms(start_sec)}) büyük olmalıdır.")
            has_error = True
            segments_input.append((start_sec, end_sec))
        elif end_sec > video_suresi + 0.001:
            st.error(f"Bölüm {i+1}: Bitiş zamanı ({_format_mmss_ms(end_sec)}) video süresini ({_format_mmss_ms(video_suresi)}) aşıyor.")
            has_error = True
            segments_input.append((start_sec, end_sec))
        else:
            segments_input.append((start_sec, min(end_sec, video_suresi)))

    if not has_error and len(segments_input) > 1:
        for i in range(1, len(segments_input)):
            onceki_end = segments_input[i - 1][1]
            simdiki_start = segments_input[i][0]
            if simdiki_start < onceki_end - 0.001:
                st.error(
                    f"Bölüm {i+1}: Başlangıç zamanı ({_format_mmss_ms(simdiki_start)}) "
                    f"önceki bölümün bitişinden ({_format_mmss_ms(onceki_end)}) küçük olamaz."
                )
                has_error = True
                break
            if bolum_duzen_modu == "Otomatik" and abs(simdiki_start - onceki_end) > 0.001:
                st.error(
                    f"Bölüm {i+1}: Otomatik modda başlangıç zamanı önceki bölümün bitişiyle aynı olmalıdır. "
                    "Arada boşluk bırakmak için Manuel modu kullanın."
                )
                has_error = True
                break

    # Çakışma kontrolü
    if not has_error and len(segments_input) > 1:
        toplam_girilen = sum(max(0, e - s) for s, e in segments_input)
        if toplam_girilen > video_suresi + 0.001:
            st.error(f"Toplam: {_format_duration_ms(toplam_girilen)} ({_format_mmss_ms(toplam_girilen)}) — Bölümler çakışıyor veya video süresini aşıyor!")
            has_error = True

    # Toplam süre kontrolü ve bilgi gösterimi
    toplam_girilen = sum(max(0, e - s) for s, e in segments_input)
    fark = video_suresi - toplam_girilen

    st.markdown("---")
    if has_error:
        st.error("Yukarıdaki hataları düzeltin. Hatalar giderilmeden bölme işlemi yapılamaz.")
    elif abs(fark) < 0.001:
        st.success(f"Toplam: {_format_duration_ms(toplam_girilen)} ({_format_mmss_ms(toplam_girilen)}) — Video süresiyle uyumlu.")
    elif fark > 0:
        st.warning(f"Toplam: {_format_duration_ms(toplam_girilen)} ({_format_mmss_ms(toplam_girilen)}) — Kalan {_format_duration_ms(fark)} kapsam dışı kalacak.")
    else:
        st.error(f"Toplam: {_format_duration_ms(toplam_girilen)} ({_format_mmss_ms(toplam_girilen)}) — Bölümler çakışıyor veya video süresini aşıyor!")
        has_error = True

    # Önizleme tablosu - widget'lardan okunan gerçek değerlerle
    st.markdown("**Bölüm Önizleme:**")
    preview_data = []
    for i, (s_sec, e_sec) in enumerate(segments_input):
        dur = max(0, e_sec - s_sec)
        preview_data.append({
            "Bölüm": f"Video {i + 1}",
            "Başlangıç": _format_mmss_ms(s_sec),
            "Bitiş": _format_mmss_ms(e_sec),
            "Süre": _format_duration_ms(dur),
        })
    st.table(preview_data)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        # Hata varsa buton her zaman devre dışı
        bolumle_disabled = has_error
        kaydet_buton_metni = "💾 Bölüm Bilgilerini Kaydet" if is_link_source else "✂️ Böl ve Kaydet"
        if st.button(kaydet_buton_metni, key="dlg_bolum_kaydet", use_container_width=True, disabled=bolumle_disabled):
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
                        if is_link_source:
                            plan_payload = {
                                "kind": "link",
                                "source_no": source_no,
                                "url": source_url,
                                "title": temp_name,
                                "duration": video_suresi,
                                "preview_url": st.session_state.get("video_bolum_preview_url", ""),
                                "segments": segments,
                                "edit_mode": bolum_duzen_modu,
                            }
                            if _upsert_video_bolum_link_plan(plan_payload):
                                _write_prompt_source_mode(PROMPT_SOURCE_LINK)
                                set_link_canvas_source("manual")
                                st.session_state.status["youtube_link"] = "idle"
                                st.session_state.status["input"] = "ok"
                                st.session_state["video_ekle_saved_notice"] = (
                                    f"Link Video {source_no} için {len(segments)} bölümlük plan kaydedildi. "
                                    "Tümünü Çalıştır'da Video İndir adımı bittikten sonra otomatik kesilecek."
                                )
                                st.session_state.video_bolum_temp_path = None
                                st.session_state.video_bolum_temp_name = None
                                st.session_state.video_bolum_source_kind = "file"
                                st.session_state.video_bolum_source_no = None
                                st.session_state.video_bolum_source_url = ""
                                st.session_state.video_bolum_source_title = ""
                                st.session_state.video_bolum_source_duration = 0.0
                                st.session_state.video_bolum_preview_url = ""
                                st.session_state.ek_dialog_open = "video_ekle"
                                st.rerun()
                            else:
                                st.error("Bölüm planı kaydedilemedi.")
                            return

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
                            _bolum_progress_bar.progress(_ilerleme, text=f"✂️ Bölüm {video_no}/{toplam_bolum} kesiliyor... ({_format_mmss_ms(_b_start)} → {_format_mmss_ms(_b_end)})")
                            _bolum_status_text.info(f"⏳ Video {video_no} işleniyor: {_format_mmss_ms(_b_start)} - {_format_mmss_ms(_b_end)} ({_format_duration_ms(_b_end - _b_start)})")

                            klasor = os.path.join(hedef_root, f"Video {video_no}")
                            os.makedirs(klasor, exist_ok=True)
                            out_name = f"bolum_{video_no}{ext}"
                            out_path = os.path.join(klasor, out_name)
                            duration = _b_end - _b_start
                            try:
                                subprocess.run(
                                    ["ffmpeg", "-y",
                                     "-i", temp_path,
                                     "-ss", _format_ffmpeg_seconds(_b_start),
                                     "-t", _format_ffmpeg_seconds(duration),
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
                            clear_placeholder = globals().get("_clear_empty_source_placeholder")
                            if callable(clear_placeholder):
                                clear_placeholder()
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
            st.session_state.video_bolum_source_kind = "file"
            st.session_state.video_bolum_source_no = None
            st.session_state.video_bolum_source_url = ""
            st.session_state.video_bolum_source_title = ""
            st.session_state.video_bolum_source_duration = 0.0
            st.session_state.video_bolum_preview_url = ""
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

def _render_gorsel_analiz_dialog_body():
    def _normalize_pair_selection(folder_name, available_images):
        pair_key = f"sel_pair_{folder_name}"
        valid_images = [name for name in st.session_state.get(pair_key, []) if name in available_images]
        if valid_images != st.session_state.get(pair_key, []):
            st.session_state[pair_key] = valid_images[:2]
        return list(st.session_state.get(pair_key, []))[:2]

    def _toggle_transition_image(folder_name, image_name, available_images):
        pair_key = f"sel_pair_{folder_name}"
        current = _normalize_pair_selection(folder_name, available_images)
        if image_name in current:
            current = [name for name in current if name != image_name]
        elif len(current) >= 2:
            st.session_state["ga_transition_selection_error"] = (
                "Transition modunda en fazla 2 görsel seçebilirsiniz. "
                "Önce mevcut seçimlerden birini kaldırın."
            )
        else:
            current.append(image_name)
        st.session_state[pair_key] = current[:2]

    kaynak_videolar = _list_gorsel_analiz_source_entries()
    kaynak_etiketi = _get_gorsel_analiz_source_label()

    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.button(
        "📸 Videodan Görsel Çıkart (İşlemi Başlat)",
        key="dlg_gorsel_analiz_start_transition",
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

    transition_state = _load_transition_ui_state()
    stored_transition_enabled = bool(transition_state.get("gorsel_analiz_transition_enabled", False))
    ga_transition_enabled = st.checkbox(
        "Start End Frame (Transition)",
        value=stored_transition_enabled,
        key="ga_transition_toggle",
        help="Açıkken iki kare seçip bunları start.png ve end.png olarak kaydedebilirsiniz.",
    )
    if ga_transition_enabled != stored_transition_enabled:
        _save_transition_ui_state({"gorsel_analiz_transition_enabled": ga_transition_enabled})

    if ga_transition_enabled:
        st.caption(
            "Transition modunda iki kare seçin. Kaydet dediğinizde klasörde yalnızca "
            "start.png ve end.png kalır."
        )

    selection_error = st.session_state.pop("ga_transition_selection_error", "")
    if selection_error:
        st.warning(selection_error)

    klasorler = get_gorsel_analiz_klasorleri()
    if not klasorler:
        if not kaynak_videolar:
            st.warning(f"{kaynak_etiketi} kaynağında işlenecek video bulunamadı.")
        else:
            st.info("Henüz kaydedilmiş Görsel Analiz çıktısı bulunamadı.")
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("⬅️ Geri", key="ga_back_empty", use_container_width=True):
            st.session_state.ek_dialog_open = "menu"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    selected_folder_state = st.session_state.get("gorsel_analiz_klasor_sec")
    if selected_folder_state not in klasorler:
        st.session_state.gorsel_analiz_klasor_sec = klasorler[0]

    selected_folder = st.selectbox(
        "Klasör Seçin:",
        options=klasorler,
        index=klasorler.index(st.session_state.get("gorsel_analiz_klasor_sec")),
        key="ga_folder_select",
    )
    st.session_state.gorsel_analiz_klasor_sec = selected_folder

    images = get_klasor_gorselleri(selected_folder)
    if not images:
        st.warning("Seçilen klasörde görsel bulunamadı.")
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("⬅️ Geri", key="ga_back_no_images", use_container_width=True):
            st.session_state.ek_dialog_open = "menu"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    single_key = f"sel_{selected_folder}"
    pair_key = f"sel_pair_{selected_folder}"

    current_single = st.session_state.get(single_key)
    if current_single not in images:
        preferred_single = "start.png" if "start.png" in images else images[0]
        st.session_state[single_key] = preferred_single

    current_pair = _normalize_pair_selection(selected_folder, images)
    if not current_pair:
        default_pair = []
        if "start.png" in images:
            default_pair.append("start.png")
        if "end.png" in images:
            default_pair.append("end.png")
        if len(default_pair) < 2:
            for image_name in images:
                if image_name not in default_pair:
                    default_pair.append(image_name)
                if len(default_pair) == 2:
                    break
        st.session_state[pair_key] = default_pair[:2]
        current_pair = list(st.session_state[pair_key])

    if ga_transition_enabled and len(images) < 2:
        st.warning("Transition modu için aynı klasörde en az 2 görsel gerekli.")

    cols_per_row = 4
    for row_start in range(0, len(images), cols_per_row):
        row_images = images[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for i, image_name in enumerate(row_images):
            with cols[i]:
                image_path = os.path.join(
                    st.session_state.settings.get("gorsel_analiz_dir", ""),
                    selected_folder,
                    image_name,
                )
                try:
                    st.image(image_path, use_container_width=True)
                except Exception:
                    st.text(image_name)

                preview_col, select_col = st.columns(2)
                with preview_col:
                    if st.button("🔍", key=f"ga_zoom_{selected_folder}_{image_name}", use_container_width=True):
                        st.session_state.lightbox_gorsel = {"path": image_path, "adi": image_name}
                        st.session_state._ek_dialog_return = "gorsel_analiz"
                        _request_ek_dialog_open("gorsel_analiz")
                        st.rerun()
                with select_col:
                    if ga_transition_enabled:
                        current_pair = _normalize_pair_selection(selected_folder, images)
                        if image_name in current_pair:
                            pair_index = current_pair.index(image_name)
                            button_label = "Start" if pair_index == 0 else "End"
                        else:
                            button_label = "Seç"
                        if st.button(
                            button_label,
                            key=f"ga_pair_{selected_folder}_{image_name}",
                            use_container_width=True,
                        ):
                            _toggle_transition_image(selected_folder, image_name, images)
                            _request_ek_dialog_open("gorsel_analiz")
                            st.rerun()
                    else:
                        button_label = "✅" if st.session_state.get(single_key) == image_name else "☐"
                        if st.button(
                            button_label,
                            key=f"ga_single_{selected_folder}_{image_name}",
                            use_container_width=True,
                        ):
                            st.session_state[single_key] = image_name
                            _request_ek_dialog_open("gorsel_analiz")
                            st.rerun()

    if ga_transition_enabled:
        current_pair = _normalize_pair_selection(selected_folder, images)
        start_label = current_pair[0] if len(current_pair) >= 1 else "-"
        end_label = current_pair[1] if len(current_pair) >= 2 else "-"
        st.caption(f"Seçili kareler: Start = {start_label} | End = {end_label}")
    else:
        st.caption(f"Seçili görsel: {st.session_state.get(single_key, '-')}")

    save_col, back_col = st.columns(2)
    with save_col:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        save_label = "💾 Start/End Olarak Kaydet" if ga_transition_enabled else "💾 Kaydet (Diğerlerini Sil)"
        if st.button(save_label, key="ga_save_selection", use_container_width=True):
            if ga_transition_enabled:
                current_pair = _normalize_pair_selection(selected_folder, images)
                if len(current_pair) != 2:
                    st.error("Transition modu için tam 2 görsel seçmelisiniz.")
                elif current_pair[0] == current_pair[1]:
                    st.error("Start ve End için farklı görseller seçin.")
                else:
                    ok = gorsel_secimini_transition_olarak_kaydet(
                        selected_folder,
                        current_pair[0],
                        current_pair[1],
                    )
                    if ok:
                        st.session_state[pair_key] = ["start.png", "end.png"]
                        st.session_state[single_key] = "start.png"
                        _request_ek_dialog_open("gorsel_analiz")
                        st.rerun()
                    st.error("Start/End frame kaydedilemedi.")
            else:
                selected_image = st.session_state.get(single_key)
                if not selected_image:
                    st.error("Lütfen bir görsel seçin.")
                else:
                    ok = gorsel_sec_ve_diger_sil(selected_folder, selected_image)
                    if ok:
                        _request_ek_dialog_open("gorsel_analiz")
                        st.rerun()
                    st.error("Görsel kaydı sırasında bir hata oluştu.")
        st.markdown('</div>', unsafe_allow_html=True)
    with back_col:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("⬅️ Geri", key="ga_back_main", use_container_width=True):
            st.session_state.ek_dialog_open = "menu"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("🖼️ Görsel Analiz", width="large")
def gorsel_analiz_dialog():
    return _render_gorsel_analiz_dialog_body()
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

    transition_state = _load_transition_ui_state()
    ga_transition_enabled = st.checkbox(
        "Start End Frame (Transition)",
        value=bool(transition_state.get("gorsel_analiz_transition_enabled", False)),
        key="ga_transition_toggle",
        help="Açıkken iki kare seçip bunları start.png ve end.png olarak kaydedebilirsiniz.",
    )
    if ga_transition_enabled != bool(transition_state.get("gorsel_analiz_transition_enabled", False)):
        _save_transition_ui_state({"gorsel_analiz_transition_enabled": ga_transition_enabled})
    if ga_transition_enabled:
        st.caption("Transition modunda tam 2 görsel seçin. Kaydet dediğinizde klasörde yalnızca start.png ve end.png kalır.")

    klasorler = get_gorsel_analiz_klasorleri()
    if klasorler:
        if st.session_state.get("gorsel_analiz_klasor_sec") not in klasorler:
            st.session_state.gorsel_analiz_klasor_sec = klasorler[0]
        idx = klasorler.index(st.session_state.get("gorsel_analiz_klasor_sec"))
        secilen = st.selectbox("Klasör Seçin:", options=klasorler, index=idx)
        if secilen:
            st.session_state.gorsel_analiz_klasor_sec = secilen
            gorseller = get_klasor_gorselleri(secilen)
            if gorseller:
                sel_key = f"sel_{secilen}"
                pair_key = f"sel_pair_{secilen}"
                if sel_key not in st.session_state: st.session_state[sel_key] = gorseller[0]
                if pair_key not in st.session_state:
                    varsayilan_pair = []
                    if "start.png" in gorseller:
                        varsayilan_pair.append("start.png")
                    if "end.png" in gorseller:
                        varsayilan_pair.append("end.png")
                    st.session_state[pair_key] = varsayilan_pair[:2]
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
                                    st.session_state[sel_key] = g_adi
                                    _request_ek_dialog_open("gorsel_analiz")
                                    st.rerun()
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                    if st.button("💾 Kaydet (Diğerlerini Sil)", use_container_width=True):
                        if st.session_state.get(sel_key): 
                            gorsel_sec_ve_diger_sil(secilen, st.session_state[sel_key])
                            _request_ek_dialog_open("gorsel_analiz")
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
    _apply_pending_gklonla_form_ui_state()
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

    mevcut_klon_model = _normalize_clone_image_model(
        st.session_state.settings.get("gorsel_klonlama_model") or st.session_state.settings.get("gorsel_model"),
        DEFAULT_GORSEL_KLONLAMA_MODEL,
    )
    secili_klon_model = st.selectbox(
        "Klonlama Modeli",
        PIXVERSE_IMAGE_CLONE_MODEL_OPTIONS,
        index=PIXVERSE_IMAGE_CLONE_MODEL_OPTIONS.index(mevcut_klon_model),
        key="gklonla_model_select",
        help="Görsel Klonla adımı PixVerse CLI image-to-image modunda bu modeli kullanır.",
    )
    mevcut_klon_kalite = _normalize_image_quality(
        st.session_state.settings.get("gorsel_klonlama_kalitesi") or st.session_state.settings.get("gorsel_kalitesi"),
        "Standart",
    )
    mevcut_klon_boyut = _normalize_image_aspect_ratio(
        st.session_state.settings.get("gorsel_klonlama_boyutu") or st.session_state.settings.get("gorsel_boyutu"),
        "16:9",
    )
    kalite_col, boyut_col = st.columns(2)
    with kalite_col:
        secili_klon_kalite = st.selectbox(
            "Klonlama Kalitesi",
            PIXVERSE_IMAGE_QUALITY_OPTIONS,
            index=PIXVERSE_IMAGE_QUALITY_OPTIONS.index(mevcut_klon_kalite),
            key="gklonla_kalite_select",
            help="Standart / Yüksek / Maksimum kalite tercihi seçin.",
        )
    with boyut_col:
        secili_klon_boyut = st.selectbox(
            "Klonlama Oranı",
            PIXVERSE_IMAGE_ASPECT_RATIO_OPTIONS,
            index=PIXVERSE_IMAGE_ASPECT_RATIO_OPTIONS.index(mevcut_klon_boyut),
            key="gklonla_boyut_select",
            help="Üretilecek klon görsel için hedef oranı seçin.",
        )
    if (
        secili_klon_model != mevcut_klon_model
        or secili_klon_kalite != mevcut_klon_kalite
        or secili_klon_boyut != mevcut_klon_boyut
    ):
        st.session_state.settings["gorsel_klonlama_model"] = secili_klon_model
        st.session_state.settings["gorsel_klonlama_kalitesi"] = secili_klon_kalite
        st.session_state.settings["gorsel_klonlama_boyutu"] = secili_klon_boyut
        save_settings(st.session_state.settings)
        st.session_state.ek_dialog_open = "gorsel_klonla"
        st.rerun()

    transition_state = _load_transition_ui_state()
    stored_clone_transition = bool(transition_state.get("gorsel_klonla_transition_enabled", False))
    clone_transition_enabled = st.checkbox(
        "Start End Frame (Transition)",
        value=stored_clone_transition,
        key="gklonla_transition_toggle",
        help="Açıkken kaynak klasörde start.png ve end.png varsa ikisi de aynı prompt ile klonlanır.",
    )
    if clone_transition_enabled != stored_clone_transition:
        _save_transition_ui_state({"gorsel_klonla_transition_enabled": clone_transition_enabled})
    if clone_transition_enabled:
        st.caption("Transition modunda kaynak klasördeki start.png ve end.png birlikte işlenir ve çıktı klasörüne aynı adlarla kaydedilir.")

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
        dolu = sum(
            1 for i in range(1, efektif_sayisi + 1)
            if _gorsel_klon_prompt_has_value(
                mevcut_data.get(i, ""),
                require_transition_pair=clone_transition_enabled,
            )
        )
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
            '💡 <b>Referans Görsel (isteğe bağlı):</b> Her görsel için bir veya birden fazla referans görsel '
            'yükleyebilirsiniz. Yüklediğiniz referanslar tek bir birleşik referans görsele dönüştürülüp modele '
            'gönderilir. Örneğin <em>"1. Görseldeki karakteri 2. Görseldeki karakterle değiştir"</em> gibi bir '
            'istemle hem ana görsel hem referans paneli birlikte kullanılabilir.'
            '</div>',
            unsafe_allow_html=True
        )

        def _render_gklonla_reference_editor(gorsel_no: int, frame_name: str | None = None):
            slot = _normalize_gorsel_referans_slot(frame_name)
            slot_suffix = f"_{slot}" if slot else ""
            slot_label = "Start" if slot == "start" else "End" if slot == "end" else "Referans"
            mevcut_ref_yollari = [yol for yol in gorsel_referans_yollari(gorsel_no, slot) if os.path.isfile(yol)]
            mevcut_ref_yol = mevcut_ref_yollari[0] if mevcut_ref_yollari else ""
            ref_var = bool(mevcut_ref_yollari)

            ref_col_up, ref_col_prev = st.columns([0.65, 0.35])
            with ref_col_up:
                ref_up = st.file_uploader(
                    f"📎 #{gorsel_no} {slot_label} Referans Görsel(ler)",
                    type=["jpg", "jpeg", "png", "bmp", "webp"],
                    key=f"ref_up{slot_suffix}_{gorsel_no}",
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                    help="Bir veya birden fazla referans görsel yükleyin; sistem bunları tek bir referans paneline dönüştürür.",
                )
                if ref_up:
                    gorsel_referans_kaydet(gorsel_no, ref_up, slot)
                    st.session_state[f"ref_saved{slot_suffix}_{gorsel_no}"] = True
                    mevcut_ref_yollari = [yol for yol in gorsel_referans_yollari(gorsel_no, slot) if os.path.isfile(yol)]
                    mevcut_ref_yol = mevcut_ref_yollari[0] if mevcut_ref_yollari else ""
                    ref_var = bool(mevcut_ref_yollari)
                _ref_label = f"📎 {slot_label} Referans #{gorsel_no}" if slot else f"📎 Referans #{gorsel_no}"
                if ref_var:
                    if len(mevcut_ref_yollari) == 1:
                        _ref_label += " ✅"
                    else:
                        _ref_label += f" ✅ ({len(mevcut_ref_yollari)} görsel)"
                st.caption(_ref_label)
            with ref_col_prev:
                if ref_var:
                    try:
                        if len(mevcut_ref_yollari) == 1:
                            st.image(mevcut_ref_yol, use_container_width=True)
                        else:
                            st.image(mevcut_ref_yollari[:4], width=82)
                            st.caption(f"{len(mevcut_ref_yollari)} referans görsel yüklü")
                            if len(mevcut_ref_yollari) > 4:
                                st.caption(f"+{len(mevcut_ref_yollari) - 4} görsel daha")
                    except Exception:
                        st.caption("📷 ref")
                    if st.button(
                        "🗑️",
                        key=f"ref_sil{slot_suffix}_{gorsel_no}",
                        help="Referans görselleri sil",
                    ):
                        gorsel_referans_sil(gorsel_no, slot)
                        st.session_state["gklonla_pending_form_ui"] = {
                            "targets": [gorsel_no],
                            "clear_ref_keys": True,
                        }
                        st.session_state.ek_dialog_open = "gorsel_klonla"
                        st.rerun()
                else:
                    st.caption("Referans yok")

        for i in range(1, efektif_sayisi + 1):
            # Thumbnail: aktif kaynaktan klasör varsa göster
            klasor_adi = klasorler[i-1] if i-1 < len(klasorler) else None
            gorsel_yol = None
            gorsel_yollari = []
            transition_pair_found = False
            if klasor_adi:
                klasor_yolu = os.path.join(aktif_dir, klasor_adi) if aktif_dir else ""
                gorseller = [
                    f for f in sorted(os.listdir(klasor_yolu))
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"))
                ] if klasor_yolu and os.path.isdir(klasor_yolu) else []
                if clone_transition_enabled and klasor_yolu and os.path.isdir(klasor_yolu):
                    start_path, end_path = resolve_transition_pair(klasor_yolu)
                    if start_path and end_path:
                        gorsel_yollari = [str(start_path), str(end_path)]
                        gorsel_yol = str(start_path)
                        transition_pair_found = True
                if gorseller:
                    sel_key = f"sel_{klasor_adi}"
                    secili_g = st.session_state.get(sel_key, gorseller[0])
                    if not gorsel_yollari:
                        gorsel_yol = os.path.join(aktif_dir, klasor_adi, secili_g)
                        gorsel_yollari = [gorsel_yol]

            mevcut_deger = _normalize_gorsel_klon_prompt_entry(mevcut_data.get(i, ""))
            doluluk_icon = "✅" if _gorsel_klon_prompt_has_value(
                mevcut_deger,
                require_transition_pair=clone_transition_enabled and transition_pair_found,
            ) else "⬜"
            etiket = klasor_adi if klasor_adi else f"Görsel {i}"
            if transition_pair_found:
                etiket = f"{etiket} (Start + End)"

            if transition_pair_found and len(gorsel_yollari) >= 2:
                duzelt_inputs[i] = {}
                for frame_name, frame_path in (("start", gorsel_yollari[0]), ("end", gorsel_yollari[1])):
                    frame_label = "Start Frame" if frame_name == "start" else "End Frame"
                    frame_value = _gorsel_klon_prompt_frame_value(mevcut_deger, frame_name)
                    frame_icon = "✅" if bool(str(frame_value or "").strip()) else "⬜"
                    col_img, col_inp = st.columns([0.18, 0.82])
                    with col_img:
                        try:
                            st.image(frame_path, use_container_width=True)
                        except Exception:
                            st.caption("📷")
                    with col_inp:
                        st.markdown(
                            f'<div style="font-size:12px;color:rgba(255,255,255,0.55);margin-bottom:2px;">'
                            f'{frame_icon} <b>#{i}</b> — {etiket} / {frame_label}</div>',
                            unsafe_allow_html=True
                        )
                        duzelt_inputs[i][frame_name] = st.text_input(
                            label=f"#{i} {frame_label}",
                            value=frame_value,
                            placeholder=f"{frame_label} için düzeltme",
                            key=f"dzt_{frame_name}_{i}",
                            label_visibility="collapsed",
                        )
                        _render_gklonla_reference_editor(i, frame_name)
                    if frame_name == "start":
                        st.markdown('<hr style="margin:6px 0;border-color:rgba(255,255,255,0.05);">', unsafe_allow_html=True)
            elif gorsel_yollari:
                col_img, col_inp = st.columns([0.18, 0.82])
                with col_img:
                    try:
                        st.image(gorsel_yollari[0], use_container_width=True)
                    except Exception:
                        st.caption("📷")
                with col_inp:
                    st.markdown(
                        f'<div style="font-size:12px;color:rgba(255,255,255,0.55);margin-bottom:2px;">'
                        f'{doluluk_icon} <b>#{i}</b> — {etiket}</div>',
                        unsafe_allow_html=True
                    )
                    duzelt_inputs[i] = st.text_input(
                        label=f"#{i}",
                        value=_gorsel_klon_prompt_frame_value(mevcut_deger, ""),
                        placeholder="Örn: Kadın yerine adam olarak değiştir",
                        key=f"dzt_{i}",
                        label_visibility="collapsed",
                    )
                    _render_gklonla_reference_editor(i)
            else:
                st.markdown(
                    f'<div style="font-size:12px;color:rgba(255,255,255,0.55);margin-bottom:2px;">'
                    f'{doluluk_icon} <b>#{i}</b> — {etiket}</div>',
                    unsafe_allow_html=True
                )
                duzelt_inputs[i] = st.text_input(
                    label=f"#{i}", value=_gorsel_klon_prompt_frame_value(mevcut_deger, ""),
                    placeholder="Örn: Kadın yerine adam olarak değiştir",
                    key=f"dzt_{i}", label_visibility="collapsed"
                )
                _render_gklonla_reference_editor(i)
            st.markdown('<hr style="margin:6px 0;border-color:rgba(255,255,255,0.07);">', unsafe_allow_html=True)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("💾 Kaydet", use_container_width=True):
                kaydet_data = {}
                for no, value in duzelt_inputs.items():
                    if isinstance(value, dict):
                        kaydet_data[no] = {
                            "start": str(value.get("start") or "").strip(),
                            "end": str(value.get("end") or "").strip(),
                        }
                    else:
                        kaydet_data[no] = str(value or "").strip()
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
                st.session_state["gklonla_pending_form_ui"] = {
                    "clear_text_keys": True,
                    "clear_ref_keys": True,
                }
                st.session_state.g_saved = False
                st.session_state.pop("gklonla_saved", None)
                st.session_state.pop("gklonla_prompt_sync_ok", None)
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
            for idx, row in enumerate(rows, start=1):
                row["selected"] = bool(select_all)
                st.session_state[f"sm_account_selected_{idx}"] = bool(select_all)
            st.session_state["sm_select_all_accounts_prev"] = bool(select_all)

        st.markdown(
            "<div style='background:rgba(255,255,255,0.045);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:12px 14px;margin:8px 0 14px 0;line-height:1.6;'>"
            "İlk satırdaki hesap <b>Tek Hesap</b> modunda kullanılacak hesaptır. "
            "Toplu paylaşımda varsayılan davranış videoları <b>seçili hesaplara sırayla dağıtmaktır</b>. "
            "İsterseniz bu davranışı kapatıp <b>her videoyu tüm seçili hesaplarda</b> ayrı ayrı paylaşabilirsiniz. "
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
            "Videoları hesaplar arasında sırayla dağıt (önerilen)",
            key="sm_hesap_dongu",
            help="Açıkken videolar seçili hesaplara sırayla dağıtılır. Kapalıysa her seçili video tüm seçili hesaplarda paylaşılır.",
        )
        aktif_hesaplar, invalid_rows = _sm_collect_accounts_from_rows()
        if invalid_rows:
            st.warning(f"Eksik bilgi olan hesap satırları: {', '.join(str(x) for x in invalid_rows)}. API Token girilmeli.")
        secili_hesap_sayisi = sum(1 for h in aktif_hesaplar if h.get("selected", True))
        toplam_hesap_sayisi = len(aktif_hesaplar)
        if not hesap_loop and secili_hesap_sayisi > 1:
            st.warning(f"Fan-out modu açık: seçili her video {secili_hesap_sayisi} hesapta ayrı ayrı paylaşılacak.")
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
        st.caption("Kaynağı ayrı ayrı seçin: Link, Video, 🎬 Klon Video, 🖼️ Görsel Oluştur, 🎞️ Video Ekle, 🎬 Toplu Video Montaj veya 🎞️ Video Montaj. Böylece tüm video türlerinin ayarları birbirine karışmaz.")

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

        _kaynak_secenekler = ["Link", "Video", "🎬 Klon Video", "🖼️ Görsel Oluştur", "🎞️ Video Ekle", "🎬 Toplu Video Montaj", "🎞️ Video Montaj"]
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
        elif kaynak_secim == "🎬 Klon Video":
            aktif_video_numaralari = sosyal_medya_klon_video_numaralari()
            _kaynak_bilgi_etiketi = "🎬 Klon Video"
            _kaynak_aciklama = "Video Klonla ekranında kaydettiğiniz görevlerden üretilecek klon videolar baz alınıyor."
            if not aktif_video_numaralari:
                st.info("Klon Video klasöründe video bulunamadı ve kayıtlı Klon Video görevi de yok. Önce 🎬 Video Klonla bölümünden ayarları kaydedin.")
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
                elif kaynak_secim == "🎬 Klon Video":
                    kaynak_etiketi = "🎬 Klon Video"
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
                hesap_dongu=True,
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

    if st.session_state.get("sm_saved_notice"):
        _sm_ph = st.empty()
        _sm_ph.success("Kaydedildi! Tümünü Çalıştır sırasında Sosyal Medya Paylaşım bu ayarla çalışacak.")
        time.sleep(2.2)
        _sm_ph.empty()
        st.session_state.pop("sm_saved_notice", None)

    cleanup_btn_cols = st.columns([1, 1.45, 1])
    with cleanup_btn_cols[1]:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button(
            "Eski Paylaşımları Temizle",
            key="sm_cleanup_old_uploads_btn",
            use_container_width=True,
            disabled=st.session_state.get("batch_mode", False) or any_running() or (not script_exists),
        ):
            ok, msg = sosyal_medya_temizle_eski_yuklemeler(
                older_than_days=SOCIAL_MEDIA_OLD_UPLOAD_CLEANUP_DAYS
            )
            st.session_state.ek_dialog_open = "sosyal_medya"
            if ok:
                st.session_state["sm_cleanup_notice"] = msg or "Eski paylaşımlar temizlendi."
                st.session_state.pop("sm_cleanup_warning", None)
            else:
                st.session_state["sm_cleanup_warning"] = msg or "Eski paylaşımlar temizlenemedi."
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.caption(f"Bu buton R2 üzerindeki {SOCIAL_MEDIA_OLD_UPLOAD_CLEANUP_DAYS} günden eski video yüklemelerini siler.")

    if st.session_state.get("sm_cleanup_notice"):
        _sm_cleanup_ph = st.empty()
        _sm_cleanup_ph.success(str(st.session_state.get("sm_cleanup_notice") or "Eski paylaşımlar temizlendi."))
        time.sleep(2.2)
        _sm_cleanup_ph.empty()
        st.session_state.pop("sm_cleanup_notice", None)

    if st.session_state.get("sm_cleanup_warning"):
        _sm_cleanup_warn_ph = st.empty()
        _sm_cleanup_warn_ph.warning(str(st.session_state.get("sm_cleanup_warning") or "Eski paylaşımlar temizlenemedi."))
        time.sleep(2.6)
        _sm_cleanup_warn_ph.empty()
        st.session_state.pop("sm_cleanup_warning", None)

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
    "Happy Horse 1.0": {
        "script_key": "happy_horse_script",
        "default_model": "happyhorse-1.0",
        "models": ["happyhorse-1.0"],
        "quality_map": {
            "happyhorse-1.0": ["720p", "1080p"],
        },
        "durations": list(range(3, 16)),
        "aspect_ratios": ["16:9", "9:16", "1:1", "4:3", "3:4"],
        "ses": True,
    },
    "Sora 2": {
        "script_key": "sora2_script",
        "default_model": "sora-2",
        "models": ["sora-2", "sora-2-pro"],
        "quality_map": {
            "sora-2": ["720p"],
            "sora-2-pro": ["720p", "1080p"],
        },
        "durations": [4, 8, 12],
        "aspect_ratios": ["16:9", "9:16"],
        "ses": True,
    },
    "Kling 3.0": {
        "script_key": "kling30_script",
        "default_model": "kling-3.0-standard",
        "models": ["kling-3.0-standard"],
        "quality_map": {
            "kling-3.0-standard": ["720p"],
        },
        "durations": list(range(3, 16)),
        "aspect_ratios": ["16:9", "9:16", "1:1"],
        "ses": True,
    },
    "Kling O3": {
        "script_key": "klingo3_script",
        "default_model": "kling-o3-standard",
        "models": ["kling-o3-standard"],
        "quality_map": {
            "kling-o3-standard": ["720p"],
        },
        "durations": list(range(3, 16)),
        "aspect_ratios": ["16:9", "9:16", "1:1"],
        "ses": True,
    },
    "Seedance 2.0": {
        "script_key": "seedance20_script",
        "default_model": "seedance-2.0-standard",
        "models": ["seedance-2.0-standard"],
        "quality_map": {
            "seedance-2.0-standard": ["480p", "720p"],
        },
        "durations": list(range(4, 16)),
        "aspect_ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9"],
        "ses": True,
    },
    "Veo 3.1 Standard": {
        "script_key": "veo31_script",
        "default_model": "veo-3.1-standard",
        "models": ["veo-3.1-standard"],
        "quality_map": {
            "veo-3.1-standard": ["720p", "1080p"],
        },
        "durations": [4, 6, 8],
        "aspect_ratios": ["16:9", "9:16"],
        "ses": True,
    },
    "Grok": {
        "script_key": "grok_script",
        "default_model": "grok-imagine",
        "models": ["grok-imagine"],
        "quality_map": {
            "grok-imagine": ["480p", "720p"],
        },
        "durations": list(range(1, 16)),
        "aspect_ratios": ["16:9", "4:3", "1:1", "9:16", "3:4", "3:2", "2:3"],
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
        "aspect_ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "3:2", "2:3", "21:9"],
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
        "aspect_ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "3:2", "2:3"],
        "ses": True,
    },
}


def _normalize_video_settings_source_mode(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"auto", "otomatik"}:
        return "auto"
    if raw in {PROMPT_SOURCE_LINK, "youtube", "manual", "link"}:
        return PROMPT_SOURCE_LINK
    if raw in {PROMPT_SOURCE_DOWNLOADED_VIDEO, "download", "indirilen_video", "indirilen video"}:
        return PROMPT_SOURCE_DOWNLOADED_VIDEO
    if raw in {PROMPT_SOURCE_ADDED_VIDEO, "video", "eklenen_video", "eklenen video"}:
        return PROMPT_SOURCE_ADDED_VIDEO
    return "auto"


def _video_settings_source_mode_label(value: str) -> str:
    normalized = _normalize_video_settings_source_mode(value)
    if normalized == PROMPT_SOURCE_LINK:
        return "Link"
    if normalized == PROMPT_SOURCE_DOWNLOADED_VIDEO:
        return "İndirilen Video"
    if normalized == PROMPT_SOURCE_ADDED_VIDEO:
        return "Eklenen Video"
    return "Otomatik Algıla"


def _extract_prompt_folder_no(folder_name: str) -> int:
    match = re.search(r"(\d+)\s*$", str(folder_name or "").strip())
    if not match:
        return 0
    try:
        return int(match.group(1))
    except Exception:
        return 0


def _normalize_prompt_mapping_key(value: str) -> str:
    return str(value or "").strip().lower().rstrip("\\/")


def _load_prompt_state_mapping() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    mapping = data.get("mapping") if isinstance(data, dict) else {}
    return mapping if isinstance(mapping, dict) else {}


def _list_prompt_link_entries() -> list[dict]:
    links_file = str(st.session_state.settings.get("links_file") or "").strip()
    if not links_file or not os.path.exists(links_file):
        return []
    out = []
    try:
        with open(links_file, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f.read().splitlines(), start=1):
                link = str(line or "").strip()
                if not link:
                    continue
                out.append({
                    "no": idx,
                    "label": f"Link {idx}",
                    "link": link,
                })
    except Exception:
        return []
    return out


def _video_settings_entry_key(source_mode: str, source_no: int, prompt_folder: str = "") -> str:
    raw = f"{_normalize_video_settings_source_mode(source_mode)}_{int(source_no or 0)}_{prompt_folder or ''}"
    cleaned = re.sub(r"[^a-z0-9_]+", "_", raw.lower()).strip("_")
    return cleaned or f"video_{int(source_no or 0)}"


def _ratio_label_to_float(value: str) -> float:
    text = str(value or "").strip()
    if ":" not in text:
        return 0.0
    try:
        left, right = text.split(":", 1)
        left_num = float(left)
        right_num = float(right)
        if left_num <= 0 or right_num <= 0:
            return 0.0
        return left_num / right_num
    except Exception:
        return 0.0


def _closest_supported_aspect_ratio(width: int, height: int, supported_ratios: list[str]) -> str:
    options = [str(item or "").strip() for item in (supported_ratios or []) if str(item or "").strip()]
    if not options:
        return ""
    if width <= 0 or height <= 0:
        return options[0]
    target = float(width) / float(height)
    return min(
        options,
        key=lambda item: (
            abs(_ratio_label_to_float(item) - target),
            options.index(item),
        ),
    )


def _closest_supported_duration(duration_seconds: float, supported_durations: list[int]) -> int:
    values = [int(item) for item in (supported_durations or []) if str(item).strip()]
    if not values:
        return 0
    if duration_seconds <= 0:
        return values[0]
    return min(values, key=lambda item: (abs(float(item) - float(duration_seconds)), item))


def _parse_saved_duration_value(value, fallback: int = 0) -> int:
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except Exception:
            return fallback
    raw = str(value or "").strip()
    match = re.search(r"(\d+)", raw)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return fallback
    return fallback


def _sanitize_video_setting_values(raw_settings: dict, harita: dict, selected_alt_model: str, default_settings: dict) -> dict:
    quality_options = list(harita.get("quality_map", {}).get(selected_alt_model, ["720p"]))
    aspect_options = list(harita.get("aspect_ratios", ["16:9"]))
    duration_options = [int(item) for item in harita.get("durations", [])]

    default_duration = _parse_saved_duration_value(default_settings.get("duration"), duration_options[0] if duration_options else 0)
    duration_value = _parse_saved_duration_value((raw_settings or {}).get("duration"), default_duration)
    if duration_options:
        if duration_value not in duration_options:
            duration_value = _closest_supported_duration(duration_value or default_duration, duration_options)
    else:
        duration_value = default_duration

    aspect_value = str((raw_settings or {}).get("aspect_ratio") or default_settings.get("aspect_ratio") or "").strip()
    if aspect_value not in aspect_options:
        aspect_value = str(default_settings.get("aspect_ratio") or "").strip()
    if aspect_value not in aspect_options and aspect_options:
        aspect_value = aspect_options[0]

    quality_value = str((raw_settings or {}).get("quality") or default_settings.get("quality") or "").strip()
    if quality_value not in quality_options and quality_options:
        quality_value = quality_options[0]

    ses_value = str((raw_settings or {}).get("ses") or default_settings.get("ses") or "kapalı").strip().lower()
    ses_value = "açık" if ses_value in {"açık", "acik", "on", "true", "yes", "evet"} else "kapalı"

    return {
        "aspect_ratio": aspect_value,
        "duration": int(duration_value or 0),
        "ses": ses_value,
        "quality": quality_value,
        "model": selected_alt_model,
    }


def _video_settings_override_default_state() -> dict:
    return {
        "mode": "single",
        "source_mode": "auto",
        "entries": [],
    }


def _video_settings_override_load() -> dict:
    state = _video_settings_override_default_state()
    if not os.path.exists(VIDEO_SETTINGS_OVERRIDE_FILE):
        return state
    try:
        with open(VIDEO_SETTINGS_OVERRIDE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return state
    if not isinstance(data, dict):
        return state
    state["mode"] = "per_video" if str(data.get("mode") or "").strip().lower() == "per_video" else "single"
    state["source_mode"] = _normalize_video_settings_source_mode(data.get("source_mode"))
    entries = data.get("entries")
    if isinstance(entries, list):
        temiz = []
        for entry in entries:
            if isinstance(entry, dict):
                temiz.append(entry)
        state["entries"] = temiz
    return state


def _video_settings_override_save(mode: str, source_mode: str, entries: list[dict], extra: dict | None = None) -> bool:
    payload = {
        "mode": "per_video" if str(mode or "").strip().lower() == "per_video" else "single",
        "source_mode": _normalize_video_settings_source_mode(source_mode),
        "entries": entries if isinstance(entries, list) else [],
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if isinstance(extra, dict):
        for key, value in extra.items():
            payload[key] = value
    try:
        with open(VIDEO_SETTINGS_OVERRIDE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _clear_video_settings_override_widget_state():
    for key in list(st.session_state.keys()):
        if str(key).startswith("va_pv_"):
            st.session_state.pop(key, None)
    for key in (
        "va_per_video_targets",
        "va_per_video_source_signature",
        "va_override_source_mode",
        "va_apply_mode",
    ):
        st.session_state.pop(key, None)


def _clear_video_settings_overrides(reset_widgets: bool = True):
    try:
        if os.path.exists(VIDEO_SETTINGS_OVERRIDE_FILE):
            os.remove(VIDEO_SETTINGS_OVERRIDE_FILE)
    except Exception:
        pass
    if reset_widgets:
        _clear_video_settings_override_widget_state()


def _match_saved_video_settings_entry(target: dict, saved_entries: list[dict]) -> dict | None:
    if not isinstance(saved_entries, list):
        return None
    target_key = str(target.get("target_key") or "").strip()
    target_prompt_folder = _normalize_prompt_mapping_key(target.get("prompt_folder"))
    try:
        target_source_no = int(target.get("source_no") or 0)
    except Exception:
        target_source_no = 0
    target_source_mode = _normalize_video_settings_source_mode(target.get("source_mode"))

    for entry in saved_entries:
        if not isinstance(entry, dict):
            continue
        if target_key and str(entry.get("target_key") or "").strip() == target_key:
            return entry
    for entry in saved_entries:
        if not isinstance(entry, dict):
            continue
        if target_prompt_folder and _normalize_prompt_mapping_key(entry.get("prompt_folder")) == target_prompt_folder:
            return entry
    for entry in saved_entries:
        if not isinstance(entry, dict):
            continue
        try:
            entry_source_no = int(entry.get("source_no") or 0)
        except Exception:
            entry_source_no = 0
        if target_source_no > 0 and entry_source_no == target_source_no:
            if _normalize_video_settings_source_mode(entry.get("source_mode")) == target_source_mode:
                return entry
    return None


def _build_saved_video_settings_fallback_targets(saved_state: dict) -> list[dict]:
    out = []
    for idx, entry in enumerate((saved_state or {}).get("entries", []), start=1):
        if not isinstance(entry, dict):
            continue
        source_no = _parse_saved_duration_value(entry.get("source_no"), idx)
        prompt_folder = str(entry.get("prompt_folder") or "").strip()
        source_mode = _normalize_video_settings_source_mode(entry.get("source_mode"))
        label = str(entry.get("label") or entry.get("source_label") or prompt_folder or f"Video {idx}").strip() or f"Video {idx}"
        out.append({
            "target_key": str(entry.get("target_key") or _video_settings_entry_key(source_mode, source_no, prompt_folder)).strip(),
            "label": label,
            "source_label": str(entry.get("source_label") or label).strip(),
            "source_mode": source_mode,
            "source_kind": str(entry.get("source_kind") or source_mode or "video").strip(),
            "source_no": source_no,
            "video_path": str(entry.get("video_path") or "").strip(),
            "video_name": str(entry.get("video_name") or "").strip(),
            "prompt_folder": prompt_folder,
            "source_link": str(entry.get("source_link") or "").strip(),
        })
    return out


def _list_video_settings_source_targets(source_mode: str) -> tuple[list[dict], str]:
    selected_mode = _normalize_video_settings_source_mode(source_mode)
    effective_mode = _get_prompt_runtime_source_mode() if selected_mode == "auto" else selected_mode
    prompt_entries = _list_video_prompt_entries()
    prompt_by_no = {}
    for item in prompt_entries:
        folder_name = str(item.get("folder_name") or "").strip()
        folder_no = _extract_prompt_folder_no(folder_name)
        if folder_no > 0 and folder_no not in prompt_by_no:
            prompt_by_no[folder_no] = folder_name

    reverse_mapping = {}
    for key, folder_name in _load_prompt_state_mapping().items():
        reverse_mapping[_normalize_prompt_mapping_key(key)] = str(folder_name or "").strip()

    targets = []
    if effective_mode == PROMPT_SOURCE_ADDED_VIDEO:
        for idx, entry in enumerate(_list_added_video_preview_entries(), start=1):
            source_no = int(entry.get("no") or idx)
            video_path = str(entry.get("video_path") or "").strip()
            prompt_folder = reverse_mapping.get(_normalize_prompt_mapping_key(video_path)) or prompt_by_no.get(source_no, "")
            targets.append({
                "target_key": _video_settings_entry_key(PROMPT_SOURCE_ADDED_VIDEO, source_no, prompt_folder),
                "label": f"Eklenen Video {source_no}",
                "source_label": "Eklenen Video",
                "source_mode": PROMPT_SOURCE_ADDED_VIDEO,
                "source_kind": PROMPT_SOURCE_ADDED_VIDEO,
                "source_no": source_no,
                "video_path": video_path,
                "video_name": str(entry.get("video_name") or "").strip(),
                "prompt_folder": prompt_folder,
                "source_link": "",
            })
    elif effective_mode == PROMPT_SOURCE_DOWNLOADED_VIDEO:
        for idx, entry in enumerate(_list_download_video_entries(), start=1):
            source_no = int(entry.get("no") or idx)
            video_path = str(entry.get("video_path") or "").strip()
            prompt_folder = reverse_mapping.get(_normalize_prompt_mapping_key(video_path)) or prompt_by_no.get(source_no, "")
            targets.append({
                "target_key": _video_settings_entry_key(PROMPT_SOURCE_DOWNLOADED_VIDEO, source_no, prompt_folder),
                "label": f"İndirilen Video {source_no}",
                "source_label": "İndirilen Video",
                "source_mode": PROMPT_SOURCE_DOWNLOADED_VIDEO,
                "source_kind": PROMPT_SOURCE_DOWNLOADED_VIDEO,
                "source_no": source_no,
                "video_path": video_path,
                "video_name": str(entry.get("video_name") or "").strip(),
                "prompt_folder": prompt_folder,
                "source_link": "",
            })
    elif effective_mode == PROMPT_SOURCE_LINK:
        download_by_no = {}
        for entry in _list_download_video_entries():
            try:
                source_no = int(entry.get("no") or 0)
            except Exception:
                source_no = 0
            if source_no > 0:
                download_by_no[source_no] = entry
        for link_entry in _list_prompt_link_entries():
            source_no = int(link_entry.get("no") or 0)
            download_entry = download_by_no.get(source_no)
            video_path = str((download_entry or {}).get("video_path") or "").strip()
            link_url = str(link_entry.get("link") or "").strip()
            prompt_folder = (
                reverse_mapping.get(_normalize_prompt_mapping_key(link_url))
                or reverse_mapping.get(_normalize_prompt_mapping_key(video_path))
                or prompt_by_no.get(source_no, "")
            )
            label = f"Link {source_no}"
            if selected_mode == "auto" and video_path:
                label = f"İndirilen Video {source_no}"
            targets.append({
                "target_key": _video_settings_entry_key(PROMPT_SOURCE_LINK, source_no, prompt_folder),
                "label": label,
                "source_label": "Link",
                "source_mode": PROMPT_SOURCE_LINK,
                "source_kind": PROMPT_SOURCE_DOWNLOADED_VIDEO if video_path else PROMPT_SOURCE_LINK,
                "source_no": source_no,
                "video_path": video_path,
                "video_name": str((download_entry or {}).get("video_name") or "").strip(),
                "prompt_folder": prompt_folder,
                "source_link": link_url,
            })

    if not targets and prompt_entries:
        for idx, item in enumerate(prompt_entries, start=1):
            folder_name = str(item.get("folder_name") or "").strip()
            source_no = _extract_prompt_folder_no(folder_name) or idx
            targets.append({
                "target_key": _video_settings_entry_key(effective_mode, source_no, folder_name),
                "label": folder_name,
                "source_label": "Prompt",
                "source_mode": effective_mode,
                "source_kind": "prompt",
                "source_no": source_no,
                "video_path": "",
                "video_name": "",
                "prompt_folder": folder_name,
                "source_link": "",
            })

    targets.sort(key=lambda item: int(item.get("source_no") or 0))
    return targets, effective_mode


def _build_video_settings_editor_entries(
    source_targets: list[dict],
    saved_state: dict,
    harita: dict,
    selected_alt_model: str,
    default_settings: dict,
) -> list[dict]:
    entries = []
    targets = list(source_targets or [])
    saved_entries = (saved_state or {}).get("entries", []) if isinstance(saved_state, dict) else []

    if not targets and isinstance(saved_entries, list):
        targets = _build_saved_video_settings_fallback_targets(saved_state)

    for idx, target in enumerate(targets, start=1):
        saved_entry = _match_saved_video_settings_entry(target, saved_entries)
        base_settings = dict(default_settings)
        detected = {
            "actual_duration_seconds": 0.0,
            "actual_duration_label": "",
            "actual_resolution": "",
            "aspect_ratio": "",
            "duration": 0,
        }
        note = ""
        video_path = str(target.get("video_path") or "").strip()
        if video_path and os.path.exists(video_path):
            metadata = _get_video_media_metadata(video_path)
            duration_seconds = float(metadata.get("duration") or 0.0)
            width = int(metadata.get("width") or 0)
            height = int(metadata.get("height") or 0)
            detected["actual_duration_seconds"] = duration_seconds
            detected["actual_duration_label"] = _format_duration(duration_seconds) if duration_seconds > 0 else ""
            detected["actual_resolution"] = f"{width}x{height}" if width > 0 and height > 0 else ""
            detected["aspect_ratio"] = _closest_supported_aspect_ratio(width, height, harita.get("aspect_ratios", []))
            detected["duration"] = _closest_supported_duration(duration_seconds, harita.get("durations", []))
            if detected["aspect_ratio"]:
                base_settings["aspect_ratio"] = detected["aspect_ratio"]
            if detected["duration"]:
                base_settings["duration"] = detected["duration"]
            if not detected["actual_duration_label"] and detected["duration"]:
                detected["actual_duration_label"] = f"{detected['duration']}sn"
        elif target.get("source_mode") == PROMPT_SOURCE_LINK:
            note = "Yerel video dosyası henüz bulunamadı. Süre ve boyut alanlarını elle düzenleyebilirsiniz."
        else:
            note = "Bu video için otomatik algılama yapılamadı. Varsayılan ayarlar kullanıldı."

        if isinstance(saved_entry, dict):
            base_settings.update(saved_entry.get("settings") if isinstance(saved_entry.get("settings"), dict) else {})
            if isinstance(saved_entry.get("detected"), dict):
                for key, value in saved_entry.get("detected", {}).items():
                    detected[key] = value
            if str(saved_entry.get("note") or "").strip():
                note = str(saved_entry.get("note") or "").strip()

        sanitized_settings = _sanitize_video_setting_values(base_settings, harita, selected_alt_model, default_settings)
        prompt_folder = str(target.get("prompt_folder") or "").strip()
        entries.append({
            "target_key": str(target.get("target_key") or _video_settings_entry_key(target.get("source_mode"), target.get("source_no"), prompt_folder)).strip(),
            "label": str(target.get("label") or f"Video {idx}").strip() or f"Video {idx}",
            "source_label": str(target.get("source_label") or "").strip(),
            "source_mode": _normalize_video_settings_source_mode(target.get("source_mode")),
            "source_kind": str(target.get("source_kind") or "").strip(),
            "source_no": int(target.get("source_no") or idx),
            "video_path": video_path,
            "video_name": str(target.get("video_name") or "").strip(),
            "prompt_folder": prompt_folder,
            "source_link": str(target.get("source_link") or "").strip(),
            "detected": detected,
            "note": note,
            "settings": sanitized_settings,
        })
    return entries


def _prime_video_settings_editor_widgets(entries: list[dict], force: bool = False):
    for entry in entries or []:
        key_suffix = str(entry.get("target_key") or "").strip()
        settings = entry.get("settings") if isinstance(entry.get("settings"), dict) else {}
        defaults = {
            f"va_pv_quality_{key_suffix}": settings.get("quality"),
            f"va_pv_aspect_{key_suffix}": settings.get("aspect_ratio"),
            f"va_pv_duration_{key_suffix}": settings.get("duration"),
            f"va_pv_ses_{key_suffix}": settings.get("ses"),
        }
        for widget_key, widget_value in defaults.items():
            if force or widget_key not in st.session_state:
                st.session_state[widget_key] = widget_value


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
            
    try:
        seen_added = set()
        for idx, entry in enumerate(_list_added_video_preview_entries(), start=1):
            try:
                source_no = int(entry.get("no") or idx)
            except Exception:
                source_no = idx
            label = f"Eklenen Video {source_no}"
            if label not in seen_added:
                result["added_videos"].append(label)
                seen_added.add(label)
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
    template_options = _get_prompt_template_options(st.session_state.settings)
    template_map = {item["key"]: item for item in template_options}
    kayitli_template_key = _normalize_prompt_template_key(
        st.session_state.settings.get("prompt_template_key"),
        "original",
    )
    if st.session_state.get("prompt_template_choice") not in template_map:
        st.session_state["prompt_template_choice"] = kayitli_template_key
    secili_template_key = _normalize_prompt_template_key(
        st.session_state.get("prompt_template_choice"),
        kayitli_template_key,
    )
    secili_template = template_map.get(secili_template_key, template_map.get("original"))

    st.markdown("#### 🧠 İstem Seçimi")
    template_cols = st.columns(len(template_options))
    for idx, template in enumerate(template_options):
        with template_cols[idx]:
            if st.button(
                template["label"],
                key=f"pa_template_{template['key']}",
                use_container_width=True,
                type="primary" if secili_template_key == template["key"] else "secondary",
            ):
                st.session_state["prompt_template_choice"] = template["key"]
                st.session_state.ek_dialog_open = "prompt_ayarlari"
                st.rerun()

    if secili_template:
        st.caption(f"Seçili istem: {secili_template['label']} ({os.path.basename(secili_template['path'])})")
        if not os.path.exists(secili_template["path"]):
            st.warning(f"Seçili istem dosyası bulunamadı: {secili_template['path']}")
    st.markdown("---")
    
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
            secili_template_key = _normalize_prompt_template_key(
                st.session_state.get("prompt_template_choice"),
                kayitli_template_key,
            )
            secili_template = template_map.get(secili_template_key, template_map.get("original"))
            if not secili_template:
                st.error("Seçili istem bulunamadı.")
                return
            if not os.path.exists(secili_template["path"]):
                st.error(f"Seçili istem dosyası bulunamadı: {secili_template['path']}")
                return

            new_mode = "all" if tumunu_uret else "custom"
            st.session_state.settings["prompt_template_key"] = secili_template["key"]
            save_settings(st.session_state.settings)
            _prompt_input_selection_save(new_mode, {
                "links": secili_linkler,
                "downloaded_videos": secili_indirilen,
                "added_videos": secili_eklenen
            })
            st.success(f"Ayarlar kaydedildi! İstem: {secili_template['label']}")
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
    active_video_model = get_active_video_model(st.session_state.settings)
    if _is_video_transition_mode() and not video_model_supports_transition(active_video_model):
        log(f"[ERROR] {active_video_model} modeli Start End Frame (Transition) modunu desteklemiyor.")
        st.session_state.status["pixverse"] = "error"
        return False

    overridden = False
    extra_args = []
    prompt_source = _resolve_video_prompt_source_for_generation()
    if prompt_source.get("kind") == "gorsel_motion":
        overridden = True
        extra_args = ["--prompt-dir", prompt_source.get("prompt_dir", GORSEL_HAREKET_PROMPT_DIR), "--ref-image-dir", prompt_source.get("ref_image_dir", GORSEL_HAREKET_REFERANS_DIR)]
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
            _current["prompt_dir"] = prompt_source.get("prompt_dir", GORSEL_HAREKET_PROMPT_DIR)
            _current["gorsel_klonlama_dir"] = prompt_source.get("ref_image_dir", GORSEL_HAREKET_REFERANS_DIR)
            with open(SETTINGS_PATH, "w", encoding="utf-8") as _wf:
                _json.dump(_current, _wf, ensure_ascii=False, indent=2)
            log(f"[INFO] Video prompt kaynağı -> Görsel Hareketlendirme Prompt ({prompt_source.get('reason', 'state_active')})")
            log(f"[INFO] PROMPT_ROOT override: {prompt_source.get('prompt_dir', GORSEL_HAREKET_PROMPT_DIR)}")
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
    saved_override_state = _video_settings_override_load()

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

    transition_state = _load_transition_ui_state()
    saved_video_mode = transition_state.get("video_mode", "normal")
    transition_supported = video_model_supports_transition(secilen_model)
    if transition_supported:
        video_mode_options = ["Normal Video", "Start End Frame (Transition)"]
        saved_mode_label = _video_mode_option_label(saved_video_mode)
        selected_video_mode_label = st.radio(
            "Üretim Modu",
            video_mode_options,
            horizontal=True,
            index=video_mode_options.index(saved_mode_label) if saved_mode_label in video_mode_options else 0,
            key="va_video_mode",
        )
        selected_video_mode = _video_mode_option_value(selected_video_mode_label)
        if selected_video_mode == "transition":
            st.info("Transition modunda PixVerse komutu `create transition --images start end` ile çalışır. Bu modda aspect-ratio alanı CLI tarafından kullanılmadığı için oran start/end görsellerinden gelir.")
    else:
        selected_video_mode = "normal"
        st.info(f"{secilen_model} modeli Start End Frame (Transition) modunu desteklemiyor. Bu model için yalnızca Normal Video kullanılabilir.")

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

    boyut_secenekleri = harita.get("aspect_ratios", ["16:9", "9:16"])
    mevcut_boyut = mevcut.get("aspect_ratio", boyut_secenekleri[0] if boyut_secenekleri else "16:9")
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
    if st.session_state.get("va_apply_mode") not in {"Tek Ayar", "Video Bazlı Ayar"}:
        st.session_state["va_apply_mode"] = "Video Bazlı Ayar" if saved_override_state.get("mode") == "per_video" else "Tek Ayar"
    if _normalize_video_settings_source_mode(st.session_state.get("va_override_source_mode")) == "auto" and saved_override_state.get("source_mode") != "auto":
        st.session_state["va_override_source_mode"] = saved_override_state.get("source_mode")

    global_settings = {
        "aspect_ratio": secilen_boyut,
        "duration": secilen_sure_int,
        "ses": secilen_ses,
        "quality": secilen_kalite,
        "model": secilen_alt_model,
    }

    st.markdown("#### 🧩 Ayar Uygulama Şekli")
    kayit_modu = st.radio(
        "Ayar modu",
        ["Tek Ayar", "Video Bazlı Ayar"],
        key="va_apply_mode",
        horizontal=True,
        label_visibility="collapsed",
    )

    override_entries_for_save = []
    override_source_mode = _normalize_video_settings_source_mode(saved_override_state.get("source_mode"))
    if kayit_modu == "Video Bazlı Ayar":
        st.caption("Video bazlı ayarda tek blok ayarı koruyup, her video için ayrıca süre/boyut/kalite/ses düzenleyebilirsiniz.")
        source_mode_options = ["auto", PROMPT_SOURCE_LINK, PROMPT_SOURCE_DOWNLOADED_VIDEO, PROMPT_SOURCE_ADDED_VIDEO]
        mevcut_source_mode = _normalize_video_settings_source_mode(st.session_state.get("va_override_source_mode"))
        if mevcut_source_mode not in source_mode_options:
            mevcut_source_mode = _normalize_video_settings_source_mode(saved_override_state.get("source_mode"))
        if mevcut_source_mode not in source_mode_options:
            mevcut_source_mode = "auto"
        st.session_state["va_override_source_mode"] = mevcut_source_mode
        override_source_mode = st.selectbox(
            "Otomatik algılama kaynağı",
            source_mode_options,
            key="va_override_source_mode",
            format_func=_video_settings_source_mode_label,
        )
        source_targets, effective_source_mode = _list_video_settings_source_targets(override_source_mode)
        source_signature = json.dumps(
            {
                "model": secilen_model,
                "alt_model": secilen_alt_model,
                "targets": [
                    {
                        "target_key": item.get("target_key"),
                        "source_no": item.get("source_no"),
                        "prompt_folder": item.get("prompt_folder"),
                        "video_path": item.get("video_path"),
                        "source_link": item.get("source_link"),
                    }
                    for item in source_targets
                ],
            },
            ensure_ascii=False,
        )

        if override_source_mode == "auto":
            st.caption(f"Aktif algılama kaynağı: {_video_settings_source_mode_label(effective_source_mode)}")

        detect_clicked = st.button(
            "📡 Otomatik Algıla / Listeyi Güncelle",
            key="va_detect_source_videos",
            use_container_width=True,
        )

        needs_init = ("va_per_video_targets" not in st.session_state) or (st.session_state.get("va_per_video_source_signature") != source_signature)
        if detect_clicked or needs_init:
            built_entries = _build_video_settings_editor_entries(
                source_targets,
                saved_override_state,
                harita,
                secilen_alt_model,
                global_settings,
            )
            st.session_state["va_per_video_targets"] = built_entries
            st.session_state["va_per_video_source_signature"] = source_signature
            _prime_video_settings_editor_widgets(built_entries, force=detect_clicked or needs_init)
            if detect_clicked:
                st.session_state.ek_dialog_open = "video_ayarlari"
                st.rerun()

        editor_entries = st.session_state.get("va_per_video_targets", []) or []
        missing_local_video = [entry for entry in editor_entries if not str(entry.get("video_path") or "").strip()]
        if missing_local_video and effective_source_mode == PROMPT_SOURCE_LINK:
            st.warning("Bazı Link girdileri için indirilen video bulunamadı. Bu satırlarda süre ve boyutu elle düzenleyebilirsiniz.")
        if not editor_entries:
            st.info("Video bazlı ayar oluşturmak için algılanacak kaynak video veya prompt bulunamadı.")
        else:
            summary_rows = []
            for entry in editor_entries:
                detected = entry.get("detected") if isinstance(entry.get("detected"), dict) else {}
                summary_rows.append({
                    "Video": entry.get("label"),
                    "Kaynak": entry.get("source_label") or _video_settings_source_mode_label(entry.get("source_mode")),
                    "Algılanan Süre": detected.get("actual_duration_label") or "Elle",
                    "Algılanan Boyut": detected.get("aspect_ratio") or "-",
                    "Prompt": entry.get("prompt_folder") or "-",
                })
            st.markdown("**Algılanan Video Listesi:**")
            st.table(summary_rows)

            duration_options = [int(item) for item in harita.get("durations", [])]
            quality_options = list(harita.get("quality_map", {}).get(secilen_alt_model, ["720p"]))
            aspect_options = list(harita.get("aspect_ratios", ["16:9"]))
            ses_options = ["açık", "kapalı"] if harita.get("ses", False) else ["kapalı"]

            for idx, entry in enumerate(editor_entries, start=1):
                target_key = str(entry.get("target_key") or f"video_{idx}").strip()
                detected = entry.get("detected") if isinstance(entry.get("detected"), dict) else {}
                prompt_caption = entry.get("prompt_folder") or "Prompt klasörü henüz oluşmadı"
                header = f"{entry.get('label') or f'Video {idx}'}"
                with st.expander(f"🎬 {header}", expanded=idx <= 3):
                    st.caption(f"Eşleşen prompt: {prompt_caption}")
                    if detected.get("actual_resolution") or detected.get("actual_duration_label"):
                        st.caption(
                            f"Algılandı: {detected.get('actual_resolution') or 'Çözünürlük yok'}"
                            f" | {detected.get('actual_duration_label') or 'Süre yok'}"
                            f" | Öneri oran: {detected.get('aspect_ratio') or '-'}"
                            f" | Öneri süre: {str(detected.get('duration') or '-') + 's' if detected.get('duration') else '-'}"
                        )
                    if entry.get("note"):
                        st.caption(str(entry.get("note") or "").strip())

                    cols = st.columns(4 if harita.get("ses", False) else 3)
                    with cols[0]:
                        st.selectbox(
                            "Kalite",
                            quality_options,
                            key=f"va_pv_quality_{target_key}",
                        )
                    with cols[1]:
                        st.selectbox(
                            "Video Boyutu",
                            aspect_options,
                            key=f"va_pv_aspect_{target_key}",
                        )
                    with cols[2]:
                        st.selectbox(
                            "Video Süresi",
                            duration_options,
                            key=f"va_pv_duration_{target_key}",
                            format_func=lambda value: f"{value}s",
                        )
                    if harita.get("ses", False):
                        with cols[3]:
                            st.selectbox(
                                "Ses",
                                ses_options,
                                key=f"va_pv_ses_{target_key}",
                            )

            for entry in editor_entries:
                target_key = str(entry.get("target_key") or "").strip()
                override_entries_for_save.append({
                    "target_key": target_key,
                    "label": str(entry.get("label") or "").strip(),
                    "source_label": str(entry.get("source_label") or "").strip(),
                    "source_mode": _normalize_video_settings_source_mode(entry.get("source_mode")),
                    "source_kind": str(entry.get("source_kind") or "").strip(),
                    "source_no": int(entry.get("source_no") or 0),
                    "video_path": str(entry.get("video_path") or "").strip(),
                    "video_name": str(entry.get("video_name") or "").strip(),
                    "prompt_folder": str(entry.get("prompt_folder") or "").strip(),
                    "source_link": str(entry.get("source_link") or "").strip(),
                    "detected": entry.get("detected") if isinstance(entry.get("detected"), dict) else {},
                    "note": str(entry.get("note") or "").strip(),
                    "settings": _sanitize_video_setting_values(
                        {
                            "quality": st.session_state.get(f"va_pv_quality_{target_key}"),
                            "aspect_ratio": st.session_state.get(f"va_pv_aspect_{target_key}"),
                            "duration": st.session_state.get(f"va_pv_duration_{target_key}"),
                            "ses": st.session_state.get(f"va_pv_ses_{target_key}", "kapalı"),
                            "model": secilen_alt_model,
                        },
                        harita,
                        secilen_alt_model,
                        global_settings,
                    ),
                })
    else:
        st.caption("Tek ayar modu seçildiğinde mevcut ayarlar tüm videolara aynı şekilde uygulanır.")

    st.markdown("---")
    c_save, c_clear, c_back = st.columns(3)
    with c_save:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("💾 Kaydet", use_container_width=True, key="va_kaydet", disabled=_v56_kisit_hatasi):
            if not tumunu_uret and not secili_promptlar:
                st.error("❌ En az 1 prompt seçin veya 'Tüm promptları üret' seçeneğini açın.")
            elif kayit_modu == "Video Bazlı Ayar" and not override_entries_for_save:
                st.error("❌ Video bazlı ayar için algılanan en az 1 video olmalı.")
            elif txt_path:
                ok = _video_ayar_kaydet(txt_path, secilen_boyut, f"{secilen_sure_int}s", secilen_ses, secilen_kalite, secilen_alt_model)
                if ok:
                    _save_transition_ui_state({"video_mode": selected_video_mode})
                    kayit = _video_prompt_selection_save(
                        prompt_options if tumunu_uret else secili_promptlar,
                        prompt_options,
                    )
                    if kayit.get("mode") == "custom":
                        secim_ozeti = ", ".join(kayit.get("selected_prompt_folders", []))
                        log(f"[INFO] Seçili promptlar kaydedildi: {secim_ozeti}")
                    else:
                        log("[INFO] Video üretimi tüm promptlar için ayarlandı.")
                    if kayit_modu == "Video Bazlı Ayar":
                        override_ok = _video_settings_override_save(
                            "per_video",
                            override_source_mode,
                            override_entries_for_save,
                            extra={
                                "selected_model": secilen_model,
                                "video_mode": selected_video_mode,
                            },
                        )
                        if not override_ok:
                            st.error("❌ Video bazlı ayarlar kaydedilemedi!")
                            st.markdown('</div>', unsafe_allow_html=True)
                            return
                        log(f"[INFO] Video bazlı ayarlar kaydedildi: {len(override_entries_for_save)} video")
                        st.session_state["video_ayar_notice"] = f"✅ Ayarlar kaydedildi! {len(override_entries_for_save)} video için ayrı video ayarı uygulanacak."
                    else:
                        _clear_video_settings_overrides(reset_widgets=True)
                        st.session_state["video_ayar_notice"] = "✅ Ayarlar kaydedildi! Tüm videolar için tek blok ayarı kullanılacak."
                    log(f"[INFO] Video ayarları kaydedildi: {secilen_model} → {secilen_boyut}, {secilen_sure_int}s, {secilen_kalite}, ses={secilen_ses}, model={secilen_alt_model}")
                    st.session_state["va_saved"] = True
                    st.session_state.ek_dialog_open = "video_ayarlari"
                    st.rerun()
                else:
                    st.error("❌ Ayarlar kaydedilemedi!")
            else:
                st.error("❌ Script yolu bulunamadı!")
        st.markdown('</div>', unsafe_allow_html=True)
    with c_clear:
        st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
        if st.button("🗑️ Kayıt Temizle", key="va_clear_saved", use_container_width=True):
            _clear_video_settings_overrides(reset_widgets=True)
            st.session_state["va_apply_mode"] = "Tek Ayar"
            st.session_state["va_override_source_mode"] = "auto"
            st.session_state["video_ayar_notice"] = "🗑️ Video bazlı kayıtlar temizlendi. Tek ayar moduna dönüldü."
            st.session_state.ek_dialog_open = "video_ayarlari"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c_back:
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("⬅️ Geri", key="bck_video_ayar", use_container_width=True):
            st.session_state.ek_dialog_open = "menu"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("video_ayar_notice"):
        st.success(st.session_state.pop("video_ayar_notice"))


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
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="bck_kredi", use_container_width=True):
        st.session_state.ek_dialog_open = "menu"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)




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
        if key == "video_klonla":
            return False
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
        "video_klonla": "Klon Video Uretiliyor...",
        "youtube_link": "📺 YouTube linkleri hazırlanıyor...",
        "download": "⬇️ Video İndiriliyor...",
        "gorsel_analiz": "🖼️ Görsel Analiz Yapılıyor...",
        "gorsel_klonlama": f"🎨 {st.session_state.settings.get('gorsel_klonlama_model', DEFAULT_GORSEL_KLONLAMA_MODEL)} ile Görsel Klonlanıyor...",
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

    _manual_batch_mode = _is_manual_batch_selection()

    if _manual_batch_mode:
        c_chk_analyze, c_btn_analyze = st.columns([0.12, 0.88])
        with c_chk_analyze:
            st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
            _batch_selection_checkbox("analyze", "Prompt Oluştur seçimi", "chk_batch_analyze")
            st.markdown("</div>", unsafe_allow_html=True)
        with c_btn_analyze:
            _clicked_analyze = render_step_button("analyze", "📝 Prompt Oluştur", "btn-info", "Prompt Oluşturuluyor...")
    else:
        _clicked_analyze = render_step_button("analyze", "📝 Prompt Oluştur", "btn-info", "Prompt Oluşturuluyor...")

    if _clicked_analyze:
        st.session_state.single_paused = False; st.session_state.single_finish_requested = False; st.session_state.single_mode = True
        st.session_state.bg_last_result = None; st.session_state.single_step = "analyze"
        cleanup_flags(); st.session_state.status["analyze"] = "running"; st.rerun()

    if render_step_button("video_klonla", "🎬 Klon Video Üret", "btn-teal", "Klon Video Üretiliyor..."):
        st.session_state.single_paused = False; st.session_state.single_finish_requested = False; st.session_state.single_mode = True
        st.session_state.bg_last_result = None; st.session_state.single_step = "video_klonla"
        cleanup_flags(); st.session_state.status["video_klonla"] = "running"; st.rerun()

    if _manual_batch_mode:
        c_chk_pixverse, c_btn_pixverse = st.columns([0.12, 0.88])
        with c_chk_pixverse:
            st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
            _batch_selection_checkbox("pixverse", "Video Üret seçimi", "chk_batch_pixverse")
            st.markdown("</div>", unsafe_allow_html=True)
        with c_btn_pixverse:
            _clicked_pixverse = render_step_button("pixverse", get_video_generation_label(), "btn-warning", get_video_generation_loading_text())
    else:
        _clicked_pixverse = render_step_button("pixverse", get_video_generation_label(), "btn-warning", get_video_generation_loading_text())

    if _clicked_pixverse:
        st.session_state.single_paused = False; st.session_state.single_finish_requested = False; st.session_state.single_mode = True
        st.session_state.bg_last_result = None; st.session_state.single_step = "pixverse"
        cleanup_flags(); st.session_state.status["pixverse"] = "running"; st.rerun()

    st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
    if st.button("⚡ Tümünü Çalıştır", key="run_all", use_container_width=True, disabled=st.session_state.get("batch_mode", False) or any_running() or st.session_state.get("single_mode", False), on_click=clear_dialog_states):
        secs = _ensure_batch_selection_state()
        queue = _build_manual_batch_queue(secs) if _is_manual_batch_selection() else _build_auto_batch_queue(secs)
        if not queue:
            st.session_state.batch_empty_selection_warning = True
            st.rerun()
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

    st.radio(
        "Tümünü Çalıştır Modu",
        [BATCH_RUN_MODE_AUTO, BATCH_RUN_MODE_MANUAL],
        horizontal=True,
        index=[BATCH_RUN_MODE_AUTO, BATCH_RUN_MODE_MANUAL].index(_get_batch_run_mode()),
        key=BATCH_RUN_MODE_WIDGET_KEY,
        on_change=_sync_batch_run_mode_widget,
        disabled=is_ui_locked(),
    )
    if _is_manual_batch_selection():
        _manual_order_text = _manual_batch_order_text()
        st.caption(f"Manual sıra: {_manual_order_text}" if _manual_order_text else "Manual sıra: seçim bekliyor")

    if st.session_state.get("batch_empty_selection_warning", False):
        st.warning("Manual Seçim için en az bir işlem işaretleyin.")
        st.session_state.batch_empty_selection_warning = False

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

    secs  = _ensure_batch_selection_state()
    # Checkbox seçili olmasa bile işlem aktif çalışıyorsa gerçek durumu göster
    _ACTIVE_STS = ("running", "ok", "error", "partial", "paused")
    ga_st = stt["gorsel_analiz"]   if (secs.get("gorsel_analiz")   or stt["gorsel_analiz"]   in _ACTIVE_STS) else "idle"
    gk_st = stt["gorsel_klonlama"] if (secs.get("gorsel_klonla")   or stt["gorsel_klonlama"] in _ACTIVE_STS) else "idle"
    pd_st = stt["prompt_duzeltme"] if (secs.get("prompt_duzeltme") or stt["prompt_duzeltme"] in _ACTIVE_STS) else "idle"
    vk_st = stt.get("video_klonla", "idle") if (secs.get("video_klonla") or stt.get("video_klonla", "idle") in _ACTIVE_STS) else "idle"

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
            "gorsel_klonlama":"Gorsel Klonla","analyze":"Prompt Olustur","prompt_duzeltme":"Prompt Duzelt","gorsel_olustur":"Gorsel Olustur","pixverse":get_workflow_video_generation_title().replace("Ü", "U").replace("ü", "u").replace("Ş", "S").replace("ş", "s").replace("İ", "I").replace("ı", "i").replace("Ö", "O").replace("ö", "o").replace("Ç", "C").replace("ç", "c"),"video_montaj":"Video Montaj","sosyal_medya":"Sosyal Medya Paylasim"}
    _TTL2= {"input":"Kaynak","download":"Video İndir","gorsel_analiz":"Görsel Analiz",
            "gorsel_klonlama":"Görsel Klonla","analyze":"Prompt Oluştur","prompt_duzeltme":"Prompt Düzelt","gorsel_olustur":f"{st.session_state.settings.get('gorsel_model', 'Nano Banana 2')} Görsel Oluştur","pixverse":get_workflow_video_generation_title(),"video_montaj":"Video Montaj","sosyal_medya":"Sosyal Medya Paylaşım"}
    _SUB = {"input":get_link_canvas_subtitle(stt),"download":"Sunucuya indir","gorsel_analiz":"Görselleri analiz et",
            "gorsel_klonlama":"Görseli klonla","analyze":"Prompt & Analiz","prompt_duzeltme":"Promptu düzelt","gorsel_olustur":"Görsel ve Hareketlendirme üret","pixverse":get_workflow_video_generation_canvas_subtitle(),"video_montaj":"Videoları birleştir","sosyal_medya":"Paylaşımı planla ve yayınla"}
    _STS = {"input":get_link_canvas_status(stt),"download":stt["download"],"gorsel_analiz":ga_st,
            "gorsel_klonlama":gk_st,"analyze":stt["analyze"],"prompt_duzeltme":pd_st,"gorsel_olustur":go_st,"pixverse":(vk_st if vk_st in _ACTIVE_STS else stt["pixverse"]),"video_montaj":vm_st,
            "sosyal_medya":(stt["sosyal_medya"] if (secs.get("sosyal_medya") or stt["sosyal_medya"] in _ACTIVE_STS) else "idle")}

    if montaj_canvas_mode == "toplu_video":
        _EMJ["video_montaj"] = "🎬"
        _TTL["video_montaj"] = "Toplu Video Montaj"
        _TTL2["video_montaj"] = "Toplu Video Montaj"
        _SUB["video_montaj"] = "Toplu varyasyon montajı oluştur"

    _manual_canvas_mode = _is_manual_batch_selection()
    _DIS = {
        "gorsel_analiz":  not secs.get("gorsel_analiz")  and stt["gorsel_analiz"]   not in _ACTIVE_STS,
        "gorsel_klonlama":not secs.get("gorsel_klonla")  and stt["gorsel_klonlama"] not in _ACTIVE_STS,
        "analyze":        _manual_canvas_mode and not secs.get("analyze") and stt["analyze"] not in _ACTIVE_STS,
        "prompt_duzeltme":not secs.get("prompt_duzeltme")and stt["prompt_duzeltme"] not in _ACTIVE_STS,
        "gorsel_olustur": not secs.get("gorsel_olustur") and go_st not in _ACTIVE_STS,
        "pixverse":       _manual_canvas_mode and not secs.get("pixverse") and _STS["pixverse"] not in _ACTIVE_STS,
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
        "sosyal_medya":   _klasor_dolu(cfg.get("video_montaj_output_dir", "")) or _klasor_dolu(cfg.get("toplu_video_output_dir", "")) or _klasor_dolu(cfg.get("video_output_dir", "")) or _klasor_dolu(cfg.get("klon_video_dir", "")),
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
            _card_grad_id = f"card_rbw_{nid}"
            top_strip = (
                f'<svg viewBox="0 0 330 8" preserveAspectRatio="none" '
                f'style="position:absolute;top:-1px;left:-1px;width:calc(100% + 2px);height:8px;overflow:hidden;pointer-events:none;">'
                f'<defs><linearGradient id="{_card_grad_id}" x1="0%" y1="0%" x2="100%" y2="0%">'
                f'<stop offset="0%" stop-color="#ff0000"/>'
                f'<stop offset="18%" stop-color="#ff8800"/>'
                f'<stop offset="36%" stop-color="#ffff00"/>'
                f'<stop offset="54%" stop-color="#4ade80"/>'
                f'<stop offset="76%" stop-color="#38bdf8"/>'
                f'<stop offset="100%" stop-color="#a855f7"/>'
                f'</linearGradient></defs>'
                f'<path d="M1.25 14 A12.75 12.75 0 0 1 14 1.25 L316 1.25 A12.75 12.75 0 0 1 328.75 14" '
                f'stroke="url(#{_card_grad_id})" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
                f'</svg>'
            )
            border_css = "background:rgba(15,23,42,0.82);border:1px solid rgba(255,255,255,0.08);border-top:0;"
        else:
            border_css = f"background:rgba(15,23,42,0.82);border:1px solid rgba(255,255,255,0.08);border-top:2.5px solid {top};"

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
            f'<div style="position:relative;{border_css}border-radius:14px;padding:14px 13px 12px;overflow:hidden;' +
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
        ds = f"stroke-dasharray:8,6;{_anim_css('dash-flow', 8.0)}" if active else "stroke-dasharray:5,5;opacity:0.25;"
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
            grad_id = f"rbw_h_{int(_wf_anim_now * 1000)}_{direction.replace('-', '_')}"
            defs = (
                f'<defs><linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="0%">'
                f'<stop offset="0%" stop-color="#ff0000"/>'
                f'<stop offset="18%" stop-color="#ff8800"/>'
                f'<stop offset="36%" stop-color="#ffff00"/>'
                f'<stop offset="54%" stop-color="#4ade80"/>'
                f'<stop offset="76%" stop-color="#38bdf8"/>'
                f'<stop offset="100%" stop-color="#a855f7"/>'
                f'</linearGradient></defs>'
            )
            c = f"url(#{grad_id})" if active else "#2d3748"
            ds = f"stroke-dasharray:8,6;{_anim_css('dash-flow', 8.0)}" if active else "stroke-dasharray:5,5;opacity:0.25;"
            x1, x2 = ("0", "100%") if direction == "left-to-right" else ("100%", "0")
            return (
                f'<div style="display:flex;align-items:center;justify-content:center;min-height:82px;padding:0 6px;">'
                f'<svg width="100%" height="14" style="overflow:visible;display:block;transform:translateZ(0);shape-rendering:geometricPrecision;">'
                f'{defs}'
                f'<line x1="{x1}" y1="7" x2="{x2}" y2="7" stroke="{c}" stroke-width="2.5" stroke-linecap="round" style="{ds}"/>'
                f'</svg></div>'
            )
        c = color if active else "#2d3748"
        ds = f"stroke-dasharray:8,6;{_anim_css('dash-flow', 8.0)}" if active else "stroke-dasharray:5,5;opacity:0.25;"
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
            grad_id = f"rbw_v_{int(_wf_anim_now * 1000)}"
            defs = (
                f'<defs><linearGradient id="{grad_id}" x1="0%" y1="0%" x2="0%" y2="100%">'
                f'<stop offset="0%" stop-color="#ff0000"/>'
                f'<stop offset="18%" stop-color="#ff8800"/>'
                f'<stop offset="36%" stop-color="#ffff00"/>'
                f'<stop offset="54%" stop-color="#4ade80"/>'
                f'<stop offset="76%" stop-color="#38bdf8"/>'
                f'<stop offset="100%" stop-color="#a855f7"/>'
                f'</linearGradient></defs>'
            )
            c = f"url(#{grad_id})" if active else "#2d3748"
            ds = f"stroke-dasharray:6,5;{_anim_css('dash-flow', 8.0)}" if active else "stroke-dasharray:5,5;opacity:0.25;"
            return (
                f'<div style="display:flex;justify-content:center;">'
                f'<svg width="20" height="34" viewBox="0 0 20 34" xmlns="http://www.w3.org/2000/svg" style="overflow:visible;transform:translateZ(0);shape-rendering:geometricPrecision;">'
                f'{defs}'
                f'<line x1="10" y1="2" x2="10" y2="32" stroke="{c}" stroke-width="2.5" stroke-linecap="round" style="{ds}"/>'
                f'</svg></div>'
            )
        c = color if active else "#2d3748"
        ds = f"stroke-dasharray:6,5;{_anim_css('dash-flow', 8.0)}" if active else "stroke-dasharray:5,5;opacity:0.25;"
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
        ds = f"stroke-dasharray:8,6;{_anim_css('dash-flow', 8.0)}" if active else "stroke-dasharray:5,5;opacity:0.25;"
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
    current_batch_step = batch_q[batch_idx] if (batch_on and 0 <= batch_idx < len(batch_q)) else None
    prev_batch_step = batch_q[batch_idx - 1] if (batch_on and 0 < batch_idx <= len(batch_q)) else None
    _wf_anim_now = time.time()

    def _anim_css(name: str, duration_s: float) -> str:
        phase = _wf_anim_now % duration_s
        return f"animation:{name} {duration_s:.2f}s linear infinite;animation-delay:-{phase:.3f}s;"

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
    e_h5_vis = batch_on and has_vm and has_sm
    e_h5_act = _edge_active("video_montaj", "sosyal_medya") or _edge_active("toplu_video", "sosyal_medya")

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
    with ca: st.markdown(_harr("#facc15", e_h4_act, e_h4_vis), unsafe_allow_html=True)
    with c2: st.markdown(_nd("pixverse"), unsafe_allow_html=True)

    # --- Arrows Row 4 to 5 ---
    if e_v4_rl_pv_vis:
        st.markdown(_diarr(_TOP["pixverse"], e_v4_rl_pv_act, e_v4_rl_pv_vis, direction="right-to-left"), unsafe_allow_html=True)
    elif e_v4_rv_vis:
        _, _, rv4 = st.columns([1, 0.28, 1])
        with rv4: st.markdown(_varr(_TOP["pixverse"], e_v4_rv_act, e_v4_rv_vis), unsafe_allow_html=True)
    else:
        lv4, _, _ = st.columns([1, 0.28, 1])
        with lv4: st.markdown(_varr("#facc15", e_v4_lv_act, e_v4_lv_vis), unsafe_allow_html=True)

    # --- Render Row 5 ---
    c1, ca, c2 = st.columns([1, 0.28, 1])
    with c1: st.markdown(_nd("sosyal_medya"), unsafe_allow_html=True)
    with ca:
        st.markdown(
            _harr(
                _TOP["video_montaj"],
                e_h5_act,
                e_h5_vis,
                direction="right-to-left"
            ),
            unsafe_allow_html=True
        )
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
        s["sora2_script"] = st.text_input("🎬 Sora 2 Script:", s.get("sora2_script",""), on_change=clear_dialog_states)
        s["kling30_script"] = st.text_input("🎬 Kling 3.0 Script:", s.get("kling30_script",""), on_change=clear_dialog_states)
        s["klingo3_script"] = st.text_input("🎬 Kling O3 Script:", s.get("klingo3_script",""), on_change=clear_dialog_states)
        s["seedance20_script"] = st.text_input("🎬 Seedance 2.0 Script:", s.get("seedance20_script",""), on_change=clear_dialog_states)
        s["happy_horse_script"] = st.text_input("🎬 Happy Horse 1.0 Script:", s.get("happy_horse_script",""), on_change=clear_dialog_states)
        s["veo31_script"] = st.text_input("🎬 Veo 3.1 Script:", s.get("veo31_script",""), on_change=clear_dialog_states)
        s["grok_script"] = st.text_input("🎬 Grok Script:", s.get("grok_script",""), on_change=clear_dialog_states)
        s["v56_script"] = st.text_input("🎬 PixVerse V6 Script:", s.get("v56_script",""), on_change=clear_dialog_states)
        s["c1_script"] = st.text_input("🎬 PixVerse Cinematic Script:", s.get("c1_script",""), on_change=clear_dialog_states)
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

    shutdown_left, shutdown_mid, shutdown_right = st.columns([1, 2, 1])
    with shutdown_mid:
        st.markdown('<div class="btn-purple">', unsafe_allow_html=True)
        if st.button("❌ Sistemi Kapat", key="shutdown_panel_btn", use_container_width=True):
            request_panel_shutdown()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("panel_shutdown_requested", False):
        st.markdown(
            '<div class="panel-shutdown-notice">Sistem kapatiliyor. Bu pencere birkac saniye icinde baglantiyi kapatacak.</div>',
            unsafe_allow_html=True,
        )

    # ---- VIDEO ÜRETME KREDİSİ — state temizleme ----
    # Grace period: başlatmadan hemen sonra bg_is_running() kısa süre False dönse bile state'i silme
    _kredi_kazan_start_ts = st.session_state.get("kredi_kazan_start_ts", 0.0)
    _kredi_cek_start_ts = st.session_state.get("kredi_cek_start_ts", 0.0)
    _kredi_kazan_grace_ok = (time.time() - _kredi_kazan_start_ts) > 10  # 10 saniye grace period
    _kredi_cek_grace_ok = (time.time() - _kredi_cek_start_ts) > 10
    if st.session_state.get("kredi_kazan_running", False) and not bg_is_running() and _kredi_kazan_grace_ok:
        _kredi_kazan_finished_by_user = st.session_state.get("kredi_kazan_finish", False)
        _clear_kredi_runtime_state()
        if not _kredi_kazan_finished_by_user:
            log("[INFO] Kredi kazanma işlemi tamamlandı.")
    if st.session_state.get("kredi_cek_running", False) and not bg_is_running() and _kredi_cek_grace_ok:
        _kredi_cek_finished_by_user = st.session_state.get("kredi_cek_finish", False)
        _clear_kredi_runtime_state()
        if not _kredi_cek_finished_by_user:
            log("[INFO] Kredi çekme işlemi tamamlandı.")


# --- PATCH_DIALOG_ROUTER_V1 ---

@st.dialog("🖼️ Görsel Oluştur", width="large")
def gorsel_olustur_dialog():
    st.subheader("Görsel Oluştur & Hareketlendir")
    mode_idx = 0 if st.session_state.get("go_mode_val", "Görsel") == "Video" else 1
    mode = st.radio("İşlem Modu", ["Video", "Görsel"], horizontal=True, index=mode_idx, key="go_mode_widget")
    if mode != st.session_state.get("go_mode_val"):
        st.session_state["go_mode_val"] = mode
    
    gorsel_models = PIXVERSE_IMAGE_MODEL_OPTIONS
    current_gm = _normalize_pixverse_image_model(
        st.session_state.settings.get("gorsel_model"),
        DEFAULT_GORSEL_MODEL,
    )
    
    secili_model = st.selectbox("Görsel Modeli", gorsel_models, index=gorsel_models.index(current_gm))
    if secili_model != current_gm:
        st.session_state.settings["gorsel_model"] = secili_model
        save_settings(st.session_state.settings)
        st.session_state.ek_dialog_open = "gorsel_olustur"
        st.rerun()

    transition_state = _load_transition_ui_state()
    stored_go_transition = bool(transition_state.get("gorsel_olustur_transition_enabled", False))
    go_transition_enabled = st.checkbox(
        "Start End Frame (Transition)",
        value=stored_go_transition,
        key="go_transition_toggle",
        help="Açıkken her görev için start ve end frame olacak şekilde iki görsel promptu kaydedilir.",
    )
    if go_transition_enabled != stored_go_transition:
        _save_transition_ui_state({"gorsel_olustur_transition_enabled": go_transition_enabled})
    if go_transition_enabled:
        st.caption("Bu modda her görev için iki görsel üretilir ve aynı klasöre start.png / end.png olarak kaydedilir.")
    
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
                start_prompt_label = "Start Frame Promptu" if go_transition_enabled else "Görsel Oluşturma Promptu"
                v_gp = st.text_area(start_prompt_label, value=st.session_state.get(f"go_gp_val_{i}", ""), key=f"go_gp_{i}")
                if v_gp != st.session_state.get(f"go_gp_val_{i}", ""): st.session_state[f"go_gp_val_{i}"] = v_gp
                
                start_style_label = "Start Frame Türü" if go_transition_enabled else "Görsel Türü"
                s_gs = st.selectbox(start_style_label, stiller, index=stiller.index(st.session_state.get(f"go_gs_val_{i}", "Yok")) if st.session_state.get(f"go_gs_val_{i}", "Yok") in stiller else 0, key=f"go_gs_{i}")
                if s_gs != st.session_state.get(f"go_gs_val_{i}", "Yok"): st.session_state[f"go_gs_val_{i}"] = s_gs

                if go_transition_enabled:
                    v_ep = st.text_area("End Frame Promptu", value=st.session_state.get(f"go_ep_val_{i}", ""), key=f"go_ep_{i}")
                    if v_ep != st.session_state.get(f"go_ep_val_{i}", ""): st.session_state[f"go_ep_val_{i}"] = v_ep

                    s_es = st.selectbox("End Frame Türü", stiller, index=stiller.index(st.session_state.get(f"go_es_val_{i}", "Yok")) if st.session_state.get(f"go_es_val_{i}", "Yok") in stiller else 0, key=f"go_es_{i}")
                    if s_es != st.session_state.get(f"go_es_val_{i}", "Yok"): st.session_state[f"go_es_val_{i}"] = s_es
                
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
                    start_prompt_label = "Start Frame Promptu" if go_transition_enabled else "Görsel Oluşturma Promptu"
                    v_vid_gp = st.text_area(start_prompt_label, value=st.session_state.get(f"go_vid_gp_val_{i}", ""), key=f"go_vid_gp_{i}")
                    if v_vid_gp != st.session_state.get(f"go_vid_gp_val_{i}", ""): st.session_state[f"go_vid_gp_val_{i}"] = v_vid_gp
                    
                    start_style_label = "Start Frame Türü" if go_transition_enabled else "Görsel Türü"
                    s_vid_gs = st.selectbox(start_style_label, stiller, index=stiller.index(st.session_state.get(f"go_vid_gs_val_{i}", "Yok")) if st.session_state.get(f"go_vid_gs_val_{i}", "Yok") in stiller else 0, key=f"go_vid_gs_{i}")
                    if s_vid_gs != st.session_state.get(f"go_vid_gs_val_{i}", "Yok"): st.session_state[f"go_vid_gs_val_{i}"] = s_vid_gs

                    if go_transition_enabled:
                        v_vid_ep = st.text_area("End Frame Promptu", value=st.session_state.get(f"go_vid_ep_val_{i}", ""), key=f"go_vid_ep_{i}")
                        if v_vid_ep != st.session_state.get(f"go_vid_ep_val_{i}", ""): st.session_state[f"go_vid_ep_val_{i}"] = v_vid_ep

                        s_vid_es = st.selectbox("End Frame Türü", stiller, index=stiller.index(st.session_state.get(f"go_vid_es_val_{i}", "Yok")) if st.session_state.get(f"go_vid_es_val_{i}", "Yok") in stiller else 0, key=f"go_vid_es_{i}")
                        if s_vid_es != st.session_state.get(f"go_vid_es_val_{i}", "Yok"): st.session_state[f"go_vid_es_val_{i}"] = s_vid_es

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
            # Modeli kaydet (ki run edince arka planda doğru modeli okusun)
            st.session_state.settings["gorsel_model"] = secili_model
            save_settings(st.session_state.settings)

            gorsel_prompt_dir = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Prompt"
            video_prompt_dir  = r"C:\Users\User\Desktop\Otomasyon\Görsel\Görsel Hareklendirme Prompt"
            os.makedirs(gorsel_prompt_dir, exist_ok=True)
            os.makedirs(video_prompt_dir, exist_ok=True)
            
            count = st.session_state.go_gorsel_count if mode == "Görsel" else st.session_state.go_vid_count
            prefix = "go" if mode == "Görsel" else "go_vid"
            has_motion_prompt = False
            validation_errors = []
            
            for i in range(count):
                g_p = st.session_state.get(f"{prefix}_gp_{i}", "").strip()
                g_s = st.session_state.get(f"{prefix}_gs_{i}", "Yok")
                e_p = st.session_state.get(f"{prefix}_ep_{i}", "").strip() if go_transition_enabled else ""
                e_s = st.session_state.get(f"{prefix}_es_{i}", "Yok") if go_transition_enabled else "Yok"
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
                final_e_p = get_full_prompt(e_p, e_s)
                final_v_p = get_full_prompt(v_p, v_s)

                if go_transition_enabled and (not final_g_p or not final_e_p):
                    validation_errors.append(f"{i+1}. görev için Start ve End prompt alanları dolu olmalı.")
                    continue

                legacy_prompt_path = os.path.join(gp_sub, "gorsel_prompt.txt")
                start_prompt_path = os.path.join(gp_sub, "start_prompt.txt")
                end_prompt_path = os.path.join(gp_sub, "end_prompt.txt")

                if go_transition_enabled:
                    for old_path in (legacy_prompt_path,):
                        if os.path.exists(old_path):
                            try: os.remove(old_path)
                            except Exception: pass
                    with open(start_prompt_path, "w", encoding="utf-8") as f:
                        f.write(final_g_p)
                    with open(end_prompt_path, "w", encoding="utf-8") as f:
                        f.write(final_e_p)
                else:
                    for old_path in (start_prompt_path, end_prompt_path):
                        if os.path.exists(old_path):
                            try: os.remove(old_path)
                            except Exception: pass
                    with open(legacy_prompt_path, "w", encoding="utf-8") as f:
                        f.write(final_g_p)
                    
                if not v_p:
                    if os.path.exists(vp_sub): shutil.rmtree(vp_sub)
                else:
                    os.makedirs(vp_sub, exist_ok=True)
                    with open(os.path.join(vp_sub, "prompt.txt"), "w", encoding="utf-8") as f:
                        f.write(final_v_p)

            if validation_errors:
                st.error("Transition kaydı tamamlanamadı. " + " | ".join(validation_errors))
                st.markdown('</div>', unsafe_allow_html=True)
                return
            
            motion_prompt_active = bool(mode == "Görsel" and has_motion_prompt)
            st.session_state["go_motion_prompt_saved"] = motion_prompt_active
            st.session_state.settings["gorsel_olustur_mode"] = _normalize_gorsel_olustur_mode(mode)
            st.session_state.settings["gorsel_motion_prompt_active"] = motion_prompt_active
            save_settings(st.session_state.settings)
            _save_gorsel_olustur_state(mode, motion_prompt_active)
            _save_transition_ui_state({"gorsel_olustur_transition_enabled": go_transition_enabled})
            if motion_prompt_active:
                log("[INFO] Görsel hareketlendirme promptları kaydedildi. Video Üret görsel prompt klasörünü kullanacak.")
            else:
                log("[INFO] Görsel hareketlendirme promptu aktif değil. Video Üret standart Prompt klasörünü kullanacak.")
            if go_transition_enabled:
                log("[INFO] Görsel Oluştur transition modu aktif. Start/End promptları kaydedildi.")
                         
            st.session_state["go_saved"] = True
            st.session_state.ek_dialog_open = "gorsel_olustur"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with s2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("🗑️ Temizle", use_container_width=True):
            keys_to_del = [k for k in st.session_state.keys() if k.startswith(("go_gp", "go_gs", "go_ep", "go_es", "go_vp", "go_vs", "go_vid"))]
            for k in keys_to_del:
                del st.session_state[k]
            st.session_state.go_gorsel_count = 1
            st.session_state.go_vid_count = 1
            st.session_state["go_motion_prompt_saved"] = False
            st.session_state.settings["gorsel_motion_prompt_active"] = False
            save_settings(st.session_state.settings)
            _save_gorsel_olustur_state(st.session_state.get("go_mode_val", ""), False)
            _save_transition_ui_state({"gorsel_olustur_transition_enabled": False})
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


@st.dialog("🎬 Video Klonla", width="large")
def video_klonla_dialog():
    state = _load_video_klonla_state()
    st.subheader("Video Klonla")
    mode = st.radio("İşlem Modu", ["Video", "Klon"], horizontal=True, index=0 if str(state.get("mode", "Video")) == "Video" else 1, key="vk_mode_widget")
    clone_model = st.selectbox("Klon Modeli", ["Motion Control", "Modify"], index=0 if str(state.get("clone_model", "Motion Control")) == "Motion Control" else 1, key="vk_model_widget")

    st.markdown("**Videoları seçin:**")
    uploaded_videos = st.file_uploader(
        "Videoları seçin",
        type=["mp4", "mov", "avi", "mkv", "webm", "m4v"],
        accept_multiple_files=True,
        key="vk_video_upload",
        label_visibility="collapsed",
    )
    saved_direct_videos = _video_klonla_saved_direct_video_paths(state)
    if saved_direct_videos:
        st.caption("Kaydedilmiş videolar: " + ", ".join(os.path.basename(p) for p in saved_direct_videos))
    st.caption("Bilgisayarınızdan video yüklerseniz sadece bu listedeki videolar için görev oluşturulur. Boş bırakırsanız aktif kaynak sırası otomatik kullanılır.")

    batch_secs = st.session_state.get("ek_batch_secimler", {}) or {}
    image_owner = "batch" if any(batch_secs.get(key, False) for key in ("gorsel_analiz", "gorsel_klonla", "gorsel_olustur", "video_klonla")) else "single"
    image_entries = _prioritize_video_klonla_internal_images(_list_video_klonla_internal_images(), image_owner)
    image_label_map = {item["label"]: item["path"] for item in image_entries}
    reverse_image_label_map = {item["path"]: item["label"] for item in image_entries}
    task_targets = _video_klonla_build_task_targets(
        uploaded_files=uploaded_videos,
        saved_paths=None if uploaded_videos else saved_direct_videos,
    )
    task_inputs = {}
    configured_count = 0

    if clone_model == "Motion Control":
        st.info("Motion Control modunda her kaynak için ayrı referans görsel kaydedilir. Sistem içinden seçimde sıra numarası korunur.")
    else:
        st.info("Modify modunda her video için ayrı prompt kaydedilir. Referans görsel kullanılmaz.")

    if not task_targets:
        source_mode = _get_prompt_runtime_source_mode()
        if source_mode == PROMPT_SOURCE_ADDED_VIDEO:
            st.warning("Henüz Eklenen Video kaynağı bulunamadı. Önce 🎞️ Video Ekle bölümünden video ekleyin.")
        elif source_mode in {PROMPT_SOURCE_LINK, PROMPT_SOURCE_DOWNLOADED_VIDEO}:
            st.warning("Henüz Link / İndirilen Video kaynağı bulunamadı. Önce 📎 Video Listesi Ekle veya ⬇️ Video İndir adımlarını kullanın.")
        else:
            st.warning("Henüz görev oluşturulacak video kaynağı bulunamadı.")
    else:
        st.caption(f"{len(task_targets)} kaynak bulundu. Her kaynak için ayrı Video Klonla ayarı kaydedebilirsiniz.")

    for target in task_targets:
        task_state = _video_klonla_resolve_task_state(state, target)
        target_key = str(target.get("key") or "").strip()
        current_label = str(target.get("label") or f"Video {target.get('no') or ''}").strip()
        source_kind = str(target.get("source_kind") or "").strip()
        video_path = str(target.get("video_path") or "").strip()
        has_video_file = bool(video_path and os.path.exists(video_path))
        status_icon = "✅" if _video_klonla_target_has_config_for_model(clone_model, task_state, target, image_entries) else "⬜"

        with st.expander(f"{status_icon} {current_label}", expanded=False):
            if has_video_file:
                st.caption(f"Video: {os.path.basename(video_path)}")
            elif str(target.get("video_name") or "").strip():
                st.caption(f"Seçilen kaynak: {str(target.get('video_name') or '').strip()}")
            elif source_kind == "placeholder_link":
                st.caption("Gerçek link veya video eklendiğinde bu alan otomatik dolacak.")
            elif source_kind == "link":
                st.caption("Bu kaynak henüz indirilen videoya dönüşmedi. Ayar kaydolur; indirme tamamlanınca aynı sıra numarasıyla çalışır.")
            else:
                st.caption("Bu kaynak için video dosyası henüz görünmüyor. Yine de ayarı kaydedebilirsiniz.")

            if clone_model == "Modify":
                prompt_value = st.text_area(
                    f"{current_label} istemi",
                    value=str(task_state.get("modify_prompt") or ""),
                    key=f"vk_prompt_{target_key}",
                    height=120,
                    placeholder=f"{current_label} için modify istemini yazın",
                )
                task_inputs[target_key] = {
                    "modify_prompt": prompt_value,
                    "selected_image": str(task_state.get("selected_image") or ""),
                    "uploaded_image": None,
                    "use_system_images": bool(task_state.get("use_system_images", True)),
                }
                is_configured = bool(str(prompt_value or "").strip())
                if is_configured:
                    configured_count += 1
                else:
                    st.caption("Bu görev çalıştırılmaz; önce bir prompt girin.")
            else:
                referans_turleri = ["Sistem İçinden", "Özel Görsel"]
                referans_idx = 0 if bool(task_state.get("use_system_images", True)) else 1
                referans_turu = st.radio(
                    f"{current_label} referans kaynağı",
                    referans_turleri,
                    index=referans_idx,
                    horizontal=True,
                    key=f"vk_ref_mode_{target_key}",
                    label_visibility="collapsed",
                )
                use_system_images = referans_turu == "Sistem İçinden"
                selected_image_path = ""
                uploaded_image = None
                preview_item = None
                preview_caption = ""
                is_configured = False

                if use_system_images:
                    planned_image_info = _video_klonla_batch_planned_image_info(target, owner=image_owner)
                    auto_label = f"Otomatik sıra ({planned_image_info.get('label')})" if planned_image_info else "Otomatik sıra"
                    options = [auto_label] + [item["label"] for item in image_entries]
                    selected_label_default = reverse_image_label_map.get(str(task_state.get("selected_image") or "").strip(), "")
                    selected_idx = options.index(selected_label_default) if selected_label_default in options else 0
                    selected_label = st.selectbox(
                        f"{current_label} sistem görseli",
                        options,
                        index=selected_idx,
                        key=f"vk_system_image_{target_key}",
                    ) if image_entries else auto_label
                    if selected_label != auto_label:
                        selected_image_path = image_label_map.get(selected_label, "")

                    system_image_info = _video_klonla_resolve_system_image_info(
                        target,
                        selected_image_path,
                        image_entries,
                        owner=image_owner,
                    )
                    if system_image_info.get("path") and os.path.exists(str(system_image_info.get("path") or "").strip()):
                        preview_item = str(system_image_info.get("path") or "").strip()
                        preview_caption = str(system_image_info.get("label") or os.path.basename(preview_item)).strip()

                    if system_image_info.get("available"):
                        is_configured = True
                        configured_count += 1
                        if system_image_info.get("planned"):
                            st.caption(f"Eşleşme: {current_label} -> {system_image_info.get('label')}")
                            if system_image_info.get("detail"):
                                st.caption(str(system_image_info.get("detail") or "").strip())
                        elif not preview_item:
                            st.caption(f"Kullanılacak görsel: {system_image_info.get('label')}")
                    else:
                        if image_owner == "batch":
                            st.caption("Tümünü Çalıştır için önce Görsel Analiz veya Görsel Klonla tarafında bu sıraya uygun görsel oluşmalı.")
                        else:
                            st.caption("Sistem içinde kullanılacak görsel bulunamadı. Önce Görsel Klonla / Görsel Analiz / Görsel Oluştur tarafında görsel kaydedin.")
                else:
                    uploaded_image = st.file_uploader(
                        f"{current_label} özel görseli",
                        type=["png", "jpg", "jpeg", "webp", "bmp"],
                        accept_multiple_files=False,
                        key=f"vk_image_upload_{target_key}",
                    )
                    existing_uploaded_image = str(task_state.get("uploaded_image") or "").strip()
                    if uploaded_image is not None:
                        preview_item = uploaded_image
                        preview_caption = "Yeni yüklenen özel görsel"
                        is_configured = True
                        configured_count += 1
                    elif existing_uploaded_image and os.path.exists(existing_uploaded_image):
                        preview_item = existing_uploaded_image
                        preview_caption = "Kaydedilmiş özel görsel"
                        is_configured = True
                        configured_count += 1
                    else:
                        st.caption("Bu görev çalıştırılmaz; önce özel referans görseli yükleyin.")

                if preview_item is not None:
                    st.image(preview_item, width=180, caption=preview_caption)

                task_inputs[target_key] = {
                    "modify_prompt": str(task_state.get("modify_prompt") or ""),
                    "selected_image": selected_image_path,
                    "uploaded_image": uploaded_image,
                    "use_system_images": use_system_images,
                }

                if use_system_images and not is_configured:
                    st.caption("Bu görev için sıra numarasına uygun sistem görseli bekleniyor.")

    if task_targets:
        pending_count = max(0, len(task_targets) - configured_count)
        renk = "limegreen" if pending_count == 0 else ("orange" if configured_count > 0 else "tomato")
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 14px;margin:12px 0;">'
            f'🎬 <b>Video Klonla Görevleri</b> &nbsp;|&nbsp; {len(task_targets)} kaynak &nbsp;|&nbsp; '
            f'<span style="color:limegreen">✅ {configured_count} hazır</span> &nbsp;|&nbsp; '
            f'<span style="color:{renk}">⬜ {pending_count} eksik</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.caption("Motion Control otomatik v5.6 / 720p, Modify otomatik v5.5 / 720p kullanır.")

    def _vk_save_payload():
        saved_uploaded_videos = _video_klonla_persist_uploaded_files(uploaded_videos, "videos") if uploaded_videos else saved_direct_videos
        tasks_payload = dict(_video_klonla_tasks_dict(state))
        resolved_targets = _video_klonla_build_task_targets(saved_paths=saved_uploaded_videos)
        first_task_payload = None

        for target in resolved_targets:
            target_key = str(target.get("key") or "").strip()
            current_task_state = _video_klonla_resolve_task_state(state, target)
            form_state = task_inputs.get(target_key, {})
            task_payload = {
                "modify_prompt": str(current_task_state.get("modify_prompt") or "").strip(),
                "selected_image": str(current_task_state.get("selected_image") or "").strip(),
                "uploaded_image": str(current_task_state.get("uploaded_image") or "").strip(),
                "use_system_images": bool(current_task_state.get("use_system_images", True)),
                "label": str(target.get("label") or "").strip(),
                "source_group": str(target.get("source_group") or "").strip(),
                "source_no": int(target.get("no") or 0),
            }

            if clone_model == "Modify":
                task_payload["modify_prompt"] = str(form_state.get("modify_prompt") or "").strip()
            else:
                task_payload["use_system_images"] = bool(form_state.get("use_system_images", task_payload["use_system_images"]))
                if task_payload["use_system_images"]:
                    task_payload["selected_image"] = str(form_state.get("selected_image") or "").strip()
                    task_payload["uploaded_image"] = ""
                else:
                    uploaded_image = form_state.get("uploaded_image")
                    if uploaded_image is not None:
                        saved_uploaded_image_list = _video_klonla_persist_uploaded_files(
                            uploaded_image,
                            os.path.join("images", _video_klonla_safe_name(target_key)),
                        )
                        saved_uploaded_image = saved_uploaded_image_list[0] if saved_uploaded_image_list else ""
                    else:
                        saved_uploaded_image = str(current_task_state.get("uploaded_image") or "").strip()
                    task_payload["selected_image"] = ""
                    task_payload["uploaded_image"] = saved_uploaded_image if saved_uploaded_image and os.path.exists(saved_uploaded_image) else ""

            tasks_payload[target_key] = task_payload
            if first_task_payload is None:
                first_task_payload = dict(task_payload)

        if first_task_payload is None:
            first_task_payload = {
                "modify_prompt": str(state.get("modify_prompt") or "").strip(),
                "selected_image": str(state.get("selected_image") or "").strip(),
                "uploaded_image": str(state.get("uploaded_image") or "").strip(),
                "use_system_images": bool(state.get("use_system_images", True)),
            }

        return {
            "mode": mode,
            "clone_model": clone_model,
            "modify_prompt": str(first_task_payload.get("modify_prompt") or "").strip(),
            "selected_videos": _video_klonla_existing_paths(state.get("selected_videos")),
            "uploaded_videos": _video_klonla_existing_paths(saved_uploaded_videos),
            "selected_image": str(first_task_payload.get("selected_image") or "").strip(),
            "uploaded_image": str(first_task_payload.get("uploaded_image") or "").strip() if str(first_task_payload.get("uploaded_image") or "").strip() and os.path.exists(str(first_task_payload.get("uploaded_image") or "").strip()) else "",
            "use_system_images": bool(first_task_payload.get("use_system_images", True)),
            "system_image_sources": ["gorsel_analiz", "gorsel_klonla", "gorsel_olustur"],
            "motion_model": "v5.6",
            "motion_quality": "720p",
            "modify_model": "v5.5",
            "modify_quality": "720p",
            "modify_keyframe_time": 0,
            "tasks": tasks_payload,
        }

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
        if st.button("💾 Kaydet", key="vk_save", use_container_width=True):
            _save_video_klonla_state(_vk_save_payload())
            st.session_state["video_klonla_saved"] = True
            st.session_state.ek_dialog_open = "video_klonla"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("🗑️ Temizle Video Klonla", key="vk_clear", use_container_width=True):
            _video_klonla_clear_uploads()
            _save_video_klonla_state(_video_klonla_default_state())
            st.session_state["video_klonla_saved"] = False
            st.session_state.ek_dialog_open = "video_klonla"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.get("video_klonla_saved"):
        _vk_ph = st.empty(); _vk_ph.success("Kaydedildi! Artık Tümünü Çalıştır'ı başlatabilirsiniz."); time.sleep(2.0); _vk_ph.empty(); st.session_state.pop("video_klonla_saved", None)
    st.markdown("---")
    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.button("🚀 Video Klonla", key="vk_start", use_container_width=True, disabled=st.session_state.get("batch_mode", False) or any_running()):
        _save_video_klonla_state(_vk_save_payload())
        st.session_state.single_paused = False; st.session_state.single_finish_requested = False; st.session_state.single_mode = True; st.session_state.bg_last_result = None; st.session_state.single_step = "video_klonla"; cleanup_flags(); st.session_state.status["video_klonla"] = "running"; st.session_state.ek_dialog_open = "video_klonla"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    render_dialog_single_controls(step_match="video_klonla", prefix="dlg_video_klonla")
    st.markdown("---")
    st.markdown('<div class="btn-info">', unsafe_allow_html=True)
    if st.button("⬅️ Geri", key="vk_back", use_container_width=True):
        st.session_state.ek_dialog_open = "menu"; st.rerun()
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
            if not _running_now and not _keep_ek_dialog_open_on_rerun(hedef):
                st.session_state.ek_dialog_open = None
        st.session_state.pop("_ek_dialog_keepalive", None)
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
        elif hedef == "video_klonla":
            video_klonla_dialog()
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

# Keep polling background logs even while a dialog is open.
if bg_is_running() and not _is_any_paused:
    time.sleep(1)
    st.rerun()
