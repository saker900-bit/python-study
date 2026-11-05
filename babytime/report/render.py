"""월간 리포트 HTML 만들기: python render.py <기록 txt/zip...> --out <폴더>"""
import argparse, json, sys
from datetime import date
from pathlib import Path
here = Path(__file__).parent
sys.path.insert(0, str(here))
from build_v2 import load_texts, build, feeding_history  # noqa
from texts_2026 import texts  # noqa

ap = argparse.ArgumentParser(); ap.add_argument("inputs", nargs="+"); ap.add_argument("--out", required=True); ap.add_argument("--only", nargs="*")
a = ap.parse_args()
recs, raw = load_texts(a.inputs)
M = {
    "2026-06": build(recs, raw, date(2026, 6, 1), date(2026, 6, 30)),
    "2026-07": build(recs, raw, date(2026, 7, 1), date(2026, 7, 31)),
    "2026-08": build(recs, raw, date(2026, 8, 1), date(2026, 8, 31)),
    "2026-09": build(recs, raw, date(2026, 9, 1), date(2026, 9, 30), sleep_from=date(2026, 9, 20)),
    "2026-10": build(recs, raw, date(2026, 10, 1), date(2026, 10, 31), sleep_from=date(2026, 10, 1)),
    "2026-11": build(recs, raw, date(2026, 11, 1), date(2026, 11, 5), sleep_from=date(2026, 11, 1), sleep_to=date(2026, 11, 4), months=5.5),
}
hist = feeding_history(recs, date(2026, 5, 31), date(2026, 11, 5))
names = {"2026-06": "june", "2026-07": "july", "2026-08": "august", "2026-09": "september", "2026-10": "october", "2026-11": "november"}
prev = {"2026-07": "2026-06", "2026-08": "2026-07", "2026-09": "2026-08", "2026-10": "2026-09", "2026-11": "2026-10"}
tpl = (here / "month_v2.html").read_text()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
nfeeds = sum(d["n"] for d in hist["days"])
for m in M:
    if a.only and m not in a.only:
        continue
    T = texts(m, M, hist if m == "2026-11" else None)
    y, mo = map(int, m.split("-"))
    start = date(2026, 5, 31) if m == "2026-06" else date(y, mo, 1)
    nrec = sum(1 for r in recs if start <= r.start.date() <= date.fromisoformat(M[m]["range"][1]))
    T["eyebrow"] = T["eyebrow"].replace("{records}", f"{nrec:,}")
    if "hist" in T:
        T["hist"]["lede"] = T["hist"]["lede"].replace("{feeds}", f"{nfeeds:,}")
        T["hist"]["copy"] = T["hist"]["copy"].replace("{feeds}", f"{nfeeds:,}")
    if m == "2026-09":
        T["peer"][3].update(band=[1.5, 2], bandLabel="3~4개월 흔한 기준 1.5~2")
    data = {"T": T, "cur": M[m], "prev": M.get(prev.get(m)), "hist": hist if m == "2026-11" else None}
    html = tpl.replace("__TITLE__", T["title"]).replace("__DATA__", json.dumps(data, ensure_ascii=False))
    (out / f"{names[m]}.html").write_text(html)
    print("wrote", out / f"{names[m]}.html", len(html) // 1024, "KB")
