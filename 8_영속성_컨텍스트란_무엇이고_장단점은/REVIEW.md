# REVIEW

## 시청 후 답할 수 있는 것

질문: **영속성 컨텍스트가 무엇이고, 장단점은 무엇인가요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **영속성 컨텍스트는 EntityManager마다 하나씩 있는, 관리 중(managed)인 엔티티 묶음이다. DB에서 읽어 오거나 save()로 새로 저장한 엔티티가 들어가고, id가 같은 Member는 객체가 하나뿐이다.**
   왜: JPA 3.2 명세의 정의가 "같은 영속 식별자마다 엔티티 인스턴스가 하나인 집합"이고, Hibernate가 식별자와 객체를 짝지어 들고 있다. (0:17 context.txt 그림)
2. **수명: 웹 요청 밖에선 트랜잭션이 시작될 때 EntityManager가 열리고 끝나면 닫혀서, 컨텍스트도 트랜잭션 하나 동안만 산다. 웹 요청에선 Spring Boot 기본값 open-in-view가 요청이 끝날 때까지 열어 둔다.**
   왜: `JpaTransactionManager`가 트랜잭션 시작 때 EntityManager를 새로 열어 스레드에 묶고 끝나면 닫는다(6번 영상에서 실험). 웹(서블릿) 앱이면 Boot가 `OpenEntityManagerInViewInterceptor`를 기본으로 등록해 요청 시작에 열고, 트랜잭션들이 그걸 같이 쓴다. (0:35 lifetime.txt 그림)
3. **장점: 같은 트랜잭션에서 같은 id를 다시 찾으면 SELECT 없이 같은 객체를 준다(1차 캐시). 다만 다른 요청과 나눠 쓰지 않아 다음 요청은 다시 SELECT한다.**
   왜: `findById`(→ `em.find`)가 컨텍스트부터 보고 없을 때만 DB에 간다. 컨텍스트는 요청·트랜잭션마다 새로 만들어진다. (0:51 find-twice.log)
4. **장점: 관리 중인 엔티티는 setName만 해도 커밋 때 save() 없이 UPDATE된다(변경 감지).**
   왜: 기본 설정에선 읽어 올 때 값의 사본(스냅샷)을 같이 두고, 커밋 직전에 지금 값과 비교해 달라진 엔티티만 UPDATE를 만든다. (0:00 훅, 1:08 snapshot.txt 그림)
5. **SQL이 나가는 때: 변경은 모아 뒀다가 플러시 때 보낸다. 기본은 커밋 직전, 그리고 바뀐 테이블을 읽는 JPQL 직전이다. 단 IDENTITY 키의 INSERT는 save() 순간 바로 나간다.**
   왜: 기본 플러시 모드(AUTO)는 쿼리 결과에 아직 안 보낸 변경이 보여야 해서 그 쿼리 앞에서도 플러시한다. IDENTITY는 id를 받으려면 행을 먼저 넣어야 한다. (1:25 when.txt 그림, 1:40 flush.log)
6. **단점: 저장할 생각이 없던 변경도 저장된다. 대처는 보여 줄 값을 엔티티를 바꾸지 말고 따로 만드는 것이다. readOnly만으론 못 막는다.**
   왜: 4번과 같은 원리다. readOnly는 그 트랜잭션의 플러시만 끄는데, 같은 컨텍스트를 쓰는 쓰기 트랜잭션(바깥 트랜잭션, open-in-view에서 같은 요청의 다음 트랜잭션)이 바뀐 값을 보낼 수 있다. (1:48 MemberService.java, 1:58 fix.txt 그림)
7. **단점: 많이 읽으면 엔티티가 컨텍스트가 닫힐 때까지 쌓이고, 플러시마다 관리 중인 엔티티를 전부 비교한다. 대처는 배치에서 일정 개수마다 flush() 다음 clear()다(clear()만 하면 안 보낸 변경이 버려지므로 flush()가 먼저).**
   왜: 컨텍스트는 엔티티를 강한 참조로 붙잡고, 플러시는 관리 중인 엔티티마다 스냅샷과 비교한다. 1000개씩 10번 읽어 바꾸면 마지막 플러시는 10000개를 본다. (2:09 batch.log, 2:23 batch.txt 그림)

기억할 한 문장: "영속성 컨텍스트는 엔티티와 스냅샷을 들고 있다가, 플러시 때 바뀐 것만 SQL로 보낸다. 덕분에 관리 중인 엔티티는 커밋 때 save() 없이 수정되지만, 원치 않는 UPDATE와 쌓이는 엔티티는 직접 챙긴다." (2:33 summary.md 그림)

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
npx --yes hyperframes@0.8.209 render -o "output/영속성_컨텍스트란_무엇이고_장단점은.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/영속성_컨텍스트란_무엇이고_장단점은.mp4"
ffmpeg -nostats -i "output/영속성_컨텍스트란_무엇이고_장단점은.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 주제 "영속성 컨텍스트란 무엇인지, 장단점"을 기본형 질문 하나로 잡았다. 뼈대는 훅(save() 없이 UPDATE) → 정의 → 수명 → 장점 둘(같은 객체·1차 캐시, 변경 감지) → SQL이 나가는 때(플러시) → 단점 둘(원치 않는 UPDATE, 쌓이는 엔티티) → 정리다.
  장단점은 팁 목록이 아니라 "id마다 객체 하나 + 스냅샷 + 플러시 때 비교 + 컨텍스트 수명"이라는 구조의 결과로만 넣었다.
- 5번 영상(save()가 persist로 가고 IDENTITY라 insert가 바로 나감)과 6번 영상(트랜잭션 매니저가 EntityManager를 열어 스레드에 묶음)의 내용은 다시 가르치지 않았다. 처음엔 첫 문장 "지난 영상의 MemberService에"와 IDENTITY 문장 "지난 영상처럼"으로 이었는데, 사용자가 지난 영상 얘기를 하지 말라고 해서 고쳤다(아래 "지난 영상 언급 삭제").
- 입문자가 보고 나서 할 수 있는 것: "관리 중"이 뭔지 말하기(컨텍스트 안에 든 상태), SQL이 언제 MySQL로 가는지 예측하기(조회는 컨텍스트에 없을 때, 수정은 커밋 직전·관련 JPQL 직전, IDENTITY insert는 save() 때), save() 없이 UPDATE된 이유 설명하기, 화면용 값을 엔티티에 쓰지 않기, 배치에서 flush()+clear()를 언제·왜 하는지 고르기.
- 다음 영상 후보(범위를 좁히느라 뺀 것):
  1. **open-in-view를 켜 두면 생기는 일**(1순위): 요청 내내 같은 컨텍스트, 트랜잭션 밖(컨트롤러)에서의 지연 로딩과 `LazyInitializationException`, readOnly 트랜잭션에서 바꾼 값을 같은 요청의 다음 쓰기 트랜잭션이 내보내는 문제(아래 "가장 약한 부분"에 실험 결과).
  2. **벌크 연산과 컨텍스트 불일치**: JPQL 벌크 UPDATE 뒤 이미 읽어 둔 엔티티는 옛 값(실험함, 아래 "확인했지만 넣지 않은 것"), `@Modifying(clearAutomatically/flushAutomatically)`.
  3. **detached와 merge**: 트랜잭션 밖에서 바꾼 엔티티, `save()`가 merge를 부를 때.
  4. **지연 로딩과 N+1**.
  5. **대량 처리**: StatelessSession, JDBC 배치, IDENTITY에선 insert 배치가 꺼지는 이유.

### 실험 환경과 재현 (2026-11-02)

- 호스트: macOS 26.5.1 (25F80), arm64, Docker client/server 29.9.2. 앱은 호스트 JDK 25.0.4 + Gradle wrapper 9.8.2로 빌드하고 컨테이너에서 실행했다(5·6번 영상과 같은 방식).
- 이미지: `mysql:8.4` (`sha256:a0225d1ea6631c8bc2385dc4c2faba17bbf1834ecf369e1659a9a382bd8d5dd7`, `SELECT VERSION()` → 8.4.13, `@@global.autocommit`=1, `transaction_isolation`=REPEATABLE-READ), `eclipse-temurin:25-jre` (`sha256:78f1f183913482ef390c2722f46c3f0ce76ada341d69590e7c482ec943ee72d5`, `java -version` → 25.0.4.1, Temurin-25.0.4.1+1). 전용 네트워크 `pc-net`, MySQL 컨테이너 `pc-mysql`, 호스트에 포트를 열지 않았다. general log는 `log_output=TABLE`.
- 앱이 찍은 버전: Java 25.0.4.1, Spring Boot 4.1.2, Spring Framework 7.0.10, Spring Data JPA 4.1.2 (`spring-data-jpa-4.1.2.jar`), Jakarta Persistence 3.2.0, Hibernate ORM 7.4.13.Final, HikariCP 7.0.2, MySQL Connector/J 9.7.0, MySQL 8.4.13.
- `build.gradle.kts`: 플러그인 `org.springframework.boot` 4.1.2, `io.spring.dependency-management` 1.1.7, toolchain Java 25. 의존성 `spring-boot-starter-data-jpa`, `spring-boot-starter-webmvc`(open-in-view 확인용), `com.mysql:mysql-connector-j`. Hibernate 바이트코드 향상 플러그인은 없다.
- `application.properties`:

