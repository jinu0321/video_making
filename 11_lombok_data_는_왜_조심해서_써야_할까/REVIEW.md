# REVIEW

## 시청 후 답할 수 있는 것

질문: **@Data는 무엇을 한 번에 만들고, 왜 아무 클래스에나, 특히 JPA 엔티티에 붙이면 위험한가요? 대신 무엇을 쓰나요?**

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **@Data는 Lombok 어노테이션 다섯 개(@Getter, @Setter, @ToString, @EqualsAndHashCode, @RequiredArgsConstructor)를 묶은 것이다. getter는 모든 필드에, setter는 final이 아닌 필드에 만들고, toString·equals·hashCode와 필수 필드(초기값 없는 final·@NonNull 필드)를 받는 생성자를 만든다.**
   왜: Lombok 문서가 @Data를 그 다섯 개를 클래스에 붙인 것과 같다고 정의한다. 컴파일된 클래스를 javap로 열면 메서드가 실제로 들어 있다. 예제 Member는 final 필드가 없어서 생성자의 인자가 없다. (0:00 훅 코드, 0:14 Data.java 그림, 0:27 javap)
2. **setter가 public으로 다 열린다. 그래서 어디서든 null도 넣을 수 있고, 규칙을 지킬 곳이 없다. 대처: getter만 열고, 값은 검사를 넣은 메서드 한 곳에서만 바꾸게 한다.**
   왜: Lombok이 만드는 getter와 setter는 public이고, 받은 값을 그대로 넣는다(@NonNull이 없을 때). `changeName`처럼 메서드 하나로 모으면 검사가 그 한 곳에 생긴다. (0:36 Main.java, 0:44 Member.java)
3. **@Data의 hashCode는 모든 필드로 계산한다. 그래서 HashSet에 넣은 뒤 이름을 바꾸면 분명 들어 있는데도 contains와 remove가 실패한다.**
   왜: HashSet(속은 HashMap)은 넣을 때의 hashCode로 칸을 정해 넣고, 찾을 땐 지금 hashCode로 칸을 다시 계산한다. 실험에서 kim은 16칸 중 칸 2에 들어갔는데, lee로 바꾼 뒤 contains는 빈 칸 1을 봤다. (0:06 훅, 0:50 hashCode 값, 0:56 HashSet 그림)
4. **@Data의 toString과 hashCode는 필드 객체의 것까지 부른다. 그래서 서로 참조하면(Member ↔ Team) 끝없이 불러 StackOverflowError가 난다. 대처는 한쪽 필드에 @ToString.Exclude와 @EqualsAndHashCode.Exclude를 붙이는 것이다.**
   왜: 생성된 toString은 `String.valueOf(getTeam())`을, hashCode는 `getTeam().hashCode()`를 부른다(바이트코드 확인). List는 원소마다 다시 toString과 hashCode를 부른다. (1:06 call-stack 그림, 1:16 run.log, 1:21 Team.java)
5. **JPA 엔티티에선 더 쉽게 터진다. id를 DB가 만들게 하면 save 전엔 null이다가 저장하면 값이 생겨 hashCode가 바뀐다. 양방향 @Data 엔티티는 트랜잭션 안에서 toString 한 번에 StackOverflowError가 난다. Hibernate 문서도 바뀌는 필드와 DB가 만드는 필드는 hashCode에 넣지 말라고 한다.**
   왜: Hibernate 7.4.13 + MySQL 8.4 실험 결과 id가 null에서 1이 되면서 contains가 false였다. 양방향 toString은 members를 읽은 뒤 StackOverflowError가 났다. (1:27 jpa.log, 1:37 jpa.log, 1:42 hashCode.txt 그림)
6. **그래서 엔티티엔 @Data 대신 @Getter처럼 필요한 것만 붙인다. equals와 hashCode를 안 만들면 같은 객체인지만 봐서 id가 생겨도 hashCode가 그대로다. Set으로 담는 연관관계라면 안 바뀌는 값으로 equals와 hashCode를 직접 만든다.**
   왜: Object.equals는 같은 객체인지만 보고, 실험에서 @Getter 엔티티는 save 전후 hashCode가 같아 contains가 true였다. Hibernate User Guide는 안 만드는 것도 고려하라고 하고, Introduction은 Set 연관관계면 바뀌지 않고 DB가 만들지도 않는 값(자연 키)으로 만들라고 한다. (1:48 Member.java)
7. **값만 담는 DTO는 Java 16부터 있는 record로 만든다. 생성자, `name()` 같은 접근자, equals, hashCode, toString을 언어가 만들어 준다. 필드가 final이라 setter가 없고 값을 다시 넣을 수도 없어서, 이 MemberDto(Long, String)는 HashSet에 넣은 뒤에도 hashCode가 그대로다. 단, JPA 명세는 record를 엔티티로 쓸 수 없다고 정해 뒀다.**
   왜: JLS §8.10에서 record의 컴포넌트 필드는 private final이고, 접근자·equals·hashCode·toString은 암묵적으로 선언된다. Jakarta Persistence 3.2 §2.1은 "An enum, record, or interface may not be designated as an entity."라고 쓴다. 실제로 Hibernate 7.4.13에서 record 엔티티를 읽으면 `InstantiationException: No default constructor for entity`가 났다. (2:04 MemberDto.java, 2:15 javap, 2:24 spec.txt)

기억할 한 문장: "@Data는 한 줄로 여러 메서드를 만들어 줘서 편하지만, 바뀌는 필드로 hashCode를 만들고 연결된 객체까지 따라가 출력한다. 그래서 엔티티엔 필요한 것만 고르고, DTO는 record로 만든다." (2:34 summary.md 그림)

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
npx --yes hyperframes@0.8.209 render -o "output/lombok_data_는_왜_조심해서_써야_할까.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/lombok_data_는_왜_조심해서_써야_할까.mp4"
ffmpeg -nostats -i "output/lombok_data_는_왜_조심해서_써야_할까.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 사용자 요청("면접관이 고개 끄덕일 정도로 롬복을 알 수 있게")을 Lombok 세 편으로 나눴고, 이 편은 @Data의 위험과 대안만 다룬다.
  - Lombok의 역사, 만든 사람, 컴파일 때의 원리, 런타임 비용은 다루지 않는다.
  - 생성자 어노테이션(@RequiredArgsConstructor와 생성자 주입, JPA 기본 생성자, @AllArgsConstructor, @Builder)도 다루지 않는다.
  - 다른 영상 얘기는 대본·화면·썸네일 어디에도 없다.
