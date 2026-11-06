# REVIEW

## 시청 후 답할 수 있는 것

출발점: 사용자가 보여 준 시퀀스 다이어그램 "Spring Data JPA 에서 MySQL 까지의 흐름"
(Spring Data JPA → JPA API → Hibernate(JPA 구현체) → JDBC API → MySQL JDBC Driver(JDBC 구현체) → MySQL DB, "위임" 화살표, "SQL 전송", "결과 전달").

질문: **`save()` 한 줄은 MySQL까지 무엇을 거쳐 가고, 왜 이렇게 칸이 나뉘어 있나요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **Spring Data JPA는 repository 구현을 대신 만들어 준다. `save()`는 새 엔티티면 `entityManager.persist`, 아니면 `merge`를 부른다.**
   왜: 우리는 `MemberRepository` 인터페이스만 선언하고, 실행하면 Spring이 그 뒤에 `SimpleJpaRepository`를 붙인다(실행 중 찍은 실제 클래스).
   저장·조회 같은 반복 코드를 매번 쓰지 않게 하는 것이 Spring Data repository의 목표다.
   `save()` 소스는 `entityInformation.isNew(entity)`로 나뉘고, 예시의 새 `Member`(id가 아직 없음)는 `persist`로 간다. (0:10 MemberRepository.java, 0:21 SimpleJpaRepository.java)
2. **JPA(`EntityManager`)는 약속(인터페이스)일 뿐이고, 실제 일은 구현체 Hibernate가 한다.**
   왜: 인터페이스 메서드 `persist`에는 몸통이 없어서(abstract) 실행할 코드가 없다. 호출하면 그 자리에 실제로 든 객체의 메서드가 바로 실행된다.
   그래서 실제 호출 스택에 `jakarta.persistence.*` 줄이 0개이고, `SimpleJpaRepository.save` 다음에 Spring 프록시 5프레임을 지나 `SessionImpl.persist`(Hibernate)가 나온다.
   그 Spring 프록시는 지금 트랜잭션의 Hibernate 객체에 호출을 넘겨 준다. (0:29 EntityManager.java, 0:45 stack.txt)
3. **Hibernate는 엔티티를 보고 SQL을 만들되 값 자리는 `?`로 비워 둔다. 이 예에선 `persist` 안에서 바로 insert가 나가지만, 보통은 예약만 했다가 커밋할 때 보낸다.**
   왜: Hibernate 로그에 `insert into member (name) values (?)`가 찍히고 값 `kim`은 bind 로그로 따로 나온다.
   `Member`의 id는 `GenerationType.IDENTITY`(MySQL이 만듦)라서, id를 알려면 행을 먼저 넣어야 한다. 그래서 `persist` 안에서 바로 보낸다.
   Session 메서드는 보통 SQL을 바로 실행하지 않고, flush(기본은 커밋 때)에 보낸다. (0:55 hibernate.log)
4. **JDBC도 약속(Java에 들어 있는 DB 접속 인터페이스)이고, 구현은 DB마다 드라이버가 한다. 그래서 Hibernate는 MySQL 드라이버 클래스를 모르고 JDBC만 부른다.**
   왜: JDBC는 "드라이버를 꽂아 여러 데이터 소스에 접근하는 틀"이다. `java.sql.Connection`은 JDK(`jrt:/java.sql`)의 인터페이스이고, 구현 `ConnectionImpl`은 `mysql-connector-j` jar에 있다.
   의존성에서도 MySQL 전용은 `mysql-connector-j` 한 줄이다.
   다른 DB로 바꿀 땐 드라이버 줄과 접속 주소(`spring.datasource.url`)를 바꾼다. 그 DB에 맞는 SQL은 Hibernate가 dialect를 알아서 골라 만든다(실험 로그 `Database dialect: MySQLDialect`, 따로 설정하지 않았다). (1:14 types.txt, 1:25 build.gradle.kts, 1:31 application.properties)
5. **그림에 없는 칸이 있다: Hibernate와 드라이버 사이의 HikariCP(커넥션 풀).**
   왜: 새 연결엔 네트워크·드라이버 작업이 들어서, 미리 열어 둔 연결을 빌려주고 돌려받는다.
   연결을 닫아도 진짜로 닫지 않고 풀로 돌려놓으려고 드라이버 연결을 한 겹 감싼다(`HikariProxyConnection` 안에 `ConnectionImpl`).
   인터페이스 덕분에 Hibernate는 사이에 끼어든 줄도 모른다. (1:40 stack.txt, 1:46 pool.txt)
6. **MySQL 드라이버 기본값에서는 MySQL이 `?`가 값으로 채워진 완성된 SQL 문자열을 받는다. 채울 때 특수문자를 이스케이프해서 SQL 인젝션을 막는다.**
   왜: Connector/J는 기본 설정에서 값을 서버에 따로 보내지 않고 직접 채워 넣는다(클라이언트 쪽 prepared statement가 기본).
   드라이버가 보낸 패킷과 MySQL general log 둘 다 `insert into member (name) values ('kim')`.
   문자열 값은 이스케이프가 필요하면 `StringUtils.escapeString`으로, 아니면 작은따옴표로 감싸서 넣는다(Connector/J 9.7.0 `StringValueEncoder`). (2:03 general.log, 2:17 StringValueEncoder.java)
