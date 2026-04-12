
import builtins
import json
import os
import re
import sys
import traceback


def patch_assignment(text, pattern, replacement):
    new_text, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.MULTILINE)
    if count == 0:
        print(f"[WARN] Değiştirilemedi: {pattern}")
    return new_text


def write_text_file(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(value or "").strip())


def main():
    if len(sys.argv) < 2:
        raise RuntimeError("Toplu video yapılandırma dosyası verilmedi.")

    config_path = sys.argv[1]
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    script_path = cfg["script_path"]
    with open(script_path, "r", encoding="utf-8", errors="replace") as f:
        source = f.read()

    source = patch_assignment(source, r"^ana_klasor\s*=.*$", f"ana_klasor = {cfg['ana_klasor']!r}")
    source = patch_assignment(source, r"^video_kaynak_ana_yol\s*=.*$", f"video_kaynak_ana_yol = {cfg['video_kaynak_ana_yol']!r}")
    source = patch_assignment(source, r"^klon_video_kaynak_ana_yol\s*=.*$", f"klon_video_kaynak_ana_yol = {cfg['klon_video_kaynak_ana_yol']!r}")
    source = patch_assignment(source, r"^toplu_montaj_klasor\s*=.*$", f"toplu_montaj_klasor = {cfg['toplu_montaj_klasor']!r}")
    source = patch_assignment(source, r"^materyal_ana_yol\s*=.*$", f"materyal_ana_yol = {cfg['materyal_ana_yol']!r}")

    materyal_ana_yol = cfg["materyal_ana_yol"]
    write_text_file(os.path.join(materyal_ana_yol, "muzik", "ses_seviyesi.txt"), cfg.get("muzik_seviyesi", "15"))
    write_text_file(os.path.join(materyal_ana_yol, "ses efekti", "ses_seviyesi.txt"), cfg.get("ses_efekti_seviyesi", "15"))
    write_text_file(os.path.join(materyal_ana_yol, "başlık.txt"), cfg.get("baslik", ""))
    write_text_file(os.path.join(materyal_ana_yol, "orijinal_ses_seviyesi.txt"), cfg.get("orijinal_ses_seviyesi", "100"))
    write_text_file(os.path.join(materyal_ana_yol, "video_ses_seviyesi.txt"), cfg.get("video_ses_seviyesi", "100"))
    with open(os.path.join(materyal_ana_yol, "orijinal_ses_kaynaklari.json"), "w", encoding="utf-8") as f:
        json.dump(cfg.get("orijinal_ses_kaynaklari") or [], f, ensure_ascii=False, indent=2)

    if "def ses_efekti_seviyesi_oku():" not in source:
        marker = "def muzik_ekle(video_clip):"
        helper = (
            "def ses_efekti_seviyesi_oku():\n"
            "    \"ses efekti/ses_seviyesi.txt dosyasından ses seviyesini oku\"\n"
            "    ses_dosyasi = os.path.join(ses_efekti_klasor, 'ses_seviyesi.txt')\n"
            "    try:\n"
            "        if os.path.exists(ses_dosyasi):\n"
            "            with open(ses_dosyasi, 'r', encoding='utf-8') as f:\n"
            "                icerik = f.read().strip()\n"
            "                icerik = icerik.replace('%', '').strip()\n"
            "                seviye = int(icerik)\n"
            "                seviye = max(0, min(100, seviye))\n"
            "                return seviye / 100.0\n"
            "    except Exception:\n"
            "        pass\n"
            "    return 0.15\n\n"
        )
        if marker in source:
            source = source.replace(marker, helper + marker, 1)

    source = source.replace("    ses_seviyesi = ses_seviyesi_oku()\n", "    ses_seviyesi = ses_efekti_seviyesi_oku()\n", 1)

    selected_source_indices = []
    for value in (cfg.get("selected_source_indices") or []):
        try:
            idx = int(value)
        except Exception:
            continue
        if idx not in selected_source_indices:
            selected_source_indices.append(idx)

    if selected_source_indices:
        marker = "mp4_dosyalar = list(dict.fromkeys(mp4_dosyalar))"
        injection = (
            "mp4_dosyalar = list(dict.fromkeys(mp4_dosyalar))\n"
            + "    selected_source_indices = " + repr(selected_source_indices) + "\n"
            + "    if selected_source_indices:\n"
            + "        filtered_videos = []\n"
            + "        for _idx, _path in enumerate(mp4_dosyalar):\n"
            + "            if _idx in selected_source_indices:\n"
            + "                filtered_videos.append(_path)\n"
            + "        mp4_dosyalar = filtered_videos\n"
            + "        print('\\n[INFO] App seçimine göre kaynak videolar filtrelendi.')\n"
            + "        print('[INFO] Seçilen indeksler: ' + ','.join(str(x) for x in selected_source_indices))\n"
        )
        if marker in source:
            source = source.replace(marker, injection, 1)

    answers = iter([
        cfg.get("format_choice", "D"),
        cfg.get("selection_text", "T"),
        "",
    ])

    original_input = builtins.input

    def fake_input(prompt=""):
        if prompt:
            print(prompt, end="")
        try:
            answer = next(answers)
        except StopIteration:
            answer = ""
        print(answer)
        return answer

    builtins.input = fake_input
    glb = {"__name__": "__main__", "__file__": script_path}

    try:
        exec(compile(source, script_path, "exec"), glb, glb)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
        raise SystemExit(code)
    finally:
        builtins.input = original_input


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] Toplu Video wrapper hatası: {exc}")
        traceback.print_exc()
        raise
