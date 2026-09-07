# AI Search — Claude 작업 가이드

이 파일을 읽으면 지금까지의 모든 작업 맥락을 파악할 수 있습니다.
자세한 내역은 `docs/changelog.md`, 코드 흐름은 `docs/code_guide.md`,
디버깅 방법은 `docs/debugging.md`, API 수동 테스트는 루트 `api.http` 를 참고하세요.

---

## 프로젝트 개요

RAG(Retrieval-Augmented Generation) 기반 문서 검색 서비스.
PDF/TXT/MD 문서를 업로드하면 임베딩 후 벡터 DB에 저장, 질문하면 관련 청크를 찾아 LLM이 답변을 스트리밍으로 반환.

---

## 기술 스택 (v4.0 — 로컬 스택)

| 서비스 | 기술 | 포트 |
|---|---|---|
| Frontend | React + TypeScript + CSS Modules | 3000 |
| Backend (메인) | Spring Boot 3.2 + JPA/H2 (Java 17) | 8080 |
| Backend (AI) | Python FastAPI | 8001 |
| LLM | Ollama (`qwen2.5:3b`) 또는 Groq (`LLM_PROVIDER=groq`) | 11434 |
| 임베딩 | Ollama (`bge-m3`, 1024차원) | 11434 |
| 벡터 DB | Qdrant 임베디드 (로컬 파일, `backend-ai/data/qdrant`) | - |

> `.env` 로 전환: `LLM_PROVIDER=groq`(+`GROQ_API_KEY`) 로 답변 생성만 클라우드로,
> `QDRANT_URL` 로 원격 Qdrant. 임베딩은 항상 Ollama. `backend-ai/.env.example` 참고.
> 이 PC는 GPU가 없어 로컬 LLM 이 느리다(25~70초) → 데모는 `LLM_PROVIDER=groq` 권장.

---

## 디렉토리 구조

```
rag_search/
├── frontend/          # React (CSS Modules, Custom Hooks, 도메인별 API)
├── backend-spring/    # Spring Boot (Controller/Service/Repository/Domain/DTO)
├── backend-ai/        # Python FastAPI (routers/services/repositories)
├── docs/
│   ├── code_guide.md   # 코드 흐름·파일별 역할
│   └── changelog.md     # 버전별 변경 이력
├── docker-compose.yml   # 전체 서비스 한번에 실행
├── start_search.ps1 / stop_search.ps1   # Windows 실행/종료
├── start_search.sh  / stop_search.sh    # macOS/Linux 실행/종료
└── CLAUDE.md            # 이 파일
```

---

## 로컬 실행 방법

### 사전 준비 (최초 1회)

```powershell
# 1. Ollama 설치 후 모델 받기
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# 2. Python AI 서비스 의존성
cd backend-ai
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# 3. 프론트엔드 의존성
cd ..\frontend
npm install
```

### 실행

```powershell
# Windows — 한 번에
.\start_search.ps1          # → http://localhost:3000
.\stop_search.ps1

# 또는 개별 실행
cd backend-ai   && .\venv\Scripts\uvicorn main:app --port 8001
cd backend-spring && mvn spring-boot:run
cd frontend     && npm start
```

Docker (호스트에 Ollama 실행 중이어야 함):
```bash
docker compose up --build   # → http://localhost:3000
```

---

## GitHub

- 레포지토리: `https://github.com/Hoonyyyy/ai_search_practice`
- 브랜치 전략: GitHub Flow (`feature/*` → PR → `master`)

### 커밋 메시지 접두사
| 접두사 | 용도 |
|---|---|
| `feat:` | 새 기능 |
| `fix:` | 버그 수정 |
| `refactor:` | 리팩토링 |
| `docs:` | 문서 수정 |
| `chore:` | 설정/환경 |

### 변경 시 필수 작업
1. `docs/changelog.md` 업데이트
2. feature 브랜치 → PR → master 머지

---

## 주요 작업 히스토리

- **v1.0** — Python FastAPI + React 초기 구현 (RAG, SSE 스트리밍, 대시보드)
- **v1.1** — 업로드 UX 개선 (SSE 진행률 스트리밍)
- **v2.0** — FE/BE 구조 정형화 (CSS Modules, Custom Hooks, 레이어드 아키텍처)
- **v3.0** — 마이크로서비스 전환 (Spring Boot 8080 + Python AI 8001)
- **v3.1** — Docker 환경 구성
- **v3.2~3.3** — GitHub Flow + gh CLI 워크플로우
- **v3.4** — Qdrant Cloud + Jina + Groq 전환 (Render 배포용, OOM/cold start 대응)
- **v4.0** — 완전 로컬 스택 전환 (Ollama LLM+임베딩, Qdrant 임베디드), Java 17, Windows 실행 스크립트

자세한 내용은 `docs/changelog.md` 참고.