- 시작은 Java 개발자에게 익숙한 `@Data class Member` 코드다. 훅은 "HashSet에 넣고 이름을 바꾸면 못 찾는다"이고, 실험으로 확인한 결과만 쓴다.
- 뺀 것(다음 영상 후보):
  1. **toString이 지연 로딩을 건드리는 문제.** 실험(J2)에서 `team.toString()`이 members SELECT를 부른 뒤 StackOverflowError가 났다(아래 로그 111행). 트랜잭션 밖이면 `LazyInitializationException`이 난다(독립 검증자 재현). 입문자에게 지연 로딩부터 설명해야 해서 뺐다.
  2. **엔티티 equals/hashCode를 제대로 만드는 법.** 자연 키, `@NaturalId`, 프록시라 `instanceof`와 getter를 쓰는 이유(Hibernate Introduction §3.26).
  3. **@Value와 record 비교.** @Value는 final 클래스, private final 필드, all-args 생성자를 만든다(Lombok @Value 문서). 시간이 없어 뺐다.
  4. **record도 순환 참조면 터진다.** List 같은 가변 컴포넌트가 있으면 "shallowly immutable"이라 내용이 바뀐다(아래 실험 R1).

### 실험 환경과 버전 (2026-11-03 ~ 11-04)

- 호스트: macOS(Darwin 25.5.0), Docker. 모든 빌드·실행은 컨테이너 안에서 했고, 호스트 포트는 열지 않았다.
- 이미지:
  - `maven:3.9-eclipse-temurin-25` (`sha256:93b8a14ea2f412782e4e842651273b4d903e35cc496284f178fbbe2d67d00976`): Maven 3.9.16, `java -version` → `openjdk version "25.0.4.1" 2026-08-18 LTS`, Temurin-25.0.4.1+1
  - `eclipse-temurin:25-jre` (`sha256:78f1f183913482ef390c2722f46c3f0ce76ada341d69590e7c482ec943ee72d5`)
  - `mysql:8.4` (`sha256:a0225d1ea6631c8bc2385dc4c2faba17bbf1834ecf369e1659a9a382bd8d5dd7`), `select version()` → 8.4.13
- Lombok 1.18.48: `spring-boot-dependencies-4.1.2.pom` 130행 `<lombok.version>1.18.48</lombok.version>`. JPA 프로젝트의 `mvn dependency:list` 결과는 아래와 같다.
  - `org.projectlombok:lombok:jar:1.18.48:compile (optional)`
  - `org.hibernate.orm:hibernate-core:jar:7.4.13.Final`
  - `jakarta.persistence:jakarta.persistence-api:jar:3.2.0`
  - `org.springframework:spring-core:jar:7.0.10`
  - `org.springframework.boot:spring-boot:jar:4.1.2`
  - `org.springframework.data:spring-data-jpa:jar:4.1.2`
  - `com.mysql:mysql-connector-j:jar:9.7.0`
- 앱이 찍은 버전: `[앱] Java 25.0.4.1, Spring Boot 4.1.2, Spring Framework 7.0.10, Hibernate 7.4.13.Final`
- 컴파일:
  - Maven 프로젝트: `maven-compiler-plugin` 3.15.0(Boot 4.1.2 BOM 값)의 `annotationProcessorPaths`에 lombok `${lombok.version}`을 지정했다.
  - 화면용 코드(기본 패키지): `javac -proc:full -cp lombok-1.18.48.jar -processorpath lombok-1.18.48.jar`로 컴파일했다.
  - 화면의 javap 줄에 패키지 이름이 안 나오게 하려고 기본 패키지를 썼다.
- Docker 자원: 네트워크 `lb11-net`, 컨테이너 `lb11-mysql`(`MYSQL_ALLOW_EMPTY_PASSWORD=yes`, `MYSQL_DATABASE=lb11`), Maven 저장소 볼륨 `lb11-m2`, 일회성 `lb11-*` 컨테이너(`--rm`)를 썼다. 끝난 뒤 모두 지웠다.

### 출처 (원문 인용)

