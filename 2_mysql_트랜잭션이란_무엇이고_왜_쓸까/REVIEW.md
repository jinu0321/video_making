# REVIEW

## 시청 후 답할 수 있는 것

질문: **MySQL 트랜잭션은 무엇이고 왜 쓰나요? 안 쓰면 무엇이 다르고, 단점은 무엇인가요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **트랜잭션은 여러 SQL을 한 묶음으로 만들어, 전부 반영하거나 전부 취소한다.** `START TRANSACTION`으로 열고 `COMMIT`으로 확정한다.
   왜 필요한가: 이체는 `UPDATE` 두 줄이지만 의미는 하나다. 첫 줄만 반영되면 1번에서 빠진 돈이 2번에 들어오지 않아 사라진다(예시: 합계 7만 원이 6만 원). (0:00 transfer.sql, 0:05 incident.log, 0:19 transfer.sql)
2. **안 쓰면 문장마다 따로 확정된다(autocommit).**
   왜: MySQL은 기본값이 autocommit이라서, 문장 하나가 그 자체로 트랜잭션이 되고 끝나자마자 COMMIT된다.
   그래서 첫 `UPDATE` 뒤에 서버가 꺼지거나 두 번째가 실패하면 첫 줄은 이미 확정된 상태이고, ROLLBACK으로도 되돌릴 수 없다. (0:29 mysql)
3. **묶어 두면 중간에 실패해도 처음 상태로 돌아간다.** 실패하면 ROLLBACK 한 번으로 첫 `UPDATE`까지 되돌리고, COMMIT 전에 서버가 꺼지면 재시작할 때 MySQL이 알아서 되돌린다.
   왜: InnoDB(MySQL 기본 저장 엔진)가 행을 바꾸기 전에 원래 값을 undo log에 적어 두고, 그 기록으로 원래 값을 되살리기 때문이다. (0:39 rollback.sql, 0:49 undo.log)
4. **COMMIT이 끝났으면 바로 뒤에 서버가 꺼져도 변경은 남는다.**
   왜: COMMIT할 때 바뀐 내용을 redo log에 적어 디스크에 내려 두기 때문이다(기본 설정). 데이터 파일에 아직 못 쓴 변경은 재시작할 때 redo log로 마저 반영한다. (1:04 redo.log)
5. **기본 설정에서는 다른 세션이 COMMIT 전의 중간 상태를 보지 못한다.** 이체 도중에 다른 세션이 합계를 봐도 7만 원 그대로다. autocommit이었다면 돈이 빠진 순간(6만 원)이 그대로 보인다.
   왜: 아직 COMMIT되지 않은 행은 undo log에 남은 예전 값으로 보여 주기 때문이다(consistent read). (1:19 session_b.sql)
6. **단점: 바꾼 행에 락이 걸리고 COMMIT이나 ROLLBACK 때까지 풀리지 않는다. 그래서 같은 행을 바꾸려는 다른 트랜잭션은 기다린다.**
   왜: `UPDATE`는 바꾼 행에 다른 트랜잭션이 못 바꾸게 하는 락(exclusive lock)을 걸고, InnoDB는 이 락을 트랜잭션이 끝날 때 한꺼번에 푼다.
   기본 50초를 넘기면 기다리던 문장은 에러(1205)로 끝난다. (1:32 lock.txt)
7. **단점: 트랜잭션이 길수록 손해가 커진다.** 다른 쪽이 그만큼 오래 기다리고, undo log도 쌓인다.
   왜: 열린 트랜잭션이 예전 값을 볼 수도 있어서, InnoDB는 그동안 undo log를 지우지 못한다.
   대처: 외부 API 응답처럼 느린 일은 트랜잭션 밖으로 빼고, 바꿀 것만 묶어 바로 COMMIT한다. (1:49 transfer.sql)
8. **단점: 데드락이 생길 수 있다.**
   왜: A가 1번에서 2번으로, B가 2번에서 1번으로 동시에 보내면, A는 1번 락을 쥔 채 2번을, B는 2번 락을 쥔 채 1번을 기다린다. 서로 상대가 놓기만 기다리니 둘 다 끝나지 않는다.
   InnoDB는 이를 알아채고 한쪽 트랜잭션을 통째로 ROLLBACK한다(에러 1213).
   대처: 이 에러가 나면 앱이 트랜잭션을 처음부터 다시 실행한다. 또 늘 같은 순서(작은 번호부터)로 `UPDATE`하면 B가 1번에서 줄을 서므로 데드락이 생기지 않는다. (2:05 deadlock.txt, 2:22 mysql)

