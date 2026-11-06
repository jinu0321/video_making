# REVIEW

## 시청 후 답할 수 있는 것

질문: **`@Transactional`을 붙인 메서드를 부르면 실제로 무슨 일이 일어나고, 왜 이렇게 만들었나요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **주입된 빈은 내 객체가 아니라 프록시다. Spring Boot 기본 설정에선 내 클래스를 상속한 클래스(`MemberService$$SpringCGLIB$$0`)이고, 진짜 객체는 그 뒤에 따로 있다.**
   왜: 호출이 진짜 객체에 닿는 앞뒤에 트랜잭션 일을 끼워 넣으려면, 호출을 먼저 받을 자리가 필요하다. 상속한 클래스라서 `MemberService` 자리에 그대로 주입된다.
   실제 스택도 프록시 → `TransactionInterceptor` → 진짜 `join` 순서다. (0:12 run.log, 0:29 call-path.txt 그림)
2. **`TransactionInterceptor`는 진짜 메서드를 부르기 전에 트랜잭션 매니저(`JpaTransactionManager`)에게 시작을 맡기고, 매니저는 Hibernate를 시켜 풀에서 연결을 빌리고 `autocommit`을 끈다(`SET autocommit=0`).**
   왜: JDBC 연결은 기본으로 문장마다 바로 커밋된다. 꺼 둬야 커밋·롤백 전까지 여러 SQL이 한 트랜잭션으로 묶인다. (0:36 tx-begin.txt 그림)
3. **매니저는 빌린 연결과 EntityManager를 지금 스레드에 묶어 둔다. 그래서 메서드 안의 `save()`는 새로 시작하지 않고 그 트랜잭션에 합류한다.**
   왜: 같은 스레드의 데이터 접근 코드가 연결을 인자로 받지 않아도 꺼내 쓸 수 있게 하려는 것. (0:53 thread.txt 그림)
4. **정상 반환이면 `COMMIT`, 예외면 `ROLLBACK`을 보낸 뒤 `autocommit`을 다시 켜고 연결을 풀에 돌려준다. `ROLLBACK`이면 이미 MySQL에 간 insert도 남지 않는다.**
   왜: 프록시 쪽 코드가 진짜 메서드 호출을 try/catch로 감싸서, 정상 반환이냐 예외냐로 성공·실패를 가른다. (1:08, 1:14 general.log, 1:25 TransactionAspectSupport.java)
5. **이렇게 만든 이유: 직접 짰다면 메서드마다 반복할 시작·커밋·롤백 틀을 프록시가 대신 감싸 준다.** 그래서 `join` 코드엔 트랜잭션 코드가 없다. (0:00, 1:35)
6. **기본 규칙은 `RuntimeException`과 `Error` 계열만 롤백한다. `Exception`처럼 `throws`로 선언해야 하는 checked 예외는 커밋된다.**
   왜: EJB 시절 관례대로, checked 예외를 업무상 예상한 결과, 일종의 다른 반환값으로 본다.
   대처: `rollbackFor`로 지정하거나, Spring 6.2부터는 `@EnableTransactionManagement(rollbackOn = RollbackOn.ALL_EXCEPTIONS)`로 전역 기본값을 바꾼다(Spring 문서가 권함). (1:40 rollback-rule.txt 그림, 1:56 rollback.txt)
7. **`@Transactional`이 없는 메서드에서 같은 클래스의 `@Transactional` 메서드를 그냥(`this`로) 부르면 트랜잭션이 시작되지 않는다.**
   왜: 가로채는 건 프록시인데, 메서드 안의 `this`는 프록시가 아니라 진짜 객체다. 그래서 `save()`만 자기 트랜잭션으로 바로 커밋되고, 예외가 나도 행이 남는다.
   대처: 그 메서드를 다른 클래스로 옮기고 주입받아 부르면 프록시를 거친다. (2:03 MemberService.java, 2:14 self-call.txt)

기억할 한 문장: "@Transactional은 프록시가 메서드 호출을 try로 감싸고, 트랜잭션 매니저가 시작과 커밋, 롤백을 맡는 구조다. 프록시를 안 거치는 this 호출과, 기본으로 커밋되는 checked 예외는 따로 챙긴다." (2:31 summary.md)

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
npx --yes hyperframes@0.8.209 render -o "output/transactional_은_어떻게_동작할까.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/transactional_은_어떻게_동작할까.mp4"
ffmpeg -nostats -i "output/transactional_은_어떻게_동작할까.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 주제 "@Transactional은 어떻게 동작할까"를 "부르면 실제로 무슨 일이 일어나고 왜 이렇게 만들었나" 하나로 좁혔다. 뼈대는 프록시 → 인터셉터 → 매니저가 시작(연결, autocommit, 스레드) → 진짜 메서드 → 커밋/롤백 → 복구·반납이다.
  결과 두 가지(기본 롤백 규칙, this 호출)는 팁 목록이 아니라 "이 구조라서 생기는 일"로만 넣었다. 롤백 규칙은 try/catch 코드의 catch에서, this 호출은 "가로채는 건 프록시"에서 이어진다.
- 5번 영상(save() 하나에도 `SET autocommit=0 → insert → COMMIT → SET autocommit=1`, repository 호출은 바깥 트랜잭션에 합류)은 첫 문장 "지난 영상의 save()처럼"과 합류 장면(1:02)으로만 이었다. 다시 가르치지 않았다.
- 입문자가 보고 나서 할 수 있는 것: 로그에 `$$SpringCGLIB$$`가 왜 찍히는지 설명하기, 트랜잭션이 언제 연결을 잡고 언제 돌려주는지 말하기, checked 예외가 커밋되는 이유와 고치는 법(`rollbackFor`, 전역 설정) 고르기, 같은 클래스 안 호출에서 트랜잭션이 안 걸리는 이유와 대처 말하기.
- 다음 영상 후보(범위를 좁히느라 뺀 것):
  - **전파(propagation)**: 이 영상은 `REQUIRED`에서 save()가 합류하는 것만 보였다. `REQUIRES_NEW`, `NESTED`.
  - **rollback-only와 `UnexpectedRollbackException`**: 안쪽에서 합류한 트랜잭션이 실패해 rollback-only로 표시되면, 바깥이 정상 반환해도 commit 호출이 실제로는 롤백한다. 이 영상의 "예외 없이 돌아오면 커밋"(1:29)은 이 경우를 빼고 말했다.
  - **격리 수준(isolation)과 `readOnly`**: 5번 영상 블로그 실험에서 `SET SESSION TRANSACTION READ ONLY`가 나가는 것을 봤다.
  - **AOP 일반**: 포인트컷, 다른 advice와 순서, JDK 프록시와 CGLIB 비교(repository는 JDK 프록시, 서비스는 CGLIB).
  - **메서드 가시성**: protected·package-private은 Spring 6.0부터 적용, public final은 시작 때 WARN 한 줄 뒤 조용히 미적용, private은 경고도 없이 미적용(아래 "실험 환경과 재현"에 실험 결과).
  - **새 스레드로는 트랜잭션이 넘어가지 않음**: 실험 출력은 있지만 화면·나레이션에서 뺐다.

### 실험 환경과 재현 (2026-11-02)

