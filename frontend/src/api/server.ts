const BASE = process.env.REACT_APP_API_URL ?? 'http://localhost:8080/api';
const AI_BASE = process.env.REACT_APP_AI_URL ?? 'http://localhost:8001';

const isOk = async (url: string): Promise<boolean> => {
  try {
    const resp = await fetch(url);
    return resp.ok;
  } catch {
    return false;
  }
};

// Spring(+DB)과 FastAPI 가 모두 응답하면 true.
// 둘을 동시에 두드려서 동시에 깨운다. 자는 중이면 Render 가 요청을 붙잡고 있다가 깨어난 뒤 응답한다.
export const pingServer = async (): Promise<boolean> => {
  const [spring, ai] = await Promise.all([
    isOk(`${BASE}/documents`),
    isOk(`${AI_BASE}/health`),
  ]);
  return spring && ai;
};

// 답을 기다리지 않고 FastAPI 를 깨우기만 한다.
// Render 안의 Spring 이 FastAPI 를 부르면 502 만 오고 깨어나지 않는다(v4.23 실측).
// 그래서 FastAPI 가 필요한 동작(검색·업로드·삭제) 직전에 브라우저가 한 번 두드린다.
export const wakeAiService = (): void => {
  fetch(`${AI_BASE}/health`).catch(() => {});
};