| 키 | 출처 (버전) | 원문 |
|---|---|---|
| L-Data | projectlombok.org/features/Data. GitHub `projectlombok/lombok` 태그 `v1.18.48`의 `website/templates/features/Data.html`과 라이브 페이지의 핵심 문장이 같은지 확인했다. | "@Data is a convenient shortcut annotation that bundles the features of @ToString, @EqualsAndHashCode, @Getter / @Setter and @RequiredArgsConstructor together: … getters for all fields, setters for all non-final fields, and appropriate toString, equals and hashCode implementations that involve the fields of the class, and a constructor that initializes all final fields, as well as all non-final fields with no initializer that have been marked with @NonNull" / "@Data is like having implicit @Getter, @Setter, @ToString, @EqualsAndHashCode and @RequiredArgsConstructor annotations on the class" / "All generated getters and setters will be public." / "All static fields will be skipped entirely" |
| L-DataJava | lombok `v1.18.48` `src/core/lombok/Data.java` javadoc | "Generates getters for all fields, a useful toString method, and hashCode and equals implementations that check all non-transient fields. Will also generate setters for all non-final fields, as well as a constructor … Equivalent to {@code @Getter @Setter @RequiredArgsConstructor @ToString @EqualsAndHashCode}." |
| L-RAC | projectlombok.org/features/constructor (`v1.18.48` 템플릿) | "@RequiredArgsConstructor generates a constructor with 1 parameter for each field that requires special handling. All non-initialized final fields get a parameter, as well as any fields that are marked as @NonNull that aren't initialized where they are declared." |
| L-EHC | projectlombok.org/features/EqualsAndHashCode (`v1.18.48` 템플릿) | "By default, it'll use all non-static, non-transient fields, but you can modify which fields are used … by marking type members with @EqualsAndHashCode.Include or @EqualsAndHashCode.Exclude." |
| L-TS | projectlombok.org/features/ToString (`v1.18.48` 템플릿) | "the format is fixed: the class name followed by parentheses containing fields separated by commas, e.g. MyClass(foo=123, bar=234)." / "By default, all non-static fields will be printed. If you want to skip some fields, you can annotate these fields with @ToString.Exclude." |
| J-Obj | JDK 25 API `java.lang.Object` | hashCode: "Whenever it is invoked on the same object more than once during an execution of a Java application, the hashCode method must consistently return the same integer, provided no information used in equals comparisons on the object is modified." / "This method is supported for the benefit of hash tables such as those provided by HashMap." / equals: "for any non-null reference values x and y, this method returns true if and only if x and y refer to the same object (x == y has the value true)." |
| J-Set | JDK 25 API `java.util.Set` | "Note: Great care must be exercised if mutable objects are used as set elements. The behavior of a set is not specified if the value of an object is changed in a manner that affects equals comparisons while the object is an element in the set." |
| J-HS | JDK 25 API `java.util.HashSet` | "This class implements the Set interface, backed by a hash table (actually a HashMap instance)." |
| J-HMsrc | OpenJDK `openjdk/jdk25u` 태그 `jdk-25.0.4.1+1` (실험 JDK와 같은 빌드) `HashSet.java`, `HashMap.java` | `HashSet.add`: `return map.put(e, PRESENT)==null;` / `HashSet.contains`: `return map.containsKey(o);` / `static final int hash(Object key) { int h; return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16); }` / `putVal`: `if ((p = tab[i = (n - 1) & hash]) == null) tab[i] = newNode(hash, key, value, null);` / `getNode`: `(first = tab[(n - 1) & (hash = hash(key))]) != null` 다음에 `first.hash == hash && ((k = first.key) == key \|\| …equals(k))` / `containsKey`: `return getNode(key) != null;` / `static class Node<K,V> { final int hash; …` |
| J-AC | JDK 25 API `java.util.AbstractCollection.toString()` | "Elements are converted to strings as by String.valueOf(Object)." |
| J-List | JDK 25 API `java.util.List.hashCode()` | "hashCode = 31*hashCode + (e==null ? 0 : e.hashCode());" |
| J-SOE | JDK 25 API `java.lang.StackOverflowError` | "Thrown when a stack overflow occurs because an application recurses too deeply." |
| J-Rec | JDK 25 API `java.lang.Record` | "A record class is a shallowly immutable, transparent carrier for a fixed set of values" / "a private final field corresponding to each component … a public accessor method corresponding to each component" / "Since: 16" |
| JLS | JLS SE 25 §8.10 (docs.oracle.com/javase/specs/jls/se25/html/jls-8.html) | "A record class is implicitly final." / §8.10.3 "A component field is private, final, and non-static." / 접근자 "Its name is the same as the name of the record component." / 암묵적 선언 "A method public final boolean equals(Object) …", "A method public final int hashCode() that returns a hash code value derived from the hash code values at every record component of R.", "A method public final String toString() …" / §8.10.4 "a record class does not implicitly declare a default constructor (§8.8.9). Instead, a record class has a canonical constructor … that initializes all the component fields" |
| JPA | Jakarta Persistence 3.2 명세 §2.1 The Entity Class (jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.html) | "An enum, record, or interface may not be designated as an entity." / "The entity class must have a public or protected constructor with no parameters" / "The entity class must be non-final. Every method and persistent instance variable of the entity class must be non-final." |
| H-Intro | Hibernate ORM 7.4 "Introduction to Hibernate 7" §3.26 equals() and hashCode() (docs.hibernate.org/orm/7.4/introduction/html_single/Hibernate_Introduction.html) | "Entity classes should override equals() and hashCode(), especially when associations are represented as sets." / "You should not include a mutable field in the hashcode, since that would require rehashing every collection containing the entity whenever the field is mutated." / "It's not completely wrong to include a generated identifier (surrogate key) in the hashcode, but since the identifier is not generated until the entity instance is made persistent, you must take great care to not add it to any hashed collection before the identifier is generated. We therefore advise against including any database-generated field in the hashcode." / "It's OK to include any immutable, non-generated field in the hashcode." / "We therefore recommend identifying a natural key for each entity" |
| H-UG | Hibernate ORM 7.4 User Guide (docs.hibernate.org/orm/7.4/userguide/html_single/Hibernate_User_Guide.html) | §3.4.7: "you may want to consider not implementing equals/hashCode altogether." / "Hibernate guarantees equivalence of persistent identity (database row) and Java identity inside a particular session scope." / "Set says that the equals/hashCode value for an object should not change while the object is part of the Set. But that is exactly what happened here because the equals/hasCode are based on the (generated) id" / §3.4.1: "Technically Hibernate can persist final classes or classes with final persistent state accessor (getter/setter) methods. However, it is generally not a good idea as doing so will stop Hibernate from being able to generate proxies for lazy-loading the entity." |
| H-Bag | Hibernate ORM 태그 `7.4.13` `hibernate-core/.../collection/spi/PersistentBag.java` | `toString()`: `read(); return collection.toString();` / equals·hashCode 위 주석: "For efficiency, bag does not respect the semantics of List#equals(Object) as specified by the supertype List. Instead, instance equality is used, to avoid the need to fetch the elements of the bag." `hashCode()`는 `return super.hashCode();` |

블로그는 근거로 쓰지 않았다. 중국어 출처는 쓰지 않았다.

### 실험 코드와 출력

출력은 실제 로그를 그대로 옮겼다. 화면에 쓴 줄에는 ◀ 표시를 했다.

**E1·E2 훅 Member와 HashSet** (기본 패키지, Lombok 1.18.48, JDK 25.0.4.1)

```java
// Member.java (화면 첫 장면과 같다)
import lombok.Data;

@Data
public class Member {
    private Long id;
    private String name;
}

// Main.java
Member member = new Member();
member.setId(1L);
member.setName("kim");
Set<Member> set = new HashSet<>();

set.add(member);
System.out.println("넣을 때 hashCode: " + member.hashCode());
member.setName("lee");
System.out.println("이름 바꾼 뒤 hashCode: " + member.hashCode());
System.out.println("contains: " + set.contains(member));
System.out.println("size: " + set.size());
System.out.println("remove: " + set.remove(member));
System.out.println("remove 뒤 size: " + set.size());

member.setName(null);
System.out.println(member);
```

```
$ javap -p Member.class
Compiled from "Member.java"
public class Member {
  private java.lang.Long id;
  private java.lang.String name;
  public Member();                                ◀
  public java.lang.Long getId();
  public java.lang.String getName();
  public void setId(java.lang.Long);
  public void setName(java.lang.String);          ◀
  public boolean equals(java.lang.Object);        ◀
  protected boolean canEqual(java.lang.Object);
  public int hashCode();                          ◀
  public java.lang.String toString();             ◀
}
$ java Main
넣을 때 hashCode: 109731                          ◀
이름 바꾼 뒤 hashCode: 110560                     ◀
contains: false                                   ◀
size: 1                                           ◀
remove: false                                     ◀
remove 뒤 size: 1
Member(id=1, name=null)                           ◀
```

**E2b** 같은 실험(패키지 `hook`)에 확인 줄을 더 넣었다:

```
넣은 직후 contains: true
넣을 때 hashCode: 109731
이름 바꾼 뒤 hashCode: 110560
이름 바꾼 뒤 contains: false
size: 1
꺼낸 것이 같은 객체인가(==): true
remove: false, remove 뒤 size: 1
이름을 kim으로 되돌린 뒤 contains: true
```

