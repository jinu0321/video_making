# REVIEW

## 시청 후 답할 수 있는 것

질문: **`@Transactional`을 붙이면 내 필드에 들어오는 '프록시 클래스'는 정체가 뭐고, 누가 언제 만들어 넣나요? 그래서 final·private 메서드엔 왜 트랜잭션이 안 걸리나요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **정체: 실행 중에 메모리에서 만든 `MemberService`의 하위 클래스(`MemberService$$SpringCGLIB$$0`)다. 그래서 이 영상의 빌드 결과(bootJar)엔 그 클래스 파일이 없다.**
   왜: CGLIB(spring-core에 들어 있음)이 바이트 배열을 만들어 바로 클래스로 정의한다. 파일로 쓰는 건 디버그 옵션(`cglib.debugLocation`)을 켰을 때뿐이다. (0:00 run.log, 1:02 auto-proxy.txt 그림)
2. **누가·언제: 생성자와 `@PostConstruct` 같은 초기화가 끝난 뒤, 자동 프록시 생성기라는 BeanPostProcessor가 만든다(Spring Boot 기본 설정 기준).**
   왜: BeanPostProcessor는 받은 빈을 그대로 돌려주거나 다른 객체로 바꿔 돌려줄 수 있다. 컨테이너는 마지막에 돌려받은 객체를 빈으로 등록하고 주입한다. 그래서 초기화 때의 `this`는 진짜 `MemberService`인데, 등록된 빈과 내 필드는 프록시다. (0:14 bean-lifecycle.txt 그림, 0:36 startup.log)
3. **누구를 감싸나: 클래스나 메서드에 `@Transactional`이 있으면 그 빈을 프록시로 감싼다. `@Transactional`도 `@Cacheable` 같은 부가 기능도 없는 빈(`PlainService`)은 받은 그대로 돌려준다.**
   왜: 생성기는 그 빈에 맞는 advisor가 하나라도 있으면 감싼다. 트랜잭션 advisor는 메서드나 클래스에 `@Transactional`이 있으면 맞고, `@Cacheable`만 있는 빈도 캐시 advisor 때문에 감싸진다(실험). (0:47 auto-proxy.txt 그림)
4. **프록시 객체는 기본으로 Objenesis를 써서 생성자를 부르지 않고 만든다. 그래서 생성자는 진짜 객체를 만들 때 한 번만 돈다. 대신 프록시의 필드(`memberRepository`)는 null이고, 콜백 필드에 인터셉터가 들어 있다.** (1:08 proxy-object.txt 그림)
5. **프록시가 덮어쓴 메서드는 내 코드를 직접 실행하지 않고, 콜백의 `intercept`로 넘긴다. 콜백은 TransactionInterceptor를 거쳐 진짜 객체의 메서드를 부른다.**
   왜: 프록시는 초기화가 끝난 진짜 빈을 감싸서 만든 것이고, 필드가 채워진 것도 진짜 객체 쪽이기 때문이다. (1:24 proxy-join.java)
6. **`final` 메서드는 하위 클래스가 덮어쓸 수 없다. 그래서 프록시에 대고 불러도 부모 코드가 빈 프록시 객체 위에서 돈다. 트랜잭션이 없고, 주입 필드를 쓰면 NullPointerException이 난다. 시작 때 남는 건 WARN 한 줄뿐이다.**
   대처: 하위 클래스 프록시가 되는 빈에선 메서드에 final을 붙이지 않는다. `@Transactional`이 없는 final 메서드도 같은 일을 겪는다(실험). (1:41 overrides.log, 1:52 final-call.txt 그림, 2:06 run.log)
7. **`private` 메서드도 덮어쓸 수 없어 가로채지 못하고, 경고조차 없다. 반대로 `protected`와 같은 패키지의 package-private은 덮어쓸 수 있다. 그래서 Spring 6.0부터 클래스 기반 프록시에선 이런 메서드에도 트랜잭션이 걸린다.**
   왜: 프록시가 가로챌 수 있는 곳은 하위 클래스가 덮어쓴 메서드뿐이다. 다른 패키지에 있는 부모의 package-private 메서드는 덮어쓸 수 없어 걸리지 않는다(실험). (2:17 visibility.txt 그림)

기억할 한 문장: "프록시 클래스는 빈 초기화가 끝난 뒤 BeanPostProcessor가 CGLIB으로 만든 하위 클래스이고, 덮어쓴 메서드로만 가로채니 final·private 메서드엔 트랜잭션이 안 걸린다." (2:34 summary.md)

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
npx --yes hyperframes@0.8.209 render -o "output/transactional_의_작동_원리_프록시_클래스.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/transactional_의_작동_원리_프록시_클래스.mp4"
ffmpeg -nostats -i "output/transactional_의_작동_원리_프록시_클래스.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 6번 영상은 프록시가 *있다는 것*과 호출 경로(프록시 → TransactionInterceptor → 진짜 메서드), 트랜잭션 시작·커밋·롤백, 기본 롤백 규칙, this 호출을 가르쳤다. 이 영상은 그중 아무것도 다시 가르치지 않고 **프록시 클래스 자체**만 다룬다. 정체(실행 중 만든 하위 클래스), 만드는 주체와 시점(BeanPostProcessor, 초기화 뒤), 인스턴스 모양(Objenesis, 빈 필드, 콜백), 덮어쓴 메서드의 동작, 그리고 "하위 클래스"라서 생기는 일(final·private·protected·package-private)이다.
- 6번 영상과는 첫 문장("지난 영상에서 봤듯이…")과 6번 장면의 "TransactionInterceptor를 거쳐" 한 구절로만 이었다. 예시 이름(`Member`, `MemberService`, `join`, 값 `kim`·`lee`)도 6번 영상 그대로 썼다.
- 입문자가 보고 나서 할 수 있는 것: 로그의 `$$SpringCGLIB$$`가 어디서 왔는지 설명하기, 프록시가 내 필드에 들어오는 순서 말하기, `@Transactional`을 붙였는데 final·private 메서드라서 트랜잭션이 안 걸리는 이유와 대처(final 빼기, 같은 패키지·protected는 6.0부터 됨) 말하기.
- 다음 영상 후보(범위를 좁히느라 뺀 것):
  - **JDK 동적 프록시와 CGLIB**: `spring.aop.proxy-target-class`(Boot 기본 true), 인터페이스가 있어도 Boot 기본은 CGLIB, `false`면 인터페이스 구현 빈은 `$Proxy104`(JDK), Spring Data repository가 `jdk.proxy2.$Proxy102`인 이유. 실험 결과는 아래에 있다.
  - **Objenesis를 끄면**: `spring.objenesis.ignore=true`에선 기본 생성자 없는 클래스(생성자 주입)는 프록시를 못 만들고 시작이 실패한다(아래 실험 R3).
  - **`@PostConstruct` 안에서 트랜잭션을 기대하면 안 되는 이유**: 프록시가 초기화 뒤에 생기기 때문(SFD annotations.adoc L228-229). this 호출과 겹쳐 뺐다.
  - **프록시 클래스가 구현하는 인터페이스**(`SpringProxy`, `Advised`, `Factory`)와 콜백 7개의 역할.
  - **순환 참조와 이른 프록시**(`getEarlyBeanReference`), **AOT로 미리 만든 프록시 클래스**, **Kotlin 클래스가 기본 final**인 문제와 all-open 플러그인.

### 실험 환경과 재현 (2026-11-02)

