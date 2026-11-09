"""월간 리포트 데이터 (v2): 수면 기록이 없는 달, 모유·유축수유·체온까지 다룬다.

    from build_v2 import load_texts, build
    recs, raw = load_texts([txt_or_zip, ...])
    data = build(recs, raw, date(2026, 9, 1), date(2026, 9, 30), sleep_from=date(2026, 9, 20))
"""
import re
import statistics as st
import sys
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import babytime_analyzer as ba  # noqa: E402

BIRTH = date(2026, 5, 20)  # 2026-11-04에 생후 5.5개월


def load_texts(paths):
    raw = ""
    for p in paths:
        p = str(p)
        if p.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                name = [n for n in z.namelist() if n.endswith("_asc.txt")][0]
                raw += z.read(name).decode("utf-8-sig")
        else:
            raw += open(p, encoding="utf-8-sig").read()
        raw += "\n====================\n"
    recs = ba.parse_babytime_text(raw)
    # 같은 기록이 두 파일에 겹치면 하나만 남긴다
    seen, out = set(), []
    for r in recs:
        key = (r.kind, r.label, r.start, r.end, r.amount)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out, raw


def age_months(d):
    return round((d - BIRTH).days / 30.44, 1)


def _mean(xs, nd=2):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), nd) if xs else None