**E3 HashSet의 칸**(실행: `java --add-opens java.base/java.util=ALL-UNNAMED`). 리플렉션으로 `HashSet.map`을 꺼내고, 그 `HashMap.table`을 연다.

```java
static int index(int h, int n) { return (n - 1) & (h ^ (h >>> 16)); }   // HashMap.hash 와 같은 식
// set.add(member) 뒤 table을 열어 null이 아닌 칸 번호를 찍는다. 이름을 lee로 바꾼 뒤 다시 찍는다.
```

```
칸 수(table.length): 16
넣을 때 hashCode 109731 -> 계산한 칸 2
실제로 들어 있는 칸: 2
이름 바꾼 뒤 hashCode 110560 -> contains가 볼 칸 1
실제로 들어 있는 칸(그대로): 2
contains: false
```

**E4 순환 참조**(패키지 `cycle`, 둘 다 `@Data`)

```java
@Data public class Team { private String name; private List<Member> members = new ArrayList<>(); }
@Data public class Member { private String name; private Team team; }
// team.setName("dev"); member.setName("kim"); member.setTeam(team); team.getMembers().add(member);
// member.toString(), member.hashCode(), member.equals(같은 team을 든 다른 Member) 를 각각 try/catch
```

```
toString(): java.lang.StackOverflowError          ◀
hashCode(): java.lang.StackOverflowError          ◀
true
```

- equals가 true인 이유: Lombok equals는 먼저 `o == this`를 보는데, 두 Member가 같은 team 객체를 들고 있어서 team 비교가 바로 true가 됐다. 그래서 equals 오버플로는 주장하지 않는다.
- **E4b** `javap -c -p cycle/Member.class`로 본 내용:
  - hashCode는 `getTeam()` 값에 `java/lang/Object.hashCode`(가상 호출이라 Team.hashCode가 불린다)를 부른다.
  - toString은 `String.valueOf(getTeam())` 다음에 `makeConcatWithConstants`를 부른다.

**E5 Exclude**(패키지 `fixed`)

```java
@Data
public class Team {
    private String name;
    @ToString.Exclude
    @EqualsAndHashCode.Exclude
    private List<Member> members = new ArrayList<>();
}
// FixedDemo: System.out.println(member); System.out.println(team); member.hashCode()
```

```
Member(name=kim, team=Team(name=dev))             ◀
Team(name=dev)
hashCode: 6368158
```

**E6 검사를 넣은 메서드**(기본 패키지)

```java
@Getter
public class Member {
    private Long id;
    private String name;

    public Member(Long id, String name) { this.id = id; this.name = name; }

    public void changeName(String name) {             // ◀ 이하 4줄
        if (name == null || name.isBlank())
            throw new IllegalArgumentException();
        this.name = name;
    }
}
```

```
$ javap -p Member.class
public class Member {
  private java.lang.Long id;
  private java.lang.String name;
  public Member(java.lang.Long, java.lang.String);
  public void changeName(java.lang.String);
  public java.lang.Long getId();
  public java.lang.String getName();
}
$ java Main
changeName("lee") 뒤 name=lee
changeName(null): java.lang.IllegalArgumentException
changeName(" "): java.lang.IllegalArgumentException
그 뒤 name=lee
```

**E7 final 필드**(`@Data class Product { private final Long id; private String name; }`). javap 결과는 `public fin.Product(java.lang.Long);`이고, `setName`은 있지만 `setId`는 없다.

**E8 record**(기본 패키지 `public record MemberDto(Long id, String name) {}`)

```
$ javap -p MemberDto.class
public final class MemberDto extends java.lang.Record {   ◀ (줄바꿈)
  private final java.lang.Long id;                        ◀
  private final java.lang.String name;                    ◀
  public MemberDto(java.lang.Long, java.lang.String);
  public final java.lang.String toString();
  public final int hashCode();
  public final boolean equals(java.lang.Object);
  public java.lang.Long id();
  public java.lang.String name();
}
$ java Main
MemberDto[id=1, name=kim]                                 ◀
name(): kim                                               ◀
contains(dto): true
```

**E9** `dto.setName("lee")`를 컴파일하면 오류가 난다:

```
Check.java:6: error: cannot find symbol
        dto.setName("lee");
  symbol:   method setName(String)
  location: variable dto of type MemberDto
```

**R1 record 순환**(Phase B에서 독립 검증자의 지적을 재현)

```java
record TeamDto(String name, List<Object> members) {}
record MemberDto(String name, TeamDto team) {}
// team = new TeamDto("dev", new ArrayList<>()); member = new MemberDto("kim", team); team.members().add(member);
```

```
record toString(): java.lang.StackOverflowError
record hashCode(): java.lang.StackOverflowError
```

→ record도 순환 참조는 풀어 주지 않는다. record가 푸는 건 "필드를 다시 넣어 hashCode가 바뀌는 문제"뿐이다. 그래서 정리 그림에서 toString → DTO 화살표를 지웠다.

**R2 iterator로는 지워진다**(Phase B 재현). 이름을 바꾼 뒤 `remove: false, size=1`이었고, `iterator.remove 뒤 size=0`이었다.
→ 그래서 "지우지도 못해요"를 "contains도 remove도 안 돼요"로 고쳤다.

**J 실험**: Spring Boot 4.1.2, Hibernate 7.4.13.Final, MySQL 8.4.13. 앱은 `eclipse-temurin:25-jre`에서 `java -jar`로 돌렸다.

```properties
spring.datasource.url=jdbc:mysql://lb11-mysql:3306/lb11
spring.datasource.username=root
spring.datasource.password=
spring.jpa.hibernate.ddl-auto=create
spring.main.web-application-type=none
logging.level.org.hibernate.SQL=debug
```