- 호스트: macOS (Darwin 25.5.0), arm64, Docker client/server 29.9.2. 앱은 호스트 JDK 25.0.4(Microsoft build) + Gradle wrapper 9.8.2로 빌드하고 컨테이너에서 실행했다(6번 영상과 같은 방식). 클래스 덤프는 호스트 `javap` 25.0.4로 읽었다.
- 이미지: `mysql:8.4` (`sha256:a0225d1ea6631c8bc2385dc4c2faba17bbf1834ecf369e1659a9a382bd8d5dd7`, `SELECT VERSION()` → 8.4.13), `eclipse-temurin:25-jre` (`sha256:78f1f183913482ef390c2722f46c3f0ce76ada341d69590e7c482ec943ee72d5`). 6번 영상과 같은 이미지 ID. 전용 네트워크 `px-net`, MySQL 컨테이너 `px-mysql`, 호스트에 포트를 열지 않았다.
- 앱이 찍은 버전: Java 25.0.4.1 (Eclipse Adoptium), Spring Boot 4.1.2, Spring Framework 7.0.10, Spring Data JPA 4.1.2, Hibernate ORM 7.4.13.Final, MySQL Connector/J 9.7.0, MySQL 8.4.13. HikariCP는 앱이 패키지 버전을 `null`로 찍어서 jar 이름 `BOOT-INF/lib/HikariCP-7.0.2.jar`로 확인했다. AspectJ는 `aspectjweaver-1.9.25.1.jar`.
- 의존: `build.gradle.kts`는 `spring-boot-starter-data-jpa`와 `mysql-connector-j` 둘뿐(6번 영상 블로그 실험 E2와 같은 형식). `./gradlew dependencies` 출력: `spring-boot-starter-data-jpa -> 4.1.2` → `spring-boot-data-jpa:4.1.2` → `spring-aspects:7.0.10` → `aspectjweaver:1.9.25.1`. 비교용 jar(`-PnoAspectj`)는 `spring-aspects`와 `aspectjweaver`를 뺐다.
- `application.properties`: `spring.datasource.url=jdbc:mysql://px-mysql:3306/pxdemo`, `spring.jpa.hibernate.ddl-auto=create`, `spring.jpa.open-in-view=false`. `logback-spring.xml`이 `org.springframework.aop.framework.CglibAopProxy` 로거를 TRACE로 켜고, "Creating CGLIB proxy …MemberService@…"를 로그로 남기는 순간의 호출 스택을 찍는 관찰용 appender를 붙였다.
- 실험 코드(관찰용 출력 줄 빼고, 요지):

```java
@Service
public class MemberService {
    private final MemberRepository memberRepository;
    private final String createdBy;
    public MemberService(MemberRepository memberRepository) {   // 생성자 주입, 기본 생성자 없음
        this.memberRepository = memberRepository; this.createdBy = "생성자"; /* 실행 횟수 +1 */ }
    @PostConstruct void init() { /* this 출력 */ }
    @Transactional public void join(String name) { memberRepository.save(new Member(name)); }
    @Transactional protected void protectedJoin(String name) { /* 같음 */ }
    @Transactional void packageJoin(String name) { /* 같음 */ }
    @Transactional public final void finalJoin(String name) { memberRepository.save(new Member(name)); }
    @Transactional private void privateJoin(String name) { /* 같음 */ }
    public void callPrivate(String name) { privateJoin(name); }   // @Transactional 없음
}
@Service public class PlainService { public String hello() { return "hello"; } }   // 부가 기능 없음
// extra 프로필(R6)에서만:
@Service @Transactional public class ClassTxService { public void hello() {…} }          // 클래스에만 @Transactional
@Service public class CacheOnlyService { @Cacheable("names") public String name(Long id) {…} }  // @EnableCaching + ConcurrentMapCacheManager
package com.example.px.base; public class BaseService {                                     // 다른 패키지의 부모
    @Transactional void basePkg() {…}  @Transactional protected void baseProt() {…} }
@Service public class ChildService extends BaseService {}                                   // com.example.px
@Service public class FinalCaseService { private final MemberRepository memberRepository; …
    @Transactional public void tx() {}
    public final String repoName() { return memberRepository.getClass().getName(); }     // 애노테이션 없음, 필드 씀
    @Transactional public final void finalTxNoField() {…}                                 // 필드 안 씀
}
```

- 관찰용 BeanPostProcessor 둘: `EarlySpy`(PriorityOrdered, 가장 높은 우선순위 → 생성기보다 앞, 등록 순서 4번), `LateSpy`(순서 없음 → 생성기 7번 뒤 9번). 호출은 같은 패키지의 `Runner`(ApplicationRunner)가 주입받은 필드로 한다.
- 실행(앱 컨테이너 `--rm`, 모두 `-v app/build/libs:/app:ro --network px-net eclipse-temurin:25-jre`):

| 이름 | 명령 요지 | 종료 |
|---|---|---|
| R1 | `java -Dcglib.debugLocation=/dump -jar /app/px.jar` (Boot 기본 설정, 생성된 클래스를 파일로 떨굼) | 0 |
| R2 | `java -jar /app/px.jar --spring.aop.proxy-target-class=false` | 0 |
| R3 | `java -Dspring.objenesis.ignore=true -jar /app/px.jar` | 1 (의도한 실패) |
| R4 | `java -jar /app/px-noaspectj.jar` | 0 |
| R5 | `java -jar /app/px.jar --logging.level.org.springframework.aop.framework.CglibAopProxy=INFO` (Boot 기본 로그 수준) | 0 |
| R6 | `java -jar /app/px.jar --spring.profiles.active=extra` (사실 확인 뒤 추가) | 0 |

- 덤프한 `com/example/px/MemberService$$SpringCGLIB$$0.class`는 `javap -p -c`로 읽었다. 독립 리뷰어가 같은 jar로 다시 돌린 덤프와 바이트 단위로 같았다.
- 화면의 identityHashCode(`@178ebac3`, `@57806346`)는 마지막 R1 실행 값이다. jar가 바뀌면 값이 바뀐다(R6용 클래스를 추가하기 전 실행에선 `@5dd2ea0a`, `@43dddfdd`). 줄 번호와 다른 출력은 같았다.

### 쓴 사실과 출처 (2026-11-02 확인)

출처는 실행한 버전의 태그로 고정했다. 약칭: **SF** = `https://github.com/spring-projects/spring-framework/blob/v7.0.10/`, **SFD** = SF + `framework-docs/modules/ROOT/pages/` (docs.spring.io/spring-framework/reference 에 게시되는 원문), **SB** = `https://github.com/spring-projects/spring-boot/blob/v4.1.2/`, **JLS** = `https://docs.oracle.com/javase/specs/jls/se25/html/jls-8.html`. 로그 줄은 시각만 빼고 그대로 옮겼다(`…`는 내가 자른 곳).

