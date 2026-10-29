---
name: shorts
description: 주제 하나만 받아 한국어 개발 설명 유튜브 쇼츠(MP4, 3분 이하)와 썸네일(PNG)을 끝까지 만든다. ~/Documents/video_making 전용. 다음 번호 폴더(N_주제) 생성 → 좁고 깊은 대본·화면(content.json) 작성 → edge-tts 나레이션(InJoon) → HyperFrames 렌더 + 썸네일. 사용자가 "/shorts <주제>"로 부르거나, 이 디렉토리에서 새 주제로 쇼츠·영상을 만들어 달라고 할 때 사용.
---

주제만 받아서 번호 폴더를 만들고, 그 안에 새 영상(MP4)과 썸네일을 만든다.
중간에 사용자에게 확인받지 않고 MP4와 썸네일까지 끝낸 뒤 보고한다.

## 호출

```
/shorts <주제>
```

주제: $ARGUMENTS

(위가 비어 있거나 치환되지 않았으면 사용자 메시지에서 주제를 찾는다. 주제가 없을 때만 묻는다.)

## 결과물

- 폴더: `video_making/<N>_<주제 slug>/` (N = 기존 번호 폴더 최댓값 + 1)
- 영상: `<폴더>/output/<주제 slug>.mp4` — 1080x1920, 30 fps, 3분 이하.
- 썸네일: `<폴더>/output/thumbnail.png` — 1080x1920(9:16). YouTube Studio(컴퓨터)에서 Shorts 썸네일로 올리는 이미지.
- `output/`에는 이 두 파일만 둔다.

## 가장 중요한 것: 좁게 잡고, 깊게 다룬다

영상을 본 사람이 "<주제>가 뭐고 장단점이 뭐예요?"라는 질문을 받으면, 이유를 붙여 여러 가지를 말할 수 있어야 한다.
그러려면 다루는 범위를 좁혀야 한다.

- 대본보다 **질문 하나와 답안(6–8개 항목, 항목마다 '왜')을 먼저** 쓴다.
- 답안의 모든 항목이 대본에 이유와 함께 나와야 한다.
- 이름만 나열하고 지나가는 항목은 넣지 않는다.
- 길면 설명을 줄이지 않는다. 범위(답안 항목)를 줄인다.

자세한 방법은 `references/content-guide.md`의 첫 절에 있다. 3단계에서 반드시 먼저 읽는다.

## 스타일 (정해진 것, 바꾸지 않는다)

v5에서 사용자가 확정한 모습이고 `template/tools/build.py`에 들어 있다. 대본만 새로 쓴다.

- 위: 민트 진행 바 + 터미널 제목줄(`❯ cat cache.py`), 가운데: 남색 코드 박스에 타이핑(민트 `▌` 커서, 글자가 늘면 박스에 맞게 축소)
- 아래: 카라오케 자막. 지금 읽는 단어 = 민트 + 하트비트, 읽은 단어 = 회색. 기술 용어는 자막에 영어로(읽기는 `pronounce`)
- 목소리 ko-KR-InJoonNeural +20%, 음악·효과음 없음, 장면 전환은 하드 컷

## 준비물 확인 (처음 한 번)

```bash
which ffmpeg ffprobe npx
ls ~/.local/share/uv/tools/edge-tts/bin/python
python3 -c "import fontTools, PIL, brotli"
```

없으면: `brew install ffmpeg` / `uv tool install edge-tts` / `python3 -m pip install fonttools pillow brotli`.
나레이션 생성과 첫 렌더에는 인터넷이 필요하다(edge-tts 서버, GSAP CDN).

## 단계

1단계 명령은 `video_making/`에서 실행하고, 2단계부터는 새 폴더 안에서 실행한다.
`$SK`는 스킬 폴더 `~/Documents/video_making/.claude/skills/shorts`를 뜻한다.

### 1. 폴더 만들기

```bash
python3 .claude/skills/shorts/scripts/new_project.py "<주제>"
```