- 호스트: macOS 26.5.1 (25F80), arm64, Docker client/server 29.9.2. 앱은 호스트 JDK 25.0.4 + Gradle wrapper 9.8.2로 빌드하고 컨테이너에서 실행했다(5번 영상 블로그 실험 E1·E2와 같은 방식).
- 이미지: `mysql:8.4` (`sha256:a0225d1ea663…`, `SELECT VERSION()` → 8.4.13, `@@global.autocommit`=1), `eclipse-temurin:25-jre` (`sha256:78f1f1839134…`, `java -version` → 25.0.4.1, Temurin-25.0.4.1+1). 전용 네트워크 `tx-net`, MySQL 컨테이너 `tx-mysql`, 호스트에 포트를 열지 않았다.
- 앱이 찍은 버전: Java 25.0.4.1, Spring Boot 4.1.2, Spring Framework 7.0.10, Spring Data JPA 4.1.2, Jakarta Persistence 3.2.0, Hibernate ORM 7.4.13.Final, HikariCP 7.0.2, Connector/J 9.7.0, MySQL 8.4.13. 트랜잭션 매니저는 Boot 자동 설정의 `org.springframework.orm.jpa.JpaTransactionManager`. 풀 크기는 기본값.
- `application.properties`: `spring.datasource.url=jdbc:mysql://tx-mysql:3306/txdemo?queryInterceptors=com.example.tx.DriverSpy`(드라이버가 보내는 SQL과 그 순간의 호출 스택을 찍는 관찰용 인터셉터), `spring.jpa.hibernate.ddl-auto=create`(실행마다 빈 테이블), `spring.jpa.open-in-view=false`, 로그 `org.springframework.orm.jpa.JpaTransactionManager=debug`, `org.springframework.transaction.interceptor=trace`, `org.hibernate.SQL=debug`. MySQL general log는 `log_output=TABLE`.
- 시나리오마다 앱을 한 번씩 실행하고(실행 전 general log 비움), 앱 로그·general log·`SELECT COUNT(*) / SELECT id, name FROM member`(mysql CLI)를 따로 남겼다. 앱도 호출 직후 `[앱] 호출 뒤 member 테이블: N행 [...]`을 찍는다.
- 실험 서비스 코드(출력용 `Probe.*` 줄 빼고 그대로):

```java
@Transactional
public void join(String name) {
    Member member = memberRepository.save(new Member(name));
}
@Transactional
public void joinFail(String name) {
    memberRepository.save(new Member(name));
    throw new RuntimeException("가입 실패");
}
@Transactional
public void joinChecked(String name) throws Exception {
    memberRepository.save(new Member(name));
    throw new Exception("가입 실패");
}
@Transactional(rollbackFor = Exception.class)
public void joinCheckedRollbackFor(String name) throws Exception { /* joinChecked와 같음 */ }
// @Transactional 없음
public void register(String name) {
    joinFail(name);
}
```

- 시나리오별 결과(MySQL general log, `Query` 줄 그대로, 실행 뒤 행):

| 호출(다른 Bean `TxRunner`가 주입받은 `memberService`로) | 메서드 안 트랜잭션 활성? | MySQL이 받은 것 | 실행 뒤 행 |
|---|---|---|---|
| `join("kim")` | true | `SET autocommit=0` / `insert into member (name) values ('kim')` / `COMMIT` / `SET autocommit=1` | 1 (`kim`) |
| `joinFail("lee")` | true | `SET autocommit=0` / `insert … ('lee')` / `ROLLBACK` / `SET autocommit=1` | 0 |
| `joinChecked("park")` | true | `SET autocommit=0` / `insert … ('park')` / `COMMIT` / `SET autocommit=1` | 1 (`park`) |
| `joinCheckedRollbackFor("choi")` | true | `SET autocommit=0` / `insert … ('choi')` / `ROLLBACK` / `SET autocommit=1` | 0 |
| `register("jung")` → 같은 클래스의 `joinFail` | **false** | `SET autocommit=0` / `insert … ('jung')` / `COMMIT` / `SET autocommit=1` (save()의 자기 트랜잭션) | 1 (`jung`) |
| `joinChecked("park")` + `@EnableTransactionManagement(rollbackOn = RollbackOn.ALL_EXCEPTIONS)` | true | `SET autocommit=0` / `insert … ('park')` / `ROLLBACK` / `SET autocommit=1` | 0 |

- 영상엔 안 쓴 실험, 메서드 가시성(사실표에서 옮김, 원본 로그는 2026-11-02 `z_임시` 정리 때 지움):
  - protected / package-private: CGLIB 프록시에서 트랜잭션 적용됨. `protectedJoin`, `packagePrivateJoin` 모두 `트랜잭션 활성? true`, `SET autocommit=0 … COMMIT`. SFD `data-access/transaction/declarative/annotations.adoc` L179–L183 "As of 6.0, `protected` or package-visible methods can also be made transactional for class-based proxies by default."
  - public final: 오류 없이 시작되고 시작 때 `WARN … CglibAopProxy : Public final method [public final void com.example.tx.MemberService.finalJoin()] cannot get proxied via CGLIB, consider removing the final marker or using interface-based JDK proxies.` 한 줄. 호출은 프록시 인스턴스 자신의 메서드로 실행됨(`[finalJoin 본문] this 클래스=com.example.tx.MemberService$$SpringCGLIB$$0, 트랜잭션 활성? false`), 주입 필드 `memberRepository 필드 == null ? true`. SF `spring-aop/src/main/java/org/springframework/aop/framework/CglibAopProxy.java#L283-L304`
  - private: 실험하지 않음(밖에서 부를 수 없음). SFD `core/aop/proxying.adoc` L19 "`private` methods cannot be advised, because they cannot be overridden." `CglibAopProxy.doValidateClass`는 private을 경고 대상에서 뺀다(`!Modifier.isPrivate(mod)`, L288) → 경고 없이 적용 안 됨

### 쓴 사실과 출처 (2026-11-02 확인)

출처는 실행한 버전의 태그로 고정했다. 약칭: **SF** = `https://github.com/spring-projects/spring-framework/blob/v7.0.10/`, **SFD** = `SF` + `framework-docs/modules/ROOT/pages/` (docs.spring.io/spring-framework/reference/ 에 게시되는 원문). 로그 줄은 시각만 빼고 그대로 옮겼다.