7. **`save()`를 따로 부르면 MySQL이 받는 SQL은 4개다: `SET autocommit=0`, insert, `COMMIT`, `SET autocommit=1`. 서비스에 트랜잭션이 이미 있으면 거기 합류해서, 끄고 커밋하고 켜는 줄(`SET autocommit`·`COMMIT`)은 서비스 트랜잭션 전체에서 한 번만 나간다(insert는 `save()`마다 나간다).**
   왜: JDBC 연결은 기본으로 문장마다 바로 커밋되는 auto-commit 모드다. `save()`에 붙은 `@Transactional`(repository 프록시의 트랜잭션 인터셉터)이 이를 끄고, insert하고, 커밋한 뒤 다시 켠다.
   바깥 트랜잭션이 있으면 repository 메서드는 거기 참여한다. 실험에서도 한 트랜잭션 안의 여러 repository 호출에 `SET autocommit=0 … COMMIT … SET autocommit=1`이 한 벌만 나갔다. (2:23 general.log)

기억할 한 문장: "JPA와 JDBC는 약속이고 실제 일은 Hibernate와 드라이버가 한다. 덕분에 위층은 아래를 몰라도 되고, MySQL 드라이버 기본값에선 완성된 SQL 문자열이 간다." (2:44 summary.md)

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
npx --yes hyperframes@0.8.209 render -o "output/spring_data_jpa_에서_mysql_까지의_흐름.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/spring_data_jpa_에서_mysql_까지의_흐름.mp4"
ffmpeg -nostats -i "output/spring_data_jpa_에서_mysql_까지의_흐름.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 주제 그림은 칸 6개와 화살표 10개라서 다 짚으면 나열이 된다. 입문자가 이 그림을 보고 물을 질문 하나로 좁혔다:
  "save() 한 줄은 무엇을 거쳐 가고, 왜 칸이 나뉘어 있나". 핵심 답은 "API 칸은 약속, 구현체 칸이 실제 일, 그래서 위층은 아래를 모른다"이고,
  나머지 항목(HikariCP, 완성된 SQL 문자열, 트랜잭션 SQL)은 "실제로 MySQL까지 가 보면 그림과 무엇이 다른가"를 같은 원리로 설명한다.
- 입문자가 보고 나서 할 수 있는 것: JPA·Hibernate·JDBC·드라이버의 차이를 이유와 함께 말하기, 의존성에 무엇을 넣고 DB를 바꿀 때 무엇을 바꾸는지(드라이버 줄 + 접속 주소) 고르기,
  Hibernate 로그엔 `?`가 보이고 실제 값은 드라이버가 이스케이프해서 채운다는 것, 로그에 보이는 HikariPool이 무엇인지, `save()` 하나에도 트랜잭션 SQL이 함께 나간다는 것.
- 연구 기반은 같은 주제로 실험까지 마친 블로그 초안(`z_블로그작성/2_spring_data_jpa_에서_mysql_까지의_흐름/`, 8장)이다. 영상에서는 블로그를 언급하지 않았다.
  블로그 8장 중 영상에 넣은 것: 1장(인터페이스), 2·3장(① ②, Spring 프록시는 한 문장), 4장(③ ④, HikariCP), 5장(⑤ COM_QUERY와 general log), 6장 일부(save의 트랜잭션 SQL 4개), 8장 일부(IDENTITY라 INSERT가 즉시, 보통은 커밋 때 — 한 문장씩).
- 다음 영상 후보(범위를 좁히느라 뺀 것):
  - **SQL은 언제 나가나**: 같은 엔티티를 두 번 `findById`하면 두 번째는 SQL이 안 나감(영속성 컨텍스트), `setName`만 해도 커밋 때 UPDATE가 나감(변경 감지·flush), IDENTITY와 SEQUENCE의 INSERT 시점 차이. 이번 영상은 "보통은 커밋할 때" 한 문장으로만 짚었다.
  - **결과는 어떻게 돌아오나(그림의 "결과 전달")**: OK 패킷의 id → generated key → 엔티티 필드, 행 → `ResultSet` → 엔티티 → `Optional`.
  - **`useServerPrepStmts=true`면 무엇이 바뀌나**: COM_STMT_PREPARE와 바이너리 COM_STMT_EXECUTE, general log의 Prepare/Execute 줄.
  - **`findById`의 readOnly 트랜잭션**: `SET SESSION TRANSACTION READ ONLY`가 Hibernate를 건너 Spring이 직접 보낸다(6개 왕복).
  - **Spring의 공유 EntityManager 프록시를 자세히**: 왜 `final` 필드에 프록시가 들어가는가, 트랜잭션 범위 영속성 컨텍스트.
  - **HikariCP 설정**: 풀 크기, 연결 검사, 누수 감지.

