import { DocumentInfo } from '../types';

const BASE = process.env.REACT_APP_API_URL ?? 'http://localhost:8080/api';

export interface UploadCallbacks {
  onStage: (message: string, done?: number, total?: number) => void;
  onDone: (doc: DocumentInfo) => void;
  onError: (message: string) => void;
}

export const uploadDocument = async (file: File, callbacks: UploadCallbacks): Promise<void> => {
  const form = new FormData();
  form.append('file', file);

  const resp = await fetch(`${BASE}/documents/upload`, { method: 'POST', body: form });
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