| 영상 속 내용 | 근거 |
|---|---|
| 주입된 객체는 `MemberService`를 상속한 다른 클래스(0:12) | 실행 출력 `memberService.getClass() : com.example.tx.MemberService$$SpringCGLIB$$0`, `그 부모 클래스(getSuperclass) : com.example.tx.MemberService`, `MemberService 타입인가? : true`, `AopUtils.isAopProxy / isCglibProxy / isJdkDynamicProxy : true / true / false`, `프록시 뒤의 진짜 객체 클래스 : com.example.tx.MemberService`, `프록시와 진짜 객체는 같은 객체인가? : false` |
| Spring Boot 기본 설정에선 상속한 프록시(0:18) | https://github.com/spring-projects/spring-boot/blob/v4.1.2/module/spring-boot-transaction/src/main/java/org/springframework/boot/transaction/autoconfigure/TransactionAutoConfiguration.java#L67-L73 `@EnableTransactionManagement(proxyTargetClass = true)` `@ConditionalOnBooleanProperty(name = "spring.aop.proxy-target-class", matchIfMissing = true)` / Boot 속성 메타데이터 `spring.aop.proxy-target-class`: "Whether subclass-based (CGLIB) proxies are to be created (true), as opposed to standard Java interface-based proxies (false)." defaultValue true / SFD `core/aop/proxying.adoc#L10-L11` "a CGLIB proxy is created which is a runtime-generated subclass of the target type." / 실행 출력 `proxyTargetClass : true` / 이름 규칙 SF `spring-core/src/main/java/org/springframework/cglib/core/SpringNamingPolicy.java#L35` `SPRING_LABEL = "$$SpringCGLIB$$"` |
| 호출 앞뒤에 트랜잭션 일을 끼우려는 것(0:24) | SFD `data-access/transaction/declarative/tx-decl-explained.adoc#L10-L16` "this support is enabled via AOP proxies … The combination of AOP with transactional metadata yields an AOP proxy that uses a TransactionInterceptor in conjunction with an appropriate TransactionManager implementation to drive transactions around method invocations." / 실행 출력 `advisor: …BeanFactoryTransactionAttributeSourceAdvisor  advice: org.springframework.transaction.interceptor.TransactionInterceptor` |
| 프록시 → TransactionInterceptor → 진짜 join(0:29) | `join` 본문에서 찍은 스택(위가 먼저): `MemberService$$SpringCGLIB$$0.join` → `CglibAopProxy$DynamicAdvisedInterceptor.intercept` → `ReflectiveMethodInvocation.proceed` → `TransactionInterceptor.invoke` → `TransactionAspectSupport.invokeWithinTransaction` → `TransactionInterceptor$1.proceedWithInvocation` → `ReflectiveMethodInvocation.proceed` → `.invokeJoinpoint` → `AopUtils.invokeJoinpointUsingReflection` → `Method.invoke` → `DirectMethodHandleAccessor.invoke` → `MemberService.join` |
| 인터셉터는 진짜 join 전에 트랜잭션 매니저에게 시작을 맡긴다(0:36) | SF `spring-tx/src/main/java/org/springframework/transaction/interceptor/TransactionAspectSupport.java#L365-L371` `TransactionInfo txInfo = createTransactionIfNecessary(ptm, txAttr, joinpointIdentification);` 다음에 `retVal = invocation.proceedWithInvocation();` / 로그 순서: `[앱] memberService.join("kim") 호출` → `JpaTransactionManager : Creating new transaction with name [com.example.tx.MemberService.join]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT` → `[드라이버→MySQL] COM_QUERY SET autocommit=0` → `[join 본문 시작]` |
| 매니저가 Hibernate를 시켜 풀에서 연결을 빌리고 autocommit을 끈다(0:42) | `SET autocommit=0`을 보내는 순간의 스택: `TransactionInterceptor.invoke` → `invokeWithinTransaction` → `createTransactionIfNecessary` → `AbstractPlatformTransactionManager.getTransaction` → `startTransaction` → `JpaTransactionManager.doBegin(JpaTransactionManager.java:411)` → `HibernateJpaDialect.beginTransaction(HibernateJpaDialect.java:147)` → `TransactionImpl.begin` → … → `LogicalConnectionManagedImpl.begin(…:291)` → `AbstractLogicalConnectionImplementor.begin(…:69)` → `HikariProxyConnection.setAutoCommit` → `ConnectionImpl.setAutoCommit` / SF `spring-orm/src/main/java/org/springframework/orm/jpa/vendor/HibernateJpaDialect.java#L147` `entityManager.getTransaction().begin();` / https://github.com/hibernate/hibernate-orm/blob/7.4.13/hibernate-core/src/main/java/org/hibernate/resource/jdbc/internal/LogicalConnectionManagedImpl.java#L280-L292 `getConnectionForTransactionManagement() { return getPhysicalConnection(); }`, `begin()`에서 `determineInitialAutoCommitMode( getConnectionForTransactionManagement() )`(물리 연결 획득) 뒤 `super.begin()` / https://github.com/hibernate/hibernate-orm/blob/7.4.13/hibernate-core/src/main/java/org/hibernate/resource/jdbc/internal/AbstractLogicalConnectionImplementor.java#L65-L71 `getConnectionForTransactionManagement().setAutoCommit( false );` / 앱 출력 `[앱] 호출 전: 빌려 간 커넥션 0개` → (join 본문) `HikariCP에서 빌려 간 커넥션 수 : 1` |
| JDBC 연결은 기본으로 문장마다 커밋, 꺼야 묶인다(0:47) | https://docs.oracle.com/en/java/javase/25/docs/api/java.sql/java/sql/Connection.html — "By default a Connection object is in auto-commit mode, which means that it automatically commits changes after executing each statement." / `setAutoCommit`: "If a connection is in auto-commit mode, then all its SQL statements will be executed and committed as individual transactions. Otherwise, its SQL statements are grouped into transactions that are terminated by a call to either the method commit or the method rollback." / 앱 출력 `풀에서 받은 Connection의 autoCommit 기본값 : true` |
| 빌린 연결과 EntityManager를 지금 스레드에 묶는다(0:53) | SF `spring-orm/src/main/java/org/springframework/orm/jpa/JpaTransactionManager.java#L432` `TransactionSynchronizationManager.bindResource(getDataSource(), conHolder);`, `#L444-L446` `// Bind the entity manager holder to the thread.` `TransactionSynchronizationManager.bindResource(obtainEntityManagerFactory(), txObject.getEntityManagerHolder());` / SF `spring-tx/src/main/java/org/springframework/transaction/support/TransactionSynchronizationManager.java#L34` "Central delegate that manages resources and transaction synchronizations per thread.", `#L77` `ThreadLocal<Map<Object, Object>> resources` / join 본문 출력 `스레드 : main`, `이 스레드에 묶인 자원 2개 (키 -> 값):` `com.zaxxer.hikari.HikariDataSource -> org.springframework.jdbc.datasource.ConnectionHolder [Connection: com.zaxxer.hikari.pool.HikariProxyConnection]`, `jdk.proxy2.$Proxy93 -> org.springframework.orm.jpa.EntityManagerHolder [EntityManager: org.hibernate.internal.SessionImpl]` |
| 같은 스레드의 데이터 접근 코드가 인자로 안 받아도 꺼내 쓴다(0:58) | SFD `data-access/transaction/declarative/tx-decl-explained.adoc#L33-L36` "`@Transactional` commonly works with thread-bound transactions managed by `PlatformTransactionManager`, exposing a transaction to all data access operations within the current execution thread. Note: This does _not_ propagate to newly started threads within the method." / repository 쪽 조회 SF `spring-orm/src/main/java/org/springframework/orm/jpa/EntityManagerFactoryUtils.java#L207` `EntityManagerHolder emHolder = (EntityManagerHolder) TransactionSynchronizationManager.getResource(emf);` / 반대 확인 출력 `같은 순간 다른 스레드(other-thread)에서 본 것: 트랜잭션 활성? false, 묶인 자원 0개` |
| save()는 새로 시작하지 않고 합류(1:02) | 로그 `Found thread-bound EntityManager [SessionImpl(448955038<open>)] for JPA transaction`(시작 때 연 것과 같은 번호), `Participating in existing transaction` / 출력 `save()한 Member(id=1)가 스레드에 묶인 EntityManager 안에 있나? true`, `스레드에 묶인 Connection == Hibernate가 쓰는 Connection ? true`, save 뒤에도 `HikariCP에서 빌려 간 커넥션 수 : 1` / SF `spring-tx/src/main/java/org/springframework/transaction/support/AbstractPlatformTransactionManager.java#L497` `logger.debug("Participating in existing transaction");` |
| 정상 끝 → COMMIT, autocommit 다시 켬, 연결 반납(1:08) | general log `Query SET autocommit=0` / `Query insert into member (name) values ('kim')` / `Query COMMIT` / `Query SET autocommit=1` (모두 같은 thread_id 109) / 앱 로그 `Committing JPA transaction on EntityManager [SessionImpl(448955038<open>)]`, `Closing JPA EntityManager after transaction`, `[앱] 호출 뒤: 빌려 간 커넥션 0개, 이 스레드에 묶인 자원 0개, 트랜잭션 활성? false` / `SET autocommit=1` 스택: `commitTransactionAfterReturning` → `JpaTransactionManager.doCommit` → `TransactionImpl.commit` → … → `LogicalConnectionManagedImpl.afterCompletion(…:296)` → `AbstractLogicalConnectionImplementor.resetConnection(…:126)` → `setAutoCommit` / Hibernate `AbstractLogicalConnectionImplementor.java#L122-L127` `if ( initiallyAutoCommit ) { … getConnectionForTransactionManagement().setAutoCommit( true ); }` / 반납 SF `JpaTransactionManager.java#L609-L642`(unbind 후 `closeAll()`), https://github.com/brettwooldridge/HikariCP/blob/HikariCP-7.0.2/src/main/java/com/zaxxer/hikari/pool/ProxyConnection.java#L240-L268 `close()` → `poolEntry.recycle()` |
| RuntimeException → ROLLBACK, 테이블에 안 남음(1:14, 1:19) | general log `Query insert into member (name) values ('lee')` → `Query ROLLBACK` → `Query SET autocommit=1` / 로그 `Completing transaction for [com.example.tx.MemberService.joinFail] after exception: java.lang.RuntimeException: 가입 실패`, `Rolling back JPA transaction on EntityManager […]` / `[앱] 호출 뒤 member 테이블: 0행 []`, mysql CLI `row_count 0` / https://dev.mysql.com/doc/refman/8.4/en/innodb-autocommit-commit-rollback.html — "A ROLLBACK statement, on the other hand, cancels all modifications made by the current transaction." |
| try/catch 틀, 예외 없으면 커밋, 예외면 catch(1:25, 1:29) | SF `TransactionAspectSupport.java#L363-L409`: `if (txAttr == null \|\| !(ptm instanceof CallbackPreferringPlatformTransactionManager cpptm)) { // Standard transaction demarcation … TransactionInfo txInfo = createTransactionIfNecessary(…); Object retVal; try { // This is an around advice: Invoke the next interceptor in the chain. // This will normally result in a target object being invoked. retVal = invocation.proceedWithInvocation(); } catch (Throwable ex) { completeTransactionAfterThrowing(txInfo, invocation, ex); throw ex; } finally { cleanupTransactionInfo(txInfo); } … commitTransactionAfterReturning(txInfo); return retVal; }` / 실험의 COMMIT 스택이 `invokeWithinTransaction(TransactionAspectSupport.java:408)` → `commitTransactionAfterReturning`을 지남 |
| 메서드마다 반복할 틀을 프록시가 대신 감쌈(1:35) | SFD `data-access/transaction/declarative.adoc#L4-L6` "Most Spring Framework users choose declarative transaction management. This option has the least impact on application code…" / 실험의 다섯 `@Transactional` 호출이 모두 `invokeWithinTransaction`을 지나 시작·끝남 |
| catch에서 늘 롤백하진 않음 / checked 예외는 기본 규칙에서 커밋(1:40) | SF `TransactionAspectSupport.java#L705-L735` `if (txInfo.transactionAttribute != null && txInfo.transactionAttribute.rollbackOn(ex)) { … rollback(…) } else { // We don't roll back on this exception. … commit(…) }` / SFD `data-access/transaction/declarative/rolling-back.adoc#L71-L72` "Checked exceptions that are thrown from a transactional method do not result in a rollback in the default configuration." / 실험 general log `insert … ('park')` → `Query COMMIT`, 로그 `Completing transaction for [com.example.tx.MemberService.joinChecked] after exception: java.lang.Exception: 가입 실패` → `Initiating transaction commit`, `[앱] 호출한 쪽으로 예외가 나옴: java.lang.Exception: 가입 실패`, `[앱] 호출 뒤 member 테이블: 1행 [park]` |
| `Exception`처럼 throws로 선언해야 하는 checked 예외(1:40) | JLS SE 25 §11.1.1 https://docs.oracle.com/javase/specs/jls/se25/html/jls-11.html — "the checked exception classes are Throwable and all its subclasses other than RuntimeException and its subclasses and Error and its subclasses." §11.2 "For each checked exception which is a possible result, the throws clause for the method or constructor must mention the class of that exception or one of the superclasses of the class of that exception" |
| 기본 규칙은 RuntimeException과 Error 계열만 롤백(1:46) | SF `spring-tx/src/main/java/org/springframework/transaction/interceptor/DefaultTransactionAttribute.java#L180-L182` `return (ex instanceof RuntimeException \|\| ex instanceof Error);` / SFD `rolling-back.adoc#L17-L20` "marks a transaction for rollback only in the case of runtime, unchecked exceptions. That is, when the thrown exception is an instance or subclass of `RuntimeException`. (`Error` instances also, by default, result in a rollback)." |
| EJB 시절 관례대로, checked 예외를 예상한 결과·다른 반환값으로 봄(1:50) | SF `DefaultTransactionAttribute.java#L166-L172` "The default behavior is as with EJB: rollback on unchecked exception (RuntimeException), assuming an unexpected outcome outside any business rules. Additionally, we also attempt to rollback on Error which is clearly an unexpected outcome as well. By contrast, a checked exception is considered a business exception and therefore a regular expected outcome of the transactional business method, i.e. a kind of alternative return value which still allows for regular completion of resource operations." |
| rollbackFor로 지정(1:56) | SF `spring-tx/src/main/java/org/springframework/transaction/annotation/Transactional.java#L231-L247` rollbackFor: "Defines zero (0) or more exception types, which must be subclasses of Throwable, indicating which exception types must cause a transaction rollback." / 실험 로그 `Creating new transaction with name [com.example.tx.MemberService.joinCheckedRollbackFor]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT,-java.lang.Exception`, general log `insert … ('choi')` → `Query ROLLBACK`, `[앱] 호출 뒤 member 테이블: 0행 []` |
| Spring 6.2부터 전역 기본값도 바꿀 수 있음(1:56) | SFD `data-access/transaction/declarative/annotations.adoc#L424-L439` "As of 6.2, you can globally change the default rollback behavior – for example, through `@EnableTransactionManagement(rollbackOn=ALL_EXCEPTIONS)`, leading to a rollback for all exceptions raised within a transaction, including any checked exception. … Unless you rely on EJB-style business exceptions with commit behavior, it is advisable to switch to `ALL_EXCEPTIONS` for consistent rollback semantics even in case of a (potentially accidental) checked exception." / SF `spring-tx/src/main/java/org/springframework/transaction/annotation/EnableTransactionManagement.java#L204-L222` `RollbackOn rollbackOn() default RollbackOn.RUNTIME_EXCEPTIONS;` (`@since 6.2`) / 실험(Boot 4.1.2, 설정 클래스에 `@EnableTransactionManagement(rollbackOn = RollbackOn.ALL_EXCEPTIONS)`): 같은 `joinChecked("park")`가 `Creating new transaction … PROPAGATION_REQUIRED,ISOLATION_DEFAULT,-java.lang.Exception` → `Query ROLLBACK`, `0행 []`, 프록시는 여전히 `MemberService$$SpringCGLIB$$0`, `proxyTargetClass : true` |
| @Transactional 없는 register에서 같은 클래스의 joinFail을 부르면 예외에도 행이 남음(2:03, 2:09) | 실험 코드(위) / 로그 `[joinFail 본문 시작] this 클래스=com.example.tx.MemberService, 트랜잭션 활성? false, 트랜잭션 이름=null, 빌려 간 커넥션=0`, general log `SET autocommit=0` / `insert … ('jung')` / `COMMIT` / `SET autocommit=1`(ROLLBACK 없음), `[앱] 호출한 쪽으로 예외가 나옴: java.lang.RuntimeException: 가입 실패`, `[앱] 호출 뒤 member 테이블: 1행 [jung]` |
| 가로채는 건 프록시, 메서드 안의 this는 진짜 객체(2:14) | SFD `core/aop/proxying.adoc#L211-L216` "once the call has finally reached the target object (the `SimplePojo` reference in this case), any method calls that it may make on itself, such as `this.bar()` or `this.foo()`, are going to be invoked against the `this` reference, and not the proxy. … self invocation via an explicit or implicit `this` reference will bypass the advice." / SFD `annotations.adoc#L224-L227` "In proxy mode (which is the default), only external method calls coming in through the proxy are intercepted. This means that self-invocation … does not lead to an actual transaction at runtime even if the invoked method is marked with `@Transactional`." / COMMIT 순간 스택에서 `MemberService.register(MemberService.java:50)` 바로 다음 줄이 `MemberService.joinFail(MemberService.java:27)`(사이에 프록시·인터셉터 프레임 없음) |
| joinFail 트랜잭션은 시작조차 안 되고, save()가 자기 트랜잭션으로 바로 커밋(2:19) | 로그 `[joinFail 본문 시작] … 트랜잭션 활성? false, 트랜잭션 이름=null` 다음 `Creating new transaction with name [org.springframework.data.jpa.repository.support.SimpleJpaRepository.save]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT`, `[드라이버→MySQL] COM_QUERY COMMIT`(16:35:57.783)이 `[앱] 호출한 쪽으로 예외가 나옴`(16:35:57.796)보다 먼저 / COMMIT 스택 `MemberService.joinFail` → `jdk.proxy2.$Proxy100.save` → … → `TransactionInterceptor` → commit |
| 다른 클래스로 옮기고 주입받아 부르면 프록시를 거침(2:26) | SFD `core/aop/proxying.adoc#L220-L223` "Avoid self invocation :: The best approach (the term "best" is used loosely here) is to refactor your code such that the self invocation does not happen." / 실험: 다른 Bean(`TxRunner`)이 주입받아 부른 `joinFail("lee")`는 트랜잭션 활성 true, `ROLLBACK`, 0행 |

