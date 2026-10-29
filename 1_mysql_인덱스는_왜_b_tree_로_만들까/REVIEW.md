# REVIEW

## 시청 후 답할 수 있는 것

질문: **MySQL 인덱스는 왜 B-tree예요? 이진 트리나 해시는 왜 안 써요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **인덱스의 비용은 비교 횟수가 아니라 페이지를 읽는 횟수다.**
   왜: MySQL 기본 저장 엔진인 InnoDB는 디스크와 메모리 사이에서 데이터를 페이지(기본 16KB) 단위로 옮긴다.
   페이지 안에서 값을 비교하는 건 메모리 안의 일이라 금방이고, 느린 건 페이지를 디스크에서 가져오는 일이다.
   그래서 페이지 한 번 읽을 때 최대한 많이 결정하는 구조가 이긴다. (0:11 innodb.txt)
2. **이진 트리는 높다. 50만 개면 약 19층이다.**
   왜: 한 칸에 값 1개, 갈림길 2개라서 한 층 내려갈 때마다 후보가 절반씩만 준다. 2^19 = 524,288 ≥ 500,000.
   칸이 서로 다른 페이지에 있으면 한 명 찾는 데 페이지를 최대 19번 읽는다. (0:32 binary_tree.txt)
3. **B-tree는 낮고 넓다. 50만 개면 3층, 넉넉히 잡아도 4층이다.**
   왜: 한 칸이 페이지 하나(16KB)라서 값이 수백 개 들어가고 갈림길도 수백 개다. 한 칸에 약 300개로 치면 3층에 2,700만 개까지 담는다.
   앞 영상의 "50만 행에서 약 4번 읽기"가 바로 이 높이다. (0:46 btree.txt, 0:57 compare.txt)
4. **실제로 디스크에서 읽는 횟수는 더 적다.**
   왜: 위쪽 층(루트 1페이지, 가지 약 6페이지)은 찾을 때마다 지나가므로 buffer pool(InnoDB의 메모리 캐시)에 늘 남아 있다.
   그래서 디스크까지 가는 건 아래쪽 한두 번인 경우가 많다. (1:04 buffer_pool.txt)
   이것이 B-tree의 한계(등호 검색도 한 번에 끝나지 않고 몇 층을 내려간다)를 메우는 이유이기도 하다.
5. **정렬 배열은 넣기가 비싸고, B-tree는 페이지 하나만 고친다.**
   왜: 정렬 배열은 이진 탐색으로 찾기는 빠르지만, 중간에 끼우면 뒤의 값을 전부 한 칸씩 밀어야 한다(50만 개면 평균 25만 개).
   B-tree는 들어갈 페이지 하나만 고치고, 그 페이지가 꽉 찼으면 두 페이지로 나눈 뒤 위 칸에 새 페이지를 적는다(페이지 분할).
   한계와 대처: 이 분할도 앞 영상에서 말한 쓰기 비용의 한 부분이다. 그래서 인덱스는 필요한 곳에만 건다. (1:18 sorted_array.txt, 1:33 page_split.txt)
6. **해시는 등호 검색은 한 번에 끝나지만 순서가 없다.**
   왜: 값을 해시 함수에 넣어 저장할 칸 번호를 바로 계산하므로, 똑같은 값은 한 번에 찾는다.
   대신 비슷한 값도 칸 번호가 제각각이라 순서가 남지 않는다. 그래서 범위 검색, 정렬, 앞부분 검색(kim으로 시작)에는 못 쓴다. (1:50, 1:58 hash.txt)
7. **B-tree는 바닥 페이지들이 키 순서대로 옆으로 이어져 있어서, 범위를 옆으로 읽는다(이 모양을 B+tree라고 부른다).**
   왜: `LIKE 'kim%'`는 위에서 'kim' 자리를 한 번만 찾고, 옆 페이지로 쭉 읽다가 'kin'이 나오면 멈춘다.
   `BETWEEN` 같은 범위 조건도, `ORDER BY` 정렬도 같은 방식으로 시작점만 찾고 옆으로 읽는다. (2:08 leaves.txt, 2:22 range.sql)

기억할 한 문장: "디스크는 페이지째 읽으니까 B-tree는 한 칸을 페이지로 만들어 낮고 넓게 쌓고, 넣을 땐 페이지 하나만 고치며, 바닥이 이어져 있어 범위도 읽는다." (2:33 summary.md)

## 만드는 법

