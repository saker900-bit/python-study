"""베이비타임 기록 분석기.

베이비타임(또는 비슷한 육아 기록 앱)에서 내보낸 CSV 파일을 읽어서
하루 수유량, 수면 패턴, 기저귀 횟수를 분석하고 월령별 일반 권장 범위와 비교한다.

사용법:
    python babytime_analyzer.py 기록.csv --months 6 --weight 7.5
    python babytime_analyzer.py 기록.csv --months 6 --date 2026-11-04 --html report.html

CSV 열 이름은 한글/영어 모두 인식한다 (종류/type, 시작/start, 종료/end, 양/amount, 메모/memo).
외부 라이브러리 없이 파이썬 표준 라이브러리만 사용한다.

※ 이 분석은 일반적인 참고용이며 의학적 진단이 아니다. 걱정되면 소아과와 상담할 것.
"""

import argparse
import csv
import html
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# 데이터 읽기
# ---------------------------------------------------------------------------

COLUMN_ALIASES = {
    "type": ["종류", "구분", "활동", "type", "activity", "category"],
    "start": ["시작", "시작시간", "시작 시간", "시간", "start", "start time", "time"],
    "end": ["종료", "종료시간", "종료 시간", "끝", "end", "end time"],
    "amount": ["양(ml)", "양", "용량", "ml", "amount", "volume"],
    "memo": ["메모", "비고", "memo", "note", "notes"],
}

TYPE_ALIASES = {
    "formula": ["분유", "formula"],
    "breast": ["모유", "수유", "모유수유", "유축", "breast", "nursing"],
    "solid": ["이유식", "간식", "solid", "solids", "food"],
    "sleep": ["수면", "잠", "낮잠", "밤잠", "sleep", "nap"],
    "diaper": ["기저귀", "소변", "대변", "diaper", "pee", "poo"],
}

TIME_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y. %m. %d. %H:%M",
]


@dataclass
class Record:
    kind: str
    start: datetime
    end: datetime | None
    amount: float | None
    memo: str


def _find_column(headers, key):
    normalized = {h.strip().lower(): h for h in headers}
    for alias in COLUMN_ALIASES[key]:
        if alias.lower() in normalized:
            return normalized[alias.lower()]
    return None


def _normalize_type(raw):
    raw = raw.strip().lower()
    for kind, aliases in TYPE_ALIASES.items():
        if any(a.lower() in raw for a in aliases):
            return kind
    return None


def _parse_time(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"시간 형식을 알 수 없음: {raw!r}")


def _parse_amount(raw):
    raw = (raw or "").strip().lower().replace("ml", "").replace(",", "")
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def load_records(path):
    # 엑셀에서 저장한 CSV는 BOM이 붙는 경우가 많아서 utf-8-sig로 읽는다.
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        cols = {key: _find_column(headers, key) for key in COLUMN_ALIASES}
        if not cols["type"] or not cols["start"]:
            raise SystemExit(f"'종류'와 '시작' 열이 필요합니다. 현재 열: {headers}")

        records = []
        for row in reader:
            kind = _normalize_type(row.get(cols["type"], ""))
            start = _parse_time(row.get(cols["start"]))
            if not kind or not start:
                continue
            end = _parse_time(row.get(cols["end"])) if cols["end"] else None
            amount = _parse_amount(row.get(cols["amount"])) if cols["amount"] else None
            memo = (row.get(cols["memo"]) or "").strip() if cols["memo"] else ""
            records.append(Record(kind, start, end, amount, memo))
    records.sort(key=lambda r: r.start)
    return records


# ---------------------------------------------------------------------------
# 월령별 일반 권장 범위 (AAP/AASM 등 일반 가이드 기준의 대략적인 값)
# ---------------------------------------------------------------------------

def sleep_range(months):
    if months < 4:
        return 14, 17
    if months < 12:
        return 12, 16
    if months < 24:
        return 11, 14
    return 10, 13


def feeding_count_range(months):
    if months < 1:
        return 8, 12
    if months < 4:
        return 6, 8
    if months < 6:
        return 5, 7
    if months < 12:
        return 4, 6
    return 3, 5


