import http from 'k6/http';
import { sleep } from 'k6';

// 재귀 깊이별 Stack Overflow 테스트
// 사용법: k6 run ch04_stack_overflow_test.js

export const options = {
    vus: 1,
    iterations: 1,
};

const depths = [10, 100, 500, 900, 990, 995, 1000, 5000];

export default function () {
    console.log('--- 재귀 깊이별 테스트 ---');
    for (const depth of depths) {
        const url = `http://127.0.0.1:8000/memory/recursive/${depth}`;
        const res = http.get(url);
        console.log(`[depth=${depth}] ${res.body}`);
        sleep(0.5);
    }

    console.log('\n--- Heap 증가 패턴 ---');
    const heapRes = http.get('http://127.0.0.1:8000/memory/heap-growth');
    console.log(`[heap-growth] ${heapRes.body}`);
}
