# 매일 새벽 밈 도감 업데이트 (예약 작업용 절차)

목표: 새로 유행하는 밈, 특히 **한국 밈**을 찾아서 도감(`catalog.json`)에 없으면 짤과 함께 추가한다.
유행에 뒤처지지 않는 게 핵심. 대신 **엉뚱한 짤을 넣는 것보다 안 넣는 게 낫다.**

## 0. 준비

- 저장소: `saker900-bit/python-study`, 브랜치 `ccr-d54495c0-z05krj`, 폴더 `memes/`
- 필요 도구: Python 3, Pillow, curl. Tenor(`tenor.com`, `media.tenor.com`) 접속이 돼야 한다.

## 1. 새 밈 찾기

웹 검색으로 최근 유행 밈을 모은다. 한국 쪽을 먼저, 많이 본다. 예시 검색어:

- "요즘 유행하는 밈", "최신 밈 정리 {이번 달}", "{올해} 유행어", "인스타 릴스 유행 밈", "틱톡 챌린지 유행",
  "디시 유행어", "커뮤니티 밈 모음", "나무위키 밈 최근", "유튜브 쇼츠 밈"
- 예능, 드라마, 영화, 스트리머, 스포츠, 뉴스에서 나온 장면 짤
- 해외: "trending memes this week", "new meme templates", "know your meme trending"

`catalog.json` 의 `id`, `name` 과 비교해서 **없는 것만** 후보로 남긴다. 하루 목표는 새 밈 5~20개.

## 2. 짤 후보 받기

```bash
cd memes
python tools/candidates.py '{"영문_id": "테너 검색어", ...}'
```

- id는 영문 소문자와 밑줄 (`kkanbu`, `muyaho` 처럼).
- 검색어는 한국어 키워드가 잘 걸린다 (인물 이름, 대사, 프로그램 이름). 안 나오면 다른 검색어로 다시.
- `cand/sheet_*.jpg` 를 **직접 열어서 눈으로 확인**한다. 태그만 믿지 말 것.
  해당 밈이 확실히 보이는 후보만 고른다. 없으면 그 밈은 건너뛴다.

## 3. 도감에 추가

`new_memes.json` 을 만들고:

```json
[{"id": "...", "pick": 0, "name": "...", "quote": "...", "source": "...", "desc": "...", "region": "ko"}]
```

- `quote`: 짤 속 대사/자막. 대사가 없으면 괄호로 동작 설명, 예: `"(고개 끄덕)"`
- `source`: 출처 (프로그램/영화/인물). **확실하지 않은 사실은 쓰지 않는다.** 모르면 더 일반적으로.
- `desc`: 어떤 장면이고 언제 쓰는지 두 문장 이내.

```bash
python tools/add_meme.py new_memes.json
rm new_memes.json
```

## 4. 앱 화면 다시 만들고 아티팩트 갱신

```bash
python tools/build.py artifact
```

`site/files.json` 목록으로 Claude 아티팩트를 다시 올린다 (아티팩트 도구가 있을 때):

- slug: `e0d5afdc-6247-4bee-80a9-a44980fb1e7a` (밈 탐정)
- `get_artifact` 로 현재 version을 받아 `base_version` 으로 쓰고, `publish_files` 에 `site/files.json` 내용을 그대로 넘긴다.
- 페이지가 쓰는 기능: `sample`, `downloads`. 이미 선언돼 있으니 다시 선언할 필요 없음.

## 5. 커밋, 푸시

```bash
git add memes/catalog.json
git commit -m "Add N new memes to catalog (YYYY-MM-DD)"
git push -u origin ccr-d54495c0-z05krj
```

`site/`, `cand/` 는 올리지 않는다 (.gitignore).

## 6. 마무리 보고

추가한 밈 이름 목록, 건너뛴 후보와 이유(짤 못 찾음 등)를 짧게 남긴다.
새 밈이 하나도 없으면 커밋하지 않고 "새 밈 없음"으로 끝낸다.
