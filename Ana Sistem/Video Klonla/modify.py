import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from typing import Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
ANA_SISTEM_DIR = SCRIPT_DIR.parent
OTOMASYON_DIR = ANA_SISTEM_DIR.parent
CONTROL_DIR = ANA_SISTEM_DIR / 'Otomasyon Çalıştırma' / '.control'
CONTROL_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = CONTROL_DIR / 'settings.local.json'
RUNTIME_FILE = CONTROL_DIR / 'video_klonla_runtime.json'
PAUSE_FLAG = CONTROL_DIR / 'PAUSE.flag'
STOP_FLAG = CONTROL_DIR / 'STOP.flag'

DEFAULT_MODEL = 'v5.5'
DEFAULT_QUALITY = '720p'
POLL_INTERVAL_SECONDS = 15

class UserFacingError(Exception):
    def __init__(self, status: str, reason: str, detail: str = '', result: str = 'Video Başarısız'):
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.detail = detail
        self.result = result


def strip_ansi(text: str) -> str:
    cleaned = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text or "")
    return "\n".join((line.split("\r")[-1] if "\r" in line else line) for line in cleaned.split("\n"))


def normalize_error_detail(detail: Any) -> str:
    if detail is None:
        return ""
    if isinstance(detail, (dict, list)):
        try:
            return json.dumps(detail, ensure_ascii=False)
        except Exception:
            return str(detail)
    return str(detail)


def is_credit_error_text(detail: Any) -> bool:
    text = strip_ansi(normalize_error_detail(detail))
    if not text:
        return False
    return bool(re.search(
        r'all\s*credits?.*used\s*up|credits?.*have\s*been\s*used|purchase\s*credits|'
        r'upgrade\s+your\s+membership|50043\b|insufficient.*credit|credit.*balance|'
        r'kredi.*yetersiz|payment.*required|402\b',
        text,
        re.IGNORECASE,
    ))


def get_user_facing_reason(detail: Any, fallback: str = 'İşlem tamamlanamadı') -> str:
    return 'Kredi yetersiz' if is_credit_error_text(detail) else fallback


def resolve_binary(name: str) -> str:
    candidates = [name, f'{name}.cmd', f'{name}.exe', f'{name}.bat'] if os.name == 'nt' else [name]
    for c in candidates:
        found = shutil.which(c)
        if found:
            return found
    raise FileNotFoundError(f"'{name}' bulunamadı")


def run_command(cmd, cwd=None, check=False, capture_output=True):
    cmd = [resolve_binary(cmd[0])] + [str(x) for x in cmd[1:]]
    res = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=capture_output, text=True, encoding='utf-8', errors='replace')
    if check and res.returncode != 0:
        raise RuntimeError(f"Komut başarısız: {' '.join(cmd)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res


def start_process(cmd, cwd=None):
    cmd = [resolve_binary(cmd[0])] + [str(x) for x in cmd[1:]]
    return subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace')


def parse_json_from_output(output: str) -> dict:
    clean = strip_ansi(output).strip()
    if not clean:
        raise ValueError('Boş çıktı')
    try:
        return json.loads(clean)
    except Exception:
        pass
    m = re.search(r'(\{.*\})', clean, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))
    raise ValueError(clean[:300])


def read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default


def get_settings() -> dict:
    return read_json(SETTINGS_FILE, {}) if SETTINGS_FILE.exists() else {}


def wait_pause():
    logged = False
    while PAUSE_FLAG.exists():
        if STOP_FLAG.exists():
            raise SystemExit(0)
        if not logged:
            print('[PAUSE] Duraklatıldı.')
            logged = True
        time.sleep(0.3)
    if logged:
        print('[PAUSE] Devam ediliyor...')


def stop_check():
    if STOP_FLAG.exists():
        print('[STOP] Bitirme isteği alındı.')
        raise SystemExit(0)


def ensure_logged_in():
    status = run_command(['pixverse', 'auth', 'status'])
    info = run_command(['pixverse', 'account', 'info'])
    if status.returncode == 0 and info.returncode == 0:
        print('Giriş yapıldı')
        return
    print('PixVerse girişi gerekiyor. Tarayıcı açılabilir...')
    login = run_command(['pixverse', 'auth', 'login'], capture_output=False)
    if login.returncode != 0:
        raise RuntimeError('PixVerse giriş işlemi başarısız oldu.')
    print('Giriş yapıldı')


def next_output_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    mx = 0
    for item in root.iterdir():
        if item.is_dir() and item.name.startswith('Video '):
            try:
                mx = max(mx, int(item.name.split('Video ', 1)[1]))
            except Exception:
                pass
    return root / f'Video {mx+1 if mx else 1}'