기억할 한 문장: "같이 성공해야 하는 여러 문장은 트랜잭션으로 묶는다. undo log로 되돌리고 redo log로 COMMIT을 지키는 대신 락을 쥐니까, 짧게 쓴다." (2:37 summary.md)

## 만드는 법

```bash
# 1) 대본/화면/썸네일 수정: content.json
# 2) 나레이션 다시 생성 (edge-tts, 문장별 캐시는 build/tts_cache)
~/.local/share/uv/tools/edge-tts/bin/python tools/tts.py
# 3) 장면 HTML + 썸네일 생성 (index.html, compositions/*.html, output/thumbnail.png 를 덮어씀)
python3 tools/build.py
python3 tools/thumbnail.py
# 4) 점검 / 장면 캡처 / 렌더 / 측정
npx --yes hyperframes@0.8.209 check > build/check.txt 2>&1; tail -3 build/check.txt
grep -oE "⚠ [a-z_]+" build/check.txt | sort | uniq -c
T=$(python3 -c "
import json; t=json.load(open('build/timing.json'))
s=[0.0]+[x['sentences'][0]['start'] for x in t['shots'][1:]]; e=s[1:]+[t['duration']]
print(','.join(['0']+[f'{(a+b)/2:.2f},{b-0.15:.2f}' for a,b in zip(s,e)]))")
npx --yes hyperframes@0.8.209 snapshot --at $T
npx --yes hyperframes@0.8.209 render -o "output/mysql_트랜잭션이란_무엇이고_왜_쓸까.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/mysql_트랜잭션이란_무엇이고_왜_쓸까.mp4"
ffmpeg -nostats -i "output/mysql_트랜잭션이란_무엇이고_왜_쓸까.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 사용자 요청은 "무엇이고 왜 쓰는지, 안 쓸 때와 비교, 장점 단점"이었다. 질문 하나로 묶었다: "무엇이고 왜 쓰나, 안 쓰면 무엇이 다르나, 단점은".
  "안 쓸 때와 비교"는 장면을 따로 두지 않고 장점 항목마다 나란히 넣었다(2번 autocommit, 3번 ROLLBACK 불가, 5번 6만 원이 보임).
- ACID 네 글자를 이름으로 늘어놓지 않았다. 영상에 "ACID"라는 말은 나오지 않는다. 답안에 필요한 세 가지만 원리와 함께 다뤘다.
  - 전부 아니면 전무: undo log (3번)
  - COMMIT 뒤에 꺼져도 남음: redo log (4번)
  - 다른 세션이 중간 상태를 못 봄: consistent read, undo log의 예전 값 (5번)
  - "일관성(C)"은 따로 다루지 않았다. 이체 예의 "합계 7만 원이 유지된다"가 그 내용이지만, 이름을 붙이면 나열이 된다.
- **격리 수준은 영상에서 이름도 꺼내지 않았다.** 대신 5번을 "기본 설정에서는"으로 한정했다(기본 격리 수준 REPEATABLE READ. READ COMMITTED에서도 같다).
  READ UNCOMMITTED에서는 COMMIT 전 값이 보일 수 있어서(dirty read), "항상 못 본다"고 말하면 틀린다.
- 단점 3개(락 대기, 긴 트랜잭션, 데드락)는 모두 이유와 대처를 붙였다.
  긴 트랜잭션은 처음에 "락을 오래 쥔다"만 있었는데, film이 162 s로 여유가 있어서 undo log가 쌓이는 이유 한 문장(5.6 s)을 더했다. 락 대기와 다른, 두 번째 이유라서다.
- "언제 쓰나"는 장면을 따로 두지 않고 정리 첫 문장("같이 성공해야 하는 여러 문장을 트랜잭션으로 묶어요")에 넣었다.
  한 문장짜리 `UPDATE`는 autocommit만으로도 그 자체가 트랜잭션이라는 것은 2번 장면에서 나온다("문장마다 바로 COMMIT").
- 길이: 첫 대본(31문장)은 film 약 162 s. 위 한 문장, hold 0.5 s(lock.txt), 정리 문장 수정 뒤 169.1 s. 170 s 아래라 줄이지 않았다.
- 다음 영상 후보(범위를 좁히느라 뺀 것):
  - **격리 수준 4가지**: 각 수준에서 다른 세션에 무엇이 보이나(dirty read, non-repeatable read, phantom), REPEATABLE READ의 스냅샷은 언제 찍히나
  - **재고 차감과 `SELECT ... FOR UPDATE`**: 두 사람이 마지막 1개를 동시에 사는 경우. 일반 SELECT는 락을 안 걸어서 생기는 문제(lost update)
  - **인덱스 없는 UPDATE는 왜 많은 행을 잠그나**: `UPDATE ... WHERE`는 검색 중 만나는 모든 레코드에 next-key lock을 건다. 인덱스 시리즈와 이어진다.
  - **COMMIT은 디스크에 무엇을 쓰나**: `innodb_flush_log_at_trx_commit` 0/1/2의 속도와 유실 차이, doublewrite buffer, binlog
  - **긴 트랜잭션 찾기**: undo log와 purge, history list length를 어떻게 보나
  - (참고) MyISAM처럼 트랜잭션이 없는 테이블은 ROLLBACK이 안 된다. 이번 영상은 InnoDB만 전제로 했다.

### 락/lock 표기 결정

- **"락"은 한글로 썼다.** 가이드의 기준 "개발자가 한국어로 말할 때 보통 한글로 쓰는가"에 따랐다. "락을 건다", "락 대기"처럼 한글로 굳은 말이고, 해시·캐시와 같은 경우다.
  "1번 락을 쥔 채"처럼 한국어 문장 속에 들어가므로, 영어로 쓰면 한 줄에 영어와 한글이 계속 섞인다.
- 같은 이유로 **"데드락"도 한글**로 썼다.
- 화면 박스의 `ERROR 1205: Lock wait timeout`, `ERROR 1213: Deadlock found`는 MySQL이 실제로 내는 에러 문구라서 영어 그대로 뒀다.
- 그 밖에 한글로 둔 말: 트랜잭션, 세션, 행, 계좌, 앱, 데이터 파일, 디스크.
  영어로 쓴 말: `MySQL`, `SQL`, `InnoDB`, `UPDATE`, `START TRANSACTION`, `COMMIT`, `ROLLBACK`, `autocommit`, `undo log`, `redo log`, `API`.
  `undo log`, `redo log`는 InnoDB 고유 구성 요소 이름이라서 B-tree 편의 `buffer pool`처럼 영어로 썼다.
  화면의 `TRANSACTION`(빨강)은 인덱스 편의 `INDEX`처럼 주제 이름 박스에만 썼다.

### 쓴 사실과 출처 (2026-10-28 확인, MySQL 8.4 Reference Manual)

| 영상 속 내용 | 출처 |
|---|---|
| 트랜잭션 = 전부 성공하거나 전부 되돌리는 작업 단위 | dev.mysql.com/doc/refman/8.4/en/glossary.html (transaction) — "When a transaction makes multiple changes to the database, either all the changes succeed when the transaction is committed, or all the changes are undone when the transaction is rolled back." |
| `START TRANSACTION`으로 열고 `COMMIT`으로 확정, `ROLLBACK`으로 취소 | dev.mysql.com/doc/refman/8.4/en/commit.html — "COMMIT commits the current transaction, making its changes permanent." / "ROLLBACK rolls back the current transaction, canceling its changes." / "With START TRANSACTION, autocommit remains disabled until you end the transaction with COMMIT or ROLLBACK." |
| 기본값은 autocommit, 문장마다 따로 트랜잭션, ROLLBACK으로 못 되돌림 | commit.html — "By default, MySQL runs with autocommit mode enabled. This means that, when not otherwise inside a transaction, each statement is atomic, as if it were surrounded by START TRANSACTION and COMMIT. You cannot use ROLLBACK to undo the effect" / dev.mysql.com/doc/refman/8.4/en/innodb-autocommit-commit-rollback.html — "In InnoDB, all user activity occurs inside a transaction. If autocommit mode is enabled, each SQL statement forms a single transaction on its own." |
| InnoDB는 MySQL 기본 저장 엔진, commit·rollback·crash-recovery | dev.mysql.com/doc/refman/8.4/en/innodb-introduction.html — "In MySQL 8.4, InnoDB is the default MySQL storage engine." / "…with transactions featuring commit, rollback, and crash-recovery capabilities to protect user data." |
| undo log에 바꾸기 전 값을 남기고 그것으로 되돌린다 | dev.mysql.com/doc/refman/8.4/en/innodb-undo-logs.html — "An undo log record contains information about how to undo the latest change by a transaction to a clustered index record." / dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html — "It keeps information about old versions of changed rows to support transactional features such as concurrency and rollback." / glossary.html (undo log) — "A storage area that holds copies of data modified by active transactions." |
| COMMIT 전에 서버가 꺼지면 재시작 때 되돌린다 | dev.mysql.com/doc/refman/8.4/en/innodb-recovery.html — "InnoDB automatically rolls back uncommitted transactions that were present at the time of the crash." / "As part of crash recovery, InnoDB rolls back transactions that were not committed or in XA PREPARE state when the server exited." |
| COMMIT이 성공하면 꺼져도 남는다 | glossary.html (ACID) — "once a commit operation succeeds, the changes made by that transaction are safe from power failures, system crashes, race conditions, or other potential dangers…" |
| COMMIT 때 redo log를 디스크에 쓴다(기본 설정) | dev.mysql.com/doc/refman/8.4/en/innodb-parameters.html (innodb_flush_log_at_trx_commit, 기본값 1) — "The default setting of 1 is required for full ACID compliance. Logs are written and flushed to disk at each transaction commit." |
| 데이터 파일에 못 쓴 변경은 재시작 때 redo log로 반영 | dev.mysql.com/doc/refman/8.4/en/innodb-redo-log.html — "The redo log is a disk-based data structure used during crash recovery to correct data written by incomplete transactions." / "Modifications that did not finish updating data files before an unexpected shutdown are replayed automatically during initialization and before connections are accepted." |
| 다른 세션은 COMMIT 전 변경을 못 본다(기본 설정) | dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html — "The query sees the changes made by transactions that committed before that point in time, and no changes made by later or uncommitted transactions." / "Consistent read is the default mode in which InnoDB processes SELECT statements in READ COMMITTED and REPEATABLE READ isolation levels." / innodb-autocommit-commit-rollback.html — "A COMMIT means that the changes made in the current transaction are made permanent and become visible to other sessions." |
| 그 예전 값은 undo log에서 가져온다 | innodb-undo-logs.html — "If another transaction needs to see the original data as part of a consistent read operation, the unmodified data is retrieved from undo log records." |
| 기본 격리 수준(5번의 "기본 설정") | dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html — "The default isolation level for InnoDB is REPEATABLE READ." / READ UNCOMMITTED: "…a possible earlier version of a row might be used. … This is also called a dirty read." |
| `UPDATE`는 행에 배타 락을 건다, 다른 트랜잭션은 기다린다 | dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html — "UPDATE ... WHERE ... sets an exclusive next-key lock on every record the search encounters. However, only an index record lock is required for statements that lock rows using a unique index to search for a unique row." / dev.mysql.com/doc/refman/8.4/en/innodb-locking.html — "If transaction T1 holds an exclusive (X) lock on row r, a request from some distinct transaction T2 for a lock of either type on r cannot be granted immediately. Instead, transaction T2 has to wait for transaction T1 to release its lock on row r." |
| 락은 COMMIT이나 ROLLBACK 때 풀린다 | innodb-autocommit-commit-rollback.html — "Both COMMIT and ROLLBACK release all InnoDB locks that were set during the current transaction." / innodb-locks-set.html — "All InnoDB locks held by a transaction are released when the transaction is committed or aborted." |
| 기본 50초 기다리다 에러, 기다리던 문장만 취소 | innodb-parameters.html (innodb_lock_wait_timeout) — "The length of time in seconds an InnoDB transaction waits for a row lock before giving up. The default value is 50 seconds." / "ERROR 1205 (HY000): Lock wait timeout exceeded; try restarting transaction" / "When a lock wait timeout occurs, the current statement is rolled back (not the entire transaction)." |
| 열린 트랜잭션이 있으면 undo log를 못 지우고 쌓인다 | innodb-multi-versioning.html — "It is recommend that you commit transactions regularly, including transactions that issue only consistent reads. Otherwise, InnoDB cannot discard data from the update undo logs, and the rollback segment may grow too big, filling up the undo tablespace in which it resides." / "…they can be discarded only after there is no transaction present for which InnoDB has assigned a snapshot that in a consistent read could require the information in the update undo log to build an earlier version of a database row." |
| 트랜잭션은 짧게, 관련 변경 뒤 바로 COMMIT | dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks-handling.html — "Keep transactions small and short in duration to make them less prone to collision." / "Commit transactions immediately after making a set of related changes…" |
| 데드락 정의, 반대 순서로 잠글 때 생긴다 | dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html — "A deadlock is a situation in which multiple transactions are unable to proceed because each transaction holds a lock that is needed by another one. Because all transactions involved are waiting for the same resource to become available, none of them ever releases the lock it holds." / "A deadlock can occur when transactions lock rows in multiple tables … but in the opposite order." |
| InnoDB가 알아채고 한쪽을 통째로 ROLLBACK | innodb-deadlocks.html — "When deadlock detection is enabled (the default) and a deadlock does occur, InnoDB detects the condition and rolls back one of the transactions (the victim)." / dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html — "A transaction deadlock causes InnoDB to roll back the entire transaction. Retry the entire transaction when this happens." |
| 에러 1213 문구 | dev.mysql.com/doc/refman/8.4/en/innodb-deadlock-example.html — "ERROR 1213 (40001): Deadlock found when trying to get lock; try restarting transaction" |
| 다시 실행할 준비, 같은 순서로 바꾸면 줄을 선다 | innodb-deadlocks-handling.html — "Always be prepared to re-issue a transaction if it fails due to deadlock." / "When modifying multiple tables within a transaction, or different sets of rows in the same table, do those operations in a consistent order each time. Then transactions form well-defined queues and do not deadlock." |
| (6번 표현 근거) 실패한 문장 하나만 취소되는 경우가 많다 | innodb-error-handling.html — "InnoDB sometimes rolls back only the statement that failed, other times it rolls back the entire transaction." / "A duplicate-key error rolls back the SQL statement…" |

### 예시로 지어낸 것

- 계좌 `account`(id, balance), 1번 50,000원, 2번 20,000원, 1만 원 이체. 첫 화면에 `# 예시: 1번에서 2번으로 1만 원`, 두 번째 화면에 `# 예시: 첫 UPDATE 뒤 서버 다운`을 넣었다.
  undo.log(5만 원), session_b.sql(7만 원, 6만 원) 장면의 숫자는 이 예시에서 이어진 값이라 다시 표시하지 않았다.