```properties
spring.datasource.url=jdbc:mysql://pc-mysql:3306/pcdemo?queryInterceptors=com.example.pc.DriverSpy
spring.datasource.username=root
spring.datasource.password=
spring.jpa.hibernate.ddl-auto=create
spring.main.banner-mode=off
logging.level.org.hibernate.SQL=debug
logging.level.org.hibernate.orm.event=debug
logging.level.org.springframework.orm.jpa.JpaTransactionManager=debug
logging.level.org.springframework.orm.jpa.support.OpenEntityManagerInViewInterceptor=debug
logging.pattern.console=%d{HH:mm:ss.SSS} %-5level %logger{36} : %msg%n
```

  - `DriverSpy`는 Connector/J `queryInterceptors` 확장점이다. 패킷을 소켓에 쓰기 직전(`preProcess(M packet)`)에 COM_QUERY의 SQL을 `HH:mm:ss.SSSSSS [드라이버→MySQL] <SQL>`로 찍는다. 앱 쪽 표시는 `[앱] …`. 그래서 앱 호출과 실제로 나간 SQL의 순서를 한 로그에서 본다.
  - `org.hibernate.orm.event=debug`는 `HHH90060071: Flushed: I insertions, U updates, D deletions to N objects` 줄을 찍는다(N = 그때 관리 중인 엔티티 수).
  - **`spring.jpa.open-in-view`는 적지 않았다**(기본값을 보려고). 웹이 아닌 시나리오는 `--spring.main.web-application-type=none`으로 돌렸다(앱 출력 `웹 애플리케이션 종류 : none`, `OpenEntityManagerInViewInterceptor 빈 수 : 0`).
- 엔티티·리포지토리(그대로):

```java
@Entity public class Member {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    private String name;
    protected Member() {}
    public Member(String name) { this.name = name; }
    // getId, getName, setName
}
@Entity public class Team { @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id; private String name; }   // Member와 상관없는 테이블

public interface MemberRepository extends JpaRepository<Member, Long> {
    List<Member> findByName(String name);
    List<Member> findByIdBetween(Long from, Long to);
    @Modifying @Query("update Member m set m.name = :name") int renameAll(@Param("name") String name);
    @Modifying(clearAutomatically = true) @Query("update Member m set m.name = :name") int renameAllAndClear(@Param("name") String name);
}
public interface TeamRepository extends JpaRepository<Team, Long> {}
```

- 실험 서비스 코드(출력용 `Probe.*` 줄 빼고 그대로). `em`은 `@PersistenceContext EntityManager`(Spring 공유 프록시):

```java
@Transactional public void rename(Long id, String name) {
    Member member = memberRepository.findById(id).orElseThrow();
    member.setName(name);
}
@Transactional public void findTwice(Long id) {
    Member a = memberRepository.findById(id).orElseThrow();
    Member b = memberRepository.findById(id).orElseThrow();
    List<Member> list = memberRepository.findByName("kim");
}
@Transactional public Member findOnce(Long id) { return memberRepository.findById(id).orElseThrow(); }
@Transactional public void readAndJoin(Long id, String name) {
    Member kim = memberRepository.findById(id).orElseThrow();
    Member choi = memberRepository.save(new Member(name));
}
@Transactional public void renameThenQuery(Long id) {
    Member member = memberRepository.findById(id).orElseThrow();
    member.setName("lee");
    long teams = teamRepository.count();
    List<Member> found = memberRepository.findByName("lee");
}
@Transactional public void join(String name) { memberRepository.save(new Member(name)); }
@Transactional public String greeting(Long id) {
    Member member = memberRepository.findById(id).orElseThrow();
    member.setName(member.getName() + "님");   // 화면에 '님'을 붙여 보여 주려고
    return member.getName();
}
@Transactional(readOnly = true) public String greetingReadOnly(Long id) { /* greeting과 같은 본문 */ }
@Transactional public String greetingNoChange(Long id) {
    Member member = memberRepository.findById(id).orElseThrow();
    String shown = member.getName() + "님";   // 엔티티는 그대로, 보여 줄 값만 따로
    return shown;
}
@Transactional public void renameThenClear(Long id) {
    Member member = memberRepository.findById(id).orElseThrow();
    member.setName("lee");
    em.clear();
}
@Transactional public void batch(long total, int chunk, boolean flushAndClear) {
    for (long from = 1; from <= total; from += chunk) {
        List<Member> members = memberRepository.findByIdBetween(from, from + chunk - 1);
        for (Member m : members) m.setName(m.getName() + "!");
        if (flushAndClear) { em.flush(); em.clear(); }
    }
}
// 다른 빈 OuterService
@Transactional public String outerCallsReadOnly(Long id) { return memberService.greetingReadOnly(id); }
// 웹: MemberController (@Transactional 없음)
@GetMapping("/members/{id}/twice") String twice(Long id) { Member a = memberService.findOnce(id); Member b = memberService.findOnce(id); return "a==b " + (a == b); }
@GetMapping("/members/{id}/readonly-then-write") String readOnlyThenWrite(Long id) { String g = memberService.greetingReadOnly(id); memberService.join("choi"); return g; }
```

- 시나리오마다 앱을 한 번씩 실행했다(실행마다 테이블을 새로 만들고, 먼저 `kim`(id 1) 한 행을 스파이를 끈 채 저장). 실행 전 `TRUNCATE TABLE mysql.general_log`, 실행 뒤 general log(`SELECT … FROM mysql.general_log WHERE user_host NOT LIKE '%localhost%' ORDER BY event_time`)와 `SELECT id, name FROM pcdemo.member`(mysql CLI)를 남겼다. 배치 시나리오는 `kim` 대신 `m1…m10000` 1만 행을 네이티브 SQL로 넣었다.

```bash
docker network create pc-net
docker run -d --name pc-mysql --network pc-net -e MYSQL_ALLOW_EMPTY_PASSWORD=yes -e MYSQL_DATABASE=pcdemo mysql:8.4
docker exec -i pc-mysql mysql -uroot -e "SET GLOBAL log_output='TABLE'; SET GLOBAL general_log='ON';"
docker run --rm --network pc-net -v "$PWD/build/libs:/app:ro" eclipse-temurin:25-jre \
  java -jar /app/pc.jar --pc.scenario=rename --spring.main.web-application-type=none --pc.capture=update
#  시나리오: rename identity both flush insert greeting greetingro greetingnc outerro clearonly bulk bulkclear
#           batch(--pc.flushClear=false|true) memory(--pc.total=100000)  [모두 web-application-type=none]
#           osiv (웹, open-in-view 설정 안 함) / osiv --spring.jpa.open-in-view=false
```

- 시나리오별 결과(드라이버가 MySQL로 보낸 것 = general log와 같은 순서, 실행 뒤 행):

