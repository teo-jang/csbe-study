"""
Ch.18 - Local Cache vs Remote Cache vs 계층 캐시
캐시도 계층 구조로 설계해야 최적의 성능을 낼 수 있다.

이 라우터는 Local Cache(cachetools TTLCache) + Remote Cache(Redis)의
계층 캐시 구조를 구현하고, 각 계층의 히트율을 직접 측정할 수 있도록 만들어졌다.

도로명 주소처럼 변경 빈도가 낮은 데이터를 매번 Redis에서 가져오는 것은
네트워크 왕복(RTT)을 낭비하는 것이다.
Local Cache를 앞단에 두면 Redis 호출 자체를 줄일 수 있다.
"""

import time

import redis
from cachetools import TTLCache
from fastapi import APIRouter

router = APIRouter(prefix="/lcache", tags=["ch18-layered-cache"])


# ─────────────────────────────────────────
# Redis 연결 정보 (docker-compose.yml의 csbe-redis 컨테이너)
# ─────────────────────────────────────────

redis_client = redis.Redis(
    host="localhost", port=6379, db=0, decode_responses=True
)


# ─────────────────────────────────────────
# Local Cache (프로세스 메모리에 상주)
# TTLCache: 최대 10,000개, TTL 300초(5분)
# ─────────────────────────────────────────

local_cache = TTLCache(maxsize=10000, ttl=300)


# ─────────────────────────────────────────
# 히트율 통계
# 데모용이라 thread safety는 엄밀하게 관리하지 않는다.
# ─────────────────────────────────────────

stats = {
    "local_hit": 0,
    "redis_hit": 0,
    "db_hit": 0,
}


# ─────────────────────────────────────────
# Mock 주소 데이터 (DB 대용)
# 변경 빈도가 낮은 도로명 주소를 시뮬레이션한다.
# ─────────────────────────────────────────

MOCK_ADDRESSES = {
    "강남역": "서울특별시 강남구 강남대로 396",
    "판교역": "경기도 성남시 분당구 판교역로 166",
    "삼성역": "서울특별시 강남구 테헤란로 513",
    "역삼역": "서울특별시 강남구 역삼로 180",
    "선릉역": "서울특별시 강남구 선릉로 지하 525",
    "교대역": "서울특별시 서초구 서초대로 지하 294",
    "서울역": "서울특별시 용산구 한강대로 405",
    "용산역": "서울특별시 용산구 한강대로 23길 55",
    "홍대입구": "서울특별시 마포구 양화로 지하 160",
    "합정역": "서울특별시 마포구 양화로 지하 64",
    "잠실역": "서울특별시 송파구 올림픽로 지하 265",
    "건대입구": "서울특별시 광진구 아차산로 지하 243",
    "왕십리역": "서울특별시 성동구 왕십리광장로 17",
    "을지로입구": "서울특별시 중구 을지로 지하 20",
    "광화문역": "서울특별시 종로구 세종대로 지하 172",
    "종각역": "서울특별시 종로구 종로 지하 55",
    "시청역": "서울특별시 중구 세종대로 지하 101",
    "명동역": "서울특별시 중구 퇴계로 지하 2",
    "동대문역": "서울특별시 종로구 종로 지하 294",
    "신촌역": "서울특별시 서대문구 신촌로 지하 90",
    "이대역": "서울특별시 서대문구 이화여대길 지하 52",
    "여의도역": "서울특별시 영등포구 여의나루로 지하 42",
    "영등포역": "서울특별시 영등포구 영등포로 지하 846",
    "구로디지털단지": "서울특별시 구로구 디지털로 지하 242",
    "가산디지털단지": "서울특별시 금천구 가산디지털1로 지하 131",
    "판교테크노밸리": "경기도 성남시 분당구 대왕판교로 660",
    "정자역": "경기도 성남시 분당구 정자일로 지하 1",
    "수원역": "경기도 수원시 팔달구 덕영대로 지하 924",
    "인천역": "인천광역시 중구 제물량로 지하 12",
    "부산역": "부산광역시 동구 중앙대로 206",
    "해운대역": "부산광역시 해운대구 해운대로 지하 782",
    "서면역": "부산광역시 부산진구 서전로 지하 60",
    "대전역": "대전광역시 동구 중앙로 215",
    "대구역": "대구광역시 북구 태평로 161",
    "광주역": "광주광역시 북구 무등로 235",
    "울산역": "울산광역시 울주군 삼남읍 신화리 일원",
    "제주공항": "제주특별자치도 제주시 공항로 2",
    "세종시청": "세종특별자치시 한누리대로 2130",
    "춘천역": "강원특별자치도 춘천시 중앙로 1",
    "전주역": "전북특별자치도 전주시 덕진구 가리내로 40",
    "천안역": "충청남도 천안시 동남구 대흥로 지하 72",
    "청주역": "충청북도 청주시 흥덕구 가로수로 지하 120",
    "포항역": "경상북도 포항시 북구 흥해읍 이인리 일원",
    "창원역": "경상남도 창원시 의창구 원이대로 450",
    "목포역": "전라남도 목포시 영산로 82",
    "여수역": "전라남도 여수시 역전길 2",
    "속초역": "강원특별자치도 속초시 중앙로 128",
    "강릉역": "강원특별자치도 강릉시 용지로 176",
    "경주역": "경상북도 경주시 동천동 일원",
    "안동역": "경상북도 안동시 경동로 532",
}


