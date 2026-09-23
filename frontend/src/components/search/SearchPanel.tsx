import React, { useEffect } from 'react';
import FileUpload from './FileUpload';
import { useUpload } from '../../hooks/useUpload';
import styles from './SearchPanel.module.css';

interface Props {
  serverReady: boolean;
  onSearch: () => void;
  question: string;
  onQuestionChange: (q: string) => void;
  searching: boolean;
  searchError: string;
}

const SearchPanel: React.FC<Props> = ({ serverReady, onSearch, question, onQuestionChange, searching, searchError }) => {
  const { docs, uploading, uploadStatus, uploadProgress, error: uploadError, loadDocs, upload, remove } = useUpload();

  useEffect(() => { if (serverReady) loadDocs(); }, [serverReady]);

  const myDocs = docs.filter((d) => !d.sample);
  const sampleDocs = docs.filter((d) => d.sample);

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
        {uploadError && <p className={styles.error} role="alert">⚠ {uploadError}</p>}
      </div>

      {myDocs.length > 0 && (
        <div>
          <h3 className={styles.sectionTitle}>내 문서</h3>
          <div className={styles.docList}>
            {myDocs.map((doc) => (
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
          <p className={styles.hint}>올린 문서는 1시간 뒤 자동으로 삭제돼요.</p>
          </div>
        </div>
      )}

      {sampleDocs.length > 0 && (
        <div>
          <h3 className={styles.sectionTitle}>예시 문서</h3>
          <div className={styles.docList}>
            {sampleDocs.map((doc) => (
              <div key={doc.doc_id} className={styles.docItem}>
                <div>
                  <span className={styles.badge}>예시</span>
                  <span className={styles.docName}>{doc.filename}</span>
                  <span className={styles.docMeta}>{doc.chunk_count} 청크</span>
                </div>
              </div>
            ))}
          </div>
          <p className={styles.hint}>먼저 둘러보시라고 올려둔 문서예요. 내 문서를 올리면 숨겨집니다.</p>
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
