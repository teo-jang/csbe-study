import http from 'k6/http';
import { check, sleep } from 'k6';

// Ch.17: Cache Stampede 재현과 Mutex Lock 방어
// Cache-Aside 기본 성능 -> Stampede(방어 없음) -> Mutex Lock(방어)
// 사용법: k6 run ch17_cache_stampede.js

const BASE_URL = 'http://127.0.0.1:8765/cache';

export const options = {
    scenarios: {
        // 시나리오 1: Cache-Aside 기본 (캐시 히트 성능 확인)
        cache_hit: {
            executor: 'constant-vus',
            vus: 10,
            duration: '10s',
            exec: 'cacheHitTest',
            startTime: '0s',
        },
        // 시나리오 2: Stampede 재현 (방어 없음, 50 VU가 동시에 DB를 때린다)
        stampede_no_lock: {
            executor: 'constant-vus',
            vus: 50,
            duration: '10s',
            exec: 'stampedeNoLockTest',
            startTime: '15s',
        },
        // 시나리오 3: Mutex Lock 방어 (1개만 DB, 나머지는 캐시 대기)
        stampede_mutex: {
            executor: 'constant-vus',
            vus: 50,
            duration: '10s',
            exec: 'stampedeMutexTest',
            startTime: '30s',
        },
    },
};

// setup: 테이블 초기화 + 시드 데이터 삽입
export function setup() {
    const res = http.post(`${BASE_URL}/reset`);
    console.log(`[Setup] 테이블 초기화: ${res.body}`);
    sleep(2);
}

// Cache-Aside 기본: 캐시 히트 시 성능
export function cacheHitTest() {
    const productId = Math.floor(Math.random() * 100) + 1;
    const res = http.get(`${BASE_URL}/product/${productId}`);
    check(res, {
        'cache-hit 200': (r) => r.status === 200,
    });
}

// Stampede 재현: 동일 상품에 50 VU가 동시 요청 (방어 없음)
export function stampedeNoLockTest() {
    // 소수의 상품에 집중해서 Stampede를 유발한다
    const productId = Math.floor(Math.random() * 5) + 1;
    const res = http.get(`${BASE_URL}/product-no-lock/${productId}`);
    check(res, {
        'stampede-no-lock 200': (r) => r.status === 200,
    });
}

// Mutex Lock 방어: 1개만 DB, 나머지는 캐시 대기
export function stampedeMutexTest() {
    const productId = Math.floor(Math.random() * 5) + 1;
    const res = http.get(`${BASE_URL}/product-mutex/${productId}`);
    check(res, {
        'stampede-mutex 200': (r) => r.status === 200,
    });
}
