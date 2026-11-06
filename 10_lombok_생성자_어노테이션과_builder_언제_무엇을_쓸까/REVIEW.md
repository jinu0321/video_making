# REVIEW

## 시청 후 답할 수 있는 것

질문: **Lombok의 @NoArgsConstructor, @RequiredArgsConstructor, @AllArgsConstructor, @Builder는 각각 무엇을 만들고, 언제 무엇을 쓰나요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **@RequiredArgsConstructor는 초기값 없는 final 필드를 인자로 받는 생성자를 만든다. Spring은 생성자가 하나뿐이면 @Autowired 없이 그 생성자로 주입한다.**
   왜: Lombok이 컴파일할 때 그 생성자를 클래스에 넣는다(delombok·javap로 확인). Spring 문서: "If a class only declares a single constructor to begin with, it will always be used, even if not annotated." (0:00 훅, 0:08 delombok, 0:18 inject.txt 그림)
2. **생성자 주입을 쓰는 이유: final이라 한 번 들어간 의존성이 바뀌지 않고, 생성자에서 다 받아야 객체가 생겨서 Spring이 만든 객체는 다 채워진 채로 나오고, Spring 없이 new로 만들어 테스트할 수 있다.**
   왜: Spring 팀이 생성자 주입을 권하는 근거가 "immutable objects", "required dependencies are not null", "fully initialized state"다. 실험에서 `new MemberService(new MemberRepository())`가 Spring 없이 돌았다. (0:23 why.txt 그림)
   - 함정: final을 빠뜨리면 그 필드는 생성자에서 빠진다. 앱은 정상으로 뜨고, 호출하는 순간 NPE가 난다. Lombok이 인자 없는 생성자를 만들고 Spring이 그걸로 객체를 만들기 때문이다. (0:41)
3. **JPA 엔티티엔 @NoArgsConstructor(access = PROTECTED)를 단다.**
   왜: Hibernate 같은 JPA 구현체가 DB에서 읽은 행을 객체로 만들 때 인자 없는 생성자를 부른다. 생성자를 하나라도 쓰면 Java는 기본 생성자를 만들어 주지 않는다. 그러면 저장은 되는데 DB에서 읽는 순간 `No default constructor for entity` 에러가 난다. JPA 명세가 public 또는 protected를 요구하고, protected면 다른 패키지 코드가 값 없는 Member를 new로 만드는 걸 컴파일 단계에서 막는다. (0:56–1:29)
4. **@AllArgsConstructor는 모든 필드를 선언 순서대로 받는다. 같은 타입 필드의 순서만 바꿔도 에러 없이 값이 뒤바뀐다.**
   왜: 컴파일러는 인자와 매개변수의 타입만 맞춰 보고 이름은 보지 않는다. String 두 개는 순서가 바뀌어도 맞는다. (1:30–1:44)
5. **@Builder는 값마다 이름을 붙여 넣어서 필드 순서와 상관없고, 인자가 많아도 무엇이 어디로 가는지 읽힌다.** (1:45)
6. **@Builder의 대표적인 함정 둘.**
   - (가) 필드 초기값이 무시된다. 빌더는 넣지 않은 값을 null(기본 타입은 0·false)로 넘기고, 생성자가 그 값으로 초기값을 덮어쓴다. 대처는 `@Builder.Default`다. (1:55–2:12)
   - (나) 꼭 필요한 값을 빠뜨려도 컴파일되고 null이나 0이 된다. 생성자라면 인자 수가 안 맞아 컴파일 에러다. 그래서 꼭 필요한 값만 있으면 생성자로 받고, 선택 값이 많은 객체에 빌더를 쓰는 게 좋다. (2:13–2:30)
7. **정리.** (2:31 summary.md 그림)

기억할 한 문장(면접용): "주입받는 클래스엔 final 필드와 @RequiredArgsConstructor, JPA 엔티티엔 protected @NoArgsConstructor를 씁니다. 값이 많은 객체엔 @Builder를 쓰고 초기값엔 @Builder.Default를 붙이며, @AllArgsConstructor는 필드 순서를 조심합니다."

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
npx --yes hyperframes@0.8.209 render -o "output/lombok_생성자_어노테이션과_builder_언제_무엇을_쓸까.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/lombok_생성자_어노테이션과_builder_언제_무엇을_쓸까.mp4"
ffmpeg -nostats -i "output/lombok_생성자_어노테이션과_builder_언제_무엇을_쓸까.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- "언제 A를 쓰고 언제 B를 쓰나" 형 질문 하나로 잡았다. 세 생성자 어노테이션과 @Builder가 각각 무엇을 만드는지 보이고, 쓰는 자리(주입받는 클래스, JPA 엔티티, 값이 많은 객체)와 함정을 이유와 함께 붙였다.
- Lombok의 동작 원리(javac 트리 수정, 만든 사람, 런타임 비용)와 @Data·equals/hashCode·toString·record는 다루지 않았다. 원리는 "Lombok이 컴파일할 때 만들어 준다" 한 문장만 쓴다.
- 시작 화면은 Spring 개발자에게 익숙한 `@Service @RequiredArgsConstructor` 코드다. 훅은 "@Autowired도 생성자도 없는데 memberRepository가 채워져 있다"이고, 실제 실행 출력으로 보였다.
- 화면에는 프레임워크 내부 로그나 스택 대신 "이 코드를 쓰면 이런 결과"(생성된 생성자, 출력 한 줄, 컴파일 에러 한 줄)를 보였다. 흐름·이유·고르기·정리는 다이어그램이다(inject, why, build, choose, summary).

