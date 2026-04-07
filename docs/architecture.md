# 아키텍처 문서

## 전체 구조

```
React (3000)
    │  HTTP (REST + SSE)
    ▼
Spring Boot (8080)          ← 메인 API 서버, 비즈니스 로직, JPA/H2
    │  내부 HTTP (REST + SSE 프록시)
    ▼
Python FastAPI (8001)       ← AI 전용 서비스 (임베딩, 벡터 검색, LLM)
    │
    ├── ChromaDB            ← 벡터 DB (로컬 파일)
    └── Ollama (11434)      ← 로컬 LLM (llama3.2:3b)
```

---

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

---

## 디렉토리 상세

### `backend-spring/`

```
src/main/java/com/ragsearch/
├── controller/          # HTTP 레이어 - Spring @RestController
│   ├── DocumentController.java   # POST /api/documents/upload, GET, DELETE
│   ├── SearchController.java     # POST /api/search/query, /feedback
│   └── MetricsController.java    # GET /api/metrics/summary, /timeline, /recent
│
├── service/             # 비즈니스 로직 - Spring @Service
│   ├── DocumentService.java      # 텍스트 추출, 청킹, 업로드 SSE 오케스트레이션
│   ├── SearchService.java        # 벡터 검색 + LLM SSE 오케스트레이션, 로그 저장
│   └── MetricsService.java       # 집계 쿼리 및 DTO 변환
│
├── repository/          # 데이터 접근 - Spring Data JPA @Repository
│   ├── DocumentRepository.java   # documents 테이블 CRUD
│   └── QueryLogRepository.java   # query_logs 테이블 CRUD + 집계 쿼리
│
├── domain/              # JPA 엔티티 (DB 테이블과 1:1 매핑)
│   ├── Document.java             # 문서 메타데이터 (doc_id, filename, chunk_count, uploaded_at)
│   └── QueryLog.java             # 쿼리 로그 (question, answer, tokens, response_time, score)
│
├── dto/                 # 요청/응답 데이터 전송 객체 (Spring의 VO/DTO)
│   ├── document/DocumentDto.java
│   ├── search/QueryRequestDto.java, FeedbackRequestDto.java
│   └── metrics/MetricsSummaryDto.java, TimelinePointDto.java, QueryLogDto.java
│
├── client/              # 외부 서비스 호출 추상화
│   └── AiServiceClient.java      # Python AI 서비스 HTTP 호출 (SSE 프록시 포함)
│
└── config/              # 설정
    ├── AppConfig.java            # RestTemplate, ExecutorService 빈 등록
    └── CorsConfig.java           # CORS 허용 설정 (localhost:3000)

src/main/resources/
└── application.yml      # 포트, DB, AI 서비스 URL, 청킹 설정
```

| 계층 | Spring 애노테이션 | 역할 |
|---|---|---|
| Controller | `@RestController` | HTTP 요청/응답, 유효성 검사 |
| Service | `@Service` | 비즈니스 로직, 트랜잭션 |
| Repository | `@Repository` | DB 접근 (JPA) |
| Domain | `@Entity` | DB 테이블 매핑 |
| DTO | - | 계층 간 데이터 전달 |
| Client | `@Component` | 외부 API 호출 |

**DB**: H2 파일 DB (`./data/ragsearch.mv.db`)
콘솔 확인: http://localhost:8080/h2-console (JDBC URL: `jdbc:h2:file:./data/ragsearch`)

---

### `backend-ai/`

```
backend-ai/
├── main.py              # FastAPI 앱 진입점, 라우터 등록, 모델 preload
├── config.py            # 설정값 (ChromaDB 경로, Ollama URL, 임베딩 모델명)
│
├── routers/             # HTTP 엔드포인트 (Spring Boot 내부 전용)
│   ├── documents.py     # POST /ai/documents/embed-and-store, DELETE /ai/documents/{id}
│   ├── search.py        # POST /ai/search (벡터 유사도 검색)
│   └── llm.py           # POST /ai/llm/stream (LLM SSE 스트리밍)
│
├── services/            # 비즈니스 로직
│   ├── embedder.py      # SentenceTransformer 임베딩 생성 (배치 처리)
│   └── llm_service.py   # Ollama API 호출, SSE 이벤트 yield
│
└── repositories/        # 데이터 접근
    └── vector_repository.py  # ChromaDB CRUD (add, search, delete)
```

**AI 서비스 내부 API:**

| 엔드포인트 | 방식 | 설명 |
|---|---|---|
| `/ai/documents/embed-and-store` | POST / SSE | 청크 임베딩 후 ChromaDB 저장 (진행률 스트리밍) |
| `/ai/documents/{doc_id}` | DELETE | ChromaDB에서 문서 벡터 삭제 |
| `/ai/search` | POST / JSON | 유사 청크 검색 |
| `/ai/llm/stream` | POST / SSE | Ollama LLM 응답 스트리밍 |

---

### `frontend/`

```
src/
├── styles/
│   ├── theme.ts         # 디자인 토큰 (색상, 간격, 폰트 크기 상수)
│   └── global.css       # 전역 CSS (reset, body, animation)
│
├── api/                 # 도메인별 API 함수
│   ├── documents.ts     # uploadDocument, listDocuments, deleteDocument
│   ├── search.ts        # queryStream, sendFeedback
│   └── metrics.ts       # getMetricsSummary, getTimeline, getRecentLogs
│
├── hooks/               # 비즈니스 로직 분리 (Custom React Hooks)
│   ├── useUpload.ts     # 업로드 상태, 진행률, 문서 목록
│   └── useSearch.ts     # 검색 상태, 스트리밍 텍스트, 출처
│
├── components/
│   ├── layout/
│   │   └── Header.tsx + Header.module.css
│   ├── search/          # 검색 관련 컴포넌트
│   │   ├── SearchPanel.tsx + .module.css   # 업로드 + 질문 입력
│   │   ├── FileUpload.tsx + .module.css    # 드래그앤드롭 + 진행 바
│   │   └── AnswerPanel.tsx + .module.css   # 스트리밍 답변 + 출처 + 별점
│   └── dashboard/       # 대시보드 관련 컴포넌트
│       ├── MetricsDashboard.tsx + .module.css
│       ├── StatCard.tsx + .module.css
│       └── charts/      # Recharts 기반 차트
│           ├── ResponseTimeChart.tsx
│           ├── TokenUsageChart.tsx
│           ├── ScoreChart.tsx
│           └── Chart.module.css
│
└── types/index.ts       # TypeScript 타입 정의
```

---

## 실행 방법

```bash
# 1. Python AI 서비스 (포트 8001)
cd backend-ai
source venv/bin/activate
uvicorn main:app --port 8001

# 2. Spring Boot (포트 8080)
cd backend-spring
mvn spring-boot:run

# 3. React (포트 3000)
cd frontend
npm start
```

> Ollama도 실행 중이어야 합니다: `ollama serve`
