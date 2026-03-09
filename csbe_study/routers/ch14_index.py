"""
Ch.14 - 인덱스를 안 걸어놓고 Redis를 설치했습니다
성능 문제의 원인을 정확히 진단하지 않으면
엉뚱한 해결책을 적용하게 된다.

이 라우터는 인덱스 유무에 따른 쿼리 성능 차이를 직접 측정한다.
EXPLAIN으로 실행 계획을 확인하고,
인덱스 추가/삭제 전후 성능을 비교할 수 있다.
"""

import random
from datetime import datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

router = APIRouter(prefix="/index", tags=["ch14-index"])


# ─────────────────────────────────────────
# MySQL 연결 정보
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
# ORM 모델 정의
# ─────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class Ch14Order(Base):
    """주문 테이블 (인덱스 성능 테스트용)

    5만 건의 데이터를 넣고, 인덱스 유무에 따른 조회 성능을 비교한다.
    """

    __tablename__ = "ch14_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    product_title = Column(String(200), nullable=False)
    amount = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)


# ─────────────────────────────────────────
# 시드 데이터용 상수
# ─────────────────────────────────────────

PRODUCT_TITLES = [
    "맥북 프로 14인치",
    "삼성 갤럭시 S24",
    "아이패드 에어",
    "로지텍 MX Keys",
    "소니 WH-1000XM5",
    "LG 울트라와이드 모니터",
    "애플 매직 마우스",
    "레노버 씽크패드",
    "다이슨 에어랩",
    "닌텐도 스위치",
    "에어팟 프로 2세대",
    "삼성 오디세이 모니터",
    "키크론 K8 프로",
    "라즈베리 파이 5",
    "아이폰 15 프로",
]


# ─────────────────────────────────────────
# 테이블 초기화 + 시드 데이터 (5만 건)
# ─────────────────────────────────────────


@router.post("/reset")
def reset_table():
    """테이블을 초기화하고 5만 건의 시드 데이터를 삽입한다

    1000건씩 배치로 INSERT한다.
    user_id는 1~1000 범위, created_at은 최근 1년 범위.
    """
    # 기존 테이블 삭제 후 재생성
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)

    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    total_seconds = int((now - one_year_ago).total_seconds())
    total_rows = 50000
    batch_size = 1000

    session = _Session()
    try:
        for batch_start in range(0, total_rows, batch_size):
            rows = []
            for _ in range(batch_size):
                random_seconds = random.randint(0, total_seconds)
                created_at = one_year_ago + timedelta(seconds=random_seconds)
                rows.append(
                    {
                        "user_id": random.randint(1, 1000),
                        "product_title": random.choice(PRODUCT_TITLES),
                        "amount": random.randint(10000, 2000000),
                        "created_at": created_at,
                    }
                )

            # bulk insert: executemany 방식
            session.execute(
                text(
                    "INSERT INTO ch14_orders (user_id, product_title, amount, created_at) "
                    "VALUES (:user_id, :product_title, :amount, :created_at)"
                ),
                rows,
            )

        session.commit()
        return {
            "message": "테이블 초기화 완료",
            "total_rows": total_rows,
            "batch_size": batch_size,
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()


# ─────────────────────────────────────────
# 주문 조회 (인덱스 성능 테스트)
# ─────────────────────────────────────────


@router.get("/orders/{user_id}")
def get_orders_by_user(user_id: int):
    """특정 사용자의 최근 주문 20건을 조회한다

    인덱스가 없으면 Full Table Scan이 발생한다.
    인덱스가 있으면 Index Scan으로 빠르게 찾는다.
    """
    session = _Session()
    try:
        result = session.execute(
            text(
                "SELECT id, user_id, product_title, amount, created_at "
                "FROM ch14_orders "
                "WHERE user_id = :uid "
                "ORDER BY created_at DESC "
                "LIMIT 20"
            ),
            {"uid": user_id},
        )
        rows = [
            {
                "id": row[0],
                "user_id": row[1],
                "product_title": row[2],
                "amount": row[3],
                "created_at": str(row[4]),
            }
            for row in result.fetchall()
        ]
        return {
            "user_id": user_id,
            "count": len(rows),
            "orders": rows,
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# EXPLAIN (실행 계획 확인)
# ─────────────────────────────────────────


@router.get("/explain/{user_id}")
def explain_query(user_id: int):
    """EXPLAIN으로 실행 계획을 확인한다

    인덱스가 없으면 type=ALL (Full Table Scan)
    인덱스가 있으면 type=ref (Index Scan)
    """
    session = _Session()
    try:
        result = session.execute(
            text(
                "EXPLAIN SELECT id, user_id, product_title, amount, created_at "
                "FROM ch14_orders "
                "WHERE user_id = :uid "
                "ORDER BY created_at DESC "
                "LIMIT 20"
            ),
            {"uid": user_id},
        )
        rows = result.fetchall()
        columns = result.keys()

        explain_rows = []
        for row in rows:
            explain_rows.append(dict(zip(columns, row)))

        return {
            "user_id": user_id,
            "explain": explain_rows,
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# 인덱스 추가/삭제
# ─────────────────────────────────────────


@router.post("/add-index")
def add_single_index():
    """user_id에 단일 인덱스를 추가한다

    WHERE user_id = ? 조건에서 Index Scan이 가능해진다.
    하지만 ORDER BY created_at DESC는 filesort가 여전히 필요하다.
    """
    with _engine.connect() as conn:
        try:
            conn.execute(
                text(
                    "ALTER TABLE ch14_orders "
                    "ADD INDEX idx_ch14_user_id (user_id)"
                )
            )
            conn.commit()
            return {"message": "단일 인덱스 추가 완료: idx_ch14_user_id (user_id)"}
        except Exception as e:
            return {"error": str(e)}


@router.post("/add-composite-index")
def add_composite_index():
    """user_id + created_at 복합 인덱스를 추가한다

    WHERE user_id = ? ORDER BY created_at DESC를 인덱스만으로 처리한다.
    Covering Index에 가까운 효과를 낸다.
    """
    with _engine.connect() as conn:
        try:
            conn.execute(
                text(
                    "ALTER TABLE ch14_orders "
                    "ADD INDEX idx_ch14_user_created (user_id, created_at DESC)"
                )
            )
            conn.commit()
            return {
                "message": "복합 인덱스 추가 완료: idx_ch14_user_created (user_id, created_at DESC)"
            }
        except Exception as e:
            return {"error": str(e)}


@router.post("/drop-indexes")
def drop_indexes():
    """추가한 인덱스를 모두 삭제한다

    Full Table Scan 상태로 되돌린다.
    """
    dropped = []
    errors = []

    with _engine.connect() as conn:
        # 현재 인덱스 목록 조회
        result = conn.execute(
            text("SHOW INDEX FROM ch14_orders WHERE Key_name != 'PRIMARY'")
        )
        index_names = list(set(row[2] for row in result.fetchall()))

        for idx_name in index_names:
            try:
                conn.execute(
                    text(f"DROP INDEX `{idx_name}` ON ch14_orders")
                )
                dropped.append(idx_name)
            except Exception as e:
                errors.append({"index": idx_name, "error": str(e)})

        conn.commit()

    return {
        "message": "인덱스 삭제 완료",
        "dropped": dropped,
        "errors": errors,
    }
