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

일부 챕터는 MySQL과 Redis가 필요하다. Docker(또는 Podman)가 설치되어 있으면 한 줄로 띄울 수 있다.

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
    main.py                  # FastAPI 앱 진입점
    routers/                 # 챕터별 API 라우터
      printer.py             # Ch.2 - System Call과 커널
      uploader.py            # Ch.3 - CPU Bound와 I/O Bound
      memory.py              # Ch.4 - 프로세스와 스레드
      concurrency.py         # Ch.5 - 동시성 제어
      network.py             # Ch.6 - 네트워크 기초
      datastructure.py       # Ch.10 - 자료구조 선택
      ch13_orm.py            # Ch.13 - ORM과 N+1
      ch14_index.py          # Ch.14 - 인덱스
      ch15_transaction.py    # Ch.15 - Transaction과 Isolation Level
      ch16_tuning.py         # Ch.16 - DB 성능 튜닝 (Pagination)
      ch17_cache.py          # Ch.17 - 캐시 장애 (Cache Stampede)
      ch18_layered_cache.py  # Ch.18 - 계층 캐시 (Local + Redis)
      ch19_scale.py          # Ch.19 - Bottleneck과 Scale-Out
      ch21_order.py          # Ch.21 - 테스트 (DI 패턴)
      ch23_security.py       # Ch.23 - 보안 (XSS, SQL Injection, IDOR)
    model/                   # SQLAlchemy 모델
    repository/              # DB 접근 계층
    service/                 # 비즈니스 로직
      order_service.py       # Ch.21 - OrderService (DI 패턴)
  tests/                     # Ch.21 - 테스트 코드
    unit/                    # Unit Test (Mock 사용)
    integration/             # Integration Test (실제 DB)
  scripts/                   # 시드 데이터 삽입 스크립트
  k6/                        # 챕터별 k6 부하 테스트 스크립트
  Dockerfile                 # Ch.22 - 컨테이너
  docker-compose.yml         # MySQL, Redis 등 외부 인프라
  pyproject.toml             # Poetry 의존성
```