- transfer.sql의 `UPDATE` 두 줄은 실제로 돌아가는 SQL이다(`SET balance` 뒤에서 줄을 나눴을 뿐). 이후 장면의 `-- 1번에서 10000 빼기`는 같은 UPDATE를 줄여 쓴 SQL 주석이다.
- autocommit 장면의 `UPDATE 1번 → 바로 COMMIT`, lock.txt의 `A 1번 UPDATE # 락`은 코드가 아니라 흐름을 보여 주는 그림이다.
- "결제 API 응답 대기"는 트랜잭션이 길어지는 예로 내가 고른 상황이다. 매뉴얼의 조언은 "작고 짧게, 관련 변경 뒤 바로 COMMIT"이고, 매뉴얼이 직접 드는 예는 "COMMIT 안 한 채 열어 둔 mysql 세션"이다.
- 데드락의 A, B 세션과 "동시에 반대로 이체"는 지어낸 상황이다(`# 예시: 동시에 반대로 이체`). 매뉴얼 예제는 Animals/Birds 테이블이지만 원리(반대 순서로 잠금)는 같다.
- 박스의 에러 문구는 줄였다: `ERROR 1205: Lock wait timeout`(원문 "ERROR 1205 (HY000): Lock wait timeout exceeded; try restarting transaction"), `ERROR 1213: Deadlock found`(원문 "ERROR 1213 (40001): Deadlock found when trying to get lock; try restarting transaction").

