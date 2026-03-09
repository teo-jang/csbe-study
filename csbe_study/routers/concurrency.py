import time
import threading

from fastapi import APIRouter

router = APIRouter(prefix="/concurrency", tags=["concurrency"])


# ─────────────────────────────────────────
# 공유 상태 (모듈 레벨 = Heap에 위치)
# ─────────────────────────────────────────

# 사례 A: 재고 관리
_inventory = {
    "stock": 100,
    "success_count": 0,
    "fail_count": 0,
}
_inventory_lock = threading.Lock()

# 사례 B: 창고 간 이동
_warehouses = {
    "A": {"stock": 100, "lock": threading.Lock()},
    "B": {"stock": 100, "lock": threading.Lock()},
}
_warehouse_stats = {
    "success_count": 0,
    "deadlock_count": 0,
}
_warehouse_stats_lock = threading.Lock()


# ─────────────────────────────────────────
# 사례 A: Race Condition (재고 관리)
# ─────────────────────────────────────────


@router.post("/inventory/reset")
def inventory_reset(stock: int = 100):
    """재고를 초기값으로 리셋한다

    주의: 테스트 시작 전 setup()에서만 호출해야 한다.
    테스트 중 호출하면 Race Condition이 발생할 수 있다.
    """
    _inventory["stock"] = stock
    _inventory["success_count"] = 0
    _inventory["fail_count"] = 0
    return {"stock": stock, "message": "재고가 리셋되었다"}


@router.post("/inventory/purchase-unsafe")
def purchase_unsafe(quantity: int = 1):
    """Lock 없이 재고를 차감한다 (Race Condition 발생)

    읽기 → 체크 → 쓰기 사이에 다른 스레드가 끼어들 수 있다.
    time.sleep()은 GIL을 해제하므로 Race Window가 확실히 열린다.
    """
    # 1) 현재 재고를 읽는다
    current_stock = _inventory["stock"]

    # 2) 인위적 지연: Race Window를 넓힌다
    #    time.sleep()은 GIL을 해제한다 → 다른 스레드가 실행된다
    time.sleep(0.01)

    # 3) 재고 체크 (stale 값으로 비교 → 이미 0인데도 통과할 수 있다)
    if current_stock >= quantity:
        # 4) 차감: 현재 stock에서 빼기 때문에 음수까지 내려갈 수 있다
        #    current_stock은 오래된 값이지만, -= 는 실제 현재 값에서 뺀다
        _inventory["stock"] -= quantity
        _inventory["success_count"] += 1
        return {
            "result": "success",
            "purchased": quantity,
            "remaining_stock": _inventory["stock"],
        }
    else:
        _inventory["fail_count"] += 1
        return {
            "result": "sold_out",
            "remaining_stock": _inventory["stock"],
        }


@router.post("/inventory/purchase-safe")
def purchase_safe(quantity: int = 1):
    """Lock으로 재고를 보호한다 (Race Condition 방지)

    읽기 → 체크 → 쓰기 전체를 하나의 Critical Section으로 묶는다.
    """
    with _inventory_lock:
        current_stock = _inventory["stock"]
        time.sleep(0.01)  # 같은 지연이지만 Lock 안에서 실행

        if current_stock >= quantity:
            # Lock 안에서는 current_stock이 곧 최신 값이므로
            # -= quantity와 동일한 결과다
            _inventory["stock"] = current_stock - quantity
            _inventory["success_count"] += 1
            return {
                "result": "success",
                "purchased": quantity,
                "remaining_stock": _inventory["stock"],
            }
        else:
            _inventory["fail_count"] += 1
            return {
                "result": "sold_out",
                "remaining_stock": _inventory["stock"],
            }


@router.get("/inventory/status")
def inventory_status():
    """현재 재고, 성공/실패 횟수를 반환한다"""
    return {
        "stock": _inventory["stock"],
        "success_count": _inventory["success_count"],
        "fail_count": _inventory["fail_count"],
        "is_negative": _inventory["stock"] < 0,
    }


# ─────────────────────────────────────────
# 사례 B: Deadlock (창고 간 재고 이동)
# ─────────────────────────────────────────


@router.post("/warehouse/reset")
def warehouse_reset(stock_a: int = 100, stock_b: int = 100):
    """두 창고의 재고를 초기화한다"""
    # Lock 객체를 새로 만든다.
    # 기존 Deadlock 상태의 스레드는 즉시 해제되지 않고 timeout 후 자연히 풀린다.
    # 이 reset은 "다음 테스트"를 위한 초기화다.
    _warehouses["A"] = {"stock": stock_a, "lock": threading.Lock()}
    _warehouses["B"] = {"stock": stock_b, "lock": threading.Lock()}
    _warehouse_stats["success_count"] = 0
    _warehouse_stats["deadlock_count"] = 0
    return {
        "warehouse_A": stock_a,
        "warehouse_B": stock_b,
        "message": "창고가 리셋되었다",
    }


