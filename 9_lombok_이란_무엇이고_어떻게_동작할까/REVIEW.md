# REVIEW

## 시청 후 답할 수 있는 것

질문: **Lombok이 뭐고, 쓰기 전엔 어땠나요? 소스에 없는 getter는 어떻게 생기고, 그 대가는요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **정체: Lombok은 어노테이션을 보고, 반복되는 코드를 컴파일할 때 대신 써 주는 라이브러리다.**
   왜(증거): `@Getter @Setter`만 붙은 Member 소스엔 메서드가 없다. 그런데 컴파일된 Member.class를 javap로 보면 getter와 setter 6개가 실제로 있다. (0:00 훅, 0:14 javap)
2. **쓰기 전: 필드 3개짜리 클래스가 6줄에서 29줄이 된다(delombok -f pretty, 빈 줄 포함).**
   왜 반복되나: Java는 필드를 private으로 감추고 getX/setX로 읽고 쓰는 게 관례다. public 필드는 구현에 묶여 나중에 바꾸기 어렵기 때문이다. 이 이름 규칙(JavaBeans)을 Spring도 따라서 값을 넣고 꺼낸다. (0:25, 0:30 그림)
3. **IDE 자동 생성으로는 부족하다. 만든 코드가 소스에 남아 사람이 관리해야 하기 때문이다.**
   예: equals를 만든 뒤 email을 추가하고 equals를 고치지 않으면, email만 다른 두 회원이 같다고 나온다. `@EqualsAndHashCode`는 컴파일마다 다시 만들어 email까지 비교한다. (0:46)
4. **누가·언제: Reinier Zwitserloot와 Roel Spilker가 2009년부터 만들어 온 오픈소스다.** (1:07)
5. **원리: 세 단계로 동작한다.**
   1. javac가 소스를 추상 구문 트리(AST)로 만든다.
   2. javac가 부르는 annotation processor인 Lombok이 그 트리에 메서드를 끼워 넣는다.
   3. javac가 바뀐 트리로 .class를 만든다.

   그래서 소스엔 없는 메서드가 클래스 파일엔 있다. (1:13 그림)
6. **보통 방식이 아니다. 표준 annotation processing API가 코드를 더하는 방법은 새 파일을 만드는 것이고, 이미 있는 Member를 다시 만들면 FilerException이 나기 때문이다.**
   Lombok은 이 길 대신, 공식 API가 아닌 javac 내부 클래스로 트리를 직접 고친다. (1:34 그림)
7. **실행할 땐 Lombok이 필요 없다. 메서드가 이미 .class에 들어 있고, getter의 바이트코드도 손으로 쓴 것과 같기 때문이다.**
   그래서 Gradle에선 compileOnly(컴파일 때만)로 넣는다. annotationProcessor 줄은 javac가 Lombok을 처리기로 돌리게 하는 줄이라, 빼면 getter가 안 생긴다. (1:51, 2:02)
8. **대가: JDK를 올리면 Lombok이 깨질 수 있다.**
   예: JDK 21에서 되던 Lombok 1.18.30이 JDK 25에선 컴파일에 실패한다. Lombok이 찾던 javac 내부 값 `TypeTag.UNKNOWN`이 JDK 24에서 지워졌기 때문이다. javac 내부는 예고 없이 바뀔 수 있다. 그래서 JDK를 올릴 땐 그 JDK를 지원하는 Lombok인지 확인한다(changelog상 JDK 25 지원은 1.18.40부터). (2:13)

기억할 한 문장(면접용): "Lombok은 컴파일할 때 javac의 구문 트리에 반복 메서드를 넣어 주는 도구라 실행할 땐 필요 없지만, 컴파일러 내부에 기대서 JDK를 올릴 땐 Lombok 지원 버전을 확인해야 한다." (2:34 그림)

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
npx --yes hyperframes@0.8.209 render -o "output/lombok_이란_무엇이고_어떻게_동작할까.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/lombok_이란_무엇이고_어떻게_동작할까.mp4"
ffmpeg -nostats -i "output/lombok_이란_무엇이고_어떻게_동작할까.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 사용자 요청: 면접관이 고개를 끄덕일 정도의 Lombok 이해, `@Getter @Setter` 코드로 시작, 쓰기 전, 만든 사람, 장단점.
  - 질문은 "정체 + 쓰기 전 + 원리 + 대가" 하나로 잡았다.
  - 뼈대: 훅(메서드 없는 Member가 컴파일됨) → javap로 정체 → 쓰기 전(29줄, JavaBeans 관례) → IDE 생성의 한계 → 만든 사람 → 원리 3단계 → 왜 표준 방식이 아닌가 → 실행 땐 필요 없음과 Gradle 설정 → JDK 업그레이드 대가 → 정리.
- 생성자 어노테이션, `@Builder`, `@Data`의 함정(setter·equals/hashCode·toString, JPA 엔티티, record)은 다루지 않았다(별도 영상의 범위).
  - 장면 5의 `@EqualsAndHashCode`는 "컴파일마다 다시 만든다"를 보여 주는 한 줄 예시로만 썼다.
- 다른 영상 언급("지난 영상", "시리즈" 등)은 대본·화면·썸네일에 없다.
- 다음 영상 후보(범위를 좁히느라 뺀 것):
  1. **IDE와 Lombok**: IntelliJ가 어떻게 생성된 메서드를 아는가, 플러그인. 아래 "빼거나 확인만 한 것" 참고.
  2. **Maven에서 Lombok**: provided + annotationProcessorPaths, JDK 23부터 필수인 이유(javac 기본 처리 꺼짐).
  3. **Lombok 대안 비교**: record, IDE 생성, 손 코드. 언제 무엇을 쓸까.
  4. **delombok의 쓰임**: javadoc, Lombok을 걷어 낼 때.

### 예시로 지어낸 상황

- 장면 5의 HandMember는 내가 쓴 예시 코드다(아래 실험 E3). IDE로 실제 생성한 코드는 아니고, id·name으로 equals를 만든 뒤 email을 추가한 상황을 흉내 냈다.
- Main의 `"kim"`, 이메일 `kim@a.com`·`kim@b.com`은 예시 값이다.