### 버전

| 항목 | 값 | 근거 |
|---|---|---|
| Spring Boot | 4.1.2 | 실험 pom parent. 실행 출력 `[spring] 7.0.10, boot 4.1.2` |
| Spring Framework | 7.0.10 | spring-boot-dependencies-4.1.2.pom 196행 `<spring-framework.version>7.0.10</spring-framework.version>` |
| Lombok | 1.18.48 | 같은 BOM 130행 `<lombok.version>1.18.48</lombok.version>`. `mvn dependency:list` 결과 `org.projectlombok:lombok:jar:1.18.48:provided`. `java -jar lombok.jar version` → `v1.18.48 "Envious Ferret"`. Maven Central sha1 `6858f13541bab505384f07053c5a7b539bbfd3e3` 일치 |
| Hibernate | 7.4.13.Final | BOM 71행, 실행 출력 `hibernate 7.4.13.Final` |
| Jakarta Persistence | 3.2.0 | BOM 92행 |
| MySQL Connector/J | 9.7.0 | BOM 155행 |
| JDK | 25.0.4.1 (Temurin) | `maven:3.9-eclipse-temurin-25`, `eclipse-temurin:25-jre`. `openjdk version "25.0.4.1" 2026-08-18 LTS` |
| MySQL | 8.4.13 | `mysql:8.4`. Hibernate 출력 `Database version: 8.4.13` |

projectlombok.org 문서가 1.18.48 기준인지: 변경 기록 맨 위가 `v1.18.48 (September 1st, 2026)`이다. 아래 Lombok 인용은 GitHub 태그 `v1.18.48`의 `website/templates/features/*.html`에서도 같은 문장으로 확인했다.

### 쓴 사실과 출처 (2026-11-03 확인)