| 영상 속 내용 | 근거 |
|---|---|
| 주입된 MemberService는 이 프록시 클래스(0:00) | 6번 영상 REVIEW(`memberService.getClass() : com.example.tx.MemberService$$SpringCGLIB$$0`). 이번 R1: `Runner에 주입된 memberService 필드` / `  = MemberService$$SpringCGLIB$$0@57806346` |
| 빌드한 jar 파일엔 이 클래스가 없다(0:05) | `$ jar tf px.jar \| grep MemberService` → `BOOT-INF/classes/com/example/px/MemberService.class` 한 줄뿐, `jar tf px.jar \| grep -c SpringCGLIB` → `0`. R1 `클래스패스에 com/example/px/MemberService$$SpringCGLIB$$0.class 파일이 있나? false` |
| 생성자로 객체를 만들고 @PostConstruct 같은 초기화를 부른다(0:14) | SF `spring-beans/src/main/java/org/springframework/beans/factory/support/AbstractAutowireCapableBeanFactory.java#L563` `instanceWrapper = createBeanInstance(beanName, mbd, args);` → `#L600-L601` `populateBean(…); exposedObject = initializeBean(beanName, exposedObject, mbd);`, initializeBean `#L1807` `applyBeanPostProcessorsBeforeInitialization`, `#L1811` `invokeInitMethods`. SFD `core/beans/factory-extension.adoc#L46-L50` "for each bean instance that is created by the container, the post-processor gets a callback from the container both before container initialization methods (such as `InitializingBean.afterPropertiesSet()` or any declared `init` method) are called, and after any bean initialization callbacks." R1 순서: `[생성자] MemberService 객체 생성 MemberService@178ebac3` → `[@PostConstruct] this = MemberService@178ebac3` |
| 초기화가 끝나면 BeanPostProcessor들에게 차례로 넘긴다(0:20) | `AbstractAutowireCapableBeanFactory.java#L1818` `wrappedBean = applyBeanPostProcessorsAfterInitialization(wrappedBean, beanName);`, `#L435-L447` `for (BeanPostProcessor processor : getBeanPostProcessors()) { Object current = processor.postProcessAfterInitialization(result, beanName); … result = current; }`. SF `spring-beans/.../config/BeanPostProcessor.java#L87` "Apply this BeanPostProcessor to the given new bean instance <i>after</i> any bean initialization callbacks". R1: @PostConstruct 줄 다음에 `[EarlySpy, 초기화 후, 자동 프록시 생성기보다 앞] 받은 빈 = MemberService@178ebac3`. 등록된 BeanPostProcessor 13개 중 4번 `com.example.px.EarlySpy`, 7번 `org.springframework.aop.aspectj.annotation.AnnotationAwareAspectJAutoProxyCreator`, 9번 `com.example.px.LateSpy` |
| 그대로 돌려줘도 되고 다른 객체로 바꿔 돌려줘도 된다(0:25) | `BeanPostProcessor.java#L101` "@return the bean instance to use, either the original or a wrapped one", `#L24-L25` "Factory hook that allows for custom modification of new bean instances — for example, checking for marker interfaces or wrapping beans with proxies." SFD `factory-extension.adoc#L51-L54` "The post-processor can take any action with the bean instance, including ignoring the callback completely. A bean post-processor typically checks for callback interfaces, or it may wrap a bean with a proxy. Some Spring AOP infrastructure classes are implemented as bean post-processors in order to provide proxy-wrapping logic." |
| 컨테이너는 마지막에 돌려받은 객체를 빈으로 등록하고 주입한다(0:30) | initializeBean이 `wrappedBean`을 돌려주고(`#L1821`) doCreateBean의 `exposedObject`가 된다(`#L601`). SF `spring-beans/.../support/DefaultSingletonBeanRegistry.java#L371` `singletonObject = singletonFactory.getObject();` → `#L404` `addSingleton(beanName, singletonObject);`. R1: `컨테이너에 등록된 빈 ctx.getBean("memberService")` / `  = MemberService$$SpringCGLIB$$0@57806346`, 주입된 필드도 `@57806346`, `ctx.getBean("memberService") 와 같은 객체? true`(== 비교) |
| 초기화 때 this는 생성자가 만든 MemberService, 등록된 빈은 다른 클래스의 다른 객체(0:36) | R1 `[생성자] … MemberService@178ebac3`, `[@PostConstruct] this = MemberService@178ebac3`, `프록시 뒤의 진짜 객체 = MemberService@178ebac3`, `Creating CGLIB proxy: SingletonTargetSource for target object [com.example.px.MemberService@178ebac3]` / 등록된 빈 `MemberService$$SpringCGLIB$$0@57806346` |
| 바꿔치기를 하는 게 자동 프록시 생성기라는 BeanPostProcessor(0:47) | 프록시를 만드는 순간의 스택(R1, 아래가 먼저): `AbstractAutowireCapableBeanFactory.initializeBean(…:1818)` → `applyBeanPostProcessorsAfterInitialization(…:440)` → `AbstractAutoProxyCreator.postProcessAfterInitialization(AbstractAutoProxyCreator.java:289)` → `wrapIfNecessary(…:337)` → `createProxy(…:431)` → `buildProxy(…:493)` → `ProxyFactory.getProxy(…:110)` → `CglibAopProxy.getProxy(…:163)` → `CglibAopProxy.buildProxy(…:173)`. 이 스택은 EarlySpy가 원본을 받은 줄과 LateSpy가 `memberService = MemberService$$SpringCGLIB$$0@57806346`을 받은 줄 사이에 찍혔다. R1 `빈 이름 org.springframework.aop.config.internalAutoProxyCreator` / `클래스 : org.springframework.aop.aspectj.annotation.AnnotationAwareAspectJAutoProxyCreator` / `BeanPostProcessor인가? true`. SF `spring-aop/.../autoproxy/AbstractAutoProxyCreator.java#L56-L58` "BeanPostProcessor implementation that wraps each eligible bean with an AOP proxy, delegating to specified interceptors before invoking the bean itself." |
| (화면엔 이름 없음) 생성기 클래스는 클래스패스에 따라 다르다 | data-jpa starter는 AspectJ를 가져온다: SB `module/spring-boot-data-jpa/build.gradle#L19` `api("org.springframework:spring-aspects")`, R1 `org.aspectj.weaver.Advice 클래스가 클래스패스에 있나? true`. SB `core/spring-boot-autoconfigure/src/main/java/org/springframework/boot/autoconfigure/aop/AopAutoConfiguration.java#L38-L56` `@ConditionalOnClass(Advice.class)` … `@EnableAspectJAutoProxy(proxyTargetClass = true)` `@ConditionalOnBooleanProperty(name = "spring.aop.proxy-target-class", matchIfMissing = true)`, `#L58-L73` `@ConditionalOnMissingClass("org.aspectj.weaver.Advice")` → `AopConfigUtils.registerAutoProxyCreatorIfNecessary(registry); AopConfigUtils.forceAutoProxyCreatorToUseClassProxying(registry);`. R4(AspectJ 뺌): `Advice 클래스가 클래스패스에 있나? false`, `클래스 : org.springframework.aop.framework.autoproxy.InfrastructureAdvisorAutoProxyCreator`, `proxyTargetClass : true`. 둘 다 `AbstractAutoProxyCreator` 하위(SF `InfrastructureAdvisorAutoProxyCreator.java#L32`, `AnnotationAwareAspectJAutoProxyCreator.java#L51` → `AspectJAwareAdvisorAutoProxyCreator.java#L50` → `AbstractAdvisorAutoProxyCreator.java#L55`) |
| 클래스나 메서드에 @Transactional이 있으면 그 빈을 프록시로 감싼다(0:51) | `AbstractAutoProxyCreator.java#L333-L340` `// Create proxy if we have advice. Object[] specificInterceptors = getAdvicesAndAdvisorsForBean(bean.getClass(), beanName, null); if (specificInterceptors != DO_NOT_PROXY) { … Object proxy = createProxy(bean.getClass(), beanName, specificInterceptors, new SingletonTargetSource(bean)); … return proxy; }`. 하나라도 맞으면: SF `spring-aop/.../support/AopUtils.java#L262-L270`(클래스의 메서드를 돌며 하나라도 `methodMatcher.matches`면 true). 트랜잭션 매처 SF `spring-tx/.../interceptor/TransactionAttributeSourcePointcut.java#L52-L56` `hasTransactionAttribute(method, targetClass)`, 메서드 다음 클래스 순으로 찾음 `AbstractFallbackTransactionAttributeSource.java#L176-L184` `findTransactionAttribute(specificMethod)` → `// Second try is the transaction attribute on the target class. txAttr = findTransactionAttribute(specificMethod.getDeclaringClass());`. SFD `data-access/transaction/declarative/annotations.adoc#L206-L207` "You can apply the `@Transactional` annotation to an interface definition, a method on an interface, a class definition, or a method on a class." 실험: R1 MemberService `advisor : [BeanFactoryTransactionAttributeSourceAdvisor]`. R6 클래스에만 붙인 `ClassTxService`: `classTxService 필드 = ClassTxService$$SpringCGLIB$$0@1e37cb10 (CGLIB? true)`, `advisor : [BeanFactoryTransactionAttributeSourceAdvisor]`, `[ClassTxService.hello 본문] 트랜잭션 활성? true`. 전제: 프록시 모드(기본, SFD annotations.adoc L224 "In proxy mode (which is the default)") |
| @Transactional도 @Cacheable 같은 기능도 없는 PlainService는 그대로(0:57) | R1 `[LateSpy, …] plainService = PlainService@3741071d`, `plainService 필드 = PlainService@3741071d (프록시? false)`, `AbstractAutoProxyCreator.java#L343-L344` `this.advisedBeans.put(cacheKey, Boolean.FALSE); return bean;`. "@Cacheable 같은 기능"이 있으면 감싸진다: R6 `cacheOnlyService 필드 = CacheOnlyService$$SpringCGLIB$$0@3fb42ec7 (CGLIB? true)`, `advisor : [BeanFactoryCacheOperationSourceAdvisor]`, `[CacheOnlyService.name 본문] id=1, 트랜잭션 활성? false`, `name(1) = kim`, 두 번째 `name(1)`은 본문 줄 없이 `kim`(캐시). R6에서도 `plainService 필드 = PlainService@24a7725d (프록시? false)` |
| CGLIB이라는 라이브러리가 실행 중에 메모리에서 만들어서 jar엔 없다(1:02) | SFD `core/aop/proxying.adoc#L4-L6` "CGLIB is a common open-source class definition library (repackaged into `spring-core`)", `#L10-L11` "a CGLIB proxy is created which is a runtime-generated subclass of the target type." SF `CglibAopProxy.java#L201` `enhancer.setSuperclass(proxySuperClass);`, `#L203` `enhancer.setNamingPolicy(SpringNamingPolicy.INSTANCE);`. 바이트 → 클래스: SF `spring-core/src/main/java/org/springframework/cglib/core/AbstractClassGenerator.java#L370` `byte[] b = strategy.generate(this);`, `#L375` `gen = ReflectUtils.defineClass(className, b, classLoader, protectionDomain, contextClass);`, `ReflectUtils.java#L462-L463` `MethodHandles.Lookup lookup = MethodHandles.privateLookupIn(contextClass, MethodHandles.lookup()); c = lookup.defineClass(b);`. 파일은 디버그 옵션일 때만: `DebuggingClassWriter.java#L34` `DEBUG_LOCATION_PROPERTY = "cglib.debugLocation"`, `#L81` `if (debugLocation != null) {`(이때만 `.class`를 씀). R1은 이 옵션을 줘서 `CGLIB debugging enabled, writing to '/dump'`가 찍혔고 그때만 파일이 생겼다. 이 빈이 CGLIB인 근거 R1 `proxyTargetClass : true`, `AopUtils.isCglibProxy / isJdkDynamicProxy : true / false`, `부모 클래스 : com.example.px.MemberService`. 이름 규칙 SF `spring-core/.../cglib/core/SpringNamingPolicy.java#L35` `SPRING_LABEL = "$$SpringCGLIB$$"` |
| 프록시 객체는 기본으로 Objenesis로 생성자를 부르지 않고 만든다(1:08) | SF `spring-aop/.../framework/ObjenesisCglibAopProxy.java#L30-L32` "Objenesis-based extension of CglibAopProxy to create proxy instances without invoking the constructor of the class. Used by default.", `#L65-L67` `if (objenesis.isWorthTrying()) { try { proxyInstance = objenesis.newInstance(proxyClass, enhancer.getUseCache());`. 기본으로 이것을 고름: SF `DefaultAopProxyFactory.java#L61`, `#L71` `return new ObjenesisCglibAopProxy(config);`. R1 `SpringObjenesis.isWorthTrying() : true`. 덤프한 클래스의 생성자는 `public com.example.px.MemberService$$SpringCGLIB$$0(com.example.px.MemberRepository);` 하나뿐이고 안에서 `invokespecial … MemberService."<init>"`을 부르는데, 생성자 실행 횟수는 1이다. 끄면(R3, `spring.objenesis.ignore`, SF `SpringObjenesis.java#L44`) `Unable to instantiate proxy using Objenesis, and regular proxy instantiation via default constructor fails as well` / `NoSuchMethodException: com.example.px.MemberService$$SpringCGLIB$$0.<init>()` |
| 생성자는 진짜 객체를 만들 때 한 번만 돈다(1:14) | SFD `proxying.adoc#L22-L23` "The constructor of your proxied object will not be called twice, since the CGLIB proxy instance is created through Objenesis." R1 `MemberService 생성자 실행 횟수 = 1`, `[생성자]` 줄 하나 |
| 프록시의 memberRepository는 null, 콜백 필드에 인터셉터(1:18) | R1(리플렉션으로 읽음) `프록시 MemberService$$SpringCGLIB$$0@57806346` / `memberRepository = null` / `createdBy = null`, `진짜 객체 MemberService@178ebac3` / `memberRepository = jdk.proxy2.$Proxy102` / `createdBy = 생성자`. 필드 `private org.springframework.cglib.proxy.MethodInterceptor CGLIB$CALLBACK_0`, 값 `CGLIB$CALLBACK_0 = org.springframework.aop.framework.CglibAopProxy$DynamicAdvisedInterceptor`. 넣는 코드 `ObjenesisCglibAopProxy.java#L91` `((Factory) proxyInstance).setCallbacks(callbacks);`, `CglibAopProxy.java#L325` `Callback aopInterceptor = new DynamicAdvisedInterceptor(this.advised);`, `#L347` `aopInterceptor,  // for normal advice`(0번) |
| 덮어쓴 join은 콜백의 intercept로 호출을 넘긴다(1:24) | 덤프 javap: `public final void join(java.lang.String);` `1: getfield #52 // Field CGLIB$CALLBACK_0` … `18: ifnull 42` … `36: invokeinterface #68, 5 // InterfaceMethod org/springframework/cglib/proxy/MethodInterceptor.intercept:(Ljava/lang/Object;Ljava/lang/reflect/Method;[Ljava/lang/Object;Lorg/springframework/cglib/proxy/MethodProxy;)Ljava/lang/Object;` `41: return`. (`42:` 이후 null 분기의 `invokespecial MemberService.join`은 화면에서 뺐다 — 아래 "예시·소스·그림") |
| 콜백이 TransactionInterceptor를 거쳐 진짜 객체의 join을 부른다(1:30) | R1 join 본문의 스택(위가 먼저, 13프레임): `Runner.calls` → `MemberService$$SpringCGLIB$$0.join(<generated>)` → `CglibAopProxy$DynamicAdvisedInterceptor.intercept(CglibAopProxy.java:714)` → `ReflectiveMethodInvocation.proceed(…:179)` → `TransactionInterceptor.invoke(TransactionInterceptor.java:130)` → `TransactionAspectSupport.invokeWithinTransaction(…:371)` → `TransactionInterceptor$1.proceedWithInvocation(…:133)` → `ReflectiveMethodInvocation.proceed(…:158)` → `ReflectiveMethodInvocation.invokeJoinpoint(…:190)` → `AopUtils.invokeJoinpointUsingReflection(AopUtils.java:359)` → `Method.invoke` → `DirectMethodHandleAccessor.invoke` → `MemberService.join(MemberService.java:32)`, 본문 `this = MemberService@178ebac3`(= 진짜 객체), `트랜잭션 활성? true`. SF `CglibAopProxy.java#L698` `target = targetSource.getTarget();`, `#L714` `retVal = new ReflectiveMethodInvocation(proxy, target, method, args, targetClass, chain).proceed();`, `ReflectiveMethodInvocation.java#L189-L190` `return AopUtils.invokeJoinpointUsingReflection(this.target, this.method, this.arguments);` |
| 완성된 진짜 빈을 감싸서 만든 거라 필드가 채워진 객체에 일을 맡긴다(1:35) | 생성 위치는 `postProcessAfterInitialization`(위 스택), `AbstractAutoProxyCreator.java#L338` `createProxy(…, new SingletonTargetSource(bean))`, R1 `Creating CGLIB proxy: SingletonTargetSource for target object [com.example.px.MemberService@178ebac3]`. 진짜 객체의 필드는 채워져 있고(`memberRepository = jdk.proxy2.$Proxy102`) 프록시의 필드는 null. Spring 문구 `CglibAopProxy.java#L301-L303` "Calls to this method will NOT be routed to the target instance and might lead to NPEs against uninitialized fields in the proxy instance."(final이 아니면 target instance로 보낸다는 뜻) |
| 프록시가 가로챌 수 있는 건 하위 클래스가 덮어쓴 메서드뿐(1:41) | SFD `proxying.adoc#L18-L21` "`final` methods cannot be advised, because they cannot be overridden." / "`private` methods cannot be advised, because they cannot be overridden." / "Methods that are not visible – for example, package-private methods in a parent class from a different package – cannot be advised because they are effectively private." |
| 덮어쓴 메서드를 찍어 보면 final과 private만 빠져 있다(1:46) | R1 `MemberService의 메서드 중 프록시 클래스가 덮어쓴 것 :` `public callPrivate 덮어씀? true` / `public final finalJoin 덮어씀? false` / `init 덮어씀? true` / `public join 덮어씀? true` / `packageJoin 덮어씀? true` / `private privateJoin 덮어씀? false` / `protected protectedJoin 덮어씀? true`(MemberService가 선언한 7개). 덤프 javap에 `finalJoin`·`privateJoin` 문자열 0회 |
| final 메서드는 부모 코드가 프록시 객체 위에서 그대로 돈다(1:52) | JLS §8.4.3.3 "A method can be declared final to prevent subclasses from overriding or hiding it. It is a compile-time error to attempt to override or hide a final method." R1 `memberService.finalJoin("lee")` → `[finalJoin 본문]` `this = MemberService$$SpringCGLIB$$0@57806346`, 스택 `2프레임`: `com.example.px.Runner.calls(Runner.java:184)` → `com.example.px.MemberService.finalJoin(MemberService.java:51)`(프록시·인터셉터 프레임 없음) |
| 인터셉터를 안 거치니 트랜잭션 없음, 여기선 memberRepository를 써서 NPE(1:59) | R1 `트랜잭션 활성? false`, `memberRepository 필드 = null`, `[앱] 호출한 쪽으로 예외가 나옴: java.lang.NullPointerException: Cannot invoke "com.example.px.MemberRepository.save(Object)" because "this.memberRepository" is null`. "여기선"(필드를 쓸 때만)의 근거 R6 `@Transactional public final finalTxNoField()`(필드 안 씀): `[finalTxNoField 본문] this = FinalCaseService$$SpringCGLIB$$0@73c1dda3, 트랜잭션 활성? false`, `[앱] finalTxNoField() 예외 없음`. Spring 문구 `CglibAopProxy.java#L300-L304` "…might lead to NPEs against uninitialized fields in the proxy instance." |
| 시작할 때 경고 로그 한 줄만 남기고 앱은 그대로 뜬다(2:06) | R5(CglibAopProxy = Boot 기본 INFO): 시작 로그의 CglibAopProxy 줄은 `WARN  o.s.aop.framework.CglibAopProxy : Public final method [public final void com.example.px.MemberService.finalJoin(java.lang.String)] cannot get proxied via CGLIB, consider removing the final marker or using interface-based JDK proxies.` 하나, 이어서 `INFO  com.example.px.PxApplication : Started PxApplication in …`. SF `CglibAopProxy.java#L292-L299` WARN은 `Modifier.isPublic(mod)`일 때, 클래스마다 한 번 검사(`#L268-L276` `validatedClasses`) |
| 하위 클래스 프록시가 되는 빈에선 메서드에 final을 붙이지 않는다(2:11) | WARN 문구 "consider removing the final marker or using interface-based JDK proxies."(R5). `CglibAopProxy.java#L283-L304` `doValidateClass`는 애노테이션과 상관없이 static이 아닌 모든 public final 메서드에 WARN을 낸다. R6 애노테이션 없는 `public final String repoName()`: `WARN … Public final method [public final java.lang.String com.example.px.FinalCaseService.repoName()] cannot get proxied via CGLIB, …`, 호출 → `NullPointerException: Cannot invoke "com.example.px.MemberRepository.getClass()" because "this.memberRepository" is null` |
| private도 덮어쓸 수 없어 가로채지 못하고 경고조차 없다(2:17) | SFD `proxying.adoc#L19`. JLS §8.4.3.3 "A private method and all methods declared immediately within a final class (§8.1.1.2) behave as if they are final, since it is impossible to override them." SF `CglibAopProxy.java#L288` `if (!Modifier.isStatic(mod) && !Modifier.isPrivate(mod)) {`(private은 검사·로그 대상에서 빠짐). R1 `private privateJoin 덮어씀? false`, `callPrivate("park")` → `[privateJoin 본문] this = MemberService@178ebac3, 트랜잭션 활성? false`. R1(TRACE)·R5(INFO) 어디에도 privateJoin을 말하는 로그 줄이 없다 |
| protected와 같은 패키지의 package-private은 덮어쓸 수 있다(2:23) | JLS §8.4.8.1 "mA is public. mA is protected. mA is declared with package access in the same package as C …". CGLIB 쪽 SF `spring-core/.../cglib/core/VisibilityPredicate.java#L49-L52` `// protected/package private if the member is in the same package as the source class // and we are generating into the same classloader. return samePackageOk && pkg.equals(TypeUtils.getPackageName(Type.getType(member.getDeclaringClass())));`. R1(같은 패키지 `com.example.px`, 같은 클래스로더 `LaunchedClassLoader`): `protectedJoin`·`packageJoin` 덮어씀? true, javap `protected final void protectedJoin`, `final void packageJoin`. 다른 패키지는 안 됨: R6 `ChildService extends com.example.px.base.BaseService` → `프록시 클래스 패키지 = com.example.px, basePkg 선언 패키지 = com.example.px.base`, `package-private basePkg 덮어씀? false`, `protected baseProt 덮어씀? true`, `[BaseService.basePkg 본문] this 클래스 = ChildService$$SpringCGLIB$$0, 트랜잭션 활성? false`, `[BaseService.baseProt 본문] this 클래스 = ChildService, 트랜잭션 활성? true`. basePkg에 대한 로그 줄 없음 |
| Spring 6.0부터 클래스 기반 프록시에서 이 메서드에도 트랜잭션(2:28) | SFD `annotations.adoc#L179-L183` "As of 6.0, `protected` or package-visible methods can also be made transactional for class-based proxies by default. Note that transactional methods in interface-based proxies must always be `public` and defined in the proxied interface." SF `spring-tx/.../annotation/AbstractTransactionManagementConfiguration.java#L85-L86` `// Accept protected @Transactional methods on CGLIB proxies, as of 6.0` `AnnotationTransactionAttributeSource tas = new AnnotationTransactionAttributeSource(false);`. R1 `[protectedJoin 본문] … 트랜잭션 활성? true`, `[packageJoin 본문] … 트랜잭션 활성? true` |
| 정리: 초기화 뒤 BeanPostProcessor가 CGLIB으로 만든 하위 클래스, 덮어쓴 메서드로만 가로챔(2:34) | 위 줄들. "CGLIB으로": AbstractAutoProxyCreator → `ProxyFactory.getProxy` → `CglibAopProxy.buildProxy`(스택) → `DefaultAopProxyFactory#L71` ObjenesisCglibAopProxy → Enhancer. "초기화 뒤": Boot 기본 `allowCircularReferences` false(SB `core/spring-boot/src/main/java/org/springframework/boot/ApplicationProperties.java#L33-L37` `private boolean allowCircularReferences;`, `SpringApplication.java#L376` `setAllowCircularReferences(…)`) → `AbstractAutowireCapableBeanFactory.java#L587-L588` `earlySingletonExposure = (mbd.isSingleton() && this.allowCircularReferences && …)` |