수치는 "빌려 간 커넥션 0개/1개", "행 수 0/1", 스택 "2프레임/7프레임"뿐이고 모두 실행 출력에서 직접 셌다.

### 화면에 실제 실행 출력을 쓴 곳 (자르거나 줄바꿈만 함)

시각·스레드 번호·패키지 이름·열은 잘랐고, 긴 줄은 나눴다. 글자를 바꾸거나 없는 내용을 넣지 않았다. `#`/`//` 주석 줄과 `← 진짜 객체`, `# ROLLBACK 없음`은 내가 단 설명이다.

- run.log(0:12): `memberService.getClass()` / `: …MemberService$$SpringCGLIB$$0`, `그 부모 클래스 : …MemberService`(`(getSuperclass)` 자름), `프록시와 진짜 객체는 같은 객체인가?` / `: false`
- (0:29 stack.txt, 0:36 app.log, 0:53 resources.txt의 실행 출력 상자는 다이어그램으로 바뀌었다. 아래 "예시·소스·그림으로 쓴 것". 그 출력은 위 표에 그대로 남아 있다.)
- general.log(1:08): `Query  SET autocommit=0`, `Query  insert into member … ('kim')`(`(name) values`를 `…`로), `Query  COMMIT`, `Query  SET autocommit=1`, `[앱] 호출 뒤: 빌려 간 커넥션 0개`
- general.log(1:14): `Query  insert into member … ('lee')`, `Query  ROLLBACK`, `[앱] 호출 뒤 member 테이블: 0행`(` []` 자름)
- rollback.txt(1:56): `// 같은 예외에 ROLLBACK, 0행`은 rollbackFor 실행 결과(choi, `Query ROLLBACK`, 0행)를 요약한 내 주석. 실행 출력 줄은 없다
- MemberService.java(2:03): `[joinFail 본문 시작]` / `this 클래스=…MemberService` / `트랜잭션 활성? false`(한 줄을 셋으로 나누고 패키지·`트랜잭션 이름=null, 빌려 간 커넥션=0` 자름), `Query  COMMIT`, `[앱] 호출 뒤 member 테이블: 1행`