| # | 영상의 주장 | 출처 | 원문 |
|---|---|---|---|
| S1 | @RequiredArgsConstructor는 초기값 없는 final 필드를 받는다 | Lombok 1.18.48 @XArgsConstructor 문서 https://projectlombok.org/features/constructor (태그본 https://github.com/projectlombok/lombok/blob/v1.18.48/website/templates/features/constructor.html) | "@RequiredArgsConstructor generates a constructor with 1 parameter for each field that requires special handling. All non-initialized final fields get a parameter, as well as any fields that are marked as @NonNull that aren't initialized where they are declared. … The order of the parameters match the order in which the fields appear in your class." |
| S2 | @AllArgsConstructor는 모든 필드를 받는다 | 같은 문서 | "@AllArgsConstructor generates a constructor with 1 parameter for each field in your class." |
| S3 | @NoArgsConstructor는 인자 없는 생성자, Hibernate가 필요로 함 | 같은 문서 | "@NoArgsConstructor will generate a constructor with no parameters. … Certain java constructs, such as hibernate and the Service Provider Interface require a no-args constructor." |
| S4 | 생성자가 하나면 @Autowired 없이 그 생성자로 주입 | Spring Framework 7.0.10 문서 "Using @Autowired" https://github.com/spring-projects/spring-framework/blob/v7.0.10/framework-docs/modules/ROOT/pages/core/beans/annotation-config/autowired.adoc (42–43행, 430–431행) | "An `@Autowired` annotation on such a constructor is not necessary if the target bean defines only one constructor." / "If a class only declares a single constructor to begin with, it will always be used, even if not annotated." |
| S5 | Spring 문서가 생성자 주입을 권함. final(불변), Spring이 만든 객체는 다 채워짐 | Spring Framework 7.0.10 문서 "Dependency Injection" https://github.com/spring-projects/spring-framework/blob/v7.0.10/framework-docs/modules/ROOT/pages/core/beans/dependencies/factory-collaborators.adoc (320–323행) | "The Spring team generally advocates constructor injection, as it lets you implement application components as immutable objects and ensures that required dependencies are not `null`. Furthermore, constructor-injected components are always returned to the client (calling) code in a fully initialized state." |
| S6 | 테스트에서 Spring 없이 new | 같은 문서 15–17행(DI 일반) / 테스트 문서 fixture-di.adoc 19–22행 https://github.com/spring-projects/spring-framework/blob/v7.0.10/framework-docs/modules/ROOT/pages/testing/testcontext-framework/fixture-di.adoc | "As a result, your classes become easier to test, particularly when the dependencies are on interfaces or abstract base classes, which allow for stub or mock implementations to be used in unit tests." / "Although field injection is discouraged in production code, field injection is actually quite natural in test code. The rationale for the difference is that you will never instantiate your test class directly." |
| S7 | 필수는 생성자, 선택은 다른 방법(권장) | factory-collaborators.adoc 314–316행 | "it is a good rule of thumb to use constructors for mandatory dependencies and setter methods or configuration methods for optional dependencies." |
| S8 | JPA 명세: 인자 없는 생성자는 public 또는 protected, 구현체가 부른다 | Jakarta Persistence 3.2 명세 §2.1 The Entity Class https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.html | "The entity class must have a public or protected constructor with no parameters, which is called by the persistence provider runtime to instantiate the entity. The entity class may have additional constructors for use by the application." |
| S9 | protected 생성자는 다른 패키지에서 new 불가 | JLS SE 25 §6.6.2.2 https://docs.oracle.com/javase/specs/jls/se25/html/jls-6.html#jls-6.6.2.2 | "If the access is by a simple class instance creation expression new C(...) … then the access is not permitted. A protected constructor can be accessed by a class instance creation expression (that does not declare an anonymous class) or a method reference expression only from within the package in which it is defined." |
| S10 | 생성자를 하나라도 쓰면 기본 생성자가 없다 | JLS SE 25 §8.8.9 https://docs.oracle.com/javase/specs/jls/se25/html/jls-8.html#jls-8.8.9 | "If a class contains no constructor declarations, then a default constructor is implicitly declared." |
| S11 | 컴파일러는 타입만 본다 | JLS SE 25 §15.12.2.2 https://docs.oracle.com/javase/specs/jls/se25/html/jls-15.html#jls-15.12.2.2 (생성자 선택 §15.9.3이 이 규칙을 씀) | "If m is not a generic method, then m is applicable by strict invocation if, for 1 ≤ i ≤ n, either ei is compatible in a strict invocation context with Fi (§5.3) or ei is not pertinent to applicability." |
| S12 | final은 한 번만 대입 | JLS SE 25 §4.12.4 https://docs.oracle.com/javase/specs/jls/se25/html/jls-4.html#jls-4.12.4 | "A final variable may only be assigned to once." |
| S13 | 빌더에 넣지 않은 값은 null/0, 초기값은 @Builder.Default로 | Lombok 1.18.48 @Builder 문서 https://projectlombok.org/features/Builder (태그본 …/v1.18.48/website/templates/features/Builder.html) | "If a certain field/parameter is never set during a build session, then it always gets 0 / null / false. If you've put @Builder on a class (and not a method or constructor) you can instead specify the default directly on the field, and annotate the field with @Builder.Default" |
| S14 | 초기값 무시 경고 문구 | Lombok 소스 HandleBuilder.java v1.18.48 575행 https://github.com/projectlombok/lombok/blob/v1.18.48/src/core/lombok/javac/handlers/HandleBuilder.java#L575 | `"@Builder will ignore the initializing expression entirely. If you want the initializing expression to serve as default, add @Builder.Default. If it is not supposed to be settable during building, make the field final."` (295–299행: 초기값이 있고 @Builder.Default가 없는 non-final 필드를 모아 경고) |
| S15 | 초기값은 생성자 본문보다 먼저 실행 → 생성자가 덮어씀 | JLS SE 25 §12.5 https://docs.oracle.com/javase/specs/jls/se25/html/jls-12.html#jls-12.5 | "Execute the instance initializers and instance variable initializers for this class … Execute the BlockStatements, if any, of the epilogue of this constructor." |

블로그 글은 근거로 쓰지 않았다. 중국어 출처는 쓰지 않았다.

### 실험 환경과 재현 (2026-11-03, 11-04)

모든 실험은 Docker 안에서 했고(호스트 포트 없음), 끝난 뒤 실험 폴더와 `lb10-` 자원을 지웠다. 아래에 핵심 코드와 출력을 옮겨 둔다.

#### E1. javac + Lombok 1.18.48 (JDK 25, `maven:3.9-eclipse-temurin-25`, `--network none`)

케이스마다 다음을 돌렸다. Lombok jar는 Maven Central에서 받아 sha1을 확인했다.

```bash
javac -cp lombok-1.18.48.jar -processorpath lombok-1.18.48.jar -d out *.java
javap -p -cp out Member        # 만들어진 생성자 확인
java -cp out Main
java -jar lombok-1.18.48.jar delombok <src> -d <out>   # Lombok이 넣은 코드 보기
```

(a) `@RequiredArgsConstructor` — final 필드만 생성자에 들어감

