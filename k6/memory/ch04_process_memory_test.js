import http from 'k6/http';
import { sleep } from 'k6';

// ProcessPool 워커 수별 메모리 사용량 테스트
// 사용법: k6 run ch04_process_memory_test.js

export const options = {
    vus: 1,
    iterations: 1,
};

const workerCounts = [1, 2, 4, 8, 16];

export default function () {
    // 테스트 전 메모리 확인
    const infoBefore = http.get('http://127.0.0.1:8000/memory/info');
    console.log(`[Before] ${infoBefore.body}`);

    for (const count of workerCounts) {
        // 워커만 생성 (Python 런타임 오버헤드만 측정)
        const url = `http://127.0.0.1:8000/memory/process-test/${count}`;
        const res = http.get(url, { timeout: '120s' });
        console.log(`[ProcessPool workers=${count}] ${res.body}`);
        sleep(2);
    }

    // 워커 + 메모리 할당 (50MB per worker)
    console.log('\n--- 워커당 50MB 추가 할당 ---');
    for (const count of [1, 4, 8, 16]) {
        const url = `http://127.0.0.1:8000/memory/process-test/${count}?size_mb=50`;
        const res = http.get(url, { timeout: '120s' });
        console.log(`[ProcessPool workers=${count}, 50MB] ${res.body}`);
        sleep(2);
    }
}