### 실험 환경과 재현 (2026-11-03)

모든 실험은 `docker run --rm --name lb9-…`로 돌렸다. 호스트 포트는 열지 않았고, 작업 폴더를 `/w`로 붙였다.

| 이미지 | 버전(실행 시 출력) | 쓴 곳 |
|---|---|---|
| `maven:3.9-eclipse-temurin-25` (93b8a14ea2f4) | `openjdk version "25.0.4.1" 2026-08-18 LTS`, Temurin-25.0.4.1+1, `javac 25.0.4.1` | javac·javap·delombok 실험 |
| `eclipse-temurin:25-jre` (78f1f1839134) | 25.0.4.1, 컨테이너 안에 `*lombok*` 파일 없음 | 실행 실험 |
| `eclipse-temurin:21-jdk` (ebfbb18d11ff, 이번에 pull, 끝나고 지움) | `javac 21.0.13` | 옛 Lombok 비교 |
| `gradle:9.8.2-jdk25` (이번에 pull, 끝나고 지움) | `Gradle 9.8.2`, `Launcher JVM: 25.0.5 (Eclipse Adoptium 25.0.5+8-LTS)` | Gradle 실험 |

Lombok jar는 Maven Central에서 받아 `.sha1`과 대조했다(모두 일치).
- 1.18.48 `6858f13541bab505384f07053c5a7b539bbfd3e3`
- 1.18.30 `f195ee86e6c896ea47a1d39defbe20eb59cd149d`
- 1.18.32 `17d46b3e205515e1e8efd3ee4d57ce8018914163`
- 1.18.34 `ec547ef414ab1d2c040118fb9c1c265ada63af14`
- 1.18.36 `5a30490a6e14977d97d9c73c924c1f1b5311ea95`
- 1.18.38 `57f8f5e02e92a30fd21b80cbd426a4172b5f8e29`
- 1.18.40 `398c6d2d7c42c96b65e78d2ddc9be0058c163453`

**Lombok 버전 1.18.48**은 Spring Boot 4.1.2 BOM 값이다.
- https://repo1.maven.org/maven2/org/springframework/boot/spring-boot-dependencies/4.1.2/spring-boot-dependencies-4.1.2.pom 130행: `<lombok.version>1.18.48</lombok.version>`
- 같은 BOM 196행: `<spring-framework.version>7.0.10</spring-framework.version>`

#### 실험 코드

```java
// Member.java (장면 0 박스 = 4–9행)
import lombok.Getter;
import lombok.Setter;

@Getter @Setter
public class Member {
    private Long id;
    private String name;
    private String email;
}

// Main.java
public class Main {
    public static void main(String[] args) {
        Member member = new Member();
        member.setName("kim");
        System.out.println(member.getName());
    }
}

// Props.java (JavaBeans 규칙으로 속성을 찾는지)
for (PropertyDescriptor p : Introspector.getBeanInfo(Member.class, Object.class).getPropertyDescriptors())
    System.out.println(p.getName() + " <- " + p.getReadMethod().getName() + "(), " + p.getWriteMethod().getName() + "(..)");
```

```java
// E3 HandMember.java: id, name 두 필드일 때 equals/hashCode를 만들어 두고, 나중에 email을 추가한 클래스
public class HandMember {
    private Long id;
    private String name;
    private String email;   // 나중에 추가한 필드
    public HandMember(Long id, String name, String email) { this.id = id; this.name = name; this.email = email; }
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        HandMember that = (HandMember) o;
        return Objects.equals(id, that.id) && Objects.equals(name, that.name);
    }
    @Override
    public int hashCode() { return Objects.hash(id, name); }
}
// E3 LombokMember.java: 같은 클래스를 Lombok으로. email을 추가한 뒤 다시 컴파일만 했다
@EqualsAndHashCode
public class LombokMember {
    private Long id; private String name; private String email;
    public LombokMember(Long id, String name, String email) { this.id = id; this.name = name; this.email = email; }
}
// E3 Main3.java
HandMember a = new HandMember(1L, "kim", "kim@a.com");
HandMember b = new HandMember(1L, "kim", "kim@b.com");
System.out.println("손으로 쓴 equals: " + a.equals(b));
LombokMember c = new LombokMember(1L, "kim", "kim@a.com");
LombokMember d = new LombokMember(1L, "kim", "kim@b.com");
System.out.println("@EqualsAndHashCode equals: " + c.equals(d));
```

```java
// E6 TryOverwrite.java: 표준 API(Filer)로 이미 있는 Member를 다시 만들 수 있는지 시험하는 처리기
@SupportedAnnotationTypes("*")
@SupportedSourceVersion(SourceVersion.RELEASE_25)
public class TryOverwrite extends AbstractProcessor {
    private boolean done;
    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment roundEnv) {
        if (done) return false;
        done = true;
        Filer filer = processingEnv.getFiler();
        Messager log = processingEnv.getMessager();
        try { filer.createSourceFile("Member"); log.printMessage(NOTE, "createSourceFile(\"Member\") -> 성공"); }
        catch (Exception e) { log.printMessage(NOTE, "createSourceFile(\"Member\") -> " + e); }
        try { filer.createClassFile("Member"); log.printMessage(NOTE, "createClassFile(\"Member\") -> 성공"); }
        catch (Exception e) { log.printMessage(NOTE, "createClassFile(\"Member\") -> " + e); }
        try (java.io.Writer w = filer.createSourceFile("MemberHelper").openWriter()) {
            w.write("public class MemberHelper {}\n");
            log.printMessage(NOTE, "createSourceFile(\"MemberHelper\") -> 성공 (새 파일)");
        } catch (Exception e) { log.printMessage(NOTE, "createSourceFile(\"MemberHelper\") -> " + e); }
        return false;
    }
}
// 대상 src/Member.java: public class Member { private String name; }
```