```java
@RequiredArgsConstructor
public class MemberService {
    private final MemberRepository memberRepository;
    private MailSender mailSender;
}
```
```
$ javap -p MemberService
  private final MemberRepository memberRepository;
  private MailSender mailSender;
  public MemberService(MemberRepository);
--- delombok
    @java.lang.SuppressWarnings("all")
    @lombok.Generated
    public MemberService(final MemberRepository memberRepository) {
        this.memberRepository = memberRepository;
    }
```
규칙 확인용 `Sample { final String a; final String b = "x"; @NonNull String c; String d; }` → `public Sample(java.lang.String, java.lang.String);`(a, c).

(c) `@AllArgsConstructor` 필드 순서. Main은 그대로 `Member m = new Member("kim", "kim@example.com");`

```java
@Getter @AllArgsConstructor
public class Member { private String name; private String email; }   // v1
public class Member { private String email; private String name; }   // v2: 순서만 바꿈
```
```
v1: [javac exit=0]  public Member(java.lang.String, java.lang.String);  → name=kim, email=kim@example.com
v2: [javac exit=0]  public Member(java.lang.String, java.lang.String);  → name=kim@example.com, email=kim
v1 delombok: public Member(final String name, final String email) { this.name = name; this.email = email; }
```

(d) `@Builder` 필드 순서. Main은 `Member.builder().name("kim").email("kim@example.com").build()`

```
v1(name, email) → name=kim, email=kim@example.com
v2(email, name) → name=kim, email=kim@example.com
javap: Member(java.lang.String, java.lang.String);  (package-private)  public static Member$MemberBuilder builder();
```

(e) 초기값과 `@Builder.Default`. Main은 `Member.builder().name("kim").build()` 뒤 `getTags()` 출력, `getTags().add("vip")`

```java
@Getter @Builder
public class Member {
    private String name;
    private List<String> tags = new ArrayList<>();      // v2는 위에 @Builder.Default
}
```
```
v1 컴파일:
Member.java:10: warning: @Builder will ignore the initializing expression entirely. If you want the initializing expression to serve as default, add @Builder.Default. If it is not supposed to be settable during building, make the field final.
    private List<String> tags = new ArrayList<>();
1 warning
[javac exit=0]
v1 실행:
tags=null
Exception in thread "main" java.lang.NullPointerException: Cannot invoke "java.util.List.add(Object)" because the return value of "Member.getTags()" is null
v2 실행:
tags=[]
tags=[vip]
```
delombok v1(왜 null인가): 필드 `private List<String> tags = new ArrayList<>();`는 그대로 있고, 생성자 `Member(final String name, final List<String> tags) { this.name = name; this.tags = tags; }`, 빌더 필드 `private List<String> tags;`(초기값 없음), `build() { return new Member(this.name, this.tags); }`.
delombok v2: `private static List<String> $default$tags() { return new ArrayList<>(); }`, `build()` 안 `if (!this.tags$set) tags$value = Member.$default$tags();`.

(f) 필수 값 빠뜨림

```
builder: Member.builder().name("kim").build()  → [javac exit=0]  name=kim, email=null
생성자(@AllArgsConstructor Member): new Member("kim")
Main.java:3: error: constructor Member in class Member cannot be applied to given types;
        Member m = new Member("kim");
  required: String,String
  found:    String
  reason: actual and formal argument lists differ in length
1 error
```

(g) `@Builder` + `@NoArgsConstructor` (영상엔 넣지 않음)

```
@Builder @NoArgsConstructor class Member { String name; String email; }
Member.java:4: error: constructor Member in class Member cannot be applied to given types;
@Builder
  required: no arguments
  found:    String,String
  reason: actual and formal argument lists differ in length
+ @AllArgsConstructor → [javac exit=0]  public Member();  public Member(java.lang.String, java.lang.String);
```

(h) 기본 타입 (11-04 추가): `@Builder` 클래스의 `private int count = 5;` → 같은 경고, `Member.builder().name("kim").build()` → `count=0`.

(i) `@Builder.Default` + 직접 쓴 생성자 (11-04 추가, 영상엔 넣지 않음): `public Member() {}`와 `Member(String, List<String>)`를 직접 쓰면 `builder tags=[]`, `new Member() tags=null`.

#### E2. Spring Boot 4.1.2 주입 (`spring-boot-starter`, Lombok은 `annotationProcessorPaths`에 `${lombok.version}`)

