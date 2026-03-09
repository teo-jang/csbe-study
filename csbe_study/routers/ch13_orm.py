"""
Ch.13 - ORM과 N+1 문제
JPA를 써서 DB를 모른다고요? - SQL과 ORM의 관계

ORM이 생성하는 SQL을 읽을 줄 모르면
N+1 같은 문제를 운영에서 발견하게 된다.

이 라우터는 Lazy Loading(N+1)과 Eager Loading(joinedload, subqueryload)의
성능 차이를 직접 비교해볼 수 있도록 만들어졌다.
"""

import random

from fastapi import APIRouter
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, text
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    sessionmaker,
    joinedload,
    subqueryload,
)

router = APIRouter(prefix="/orm", tags=["ch13-orm"])


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
# ORM 모델 정의
# User(1) : Order(N) 관계
# ─────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class Ch13User(Base):
    """사용자 테이블"""

    __tablename__ = "ch13_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)

    # Lazy Loading이 기본값이다
    # user.orders에 접근할 때마다 SELECT가 발생한다 (N+1의 원인)
    orders = relationship("Ch13Order", back_populates="user", lazy="select")


class Ch13Order(Base):
    """주문 테이블"""

    __tablename__ = "ch13_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("ch13_users.id"), nullable=False)
    product = Column(String(100), nullable=False)
    amount = Column(Integer, nullable=False)

    user = relationship("Ch13User", back_populates="orders")


# ─────────────────────────────────────────
# 테이블 초기화 + 시드 데이터
# ─────────────────────────────────────────

PRODUCTS = [
    "노트북",
    "키보드",
    "마우스",
    "모니터",
    "헤드셋",
    "웹캠",
    "USB허브",
    "SSD",
    "RAM",
    "충전기",
]


@router.post("/reset")
def reset_tables():
    """테이블을 초기화하고 시드 데이터를 삽입한다

    100명의 User, 각 User당 5건의 Order = 총 500건
    """
    # 기존 테이블 삭제 후 재생성
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)

    session = _Session()
    try:
        # 100명의 User 생성
        users = []
        for i in range(1, 101):
            user = Ch13User(
                name=f"user_{i:03d}",
                email=f"user_{i:03d}@example.com",
            )
            users.append(user)

        session.add_all(users)
        session.flush()  # ID 할당을 위해 flush

        # 각 User당 5건의 Order 생성
        orders = []
        for user in users:
            for _ in range(5):
                order = Ch13Order(
                    user_id=user.id,
                    product=random.choice(PRODUCTS),
                    amount=random.randint(10000, 500000),
                )
                orders.append(order)

        session.add_all(orders)
        session.commit()

        return {
            "message": "테이블 초기화 완료",
            "users": len(users),
            "orders": len(orders),
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()


# ─────────────────────────────────────────
# Lazy Loading (N+1 발생)
# ─────────────────────────────────────────


@router.get("/lazy")
def get_users_lazy():
    """Lazy Loading: User를 가져온 뒤 루프에서 orders에 접근한다

    1번의 SELECT로 User 100명을 가져온 뒤,
    각 User의 orders에 접근할 때마다 SELECT가 1번씩 추가 발생한다.
    총 101번의 쿼리가 실행된다 (1 + N = 1 + 100 = 101).
    이것이 N+1 문제다.
    """
    session = _Session()
    try:
        # 1번째 쿼리: SELECT * FROM ch13_users
        users = session.query(Ch13User).all()

        result = []
        for user in users:
            # N번의 추가 쿼리: SELECT * FROM ch13_orders WHERE user_id = :id
            # user.orders에 접근할 때마다 Lazy Loading이 발동한다
            order_count = len(user.orders)
            total_amount = sum(o.amount for o in user.orders)
            result.append(
                {
                    "user_id": user.id,
                    "name": user.name,
                    "order_count": order_count,
                    "total_amount": total_amount,
                }
            )

        return {
            "strategy": "lazy",
            "user_count": len(result),
            "description": "N+1 발생: 1(User) + 100(Order) = 101 쿼리",
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# Eager Loading - joinedload (JOIN 1회)
# ─────────────────────────────────────────


@router.get("/eager-join")
def get_users_eager_join():
    """joinedload: LEFT OUTER JOIN으로 한 번에 가져온다

    SELECT users LEFT OUTER JOIN orders ON users.id = orders.user_id
    단 1번의 쿼리로 User + Order를 모두 가져온다.
    N+1 문제가 발생하지 않는다.
    """
    session = _Session()
    try:
        # 1번의 쿼리: SELECT ... FROM ch13_users LEFT OUTER JOIN ch13_orders ...
        users = (
            session.query(Ch13User).options(joinedload(Ch13User.orders)).all()
        )

        result = []
        for user in users:
            # 이미 JOIN으로 데이터를 가져왔으므로 추가 쿼리 없음
            order_count = len(user.orders)
            total_amount = sum(o.amount for o in user.orders)
            result.append(
                {
                    "user_id": user.id,
                    "name": user.name,
                    "order_count": order_count,
                    "total_amount": total_amount,
                }
            )

        return {
            "strategy": "eager-join (joinedload)",
            "user_count": len(result),
            "description": "JOIN 1회로 해결: 쿼리 1번",
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# Eager Loading - subqueryload (서브쿼리 2회)
# ─────────────────────────────────────────


@router.get("/eager-subquery")
def get_users_eager_subquery():
    """subqueryload: User 쿼리 + Order 서브쿼리, 총 2번

    1번: SELECT * FROM ch13_users
    2번: SELECT * FROM ch13_orders WHERE user_id IN (SELECT id FROM ch13_users)
    N+1은 아니지만 JOIN보다 쿼리가 1번 더 나간다.
    데이터가 많을 때 JOIN보다 유리할 수 있다 (Cartesian Product 방지).
    """
    session = _Session()
    try:
        # 2번의 쿼리: User SELECT + Order 서브쿼리 SELECT
        users = (
            session.query(Ch13User)
            .options(subqueryload(Ch13User.orders))
            .all()
        )

        result = []
        for user in users:
            # 서브쿼리로 이미 로딩 완료, 추가 쿼리 없음
            order_count = len(user.orders)
            total_amount = sum(o.amount for o in user.orders)
            result.append(
                {
                    "user_id": user.id,
                    "name": user.name,
                    "order_count": order_count,
                    "total_amount": total_amount,
                }
            )

        return {
            "strategy": "eager-subquery (subqueryload)",
            "user_count": len(result),
            "description": "서브쿼리 2회로 해결: 쿼리 2번",
        }
    finally:
        session.close()