수치는 "생성자 1번", "스택 13프레임/2프레임", "BeanPostProcessor 13개 중 4·7·9번"뿐이고 모두 실행 출력에서 직접 셌다.

### 화면에 실제 실행 출력을 쓴 곳 (자르거나 줄바꿈만 함)

시각·로거 이름·패키지 이름은 잘랐고(`…`), 긴 줄은 나눴다. 줄 순서를 바꾸거나 글자를 고치지 않았다. `#` 주석 줄은 내가 단 설명이다.

- run.log(0:00): `memberService 필드`(앞의 `Runner에 주입된 ` 자름) / `  = MemberService$$SpringCGLIB$$0…`(`@57806346` 자름), `$ jar tf px.jar | grep MemberService` / `…/MemberService.class`(`BOOT-INF/classes/com/example/px` 자름)
- startup.log(0:36): `[생성자] … MemberService@178ebac3`(가운데 `MemberService 객체 생성 ` 자름), `[@PostConstruct] this` / `  = MemberService@178ebac3`, `컨테이너에 등록된 빈 …`(`ctx.getBean("memberService")` 자름) / `  = MemberService$$SpringCGLIB$$0` / `    @57806346`
- overrides.log(1:41): R1의 `덮어씀?` 표에서 callPrivate·init 두 줄을 빼고 앞 공백·정렬 공백만 줄였다. 순서(이름순) 그대로.
- run.log(2:06): R5의 WARN 줄을 `WARN … : Public final method` / ` [… finalJoin(…)] cannot get proxied …`로 자르고 나눔(뒤의 ` via CGLIB, consider removing …`를 ` …`로 표시). R1의 `[finalJoin 본문]` / `  this = …$$SpringCGLIB$$0@57806346`(`MemberService` 자름) / `  트랜잭션 활성? false` / `  memberRepository 필드 = null`.

