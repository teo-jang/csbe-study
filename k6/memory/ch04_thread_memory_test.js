import http from 'k6/http';
import { sleep } from 'k6';

// ThreadPool 워커 수별 메모리 사용량 테스트
// 사용법: k6 run ch04_thread_memory_test.js

export const options = {
    vus: 1,
    iterations: 1,
};

const workerCounts = [1, 2, 4, 8, 16];

export default function () {
    const infoBefore = http.get('http://127.0.0.1:8000/memory/info');
    console.log(`[Before] ${infoBefore.body}`);

    for (const count of workerCounts) {
        const url = `http://127.0.0.1:8000/memory/thread-test/${count}`;
        const res = http.get(url, { timeout: '120s' });
        console.log(`[ThreadPool workers=${count}] ${res.body}`);
        sleep(2);
    }
}