@router.post("/warehouse/transfer-unsafe")
def transfer_unsafe(from_wh: str = "A", to_wh: str = "B", quantity: int = 10):
    """두 창고의 Lock을 순서 없이 잡는다 (Deadlock 발생 가능)

    A→B: lock_A 먼저, 그다음 lock_B
    B→A: lock_B 먼저, 그다음 lock_A
    → 동시에 실행되면 서로 상대방의 Lock을 기다리며 Deadlock
    """
    from_lock = _warehouses[from_wh]["lock"]
    to_lock = _warehouses[to_wh]["lock"]

    # 첫 번째 Lock 획득
    acquired_first = from_lock.acquire(timeout=5)
    if not acquired_first:
        with _warehouse_stats_lock:
            _warehouse_stats["deadlock_count"] += 1
        return {
            "result": "deadlock_timeout",
            "message": f"{from_wh} Lock 획득 시간 초과",
        }

    try:
        # 인위적 지연: Deadlock Window를 넓힌다
        time.sleep(0.05)

        # 두 번째 Lock 획득
        acquired_second = to_lock.acquire(timeout=5)
        if not acquired_second:
            with _warehouse_stats_lock:
                _warehouse_stats["deadlock_count"] += 1
            return {
                "result": "deadlock_timeout",
                "message": f"{to_wh} Lock 획득 시간 초과 (Deadlock 발생)",
            }

        try:
            # 이동 처리
            if _warehouses[from_wh]["stock"] >= quantity:
                _warehouses[from_wh]["stock"] -= quantity
                _warehouses[to_wh]["stock"] += quantity
                with _warehouse_stats_lock:
                    _warehouse_stats["success_count"] += 1
                return {
                    "result": "success",
                    "from": from_wh,
                    "to": to_wh,
                    "quantity": quantity,
                    "from_stock": _warehouses[from_wh]["stock"],
                    "to_stock": _warehouses[to_wh]["stock"],
                }
            else:
                return {
                    "result": "insufficient_stock",
                    "from": from_wh,
                    "from_stock": _warehouses[from_wh]["stock"],
                }
        finally:
            to_lock.release()
    finally:
        from_lock.release()


@router.post("/warehouse/transfer-safe")
def transfer_safe(from_wh: str = "A", to_wh: str = "B", quantity: int = 10):
    """Lock 순서를 항상 알파벳순으로 고정한다 (Deadlock 방지)

    A→B든 B→A든 항상 lock_A를 먼저 잡고 lock_B를 잡는다.
    Circular Wait 조건을 깨서 Deadlock을 원천 봉쇄한다.
    """
    # 항상 알파벳순으로 Lock을 잡는다
    first_wh, second_wh = sorted([from_wh, to_wh])
    first_lock = _warehouses[first_wh]["lock"]
    second_lock = _warehouses[second_wh]["lock"]

    with first_lock:
        time.sleep(0.05)  # 같은 지연이지만 순서가 고정되어 있어 Deadlock 없음
        with second_lock:
            if _warehouses[from_wh]["stock"] >= quantity:
                _warehouses[from_wh]["stock"] -= quantity
                _warehouses[to_wh]["stock"] += quantity
                with _warehouse_stats_lock:
                    _warehouse_stats["success_count"] += 1
                return {
                    "result": "success",
                    "from": from_wh,
                    "to": to_wh,
                    "quantity": quantity,
                    "from_stock": _warehouses[from_wh]["stock"],
                    "to_stock": _warehouses[to_wh]["stock"],
                }
            else:
                return {
                    "result": "insufficient_stock",
                    "from": from_wh,
                    "from_stock": _warehouses[from_wh]["stock"],
                }


@router.get("/warehouse/status")
def warehouse_status():
    """두 창고의 현재 재고와 통계를 반환한다"""
    return {
        "warehouse_A": _warehouses["A"]["stock"],
        "warehouse_B": _warehouses["B"]["stock"],
        "total_stock": _warehouses["A"]["stock"] + _warehouses["B"]["stock"],
        "success_count": _warehouse_stats["success_count"],
        "deadlock_count": _warehouse_stats["deadlock_count"],
    }
