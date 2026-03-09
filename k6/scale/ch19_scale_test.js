import http from 'k6/http';
import { check, sleep } from 'k6';

// Ch.19: Bottleneck 시뮬레이션 - 원본 vs 최적화
// DB 쿼리가 Bottleneck일 때 서버를 늘려봤자 의미 없다.
// Bottleneck만 해소하면 throughput이 극적으로 올라간다.
// 사용법: k6 run ch19_scale_test.js

const BASE_URL = 'http://127.0.0.1:8765/scale';

export const options = {
    scenarios: {
        // 시나리오 1: 원본 (DB 쿼리 1.6초, 전체 2.0초)
        original: {
            executor: 'constant-vus',
            vus: 5,
            duration: '30s',
            exec: 'originalTest',
            startTime: '0s',
        },
        // 시나리오 2: 최적화 (DB 쿼리 0.05초, 전체 0.45초)
        optimized: {
            executor: 'constant-vus',
            vus: 5,
            duration: '30s',
            exec: 'optimizedTest',
            startTime: '35s',
        },
    },
};

// 원본: DB 쿼리가 Bottleneck (1.6초/2.0초 = 80%)
export function originalTest() {
    const res = http.get(`${BASE_URL}/search`);
    check(res, {
        'original 200': (r) => r.status === 200,
    });
}

// 최적화: DB 쿼리에 인덱스 적용 (1.6초 -> 0.05초)
export function optimizedTest() {
    const res = http.get(`${BASE_URL}/search-optimized`);
    check(res, {
        'optimized 200': (r) => r.status === 200,
    });
}
