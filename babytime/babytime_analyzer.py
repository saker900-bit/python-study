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
    label: str = ""  # 앱에 적힌 원래 기록 종류 (예: 밤잠, 낮잠, 목욕)


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


# 베이비타임 앱의 "기록 내보내기" 텍스트 형식:
#   2026-10-01 01:05 AM ~ 2026-10-01 01:13 AM
#   기록 종류: 분유
#   분유 총 양(ml): 245 (ml)
#   ====================
def parse_babytime_text(text):
    records = []
    for block in text.replace("\r", "").split("===================="):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        times = [t.strip() for t in lines[0].split("~")]
        try:
            start = datetime.strptime(times[0], "%Y-%m-%d %I:%M %p")
            end = datetime.strptime(times[1], "%Y-%m-%d %I:%M %p") if len(times) > 1 else None
        except ValueError:
            continue
        fields = {}
        for line in lines[1:]:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
        label = fields.get("기록 종류", "")
        kind = _normalize_type(label) or "etc"
        amount = None
        for key, value in fields.items():
            if "(ml)" in key or key in ("양", "용량"):
                amount = _parse_amount(value.replace("(ml)", ""))
        if label == "병원":
            memo = fields.get("방문사유") or fields.get("방문유형", "")
        elif kind == "diaper":
            # "둘다"는 소변+대변이라 대변으로도 센다
            memo = fields.get("배변 형태", "")
            memo = memo + " 대변" if memo == "둘다" else memo
        else:
            detail = [v for k, v in fields.items() if k not in ("기록 종류", "소요시간") and "(ml)" not in k and k != "image"]
            memo = ", ".join(detail)
        records.append(Record(kind, start, end, amount, memo, label))
    records.sort(key=lambda r: r.start)
    return records


def load_any(path):
    """CSV, 베이비타임 텍스트(.txt), 또는 베이비타임 내보내기 zip을 읽는다."""
    if path.lower().endswith(".zip"):
        import zipfile

        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".txt")]
            if not names:
                raise SystemExit("zip 안에 .txt 기록 파일이 없습니다.")
            return parse_babytime_text(z.read(names[0]).decode("utf-8-sig"))
    with open(path, encoding="utf-8-sig") as f:
        head = f.read(64)
    if head[:4].isdigit() and "기록 종류" in open(path, encoding="utf-8-sig").read(500):
        return parse_babytime_text(open(path, encoding="utf-8-sig").read())
    return load_records(path)


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
    # 앱이 낮잠/밤잠을 구분해 주면 그걸 쓰고, 아니면 시간대(19시~7시)로 나눈다
    labeled = any(s.label in ("낮잠", "밤잠") for s in sleeps)
    for s in sleeps:
        part = _overlap(s.start, s.end, day_start, day_end)
        total_sleep += part
        if labeled:
            night_sleep += part if s.label == "밤잠" else timedelta(0)
        else:
            for ws, we in night_windows:
                night_sleep += _overlap(s.start, s.end, max(ws, day_start), min(we, day_end))
    day_sleep = total_sleep - night_sleep
    if labeled:
        naps = [s for s in sleeps if s.label == "낮잠" and s.start >= day_start]
    else:
        naps = [s for s in sleeps if NIGHT_END_HOUR <= s.start.hour < NIGHT_START_HOUR and s.start >= day_start]
    started = [s for s in sleeps if s.start >= day_start] or sleeps
    longest = max(started, key=lambda s: s.end - s.start) if started else None

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

    if any(r.amount for r in feeds):
        # 양 기록이 있으면 총량으로 평가한다 (1회량이 크면 횟수가 적어도 괜찮다)
        ml_low, ml_high = milk_ml_range(months, weight_kg)
        judge("하루 수유량", milk_ml, ml_low, ml_high, "ml")
    else:
        fc_low, fc_high = feeding_count_range(months)
        judge("수유 횟수", len(feeds), fc_low, fc_high, "회")
    sl_low, sl_high = sleep_range(months)
    judge("총 수면", total_sleep.total_seconds() / 3600, sl_low, sl_high, "시간", fmt=lambda v: f"{v:.1f}")
    if months < 4 or len(diapers) > 0:
        low = 6 if months < 12 else 4
        status = "적정" if len(diapers) >= low else "부족"
        findings.append(("기저귀", status, f"{len(diapers)}회 (하루 {low}회 이상이면 충분)"))

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


