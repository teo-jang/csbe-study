import bisect
import time

from fastapi import APIRouter
import random

from csbe_study.repository.TrafficInfoRepository import TrafficInfoRepository

router = APIRouter(prefix="/iterator", tags=["iterate"])

data = random.sample(range(1, 1000001), 10000)

list_data = list(data)
set_data = set(data)

ACTION_COUNT = 1000

traffic_data = {}


@router.on_event("startup")
async def startup():
    global traffic_data
    repository = TrafficInfoRepository()
    print("cache load started...")
    start = time.time()
    traffic_data = await repository.get_all()
    end = time.time()
    print(f"cache load completed... {end - start} seconds")


@router.get("/find_in_list/{value}")
async def find_in_list(value: int):
    ret = True
    for _ in range(ACTION_COUNT):
        ret = value in list_data

    return ret


@router.get("/find_in_set/{value}")
async def find_in_set(value: int):
    ret = True
    for _ in range(ACTION_COUNT):
        ret = value in set_data

    return ret


CONTAINS_COUNT = 100
APPEND_COUNT = 100


@router.get("/complex_in_list/{value}")
async def complex_in_list(
    value: int, contains_multiplier: int = 0, append_multiplier: int = 0
):
    ret = True
    append_value = 1000001

    new_data = list_data[:]

    for _ in range(CONTAINS_COUNT * contains_multiplier):
        ret = value in new_data

    for _ in range(APPEND_COUNT * append_multiplier):
        new_data.append(append_value)
        append_value += 1

    return ret


@router.get("/complex_in_set/{value}")
async def complex_in_list(
    value: int, contains_multiplier: int = 0, append_multiplier: int = 0
):
    ret = True
    append_value = 1000001

    new_data = set(data)

    for _ in range(CONTAINS_COUNT * contains_multiplier):
        ret = value in new_data

    for _ in range(APPEND_COUNT * append_multiplier):
        new_data.add(append_value)
        append_value += 1

    return ret


@router.get("/python_resize_test/")
async def python_resize_test():
    import sys

    lst = []
    initial_size = sys.getsizeof(lst)
    print(f"Initial size: {initial_size} bytes")

    for i in range(100):
        lst.append(i)
        size = sys.getsizeof(lst)
        if size != initial_size:
            print(f"Size after {i + 1} elements: {size} bytes")
            initial_size = size

    return True


@router.get("/contains_speed_test/{value}")
async def contains_speed_test(
    value: int, is_sort: bool = False, contains_multiplier: int = 0
):
    target_data = list_data[:]
    ret = True

    if is_sort:
        target_data.sort()

    for _ in range(contains_multiplier):
        if is_sort:
            index = bisect.bisect_left(target_data, value)
            ret = target_data[index] == value
        else:
            ret = value in target_data

    return ret


@router.get(
    "/cache_test/{transportation_date}/{line_name}/{station_name}/{division_name}"
)
async def cache_test(
    transportation_date: str,
    line_name: str,
    station_name: str,
    division_name: str,
    use_cache: bool = False,
):
    repository = TrafficInfoRepository()

    if use_cache:
        key = f"{transportation_date}_{line_name}_{station_name}_{division_name}"
        return True if traffic_data.get(key, None) else False
    else:
        return (
            True
            if await repository.get_one(
                transportation_date, line_name, station_name, division_name
            )
            else None
        )
