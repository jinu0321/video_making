# REVIEW

## 시청 후 답할 수 있는 것

질문: **MySQL 인덱스가 무엇이고, 왜 쓰며, 단점은 무엇인가요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **인덱스는 컬럼 값을 정렬해 두고, 각 값이 어느 행(기본 키)인지 적어 둔 별도의 목록이다.**
   왜: 정렬돼 있어야 처음부터 다 보지 않고 원하는 값으로 바로 갈 수 있다. 책 맨 뒤 찾아보기와 같다. (0:32 idx_email.txt)
2. **인덱스가 없으면 풀 테이블 스캔을 한다.**
   왜: InnoDB 테이블은 기본 키 순서로 저장돼 있어서 이메일 같은 다른 컬럼 값은 어디 있는지 알 수 없다.
   그래서 첫 줄부터 하나씩 비교하고, 행이 두 배면 읽는 양도 두 배가 된다. (0:14 users.txt)
3. **인덱스가 있으면 몇 번만 읽고 찾는다.**
   왜: B-트리라서 맨 위에서 구간을 골라 한 단계씩 내려가고, 한 칸에 값이 여러 개 들어 있어 단계가 적다.
   MySQL 문서 계산 예로 50만 행에서 약 4번이고, 행이 10배가 돼도 많아야 한 번쯤 는다. (0:51 btree.txt, 1:05 compare.txt)
4. **쓰기(INSERT·UPDATE·DELETE)가 느려진다.**
   왜: 행을 넣고 고칠 때마다 인덱스마다 정렬된 자리를 찾아 값을 끼워 넣어야 한다. 인덱스 수만큼 일이 는다.
   대처: 실제로 자주 찾는 조건에만 만든다. (1:19 insert.sql)
5. **저장 공간을 더 쓴다.**
   왜: 인덱스마다 컬럼 값과 기본 키를 한 벌씩 따로 저장한다. 대처: 안 쓰는 인덱스는 지운다. (1:35 disk.txt)
6. **값 종류가 적은 컬럼(상태가 활성과 휴면뿐)은 인덱스가 있어도 MySQL이 풀 스캔을 고르기도 한다.**
   왜: 인덱스에는 값과 기본 키만 있어서, 찾은 행마다 기본 키로 실제 행을 한 번 더 찾아가야 한다.
   절반(25만 명)이 해당되면 25만 번 왕복하느니 처음부터 읽는 게 빠르다. 대처: 값이 잘 안 겹치는 컬럼에 만든다. (1:47 mysql, 1:59 lookup.txt)
7. **인덱스를 쓰는지는 EXPLAIN으로 확인한다(type, key, rows).**
   왜: 쓸지 말지는 MySQL이 쿼리마다 정하므로, 만들었다고 쓰이는 게 아니다(6번이 그 예). (0:05, 1:14, 2:16 mysql)
8. **언제 만드나: 행이 많고, 자주 찾는 조건이고, 값이 잘 안 겹치는 컬럼.**
   안 만들어도 되는 때: 행이 적을 때(다 읽어도 금방), 쓰기가 대부분일 때(4번 비용이 더 큼), 값이 몇 종류뿐일 때(6번).
   (2:25 checklist.md)