def build(recs, raw, start, end, sleep_from=None, sleep_to=None, months=None, weight=9):
    """[start, end] 기간 데이터. sleep_from~sleep_to: 수면을 평균에 넣을 날 (수면 기록이 없으면 None)."""
    months = months if months is not None else age_months(start + (end - start) / 2)
    H = lambda td: round(td.total_seconds() / 3600, 2) if td else 0
    in_rng = lambda dt: start <= dt.date() <= end
    feeds_all = sorted([r for r in recs if r.kind in ("formula", "breast") and r.amount], key=lambda r: r.start)
    rng = [r for r in recs if in_rng(r.start)]
    has_sleep = sleep_from is not None
    sleep_to = sleep_to or end

    days = []
    d = start
    while d <= end:
        res = ba.analyze_day(recs, d, months, weight)
        fs = [f for f in feeds_all if f.start.date() == d]
        if fs:
            ds = datetime.combine(d, datetime.min.time())
            prev = [f for f in feeds_all if f.start < fs[0].start]
            gaps = [(b.start - a.start).total_seconds() / 3600 for a, b in zip(([prev[-1]] if prev else []) + fs, fs)]
            row = dict(date=d.isoformat(), milk=sum(f.amount for f in fs), feeds=len(fs),
                       per=round(st.mean(f.amount for f in fs), 1), max=max(f.amount for f in fs),
                       formula=sum(f.amount for f in fs if f.kind == "formula"), breast=sum(f.amount for f in fs if f.kind == "breast"),
                       night_feeds=sum(1 for f in fs if f.start.hour < 6), gap=round(max(gaps), 2) if gaps else None,
                       diapers=res["diaper_count"], poo=res["poo_count"],
                       feedpts=[[round((f.start - ds).total_seconds() / 3600, 3), f.amount] for f in fs])
            if has_sleep and sleep_from <= d:
                row.update(sleep=H(res["total_sleep"]), night=H(res["night_sleep"]), nap=H(res["day_sleep"]), naps=res["nap_count"],
                           longest=H(res["longest_sleep"]), sleep_ok=d <= sleep_to,
                           segs=[[round((max(s.start, ds) - ds).total_seconds() / 3600, 3), round((min(s.end, ds + timedelta(days=1)) - ds).total_seconds() / 3600, 3),
                                  "n" if s.label == "밤잠" else "d"] for s in res["sleeps"]])
            days.append(row)
        d += timedelta(days=1)

    # 밤 단위: 저녁에 시작한 밤잠 묶음. 아침 6시 이후 수유하고 다시 잔 잠은 따로 본다
    nights = []
    if has_sleep:
        ns = sorted([r for r in recs if r.kind == "sleep" and r.label == "밤잠" and r.end], key=lambda r: r.start)
        groups = []
        for s in ns:
            if groups:
                gap = s.start - groups[-1][-1].end
                morning = 6 <= s.start.hour < 12 and gap > timedelta(minutes=20)
                if gap <= timedelta(hours=3) and not morning:
                    groups[-1].append(s)
                    continue
            groups.append([s])
        for g in groups:
            bed = g[0].start
            if not (bed.hour >= 18 or bed.hour < 3):
                continue
            nd = bed.date() if bed.hour >= 12 else bed.date() - timedelta(days=1)
            if not (max(start, sleep_from - timedelta(days=1)) <= nd <= end):
                continue
            wake = g[-1].end
            fed = [f for f in feeds_all if bed < f.start < wake]
            nights.append(dict(date=nd.isoformat(), bed=bed.strftime("%m-%d %H:%M"), bedh=round(bed.hour + bed.minute / 60, 2),
                               wake=wake.strftime("%H:%M"), wakeh=round(wake.hour + wake.minute / 60, 2), wakings=len(g) - 1,
                               feeds=len(fed), asleep=H(sum((s.end - s.start for s in g), timedelta()))))
        # 아직 자는 중인 밤 (끝 시각 없음)
        open_ = [r for r in recs if r.kind == "sleep" and r.label == "밤잠" and not r.end and in_rng(r.start)]
        for r in open_:
            nights.append(dict(date=r.start.date().isoformat(), bedh=round(r.start.hour + r.start.minute / 60, 2), open=True))

    sdays = [x for x in days if x.get("sleep_ok")]
    fdays = days
    feeds_rng = [f for f in feeds_all if in_rng(f.start)]
    naps = [r for r in rng if r.kind == "sleep" and r.label == "낮잠" and r.end]
    sl = sorted([r for r in recs if r.kind == "sleep" and r.end], key=lambda r: r.start)
    ww = [round((b.start - a.end).total_seconds() / 60) for a, b in zip(sl, sl[1:])
          if in_rng(a.end) and 20 <= (b.start - a.end).total_seconds() / 60 <= 360 and 6 <= a.end.hour < 21]
    fh = [0] * 24
    for f in feeds_rng:
        fh[f.start.hour] += 1
    etc = [r for r in rng if r.kind == "etc"]

    def count(xs):
        c = {}
        for x in xs:
            c[x] = c.get(x, 0) + 1
        return sorted(c.items(), key=lambda kv: -kv[1])

    meds = count([m.strip() for r in etc if r.label == "투약" for m in r.memo.split(",") if m.strip()])
    temps = [[r.start.strftime("%Y-%m-%d %H:%M"), float(r.memo)] for r in etc if r.label == "열" and re.match(r"^\d", r.memo)]
    colors, memos = [], []
    for block in raw.replace("\r", "").split("===================="):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        try:
            t = datetime.strptime(lines[0].split("~")[0].strip(), "%Y-%m-%d %I:%M %p")
        except ValueError:
            continue
        if not in_rng(t):
            continue
        kind = lines[1].split(":", 1)[1].strip() if len(lines) > 1 and ":" in lines[1] else ""
        for l in lines[1:]:
            if l.startswith("배변색:"):
                colors.append([t.date().isoformat(), "#" + l.split(":", 1)[1].strip()])
            if l.startswith("메모:"):
                memos.append([t.strftime("%Y-%m-%d %H:%M"), kind, l.split(":", 1)[1].strip()])
    colors = sorted(set(map(tuple, colors)))

    summary = dict(
        months=months, days=len(fdays), sleep_days=len(sdays),
        milk=_mean([x["milk"] for x in fdays], 0), feeds=_mean([x["feeds"] for x in fdays], 1),
        per_feed=round(sum(f.amount for f in feeds_rng) / len(feeds_rng)) if feeds_rng else 0,
        max_feed=max((f.amount for f in feeds_rng), default=0),
        breast_share=round(sum(f.amount for f in feeds_rng if f.kind == "breast") / max(1, sum(f.amount for f in feeds_rng)) * 100, 1),
        pump=round(sum(r.amount or 0 for r in rng if r.kind == "pump")),
        night_feeds_clock=_mean([x["night_feeds"] for x in fdays]), gap=_mean([x["gap"] for x in fdays]),
        diapers=_mean([x["diapers"] for x in fdays], 1), poo_days=sum(1 for x in fdays if x["poo"]),
        baths=sum(1 for r in etc if r.label == "목욕"), tummy=sum(1 for r in etc if r.label == "터미타임"),
        tummy_min=round(sum(((r.end or r.start) - r.start).total_seconds() / 60 for r in etc if r.label == "터미타임")),
        walks=sum(1 for r in etc if r.label == "기록A" and "산책" in r.memo),
        hospital=[[r.start.date().isoformat(), r.memo] for r in etc if r.label == "병원"],
        temp_max=max((t[1] for t in temps), default=None), temp_n=len(temps),
        solids=sum(1 for r in rng if r.kind == "solid"),
    )
    if has_sleep and sdays:
        full_nights = [n for n in nights if not n.get("open")]
        summary.update(
            sleep=_mean([x["sleep"] for x in sdays]), night=_mean([x["night"] for x in sdays]), nap=_mean([x["nap"] for x in sdays]),
            naps=_mean([x["naps"] for x in sdays]), longest=_mean([x["longest"] for x in sdays]),
            wakings=_mean([n["wakings"] for n in full_nights]), night_feeds=_mean([n["feeds"] for n in full_nights]),
            bed=_mean([n["bedh"] if n["bedh"] > 12 else n["bedh"] + 24 for n in nights]),
            bed_min=min((n["bedh"] if n["bedh"] > 12 else n["bedh"] + 24 for n in nights), default=None),
            bed_max=max((n["bedh"] if n["bedh"] > 12 else n["bedh"] + 24 for n in nights), default=None),
            wake=_mean([n["wakeh"] for n in full_nights]),
            nap_med=st.median([round((n.end - n.start).total_seconds() / 60) for n in naps]) if naps else None,
            ww_med=st.median(ww) if ww else None,
        )
    return dict(range=[start.isoformat(), end.isoformat()], has_sleep=has_sleep, days=days, nights=nights,
                nap_len=[round((n.end - n.start).total_seconds() / 60) for n in naps], wake_windows=ww, feed_hours=fh,
                amounts=[f.amount for f in feeds_rng], meds=meds, temps=temps, colors=colors, memos=memos, summary=summary)


