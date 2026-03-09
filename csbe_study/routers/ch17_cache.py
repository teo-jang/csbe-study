"""
Ch.17 - 캐시를 붙였더니 장애가 났습니다
캐시는 만능이 아니며, 캐시 자체가 새로운 장애 포인트를 만든다.

이 라우터는 Cache-Aside 패턴의 기본 동작,
Cache Stampede 현상의 재현,
그리고 Mutex Lock을 이용한 방어 전략을 직접 비교해볼 수 있도록 만들어졌다.
"""

import json
import random
import time

import redis
from fastapi import APIRouter
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

router = APIRouter(prefix="/cache", tags=["ch17-cache"])


# ─────────────────────────────────────────
# MySQL 연결 정보 (docker-compose.yml의 csbe-mysql 컨테이너)
# ─────────────────────────────────────────

MYSQL_URL = "mysql+pymysql://root:csbe@localhost:3306/csbe_study"

_engine = create_engine(
    MYSQL_URL,
    pool_size=10,
    max_overflow=5,
    pool_recycle=3600,
)

_Session = sessionmaker(bind=_engine)


# ─────────────────────────────────────────
# Redis 연결 정보 (docker-compose.yml의 csbe-redis 컨테이너)
# ─────────────────────────────────────────

redis_client = redis.Redis(
    host="localhost", port=6379, db=0, decode_responses=True
)


# ─────────────────────────────────────────
# ORM 모델 정의
# ─────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class Ch17Product(Base):
    """상품 테이블"""

    __tablename__ = "ch17_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)


# ─────────────────────────────────────────
# 시드 데이터용 상수
# ─────────────────────────────────────────

PRODUCT_NAMES = [
    "무선 키보드",
    "기계식 키보드",
    "게이밍 마우스",
    "무선 마우스",
    "27인치 모니터",
    "34인치 울트라와이드",
    "노이즈 캔슬링 헤드셋",
    "게이밍 헤드셋",
    "USB-C 허브",
    "USB 독 스테이션",
    "NVMe SSD 1TB",
    "SATA SSD 500GB",
    "DDR5 RAM 16GB",
    "DDR4 RAM 32GB",
    "65W 충전기",
    "100W GaN 충전기",
    "웹캠 1080p",
    "웹캠 4K",
    "블루투스 스피커",
    "사운드바",
]

CATEGORIES = [
    "키보드",
    "마우스",
    "모니터",
    "음향",
    "허브/독",
    "저장장치",
    "메모리",
    "충전기",
    "카메라",
    "스피커",
]


# ─────────────────────────────────────────
# 테이블 초기화 + 시드 데이터
# ─────────────────────────────────────────


