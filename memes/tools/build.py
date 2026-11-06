"""도감(catalog.json)으로 앱 화면을 만든다.

  python tools/build.py artifact   # Claude 아티팩트용: 짤 mp4를 받아서 site/m/ 에 넣음
  python tools/build.py app        # 스토어 앱용: 짤은 원격 URL로 재생, site/ 에 index.html
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
mode = sys.argv[1] if len(sys.argv) > 1 else "artifact"
out = ROOT / "site"
(out / "m").mkdir(parents=True, exist_ok=True)

catalog = json.loads((ROOT / "catalog.json").read_text())
memes = catalog["memes"]
config = {"mediaBase": "m"} if mode == "artifact" else {}

if mode == "artifact":
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
(out / "index.html").write_text(html)

files = [{"as": "index.html", "path": str(out / "index.html")}]
if mode == "artifact":
    files += [{"as": f"m/{m['id']}.mp4", "path": str(out / "m" / f"{m['id']}.mp4")} for m in memes]
(out / "files.json").write_text(json.dumps(files, ensure_ascii=False))
print(f"{mode}: {len(memes)}개 밈 -> {out}/index.html (publish 목록: site/files.json)")
