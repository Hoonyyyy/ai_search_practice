// 익명 세션 식별자. 로그인이 아니다 — 인증이 아니고, 위조도 가능하다.
// 목적은 "방문자끼리 문서가 섞이지 않게" 하는 것뿐이다.
// 같은 PC·같은 브라우저의 모든 탭 = 같은 세션. 시크릿 창·다른 브라우저 = 다른 세션.
const KEY = 'rag_session_id';

export const getSessionId = (): string => {
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(KEY, id);
  }
  return id;
};

export const sessionHeader = (): Record<string, string> => ({
  'X-Session-Id': getSessionId(),
});
