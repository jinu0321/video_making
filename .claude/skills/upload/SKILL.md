---
name: upload
description: 완성된 쇼츠 폴더(N_주제) 하나를 YouTube에 공개로 올린다. content.json·REVIEW.md를 읽고 제목·설명·태그(youtube.json)를 쓴 뒤, scripts/upload.py(YouTube Data API)로 MP4를 올리고 썸네일 설정을 시도한다. ~/Documents/video_making 전용. 사용자가 "/upload <폴더>"로 부르거나 만든 쇼츠를 유튜브에 올려 달라고 할 때 사용.
---

완성된 쇼츠 폴더 하나를 YouTube에 올린다. 기본은 **바로 공개**다(사용자가 정했다). 올리기 전에 확인받지 않는다.
사용자가 공개 시각을 말하면 예약 공개로 올린다(그 시각까지 비공개였다가 YouTube가 공개한다).

## 호출

```
/upload <폴더> [공개 시각]
```

인자: $ARGUMENTS

(비어 있거나 치환되지 않았으면 사용자 메시지에서 폴더를 찾는다. 없을 때만 묻는다.)
`$SK`는 스킬 폴더 `~/Documents/video_making/.claude/skills/upload`를 뜻한다. 명령은 `video_making/`에서 실행한다.

## 처음 한 번 (사용자가 브라우저에서 직접)

`~/.config/youtube-upload/client_secret.json`이 없으면 업로드하지 말고 이 절을 사용자에게 안내한다.

1. Google Cloud Console에서 새 프로젝트 → API 및 서비스 → 라이브러리 → **YouTube Data API v3** 사용 설정
2. OAuth 동의 화면(Google 인증 플랫폼): 사용자 유형 **External**, 앱 이름·이메일만 채운다.
   개인 Gmail 계정에는 Internal이 없다(Workspace 조직 전용).
3. 대상(Audience): 게시 상태는 **테스트 중**으로 두고, 테스트 사용자에 채널을 가진 본인 Gmail을 추가한다.
   프로덕션으로 바꾸려면 홈페이지·개인정보처리방침 URL이 필요해서 쓰지 않는다(2026-10 확인).
   테스트 상태라 로그인이 7일마다 풀린다. 풀리면 upload.py가 브라우저 로그인 창을 다시 띄운다.
   로그인할 때 "확인되지 않은 앱" 경고가 뜨면 고급 → 이동을 누른다.
4. 클라이언트 → 클라이언트 만들기 → 유형 **데스크톱 앱** → JSON 다운로드
5. 터미널에서 옮긴다:
   ```bash
   mkdir -p ~/.config/youtube-upload && mv ~/Downloads/client_secret_*.json ~/.config/youtube-upload/client_secret.json && chmod 600 ~/.config/youtube-upload/client_secret.json
   ```

첫 업로드 때 브라우저 로그인 창이 뜬다. 사용자가 로그인하고 올릴 채널을 고르면 `token.json`이 저장되고, 그 뒤로는 7일마다 한 번씩만 다시 묻는다.
썸네일을 API로 설정하려면 채널 전화번호 인증(youtube.com/verify)도 돼 있어야 한다.

## 단계

### 1. 확인

- `<폴더>/output/`에 MP4 하나와 `thumbnail.png`가 있는가
- `<폴더>/youtube.json`에 `videoId`가 있으면 이미 올린 영상이다. 멈추고 `url`을 알려 준다.

### 2. youtube.json 쓰기

`content.json`의 `question`, `thumbnail`과 `REVIEW.md`의 "시청 후 답할 수 있는 것"을 읽고 쓴다.

```json
{
  "title": "MySQL 인덱스, 왜 빠르고 언제 손해일까?",
  "description": "MySQL 인덱스가 무엇이고, 왜 쓰며, 단점은 무엇인가요?\n\n- 인덱스 = 정렬된 값 + 행 위치 목록. 그래서 처음부터 다 안 읽는다\n- ...\n\n#MySQL #인덱스 #데이터베이스 #개발",
  "tags": ["MySQL", "인덱스", "B-tree", "EXPLAIN", "데이터베이스"]
}
```

- `title`: 영상이 답하는 질문을 짧게. 휴대폰에서는 앞 40자 정도만 보이니 핵심 용어를 앞에 둔다. 100자 이하.
- `description`: 첫 줄은 질문, 그다음 답안 항목을 한 줄씩(주장 + 짧은 '왜'), 마지막 줄에 해시태그 3–5개.
- 기술 용어는 영어로 쓴다(자막 규칙과 같다). `<r>` 같은 마크업과 `<` `>` 문자는 넣지 않는다(YouTube가 거부한다).

### 3. 올리기

```bash
uv run $SK/scripts/upload.py "<폴더>"
uv run $SK/scripts/upload.py "<폴더>" --publish-at 2026-10-30T18:00:00+09:00   # 예약 공개
```

- `--publish-at`은 한국 시간이면 `+09:00`을 붙인 RFC 3339 형식으로 쓴다. 지난 시각은 YouTube가 거부한다.
- 첫 실행과 7일마다 한 번은 사용자가 브라우저에서 로그인할 때까지 기다리므로, 항상 Bash timeout을 600000으로 준다.
- `missing .../client_secret.json` → "처음 한 번" 절을 안내한다.
- `thumbnail: not set` → 업로드는 성공한 것이다. 쇼츠에 API로 썸네일을 넣을 수 없는 채널일 수 있다. 보고에 수동 방법을 적는다.
- `warning: asked for public, got private` → 영상은 올라갔지만 비공개로 잠긴 것이다. API 프로젝트가 감사(YouTube API Services Audit)를 받아야 공개할 수 있다고 알린다.
- 성공하면 스크립트가 `youtube.json`에 `videoId`, `url`, `privacy`, `uploadedAt`을 적는다.

### 4. 보고

- Studio 링크(스크립트 출력의 `studio:`)와 쇼츠 링크
- 제목, 공개 상태(공개 / 예약 시각)
- 썸네일: 설정됨, 또는 YouTube Studio(컴퓨터) → 콘텐츠 → Shorts → 영상 → 썸네일 → 파일 업로드
- 올린 직후 몇 분은 저화질과 영상 프레임 썸네일이 보일 수 있다고 알린다. 0번 영상은 1080p 처리가 3분 안에 끝났고, 썸네일은 화면마다 반영이 더 늦었다.

## 올린 뒤 고칠 때

- 제목·설명·썸네일은 Studio에서 고친다. 이 스크립트 권한(`youtube.upload`)으로는 올린 영상을 수정할 수 없다.
- 영상 자체를 다시 올리려면 사용자가 Studio에서 기존 영상을 지운 뒤, `youtube.json`에서 `videoId`·`url`·`privacy`·`publishAt`·`uploadedAt`을 지우고 3단계를 다시 한다.

## 하지 말 것

- `client_secret.json`, `token.json` 내용 출력, 영상 폴더로 복사
- `youtube.json`에 `videoId`가 있는 폴더 다시 올리기(중복 업로드)
