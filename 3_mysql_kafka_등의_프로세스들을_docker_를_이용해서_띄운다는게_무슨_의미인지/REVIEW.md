# REVIEW

## 시청 후 답할 수 있는 것

질문: **MySQL, Kafka, Redis, nginx 같은 프로그램을 Docker로 띄운다는 건, 내 컴퓨터에서 실제로 무엇을 실행한다는 뜻일까?**

특정 프로그램이 아니라 "프로세스를 Docker로 띄운다"의 일반적인 뜻이 주제다. 네 프로그램은 예시로만 쓰고, 같은 확인을 네 프로그램에 똑같이 해서 표로 보였다.

답안(항목마다 주장 + 왜). 괄호는 영상 속 위치.

1. **프로그램 실행 = 디스크의 실행 파일을 읽어 프로세스를 만드는 일이다. 그런데 실행 파일은 기대는 파일이 있어야 돈다.**
   왜: 실행 파일은 공유 라이브러리나 런타임 위에서 돈다. 예: nginx는 `libssl`, `libc` 같은 라이브러리(ldd로 확인), Kafka는 Java 17 이상(공식 안내)이 있어야 한다.
   그래서 설치란 이런 파일들을 내 컴퓨터에 깔아 두는 일이다. (0:12 run.txt)
2. **Docker 이미지는 프로그램과 그게 기대는 파일을, 리눅스 기본 파일까지 통째로 묶은 것이다. 그래서 내 컴퓨터에 깔 게 없다.**
   증거(실측): `apache/kafka:4.4.0` 안에는 `/opt/kafka`와 Java 25(`/opt/java/openjdk`)가 있다. 컨테이너 안의 `/etc/os-release`는 이미지마다 다르다: mysql은 Oracle Linux 9.8, kafka는 Alpine 3.24, redis와 nginx는 Debian 13. 맥에서 띄웠는데도 그렇다. (0:29 image.txt, 0:35 os-release)
3. **`docker run`은 이미지 파일(읽기 전용) 위에 컨테이너만의 쓰기 칸을 얹고, 그 위에서 프로세스 하나를 실행한다. 그 프로세스가 컨테이너다.**
   증거(실측): 네 컨테이너 안의 1번 프로세스(`/proc/1/comm`)는 각각 `mysqld`, `java`, `redis-server`, `nginx`다. (0:45 docker run, 0:51 pid1.txt)
4. **그래서 그 프로세스가 끝나면 컨테이너도 끝난다.**
   왜: 컨테이너는 따로 켜 둔 컴퓨터가 아니라 그 프로세스 자체이기 때문이다.
   증거(실측): Redis 컨테이너(`cache`)에 `redis-cli shutdown`을 보내자 상태가 `Up 9 seconds`에서 `Exited (0) 1 second ago`로 바뀌었다. (0:58 docker ps)
5. **컨테이너는 가상 머신이 아니라 보통 프로세스다. 커널이 namespace로 그 프로세스에게 보이는 범위(PID, 파일, 네트워크, 호스트 이름)를 따로 잘라 준다.**
   증거(실측): nginx는 안에서 1번, 밖(`docker top web`)에서 4829번이다. 네 컨테이너는 IP도 각자 받았다(172.17.0.2–.5). (1:12 vm.txt, 1:25 pid.txt)
6. **보이는 범위와 별개로, 쓸 수 있는 양은 cgroup이 나눈다.**
   왜: namespace는 보이는 것만 나누고 사용량은 막지 않는다. `-m 512m`을 주면 커널이 그 프로세스의 메모리 상한을 건다.
   증거(실측): `-m` 없이 띄운 Redis의 `memory.max`는 `max`, `-m 512m`으로 띄운 Redis는 `536870912`. (1:35 cgroup)
7. **커널은 하나다. 맥과 윈도우에서는 Docker Desktop이 띄운 리눅스 VM의 커널이다. OS 부팅이 없어서 빨리 뜬다.**
   증거(실측): 네 컨테이너 모두 `uname -r`이 `7.0.14-linuxkit`이고, 맥 자신은 Darwin 25.5.0이다. 앞의 PID 4829도 그 VM 안의 번호다(화면).
   컨테이너를 만들고 지우는 데 0.14–0.19초가 걸렸다(5회). (1:48 uname.txt, 1:58 time.txt)
