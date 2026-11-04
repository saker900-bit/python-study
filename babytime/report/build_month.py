"""두 달 기록을 합쳐서 [start, end] 기간의 그래프용 데이터를 만든다."""
import json, re, sys, zipfile
import statistics as st
from datetime import datetime, timedelta, date
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import babytime_analyzer as ba


def load(paths):
    recs, raw = [], ""
    for p in paths:
        with zipfile.ZipFile(p) as z:
            name = [n for n in z.namelist() if n.endswith("_asc.txt")][0]
            text = z.read(name).decode("utf-8-sig")
        raw += text
        recs += ba.parse_babytime_text(text)
    recs.sort(key=lambda r: r.start)
    return recs, raw


def build(recs, raw, start, end, months=5.5, weight=9):
    H = lambda td: round(td.total_seconds() / 3600, 2) if td else 0
    in_range = lambda dt: start <= dt.date() <= end
    rng = [r for r in recs if in_range(r.start)]
    days_res = [ba.analyze_day(recs, start + timedelta(days=i), months, weight) for i in range((end - start).days + 1)]
    days_res = [d for d in days_res if d["feed_count"]]

    days = []
    for d in days_res:
        ds = datetime.combine(d["date"], datetime.min.time())
        segs = [[round((max(s.start, ds) - ds).total_seconds() / 3600, 3), round((min(s.end, ds + timedelta(days=1)) - ds).total_seconds() / 3600, 3),
                 "n" if s.label == "밤잠" else "d"] for s in d["sleeps"]]
        feeds = [[round((f.start - ds).total_seconds() / 3600, 3), f.amount or 0] for f in d["feeds"]]
        nf = sum(1 for f in d["feeds"] if f.start.hour < 6)
        days.append(dict(date=d["date"].isoformat(), milk=d["milk_ml"], feeds=d["feed_count"], sleep=H(d["total_sleep"]),
                         night=H(d["night_sleep"]), nap=H(d["day_sleep"]), naps=d["nap_count"], longest=H(d["longest_sleep"]),
                         diapers=d["diaper_count"], poo=d["poo_count"], night_feeds=nf, segs=segs, feedpts=feeds))

    # 밤 단위: 저녁(18시 이후)에 시작한 밤잠 블록. 아침 수유 후 다시 잔 '밤잠'(3시간 넘게 떨어진 블록)은 따로 센다
    nights_all = [r for r in recs if r.kind == "sleep" and r.label == "밤잠" and r.end]
    groups = []
    for s in nights_all:
        if groups and (s.start - groups[-1][-1].end) <= timedelta(hours=3) and not (s.start.hour >= 6 and groups[-1][-1].end.hour >= 6 and s.start.hour < 12 and (s.start - groups[-1][-1].end) > timedelta(minutes=20)):
            groups[-1].append(s)
        else:
            groups.append([s])
    night_rows = []
    for g in groups:
        bed = g[0].start
        if not (bed.hour >= 18 or bed.hour < 3):
            continue
        nd = bed.date() if bed.hour >= 12 else bed.date() - timedelta(days=1)
        if not (start <= nd <= end):
            continue
        wake = g[-1].end
        fed = [f for f in recs if f.kind in ("formula", "breast") and bed < f.start < wake]
        night_rows.append(dict(date=nd.isoformat(), bed=bed.strftime("%m-%d %H:%M"), bedh=round(bed.hour + bed.minute / 60, 2),
                               wake=wake.strftime("%H:%M"), wakeh=round(wake.hour + wake.minute / 60, 2), wakings=len(g) - 1,
                               feeds=len(fed), asleep=H(sum((s.end - s.start for s in g), timedelta())), span=H(wake - bed)))

    naps = [r for r in rng if r.kind == "sleep" and r.label == "낮잠" and r.end]
    sleeps = sorted([r for r in recs if r.kind == "sleep" and r.end], key=lambda r: r.start)
    ww = [round((b.start - a.end).total_seconds() / 60) for a, b in zip(sleeps, sleeps[1:])
          if in_range(a.end) and 20 <= (b.start - a.end).total_seconds() / 60 <= 360 and 6 <= a.end.hour < 21]
    feeds_all = [r for r in rng if r.kind in ("formula", "breast")]
    fh = [0] * 24
    for f in feeds_all:
        fh[f.start.hour] += 1
    etc = [r for r in rng if r.kind == "etc"]
    count = lambda xs: sorted({x: xs.count(x) for x in xs}.items(), key=lambda kv: -kv[1])
    meds = count([m.strip() for r in etc if r.label == "투약" for m in r.memo.split(",") if m.strip()])
    # 배변색, 메모 (원문에서)
    colors, memos = [], []
    for block in raw.replace("\r", "").split("===================="):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        try:
            t = datetime.strptime(lines[0].split("~")[0].strip(), "%Y-%m-%d %I:%M %p")
        except ValueError:
            continue
        if not in_range(t):
            continue
        for l in lines[1:]:
            if l.startswith("배변색:"):
                colors.append([t.date().isoformat(), "#" + l.split(":", 1)[1].strip()])
            if l.startswith("메모:") and "분유" not in l:
                memos.append([t.strftime("%Y-%m-%d %H:%M"), l.split(":", 1)[1].strip(), lines[1].split(":", 1)[1].strip()])

    mean = lambda xs: round(st.mean(xs), 2) if xs else 0
    summary = dict(
        days=len(days), milk=mean([d["milk"] for d in days]), feeds=mean([d["feeds"] for d in days]),
        per_feed=mean([f.amount for f in feeds_all if f.amount]), sleep=mean([d["sleep"] for d in days]),
        night=mean([d["night"] for d in days]), nap=mean([d["nap"] for d in days]), naps=mean([d["naps"] for d in days]),
        longest=mean([d["longest"] for d in days]), diapers=mean([d["diapers"] for d in days]),
        poo_days=sum(1 for d in days if d["poo"]), night_feeds=mean([n["feeds"] for n in night_rows]),
        wakings=mean([n["wakings"] for n in night_rows]), bed=mean([n["bedh"] if n["bedh"] > 12 else n["bedh"] + 24 for n in night_rows]),
        wake=mean([n["wakeh"] for n in night_rows]), nap_med=st.median([round((n.end - n.start).total_seconds() / 60) for n in naps]) if naps else 0,
        ww_med=st.median(ww) if ww else 0, baths=sum(1 for r in etc if r.label == "목욕"),
        skin=sum(v for k, v in meds if any(w in k for w in ("보습", "로션", "오일", "크림"))),
        hospital=[[r.start.date().isoformat(), r.memo] for r in etc if r.label == "병원"],
        tummy=sum(1 for r in etc if r.label == "터미타임"),
        solids=sum(1 for r in rng if r.kind == "solid"),
    )
    return dict(range=[start.isoformat(), end.isoformat()], days=days, nights=night_rows,
                nap_len=[round((n.end - n.start).total_seconds() / 60) for n in naps], wake_windows=ww, feed_hours=fh,
                amounts=[f.amount for f in feeds_all if f.amount], meds=meds, colors=colors, memos=memos, summary=summary)


if __name__ == "__main__":
    recs, raw = load(sys.argv[1:3])
    oct_ = build(recs, raw, date(2026, 10, 1), date(2026, 10, 31))
    nov = build(recs, raw, date(2026, 11, 1), date(2026, 11, 4))
    json.dump(dict(oct=oct_, nov=nov), open("data_nov.json", "w"), ensure_ascii=False)
    for k, v in (("OCT", oct_), ("NOV", nov)):
        print(k, json.dumps(v["summary"], ensure_ascii=False))
        print("  nights", [(n["date"], n["bed"], n["wake"], n["wakings"], n["feeds"], n["asleep"]) for n in v["nights"][-5:]])
    print("NOV days", [(d["date"], d["milk"], d["feeds"], d["sleep"], d["night"], d["nap"], d["naps"], d["longest"], d["diapers"], d["night_feeds"]) for d in nov["days"]])
    print("NOV meds", nov["meds"], "colors", nov["colors"], "memos", nov["memos"])
    print("NOV naps", nov["nap_len"], "ww", nov["wake_windows"], "amounts", nov["amounts"])
    print("OCT colors", oct_["colors"][:3], len(oct_["colors"]))
