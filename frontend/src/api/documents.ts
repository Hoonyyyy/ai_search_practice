import { DocumentInfo } from '../types';

const BASE = process.env.REACT_APP_API_URL ?? 'http://localhost:8080/api';

// 백엔드 application.yml 의 max-file-size 와 같아야 한다.
// 브라우저 검사는 친절함(보내기 전에 바로 알림), 진짜 방어는 서버(누구나 우회 가능하니까).
export const MAX_UPLOAD_MB = 10;

export interface UploadCallbacks {
  onStage: (message: string, done?: number, total?: number) => void;
  onDone: (doc: DocumentInfo) => void;
  onError: (message: string) => void;
}

export const uploadDocument = async (file: File, callbacks: UploadCallbacks): Promise<void> => {
  const form = new FormData();
  form.append('file', file);

  const resp = await fetch(`${BASE}/documents/upload`, { method: 'POST', body: form });

  // 서버가 거절하면(413 등) 본문이 SSE 가 아니다. 여기서 끝내지 않으면 화면이 "업로드 중..." 에서 멈춘다.
  if (!resp.ok) {
    const body = await resp.json().catch(() => null);
    callbacks.onError(body?.message ?? '업로드에 실패했어요. 잠시 후 다시 시도해 주세요.');
    return;
  }

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const json = JSON.parse(line.slice(5).trimStart());
      if (json.stage === 'done') {
        callbacks.onDone({
          doc_id: json.doc_id,
          filename: json.filename,
          chunk_count: json.chunk_count,
          uploaded_at: json.uploaded_at ?? '',
        });
      } else if (json.stage === 'error') {
        callbacks.onError(json.message);
      } else {
        callbacks.onStage(json.message, json.done, json.total);
      }
    }
  }
};

export const listDocuments = async (): Promise<DocumentInfo[]> => {
  const resp = await fetch(`${BASE}/documents`);
  return resp.json();
};

export const deleteDocument = async (docId: string): Promise<void> => {
  await fetch(`${BASE}/documents/${docId}`, { method: 'DELETE' });
};
