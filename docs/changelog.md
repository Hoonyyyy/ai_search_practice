# 변경 이력

---

## v4.0 — 완전 로컬 스택 전환

### 배경
- Render/Vercel 배포본이 동작 불능 (무료 티어 만료·외부 API 키 문제)
- 개발·디버깅을 외부 API(Groq/Jina/Qdrant Cloud) 없이 로컬에서 완결하고 싶음

### 변경 사항

**backend-ai**
- 임베딩: Jina AI API → **Ollama `nomic-embed-text`** (768차원). `_embed` 가 `/api/embed` 배치 호출
- LLM: Groq API → **Ollama `llama3.2:3b`** (`/api/chat` 스트리밍). 토큰 수는 `prompt_eval_count`/`eval_count` 사용
- 벡터 DB: Qdrant Cloud → **Qdrant 임베디드**(`QdrantClient(path=...)`, 로컬 파일). Docker·API 키 불필요
  - `QDRANT_URL` 설정 시 원격 Qdrant 로 자동 전환 (하위호환)
  - payload 인덱스는 원격 모드에서만 생성 (임베디드는 무의미 + 경고)
- `config.py`: `ollama_base_url`, `llm_model`, `embed_model`, `embed_dim`, `qdrant_path` 추가
- `requirements.txt`: 버전 핀 추가, `groq` 제거
- `.env.example` 추가

**backend-spring**
- `pom.xml`: `java.version` 20 → **17** (설치된 JDK 17로 빌드, Spring Boot 3.2.3은 17 지원)

**인프라/실행**
- `start_search.ps1` / `stop_search.ps1` — Windows PowerShell 실행 스크립트 신규
- `docker-compose.yml` — 로컬 스택 기준으로 재작성 (Ollama 호스트 접근, Qdrant 임베디드 볼륨, ChromaDB/키 환경변수 제거)
- 낡은 주석 정리 (ChromaDB/Ollama-only 표현 → 현재 스택)

---

## v4.1 — RAG 품질/인코딩 디버깅 (한국어 문서)

### 증상
- 답변 품질이 낮고 환각이 심함, 응답이 느림 (이력서 PDF 기준)

### 원인 및 조치

**1. 한국어 깨짐 (MS949) — 가장 큰 원인**
- 한국어 Windows 에서 JVM `file.encoding=MS949` → AI 서비스의 UTF-8 응답(SSE),
  업로드 텍스트 파일, 멀티파트 파일명이 전부 깨져서 LLM 에 gibberish 컨텍스트가 들어감
- `pom.xml` spring-boot-maven-plugin 에 `-Dfile.encoding=UTF-8 -Dsun.jnu.encoding=UTF-8`
- `AiServiceClient`: `InputStreamReader` 에 `StandardCharsets.UTF_8` 명시 (2곳)
- `DocumentService.extractText`: `new String(bytes, UTF_8)`
- `Dockerfile`: JDK 20→17, `ENTRYPOINT` 에 UTF-8 플래그

**2. 임베딩 모델이 한국어에서 사실상 무작위**
- `nomic-embed-text` 는 영어 위주 → 한국어 쿼리·청크 유사도가 거의 구분 안 됨
  (검증: 청크에 그대로 들어있는 문장을 쿼리해도 top-8 밖)
- → `bge-m3` (다국어, 1024d) 로 교체. 동일 쿼리에서 정답 청크가 명확한 마진으로 1위

**3. 청킹이 문장 중간을 자름**
- 고정 500자 슬라이딩 → 줄 단위로 모아 700자까지 채우는 방식으로 변경 (`splitText`)
- 이력서·표처럼 줄 구조가 의미를 갖는 문서에서 청크 경계가 자연스러워짐

**4. 다단(컬럼) PDF 추출 순서 엉킴**
- `PDFTextStripper.setSortByPosition(true)` — 좌→우, 상→하 순서로 추출

**5. LLM**
- `llama3.2:3b` → `qwen2.5:3b` (한국어 품질·속도 모두 우위, ~12 tok/s)
- 프롬프트에 간결성 규칙 추가, `num_predict` 1024→640, `top_k` 6→4

### 남은 한계 (하드웨어)
- 이 PC: Intel Ultra 5 125H, 16GB, 디스크리트 GPU 없음 → Ollama 100% CPU
- bge-m3(1.2GB) + qwen2.5:3b(2.2GB) 동시 로드 시 RAM 여유 부족 → 스와핑 → 응답 지연 편차 큼

