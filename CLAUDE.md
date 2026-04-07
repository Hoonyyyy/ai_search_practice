# AI Search — Claude 작업 가이드

이 파일을 읽으면 지금까지의 모든 작업 맥락을 파악할 수 있습니다.
자세한 내역은 `docs/changelog.md`, 구조는 `docs/architecture.md`를 참고하세요.

---

## 프로젝트 개요

RAG(Retrieval-Augmented Generation) 기반 문서 검색 서비스.
PDF/TXT/MD 문서를 업로드하면 임베딩 후 ChromaDB에 저장, 질문하면 관련 청크를 찾아 Ollama LLM이 답변을 스트리밍으로 반환.

---

## 기술 스택

| 서비스 | 기술 | 포트 |
|---|---|---|
| Frontend | React + TypeScript + CSS Modules | 3000 |
| Backend (메인) | Spring Boot + JPA/H2 | 8080 |
| Backend (AI) | Python FastAPI + ChromaDB + Ollama | 8001 |
| LLM | Ollama (`llama3.2:3b`) | 11434 |
| 벡터 DB | ChromaDB (로컬 파일) | - |

---

## 디렉토리 구조

```
ai_search/
├── frontend/          # React (CSS Modules, Custom Hooks, 도메인별 API)
├── backend-spring/    # Spring Boot (Controller/Service/Repository/Domain/DTO)
├── backend-ai/        # Python FastAPI (routers/services/repositories)
├── docs/
│   ├── architecture.md  # 전체 아키텍처 상세
│   └── changelog.md     # 버전별 변경 이력 (v1.0 ~ 현재)
├── docker-compose.yml   # 전체 서비스 한번에 실행
└── CLAUDE.md            # 이 파일
```

---

## 로컬 실행 방법

```bash
# 1. Ollama 실행 (필수)
ollama serve

# 2. Python AI 서비스
cd backend-ai && source venv/bin/activate
uvicorn main:app --port 8001

# 3. Spring Boot
cd backend-spring && mvn spring-boot:run

# 4. React
cd frontend && npm start
```

또는 Docker로 한번에:
```bash
docker compose up --build
# 브라우저: http://localhost:3000
```

---

## GitHub

- 레포지토리: `git@github.com:Hoonyyyy/ai_search_practice.git`
- 브랜치 전략: GitHub Flow (`feature/*` → PR → `master`)
- PR 도구: `gh` CLI

---

## 개발 규칙

### 브랜치 & PR 흐름
```bash
git checkout -b feature/기능명
# 개발
git add . && git commit -m "feat: 설명"
git push origin feature/기능명
gh pr create --title "..." --body "..."
gh pr merge --squash --delete-branch
git checkout master && git pull
```

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
3. GitHub push

---

## 지금까지 주요 작업 히스토리

- **v1.0** — Python FastAPI + React 초기 구현 (RAG, SSE 스트리밍, 대시보드)
- **v1.1** — 업로드 UX 개선 (SSE 진행률 스트리밍, 임베딩 모델 preload)
- **v2.0** — FE/BE 구조 정형화 (CSS Modules, Custom Hooks, 레이어드 아키텍처)
- **v3.0** — 마이크로서비스 전환 (Spring Boot 8080 + Python AI 8001)
- **v3.1** — Docker 환경 구성 (docker-compose, Nginx, 멀티스테이지 빌드)
- **v3.2** — GitHub Flow 브랜치 전략 도입
- **v3.3** — gh CLI 인증 및 PR 기반 워크플로우 설정

자세한 내용은 `docs/changelog.md` 참고.

---

## 사용자 정보

- 맥북 사용자 (macOS, zsh)
- Claude Code CLI 또는 VS Code 익스텐션으로 작업
- Python 환경: `Optional[float]` 사용 (`float | None` 미지원)
