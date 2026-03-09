# CSBE Study

[CSBE (Computer Science for Backend Engineer)](https://teo-jang.github.io/csbe/) 강의의 실습 코드 및 질문/답변을 위한 저장소.


## 환경 세팅

Python 3.11 이상, [Poetry](https://python-poetry.org/docs/#installation), [k6](https://k6.io/docs/get-started/installation/) 가 필요하다.

```bash
# 의존성 설치
poetry install

# pre-commit 훅 설치
poetry run pre-commit install
```

일부 챕터는 MySQL이 필요하다. Docker(또는 Podman)가 설치되어 있으면 한 줄로 띄울 수 있다.

```bash
docker compose up -d
```


## 서버 실행

main.py의 import가 상대 경로이므로 csbe_study/ 디렉토리에서 실행해야 한다.

```bash
cd csbe_study
poetry run uvicorn main:app
```

서버가 뜨면 http://localhost:8000/docs 에서 API 문서를 확인할 수 있다.


## k6 테스트 실행

서버를 띄운 상태에서, 프로젝트 루트에서 k6 스크립트를 실행한다.

```bash
# 예시: Ch.2 print 성능 테스트
k6 run k6/printer/240601_io_performance_test.js
```


## 디렉토리 구조

```
csbe-study/
  csbe_study/
    main.py              # FastAPI 앱 진입점
    routers/             # 챕터별 API 라우터
      printer.py         # Ch.2 - System Call과 커널
      uploader.py        # Ch.3 - CPU Bound와 I/O Bound
      memory.py          # Ch.4 - 프로세스와 스레드
      concurrency.py     # Ch.5 - 동시성 제어
      network.py         # Ch.6 - 네트워크 기초
      datastructure.py   # Ch.10 - 자료구조 선택
    model/               # SQLAlchemy 모델
    repository/          # DB 접근 계층
    service/             # 비즈니스 로직
  k6/                    # 챕터별 k6 부하 테스트 스크립트
  docker-compose.yml     # MySQL 등 외부 인프라
  pyproject.toml         # Poetry 의존성
```
