import os
import sys
import resource
import threading
import tracemalloc
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from fastapi import APIRouter

router = APIRouter(prefix="/memory", tags=["memory"])


def _get_rss_mb():
    """현재 프로세스의 max RSS를 MB 단위로 반환"""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    if sys.platform == "darwin":
        # macOS: ru_maxrss는 bytes 단위
        return usage.ru_maxrss / (1024 * 1024)
    else:
        # Linux: ru_maxrss는 KB 단위
        return usage.ru_maxrss / 1024


def _process_worker_info():
    """프로세스 워커에서 자신의 PID와 RSS를 반환"""
    return {
        "pid": os.getpid(),
        "rss_mb": round(_get_rss_mb(), 2),
    }


def _process_worker_with_alloc(size_mb):
    """프로세스 워커에서 메모리를 할당한 뒤 RSS를 반환"""
    # 실제 물리 메모리를 할당 (Copy-on-Write 우회)
    data = bytearray(size_mb * 1024 * 1024)
    for i in range(0, len(data), 4096):
        data[i] = 1

    rss = _get_rss_mb()
    pid = os.getpid()
    del data
    return {"pid": pid, "rss_mb": round(rss, 2)}


def _thread_worker_info():
    """스레드 워커에서 자신의 PID와 스레드 ID를 반환"""
    return {
        "pid": os.getpid(),
        "thread_id": threading.current_thread().ident,
        "rss_mb": round(_get_rss_mb(), 2),
    }


# ─────────────────────────────────────────
# 카테고리 트리 (사례 B: 재귀 탐색 vs 직접 조회)
# ─────────────────────────────────────────


def _build_category_tree(depth):
    """깊이 depth인 일직선 카테고리 트리를 생성한다.

    실제 서비스에서는 DB에 저장되지만, 여기서는 dict로 시뮬레이션.
    ID를 키로 쓰므로 O(1) 직접 접근이 가능한 구조다.
    """
    tree = {}
    for i in range(depth):
        tree[i] = {
            "name": f"category-{i}",
            "parent_id": i - 1 if i > 0 else None,
        }
    return tree


def _find_from_root_recursive(tree, target_id, current_id=0):
    """루트(ID 0)부터 재귀 DFS로 타겟 카테고리를 찾는다 (비효율적).

    모든 자식을 순회하면서 타고 내려가기 때문에,
    트리 깊이가 깊으면 RecursionError가 발생한다.
    """
    if current_id == target_id:
        return [tree[current_id]["name"]]
    # 현재 노드의 자식을 찾기 위해 전체 트리를 순회한다
    children = [cid for cid, cat in tree.items() if cat["parent_id"] == current_id]
    for child_id in children:
        result = _find_from_root_recursive(tree, target_id, child_id)
        if result is not None:
            return [tree[current_id]["name"]] + result
    return None


def _find_by_direct_lookup(tree, target_id):
    """ID로 직접 접근 후 parent를 따라 올라간다 (효율적).

    재귀 없이 while 루프로 처리. Stack Overflow 위험 없음.
    트리 깊이가 얼마든 상관없다.
    """
    if target_id not in tree:
        return None
    path = []
    current = target_id
    while current is not None:
        path.append(tree[current]["name"])
        current = tree[current]["parent_id"]
    return list(reversed(path))


# ─────────────────────────────────────────
# 엔드포인트
# ─────────────────────────────────────────


@router.get("/info")
def memory_info():
    """현재 프로세스 메모리 정보"""
    return {
        "pid": os.getpid(),
        "rss_mb": round(_get_rss_mb(), 2),
        "recursion_limit": sys.getrecursionlimit(),
    }


@router.get("/process-test/{count}")
def process_test(count: int, size_mb: int = 0):
    """N개 프로세스 워커 생성 후 각 워커의 메모리를 측정

    - size_mb=0: 워커만 생성 (Python 런타임 오버헤드만 측정)
    - size_mb>0: 워커마다 size_mb만큼 메모리를 추가 할당
    """
    main_rss = _get_rss_mb()

    worker_fn = _process_worker_info if size_mb == 0 else _process_worker_with_alloc
    with ProcessPoolExecutor(max_workers=count) as executor:
        if size_mb == 0:
            futures = [executor.submit(worker_fn) for _ in range(count)]
        else:
            futures = [executor.submit(worker_fn, size_mb) for _ in range(count)]
        workers = [f.result() for f in futures]

    return {
        "worker_type": "process",
        "worker_count": count,
        "size_mb_per_worker": size_mb,
        "main_process": {"pid": os.getpid(), "rss_mb": round(main_rss, 2)},
        "workers": workers,
        "total_rss_mb": round(main_rss + sum(w["rss_mb"] for w in workers), 2),
        "unique_pids": len(set(w["pid"] for w in workers)),
    }


@router.get("/thread-test/{count}")
def thread_test(count: int):
    """N개 스레드 워커 생성 후 메모리를 측정"""
    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(_thread_worker_info) for _ in range(count)]
        workers = [f.result() for f in futures]
        main_rss = _get_rss_mb()  # 스레드가 아직 살아있는 동안 측정

    return {
        "worker_type": "thread",
        "worker_count": count,
        "main_process": {"pid": os.getpid(), "rss_mb": round(main_rss, 2)},
        "workers": workers,
        "total_rss_mb": round(main_rss, 2),
        "unique_pids": len(set(w["pid"] for w in workers)),
    }


@router.get("/category/recursive/{depth}")
def category_recursive_search(depth: int):
    """루트부터 재귀 DFS로 가장 깊은 카테고리의 경로를 찾는다"""
    tree = _build_category_tree(depth)
    target_id = depth - 1  # 가장 깊은 카테고리

    try:
        result = _find_from_root_recursive(tree, target_id)
        return {
            "depth": depth,
            "target_id": target_id,
            "method": "recursive_dfs",
            "result": "success",
            "path_length": len(result) if result else 0,
            "recursion_limit": sys.getrecursionlimit(),
        }
    except RecursionError as e:
        return {
            "depth": depth,
            "target_id": target_id,
            "method": "recursive_dfs",
            "result": "RecursionError",
            "message": str(e),
            "recursion_limit": sys.getrecursionlimit(),
        }


@router.get("/category/iterative/{depth}")
def category_iterative_search(depth: int):
    """ID로 직접 접근 후 parent를 따라 올라간다"""
    tree = _build_category_tree(depth)
    target_id = depth - 1

    result = _find_by_direct_lookup(tree, target_id)
    return {
        "depth": depth,
        "target_id": target_id,
        "method": "direct_lookup",
        "result": "success",
        "path_length": len(result) if result else 0,
    }


@router.get("/heap-growth")
def heap_growth():
    """Heap 메모리 증가 패턴 관찰 (tracemalloc 사용)"""
    tracemalloc.start()
    results = []
    data = []

    for i in range(10):
        # 10만 개씩 추가
        data.extend(range(i * 100_000, (i + 1) * 100_000))
        current, peak = tracemalloc.get_traced_memory()
        results.append(
            {
                "items": len(data),
                "current_mb": round(current / (1024 * 1024), 2),
                "peak_mb": round(peak / (1024 * 1024), 2),
            }
        )

    tracemalloc.stop()
    del data

    return results
