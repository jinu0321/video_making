# REVIEW

## 시청 후 답할 수 있는 것

질문: **"Java Spring 백엔드"라고 하면, 요청 하나가 어떤 기술들을 지나가고, 각각 무슨 일을 하나요?**

이 편은 **넓게 훑기 편**이다. 사용자가 "커버 범위가 너무 넓으니 상세하게 갈 필요 없이, 넓게 슥 훑어보는 느낌으로"를 요청했다.
그래서 스킬의 "좁게 잡고 깊게" 원칙 대신, 층마다 "무엇 + 하는 일(왜 있나) 한 줄"을 답안 단위로 잡았다. 이름만 대고 지나간 항목은 박스에만 두었다(아래 "내린 결정").
영상도 시작에서 "깊게 들어가진 않고, 전체를 한 번 쭉 훑어보는 게 목적"이라고 밝힌다(0:00, 사용자 요청).

답안(괄호는 영상 속 위치):

1. **언어와 런타임.** Java든 Kotlin이든 JVM이 읽는 바이트코드로 컴파일된다. 그래서 한 프로젝트에 섞어 써도 된다. (0:14 build.txt)
2. **빌드.** Gradle이 라이브러리를 받아 jar 하나로 묶는다. (0:22 gradlew bootJar)
3. **Spring.** 객체를 직접 new 하지 않아도 Spring이 만들어서 필요한 곳에 넣어 준다. 이 객체가 Bean이고, 넣어 주는 게 DI(의존성 주입)다. (0:27 ItemService.java)
4. **Spring Boot.** starter 하나로 라이브러리와 기본 설정을 같이 가져온다. Tomcat이 jar 안에 있어서 웹 서버를 따로 설치하지 않는다. (0:37 build.gradle)
5. **웹 계층.** Tomcat이 요청을 받고, 필터(로그인 검사)를 지나, DispatcherServlet이 맞는 컨트롤러로 넘긴다. 컨트롤러에서 서비스, 리포지토리 순으로 일이 넘어가고, 돌려준 객체는 Jackson이 JSON으로 바꾼다. (0:47 request.log, 0:54 ItemController.java)
6. **데이터 계층.**
   - Spring Data JPA는 인터페이스만 만들면 메서드 이름을 보고 쿼리를 만든다.
   - 복잡한 조회는 JPQL로 쓰는데, 테이블이 아니라 엔티티 클래스를 대상으로 쓴다.
   - JPA(표준) 일은 Hibernate(구현체)가 한다. Hibernate가 만든 SQL은 JDBC(표준)를 거쳐 MySQL 드라이버(구현체)가 DB로 보낸다.
   - 연결은 맺는 데 오래 걸리므로, HikariCP가 미리 열어 둔 연결을 빌려 쓴다.
   - `@Transactional`을 붙이면 Spring이 트랜잭션을 열고 커밋하고, 예외가 나면 롤백한다.
   (1:03–1:51)
7. **표준과 구현체의 짝.** JPA와 Hibernate, JDBC와 MySQL Driver, Servlet과 Tomcat처럼 짝인 곳이 많다. 코드는 표준에만 기대므로 구현체를 바꿔도 코드는 거의 그대로다. (1:33 pairs.txt)
8. **S3.** 파일을 DB에 넣으면 DB가 무거워지므로, 파일은 S3에 두고 DB에는 위치(키)만 적는다. 업로드는 Presigned URL로 브라우저가 S3에 바로 올린다. 그래서 서버가 큰 파일을 나르지 않는다. (1:51 upload.md)
9. **보안, 배포, 운영.**
   - Spring Security가 컨트롤러 앞의 필터에서 토큰을 확인한다.
   - GitHub Actions가 테스트하고 Docker 이미지로 묶으면, ECS나 EC2에서 띄우고 ALB가 요청을 나눈다.
   - DB는 RDS, 캐시는 ElastiCache를 써서 백업과 장애 대비를 AWS에 맡긴다.
   - 운영 중에는 Actuator로 상태를 보고, Prometheus와 Grafana로 지표를 본다.
   (2:02–2:30)