```java
@Data @Entity
public class Member {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    private String name;
    @ManyToOne(fetch = FetchType.LAZY) private Team team;
}
@Data @Entity
public class Team {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    private String name;
    @OneToMany(mappedBy = "team") private List<Member> members = new ArrayList<>();
}
@Getter @Entity(name = "GoodMember")          // 대조군: @Data 대신 @Getter만, equals/hashCode 없음
public class Member { @Id @GeneratedValue(strategy = IDENTITY) private Long id; private String name;
    protected Member() {} public Member(String name) { this.name = name; } }

// J1 (트랜잭션 없음, save가 자체 트랜잭션)
Member member = new Member(); member.setName("kim");
Set<Member> set = new HashSet<>(); set.add(member);
log("save 전  id=" + member.getId() + ", hashCode=" + member.hashCode());
memberRepository.save(member);
log("save 뒤  id=" + member.getId() + ", hashCode=" + member.hashCode());
log("set.contains(member) = " + set.contains(member));

// J2: @Transactional saveTeamWithMember()로 team(dev)과 member(lee, team) 저장 뒤
@Transactional(readOnly = true)
public void printTeam(Long teamId) {
    Team team = teamRepository.findById(teamId).orElseThrow();
    log("team 읽음. 이제 toString() 호출");
    try { System.out.println(team.toString()); } catch (StackOverflowError e) { log("toString(): " + e); }
}
// J2b: 같은 방식으로 team.getMembers().get(0).hashCode()
// J3 (--spring.profiles.active=record): @Entity public record BookRecord(@Id Long id, String title) {}
//    @Transactional em.persist(new BookRecord(1L, "JPA")); 다음 트랜잭션에서 em.find(BookRecord.class, 1L)
```

```
[앱] Java 25.0.4.1, Spring Boot 4.1.2, Spring Framework 7.0.10, Hibernate 7.4.13.Final
[앱] === J1 @Data 엔티티 + HashSet + save()
[앱] save 전  id=null, hashCode=6620374                         ◀
DEBUG org.hibernate.SQL : insert into member (name,team_id) values (?,?)
[앱] save 뒤  id=1, hashCode=6474172                            ◀
[앱] set.contains(member) = false                               ◀
[앱] set.size() = 1
[앱] === J1-대조 @Getter 엔티티 + HashSet + save()
[앱] [@Getter 엔티티] save 전  id=null, hashCode=363243807       ◀
DEBUG org.hibernate.SQL : insert into good_member (name) values (?)
[앱] [@Getter 엔티티] save 뒤  id=1, hashCode=363243807          ◀
[앱] [@Getter 엔티티] set.contains(member) = true               ◀
[앱] === J2 양방향 @Data 엔티티 toString()
DEBUG org.hibernate.SQL : insert into team (name) values (?)
DEBUG org.hibernate.SQL : insert into member (name,team_id) values (?,?)
DEBUG org.hibernate.SQL : select t1_0.id,t1_0.name from team t1_0 where t1_0.id=?
[앱] team 읽음. 이제 toString() 호출                             ◀
DEBUG org.hibernate.SQL : select m1_0.team_id,m1_0.id,m1_0.name from member m1_0 where m1_0.team_id=?
[앱] toString(): java.lang.StackOverflowError                   ◀ (줄바꿈)
[앱] === J2-b 양방향 @Data 엔티티 hashCode()
DEBUG org.hibernate.SQL : select t1_0.id,t1_0.name from team t1_0 where t1_0.id=?
DEBUG org.hibernate.SQL : select m1_0.team_id,m1_0.id,m1_0.name from member m1_0 where m1_0.team_id=?
[앱] member 읽음. 이제 hashCode() 호출
[앱] hashCode = 791065985

[앱] === J3 record를 @Entity로
[앱] persist(BookRecord) 끝
DEBUG org.hibernate.SQL : insert into book_record (title,id) values (?,?)
DEBUG org.hibernate.SQL : select br1_0.id,br1_0.title from book_record br1_0 where br1_0.id=?
[앱] find 예외: org.hibernate.InstantiationException: No default constructor for entity 'com.example.lb11.bad.BookRecord'   ◀ (자르고 줄바꿈)
```

- J2b가 터지지 않은 이유: `PersistentBag.hashCode()`가 객체 동일성 기준이기 때문이다(H-Bag). 그래서 JPA 장면은 toString만 말한다.
- J3: Hibernate 7.4.13은 record 엔티티를 기동 때 거부하지 않고 INSERT까지 했다. 읽을 때만 실패했다. "못 쓴다"의 근거는 명세 문장(JPA)이고, 이 실험은 "실제로 읽어 오면"의 근거다.
- J1·J2 실행 때 `com.example.lb11.bad` 패키지가 기본 스캔에 들어가 `book_record` 테이블도 만들어졌다. J1·J2 결과와는 상관없다.

### 문장·화면 줄별 근거

표기는 N = 나레이션, B = 코드 박스 줄, D = 다이어그램 라벨이다. "결론"은 공식 권장이 아니라, 위 출처와 실험에서 내가 낸 결론이라는 뜻이다.