### 예시·소스·그림으로 쓴 것 (실행 출력이 아님)

- proxy-join.java(1:24): 덤프한 `MemberService$$SpringCGLIB$$0.class`의 `javap -c` join 바이트코드를 Java 모양으로 줄인 것. 화면 첫 줄 `// 프록시의 join, javap 결과를 줄임`, 마지막 줄 `// cb가 null일 때의 분기는 뺌`. 남긴 흐름: `CGLIB$CALLBACK_0`을 읽고 `intercept(this, …)`. 뺀 것: 콜백이 null이면 `CGLIB$BIND_CALLBACKS`로 채워 보고, 그래도 null이면 `super.join`(`invokespecial MemberService.join`)을 부르는 분기, 예외 표(RuntimeException·Error는 그대로 던지고 그 밖의 Throwable은 `UndeclaredThrowableException`으로 감쌈). 이 분기는 Spring 프록시에선 타지 않는다. Spring이 인스턴스를 돌려주기 전에 콜백을 채우기 때문이다(`ObjenesisCglibAopProxy.java#L91`). `public final`은 생성된 메서드의 실제 수정자다. CGLIB이 덮어쓴 메서드를 final로 만든다(SF `spring-core/.../cglib/proxy/Enhancer.java#L668` `int modifiers = Constants.ACC_FINAL | …`). 매개변수 이름 `n`은 내가 붙였다.
- bean-lifecycle.txt(0:14, 그림): 생성자(객체 생성) → @PostConstruct(초기화) → BeanPostProcessor들(초기화 후 단계) →[돌려준 객체] 컨테이너(빈으로 등록) → 내 필드(주입). "초기화 후 단계"로 범위를 좁혔다. @PostConstruct 자체도 초기화 전 BPP 훅(CommonAnnotationBeanPostProcessor)이 부르기 때문이다. 화살표 라벨 "돌려준 객체"는 출발점(BeanPostProcessor)이 하는 일(`postProcessAfterInitialization`의 반환값)이다.
- auto-proxy.txt(0:47, 그림): MemberService(@Transactional 있음), PlainService(부가 기능 없음) → 자동 프록시 생성기(BeanPostProcessor) → 프록시(`…$$SpringCGLIB$$0`), PlainService(그대로). 상자 이름 "자동 프록시 생성기"는 auto-proxy creator의 번역이고, 실제 클래스 이름은 위 표에 있다.
- proxy-object.txt(1:08, 그림): Objenesis(생성자 없이 생성) → 틀 "프록시 객체": null(memberRepository), 인터셉터(CGLIB$CALLBACK_0) / 틀 "진짜 객체": $Proxy102(memberRepository, R1의 `jdk.proxy2.$Proxy102`에서 패키지 자름), 1번(생성자 실행). 화살표는 Objenesis → 프록시 객체 하나뿐이다. 진짜 객체는 Spring이 생성자로 만든다.
- final-call.txt(1:52, 그림): `finalJoin("lee") 호출` → 프록시 객체(덮어쓴 finalJoin 없음) →[가로채지 않음] MemberService의 코드(this = 프록시 객체, 트랜잭션 없음) → NullPointerException(필드를 쓰면). 화살표 라벨은 출발점인 프록시 객체가 이 호출에 대해 하는 일(아무것도 가로채지 않음)이다.
- visibility.txt(2:17, 그림): public final → 적용 안 됨(WARN 한 줄), private → 적용 안 됨(경고도 없음), protected → 트랜잭션 적용(6.0부터), package-private(같은 패키지면 덮어씀) → 트랜잭션 적용(6.0부터). "public final"로 좁힌 이유: WARN은 public일 때만 나온다(`CglibAopProxy.java#L292`).
- summary.md(2:34, 그림): 초기화 끝난 빈(MemberService) → BeanPostProcessor(자동 프록시 생성기) → 틀 "하위 클래스 프록시": 덮어쓴 메서드(가로챔), final·private(못 가로챔). "트랜잭션 적용"이라 쓰지 않은 이유: 덮어썼어도 `@Transactional`이 없으면(callPrivate) 트랜잭션은 없다.