```java
@Repository
public class MemberRepository {
    public String findName(Long id) { return "kim"; }
}

@Service
@RequiredArgsConstructor
public class MemberService {
    private final MemberRepository memberRepository;     // B: final을 뺌
    public String getName(Long id) { return memberRepository.findName(id); }
}
// CommandLineRunner: MemberService 생성자 목록, memberRepository 값, getName(1L) 결과 출력
```
```
A(final):
Started DemoApplication in 0.339 seconds
[spring] 7.0.10, boot 4.1.2
[생성자] public com.example.demo.MemberService(com.example.demo.MemberRepository)
[주입] memberRepository = com.example.demo.MemberRepository@7fcff1b9
[호출] memberService.getName(1L) = kim

B(final 없음):
Started DemoApplication in 0.31 seconds
[생성자] public com.example.demo.MemberService()
[주입] memberRepository = null
[호출] java.lang.NullPointerException: Cannot invoke "com.example.demo.MemberRepository.findName(java.lang.Long)" because "this.memberRepository" is null
```
Spring 없이(같은 프로젝트, `PlainMain`): `new MemberService(new MemberRepository())` → `[Spring 없이] getName(1L) = kim`.
비교(영상엔 넣지 않음): `@Autowired private MemberRepository memberRepository;` 필드 주입 클래스를 `new MemberService()` → `"this.memberRepository" is null` NPE.

#### E3. Spring Boot 4.1.2 + Hibernate 7.4.13 + MySQL 8.4 (`spring-boot-starter-data-jpa`, `mysql-connector-j`, Docker 네트워크 `lb10-net`, `ddl-auto=create`, `show-sql=true`, `open-in-view=false`)

```java
@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)     // B: 대신 protected Member() { System.out.println("[JPA] protected Member() 호출됨"); }
public class Member {                                  // C: 인자 없는 생성자 없음
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
    private String email;
    public Member(String name, String email) { this.name = name; this.email = email; }
}
// Runner(트랜잭션 없음 → save와 findById가 각자 트랜잭션):
// Member saved = memberRepository.save(new Member("kim", "kim@example.com"));
// Member found = memberRepository.findById(saved.getId()).orElseThrow();
```
```
A: [생성자] protected com.example.demo.Member()
   [생성자] public com.example.demo.Member(java.lang.String,java.lang.String)
   Hibernate: insert into member (email,name) values (?,?)
   Hibernate: select m1_0.id,m1_0.email,m1_0.name from member m1_0 where m1_0.id=?
   [조회] name=kim, email=kim@example.com
   [조회] 저장한 객체와 같은 객체? false

B: [JPA] protected Member() 호출됨                      ← 앱 시작 중(Hibernate 부트스트랩)
   Hibernate: insert into member (email,name) values (?,?)
   Hibernate: select m1_0.id,m1_0.email,m1_0.name from member m1_0 where m1_0.id=?
   [JPA] protected Member() 호출됨                      ← DB에서 읽은 행으로 객체를 만들 때
   [조회] name=kim, email=kim@example.com

C: INFO … HHH000182: No default (no-argument) constructor for class [com.example.demo.Member] (class must be instantiated by Interceptor)
   Started DemoApplication in 1.27 seconds
   Hibernate: insert into member (email,name) values (?,?)
   [저장] id=1
   Hibernate: select m1_0.id,m1_0.email,m1_0.name from member m1_0 where m1_0.id=?
   ERROR … Application run failed
   org.springframework.orm.jpa.JpaSystemException: No default constructor for entity 'com.example.demo.Member'
   Caused by: org.hibernate.InstantiationException: No default constructor for entity 'com.example.demo.Member'
```
F (11-04 추가, C의 엔티티로, `TransactionTemplate` 한 트랜잭션 안에서 save → findById, 그다음 따로 findById):
```
Hibernate: insert into member (email,name) values (?,?)
[한 트랜잭션] name=lee, 같은 객체? true          ← select 없음, 에러 없음 (영속성 컨텍스트가 같은 객체를 돌려줌)
[따로] findById(1) 시작
Hibernate: select m1_0.id,m1_0.email,m1_0.name from member m1_0 where m1_0.id=?
org.springframework.orm.jpa.JpaSystemException: No default constructor for entity 'com.example.demo.Member'
```
그래서 영상은 "조회하는 순간"이 아니라 "DB에서 읽는 순간"이라고 말한다.

D (다른 패키지 `com.example.demo.other.MemberFactory`에서 `return new Member();`, A의 엔티티):
```
[ERROR] /work/src/main/java/com/example/demo/other/MemberFactory.java:[7,16] constructor Member in class com.example.demo.Member cannot be applied to given types;
  required: no arguments
  found:    no arguments
  reason: Member() has protected access in com.example.demo.Member
```
E (같은 패키지 `com.example.demo.SamePackageFactory`에서 `new Member()`): 컴파일 성공(exit 0). 그래서 영상은 "다른 패키지 코드"로 한정했다.

### 화면에 실제 실행 출력을 쓴 곳 (자르거나 줄바꿈만 함)