### 예시·소스·그림으로 쓴 것 (실행 출력이 아님)

- MemberService.java(0:00, 2:03), throw 줄(1:14, 1:40), `@Transactional(rollbackFor = Exception.class)`: 실험 코드 그대로. `join`에서 출력용 `Probe.*` 두 줄과 `Member member =` 대입을 뺐고, save 호출을 두 줄로 나눴다. `register`에서 `Probe.brief` 줄을 뺐다. `// this.joinFail`은 내 주석.
- TransactionAspectSupport.java(1:25): Spring Framework 7.0.10 `invokeWithinTransaction`의 일반(명령형) 경로를 줄인 것. 화면 첫 두 줄에 `// invokeWithinTransaction` / `// (일반 경로, 줄임)` 표시. 원본 순서 그대로 `createTransactionIfNecessary(…)` → `try { invocation.proceed…(); }` → `catch (Throwable ex) { completeTransactionAfterThrowing(…); throw ex; }` → `commitTransactionAfterReturning(…)`. 뺀 것: 대입, 인자, `finally { cleanupTransactionInfo(txInfo); }`, Future·Vavr 반환값 처리 블록, 리액티브·CallbackPreferring 분기.
- `@EnableTransactionManagement(` / `rollbackOn =` / `RollbackOn.ALL_EXCEPTIONS)`(1:56): 실험 코드와 같은 표기. `ALL_EXCEPTIONS`는 enum `org.springframework.transaction.annotation.RollbackOn`의 상수라, static import 없이는 `RollbackOn.`을 붙여야 컴파일된다(문서 annotations.adoc L425의 `rollbackOn=ALL_EXCEPTIONS`는 본문 속 약식 표기). 처음엔 문서 약식대로 `rollbackOn = ALL_EXCEPTIONS)`로 썼다가 그림 독립 검증에서 지적받아 고쳤다.
- self-call.txt(2:14): 개념 그림. 구조는 위 표의 self 호출 스택과 같다. 프록시 상자의 부제 "바깥 호출만 가로챔"은 annotations.adoc L224의 "only external method calls coming in through the proxy are intercepted".
- call-path.txt(0:29, 그림): 호출하는 쪽 →(join()) 프록시 → TransactionInterceptor → 진짜 join(). 위 표의 join 본문 스택에서 사이 프레임(CglibAopProxy, ReflectiveMethodInvocation, 리플렉션 등)을 뺀 순서 그대로다. 프록시 상자의 부제 `MemberService$$SpringCGLIB$$0`은 실행 출력의 클래스 이름(패키지 자름).
- tx-begin.txt(0:36, 그림): TransactionInterceptor →(시작) JpaTransactionManager → Hibernate, HikariCP →(연결) Hibernate, Hibernate →(`setAutoCommit(false)`) MySQL. 위 표의 `SET autocommit=0` 스택(`TransactionInterceptor` → `JpaTransactionManager.doBegin` → `HibernateJpaDialect.beginTransaction` → `LogicalConnectionManagedImpl.begin` → `HikariProxyConnection.setAutoCommit` → `ConnectionImpl.setAutoCommit`)을 줄인 것. 실제로 SQL 문자열을 MySQL에 보내는 건 MySQL 드라이버(`ConnectionImpl`)이고 Hikari 프록시 연결을 거치는데, 나레이션("매니저가 Hibernate를 시켜, 풀에서 연결을 빌리고 autocommit을 꺼요")에 맞춰 드라이버 칸은 그리지 않았다(5번 영상에서 다룸). 화살표 라벨은 Hibernate가 실제로 부르는 JDBC 메서드 `setAutoCommit(false)`(`AbstractLogicalConnectionImplementor.java#L69`)다. `SET autocommit=0` 문자열은 hibernate-core 7.4.13 소스에 없고 Connector/J `ConnectionImpl`에 있어서, 처음 라벨 `SET autocommit=0`은 Hibernate가 SQL을 보내는 것처럼 읽혔다(5번 영상의 "Hibernate는 … JDBC만 불러요"와도 어긋남). 그림 독립 검증에서 지적받아 고쳤다. MySQL이 받는 `SET autocommit=0`은 1:08 general.log 장면이 보여 준다.
- thread.txt(0:53, 그림): 틀 "지금 스레드" 안 첫 줄에 연결(`ConnectionHolder`)과 EntityManager(`EntityManagerHolder`) — 위 표의 "이 스레드에 묶인 자원 2개" 출력. 둘째 줄에 같은 스레드에서 도는 join()과 save()(나레이션 "같은 스레드의 데이터 접근 코드"의 조건을 그림에도 보이려고 틀 안에 넣음, 처음엔 틀 밖이었다). EntityManager →(꺼내 씀) save(): repository 쪽이 스레드에 묶인 `EntityManagerHolder`를 찾는다(`EntityManagerFactoryUtils.java#L207`, 로그 `Found thread-bound EntityManager`). save()가 쓰는 건 EntityManager라서 화살표는 EntityManager에서만 긋고, 같은 연결을 쓴다는 건 표의 `스레드에 묶인 Connection == Hibernate가 쓰는 Connection ? true`가 근거. join() → save()는 호출.
- rollback-rule.txt(1:40, 그림): 맨 위 글자 "기본 규칙: 밖으로 나온 예외". 메서드 밖으로 나온 예외가 RuntimeException(+ Error 계열)이면 ROLLBACK, checked 예외(예: Exception)면 COMMIT. "기본 규칙"은 나레이션과 요약 그림("기본은 COMMIT")의 조건을 맞춘 것(처음엔 "메서드 밖으로 예외"라 조건이 없었다). "메서드 밖으로"는 규칙이 `invokeWithinTransaction`의 catch에 잡힌 예외(= 메서드가 던진 예외)에 적용되기 때문(`completeTransactionAfterThrowing`). COMMIT 상자 부제 "실험: 행이 남음"은 joinChecked("park") 결과 1행, 배지 "EJB 관례"는 `DefaultTransactionAttribute` javadoc "The default behavior is as with EJB".
- summary.md(2:31, 그림): 호출 → 프록시(try로 감쌈) → 트랜잭션 매니저(시작, 커밋, 롤백)와 진짜 메서드. 프록시(안의 인터셉터)가 매니저와 진짜 메서드를 각각 부르므로 화살표를 프록시에서 둘로 나눴다(매니저가 진짜 메서드를 부르는 게 아니다). 틀 "따로 챙길 것": this 호출(프록시 안 거침), checked 예외(기본은 COMMIT — "기본" 조건을 붙였다).