```bash
# 1) 대본/화면/썸네일 수정: content.json
# 2) 나레이션 다시 생성 (edge-tts, 문장별 캐시는 build/tts_cache)
~/.local/share/uv/tools/edge-tts/bin/python tools/tts.py
# 3) 장면 HTML + 썸네일 생성 (index.html, compositions/*.html, output/thumbnail.png 를 덮어씀)
python3 tools/build.py
python3 tools/thumbnail.py
# 4) 점검 / 장면 캡처 / 렌더 / 측정
npx --yes hyperframes@0.8.209 check
npx --yes hyperframes@0.8.209 check 2>&1 | grep -oE "⚠ [a-z_]+" | sort | uniq -c
T=$(python3 -c "
import json; t=json.load(open('build/timing.json'))
s=[0.0]+[x['sentences'][0]['start'] for x in t['shots'][1:]]; e=s[1:]+[t['duration']]
print(','.join(['0']+[f'{(a+b)/2:.2f},{b-0.15:.2f}' for a,b in zip(s,e)]))")
npx --yes hyperframes@0.8.209 snapshot --at $T
npx --yes hyperframes@0.8.209 render -o "output/mysql_인덱스는_왜_b_tree_로_만들까.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/mysql_인덱스는_왜_b_tree_로_만들까.mp4"
ffmpeg -nostats -i "output/mysql_인덱스는_왜_b_tree_로_만들까.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- `0_mysql_인덱스란_무엇이고_왜_쓸까`의 후속편이다. 같은 예시(회원 50만 명 `users` 테이블, 이메일로 찾기, `kim@ex.com`)를 이어 썼다.
  앞 영상 요약은 첫 문장 하나(0:00–0:05)뿐이고, 인덱스가 무엇인지, EXPLAIN, 언제 만드나는 다시 설명하지 않았다.
- 질문은 사용자가 정한 범위("왜 B-tree인가, 이진 트리나 해시는 왜 아닌가")를 그대로 썼다. 사용자가 준 6개 항목을 하나씩 확인했고, 바꾼 곳은 다음과 같다.
  - 2번(이진 트리 vs B-tree 높이)은 두 항목으로 나눴다. 이진 트리가 왜 높은지와 B-tree가 왜 낮은지는 이유가 서로 달라서다. 그래서 답안은 7개다.
  - 4번의 "그 페이지 분할이 앞 영상의 쓰기 비용의 출처다"는 **"쓰기 비용의 한 부분"으로 고쳤다.**
    MySQL 문서는 쓰기 비용을 "새 값을 넣을 자리를 찾는 읽기 + 인덱스 갱신과 행 쓰기"로 설명한다(estimating-performance.html).
    분할은 페이지가 꽉 찼을 때만 일어난다. 그래서 분할이 쓰기 비용 전부라고 하면 틀린 말이 된다.
  - 4번의 "반으로 나눈다"는 **"두 페이지로 나눈다"로 말했다.** MySQL 소스 문서의 함수 설명은 "Splits an index page to halves"이지만,
    매뉴얼은 순서대로 넣으면 페이지가 약 15/16까지 차고, 무작위로 넣으면 1/2–15/16 찬다고 쓴다. 즉 항상 정확히 반은 아니다.
  - 6번의 "B+tree"는 MySQL 공식 문서가 쓰는 이름이 아니다. 문서는 "B-tree"라고 부르고, 용어집에서 "고전 B-tree에 없는 개선이 들어간 변형"이라고 한다.
    바닥끼리 이어진 것은 MySQL 소스 문서(fil0types.h)로 확인했다. 그래서 영상에서는 "정확히는 B+tree라고 불러요"로 이름만 소개했다(아래 '가장 약한 부분' 참고).
  - 1, 3, 5번은 그대로 맞았다.
- 길이 때문에 뺀 것: 처음 대본은 33문장, film 172.4 s였다. 가이드 순서대로 이유를 말하지 않는 문장부터 뺐다.
  - **"InnoDB에서 고를 수 있는 인덱스 방식도, B-tree 하나뿐이에요."** (4.4 s) 사실이지만 이유가 아니라서 뺐다.
    create-index.html의 표에서 InnoDB가 허용하는 index_type은 `BTREE`뿐이고, `HASH`는 MEMORY 엔진(과 NDB)에서 고를 수 있다.
  - 정렬 배열 장면의 다리 질문 "그럼 … 반씩 나눠 찾으면 어떨까요? 찾기는 빨라요."를 "정렬된 배열에서 반씩 나눠 찾아도, 찾기는 빨라요."로 줄였다.
  - 그 결과 166.4 s. 그 뒤 마지막 줄이 짧게 보이는 장면 3개(5, 10, 12번)에 hold 0.5 s씩을 줘서 167.9 s가 됐다.
- 일부러 넣지 않은 것: InnoDB의 adaptive hash index(자주 찾는 B-tree 페이지 위에 InnoDB가 자동으로 만드는 해시). "해시는 안 쓴다"는 말과 부딪쳐 보일 수 있지만,
  사용자가 직접 만드는 인덱스의 구조가 아니고 설명하려면 한 장면이 더 필요해서 뺐다.
- 다음 영상 후보(범위를 좁히느라 뺀 것):
  - 클러스터드 인덱스와 세컨더리 인덱스, 커버링 인덱스("왜 `SELECT *`가 더 느릴까")
  - 인덱스를 못 타는 쿼리: `LIKE '%…'`, 컬럼에 함수 씌우기, 복합 인덱스의 왼쪽부터 규칙
  - 트랜잭션과 락
  - (이번 편에서 새로 나온 것) 기본 키를 UUID로 하면 왜 느려질까: 순서대로 넣을 때와 무작위로 넣을 때의 페이지 분할 차이. 클러스터드 인덱스 편 다음이 자연스럽다.
  - (이번 편에서 새로 나온 것) adaptive hash index: InnoDB가 B-tree 위에 해시를 자동으로 얹는 경우

### 쓴 사실과 출처 (2026-10-28 확인, MySQL 8.4 Reference Manual과 MySQL 소스 문서)

| 영상 속 내용 | 출처 |
|---|---|
| 앞 영상 요약: 50만 행에서 약 4번 읽기 | dev.mysql.com/doc/refman/8.4/en/estimating-performance.html — "For a 500,000-row table … log(500,000)/log(1024/3*2/(3+4)) + 1 = 4 seeks." |
| InnoDB는 MySQL의 기본 저장 엔진이다 | dev.mysql.com/doc/refman/8.4/en/innodb-introduction.html — "In MySQL 8.4, InnoDB is the default MySQL storage engine." |
| InnoDB는 디스크와 메모리 사이에서 페이지 단위로 데이터를 옮긴다 | dev.mysql.com/doc/refman/8.4/en/glossary.html (page) — "A unit representing how much data InnoDB transfers at any one time between disk (the data files) and memory (the buffer pool)." |
| 기본 페이지는 16KB, InnoDB 인덱스는 B-tree이고 인덱스 레코드는 잎 페이지에 있다 | dev.mysql.com/doc/refman/8.4/en/innodb-physical-structure.html — "InnoDB indexes are B-tree data structures." "Index records are stored in the leaf pages…" "The default size of an index page is 16KB." |
| 비용은 디스크 읽기 횟수로 잡는다 | estimating-performance.html — "In most cases, you can estimate query performance by counting disk seeks." |
| B-tree는 자식이 많고, 자식이 2개뿐인 이진 트리와 다르다 | glossary.html (B-tree) — "Because B-tree nodes can have many children, a B-tree is not the same as a binary tree, which is limited to 2 children per node." |
| 위쪽 층은 buffer pool(메모리)에 남아 있다 | dev.mysql.com/doc/refman/8.4/en/innodb-buffer-pool.html — "The buffer pool is an area in main memory where InnoDB caches table and index data as it is accessed." / "The algorithm keeps frequently used pages in the new sublist." |
| 디스크까지 가는 건 한두 번인 경우가 많다 | estimating-performance.html — "…so you probably have much of the index in memory and so need only one or two calls to read data to find the row." |
| 꽉 찬 페이지는 나뉜다(페이지 분할) | glossary.html (fill factor) — "the proportion of a page that is taken up by index data before the page is split." / dev.mysql.com/doc/dev/mysql-server/latest/btr0btr_8h.html — `btr_page_split_and_insert`: "Splits an index page to halves and inserts the tuple." |
| 분할 뒤 페이지가 얼마나 차는지 | innodb-physical-structure.html — "If index records are inserted in a sequential order … about 15/16 full. If records are inserted in a random order, the pages are from 1/2 to 15/16 full." |
| 쓰기 비용 = 넣을 자리 찾기 + 인덱스 갱신과 행 쓰기 | estimating-performance.html — "For writes, however, you need four seek requests to find where to place a new index value and normally two seeks to update the index and write the row." |
| 해시는 등호만, 범위와 정렬은 못 한다 | dev.mysql.com/doc/refman/8.4/en/index-btree-hash.html — "They are used only for equality comparisons that use the = or <=> operators (but are very fast). They are not used for comparison operators such as < that find a range of values." / "The optimizer cannot use a hash index to speed up ORDER BY operations. (This type of index cannot be used to search for the next entry in order.)" / "Only whole keys can be used to search for a row." |
| 같은 층의 B-tree 페이지는 키 순서대로 양쪽으로 이어져 있다 | dev.mysql.com/doc/dev/mysql-server/latest/fil0types_8h.html — FIL_PAGE_NEXT: "B-tree index pages … on the same PAGE_LEVEL are maintained as a doubly linked list via FIL_PAGE_PREV and FIL_PAGE_NEXT in the collation order of the smallest user record on each page." |
| `LIKE 'kim%'`는 'kim' 이상 'kin' 미만 범위가 된다 | index-btree-hash.html — "…if the argument to LIKE is a constant string that does not start with a wildcard character." 예: `LIKE 'Patrick%'` → "'Patrick' <= key_col < 'Patricl'" |
| `BETWEEN`은 B-tree 범위 조건이다 | dev.mysql.com/doc/refman/8.4/en/range-optimization.html — "for BTREE indexes, comparison of a key part with a constant value is a range condition when using the >, <, >=, <=, BETWEEN, != , or <> operators, or LIKE comparisons if the argument to LIKE is a constant string that does not start with a wildcard character." |
| `ORDER BY`도 인덱스로 처리할 수 있다 | dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html — "In some cases, MySQL may use an index to satisfy an ORDER BY clause and avoid the extra sorting involved in performing a filesort operation." |
| (뺀 문장) InnoDB의 index_type은 BTREE뿐 | dev.mysql.com/doc/refman/8.4/en/create-index.html — Index Types Per Storage Engine: InnoDB `BTREE`, MEMORY/HEAP `HASH`, `BTREE` |
| 레코드 헤더 5바이트, 세컨더리 인덱스 레코드에 기본 키가 들어간다(아래 계산에 씀) | dev.mysql.com/doc/refman/8.4/en/innodb-row-format.html — "Each index record contains a 5-byte header…" / "Each secondary index record contains all the primary key columns…" |
| 위 계산의 교차 확인(공식 문서 아님) | blog.jcole.us/2013/01/10/btree-index-structures-in-innodb/ (Jeremy Cole, InnoDB 내부 구조 분석) — INT 키 테이블에서 16KB 페이지에 "468 records per leaf page, or 1203 records per non-leaf page", 100만 행이 3층 |

### 직접 계산한 수치

- **이진 트리 약 19층**: log2(500,000) ≈ 18.93. 2^18 = 262,144 < 500,000 ≤ 2^19 = 524,288이라서, 균형이 완벽해도 19층이 필요하다.
- **한 칸에 수백 개**: `idx_email`의 한 항목 ≈ 이메일(평균 약 20바이트로 가정) + 길이 1바이트 + id(INT 4바이트로 가정) + 레코드 헤더 5바이트 (+ 가지 페이지라면 자식 페이지 번호 4바이트) ≈ 30–35바이트.
  16,384 ÷ 35 ≈ 470개(꽉 찼을 때). 무작위로 넣으면 페이지가 1/2–15/16 차므로(매뉴얼) 약 230–440개. 그래서 "수백 개"라고 했다.
  Jeremy Cole의 실측(INT 키, 468개와 1,203개)과도 자릿수가 맞는다.
- **"한 칸에 약 300개라 치면"**: 위 범위의 중간쯤 값을 가정으로 골랐고, 화면과 대본에 "치면"으로 가정임을 밝혔다. 300 → 300² = 90,000 → 300³ = 27,000,000.
- **3층, 넉넉히 4층**: 300개씩이면 잎 500,000 ÷ 300 ≈ 1,667(화면 "약 1,700") → 가지 1,667 ÷ 300 ≈ 5.6(화면 "약 6") → 루트 1. 그래서 3층이다.
  4층이 되려면 한 칸에 약 80개 미만이어야 한다(80³ = 512,000). 앞 영상이 쓴 문서 공식(1KB 블록 가정)은 log(500,000)/log(97.5) + 1 ≈ 3.9로 "4"가 나온다.
  같은 공식에 16KB와 항목 30–50바이트를 넣으면 3.2–3.4다. 그래서 "3층, 넉넉히 잡아도 4층"이라고 했다.
- **평균 25만 개 이동**: 넣는 자리가 고르게 퍼져 있으면 평균적으로 뒤의 절반을 민다. 500,000 ÷ 2 = 250,000.

### 예시로 지어낸 것

- 회원 50만 명 `users`, `kim@ex.com`은 앞 영상에서 이어 온 예시다. 첫 화면에 `# 지난 영상: users 50만 명`이라고 밝혔다.
- 정렬 배열의 값(`ahn, choi, kim, lee, park`), 새로 넣는 `'jung'`, 잎 페이지의 `jin, jung, kang`은 지어낸 값이다.
- 해시 장면의 `hash('kim@ex.com') → 7`, `kim1 → 2`, `kima → 9`는 지어낸 칸 번호다. 비슷한 값이 흩어진다는 것을 보이려는 그림이다.
- 'kin'에서 멈추는 것은 단순화했다. 정확한 조건은 `'kim' <= email < 'kin'`이다(문서의 'Patrick' 예와 같은 규칙).
- range.sql 화면의 `BETWEEN 'kim' AND 'kin'`은 범위 조건의 모양을 보여 주는 예다. 'kin'과 똑같은 값도 포함하므로 `LIKE 'kim%'`와 똑같은 조건은 아니다.