- run.log(0:04): E2-A `[주입] memberRepository = com.example.demo.MemberRepository@7fcff1b9`를 `[주입] ` 없이 세 줄로 줄바꿈. 해시 `@7fcff1b9`는 실행마다 바뀐다.
- MemberService.java(0:08): E1(a) delombok에서 `@java.lang.SuppressWarnings("all")`, `@lombok.Generated` 두 줄을 빼고 줄바꿈. `// Lombok이 만든 생성자`는 설명 주석.
- MemberService.java(0:41): E2-B NPE 메시지에서 `java.lang.`과 `Cannot invoke "…"`를 `…`로 자르고 줄바꿈. `// 만들어진 생성자: MemberService()`는 E2-B 생성자 출력의 요약.
- find.log(1:01): E3-B select 줄에서 `Hibernate: `와 컬럼 목록을 `…`로 자름. `[JPA] protected Member() 호출됨`은 그대로, `[조회] name=kim`은 뒤의 email 부분을 자름.
- find.log(1:08): E3-C insert(`Hibernate: `, `values (?,?)` 자름), select(자름), `No default constructor for entity 'com.example.demo.Member'`(예외 클래스 이름을 자르고 줄바꿈).
- MemberFactory.java(1:19): E3-D `reason: Member() has protected access in com.example.demo.Member`에서 앞뒤를 자름.
- Main.java(1:35): E1(c) v2 출력 `name=kim@example.com, email=kim` 그대로.
- Main.java(1:45): E1(d) v2 출력 그대로.
- Member.java(1:55): E1(e) 경고의 첫 문장만, 줄바꿈.
- Main.java(2:08): E1(e) `tags=null`(v1), `tags=[]`(v2) 그대로.
- Main.java(2:13): E1(f) `name=kim, email=null`, `required: String,String` 그대로(`found:    String`은 자름).

### 예시·소스·그림으로 쓴 것 (실행 출력이 아님)

- 코드 화면은 실험 소스에서 `Member m = `, import, `@Getter`, 메서드 본문을 줄인 조각이다. 엔티티 화면의 `// id, name, email + 생성자`는 생략 표시.
- 예시 이름 `MemberService`, `MemberRepository`, `kim`, `kim@example.com`, `tags`, `getName(1L)`, 패키지 `com.example.demo(.other)`는 실험용으로 지은 것이다.
- 다이어그램: inject.txt(MemberRepository → 하나뿐인 생성자, 배지 `@Autowired 없음`), why.txt(세 이유), build.txt(`builder().name("kim")` → `build()` → 생성자 `this.tags = tags (null)`, delombok 요약), choose.txt(꼭 필요한 값 → 생성자 / 선택 값이 많음 → @Builder), summary.md(네 어노테이션과 쓰는 자리).
- 썸네일: `# Lombok NoArgs · RequiredArgs · AllArgs` / `생성자와 @Builder, 언제 뭘 쓸까?`. 질문을 줄인 것이다.

### 확인했지만 넣지 않은 것

- `@Builder` + `@NoArgsConstructor`만 달면 컴파일 에러, `@AllArgsConstructor`를 더하면 성공(E1 g). Lombok 문서: "applying @Builder to a class is as if you added @AllArgsConstructor(access = AccessLevel.PACKAGE) to the class and applied the @Builder annotation to this all-args-constructor. This only works if you haven't written any explicit constructors yourself or allowed lombok to create one such as with @NoArgsConstructor." 고친 뒤 film이 170초를 넘어 넣지 못했다(아래 "가장 약한 부분").
- @RequiredArgsConstructor는 초기값 없는 `@NonNull` 필드도 받는다(E1 a 규칙 확인).
- 필드 주입 클래스를 Spring 없이 new 하면 NPE(E2 비교).
- Hibernate는 앱 시작 때도 인자 없는 생성자를 한 번 부른다(E3-B).

### 그 밖의 결정

- "빈 생성자"는 Spring의 "빈(bean)"과 헷갈려서 "인자 없는 생성자", "기본 생성자"로 썼다.
- @RequiredArgsConstructor 설명은 "초기값이 없는 final 필드를 인자로 받는"으로 썼다. "final 필드만"이라고 하지 않아 @NonNull 경우와 어긋나지 않는다.
- 읽기(`pronounce`)는 긴 어노테이션 이름을 한 단어로 붙였다: `@RequiredArgsConstructor` → "리콰이어드아그스컨스트럭터", `@NoArgsConstructor` → "노아그스컨스트럭터", `@AllArgsConstructor` → "올아그스컨스트럭터", `@Builder.Default` → "빌더디폴트". 자막의 단어 수와 맞추기 위해서다.

### 독립 사실 확인 반영 기록 (2026-11-04)

독립 확인 결과: 틀림 0, 오해 소지 1, 사소 7. 검증자는 사실표 인용과 화면 실행 출력을 원문·재실행과 대조했고 차이가 없었다.