# ─────────────────────────────────────────
# 계층 캐시 조회
# Layer 1: Local Cache -> Layer 2: Redis -> Layer 3: DB(Mock)
# ─────────────────────────────────────────


@router.get("/address/{keyword}")
def get_address_layered(keyword: str):
    """계층 캐시 조회: Local -> Redis -> DB 순서로 조회한다

    Layer 1 (Local Cache): 프로세스 메모리. RTT 없이 즉시 반환.
    Layer 2 (Redis): 네트워크 RTT 1회. 다른 서버 인스턴스와 공유 가능.
    Layer 3 (DB/Mock): 가장 느림. 디스크 I/O + 네트워크 RTT.

    Local Cache가 Redis 호출을 얼마나 줄이는지가 핵심 관찰 포인트다.
    """
    start = time.time()
    cache_key = f"addr:{keyword}"

    # Layer 1: Local Cache
    if cache_key in local_cache:
        stats["local_hit"] += 1
        elapsed_ms = round((time.time() - start) * 1000, 2)
        return {
            "address": local_cache[cache_key],
            "source": "local",
            "elapsed_ms": elapsed_ms,
        }

    # Layer 2: Redis
    cached = redis_client.get(cache_key)
    if cached:
        stats["redis_hit"] += 1
        local_cache[cache_key] = cached
        elapsed_ms = round((time.time() - start) * 1000, 2)
        return {
            "address": cached,
            "source": "redis",
            "elapsed_ms": elapsed_ms,
        }

    # Layer 3: "DB" (mock)
    stats["db_hit"] += 1
    time.sleep(0.05)  # DB 조회 시뮬레이션

    address = MOCK_ADDRESSES.get(keyword, f"{keyword} 관련 주소 없음")

    # DB에서 읽은 데이터를 양쪽 캐시에 모두 저장한다
    redis_client.setex(cache_key, 3600, address)  # Redis TTL 1시간
    local_cache[cache_key] = address

    elapsed_ms = round((time.time() - start) * 1000, 2)
    return {
        "address": address,
        "source": "db",
        "elapsed_ms": elapsed_ms,
    }


# ─────────────────────────────────────────
# 히트율 통계 조회
# ─────────────────────────────────────────


@router.get("/stats")
def get_stats():
    """캐시 계층별 히트율 통계를 반환한다

    - local_hit_rate: 전체 요청 중 Local Cache에서 처리된 비율
    - redis_reduction_rate: Local Cache가 Redis 호출을 얼마나 줄였는가
    """
    total = stats["local_hit"] + stats["redis_hit"] + stats["db_hit"]

    return {
        "total_requests": total,
        "local_hit": stats["local_hit"],
        "redis_hit": stats["redis_hit"],
        "db_hit": stats["db_hit"],
        "local_hit_rate": round(
            stats["local_hit"] / max(total, 1) * 100, 2
        ),
        "redis_reduction_rate": round(
            stats["local_hit"]
            / max(stats["local_hit"] + stats["redis_hit"], 1)
            * 100,
            2,
        ),
    }


# ─────────────────────────────────────────
# 캐시 무효화 (양쪽 캐시 전부 삭제)
# ─────────────────────────────────────────


@router.post("/invalidate")
def invalidate_cache():
    """Local Cache와 Redis의 addr:* 키를 전부 삭제한다

    통계도 초기화한다.
    실무에서 캐시 무효화는 데이터 정합성의 핵심이다.
    """
    local_cache.clear()

    # Redis에서 addr:* 패턴의 키를 삭제한다
    keys = redis_client.keys("addr:*")
    if keys:
        redis_client.delete(*keys)

    stats.update({"local_hit": 0, "redis_hit": 0, "db_hit": 0})

    return {"message": "캐시 무효화 완료"}
