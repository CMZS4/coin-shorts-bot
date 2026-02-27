import json, re, subprocess, datetime, argparse, time
from pathlib import Path
import requests

OUT = Path("out"); OUT.mkdir(exist_ok=True)
ASSETS = Path("assets"); ASSETS.mkdir(exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
CACHE = Path("coin_cache.json")

def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def first_sentences(text: str, n=2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [p.strip() for p in parts if p.strip()]
    return " ".join(parts[:n]).strip()

def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def save_cache(c: dict):
    CACHE.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")

def coingecko_resolve_id(name: str) -> str:
    url = "https://api.coingecko.com/api/v3/search"
    r = requests.get(url, params={"query": name}, timeout=30, headers={"User-Agent":"coin-shorts-bot/1.0"})
    r.raise_for_status()
    coins = r.json().get("coins", [])
    if not coins:
        return ""
    return coins[0].get("id", "")

def coingecko_fetch(coin_id: str) -> dict:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "false",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    }
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent":"coin-shorts-bot/1.0"})
    r.raise_for_status()
    data = r.json()

    desc = data.get("description", {}) or {}
    en = strip_html(desc.get("en", ""))  # EN ONLY
    categories = data.get("categories", []) or []
    img = (data.get("image", {}) or {}).get("large", "")  # logo url
    return {"en": en, "categories": categories, "image": img}

def download_logo(url: str, out_path: Path):
    if not url:
        return False
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent":"coin-shorts-bot/1.0"})
        r.raise_for_status()
        out_path.write_bytes(r.content)
        return out_path.exists() and out_path.stat().st_size > 500
    except:
        return False

def build_script_en(coin: dict, info: dict) -> str:
    rank = coin.get("rank", "")
    name = coin.get("name", "")
    symbol = coin.get("symbol", "")

    base = first_sentences(info.get("en", ""), 2)
    if base:
        words = base.split()
        if len(words) > 42:
            base = " ".join(words[:42]).strip() + "."

    cats = info.get("categories", [])
    cat = cats[0] if cats else ""

    s1 = f"Top 100 #{rank}: {name} ({symbol}) is a cryptocurrency project in the ecosystem."
    s2 = base if base else (f"It is commonly associated with {cat.lower()} use cases." if cat else "It is designed for specific use cases within blockchain networks.")
    s3 = "Risk note: crypto assets are highly volatile, and there can be technical, security, and regulatory risks."
    s4 = "This is not financial advice."
    text = " ".join([s1, s2, s3, s4])

    w = text.split()
    if len(w) > 95:
        text = " ".join(w[:95]).strip()
        if not text.endswith("."):
            text += "."
        if "not financial advice" not in text.lower():
            text += " This is not financial advice."
    return text

def srt_time(ms:int)->str:
    h=ms//3600000; ms%=3600000
    m=ms//60000; ms%=60000
    s=ms//1000; ms%=1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def make_srt(text:str, total_ms:int=34000)->str:
    # daha kısa satırlar
    words = text.split()
    chunks = []
    step = 5
    for i in range(0, len(words), step):
        chunks.append(" ".join(words[i:i+step]))
    seg = max(1200, total_ms // max(1, len(chunks)))
    cur=0; out=[]
    for i,ch in enumerate(chunks,1):
        start=cur; end=min(total_ms, cur+seg)
        out += [str(i), f"{srt_time(start)} --> {srt_time(end)}", ch, ""]
        cur=end
    return "\n".join(out)

def render_one(coin: dict, idx: int, cache: dict):
    rank = coin.get("rank", idx+1)
    name = coin["name"]; symbol = coin["symbol"]

    key = f"{rank}:{symbol}"
    if key not in cache:
        cid = coingecko_resolve_id(name)
        info = coingecko_fetch(cid) if cid else {"en":"","categories":[],"image":""}
        cache[key] = {"id": cid, "info": info}
        save_cache(cache)

    cid = cache[key]["id"]
    info = cache[key]["info"]

    # logo indir (her coin için)
    logo_path = ASSETS / f"{(cid or symbol).lower()}.png"
    has_logo = logo_path.exists() and logo_path.stat().st_size > 500
    if not has_logo:
        has_logo = download_logo(info.get("image",""), logo_path)

    text = build_script_en({"rank": rank, "name": name, "symbol": symbol}, info)

    title = f"#{rank} {symbol} — What is it?"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{idx:03d}_{symbol}_{stamp}"

    txt = OUT / f"{base}.txt"
    srt = OUT / f"{base}.srt"
    mp3 = OUT / f"{base}.mp3"
    mp4 = OUT / f"{base}.mp4"
    title_file = OUT / f"{base}_title.txt"

    txt.write_text(text, encoding="utf-8")
    srt.write_text(make_srt(text), encoding="utf-8")
    title_file.write_text(title, encoding="utf-8")

    # EN voice
    subprocess.check_call([
        "edge-tts",
        "--voice","en-US-JennyNeural",
        "--rate","+10%",
        "--file", str(txt),
        "--write-media", str(mp3)
    ])

    # Subtitles: küçük (12) + altta
    sub_style = "FontName=DejaVu Sans,FontSize=12,Outline=2,Shadow=1,Alignment=2,MarginV=18"

    if has_logo:
        cmd = [
            "ffmpeg","-y",
            "-f","lavfi","-i","color=c=#0b1020:s=1080x1920:r=30:d=60",
            "-loop","1","-i",str(logo_path),
            "-i",str(mp3),
            "-filter_complex",
            (
                # önce arkaya hafif büyük sembol yaz
                f"[0:v]drawtext=fontfile={FONT}:text='{symbol}':"
                "fontcolor=white@0.18:fontsize=220:borderw=0:x=(W-text_w)/2:y=700[bg0];"
                # logo overlay
                "[1:v]scale=720:-1:flags=lanczos,format=rgba,colorchannelmixer=aa=0.92[logo];"
                "[bg0][logo]overlay=x=(W-w)/2:y=560[bg];"
                # başlık + altyazı
                "[bg]"
                "drawbox=x=0:y=0:w=iw:h=260:color=black@0.35:t=fill,"
                f"drawtext=fontfile={FONT}:textfile='{title_file}':reload=1:"
                "fontcolor=white:fontsize=68:borderw=4:bordercolor=black:"
                "x=(w-text_w)/2:y=90,"
                f"subtitles='{srt}':force_style='{sub_style}'"
                "[v]"
            ),
            "-map","[v]","-map","2:a",
            "-c:v","libx264","-pix_fmt","yuv420p",
            "-c:a","aac",
            "-shortest",
            str(mp4)
        ]
    else:
        cmd = [
            "ffmpeg","-y",
            "-f","lavfi","-i","color=c=#0b1020:s=1080x1920:r=30:d=60",
            "-i",str(mp3),
            "-vf",
            (
                f"drawtext=fontfile={FONT}:text='{symbol}':fontcolor=white@0.18:fontsize=220:x=(w-text_w)/2:y=700,"
                "drawbox=x=0:y=0:w=iw:h=260:color=black@0.35:t=fill,"
                f"drawtext=fontfile={FONT}:textfile='{title_file}':reload=1:fontcolor=white:fontsize=68:borderw=4:bordercolor=black:x=(w-text_w)/2:y=90,"
                f"subtitles='{srt}':force_style='{sub_style}'"
            ),
            "-c:v","libx264","-pix_fmt","yuv420p",
            "-c:a","aac",
            "-shortest",
            str(mp4)
        ]

    subprocess.check_call(cmd)
    print("OK:", mp4, "| logo:", ("YES" if has_logo else "NO"))

def main(count: int):
    coins = json.loads(Path("coins.json").read_text(encoding="utf-8"))
    idx_file = Path("coin_index.txt")
    idx = int(idx_file.read_text().strip()) if idx_file.exists() else 0
    cache = load_cache()

    for _ in range(count):
        coin = coins[idx % len(coins)]
        render_one(coin, idx, cache)
        idx += 1
        idx_file.write_text(str(idx), encoding="utf-8")
        time.sleep(1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1)
    args = ap.parse_args()
    main(args.count)