| 지적 | 전 | 후 | 근거 |
|---|---|---|---|
| [오해 소지] 1:14 한 트랜잭션 안에선 save 직후 findById가 DB를 읽지 않아 에러가 안 남 | 그러면 저장은 되는데, 조회하는 순간 에러가 나요. | 그러면 저장은 되는데, DB에서 읽는 순간 에러가 나요. | E3-F 재실험(위) |
| 2:13 기본 타입은 0·false | …그 값은 null이 돼요. | …그 값은 null이나 0이 돼요. | S13 "always gets 0 / null / false", E1(h) `count=0` |
| 2:03 (같은 뜻 맞춤) | 빌더는 넣지 않은 값을 null로 넘기고, | 빌더는 넣지 않은 tags를 null로 넘기고, | 예시 필드(List)로 한정 |
| 1:35 타입이 다르면 컴파일 에러 | 그런데 필드 순서만 바꿔도, 기존 코드가 에러 없이 컴파일되고 값이 뒤바뀌어요. | 그런데 같은 타입 필드 순서만 바꿔도, 에러 없이 값이 뒤바뀌어요. | S11 |
| 2:38 @Builder.Default는 초기값 있는 필드에 붙이는 것 | 값이 많은 객체엔 @Builder와 @Builder.Default를 쓰고, @AllArgsConstructor는 필드 순서를 조심해요. | 값이 많은 객체엔 @Builder를 쓰고, 초기값엔 @Builder.Default를 붙여요. / @AllArgsConstructor는 필드 순서를 조심하고요. 그림 부제 `값이 많은 객체 · 초기값엔 @Builder.Default` | S13 |
| 1:01 행위 주체 | JPA는 DB에서 읽은 행을 객체로 만들 때, 이 인자 없는 생성자부터 부르거든요. | Hibernate 같은 JPA 구현체는, DB에서 읽은 행을 객체로 만들 때 이 생성자를 부르거든요. | S8 "persistence provider runtime", E3-B |
| 1:55 함정은 더 있음 | 대신 @Builder엔 함정이 둘 있어요. | 대신 @Builder엔 대표적인 함정이 둘 있어요. | E1(g), S14 경고의 final 언급 |
| 0:31 new로 null을 넘기면 덜 채워질 수 있음 | 생성자에서 다 받아야 객체가 생기니, 덜 채워진 채로 쓰일 일이 없어요. | 생성자에서 다 받아야 객체가 생기니, Spring이 만든 객체는 다 채워진 채로 나와요. 그림 부제 `Spring이 만든 객체는 다 채워짐` | S5 "always returned to the client (calling) code in a fully initialized state" |
| 2:24 권장임을 드러냄 | …선택 값이 많은 객체엔 빌더를 써요. | …선택 값이 많은 객체엔 빌더를 쓰는 게 좋아요. | S7(같은 원칙의 Spring 판) |
| (길이) 고친 뒤 film 171.1 s | 1:55 장면 둘째 문장 "Lombok도 컴파일할 때, 이렇게 경고를 줘요." | 삭제. 경고 원문은 같은 화면에 그대로 둠 | 이유를 말하지 않는 연결 문장이라 먼저 뺐다(가이드 "길이" 1번) |

바꾼 문장의 다이어그램·블록 `at` 단어는 모두 문장에 남아 있다(build.py가 못 찾으면 멈추는데 멈추지 않았다).

## 측정한 것 / 보기만 한 것

- 렌더: 1080x1920, 30 fps, 168.50 s(2:48), 18.8 MB. 3분 한도 안이다.
- 오디오: 통합 -14.1 LUFS, 피크 -1.2 dBFS.
- 나레이션: 31문장, narration 166.88 s, film 168.48 s.
- `hyperframes check`: 오류 0, 경고 `line_unread` 29건(아래). 다른 종류의 경고는 없었다.
- `build.py`: `font down to`, `diagram text down to` 경고 없음. 처음엔 `shot-09 block 1: 33 chars/s`가 나와 그 장면 hold를 0.4 → 0.7 s로 늘려 없앴다.
- `thumbnail.py`: 처음 제목 `Lombok 생성자 / @Builder, / 언제 뭘 쓸까?`가 132px로 줄어(`title font down to`) `생성자와 / @Builder, / 언제 뭘 쓸까?`로 바꾸고 "Lombok"은 부제(`# Lombok NoArgs · RequiredArgs · AllArgs`)로 옮겼다. 제목 165px.
- 화면: 장면마다 가운데와 끝 직전(컷 0.15초 전)을 캡처해서 봤다(0초 포함 39장). why.txt는 원본 크기 프레임으로 부제가 읽히는지 봤다. 렌더한 MP4에서도 0:00과 2:13 직전 프레임을 뽑아 캡처와 같은지 확인했다.
  - 0초 프레임에 첫 박스(`@Service @RequiredArgsConstructor` 코드)와 첫 자막이 보인다.
  - 코드 박스는 한 줄 36칸 안쪽으로 줄바꿈해 글자가 약 50–62px다. 처음 초안의 delombok 한 줄(44칸, 약 39px)은 줄바꿈으로 고쳤다.
  - inject.txt의 배지 `@Autowired 없음`은 상자 오른쪽 위에 있고, 위에서 들어오는 화살표(가운데)와 겹치지 않는다.
  - 자막은 모두 2줄 안이다. 기술 용어는 영어로 나온다(한글 음차 없음).
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - **@RequiredArgsConstructor가(0:08, 2:31)**: "리콰이어드아그스컨스트럭터"를 한 단어로 읽게 했다
  - **@NoArgsConstructor를(0:56, 2:31)**: "노아그스컨스트럭터", **@AllArgsConstructor는(1:30, 2:43)**: "올아그스컨스트럭터"
  - **memberRepository가(0:04, 0:23)**: "멤버리포지토리가"
  - **NullPointerException이(0:51)**: "널포인터익셉션이"
  - **Hibernate 같은 JPA 구현체는(1:01)**: "하이버네이트", "제이피에이"
  - **public이나 protected로(1:19)**, **Member를 new로(1:23)**: "멤버를 뉴로"
  - **String이라(1:40)**: "스트링이라"
  - **tags를, tags는(2:03, 2:08)**: "태그스"
  - **@Builder.Default를(2:08, 2:38)**: "빌더디폴트"
  - **null이나 0이(2:13)**: "널이나 영이"로 읽히는지

