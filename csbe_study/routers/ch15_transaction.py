"""
Ch.15 - Transaction과 Isolation Level
동시 요청 환경에서 데이터 정합성을 지키려면
Isolation Level을 이해해야 한다.

이 라우터는 동시 주문 시나리오에서
Race Condition, Pessimistic Locking, Optimistic Locking의
차이를 직접 재현한다.

Ch.5의 threading Lock이 애플리케이션 레벨이었다면,
여기서는 DB 레벨에서 동시성을 제어한다.
"""

import time

from fastapi import APIRouter
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

router = APIRouter(prefix="/tx", tags=["ch15-transaction"])


# ─────────────────────────────────────────
# MySQL 연결 정보
# ─────────────────────────────────────────

MYSQL_URL = "mysql+pymysql://root:csbe@localhost:3306/csbe_study"

_engine = create_engine(
    MYSQL_URL,
    pool_size=30,
    max_overflow=10,
    pool_recycle=3600,
)

_Session = sessionmaker(bind=_engine)


# ─────────────────────────────────────────
# ORM 모델 정의
# ─────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class Ch15Product(Base):
    """상품 테이블 (동시성 테스트용)

    stock: 재고 수량
    version: Optimistic Locking용 버전 번호
    """

    __tablename__ = "ch15_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=0)


# ─────────────────────────────────────────
# 테이블 초기화
# ─────────────────────────────────────────


