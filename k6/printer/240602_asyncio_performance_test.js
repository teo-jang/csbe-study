import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  vus: 100,        // 동시 가상 사용자 수
  duration: '10s', // 테스트 지속 시간
};

// async print 엔드포인트에 부하를 건다 (Ch.3에서 사용)
export default function() {
  http.get('http://127.0.0.1:8000/print/doPrintAsync/' + generateUUID());
  sleep(1); // 실제 사용자처럼 1초 대기 (think time)
}

// 매 요청마다 고유한 UUID를 생성한다 (캐시 영향 배제)
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = (Math.random() * 16) | 0,
            v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}