### 쓴 사실과 출처 (2026-10-29 확인, ★는 2026-10-30 리뷰 반영 때 추가 확인)

블로그 초안의 출처 [n]과 실험 기록 E1–E8을 근거로 썼고, 나머지는 직접 공식 문서·소스를 열어 확인했다.

| 영상 속 내용 | 근거 |
|---|---|
| 반복 코드를 줄이는 게 목적(0:17) | docs.spring.io/spring-data/jpa/reference/jpa.html — "The goal of the Spring Data repository abstraction is to significantly reduce the amount of boilerplate code required to implement data access layers for various persistence stores." |
| repository 뒤에 SimpleJpaRepository가 붙는다(0:10) | 실험 E3 1절 `프록시 뒤의 실제 객체 클래스 : org.springframework.data.jpa.repository.support.SimpleJpaRepository` / Spring Data JPA Reference, Custom Repository Implementations [8] |
| ★ `save()`: 새 엔티티면 persist, 아니면 merge(0:21) | Spring Data JPA 4.1.2 소스 SimpleJpaRepository.java [7] `if (entityInformation.isNew(entity)) { entityManager.persist(entity); return entity; } else { return entityManager.merge(entity); }` / docs.spring.io/spring-data/jpa/reference/jpa/entity-persistence.html — "If the entity has not yet been persisted, Spring Data JPA saves the entity with a call to the entityManager.persist(…) method. Otherwise, it calls the entityManager.merge(…) method." / "If the identifier property is null, then the entity is assumed to be new." |
| EntityManager는 JPA 인터페이스, persist는 abstract | Jakarta Persistence 3.2 API [5] "public interface EntityManager", 실험 E3 1절 `EntityManager.persist(Object) 는 abstract? true` |
| 호출하면 그 자리에 든 객체의 메서드가 실행 | JVM Spec SE 25 §6.5 invokeinterface [10] "Let C be the class of objectref. A method is selected with respect to C…" |
| 실제 스택에 JPA 코드 0줄, Spring 프록시 5프레임 뒤 SessionImpl.persist | 실험 E3 2절 `jakarta.persistence.* 프레임 수: 0`, 층별 요약(JDK-PROXY 1 + SPRING-ORM 2 + JDK-REFLECT 2 = 5, 계산 C1) |
| Spring 프록시는 지금 트랜잭션의 EntityManager에 위임 | Spring Framework 7.0.10 SharedEntityManagerCreator [12] "It will delegate all calls to the current transactional EntityManager, if any…" |
| Hibernate가 `?`로 SQL을 만들고 값은 따로 바인딩 | 실험 E3 2절 `DEBUG org.hibernate.SQL : insert into member (name) values (?)`, `TRACE … binding parameter (1:VARCHAR) <- [kim]` |
| ★ IDENTITY라 persist 안에서 바로 insert(1:04) | Hibernate 7.4 User Guide, Using IDENTITY columns [27] "…the entity row must be physically inserted prior to the identifier value being known." / 실험 엔티티 `@GeneratedValue(strategy = GenerationType.IDENTITY)`, E3 스택(`SessionImpl.persist` → … → `ClientPreparedStatement.executeUpdate`)과 시각(INSERT 22.454765가 `save() 반환` 22.464760보다 먼저) |
| ★ 보통 persist는 예약만, insert는 커밋 때(1:09) | docs.hibernate.org/orm/7.4/introduction/html_single/Hibernate_Introduction.html §5.10 "Flushing the session" — "Notice that SQL statements are not usually executed synchronously by methods of the Session interface" / 같은 문서 — "persist() and remove() have no immediate effect on the database, and instead simply schedule a command for later execution." / flush 시점 [11] "By default, a flush is triggered: when the current transaction commits, …" |
| Hibernate는 JDBC 인터페이스만 부름 | javap E7 `invokeinterface … java/sql/PreparedStatement.executeUpdate` |
| JDBC는 DB마다 드라이버를 끼우는 틀 | docs.oracle.com/en/java/javase/25/docs/api/java.sql/java/sql/package-summary.html — "This API includes a framework whereby different drivers can be installed dynamically to access different data sources." / Driver: "The interface that every driver class must implement." |
| `java.sql.Connection`은 JDK 인터페이스, `ConnectionImpl`은 드라이버 jar | 실험 E3 1절 타입 표 |
| 의존성: 스타터가 Spring Data JPA·JPA·Hibernate·HikariCP, MySQL 전용은 드라이버 한 줄 | 실험 E8 의존성 트리(`spring-data-jpa:4.1.2`, `jakarta.persistence-api:3.2.0`, `hibernate-core:7.4.13.Final`, `HikariCP:7.0.2`가 스타터 아래, `mysql-connector-j -> 9.7.0`은 따로) |
| ★ DB를 바꾸면 드라이버 줄과 접속 주소를 바꾼다(1:31) | docs.spring.io/spring-boot/reference/data/sql.html "DataSource Configuration" — "You should at least specify the URL by setting the spring.datasource.url property." / "Spring Boot can deduce the JDBC driver class for most databases from the URL." / 실험 `application.properties`의 `spring.datasource.url=jdbc:mysql://blog-mysql:3306/flow?…` |
| ★ 그 DB에 맞는 SQL은 Hibernate가 골라 만든다(1:35) | Hibernate 7.4 Introduction §2.7 — "The correct Hibernate SQL Dialect will be determined for you automatically." / 실험 E3 시작 로그 `Database dialect: MySQLDialect`(dialect 설정 없음), DDL `create table member (id bigint not null auto_increment, … ) engine=InnoDB` |
| Hibernate와 드라이버 사이에 HikariCP | 실험 E3 2절 스택 `HIBERNATE … ResultSetReturnImpl.executeUpdate` → `HIKARICP … HikariProxyPreparedStatement` → `HIKARICP … ProxyPreparedStatement` → `MYSQL-DRIVER … ClientPreparedStatement` |
| 새 연결엔 네트워크·드라이버 작업이 든다 | dev.mysql.com/doc/connector-j/en/connector-j-usagenotes-j2ee-concepts-connection-pooling.html — "creating new JDBC connections still incurs networking and JDBC driver overhead that will be avoided if connections are recycled." |
| 닫아도 닫지 않고 풀로 반납, 드라이버 연결을 감쌈 | HikariCP 7.0.2 ProxyConnection.close() [16](`poolEntry.recycle()`), 실험 E3 1절 `Hibernate가 받은 Connection : com.zaxxer.hikari.pool.HikariProxyConnection` / `그 안의 드라이버 Connection : com.mysql.cj.jdbc.ConnectionImpl` |
| 드라이버가 `?`를 채운 문자열을 보내고 MySQL도 그 문자열을 받음 | 실험 E3 `[드라이버→MySQL] COM_QUERY [03 00 01] insert into member (name) values ('kim')`, E4 general log `Query | insert into member (name) values ('kim')` / COM_QUERY 형식 [17] |
| 기본 설정에서 드라이버가 직접 채움 | Connector/J Implementation Notes [19] "Client-side prepared statements are used by default…", useServerPrepStmts 기본값 false [20] |
| ★ 채울 때 이스케이프해서 SQL 인젝션을 막음(2:17) | mysql-connector-j 9.7.0 소스 StringValueEncoder.getBytes (github.com/mysql/mysql-connector-j/blob/9.7.0/src/main/protocol-impl/java/com/mysql/cj/protocol/a/StringValueEncoder.java#L102-L109): `if (isEscapeNeededForString(x, stringLength)) { … StringUtils.escapeString(…) … } return StringUtils.getBytesWrapped(x, '\'', '\'', …);` |
| save()를 따로 부르면 SQL 4개 | 실험 E4 general log 22.442343–22.464407 네 줄, 계산 C2(실험은 `CommandLineRunner`에서 바깥 트랜잭션 없이 `save()`를 불렀다) |
| JDBC 연결 기본은 auto-commit | java.sql.Connection [6] "By default a Connection object is in auto-commit mode, which means that it automatically commits changes after executing each statement." |
| save()의 트랜잭션 | SimpleJpaRepository.save의 `@Transactional` [7], Spring Data JPA Transactionality [9], E6 스택(`TransactionInterceptor` → `JpaTransactionManager.doBegin` → … → `setAutoCommit`) |
| ★ 서비스 트랜잭션이 있으면 합류, 끄고 커밋하고 켜는 줄은 한 번만(2:39) | docs.spring.io/spring-data/jpa/reference/jpa/transactions.html — "…to run inside a transaction (participating in an existing one or creating a new one if none are already running). The transaction configuration at the repositories is then neglected, as the outer transaction configuration determines the actual one used." / 실험 E3 4절(`TransactionTemplate` 안에서 `findById` 두 번: `SET autocommit=0` 한 번, `COMMIT`·`SET autocommit=1` 한 번) |

수치는 "SQL 4개", "프레임 0개", "5프레임"뿐이고 모두 실험 출력에서 직접 셌다.

### 화면에 실제 실행 출력을 쓴 곳 (자르거나 줄바꿈만 함)

블로그 실험(Spring Boot 4.1.2, Hibernate 7.4.13.Final, HikariCP 7.0.2, Connector/J 9.7.0, MySQL 8.4.13) 기록에서 가져왔다. 시각·스레드 번호·패키지 이름·열은 잘랐고, 긴 줄은 나눴다. 글자를 바꾸거나 없는 내용을 넣지 않았다.

- MemberRepository.java(0:10): `프록시 뒤의 실제 객체 클래스 : …SimpleJpaRepository`
- EntityManager.java(0:34): `EntityManager.persist(Object) 는 abstract? true`
- stack.txt(0:45): `SPRING-DATA … SimpleJpaRepository.save`, `HIBERNATE … SessionImpl.persist`, `jakarta.persistence.* 프레임 수: 0`(뒤의 `, java.sql.* 프레임 수: 0`은 잘랐다). `… 5프레임`과 `# 5프레임 = Spring 프록시`는 내가 단 주석이다.
- hibernate.log(0:55): `insert into member (name) values (?)`, `binding parameter (1:VARCHAR) <- [kim]`
- types.txt(1:14): 타입 표 두 줄 `java.sql.Connection interface=true jrt:/java.sql`, `com.mysql.cj.jdbc.ConnectionImpl interface=false mysql-connector-j`(가운데 열과 jar 버전 `-9.7.0.jar`는 잘랐다)
- application.properties(1:35): Hibernate 시작 로그 `Database dialect: MySQLDialect`(HHH10001005 블록의 한 줄)
- stack.txt(1:40): 연속된 네 프레임 `HIBERNATE …ResultSetReturnImpl`, `HIKARICP HikariProxyPreparedStatement`, `HIKARICP ProxyPreparedStatement`, `MYSQL-DRIVER ClientPreparedStatement`(메서드 이름 `.executeUpdate`와 패키지는 잘랐다)
- pool.txt(1:58): `Hibernate가 받은 Connection : …hikari.pool.HikariProxyConnection`, `그 안의 드라이버 Connection : com.mysql.cj.jdbc.ConnectionImpl`
- general.log(2:03): 스파이 줄 `COM_QUERY insert into member (name) values ('kim')`(`[드라이버→MySQL]`, `[03 00 01]`은 잘랐다), general log `Query insert into member (name) values ('kim')`
- general.log(2:23): general log 네 줄 `Query SET autocommit=0`, `Query insert into member …`, `Query COMMIT`, `Query SET autocommit=1`

### 예시·소스·그림으로 쓴 것 (실행 출력이 아님)

- flow.txt(0:00): 사용자 그림의 칸 이름을 옮긴 것.
- MemberService.java(0:06): `memberRepository.save(member);`는 설명용 한 줄이다. 실험은 `memberRepository.save(new Member("kim"))`를 `CommandLineRunner`에서 불렀다. 2:38 문장이 "서비스에 트랜잭션이 있으면" 경우를 따로 말한다.
- MemberRepository.java: 실험 코드와 같은 `interface MemberRepository extends JpaRepository<Member, Long>`(줄만 나눔). 코드 세 줄과 실행 출력 세 줄을 한 덩어리로 위에서부터 차례로 친다(아래 "박스 어긋남" 참고).
- SimpleJpaRepository.java(0:21): 4.1.2 소스의 if/else 6줄 그대로(들여쓰기만 2칸). 메서드 시그니처와 `@Transactional`, `Assert.notNull` 줄은 뺐다.
- EntityManager.java: Jakarta Persistence 3.2 API의 선언을 줄인 것(`extends AutoCloseable`와 다른 메서드는 뺐다).
- hibernate.log의 `@GeneratedValue(strategy = GenerationType.IDENTITY)`: 실험 엔티티 `Member`의 소스 그대로(줄만 나눔).
- build.gradle.kts(1:25): 의존성 트리(E8)를 요약한 주석이다. 실제 `build.gradle.kts`의 문법 그대로가 아니다.
- application.properties(1:31): 실험 설정 `spring.datasource.url=jdbc:mysql://blog-mysql:3306/flow?queryInterceptors=com.example.flow.DriverSpy`에서 실험용 쿼리 파라미터를 뺀 것.
- pool.txt 첫 두 줄(`커넥션 풀: 미리 연 연결을 빌려줌`, `close() → 닫지 않고 풀로 반납`): 개념 그림.
- StringValueEncoder.java(2:17): Connector/J 9.7.0 소스를 `…`로 줄인 것(`isEscapeNeededForString(x, stringLength)` → `(x, …)` 등).
- general.log(2:23)의 `# 서비스 트랜잭션 안: SET·COMMIT은 1번만`: 내 주석. 이 경우는 `save()`가 아니라 `findById` 두 번으로 실험했다(E3 4절).
  리뷰가 제안한 문구는 `# 서비스 트랜잭션 안이면: SET·COMMIT은 1번만`(44칸)인데, 박스 전체 글씨가 작아져서 "이면"만 뺀 40칸으로 썼다.
- summary.md: 정리. `(Connector/J 기본값)` 조건을 마지막 줄에 붙였다.

### 그 밖의 결정

- 이야기 구조는 "왜 X일까"형(B-tree 편 방식)에 가깝게, 그림의 칸을 위에서 아래로 따라가며 칸마다 "무엇 + 왜"를 붙였다. 장점·단점 절은 두지 않았다(주제가 "흐름"이라서).
- `pronounce`: Spring Data JPA 스프링 데이터 제이피에이, Spring 스프링, SimpleJpaRepository 심플제이피에이리포지토리, EntityManager 엔티티매니저,
  repository 리포지토리, HikariCP 히카리씨피, Hibernate 하이버네이트, MySQL 마이에스큐엘, JPA 제이피에이, JDBC 제이디비씨, SQL 에스큐엘, save() 세이브, persist 퍼시스트,
  merge 머지, Member 멤버, insert 인서트, autocommit 오토커밋, Java 자바, kim 킴, DB 디비, id 아이디. `say`를 쓴 문장은 없다(단어 수 불일치가 한 번도 나지 않았다).
  `id`는 짧아서 다른 단어 안에서 바뀔 수 있는데, 지금 대본에서 `id`가 들어간 문장은 1:04 하나뿐임을 확인했다.
- 한글로 둔 말: 인터페이스, 프록시, 커넥션 풀, 트랜잭션, 커밋(동사 "커밋되는", "커밋하고", "커밋할 때"), 의존성, 드라이버, 스택, 구현체, 엔티티, 이스케이프, SQL 인젝션의 "인젝션".
  "드라이버"는 MySQL JDBC Driver를 한국어 문장에서 가리킬 때 한글로 썼다(박스의 칸 이름은 `MySQL Driver`). "dialect"는 나레이션에서 말하지 않고 화면에만 `MySQLDialect`로 나온다.
- 길이:
  - 첫 판: 35문장 175.8 s → 연결 문장 넷을 빼고 32문장 166.65 s로 렌더.
  - 리뷰 반영(2026-10-30): 지적 6건을 고치느라 문장 7개와 장면 2개(`application.properties`, `StringValueEncoder.java`)가 늘어 184.3 s가 됐다.
    이유를 말하지 않는 연결 표현만 줄여 34문장 177.13 s가 됐다. 2차 리뷰 반영(2:39 문장을 "끄고 커밋하고 켜는 줄은"으로 고침)으로 177.87 s. 줄인 것: 훅 두 문장을 하나로("Spring Data JPA의 save() 한 줄이, 여섯 칸을 지나 MySQL에 닿는다는 그림이에요."),
    "먼저 Spring Data JPA예요" 삭제와 repository 두 문장 합침, "이 SQL을 JDBC라는, 또 하나의 인터페이스로 넘겨요" 삭제, HikariCP 도입 두 문장을 하나로,
    Spring 프록시·커넥션 풀·MySQL 로그·서비스 합류 문장의 표현 단축. 답안 항목과 '왜' 문장은 빼지 않았다.
- `build.py`의 `chars/s` 경고(stack.txt 38자/s, pool.txt 33자/s, StringValueEncoder.java 33자/s)는 머리 주석을 줄이고 hold를 0.8/0.3/0.8 s로 늘려 없앴다. build.gradle.kts에도 hold 0.7 s를 줬다.
- 썸네일: 제목 `save() 한 줄, / MySQL까지 / 뭘 거쳐 갈까?`(159px, 경고 없음), 부제 `# Spring Data JPA → MySQL`, 제목줄 `❯ cat MemberService.java`. 리뷰 반영 때 문구는 바꾸지 않고 다시 그렸다.

### 리뷰 반영 기록 (2026-10-30, 독립 리뷰 6건)

| # | 지적 | 바꾼 것 |
|---|---|---|
| 1 | "드라이버 줄만 바꾸면 돼요"는 틀림(URL도 바꿔야 하고, Hibernate는 dialect로 DB를 안다) | 1:19 "MySQL의 클래스를 전혀 모른 채" → "MySQL 드라이버 클래스를 모른 채". 1:31 문장을 "드라이버 줄과 접속 주소를 바꿔요" + "그 DB에 맞는 SQL은, Hibernate가 알아서 골라 만들어요"로 바꾸고 `application.properties` 장면(URL + `Database dialect: MySQLDialect`)을 새로 뒀다. |
| 2 | SQL 4개는 바깥 트랜잭션이 없을 때만 | 2:23 "save()만 따로 부르면…넷이에요", 2:33 "save()에 붙은 트랜잭션이 이 모드를 끄고…", 2:39 "서비스에 트랜잭션이 있으면 거기 합류해서, 끄고 커밋하고 켜는 줄은 한 번만 나가요." 추가. 화면 머리말과 주석 한 줄 바꿈. |

2차 리뷰(2026-10-30, 2건):

| # | 지적 | 바꾼 것 |
|---|---|---|
| R1 | 0:10–0:21 MemberRepository.java에서 두 덩어리가 모두 `"at": 0`이라 줄이 섞여 쳐지고, 0:18–0:21에 바탕 판이 글자와 어긋남(첫 줄은 판 위로, 마지막 줄은 판 아래로) | 두 덩어리를 한 덩어리(`"at": 0`)로 합쳐 위에서부터 차례로 치게 했다. 다른 장면에는 같은 `at`을 가진 덩어리가 없음을 확인했다. |
| R2 | 2:38 "이 줄들은 한 번만"이 insert까지 포함하는 것처럼 들림 | 2:39 "서비스에 트랜잭션이 있으면 거기 합류해서, 끄고 커밋하고 켜는 줄은 한 번만 나가요."로, 화면 주석을 `# 서비스 트랜잭션 안: SET·COMMIT은 1번만`으로 바꿈. |
| 3 | 정리에서 "기본 설정" 조건이 빠짐 | 2:50 "MySQL 드라이버 기본값에선 완성된 SQL 문자열이 가요.", 화면 `(Connector/J 기본값)` 줄 추가. |
| 4 | `// ...`가 if/else를 숨김 | 화면을 소스 if/else 6줄로 바꾸고, 0:21 "새 엔티티면 persist, 아니면 merge를 불러요." + 0:26 "지금은 새 Member라서 persist예요." |
| 5 | persist에서 바로 insert는 IDENTITY 때문 | 1:04 "여기선 id를 MySQL이 만들어서, persist 안에서 바로 insert가 나가요." + 1:09 "보통 persist는 예약만 하고, insert는 커밋할 때 나가요." 추가, 화면에 `@GeneratedValue(strategy = GenerationType.IDENTITY)`. |
| 6 | 이스케이프를 말하지 않으면 문자열 연결로 오해 / 마지막 칸은 MySQL DB | 2:03 "마지막 칸" → "Java 쪽 마지막 칸". 2:17 "채울 땐 따옴표 같은 특수문자를 이스케이프해서, SQL 인젝션을 막아요." + `StringValueEncoder.java` 장면 추가. |

## 측정한 것 / 보기만 한 것

- 렌더: 1080x1920, 30 fps, 177.87 s(2:58), 17.9 MB. 3분 한도 안이고 여유는 약 2 s다.
- 오디오: 통합 -13.9 LUFS, 피크 -1.5 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 25건(아래). 다른 종류의 경고는 없었다.
- `build.py`: 마지막 빌드에서 `font down to`, `chars/s` 경고 없음. `thumbnail.py`: 제목 159px, 경고 없음.
- 화면: 리뷰 반영 뒤 장면마다 가운데 시점과 끝 직전(컷 0.15초 전)을 다시 캡처해서 봤다(33장 + build.gradle.kts hold 뒤 2장).
  - 0초 프레임에 첫 박스(그림의 여섯 칸)와 첫 자막이 보인다.
  - **박스 어긋남(고침)**: 리뷰 반영 1차 렌더(177.13 s)에서는 0:10–0:21 MemberRepository.java의 두 덩어리가 같은 시점(`"at": 0`)에 동시에 쳐져서 줄 순서가 섞였고,
    0:18–0:21에는 남색 바탕 판이 글자와 어긋났다(첫 줄 `interface MemberRepository extends`는 판 위로, 마지막 줄 `: …SimpleJpaRepository`는 판 아래로 삐져나옴).
    `build.py`가 두 덩어리의 타이핑 단계를 시간순이 아니라 덩어리 순서로 이어 붙여서, 판 크기 변화가 뒤섞인 것으로 보인다. 그때 나는 장면 가운데 캡처에서 섞여 쳐지는 것을 보고도 놓쳤다.
    한 덩어리로 합친 뒤 그 장면의 시작·1/4·가운데·3/4·끝 프레임과 16개 장면 전부의 끝 프레임(컷 0.15초 전)을 다시 봤다. 지금은 모든 장면에서 글자가 판 안에 있고 넘치지 않는다.
  - 자막은 모두 2줄 안이다. 자막의 기술 용어는 영어로 나온다(한글 음차 없음).
  - 가장 작은 글씨는 stack.txt(1:40, 한 줄 약 41칸)와 SimpleJpaRepository.java(0:21, if/else 줄 약 38칸)다. 캡처에서는 읽혔다.
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - **SimpleJpaRepository로(0:10)**: "심플제이피에이리포지토리"를 한 단어로 붙여 읽게 했다. 뭉개지면 `say`로 띄어 읽게 바꾼다(그때는 자막 단어 수와 맞춰야 한다).
  - **persist, merge(0:21)**: "퍼시스트", "머지". 그리고 "새 Member라서 persist예요"(0:26)
  - **id를(1:04)**: "아이디를"로 읽히는지
  - **이스케이프해서, SQL 인젝션을(2:17)**: 한글 그대로 읽힌다. "에스큐엘 인젝션"으로 자연스러운지
  - save()(0:00, 0:21, 2:23, 2:33)가 "세이브"로, EntityManager의 persist(0:29)가 "엔티티매니저의 퍼시스트"로 읽히는지
  - repository(0:10), Hibernate(0:55 등), insert SQL을(0:55), insert가(1:04, 1:09), kim은/kim으로(1:00, 2:03), JDBC는(1:14), Java에/Java 쪽(1:14, 2:03), DB마다/DB로(1:14, 1:31), HikariCP라는(1:40), autocommit(2:28), insert한(2:33)
  - 숫자는 대본에 없다. "Dialect"는 말하지 않는다.

## 일부러 남긴 경고

`line_unread` 25건. 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: `memberRepository.save(member);`를 26단어로 셈). 실제로는 대부분 한두 단어짜리 코드 줄이다.

