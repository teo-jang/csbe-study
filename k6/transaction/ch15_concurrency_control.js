import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

// Ch.15: 동시성 제어 방식별 비교
// naive(Race Condition), pessimistic(FOR UPDATE), optimistic(version)
// 재고 10개인 상품에 20명이 동시 구매 요청
// 사용법: k6 run ch15_concurrency_control.js

const BASE_URL = 'http://127.0.0.1:8765/tx';

const naivePurchased = new Counter('naive_purchased');
const naiveSoldOut = new Counter('naive_sold_out');
const pessimisticPurchased = new Counter('pessimistic_purchased');
const pessimisticSoldOut = new Counter('pessimistic_sold_out');
const optimisticPurchased = new Counter('optimistic_purchased');
const optimisticSoldOut = new Counter('optimistic_sold_out');
const optimisticConflict = new Counter('optimistic_conflict');

export const options = {
    scenarios: {
        // naive: 동시성 제어 없음 → Race Condition 발생
        naive_test: {
            executor: 'per-vu-iterations',
            vus: 20,
            iterations: 1,
            exec: 'naiveTest',
            startTime: '0s',
        },
        // pessimistic: SELECT ... FOR UPDATE → 정확한 재고 관리
        pessimistic_test: {
            executor: 'per-vu-iterations',
            vus: 20,
            iterations: 1,
            exec: 'pessimisticTest',
            startTime: '15s',
        },
        // optimistic: version 기반 → 충돌 시 재시도
        optimistic_test: {
            executor: 'per-vu-iterations',
            vus: 20,
            iterations: 1,
            exec: 'optimisticTest',
            startTime: '30s',
        },
    },
};

// setup: 첫 번째 테스트를 위한 재고 초기화
export function setup() {
    const res = http.post(`${BASE_URL}/reset`);
    console.log(`[Setup] naive 테스트 초기화: ${res.body}`);
    sleep(1);
}

// naive: 아무런 동시성 제어 없이 구매
export function naiveTest() {
    const res = http.post(`${BASE_URL}/purchase-naive`);
    check(res, {
        'naive 200': (r) => r.status === 200,
    });

    const body = JSON.parse(res.body);
    if (body.result === 'purchased') {
        naivePurchased.add(1);
    } else {
        naiveSoldOut.add(1);
    }
}

// pessimistic: SELECT ... FOR UPDATE
export function pessimisticTest() {
    // 첫 VU가 재고를 리셋한다
    if (__ITER === 0 && __VU <= 20) {
        // 모든 VU 중 하나만 리셋하도록
        if (__VU === 1) {
            const resetRes = http.post(`${BASE_URL}/reset`);
            console.log(`[Pessimistic Setup] 재고 리셋: ${resetRes.body}`);
            sleep(1);
        } else {
            sleep(1.5);  // 리셋 완료 대기
        }
    }

    const res = http.post(`${BASE_URL}/purchase-pessimistic`);
    check(res, {
        'pessimistic 200': (r) => r.status === 200,
    });

    const body = JSON.parse(res.body);
    if (body.result === 'purchased') {
        pessimisticPurchased.add(1);
    } else {
        pessimisticSoldOut.add(1);
    }
}

// optimistic: version 기반 충돌 감지
export function optimisticTest() {
    // 첫 VU가 재고를 리셋한다
    if (__ITER === 0 && __VU <= 20) {
        if (__VU === 1) {
            const resetRes = http.post(`${BASE_URL}/reset`);
            console.log(`[Optimistic Setup] 재고 리셋: ${resetRes.body}`);
            sleep(1);
        } else {
            sleep(1.5);  // 리셋 완료 대기
        }
    }

    const res = http.post(`${BASE_URL}/purchase-optimistic`);
    check(res, {
        'optimistic 200': (r) => r.status === 200,
    });

    const body = JSON.parse(res.body);
    if (body.result === 'purchased') {
        optimisticPurchased.add(1);
    } else if (body.result === 'conflict') {
        optimisticConflict.add(1);
    } else {
        optimisticSoldOut.add(1);
    }
}

// teardown: 각 방식별 최종 재고 확인
export function teardown() {
    sleep(2);
    const res = http.get(`${BASE_URL}/stock`);
    console.log(`[Teardown] 최종 재고: ${res.body}`);
}