```groovy
// E8 a/build.gradle (b는 annotationProcessor 줄만 뺐다)
plugins {
    id 'java'
    id 'org.springframework.boot' version '4.1.2'
    id 'io.spring.dependency-management' version '1.1.7'
}
java { toolchain { languageVersion = JavaLanguageVersion.of(25) } }
repositories { mavenCentral() }
dependencies {
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
}
springBoot { mainClass = 'Main' }
```

E7 hand2(흔히 쓰는 모양의 손 코드):

```java
public class Member {
    private Long id; private String name; private String email;
    public Long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }
    public void setId(Long id) { this.id = id; }
    public void setName(String name) { this.name = name; }
    public void setEmail(String email) { this.email = email; }
}
```

#### 명령과 핵심 출력

`L=/w/jars/lombok-1.18.48.jar`. 출력은 로그 그대로이고, `…`는 자른 자리다.
JDK 24+는 Lombok 실행마다 다음 경고 4줄을 찍는다. 아래에선 뺐다.
- `WARNING: A terminally deprecated method in sun.misc.Unsafe has been called`
- `WARNING: sun.misc.Unsafe::objectFieldOffset has been called by lombok.permit.Permit`
- …

```
## E1 (JDK 25.0.4.1, Lombok 1.18.48)
$ javac -processorpath $L -cp $L -s gen -d out -XprintRounds src/Member.java src/Main.java src/Props.java
Round 1:
	input files: {Member, Main, Props}
	annotations: [lombok.Getter, lombok.Setter]
	last round: false
… (Round 2–4: input files: {}, annotations: [])
[exit 0]
$ find out gen -type f
out/Member.class
out/Props.class
out/Main.class                       ← gen(새 소스 파일 자리)은 비어 있음
$ javap -p -cp out Member
Compiled from "Member.java"
public class Member {
  private java.lang.Long id;
  private java.lang.String name;
  private java.lang.String email;
  public Member();
  public java.lang.Long getId();
  public java.lang.String getName();
  public java.lang.String getEmail();
  public void setId(java.lang.Long);
  public void setName(java.lang.String);
  public void setEmail(java.lang.String);
}
$ javap -v -cp out Member | grep lombok
  #25 = Utf8               Llombok/Generated;
    RuntimeInvisibleAnnotations: … lombok.Generated   (메서드 6개마다)
$ javac -cp $L -d out-cp src/Member.java src/Main.java      ← processor path 없이 class path만
src/Main.java:4: error: cannot find symbol
        member.setName("kim");
  symbol:   method setName(String)
src/Main.java:5: error: cannot find symbol
  symbol:   method getName()
2 errors
[exit 1]
$ java -jar $L delombok -p -f pretty src/Member.java   → 출력 30줄(맨 앞 빈 줄 + class 29줄)

public class Member {
    private Long id;
    private String name;
    private String email;

    public Long getId() {
        return this.id;
    }
… (getName, getEmail, setId 같은 모양, 사이에 빈 줄)
    public void setEmail(final String email) {
        this.email = email;
    }
}
$ java -jar $L delombok -p src/Member.java   → 기본 형식은 메서드마다 @java.lang.SuppressWarnings("all") @lombok.Generated가 붙어 class가 41줄
$ java -jar $L delombok --format-help | tail -1
The '-f pretty' option is shorthand for '-f suppressWarnings:skip -f generated:skip -f danceAroundIdeChecks:skip -f generateDelombokComment:skip -f javaLangAsFQN:skip'

## E1r (eclipse-temurin:25-jre, lombok jar 없음)
$ find / -xdev -iname '*lombok*' -not -path '/w/*'     → (없음)
$ ls out
Main.class
Member.class
$ java -cp out Main
kim
$ java -cp out Props            (Props.class를 같이 넣은 이전 실행)
email <- getEmail(), setEmail(..)
id <- getId(), setId(..)
name <- getName(), setName(..)

## E3 (JDK 25, Lombok 1.18.48)
$ java -Dstdout.encoding=UTF-8 -cp out Main3
손으로 쓴 equals: true
@EqualsAndHashCode equals: false
$ java -jar $L delombok -p -f pretty src/LombokMember.java   (equals 일부)
        final Object this$email = this.email;
        final Object other$email = other.email;
        if (this$email == null ? other$email != null : !this$email.equals(other$email)) return false;

## E5 (같은 Member/Main)
===== JDK 21
$ javac -version
javac 21.0.13
$ javac -processorpath …/lombok-1.18.30.jar -cp …/lombok-1.18.30.jar -d out-21.0.13-1.18.30 Member.java Main.java
[exit 0]
$ java -cp out-21.0.13-1.18.30 Main
kim
===== JDK 25
$ javac -version
javac 25.0.4.1
$ javac -processorpath …/lombok-1.18.30.jar -cp …/lombok-1.18.30.jar -d out-25.0.4.1-1.18.30 Member.java Main.java
An annotation processor threw an uncaught exception.
Consult the following stack trace for details.
java.lang.ExceptionInInitializerError
	at lombok.javac.apt.LombokProcessor.placePostCompileAndDontMakeForceRoundDummiesHook(LombokProcessor.java:174)
	…
Caused by: java.lang.NoSuchFieldException: com.sun.tools.javac.code.TypeTag :: UNKNOWN
	at lombok.permit.Permit.getField(Permit.java:144)
	at lombok.javac.JavacTreeMaker$SchroedingerType.getFieldCached(JavacTreeMaker.java:171)
	at lombok.javac.JavacTreeMaker$TypeTag.typeTag(JavacTreeMaker.java:259)
	at lombok.javac.Javac.<clinit>(Javac.java:186)
	... 16 more
[exit 3]
$ javac … lombok-1.18.48 … (JDK 21, JDK 25 둘 다)  → [exit 0], java … Main → kim
JDK 25에서 버전별: 1.18.30·1.18.32·1.18.34·1.18.36 → 위와 같은 NoSuchFieldException(exit 3), 1.18.38·1.18.40·1.18.48 → exit 0

## E6 (JDK 25)
$ javac -encoding UTF-8 -processorpath pout -processor TryOverwrite -s gen -d out src/Member.java
Note: createSourceFile("Member") -> javax.annotation.processing.FilerException: Attempt to recreate a file for type Member
Note: createClassFile("Member") -> javax.annotation.processing.FilerException: Attempt to recreate a file for type Member
Note: createSourceFile("MemberHelper") -> 성공 (새 파일)
[exit 0]
$ find gen out -type f
gen/MemberHelper.java
out/MemberHelper.class
out/Member.class
$ java --describe-module jdk.compiler
exports com.sun.source.doctree
exports com.sun.source.tree
exports com.sun.source.util
exports com.sun.tools.javac
qualified exports com.sun.tools.javac.tree to jdk.javadoc jdk.jshell jdk.internal.md
qualified exports com.sun.tools.javac.code to jdk.javadoc jdk.jshell
contains com.sun.tools.javac.processing
…

## E7 (JDK 25): javap -c -p로 메서드 바이트코드 비교
$ javac -d out-hand hand/Member.java     (hand = delombok -f pretty 출력 그대로)
$ diff lombok.javap hand.javap           → 출력 없음 [exit 0]
$ diff lombok.javap hand2.javap          → 출력 없음 [exit 0]  (hand2 = 위의 흔히 쓰는 모양)
  public java.lang.String getName();
    Code:
         0: aload_0
         1: getfield      #13                 // Field name:Ljava/lang/String;
         4: areturn

## E8 (Gradle 9.8.2, JDK 25.0.5)
a) $ gradle -q --no-daemon --console=plain bootJar        → [exit 0]
   dependencies --configuration compileClasspath     → \--- org.projectlombok:lombok -> 1.18.48
   dependencies --configuration annotationProcessor  → \--- org.projectlombok:lombok -> 1.18.48
   dependencies --configuration runtimeClasspath     → No dependencies
   $ jar tf build/libs/lb9-a.jar | grep BOOT-INF
   BOOT-INF/classes/Main.class
   BOOT-INF/classes/Member.class
   BOOT-INF/lib/spring-boot-jarmode-tools-4.1.2.jar       ← lombok jar 없음
   (eclipse-temurin:25-jre) $ java -jar build/libs/lb9-a.jar → kim
b) $ gradle -q --no-daemon --console=plain compileJava   (annotationProcessor 줄 없음)
   /w/exp8/b/src/main/java/Main.java:4: error: cannot find symbol
           member.setName("kim");
     symbol:   method setName(String)
   /w/exp8/b/src/main/java/Main.java:5: error: cannot find symbol
           System.out.println(member.getName());
     symbol:   method getName()
   2 errors
   BUILD FAILED in 2s
```