| 시나리오 | MySQL이 받은 것(트랜잭션 안) | 실행 뒤 |
|---|---|---|
| `rename(1, "lee")` | `SET autocommit=0` / `select … where m1_0.id=1` / `update member set name='lee' where id=1` / `COMMIT` / `SET autocommit=1` | `1 \| lee` |
| `findTwice(1)` | select `id=1` 한 번, JPQL `select … where m1_0.name='kim'` 한 번, `COMMIT` | `1 \| kim` |
| `findOnce(1)` × 2 (트랜잭션 따로) | 트랜잭션마다 select `id=1` (두 번) | `1 \| kim` |
| `readAndJoin(1, "choi")` | select `id=1` / `insert into member (name) values ('choi')` / `COMMIT` | `kim`, `choi` |
| `renameThenQuery(1)` | select `id=1` / `select count(*) from team t1_0` / `update member set name='lee' where id=1` / `select … where m1_0.name='lee'` / `COMMIT` | `1 \| lee` |
| `join("choi")` | `insert into member (name) values ('choi')`(save() 반환 전) / `COMMIT` | `kim`, `choi` |
| `greeting(1)` | select / `update member set name='kim님' where id=1` / `COMMIT` | `1 \| kim님` |
| `greetingReadOnly(1)` | `SET SESSION TRANSACTION READ ONLY` / select / `COMMIT`(update 없음) | `1 \| kim` |
| `greetingNoChange(1)` | select / `COMMIT`(update 없음) | `1 \| kim` |
| `outerCallsReadOnly(1)`(바깥 쓰기 트랜잭션) | select / `update member set name='kim님' where id=1` / `COMMIT` (READ ONLY 줄 없음) | `1 \| kim님` |
| `renameThenClear(1)` | select / `COMMIT`(update 없음) | `1 \| kim` |
| `batch(10000, 1000, false)` | 1000개씩 select 10번, update 10000번, 플러시 로그 `to 1000 … 10000 objects` | 이름 끝에 `!` |
| `batch(10000, 1000, true)` | 같은 SQL, 플러시 로그는 매번 `to 1000 objects`, clear 뒤 관리 중 0개 | 이름 끝에 `!` |
| 웹 `GET /members/1/twice` ×2, open-in-view 기본 | 요청마다 select `id=1` 한 번(트랜잭션 둘이 한 EntityManager) | `1 \| kim` |
| 웹 같은 요청, `open-in-view=false` | 트랜잭션마다 select `id=1`(요청마다 두 번) | `1 \| kim` |
| 웹 `readonly-then-write`, open-in-view 기본 | readOnly 트랜잭션: select, `COMMIT` / 다음 트랜잭션: `insert … ('choi')`, `update member set name='kim님' where id=1`, `COMMIT` | `kim님`, `choi` |
| 웹 `readonly-then-write`, `open-in-view=false` | readOnly: select, `COMMIT` / 다음: `insert … ('choi')`, `COMMIT`(update 없음) | `kim`, `choi` |

### 쓴 사실과 출처 (2026-11-02 확인)

출처는 실행한 버전의 태그로 고정했다. 약칭:
- **JPA** = Jakarta Persistence 3.2 명세 https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.html
- **JPAAPI** = `https://github.com/jakartaee/persistence/blob/3.2-3.2.0-RELEASE/api/src/main/java/jakarta/persistence/` (런타임 jar `jakarta.persistence-api-3.2.0`과 같은 릴리스. jakarta.ee의 apidocs 페이지는 404라 소스의 javadoc을 인용)
- **HIB** = `https://github.com/hibernate/hibernate-orm/blob/7.4.13/`, **HIBDOC** = HIB + `documentation/src/main/asciidoc/` (docs.hibernate.org/orm/7.4 원문. 게시된 HTML은 7.4.15판이라 태그의 adoc를 인용)
- **SF** = `https://github.com/spring-projects/spring-framework/blob/v7.0.10/`, **SFD** = SF + `framework-docs/modules/ROOT/pages/`
- **SB** = `https://github.com/spring-projects/spring-boot/blob/v4.1.2/`
- **SDJ** = `https://github.com/spring-projects/spring-data-jpa/blob/4.1.2/`

로그 줄은 시각만 빼고 그대로 옮겼다. `[드라이버→MySQL]`은 드라이버 스파이, `[앱]`은 실험 코드의 출력이다.