기억할 한 문장: "인덱스는 정렬된 찾아보기라서 읽기를 몇 번으로 줄여 주지만, 쓰기와 공간을 내주니 꼭 필요한 컬럼에만 건다."

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
T=$(python3 -c "
import json; t=json.load(open('build/timing.json'))
s=[0.0]+[x['sentences'][0]['start'] for x in t['shots'][1:]]; e=s[1:]+[t['duration']]
print(','.join(['0']+[f'{(a+b)/2:.2f},{b-0.15:.2f}' for a,b in zip(s,e)]))")
npx --yes hyperframes@0.8.209 snapshot --at $T
npx --yes hyperframes@0.8.209 render -o "output/mysql_인덱스란_무엇이고_왜_쓸까.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/mysql_인덱스란_무엇이고_왜_쓸까.mp4"
ffmpeg -nostats -i "output/mysql_인덱스란_무엇이고_왜_쓸까.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 시리즈(인덱스 → 트랜잭션 → Docker → Redis → BullMQ)의 첫 편이다. 트랜잭션과 락은 다음 편 주제라서 넣지 않았다.
  인덱스 설명에 꼭 필요한 곳도 없었다.
- 처음 대본은 답안 9개, 39문장, film 195.7 s로 목표(170 s)를 넘었다. 가이드대로 설명은 줄이지 않고 항목을 뺐다.
  - **뺀 항목: "앞부분을 모르는 검색(`LIKE '%@ex.com'`)은 인덱스를 못 쓴다"** (2장면, 24.5 s).
    다른 항목은 인덱스를 만들지 말지 고르는 기준이고, 이 항목만 쿼리 작성 요령이라서 골랐다.
  - 이것만 빼면 171.2 s였다. 그래서 '왜'가 없는 다리 장면 하나("컬럼마다 전부 걸면 될까요?", CREATE INDEX 3줄)를 없앴다.
    그 질문은 쓰기 비용 장면의 첫 문장("그런데 인덱스는 공짜가 아니에요.")으로 합쳤다. 결과는 166.8 s다.
  - 그 뒤 코드가 많고 문장이 짧은 EXPLAIN 장면 3개(2, 12, 14번)에 hold 0.5 s씩을 줘서 film은 168.3 s가 됐다.
- 다음 영상 후보(범위를 좁히느라 뺀 것):
  - 인덱스를 못 타는 쿼리: `LIKE '%…'`, 컬럼에 함수 씌우기. 대본과 출처까지 준비했다가 길이 때문에 뺐다.
  - 복합 인덱스와 "왼쪽부터" 규칙(leftmost prefix)
  - 클러스터드 인덱스와 커버링 인덱스(기본 키가 짧아야 하는 이유)
  - UNIQUE 인덱스로 중복 막기, ORDER BY·범위 검색에 인덱스 쓰기

### 쓴 사실과 출처 (2026-10-28 확인, MySQL 8.4 Reference Manual)

| 영상 속 내용 | 출처 |
|---|---|
| 인덱스가 없으면 첫 행부터 테이블 전체를 읽는다. 있으면 데이터 중간의 위치로 바로 간다 | dev.mysql.com/doc/refman/8.4/en/mysql-indexes.html — "Without an index, MySQL must begin with the first row and then read through the entire table…" / "…quickly determine the position to seek to in the middle of the data file…" |
| PRIMARY KEY·UNIQUE·INDEX는 B-tree에 저장된다. InnoDB 인덱스는 B-tree이고 기본 페이지는 16KB다 | 위 페이지 — "Most MySQL indexes (PRIMARY KEY, UNIQUE, INDEX, and FULLTEXT) are stored in B-trees." / dev.mysql.com/doc/refman/8.4/en/innodb-physical-structure.html — "InnoDB indexes are B-tree data structures." "The default size of an index page is 16KB." |
| 테이블은 기본 키 순서로 저장된다(클러스터드 인덱스) | dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html — "Each InnoDB table has a special index called the clustered index that stores row data. Typically, the clustered index is synonymous with the primary key." |
| 인덱스에는 값과 기본 키만 있고, 기본 키로 실제 행을 한 번 더 찾아간다 | 위 페이지 — "each record in a secondary index contains the primary key columns for the row, as well as the columns specified for the secondary index. InnoDB uses this primary key value to search for the row in the clustered index." |
| 50만 행에서 약 4번 읽기 | dev.mysql.com/doc/refman/8.4/en/estimating-performance.html — "For a 500,000-row table … the formula indicates log(500,000)/log(1024/3*2/(3+4)) + 1 = 4 seeks." |
| 행이 10배가 돼도 읽기는 많아야 한 번쯤 는다 | 같은 공식에서 계산했다. 한 블록 분기 수 ≈ 1024/3*2/7 ≈ 97이므로 log(10)/log(97) ≈ 0.5단계. 문서에 직접 쓰인 문장은 아니다 |
| 새 값을 넣을 때도 인덱스에서 넣을 자리를 찾아야 한다 | estimating-performance.html — "For writes, however, you need four seek requests to find where to place a new index value…" |
| 인덱스는 쓰기를 느리게 하고 공간을 쓴다 | dev.mysql.com/doc/refman/8.4/en/optimization-indexes.html — "unnecessary indexes waste space … Indexes also add to the cost of inserts, updates, and deletes because each index must be updated." |
| 해당 행이 많으면 인덱스가 있어도 풀 스캔을 고른다 | dev.mysql.com/doc/refman/8.4/en/index-btree-hash.html — "…when the optimizer estimates that using the index would require MySQL to access a very large percentage of the rows in the table. (In this case, a table scan is likely to be much faster because it requires fewer seeks.)" |
| 작은 테이블에서는 인덱스가 덜 중요하다 | mysql-indexes.html — "Indexes are less important for queries on small tables, or big tables where report queries process most or all of the rows." |
| EXPLAIN의 type ALL = 풀 테이블 스캔, ref = 인덱스로 찾기, key NULL = 인덱스 안 씀, rows = 읽을 행 수 추정 | dev.mysql.com/doc/refman/8.4/en/explain-output.html — `ALL`: "A full table scan…", `key`: "If key is NULL, MySQL found no index to use…", `rows`: "…the number of rows MySQL believes it must examine… For InnoDB tables, this number is an estimate" |
| (뺀 항목) `LIKE`는 와일드카드로 시작하지 않을 때만 인덱스를 쓴다 | index-btree-hash.html — "…if the argument to LIKE is a constant string that does not start with a wildcard character." |

### 예시로 지어낸 것

- 회원 50만 명 `users` 테이블, `kim@ex.com`(id 42) 등 이메일과 id, 인덱스 3개(email, name, phone), 상태 컬럼(active와 dormant가 절반씩)은 지어낸 예시다.
  첫 화면에 `# 예시: 회원 50만 명`이라고 밝혔다.
  50만이라는 숫자는 MySQL 문서의 계산 예(50만 행 → 약 4번)와 맞추려고 골랐다.
- EXPLAIN 화면은 `\G` 세로 출력에서 type, key, rows(, possible_keys)만 남긴 것이다.
  `rows: ~500,000`은 실제로는 50만에 가까운 추정치로 나온다.
  email 인덱스는 `CREATE INDEX`(UNIQUE 아님)라서 type이 `ref`다. UNIQUE였다면 `const`가 나온다.

### 그 밖의 결정

- 기술 용어는 자막에도 영어로 쓴다(`MySQL`, `EXPLAIN`, `B-tree`, `Full Table Scan`, `Full Scan`).
  읽기는 `content.json`의 `pronounce`에 적었다("마이에스큐엘", "익스플레인", "비트리", "풀 테이블 스캔", "풀 스캔").
  인덱스, 테이블, 컬럼, 쿼리, 기본 키처럼 한글로 굳은 말은 한글로 뒀다.
- '옵티마이저'라는 용어는 새로 소개하지 않았다. "MySQL이 쿼리마다 정한다"로 말했다.
- 썸네일: 제목 `MySQL 인덱스 / 왜 빠르고 / 언제 손해?`, 부제 `# 1명 찾으려고 50만 줄을 읽을 때`.
  처음 넣은 `MySQL 인덱스,`(쉼표 포함)는 134px로 경고가 나서 쉼표를 뺐다(141px).
- `content.json`에 `question` 키를 메모로 넣었다(`markup`처럼 도구는 읽지 않는다).

## 측정한 것 / 보기만 한 것

- 렌더: 1080x1920, 30 fps, 168.4 s(2:48), 15.1 MB.
- 오디오: 통합 -14.1 LUFS, 피크 -1.5 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 10건(아래). 다른 종류의 경고는 없었다. contrast 150/150 통과.
- `build.py`는 `font down to`나 `chars/s` 경고를 내지 않았다. 가장 빽빽한 insert.sql 박스는 약 55px로, 원본 크기 프레임에서 읽힌다.
- 화면: 장면마다 가운데 시점과 끝 직전 시점(박스가 다 찬 상태)을 캡처해서 봤다. 박스 넘침은 없었고 자막은 모두 2줄 안이었다.
  0초 프레임에 첫 박스(쿼리)와 첫 자막이 보인다.
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - EXPLAIN(0:05, 2:22), MySQL(1:05, 1:56, 2:18), B-tree라는(0:51), Full Table Scan(0:24)
  - 숫자: "50만"(0:01, 0:10, 1:07, 2:40), "25만"(2:07, 2:09), "네 번"(1:08), "열 배"(1:11), "두 배"(0:27)

## 일부러 남긴 경고

`line_unread` 10건. 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: "rows: 1"을 5단어로 셈). 해당하는 줄은 다음과 같다.

