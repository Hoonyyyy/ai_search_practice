import { useState } from 'react';
import { DocumentInfo } from '../types';
import { uploadDocument, listDocuments, deleteDocument, MAX_UPLOAD_MB } from '../api/documents';
import { wakeAiService } from '../api/server';

export interface UploadProgress {
  done: number;
  total: number;
}

export function useUpload() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState('');

  const loadDocs = async () => {
    const list = await listDocuments();
    setDocs(list);
  };

  const upload = async (file: File) => {

    const sizeMb = file.size / 1024 / 1024;
    if (sizeMb > MAX_UPLOAD_MB) {
      setError(`${MAX_UPLOAD_MB}MB 이하 파일만 올릴 수 있어요. (선택한 파일: ${file.name}, ${sizeMb.toFixed(1)}MB)`);
      return;
    }

    const existing = docs.find((d) => !d.sample);
    if (existing && !window.confirm(
      `이미 "${existing.filename}" 을 올려두셨어요.\n` +
      `"${file.name}" 으로 바꿀까요?\n\n기존 문서는 삭제됩니다.`
    )) {
      return;
    }

    wakeAiService();
    setUploading(true);
    setUploadStatus('');
    setUploadProgress(null);
    setError('');

    try {
      await uploadDocument(file, {
        onStage: (message, done, total) => {
          setUploadStatus(message);
          if (done !== undefined && total !== undefined) {
            setUploadProgress({ done, total });
          }
        },
        onDone: async () => {
          setUploadStatus('완료!');
          setUploadProgress(null);
          await loadDocs();
          setTimeout(() => {
            setUploading(false);
            setUploadStatus('');
          }, 800);
        },
        onError: (msg) => {
          setError(msg);
          setUploading(false);
          setUploadStatus('');
        },
      });
    } catch {
      setError('업로드 중 오류가 발생했습니다.');
      setUploading(false);
      setUploadStatus('');
    }
  };

  const remove = async (docId: string) => {
    wakeAiService();
    setError('');

    try {
      await deleteDocument(docId);
    } catch (e) {
      // 실패를 삼키면 "지웠는데 다시 나타나는" 유령 버그가 된다
      setError(e instanceof Error ? e.message : '삭제하지 못했어요.');
    }

    await loadDocs();   // 성공이든 실패든 서버 상태에 화면을 맞춘다
  };

  return { docs, uploading, uploadStatus, uploadProgress, error, setError, loadDocs, upload, remove };
}
