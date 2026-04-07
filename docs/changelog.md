# 변경 이력

---

## v3.1 — Docker 환경 구성 및 파일 정리

### 배경
- 다른 PC(회사 노트북 등)에서 프로젝트를 이어서 개발할 때 환경 세팅 없이 바로 실행할 수 있도록
- `docker compose up` 한 줄로 전체 서비스가 뜨는 환경 구성

### 변경 사항

**신규 생성**
- `backend-spring/Dockerfile` — Maven 빌드 후 JRE로 실행 (멀티스테이지 빌드)
- `backend-ai/Dockerfile` — Python 패키지 설치 후 uvicorn 실행

**수정**
- `docker-compose.yml` — 구 `backend/` 기준 → 현재 3-서비스 구조로 전면 재작성
  - `backend-ai` (8001), `backend-spring` (8080), `frontend` (3000) 3개 서비스
  - Ollama는 호스트에서 별도 실행 (`host.docker.internal` 로 접근)
  - 볼륨: `chroma_data` (ChromaDB), `h2_data` (H2 DB)
- `frontend/nginx.conf` — 프록시 대상 변경 (`backend:8000` → `backend-spring:8080`), SSE 스트리밍 헤더 추가
- `frontend/Dockerfile` — 주석 정리
- `backend-spring/application.yml` — AI 서비스 URL을 환경변수로 주입 가능하도록 변경 (`${AI_SERVICE_URL:http://localhost:8001}`)

**삭제**
- `backend/` — 구 Python 올인원 백엔드 전체 제거
- `README.md`, `CODE_GUIDE.md`, `DESIGN.md` — 초기 자동생성 문서 제거 (`docs/`로 대체)
- 프로젝트 전체 `.DS_Store` 파일 제거

### Docker 실행 방법
```bash
# 사전 조건: Docker Desktop 설치, Ollama 실행 (ollama serve)
docker compose up --build
# 브라우저: http://localhost:3000
```

---

## v3.0 — 마이크로서비스 전환 (Spring Boot + Python AI)

### 배경
- Python과 React만으로는 Java/Spring 경험을 쌓기 어려움
- 대기업 이직 포트폴리오 강화 목적
- AI/ML 계층(Python)과 비즈니스 로직 계층(Java)을 분리하는 실무 패턴 적용

### 변경 사항

**신규 생성: `backend-spring/` (Spring Boot, 포트 8080)**
- `controller/` — HTTP 레이어, React와 직접 통신
- `service/` — 비즈니스 로직 (텍스트 추출, 청킹, SSE 오케스트레이션)
- `repository/` — Spring Data JPA (H2 DB)
- `domain/` — JPA 엔티티 (`Document`, `QueryLog`)
- `dto/` — 요청/응답 DTO
- `client/AiServiceClient.java` — Python AI 서비스 HTTP 호출 + SSE 프록시

**신규 생성: `backend-ai/` (Python FastAPI, 포트 8001)**
- `routers/` — Spring Boot 내부 전용 엔드포인트
- `services/` — 임베딩 생성, LLM 스트리밍
- `repositories/` — ChromaDB 접근

**프론트엔드 변경**
- API 타겟 변경: `localhost:8000` → `localhost:8080`

**아키텍처 흐름 변경**
```
이전: React → Python FastAPI (all-in-one)
이후: React → Spring Boot → Python AI Service
```

---

## v2.0 — FE/BE 구조 정형화 (리팩토링)

### 배경
- CSS가 모든 컴포넌트에 인라인으로 분산되어 유지보수 불가
- FastAPI 라우터에 비즈니스 로직과 DB 접근이 혼재
- API 함수가 `client.ts` 한 파일에 모두 집중

### Backend 변경 (`backend/` → `backend/`)

| 이전 | 이후 | 변경 내용 |
|---|---|---|
| `models/` | `schemas/` | FastAPI 관례에 맞게 이름 변경, 도메인별 파일 분리 |
| `services/` | `services/` + `repositories/` | 비즈니스 로직과 DB 접근 레이어 분리 |
| `services/rag_chain.py` | `services/search_service.py` | 역할을 명확히 하는 이름으로 변경 |
| `services/vector_store.py` | `repositories/vector_repository.py` | Repository 계층으로 이동 |
| `services/metrics_collector.py` | `repositories/metrics_repository.py` | Repository 계층으로 이동 |
| `routers/documents.py` (비즈니스 로직 포함) | `services/document_service.py` + 얇은 라우터 | 관심사 분리 |