def milk_ml_range(months, weight_kg):
    """하루 분유/모유 권장량. 체중이 있으면 체중 기준(약 150ml/kg, 최대 1000ml)."""
    if months >= 12:
        return 400, 600
    if weight_kg:
        center = min(weight_kg * 150, 1000)
        if months >= 6:  # 이유식을 시작하면 우유량이 조금 줄어드는 게 보통
            center = min(center, 900) * 0.9
        return round(center * 0.85), round(min(center * 1.15, 1000))
    if months < 1:
        return 400, 700
    if months < 6:
        return 700, 1000
    return 600, 900


# ---------------------------------------------------------------------------
# 분석
# ---------------------------------------------------------------------------

NIGHT_START_HOUR = 19  # 저녁 7시 ~ 아침 7시를 밤잠으로 본다
NIGHT_END_HOUR = 7


def _overlap(a_start, a_end, b_start, b_end):
    start, end = max(a_start, b_start), min(a_end, b_end)
    return max(end - start, timedelta(0))


def _fmt_hours(td):
    minutes = int(td.total_seconds() // 60)
    return f"{minutes // 60}시간 {minutes % 60:02d}분"


def analyze_day(records, day, months, weight_kg=None):
    """day 날짜의 하루(0시~24시)를 분석해서 dict로 돌려준다."""
    day_start = datetime.combine(day, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    in_day = [r for r in records if day_start <= r.start < day_end]

    # ---- 수유 ----
    feeds = [r for r in in_day if r.kind in ("formula", "breast")]
    solids = [r for r in in_day if r.kind == "solid"]
    milk_ml = sum(r.amount or 0 for r in feeds)
    solid_ml = sum(r.amount or 0 for r in solids)
    gaps = [(b.start - a.start) for a, b in zip(feeds, feeds[1:])]
    avg_gap = sum(gaps, timedelta(0)) / len(gaps) if gaps else None
    max_gap = max(gaps) if gaps else None

    # ---- 수면: 하루 경계에 걸친 잠은 해당 날짜에 속한 부분만 센다 ----
    sleeps = [r for r in records if r.kind == "sleep" and r.end and r.end > day_start and r.start < day_end]
    total_sleep = timedelta(0)
    night_sleep = timedelta(0)
    night_windows = [
        (day_start - timedelta(days=1) + timedelta(hours=NIGHT_START_HOUR), day_start + timedelta(hours=NIGHT_END_HOUR)),
        (day_start + timedelta(hours=NIGHT_START_HOUR), day_start + timedelta(days=1, hours=NIGHT_END_HOUR)),
    ]
    for s in sleeps:
        total_sleep += _overlap(s.start, s.end, day_start, day_end)
        for ws, we in night_windows:
            night_sleep += _overlap(s.start, s.end, max(ws, day_start), min(we, day_end))
    day_sleep = total_sleep - night_sleep
    naps = [s for s in sleeps if NIGHT_END_HOUR <= s.start.hour < NIGHT_START_HOUR and s.start >= day_start]
    longest = max(sleeps, key=lambda s: s.end - s.start) if sleeps else None

    # 밤중 깬 횟수: 밤 시간대(0~7시)에 시작한 수유 횟수로 대략 추정
    night_feeds = [r for r in feeds if r.start.hour < NIGHT_END_HOUR]

    # ---- 기저귀 ----
    diapers = [r for r in in_day if r.kind == "diaper"]
    poo = [d for d in diapers if "대변" in d.memo or "poo" in d.memo.lower() or "응가" in d.memo]

    # ---- 평가 ----
    findings = []

    def judge(label, value, low, high, unit, fmt=lambda v: f"{v:.0f}"):
        if value < low:
            status = "부족"
        elif value > high:
            status = "많음"
        else:
            status = "적정"
        findings.append((label, status, f"{fmt(value)}{unit} (권장 {fmt(low)}~{fmt(high)}{unit})"))
        return status

    fc_low, fc_high = feeding_count_range(months)
    judge("수유 횟수", len(feeds), fc_low, fc_high, "회")
    if any(r.amount for r in feeds):
        ml_low, ml_high = milk_ml_range(months, weight_kg)
        judge("하루 수유량", milk_ml, ml_low, ml_high, "ml")
    sl_low, sl_high = sleep_range(months)
    judge("총 수면", total_sleep.total_seconds() / 3600, sl_low, sl_high, "시간", fmt=lambda v: f"{v:.1f}")
    if months < 4 or len(diapers) > 0:
        judge("기저귀(소변 포함)", len(diapers), 6 if months < 12 else 4, 12, "회")

    tips = []
    statuses = {label: status for label, status, _ in findings}
    if statuses.get("하루 수유량") == "부족" or statuses.get("수유 횟수") == "부족":
        tips.append("수유가 평소보다 적어요. 컨디션(열, 콧물, 이앓이)을 살펴보고, 며칠 계속되면 소아과 상담을 권해요.")
    if statuses.get("하루 수유량") == "많음":
        tips.append("수유량이 권장보다 많아요. 토하거나 배가 빵빵하면 1회량을 줄이고 간격을 조절해 보세요.")
    if statuses.get("총 수면") == "부족":
        tips.append("수면이 부족해요. 낮잠 시간을 확보하고, 잠들기 전 루틴(목욕-수유-소등)을 일정하게 해보세요.")
    if max_gap and max_gap > timedelta(hours=5) and months < 4:
        tips.append(f"수유 간격이 최대 {_fmt_hours(max_gap)}까지 벌어졌어요. 신생아는 3~4시간 이내 간격이 좋아요.")
    if months >= 6 and not solids:
        tips.append("6개월 이후인데 오늘 이유식 기록이 없어요.")
    if night_sleep and longest and (longest.end - longest.start) >= timedelta(hours=5):
        tips.append(f"한 번에 {_fmt_hours(longest.end - longest.start)} 동안 길게 자서 통잠이 잘 잡혀가고 있어요. 👍")
    if not tips:
        tips.append("오늘은 전반적으로 안정적인 하루였어요.")

    return {
        "date": day,
        "months": months,
        "feed_count": len(feeds),
        "milk_ml": milk_ml,
        "solid_count": len(solids),
        "solid_ml": solid_ml,
        "avg_gap": avg_gap,
        "max_gap": max_gap,
        "night_feeds": len(night_feeds),
        "total_sleep": total_sleep,
        "night_sleep": night_sleep,
        "day_sleep": day_sleep,
        "nap_count": len(naps),
        "longest_sleep": (longest.end - longest.start) if longest else None,
        "longest_sleep_at": longest.start if longest else None,
        "diaper_count": len(diapers),
        "poo_count": len(poo),
        "findings": findings,
        "tips": tips,
        "feeds": feeds + solids,
        "sleeps": sleeps,
    }


def score(result):
    """적정 항목 비율로 0~100점을 매긴다."""
    if not result["findings"]:
        return None
    ok = sum(1 for _, status, _ in result["findings"] if status == "적정")
    return round(ok / len(result["findings"]) * 100)


def analyze_week(records, end_day, months, weight_kg=None, days=7):
    return [analyze_day(records, end_day - timedelta(days=i), months, weight_kg) for i in reversed(range(days))]


# ---------------------------------------------------------------------------
# 출력
# ---------------------------------------------------------------------------

STATUS_ICON = {"적정": "✅", "부족": "⚠️", "많음": "⚠️"}


def text_report(r, week=None):
    lines = [
        f"===== {r['date']} 하루 리포트 (생후 {r['months']}개월) =====",
        f"종합 점수: {score(r)}점",
        "",
        "[수유]",
        f"  분유/모유 {r['feed_count']}회, 총 {r['milk_ml']:.0f}ml",
    ]
    if r["avg_gap"]:
        lines.append(f"  평균 간격 {_fmt_hours(r['avg_gap'])}, 최대 간격 {_fmt_hours(r['max_gap'])}")
    if r["solid_count"]:
        lines.append(f"  이유식 {r['solid_count']}회, {r['solid_ml']:.0f}ml(g)")
    lines.append(f"  밤중 수유(0~7시) {r['night_feeds']}회")
    lines += [
        "",
        "[수면]",
        f"  총 {_fmt_hours(r['total_sleep'])} (밤잠 {_fmt_hours(r['night_sleep'])} / 낮잠 {_fmt_hours(r['day_sleep'])}, 낮잠 {r['nap_count']}회)",
    ]
    if r["longest_sleep"]:
        lines.append(f"  가장 긴 잠 {_fmt_hours(r['longest_sleep'])} ({r['longest_sleep_at']:%m/%d %H:%M} 시작)")
    lines += ["", "[기저귀]", f"  {r['diaper_count']}회 (대변 {r['poo_count']}회)", "", "[평가]"]
    for label, status, detail in r["findings"]:
        lines.append(f"  {STATUS_ICON[status]} {label}: {status} - {detail}")
    lines += ["", "[한 줄 코멘트]"] + [f"  - {t}" for t in r["tips"]]

    if week:
        lines += ["", "[최근 7일 추이]", "  날짜        수유량   수유  수면시간   점수"]
        for w in week:
            if not w["feed_count"]:
                lines.append(f"  {w['date']}  (기록 부족)")
                continue
            lines.append(
                f"  {w['date']}  {w['milk_ml']:5.0f}ml  {w['feed_count']:2d}회  {w['total_sleep'].total_seconds() / 3600:5.1f}h  {score(w)}점"
            )
    lines += ["", "※ 일반 권장 범위와 비교한 참고용 분석입니다. 의학적 판단은 소아과와 상담하세요."]
    return "\n".join(lines)


def html_report(r, week=None):
    """휴대폰에서 보기 좋은 단일 HTML 리포트 (24시간 타임라인 포함)."""
    esc = html.escape
    day_start = datetime.combine(r["date"], datetime.min.time())
    day_end = day_start + timedelta(days=1)

    def pct(t):
        t = min(max(t, day_start), day_end)
        return (t - day_start).total_seconds() / 864

    bars = []
    for s in r["sleeps"]:
        left, right = pct(s.start), pct(s.end)
        bars.append(f'<div class="bar sleep" style="left:{left:.2f}%;width:{max(right - left, 0.4):.2f}%"></div>')
    for f in r["feeds"]:
        cls = "solid" if f.kind == "solid" else "feed"
        bars.append(f'<div class="dot {cls}" style="left:{pct(f.start):.2f}%" title="{f.start:%H:%M} {f.amount or ""}ml"></div>')

    findings = "".join(
        f'<li class="{ "ok" if s == "적정" else "warn" }"><b>{esc(l)}</b> {esc(s)}<span>{esc(d)}</span></li>'
        for l, s, d in r["findings"]
    )
    tips = "".join(f"<li>{esc(t)}</li>" for t in r["tips"])

    week_html = ""
    if week:
        max_ml = max((w["milk_ml"] for w in week), default=0) or 1
        max_sleep = max((w["total_sleep"].total_seconds() for w in week), default=0) or 1
        rows = "".join(
            f'<tr><td>{w["date"]:%m/%d}</td>'
            f'<td><div class="h milk" style="width:{w["milk_ml"] / max_ml * 100:.0f}%"></div>{w["milk_ml"]:.0f}ml</td>'
            f'<td><div class="h sl" style="width:{w["total_sleep"].total_seconds() / max_sleep * 100:.0f}%"></div>'
            f'{w["total_sleep"].total_seconds() / 3600:.1f}h</td></tr>'
            for w in week
            if w["feed_count"]
        )
        week_html = f'<section><h2>최근 7일</h2><table><tr><th></th><th>수유량</th><th>수면</th></tr>{rows}</table></section>'

    gap = _fmt_hours(r["avg_gap"]) if r["avg_gap"] else "-"
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>아기 하루 리포트</title>
<style>
:root{{--bg:#fffaf5;--card:#fff;--fg:#2d2a26;--mute:#8a8178;--sleep:#7c8cf0;--feed:#f2994a;--solid:#6fcf97;--warn:#eb5757}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1d1b19;--card:#2a2724;--fg:#f2ede8;--mute:#a59d94}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}}
main{{max-width:560px;margin:auto;padding:16px}} section{{background:var(--card);border-radius:16px;padding:16px;margin:12px 0}}
h1{{font-size:20px;margin:8px 0}} h2{{font-size:15px;margin:0 0 10px;color:var(--mute)}}
.score{{font-size:44px;font-weight:700}} .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center}}
.grid b{{display:block;font-size:20px}} .grid small{{color:var(--mute)}}
.tl{{position:relative;height:36px;background:rgba(128,128,128,.12);border-radius:8px;overflow:hidden}}
.bar{{position:absolute;top:0;bottom:0}} .sleep{{background:var(--sleep)}}
.dot{{position:absolute;top:12px;width:12px;height:12px;margin-left:-6px;border-radius:50%;border:2px solid var(--card)}}
.feed{{background:var(--feed)}} .solid{{background:var(--solid)}}
.ticks{{display:flex;justify-content:space-between;font-size:11px;color:var(--mute);margin-top:4px}}
.legend{{font-size:12px;color:var(--mute);margin-top:8px}} .legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 10px}}
ul{{padding:0;margin:0;list-style:none}} li{{padding:8px 0;border-bottom:1px solid rgba(128,128,128,.15)}}
li span{{display:block;font-size:13px;color:var(--mute)}} li.warn b{{color:var(--warn)}}
table{{width:100%;font-size:13px;border-collapse:collapse}} td{{padding:4px;white-space:nowrap}}
.h{{height:8px;border-radius:4px;margin-bottom:2px}} .milk{{background:var(--feed)}} .sl{{background:var(--sleep)}}
footer{{font-size:12px;color:var(--mute);text-align:center;padding:8px}}
</style></head><body><main>
<h1>{r['date']:%Y년 %m월 %d일} · 생후 {r['months']}개월</h1>
<section><h2>오늘 종합 점수</h2><div class="score">{score(r)}점</div></section>
<section class="grid">
<div><b>{r['milk_ml']:.0f}ml</b><small>수유 {r['feed_count']}회</small></div>
<div><b>{r['total_sleep'].total_seconds() / 3600:.1f}h</b><small>총 수면</small></div>
<div><b>{r['diaper_count']}회</b><small>기저귀</small></div>
<div><b>{gap}</b><small>평균 수유간격</small></div>
<div><b>{r['night_sleep'].total_seconds() / 3600:.1f}h</b><small>밤잠</small></div>
<div><b>{r['nap_count']}회</b><small>낮잠</small></div>
</section>
<section><h2>24시간 타임라인</h2><div class="tl">{''.join(bars)}</div>
<div class="ticks"><span>0시</span><span>6시</span><span>12시</span><span>18시</span><span>24시</span></div>
<div class="legend"><i style="background:var(--sleep)"></i>수면<i style="background:var(--feed)"></i>수유<i style="background:var(--solid)"></i>이유식</div></section>
<section><h2>평가</h2><ul>{findings}</ul></section>
<section><h2>코멘트</h2><ul>{tips}</ul></section>
{week_html}
<footer>일반 권장 범위와 비교한 참고용 분석입니다. 의학적 판단은 소아과와 상담하세요.</footer>
</main></body></html>"""


def main():
    p = argparse.ArgumentParser(description="베이비타임 기록 CSV 분석기")
    p.add_argument("csv", help="베이비타임에서 내보낸 CSV 파일")
    p.add_argument("--months", type=int, required=True, help="아기 월령 (개월)")
    p.add_argument("--weight", type=float, help="아기 체중 kg (수유량 권장치 계산에 사용)")
    p.add_argument("--date", help="분석할 날짜 YYYY-MM-DD (기본: 기록의 마지막 날)")
    p.add_argument("--html", help="HTML 리포트 저장 경로")
    args = p.parse_args()

    records = load_records(args.csv)
    if not records:
        raise SystemExit("읽을 수 있는 기록이 없습니다.")
    day = date.fromisoformat(args.date) if args.date else max(
        r.start.date() for r in records if r.kind != "sleep" or r.start.hour >= NIGHT_END_HOUR
    )

    result = analyze_day(records, day, args.months, args.weight)
    week = analyze_week(records, day, args.months, args.weight)
    print(text_report(result, week))
    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(html_report(result, week))
        print(f"\nHTML 리포트 저장: {args.html}")


if __name__ == "__main__":
    main()
