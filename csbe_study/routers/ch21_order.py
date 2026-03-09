"""
Ch.21 - 테스트를 짜라고 했더니 전부 Mocking입니다

주문 API 엔드포인트.
OrderService에 DI 패턴을 적용해서
Unit Test와 Integration Test의 차이를 보여준다.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import Integer, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from service.order_service import InventoryService, OrderRepository, OrderService


# ─────────────────────────────────────────
# MySQL 연결 (docker-compose.yml의 csbe-mysql 컨테이너)
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
# ORM 모델 정의 (inline)
# ─────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class Ch21Order(Base):
    """주문 테이블"""

    __tablename__ = "ch21_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")


class Ch21Product(Base):
    """상품 테이블"""

    __tablename__ = "ch21_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ─────────────────────────────────────────
# 요청 모델
# ─────────────────────────────────────────


class CreateOrderRequest(BaseModel):
    """주문 생성 요청"""

    user_id: int
    product_name: str
    quantity: int


# ─────────────────────────────────────────
# 라우터 정의
# ─────────────────────────────────────────

router = APIRouter(prefix="/order", tags=["ch21-order"])


@router.post("/reset")
def reset_tables():
    """테이블 초기화 및 샘플 데이터 삽입

    테스트 전에 호출해서 깨끗한 상태를 만든다.
    """
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)

    session = _Session()
    try:
        # 샘플 상품 5종 삽입
        products = [
            {"name": "노트북", "stock": 100, "price": 1500000},
            {"name": "키보드", "stock": 50, "price": 150000},
            {"name": "마우스", "stock": 200, "price": 50000},
            {"name": "모니터", "stock": 30, "price": 500000},
            {"name": "헤드셋", "stock": 80, "price": 100000},
        ]
        for p in products:
            session.execute(
                text(
                    "INSERT INTO ch21_products (name, stock, price) "
                    "VALUES (:name, :stock, :price)"
                ),
                p,
            )
        session.commit()
        return {"message": "테이블 초기화 완료", "products": len(products)}
    finally:
        session.close()


@router.post("/create")
def create_order(req: CreateOrderRequest):
    """주문을 생성한다

    OrderService에 실제 Repository와 InventoryService를 주입한다.
    """
    session = _Session()
    try:
        order_repo = OrderRepository(session)
        inventory = InventoryService(session)
        service = OrderService(order_repo, inventory)

        # 상품 가격 조회
        row = session.execute(
            text("SELECT price FROM ch21_products WHERE name = :name"),
            {"name": req.product_name},
        ).fetchone()
        if row is None:
            return {"success": False, "reason": f"상품 '{req.product_name}'이 없다"}
        price = row[0]

        result = service.create_order(
            user_id=req.user_id,
            product_name=req.product_name,
            quantity=req.quantity,
            price=price,
        )
        return result
    finally:
        session.close()


@router.get("/{order_id}")
def get_order(order_id: int):
    """주문을 조회한다"""
    session = _Session()
    try:
        order_repo = OrderRepository(session)
        inventory = InventoryService(session)
        service = OrderService(order_repo, inventory)

        order = service.get_order(order_id)
        if order is None:
            return {"error": "주문을 찾을 수 없다", "order_id": order_id}
        return order
    finally:
        session.close()


@router.get("/user/{user_id}")
def get_user_orders(user_id: int):
    """사용자의 주문 목록을 조회한다"""
    session = _Session()
    try:
        order_repo = OrderRepository(session)
        inventory = InventoryService(session)
        service = OrderService(order_repo, inventory)

        orders = service.get_user_orders(user_id)
        return {"user_id": user_id, "orders": orders, "count": len(orders)}
    finally:
        session.close()