### 쓴 사실과 출처 (2026-11-03 확인)

출처 약칭:
- **CL**: Lombok changelog 태그 v1.18.48, https://github.com/projectlombok/lombok/blob/v1.18.48/doc/changelog.markdown
- **LP**: Lombok 소스 태그 v1.18.48, `https://github.com/projectlombok/lombok/blob/v1.18.48/src/`
- **FILER**: JDK 25 API `javax.annotation.processing.Filer`, https://docs.oracle.com/en/java/javase/25/docs/api/java.compiler/javax/annotation/processing/Filer.html
- **JAVAC**: JDK 25 javac 매뉴얼, https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html
- **OVERVIEW**: OpenJDK 컴파일러 그룹 "Compilation Overview"(버전 표시 없음), https://openjdk.org/groups/compiler/doc/compilation-overview/index.html
- **JDKC**: JDK 25 `jdk.compiler` 모듈, https://docs.oracle.com/en/java/javase/25/docs/api/jdk.compiler/module-summary.html
- **SF**: Spring Framework v7.0.10 문서, https://github.com/spring-projects/spring-framework/blob/v7.0.10/framework-docs/modules/ROOT/pages/core/validation/data-binding.adoc

실험 번호(E1…E8)는 위 "명령과 핵심 출력".

| 영상 속 내용 | 근거 |
|---|---|
| 박스 `@Getter @Setter` Member (0:00) | 실험 Member.java 4–9행. 사용자가 정한 시작 장면 |
| "메서드는 한 줄도 없어요" / "setName과 getName을 부르면, 컴파일도 되고 실행도 돼요"(0:00, 0:05), 박스 Main 3줄 + `kim` | E1 컴파일 exit 0, E1r `java -cp out Main` → `kim` |
| "컴파일된 Member.class를 열어 보면, getter와 setter가 진짜로 들어 있어요"(0:14), 박스 `public java.lang.String getName();` `public void setName(java.lang.String);` `… getId, getEmail, setId, setEmail` | E1 javap 출력에서 두 줄(앞 공백만 뺌). 마지막 줄은 내 주석 |
| "Lombok은 이렇게 어노테이션을 보고, 반복되는 코드를 컴파일할 때 대신 써 주는 라이브러리예요."(0:19) | README(v1.18.48) "Project Lombok is a java library that automatically plugs into your editor and build tools, spicing up your java. Never write another getter or equals method again". https://projectlombok.org/features/GetterSetter "You can annotate any field with @Getter and/or @Setter, to let lombok generate the default getter/setter automatically." "컴파일할 때"는 E1 `-XprintRounds` Round 1 `annotations: [lombok.Getter, lombok.Setter]` |
| "Lombok이 만든 코드를 소스로 풀어 보면, 6줄이 29줄이 돼요."(0:25), 박스 `# delombok -f pretty, 빈 줄 포함` `# 6줄 → 29줄` getName 3줄 `… 메서드 5개 더` | 6줄 = Member.java 4–9행. 29줄 = E1 `delombok -p -f pretty` 출력의 `public class Member {`부터 `}`까지(빈 줄 포함, 기본 형식은 41줄). https://projectlombok.org/features/all "Delombok copies your source files to another directory, replacing all lombok annotations with their desugared form. So, it'll turn @Getter back into the actual getter." 박스 getName 3줄은 그 출력에서 앞 공백만 뺐다 |
| "Java에선 필드를 private으로 감추고, getName과 setName 같은 메서드로 읽고 써요."(0:30) | Oracle Java Tutorials(JDK 8 기준) https://docs.oracle.com/javase/tutorial/java/javaOO/accesscontrol.html "Use private unless you have a good reason not to. Avoid public fields except for constants." + JDK 25 `java.beans.PropertyDescriptor` "Constructs a PropertyDescriptor for a property that follows the standard Java convention by having getFoo and setFoo accessor methods. Thus if the argument name is "fred", it will assume that the writer method is "setFred" and the reader method is "getFred"" |
| "필드를 public으로 열어 두면, 그 구현에 묶여서 나중에 바꾸기 어려워지거든요."(0:35) | 같은 튜토리얼 "Public fields tend to link you to a particular implementation and limit your flexibility in changing your code." |
| "이 이름 규칙이 JavaBeans 관례인데, Spring도 이 이름으로 값을 넣고 꺼내요."(0:40), 그림 `Spring` / `이 이름으로 값을 넣고 꺼냄` | SF 52–55행 "The `org.springframework.beans` package adheres to the JavaBeans standard. A JavaBean is a class with a default no-argument constructor and that follows a naming convention where (for example) a property named `bingoMadness` would have a setter method `setBingoMadness(..)` and a getter method `getBingoMadness()`." 5행 "… following JavaBeans conventions." 보조: E1r Introspector `name <- getName(), setName(..)` |
| 그림 `private String name` / `밖에서 직접 못 씀` | JLS SE 25 §6.6.1 "Otherwise, the member or constructor is declared private. Access is permitted only when one of the following is true: Access occurs from within the body of the top level class or interface that encloses the declaration of the member or constructor. …" |
| 그림 `getName()` 읽기, `setName()` 쓰기 | GetterSetter 문서 "A default getter simply returns the field … A default setter … simply sets the field to this value." |
| "IDE로 자동 생성해도 되지만, 만든 코드가 소스에 남아서 사람이 관리해야 해요."(0:46) | JetBrains IntelliJ IDEA 문서 https://www.jetbrains.com/help/idea/generating-code.html "Select the fields that should be used to determine equality, and click Next." / "If the overrides for equals() and hashCode() methods already exist in the class, you will be prompted whether you want to delete them before generating new ones." (생성 시점의 필드로 소스에 써 넣고, 다시 만들려면 사람이 다시 실행) |
| "두 객체가 같은지 보는 equals를 만든 뒤, email 필드를 추가했어요."(0:51), 박스 `// email 추가 전에 만든 equals` + `return Objects.equals(id, that.id)` / `&& Objects.equals(name, that.name);` | 예시 상황. E3 HandMember의 equals 한 줄을 두 줄로 나눔. equals 뜻은 같은 JetBrains 문서 "returns true if the object passed to it as the argument is equal to the object on which this method is invoked" |
| "equals 고치는 걸 잊으면, email만 다른 두 회원이 같다고 나와요."(0:57), 박스 `손으로 쓴 equals: true` | E3 출력 그대로 |
| "@EqualsAndHashCode를 붙이면, 컴파일할 때마다 다시 만들어서 email까지 비교해요."(1:01), 박스 `@EqualsAndHashCode equals: false` | E3 출력 그대로, E3 delombok의 `this$email … other$email` 비교. '컴파일할 때마다'는 LP `LombokProcessor`가 javac 실행 때마다 불리는 처리기(아래) |
| "Lombok은 Reinier Zwitserloot와 Roel Spilker가, 2009년부터 만들어 온 오픈소스예요."(1:07) | https://projectlombok.org/credits "Project Lombok - About the authors and everyone that's helped us create Project Lombok. Regular contributors to Project Lombok: Reinier Zwitserloot Roel Spilker". https://projectlombok.org/contact "Project Lombok is an open source project, maintained primarily by Roel Spilker and Reinier Zwitserloot." GitHub API(2026-11-03): 첫 커밋 `1677c4a52a` 2009-06-08 Reinier Zwitserloot "Initial commit. As a proof of concept, it already works in javac and eclipse!", Roel(rspilker) 첫 커밋 `8ada852308` 2009-07-14, 2009년 안에 69개. CL 619행 "### v0.8.1 (July 26th, 2009)" "Changelog tracking from this version on." LICENSE(v1.18.48) "Copyright (C) 2009-2021 The Project Lombok Authors." (MIT) |
| 박스 `# GitHub 첫 커밋` `2009-06-08 Initial commit.` `  Reinier Zwitserloot` `# projectlombok.org/credits` `Regular contributors:` `Reinier Zwitserloot, Roel Spilker` | 위 GitHub API 값(메시지 뒷부분 자름)과 credits 페이지(두 이름 사이 쉼표만 넣음) |
| "먼저 javac가 소스를 읽어서, 코드 구조를 나무 모양의 추상 구문 트리, AST로 정리해요."(1:13), 그림 `AST` / `추상 구문 트리: class, 필드 3개` | OVERVIEW "All the source files specified on the command line are read, parsed into syntax trees, …". JDKC "The com.sun.source.* packages provide the Compiler Tree API: an API for accessing the abstract trees (ASTs) representing Java source code" |
| "그다음 javac가 annotation processor라는 처리기를 부르는데, Lombok이 바로 이 처리기예요."(1:20) | OVERVIEW "All appropriate annotation processors are called." JAVAC "the compiler queries the processors to determine what annotations they process. When a match is found, the processor is called." "Processors are located by means of service provider-configuration files named META-INF/services/javax.annotation.processing.Processor". lombok-1.18.48.jar의 그 파일 내용: `lombok.launch.AnnotationProcessorHider$AnnotationProcessor`, `lombok.launch.AnnotationProcessorHider$ClaimingProcessor`. LP `src/core/lombok/javac/apt/LombokProcessor.java` 69–76행 "This Annotation Processor is the standard injection mechanism for lombok-enabling the javac compiler." `public class LombokProcessor extends AbstractProcessor` |
| "Lombok은 트리에서 @Getter를 찾아, getName 같은 메서드를 끼워 넣어요."(1:25), 그림 `AST + getName() …` / `메서드 6개가 붙은 트리` | LP `src/core/lombok/javac/handlers/HandleGetter.java` 222행 `injectMethod(fieldNode.up(), source, createGetter(...))`, 272행 `treeMaker.MethodDef(...)`. `JavacHandlerUtil.java` 1394–1416행 `JCClassDecl type = (JCClassDecl) typeNode.get(); … type.defs = type.defs.append(method);`. 6개는 E1 javap |
| "마지막으로 javac가, 바뀐 트리로 Member.class를 만들어요."(1:30), 그림 `Member.class` / `getName() 들어 있음`, 화살표 `1. javac` `2. Lombok` `3. javac` | OVERVIEW "Finally, the syntax trees created by the parser are analyzed and translated into class files." E1: 새 소스 파일 없이(gen 비어 있음) 같은 Member.class에 메서드 |
| "그런데 annotation processor가 표준 API로 코드를 더하는 방법은, 새 파일을 만드는 거예요."(1:34), 그림 `표준 API` / `Filer`, `새 파일` / `MemberHelper: 성공` | FILER "This interface supports the creation of new files by an annotation processor." API Note "Some of the effect of overwriting a file can be achieved by using a decorator-style pattern. Instead of modifying a class directly, the class is designed so that either its superclass is generated by annotation processing or subclasses of the class are generated by annotation processing." JAVAC "If any processors generate new source files, then another round of annotation processing occurs". E6 `createSourceFile("MemberHelper") -> 성공 (새 파일)` |
| "실제로 이미 있는 Member를 다시 만들려 하면, FilerException이 나요."(1:40), 그림 `기존 Member` / `FilerException` | E6 `FilerException: Attempt to recreate a file for type Member`. FILER "The initial inputs to the tool are considered to be created by the zeroth round; therefore, attempting to create a source or class file corresponding to one of those inputs will result in a FilerException." |
| "Lombok은 이 길 대신, 공식 API가 아닌 javac 내부 클래스로 Member의 트리를 직접 고쳐요."(1:45), 그림 `Lombok` → `javac 내부` / `공식 API 아님` → `트리 직접 수정` / `메서드 추가` | LP `LombokProcessor.java` 55–57행 import `com.sun.tools.javac.processing.JavacFiler`, `…JavacProcessingEnvironment`, `com.sun.tools.javac.tree.JCTree.JCCompilationUnit`. 420–422행 `addOpensForLombok()` 뒤 `(JavacProcessingEnvironment) procEnv` 캐스팅. 469–491행 `addOpensForLombok()`가 `sun.misc.Unsafe`와 `implAddOpens`로 `com.sun.tools.javac.code/comp/file/main/model/parser/processing/tree/util/jvm`을 연다. '공식 API 아님'의 근거는 세 가지다. (1) JDKC Exports 표에서 모두에게 여는 export는 `com.sun.source.doctree/tree/util`와 `com.sun.tools.javac`("legacy entry point")뿐이다. (2) E6 `--describe-module`로 보면 `com.sun.tools.javac.tree`는 jdk.javadoc·jdk.jshell·jdk.internal.md에만 qualified export되고, `.processing`은 export가 없다(`contains`). (3) JEP 403 https://openjdk.org/jeps/403 "Tools that use the com.sun.tools.javac.* packages to process source code. Such tools should instead use the javax.tools, javax.lang.model, and com.sun.source.* APIs". 참고로 `JCTree` 자체는 `public abstract class`다. 막혀 있는 건 모듈 export다 |
| "메서드는 이미 클래스 파일에 들어 있어서, 실행할 땐 Lombok이 필요 없어요."(1:51), 박스 `# Lombok jar가 없는 JRE에서` `$ java -cp out Main` `kim` | E1r. https://projectlombok.org/setup/gradle "you have to specify that the lombok dependency is required to compile your source code, but does not need to be present when running/testing/jarring/otherwise deploying your code." CL 6행(1.18.48) "`@SneakyThrows` usage on JDK26 no longer results in class files that require `lombok.jar` to be on the runtime classpath (which should not be neccessary)." |
| "Lombok jar가 없는 곳에서도 잘 돌고, getter의 바이트코드도 손으로 쓴 것과 같아요."(1:57), 박스 `# 손으로 쓴 Member와 javap -c 비교` `$ diff lombok.javap hand.javap` `# 출력 없음: 메서드 바이트코드 같음` | E7(`javap -c -p` 기준, hand와 hand2 둘 다 차이 없음). 클래스 파일 전체가 같지는 않다. Lombok 쪽에만 `RuntimeInvisibleAnnotations: lombok.Generated`가 있고 LineNumberTable도 다르다(검증자 확인) |
| "그래서 Gradle에선 compileOnly로, 컴파일할 때만 넣어요."(2:02), 박스 `dependencies {` `  compileOnly 'org.projectlombok:lombok'` | Gradle 9.8.2 https://docs.gradle.org/9.8.2/userguide/java_plugin.html compileOnly "Represents dependencies that are required only at compile time and are not included in the runtime classpath (i.e., compile time only dependencies, not used at runtime)." Lombok gradle 설치 문서 "gradle has the built-in compileOnly scope, which can be used to tell gradle to add lombok only during compilation." E8a runtimeClasspath `No dependencies`, bootJar lib에 lombok 없음 |
| "annotationProcessor 줄은 javac가 Lombok을 처리기로 돌리게 해서, 빼면 getter가 안 생겨요."(2:07), 박스 `  annotationProcessor 'org.projectlombok:lombok'` `}` `# annotationProcessor 줄을 빼면` `error: cannot find symbol` | 같은 Gradle 문서 annotationProcessor "Represents annotation processors used during the compilation of a project's source code (i.e., annotation processors used during compilation)." E8b(에러 줄은 앞 경로를 자름). javac 단독도 같다: E1 `-cp`만 주면 cannot find symbol. JAVAC "-proc … If this option is not used, annotation processing and compilation are done if at least one other option is used to explicitly configure annotation processing." |
| "대신 JDK 21에서 잘 되던 Lombok 1.18.30을, JDK 25에서 쓰면 컴파일이 실패해요."(2:13), 박스 `# Lombok 1.18.30, JDK 21: 성공` `# 같은 코드, JDK 25:` `An annotation processor threw` ` an uncaught exception.` `…NoSuchFieldException:` ` …TypeTag :: UNKNOWN` | E5(에러 첫 줄은 줄바꿈만, Caused by 줄은 앞을 '…'로 자름). CL 68–69행 "### v1.18.30 (September 20th, 2023)" "PLATFORM: Initial JDK21 support added." |
| "javac 안에 있던 UNKNOWN이라는 값이 JDK 24에서 지워졌는데, 옛 Lombok이 그 값을 찾았거든요."(2:20) | OpenJDK `src/jdk.compiler/share/classes/com/sun/tools/javac/code/TypeTag.java`: 태그 `jdk-23-ga` 126행 `UNKNOWN,`(주석 "The tag of an unknown type") 있음, `jdk-24-ga`·`jdk-25-ga`엔 없음(검증자: jdk-24+22부터 없음). 지운 커밋 https://github.com/openjdk/jdk/commit/f0b130e54f33d3190640ce33c991e35f27e9f812 (2024-10-24, "8339296: Record deconstruction pattern in switch fails to compile"). E5 스택 `lombok.permit.Permit.getField` ← `JavacTreeMaker$TypeTag.typeTag` ← `lombok.javac.Javac.<clinit>`. 1.18.36(CL 43–44행 "JDK23 support added")까지 실패, 1.18.38(CL 37–38행 "JDK24 support added")부터 성공 |
| "javac 내부는 예고 없이 바뀔 수 있어서, JDK를 올릴 땐 그 JDK를 지원하는 Lombok인지 확인해야 해요."(2:27) | JEP 260 https://openjdk.org/jeps/260 "This JEP does not commit to preserve the compatibility of any internal APIs across releases; they continue to remain unstable and subject to change without notice." CL의 JDK별 항목: 4–5행 v1.18.48 "JDK27 support added", 13–14행 v1.18.46 "JDK26 support added", 29–30행 v1.18.40 "JDK25 support added", 37–38행 v1.18.38 "JDK24 support added" |
| "정리하면, Lombok은 컴파일할 때 javac의 구문 트리에 반복 메서드를 넣어 주는 도구예요." / "그래서 실행할 땐 필요 없지만, 컴파일러 내부에 기대서 JDK를 올릴 땐 Lombok 지원 버전을 확인해야 해요."(2:34), 그림 `Lombok` / `컴파일 때 AST에 메서드 추가`, `실행` / `Lombok 없이 돎`, `JDK 업그레이드` / `Lombok 지원 버전 확인` | 위 1:13–1:45, 1:51, 2:13–2:27 근거 |
| 썸네일 `# 메서드 0줄인데 getName()이 된다` / `Lombok이란? 어떻게 동작할까?` | 장면 0·1. 영상의 질문을 줄인 것 |