### 그 밖의 결정

- 이야기 구조: 훅(jar에도 없는 클래스) → 빈 생명주기 → 실제 로그 → 생성기·대상·CGLIB → 인스턴스(Objenesis, 빈 필드) → 덮어쓴 join → 덮어쓴 메서드 표 → final(그림·로그·대처) → private·protected·package-private → 정리. 다이어그램 6장면, 박스 5장면이다. 박스는 실제 출력이나 바이트코드가 증거인 곳에만 썼고, 모두 6줄 이하다.
- `pronounce`: @Transactional 트랜잭셔널, @PostConstruct 포스트컨스트럭트, @Cacheable 캐셔블, TransactionInterceptor 트랜잭션인터셉터, NullPointerException 널포인터익셉션, BeanPostProcessor 빈포스트프로세서, memberRepository 멤버리포지토리, package-private 패키지프라이빗, MemberService 멤버서비스, PlainService 플레인서비스, Spring 스프링, Objenesis 오브제네시스, intercept 인터셉트, protected 프로텍티드, private 프라이빗, CGLIB 씨지립, final 파이널, join 조인, this 디스, jar 자, null 널. `say`를 쓴 문장은 없다(단어 수 불일치가 나지 않았다).
- 한글로 둔 말: 프록시, 하위 클래스, 생성자, 초기화, 빈, 컨테이너, 콜백, 인터셉터, 바이트코드, 트랜잭션, 자동 프록시 생성기.
- 길이: 첫 판 32문장 172.10 s → 이유 없는 연결 문장 "그럼 final 메서드를, 프록시에 대고 부르면 어떻게 될까요?"를 다음 문장에 합치고, "그래서 jar 파일엔 없었던 거죠."를 앞 문장에 합쳐 30문장 167.19 s. 사실 확인을 반영한 뒤 168.82 s(답안 항목과 '왜' 문장은 빼지 않았다).
- 썸네일: 제목 `@Transactional` / `프록시 클래스` / `정체는?`, 부제 `# jar에도 없는 그 클래스`, 제목줄 `❯ cat run.log`. `thumbnail.py`가 `title font down to 118px`를 냈다. 가장 긴 줄이 나눌 수 없는 이름 `@Transactional` 하나라서 그대로 두었다(6번 영상과 같음). 이미지를 열어 보니 제목이 박스 폭을 채우고 한눈에 읽힌다.