- shot-02 `rows: ~500,000`
- shot-09 EXPLAIN 3줄(`mysql> EXPLAIN…`, `key: idx_email`, `rows: 1`)
- shot-11 `DROP INDEX…`
- shot-12 `possible_keys`, `key: NULL`, `type: ALL`
- shot-14 `key: NULL`
- shot-15 `status 처럼 몇 종류`

모두 장면 끝에 타이핑되는 줄이고, 그 내용은 나레이션이 함께 말한다.
EXPLAIN 장면 2, 9, 12, 14번에는 0.5 s씩 hold를 줬다.

## 가장 약한 부분

- "50만 행 → 약 4번"은 문서 예시를 그대로 쓴 것이다. 그 예시는 1KB 인덱스 블록과 3바이트 키(MEDIUMINT)를 가정한다.
  InnoDB는 16KB 페이지라 한 칸에 더 많이 들어가지만, 이메일 키는 더 길다. 그래서 실제 단계 수는 3–4 정도로 비슷한 수준이다.
  영상에서는 "문서의 계산 예"라고 말했다.
- "25만 번 왕복"은 단순화다. 실제로는 버퍼 풀 캐시나 Multi-Range Read 같은 최적화가 있다.
  요점은 "많이 해당되면 MySQL이 풀 스캔이 싸다고 판단한다"는 것이고, "안 쓰기도 해요"로 단정을 피했다.
- 쓰기 비용은 "인덱스마다 자리를 찾아 넣는다"까지만 설명했다. 페이지 분할 같은 내부 동작은 다루지 않았다.
- 길이 2:48은 3분 한도 안이지만 여유가 12 s뿐이다. 더 줄인다면 1순위는 공간 장면(disk.txt, 약 12 s)이다.
- 썸네일 제목 141px은 경고 기준(140px) 바로 위다. 더 크게 하려면 `MySQL`을 부제로 내리고 `인덱스,`만 크게 쓴다.

## 고친 이력

- v2 (2026-10-28, 사용자 요청): 자막의 기술 용어를 한글 음차에서 영어로 바꿨다(8문장). 읽는 소리는 `pronounce`로 v1과 똑같이 맞춰서,
  나레이션과 단어 타이밍이 v1과 같다(TTS 캐시 재사용).
  같은 때 템플릿을 고쳐 자막 패널이 영상 내내 켜져 있다. v1에서는 장면 사이 0.3–0.9 s 동안 패널이 꺼졌다(35번, 합계 14.6 s).
