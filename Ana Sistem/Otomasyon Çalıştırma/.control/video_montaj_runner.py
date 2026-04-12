import builtins
import json
import os
import re
import sys
import traceback

def patch_assignment(text, pattern, replacement):
    new_text, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.MULTILINE)
    if count == 0:
        print(f'[WARN] Değiştirilemedi: {pattern}')
    return new_text

def main():
    if len(sys.argv) < 2:
        raise RuntimeError('Video montaj yapılandırma dosyası verilmedi.')

    config_path = sys.argv[1]
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    script_path = cfg['script_path']
    with open(script_path, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()

    source = patch_assignment(source, r'^ana_klasor\s*=.*$', f"ana_klasor = {cfg['ana_klasor']!r}")
    source = patch_assignment(source, r'^video_klasor\s*=.*$', f"video_klasor = {cfg['video_klasor']!r}")
    source = patch_assignment(source, r'^klon_video_klasor\s*=.*$', f"klon_video_klasor = {cfg['klon_video_klasor']!r}")
    source = patch_assignment(source, r'^montaj_klasor\s*=.*$', f"montaj_klasor = {cfg['montaj_klasor']!r}")
    source = patch_assignment(source, r'^gorsel_klasor\s*=.*$', f"gorsel_klasor = {cfg['gorsel_klasor']!r}")

    # Orijinal ses ve video ses seviyesi dosyalarını yaz
    ek_klasor = os.path.join(os.path.dirname(cfg['script_path']), 'ek')
    os.makedirs(ek_klasor, exist_ok=True)
    orijinal_ses_sev = cfg.get('orijinal_ses_seviyesi', '100')
    video_ses_sev = cfg.get('video_ses_seviyesi', '100')
    with open(os.path.join(ek_klasor, 'orijinal_ses_seviyesi.txt'), 'w', encoding='utf-8') as _f: _f.write(str(orijinal_ses_sev))
    with open(os.path.join(ek_klasor, 'video_ses_seviyesi.txt'), 'w', encoding='utf-8') as _f: _f.write(str(video_ses_sev))
    with open(os.path.join(ek_klasor, 'orijinal_ses_kaynaklari.json'), 'w', encoding='utf-8') as _f: json.dump(cfg.get('orijinal_ses_kaynaklari') or [], _f, ensure_ascii=False, indent=2)

    answers = iter([
        cfg.get('format_choice', 'D'),
        cfg.get('selection_text', 'T'),
        ''
    ])

    original_input = builtins.input

    def fake_input(prompt=''):
        if prompt:
            print(prompt, end='')
        try:
            answer = next(answers)
        except StopIteration:
            answer = ''
        print(answer)
        return answer

    builtins.input = fake_input
    glb = {'__name__': '__main__', '__file__': script_path}

    try:
        exec(compile(source, script_path, 'exec'), glb, glb)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
        raise SystemExit(code)
    finally:
        builtins.input = original_input

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[ERROR] Video Montaj wrapper hatası: {exc}')
        traceback.print_exc()
        raise