8. **칸이 나뉘어 있으니, 밖에서 쓰려면 이어 줘야 한다: 포트는 `-p`, 남길 파일은 볼륨.**
   왜(포트): 네트워크가 따로라서 `-p` 없이 띄운 Redis는 맥에서 `localhost:6379`로 접속이 안 됐다. `-p 8080:80`을 주자 맥의 8080번으로 nginx 기본 페이지(`Welcome to nginx!`)가 왔다.
   왜(파일): 안에서 쓴 파일은 기본적으로 그 컨테이너의 쓰기 칸에 들어간다(`docker diff web` → `A /tmp/note.txt`). 컨테이너를 지우고 새로 띄우면 그 파일이 없다. 남겨야 할 데이터는 볼륨으로 컨테이너 밖에 둔다. (2:04 docker run, 2:15 docker diff)

기억할 한 문장: "Docker로 띄운다는 건 이미지의 파일로 프로세스 하나를 칸막이 안에서 실행하는 것이다. 보이는 범위는 namespace가, 쓸 양은 cgroup이 나누고, 커널은 다 같이 쓴다. 그래서 설치 없이 바로 뜨는 대신, 포트와 남길 파일은 밖으로 이어 줘야 한다." (2:29 summary.md)

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
S="mysql_kafka_등의_프로세스들을_docker_를_이용해서_띄운다는게_무슨_의미인지"
npx --yes hyperframes@0.8.209 render -o "output/$S.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 "output/$S.mp4"
ffmpeg -nostats -i "output/$S.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
# 5) 캡처·렌더 임시 파일 정리
rm -rf .hyperframes renders
```

`index.html`과 `compositions/`는 `tools/build.py`가 만드는 파일이다. 직접 고치지 말고 `content.json`을 고친다.
`output/`에는 영상과 썸네일 두 파일만 둔다.

## 내린 결정

### 다시 만든 이유 (2026-10-29, 3차)

사용자가 바란 것은 "MySQL, Kafka 각각"이 아니라 "어떤 프로세스를 Docker로 띄운다는 게 무슨 뜻인지"였다. 1·2차 영상은 질문을 "무슨 뜻 + 직접 설치와 무엇이 다르고 무엇을 챙겨야 하나"로 넓혔다. 그래서 뒤쪽 절반(약 85초)이 MySQL 사용법(버전 나란히, 포트 보안, MySQL 이미지의 익명 볼륨, 초기화 스크립트와 비밀번호)이 됐다. 3차는 질문을 주제 그대로 좁히고 대본을 새로 썼다.

- 예시를 MySQL, Kafka, Redis, nginx 넷으로 나눴다. 같은 확인(os-release, PID 1, uname)은 네 프로그램 모두에 해서 표로 보였다. 한 프로그램만 보여 주는 장면은 프로그램을 돌려 가며 맡겼다.

| 장면 | 쓴 프로그램 |
|---|---|
| 0:00 첫 화면 | 넷 모두 |
| 0:12 실행 파일이 기대는 파일 | nginx(ldd), Kafka(Java) |
| 0:29 이미지 안 | Kafka |
| 0:35 os-release, 0:51 PID 1, 1:48 uname | 넷 모두(표) |
| 0:58 프로세스가 끝나면 컨테이너도 끝 | Redis |
| 1:25 안 1번 / 밖 4829번, IP | nginx, IP는 넷 모두 |
| 1:35 cgroup 메모리 | Redis |
| 2:04 포트 | Redis(-p 없음), nginx(-p) |
| 2:15 쓰기 칸 | nginx |

- 새로 넣은 답안: 실행 파일이 기대는 파일(1), 프로세스가 끝나면 컨테이너도 끝(4), cgroup(6). 셋 다 "프로세스를 띄운다"의 일반적인 뜻에 속한다.
- 뺀 것(1·2차에 있던 것): 버전이 다른 MySQL 나란히 띄우기, `-p` 포트 충돌 에러, `-p` 주소와 보안, MySQL 이미지의 익명 볼륨, MySQL 초기화 스크립트와 환경 변수, 비밀번호가 무시되는 경우. 모두 "Docker로 띄울 때 챙길 것"에 속해서 다음 영상 후보로 옮겼다.
- 썸네일 부제를 `# 설치 안 했는데 MySQL이 뜬다?`에서 `# 설치 안 했는데 왜 뜰까?`로 바꿨다. 제목은 그대로다.

