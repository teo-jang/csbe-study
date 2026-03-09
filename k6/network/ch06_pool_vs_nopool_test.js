import http from 'k6/http';
import { sleep } from 'k6';

// Connection Pool vs NullPool 성능 비교 벤치마크
// QueuePool(size=10) vs NullPool로 동일 쿼리 실행 시 Throughput/Latency 비교
// 사용법: k6 run ch06_pool_vs_nopool_test.js

const BASE_URL = 'http://127.0.0.1:8765/network';

export const options = {
    scenarios: {
        // QueuePool(size=10): Connection 재활용
        with_pool: {
            executor: 'per-vu-iterations',
            vus: 50,
            iterations: 10,
            exec: 'withPool',
            startTime: '0s',
        },
        // NullPool: 매 요청마다 새 Connection
        without_pool: {
            executor: 'per-vu-iterations',
            vus: 50,
            iterations: 10,
            exec: 'withoutPool',
            startTime: '60s',
        },
    },
};

// setup: 테이블 초기화
export function setup() {
    const res = http.post(`${BASE_URL}/pool/reset`);
    console.log(`[Setup] 테이블 초기화: ${res.body}`);
    sleep(1);
}

// QueuePool: Connection 재활용 → 빠르다
export function withPool() {
    http.post(`${BASE_URL}/bench/with-pool`, null, {
        timeout: '10s',
    });
}

// NullPool: 매번 새 Connection → 느리다
export function withoutPool() {
    http.post(`${BASE_URL}/bench/without-pool`, null, {
        timeout: '10s',
    });
}

// teardown: 결과 비교는 k6 기본 출력에서 확인
export function teardown() {
    console.log('[Teardown] k6 출력의 http_req_duration을 시나리오별로 비교한다');
    console.log('  - with_pool: QueuePool(size=10) 사용');
    console.log('  - without_pool: NullPool 사용');
}
