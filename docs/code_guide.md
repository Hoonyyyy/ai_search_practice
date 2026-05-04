# 코드 흐름 가이드

바이브코딩으로 만들어진 코드 전체 흐름과 각 파일/함수의 역할을 설명합니다.

---

## 현재 기술 스택

| 서비스 | 기술 | 위치 |
|---|---|---|
| 프론트엔드 | React + TypeScript | Vercel |
| 메인 백엔드 | Spring Boot (Java) | Render |
| AI 백엔드 | Python FastAPI | Render |
| 벡터 DB | Qdrant Cloud | Qdrant Cloud (무료) |
| LLM | Groq API (llama-3.1-8b) | Groq Cloud (무료) |
| 임베딩 | Jina AI API (jina-embeddings-v3) | Jina Cloud (무료) |

---

## 전체 구조

```
사용자 브라우저
    │  HTTP (REST + SSE)
    ▼
React 프론트엔드 (Vercel)
    │  HTTP (REST + SSE)
    ▼
Spring Boot 메인 백엔드 (Render, 8080)
    │  내부 HTTP
    ├──────────────────────────────────────┐
    ▼                                      ▼
Python AI 백엔드 (Render, 8001)       H2 파일 DB (로컬)
    │                                  (문서 메타 + 쿼리 로그)
    ├── Jina AI API  (임베딩 생성)
    ├── Qdrant Cloud (벡터 저장/검색)
    └── Groq API     (LLM 답변 생성)
```

**핵심 원칙**: 프론트엔드는 Spring Boot하고만 통신한다. Python AI 서비스는 Spring Boot가 내부적으로만 호출한다.

---

## 두 가지 주요 흐름

### 흐름 1: 문서 업로드

```
사용자가 PDF/TXT/MD 파일을 드래그앤드롭
    │
    ▼
[React] FileUpload.tsx
→ api/documents.ts: uploadDocument()
→ POST /api/documents/upload (multipart/form-data)
    │
    ▼
[Spring Boot] DocumentController.java: upload()
→ DocumentService.java: upload()
    │
    ├─ 1. 텍스트 추출 (PDF → PDFBox, TXT/MD → 그냥 읽기)
    ├─ 2. 청킹 (500자씩 자르기, 50자 겹침)
    ├─ 3. AiServiceClient.embedAndStore() 호출
    │       │
    │       ▼
    │   [Python AI] POST /ai/documents/embed-and-store
    │   → routers/documents.py: embed_and_store()
    │   → vector_repository.add_chunks_stream()
    │       ├─ Jina AI API로 임베딩 벡터 생성 (512차원)
    │       └─ Qdrant Cloud에 저장 (배치 16개씩)
    │       → SSE로 진행률 Spring Boot에 스트리밍 (1/10, 2/10 ...)
    │
    ├─ 4. 문서 메타데이터 H2 DB에 저장 (doc_id, filename, chunk_count)
    └─ 5. "done" 이벤트 → React에 완료 알림
```

### 흐름 2: 검색 (RAG)

```
사용자가 질문 입력 후 검색 버튼
    │
    ▼
[React] SearchPanel.tsx
→ api/search.ts: queryStream()
→ POST /api/search/query
    │
    ▼
[Spring Boot] SearchController.java: query()
→ SearchService.java: query()
    │
    ├─ 1. AiServiceClient.searchVectors() 호출
    │       │
    │       ▼
    │   [Python AI] POST /ai/search
    │   → routers/search.py: search()
    │   → vector_repository.similarity_search()
    │       ├─ Jina AI API로 질문 임베딩 (512차원)
    │       └─ Qdrant Cloud에서 유사 청크 top-k개 반환
    │
    ├─ 2. 출처 정보(sources) SSE 이벤트로 React에 전송
    │
    ├─ 3. AiServiceClient.streamLlm() 호출
    │       │
    │       ▼
    │   [Python AI] POST /ai/llm/stream
    │   → routers/llm.py: stream_llm()
    │   → llm_service.stream_response()
    │       ├─ 시스템 프롬프트 + 검색된 청크 + 질문을 합쳐 프롬프트 구성
    │       └─ Groq API에 스트리밍 요청 → 토큰 단위로 SSE yield
    │
    ├─ 4. 쿼리 로그 H2 DB에 저장 (질문, 답변, 토큰수, 응답시간)
    └─ 5. "done" 이벤트 → React에 완료 알림
```

---

## Spring Boot 파일별 역할

### `controller/DocumentController.java`
HTTP 요청을 받는 창구. 비즈니스 로직은 없고 Service에 위임만 한다.
- `POST /api/documents/upload` → `DocumentService.upload()`
- `GET /api/documents` → `DocumentService.listDocuments()`
- `DELETE /api/documents/{docId}` → `DocumentService.deleteDocument()`

### `controller/SearchController.java`
- `POST /api/search/query` → `SearchService.query()`
- `POST /api/search/feedback` → `SearchService.saveFeedback()`

### `service/DocumentService.java`
문서 업로드의 전체 오케스트레이션을 담당한다.

