import http from 'k6/http';
import { check, sleep } from 'k6';

// Ch.18: Local Cache vs Remote Cache 계층 캐시 히트율 측정
// Local Cache가 Redis 호출을 얼마나 줄이는지 확인한다.
// 사용법: k6 run ch18_layered_cache.js

const BASE_URL = 'http://127.0.0.1:8765/lcache';

// 테스트용 주소 키워드 (MOCK_ADDRESSES에 존재하는 키)
const KEYWORDS = [
    '강남역',
    '판교역',
    '삼성역',
    '역삼역',
    '선릉역',
    '서울역',
    '홍대입구',
    '잠실역',
    '여의도역',
    '부산역',
];

export const options = {
    scenarios: {
        // 20 VU가 30초간 동일한 키워드 풀에서 랜덤 조회
        // Local Cache 히트율이 시간이 지날수록 올라가는 것을 관찰한다
        layered_cache: {
            executor: 'constant-vus',
            vus: 20,
            duration: '30s',
            exec: 'layeredCacheTest',
        },
    },
};

// setup: 캐시 무효화 (깨끗한 상태에서 시작)
export function setup() {
    const res = http.post(`${BASE_URL}/invalidate`);
    console.log(`[Setup] 캐시 무효화: ${res.body}`);
    sleep(1);
}

// 계층 캐시 조회
export function layeredCacheTest() {
    const keyword = KEYWORDS[Math.floor(Math.random() * KEYWORDS.length)];
    const res = http.get(`${BASE_URL}/address/${keyword}`);
    check(res, {
        'layered-cache 200': (r) => r.status === 200,
    });
}

// teardown: 히트율 통계를 출력한다
export function teardown() {
    const res = http.get(`${BASE_URL}/stats`);
    console.log(`[Teardown] 캐시 히트율 통계:`);
    console.log(res.body);
}