### 범위

- namespace 종류는 PID, 파일, 네트워크, 호스트 이름만 말했다. IPC, cgroup namespace, user namespace는 넣지 않았다.
- cgroup은 메모리 하나로만 보였다. CPU 제한은 넣지 않았다.
- 이미지 레이어 구조(여러 레이어, overlay)는 "이미지 파일(읽기 전용) + 쓰기 칸" 두 층으로만 그렸다.
- 길이: 3차 첫 대본은 30문장, film 179.7 s였다. 줄인 순서:
  - 첫 문장 "MySQL, Kafka, Redis, nginx. 쓰는 법을 찾아보면, …"이 쉼표마다 쉬어서 9.1 s였다. "MySQL, Kafka, Redis 같은 프로그램은 설치 대신, 이런 한 줄로 띄우곤 해요"로 바꿨다. nginx는 화면에 있다.
  - 연결 문장 "칸이 나뉘어 있으니, 밖에서 쓰려면 직접 이어 줘야 해요"를 뺐다.
  - "아까 본 4829번도 그 VM 안의 번호고요"를 나레이션에서 빼고 화면 줄로 옮겼다.
  - "이 프로세스가 바로 컨테이너예요. 컨테이너 안의 1번 프로세스가 …"를 줄였다.
  - 결과: 29문장, film 168.3 s(8080으로 바꾼 뒤 168.34 s). hold: os-release 0.3 s, pid1.txt 0.3 s, time.txt 0.3 s, 포트 0.5 s.
- 다음 영상 후보:
  - **Docker로 띄울 때 챙길 것**: `-p`는 주소를 안 적으면 다른 기기에도 열린다(`127.0.0.1:`), 이미지가 VOLUME으로 지정한 경로는 익명 볼륨이 되고 컨테이너를 지워도 남는다, MySQL처럼 첫 시작 때만 환경 변수로 초기화하는 이미지, 태그와 digest. 1·2차 영상과 블로그 7–8장에 재료가 있다.
  - **Kafka를 Docker로 띄우면 토픽은 어디에 남을까**: 기본 `log.dirs=/tmp/kraft-combined-logs`(쓰기 레이어), `KAFKA_LOG_DIRS`만 주면 `process.roles` 누락, `/tmp/…`에 볼륨을 붙이면 권한 문제(블로그 실험).
  - **Docker로 띄울까, 그냥 설치할까**: 개발용과 운영용, 맥에서 VM 한 겹 때문에 생기는 차이
  - **Docker Compose로 여러 컨테이너를 한 번에**, **Kafka advertised.listeners**, **이미지는 왜 레이어로 쌓일까**

### 쓴 사실과 출처 (2026-10-29 확인)