| 영상 속 내용 | 근거 |
|---|---|
| rename은 찾아서 setName만, save() 호출 없음(0:00, 0:04) | 실험 코드 `rename`(위) / 출력 `[앱] [rename 본문 끝] save() 호출 없음. FlushMode=AUTO, defaultReadOnly=false` |
| MySQL 로그에 UPDATE, 이름이 실제로 바뀜(0:08) | general log `Query select m1_0.id,m1_0.name from member m1_0 where m1_0.id=1` / `Query update member set name='lee' where id=1` / `Query COMMIT`, mysql CLI `1 \| lee` |
| save() 없이 저장된 건 영속성 컨텍스트 때문(0:13) | HIBDOC `introduction/Interacting.adoc#L72-L73` "They enable _automatic dirty checking_: after modifying an entity, we don't need to perform any explicit operation to ask Hibernate to propagate that change back to the database. Instead, the change will be automatically synchronized with the database when the session is flushed." / 커밋 중 로그 `HHH90060071: Flushed: 0 insertions, 1 updates, 0 deletions to 1 objects` / UPDATE를 보내는 순간의 스택(위가 먼저): `TransactionAspectSupport.commitTransactionAfterReturning(…:687)` → `AbstractPlatformTransactionManager.commit` → `JpaTransactionManager.doCommit(JpaTransactionManager.java:552)` → `TransactionImpl.commit` → `JdbcResourceLocalTransactionCoordinatorImpl.beforeCompletionCallback` → `SessionImpl.flushBeforeTransactionCompletion(SessionImpl.java:2104)` → `SessionImpl.managedFlush` → `DefaultFlushEventListener.onFlush` → `AbstractFlushingEventListener.performExecutions` → `EntityUpdateAction.execute` → … → `ResultSetReturnImpl.executeUpdate` |
| EntityManager마다 하나씩 있는 엔티티 묶음(0:17) | JPA §3.1 (#overview) "Every instance of EntityManager has an associated persistence context. A persistence context is a set of entity instances in which for any given persistent entity identity there is a unique entity instance. Within the persistence context, the entity instances and their lifecycle are managed." / §7.1 (#a11432) "A persistence context is a set of managed entity instances …" |
| DB에서 읽거나 save()로 새로 저장한 엔티티가 들어감(0:22) | HIBDOC Interacting.adoc#L43 "For every entity instance read from the database within the scope of a persistence context, and for every new entity made persistent within the scope of the persistence context, the context holds a unique mapping from the identifier of the entity instance to the instance itself." / 새 엔티티 save()는 persist: SDJ `spring-data-jpa/src/main/java/org/springframework/data/jpa/repository/support/SimpleJpaRepository.java#L659-L669` `if (entityInformation.isNew(entity)) { entityManager.persist(entity); return entity; } else { return entityManager.merge(entity); }` / readAndJoin 출력: `[드라이버→MySQL] select … where m1_0.id=1` → `[앱] findById(1) 뒤 관리 중 엔티티 수=1, em.contains? true` → `[드라이버→MySQL] insert into member (name) values ('choi')` → `[앱] save(new Member("choi")) 뒤 관리 중 엔티티 수=2, em.contains? true`, `[앱]   컨텍스트 안: EntityKey[com.example.pc.Member with id '2'] → Member(name=choi)`, `[앱]   컨텍스트 안: EntityKey[com.example.pc.Member with id '1'] → Member(name=kim)`. JPQL로 읽은 것도 들어감: 배치 출력 `id 1~1000 처리 뒤 관리 중 엔티티 수=1000`(`findByIdBetween`) |
| id가 같은 Member는 객체도 하나(0:27) | JPA §3.1 위 인용 / HIBDOC Interacting.adoc#L43 "unique mapping from the identifier … to the instance itself" / 출력 `(2) 반환: (1)과 같은 객체인가(a == b)? true, 관리 중 엔티티 수=1`, `같은 id로 다시 findById(1) == 처음 객체? true`. 명세의 식별자는 엔티티 종류 + id라서 "Member는"으로 범위를 묶었다 |
| 묶음 안에 든 상태 = 관리 중, managed(0:30) | JPA §3.3 (#a1929) "A managed entity instance is an instance with a persistent identity that is currently associated with a persistence context." / 출력 `findById 반환: name=kim, em.contains(member)? true`, `스냅샷: 상태=MANAGED` |
| 웹 요청 밖: 트랜잭션 시작에 EntityManager 열림, 끝나면 닫힘(0:35) | SF `spring-orm/src/main/java/org/springframework/orm/jpa/JpaTransactionManager.java#L395-L404`(doBegin: 묶인 것이 없으면 `createEntityManagerForTransaction()`, `logger.debug("Opened new EntityManager [" + newEm + "] for JPA transaction")`), `#L443-L446`(`// Bind the entity manager holder to the thread.`), `#L609-L646`(doCleanupAfterCompletion: 새로 연 것이면 `logger.debug("Closing JPA EntityManager after transaction"); … closeAll();`) / 출력 순서 `[앱] memberService.rename(1, "lee") 호출` → `Opened new EntityManager [SessionImpl(2101594271<open>)] for JPA transaction` → … → `Closing JPA EntityManager after transaction` → `[앱] rename() 반환` (이 실행은 `웹 애플리케이션 종류 : none`) |
| 컨텍스트도 트랜잭션 하나 동안(0:41) | HIBDOC Interacting.adoc#L55 "The lifetime of a persistence context usually corresponds to the lifetime of a transaction …" / JPA §3.4.2 (#transaction-commit) "The managed entities of a transaction-scoped persistence context become detached when the transaction commits" / 트랜잭션 따로 두 번: `[findOnce] 세션=SessionImpl@10bae3c0 …`, `[findOnce] 세션=SessionImpl@5fc3dfc1 …`, select 두 번, `두 트랜잭션에서 받은 객체가 같은가(a == b)? false` |
| 웹 요청: Boot 기본값 open-in-view가 요청 끝까지 열어 둠(0:45, 그림 머리 "웹 요청 (기본값)") | SB `module/spring-boot-jpa/src/main/java/org/springframework/boot/jpa/autoconfigure/JpaBaseConfiguration.java#L231-L236` `@ConditionalOnWebApplication(type = Type.SERVLET)` `@ConditionalOnClass(WebMvcConfigurer.class)` … `@ConditionalOnBooleanProperty(name = "spring.jpa.open-in-view", matchIfMissing = true)`, `#L249-L252` `if (this.jpaProperties.getOpenInView() == null) { logger.warn("spring.jpa.open-in-view is enabled by default. Therefore, database queries may be performed during view rendering. …")` / `JpaProperties.java#L62-L66` "Register OpenEntityManagerInViewInterceptor. Binds a JPA EntityManager to the thread for the entire processing of the request." / spring-boot-jpa-4.1.2.jar 속성 메타데이터 `spring.jpa.open-in-view` `"defaultValue": true` / SB `documentation/spring-boot-docs/src/docs/antora/modules/reference/pages/data/sql.adoc#L339-L342` "If you are running a web application, Spring Boot by default registers OpenEntityManagerInViewInterceptor to apply the "Open EntityManager in View" pattern, to allow for lazy loading in web views." / SF `spring-orm/src/main/java/org/springframework/orm/jpa/support/OpenEntityManagerInViewInterceptor.java#L37-L41` "binds a JPA EntityManager to the thread for the entire processing of the request", `#L85-L90`(preHandle: `createEntityManager()` 후 `bindResource`), `#L107-L112`(afterCompletion: 닫기) / 웹 실행(설정 안 함): 시작 로그 `WARN o.s.b.j.a.JpaBaseConfiguration$JpaWebConfiguration : spring.jpa.open-in-view is enabled by default. Therefore, database queries may be performed during view rendering. Explicitly configure spring.jpa.open-in-view to disable this warning`, `OpenEntityManagerInViewInterceptor 빈 수 : 1`, 요청 중 `Opening JPA EntityManager in OpenEntityManagerInViewInterceptor` → 두 트랜잭션 모두 `Found thread-bound EntityManager [SessionImpl(723744907<open>)] for JPA transaction`, `[findOnce] 세션=SessionImpl@2b23788b` ×2, `Not closing pre-bound JPA EntityManager after transaction` → `Closing JPA EntityManager in OpenEntityManagerInViewInterceptor` / `open-in-view=false`: `빈 수 : 0`, 트랜잭션마다 `Opened new EntityManager` |
| 같은 트랜잭션에서 같은 id를 다시 찾으면 SELECT 없이 같은 객체(0:51) | 출력 `(1) findById(1) 호출` → `[드라이버→MySQL] select m1_0.id,m1_0.name from member m1_0 where m1_0.id=1` → `(2) findById(1) 다시 호출` → `(2) 반환: (1)과 같은 객체인가(a == b)? true` (사이에 드라이버 줄 없음) |
| findById가 컨텍스트부터, 없을 때만 DB / 1차 캐시(0:56) | SDJ SimpleJpaRepository.java#L328-L343 `findById` → `entityManager.find(domainType, id)` / JPAAPI `EntityManager.java#L260-L265` "Find by primary key. Search for an entity of the specified class and primary key. If the entity instance is contained in the persistence context, it is returned from there." / HIB `hibernate-core/src/main/java/org/hibernate/event/internal/DefaultLoadEventListener.java#L496-L526` `loadFromSessionCache(…)` 먼저, 없으면 `load` → `loadFromCacheOrDatasource`(#L550-L554, 2차 캐시 → DB) / HIBDOC Interacting.adoc#L42 "A persistence context is a sort of cache; we sometimes call it the "first-level cache" …" |
| 다른 요청과 나눠 쓰지 않음, 다음 요청은 다시 SELECT(1:03) | 웹 실행(open-in-view 기본): 요청 2에서 `Opening JPA EntityManager …` 새로, `[드라이버→MySQL] select m1_0.id,m1_0.name from member m1_0 where m1_0.id=1`, `세션=SessionImpl@6e5a6134`(요청 1은 `@2b23788b`). `open-in-view=false`도 요청 2에서 다시 select / HIBDOC Interacting.adoc#L59 "A persistence context … absolutely positively **must not be shared between multiple threads or between concurrent transactions.**", #L83 "a persistence context can't be reused across unrelated transactions" |
| 기본 설정에선 읽을 때 사본(스냅샷)을 같이 둠(1:08) | findById 직후 출력 `스냅샷: 상태=MANAGED, 속성=[name], loadedState=[kim]`(Hibernate `EntityEntry.getLoadedState()`) / HIBDOC `userguide/chapters/pc/BytecodeEnhancement.adoc#L49-L51` "Historically Hibernate only supported diff-based dirty calculation … Hibernate would keep track of the last known state of an entity in regards to the database (typically the last read or write). Then, as part of flushing the persistence context, Hibernate would walk every entity associated with the persistence context and check its current state against that "last known database state"." / HIB `…/event/internal/DefaultFlushEntityEventListener.java#L487-L492` `// dirty check against the usual snapshot of the entity` `dirtyProperties = persister.findDirty( values, loadedState, entity, session );` / "기본 설정" 근거: `바이트코드 향상? ManagedEntity=false, SelfDirtinessTracker=false`, 시작 로그 `No LoadTimeWeaver setup: ignoring JPA class transformer`, 빌드에 향상 플러그인 없음. 웹 요청 밖 readOnly 트랜잭션에선 `상태=READ_ONLY … loadedState=null` |
| 커밋 직전에 지금 값과 스냅샷을 비교, 달라진 엔티티만 UPDATE(1:14) | 출력 `setName("lee") 뒤: 지금 값 name=lee` / `스냅샷: … loadedState=[kim]` → 커밋 중 `Flushed: 0 insertions, 1 updates …` → `update member set name='lee' where id=1` → `COMMIT` / 달라진 것만: 배치 `Flushed: 0 insertions, 1000 updates, 0 deletions to 2000 objects`(관리 중 2000, 바뀐 1000만), 안 바꾼 findTwice `Flushed: 0 insertions, 0 updates …` / DefaultFlushEntityEventListener.java#L145 `if ( isUpdateNecessary( event, mightBeDirty ) )`, #L458-L473 dirtyCheck |
| 변경 감지(1:20) | HIBDOC Interacting.adoc#L72 "automatic dirty checking" |
| 모아 둔 변경을 SQL로 보내는 것 = 플러시, 기본은 커밋 직전(1:25) | HIBDOC Interacting.adoc#L727 "a _flush_ operation is triggered, and the session synchronizes dirty state held in memory … with persistent state held in the database. Of course, it does this by executing SQL INSERT, UPDATE, and DELETE statements.", #L729-L731 "By default, a flush is triggered: - when the current transaction commits …", #L825 `AUTO` "Flush before transaction commit, and before execution of a query whose results might be affected by modifications held in memory" / Spring이 쓰기 트랜잭션엔 AUTO: SF `spring-orm/src/main/java/org/springframework/orm/jpa/vendor/HibernateJpaDialect.java#L182-L186` `// We need AUTO or COMMIT for a non-read-only transaction.` `session.setHibernateFlushMode(FlushMode.AUTO)`, 출력 `FlushMode=AUTO` / 위 스택(커밋 → `flushBeforeTransactionCompletion` → UPDATE → 그다음 `COMMIT`) |
| setName 순간엔 아무것도 안 나감(1:31) | rename 출력: `[드라이버→MySQL] select …` 다음 드라이버 줄이 `update …`이고, 그 사이에 `[앱] setName("lee") 뒤 …`, `[앱] [rename 본문 끝] …`가 있다 |
| IDENTITY 키는 DB가 id를 정해서, INSERT가 save() 순간 바로(1:34) | 출력 `[앱] save(new Member("choi")) 호출` → `[드라이버→MySQL] insert into member (name) values ('choi')` → `[앱] save() 반환: id=2, em.contains? true` → `COMMIT` / insert 순간 스택 `SessionImpl.persist(SessionImpl.java:692)` → … → `GetGeneratedKeysDelegate.performMutation` / HIBDOC `userguide/chapters/domain/identifiers.adoc#L427-L428` "using IDENTITY columns imposes a runtime behavior where the entity row *must* be physically inserted prior to the identifier value being known." / Member는 `GenerationType.IDENTITY`. 5번 영상과 같은 사실 |
| 바뀐 테이블을 읽는 JPQL 직전에도 플러시, 결과에 보여야 해서(1:40) | 출력 `[앱] setName("lee") 끝. FlushMode=AUTO` → `[앱] (a) teamRepository.count() 호출: Team 테이블 JPQL` → `[드라이버→MySQL] select count(*) from team t1_0`(update 없음) → `[앱] (b) memberRepository.findByName("lee") 호출: Member 테이블 JPQL` → `[드라이버→MySQL] update member set name='lee' where id=1` → `[드라이버→MySQL] select m1_0.id,m1_0.name from member m1_0 where m1_0.name='lee'` (general log도 같은 순서) / JPA §3.11.2 (#a4374) "the persistence provider is responsible for ensuring that all updates to the state of all entities in the persistence context which could potentially affect the result of the query are visible to the processing of the query. The persistence provider implementation may achieve this by flushing those entities to the database or by some other means." / HIBDOC Interacting.adoc#L732 "before execution of a query whose result would be affected by the synchronization of dirty state held in memory" / HIB `…/event/internal/DefaultAutoFlushEventListener.java#L84-L87` `areTablesToBeUpdated( event.getQuerySpaces() )` |
| 같은 이유로 저장할 생각 없던 변경도 저장, kim님(1:48, 1:53) | greeting 출력 `[앱] [greeting 본문 끝] 반환값=kim님, save() 호출 없음` → `Flushed: 0 insertions, 1 updates …` → `[드라이버→MySQL] update member set name='kim님' where id=1` → `COMMIT`, general log `Query update member set name='kim님' where id=1`, mysql CLI `1 \| kim님`. "화면에 보여 주려고"는 지어낸 예시 상황(코드 주석) |
| 보여 줄 값은 엔티티를 바꾸지 말고 따로(1:58, 그림 "보여 줄 값 → UPDATE 없음") | greetingNoChange 출력 `[앱] [greetingNoChange 본문 끝] 반환값=kim님, 엔티티 name=kim` → `Flushed: 0 insertions, 0 updates …` → `COMMIT`(update 없음), `1 \| kim` |
| readOnly만으론 못 막음: 같은 컨텍스트를 쓰는 쓰기 트랜잭션이 보낼 수 있음(2:02, 그림 "readOnly = true / 그 트랜잭션만 플러시 끔 → UPDATE 나갈 수 있음 / 같은 컨텍스트의 쓰기 트랜잭션") | 그 트랜잭션만 플러시 끔: SF HibernateJpaDialect.java#L150 `prepareFlushMode(session, definition.isReadOnly())`, #L172-L181 `// We should suppress flushing for a read-only transaction.` `session.setHibernateFlushMode(FlushMode.MANUAL)`, #L249-L252 `resetSessionState()`가 끝나면 이전 플러시 모드로 되돌림 / SDJ `src/main/antora/modules/ROOT/pages/jpa/transactions.adoc#L89` "when used with Hibernate, the flush mode is set to MANUAL when you configure a transaction as readOnly, which causes Hibernate to skip dirty checks" / 단독 readOnly: `반환값=kim님, FlushMode=MANUAL, defaultReadOnly=true, isReadOnly(member)? true, 스냅샷: 상태=READ_ONLY … loadedState=null`, `COMMIT`만, `1 \| kim`. **경우 (가) 바깥 쓰기 트랜잭션 안에서 부르면 readOnly가 무시됨**: SFD `data-access/transaction/declarative/tx-propagation.adoc#L23-L24` "By default, a participating transaction joins the characteristics of the outer scope, silently ignoring the local isolation level, timeout value, or read-only flag (if any)." / 실험 `outerCallsReadOnly(1)`: `Creating new transaction with name [com.example.pc.OuterService.outerCallsReadOnly]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT` → `Participating in existing transaction` → `[greetingReadOnly 본문 끝] 반환값=kim님, FlushMode=AUTO, defaultReadOnly=false, isReadOnly(member)? false, 스냅샷: 상태=MANAGED … loadedState=[kim]` → `Flushed: 0 insertions, 1 updates …` → `update member set name='kim님' where id=1` → `COMMIT`, `1 \| kim님`. **경우 (나) open-in-view(기본값)에서 같은 요청의 다음 쓰기 트랜잭션**: `readonly-then-write` 출력 `[greetingReadOnly 본문 끝] 반환값=kim님, FlushMode=MANUAL, defaultReadOnly=false, isReadOnly(member)? false, 스냅샷: 상태=MANAGED … loadedState=[kim]` → readOnly 트랜잭션 `COMMIT`(update 없음) → `[앱] save(new Member("choi")) 호출` → `insert into member (name) values ('choi')` → `update member set name='kim님' where id=1` → `COMMIT`, 행 `kim님`, `choi`. 원인: HibernateJpaDialect.java#L151-L157 `setDefaultReadOnly(true)`는 `rtd.isLocalResource()`(트랜잭션 전용 EntityManager)일 때만 적용된다. `open-in-view=false`에선 같은 호출이 update 없이 끝남(`READ_ONLY … loadedState=null`, 행 `kim`, `choi`) |
| 컨텍스트는 읽어 온 엔티티를 닫힐 때까지 붙잡아 둠(2:09) | HIBDOC Interacting.adoc#L85 "a persistence context holds a hard references to all its entities, preventing them from being garbage collected." / HIBDOC `introduction/Tuning.adoc#L903-L904` "Entity instances aren't automatically evicted from the session cache when they're no longer needed. Instead, they stay pinned in memory until the session they belong to is discarded by your program." / 배치 출력 `id 1~1000 처리 뒤 관리 중 엔티티 수=1000`, `id 1001~2000 … =2000`, …, `id 9001~10000 … =10000` |
| 플러시할 때마다 관리 중인 엔티티를 전부 스냅샷과 비교(2:14) | HIBDOC Interacting.adoc#L801 "flushing is a somewhat expensive operation (the session must dirty-check every entity in the persistence context)" / BytecodeEnhancement.adoc#L51(위 인용) / HIB `…/event/internal/AbstractFlushingEventListener.java#L205-L240`(flushEntities: `reentrantSafeManagedEntities()` 전부에 `onFlushEntity`), #L93-L111(로그의 objects = `persistenceContext.getNumberOfManagedEntities()`). 조건: 기본 설정(향상 없음, readOnly 아님). 읽기 전용 엔티티는 비교하지 않는다(HIBDOC Interacting.adoc#L842 "It's not necessary to dirty-check an entity instance in read-only mode.") |
| 1000개씩 10번 읽어 바꾸면 마지막엔 10000개 비교(2:19) | `batch(10000, 1000, false)` 플러시 로그 `HHH90060071: Flushed: 0 insertions, 1000 updates, 0 deletions to 1000 objects`, `… to 2000 objects`, `… to 3000 objects`, …, `… to 9000 objects`, 커밋 때 `… to 10000 objects`. 중간 플러시는 다음 `findByIdBetween`(Member JPQL) 직전의 AUTO 플러시다(1:40과 같은 규칙) |
| 배치에선 일정 개수마다 flush()로 보내고 clear()로 비움(2:23) | HIBDOC `userguide/chapters/batch/Batching.adoc#L79` "When you make new objects persistent, employ methods flush() and clear() to the session regularly, to control the size of the first-level cache.", #L93 "When you retrieve and update data, flush() and clear() the session regularly." / `batch(10000, 1000, true)`: `id 1~1000 처리 뒤 관리 중 엔티티 수=1000`, `Flushed: 0 insertions, 1000 updates, 0 deletions to 1000 objects`, `flush() + clear() 뒤 관리 중 엔티티 수=0`, 이후 모든 플러시가 `to 1000 objects`. 두 방식 모두 UPDATE 10000건(general log `update member` 10000줄) |
| clear()만 하면 안 보낸 변경이 버려짐, flush() 먼저(2:28) | JPAAPI `EntityManager.java#L888-L892` "Clear the persistence context, causing all managed entities to become detached. Changes made to entities that have not already been flushed to the database will never be made persistent." / renameThenClear 출력 `setName("lee") 뒤 clear() (flush 없이)` → `clear() 뒤 관리 중 엔티티 수=0, em.contains(member)? false` → `COMMIT`(update 없음), `1 \| kim` |
| 관리 중인 엔티티는 커밋 때 save() 없이 수정(2:40) | 위 변경 감지 근거 / "커밋 때" 조건: JPAAPI `FlushModeType.java#L36-L38` "If there is no transaction active or the persistence context is not joined to the current transaction, the persistence provider must not flush to the database." (트랜잭션 밖에서 바꾼 것은 그 자리에서 저장되지 않는다. 독립 사실 확인의 재실행에서 컨트롤러 변경 뒤 쓰기 트랜잭션이 없으면 DB가 `kim`으로 남음을 확인) |

수치는 "SELECT 1번/2번", "관리 중 0·1·2·1000…10000개", "objects 1000…10000"뿐이고 모두 실행 출력에서 직접 셌다.

### 화면에 실제 실행 출력을 쓴 곳 (자르거나 줄바꿈만 함)

시각·`[앱]`·`[드라이버→MySQL]` 머리표·열은 잘랐다. `→`는 "드라이버가 MySQL로 보낸 SQL"이라는 내 표시, `…`는 자른 자리, `#`/`//` 주석은 내 설명이다.

- general.log(0:08): general log `Query  select … where m1_0.id=1`(`m1_0.id,m1_0.name from member m1_0`을 `…`로), `Query  update member set name='lee'` / `where id=1`(한 줄을 둘로), `Query  COMMIT`. `1 | lee`는 mysql CLI 표를 한 줄로 옮긴 것.
- find-twice.log(0:51): `(1) findById(1) 호출`, `→ select … where m1_0.id=1`, `(2) findById(1) 다시 호출`, `(1)과 같은 객체인가(a == b)? true`(`(2) 반환: `과 `, 관리 중 엔티티 수=1` 자름). 둘째 덩어리 `# 다른 웹 요청: 새 컨텍스트` / `→ select … where m1_0.id=1`은 웹 실행 요청 2의 드라이버 줄(첫 덩어리는 웹이 아닌 실행이다).
- flush.log(1:40): `teamRepository.count()`와 `findByName("lee")`는 `[앱] (a) teamRepository.count() 호출: Team 테이블 JPQL`, `[앱] (b) memberRepository.findByName("lee") 호출: …`에서 따온 것. `→ select count(*) from team t1_0`, `→ update member set name='lee' …`(`where id=1` 자름), `→ select … where m1_0.name='lee'`.
- MemberService.java(1:48) 둘째 덩어리: `Query  update … name='kim님' …`(general log `update member set name='kim님' where id=1`에서 `member set`, `where id=1` 자름), `1 | kim님`.
- batch.log(2:09): `Flushed: … to 1000 objects`, `… to 2000 objects`(`HHH90060071:`과 `0 insertions, 1000 updates, 0 deletions` 자름), `…`, `관리 중 엔티티 수=10000`(`id 9001~10000 처리 뒤` 자름), `Flushed: … to 10000 objects`. 원래 순서 그대로.

### 예시·소스·그림으로 쓴 것 (실행 출력이 아님)

- MemberService.java(0:00): 실험 코드 `rename`에서 `Probe.*` 줄을 빼고 줄만 나눴다. `// save() 호출 없음`은 내 주석.
- MemberService.java(1:48) 첫 덩어리: 실험 코드 `greeting`. 줄 끝 주석 `// 화면에 '님'을 붙여 보여 주려고`를 윗줄로 옮기고 `Probe` 줄을 뺐다.
- context.txt(0:17, 그림): 틀 `EntityManager` 안의 틀 `영속성 컨텍스트`(JPA §3.1 "Every instance of EntityManager has an associated persistence context.", Hibernate 구현은 세션이 컨텍스트를 만들어 가짐: HIB `hibernate-core/src/main/java/org/hibernate/internal/SessionImpl.java#L192` `persistenceContext = createPersistenceContext( options );`). 안의 `Member / id 1, kim`, `Member / id 2, choi`는 readAndJoin 한 트랜잭션의 `컨텍스트 안:` 두 줄. `findById(1) / DB에서 읽음`(예시, 나레이션은 "DB에서 읽어 오거나"), `save() / 새 Member 저장`.
- lifetime.txt(0:35, 그림): 왼쪽 `웹 요청 밖`: `트랜잭션 시작 / EntityManager 열기` → `트랜잭션 끝 / EntityManager 닫기`(`Opened new EntityManager …`, `Closing JPA EntityManager after transaction`). 오른쪽 `웹 요청 (기본값)`: `요청 시작 / open-in-view: 열기` → `트랜잭션 1, 2 … / 같은 EntityManager` → `요청 끝 / EntityManager 닫기`(`Opening JPA EntityManager in OpenEntityManagerInViewInterceptor`, `Found thread-bound EntityManager [SessionImpl(723744907<open>)]` ×2, `Closing JPA EntityManager in OpenEntityManagerInViewInterceptor`). 화살표는 로그의 시간 순서. "(기본값)"은 `JpaBaseConfiguration.java#L231-L236`의 조건(SERVLET + WebMvcConfigurer + `matchIfMissing = true`).
- snapshot.txt(1:08, 그림): `Member / 지금 name=lee`, `스냅샷 / 읽을 때 name=kim`(rename 출력 `setName("lee") 뒤: 지금 값 name=lee`, `loadedState=[kim]`) → `비교 / 커밋 직전` → `MySQL`, 화살표 라벨 `UPDATE`.
- when.txt(1:25, 그림): `findById(1)` → `SELECT`, `setName()` → `(아직 없음)`, `커밋 / 직전에 플러시` → `UPDATE / 그다음 COMMIT`(rename 출력), `IDENTITY 키라면` `save() / 새 Member` → `INSERT / 바로`(join 출력).
- fix.txt(1:58, 그림): 위 `보여 줄 값 / 엔티티 말고 따로` → `UPDATE 없음`(greetingNoChange), 아래 `readOnly = true / 그 트랜잭션만 플러시 끔` → `UPDATE 나갈 수 있음 / 같은 컨텍스트의 쓰기 트랜잭션`(outerCallsReadOnly, open-in-view readonly-then-write).
- batch.txt(2:23, 그림): `1000개 읽고 바꾸기` → `flush() / UPDATE 보내기` → `clear() / 비우기: 관리 중 0개` → `다음 1000개`(batch flushAndClear=true 출력).
- summary.md(2:33, 그림): 틀 `영속성 컨텍스트`: `엔티티 / id마다 하나`, `스냅샷 / DB와 맞춘 값` → `플러시 / 비교해서 바뀐 것만 SQL`, `덕분에 / 같은 객체 · save() 없이 수정`, `챙길 것 / 원치 않는 UPDATE · 쌓이는 엔티티`. 스냅샷을 일반적으로 말할 땐 "DB와 맞춘 값"으로 썼다. 플러시로 UPDATE를 보낸 뒤엔 스냅샷이 보낸 값으로 바뀌기 때문이다(HIB `hibernate-core/src/main/java/org/hibernate/engine/internal/EntityEntryImpl.java#L284-L285` `public void postUpdate(…) { loadedState = updatedState;`).
- 썸네일: 제목 `영속성 / 컨텍스트란? / 장단점은?`, 부제 `# save() 없이 UPDATE가 나갔다`(훅의 실험), 제목줄 `❯ cat MemberService.java`.

### 확인했지만 넣지 않은 것

- **벌크 JPQL UPDATE는 컨텍스트를 건너뜀**: 같은 트랜잭션에서 findById → `name=kim`, `renameAll("park")` → `update member m1_0 set name='park'`, 다시 findById → `다시 찾은 name=kim, 처음과 같은 객체? true`(SELECT 없음), DB는 `park`. `@Modifying(clearAutomatically = true)`면 `관리 중 엔티티 수=0` → select → `name=park`. 근거 JPA §4.11 (#a5636) "The persistence context is not synchronized with the result of the bulk update or delete." / SDJ `src/main/antora/modules/ROOT/pages/jpa/query-methods.adoc#L633-L634`. 길이 때문에 뺐다(다음 영상 후보 2).
- **JPQL은 컨텍스트에 있어도 SELECT를 보내고, 그래도 같은 객체를 줌**: findTwice (3) `select … where m1_0.name='kim'` → `(1)과 같은 객체인가? true`.
- **Team 쿼리 앞에도 `Flushed: … 1 updates` 줄이 찍힘**: Hibernate가 변경을 확인했지만 테이블이 겹치지 않아 실행하지 않은 것이다(`DefaultAutoFlushEventListener.java#L47-L72`, `noNeedToExecuteFlush`). 그래서 SQL이 실제로 나갔는지는 드라이버 줄과 general log로만 판단했다.
- **메모리 수치**: 엔티티 10만 개를 읽으면 GC 뒤 힙 22 MB → 58 MB, `clear()` 뒤(리스트는 아직 참조) 35 MB, 리스트도 놓으면 26 MB. JVM·GC에 따라 달라 영상엔 쓰지 않았다.
- **배치 시간**: 1만 개에선 clear 없음 1894 ms, flush+clear 1872 ms로 거의 같았다(UPDATE 1만 번 왕복이 대부분). 그래서 "빨라진다"고 말하지 않고, 비교 대상 수(1000→10000 vs 1000 고정)만 말했다.

### 그 밖의 결정

- 이야기 구조: 훅(save() 없이 UPDATE) → 정의 → 수명 → 1차 캐시 → 스냅샷·변경 감지 → 플러시 시점 → 원치 않는 UPDATE와 대처 → 쌓이는 엔티티와 flush·clear → 정리.
- 예시 이름은 5·6번 영상과 이어지게 `Member`, `MemberService`, 값 `kim`을 썼다. 시나리오마다 `lee`(바꾼 이름), `choi`(새로 저장), `kim님`(원치 않는 변경)을 써서 로그를 구분했다.
- `pronounce`: MemberService 멤버서비스, rename 리네임, setName 셋네임, save() 세이브, MySQL 마이에스큐엘, UPDATE 업데이트, EntityManager 엔티티매니저, findById 파인드바이아이디, Member 멤버, managed 매니지드, Spring Boot 스프링 부트, Spring 스프링, open-in-view 오픈인뷰, SELECT 셀렉트, DB 디비, id 아이디, IDENTITY 아이덴티티, INSERT 인서트, JPQL 제이피큐엘, SQL 에스큐엘, kim 킴, readOnly 리드온리, flush() 플러시, clear() 클리어. `say`를 쓴 문장은 없다(단어 수 불일치가 한 번도 나지 않았다).
- 한글로 둔 말: 영속성 컨텍스트, 엔티티, 트랜잭션, 스냅샷, 캐시·1차 캐시, 변경 감지, 플러시(동사·개념 "플러시해요", "플러시 때"), 커밋(동사), 배치, 쿼리. 메서드 자체는 `flush()`, `clear()`로 썼다.
- 다이어그램 7장면(context, lifetime, snapshot, when, fix, batch, summary), 박스 6장면(실제 코드·실행 출력이 증거인 곳: 훅 코드, general log, find-twice, flush, greeting, batch 로그). 6번 영상 첫 렌더 뒤 "텍스트가 많다"는 피드백대로 흐름·구조·시간선·분기·정리는 처음부터 그림으로 그렸다.
- 길이: 첫 판 32문장 173.09 s → 이유 없는 표현을 줄여(훅 질문 문장, "그래서 1차 캐시라고도 불러요" → "1차 캐시라고도 해요", 첫 문장의 "이름을 바꾸는", 정리 문장) 169.06 s. 사실 확인 반영 뒤 168.48 s, 지난 영상 언급을 지운 뒤 167.91 s. 답안 항목과 '왜' 문장은 빼지 않았다.
- 썸네일: `thumbnail.py`가 제목 181px, 줄어듦 경고 없음. 이미지를 열어 보니 세 줄이 한눈에 읽힌다.

### 독립 사실 확인 반영 기록 (2026-11-02)

렌더 전에 독립 리뷰어가 초안을 태그의 소스, 실험 로그, 같은 앱으로 다시 돌린 결과와 대조했다. 받아 둔 출처 사본 17개는 공식 jar·태그와 같았고, 화면의 실행 출력 줄은 모두 원본 로그와 맞았다. 5·6번 영상과 어긋나는 곳도 없었다. 고친 것:

| # | 지적 | 바꾼 것 (전 → 후) |
|---|---|---|
| 1 (필수) | readOnly 조언이 틀림. (가) 바깥 쓰기 트랜잭션 안에서 부르면 readOnly는 조용히 무시되고 FlushMode가 AUTO로 남는다(SFD tx-propagation.adoc#L23-L24, 리뷰어 재실행: `Participating in existing transaction`, `FlushMode=AUTO`, `update … 'kim님'`). (나) open-in-view 기본값에선 같은 요청의 다음 쓰기 트랜잭션이 내보낸다(내 실험 로그) | 1:58 "그러니 보여 줄 값은 엔티티를 바꾸지 말고 따로 만들고," → "그러니 보여 줄 값은 엔티티를 바꾸지 말고 따로 만들어요." / 2:02 "읽기만 하는 트랜잭션은 readOnly로 열어요. 그 트랜잭션에선 Spring이 플러시를 꺼서, UPDATE가 안 나가요." → "readOnly만으론 못 막아요. 같은 컨텍스트를 쓰는 쓰기 트랜잭션이, 바꾼 값을 보낼 수 있거든요." / 그림: `readOnly = true`의 부제 `플러시 끔` → `그 트랜잭션만 플러시 끔`, `readOnly → UPDATE 없음` 화살표 삭제, 대신 `readOnly → UPDATE 나갈 수 있음 / 같은 컨텍스트의 쓰기 트랜잭션`. 경우 (가)를 내 실험(`outerCallsReadOnly`)으로도 재현해 위 표에 넣었다 |
| 2 | 정리 문장이 open-in-view와 겹치면 "컨트롤러(트랜잭션 밖)에서 바꿔도 저장된다"로 읽힐 수 있음. 트랜잭션이 없으면 플러시하지 않는다(JPAAPI FlushModeType.java#L36-L38) | 2:40 "덕분에 관리 중인 엔티티는 save() 없이 수정되지만, …" → "덕분에 관리 중인 엔티티는 커밋 때 save() 없이 수정되지만, …" |
| 3 | 그림의 "웹 요청"은 기본값일 때만 | lifetime.txt 머리 `웹 요청` → `웹 요청 (기본값)` |
| 4 | "findById로 읽어 오거나"는 JPQL로 읽은 엔티티를 빠뜨림(배치의 `findByIdBetween`도 관리 중 1000개) | 0:22 "findById로 읽어 오거나, save()로 새로 저장한 엔티티가 여기 들어가요." → "DB에서 읽어 오거나, save()로 새로 저장한 엔티티가 여기 들어가요." (그림의 `findById(1)` 상자는 예시로 둠) |
| 5 | 스냅샷을 일반적으로 "읽을 때 값"이라 하면 틀림. 플러시한 UPDATE 뒤엔 보낸 값이 된다(HIB EntityEntryImpl.java#L284-L285) | summary.md `스냅샷 / 읽을 때 값` → `DB와 맞춘 값`. snapshot.txt의 `읽을 때 name=kim`은 그 장면에 맞으니 그대로 |
| 6 | find-twice.log 첫 덩어리는 웹이 아닌 실행인데 "다음 웹 요청"이 웹처럼 읽힘 | `# 다음 웹 요청: 새 컨텍스트` → `# 다른 웹 요청: 새 컨텍스트` |

리뷰어가 그대로 둬도 된다고 한 것: "EntityManager마다 하나씩"(공유 프록시는 5번 영상에서 다룸).

### 지난 영상 언급 삭제 (2026-11-03)

사용자가 "지난 영상 얘기는 하지 말라"고 해서 대본 두 문장을 고치고 나레이션부터 다시 만들었다. 화면과 다른 문장은 그대로다.

| 위치 | 전 | 후 |
|---|---|---|
| 0:00 첫 문장 | "지난 영상의 MemberService에, rename을 하나 만들었어요." | "MemberService에, rename을 하나 만들었어요." |
| 1:34 when.txt 셋째 문장 | "단, IDENTITY 키의 INSERT는 지난 영상처럼, save() 순간 바로 나가요." | "단, IDENTITY 키는 DB가 id를 정해서, INSERT가 save() 순간 바로 나가요." |

둘째 문장은 "지난 영상처럼"이 맡던 맥락을 이유로 바꿨다. 근거는 위 "쓴 사실과 출처"의 IDENTITY 줄에 있는 HIBDOC identifiers.adoc#L427-L428 인용이다("the entity row *must* be physically inserted prior to the identifier value being known"). 이 영상만 본 사람도 왜 바로 나가는지 알 수 있다. 그림의 cue 단어(`IDENTITY`, `save()`, `바로`)는 그대로라 그림 등장 시점도 그대로다.
첫 문장이 약 0.6초 짧아져 1번 장면부터 위치가 약 0.6초 앞당겨졌다. 이 문서의 다른 시각 표기(m:ss)는 고치기 전 기준이라 1초 안쪽으로 어긋날 수 있다.
다시 렌더한 뒤 `check`는 오류 0, `line_unread` 7건으로 전과 같았다. 렌더한 MP4에서 0:01(첫 문장 자막)과 1:39(when.txt, `INSERT / 바로` 상자가 나온 뒤) 두 프레임을 뽑아 봤다.

## 측정한 것 / 보기만 한 것

- 렌더: 1080x1920, 30 fps, 167.93 s(2:48), 14.7 MB. 3분 한도 안이다(2026-11-03 지난 영상 언급을 지우고 다시 렌더한 값).
- 오디오: 통합 -14.1 LUFS, 피크 -1.5 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 7건(아래). 다른 종류의 경고는 없었다.
- `build.py`: `font down to`, `chars/s`, `diagram text down to` 경고 없음. `thumbnail.py`: 제목 181px, 경고 없음.
- 화면: 장면마다 가운데와 끝 직전(컷 0.15초 전)을 캡처해서 봤다(0초 포함 27장). 다이어그램은 원본 크기 프레임으로 봤다. 고친 뒤 fix.txt·snapshot.txt를 네 시점에서 다시 찍었고, 렌더한 MP4에서도 두 프레임(0:00, 2:09 직전)을 뽑아 캡처와 같은지 확인했다.
  - 0초 프레임에 첫 박스(rename 코드)와 첫 자막이 보인다.
  - 고친 것: fix.txt를 처음엔 두 열(왼쪽 `보여 줄 값 → UPDATE 없음`, 오른쪽 `readOnly = true`)로 그렸는데, 오른쪽 상자의 부제 `그 트랜잭션만 플러시 끔`이 약 29px로 줄고 오른쪽이 비어 "readOnly로는 부족하다"가 그림에 드러나지 않았다. 한 열 네 상자(`보여 줄 값 → UPDATE 없음`, `readOnly = true → UPDATE 나갈 수 있음`)로 바꿔 부제를 제 크기(36px)로 키웠다. snapshot.txt의 `UPDATE` 화살표 라벨이 위 `비교` 상자 바닥에 거의 닿아 줄 간격을 70 → 90px로 늘렸다.
  - 걱정했던 곳: context.txt의 이중 틀은 원본 크기에서 `Member / id 1, kim` 글자가 읽히고, 화살표 끝이 안쪽 틀 테두리 바로 아래에 닿을 뿐 상자와 겹치지 않는다. lifetime.txt의 부제 `open-in-view: 열기`는 상자 안에 들어간다. 머리 `웹 요청 (기본값)`은 왼쪽 `웹 요청 밖`보다 작게 나오지만 읽힌다. summary.md의 긴 부제(`원치 않는 UPDATE · 쌓이는 엔티티`)는 상자 안에 들어가고 읽힌다.
  - 자막은 모두 2줄 안이다. 기술 용어는 영어로 나온다(한글 음차 없음).
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - **findById가(0:56)**: "파인드바이아이디가"를 한 단어로 읽게 했다
  - **open-in-view가(0:45)**: "오픈인뷰가"
  - **managed라고(0:30)**: "매니지드라고"
  - **1차 캐시(0:56)**: "일차"로 읽히는지
  - **JPQL(1:39)**, **IDENTITY 키는 DB가 id를(1:34)**: "디비가 아이디를"
  - **kim님이(1:53)**: "킴님이"
  - **readOnly만으론(2:02)**: "리드온리만으론"
  - **1000개씩 열 번(2:19)**: "천 개씩"으로 읽히는지, **만 개를(2:19)**
  - **flush()로, clear()로(2:23)**: "플러시로", "클리어로"

## 일부러 남긴 경고

`line_unread` 7건. 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: `Query update member set name='lee'`를 27단어로 셈). 실제로는 한두 단어짜리 로그·SQL 줄이고, 나레이션이 같은 내용을 말한다.

- shot-02(general.log) `Query update member set name='lee'`, `# 실행 뒤 member 테이블`: hold 0.4 s
- shot-05(find-twice.log) 둘째 덩어리 `→ select … where m1_0.id=1`
- shot-08(flush.log) `→ update member set name='lee' …`, `→ select … where m1_0.name='lee'`: hold 0.8 s
- shot-09(greeting) `Query update … name='kim님' …`
- shot-11(batch.log) `Flushed: … to 10000 objects`

더 줄이려면 장면마다 hold를 늘려야 하는데, film이 이미 167.9 s라 170 s 기준을 넘는다. 그대로 뒀다.

## 가장 약한 부분

- **readOnly 함정(1:58–2:08)**: 영상은 "readOnly만으론 못 막아요. 같은 컨텍스트를 쓰는 쓰기 트랜잭션이, 바꾼 값을 보낼 수 있거든요."까지만 말한다. 실험한 두 경우는 다음과 같다.
  - (가) `@Transactional` 바깥 메서드 안에서 `@Transactional(readOnly = true)` 메서드를 부르면 참여 트랜잭션이라 readOnly가 조용히 무시된다(`FlushMode=AUTO`, `READ ONLY` 줄 없음). 바깥 커밋 때 `update member set name='kim님' where id=1`.
  - (나) open-in-view 기본값에선 같은 요청의 readOnly 트랜잭션이 끝나도 엔티티가 스냅샷(`[kim]`)과 함께 관리 중으로 남는다. 다음 쓰기 트랜잭션(`join("choi")`) 커밋 때 같은 UPDATE가 나간다. `open-in-view=false`에선 안 나간다.
  - 원인은 Spring이 readOnly일 때 그 트랜잭션의 플러시만 MANUAL로 바꾸고(끝나면 되돌림), 엔티티를 읽기 전용으로 만드는 `setDefaultReadOnly(true)`는 트랜잭션 전용 EntityManager일 때만 하기 때문이다. 왜 그런지(전파, open-in-view)는 영상에서 설명하지 않았다. 다음 영상 후보 1번.
- **"웹 요청"(0:35–0:50)**: 서블릿(Spring MVC) 웹 앱의 기본값이다(조건 SERVLET + WebMvcConfigurer). 나레이션은 MVC를 말하지 않는다. WebFlux는 확인하지 않았다.
- **"기본 설정에선 스냅샷"(1:08), "전부 비교"(2:14)**: Hibernate 바이트코드 향상(dirty tracking)을 켜면 다르다. 실험하지 않았다.
- **"없을 때만 DB에"(0:56)**: 2차 캐시를 켜면 컨텍스트 다음에 2차 캐시를 본다. 이 문장은 필요조건으로만 맞고, 2차 캐시는 실험하지 않았다.
- **"바뀐 테이블을 읽는 JPQL 직전에도 플러시"(1:40)**: Hibernate AUTO 모드의 규칙(쿼리가 읽는 테이블과 겹칠 때)이다. 네이티브 SQL 쿼리 앞의 동작은 확인하지 않았다.
- **배치 장면(2:09–2:32)**: 중간 플러시 9번은 다음 `findByIdBetween`(JPQL) 앞의 AUTO 플러시다. 영상은 "플러시할 때마다"라고만 하고 왜 열 번 플러시되는지는 따로 말하지 않았다(1:40의 규칙과 같다).
- 실험의 원본 로그·소스 사본·실험 앱(`z_임시/영속성_실험/`, 사실표.md 포함)은 2026-11-02 작업을 마치며 지웠다. 이 REVIEW는 그 파일 없이 읽히도록 핵심 코드와 로그 줄을 옮겨 적었다.