### 6. LLM provider 선택 + 소규모 문서 full-context (v4.1 후속)
- `LLM_PROVIDER=ollama|groq` — 임베딩·벡터는 계속 로컬, 답변 생성만 Groq 클라우드로 오프로드 가능
  - `_stream_ollama` / `_stream_groq` 분기, SSE 계약 동일
  - 기본 모델 `openai/gpt-oss-120b`. gpt-oss 계열은 `reasoning_effort=low` 로 과잉 추론 억제
    (안 하면 단답에도 10~17초). 적용 후 이력서 6질문 평균 3.1초 (Ollama CPU 는 25~70초)
  - Groq 모델 목록이 자주 바뀜 — `llama-3.3-70b-versatile` 등 구 모델은 404. 콘솔에서 확인
- `FULL_CONTEXT_THRESHOLD` (기본 12) — 컬렉션 청크 수가 이하이면 벡터 검색을 건너뛰고
  전체 청크를 순서대로 컨텍스트에 넣는다. 문서 1~2개짜리 데모에서 검색 누락 제거

---

## v3.4 — Qdrant Cloud 전환 + Render cold start 502 대응

### 배경
- Render 무료 플랜 512MB RAM 초과 (chromadb + onnxruntime ~430MB) → OOM
- Python AI cold start 시 Render nginx가 502 즉시 반환 → 검색/삭제 실패

### 변경 사항

**OOM 해결 (backend-ai)**
- chromadb + onnxruntime → Qdrant Cloud (HTTP 클라이언트) + fastembed 전환
- `requirements.txt`: `qdrant-client[fastembed]`, `groq` 로 교체
- `config.py`: `qdrant_url`, `qdrant_api_key` 설정 추가
- `repositories/vector_repository.py`: Qdrant Cloud 기반 전면 재작성
- `services/embedder.py`: fastembed `BAAI/bge-small-en-v1.5` 모델 preload
- `Dockerfile`: 빌드 시 fastembed 모델 다운로드 (cold start 지연 방지)
- 메모리 사용량: ~430MB → ~230MB

**Render cold start 502 대응 (backend-spring)**
- `AiServiceClient`: `searchVectors`, `deleteVectors`, `embedAndStore` 에 retry 로직 추가
  - 502 응답 시 5초 간격으로 최대 12회 재시도 (총 60초)
- `SearchController`, `DocumentController`: `X-Accel-Buffering: no` 헤더 추가
- `SearchService`, `DocumentService`: heartbeat SSE comment 5초 간격 전송 (nginx 502 방지)

---

## v3.3 — GitHub CLI 및 PR 기반 협업 워크플로우 설정

### 배경
- `git push` + GitHub 웹에서 PR 여는 방식은 번거로움
- CLI에서 모든 작업(브랜치 생성 → 커밋 → PR 생성)을 완결하기 위해 gh CLI 도입

### 변경 사항
- `gh` CLI 설치 및 GitHub 계정 인증 (`gh auth login`)
- SSH 프로토콜로 git 연동 (`git@github.com:Hoonyyyy/ai_search_practice.git`)
- 이제부터 모든 기능 개발은 feature 브랜치 → PR → master merge 방식으로 진행

### 개발 흐름 (실제 사용 예시)
```bash
git checkout -b feature/기능명        # 브랜치 생성
# 개발 작업
git add -p                             # 변경 사항 확인하며 스테이징
git commit -m "feat: 기능 설명"
git push origin feature/기능명
gh pr create --title "..." --body "..." # PR 생성
gh pr merge --squash                    # PR 머지
git checkout master && git pull
git branch -d feature/기능명
```

---

## v3.2 — GitHub Flow 브랜치 전략 도입

### 배경
- `master` 단일 브랜치만 사용하는 방식은 현업 협업 환경과 다름
- 기능 단위로 브랜치를 분리해 이력을 명확히 관리

### 브랜치 전략 (GitHub Flow)

```
master          → 항상 배포 가능한 최종 코드. 직접 commit 금지.
feature/이름    → 기능 하나씩 개발. 완료되면 master에 merge.
hotfix/이름     → 긴급 버그 수정. 완료되면 master에 merge.
```

**작업 흐름:**
```
1. feature/기능명 브랜치 생성
2. 개발 및 커밋
3. master에 merge
4. GitHub push
```

### 변경 사항
- `docs/architecture.md` — 브랜치 전략 섹션 추가
- GitHub remote 연결: `git@github.com:Hoonyyyy/ai_search_practice.git`
- `.gitignore` 현재 구조에 맞게 재작성 (venv, target, node_modules 등)

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
