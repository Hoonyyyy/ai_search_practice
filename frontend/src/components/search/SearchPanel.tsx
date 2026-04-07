import React, { useEffect } from 'react';
import FileUpload from './FileUpload';
import { useUpload } from '../../hooks/useUpload';
import styles from './SearchPanel.module.css';

interface Props {
  onSearch: () => void;
  question: string;
  onQuestionChange: (q: string) => void;
  searching: boolean;
  searchError: string;
}

const SearchPanel: React.FC<Props> = ({ onSearch, question, onQuestionChange, searching, searchError }) => {
  const { docs, uploading, uploadStatus, uploadProgress, error: uploadError, loadDocs, upload, remove } = useUpload();

  useEffect(() => { loadDocs(); }, []);

  return (
    <div className={styles.container}>
      <div>
        <h3 className={styles.sectionTitle}>문서 업로드</h3>
        <FileUpload
          onUpload={upload}
          uploading={uploading}
          uploadStatus={uploadStatus}
          uploadProgress={uploadProgress}
        />
        {uploadError && <p className={styles.error}>{uploadError}</p>}
      </div>

      {docs.length > 0 && (
        <div>
          <h3 className={styles.sectionTitle}>업로드된 문서 ({docs.length})</h3>
          <div className={styles.docList}>
            {docs.map((doc) => (
              <div key={doc.doc_id} className={styles.docItem}>
                <div>
                  <span className={styles.docName}>{doc.filename}</span>
                  <span className={styles.docMeta}>{doc.chunk_count} 청크</span>
                </div>
                <button className={styles.deleteBtn} onClick={() => remove(doc.doc_id)}>
                  삭제
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 className={styles.sectionTitle}>질문하기</h3>
        <div className={styles.searchRow}>
          <input
            className={styles.searchInput}
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onSearch()}
            placeholder="문서에 대해 질문하세요..."
          />
          <button
            className={styles.searchBtn}
            onClick={onSearch}
            disabled={searching || !question.trim()}
          >
            {searching ? '생성 중...' : '검색'}
          </button>
        </div>
        {searchError && <p className={styles.error}>{searchError}</p>}
      </div>
    </div>
  );
};

export default SearchPanel;