### 그 밖의 결정

- 이야기 구조: 훅(코드에 시작·커밋이 없다) → 프록시 → 인터셉터·매니저가 시작 → 스레드 → 커밋·롤백 → Spring 코드(try/catch)로 묶음 → catch의 규칙(checked) → this 호출 → 정리. 장점·단점 절은 두지 않았다(주제가 "어떻게 동작하나"라서).
- 예시 이름은 5번 영상과 이어지게 `Member`, `MemberService`, 값 `kim`을 썼다. 시나리오마다 이름(kim, lee, park, choi, jung)을 달리해 로그와 행을 구분했다.
- `pronounce`: @Transactional 트랜잭셔널, TransactionInterceptor 트랜잭션인터셉터, MemberService 멤버서비스, Spring Boot 스프링 부트, Spring 스프링, EntityManager 엔티티매니저, RuntimeException 런타임익셉션, Exception 익셉션, Error 에러, rollbackFor 롤백포, joinFail 조인페일, join 조인, save() 세이브, autocommit 오토커밋, COMMIT 커밋, ROLLBACK 롤백, MySQL 마이에스큐엘, JDBC 제이디비씨, SQL 에스큐엘, insert 인서트, checked 체크드, this 디스, try 트라이, catch 캐치, throws 쓰로우즈, register 레지스터, Hibernate 하이버네이트, EJB 이제이비. `say`를 쓴 문장은 없다(단어 수 불일치가 한 번도 나지 않았다).
- 한글로 둔 말: 프록시, 트랜잭션, 트랜잭션 매니저, 커넥션 풀, 스레드, 예외, 커밋·롤백(동사 "커밋돼요", "커밋했어요", "롤백하거든요", "롤백으로"). 명령 자체는 `COMMIT`, `ROLLBACK`.
- 길이:
  - 첫 판(사실 확인 전): 32문장, film 168.42 s.
  - 사실 확인 반영 뒤: 문장을 고치고 "그래서 비즈니스 코드엔, 트랜잭션 코드가 한 줄도 없어요."(앞 문장과 훅의 반복)를 뺐다.
    `build.py`의 타이핑 속도 경고(shot-06 32자/s, shot-09 49자/s, shot-10 43자/s)를 없애느라 rollbackFor 문장에 전역 설정을 붙여 나레이션과 화면을 맞추고, self 호출 결과 문장을 화면 내용("ROLLBACK은 없고")만큼 늘리고, hold(0.7 s, 0.5 s)를 줬다.
    대신 이유 없는 연결 문장 두 개를 합치거나 뺐다: "이번엔 save() 다음에, RuntimeException을 던져 볼게요." + "그러면 COMMIT 대신 ROLLBACK을 보내요." → 한 문장, "그런데 catch에서 늘 롤백하는 건 아니에요." 삭제("하지만"으로 대비만 남김). 최종 29문장, film 167.35 s. 답안 항목과 '왜' 문장은 빼지 않았다.