### 그 밖의 결정

- 기술 용어는 자막에도 영어로 썼다: `MySQL`, `InnoDB`, `B-tree`, `B+tree`, `buffer pool`, `16KB`, `BETWEEN`, `ORDER BY`. 예시 값 `kim`, `kin`도 영어로 썼다.
  읽기는 `content.json`의 `pronounce`에 적었다:
  `MySQL` 마이에스큐엘, `InnoDB` 이노디비, `B-tree` 비트리, `B+tree` 비플러스트리, `buffer pool` 버퍼 풀, `16KB` 십육킬로바이트,
  `BETWEEN` 비트윈, `ORDER BY` 오더 바이, `kim` 킴, `kin` 킨.
- "해시"는 한글, "buffer pool"은 영어로 쓴다(사용자 결정). 해시는 해시맵·해시 함수처럼 한글로 굳은 말이고 "이진 트리"와 나란히 나온다.
  buffer pool은 InnoDB 고유 구성 요소 이름이다(`innodb_buffer_pool_size`). 이진 트리, 배열, 페이지, 메모리, 디스크, 캐시, 페이지 분할도 한글로 뒀다.
  화면 박스의 `hash('kim@ex.com')`처럼 코드로 쓴 함수 이름은 그대로 뒀다.
- 0:40 문장 "…페이지를 19번 읽을 수도 있죠."는 edge-tts가 "19번 읽을"을 한 단어로 묶어 `word count mismatch`가 났다.
  그 문장만 `say`로 "열아홉번 읽을"이라고 읽게 했다(자막은 "19번").
