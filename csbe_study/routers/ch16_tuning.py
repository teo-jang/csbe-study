"""
Ch.16 - DB 성능 튜닝의 실무
Slow Query 하나가 전체 DB를 먹통으로 만들 수 있다.

이 라우터는 Offset Pagination과 Cursor-based Pagination의
성능 차이를 직접 비교한다.

Offset이 커질수록 DB는 앞의 데이터를 모두 읽고 버려야 한다.
Cursor 방식은 WHERE 조건으로 시작점을 지정하므로
페이지 번호와 무관하게 일정한 성능을 낸다.
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

router = APIRouter(prefix="/tuning", tags=["ch16-tuning"])


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
# 테이블 초기화 + 시드 데이터 (10만 건)
# ─────────────────────────────────────────


@router.post("/reset")
def reset_table():
    """테이블을 초기화하고 10만 건의 시드 데이터를 삽입한다

    1000건씩 배치로 INSERT한다.
    created_at에 인덱스를 걸어둔다 (Pagination 비교를 위해).
    """
    with _engine.connect() as conn:
        # 기존 테이블 삭제
        conn.execute(text("DROP TABLE IF EXISTS ch16_orders"))

        # 테이블 생성
        conn.execute(
            text(
                "CREATE TABLE ch16_orders ("
                "  id INT AUTO_INCREMENT PRIMARY KEY,"
                "  user_id INT NOT NULL,"
                "  product_title VARCHAR(200) NOT NULL,"
                "  amount INT NOT NULL,"
                "  created_at DATETIME NOT NULL,"
                "  INDEX idx_ch16_created_id (created_at DESC, id DESC)"
                ")"
            )
        )
        conn.commit()

    # 시드 데이터 삽입
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    total_seconds = int((now - one_year_ago).total_seconds())
    total_rows = 100000
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
                        "user_id": random.randint(1, 5000),
                        "product_title": random.choice(PRODUCT_TITLES),
                        "amount": random.randint(10000, 2000000),
                        "created_at": created_at,
                    }
                )

            session.execute(
                text(
                    "INSERT INTO ch16_orders (user_id, product_title, amount, created_at) "
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
# Offset Pagination
# ─────────────────────────────────────────


@router.get("/orders-offset")
def get_orders_offset(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    """Offset 기반 Pagination

    OFFSET = (page - 1) * size
    페이지 번호가 커질수록 앞의 데이터를 모두 스캔하고 버려야 한다.
    page=4990이면 약 99,800건을 읽고 버린 뒤 20건만 반환한다.
    이것이 Slow Query의 대표적인 원인이다.
    """
    offset = (page - 1) * size

    session = _Session()
    try:
        result = session.execute(
            text(
                "SELECT id, user_id, product_title, amount, created_at "
                "FROM ch16_orders "
                "ORDER BY created_at DESC "
                "LIMIT :size OFFSET :offset"
            ),
            {"size": size, "offset": offset},
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
            "pagination": "offset",
            "page": page,
            "size": size,
            "offset": offset,
            "count": len(rows),
            "orders": rows,
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# Cursor-based Pagination
# ─────────────────────────────────────────


@router.get("/orders-cursor")
def get_orders_cursor(
    last_created_at: Optional[str] = Query(default=None),
    last_id: Optional[int] = Query(default=None),
    size: int = Query(default=20, ge=1, le=100),
):
    """Cursor 기반 Pagination

    WHERE (created_at, id) < (:last_created_at, :last_id) 조건으로
    마지막으로 본 데이터 다음부터 가져온다.
    인덱스를 타므로 페이지 위치와 무관하게 일정한 성능을 낸다.

    첫 페이지는 last_created_at, last_id 없이 호출한다.
    """
    session = _Session()
    try:
        if last_created_at is not None and last_id is not None:
            # 2번째 이후 페이지: 커서 기준으로 다음 데이터를 가져온다
            result = session.execute(
                text(
                    "SELECT id, user_id, product_title, amount, created_at "
                    "FROM ch16_orders "
                    "WHERE (created_at < :last_created_at) "
                    "   OR (created_at = :last_created_at AND id < :last_id) "
                    "ORDER BY created_at DESC, id DESC "
                    "LIMIT :size"
                ),
                {
                    "last_created_at": last_created_at,
                    "last_id": last_id,
                    "size": size,
                },
            )
        else:
            # 첫 페이지: 가장 최신 데이터부터
            result = session.execute(
                text(
                    "SELECT id, user_id, product_title, amount, created_at "
                    "FROM ch16_orders "
                    "ORDER BY created_at DESC, id DESC "
                    "LIMIT :size"
                ),
                {"size": size},
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

        # 다음 페이지를 위한 커서 정보
        next_cursor = None
        if rows:
            last_row = rows[-1]
            next_cursor = {
                "last_created_at": last_row["created_at"],
                "last_id": last_row["id"],
            }

        return {
            "pagination": "cursor",
            "size": size,
            "count": len(rows),
            "next_cursor": next_cursor,
            "orders": rows,
        }
    finally:
        session.close()
