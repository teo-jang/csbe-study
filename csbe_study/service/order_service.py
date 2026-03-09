"""
Ch.21 - 테스트를 짜라고 했더니 전부 Mocking입니다

OrderService는 DI(Dependency Injection) 패턴으로 설계되어 있다.
외부 의존성(DB, 결제)을 생성자로 주입받기 때문에
Unit Test에서 Mock으로 교체할 수 있고,
Integration Test에서는 실제 구현체를 넣을 수 있다.
"""


class OrderRepository:
    """주문 저장소 인터페이스 (실제로는 DB 접근)"""

    def __init__(self, session):
        self._session = session

    def save(self, order_data: dict) -> dict:
        """주문을 DB에 저장한다"""
        from sqlalchemy import text

        result = self._session.execute(
            text(
                "INSERT INTO ch21_orders (user_id, product_name, quantity, total_price, status) "
                "VALUES (:user_id, :product_name, :quantity, :total_price, :status)"
            ),
            order_data,
        )
        self._session.commit()
        return {**order_data, "id": result.lastrowid}

    def find_by_id(self, order_id: int) -> dict | None:
        """주문 ID로 조회한다"""
        from sqlalchemy import text

        row = self._session.execute(
            text("SELECT * FROM ch21_orders WHERE id = :id"),
            {"id": order_id},
        ).fetchone()
        if row is None:
            return None
        return dict(row._mapping)

    def find_by_user_id(self, user_id: int) -> list[dict]:
        """사용자 ID로 주문 목록을 조회한다"""
        from sqlalchemy import text

        rows = self._session.execute(
            text(
                "SELECT * FROM ch21_orders WHERE user_id = :user_id ORDER BY id DESC"
            ),
            {"user_id": user_id},
        ).fetchall()
        return [dict(r._mapping) for r in rows]


class InventoryService:
    """재고 관리 서비스"""

    def __init__(self, session):
        self._session = session

    def check_stock(self, product_name: str) -> int:
        """재고를 확인한다"""
        from sqlalchemy import text

        row = self._session.execute(
            text("SELECT stock FROM ch21_products WHERE name = :name"),
            {"name": product_name},
        ).fetchone()
        if row is None:
            return 0
        return row[0]

    def decrease_stock(self, product_name: str, quantity: int) -> bool:
        """재고를 차감한다"""
        from sqlalchemy import text

        result = self._session.execute(
            text(
                "UPDATE ch21_products SET stock = stock - :qty "
                "WHERE name = :name AND stock >= :qty"
            ),
            {"name": product_name, "qty": quantity},
        )
        self._session.commit()
        return result.rowcount > 0


class OrderService:
    """주문 서비스 - DI 패턴

    외부 의존성을 생성자로 주입받는다.
    테스트 시 Mock 객체를 넣을 수 있다.
    """

    def __init__(self, order_repo: OrderRepository, inventory: InventoryService):
        self._order_repo = order_repo
        self._inventory = inventory

    def create_order(
        self, user_id: int, product_name: str, quantity: int, price: int
    ) -> dict:
        """주문을 생성한다

        1. 재고 확인
        2. 재고 차감
        3. 주문 저장
        """
        # 1. 재고 확인
        stock = self._inventory.check_stock(product_name)
        if stock < quantity:
            return {
                "success": False,
                "reason": f"재고 부족 (현재: {stock}, 요청: {quantity})",
            }

        # 2. 재고 차감
        decreased = self._inventory.decrease_stock(product_name, quantity)
        if not decreased:
            return {
                "success": False,
                "reason": "재고 차감 실패 (동시 요청으로 재고 소진)",
            }

        # 3. 주문 저장
        total_price = price * quantity
        order = self._order_repo.save(
            {
                "user_id": user_id,
                "product_name": product_name,
                "quantity": quantity,
                "total_price": total_price,
                "status": "completed",
            }
        )

        return {"success": True, "order": order}

    def get_order(self, order_id: int) -> dict | None:
        """주문을 조회한다"""
        return self._order_repo.find_by_id(order_id)

    def get_user_orders(self, user_id: int) -> list[dict]:
        """사용자의 주문 목록을 조회한다"""
        return self._order_repo.find_by_user_id(user_id)
