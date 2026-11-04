# 베이비타임 기록 분석기

베이비타임에서 내보낸 기록(zip/txt) 또는 CSV를 읽어서 한 달 종합 분석과 하루 분석을 해줍니다.

## 베이비타임에서 기록 내보내기

베이비타임 앱의 기록 내보내기로 받은 `Activity_...zip` 파일을 그대로 넣으면 됩니다.
(zip 안의 `activity_이름_YYYYMM_asc.txt`를 읽습니다.)

```bash
# 한 달 종합 분석 (+ 휴대폰용 HTML)
python babytime_analyzer.py Activity_202610.zip --months 5 --html month.html

# 특정 하루만
python babytime_analyzer.py Activity_202610.zip --months 5 --date 2026-10-30
```

한 달 분석에는 하루 평균 수유량·수면, 취침/기상 시각, 최장 연속 수면 추이(월초 vs 월말),
날짜별 24시간 수면 패턴, 병원 간 날 전후 비교, 투약·목욕 등 기타 기록 요약이 들어갑니다.

- **수유**: 횟수, 총량(ml), 평균/최대 간격, 밤중 수유, 이유식
- **수면**: 총 수면, 밤잠/낮잠 비율, 낮잠 횟수, 가장 길게 잔 시간
- **기저귀**: 횟수, 대변 횟수
- **평가**: 월령(체중)별 일반 권장 범위와 비교 → 적정/부족/많음 + 종합 점수 + 코멘트
- **최근 7일 추이**, 휴대폰용 **HTML 리포트**(24시간 타임라인)

외부 라이브러리 없이 Python 3.10+ 표준 라이브러리만 씁니다.

## CSV로 쓰는 경우

```bash
python babytime_analyzer.py sample_babytime.csv --months 6 --weight 7.5
python babytime_analyzer.py 내기록.csv --months 6 --date 2026-11-04 --html report.html
```

## CSV 형식

열 이름은 한글/영어 모두 인식합니다. `종류`, `시작`은 필수입니다.

| 종류 | 시작 | 종료 | 양(ml) | 메모 |
|---|---|---|---|---|
| 분유 / 모유 / 이유식 / 수면 / 기저귀 | 2026-11-04 08:10 | 2026-11-04 08:25 | 140 | 대변 |

앱에서 내보낸 파일의 열 이름이 다르면 `COLUMN_ALIASES`, `TYPE_ALIASES`에 추가하면 됩니다.

> 일반 권장 범위와 비교한 참고용 분석이며 의학적 진단이 아닙니다.