| 장면 | 문장·화면 | 근거 |
|---|---|---|
| S01 0:00 Member.java | N "@Data 한 줄이면, getter, setter, equals, toString까지 생겨요." | L-Data, E1 javap |
| | B `@Data` 클래스 5줄 | E1 Member.java 그대로(import 생략) |
| S02 0:06 Main.java | N "그런데 이걸 HashSet에 넣고, 이름을 바꾸면," | E2 코드 |
| | N "분명 하나 들어 있는데, contains도 remove도 안 돼요." | E2 `contains: false`, `size: 1`, `remove: false` / E2b `꺼낸 것이 같은 객체인가(==): true` |
| | B `set.add(member); // name=kim`, `member.setName("lee");` | E2 코드(주석은 내 설명) |
| | B `# 실행 결과` / `contains: false` / `size: 1` / `remove: false` | E2 출력 그대로 |
| S03 0:14 Data.java | N "@Data는 Lombok 어노테이션 다섯 개를 하나로 묶은 거예요." | L-Data, L-DataJava |
| | N "getter는 모든 필드에, setter는 final이 아닌 필드에 만들고," | L-Data "getters for all fields, setters for all non-final fields", E7 |
| | N "toString, equals와 hashCode, 필수 필드를 받는 생성자도 만들어요." | L-Data, L-RAC("required args" = 초기값 없는 final + @NonNull) |
| | D `@Getter / 모든 필드`, `@Setter / final 아닌 필드`, `@ToString`, `@EqualsAndHashCode`, `@RequiredArgsConstructor / 초기값 없는 final·@NonNull 필드` | 위와 같다 |
| S04 0:27 javap -p Member | N "javap로 열어 보면, 이 메서드들이 실제로 들어 있어요." | E1 |
| | N "생성자는 받을 필수 필드가 없어서, 인자가 없어요." | E1 `public Member();`, L-RAC(Member엔 final·@NonNull 필드가 없음) |
| | B javap 5줄 | E1 출력에서 앞 공백 2칸만 뺐다 |
| | B `# getId, getName, setId 등은 생략` | 내 설명(`canEqual`도 생략) |
| S05 0:36 Main.java | N "setter는 public이라, 어디서든 값을 바꿀 수 있어요." | L-Data "All generated getters and setters will be public.", E1 |
| | N "이름에 null을 넣어도, 막아 줄 곳이 없어요." | E2 `Member(id=1, name=null)` |
| | B `// 어느 클래스에서든 호출 가능` / `member.setName(null);` / `System.out.println(member);` / `# 실행 결과` / `Member(id=1, name=null)` | E2 코드와 출력(주석은 내 설명) |
| S06 0:44 Member.java | N "그래서 getter만 열고, 값은 검사를 넣은 메서드 한 곳에서만 바꾸게 해요." | **결론.** E2(검사 없는 setter), E6(changeName이 null·공백을 막음, setter 없음) |
| | B `// 클래스엔 @Getter만` + changeName 4줄 | E6 코드(들여쓰기만 줄임, 닫는 괄호 생략) |
| S07 0:50 Main.java | N "@Data의 hashCode는 모든 필드로 계산해서, 이름이 바뀌면 hashCode도 바뀌어요." | L-EHC "all non-static, non-transient fields", E2 |
| | B `# 실행 결과 (id=1)` / `넣을 때 hashCode: 109731` / `이름 바꾼 뒤 hashCode: 110560` | E2 출력 |
| S08 0:56 HashSet | N "HashSet은 넣을 때의 hashCode로 칸을 정해서 넣고," | J-HS, J-HMsrc(add→put→`hash()`→`tab[(n-1)&hash]`, `Node.hash` 저장) |
| | N "찾을 땐 지금 hashCode로 칸을 다시 계산해요." | J-HMsrc(contains→containsKey→getNode가 `hash(key)` 새로 계산) |
| | N "그래서 빈 칸을 보고, 없다고 답해요." | E3(칸 1은 비어 있고 원소는 칸 2), J-HMsrc getNode null → false. 일반 근거 J-Set, J-Obj |
| | D `HashSet: 칸 16개`, `넣을 때 / hashCode 109731`, `찾을 때 / hashCode 110560`, `칸 2 / Member 있음`, `칸 1 / 비어 있음`, `contains → false` | E3 출력 |
| S09 1:06 call-stack.txt | N "@Data의 toString과 hashCode는, 필드 객체의 것까지 불러요." | E4b 바이트코드, L-TS 형식 |
| | N "Member가 Team을, Team이 다시 Member 목록을 들고 있으면, 서로를 끝없이 불러요." | E4, J-AC, J-List |
| | D `member.toString()` → `team.toString()` → `members.toString()` → `member.toString() / 처음과 같은 객체` → `…` | E4 구조(member를 team.members에 넣음), J-AC |
| S10 1:16 run.log | N "결국 호출이 계속 쌓이다가, StackOverflowError가 나요." | E4, J-SOE |
| | B `# Member, Team 둘 다 @Data` / `toString():` `java.lang.StackOverflowError` / `hashCode():` `java.lang.StackOverflowError` | E4 출력(콜론 뒤 줄바꿈) |
| S11 1:21 Team.java | N "그래서 한쪽 필드에 Exclude를 붙여, 출력과 비교에서 빼요." | L-TS, L-EHC, E5 |
| | B Exclude 2줄 + 필드 2줄 / `# println(member)` / `Member(name=kim, team=Team(name=dev))` | E5 코드(한 줄을 둘로)와 출력 |
| S12 1:27 jpa.log | N "JPA 엔티티의 id를 DB가 만들게 하면, save 전엔 null이다가 저장하면 값이 생겨요." | J1(IDENTITY), H-Intro "the identifier is not generated until the entity instance is made persistent" |
| | N "그래서 저장 전에 HashSet에 넣었다면, 저장 뒤엔 못 찾아요." | J1 `set.contains(member) = false`, H-UG |
| | B `# @Data @Entity, id는 DB가 만듦` / `# set.add(member) 뒤 save(member)` | 내 설명(J1 코드) |
| | B `save 전  id=null, hashCode=6620374` / `save 뒤  id=1, hashCode=6474172` / `set.contains(member) = false` | J1 로그(`[앱] ` 자름) |
| S13 1:37 jpa.log | N "양방향 @Data 엔티티는, 트랜잭션 안에서 toString 한 번에 StackOverflowError가 나요." | J2(`@Transactional(readOnly = true)` 안) |
| | B `# 트랜잭션 안, 양방향, 둘 다 @Data` / `team 읽음. 이제 toString() 호출` / `toString():` `java.lang.StackOverflowError` | J2 로그(머리표 자름, 줄바꿈, members SELECT 줄 생략) |
| S14 1:42 hashCode.txt | N "Hibernate 문서도, 바뀌는 필드와 DB가 만드는 필드는 hashCode에 넣지 말라고 해요." | H-Intro "should not include a mutable field" / "advise against including any database-generated field" |
| | D `@Data 엔티티의 hashCode` 안에 `id / DB가 만드는 필드`, `name / 바뀌는 필드` → `Hibernate 문서: 둘 다 넣지 말 것` | L-EHC, J1, E2, H-Intro |
| S15 1:48 Member.java | N "그래서 엔티티엔 @Data 대신, @Getter처럼 필요한 것만 붙여요." | **결론.** J1, J2, J1b, H-UG "consider not implementing equals/hashCode altogether" |
| | N "equals와 hashCode를 안 만들면 같은 객체인지만 봐서, id가 생겨도 그대로예요." | J-Obj equals, J1b hashCode 같음·contains true, H-UG(세션 안에선 같은 행 = 같은 객체) |
| | N "Set으로 담는 연관관계라면, 안 바뀌는 값으로 직접 만들고요." | H-Intro "Entity classes should override equals() and hashCode(), especially when associations are represented as sets." / "It's OK to include any immutable, non-generated field" / "recommend identifying a natural key" |
| | B `@Getter @Entity  // @Data 대신` / `# 같은 실험` / save 전·뒤 / `set.contains(member) = true` | J1b 코드(`@Entity`의 name 속성 생략), 로그(머리표 자름) |
| S16 2:04 MemberDto.java | N "값만 담는 DTO라면, Java 16부터 있는 record가 맞아요." | **결론** + J-Rec "transparent carrier for a fixed set of values", "Since: 16" |
| | N "생성자와 name() 같은 접근자, equals, hashCode, toString을 언어가 만들어 줘요." | JLS §8.10.3·§8.10.4, E8 |
| | B `public record MemberDto(` / `Long id, String name) {}` / `# 실행 결과` / `MemberDto[id=1, name=kim]` / `name(): kim` | E8 코드(줄바꿈)와 출력 |
| S17 2:15 javap -p MemberDto | N "필드가 final이라 setter가 없고, 값을 다시 넣을 수도 없어요." | JLS "A component field is private, final, and non-static.", E8, E9 |
| | N "그래서 이 MemberDto는, HashSet에 넣은 뒤에도 hashCode가 그대로예요." | JLS hashCode는 컴포넌트 값에서 계산, 컴포넌트가 Long·String(불변). E8 `contains(dto): true`. "이 MemberDto는"으로 한정한 이유는 R1(가변 컴포넌트) |
| | B javap 4줄 + `# set으로 시작하는 메서드는 없음` | E8 출력(첫 줄 줄바꿈, 앞 공백 제거), 메서드 목록 |
| S18 2:24 spec.txt | N "단, JPA 명세는 record를 엔티티로 쓸 수 없다고 정해 뒀어요." | JPA "An enum, record, or interface may not be designated as an entity." |
| | N "실제로 Hibernate로 읽어 오면, 기본 생성자가 없다는 예외가 나요." | J3, JLS §8.10.4(record엔 기본 생성자가 암묵적으로 없음) |
| | B `# Jakarta Persistence 3.2, 2.1절` + 원문 2줄 / `# @Entity record, em.find로 읽으면` / `org.hibernate.InstantiationException:` / ` No default constructor for entity` | JPA 원문(줄바꿈), J3 로그(앞 `find 예외: `와 뒤 엔티티 이름을 자르고 줄바꿈) |
| S19 2:34 summary.md | N "정리하면, @Data는 한 줄로 여러 메서드를 만들어 줘서 편하지만," | L-Data, E1 |
| | N "바뀌는 필드로 hashCode를 만들고, 연결된 객체까지 따라가 출력해요." | L-EHC, E2, J1 / E4b, E4, J2 |
| | N "그래서 엔티티엔 필요한 것만 고르고, DTO는 record로 만들어요." | S15, S16의 결론 |
| | D `@Data / getter·setter·equals·hashCode·toString` → `hashCode / 바뀌는 필드로 계산`, `toString / 연결된 객체까지`; 아랫줄 `엔티티 / @Getter 등 필요한 것만`, `DTO / record`(화살표 없음) | 위와 같다. 아랫줄 화살표를 지운 이유는 R1 |
| 썸네일 | `# HashSet에 넣었는데 못 찾는다` / `@Data, 왜 조심해서 써야 할까?` | E2, 영상 질문 |

