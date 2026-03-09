import http from 'k6/http';
import { check, sleep } from 'k6';

// Ch.16: Offset Pagination vs Cursor-based Pagination 성능 비교
// Offset: 마지막 페이지 근처(page=4990) 조회 → 99,800건 스캔 후 버림
// Cursor: 동일 위치를 WHERE 조건으로 직접 접근 → 인덱스 활용
// 사용법: k6 run ch16_pagination.js

const BASE_URL = 'http://127.0.0.1:8765/tuning';

// 커서 기반 테스트에 쓸 변수
// setup에서 마지막 페이지 근처의 커서를 미리 조회해둔다
let cursorCreatedAt = null;
let cursorId = null;

export const options = {
    scenarios: {
        // Offset: 끝 근처 페이지 조회 (매우 느림)
        offset_test: {
            executor: 'constant-vus',
            vus: 5,
            duration: '10s',
            exec: 'offsetTest',
            startTime: '0s',
        },
        // Cursor: 동일 위치를 커서로 조회 (빠름)
        cursor_test: {
            executor: 'constant-vus',
            vus: 5,
            duration: '10s',
            exec: 'cursorTest',
            startTime: '15s',
        },
    },
};

// setup: 커서 기반 테스트를 위한 시작점 조회
export function setup() {
    // Offset으로 page=4990 위치의 데이터를 하나 가져온다
    // 이 데이터의 created_at, id를 커서로 사용한다
    const res = http.get(`${BASE_URL}/orders-offset?page=4990&size=20`);
    if (res.status === 200) {
        const body = JSON.parse(res.body);
        if (body.orders && body.orders.length > 0) {
            const firstOrder = body.orders[0];
            console.log(`[Setup] 커서 기준점: created_at=${firstOrder.created_at}, id=${firstOrder.id}`);
            return {
                cursorCreatedAt: firstOrder.created_at,
                cursorId: firstOrder.id,
            };
        }
    }
    console.log('[Setup] 커서 기준점 조회 실패. /tuning/reset을 먼저 실행해라.');
    return { cursorCreatedAt: null, cursorId: null };
}

// Offset Pagination: 마지막 페이지 근처 조회
export function offsetTest() {
    const res = http.get(`${BASE_URL}/orders-offset?page=4990&size=20`);
    check(res, {
        'offset 200': (r) => r.status === 200,
    });
}

// Cursor-based Pagination: 동일 위치를 커서로 조회
export function cursorTest(data) {
    if (!data.cursorCreatedAt || !data.cursorId) {
        // 커서 정보가 없으면 첫 페이지 조회
        const res = http.get(`${BASE_URL}/orders-cursor?size=20`);
        check(res, {
            'cursor fallback 200': (r) => r.status === 200,
        });
        return;
    }

    const url = `${BASE_URL}/orders-cursor?last_created_at=${encodeURIComponent(data.cursorCreatedAt)}&last_id=${data.cursorId}&size=20`;
    const res = http.get(url);
    check(res, {
        'cursor 200': (r) => r.status === 200,
    });
}
