import http from 'k6/http';
import { check } from 'k6';

// Ch.14: 인덱스 유무에 따른 쿼리 성능 비교
// random user_id로 /index/orders/{user_id} 호출
// 인덱스 추가 전/후 각각 실행해서 비교한다
// 사용법: k6 run ch14_index_performance.js

const BASE_URL = 'http://127.0.0.1:8765/index';

export const options = {
    scenarios: {
        order_query: {
            executor: 'constant-vus',
            vus: 10,
            duration: '10s',
            exec: 'queryOrders',
        },
    },
};

// random user_id 생성 (1~1000)
function randomUserId() {
    return Math.floor(Math.random() * 1000) + 1;
}

// 특정 사용자의 최근 주문 조회
export function queryOrders() {
    const userId = randomUserId();
    const res = http.get(`${BASE_URL}/orders/${userId}`);

    check(res, {
        'orders 200': (r) => r.status === 200,
    });
}