### 독립 사실 확인 반영 기록 (2026-11-04)

독립 검증 결과는 틀림 0, 오해 소지 1, 사소 6건이었다. 검증자가 다시 돌린 결과는 모두 내 로그와 같았다. 다시 돌린 것: javap, Filer 재생성 FilerException, 1.18.30의 JDK 21/25 결과, Lombok 없는 JRE 실행, Gradle a/b, JEP 260 인용, TypeTag UNKNOWN 삭제.

| 지적 | 전 | 후 |
|---|---|---|
| [오해 소지] Lombok equals는 `@EqualsAndHashCode`(또는 `@Data`)가 있어야 생긴다. 영상의 Member는 `@Getter @Setter`뿐이라 "Lombok이면 equals가 저절로"로 읽힌다. 검증자 재현: `@Getter @Setter`만 붙이면 값이 모두 같아도 `false`(Object.equals) | 나레이션 "Lombok은 컴파일할 때마다 다시 만들어서, email까지 비교해요." / 화면 `Lombok equals: false` | "@EqualsAndHashCode를 붙이면, 컴파일할 때마다 다시 만들어서 email까지 비교해요." / 화면 `@EqualsAndHashCode equals: false`. 실험 출력 라벨도 같게 바꿔 다시 돌림(E3). pronounce `@EqualsAndHashCode` 추가 |
| '그래서'의 동기는 공식 문서에 없다. `JCTree`는 public 클래스이고, 막힌 건 모듈 export다 | "그래서 Lombok은 공개되지 않은 javac 내부 클래스로, Member의 트리를 직접 고쳐요." / 그림 sub `공개 API 아님` | "Lombok은 이 길 대신, 공식 API가 아닌 javac 내부 클래스로 Member의 트리를 직접 고쳐요." / 그림 sub `공식 API 아님`. 근거에 Filer API Note와 `--describe-module` 결과 추가 |
| 첫 커밋은 Reinier 혼자, Roel 첫 커밋은 2009-07-14 | "Lombok은 2009년, Reinier Zwitserloot와 Roel Spilker가 만든 오픈소스예요." | "Lombok은 Reinier Zwitserloot와 Roel Spilker가, 2009년부터 만들어 온 오픈소스예요." |
| changelog상 JDK25 지원은 1.18.40부터지만 1.18.38도 됨. 늘 깨지는 건 아니니 권고로 | "…JDK를 올리면 그 JDK를 지원하는 Lombok으로 같이 올려야 해요." / 정리 "JDK를 올릴 땐 Lombok 버전도 맞춰야 해요" / 그림 `Lombok도 같이` | "…JDK를 올릴 땐 그 JDK를 지원하는 Lombok인지 확인해야 해요." / 정리 "…Lombok 지원 버전을 확인해야 해요." / 그림 `Lombok 지원 버전 확인` |
| 29줄은 `-f pretty`·빈 줄 포함 숫자, 기본 delombok은 41줄 | 화면 `# 필드 3개: 메서드 6개, 6줄 → 29줄` | 화면 `# delombok -f pretty, 빈 줄 포함` / `# 6줄 → 29줄` |
| AST = abstract syntax tree | "나무 모양의 AST, 구문 트리로" / 그림 `구문 트리: …` | "나무 모양의 추상 구문 트리, AST로" / 그림 `추상 구문 트리: …` |
| markup의 JDK 버전: Gradle 실험은 25.0.5 | "JDK 25.0.4.1 …, Gradle 9.8.2" 한 줄 | javac 25.0.4.1, JRE 25.0.4.1, JDK 21.0.13, Gradle 실험 JDK 25.0.5를 따로 적음 |
| 바이트코드 같음은 `javap -c -p` 기준만 | "바이트코드도 손으로 쓴 getter와 똑같아요." / 화면 `# 출력 없음: 차이 없음` | "getter의 바이트코드도 손으로 쓴 것과 같아요." / 화면 `# 출력 없음: 메서드 바이트코드 같음`. 이 표에 클래스 파일 차이 명시 |
| 사실표 정정: CL v1.18.48 머리줄은 4행, JDKC Exports엔 "모두에게 여는 export 기준" 조건 | — | 위 출처 표에 반영 |