@router.post("/reset")
def reset_product():
    """상품 테이블을 초기화한다

    상품 1개, 재고 10개, 버전 0으로 세팅한다.
    """
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)

    session = _Session()
    try:
        product = Ch15Product(name="한정판 키보드", stock=10, version=0)
        session.add(product)
        session.commit()
        return {
            "message": "상품 초기화 완료",
            "product": product.name,
            "stock": product.stock,
            "version": product.version,
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()


# ─────────────────────────────────────────
# 현재 재고 조회
# ─────────────────────────────────────────


@router.get("/stock")
def get_stock():
    """현재 재고를 조회한다"""
    session = _Session()
    try:
        result = session.execute(
            text(
                "SELECT id, name, stock, version "
                "FROM ch15_products WHERE id = 1"
            )
        )
        row = result.fetchone()
        if row is None:
            return {"error": "상품이 없다. /tx/reset을 먼저 호출해라."}
        return {
            "id": row[0],
            "name": row[1],
            "stock": row[2],
            "version": row[3],
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# Naive 방식 (Race Condition 발생)
# ─────────────────────────────────────────


@router.post("/purchase-naive")
def purchase_naive():
    """아무런 동시성 제어 없이 구매한다 (Race Condition 발생)

    1) SELECT로 재고를 읽는다
    2) sleep(0.05)으로 Race Window를 만든다
    3) stock -= 1로 차감한다

    20명이 동시에 요청하면, 10개 재고인데 20명 전부 "재고 있음"으로 읽고
    마이너스까지 내려갈 수 있다.
    """
    session = _Session()
    try:
        # 1) 재고를 읽는다 (이 시점의 값은 stale해질 수 있다)
        result = session.execute(
            text("SELECT stock FROM ch15_products WHERE id = 1")
        )
        row = result.fetchone()
        if row is None:
            return {"error": "상품이 없다"}

        current_stock = row[0]

        # 2) 인위적 지연: 다른 트랜잭션이 끼어들 수 있는 시간
        time.sleep(0.05)

        # 3) 재고 확인 후 차감
        if current_stock <= 0:
            return {"result": "sold_out", "stock": current_stock}

        session.execute(
            text(
                "UPDATE ch15_products SET stock = stock - 1 WHERE id = 1"
            )
        )
        session.commit()

        # 차감 후 재고 확인
        result = session.execute(
            text("SELECT stock FROM ch15_products WHERE id = 1")
        )
        new_stock = result.fetchone()[0]

        return {"result": "purchased", "stock": new_stock}
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()


# ─────────────────────────────────────────
# Pessimistic Locking (SELECT ... FOR UPDATE)
# ─────────────────────────────────────────


@router.post("/purchase-pessimistic")
def purchase_pessimistic():
    """SELECT ... FOR UPDATE로 행을 잠그고 구매한다 (Pessimistic Locking)

    FOR UPDATE가 걸린 행은 다른 트랜잭션이 읽거나 쓸 수 없다.
    잠금을 획득한 트랜잭션만 재고를 조회하고 차감할 수 있으므로
    Race Condition이 발생하지 않는다.

    단점: Lock 대기 시간이 길어질 수 있다.
    """
    session = _Session()
    try:
        # FOR UPDATE: 이 행에 배타적 잠금을 건다
        # 다른 트랜잭션은 이 잠금이 풀릴 때까지 대기한다
        result = session.execute(
            text(
                "SELECT stock FROM ch15_products WHERE id = 1 FOR UPDATE"
            )
        )
        row = result.fetchone()
        if row is None:
            return {"error": "상품이 없다"}

        current_stock = row[0]

        # 인위적 지연이 있어도 Lock이 걸려 있으므로 안전하다
        time.sleep(0.05)

        if current_stock <= 0:
            session.commit()  # Lock 해제를 위해 commit
            return {"result": "sold_out", "stock": current_stock}

        session.execute(
            text(
                "UPDATE ch15_products SET stock = stock - 1 WHERE id = 1"
            )
        )
        session.commit()

        # 차감 후 재고 확인
        result = session.execute(
            text("SELECT stock FROM ch15_products WHERE id = 1")
        )
        new_stock = result.fetchone()[0]

        return {"result": "purchased", "stock": new_stock}
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()


# ─────────────────────────────────────────
# Optimistic Locking (version 기반)
# ─────────────────────────────────────────


@router.post("/purchase-optimistic")
def purchase_optimistic():
    """version 칼럼을 이용한 Optimistic Locking으로 구매한다

    1) SELECT로 stock과 version을 읽는다
    2) UPDATE 시 WHERE version = :ver 조건을 건다
    3) 다른 트랜잭션이 먼저 version을 올렸으면 rowcount == 0 → 재시도 or 실패

    Lock을 잡지 않으므로 대기 시간이 없다.
    대신 충돌 시 재시도 비용이 발생한다.
    """
    max_retries = 3
    session = _Session()

    try:
        for attempt in range(max_retries):
            # 1) 현재 stock과 version을 읽는다
            result = session.execute(
                text(
                    "SELECT stock, version FROM ch15_products WHERE id = 1"
                )
            )
            row = result.fetchone()
            if row is None:
                return {"error": "상품이 없다"}

            current_stock = row[0]
            current_version = row[1]

            # 인위적 지연
            time.sleep(0.05)

            if current_stock <= 0:
                return {"result": "sold_out", "stock": current_stock}

            # 2) version이 변하지 않았을 때만 UPDATE
            result = session.execute(
                text(
                    "UPDATE ch15_products "
                    "SET stock = stock - 1, version = version + 1 "
                    "WHERE id = 1 AND version = :ver"
                ),
                {"ver": current_version},
            )

            if result.rowcount == 1:
                # 3) 성공: version이 안 바뀌었다 = 충돌 없음
                session.commit()

                # 차감 후 재고 확인
                result = session.execute(
                    text(
                        "SELECT stock, version FROM ch15_products WHERE id = 1"
                    )
                )
                new_row = result.fetchone()
                return {
                    "result": "purchased",
                    "stock": new_row[0],
                    "version": new_row[1],
                    "attempts": attempt + 1,
                }
            else:
                # rowcount == 0: 다른 트랜잭션이 먼저 version을 올렸다
                session.rollback()
                # 재시도

        # 최대 재시도 초과
        return {
            "result": "conflict",
            "message": f"{max_retries}회 재시도 실패 (다른 요청과 충돌)",
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()