기억할 한 문장: "Spring Boot가 Tomcat으로 요청을 받아, JPA와 JDBC로 MySQL에, AWS SDK로 S3에 닿는다. 이름은 많아도 상당수는 표준과 구현체의 짝이다." (2:30 summary.md)
영상은 그 뒤에 "정말 넓은 Java 백엔드 세상이네요. 공부할 게 많아서 행복해요."로 끝난다(사용자 요청).

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
S="java_spring_백엔드_기술_스택_한_번에_훑기"
npx --yes hyperframes@0.8.209 render -o "output/$S.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/$S.mp4"
ffmpeg -nostats -i "output/$S.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
화면은 장면마다 `blocks`(코드 박스) 또는 `diagram`(상자와 화살표) 중 하나다. 다이어그램 쓰는 법은 스킬의 `references/content-guide.md` "다이어그램 장면" 절에 있다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 범위

- 바탕은 직전 대화에서 정리한 실무 기준 목차(Part A–D, 21개 절)다. 사용자가 "넓게 슥 훑기"를 원했으므로 깊이보다 범위를 우선했다. 그래도 3분 안에 들어가도록, 요청 하나가 지나가는 길(웹, 데이터, S3)에 시간을 몰고 보안·배포·운영은 한두 문장으로 지나갔다.
- 영상 전체를 묶는 '왜'는 첨부 이미지의 핵심인 **표준과 구현체의 짝**으로 잡았다. "이름이 왜 이렇게 많은가"에 대한 답이 되기 때문이다(1:33, 2:30).
- **이름만 화면에 둔 것**(나레이션에서 설명하지 않음): ECR, SLF4J/Logback, Lombok `@RequiredArgsConstructor`, Spring MVC.
  BCrypt, CloudFront, Micrometer는 3차에서 다이어그램으로 바꾸며 화면에서도 빠졌다.
- **뺀 것**: Redis 캐시와 `@Cacheable`, Kafka·SQS 메시징, Spring Batch, 입력 검증(Bean Validation), 예외 처리(`@RestControllerAdvice`), Flyway 마이그레이션, Querydsl, 테스트(JUnit, Testcontainers), API 문서(springdoc, REST Docs), IaC, 블루·그린 배포, MSA.
- 길이(1차): 첫 대본은 38문장, film 211.8 s였다. 연결 문장을 빼고 문장을 합쳐 33문장, 168.1 s가 됐다.
  이 과정에서 "크게 여섯 덩어리예요" 장면은 지도 박스를 칠 시간이 모자라서(49 chars/s 경고) 인트로 둘째 문장과 합쳤다.
- 다음 영상 후보는 `z_영상주제들/spring_백엔드_스택_학습주제.md`와 `spring_db_연결_흐름_학습주제.md`(4번 후보 표시)에 옮겼다:
  - JPA와 Hibernate는 뭐가 다를까
  - Spring Bean과 DI는 왜 쓸까
  - `@Transactional`은 어떻게 동작할까
  - 커넥션 풀은 왜 필요할까
  - S3 업로드는 서버를 거칠까, Presigned URL로 할까
  - 세션과 JWT 중 무엇으로 할까
  - N+1 문제

### 2차 수정 (2026-10-29, 사용자 요청)

| 위치 | 바뀐 것 |
|---|---|
| 0:05 (새 문장) | 채용 공고 뒤에 "깊게 들어가진 않고, 전체를 한 번 쭉 훑어보는 게 목적이에요."를 넣었다. |
| 0:10 map.md | "요청 하나가 지나가는 길을 따라, 이 여섯 층을 쭉 훑어볼게요" → "요청이 지나가는 길을 따라, 여섯 층을 차례로 볼게요". 바로 앞 새 문장과 "쭉 훑어"가 겹쳐서 바꿨다. |
| 2:30 끝 (새 문장) | "정말 넓은 Java 백엔드 세상이네요. 공부할 게 많아서 행복해요."를 넣었다. 박스는 바꾸지 않았다. 화면이 나레이션을 그대로 반복하지 않게 하려는 것이다. |

두 문장을 넣으니 film이 178.0 s가 되었다. 그래서 다른 문장을 줄여 169.9 s로 맞췄다. 줄인 문장에서도 '왜'는 남겼다.