- shot-02 `memberRepository.save(member);`(4.71 s), `// 칸마다 무슨 일을 할까?`(1.91 s)
- shot-03 `: …SimpleJpaRepository`(3.38 s): 덩어리를 합치면서 새로 생겼다. 나레이션 첫 문장이 "SimpleJpaRepository로 붙여 줘요"라고 말한다.
- shot-04 `return entityManager.merge(entity);`(3.56 s)
- shot-07 `strategy = GenerationType.IDENTITY)`(5.93 s)
- shot-08 타입 표 두 줄(5.51 s, 3.31 s)
- shot-09 의존성 네 줄(`spring-boot-starter-data-jpa` 5.60, `Hibernate, HikariCP` 3.40, `mysql-connector-j` 2.57, `MySQL 전용은 이 줄뿐` 1.76 s). `MySQL 전용은 이 줄뿐`(1.76 s)이 가장 짧은데, 나레이션이 같은 말("MySQL 전용은 드라이버 한 줄뿐이에요")을 한다.
  hold 0.7 s를 줬지만 `build.py`가 타이핑을 창의 80%로 늘려서 0.2 s만 늘었다.
- shot-10 `Database dialect: MySQLDialect`(3.09 s)
- shot-11 스택 네 줄(5.90, 4.84, 3.49, 2.37 s)
- shot-12 Connection 네 줄(4.90, 4.10, 2.83, 2.11 s)
- shot-14 Connector/J 소스 네 줄(5.14, 3.90, 2.90, 2.07 s)
- shot-16 `(Connector/J 기본값)`(3.09 s)