**Spring MVC 대응표**

| Spring MVC | FastAPI (리팩토링 후) |
|---|---|
| `@Controller` | `routers/` |
| `@Service` | `services/` |
| `@Repository` | `repositories/` |
| `VO/DTO` | `schemas/` |

### Frontend 변경 (`frontend/src/`)

**디렉토리 구조 정비**
```
이전                              이후
components/                       components/
  AnswerPanel.tsx                   layout/Header.tsx
  MetricsDashboard.tsx              search/SearchPanel.tsx
  SearchPanel.tsx                   search/FileUpload.tsx
  common/FileUpload.tsx             search/AnswerPanel.tsx
  common/StatCard.tsx               dashboard/MetricsDashboard.tsx
  charts/...                        dashboard/StatCard.tsx
api/client.ts                       dashboard/charts/...
                                  api/documents.ts
                                  api/search.ts
                                  api/metrics.ts
                                  hooks/useUpload.ts
                                  hooks/useSearch.ts
                                  styles/theme.ts
                                  styles/global.css
```

**CSS 분리**
- 인라인 `style={{...}}` → CSS Modules (`.module.css`)
- 색상/간격 상수를 `styles/theme.ts` 에서 중앙 관리
- `react-app-env.d.ts` 추가 (CSS Module 타입 선언)

**React 패턴 적용**
- Custom Hook 분리: 컴포넌트 내 비즈니스 로직 → `hooks/useUpload.ts`, `hooks/useSearch.ts`
- API 레이어 도메인별 분리: `api/client.ts` 단일 파일 → `api/documents.ts`, `api/search.ts`, `api/metrics.ts`
- `App.tsx`에서 레이아웃 로직을 `Header.tsx`로 분리

---

## v1.1 — 업로드 UX 개선

### 배경
- 문서 업로드 시 진행 상황이 전혀 보이지 않아 완료 여부를 알 수 없었음
- 첫 업로드 시 임베딩 모델 로드 지연으로 수십 초 대기

### 변경 사항

**Backend**
- 업로드 엔드포인트를 단순 POST → SSE 스트리밍으로 변환
- 진행 단계를 이벤트로 전송: `extracting` → `splitting` → `embedding (N/M)` → `done`
- `embedder.py` 에 배치 처리 제너레이터 추가 (`embed_texts_batched`)
- `vector_repository.py` 에 스트리밍 저장 메서드 추가 (`add_chunks_stream`)
- 서버 시작 시 임베딩 모델 미리 로드 (`startup` 이벤트에서 `preload()`)

**Frontend**
- `FileUpload.tsx` — 진행 상황 텍스트 + 프로그레스 바 UI 추가
- `SearchPanel.tsx` — 업로드 콜백 구조 변경 (`onStage`, `onDone`, `onError`)
- `api/client.ts` — `uploadDocument` 함수를 SSE 스트리밍 방식으로 교체

---

## v1.0 — 초기 구현

### 구성
- **Backend**: Python FastAPI (포트 8000)
  - `routers/` — 문서, 검색, 메트릭 엔드포인트
  - `services/` — RAG 체인, 임베딩, 벡터 저장, 메트릭 수집
  - `models/` — Pydantic 요청/응답 모델
- **Frontend**: React + TypeScript (포트 3000)
  - 단일 `api/client.ts`로 API 통신
  - 인라인 스타일 CSS

### 주요 기능
- PDF/TXT/MD 문서 업로드 및 청킹 (500자, 50자 오버랩)
- sentence-transformers 임베딩 후 ChromaDB 저장
- Ollama (`llama3.2:3b`) LLM 기반 RAG 검색
- SSE 스트리밍 답변
- 성능 대시보드 (응답시간, 토큰 사용량, 사용자 평가 차트)

---

## 수정된 버그

### SSE 스트리밍 버그 (v1.0 → v1.1)

**문제**
- Ollama가 꺼져있을 때 검색하면 백엔드 ASGI 크래시
- 스트림이 `done` 이벤트 없이 끊기면 프론트 버튼이 영구 잠김 (`searching` 상태 stuck)

**원인**
- `rag_chain.py`에 `httpx.ConnectError` 예외 처리 없음
- `SearchPanel.tsx`에서 `setSearching(false)`를 `onDone` 콜백 안에서만 호출

**수정**
- Backend: `ConnectError` 잡아서 에러 SSE 이벤트 전송 후 정상 종료
- Frontend: `setSearching(false)`를 `finally` 블록으로 이동, `onError` 콜백 추가
