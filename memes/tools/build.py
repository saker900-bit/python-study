"""도감(catalog.json)으로 앱 화면을 만든다.

  python tools/build.py artifact   # Claude 아티팩트용: 짤 mp4를 받아서 site/m/ 에 넣음
  KLIPY_KEY=... KLIPY_KEY_NOADS=... MEME_API=https://서버 python tools/build.py app
                                   # 스토어 앱용: 짤은 KLIPY에서 앱이 직접 받아 옴
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
mode = sys.argv[1] if len(sys.argv) > 1 else "artifact"
test = mode == "test"   # 테스트 버전: 미리보기와 같은데 광고 없음
if test:
    mode = "artifact"
out = ROOT / "site"
(out / "m").mkdir(parents=True, exist_ok=True)

catalog = json.loads((ROOT / "catalog.json").read_text())
memes = catalog["memes"]
if mode == "artifact":
    config = {"mediaBase": "m", "noAds": test}
else:
    # 스토어 앱: 짤은 KLIPY에서 앱이 직접 받음. 앱 안에는 우리 텍스트만 넣고 Tenor 주소는 빼기
    import os
    config = {k: v for k, v in {
        "klipyKey": os.environ.get("KLIPY_KEY", ""),
        "klipyKeyNoAds": os.environ.get("KLIPY_KEY_NOADS", ""),
        "api": os.environ.get("MEME_API", ""),
    }.items() if v}
    memes = [{k: v for k, v in m.items() if k != "media"} for m in memes]

if mode == "artifact":
    # 미리보기는 짤 파일이 있는 밈만
    memes = [m for m in memes if m.get("media")]

    def fetch(m):
        dst = out / "m" / f"{m['id']}.mp4"
        if dst.exists() and dst.stat().st_size > 1000:
            return m["id"], True
        r = subprocess.run(["curl", "-sfL", "-m", "60", "-A", "Mozilla/5.0", "-o", str(dst), m["media"]["mp4"]])
        return m["id"], r.returncode == 0
    with ThreadPoolExecutor(8) as ex:
        failed = [i for i, ok in ex.map(fetch, memes) if not ok]
    if failed:
        print("다운로드 실패:", failed)
        memes = [m for m in memes if m["id"] not in failed]

lib = json.dumps(memes, ensure_ascii=False).replace("</", "<\\/")
html = (ROOT / "web" / "template.html").read_text()
html = html.replace("__LIB__", lib).replace("__CONFIG__", json.dumps(config))
index_name = "index_test.html" if test else "index.html"
(out / index_name).write_text(html)

files = [{"as": "index.html", "path": str(out / index_name)}]
if mode == "artifact":
    files += [{"as": f"m/{m['id']}.mp4", "path": str(out / "m" / f"{m['id']}.mp4")} for m in memes]
(out / ("files_test.json" if test else "files.json")).write_text(json.dumps(files, ensure_ascii=False))
print(f"{mode}: {len(memes)}개 밈 -> {out}/index.html (publish 목록: site/files.json)")
