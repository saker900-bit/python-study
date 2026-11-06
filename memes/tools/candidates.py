"""Tenor에서 밈 후보 GIF를 찾아 한눈에 보는 시트를 만든다.

  python tools/candidates.py '{"새밈id": "검색어", "다른id": "검색어"}'

결과: cand/candidates.json (후보 목록), cand/sheet_*.jpg (후보 첫 프레임 모음, 빨간 숫자 = 후보 번호)
시트를 눈으로 보고 맞는 번호를 고른 뒤 tools/add_meme.py 로 도감에 추가한다.
"""
import json
import re
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "cand"
CAND.mkdir(exist_ok=True)


def get(url, out=None):
    args = ["curl", "-s", "-m", "25", "-A", "Mozilla/5.0", "-L", url] + (["-o", str(out)] if out else [])
    return subprocess.run(args, capture_output=True).stdout


def search(item):
    key, q = item
    page = get(f"https://tenor.com/search/{urllib.parse.quote(q.replace(' ', '-'))}-gifs").decode("utf8", "ignore")
    m = re.search(r'<script id="store-cache" type="text/x-cache"[^>]*>(.*?)</script>', page, re.S)
    results = []
    if m:
        for v in json.loads(m.group(1)).get("universal", {}).get("search", {}).values():
            results = v.get("results", [])
            break
    out = []
    for r in results[:8]:
        f = r["media_formats"]
        if "mp4" not in f:
            continue
        out.append({
            "tenor_id": r["id"], "title": r.get("h1_title", ""), "tags": r.get("tags", []),
            "mp4": f["mp4"]["url"], "dims": f["mp4"].get("dims", [0, 0]),
            "preview": f.get("gifpreview", {}).get("url"),
        })
    for i, c in enumerate(out):
        if c["preview"]:
            get(c["preview"], CAND / f"{key}_{i}.jpg")
    return key, out


def sheets(data):
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    W, H, per = 170, 120, 6
    keys = list(data)
    for s in range(0, len(keys), per):
        chunk = keys[s:s + per]
        sheet = Image.new("RGB", (8 * W + 140, len(chunk) * (H + 4)), "white")
        d = ImageDraw.Draw(sheet)
        for r, k in enumerate(chunk):
            y = r * (H + 4)
            d.text((4, y + 50), k[:15], fill="black", font=font)
            for i in range(len(data[k])):
                try:
                    im = Image.open(CAND / f"{k}_{i}.jpg").convert("RGB")
                    im.thumbnail((W - 4, H - 4))
                    sheet.paste(im, (140 + i * W, y))
                except OSError:
                    pass
                d.text((143 + i * W, y + 2), str(i), fill="red", font=font)
        sheet.save(CAND / f"sheet_{s // per:02d}.jpg", quality=80)


if __name__ == "__main__":
    queries = json.loads(sys.argv[1])
    with ThreadPoolExecutor(8) as ex:
        data = dict(ex.map(search, queries.items()))
    (CAND / "candidates.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    sheets(data)
    for k, v in data.items():
        print("##", k)
        for i, c in enumerate(v):
            print(i, c["title"][:45], "|", ",".join(c["tags"])[:60])
    print("시트:", sorted(p.name for p in CAND.glob("sheet_*.jpg")))
