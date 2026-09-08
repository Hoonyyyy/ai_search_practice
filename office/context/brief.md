# 프로젝트 브리핑 — RAG 문서 검색 (ai_search_practice)

## 한 문단 개요

PDF/TXT/MD 문서를 업로드하면 청킹 → 임베딩 → 벡터 DB 저장. 질문하면 관련 청크를
찾아 LLM이 근거 기반 답변을 SSE로 스트리밍한다. 포트폴리오용 개인 프로젝트이며
후니가 혼자 개발 중이다.

## 스택 (v4.0 — 로컬 스택)

| 서비스 | 기술 | 포트 |
|---|---|---|
| Frontend | React + TypeScript + CSS Modules | 3000 |
| Backend (메인) | Spring Boot 3.2 + JPA/H2 (Java 17) | 8080 |
| Backend (AI) | Python FastAPI (routers/services/repositories) | 8001 |
| LLM | Ollama `qwen2.5:3b` 또는 Groq (`LLM_PROVIDER=groq`) | 11434 |
| 임베딩 | Ollama `bge-m3` (1024차원) — 항상 로컬 | 11434 |
| 벡터 DB | Qdrant 임베디드 (로컬 파일 `backend-ai/data/qdrant`) | - |

흐름: React → Spring(:8080, 업로드·청킹·SSE 오케스트레이션) → FastAPI(:8001, 임베딩·벡터검색·LLM 스트림).

## 현재 알려진 이슈 / 최근 작업

- **한국어 검색 품질**: `nomic-embed-text`(768d)는 한국어에서 사실상 무작위였음 →
  기본 임베딩을 `bge-m3`(1024d)로 전환해 랭킹 마진 확보. 여전히 하이브리드(BM25)·
  리랭커·더 나은 다국어 모델이 다음 후보.
- **MS949 인코딩**: 한국어 Windows JVM 기본 `file.encoding=MS949`가 UTF-8 텍스트를
  깨뜨렸음 → `-Dfile.encoding=UTF-8`, 명시적 `StandardCharsets.UTF_8` 로 수정 완료.
  파이썬 쪽도 콘솔 로그는 `PYTHONUTF8=1` 권장.
- **청킹**: 문장 중간에서 잘리던 것 → 줄 단위로 최대 700자까지 패킹하도록 재작성.
- **PDF 추출**: 다단(multi-column) 순서 문제 → `PDFTextStripper.setSortByPosition(true)`.
- **지연**: 이 PC는 GPU가 없어 로컬 LLM이 느림(25~70초) → 데모는 `LLM_PROVIDER=groq`
  (`openai/gpt-oss-120b`, `reasoning_effort=low`). 이력서 PDF 6문항 평균 3.1초.
- **소규모 문서 최적화**: 컬렉션 청크 수가 `full_context_threshold`(12) 이하이면
  벡터 검색을 건너뛰고 전체 청크를 컨텍스트로 넣음 → 데모 검색 누락 제거.
- **H2 ↔ Qdrant 비동기화**: 한쪽 데이터 디렉토리만 지우면 orphan 벡터 발생.
  재조정(reconciliation) 로직 없음 — 미해결.
- **배포판**: Render/Vercel 버전이 깨져 있음 — 원인 미진단.

## 용어

- **청크(chunk)**: 문서를 검색 단위로 자른 조각 (현재 최대 700자, 줄 경계 존중).
- **임베딩(embedding)**: 텍스트를 1024차원 벡터로 변환. `search_document:` /
  `search_query:` 태스크 프리픽스를 붙이면 한국어 검색 순서가 개선됨.
- **top_k**: 질문당 벡터 검색으로 가져오는 청크 수 (기본 4).
- **full_context_threshold**: 이 값 이하 청크 수면 검색 생략하고 전부 컨텍스트로 (기본 12).
- **SSE**: `data: {json}\n\n` 형식으로 토큰·진행률을 스트리밍.

> 이 브리핑은 후니가 관리한다. 사무실 동료들은 이 내용 + 최근 커밋 + 레포 구조만 알고,
> 실제 파일 내용은 보지 않는다(Phase 1).