| 영상 속 내용 | 출처 |
|---|---|
| 실행 = 실행 파일을 읽어 프로세스로 | man7.org/linux/man-pages/man2/execve.2.html — "execve() executes the program referred to by path. This causes the program that is currently being run by the calling process to be replaced with a new program, with newly initialized stack, heap, and (initialized and uninitialized) data segments." |
| 실행 파일이 기대는 라이브러리(ldd) | man7.org/linux/man-pages/man1/ldd.1.html — "ldd prints the shared objects (shared libraries) required by each program or shared object specified on the command line." |
| Kafka는 Java 17 이상 필요 | kafka.apache.org/quickstart — "NOTE: Your local environment must have Java 17+ installed." |
| 이미지 = 실행에 필요한 파일·라이브러리·설정 묶음 | docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/ — "A container image is a standardized package that includes all of the files, binaries, libraries, and configurations to run a container." |
| 쓰기 칸(읽기 전용 이미지 위), 컨테이너를 지우면 사라짐 | docs.docker.com/engine/storage/ — "By default all files created inside a container are stored on a writable container layer that sits on top of the read-only, immutable image layers." / "Data written to the container layer doesn't persist when the container is destroyed." |
| 컨테이너 = 격리된 프로세스, VM과 차이, 커널 공유 | docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/ — "A container is simply an isolated process with all of the files it needs to run." / "a VM is an entire operating system with its own kernel, hardware drivers, programs, and applications." / "If you run multiple containers, they all share the same kernel" |
| 컨테이너의 주 프로세스 | docs.docker.com/engine/containers/multi-service_container/ — "A container's main running process is the `ENTRYPOINT` and/or `CMD` at the end of the `Dockerfile`." / docs.docker.com/reference/cli/docker/container/stop/ — "The main process inside the container will receive `SIGTERM`, and after a grace period, `SIGKILL`." |
| namespace로 격리, 안에서 PID 1 | docs.docker.com/get-started/docker-overview/ — "Docker uses a technology called namespaces to provide the isolated workspace called the container." / man7.org/linux/man-pages/man7/pid_namespaces.7.html — "The first process created in a new namespace … has the PID 1, and is the "init" process for the namespace" |
| cgroup = 사용량 제한 | man7.org/linux/man-pages/man7/cgroups.7.html — "Control groups, usually referred to as cgroups, are a Linux kernel feature which allow processes to be organized into hierarchical groups whose usage of various types of resources can then be limited and monitored." / docs.docker.com/engine/containers/resource_constraints/ — "`-m` or `--memory=` … The maximum amount of memory the container can use." |
| 맥·윈도우는 Docker Desktop의 리눅스 VM 안에서 돈다 | docs.docker.com/desktop/features/vmm/ — "Docker Desktop supports multiple Virtual Machine Managers (VMMs) to power the Linux VM that runs containers." |
| publish하지 않은 포트는 막힌다, `-p 호스트:컨테이너` | docs.docker.com/engine/network/port-publishing/ — "By default, for both IPv4 and IPv6, the Docker daemon blocks access to ports that have not been published." / "Map port `8080` on the Docker host to TCP port `80` in the container." |
| 볼륨은 컨테이너를 지워도 남는다 | docs.docker.com/engine/storage/volumes/ — "A volume's contents exist outside the lifecycle of a given container. … Using a volume ensures that the data is persisted even if the container using it is removed." |

"주 프로세스가 끝나면 컨테이너가 끝난다"를 그대로 적은 문장은 위 Docker 문서들(multi-service_container, container stop, containers/run)에서 찾지 못했다. 영상의 이 주장은 Redis 실험(`Exited (0)`)과 "주 프로세스 = ENTRYPOINT/CMD" 문장에 기댄다.

### 직접 실험한 것

3차(2026-10-29 03:44–03:46 UTC, 이 맥, Docker Desktop 4.97.0, Engine 29.9.2 linux/arm64). 스크립트와 전체 출력: `/private/tmp/claude-501/-Users-user1-Documents-video-making/9b37783c-5076-4759-b34a-d7f8603371ee/scratchpad/shorts-v2/exp.sh`, `exp.txt`(임시 폴더라 언젠가 지워진다. 핵심 출력은 아래에 옮겼다).

