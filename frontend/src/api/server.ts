const BASE = process.env.REACT_APP_API_URL ?? 'http://localhost:8080/api';

// 서버(Spring + DB)가 응답하면 true.
// 자는 중이면 Render 가 요청을 붙잡고 있다가, 깨어난 뒤에 응답한다(실측 29~132초).
export const pingServer = async (): Promise<boolean> => {
  try {
    const resp = await fetch(`${BASE}/documents`);
    return resp.ok;
  } catch {
    return false;
  }
};