- "그래서 InnoDB의 메모리 캐시인 buffer pool에, …"는 자막이 "buffer"와 "pool에" 사이에서 줄이 바뀌었다.
  "그래서 InnoDB의 메모리 캐시, buffer pool에 늘 올라와 있죠."로 바꿔서 쉼표에서 나뉘게 했다.
- '노드' 대신 앞 영상처럼 '칸'이라는 말을 썼다. '팬아웃' 같은 용어는 쓰지 않고 '갈림길'이라고 했다.
- 썸네일: 제목 `인덱스는 왜 / B-tree일까?`(166px), 부제 `# 이진 트리도, 해시도 아니고`, 제목줄 `❯ mysql`.
- `content.json`에 `question` 키를 메모로 넣었다(`markup`처럼 도구는 읽지 않는다).
- 폴더 이름의 `b_tree_로`는 `new_project.py`가 하이픈과 영문·한글 경계를 `_`로 바꾼 결과라서 그대로 뒀다.

## 측정한 것 / 보기만 한 것

- 렌더: 1080x1920, 30 fps, 167.9 s(2:48), 14.9 MB.
- 오디오: 통합 -13.9 LUFS, 피크 -1.5 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 2건(아래). 다른 종류의 경고는 없었다. contrast 167/167 통과.
- `build.py`는 `font down to`나 `chars/s` 경고를 내지 않았다. `thumbnail.py`는 제목 166px로 경고가 없었다.
- 화면: 장면마다 가운데 시점과 끝 직전 시점을 캡처해서 봤다(29장). 박스 넘침은 없었고 자막은 모두 2줄 안이었다.
  0초 프레임에 첫 박스(지난 영상 요약)와 첫 자막이 보인다. 자막에 한글 음차("마이에스큐엘" 등)는 없다.
  가장 빽빽한 박스는 btree.txt(6줄)와 page_split.txt로, 원본 크기 프레임에서 읽힌다.
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - 영어 용어: MySQL의(0:15), InnoDB는(0:17), InnoDB의(1:09), B-tree(0:06, 0:46, 1:33, 2:08, 2:35, 2:45), B+tree라고(2:30),
    해시는(0:09, 1:50), buffer pool에(1:11), BETWEEN(2:22), ORDER BY(2:24), kim으로(2:05, 2:13), kim(2:15), kin이(2:19)
  - 숫자: 16KB짜리(0:18, "십육킬로바이트"), 50만(0:01, 0:36, 0:57, 1:29), 네 번(0:04), 19층(0:39), 19번(0:44, "열아홉번"),
    300개라(0:52), 3층만(0:53), 2700만(0:54), 3층과 4층이면(0:58, 1:00), 25만(1:31)

