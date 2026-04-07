import React, { useCallback, useState } from 'react';
import styles from './FileUpload.module.css';

interface UploadProgress {
  done: number;
  total: number;
}

interface Props {
  onUpload: (file: File) => void;
  uploading: boolean;
  uploadStatus?: string;
  uploadProgress?: UploadProgress | null;
}

const FileUpload: React.FC<Props> = ({ onUpload, uploading, uploadStatus, uploadProgress }) => {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  }, [onUpload]);

  const dropzoneClass = [
    styles.dropzone,
    dragging ? styles.dropzoneDragging : '',
  ].join(' ');

  return (
    <div
      className={dropzoneClass}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => document.getElementById('file-input')?.click()}
    >
      <input
        id="file-input"
        type="file"
        accept=".pdf,.txt,.md"
        style={{ display: 'none' }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); }}
      />

      {uploading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
          <span className={styles.statusText}>{uploadStatus || '업로드 중...'}</span>
          {uploadProgress && (
            <div className={styles.progressBar}>
              <div className={styles.progressTrack}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${Math.round((uploadProgress.done / uploadProgress.total) * 100)}%` }}
                />
              </div>
              <div className={styles.progressLabel}>
                {uploadProgress.done} / {uploadProgress.total}
              </div>
            </div>
          )}
        </div>
      ) : (
        <>
          <div className={styles.icon}>📄</div>
          <div className={styles.hint}>PDF, TXT, MD 파일을 드래그하거나 클릭하여 업로드</div>
        </>
      )}
    </div>
  );
};

export default FileUpload;
