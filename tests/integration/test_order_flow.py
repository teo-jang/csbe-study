"""
Ch.21 - Integration Test (실제 DB 사용)

Mock 없이 실제 MySQL에 연결해서 테스트한다.
Unit Test에서 못 잡는 문제를 여기서 잡는다:
- DB 스키마와 코드의 불일치
- SQL 문법 오류
- 트랜잭션 동작
"""
import pytest

from service.order_service import InventoryService, OrderRepository, OrderService


@pytest.mark.integration
class TestOrderFlow:
    """주문 생성부터 조회까지 전체 흐름을 테스트한다"""

    def test_create_and_get_order(self, db_session, setup_tables):
        """주문 생성 후 조회가 되는지 확인한다"""
        order_repo = OrderRepository(db_session)
        inventory = InventoryService(db_session)
        service = OrderService(order_repo, inventory)

        # 주문 생성
        result = service.create_order(
            user_id=1, product_name="키보드", quantity=2, price=150000
        )
        assert result["success"] is True
        order_id = result["order"]["id"]

        # 주문 조회
        order = service.get_order(order_id)
        assert order is not None
        assert order["product_name"] == "키보드"
        assert order["quantity"] == 2
        assert order["total_price"] == 300000

    def test_stock_decreases_after_order(self, db_session, setup_tables):
        """주문 후 재고가 줄어드는지 확인한다"""
        order_repo = OrderRepository(db_session)
        inventory = InventoryService(db_session)
        service = OrderService(order_repo, inventory)

        # 초기 재고 확인
        initial_stock = inventory.check_stock("키보드")
        assert initial_stock == 50

        # 주문 생성
        service.create_order(
            user_id=1, product_name="키보드", quantity=3, price=150000
        )

        # 재고 감소 확인
        remaining_stock = inventory.check_stock("키보드")
        assert remaining_stock == 47

    def test_order_fails_when_out_of_stock(self, db_session, setup_tables):
        """재고보다 많은 수량을 주문하면 실패하는지 확인한다"""
        order_repo = OrderRepository(db_session)
        inventory = InventoryService(db_session)
        service = OrderService(order_repo, inventory)

        result = service.create_order(
            user_id=1, product_name="키보드", quantity=999, price=150000
        )
        assert result["success"] is False
