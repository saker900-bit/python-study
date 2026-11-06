"""KLIPY에서 검색어별로 짤이 제대로 나오는지 확인 (개발용, KLIPY 테스트 키 필요).

  KLIPY_KEY=... python tools/klipy_check.py '{"id": "검색어"}' [gifs|clips]

결과: cand/klipy_sheet_*.jpg (앞 6개 결과 첫 화면). 확인 후 cand/ 는 지운다 (KLIPY 콘텐츠 저장 금지).
"""
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "cand"
CAND.mkdir(exist_ok=True)
key = os.environ["KLIPY_KEY"]
kind = sys.argv[2] if len(sys.argv) > 2 else "gifs"
queries = json.loads(sys.argv[1])


def urls(item):
    found = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and v.startswith("http") and k in ("gif", "webp", "jpg", "png", "url"):
                    found.append((k, v))
                elif isinstance(v, dict) and isinstance(v.get("url"), str) and k in ("gif", "webp", "jpg", "png"):
                    found.append((k, v["url"]))
                else:
                    walk(v)
    walk(item.get("file") or item)
    pref = {"jpg": 0, "png": 0, "gif": 1, "webp": 2}
    found.sort(key=lambda x: pref.get(x[0], 9))
    return found[0][1] if found else None


font = ImageFont.load_default()
for n, (mid, q) in enumerate(queries.items()):
    params = urllib.parse.urlencode({"q": q, "page": 1, "per_page": 8, "customer_id": "dev-check", "locale": "kr"})
    raw = subprocess.run(["curl", "-s", "-m", "20", f"https://api.klipy.com/api/v1/{key}/{kind}/search?{params}"],
                         capture_output=True).stdout
    data = json.loads(raw or b"{}")
    items = [i for i in ((data.get("data") or {}).get("data") or []) if i.get("type") != "ad"][:6]
    print("##", mid, q, len(items))
    sheet = Image.new("RGB", (6 * 170, 150), "white")
    d = ImageDraw.Draw(sheet)
    for i, it in enumerate(items):
        print(" ", i, it.get("slug"), "|", (it.get("title") or "")[:50])
        u = urls(it)
        if not u:
            continue
        f = CAND / f"k_{mid}_{i}"
        subprocess.run(["curl", "-s", "-m", "20", "-o", str(f), u])
        try:
            im = Image.open(f).convert("RGB")
            im.thumbnail((166, 130))
            sheet.paste(im, (i * 170, 18))
        except OSError:
            pass
        d.text((i * 170 + 2, 2), str(i), fill="red", font=font)
    sheet.save(CAND / f"klipy_sheet_{n:02d}_{mid}.jpg", quality=80)
print("시트:", sorted(p.name for p in CAND.glob("klipy_sheet_*.jpg")))
