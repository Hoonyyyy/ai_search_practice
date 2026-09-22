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
    await deleteDocument(docId);
    await loadDocs();
  };

  return { docs, uploading, uploadStatus, uploadProgress, error, setError, loadDocs, upload, remove };
}
