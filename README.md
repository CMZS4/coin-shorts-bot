# Coin Shorts Bot 🎬🪙 (Top 25 / Top 100)

A small automation that generates **1080×1920 YouTube Shorts** for coins listed in `coins.json`.

- ✅ English script from **CoinGecko** descriptions  
- ✅ English voiceover via **Edge TTS**  
- ✅ Subtitles at the **bottom** (small font)  
- ✅ Coin **logo overlay**  
- ✅ Outputs `.mp4` into `out/` (ignored by git)

> **Disclaimer:** Educational content only. No price predictions. **Not financial advice.**

## Quick start (WSL Ubuntu)
```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python make_coin_short.py --count 5
explorer.exe out
Files

coins.json → coin list (Top 25 / Top 100)

make_coin_short.py → generator

out/ → generated mp4 (gitignored)

assets/ → cached logos (gitignored)
