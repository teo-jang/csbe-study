import http from "k6/http";
import { check } from "k6";

// Ch.10: List vs Set vs Dict 검색 성능 비교
// 각 자료구조에서 10,000번 contains 검색 후 응답 시간 비교

export const options = {
  scenarios: {
    list_search: {
      executor: "shared-iterations",
      vus: 1,
      iterations: 5,
      exec: "searchList",
      startTime: "0s",
    },
    set_search: {
      executor: "shared-iterations",
      vus: 1,
      iterations: 5,
      exec: "searchSet",
      startTime: "10s",
    },
    dict_search: {
      executor: "shared-iterations",
      vus: 1,
      iterations: 5,
      exec: "searchDict",
      startTime: "20s",
    },
  },
};

const BASE_URL = "http://127.0.0.1:8000";

export function searchList() {
  const res = http.get(`${BASE_URL}/ds/search/list`);
  check(res, {
    "list search 200": (r) => r.status === 200,
  });
  const body = JSON.parse(res.body);
  console.log(
    `[List] elapsed: ${body.elapsed_ms}ms, found: ${body.found}/${body.search_count}`
  );
}

export function searchSet() {
  const res = http.get(`${BASE_URL}/ds/search/set`);
  check(res, {
    "set search 200": (r) => r.status === 200,
  });
  const body = JSON.parse(res.body);
  console.log(
    `[Set] elapsed: ${body.elapsed_ms}ms, found: ${body.found}/${body.search_count}`
  );
}

export function searchDict() {
  const res = http.get(`${BASE_URL}/ds/search/dict`);
  check(res, {
    "dict search 200": (r) => r.status === 200,
  });
  const body = JSON.parse(res.body);
  console.log(
    `[Dict] elapsed: ${body.elapsed_ms}ms, found: ${body.found}/${body.search_count}`
  );
}