@router.post("/reset")
def reset_tables():
    """테이블을 초기화하고 시드 데이터를 삽입한다

    100개의 상품을 생성하고 Redis의 product:* 키를 전부 삭제한다.
    """
    # 기존 테이블 삭제 후 재생성
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)

    session = _Session()
    try:
        products = []
        for i in range(1, 101):
            product = Ch17Product(
                name=f"{random.choice(PRODUCT_NAMES)} v{i}",
                price=random.randint(10000, 990000),
                description=f"상품 {i}번 설명. 전자제품 카테고리.",
                category=random.choice(CATEGORIES),
            )
            products.append(product)

        session.add_all(products)
        session.commit()

        # Redis에서 product:* 패턴의 키를 삭제한다
        keys = redis_client.keys("product:*")
        if keys:
            redis_client.delete(*keys)

        # lock:* 키도 정리한다
        lock_keys = redis_client.keys("lock:*")
        if lock_keys:
            redis_client.delete(*lock_keys)

        return {
            "message": "테이블 초기화 완료",
            "products": len(products),
            "redis_flushed": len(keys) if keys else 0,
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()


# ─────────────────────────────────────────
# Cache-Aside 패턴 (기본)
# ─────────────────────────────────────────


@router.get("/product/{product_id}")
def get_product_cached(product_id: int):
    """Cache-Aside 패턴: 캐시에 있으면 캐시, 없으면 DB에서 읽어 캐시에 저장

    1. Redis에서 먼저 조회한다
    2. 캐시 히트면 바로 반환한다
    3. 캐시 미스면 DB에서 읽어서 Redis에 저장한 뒤 반환한다
    TTL은 5분(300초)으로 설정한다.
    """
    start = time.time()
    cache_key = f"product:{product_id}"

    # 캐시 조회
    cached = redis_client.get(cache_key)
    if cached:
        elapsed_ms = round((time.time() - start) * 1000, 2)
        return {
            "data": json.loads(cached),
            "source": "cache",
            "elapsed_ms": elapsed_ms,
        }

    # DB 조회
    session = _Session()
    try:
        product = (
            session.query(Ch17Product)
            .filter(Ch17Product.id == product_id)
            .first()
        )
        if not product:
            return {"error": "상품 없음"}

        data = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description,
            "category": product.category,
        }

        # 캐시에 저장 (TTL 5분)
        redis_client.setex(cache_key, 300, json.dumps(data))

        elapsed_ms = round((time.time() - start) * 1000, 2)
        return {
            "data": data,
            "source": "db",
            "elapsed_ms": elapsed_ms,
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# Cache Stampede 재현 (방어 없음)
# ─────────────────────────────────────────


@router.get("/product-no-lock/{product_id}")
def get_product_stampede(product_id: int):
    """Cache Stampede 재현: TTL 만료 시 모든 요청이 동시에 DB로 몰린다

    캐시를 일부러 삭제하고, 느린 DB 쿼리를 시뮬레이션한다.
    동시에 50개의 요청이 들어오면 50개 전부 DB를 때린다.
    이것이 Cache Stampede(또는 Thundering Herd)다.
    """
    start = time.time()
    cache_key = f"product:{product_id}"

    # TTL 만료 시뮬레이션: 캐시를 삭제한다
    redis_client.delete(cache_key)

    # 모든 요청이 동시에 DB로 몰린다 - Cache Stampede
    time.sleep(0.5)  # 느린 DB 쿼리 시뮬레이션

    session = _Session()
    try:
        product = (
            session.query(Ch17Product)
            .filter(Ch17Product.id == product_id)
            .first()
        )
        if not product:
            return {"error": "상품 없음"}

        data = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description,
            "category": product.category,
        }

        # 캐시에 저장 (하지만 다른 요청도 동시에 같은 짓을 한다)
        redis_client.setex(cache_key, 300, json.dumps(data))

        elapsed_ms = round((time.time() - start) * 1000, 2)
        return {
            "data": data,
            "source": "db (stampede)",
            "elapsed_ms": elapsed_ms,
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# Cache Stampede 방어 (Mutex Lock)
# ─────────────────────────────────────────


@router.get("/product-mutex/{product_id}")
def get_product_mutex(product_id: int):
    """Mutex Lock 방어: 하나의 요청만 DB에 접근하고 나머지는 대기한다

    Redis SETNX를 이용한 분산 락이다.
    - 캐시 미스가 발생하면 락을 먼저 시도한다
    - 락을 잡은 요청만 DB에 접근해서 캐시를 채운다
    - 락을 못 잡은 요청은 잠시 대기 후 캐시를 다시 확인한다
    50개 요청 중 1개만 DB를 때린다. 나머지 49개는 캐시를 읽는다.
    """
    start = time.time()
    cache_key = f"product:{product_id}"
    lock_key = f"lock:{product_id}"

    # 캐시 조회
    cached = redis_client.get(cache_key)
    if cached:
        elapsed_ms = round((time.time() - start) * 1000, 2)
        return {
            "data": json.loads(cached),
            "source": "cache",
            "elapsed_ms": elapsed_ms,
        }

    # Mutex: 하나의 요청만 DB에 접근한다
    # SETNX: 키가 없을 때만 설정한다 (원자적 연산)
    acquired = redis_client.set(lock_key, "1", nx=True, ex=5)

    if not acquired:
        # 다른 요청이 캐시를 채우는 중, 잠시 대기 후 재시도
        time.sleep(0.1)
        cached = redis_client.get(cache_key)
        if cached:
            elapsed_ms = round((time.time() - start) * 1000, 2)
            return {
                "data": json.loads(cached),
                "source": "cache (retry)",
                "elapsed_ms": elapsed_ms,
            }
        return {"data": None, "source": "retry_failed"}

    # 락을 잡았다. DB에서 읽어서 캐시를 채운다
    try:
        time.sleep(0.5)  # 느린 DB 쿼리 시뮬레이션

        session = _Session()
        try:
            product = (
                session.query(Ch17Product)
                .filter(Ch17Product.id == product_id)
                .first()
            )
            if not product:
                return {"error": "상품 없음"}

            data = {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "description": product.description,
                "category": product.category,
            }

            # 캐시에 저장 (TTL 5분)
            redis_client.setex(cache_key, 300, json.dumps(data))

            elapsed_ms = round((time.time() - start) * 1000, 2)
            return {
                "data": data,
                "source": "db (mutex holder)",
                "elapsed_ms": elapsed_ms,
            }
        finally:
            session.close()
    finally:
        # 락 해제
        redis_client.delete(lock_key)
