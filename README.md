## 전체 구조 (v4.0 — 로컬 스택)

```
사용자 브라우저
    │  HTTP (REST + SSE)
    ▼
React 프론트엔드 (:3000)
    │  HTTP (REST + SSE)
    ▼
Spring Boot 메인 백엔드 (:8080)
    │  내부 HTTP
    ├──────────────────────────────────┐
    ▼                                  ▼
Python AI 백엔드 (:8001)          H2 파일 DB
    │                              (문서 메타 + 쿼리 로그)
    ├── Ollama (:11434)  임베딩(nomic-embed-text) + LLM(llama3.2:3b)
    └── Qdrant 임베디드  벡터 저장/검색 (backend-ai/data/qdrant)
```

**핵심 원칙**: 프론트엔드는 Spring Boot하고만 통신한다. Python AI 서비스는 Spring Boot가 내부적으로만 호출한다.

실행 방법과 상세 맥락은 `CLAUDE.md`, 코드 흐름은 `docs/code_guide.md` 참고.