- 0:00 "이 한 마디 뒤엔" → "그 뒤엔"
- 0:27 "그 위가 Spring이에요. 객체를 직접 new 하지 않고, Spring이 만들어 넣어 줘요." → "Spring은 객체를 직접 new 하지 않아도, 만들어서 필요한 곳에 넣어 줘요."
- 0:37 "필요한 라이브러리와" → "라이브러리와"
- 1:03 "DB 쪽은 Spring Data JPA예요. 인터페이스만 만들면, 구현은 알아서 생겨요." → "Spring Data JPA는 인터페이스만 만들면, 구현이 알아서 생겨요."
- 1:33 "이렇게 표준과 구현체가 짝인 곳이 많아요. Tomcat도 Servlet 표준의 구현체예요." → "Tomcat도 Servlet 표준의 구현체예요. 이런 짝이 아주 많아요."
- 1:43 "서비스에 @Transactional을" → "@Transactional을". 박스 코드가 서비스 메서드를 보여 준다.
- 2:08 "나눠 줘요" → "나눠요"
- 2:18 두 문장을 한 문장으로 합쳤다: "DB는 RDS, 캐시는 ElastiCache를 써서, 백업과 장애 대비를 AWS에 맡겨요." 박스 두 덩어리도 하나로 합쳤다.
- 2:24 "지표를 그래프로 봐요" → "지표를 봐요"

Spring Boot 장면(0:37)의 박스 순서도 바꿨다. 문장이 짧아져서 첫 덩어리의 타이핑이 33 chars/s로 빨라졌기 때문이다.

- 첫 줄 `// build.gradle (Boot 3 기준)`을 `// Boot 3 기준`으로 줄였다. 파일 이름은 제목줄에 이미 나온다.
- `data-jpa → Hibernate + HikariCP`를 먼저 보여 주고, `web → Spring MVC + Tomcat`은 Tomcat을 말하는 둘째 문장에서 친다.

### 3차 수정 (2026-10-29, 사용자 요청): 흐름·구조 장면을 다이어그램으로

사용자가 업로드 뒤에 "다루는 내용이 많아서 잘 이해가 안 된다. 글자 말고 다이어그램이면 더 쉬울 것 같다"고 했다.
`build.py`에 다이어그램 장면(`diagram`)을 새로 만들어 스킬 템플릿에 넣고, 이 영상의 20장면 중 12장면을 바꿨다.
나레이션은 한 글자도 바꾸지 않았다. 그래서 `tts.py`는 다시 돌리지 않았고 길이와 소리는 2차와 같다.

- 바꾼 장면: 지도(0:10), 언어와 런타임(0:14), 요청 경로(0:47), 계층(0:54), JPA 흐름(1:17), 표준과 구현체(1:33), S3(1:51), 보안(2:02), 배포(2:08), AWS(2:18), 운영(2:24), 정리(2:30).
- 둔 장면: 채용 공고, `gradlew bootJar`, DI 코드, `build.gradle`, `ItemRepository`, JPQL, `application.yml`, `@Transactional` 코드. 코드·설정·명령 자체가 예시인 장면이다.
- 상자는 나레이션이 그 이름을 말하는 순간 나타난다. 지금 말하는 것 하나만 민트 테두리이고, 다음 것이 나오면 원래 색으로 돌아간다.
- 표준은 노란 점선, 구현체는 분홍 테두리로 그렸다. JPA 흐름(1:17)에서는 표준 틀 안에 구현체를 넣었다. 표준과 구현체 장면(1:33)은 두 열로 그렸다.
- 그리면서 내용이 바뀐 곳:
  - 계층(0:54): 컨트롤러 코드 대신 `ItemController → ItemService → ItemRepository → MySQL`과, 위로 `Jackson → {"id":42,...}`를 그렸다.
  - 보안(2:02): 0:47의 요청 경로를 다시 보여 주고, 그 안의 필터를 `Spring Security`로 바꿔 강조했다. BCrypt 줄은 뺐다.
  - 배포(2:08): 예전 박스는 `→ ECS, EC2 → ALB`로 ALB가 맨 뒤에 있었다. ALB가 앞에서 요청을 나눠 주는 그림(ALB → 서버 1, 서버 2)으로 고쳤다. 서버 두 대는 예시다.
  - AWS(2:18): `Spring Boot 앱`이 AWS 틀 안의 RDS와 ElastiCache를 쓰는 그림. CloudFront 줄은 뺐다.
  - 운영(2:24): `Spring Boot 앱(Actuator) → Prometheus → Grafana`. curl 명령, SLF4J와 Micrometer 줄은 뺐다.
  - S3(1:51): 브라우저 → S3(파일), 서버 → 브라우저(Presigned URL), 서버 → MySQL(image_key).