def download_asset(video_id: Any, out_dir: Path) -> Optional[dict]:
    res = run_command(['pixverse', 'asset', 'download', str(video_id), '--json'], cwd=out_dir)
    if res.returncode != 0:
        raise UserFacingError('Video indirme', 'Video indirilemedi', strip_ansi(res.stderr or res.stdout)[:180])
    try:
        return parse_json_from_output(res.stdout)
    except Exception:
        return None


def wait_for_completion(video_id: Any, out_dir: Path) -> dict:
    proc = start_process(['pixverse', 'task', 'wait', str(video_id), '--json'], cwd=out_dir)
    start = time.monotonic()
    next_log = POLL_INTERVAL_SECONDS
    print(f'Durum: video üretimi başlatıldı | görev ID: {video_id}')
    print('Durum: video oluşturuluyor | sonuç bekleniyor')
    while True:
        wait_pause(); stop_check()
        rc = proc.poll()
        elapsed = int(time.monotonic() - start)
        if rc is not None:
            stdout, stderr = proc.communicate()
            if rc != 0:
                raise UserFacingError('Video oluşturma bekleme', 'İşlem tamamlanamadı', strip_ansi(stderr or stdout)[:200])
            data = parse_json_from_output(stdout)
            print(f'Durum: video oluşturma tamamlandı | {elapsed} sn sürdü')
            return data
        if elapsed >= next_log:
            print(f'Durum: oluşturuluyor | {elapsed} sn geçti')
            next_log += POLL_INTERVAL_SECONDS
        time.sleep(1)


def build_modify_cmd(video: str, prompt: str, model: str, quality: str, keyframe_time: int, no_wait: bool) -> list:
    cmd = ['pixverse', 'create', 'modify', '--video', video, '--prompt', prompt, '--model', model, '--quality', quality, '--keyframe-time', str(keyframe_time), '--json']
    if no_wait:
        cmd.append('--no-wait')
    return cmd


def submit_modify_request(video: str, prompt: str, model: str, quality: str, keyframe_time: int, out_dir: Path) -> dict:
    cmd = build_modify_cmd(video, prompt, model, quality, keyframe_time, no_wait=True)
    print('Komut gonderiliyor: modify')
    print("Durum: istek PixVerse'e iletildi | gorev kabul ediliyor")
    proc = start_process(cmd, cwd=out_dir)
    start = time.monotonic()
    next_log = POLL_INTERVAL_SECONDS
    while True:
        wait_pause(); stop_check()
        rc = proc.poll()
        elapsed = int(time.monotonic() - start)
        if rc is not None:
            stdout, stderr = proc.communicate()
            if rc != 0:
                detail = strip_ansi(stderr or stdout)[:260]
                raise UserFacingError('Prompt gonderme', get_user_facing_reason(detail), detail)
            data = parse_json_from_output(stdout)
            if data.get('error'):
                detail = normalize_error_detail(data.get('error'))[:260]
                raise UserFacingError('Prompt gonderme', get_user_facing_reason(detail), detail)
            print(f'Durum: gorev olusturma yaniti alindi | {elapsed} sn surdu')
            return data
        if elapsed >= next_log:
            print(f'Durum: gorev kabul ediliyor | {elapsed} sn gecti')
            next_log += POLL_INTERVAL_SECONDS
        time.sleep(1)


