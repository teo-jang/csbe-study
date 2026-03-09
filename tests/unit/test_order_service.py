"""
Ch.21 - Unit Test (Mock 사용)

OrderService의 비즈니스 로직만 테스트한다.
DB나 외부 서비스는 Mock으로 대체한다.

이 테스트의 한계:
- Mock이 실제 DB 동작을 100% 재현하지 못한다
- DB 스키마 변경 시 Mock은 알려주지 않는다
- 그래서 Integration Test도 반드시 필요하다
"""
from unittest.mock import MagicMock

from service.order_service import OrderService


def test_create_order_success():
    """재고가 충분할 때 주문이 성공하는지 확인한다"""
    mock_order_repo = MagicMock()
    mock_inventory = MagicMock()

    # Mock 설정: 재고 100, 차감 성공
    mock_inventory.check_stock.return_value = 100
    mock_inventory.decrease_stock.return_value = True
    mock_order_repo.save.return_value = {
        "id": 1,
        "user_id": 1,
        "product_name": "노트북",
        "quantity": 2,
        "total_price": 3000000,
        "status": "completed",
    }

    service = OrderService(mock_order_repo, mock_inventory)
    result = service.create_order(
        user_id=1, product_name="노트북", quantity=2, price=1500000
    )

    assert result["success"] is True
    assert result["order"]["total_price"] == 3000000
    mock_inventory.check_stock.assert_called_once_with("노트북")
    mock_inventory.decrease_stock.assert_called_once_with("노트북", 2)


def test_create_order_insufficient_stock():
    """재고가 부족할 때 주문이 실패하는지 확인한다"""
    mock_order_repo = MagicMock()
    mock_inventory = MagicMock()

    # Mock 설정: 재고 1개뿐
    mock_inventory.check_stock.return_value = 1

    service = OrderService(mock_order_repo, mock_inventory)
    result = service.create_order(
        user_id=1, product_name="노트북", quantity=5, price=1500000
    )

    assert result["success"] is False
    assert "재고 부족" in result["reason"]
    # 재고 차감 시도 자체를 하지 않아야 한다
    mock_inventory.decrease_stock.assert_not_called()


def test_create_order_concurrent_stock_depletion():
    """동시 요청으로 재고 차감이 실패하는 경우를 테스트한다"""
    mock_order_repo = MagicMock()
    mock_inventory = MagicMock()

    # 재고 확인 시점에는 있지만, 차감 시점에는 다른 요청이 먼저 가져감
    mock_inventory.check_stock.return_value = 1
    mock_inventory.decrease_stock.return_value = False  # 동시 요청으로 실패

    service = OrderService(mock_order_repo, mock_inventory)
    result = service.create_order(
        user_id=1, product_name="노트북", quantity=1, price=1500000
    )

    assert result["success"] is False
    assert "재고 차감 실패" in result["reason"]