def _avg(values):
    values = list(values)
    return sum(values) / len(values) if values else 0


def _avg_clock(times, pivot_hour=12):
    """시각들의 평균 (자정을 넘나드는 취침 시각도 처리하도록 pivot 기준으로 펼침)."""
    if not times:
        return None
    mins = [(t.hour * 60 + t.minute - pivot_hour * 60) % 1440 for t in times]
    m = (round(_avg(mins)) + pivot_hour * 60) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def _count(items):
    counts = {}
    for x in items:
        counts[x] = counts.get(x, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])


def _sick_compare(days, visit_dates):
    """병원 간 날 앞뒤 하루씩을 '아픈 기간'으로 보고 평소와 비교한다."""
    if not visit_dates:
        return None
    sick_days = {v + timedelta(days=k) for v in visit_dates for k in (-1, 0, 1)}
    sick = [d for d in days if d["date"] in sick_days]
    normal = [d for d in days if d["date"] not in sick_days]
    if not sick or not normal:
        return None
    h = lambda ds: _avg(d["total_sleep"].total_seconds() / 3600 for d in ds)
    m = lambda ds: _avg(d["milk_ml"] for d in ds)
    return {"sick_sleep": h(sick), "normal_sleep": h(normal), "sick_milk": m(sick), "normal_milk": m(normal), "n": len(sick)}