### 그 밖의 결정

- 예시는 인덱스 편의 `users` 테이블을 쓰지 않고 이체를 골랐다. 반만 반영되면 돈이 사라지는 것이 한눈에 보이고, 같은 예시로 격리(합계 7만/6만)와 데드락(반대 방향 이체)까지 이어서 보여 줄 수 있어서다.
  재고 차감 예는 동시 주문(lost update) 문제로 이어지는데, 그건 `SELECT ... FOR UPDATE`가 필요해서 다음 영상 후보로 돌렸다.
- 3번의 "두 번째가 실패해도 ROLLBACK 한 번에"는 앱이 ROLLBACK을 보내는 것으로 말했다. 에러가 난 문장 자체는 대개 그 문장만 취소되고, 트랜잭션 전체가 자동으로 취소되지는 않기 때문이다(innodb-error-handling.html).
- `pronounce`: `MySQL` 마이에스큐엘, `SQL` 에스큐엘, `InnoDB` 이노디비, `UPDATE` 업데이트, `START TRANSACTION` 스타트 트랜잭션, `COMMIT` 커밋, `ROLLBACK` 롤백,
  `autocommit` 오토커밋, `undo log` 언두 로그, `redo log` 리두 로그, `API` 에이피아이.
- `say`를 쓴 문장 두 개(edge-tts가 "1번 계좌에서", "1번 락을"을 한 단어로 묶어 `word count mismatch`):
  - 0:00 "1번 계좌에서 2번 계좌로…" → "일번 계좌에서 이번 계좌로…"
  - 2:12 "A는 1번 락을 쥔 채 2번을, B는 2번 락을…" → "A는 일번 락을 쥔 채 2번을, B는 이번 락을…"
  `say`가 있는 문장에는 `pronounce`가 적용되지 않으므로 첫 문장의 `UPDATE`도 `say`에 "업데이트"로 직접 썼다.
