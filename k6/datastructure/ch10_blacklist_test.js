import http from "k6/http";
import { check } from "k6";

// Ch.10: 블랙리스트 체크 - List vs Set 실무 사례
// 10,000명의 유저를 1,000개의 블랙리스트에서 체크

export const options = {
  scenarios: {
    blacklist_list: {
      executor: "shared-iterations",
      vus: 1,
      iterations: 10,
      exec: "blacklistList",
      startTime: "0s",
    },
    blacklist_set: {
      executor: "shared-iterations",
      vus: 1,
      iterations: 10,
      exec: "blacklistSet",
      startTime: "15s",
    },
  },
};

const BASE_URL = "http://127.0.0.1:8000";

export function blacklistList() {
  const res = http.get(`${BASE_URL}/ds/blacklist/list`);
  check(res, {
    "blacklist list 200": (r) => r.status === 200,
  });
  const body = JSON.parse(res.body);
  console.log(
    `[Blacklist-List] elapsed: ${body.elapsed_ms}ms, blocked: ${body.blocked}/${body.user_count}`
  );
}

export function blacklistSet() {
  const res = http.get(`${BASE_URL}/ds/blacklist/set`);
  check(res, {
    "blacklist set 200": (r) => r.status === 200,
  });
  const body = JSON.parse(res.body);
  console.log(
    `[Blacklist-Set] elapsed: ${body.elapsed_ms}ms, blocked: ${body.blocked}/${body.user_count}`
  );
}
