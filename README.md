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