def normalize_input_item(raw: dict) -> dict:
    return {
        'name': str(raw.get('name') or raw.get('folder_name') or '').strip(),
        'video': str(raw.get('video') or raw.get('video_path') or '').strip(),
        'prompt': str(raw.get('prompt') or '').strip(),
        'model': str(raw.get('model') or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        'quality': str(raw.get('quality') or DEFAULT_QUALITY).strip() or DEFAULT_QUALITY,
        'keyframe_time': int(raw.get('keyframe_time') or 0),
    }


def collect_runtime_items(runtime: dict) -> list[dict]:
    items = []
    for raw in runtime.get('items', []) or []:
        item = normalize_input_item(raw)
        if item['video'] and item['prompt']:
            items.append(item)
    if items:
        return items
    # Tekli fallback
    single = normalize_input_item(runtime)
    return [single] if single['video'] and single['prompt'] else []


def _legacy_process_item(item: dict, out_root: Path, auto_download: bool) -> bool:
    out_dir = next_output_dir(out_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nİŞLEM: {item.get('name') or os.path.basename(item['video'])}")
    print(f"✓ Video bulundu: {item['video']}")
    print(f"✓ Prompt okundu: {len(item['prompt'])} karakter")
    cmd = build_modify_cmd(item['video'], item['prompt'], item['model'], item['quality'], item['keyframe_time'], no_wait=True)
    print('Komut gönderiliyor: modify')
    res = run_command(cmd, cwd=out_dir)
    if res.returncode != 0:
        detail = strip_ansi(res.stderr or res.stdout)[:200]
        raise UserFacingError('Prompt gönderme', get_user_facing_reason(detail), detail)
    data = parse_json_from_output(res.stdout)
    if data.get('error'):
        detail = normalize_error_detail(data.get('error'))[:220]
        raise UserFacingError('Prompt gönderme', get_user_facing_reason(detail), detail)
    video_id = data.get('video_id') or data.get('task_id')
    if auto_download and video_id:
        print(f'Durum: görev alındı | ID: {video_id}')
        final = wait_for_completion(video_id, out_dir)
        if final.get('error'):
            detail = normalize_error_detail(final.get('error'))[:220]
            raise UserFacingError('Video oluşturma', get_user_facing_reason(detail), detail)
        download_asset(video_id, out_dir)
        meta = final
    else:
        meta = data
    with open(out_dir / 'video_result.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print('✓ Modify tamamlandı')
    return True


def process_item(item: dict, out_root: Path, auto_download: bool) -> bool:
    out_dir = next_output_dir(out_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nISLEM: {item.get('name') or os.path.basename(item['video'])}")
    print(f"Video bulundu: {item['video']}")
    print(f"Prompt okundu: {len(item['prompt'])} karakter")
    data = submit_modify_request(
        item['video'],
        item['prompt'],
        item['model'],
        item['quality'],
        item['keyframe_time'],
        out_dir,
    )
    video_id = data.get('video_id') or data.get('task_id')
    if auto_download and video_id:
        print(f'Durum: gorev alindi | ID: {video_id}')
        final = wait_for_completion(video_id, out_dir)
        if final.get('error'):
            detail = normalize_error_detail(final.get('error'))[:220]
            raise UserFacingError('Video olusturma', get_user_facing_reason(detail), detail)
        print('Durum: video hazir | cikti indiriliyor')
        download_asset(video_id, out_dir)
        print('Durum: cikti indirildi')
        meta = final
    else:
        if auto_download and not video_id:
            print('Durum: gorev kimligi alinamadi | canli takip atlandi')
        meta = data
    with open(out_dir / 'video_result.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print('Modify tamamlandi')
    return True


def main():
    parser = argparse.ArgumentParser(description='PixVerse Modify runner')
    parser.add_argument('--config', default=str(RUNTIME_FILE))
    parser.add_argument('--video')
    parser.add_argument('--prompt')
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--quality', default=DEFAULT_QUALITY)
    parser.add_argument('--keyframe-time', type=int, default=0)
    parser.add_argument('--output-root')
    parser.add_argument('--no-download', action='store_true')
    args = parser.parse_args()

    settings = get_settings()
    runtime = read_json(Path(args.config), {})
    if args.video:
        runtime['video'] = args.video
    if args.prompt:
        runtime['prompt'] = args.prompt
    if args.model:
        runtime['model'] = args.model
    if args.quality:
        runtime['quality'] = args.quality
    runtime['keyframe_time'] = args.keyframe_time if args.keyframe_time is not None else runtime.get('keyframe_time', 0)

    items = collect_runtime_items(runtime)
    if not items:
        print('HATA: İşlenecek video/prompt bulunamadı.')
        raise SystemExit(1)

    output_root = Path(args.output_root or runtime.get('output_root') or settings.get('klon_video_dir') or settings.get('video_klonla_dir') or settings.get('video_output_dir') or (OTOMASYON_DIR / 'Video' / 'Video'))
    ensure_logged_in()

    ok_count = 0
    fail_count = 0
    for item in items:
        try:
            wait_pause(); stop_check()
            process_item(item, output_root, auto_download=not args.no_download)
            ok_count += 1
        except UserFacingError as e:
            fail_count += 1
            print(f'\nHATA DURUMU: {e.status}')
            print(f'SEBEP      : {e.reason}')
            if e.detail:
                print(f'DETAY      : {e.detail}')
            print(f'SONUÇ      : {e.result}')
        except SystemExit:
            raise
        except Exception as e:
            fail_count += 1
            print(f'\nHATA DURUMU: Beklenmeyen hata')
            print(f'SEBEP      : İşlem tamamlanamadı')
            print(f'DETAY      : {str(e)[:220]}')
            print('SONUÇ      : Video Başarısız')

    print('\nTÜM İŞLEMLER TAMAMLANDI!')
    print(f'Başarılı: {ok_count}')
    print(f'Başarısız: {fail_count}')
    raise SystemExit(0 if ok_count > 0 and fail_count == 0 else (2 if ok_count > 0 else 1))

if __name__ == '__main__':
    main()