### 쓴 사실과 출처 (2026-10-29 확인)

| 영상 속 내용 | 출처 |
|---|---|
| `spring-boot-starter-web`은 Spring MVC로 웹 앱을 만드는 starter이고, 기본 내장 서버는 Tomcat | docs.spring.io/spring-boot/reference/using/build-systems.html. 원문: "Starter for building web, including RESTful, applications using Spring MVC. Uses Tomcat as the default embedded container" |
| Boot 4에서 `spring-boot-starter-web`은 `-webmvc`로 대체 예정(deprecated) | github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide. 원문: "The older starters remain, but should be considered deprecated". 그래서 박스에 "Boot 3 기준"을 붙였다 |
| `spring-boot-starter-data-jpa` = Spring Data JPA + Hibernate, HikariCP 자동 포함 | docs.spring.io/spring-boot/reference/data/sql.html. 원문: "We prefer HikariCP for its performance and concurrency." / "If you use the spring-boot-starter-jdbc or spring-boot-starter-data-jpa starters, you automatically get a dependency to HikariCP." |
| HikariCP `maximumPoolSize` 기본 10 | github.com/brettwooldridge/HikariCP README. 원문: "Default: 10" |
| 메서드 이름에서 쿼리를 만든다 | docs.spring.io/spring-data/jpa/reference/repositories/query-methods-details.html. 원문: "By deriving the query from the method name directly." |
| JPQL은 테이블이 아니라 엔티티 대상 | Hibernate Query Language 가이드(docs.hibernate.org, 7.4). 원문: "We're not permitted to directly reference database tables and columns in HQL or JPQL." |
| `@Transactional`은 RuntimeException과 Error에서 롤백하고, 체크 예외에서는 롤백하지 않는다 | docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html. 원문: "Checked exceptions that are thrown from a transactional method do not result in a rollback in the default configuration." |
| Presigned URL이 있으면 자격 증명 없이 업로드할 수 있다 | docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html. 원문: "Using a presigned URL will allow an upload without requiring another party to have AWS security credentials or permissions." |
| Spring Security는 서블릿 필터 기반 | docs.spring.io/spring-security/reference/servlet/architecture.html. 원문: "Spring Security's Servlet support is based on Servlet Filters" |
| Boot는 기본으로 Logback | docs.spring.io/spring-boot/reference/features/logging.html. 원문: "By default, if you use the starters, Logback is used for logging." |
| `/actuator/health`, `/actuator/prometheus` | docs.spring.io/spring-boot/reference/actuator/endpoints.html, …/actuator/metrics.html. 단, 기본으로는 health만 HTTP로 열리고 prometheus는 `micrometer-registry-prometheus` 의존성과 노출 설정이 필요하다 |
| `:min` 같은 이름 파라미터가 `@Param` 없이 동작하는 이유(`-parameters`) | docs.spring.io/spring-boot/gradle-plugin/reacting.html. 원문: "Configures any JavaCompile tasks to use the -parameters compiler argument." |
| Kotlin과 Java를 섞어 쓴다 | kotlinlang.org/docs/java-interop.html. 원문: "Existing Java code can be called from Kotlin in a natural way, and Kotlin code can be used from Java rather smoothly as well." "바이트코드로 컴파일된다"는 이 페이지에 없다. 일반 지식으로 썼다 |