출력된 경로로 이동한다. `already exists`가 나오면 같은 주제 폴더가 이미 있는 것이니 사용자에게 다시 만들지 묻는다.
폴더에는 템플릿(tools/, HyperFrames 설정)이 복사돼 있고 `content.json`만 없다.
`assets/fonts`는 `video_making/fonts/`를 가리키는 심볼릭 링크다. 글꼴은 그 한 곳에만 두고 영상 폴더로 복사하지 않는다.

### 2. 조사

주제의 핵심 사실, 대표 명령/코드, 비교 수치를 확인한다. 공식 문서를 먼저 본다.
'무엇'뿐 아니라 '왜 그런지'(원리, 장단점의 이유, 한계와 대처)까지 확인한다. 답안의 '왜'는 모두 이 조사에 근거해야 한다.
수치와 출처는 7단계 REVIEW.md에 적는다. 확인 못 한 수치는 쓰지 않는다.

### 3. content.json 작성

`$SK/references/content-guide.md`를 읽고 그 규칙대로 쓴다. 형식 예시는 `$SK/references/content.example.json`이다.

1. 질문과 답안을 먼저 쓴다(가이드 첫 절).
2. 답안 항목마다 장면을 짠다.
3. 다 쓴 뒤 답안 항목마다 대본에서 '왜' 문장을 찾아 확인한다.
4. `thumbnail` 문구도 이때 쓴다. 정한 질문을 짧게 줄인 것이다.

### 4. 나레이션

```bash
~/.local/share/uv/tools/edge-tts/bin/python tools/tts.py
```

- `word count mismatch` → 그 문장의 기호·숫자 표기나 `pronounce` 읽기의 단어 수를 고친다(가이드 참고). 다시 실행하면 바뀐 문장만 새로 받는다.
- `film`이 170초를 넘으면 가이드 "길이" 절의 순서대로 줄인다. 먼저 이유 없는 연결 문장을 빼고, 그래도 넘으면 답안 항목을 장면째 뺀다.
  170초 아래가 될 때까지 반복한다. 남은 항목의 '왜' 설명은 줄이지 않는다.

### 5. 화면 생성 + 점검

```bash
python3 tools/build.py
python3 tools/thumbnail.py
npx --yes hyperframes@0.8.209 check > build/check.txt 2>&1; tail -3 build/check.txt
grep -oE "⚠ [a-z_]+" build/check.txt | sort | uniq -c
```

- `build.py`가 `font down to NNpx`나 `chars/s`를 출력하면 그 장면 박스를 줄이거나 나눈다.
- `thumbnail.py`가 `title font down to`를 출력하면 썸네일 제목 줄을 짧게 하거나 나눈다.
- check는 오류 0이어야 한다. 경고는 `line_unread`만 허용한다. 글자마다 `<span>`이라 단어 수가 부풀려 세어지는 경고이고,
  인덱스 편에서 10건, B-tree 편에서 2건 나왔다. 다른 종류의 경고는 고친다.
