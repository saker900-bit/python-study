# 매일 새벽 밈 도감 업데이트 (예약 작업용 절차)

목표: 새로 유행하는 밈, 특히 **한국 밈**을 찾아서 도감(`catalog.json`)에 없으면 짤과 함께 추가한다.
유행에 뒤처지지 않는 게 핵심. 대신 **엉뚱한 짤을 넣는 것보다 안 넣는 게 낫다.**

## 돈 버는 앱이라 꼭 지킬 것

- 설명(`desc`)은 **직접 쓴다.** 나무위키 등 남의 글을 베끼지 않는다 (나무위키는 영리 이용 금지 라이선스).
- 대사(`quote`)는 짧게. 노래 가사는 한 소절 이하.
- **정치인, 정치 구호, 혐오·비하, 성적인 밈, 실제 사건 피해자를 조롱하는 밈은 넣지 않는다** (스토어 심사 거절, 광고 제한 위험).
- 사실이 불확실하면 출처를 일반적으로 쓴다 (예: "인터넷 유행어 (2026)").
- 스토어 앱의 짤은 KLIPY에서 나오므로, 도감에는 짤 파일이 없어도 된다. `keyword` 만 잘 정하면 됨.
  KLIPY에 짤이 없을 게 확실하면 `keyword` 를 `null` 로 두면 앱이 글자 카드로 보여준다.

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
[{"id": "...", "pick": 0, "name": "...", "quote": "...", "source": "...", "desc": "...", "region": "ko",
  "keyword": "KLIPY 검색어", "kind": "gifs"}]
```

- `quote`: 짤 속 대사/자막. 대사가 없으면 괄호로 동작 설명, 예: `"(고개 끄덕)"`
- `source`: 출처 (프로그램/영화/인물). **확실하지 않은 사실은 쓰지 않는다.** 모르면 더 일반적으로.
- `desc`: 어떤 장면이고 언제 쓰는지 두 문장 이내.
- `keyword`: 스토어 앱이 KLIPY에서 짤을 찾을 때 쓰는 검색어. 밈 이름 + 인물/프로그램 이름처럼 짤이 바로 나올 말.
  환경변수 `KLIPY_KEY` 가 있으면 `python tools/klipy_check.py '{"id": "검색어"}'` 로 KLIPY 결과가 그 밈인지 확인하고 검색어를 고친다.
- `kind`: 보통 `"gifs"`. 영화·드라마 장면이면 `"clips"` 가 더 잘 나오는지도 klipy_check 로 비교.

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

## 5-1. 아직 확인 안 된 검색어 확인 (KLIPY_KEY 있을 때만)

`catalog.json` 에서 `"verified": false` 인 밈을 시간당 80개 이하로 `tools/klipy_check.py` 로 돌려 본다.
맞는 짤이 나오면 `verified: true`, 안 나오면 검색어를 바꾸거나 `keyword: null`.

## 6. 마무리 보고

추가한 밈 이름 목록, 건너뛴 후보와 이유(짤 못 찾음 등)를 짧게 남긴다.
새 밈이 하나도 없으면 커밋하지 않고 "새 밈 없음"으로 끝낸다.