- transfer.sql(shot 4)은 처음에 4줄을 한 덩어리로 쳐서 `COMMIT; # 둘 다 확정`이 1.86 s만 보였다. `START TRANSACTION`과 주석 두 줄을 첫 문장에, `COMMIT`을 둘째 문장에 나눴다.
- 썸네일: 제목 `트랜잭션 / 왜 묶고 / 대가는?`(190px), 부제 `# MySQL 이체 중 서버가 꺼지면`, 제목줄 `❯ mysql`. 인덱스 편의 `왜 빠르고 / 언제 손해?` 형식을 따랐다.
- `content.json`에 `question` 키를 메모로 넣었다(도구는 읽지 않는다).

## 측정한 것 / 보기만 한 것

- 렌더: 1080x1920, 30 fps, 169.1 s(2:49), 15.7 MB.
- 오디오: 통합 -13.8 LUFS, 피크 -1.4 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 7건(아래). 다른 종류의 경고는 없었다.
- `build.py`는 `font down to`나 `chars/s` 경고를 내지 않았다. `thumbnail.py`는 제목 190px로 경고가 없었다.
- 화면: 장면마다 가운데 시점과 끝 직전 시점을 캡처해서 봤다(29장 + 바꾼 정리 장면 3장). 박스 넘침은 없었고 자막은 모두 2줄 안이었다.
  0초 프레임에 첫 박스(이체 SQL)와 첫 자막이 보인다. 자막에 한글 음차("마이에스큐엘", "커밋" 등)는 없다.
  가장 빽빽한 박스는 deadlock.txt, mysql(2:22), summary.md(6줄)이고 원본 크기 프레임에서 읽힌다.
  지금 읽는 단어의 하트비트 확대 때문에 쉼표 뒤 띄어쓰기가 순간적으로 가려 보이는 프레임이 있다(0:18 "바로,트랜잭션이에요"). 정해진 스타일의 동작이라 그대로 뒀다.
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - 영어 용어: UPDATE가(0:02), SQL을(0:20), START TRANSACTION으로(0:25), COMMIT으로(0:27), autocommit이라(0:32), COMMIT돼요(0:33),
    ROLLBACK으로도(0:37), ROLLBACK(0:41, 1:40), MySQL이(0:47), MySQL 기본 엔진인 InnoDB가(0:50), undo log를(0:52), ROLLBACK하면(1:00),
    redo log에(1:11), undo log의(1:25), autocommit이었다면(1:28), InnoDB는 undo log도(1:56), API(2:00), ROLLBACK해요(2:25), redo log로 COMMIT을(2:43)
  - 숫자: 1번/2번(0:00, "일번/이번"로 `say`), 1번에선·2번엔(0:09, 0:11), 5만(0:59), 7만(1:22), 6만(1:29), 50초를(1:45), 1번/2번(2:09–2:16, 2:34)
  - 알파벳 A, B(2:08–2:16, 2:34): "에이는", "비는"으로 읽히는지