- `index.html`과 `compositions/`는 `build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.

### 6. 눈으로 확인

브라우저 미리보기(`hyperframes preview`)는 띄우지 않는다(사용자가 원하지 않음). 대신 장면마다 캡처해서 본다.
장면마다 가운데와 끝(컷 0.15초 전, 박스가 다 찬 모습)을 찍는다.

```bash
T=$(python3 -c "
import json; t=json.load(open('build/timing.json'))
s=[0.0]+[x['sentences'][0]['start'] for x in t['shots'][1:]]; e=s[1:]+[t['duration']]
print(','.join(['0']+[f'{(a+b)/2:.2f},{b-0.15:.2f}' for a,b in zip(s,e)]))")
npx --yes hyperframes@0.8.209 snapshot --at $T
```

출력된 폴더의 contact sheet를 모두 읽고 확인한다. 프레임이 많으면 `contact-sheet-1.jpg`, `-2`, `-3`, …으로 나뉜다.
자세히 볼 장면은 같은 폴더의 `frame-NN-at-*.png`를 읽는다.

- 0초 프레임에 첫 박스와 첫 자막이 보이는가. 이 프레임은 휴대폰 앱에서 표지를 영상 프레임 중에서 고를 때 쓰인다.
- `output/thumbnail.png`를 읽고 확인한다.
  - 제목이 크게 한눈에 읽히는가
  - 영상이 실제로 답하는 질문인가
- 장면 끝 프레임에서 박스 글자가 너무 작거나 넘치지 않는가, 자막이 2줄 안인가
- 자막의 기술 용어가 영어로 나오는가("마이에스큐엘" 같은 한글 음차가 없는가)
- 화면 문구가 나레이션을 그대로 반복하지 않는가

### 7. 렌더 + 측정

```bash
npx --yes hyperframes@0.8.209 render -o output/<slug>.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 output/<slug>.mp4
ffmpeg -nostats -i output/<slug>.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
```

기준: 길이 180초 미만, 통합 음량 약 -14 LUFS(-13 ~ -15), 피크 -1 dBFS 이하.

측정이 끝나면 캡처와 렌더 임시 파일을 지운다(한 편에 수 MB씩 쌓인다).

```bash
rm -rf .hyperframes renders
```

그다음 `REVIEW.md`를 이 절 순서로 쓴다.

- `## 시청 후 답할 수 있는 것`: 3단계에서 정한 질문과 답안
- `## 만드는 법`: 다시 만드는 명령(4–7단계). `index.html`과 `compositions/`는 생성 파일이니 `content.json`을 고치라고 적는다.
- `## 내린 결정`: 쓴 수치와 출처, 예시로 지어낸 상황, 범위에서 뺀 것
- `## 측정한 것 / 보기만 한 것`: 길이, LUFS, 피크, check 결과. 직접 들어 봐야 할 곳(영어 약어, 숫자 발음)
- `## 일부러 남긴 경고`: `line_unread` 건수와 이유
- `## 가장 약한 부분`

### 8. 보고

사용자에게 짧게 알린다.

- 영상과 썸네일 경로, 여는 명령: `open "<N>_<slug>/output/<slug>.mp4"`, `open "<N>_<slug>/output/thumbnail.png"`
- 썸네일 올리는 법(한 줄): YouTube Studio(컴퓨터) → 콘텐츠 → Shorts → 영상 → 썸네일 → 파일 업로드.
  인증된 계정이어야 한다. 휴대폰 앱에서는 영상 프레임 중에서만 고를 수 있다.
- YouTube에 올리는 법(한 줄): 영상을 확인한 뒤 `/upload <N>_<slug>` (바로 공개로 올라간다)
- 길이, 장면 흐름 한 줄 요약(훅 → … → 정리)
- 이 영상을 보면 답할 수 있는 질문과 답안 요약
- 범위를 좁히느라 뺀 내용이 있으면 "다음 영상 후보"로 제안
- 들어서 확인할 곳(영어 약어, 숫자 읽기)
- 고치고 싶은 곳은 시점과 내용을 말해 달라고 안내

## 수정 요청이 오면

`content.json`을 고친다 → 4–7단계 → 같은 파일명으로 다시 렌더해 덮어쓴다(`output/`에는 영상과 썸네일만). 예전 버전은 남기지 않는다.
썸네일만 고칠 때는 `content.json`의 `thumbnail`을 고치고 `python3 tools/thumbnail.py`만 다시 실행한다.

## 스타일을 바꾸고 싶다고 하면

새 영상의 모습은 `$SK/template/tools/build.py`가 정한다. 여기를 고치면 이후 새 폴더부터 적용된다.
이미 만든 폴더는 각자 `tools/build.py` 사본을 쓰므로 영향받지 않는다.

## 하지 말 것

- 브라우저 미리보기 띄우기, `compositions/`·`index.html` 직접 편집
- 배경음악·효과음 임의 추가
- `output/`에 버전별 파일 여러 개 두기(고치면 덮어쓴다)
- git 저장소 만들기, 커밋(사용자가 git을 쓰지 않기로 했다)
- 3분 넘는 영상
- 이름만 나열하고 넘어가는 대본(예: "세션, 랭킹, 요청 제한에도 써요" 한 문장으로 끝내기)