고친 뒤 film 166.6초에서 169.0초가 됐다.

### 빼거나 확인만 한 것

- **IntelliJ 내장 여부**: 공식 자료끼리 다르게 읽혀서 뺐다.
  - JetBrains intellij-community `plugins/lombok/README.md`: "Integrated into IntelliJ starting with 2020.3 Release"
  - https://projectlombok.org/setup/intellij: "The Jetbrains IntelliJ IDEA editor is compatible with lombok without a plugin as of version 2020.3 to version 2023.1. For versions prior to 2020.3 or later than 2023.1, you can add the Lombok IntelliJ plugin …"
- **이름 유래**: 1차 출처를 찾지 못해 뺐다.
- **Maven**: https://projectlombok.org/setup/maven
  - `<scope>provided</scope>`
  - "You also need to add lombok as an annotation processor. This is mandatory starting with JDK23, or JDK9+ if compiling as modules"
- **JDK 24+ Unsafe 경고**: Lombok 1.18.48도 JDK 25에서 `sun.misc.Unsafe::objectFieldOffset … will be removed in a future release` 경고를 찍는다. 범위 밖이라 뺐다.
- **Perry Nguyen**: credits 페이지의 "for creating the inspiration for project lombok"은 확인만 했다.

## 측정한 것 / 보기만 한 것

