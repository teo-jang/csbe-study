import http from 'k6/http';
import { check, sleep } from 'k6';

// Ch.23 - 보안은 남의 일이 아니다
// SQL Injection과 XSS 공격 페이로드를 취약/안전 엔드포인트에 각각 보내서
// 방어 여부를 비교한다.
// 사용법: k6 run ch23_injection_test.js

const BASE_URL = 'http://127.0.0.1:8765/security';

export const options = {
    scenarios: {
        // SQL Injection 공격 테스트
        sqli_attack: {
            executor: 'constant-vus',
            vus: 5,
            duration: '10s',
            exec: 'sqliTest',
            startTime: '0s',
        },
        // XSS 공격 테스트
        xss_attack: {
            executor: 'constant-vus',
            vus: 5,
            duration: '10s',
            exec: 'xssTest',
            startTime: '15s',
        },
    },
};

// setup: 테이블 초기화
export function setup() {
    const res = http.post(`${BASE_URL}/reset`);
    console.log(`[Setup] 테이블 초기화: ${res.status}`);
    sleep(1);
}

// SQL Injection 페이로드 목록
const SQLI_PAYLOADS = [
    "'; DROP TABLE ch23_posts; --",
    "' OR '1'='1",
    "' UNION SELECT * FROM ch23_users --",
];

// XSS 페이로드 목록
const XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert('xss')>",
];

export function sqliTest() {
    const payload = SQLI_PAYLOADS[Math.floor(Math.random() * SQLI_PAYLOADS.length)];
    const encoded = encodeURIComponent(payload);

    // 취약 엔드포인트에 공격
    const vulnRes = http.get(`${BASE_URL}/sqli-vulnerable?keyword=${encoded}`);
    check(vulnRes, {
        '[취약] SQL Injection 요청 전송됨': (r) => r.status === 200 || r.status === 500,
    });

    // 안전 엔드포인트에 같은 공격
    const safeRes = http.get(`${BASE_URL}/sqli-safe?keyword=${encoded}`);
    check(safeRes, {
        '[안전] SQL Injection 방어 성공 (200)': (r) => r.status === 200,
        '[안전] 파라미터 바인딩 사용': (r) => {
            const body = JSON.parse(r.body);
            return body.defense !== undefined;
        },
    });

    sleep(0.5);
}

export function xssTest() {
    const payload = XSS_PAYLOADS[Math.floor(Math.random() * XSS_PAYLOADS.length)];
    const encoded = encodeURIComponent(payload);

    // 취약 엔드포인트: 페이로드가 그대로 HTML에 삽입된다
    const vulnRes = http.get(`${BASE_URL}/xss-vulnerable?keyword=${encoded}`);
    check(vulnRes, {
        '[취약] XSS 페이로드가 그대로 반영됨': (r) => {
            return r.status === 200 && r.body.includes(payload);
        },
    });

    // 안전 엔드포인트: 페이로드가 이스케이프된다
    const safeRes = http.get(`${BASE_URL}/xss-safe?keyword=${encoded}`);
    check(safeRes, {
        '[안전] XSS 방어 성공 (200)': (r) => r.status === 200,
        '[안전] 스크립트 태그가 이스케이프됨': (r) => {
            return !r.body.includes('<script>') && !r.body.includes('onerror=');
        },
    });

    sleep(0.5);
}