- 이미지: `mysql:8.4`(mysqld 8.4.13), `apache/kafka:4.4.0`(kafka_2.13-4.4.0, Temurin 25.0.4.1), `redis:8.8`(8.8.4), `nginx:1.30`(1.30.6).
- 띄운 컨테이너: `db`(`-e MYSQL_ALLOW_EMPTY_PASSWORD=yes mysql:8.4`), `kafka`, `cache`(redis), `web`(`-p 8081:80 nginx:1.30`, 이때 8080은 다른 프로그램이 쓰고 있었다. 포트 확인은 아래처럼 8080으로 다시 했다).
- 컨테이너별 `/etc/os-release` | `/proc/1/comm` | `uname -r`:
  ```
  db    | PRETTY_NAME="Oracle Linux Server 9.8"      | PID1=mysqld       | 7.0.14-linuxkit
  kafka | PRETTY_NAME="Alpine Linux v3.24"           | PID1=java         | 7.0.14-linuxkit
  cache | PRETTY_NAME="Debian GNU/Linux 13 (trixie)" | PID1=redis-server | 7.0.14-linuxkit
  web   | PRETTY_NAME="Debian GNU/Linux 13 (trixie)" | PID1=nginx        | 7.0.14-linuxkit
  ```
  맥 `uname -sr` → `Darwin 25.5.0`.
- `docker top web` → `root 4829 4805 … nginx: master process nginx -g daemon off;`(worker 10개는 4872–4881).
- IP: db 172.17.0.2, kafka 172.17.0.3, cache 172.17.0.4, web 172.17.0.5.
- `ldd /usr/sbin/nginx`: linux-vdso, libcrypt, libpcre2-8, libssl.so.3, libcrypto.so.3, libz, libc.so.6, ld-linux-aarch64, libzstd(9줄). redis-server 8줄, mysqld 76줄. Kafka: java는 `/opt/java/openjdk/bin/java`, `/opt/kafka/libs`에 jar 110개.
- 포트: 맥에서 `curl localhost:8081` → `<title>Welcome to nginx!</title>`. 사용자가 8080을 쓰던 프로그램을 끈 뒤 `docker run -d --name web -p 8080:80 nginx:1.30`으로 다시 띄워 `docker ps` → `0.0.0.0:8080->80/tcp, [::]:8080->80/tcp`, `curl localhost:8080` → `<title>Welcome to nginx!</title>`(영상은 이 값). `localhost:6379` → 실패(`cache`는 `-p` 없음). 안에서 `redis-cli ping` → `PONG`.
- cgroup: `cache`(‑m 없음) `memory.max` → `max`. `cache-m`(`-m 512m redis:8.8`) → `536870912`.
- 쓰기 칸: `docker exec web sh -c 'echo hi > /tmp/note.txt'` → `docker diff web | grep note` → `A /tmp/note.txt`. `docker rm -fv web` 후 같은 명령으로 새로 띄운 `web`에서 `cat /tmp/note.txt` → `No such file or directory`.
- 주 프로세스 종료: `cache  Up 9 seconds` → `docker exec cache redis-cli shutdown` → `cache  Exited (0) 1 second ago`. 로그 마지막 줄 `Redis is now ready to exit, bye bye...`.
- 시작 시간(0.14–0.19 s)은 같은 날 블로그 실험(`docker run --rm alpine:3.22 true`, 맥 쪽 벽시계 5회: 0.19/0.16/0.16/0.16/0.14 s) 값이다.
- 정리: 실험 컨테이너는 `docker rm -fv`로 익명 볼륨까지 지웠다. 받은 이미지 `apache/kafka:4.4.0`, `redis:8.8`, `nginx:1.30`을 지웠다. 원래 있던 `mysql:8.4`, `hello-world`와 사용자의 `eclipse-temurin:25-jre`, `maven:3.9-eclipse-temurin-25`, 볼륨 `cfea1a08…`(10-28), `d08f4d60…`(03:26 UTC), `5d3642eb…`(03:38 UTC)는 손대지 않았다. 뒤의 두 볼륨은 실험 전에 생긴 것이라 이 작업의 것이 아니다.

### 예시로 줄이거나 바꾼 화면

