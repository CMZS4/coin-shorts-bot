# coin-shorts-bot

Generates 1080x1920 Shorts videos for coins listed in `coins.json`.

Features:
- English script from CoinGecko description
- English voiceover via Edge TTS
- Subtitles at bottom
- Coin logo overlay
- Output: mp4 files in `out/` (ignored by git)

## Setup (WSL Ubuntu)
sudo apt update
sudo apt install -y ffmpeg python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## Run
python make_coin_short.py --count 5