def feeding_history(recs, start, end):
    """기록 첫날부터 오늘까지 날짜별·월별 수유 변화."""
    feeds = sorted([r for r in recs if r.kind in ("formula", "breast") and r.amount], key=lambda r: r.start)
    days, d = [], start
    while d <= end:
        fs = [f for f in feeds if f.start.date() == d]
        if fs:
            prev = [f for f in feeds if f.start < fs[0].start]
            seq = ([prev[-1]] if prev else []) + fs
            gaps = [(b.start - a.start).total_seconds() / 3600 for a, b in zip(seq, seq[1:])]
            days.append(dict(date=d.isoformat(), age=round((d - BIRTH).days / 30.44, 2), total=sum(f.amount for f in fs), n=len(fs),
                             per=round(st.mean(f.amount for f in fs), 1), max=max(f.amount for f in fs),
                             breast=sum(f.amount for f in fs if f.kind == "breast"), night=sum(1 for f in fs if f.start.hour < 6),
                             gap=round(max(gaps), 2) if gaps else None))
        d += timedelta(days=1)
    by_m = {}
    for x in days:
        by_m.setdefault(x["date"][:7], []).append(x)
    months = []
    for m, xs in by_m.items():
        months.append(dict(month=m, days=len(xs), age=round(st.mean(x["age"] for x in xs), 1),
                           total=round(st.mean(x["total"] for x in xs)), n=round(st.mean(x["n"] for x in xs), 1),
                           per=round(sum(x["total"] for x in xs) / sum(x["n"] for x in xs)), max=max(x["max"] for x in xs),
                           breast_share=round(sum(x["breast"] for x in xs) / sum(x["total"] for x in xs) * 100, 1),
                           night=round(st.mean(x["night"] for x in xs), 2), gap=round(st.mean(x["gap"] for x in xs if x["gap"]), 2)))
    return dict(days=days, months=months)


def interval_by_amount(recs, start, end, buckets=((0, 180), (180, 220), (220, 240), (240, 400))):
    """낮(6~19시) 수유의 1회량 구간별로 다음 수유까지 평균 간격(시간)."""
    feeds = sorted([r for r in recs if r.kind in ("formula", "breast") and r.amount and start <= r.start.date() <= end], key=lambda r: r.start)
    pairs = [(a.amount, (b.start - a.start).total_seconds() / 3600) for a, b in zip(feeds, feeds[1:]) if 6 <= a.start.hour < 19]
    out = []
    for lo, hi in buckets:
        g = [h for amt, h in pairs if lo <= amt < hi]
        label = f"{hi}ml 미만" if lo == 0 else (f"{lo}ml 이상" if hi >= 400 else f"{lo}~{hi - 1}ml")
        out.append([label, round(st.mean(g), 2) if g else None, len(g)])
    share240 = round(sum(1 for f in feeds if f.amount >= 240) / len(feeds) * 100)
    return dict(buckets=out, share240=share240, n=len(pairs))
