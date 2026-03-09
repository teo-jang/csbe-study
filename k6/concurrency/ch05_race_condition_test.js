import http from 'k6/http';
import { sleep } from 'k6';

// Race Condition 테스트: 동시 구매 시 재고가 마이너스가 되는지 확인
// unsafe와 safe를 순차적으로 비교한다
// 사용법: k6 run ch05_race_condition_test.js

const BASE_URL = 'http://127.0.0.1:8765/concurrency';

export const options = {
    scenarios: {
        // unsafe: 50 VUs x 3회 = 150건 (재고 100)
        unsafe_test: {
            executor: 'per-vu-iterations',
            vus: 50,
            iterations: 3,
            exec: 'unsafeTest',
            startTime: '0s',
        },
        // safe: 50 VUs x 1회 = 50건 (재고 100, unsafe 종료 후 리셋)
        safe_test: {
            executor: 'per-vu-iterations',
            vus: 50,
            iterations: 1,
            exec: 'safeTest',
            startTime: '30s',
        },
    },
};

// setup: unsafe 테스트를 위한 재고 리셋
export function setup() {
    const res = http.post(`${BASE_URL}/inventory/reset?stock=100`);
    console.log(`[Setup] unsafe 테스트 재고 리셋: ${res.body}`);
    sleep(1);
}

export function unsafeTest() {
    http.post(`${BASE_URL}/inventory/purchase-unsafe?quantity=1`);
}

export function safeTest() {
    // safe 테스트 첫 VU가 재고를 리셋한다
    if (__ITER === 0 && __VU === 1) {
        const resetRes = http.post(`${BASE_URL}/inventory/reset?stock=100`);
        console.log(`[Safe Setup] 재고 리셋: ${resetRes.body}`);
        sleep(1);
    }
    http.post(`${BASE_URL}/inventory/purchase-safe?quantity=1`);
}

// teardown: 최종 상태 확인
export function teardown() {
    sleep(2);
    const res = http.get(`${BASE_URL}/inventory/status`);
    console.log(`[Teardown] 최종 상태: ${res.body}`);
}
