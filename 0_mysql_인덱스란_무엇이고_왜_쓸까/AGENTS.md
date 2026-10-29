# 쇼츠 영상 폴더

이 폴더는 `/shorts` 스킬(`~/Documents/video_making/.claude/skills/shorts/SKILL.md`)이 만든 HyperFrames 영상이다.
만들기·고치기는 그 SKILL.md를 따른다. 아래는 그중 꼭 지킬 것이다.

- **브라우저 미리보기를 띄우지 않는다.** `hyperframes preview`, `npm run dev` 둘 다 쓰지 않는다. 사용자가 원하지 않는다.
  확인은 `check`와 `snapshot`으로 하고, 캡처 이미지를 직접 읽는다.
- 명령은 버전을 고정해서 쓴다: `npx --yes hyperframes@0.8.209 check | snapshot | render`
- `index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친 뒤 다시 만든다.
- 고치는 순서: `content.json` → `~/.local/share/uv/tools/edge-tts/bin/python tools/tts.py` → `python3 tools/build.py`
  → `python3 tools/thumbnail.py` → check → snapshot → render. 결과는 `output/`의 영상과 썸네일을 덮어쓴다.
- git은 쓰지 않는다.
- 화면 구조 자체(`tools/build.py`)를 바꿀 때만 HyperFrames 규칙을 확인한다: `npx --yes hyperframes@0.8.209 docs compositions`