- 첫 화면 `docker run ... mysql:8.4` 등의 `...`는 옵션을 줄인 것이다(MySQL은 `MYSQL_ROOT_PASSWORD` 같은 변수가 있어야 뜬다).
- run.txt의 `libssl.so.3, libc.so.6, …`는 ldd 출력 9줄 중 두 개만 적은 것이다. "Java 17 이상 먼저 설치"는 Kafka 공식 안내다(이미지 안에는 Java 25가 있다).
- image.txt의 `/bin /lib /etc # 리눅스 기본`은 설명용 줄이다(Alpine 기본 디렉터리).
- os-release 표는 `PRETTY_NAME`을 줄였다(`Alpine Linux v3.24` → `Alpine Linux 3.24`, `Debian GNU/Linux 13 (trixie)` → `Debian 13`). 표의 이름(mysql, kafka, redis, nginx)은 컨테이너 이름이 아니라 이미지 이름이다.
- docker run 장면의 `[ 쓰기 칸 ] / [ 이미지 파일 ]`은 그림이다(실제는 overlay 파일 시스템, 이미지 레이어 여러 개).
- pid.txt의 `PID 4829  nginx: master`는 `docker top` 출력에서 PID와 CMD 앞부분만 남겼다. IP 줄은 네 IP의 마지막 자리만 적었다.
- cgroup 장면의 두 값은 Redis 컨테이너 두 개(`cache`, `cache-m`)에서 나왔다.
- 포트 장면의 `$ docker run -p 8080:80 nginx`는 실제 명령 `docker run -d --name web -p 8080:80 nginx:1.30`을 줄였다. 처음에는 8080이 다른 Java 프로그램에 쓰여 8081로 찍었지만, 예시는 흔히 쓰는 8080이어야 해서(사용자 요청) 그 프로그램을 끄고 8080으로 다시 실험해 바꿨다.
- docker diff 장면의 `cat: /tmp/note.txt: No such file`은 실제 출력 `cat: /tmp/note.txt: No such file or directory`를 줄였다. `-v 이름:경로` 줄은 설명용이다(볼륨 실험은 이번에 하지 않았다. 볼륨이 남는다는 것은 1차 MySQL 실험과 블로그 실험에서 확인했다).

### 표기

- 영어: `MySQL`, `Kafka`, `Redis`, `nginx`, `Docker`, `Docker Desktop`, `docker run`, `Java`, `VM`, `OS`, `IP`, `namespace`, `cgroup`, `Exited`, `libssl`, `-p`.
- 한글로 둔 말: 이미지, 컨테이너, 프로세스, 커널, 가상 머신, 라이브러리, 실행 파일, 쓰기 칸, 볼륨, 포트, 네트워크, 메모리.
- `pronounce`: MySQL 마이에스큐엘, Kafka 카프카, Redis 레디스, nginx 엔진엑스, Docker Desktop 도커 데스크톱, docker run 도커 런, Docker 도커, Java 자바, VM 브이엠, OS 오에스, IP 아이피, namespace 네임스페이스, cgroup 씨그룹, Exited 엑시티드, libssl 립에스에스엘, -p 피.
- `say`를 쓴 문장 5개: 0:51 "1번"(일번), 1:25 "1번", "4829번"(일번, 사천팔백이십구번), 1:42 "512MB"(오백십이메가), 1:58 "0.2초도"(영점이초도), 2:09 "8080번", "80번"(팔공팔공번, 팔십번).
- 썸네일: 제목 `Docker로 / 띄운다는 건 / 무슨 뜻?`(190px), 부제 `# 설치 안 했는데 왜 뜰까?`, 제목줄 `❯ docker run`.

## 측정한 것 / 보기만 한 것

- 렌더: 1080x1920, 30 fps, 168.4 s(2:48.4), 18.2 MB.
- 오디오: 통합 -13.8 LUFS, 피크 -1.4 dBFS.
- `hyperframes check`: 오류 0, 경고 `line_unread` 10건(아래). 다른 종류의 경고는 없었다.
- `build.py`는 `font down to`나 `chars/s` 경고를 내지 않았다. `thumbnail.py`는 제목 190px로 경고가 없었다.
- 화면: 장면마다 가운데와 끝 직전을 캡처해 봤다(31장). 박스 넘침은 없었고 자막은 모두 2줄 안이었다. 0초 프레임에 첫 박스(docker run 네 줄)와 첫 자막이 보인다. 자막에 한글 음차는 없다.
  가장 작은 글씨는 docker ps 장면(0:58, 가장 긴 줄 `$ docker exec cache redis-cli shutdown`)과 포트 장면(2:04, 5줄)이고, 원본 크기 프레임에서 읽힌다.
