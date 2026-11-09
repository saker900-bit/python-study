"""월간 리포트 HTML 만들기: python render.py <기록 txt/zip...> --out <폴더>"""
import argparse, json, sys
from datetime import date
from pathlib import Path
here = Path(__file__).parent
sys.path.insert(0, str(here))
from build_v2 import load_texts, build, feeding_history, interval_by_amount  # noqa
from texts_2026 import texts  # noqa

ap = argparse.ArgumentParser(); ap.add_argument("inputs", nargs="+"); ap.add_argument("--out", required=True); ap.add_argument("--only", nargs="*")
a = ap.parse_args()
NOV_END = date(2026, 11, 8)  # 마지막 완전한 날
recs, raw = load_texts(a.inputs)
M = {
    "2026-06": build(recs, raw, date(2026, 6, 1), date(2026, 6, 30)),
    "2026-07": build(recs, raw, date(2026, 7, 1), date(2026, 7, 31)),
    "2026-08": build(recs, raw, date(2026, 8, 1), date(2026, 8, 31)),
    "2026-09": build(recs, raw, date(2026, 9, 1), date(2026, 9, 30), sleep_from=date(2026, 9, 20)),
    "2026-10": build(recs, raw, date(2026, 10, 1), date(2026, 10, 31), sleep_from=date(2026, 10, 1)),
    "2026-11": build(recs, raw, date(2026, 11, 1), NOV_END, sleep_from=date(2026, 11, 1), sleep_to=NOV_END, months=5.6),
}
hist = feeding_history(recs, date(2026, 5, 31), NOV_END)
names = {"2026-06": "june", "2026-07": "july", "2026-08": "august", "2026-09": "september", "2026-10": "october", "2026-11": "november"}
prev = {"2026-07": "2026-06", "2026-08": "2026-07", "2026-09": "2026-08", "2026-10": "2026-09", "2026-11": "2026-10"}
tpl = (here / "month_v2.html").read_text()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
nfeeds = sum(d["n"] for d in hist["days"])
iq = interval_by_amount(recs, date(2026, 10, 1), NOV_END)
Q = {"badge": "늘리지 않아도 돼요",
     "answer": "지금 1회량(평균 213ml, 컨디션 좋은 날 240ml)이 이 월령에서 늘어나는 끝자리예요. 더 늘리면 하루 상한을 넘기고, 우리 아기 기록에서도 더 먹는다고 더 오래 버티지 않았어요. 늘릴 건 젖병 크기가 아니라 곧 시작할 이유식이에요.",
     "buckets": iq["buckets"],
     "points": [
        ["ok", f"<b>공식 기준의 끝에 와 있어요.</b> 미국소아과학회는 1회량이 7~8온스(210~240ml)에서 더 늘지 않는다고 해요. 10~11월 수유의 {iq['share240']}%가 이미 240ml 이상이에요."],
        ["ok", "<b>더 늘리면 하루 상한을 넘어요.</b> 240ml × 4번 = 960ml로 이미 하루 32온스(약 950ml)에 닿아요. 250ml씩 4번이면 1,000ml예요."],
        ["ok", f"<b>많이 먹어도 더 오래 버티지 않아요.</b> 10~11월 낮 수유 {iq['n']}번을 보면, 220ml를 넘긴 뒤엔 240ml 이상을 먹어도 다음 수유까지 간격이 같았어요(위 그래프)."],
        ["ok", "<b>11월에 줄어든 건 젖병이 작아서가 아니에요.</b> 아픈 날 남기거나 하루 3번만 먹어서 줄었고, 회복한 11/8엔 240ml씩 네 번을 다 먹었어요."],
        ["mid", "<b>이럴 땐 그 회차만 조금 더:</b> 240ml를 5분 안에 다 먹고도 입을 벌리고 찾으면 20~30ml 더 줘도 돼요. 하루 950ml 안에서만요."],
        ["mid", "<b>모자란 열량은 이유식으로:</b> 생후 6개월(11월 20일 무렵)부터 이유식을 시작하면 분유는 오히려 조금씩 줄어도 정상이에요."],
     ]}
for m in M:
    if a.only and m not in a.only:
        continue
    T = texts(m, M, hist if m == "2026-11" else None, Q if m == "2026-11" else None)
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
