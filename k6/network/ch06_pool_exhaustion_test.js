import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

// Connection Pool 고갈 테스트
// pool_size=3인 엔진에 10 VUs가 동시 요청 → Pool 고갈 재현
// 사용법: k6 run ch06_pool_exhaustion_test.js

const BASE_URL = 'http://127.0.0.1:8765/network';

const poolExhausted = new Counter('pool_exhausted');
const poolSuccess = new Counter('pool_success');

export const options = {
    scenarios: {
        // Pool(size=3)에 10 VUs 동시 요청 → 고갈
        pool_test: {
            executor: 'per-vu-iterations',
            vus: 10,
            iterations: 5,
            exec: 'poolTest',
            startTime: '0s',
        },
        // NullPool: Pool이 없으니 고갈 없음 (대신 느림)
        nopool_test: {
            executor: 'per-vu-iterations',
            vus: 10,
            iterations: 5,
            exec: 'nopoolTest',
            startTime: '90s',
        },
    },
};

// setup: 테이블 초기화
export function setup() {
    const res = http.post(`${BASE_URL}/pool/reset`);
    console.log(`[Setup] 테이블 초기화: ${res.body}`);
    sleep(1);
}

// Pool(size=3) 사용 → 동시 10 VUs면 7개는 대기/실패
export function poolTest() {
    const res = http.post(`${BASE_URL}/pool/query-pool`, null, {
        timeout: '10s',
    });

    if (res.status === 200) {
        poolSuccess.add(1);
    } else {
        poolExhausted.add(1);
    }
}

// NullPool: 매번 새 Connection → Pool 고갈 없지만 느림
export function nopoolTest() {
    http.post(`${BASE_URL}/pool/query-nopool`, null, {
        timeout: '10s',
    });
}

// teardown: Pool 상태 확인
export function teardown() {
    sleep(2);
    const res = http.get(`${BASE_URL}/pool/status`);
    console.log(`[Teardown] Pool 상태: ${res.body}`);
}
