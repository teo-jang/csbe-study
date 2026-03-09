"""
Ch.10 - contains()를 쓰지 마세요: 자료구조 선택의 기준

List vs Set vs Dict에서 contains() (in 연산자) 성능 차이를 보여주는 엔드포인트.
"""

import random
import time

from fastapi import APIRouter

router = APIRouter(prefix="/ds", tags=["datastructure"])

# 10만 개의 랜덤 정수 데이터
DATASET_SIZE = 100_000
raw_data = random.sample(range(1, 1_000_001), DATASET_SIZE)

# 동일한 데이터를 세 가지 자료구조로 보관
list_data = list(raw_data)
set_data = set(raw_data)
dict_data = {v: True for v in raw_data}

# 검색 대상: 절반은 존재하는 값, 절반은 존재하지 않는 값
SEARCH_COUNT = 10_000
existing_values = random.sample(list_data, SEARCH_COUNT // 2)
missing_values = random.sample(range(1_000_001, 2_000_001), SEARCH_COUNT // 2)
search_targets = existing_values + missing_values
random.shuffle(search_targets)


@router.get("/info")
async def info():
    """데이터셋 정보를 반환한다."""
    return {
        "dataset_size": DATASET_SIZE,
        "search_count": SEARCH_COUNT,
        "list_len": len(list_data),
        "set_len": len(set_data),
        "dict_len": len(dict_data),
    }


@router.get("/search/list")
async def search_in_list():
    """List에서 in 연산자로 검색한다. O(n) x SEARCH_COUNT번."""
    found = 0
    start = time.perf_counter()

    for target in search_targets:
        if target in list_data:
            found += 1

    elapsed = time.perf_counter() - start
    return {
        "structure": "list",
        "dataset_size": DATASET_SIZE,
        "search_count": SEARCH_COUNT,
        "found": found,
        "elapsed_ms": round(elapsed * 1000, 2),
    }


@router.get("/search/set")
async def search_in_set():
    """Set에서 in 연산자로 검색한다. O(1) x SEARCH_COUNT번."""
    found = 0
    start = time.perf_counter()

    for target in search_targets:
        if target in set_data:
            found += 1

    elapsed = time.perf_counter() - start
    return {
        "structure": "set",
        "dataset_size": DATASET_SIZE,
        "search_count": SEARCH_COUNT,
        "found": found,
        "elapsed_ms": round(elapsed * 1000, 2),
    }


@router.get("/search/dict")
async def search_in_dict():
    """Dict에서 in 연산자로 검색한다. O(1) x SEARCH_COUNT번."""
    found = 0
    start = time.perf_counter()

    for target in search_targets:
        if target in dict_data:
            found += 1

    elapsed = time.perf_counter() - start
    return {
        "structure": "dict",
        "dataset_size": DATASET_SIZE,
        "search_count": SEARCH_COUNT,
        "found": found,
        "elapsed_ms": round(elapsed * 1000, 2),
    }


@router.get("/search/compare")
async def search_compare():
    """세 자료구조의 검색 성능을 한 번에 비교한다."""
    results = {}

    for name, container in [
        ("list", list_data),
        ("set", set_data),
        ("dict", dict_data),
    ]:
        found = 0
        start = time.perf_counter()
        for target in search_targets:
            if target in container:
                found += 1
        elapsed = time.perf_counter() - start
        results[name] = {
            "found": found,
            "elapsed_ms": round(elapsed * 1000, 2),
        }

    return {
        "dataset_size": DATASET_SIZE,
        "search_count": SEARCH_COUNT,
        "results": results,
    }


# 실무 사례: 블랙리스트 체크
BLACKLIST_SIZE = 1_000
blacklist_raw = random.sample(range(1, 100_001), BLACKLIST_SIZE)
blacklist_list = list(blacklist_raw)
blacklist_set = set(blacklist_raw)

# 유저 ID 10,000개 (일부는 블랙리스트에 포함)
USER_COUNT = 10_000
user_ids = [random.randint(1, 100_000) for _ in range(USER_COUNT)]


@router.get("/blacklist/list")
async def blacklist_check_list():
    """블랙리스트를 List로 체크한다. O(n*m)"""
    blocked = 0
    start = time.perf_counter()

    for uid in user_ids:
        if uid in blacklist_list:
            blocked += 1

    elapsed = time.perf_counter() - start
    return {
        "method": "list",
        "user_count": USER_COUNT,
        "blacklist_size": BLACKLIST_SIZE,
        "blocked": blocked,
        "elapsed_ms": round(elapsed * 1000, 2),
    }


@router.get("/blacklist/set")
async def blacklist_check_set():
    """블랙리스트를 Set으로 체크한다. O(n)"""
    blocked = 0
    start = time.perf_counter()

    for uid in user_ids:
        if uid in blacklist_set:
            blocked += 1

    elapsed = time.perf_counter() - start
    return {
        "method": "set",
        "user_count": USER_COUNT,
        "blacklist_size": BLACKLIST_SIZE,
        "blocked": blocked,
        "elapsed_ms": round(elapsed * 1000, 2),
    }