| 메서드 | 역할 |
|---|---|
| `upload(file)` | 전체 업로드 흐름 실행 (SSE 스트리밍) |
| `extractText(file)` | PDF → PDFBox, TXT/MD → 문자열 변환 |
| `splitText(text)` | 500자 청크로 분할, 50자 겹침으로 문맥 유지 |
| `listDocuments()` | H2 DB에서 문서 목록 조회 |
| `deleteDocument(docId)` | Qdrant 벡터 삭제 + H2 메타데이터 삭제 |

### `service/SearchService.java`
검색 + LLM 흐름의 전체 오케스트레이션을 담당한다.

| 메서드 | 역할 |
|---|---|
| `query(question, topK)` | 벡터 검색 → 출처 전송 → LLM 스트리밍 → 로그 저장 |
| `saveFeedback(queryId, score)` | 별점 피드백을 쿼리 로그에 업데이트 |

### `client/AiServiceClient.java`
Python AI 서비스와 통신하는 HTTP 클라이언트. 502 에러(Render cold start) 시 5초 간격으로 최대 12번 재시도한다.

| 메서드 | 역할 |
|---|---|
| `embedAndStore(docId, filename, chunks, emitter)` | Python AI에 청크 전송, SSE 응답을 React로 프록시 |
| `searchVectors(query, topK)` | Python AI에 검색 요청, 청크 목록 반환 |
| `streamLlm(question, chunks, queryId, emitter)` | Python AI LLM 스트리밍, 토큰/답변 수집 후 반환 |
| `deleteVectors(docId)` | Python AI에 삭제 요청 |

### `domain/Document.java`
H2 DB의 `documents` 테이블과 1:1 매핑되는 엔티티.
- `doc_id` (PK), `filename`, `chunk_count`, `uploaded_at`

### `domain/QueryLog.java`
H2 DB의 `query_logs` 테이블. 검색할 때마다 저장된다.
- `id`, `question`, `answer`, `response_time_ms`, `input_tokens`, `output_tokens`, `score`

---

## Python AI 파일별 역할

### `main.py`
FastAPI 앱 시작점. 라우터 3개를 등록한다.
```
/ai/documents  → routers/documents.py
/ai/search     → routers/search.py
/ai/llm        → routers/llm.py
```

### `config.py`
`.env` 파일에서 환경변수를 읽어 `settings` 객체로 제공한다.
- `groq_api_key`, `qdrant_url`, `qdrant_api_key`, `jina_api_key`

### `routers/documents.py`
| 엔드포인트 | 역할 |
|---|---|
| `POST /ai/documents/embed-and-store` | 청크 임베딩 후 Qdrant 저장, 진행률 SSE 스트리밍 |
| `DELETE /ai/documents/{doc_id}` | Qdrant에서 해당 문서 벡터 전체 삭제 |

### `routers/search.py`
| 엔드포인트 | 역할 |
|---|---|
| `POST /ai/search` | 질문 임베딩 후 Qdrant 유사도 검색, 청크 목록 반환 |

### `routers/llm.py`
| 엔드포인트 | 역할 |
|---|---|
| `POST /ai/llm/stream` | Groq API로 LLM 답변 생성, SSE 스트리밍 |

### `repositories/vector_repository.py`
Qdrant Cloud와 직접 통신하는 데이터 접근 레이어.

| 함수 | 역할 |
|---|---|
| `_get_client()` | Qdrant 클라이언트 초기화 (컬렉션 없으면 자동 생성, doc_id 인덱스 생성) |
| `_embed(texts)` | Jina AI API 호출해 텍스트 → 512차원 벡터 변환 |
| `add_chunks_stream(doc_id, filename, chunks)` | 16개씩 배치로 임베딩 후 Qdrant 저장, 진행률 yield |
| `similarity_search(query, top_k)` | 질문 임베딩 후 Qdrant에서 유사 청크 검색 |
| `delete_document(doc_id)` | doc_id 필터로 Qdrant 벡터 삭제 |

### `services/llm_service.py`

| 함수 | 역할 |
|---|---|
| `_build_prompt(question, chunks)` | 검색된 청크들을 컨텍스트로 묶어 프롬프트 생성 |
| `stream_response(question, chunks)` | Groq API에 스트리밍 요청, 토큰 단위로 SSE yield |

---

## SSE(Server-Sent Events)란?

이 프로젝트에서 업로드/검색 진행 상황을 실시간으로 보여주는 데 사용한다.

```
일반 HTTP:  요청 → [서버 처리] → 응답 (한 번에 전체)
SSE:        요청 → 서버가 조금씩 데이터를 밀어줌 → 연결 종료
```

Spring Boot의 `SseEmitter`가 SSE 연결을 관리하고, Python AI 서비스도 `StreamingResponse`로 SSE를 내보낸다. Spring Boot는 Python AI의 SSE를 받아서 React로 다시 프록시한다.

---

## 환경변수 목록

| 변수 | 위치 | 용도 |
|---|---|---|
| `GROQ_API_KEY` | Python AI | Groq LLM API 인증 |
| `QDRANT_URL` | Python AI | Qdrant Cloud 클러스터 주소 |
| `QDRANT_API_KEY` | Python AI | Qdrant Cloud 인증 |
| `JINA_API_KEY` | Python AI | Jina AI 임베딩 API 인증 |
| `AI_SERVICE_URL` | Spring Boot | Python AI 서비스 주소 |
| `CORS_ALLOWED_ORIGINS` | Spring Boot | Vercel 프론트엔드 도메인 허용 |