## 일부러 남긴 경고

`line_unread` 2건. 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: "3층 27,000,000"을 10단어로 셈).

- shot-05 `3층  27,000,000` (화면에 2.26 s): 장면 마지막 줄이고, 나레이션이 "3층만 쌓아도 2700만 개"라고 같이 말한다.
- shot-10 `WHERE email = 'kim@ex.com'` (화면에 4.01 s): 앞 영상부터 계속 나온 쿼리라서 처음 보는 줄이 아니다.

두 장면 모두 hold 0.5 s를 줬다(12번 leaves.txt도 같이 줘서 그 장면의 경고는 없어졌다).

## 가장 약한 부분

- **"한 칸에 수백 개, 약 300개"는 계산이지 실측이 아니다.** 이메일 평균 길이와 페이지가 찬 정도를 가정했다.
  실제 테이블이 있다면 `SELECT stat_name, stat_value FROM mysql.innodb_index_stats WHERE table_name='users' AND index_name='idx_email';`의
  `n_leaf_pages`와 `size`로 확인할 수 있다. 다만 결론(3층 안팎)은 한 칸이 80개만 넘으면 바뀌지 않는다.
- **"B+tree"라는 이름**: MySQL 공식 문서는 "B-tree"라고만 부른다. 레코드가 잎에만 있고 잎끼리 이어진 것은 문서와 소스 문서로 확인했지만,
  그 구조를 B+tree라고 부르는 것은 일반적인 자료구조 용어다. 영상에서는 "정확히는 B+tree라고 불러요"로 말했다.
  또 InnoDB는 잎뿐 아니라 모든 층의 페이지를 양옆으로 잇는다(소스 문서 "on the same PAGE_LEVEL"). 영상은 범위 읽기에 쓰는 바닥만 말했다.
