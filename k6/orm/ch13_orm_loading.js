import http from 'k6/http';
import { check, sleep } from 'k6';

// Ch.13: ORM Loading 전략별 성능 비교
// Lazy Loading(N+1) vs joinedload(JOIN) vs subqueryload(서브쿼리)
// 사용법: k6 run ch13_orm_loading.js

const BASE_URL = 'http://127.0.0.1:8765/orm';

export const options = {
    scenarios: {
        // Lazy Loading: N+1 발생 (101 쿼리)
        lazy_loading: {
            executor: 'constant-vus',
            vus: 10,
            duration: '10s',
            exec: 'lazyTest',
            startTime: '0s',
        },
        // joinedload: JOIN 1회
        eager_join: {
            executor: 'constant-vus',
            vus: 10,
            duration: '10s',
            exec: 'eagerJoinTest',
            startTime: '15s',
        },
        // subqueryload: 서브쿼리 2회
        eager_subquery: {
            executor: 'constant-vus',
            vus: 10,
            duration: '10s',
            exec: 'eagerSubqueryTest',
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

// Lazy Loading: user.orders 접근 시마다 SELECT 발생
export function lazyTest() {
    const res = http.get(`${BASE_URL}/lazy`);
    check(res, {
        'lazy 200': (r) => r.status === 200,
    });
}

// joinedload: LEFT OUTER JOIN으로 한 번에 가져온다
export function eagerJoinTest() {
    const res = http.get(`${BASE_URL}/eager-join`);
    check(res, {
        'eager-join 200': (r) => r.status === 200,
    });
}

// subqueryload: User + Order 서브쿼리 2번
export function eagerSubqueryTest() {
    const res = http.get(`${BASE_URL}/eager-subquery`);
    check(res, {
        'eager-subquery 200': (r) => r.status === 200,
    });
}