### 독립 사실 확인 반영 기록 (2026-11-02)

렌더 전에 독립 리뷰어가 초안을 v7.0.10·v4.1.2 소스와 실험 로그로 대조하고, 같은 jar를 `px-net`에서 다시 돌렸다. R1·R5가 재현됐고, 덤프한 프록시 클래스는 바이트 단위로 같았고, 리뷰어의 javap는 이 실험의 javap와 차이 0이었다. 화면의 실행 출력 줄은 모두 원본 로그와 맞았다. 결과: 틀린 문장 0, 오해를 부르는 문장 5, 사소한 것 9. 리뷰어가 따로 돌린 사례(@Cacheable만 있는 빈, @Aspect만 있는 빈, 클래스·인터페이스 레벨 @Transactional, 다른 패키지 부모, 애노테이션 없는 final, 필드를 안 쓰는 final)는 나레이션에 새로 단정한 것만 이 영상의 실험(R6)으로 다시 확인해 위 표에 넣었다.

| # | 지적 | 바꾼 것 (전 → 후) |
|---|---|---|
| 1 | 0:51 "@Transactional 있으면 감싸고, 없으면 그대로"가 @Transactional 빈만 프록시가 된다고 읽힌다. 생성기는 어떤 advisor든 맞으면 감싸고, 클래스 레벨 @Transactional도 된다 | "빈의 메서드에 @Transactional이 하나라도 있으면, 그 빈을 프록시로 감싸서 돌려줘요." → "클래스나 메서드에 @Transactional이 있으면, 그 빈을 프록시로 감싸서 돌려줘요." / "@Transactional이 없는 PlainService는, 받은 그대로 돌려줬고요." → "@Transactional도, @Cacheable 같은 기능도 없는 PlainService는 그대로 돌려줬고요." / 그림 PlainService 부제 `@Transactional 없음` → `부가 기능 없음`. 근거 실험 R6(ClassTxService, CacheOnlyService) 추가 |
| 2 | 2:23 package-private이 조건 없이 덮어쓸 수 있다고 함. 같은 패키지(같은 클래스로더)일 때만 | "반대로 protected와 package-private은, 하위 클래스가 덮어쓸 수 있어요." → "반대로 protected와, 같은 패키지의 package-private은 덮어쓸 수 있어요." / 그림 부제 `덮어씀` → `같은 패키지면 덮어씀`. 근거 실험 R6(ChildService, BaseService) 추가 |
| 3 | 2:11 대처가 좁다. WARN·NPE는 @Transactional이 없는 public final 메서드에도 생긴다 | "그러니 하위 클래스 프록시에선, 트랜잭션이 필요한 메서드에 final을 붙이지 않아야 해요." → "그러니 하위 클래스 프록시가 되는 빈에선, 메서드에 final을 붙이지 않아야 해요." 근거 R6 repoName() |
| 4 | 1:24 코드 박스의 `if (cb == null) super.join(n);`이 실제로는 타지 않는 분기이고 "CGLIB 프록시는 super를 부른다"는 오해를 부르며 "진짜 객체에 일을 맡긴다"와 부딪힌다 | 그 줄을 빼고 `cb.intercept(this, …);`만 남김, 마지막 줄 `// cb가 null일 때의 분기는 뺌` 추가 |
| 5 | 1:59 NPE가 늘 나는 것처럼 들린다(필드를 쓸 때만) | "…비어 있는 memberRepository 때문에 NullPointerException이 나요." → "…여기선 비어 있는 memberRepository를 써서 NullPointerException이 나요." / 그림 NPE 상자 부제 `"this.memberRepository" is null` → `필드를 쓰면`. 근거 R6 finalTxNoField() |
| 사소 | 2:06 WARN 줄 뒤를 표시 없이 자름 | 줄 끝에 ` …` |
| 사소 | 2:34 "BeanPostProcessor가 실행 중에 만든" — 바이트는 CGLIB이 만든다 | "…BeanPostProcessor가 실행 중에 만든 하위 클래스예요." → "…BeanPostProcessor가 CGLIB으로 만든 하위 클래스예요." |

리뷰어가 나레이션은 두되 약점으로 적으라고 한 것은 아래 "가장 약한 부분"에 옮겼다.