- **이진 트리 "19번 읽을 수도"**는 칸마다 다른 페이지에 있을 때의 최악이다. 이진 트리의 칸을 페이지에 묶어 담으면 줄일 수 있지만, 그게 사실상 B-tree의 생각이다.
- **"비교는 금방, 읽기는 느림"**에 구체적인 수치를 붙이지 않았다. 매뉴얼은 "디스크 읽기 횟수로 성능을 어림한다"고만 하고, 이 영상에 맞는 공식 수치가 없어서다.
- **해시**: InnoDB에서는 사용자가 해시 인덱스를 고를 수 없다는 것과 adaptive hash index를 영상에서 말하지 않았다. 날카로운 시청자는 "MySQL에도 해시가 있지 않나요?"라고 물을 수 있다.
- **"인덱스는 필요한 곳에만 걸어요"**는 앞 영상의 결론을 다시 쓴 것이다. 이번 편에서는 페이지 분할이 왜 그 이유 중 하나인지만 보탰다.
- 길이 2:48은 3분 한도 안이지만 여유가 12 s다. 더 줄인다면 1순위는 range.sql의 B+tree 이름 소개 문장(약 4.6 s)이다.

## 고친 이력

- v2 (2026-10-28, 사용자 결정): 자막·화면 박스·썸네일의 "Hash"를 "해시"로 바꿨다. "buffer pool"은 영어 그대로 둔다.
  읽는 소리는 v1과 같아서 나레이션과 단어 타이밍이 그대로다(TTS 캐시 재사용).