def analyze_period(records, months, weight_kg=None):
    """기록 전체 기간을 날짜별로 분석하고 한 달 종합 요약을 만든다."""
    first, last = records[0].start.date(), records[-1].start.date()
    days = [analyze_day(records, first + timedelta(days=i), months, weight_kg) for i in range((last - first).days + 1)]
    days = [d for d in days if d["feed_count"]]  # 수유 기록이 없는 날은 기록 누락으로 보고 뺀다

    def stats(ds):
        return {
            "milk": _avg(d["milk_ml"] for d in ds),
            "feeds": _avg(d["feed_count"] for d in ds),
            "sleep": _avg(d["total_sleep"].total_seconds() / 3600 for d in ds),
            "night": _avg(d["night_sleep"].total_seconds() / 3600 for d in ds),
            "nap": _avg(d["day_sleep"].total_seconds() / 3600 for d in ds),
            "naps": _avg(d["nap_count"] for d in ds),
            "longest": _avg(d["longest_sleep"].total_seconds() / 3600 for d in ds if d["longest_sleep"]),
            "diapers": _avg(d["diaper_count"] for d in ds),
            "score": _avg(score(d) for d in ds),
        }

    feeds = [r for r in records if r.kind in ("formula", "breast") and r.amount]
    nights = [r for r in records if r.kind == "sleep" and r.label == "밤잠" and r.end]
    # 취침: 저녁 6시 이후 시작한 밤잠, 기상: 오전(4~11시)에 끝난 밤잠 중 그날 마지막
    bedtimes, wakes = {}, {}
    for s in nights:
        if s.start.hour >= 18:
            bedtimes.setdefault(s.start.date(), s.start)
        if 4 <= s.end.hour < 12:
            wakes[s.end.date()] = s.end
    etc = [r for r in records if r.kind == "etc"]
    etc_counts = {}
    for r in etc:
        etc_counts[r.label] = etc_counts.get(r.label, 0) + 1

    week = 7 if len(days) >= 14 else max(len(days) // 2, 1)
    return {
        "first": first,
        "last": last,
        "days": days,
        "all": stats(days),
        "early": stats(days[:week]),
        "late": stats(days[-week:]),
        "trend_days": week,
        "per_feed_ml": _avg(r.amount for r in feeds),
        "max_feed_ml": max((r.amount for r in feeds), default=0),
        "bedtime": _avg_clock(list(bedtimes.values())),
        "wake": _avg_clock(list(wakes.values()), pivot_hour=0),
        "poo_days": sum(1 for d in days if d["poo_count"]),
        "etc_counts": etc_counts,
        "hospital": [r for r in etc if r.label == "병원"],
        "notes": [r for r in etc if r.label in ("기타", "기록A") and r.memo and r.memo != "산책"],
        "custom_counts": _count(r.memo for r in etc if r.label == "기록A" and r.memo),
        "med_counts": _count(m.strip() for r in etc if r.label == "투약" for m in r.memo.split(",") if m.strip()),
        "sick": _sick_compare(days, [r.start.date() for r in etc if r.label == "병원"]),
        "meds": [r for r in etc if r.label == "투약"],
        "low_milk": sorted(days, key=lambda d: d["milk_ml"])[:3],
        "low_sleep": sorted(days, key=lambda d: d["total_sleep"])[:3],
    }


def _trend(early, late, unit, fmt="{:.0f}"):
    diff = late - early
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "="
    return f"{fmt.format(early)}{unit} → {fmt.format(late)}{unit} ({arrow}{fmt.format(abs(diff))})"


def period_comments(p, months, weight_kg=None):
    a, e, l = p["all"], p["early"], p["late"]
    out = []
    ml_low, ml_high = milk_ml_range(months, weight_kg)
    if a["milk"] < ml_low:
        out.append(f"하루 평균 수유량 {a['milk']:.0f}ml로 권장({ml_low}~{ml_high}ml)보다 조금 적어요.")
    elif a["milk"] > ml_high:
        out.append(f"하루 평균 수유량 {a['milk']:.0f}ml로 권장({ml_low}~{ml_high}ml)보다 많은 편이에요. 1회량이 많지 않은지 봐주세요.")
    else:
        out.append(f"하루 평균 수유량 {a['milk']:.0f}ml로 권장 범위({ml_low}~{ml_high}ml) 안이에요. 잘 먹고 있어요. 👍")
    sl_low, sl_high = sleep_range(months)
    if a["sleep"] < sl_low:
        out.append(f"하루 평균 수면 {a['sleep']:.1f}시간으로 권장({sl_low}~{sl_high}시간)보다 짧게 기록됐어요. 기록이 빠진 잠이 있는지도 확인해 보세요.")
    else:
        out.append(f"하루 평균 수면 {a['sleep']:.1f}시간으로 권장 범위({sl_low}~{sl_high}시간) 안이에요.")
    if l["longest"] - e["longest"] >= 0.5:
        out.append(f"가장 길게 이어 잔 시간이 월초 {e['longest']:.1f}시간 → 월말 {l['longest']:.1f}시간으로 늘었어요. 통잠이 자리 잡는 중이에요.")
    elif e["longest"] - l["longest"] >= 0.5:
        out.append(f"가장 길게 이어 잔 시간이 월초보다 줄었어요({e['longest']:.1f} → {l['longest']:.1f}시간). 감기·이앓이·뒤집기 같은 발달 시기에 흔히 그래요.")
    if abs(l["milk"] - e["milk"]) >= 80:
        word = "늘었어요" if l["milk"] > e["milk"] else "줄었어요"
        out.append(f"월말 수유량이 월초보다 {abs(l['milk'] - e['milk']):.0f}ml {word}.")
    sick = p["sick"]
    if sick:
        msg = (f"병원 다녀온 날 전후({sick['n']}일)엔 평균 수면 {sick['sick_sleep']:.1f}시간, 수유 {sick['sick_milk']:.0f}ml로 "
               f"평소({sick['normal_sleep']:.1f}시간, {sick['normal_milk']:.0f}ml)")
        if sick["normal_sleep"] - sick["sick_sleep"] >= 0.5 or sick["normal_milk"] - sick["sick_milk"] >= 50:
            msg += "보다 줄었어요. 감기 때문에 잠·식사가 흔들린 걸로 보여요."
        else:
            msg += "와 큰 차이가 없어요. 아플 때도 잘 버텨줬네요."
        out.append(msg)
    return out


def period_text(p, months, weight_kg=None):
    a, e, l = p["all"], p["early"], p["late"]
    n = p["trend_days"]
    lines = [
        f"===== {p['first']} ~ {p['last']} 종합 분석 (생후 {months:g}개월 기준, {len(p['days'])}일) =====",
        "",
        "[먹기]",
        f"  하루 평균 {a['milk']:.0f}ml / {a['feeds']:.1f}회, 1회 평균 {p['per_feed_ml']:.0f}ml (최대 {p['max_feed_ml']:.0f}ml)",
        f"  첫 {n}일 → 마지막 {n}일: {_trend(e['milk'], l['milk'], 'ml')}",
        "",
        "[잠]",
        f"  하루 평균 {a['sleep']:.1f}시간 (밤잠 {a['night']:.1f}h + 낮잠 {a['nap']:.1f}h, 낮잠 {a['naps']:.1f}회)",
        f"  평균 취침 {p['bedtime'] or '-'}, 평균 기상 {p['wake'] or '-'}",
        f"  가장 길게 이어 잔 시간 평균 {a['longest']:.1f}시간",
        f"  첫 {n}일 → 마지막 {n}일: 총 수면 {_trend(e['sleep'], l['sleep'], 'h', '{:.1f}')}, 최장 수면 {_trend(e['longest'], l['longest'], 'h', '{:.1f}')}",
        "",
        "[기저귀]",
        f"  하루 평균 {a['diapers']:.1f}회, 대변 본 날 {p['poo_days']}/{len(p['days'])}일",
        "",
        "[그 밖의 기록]",
        "  " + ", ".join(f"{k} {v}회" for k, v in sorted(p["etc_counts"].items(), key=lambda kv: -kv[1])),
    ]
    if p["med_counts"]:
        lines.append("  투약 내역: " + ", ".join(f"{k} {v}회" for k, v in p["med_counts"][:4]))
    if p["custom_counts"]:
        lines.append("  기록A: " + ", ".join(f"{k} {v}회" for k, v in p["custom_counts"][:3]))
    for h in p["hospital"]:
        lines.append(f"  - {h.start:%m/%d} 병원: {h.memo}")
    for note in p["notes"]:
        lines.append(f"  - {note.start:%m/%d} {note.memo}")
    lines += ["", "[덜 먹은 날 / 덜 잔 날]"]
    lines.append("  수유량 적은 날: " + ", ".join(f"{d['date']:%m/%d}({d['milk_ml']:.0f}ml)" for d in p["low_milk"]))
    lines.append("  수면 짧은 날: " + ", ".join(f"{d['date']:%m/%d}({d['total_sleep'].total_seconds() / 3600:.1f}h)" for d in p["low_sleep"]))
    lines += ["", "[종합 코멘트]"] + [f"  - {c}" for c in period_comments(p, months, weight_kg)]
    lines += ["", "[날짜별]", "  날짜    수유량  횟수  총수면  밤잠  낮잠  최장  기저귀  점수"]
    for d in p["days"]:
        h = lambda td: td.total_seconds() / 3600 if td else 0
        lines.append(
            f"  {d['date']:%m/%d}  {d['milk_ml']:5.0f}ml  {d['feed_count']:2d}회  {h(d['total_sleep']):5.1f}h  "
            f"{h(d['night_sleep']):4.1f}  {h(d['day_sleep']):4.1f}  {h(d['longest_sleep']):4.1f}  {d['diaper_count']:4d}회  {score(d):3d}점"
        )
    lines += ["", "※ 일반 권장 범위와 비교한 참고용 분석입니다. 의학적 판단은 소아과와 상담하세요."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 출력
# ---------------------------------------------------------------------------

STATUS_ICON = {"적정": "✅", "부족": "⚠️", "많음": "⚠️"}


def text_report(r, week=None):
    lines = [
        f"===== {r['date']} 하루 리포트 (생후 {r['months']:g}개월) =====",
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


_CSS = """<style>
:root{--bg:#fffaf5;--card:#fff;--fg:#2d2a26;--mute:#8a8178;--sleep:#7c8cf0;--feed:#f2994a;--solid:#6fcf97;--warn:#eb5757}
@media (prefers-color-scheme:dark){:root{--bg:#1d1b19;--card:#2a2724;--fg:#f2ede8;--mute:#a59d94}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
main{max-width:560px;margin:auto;padding:16px} section{background:var(--card);border-radius:16px;padding:16px;margin:12px 0}
h1{font-size:20px;margin:8px 0} h2{font-size:15px;margin:0 0 10px;color:var(--mute)}
.score{font-size:44px;font-weight:700} .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center}
.grid b{display:block;font-size:20px} .grid small{color:var(--mute)}
.tl{position:relative;height:36px;background:rgba(128,128,128,.12);border-radius:8px;overflow:hidden}
.bar{position:absolute;top:0;bottom:0} .sleep{background:var(--sleep)}
.dot{position:absolute;top:12px;width:12px;height:12px;margin-left:-6px;border-radius:50%;border:2px solid var(--card)}
.feed{background:var(--feed)} .solid{background:var(--solid)}
.ticks{display:flex;justify-content:space-between;font-size:11px;color:var(--mute);margin-top:4px}
.legend{font-size:12px;color:var(--mute);margin-top:8px} .legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 10px}
ul{padding:0;margin:0;list-style:none} li{padding:8px 0;border-bottom:1px solid rgba(128,128,128,.15)}
li span{display:block;font-size:13px;color:var(--mute)} li.warn b{color:var(--warn)}
table{width:100%;font-size:13px;border-collapse:collapse} td{padding:4px;white-space:nowrap}
.h{height:8px;border-radius:4px;margin-bottom:2px} .milk{background:var(--feed)} .sl{background:var(--sleep)}
footer{font-size:12px;color:var(--mute);text-align:center;padding:8px}
</style>"""


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
{_CSS}</head><body><main>
<h1>{r['date']:%Y년 %m월 %d일} · 생후 {r['months']:g}개월</h1>
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


def _timeline(d):
    day_start = datetime.combine(d["date"], datetime.min.time())
    day_end = day_start + timedelta(days=1)

    def pct(t):
        return (min(max(t, day_start), day_end) - day_start).total_seconds() / 864

    parts = []
    for s in d["sleeps"]:
        cls = "sleep" if s.label != "낮잠" else "sleep nap"
        parts.append(f'<div class="bar {cls}" style="left:{pct(s.start):.2f}%;width:{max(pct(s.end) - pct(s.start), 0.3):.2f}%"></div>')
    for f in d["feeds"]:
        parts.append(f'<div class="tick" style="left:{pct(f.start):.2f}%"></div>')
    return "".join(parts)


def html_period(p, months, weight_kg=None):
    """한 달 종합 리포트 HTML (날짜별 24시간 수면 타임라인 포함)."""
    esc = html.escape
    a, e, l = p["all"], p["early"], p["late"]
    n = p["trend_days"]
    comments = "".join(f"<li>{esc(c)}</li>" for c in period_comments(p, months, weight_kg))
    rows = "".join(
        f'<div class="row"><span>{d["date"]:%m/%d}</span><div class="tl small">{_timeline(d)}</div></div>'
        for d in p["days"]
    )
    max_ml = max(d["milk_ml"] for d in p["days"]) or 1
    max_sl = max(d["total_sleep"].total_seconds() for d in p["days"]) or 1
    table = "".join(
        f'<tr><td>{d["date"]:%m/%d}</td>'
        f'<td><div class="h milk" style="width:{d["milk_ml"] / max_ml * 100:.0f}%"></div>{d["milk_ml"]:.0f}ml · {d["feed_count"]}회</td>'
        f'<td><div class="h sl" style="width:{d["total_sleep"].total_seconds() / max_sl * 100:.0f}%"></div>'
        f'{d["total_sleep"].total_seconds() / 3600:.1f}h</td></tr>'
        for d in p["days"]
    )
    events = "".join(f"<li><b>{h.start:%m/%d} 병원</b><span>{esc(h.memo)}</span></li>" for h in p["hospital"])
    events += "".join(f"<li><b>{x.start:%m/%d}</b><span>{esc(x.memo)}</span></li>" for x in p["notes"])
    etc = " · ".join(f"{esc(k)} {v}회" for k, v in sorted(p["etc_counts"].items(), key=lambda kv: -kv[1]))
    if p["med_counts"]:
        etc += "<br><small>투약: " + esc(", ".join(f"{k} {v}회" for k, v in p["med_counts"][:4])) + "</small>"

    def trend_li(label, ev, lv, unit, fmt="{:.0f}"):
        return f"<li><b>{label}</b><span>{_trend(ev, lv, unit, fmt)}</span></li>"

    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>아기 월간 리포트</title>
{_CSS}<style>
.row{{display:flex;align-items:center;gap:8px;margin:3px 0}} .row span{{font-size:11px;color:var(--mute);width:34px}}
.tl.small{{flex:1;height:14px;border-radius:4px}} .nap{{opacity:.55}}
.tick{{position:absolute;top:0;bottom:0;width:2px;background:var(--feed)}}
.grid{{grid-template-columns:repeat(3,1fr)}}
</style></head><body><main>
<h1>{p['first']:%Y.%m.%d} ~ {p['last']:%m.%d} 종합 분석</h1>
<p style="color:var(--mute);margin:0 0 4px">생후 {months:g}개월 기준 · {len(p['days'])}일 기록</p>
<section class="grid">
<div><b>{a['milk']:.0f}ml</b><small>하루 수유량</small></div>
<div><b>{a['feeds']:.1f}회</b><small>하루 수유</small></div>
<div><b>{p['per_feed_ml']:.0f}ml</b><small>1회 평균</small></div>
<div><b>{a['sleep']:.1f}h</b><small>하루 수면</small></div>
<div><b>{a['night']:.1f}h</b><small>밤잠</small></div>
<div><b>{a['nap']:.1f}h</b><small>낮잠 {a['naps']:.1f}회</small></div>
<div><b>{p['bedtime'] or '-'}</b><small>평균 취침</small></div>
<div><b>{p['wake'] or '-'}</b><small>평균 기상</small></div>
<div><b>{a['longest']:.1f}h</b><small>최장 연속 수면</small></div>
</section>
<section><h2>종합 코멘트</h2><ul>{comments}</ul></section>
<section><h2>첫 {n}일 → 마지막 {n}일</h2><ul>
{trend_li("하루 수유량", e['milk'], l['milk'], "ml")}
{trend_li("하루 수면", e['sleep'], l['sleep'], "h", "{:.1f}")}
{trend_li("밤잠", e['night'], l['night'], "h", "{:.1f}")}
{trend_li("최장 연속 수면", e['longest'], l['longest'], "h", "{:.1f}")}
</ul></section>
<section><h2>날짜별 수면 패턴 (0시 → 24시)</h2>{rows}
<div class="ticks" style="margin-left:42px"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>
<div class="legend"><i style="background:var(--sleep)"></i>밤잠<i style="background:var(--sleep);opacity:.55"></i>낮잠<i style="background:var(--feed);border-radius:0;width:3px"></i>수유</div></section>
<section><h2>날짜별 먹기·잠</h2><table><tr><th></th><th>수유</th><th>수면</th></tr>{table}</table></section>
<section><h2>그 밖의 기록</h2><p style="margin:0 0 8px">{etc}</p><ul>{events}</ul>
<p style="font-size:13px;color:var(--mute)">기저귀 하루 {a['diapers']:.1f}회 · 대변 본 날 {p['poo_days']}/{len(p['days'])}일</p></section>
<footer>일반 권장 범위와 비교한 참고용 분석입니다. 의학적 판단은 소아과와 상담하세요.</footer>
</main></body></html>"""


def main():
    p = argparse.ArgumentParser(description="베이비타임 기록 분석기")
    p.add_argument("csv", help="베이비타임 내보내기 파일 (.zip / .txt) 또는 CSV")
    p.add_argument("--months", type=float, required=True, help="아기 월령 (개월, 5.5처럼 소수 가능)")
    p.add_argument("--weight", type=float, help="아기 체중 kg (수유량 권장치 계산에 사용)")
    p.add_argument("--date", help="하루만 분석할 날짜 YYYY-MM-DD (없으면 기간 전체 종합 분석)")
    p.add_argument("--html", help="HTML 리포트 저장 경로")
    args = p.parse_args()

    records = load_any(args.csv)
    if not records:
        raise SystemExit("읽을 수 있는 기록이 없습니다.")

    span = (records[-1].start.date() - records[0].start.date()).days + 1
    if not args.date and span >= 3:
        period = analyze_period(records, args.months, args.weight)
        print(period_text(period, args.months, args.weight))
        if args.html:
            with open(args.html, "w", encoding="utf-8") as f:
                f.write(html_period(period, args.months, args.weight))
            print(f"\nHTML 리포트 저장: {args.html}")
        return

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