더 줄이려면 장면마다 hold를 늘려야 하는데, 3분까지 여유가 약 2 s라 그대로 뒀다.

## 가장 약한 부분

- **길이 2:58**: 3분 한도까지 약 2 s다. 앞으로 문장을 더하려면 다른 장면을 빼야 한다. 1순위 후보는 Spring 프록시 문장(0:49)과 커넥션 풀의 "인터페이스 덕분에…"(1:58)다.
- **StringValueEncoder.java 장면(2:17)**: 입문자에게 소스 코드 네 줄은 무겁고 4.8 s 만에 지나간다. 나레이션이 핵심(이스케이프 → SQL 인젝션 방지)을 말하므로 화면은 근거 표시 역할이다.
  "SQL 인젝션을 막아요"는 문자열 값의 이스케이프 동작(소스)에서 나온 말이고, Connector/J 문서에서 그 문장을 직접 찾지는 않았다. `NO_BACKSLASH_ESCAPES` 모드에서는 다른 코드 경로(`escapeBytesIfNeeded`)를 탄다는 것도 말하지 않았다.
- **"보통 persist는 예약만 하고, insert는 커밋할 때 나가요"(1:09)**: flush는 커밋 때 말고도 결과에 영향받는 쿼리 전, `flush()` 직접 호출 때도 일어난다. 영상은 기본 경우(커밋)만 말했다. IDENTITY 외의 방식(SEQUENCE 등)으로 직접 돌려 보지는 않았다.
- **"서비스에 트랜잭션이 있으면 거기 합류해서, 끄고 커밋하고 켜는 줄은 한 번만 나가요"(2:39)**: 실험은 `TransactionTemplate` 안에서 `findById` 두 번으로 확인했다. `@Transactional` 서비스 안의 `save()`로 직접 돌려 보지는 않았다(문서의 "participating in an existing one"과 같은 원리).
- **"그 DB에 맞는 SQL은, Hibernate가 알아서 골라 만들어요"(1:35)**: 기본 SQL 문법은 dialect가 맞춰 주지만, 네이티브 쿼리나 DB 전용 함수를 쓴 코드는 직접 바꿔야 한다. 다른 DB로 바꿔 돌려 보지는 않았다.
- **Spring 프록시**: 한 문장("지금 트랜잭션의 Hibernate 객체에 넘겨 줄 뿐")으로만 다뤘다. 왜 프록시가 필요한지(필드는 `final`인데 영속성 컨텍스트는 트랜잭션마다 따로)는 말하지 않았다.
- **HikariCP가 감싸는 이유**: 소스로 확인한 `close()` 동작만 말했다. "새 연결엔 네트워크와 드라이버 작업이 든다"는 Connector/J 문서 그대로지만, 같은 문서는 "MySQL은 연결이 빨라서 보통 큰 문제는 아니다"라고도 한다. 영상은 이 단서를 말하지 않았다.
- 결과가 돌아오는 길(그림의 "결과 전달")은 다루지 않았다. 그림의 아래 절반이 영상에서 빠진 셈이다(다음 영상 후보).
