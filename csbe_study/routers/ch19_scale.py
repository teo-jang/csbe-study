"""
Ch.19 - 성능이 안 나오네, Replica를 200개로 늘려볼까요?
Bottleneck을 찾지 않고 Scale-Out하면 돈만 날린다.

이 라우터는 요청 처리 과정에서 Bottleneck이 어디에 있는지를
시간 비율로 시뮬레이션한다.

전체 2.0초 중 80%가 DB 쿼리에 소요되는 구조에서
서버를 10대로 늘려봤자 DB가 Bottleneck이면 성능이 안 오른다.
DB 쿼리만 최적화하면 전체 응답 시간이 극적으로 줄어든다.
이것이 Amdahl's Law의 실무적 의미다.

외부 의존성 없이 time.sleep()으로 시뮬레이션한다.
"""

import time

from fastapi import APIRouter

router = APIRouter(prefix="/scale", tags=["ch19-scale"])


# ─────────────────────────────────────────
# Bottleneck 시뮬레이션 (원본)
# ─────────────────────────────────────────


@router.get("/search")
def search_original():
    """원본 검색 API: 전체 2.0초 중 80%가 DB 쿼리다

    - 1단계: 요청 파싱 + 비즈니스 로직 (0.1초, 5%)
    - 2단계: DB 쿼리 (1.6초, 80%) - Bottleneck!
    - 3단계: 결과 가공 + JSON 직렬화 (0.2초, 10%)
    - 4단계: 응답 전송 (0.1초, 5%)

    서버를 10대로 늘려도 각 서버가 DB에 1.6초씩 기다린다.
    DB가 Bottleneck인 한 Scale-Out은 의미 없다.
    """
    start = time.time()

    # 1단계: 요청 파싱 + 비즈니스 로직 (0.1초, 5%)
    time.sleep(0.1)

    # 2단계: DB 쿼리 (1.6초, 80%) - Bottleneck!
    time.sleep(1.6)

    # 3단계: 결과 가공 + JSON 직렬화 (0.2초, 10%)
    time.sleep(0.2)

    # 4단계: 응답 전송 (0.1초, 5%)
    time.sleep(0.1)

    elapsed = time.time() - start
    return {
        "result": "검색 결과 20건",
        "elapsed_sec": round(elapsed, 2),
        "breakdown": {
            "parsing": "0.1s (5%)",
            "db_query": "1.6s (80%) - Bottleneck",
            "processing": "0.2s (10%)",
            "response": "0.1s (5%)",
        },
    }


# ─────────────────────────────────────────
# Bottleneck 해소 후 (DB 쿼리 최적화)
# ─────────────────────────────────────────


@router.get("/search-optimized")
def search_optimized():
    """최적화된 검색 API: DB 쿼리에 인덱스/캐시를 적용했다

    - 1단계: 요청 파싱 + 비즈니스 로직 (0.1초)
    - 2단계: DB 쿼리 (0.05초) - 인덱스 적용 후 1.6초 -> 0.05초
    - 3단계: 결과 가공 + JSON 직렬화 (0.2초)
    - 4단계: 응답 전송 (0.1초)

    Bottleneck이었던 DB 쿼리만 개선했는데 전체 응답이 2.0초 -> 0.45초.
    서버를 늘리기 전에 Bottleneck부터 찾는 것이 핵심이다.
    """
    start = time.time()

    # 1단계: 요청 파싱 + 비즈니스 로직 (변함없음)
    time.sleep(0.1)

    # 2단계: DB 쿼리 (인덱스 적용 후 1.6초 -> 0.05초)
    time.sleep(0.05)

    # 3단계: 결과 가공 + JSON 직렬화 (변함없음)
    time.sleep(0.2)

    # 4단계: 응답 전송 (변함없음)
    time.sleep(0.1)

    elapsed = time.time() - start
    return {
        "result": "검색 결과 20건",
        "elapsed_sec": round(elapsed, 2),
        "breakdown": {
            "parsing": "0.1s",
            "db_query": "0.05s (인덱스 적용: 1.6s -> 0.05s)",
            "processing": "0.2s",
            "response": "0.1s",
        },
    }