출처 페이지를 따로 열어 보지 않고 일반 지식으로 쓴 것: SLF4J와 Logback, DataSource와 HikariCP, Servlet과 Tomcat의 표준·구현체 관계. RDS와 ElastiCache가 백업과 장애 대비를 맡는다는 것(RDS 자동 백업, Multi-AZ). Jackson이 기본 JSON 라이브러리라는 것(Spring Boot servlet 문서에 있다는 서브에이전트 보고만 받았고 직접 원문을 보지는 않았다).

### 예시로 지어낸 것

- 채용 공고(0:00)는 예시다. 박스 첫 줄에 `(예시)`를 넣었다.
- `Item`, `ItemService`, `stockRepo`, `orderRepo`, `items/42/main.jpg`, `{"id":42,"name":"키보드"}`는 지어낸 예시 이름과 값이다.
- 엔티티 이름을 `Order`로 하지 않고 `Item`으로 했다. `ORDER`가 SQL 예약어라 JPQL 예시에서 헷갈릴 수 있어서다.
- 코드는 문법상 돌아가는 형태로 썼다. 다만 클래스·메서드 몸통은 생략했다(`stockRepo.decrease`, `ItemDto` 등은 있다고 가정).

### 표기

- 영어로 쓴 것: Java, Kotlin, JVM, Gradle, jar, Spring, Spring Boot, Bean, DI, starter, Tomcat, HTTP, DispatcherServlet, Jackson, JSON, Spring Data JPA, JPQL, JPA, Hibernate, SQL, JDBC, MySQL, HikariCP, Servlet, `@Transactional`, S3, Presigned URL, AWS SDK, Spring Security, GitHub Actions, Docker, ECS, EC2, ALB, RDS, ElastiCache, AWS, Actuator, Prometheus, Grafana, new.
  마지막 문장의 "자바 백엔드"도 자막 규칙에 따라 "Java 백엔드"로 썼다.
- 한글로 둔 것: 컨트롤러, 서비스, 리포지토리, 필터, 엔티티, 인터페이스, 트랜잭션, 커밋, 롤백, 키, 바이트코드. 개발자가 한국어로 말할 때 한글로 쓰는 말이고, 동사로 쓴 커밋·롤백은 사용자 규칙대로 한글로 썼다.
- `say`를 쓴 문장은 없다. 모든 읽기는 `pronounce`로 처리했다.
- 썸네일: 제목 `Spring 백엔드, / 뒤에 뭐가 / 쌓여 있나?`(140px), 부제 `# 요청 하나가 지나가는 길`, 제목줄 `❯ cat stack.txt`. 2차에서 바꾸지 않았다.

## 측정한 것 / 보기만 한 것

- 렌더(3차): 1080x1920, 30 fps, 169.9 s(2:50), 16.3 MB.
- 오디오: 통합 -14.0 LUFS, 피크 -1.5 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 11건(아래). 다른 종류의 경고는 없었다.
- `build.py`: 최종본에서 `font down to`, `chars/s`, `diagram text down to` 경고는 없었다.
- `thumbnail.py`: 제목 140px, 경고 없음.
- 화면: 장면마다 가운데와 끝 직전을 캡처해 봤다(41장). 새 인트로 문장은 7.5 s 프레임을 따로 찍어 확인했다.
  - 3차: 다이어그램 12장면을 41장 전체 캡처로 본 뒤, 고친 곳(화살표 간격, 원통 높이, S3 배치, 정리 장면의 배지)을 14장 다시 찍어 봤다.
    렌더된 MP4에서도 1:27과 2:02 프레임을 뽑아 다이어그램이 캡처와 같게 나오는 것을 확인했다.
  - 박스가 넘친 곳은 없고, 자막은 모두 2줄 안이며, 자막에 한글 음차는 없다.
  - 0초 프레임에 채용 공고 박스와 첫 자막이 보인다.
  - 가장 빽빽한 박스는 ItemService.java(0:27, 6줄)와 ItemRepository.java(1:03)다. 원본 크기에서 읽히지만 휴대폰에서는 작다.
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - 약어: JVM(0:14), jar "자르"(0:22, 0:37), DI(0:27), HTTP(0:47), JSON(0:54), JPQL "제이피큐엘"(1:11), JDBC(1:17), S3 "에스쓰리"(1:51), ECS·EC2 "이씨에스·이씨투"(2:08), ALB(2:08), RDS(2:18), AWS SDK(2:30)
  - 긴 이름: DispatcherServlet "디스패처서블릿"(0:47), HikariCP "히카리씨피"(1:27), `@Transactional` "트랜잭셔널"(1:43, 문장 첫 단어), Presigned URL "프리사인드 유알엘"(1:51), ElastiCache "일래스티캐시"(2:18), GitHub Actions(2:08)
  - new "뉴"(0:27): 한 음절이라 어색하게 들릴 수 있다.
  - 마지막 문장(2:30 이후) "행복해요"의 억양