- self 호출 다이어그램: 처음엔 register()와 joinFail()을 가로로 두었는데, 프록시 → register 대각선 화살표가 틀 이름 "진짜 MemberService"를 가로지르고 "this" 라벨이 상자에 붙었다. 세로 한 줄(register 위, joinFail 아래, "this"는 화살표 옆)로 바꾸고 틀 이름을 "진짜 객체"로 줄였다.
- 다이어그램으로 바꾼 장면(2026-11-02, 첫 렌더를 본 사용자가 "텍스트가 너무 많다"고 해서): 0:29 stack.txt → call-path.txt, 0:36 app.log → tx-begin.txt, 0:53 resources.txt → thread.txt, 1:40 general.log(10줄) → rollback-rule.txt 그림 + 1:56 rollback.txt(6줄 박스)로 나눔, 2:31 summary.md 글자 → 그림. 나레이션은 한 글자도 바꾸지 않았다(사실 확인을 마친 문장 그대로). 그림의 상자·라벨은 위 표의 근거와 하나씩 대조했다("예시·소스·그림으로 쓴 것"). 실제 출력이 증거인 장면(프록시 클래스 이름, COMMIT·ROLLBACK general log, this 호출 결과)과 Spring 코드 장면은 박스로 남겼다. 장면 수 12 → 13, 다이어그램 1 → 6장면.
  - 캡처에서 고친 것: thread.txt의 save() 배지 "합류"가 들어오는 화살표 끝을 가려서 배지를 빼고 focus로만 강조, rollback-rule.txt의 배지 "EJB 관례"가 "checked 예외" 글자에 닿아서 COMMIT 상자로 옮김, call-path.txt 첫 화살표 라벨 `join()`이 위 글자에 붙어서 줄 간격을 84px로 늘림.
- 썸네일: 제목 `@Transactional` / `어떻게` / `동작할까?`, 부제 `# 코드엔 커밋이 없는데`, 제목줄 `❯ cat MemberService.java`. `thumbnail.py`가 `title font down to 118px`를 냈다. 가장 긴 줄이 나눌 수 없는 이름 `@Transactional` 하나라서 그대로 두었다. 이미지를 열어 보니 제목이 박스 폭을 채우고 한눈에 읽힌다.

### 독립 사실 확인 반영 기록 (2026-11-02)

렌더 전에 독립 리뷰어가 초안을 v7.0.10 소스, 실험 로그, 같은 jar로 직접 다시 돌린 결과(commit, self, checked)와 대조했다. 화면의 실행 출력 줄은 모두 원본 로그와 맞았고, 받아 둔 소스 사본도 태그와 같았다. 고친 것:

| # | 지적 | 바꾼 것 (전 → 후) |
|---|---|---|
| 1 | 0:36–0:45 주어가 틀림: 인터셉터는 `getTransaction`/`commit`/`rollback`만 부르고, 연결 획득·`setAutoCommit(false)`는 `JpaTransactionManager.doBegin` → `HibernateJpaDialect` → Hibernate가 한다. 스레드에 묶는 것도 매니저 | "TransactionInterceptor는 진짜 join을 부르기 전에, 트랜잭션부터 시작해요." → "TransactionInterceptor는 진짜 join을 부르기 전에, 트랜잭션 매니저에게 시작을 맡겨요." / "커넥션 풀에서 연결을 하나 빌려, autocommit을 끄는 거예요." → "매니저가 Hibernate를 시켜, 풀에서 연결을 빌리고 autocommit을 꺼요." / 화면에 실제 로그 `JpaTransactionManager : Creating new transaction with name […MemberService.join]` 추가. 이어지는 0:53(스레드에 묶음), 1:08(COMMIT, autocommit 복구, 반납), 1:14(ROLLBACK)은 숨은 주어가 매니저(+Hibernate)여도 맞는지 스택으로 확인하고 그대로 두었다. 정리 문장도 같은 이유로 고침: "…프록시가 메서드 호출을 try로 감싸서, 시작과 커밋과 롤백을 대신 해 주는 거예요." → "…프록시가 메서드 호출을 try로 감싸고, 트랜잭션 매니저가 시작과 커밋, 롤백을 맡는 구조예요.", 화면 `시작:` → `매니저:` |
| 2 | 1:57 근거를 오해하게 씀: javadoc은 EJB 관례라고 하고, 6.2부터 문서는 EJB식 비즈니스 예외에 기대지 않으면 ALL_EXCEPTIONS를 권한다 | "checked 예외는 업무상 미리 예상한 결과, 일종의 다른 반환값으로 봐요." → "EJB 시절 관례대로, checked 예외를 예상한 결과, 일종의 다른 반환값으로 봐요." / 화면 rollbackFor 덩어리에 `# Spring 6.2+ 전역 설정:` `@EnableTransactionManagement(` `rollbackOn = ALL_EXCEPTIONS)` 추가 |
| 3 | 0:56 javadoc상 스레드 자원은 자원 관리 코드용 | "같은 스레드에서 도는 코드라면, 어디서든 꺼내 쓸 수 있게요." → "같은 스레드의 데이터 접근 코드가, 인자로 안 받아도 꺼내 쓰게요." |
| 4 | 1:48 동격 표현이 "checked 예외 = Exception 클래스"로 읽힘 | "throws로 선언해야 하는 checked 예외, Exception을 던지면 기본 규칙에선 커밋돼요." → "하지만 Exception처럼 throws로 선언해야 하는 checked 예외를 던지면, 기본 규칙에선 커밋돼요." |
| 5 | 코드 상자가 일반 경로만인데 표시가 없음 | `// invokeWithinTransaction (줄임)` → `// invokeWithinTransaction` / `// (일반 경로, 줄임)` |
| 길이 | 170 s 안에 두려고 반복 문장을 뺌 | "그래서 비즈니스 코드엔, 트랜잭션 코드가 한 줄도 없어요." 삭제 |

리뷰어가 동의해서 일부러 그대로 둔 것: "예외 없이 돌아오면 커밋"(rollback-only 경우는 다음 영상), "다른 클래스로 옮기고"(문서의 self-invocation 피하기 중 한 방법), 훅 문장, final 메서드 관련 단서(영상에 없음), `REQUIRED` 전제, repository 프록시가 JDK 프록시라는 점(영상에 안 나옴).

### 그림 독립 사실 확인 반영 기록 (2026-11-02)

다이어그램으로 바꾼 장면(0:29, 0:36, 0:53, 1:40, 1:56, 2:31)은 위 확인 뒤에 만들어서, 따로 독립 리뷰어가 렌더된 MP4의 끝 프레임과 정확한 버전의 sources jar(spring-tx/orm 7.0.10, hibernate-core 7.4.13.Final, HikariCP 7.0.2, spring-boot-transaction 4.1.2), v7.0.10 문서 원문으로 다시 봤다. 틀림은 없었고 고친 것:

| # | 지적 | 바꾼 것 |
|---|---|---|
| 1 | 오해 소지: tx-begin의 Hibernate → MySQL 라벨 `SET autocommit=0`이 Hibernate가 SQL을 보내는 것처럼 읽힘(실제로는 JDBC `setAutoCommit(false)`를 부르고 문장은 드라이버가 만듦) | 라벨 → `setAutoCommit(false)`, 라벨이 HikariCP 상자에 닿지 않게 줄 간격 72 → 96px |
| 2 | 오해 소지: rollback-rule 그림에 "기본" 조건이 없어 checked → COMMIT이 무조건처럼 읽힘 | 맨 위 글자 "메서드 밖으로 예외" → "기본 규칙: 밖으로 나온 예외" |
| 3 | 오해 소지: rollback.txt의 `rollbackOn = ALL_EXCEPTIONS)`는 static import 없이 컴파일 안 됨(바로 위 rollbackFor 줄은 그대로 쓸 수 있는 코드라 같이 복사하기 쉬움) | `rollbackOn =` / `RollbackOn.ALL_EXCEPTIONS)` 두 줄로, hold 0.5 → 1.0 s |
| 4 | 사소: Java 코드 사이의 `#` 주석 | `//`로 |
| 6 | 사소: thread 그림에서 join()·save()가 "지금 스레드" 틀 밖이라 "같은 스레드의" 조건이 안 보임 | 두 상자를 틀 안 둘째 줄로 |