### 예시로 정한 값

- Member(id 1, kim → lee), Team(dev), MemberDto(1, kim)는 예시 값이다. 화면의 hashCode, 칸 번호, id 같은 숫자는 모두 이 예시로 실제로 돌린 결과다.
- 칸 번호 2와 1은 기본 용량(16칸) HashSet에 이 hashCode가 들어갈 때만 맞는 값이다.
- JPA 실험의 hashCode 값(6620374, 6474172, 363243807)은 실행마다 다를 수 있다. 대본은 "바뀌는지, 그대로인지"만 말한다.

### 독립 사실 확인 반영 기록

Phase A 초안 뒤 독립 검증자가 결과를 냈다. 틀림 0, 오해 소지 2, 사소 6이었다. 검증자도 Docker로 다시 실험했고, HashSet, Exclude, JPA @Data·@Getter 엔티티, record javap·출력이 모두 내 로그와 같았다.

| # | 지적 | 전 | 후 | 근거 |
|---|---|---|---|---|
| 1 | [오해 소지] 정리 그림의 `toString → DTO(record)` 화살표가 "record가 순환을 풀어 준다"로 읽힌다 | 화살표 `hc→ent`, `ts→dto` | 아랫줄로 가는 화살표를 모두 지웠다(`data→hc`, `data→ts`만 남김). 나레이션엔 그런 주장이 없음을 확인했다 | R1 재현: record 순환도 toString·hashCode가 StackOverflowError |
| 2 | [오해 소지] S15 끝 문장이 바로 앞 "Hibernate 문서도"(Introduction)와 어긋난다(Introduction은 만드는 쪽이 기본) | "equals와 hashCode가 꼭 필요하면, 바뀌지 않는 값으로 직접 만들고요." | "Set으로 담는 연관관계라면, 안 바뀌는 값으로 직접 만들고요." | H-Intro §3.26 "should override … especially when associations are represented as sets", H-UG §3.4.7 "consider not implementing" |
| 3 | S18이 final을 이유로 들었는데, 명세엔 record를 직접 막는 문장이 있고 Hibernate는 final 클래스도 저장한다 | "단, record는 JPA 엔티티로는 못 써요." / "JPA 명세가 엔티티는 final이면 안 된다고 정했는데, record는 항상 final이거든요." / 화면에 "must be non-final"과 JLS "implicitly final" | "단, JPA 명세는 record를 엔티티로 쓸 수 없다고 정해 뒀어요." / "실제로 Hibernate로 읽어 오면, 기본 생성자가 없다는 예외가 나요." / 화면에 "An enum, record, or interface may not be designated as an entity."와 J3 예외 | JPA §2.1, H-UG §3.4.1, J3 |
| 4 | S13 toString 오버플로는 트랜잭션 안에서만 그렇다(밖이면 LazyInitializationException) | "양방향으로 서로를 든 @Data 엔티티라면, toString 한 번에 StackOverflowError가 나요." / 주석 `# Team, Member 양방향, 둘 다 @Data` | "양방향 @Data 엔티티는, 트랜잭션 안에서 toString 한 번에 StackOverflowError가 나요." / 주석 `# 트랜잭션 안, 양방향, 둘 다 @Data` | J2(readOnly 트랜잭션 안). 트랜잭션 밖 결과는 검증자 재현이고 나는 다시 돌리지 않았다 |
| 5 | S09 주어가 빠졌다(Object 기본 toString은 필드를 부르지 않음) | "toString과 hashCode는, 필드에 든 객체의 toString과 hashCode까지 불러요." | "@Data의 toString과 hashCode는, 필드 객체의 것까지 불러요." | E4b, J-Obj |
| 6 | S03 생성자 설명이 부정확하고, S04의 인자 없는 `public Member();`가 헷갈린다 | N "…final 필드를 받는 생성자도 만들어요." / D sub "final 필드를 받는 생성자" | N "…필수 필드를 받는 생성자도 만들어요." / D sub "초기값 없는 final·@NonNull 필드" / S04에 문장 추가 "생성자는 받을 필수 필드가 없어서, 인자가 없어요." | L-RAC, E1, E7 |
| 7 | S02 "지우지도 못해요"는 iterator로는 지울 수 있어서 과장이다 | "분명 하나 들어 있는데, contains는 false고, 지우지도 못해요." | "분명 하나 들어 있는데, contains도 remove도 안 돼요." | E2 `remove: false`, R2 `iterator.remove 뒤 size=0` |
| 8 | S12 "1이 돼요"는 빈 테이블의 첫 행일 때만 맞다 | "…save 전엔 null이다가 저장하면 1이 돼요." | "…save 전엔 null이다가 저장하면 값이 생겨요." (화면 id=1은 실제 로그라 그대로) | J1 |

