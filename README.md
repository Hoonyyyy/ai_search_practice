RAG 프로젝트

## 서비스별 역할

### React (`frontend/`)
- 사용자 인터페이스
- Spring Boot `/api/**` 와만 통신 (8080)
- Python AI 서비스에는 직접 접근하지 않는다

### Spring Boot (`backend-spring/`)
- React의 모든 요청을 받는 메인 API 게이트웨이
- PDF/TXT/MD 텍스트 추출 및 청킹 (PDFBox)
- 문서 메타데이터 · 쿼리 로그를 H2(JPA)로 관리
- Python AI 서비스를 내부적으로 호출해 결과를 프록시

### Python FastAPI (`backend-ai/`)
- AI/ML 전용 내부 서비스 (외부에서 직접 호출 안 함)
- 임베딩 생성 (sentence-transformers `all-MiniLM-L6-v2`)
- 벡터 저장/검색 (ChromaDB)
- LLM 응답 스트리밍 (Ollama)


<br>
<br>

FE
- react, typescript

BE
- java spring boot
- python fastapi

DB
- chroma db
- h2