- 소리는 들어 보지 않았다. 직접 들어서 확인할 곳:
  - 영어: MySQL, Kafka, Redis(0:00), nginx·libssl(0:17, "엔진엑스", "립에스에스엘"), docker run(0:45, "도커 런"), Exited(1:03, "엑시티드"), namespace(1:18), cgroup(1:35, "씨그룹"), Docker Desktop·VM(1:54), -p(2:04, 2:09)
  - 숫자: Java 17(0:17), 1번(0:51, 1:25), 4829번(1:25), 512MB(1:42, "오백십이메가"), 0.2초도(1:58), 8080번·80번(2:09, "팔공팔공번", "팔십번")

## 일부러 남긴 경고

`line_unread` 10건. 글자마다 `<span>`이라 단어 수가 부풀려 세어진다(예: `nginx  nginx`를 10단어로 셈). 실제 단어 수로는 모두 2–6단어다.

- shot-03 `/opt/java/openjdk  # Java 25`(4.00 s), `/bin /lib /etc  # 리눅스 기본`(2.60 s)
- shot-04 `nginx  Debian 13`(3.07 s): hold 0.3 s
- shot-06 `redis  redis-server`(3.65 s), `nginx  nginx`(2.27 s): hold 0.3 s
- shot-09 `db .2  kafka .3  cache .4  web .5`(3.83 s)
- shot-11 `# 앞의 PID 4829도 이 VM 안 번호`(2.63 s): 나레이션에서 뺀 내용이라 화면에만 있다. 이 장면 끝이 짧다.
- shot-12 `컨테이너 생성→삭제  0.14–0.19초`(3.53 s): hold 0.3 s
- shot-13 `<title>Welcome to nginx!</title>`(3.16 s): hold 0.5 s
- shot-14 `-v 이름:경로  # 컨테이너 밖에 두기`(3.06 s)

## 가장 약한 부분

- **"그 프로세스가 끝나면 컨테이너도 끝나요"**는 이 말을 그대로 적은 Docker 문서 문장을 찾지 못했다. Redis 실험과 "주 프로세스 = ENTRYPOINT/CMD" 문장에 기댄다. 또 `--restart` 정책을 주면 Docker가 다시 띄운다. 영상은 이것을 말하지 않았다.
- **"안에서 쓴 파일은 기본적으로 쓰기 칸에"**: 이미지가 `VOLUME`으로 지정한 경로(mysql의 `/var/lib/mysql`, kafka의 세 경로 등. 블로그 실험에서 확인)에 쓴 파일은 쓰기 칸이 아니라 익명 볼륨에 들어가고, 컨테이너를 지워도(`-v` 없이) 남는다. 영상은 Docker 문서의 "By default"를 따라 "기본적으로"라고만 했고, 실험은 VOLUME이 아닌 `/tmp`로 했다.
- **"0.2초도 안 걸렸어요"**는 아무것도 안 하는 alpine 컨테이너로 잰 값이다. 네 프로그램이 준비되는 시간은 프로그램마다 다르다(같은 날 블로그 실험: Kafka 약 1.3 s, MySQL 첫 시작 약 4.3 s). 가상 머신 부팅 시간은 재지 않았다.
- **"맥과 윈도우에선 Docker Desktop의 리눅스 VM 커널"**: 윈도우는 직접 확인하지 않았다(Docker 문서의 VMM 설명에 기댄다). 리눅스 서버에서는 호스트 커널을 바로 쓴다는 것도 말하지 않았다.
- namespace 장면은 PID와 IP만 실측으로 보였다. "파일은 이미지 것만 보인다"는 os-release 표(0:35)로, 호스트 이름은 블로그 실험으로 확인한 것이다.
- `-p 8080:80`은 주소를 안 적은 형태라 다른 기기에도 열린다. 이 영상의 범위에서 뺐다(다음 영상 후보).