- 길이: 169.03초(ffprobe). 1080x1920, 30fps. film(timing.json) 169.028초, 30문장, 13장면.
- 음량: 통합 -14.1 LUFS, 피크 -1.5 dBFS.
- check: 0 errors, 경고는 `line_unread` 15건뿐(아래).
- build.py 경고: 처음 빌드에서 세 가지가 나와서 고쳤다. 마지막 빌드는 경고 없음.
  - `chars/s` 3건(javap, delombok, history 박스): javap의 두 번째 블록(`Lombok`)을 빼고, delombok·history 박스의 주석 줄을 줄였다.
  - processor 그림 `diagram text down to 37px`: 상자 글자를 줄였다(`새 파일`, `기존 Member`, `javac 내부`, `트리 직접 수정`).
- 눈으로 본 것(snapshot, 장면마다 가운데·끝 프레임):
  - 0초 프레임에 Member 박스와 첫 자막이 보인다.
  - 자막은 모두 2줄 안이고, 기술 용어는 영어로 나온다.
  - 다이어그램 라벨이 겹치지 않는다.
  - build.gradle 박스는 가장 긴 줄이 48칸이라 약 38px이다. 원본 크기 프레임에서 읽혔다.
  - 썸네일 제목 145px.
- 들어서 확인할 곳:
  - 1:07 사람 이름: "Reinier Zwitserloot"(레이니어 즈비처로트), "Roel Spilker"(룰 스필커). 네덜란드어 이름을 대략 옮겼다.
  - 1:01 "@EqualsAndHashCode"(이퀄즈앤해시코드)
  - 2:13 "Lombok 1.18.30"(일점십팔점삼십), "JDK 21", "JDK 25"
  - 2:20 "UNKNOWN", "JDK 24"
  - 0:25 "6줄이 29줄이"
  - 1:13, 1:20 "AST", "annotation processor"
  - 2:02, 2:07 "compileOnly", "annotationProcessor"
  - 0:14 "Member.class"(멤버클래스)

