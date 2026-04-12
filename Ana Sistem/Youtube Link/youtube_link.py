import argparse
import json
import os
import re
import sys
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    webdriver = None
    ChromeOptions = None
    By = None
    WebDriverWait = None

MAX_PER_CHANNEL = 50
WAIT_LONG = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)

POPULAR_LABELS = ["Popüler", "Popular"]
RECENT_LABELS = [
    "Son yüklenenler",
    "Latest",
    "Newest",
    "Most recent",
    "Recently uploaded",
]


def log(msg: str):
    print(msg, flush=True)


def normalize_channel_base(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("Boş URL gönderildi.")

    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url

    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().replace("m.", "").replace("www.", "")
    if host != "youtube.com":
        raise ValueError("Geçerli bir YouTube kanal / sayfa linki girin.")

    path = parsed.path.rstrip("/")
    if not path:
        raise ValueError("YouTube kanal / sayfa linki gerekli.")

    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        raise ValueError("YouTube kanal / sayfa linki gerekli.")

    first = segments[0]
    if first.startswith("@"):
        base_path = "/" + first
    elif first in {"channel", "user", "c"} and len(segments) >= 2:
        base_path = "/" + first + "/" + segments[1]
    else:
        raise ValueError("Kanal / sayfa linki biçimi desteklenmiyor.")

    return urlunparse(("https", "www.youtube.com", base_path, "", "", ""))


def build_section_url(source_url: str, video_type: str) -> str:
    base = normalize_channel_base(source_url)
    section = "shorts" if video_type == "shorts" else "videos"
    return f"{base}/{section}"


def clamp_count(value: int) -> int:
    return max(1, min(MAX_PER_CHANNEL, int(value)))


def dedupe(urls: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for url in urls:
        clean = (url or "").strip()
        if clean and clean not in seen:
            out.append(clean)
            seen.add(clean)
    return out


def normalize_video_url(url: str, video_type: str) -> Optional[str]:
    if not url:
        return None
    url = url.strip()
    if not url.startswith("http"):
        if url.startswith("/"):
            url = "https://www.youtube.com" + url
        else:
            return None

    if "youtu.be/" in url:
        m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)
        if not m:
            return None
        vid = m.group(1)
        return f"https://www.youtube.com/shorts/{vid}" if video_type == "shorts" else f"https://www.youtube.com/watch?v={vid}"

    if video_type == "shorts":
        m = re.search(r"(?:/shorts/|[?&]v=)([A-Za-z0-9_-]{11})", url)
        if not m:
            return None
        return f"https://www.youtube.com/shorts/{m.group(1)}"

    m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    m = re.search(r"/shorts/([A-Za-z0-9_-]{11})", url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return None


def _make_driver() -> "webdriver.Chrome":
    if webdriver is None:
        raise RuntimeError("selenium modülü yüklü değil. Kurulum için: pip install selenium")

    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1700,2400")
    options.add_argument("--lang=tr-TR")
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    return driver


def _wait_for_page_ready(driver) -> None:
    WebDriverWait(driver, WAIT_LONG).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def _wait_for_any_tiles(driver) -> None:
    script = """
    const items = Array.from(document.querySelectorAll(
      'ytd-rich-item-renderer, ytd-grid-video-renderer, ytd-rich-grid-media, ytd-video-renderer, ytd-reel-item-renderer'
    ));
    return items.length;
    """
    WebDriverWait(driver, WAIT_LONG).until(lambda d: int(d.execute_script(script) or 0) > 0)


def _find_chip(driver, labels: List[str]):
    script = """
    const wanted = arguments[0].map(x => String(x).trim().toLowerCase());
    const nodes = Array.from(document.querySelectorAll(
      'yt-chip-cloud-chip-renderer, button, [role="tab"], tp-yt-paper-tab, yt-formatted-string'
    ));
    function norm(t) {
      return String(t || '').replace(/\\s+/g, ' ').trim().toLowerCase();
    }
    for (const node of nodes) {
      const txt = norm(node.innerText || node.textContent || '');
      if (!txt) continue;
      if (!wanted.includes(txt)) continue;
      return node;
    }
    return null;
    """
    return driver.execute_script(script, labels)


def _click_chip(driver, labels: List[str]) -> bool:
    el = _find_chip(driver, labels)
    if not el:
        return False

    driver.execute_script(
        """
        const el = arguments[0];
        const host = el.closest('yt-chip-cloud-chip-renderer, button, [role="tab"], tp-yt-paper-tab') || el;
        host.scrollIntoView({block: 'center'});
        """,
        el,
    )
    time.sleep(0.6)

    try:
        el.click()
    except Exception:
        driver.execute_script(
            """
            const el = arguments[0];
            const host = el.closest('yt-chip-cloud-chip-renderer, button, [role="tab"], tp-yt-paper-tab') || el;
            host.click();
            host.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
            """,
            el,
        )
    time.sleep(2.0)
    return True


def _first_grid_href(driver, video_type: str) -> str:
    script = """
    const wantShorts = arguments[0] === 'shorts';
    const items = Array.from(document.querySelectorAll(
      'ytd-rich-item-renderer, ytd-grid-video-renderer, ytd-rich-grid-media, ytd-video-renderer, ytd-reel-item-renderer'
    ));
    const rows = [];
    for (const item of items) {
      const r = item.getBoundingClientRect();
      if (r.width < 40 || r.height < 40) continue;
      let a = null;
      if (wantShorts) {
        a = item.querySelector('a[href*="/shorts/"]') || item.querySelector('a[href*="/watch?v="]');
      } else {
        a = item.querySelector('a[href*="/watch?v="]') || item.querySelector('a[href*="/shorts/"]');
      }
      if (!a) continue;
      const href = a.href || a.getAttribute('href') || '';
      if (!href) continue;
      rows.push({href, top: r.top + window.scrollY, left: r.left + window.scrollX});
    }
    rows.sort((a,b) => a.top === b.top ? a.left - b.left : a.top - b.top);
    return rows.length ? rows[0].href : '';
    """
    return driver.execute_script(script, video_type) or ""


def _collect_grid_urls(driver, desired_count: int, video_type: str) -> List[str]:
    urls: List[str] = []
    seen = set()
    stagnation = 0
    last_total = 0

    while len(urls) < desired_count and stagnation < 4:
        rows = driver.execute_script(
            """
            const wantShorts = arguments[0] === 'shorts';
            const items = Array.from(document.querySelectorAll(
              'ytd-rich-item-renderer, ytd-grid-video-renderer, ytd-rich-grid-media, ytd-video-renderer, ytd-reel-item-renderer'
            ));
            const out = [];
            for (const item of items) {
              const r = item.getBoundingClientRect();
              const style = window.getComputedStyle(item);
              if (r.width < 40 || r.height < 40) continue;
              if (style.display === 'none' || style.visibility === 'hidden') continue;
              let a = null;
              if (wantShorts) {
                a = item.querySelector('a[href*="/shorts/"]') || item.querySelector('a[href*="/watch?v="]');
              } else {
                a = item.querySelector('a[href*="/watch?v="]') || item.querySelector('a[href*="/shorts/"]');
              }
              if (!a) continue;
              const href = a.href || a.getAttribute('href') || '';
              if (!href) continue;
              out.push({href, top: r.top + window.scrollY, left: r.left + window.scrollX});
            }
            out.sort((a,b) => a.top === b.top ? a.left - b.left : a.top - b.top);
            return out.map(x => x.href);
            """,
            video_type,
        ) or []

        for href in rows:
            norm = normalize_video_url(href, video_type)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            urls.append(norm)
            if len(urls) >= desired_count:
                return urls

        current_total = len(rows)
        if current_total <= last_total:
            stagnation += 1
        else:
            stagnation = 0
            last_total = current_total

        driver.execute_script("window.scrollBy(0, 1200);")
        time.sleep(1.4)

    return urls


def fetch_urls_via_ui_order(section_url: str, desired_count: int, video_type: str, mode: str) -> List[str]:
    driver = None
    try:
        log(f"[INFO] Selenium ile sayfa açılıyor: {section_url}")
        driver = _make_driver()
        driver.get(section_url)
        _wait_for_page_ready(driver)
        _wait_for_any_tiles(driver)

        labels = POPULAR_LABELS if mode == "popular" else RECENT_LABELS
        before_first = _first_grid_href(driver, video_type)

        clicked = _click_chip(driver, labels)
        if mode == "popular" and not clicked:
            raise RuntimeError("Popüler filtresi bulunamadı veya tıklanamadı.")

        if clicked:
            try:
                WebDriverWait(driver, 8).until(
                    lambda d: _first_grid_href(d, video_type) != before_first or len(_collect_grid_urls(d, 1, video_type)) > 0
                )
            except Exception:
                pass
            time.sleep(1.0)

        _wait_for_any_tiles(driver)
        urls = _collect_grid_urls(driver, desired_count, video_type)
        if not urls:
            raise RuntimeError("Ekrandaki kart sırası okunamadı.")

        log(f"[OK] Arayüz sırası okundu. Bulunan link sayısı: {len(urls)}")
        return urls[:desired_count]
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def fetch_recent_urls_ytdlp(section_url: str, desired_count: int, video_type: str) -> List[str]:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp modülü yüklü değil. Kurulum için: pip install yt-dlp")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": max(desired_count * 6, 20),
        "lazy_playlist": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(section_url, download=False)

    if not info:
        return []

    entries = info.get("entries") or []
    out: List[str] = []
    for entry in entries:
        if not entry:
            continue
        raw = entry.get("webpage_url") or entry.get("url") or entry.get("id") or ""
        norm = normalize_video_url(raw, video_type)
        if norm:
            out.append(norm)
        if len(out) >= desired_count:
            break
    return dedupe(out)[:desired_count]


def save_urls(urls: List[str], output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in urls:
            f.write(item.strip() + "\n")


def load_jobs(args) -> Dict:
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            data = json.load(f)
        jobs = []
        for item in (data.get("entries") or []):
            url = str(item.get("url", "")).strip()
            if url:
                jobs.append({"url": url, "count": clamp_count(item.get("count", 1))})
        return {
            "output": data.get("output") or args.output,
            "mode": (data.get("mode") or args.mode or "recent").strip().lower(),
            "video_type": (data.get("video_type") or args.video_type or "video").strip().lower(),
            "jobs": jobs,
        }

    if not args.url or not args.output or not args.mode:
        raise ValueError("Tekli kullanım için --url, --mode, --count ve --output zorunludur.")

    return {
        "output": args.output,
        "mode": args.mode.strip().lower(),
        "video_type": (args.video_type or "video").strip().lower(),
        "jobs": [{"url": args.url.strip(), "count": clamp_count(args.count)}],
    }


def validate_mode(value: str) -> str:
    if value not in {"popular", "recent"}:
        raise ValueError("mode yalnızca 'popular' veya 'recent' olabilir.")
    return value


def validate_video_type(value: str) -> str:
    if value not in {"video", "shorts"}:
        raise ValueError("video_type yalnızca 'video' veya 'shorts' olabilir.")
    return value


def fetch_urls_for_channel(source_url: str, count: int, mode: str, video_type: str) -> List[str]:
    section_url = build_section_url(source_url, video_type)
    log(f"[INFO] Kullanılan bölüm URL'si: {section_url}")

    if mode == "popular":
        # Popüler için yalnızca gerçek arayüz sırasını kullan.
        return fetch_urls_via_ui_order(section_url, count, video_type, mode)

    # Recent için önce gerçek arayüz sırası, olmazsa yt-dlp yedeği.
    try:
        return fetch_urls_via_ui_order(section_url, count, video_type, mode)
    except Exception as exc:
        log(f"[WARN] Arayüz sırası alınamadı, recent için yt-dlp deneniyor: {exc}")
        return fetch_recent_urls_ytdlp(section_url, count, video_type)


def main():
    parser = argparse.ArgumentParser(description="YouTube kanal sayfalarından video linkleri çıkarır.")
    parser.add_argument("--config", help="JSON yapılandırma dosyası yolu")
    parser.add_argument("--url", help="YouTube kanal / sayfa linki")
    parser.add_argument("--mode", choices=["popular", "recent"], help="Seçim modu")
    parser.add_argument("--count", type=int, default=1, help="Kaç video alınacağı")
    parser.add_argument("--output", help="Kaydedilecek txt yolu")
    parser.add_argument("--video-type", choices=["video", "shorts"], default="video", help="İçerik türü")
    args = parser.parse_args()

    payload = load_jobs(args)
    output_path = payload["output"]
    mode = validate_mode(payload["mode"])
    video_type = validate_video_type(payload["video_type"])
    jobs = payload["jobs"]

    if not output_path:
        raise ValueError("Çıktı dosyası yolu bulunamadı.")
    if not jobs:
        raise ValueError("İşlenecek en az bir kanal / sayfa linki gerekli.")

    log("============================================================")
    log("[INFO] YouTube link çıkarma işlemi başlatıldı")
    log(f"[INFO] Video türü: {'Shorts Video' if video_type == 'shorts' else 'Video'}")
    log(f"[INFO] Seçim modu: {'en popüler' if mode == 'popular' else 'en son'}")
    log(f"[INFO] Kanal sayısı: {len(jobs)}")
    log(f"[INFO] Çıktı dosyası: {output_path}")

    all_urls: List[str] = []
    global_seen = set()
    success_count = 0
    failed_count = 0

    for idx, job in enumerate(jobs, start=1):
        source_url = job["url"]
        count = clamp_count(job["count"])
        log("")
        log(f"[INFO] Kanal {idx} işleniyor: {source_url}")
        log(f"[INFO] Kanal {idx} için istenen video sayısı: {count}")
        try:
            found_urls = fetch_urls_for_channel(source_url, count, mode, video_type)
        except Exception as exc:
            failed_count += 1
            log(f"[ERROR] Kanal {idx} için video listesi alınamadı: {exc}")
            continue

        kept = []
        for url in found_urls[:count]:
            if url not in global_seen:
                global_seen.add(url)
                all_urls.append(url)
                kept.append(url)

        success_count += 1
        log(f"[OK] Kanal {idx} için bulunan video sayısı: {len(found_urls[:count])}")
        for vid_idx, item in enumerate(found_urls[:count], start=1):
            log(f"[OK] Kanal {idx} - Video {vid_idx}: {item}")
        if len(kept) < len(found_urls[:count]):
            log(f"[WARN] Kanal {idx}: bazı linkler tekrar ettiği için tekilleştirildi.")

    log("")
    log(f"Başarılı: {success_count}")
    log(f"Başarısız: {failed_count}")

    if not all_urls:
        log("[ERROR] Hiçbir link kaydedilemedi.")
        sys.exit(1)

    save_urls(all_urls, output_path)
    log(f"[OK] Toplam kaydedilen link sayısı: {len(all_urls)}")
    log("[OK] Linkler başarıyla txt dosyasına kaydedildi.")
    log("[OK] TÜM İŞLEMLER TAMAMLANDI")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("[WARN] İşlem kullanıcı tarafından durduruldu.")
        sys.exit(1)
    except Exception as e:
        log(f"[ERROR] Beklenmeyen hata: {e}")
        sys.exit(1)