반영 뒤 화면 점검(캡처)에서 고친 것:
- 0:14 bean-lifecycle.txt와 1:52 final-call.txt: 화살표 라벨이 위아래 상자에 닿았다. 두 그림의 줄 간격을 48·56 → 84 px로 늘렸다.
- 1:52 final-call.txt 화살표 라벨 "그대로 실행"은 출발점(프록시 객체)이 하는 일이 아니었다. "가로채지 않음"으로 바꿨다.
- 1:41 overrides.log: 표가 둘째 문장에서야 타이핑돼 마지막 줄이 2.2 s만 보였다. 표를 첫 문장부터 나오게 했다. 그러자 같은 장면에 `at: 0` 블록이 둘이 되어 `gsap_tween_tail` 경고가 8건 났다(박스 확대 트윈이 겹침). 블록을 하나로 합쳤고, 같은 구조인 2:06 run.log도 하나로 합쳤다.

## 측정한 것 / 보기만 한 것

- 렌더: 1080x1920, 30 fps, 168.83 s(2:49), 15.6 MB. 3분 한도까지 약 11 s 남는다.
- 오디오: 통합 -14.1 LUFS, 피크 -1.5 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 6건(아래). 다른 종류의 경고는 없다.
- `build.py`: `font down to`, `chars/s`, `diagram text down to` 경고 없음. `thumbnail.py`: 제목 118 px(위 "그 밖의 결정").
- 화면: 장면마다 가운데와 끝 직전(컷 0.15초 전)을 캡처해서 봤다(24장). 다이어그램 6장과 코드 박스 2장(proxy-join, run.log)은 끝 프레임을 원본 크기로 잘라 봤다. 렌더한 MP4에서도 두 프레임(0:36, 2:06)을 뽑아 캡처와 같은지 확인했다.
  - 0초 프레임에 첫 박스(주입된 필드의 클래스)와 첫 자막이 보인다.
  - 모든 장면 끝 프레임에서 글자가 판 안에 있다. 화살표 라벨은 상자에 닿지 않고, 배지가 화살표를 가리는 곳도 없다(배지는 쓰지 않았다).
  - 자막은 모두 2줄 안이다. 기술 용어는 영어로 나온다(한글 음차 없음).
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - **@Transactional(0:51, 0:57)**: "트랜잭셔널"
  - **@Cacheable(0:57)**: "캐셔블"로 읽게 했다
  - **BeanPostProcessor(0:20, 0:25, 0:47, 2:34)**: "빈포스트프로세서"를 한 단어로 붙여 읽게 했다
  - **@PostConstruct(0:14)**: "포스트컨스트럭트"
  - **CGLIB이라는(1:02), CGLIB으로(2:34)**: "씨지립"
  - **Objenesis라는(1:08)**: "오브제네시스"
  - **memberRepository는(1:18, 1:59)**, **NullPointerException이(1:59)**
  - **package-private은(2:23)**: "패키지프라이빗은", **protected와(2:23)**, **Spring 6.0부터는(2:28)**: 숫자를 "육 점 영"으로 읽는지
  - **jar 파일(0:05), jar엔(1:02)**: "자"
  - **intercept로(1:24)**, **TransactionInterceptor를(1:30)**

## 일부러 남긴 경고

`line_unread` 6건. 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: `= MemberService$$SpringCGLIB$$0`을 29단어로 셈). 실제로는 한두 단어짜리 코드·로그 줄이다.

- shot-03(startup.log) `= MemberService$$SpringCGLIB$$0`, `@57806346`: hold 0.4 s, 나레이션이 같은 내용("다른 클래스의 다른 객체")을 말한다
- shot-07(overrides.log) `private privateJoin 덮어씀? false`, `protected protectedJoin 덮어씀? true`: hold 0.5 s
- shot-09(run.log) `this = …$$SpringCGLIB$$0@57806346`, `memberRepository 필드 = null`: hold 0.5 s, 바로 앞 그림(final-call.txt)이 같은 내용을 보여 줬다

더 줄이려면 장면마다 hold를 늘려야 한다. 이미 나레이션이나 앞 그림이 같은 내용을 말하는 줄이라 그대로 뒀다.

## 가장 약한 부분

- **"jar엔 없었던 거예요"(1:02)와 썸네일 "# jar에도 없는 그 클래스"**: 이 영상의 일반 bootJar에선 맞다(`jar tf px.jar | grep -c SpringCGLIB` → 0). Spring AOT 처리를 켜면 프록시 클래스를 빌드 때 미리 만든다(SFD `core/aot.adoc#L29-L33` "it becomes possible to perform ahead-of-time processing at build time and generate additional assets. A Spring AOT processed application typically generates: … Bytecode (usually for dynamic proxies)", SF `AbstractClassGenerator.java#L364-L367` "Make sure to enable Spring AOT processing to pre-generate '…' at build time."). `cglib.debugLocation`은 실행 중 덤프 폴더에만 쓴다.
- **"초기화가 끝난 뒤"(0:20, 2:34)**: Boot 기본값 `allowCircularReferences=false`에서 맞다(이른 참조 경로가 꺼짐, 위 표 마지막 줄). 순환 참조를 허용하고 그 빈이 순환에 끼면 `getEarlyBeanReference`(SF `AbstractAutoProxyCreator.java#L237-L240`)로 초기화 전에 프록시가 나갈 수 있다. 실험하지 않았다.
- **@PostConstruct도 BeanPostProcessor가 부른다**: `@PostConstruct`는 초기화 전 BPP 훅(CommonAnnotationBeanPostProcessor)에서 불린다. 그림의 "초기화 후 단계"가 프록시를 만드는 단계를 가리킨다. "@PostConstruct가 끝난 뒤 BeanPostProcessor에 처음 넘긴다"는 뜻이 아니다.
- **"WARN 한 줄"은 public final만**: protected·package-private final 메서드도 덮어쓸 수 없어 가로채지 못하는데, 경고는 없다(DEBUG만, `CglibAopProxy.java#L292-L304`). 그림은 "public final"로 한정했다. final 메서드가 여러 개면 메서드마다 한 줄이다.
- **"Spring 6.0부터"(2:28)는 설정 기본값의 변화**: 덮어쓸 수 있느냐가 바뀐 게 아니라, 트랜잭션 속성을 public이 아닌 메서드에서도 읽도록 기본값이 바뀌었다(`AnnotationTransactionAttributeSource(false)`). XML `<tx:annotation-driven/>`은 여전히 public만이다.
- **생성된 `join`도 final이다**: CGLIB이 덮어쓴 메서드를 final로 만든다(`Enhancer.java#L668` `ACC_FINAL`). 프록시를 다시 상속할 일은 없지만 화면 코드의 `public final`이 이 뜻이다.
- **final·private 이야기는 모두 프록시 모드(기본)에서만**: AspectJ 모드는 바이트코드를 직접 엮어서 어떤 메서드에도 적용된다(SFD annotations.adoc L231-234).
- **"같은 객체"를 identityHashCode로 말한 곳(0:36)**: 생성자·@PostConstruct·프록시 뒤의 진짜 객체가 같다는 건 해시 일치와 소스(`SingletonTargetSource(bean)`)로 말한다. `==`로 확인한 건 "주입된 필드 = 등록된 빈"뿐이다.
- **"Objenesis로 생성자를 부르지 않고"(1:08)**: JVM이 생성자 우회를 허용할 때다(SFD proxying.adoc L23-25 "if your JVM does not allow for constructor bypassing, you might see double invocations"). "기본으로"만 붙였다.
- 실험 앱 소스·원본 로그·소스 사본·덤프(`z_임시/프록시_실험/`)는 이 REVIEW를 쓴 뒤 지웠다. 위 표와 "실험 환경과 재현"에 핵심 코드와 로그 줄을 옮겨 적었다.