## 일부러 남긴 경고

`line_unread` 7건. 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: `UPDATE account SET balance`를 23단어로 셈). 실제 단어 수로는 모두 읽을 시간이 된다.

- shot-01 `UPDATE account SET balance` 2건(5.33 s): 첫 장면 내내 보이는 줄이고 실제로는 4단어다.
- shot-02 `합계 70,000 → 60,000`(2.91 s): 이미 hold 0.5 s. 나레이션이 "돈이 사라진 거죠"로 같이 말한다.
- shot-07 `ROLLBACK → 1번 = 50,000`(3.63 s), shot-08 `# 재시작: redo log로 마저 반영`(3.35 s): 나레이션이 같은 내용을 말하는 동안 보인다.
- shot-09 `60,000 # autocommit: 중간 상태`(4.51 s).
- shot-10 `ERROR 1205: Lock wait timeout`(3.40 s): hold 0.5 s를 줘서 3.04 s에서 늘렸다.

처음 9건에서 shot-04 덩어리를 나누고(2건 없어짐) lock.txt에 hold를 줘서 7건이 됐다. 더 줄이려면 hold를 늘려야 하는데 film이 170 s를 넘는다.

## 가장 약한 부분

- **redo log 설명은 단순화했다.** "COMMIT할 때 redo log를 디스크에 내려 둔다"는 기본 설정(`innodb_flush_log_at_trx_commit=1`)에서만 맞다. 0이나 2면 약 1초 치를 잃을 수 있다.
  나레이션에는 "기본 설정"이라는 말이 없고 박스 주석(`# 기본 설정`)에만 있다. doublewrite buffer와 binlog는 말하지 않았다.
  또 "데이터 파일엔 나중에 써도 된다"의 이유(왜 데이터 파일에 바로 쓰지 않나)는 말하지 않았다. 읽은 매뉴얼 쪽에서 그 이유를 직접 쓴 문장을 찾지 못해서다.
