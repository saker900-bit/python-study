"""후보 시트에서 고른 GIF로 도감(catalog.json)에 밈을 추가한다.

  python tools/add_meme.py new_memes.json

new_memes.json 예시:
[{"id": "muyaho", "pick": 0, "name": "무야호", "quote": "무야호~!", "source": "무한도전 알래스카 편",
  "desc": "두 문장 이내 설명", "region": "ko"}]
pick = cand/candidates.json 에서 그 id의 후보 번호.
"""
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cat_path = ROOT / "catalog.json"
catalog = json.loads(cat_path.read_text())
cands = json.loads((ROOT / "cand" / "candidates.json").read_text())
today = datetime.date.today().isoformat()
have = {m["id"] for m in catalog["memes"]}
have_media = {m["media"]["id"] for m in catalog["memes"]}

added = []
for e in json.loads(Path(sys.argv[1]).read_text()):
    if e["id"] in have:
        print("이미 있음:", e["id"])
        continue
    c = cands[e["id"]][e["pick"]]
    if c["tenor_id"] in have_media:
        print("같은 짤이 이미 있음:", e["id"])
        continue
    w, h = (c["dims"] + [0, 0])[:2]
    catalog["memes"].append({
        "id": e["id"], "name": e["name"], "quote": e["quote"], "source": e["source"], "desc": e["desc"],
        "region": e.get("region", "ko"),
        "media": {"provider": "tenor", "id": c["tenor_id"], "mp4": c["mp4"], "w": w, "h": h},
        "added": today,
        "keyword": e.get("keyword", e["name"]), "kind": e.get("kind", "gifs"),
    })
    added.append(e["id"])

catalog["updated"] = today
cat_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=1))
print(f"추가 {len(added)}개: {added} / 전체 {len(catalog['memes'])}개")