## 일부러 남긴 경고

`line_unread` 15건. 글자마다 `<span>`이라 단어 수가 부풀려 세어지는 경고다(인덱스 편 10건, B-tree 편 2건과 같은 종류).
- 긴 코드·로그 줄(System.out.println, javap, delombok, equals 결과, credits, diff, build.gradle)이 화면에 4–7초 머문다.
- 박스는 다음 장면까지 남고, 같은 내용을 나레이션이 설명하므로 그대로 뒀다.

## 가장 약한 부분

- **"두 사람이 2009년부터 만들어 온"**: 공식 사이트는 두 사람을 "Regular contributors", "maintained primarily by"로만 적고 "창시자"라는 말은 없다. 첫 커밋은 Reinier 혼자다. "2009년부터 만들어 온"으로 표현을 낮췄다.
- **private 관례의 이유**: Oracle Java Tutorials(JDK 8 기준)에서 가져왔다. 같은 문장을 JDK 25 문서에서 찾지 못했다.
- **IDE 생성 부분**: IntelliJ 문서로 절차만 확인했고, IDE로 실제 생성해 보지는 않았다. 화면의 equals는 내가 쓴 예시 코드다.
- **"표준 API로 코드를 더하는 방법은 새 파일을 만드는 것"**: Filer 문서와 API Note, E6 실험에 근거한 요약이다. 표준 API에는 메시지 출력(Messager)이나 요소 조회 같은 다른 기능도 있다. 그래서 "코드를 더하는 방법"으로 범위를 좁혔다.
- **"JDK 24에서 지워졌는데"**: 1.18.30은 JDK 21~23에서 TypeTag.UNKNOWN을 찾을 수 있었다는 뜻이다. 다만 JDK 22·23에서 직접 돌려 보지는 않았다(소스 태그 jdk-23-ga에 UNKNOWN이 있는 것만 확인).