## 일부러 남긴 경고

`line_unread` 29건. 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: `@RequiredArgsConstructor`를 23단어로 셈). 실제로는 한두 단어짜리 코드·출력 줄이고, 나레이션이 같은 내용을 말한다.
경고가 나온 장면(건수): shot-01 훅 코드 0:00(3), shot-02 run.log 0:04(4), shot-06 final 빠뜨림 0:41(2), shot-07 엔티티 0:56(3), shot-08 find.log 1:01(2), shot-09 find.log 1:08(4), shot-10 MemberFactory 1:19(1), shot-11 @AllArgsConstructor 1:30(3), shot-12 순서 바꾼 결과 1:35(1), shot-13 Builder 1:45(1), shot-14 경고 화면 1:55(2), shot-16 tags 결과 2:08(2), shot-17 필수 값 2:13(1).
없애려면 장면마다 hold를 1–4초씩 늘려야 하는데, film이 이미 168.5 s라 170 s 기준을 넘는다. 그대로 뒀다.

## 가장 약한 부분

- **@Builder + @NoArgsConstructor 충돌을 영상에서 말하지 않는다.** 대본이 엔티티 Member(1:01–1:29)와 빌더 Member(1:45–2:23)에 같은 이름을 써서, 시청자가 엔티티에 `@NoArgsConstructor(access = PROTECTED)`와 클래스 `@Builder`를 같이 달고 싶어지기 쉽다. 그러면 `required: no arguments / found: String,String` 컴파일 에러가 난다. `@AllArgsConstructor`를 더하면 컴파일된다(E1 g). 문서는 직접 쓴 생성자가 있으면 그 생성자에 `@Builder`를 달라고 한다("If you do have an explicit constructor, put the @Builder annotation on the constructor instead of on the class."). 이 방법은 실험하지 않았다. 고친 뒤 film이 170초에 가까워 넣지 못했다. 다음 영상 후보 1번.
- **1:30 "모든 필드를"**: static 필드와 초기값이 있는 final 필드는 빠진다. Lombok 소스 HandleConstructor.java v1.18.48 173–187행(`//Skip static fields.`, `//Skip initialized final fields`), 문서 "Static fields are skipped by these annotations."
- **@Builder.Default를 붙이면 직접 쓴 생성자에선 초기값이 사라진다.** 실험 E1(i): `builder tags=[]` / `new Member() tags=null`. 문서: "explicit constructors will no longer use the default values and will need to be set manually or call a Lombok-generated constructor such as this(); to set the defaults." 영상은 @Builder.Default를 대처로만 말한다.
- **0:37 "테스트에선 Spring 없이도, new로"**: 이 근거는 Spring 문서의 constructor-vs-setter 단락이 아니라 DI 일반 단락(factory-collaborators.adoc 15–17행)과 테스트 문서의 대비, 그리고 E2 실험이다. 그림 제목 "생성자 주입을 권하는 이유" 아래 셋째 상자로 묶여 있어 Spring 문서가 그 이유를 직접 든 것처럼 보일 수 있다.
- **1:45 "인자가 많아도 바로 읽히고요"**, **2:24 "빌더를 쓰는 게 좋아요"**: 평가·권장 문장이다. 앞의 근거는 S7과 E1 실험이다.
- 실험의 원본 로그·소스·실험 앱(`z_임시/lb10_실험/`, 사실표.md 포함)은 작업을 마치며 지웠다. 이 REVIEW는 그 파일 없이 읽히도록 핵심 코드와 로그 줄을 옮겨 적었다.