그대로 둔 것(리뷰어도 선택 사항이라 함): summary 그림 프록시 상자 부제 "try로 감쌈"(실제 try는 프록시 안의 `TransactionInterceptor`, 나레이션 "프록시가 … try로 감싸고"와 문서 "AOP proxy that uses a TransactionInterceptor" 수준에 맞춤), tx-begin의 HikariCP → Hibernate "연결" 화살표 방향(부르는 쪽은 Hibernate의 `getConnection()`이지만 나레이션 "풀에서 연결을 빌리고"의 흐름 방향).

## 측정한 것 / 보기만 한 것

- 렌더(그림 독립 검증 반영 뒤): 1080x1920, 30 fps, 168.47 s(2:48), 16.3 MB. 3분 한도까지 약 11.5 s 남는다. (첫 렌더 167.37 s → 다이어그램 수정 167.97 s → rollback.txt hold 0.5 → 1.0 s로 168.45 s. 위 시각 표기는 1:56 이후 약 1 s 늦다.)
- 오디오: 통합 -14.0 LUFS, 피크 -1.5 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 12건(아래). 다른 종류의 경고는 없었다.
- `build.py`(다이어그램 수정 뒤 다시 빌드): 마지막 빌드에서 `font down to`, `chars/s`, `diagram text down to` 경고 없음. `thumbnail.py`: 제목 118px(위 "그 밖의 결정").
- 화면: 장면마다 가운데와 끝 직전(컷 0.15초 전)을 캡처해서 봤고(25장), 다이어그램을 고친 뒤 그 장면을 세 시점에서 다시 봤다. 렌더한 MP4에서도 두 프레임(0:52, 2:00)을 뽑아 캡처와 같은지 확인했다.
  - 0초 프레임에 첫 박스(`@Transactional` join 코드)와 첫 자막이 보인다.
  - 모든 장면 끝 프레임에서 글자가 판 안에 있다. 다이어그램 수정 뒤 바뀐 6장면의 끝 프레임을 다시 캡처해 원본 크기로 봤다(배지·라벨 겹침 없음). 가장 빽빽한 박스는 이제 2:03 MemberService.java(8줄)다.
  - 자막은 모두 2줄 안이다. 기술 용어는 영어로 나온다(한글 음차 없음).
  - 고친 것: self 호출 다이어그램의 화살표·라벨 겹침(위 "그 밖의 결정").
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - **@Transactional(0:00, 2:03, 2:31)**: "트랜잭셔널"로 읽히는지
  - **TransactionInterceptor(0:29, 0:36)**: "트랜잭션인터셉터"를 한 단어로 붙여 읽게 했다
  - **MemberService를(0:12)**: "멤버서비스를"
  - **Hibernate를(0:42)**, **EntityManager를(0:53)**
  - **throws로(1:40)**: "쓰로우즈로", **checked 예외(1:40, 1:50, 1:56, 2:40)**: "체크드 예외"
  - **EJB 시절(1:50)**: "이제이비 시절"
  - **rollbackFor로(1:56)**: "롤백포로", **Spring 6.2부터는(1:56)**: 숫자 "육 점 이"로 읽히는지
  - **register에서(2:03)**: "레지스터에서", **this는(2:14), this 호출과(2:40)**: "디스"
  - **try와 catch(1:25)**, **save()처럼(0:00)**, **RuntimeException과 Error(1:46)**

## 일부러 남긴 경고

`line_unread` 12건(다이어그램 수정 전 16건 — 스택·자원 장면이 그림이 되며 4건 줄었다). 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: `Query ROLLBACK`을 13단어로 셈). 실제로는 대부분 한두 단어짜리 코드·로그 줄이다.

- shot-06(commit general.log) `Query insert … ('kim')`, `Query SET autocommit=1`, `[앱] 호출 뒤: 빌려 간 커넥션 0개`: hold 0.7 s
- shot-07(rollback) `Query insert … ('lee')`, `Query ROLLBACK`, `[앱] 호출 뒤 member 테이블: 0행`
- shot-08(TransactionAspectSupport.java) `commitTransactionAfterReturning(…);`
- shot-10(rollback.txt) `@EnableTransactionManagement(`, `RollbackOn.ALL_EXCEPTIONS)`: hold 1.0 s, 나레이션이 같은 내용("Spring 6.2부터는 전역 기본값도 바꿀 수 있어요")을 말한다
- shot-11(register) `this 클래스=…MemberService`, `Query COMMIT # ROLLBACK 없음`, `[앱] 호출 뒤 member 테이블: 1행`: hold 0.5 s

더 줄이려면 장면마다 hold를 늘려야 한다. 이미 나레이션이 같은 내용을 말하는 줄이라 그대로 뒀다.

## 가장 약한 부분

- **"예외 없이 돌아오면 커밋"(1:29)**: `commitTransactionAfterReturning` 경로를 말한 것이다. 안쪽에서 합류한 트랜잭션이 실패해 rollback-only로 표시됐다면 commit 호출이 실제로는 롤백한다(`UnexpectedRollbackException`). 전파 주제라 뺐다.
- **"Spring 코드로 보면, 이 흐름은 try와 catch 하나예요"(1:25)**: 명령형 `PlatformTransactionManager` 경로만 해당한다(화면에 "일반 경로" 표시). 리액티브 반환형과 `CallbackPreferringPlatformTransactionManager`는 다른 분기다.
- **"다른 클래스로 옮기고, 주입받아서 부르면 프록시를 거쳐요"(2:26)**: 문서가 권하는 건 "self invocation이 없도록 코드를 고치기"이고, 옮기기는 그 한 방법이다. 문서의 다른 대안(self injection, `AopContext.currentProxy()`, AspectJ 모드)은 말하지 않았다.
- **첫 문장 "@Transactional 한 줄만 붙이면 트랜잭션 안에서 실행돼요"(0:00)**: 프록시를 거쳐 부를 때만 맞다. 2:03–2:31에서 예외를 다룬다.
- **"Spring Boot 기본 설정에선, 상속한 프록시"(0:18)**: 인터페이스를 구현한 서비스도 Boot 기본값(`spring.aop.proxy-target-class=true`)에선 CGLIB이다. 실험은 인터페이스 없는 클래스로만 했다.
- **전역 롤백 설정(1:56)**: Boot 4.1.2엔 이를 바꾸는 `spring.*` 속성이 없어 `@EnableTransactionManagement`를 직접 써야 하고, 그러면 Boot의 트랜잭션 관리 자동 설정이 빠진다(`@ConditionalOnMissingBean(AbstractTransactionManagementConfiguration.class)`). 실험에선 프록시가 여전히 CGLIB이었지만(AOP 자동 설정이 클래스 프록시를 강제), 영상은 이 단서를 말하지 않았다.
- **0:36 tx-begin.txt 그림**: Hibernate에서 MySQL로 바로 `setAutoCommit(false)` 화살표를 그었다. 실제로는 Hikari 프록시 연결과 MySQL 드라이버를 거친다(위 "예시·소스·그림으로 쓴 것"). 나레이션과 같은 수준으로 줄인 것이고, 드라이버 칸은 5번 영상에서 다뤘다.
- 실험의 원본 로그·소스 사본·실험 앱 소스(`z_임시/transactional_실험/`, 사실표.md 포함)는 2026-11-02 사용자 요청으로 지웠다. 이 REVIEW는 그 파일 없이 읽히도록 핵심 줄을 옮겨 적었다.
