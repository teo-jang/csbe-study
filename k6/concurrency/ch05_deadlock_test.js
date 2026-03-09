import http from 'k6/http';
import { sleep } from 'k6';

// Deadlock 테스트: A→B와 B→A 동시 이동 시 Deadlock 발생 확인
// unsafe와 safe를 순차적으로 비교한다
// 사용법: k6 run ch05_deadlock_test.js

const BASE_URL = 'http://127.0.0.1:8765/concurrency';

export const options = {
    scenarios: {
        // unsafe: 10 VUs x 3회. 짝수 VU는 A→B, 홀수 VU는 B→A
        unsafe_test: {
            executor: 'per-vu-iterations',
            vus: 10,
            iterations: 3,
            exec: 'unsafeTest',
            startTime: '0s',
        },
        // safe: 10 VUs x 3회. 같은 조건, Lock 순서 고정
        safe_test: {
            executor: 'per-vu-iterations',
            vus: 10,
            iterations: 3,
            exec: 'safeTest',
            startTime: '90s',
        },
    },
};

// setup: 창고 리셋
export function setup() {
    const res = http.post(`${BASE_URL}/warehouse/reset?stock_a=100&stock_b=100`);
    console.log(`[Setup] 창고 리셋: ${res.body}`);
    sleep(1);
}

// __VU는 k6의 가상 사용자 번호 (1부터 시작)
// 짝수 VU는 A→B, 홀수 VU는 B→A 이동
// → 동시에 양방향 요청이 발생하므로 Deadlock이 재현된다
export function unsafeTest() {
    if (__VU % 2 === 0) {
        http.post(`${BASE_URL}/warehouse/transfer-unsafe?from_wh=A&to_wh=B&quantity=5`, null, {
            timeout: '15s',
        });
    } else {
        http.post(`${BASE_URL}/warehouse/transfer-unsafe?from_wh=B&to_wh=A&quantity=5`, null, {
            timeout: '15s',
        });
    }
}

export function safeTest() {
    // safe 테스트 시작 전 창고 리셋
    if (__ITER === 0 && __VU === 1) {
        const resetRes = http.post(`${BASE_URL}/warehouse/reset?stock_a=100&stock_b=100`);
        console.log(`[Safe Setup] 창고 리셋: ${resetRes.body}`);
        sleep(1);
    }
    if (__VU % 2 === 0) {
        http.post(`${BASE_URL}/warehouse/transfer-safe?from_wh=A&to_wh=B&quantity=5`, null, {
            timeout: '15s',
        });
    } else {
        http.post(`${BASE_URL}/warehouse/transfer-safe?from_wh=B&to_wh=A&quantity=5`, null, {
            timeout: '15s',
        });
    }
}

// teardown: 최종 상태 확인
export function teardown() {
    sleep(2);
    const res = http.get(`${BASE_URL}/warehouse/status`);
    console.log(`[Teardown] 최종 상태: ${res.body}`);
}