- **5번 "다른 세션은 못 본다"는 기본 설정 한정이다.** READ UNCOMMITTED에서는 보일 수 있다. 영상은 "기본 설정에서는"으로만 한정하고 격리 수준 이름은 꺼내지 않았다.
  또 "undo log의 예전 값으로 보여 준다"는 일반 SELECT(consistent read) 이야기다. `SELECT ... FOR UPDATE` 같은 락 읽기는 기다린다.
- **6번 락 범위**: 예시는 기본 키(`WHERE id = 1`)로 한 행만 바꾸므로 그 행만 잠긴다. 인덱스가 없는 조건으로 UPDATE하면 검색 중 만나는 레코드를 모두 잠가서 훨씬 넓게 잠긴다. 영상은 이 경우를 말하지 않았다.
- **3번 ROLLBACK**: 영상은 "실패하면 ROLLBACK 한 번에"라고 해서, 시청자가 실패하면 자동으로 전부 되돌려진다고 들을 수 있다. 실제로는 대개 실패한 문장만 취소되고 앱이 ROLLBACK을 보내야 한다(데드락은 예외로 전체가 취소된다).
- **"외부 API 응답"**은 매뉴얼의 "짧게"를 내 예로 바꾼 것이다. 원리(락을 쥔 시간 = 다른 쪽이 기다리는 시간)는 매뉴얼과 맞다.
- 길이 2:49는 3분 한도 안이지만 여유가 11 s다. 더 줄인다면 1순위는 긴 트랜잭션의 undo log 문장(1:54, 약 5.6 s)이다. 그러면 7번 항목의 두 번째 이유가 빠진다.