## 일부러 남긴 경고

`line_unread` 11건. 모두 코드 박스로 남긴 장면이다. 글자마다 `<span>`이 있어서 단어 수가 부풀려 세어진다(예: `build/libs/app.jar`를 15단어로 셈). 실제 단어 수로 보면 대부분 읽을 시간이 된다.
2차의 22건에서 줄어든 것은, 다이어그램으로 바꾼 장면에서 경고가 사라졌기 때문이다. 다이어그램은 글자를 한 자씩 치지 않는다.

- 실제로도 짧은 편인 줄(2 s 안팎):
  - gradlew의 `$ java -jar app.jar`(1.93 s)
  - JPQL의 `// Item: 테이블 말고 엔티티`(1.97 s)
  - application.yml의 `# 연결을 미리 열어 두고 빌려 쓰기`(2.16 s)

  세 장면 모두 끝에 hold 0.5 s를 줬다. 나레이션이 같은 내용을 말하거나 박스의 보조 줄이다.
- 나머지 8건은 2.5–5.5 s 동안 보이고 실제 단어 수는 3–6개라서 읽힌다.

hold를 늘리면 film이 170 s를 넘는다(지금 169.9 s).

## 가장 약한 부분

- **스킬 원칙과 다르게 넓고 얕다.** 사용자 요청대로다. 층마다 '왜'는 한 줄씩만 있다. "Spring이 만들어 넣어 준다"는 말했지만, 그게 왜 좋은지(교체·테스트가 쉬움)는 말하지 않았다.
- **"예외가 터지면 전부 롤백"**: 기본 설정에서는 RuntimeException과 Error만 롤백된다. 체크 예외는 롤백되지 않는다. 박스에는 `RuntimeException`이라고 적었지만, 나레이션은 단순화했다.
- **"연결은 맺는 데 오래 걸려서"**: 수치를 대지 않았다. 직접 재지도 않았다.
- **flow.txt(1:17)에 HikariCP가 빠져 있다.** 실제로는 Hibernate가 HikariCP에서 연결을 빌려 JDBC를 쓴다. 바로 다음 장면에서 따로 다뤘다.
- **Lombok `@RequiredArgsConstructor`를 설명 없이 보여 줬다.** 입문자는 처음 보는 어노테이션일 수 있다. 박스 공간 때문에 생성자를 직접 쓰지 않았다.
- **"로그인은 토큰을 확인"**: JWT 방식을 전제로 했다. 세션 방식도 흔하다.
- **"Tomcat이 jar 안에 있다"**: Boot 기본값(내장 서버) 기준이다. war로 외부 Tomcat에 배포하는 레거시 방식은 다루지 않았다.
- **Actuator prometheus 엔드포인트**: 박스는 바로 쓸 수 있는 것처럼 보이지만, 의존성 추가와 노출 설정이 필요하다.
- **지도(0:10)가 짧게 보인다.** 여섯 상자가 0.35 s 간격으로 나타나고, 마지막 상자는 약 2.7 s 보인 뒤 넘어간다. 각 층은 뒤에서 다시 나오지만, 목차로 멈춰 읽기에는 빠듯하다.
- **다이어그램은 단순화한 그림이다.** S3(1:51)에서 브라우저가 서버에 URL을 먼저 요청하는 단계는 그리지 않았다. 배포(2:08)는 위에서 아래로 흐르는데 ALB 화살표만 아래에서 위로 간다.
- **계층(0:54)의 Jackson 화살표가 짧다.** JSON 줄과 컨트롤러 사이 간격(64px)이 화살표 길이라서, 휴대폰에서는 작게 보인다.