### 그 밖의 결정

- **길이 맞추기:** 3번(S18) 고치기와 4번(S13) 조건 붙이기로 문장이 길어졌고, S04에 문장이 하나 늘었다. film 170초 아래를 지키려고 '왜'가 아닌 표현을 줄였다.
  - "그래서 엉뚱한 빈 칸을 보고, 없다고 답하는 거예요." → "그래서 빈 칸을 보고, 없다고 답해요."
  - "값만 담아 옮기는 DTO라면" → "값만 담는 DTO라면"
  - "…toString을 Lombok 없이 언어가 만들어 줘요." → "…toString을 언어가 만들어 줘요."
  - "정리하면, @Data는 여러 메서드를 한 번에 만들어 줘서 편하지만," → "정리하면, @Data는 한 줄로 여러 메서드를 만들어 줘서 편하지만,"
- **타이핑 속도(`chars/s`) 경고 없애기:**
  - S04는 문장이 둘이 돼서 타이핑 시간이 늘었다.
  - S06은 주석을 "// 클래스엔 @Getter만"으로 줄이고 닫는 `}`를 뺐으며, hold를 1.1초로 늘렸다.
  - S10은 hold 0.4초를 줬다.
  - S11은 주석을 `# println(member)`로 줄이고 hold를 1.35초로 늘렸다.
  - S12는 주석 3줄을 2줄로 합쳤다(MySQL 8.4 표기는 REVIEW에만 남김).
- **HashSet 그림:** 처음엔 "HashSet (칸 16개)"를 틀 이름표로 썼는데, 넣을 때 화살표가 이름표 글자 위를 지나갔다(snapshot에서 확인). 그래서 틀을 없애고 맨 윗줄 글자 "HashSet: 칸 16개"로 바꿨다.
- **긴 줄 박스:** S06 setter 대처 코드(41칸)와 S04 javap(40칸) 박스는 글자가 약 44–45px로 작아진다. 원본 크기 프레임(1080x1920)에서 읽히는 것을 확인했다.
- **Lombok 버전:** spring-boot-dependencies 4.1.2 BOM의 `lombok.version` 값인 1.18.48을 썼다.

## 측정한 것 / 보기만 한 것

- 길이: film 169.62초(`tts.py`: narration 168.02초). MP4는 169.633초, 1080x1920, 30 fps이고 3분 미만이다. 35문장, 19장면.
- 통합 음량 -14.0 LUFS, 피크 -1.5 dBFS. 기준(-13 ~ -15 LUFS, 피크 -1 dBFS 이하) 안이다.
- check 결과는 `0 error(s), 26 warning(s)`이고 `◇ Check passed`다. 경고는 26건 모두 `line_unread`다.
- `build.py`: 마지막 빌드에서 `font down to`, `chars/s`, `diagram text down to` 경고가 없었다.
- `thumbnail.py`: 제목 190px, 경고 없음.
- 눈으로 본 것: 0초와 장면마다 가운데·끝, 모두 39개 시점을 snapshot으로 찍었다. 바꾼 HashSet 그림과 S06·S04 박스, 렌더된 MP4의 0초·152초 프레임도 원본 크기로 봤다.
  - 0초 프레임에 첫 박스(`@Data Member`)와 첫 자막이 있다.
  - 자막은 2줄 안이고, 기술 용어는 영어로 나온다.
  - 썸네일 제목 "@Data, / 왜 조심해서 / 써야 할까?"가 크게 읽힌다.
- 직접 들어 봐야 할 곳:
  - 0:00 "@Data" → "앳데이터". 개발자들은 "데이터 어노테이션"이라고도 말한다.
  - 0:10 "contains도 remove도" → "컨테인스도 리무브도"
  - 0:27 "javap" → "자바피"
  - 1:16·1:37 "StackOverflowError" → "스택오버플로에러"
  - 1:27 say 문장: "제이피에이 엔티티의 아이디를 디비가…"
  - 1:48 "@Getter" → "앳게터"
  - 2:04 "Java 16" → 숫자 읽기 "십육"
  - 2:08 "name()" → "네임"
  - 2:19 "MemberDto" → "멤버디티오"
  - 2:29 "Hibernate" → "하이버네이트"

## 일부러 남긴 경고

- `line_unread` 26건. 글자마다 `<span>`으로 감싸서 단어 수가 부풀려 세어지는 경고다(예: `"c o n t a i n s : f a l s e" (13 words)`).
- 이전 편보다 많다(인덱스 편 10건, B-tree 편 2건). 이 편엔 코드·로그 박스가 14장면이라 줄이 많다. 경고가 난 줄은 화면에 1.56–6.69초 있다.

## 가장 약한 부분

- **엔티티 대처의 권장(S15)은 공식 권장 하나로 정리되지 않는다.** Hibernate Introduction은 "Set 연관관계면 equals/hashCode를 자연 키로 만들라"고 하고, User Guide는 "안 만드는 것도 고려하라"고 한다. 대본은 두 경우를 나눠 말했다. 하지만 "@Getter처럼 필요한 것만"은 실험과 문서에서 낸 결론이고, 공식 문장이 아니다.
- **S13은 트랜잭션 안의 결과만 직접 확인했다.** 트랜잭션 밖의 `LazyInitializationException`은 검증자 결과로만 알고 있다. 영상에선 지연 로딩을 설명하지 않아서, toString이 왜 members까지 읽는지는 보여 주지 않는다.
- **"모든 필드"(S03, S07)는 문서 표현을 따른 단순화다.** 정확히는 static 필드는 전부 빠지고, transient 필드는 equals/hashCode에서 빠진다.
- **record는 "shallowly immutable"이다.** S17은 "이 MemberDto는"으로 한정했지만, 시청자가 "record면 언제나 hashCode가 안 바뀐다"로 일반화할 수 있다. List 같은 가변 컴포넌트를 가진 record는 내용이 바뀐다(R1).
- **코드 박스가 많다.** 19장면 중 14장면이 박스다. 다이어그램은 5장면이다(Data.java, HashSet, call-stack, hashCode.txt, summary). 박스는 대부분 실행 결과가 증거인 곳이지만, 문서 인용(S18)도 박스로 뒀다.
