import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool, QueuePool

router = APIRouter(prefix="/network", tags=["network"])


# ─────────────────────────────────────────
# MySQL 연결 정보 (docker-compose.yml의 csbe-mysql 컨테이너)
# repository/base.py와 동일한 정보를 사용한다
# ─────────────────────────────────────────

MYSQL_USER = "root"
MYSQL_PASSWORD = "csbe"
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_DB = "csbe_study"

SYNC_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)


# ─────────────────────────────────────────
# 사례 A: Connection Pool 고갈
# pool_size=3, max_overflow=0 → 최대 3개만 동시 사용 가능
# pool_timeout=3 → 3초 안에 Connection을 못 잡으면 에러
# ─────────────────────────────────────────

_small_pool_engine = create_engine(
    SYNC_URL,
    pool_size=3,
    max_overflow=0,
    pool_timeout=3,
    pool_recycle=3600,
    poolclass=QueuePool,
)

# NullPool: 매 요청마다 새 Connection을 만들고 즉시 닫는다
_nopool_engine = create_engine(
    SYNC_URL,
    poolclass=NullPool,
)


# ─────────────────────────────────────────
# 사례 B: Connection 생성 비용 비교
# QueuePool(size=10) vs NullPool 벤치마크
# ─────────────────────────────────────────

_bench_pool_engine = create_engine(
    SYNC_URL,
    pool_size=10,
    max_overflow=5,
    pool_timeout=10,
    pool_recycle=3600,
    poolclass=QueuePool,
)

# 벤치마크용 NullPool (사례 A의 _nopool_engine과 별도)
_bench_nopool_engine = create_engine(
    SYNC_URL,
    poolclass=NullPool,
)


# ─────────────────────────────────────────
# 테이블 초기화
# ─────────────────────────────────────────


@router.post("/pool/reset")
def pool_reset():
    """테스트 테이블을 초기화한다"""
    with _small_pool_engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS ch06_network_test ("
                "  id INT AUTO_INCREMENT PRIMARY KEY,"
                "  data VARCHAR(100),"
                "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(text("TRUNCATE TABLE ch06_network_test"))
        conn.commit()
    return {"message": "테이블 초기화 완료"}


# ─────────────────────────────────────────
# 사례 A: Connection Pool 고갈 엔드포인트
# ─────────────────────────────────────────


@router.post("/pool/query-pool")
def query_with_pool():
    """pool_size=3인 Pool에서 Connection을 가져온다

    SELECT SLEEP(1)로 1초간 Connection을 점유한다.
    동시에 3개 이상의 요청이 오면 Pool이 고갈된다.
    """
    try:
        with _small_pool_engine.connect() as conn:
            # 1초간 Connection을 점유 (Pool 고갈 유발)
            conn.execute(text("SELECT SLEEP(1)"))
            result = conn.execute(text("SELECT 1 AS alive"))
            row = result.fetchone()
            return {
                "result": "success",
                "pool_type": "QueuePool(size=3)",
                "data": row[0],
            }
    except Exception as e:
        # TimeoutError: Pool에서 Connection을 못 잡은 경우
        error_name = type(e).__name__
        return JSONResponse(
            status_code=503,
            content={
                "error": "connection_pool_exhausted",
                "detail": f"{error_name}: Connection Pool에서 "
                f"3초 안에 Connection을 확보하지 못했다",
                "pool_size": 3,
                "pool_timeout": 3,
            },
        )


@router.post("/pool/query-nopool")
def query_without_pool():
    """NullPool: 매 요청마다 새 Connection을 만들고 즉시 닫는다

    Pool이 없으니 고갈이 없다. 대신 매번 TCP Handshake + 인증이 발생한다.
    """
    with _nopool_engine.connect() as conn:
        conn.execute(text("SELECT SLEEP(1)"))
        result = conn.execute(text("SELECT 1 AS alive"))
        row = result.fetchone()
        return {
            "result": "success",
            "pool_type": "NullPool",
            "data": row[0],
        }


@router.get("/pool/status")
def pool_status():
    """현재 Pool 상태를 반환한다"""
    pool = _small_pool_engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": 0,
        "pool_timeout": 3,
    }


# ─────────────────────────────────────────
# 사례 B: Connection 생성 비용 비교
# ─────────────────────────────────────────


@router.post("/bench/with-pool")
def bench_with_pool():
    """QueuePool(size=10)로 간단한 쿼리를 실행한다

    Connection을 Pool에서 빌려서 쓰고 반환한다.
    TCP Handshake 없이 재활용한다.
    """
    start = time.monotonic()
    with _bench_pool_engine.connect() as conn:
        conn.execute(
            text("INSERT INTO ch06_network_test (data) VALUES (:data)"),
            {"data": "pool_test"},
        )
        result = conn.execute(text("SELECT COUNT(*) FROM ch06_network_test"))
        count = result.scalar()
        conn.commit()
    elapsed_ms = (time.monotonic() - start) * 1000
    return {
        "result": "success",
        "pool_type": "QueuePool(size=10)",
        "row_count": count,
        "elapsed_ms": round(elapsed_ms, 2),
    }


@router.post("/bench/without-pool")
def bench_without_pool():
    """NullPool로 같은 쿼리를 실행한다

    매 요청마다 TCP 3-Way Handshake + MySQL 인증 + 쿼리 + 4-Way Handshake.
    Connection을 재활용하지 않으니 느리고, TIME_WAIT가 대량 발생한다.
    """
    start = time.monotonic()
    with _bench_nopool_engine.connect() as conn:
        conn.execute(
            text("INSERT INTO ch06_network_test (data) VALUES (:data)"),
            {"data": "nopool_test"},
        )
        result = conn.execute(text("SELECT COUNT(*) FROM ch06_network_test"))
        count = result.scalar()
        conn.commit()
    elapsed_ms = (time.monotonic() - start) * 1000
    return {
        "result": "success",
        "pool_type": "NullPool",
        "row_count": count,
        "elapsed_ms": round(elapsed_ms, 2),
    }
