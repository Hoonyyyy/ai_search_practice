# 변경 이력

---

## v4.6 — 잔여 벡터(정합성 깨짐) 예방·감지·회복

### 배경
- `DocumentService.upload()` 은 **벡터를 먼저 저장하고(`embedAndStore`) 문서 메타데이터를 나중에 저장**(`documentRepository.save`)했다.
  그 사이에서 예외가 나거나 프로세스가 죽으면 **Qdrant에는 벡터가 있는데 H2에는 문서가 없는** 상태가 남는다.
- `similarity_search` 는 컬렉션 전체를 대상으로 하므로, 주인 없는 벡터도 검색 결과와 LLM 컨텍스트에 섞여 들어간다.
  청크 수가 `full_context_threshold` 이하면 `scroll` 로 **전부** LLM에 전달되므로 영향이 더 크다.
- 실측: Qdrant `doc_id` 2건 vs H2 문서 0건. 화면 목록은 비어 있는데 검색은 답을 내놓는 상태였다.

### 변경 사항

**예방 — 보상 트랜잭션**
- `DocumentService.upload()` 의 `embedAndStore` 를 `try/catch` 로 감싸고, 실패 시 `cleanupLeftoverVectors(docId)` 로 방금 저장한 벡터를 삭제한 뒤 원래 예외를 그대로 재던진다(`throw e`).
- 정리 자체가 실패해도 원래 예외를 덮지 않도록 헬퍼 내부에서 다시 `try/catch` 하고 로그만 남긴다.

**감지 — 시작 시 정합성 점검**
- `@EventListener(ApplicationReadyEvent.class) checkLeftoversOnStartup()` — 앱이 완전히 뜬 뒤 Qdrant/H2 차집합을 계산해 **경고만** 남긴다. 자동 삭제는 하지 않는다.
- AI 서비스가 아직 안 떠 있어도 스프링 기동을 막지 않도록 전체를 `try/catch` 로 감쌌다.

**회복 — 명시적 정리 API**
- `GET  /api/documents/leftovers` — 삭제 없이 조회만
- `POST /api/documents/cleanup` — 실제 삭제, 삭제 건수 반환
- 삭제는 되돌릴 수 없으므로 **감지와 실행을 분리**했다.

**Backend (AI)**
- `vector_repository.list_doc_ids()` — `scroll` 페이지네이션으로 전체를 훑어 중복 제거된 `doc_id` 목록 반환. `with_vectors=False` 로 1024차원 벡터는 받지 않는다.
- `GET /ai/documents/doc-ids` 라우터 추가 (변수 경로 `/{doc_id}` 보다 위에 배치)

### 검증
- **결함 주입(fault injection)**: `embedAndStore` 직후에 임시로 `RuntimeException` 을 던져 실패 경로를 강제 실행.
  로그에서 `잔여 벡터 정리 완료` → `업로드 처리 실패` 순서를 확인해 **정리 후 원래 예외가 살아서 전파되는 것**까지 증명했다. 확인 후 주입 코드는 제거.
- 실제 잔여 벡터 2건을 감지 → 조회 → 정리 → 재조회(`count: 0`)까지 전 과정 로그로 확인.

### 배운 것
- `h2:file:` 인 것을 먼저 확인했다. `h2:mem:` 이었다면 재시작마다 H2가 비므로 "H2에 없는 벡터를 지운다"는 로직이 **Qdrant를 통째로 삭제**했을 것이다. 삭제 로직은 판단 기준이 되는 데이터가 비어 있을 수 있는지를 먼저 의심해야 한다.
- 실행 중인 JVM은 시작 시점의 클래스를 들고 있다. 소스를 고쳐도 **재시작 전까지 반영되지 않는다**.
- 서비스 간 경로는 문자열이라 컴파일러가 검사해주지 않는다(`/docids` 오타 → 404). 마이크로서비스의 구조적 비용.

---

## v4.5 — 단계별 소요 시간 계측 + 청킹 버그 수정 (backend-spring 첫 테스트)

### 배경
- v4.4 의 요청 로깅으로 "업로드가 느리다"는 건 알았지만 **어느 단계가** 느린지는 몰랐음.
  SSE 때문에 필터가 재는 시간(40~63ms)이 실제 소요 시간(11~17초)과 무관했기 때문
- 감으로 최적화하면 전체의 3% 짜리(PDF 추출)를 붙잡을 위험이 있었음

### 변경 사항
- `DocumentService.upload()` 에 단계별 계측: `extract / split / embed / total`
- `vector_repository.add_chunks_stream()` 에 `embed / upsert` 분리 계측
- `splitText` 를 `static` + 파라미터(`chunkSize`, `chunkOverlap`) 방식으로 변경 —
  필드 의존을 없애 **순수 함수**로 만들어 단위 테스트가 가능해짐
- **버그 수정**: 청크 사이 겹침(overlap)을 이어붙일 때 `chunkSize` 초과 여부를 검사하지 않아,
  긴 줄이 들어오면 청크가 `chunkSize + chunkOverlap + 1` 까지 커졌음
  (700 설정에서 **751자** 관측). 겹침을 붙여도 한도를 넘지 않을 때만 붙이도록 수정 —
  문장을 중간에서 자르는 대신 겹침을 포기하는 쪽을 택함
- `src/test/java/com/ragsearch/service/DocumentServiceSplitTextTest` 신규 —
  **backend-spring 최초의 테스트**. 실행: `cd backend-spring; mvn test`

### 측정 결과 (9청크 PDF 업로드)
```
Java   : extract 135ms, split 6ms, embed 11144ms, total 11285ms
Python : embed 11053ms, upsert 52ms, total 11107ms
```
- **임베딩이 전체의 97.9%.** Qdrant 저장 52ms(0.5%), Spring↔FastAPI 통신 37ms
- `bge-m3` 가 100% CPU 로 도는 환경(GPU 없음)이라 소프트웨어 최적화 여지가 거의 없음 →
  실질적 선택지는 **GPU 데스크탑** 또는 **클라우드 임베딩 API**(배포 시 어차피 필요)
- 벤치마크 교훈: 처음엔 `"가".repeat(500)` 으로 측정했는데 반복 문자는 토큰이 훨씬 적게 나와
  실제보다 빠르게 측정됨. **실제 데이터로 재야 한다**

### 정정 — "청크가 설정값의 2배" 는 코드 버그가 아니라 **측정 오류**였음
조사 중 "Qdrant 에 저장된 청크가 평균 1,362자(최대 1,663자)" 로 관측되어 `splitText` 의
이론적 상한(801자)을 넘는 것처럼 보였으나, **검증 결과 저장된 청크는 최대 699자로 정상**이었다.

원인은 코드가 아니라 조회에 쓴 도구였다. PowerShell 5.1 의 `Invoke-WebRequest` 가 UTF-8
응답을 Latin-1 로 디코딩하면서 **한글 1자(UTF-8 3바이트)가 깨진 글자 3개로 늘어나** 문자열
길이가 ~2.5배로 부풀었다.

```
Java 로그            : 80 chunks, textLen 47611, longest 699
PowerShell 기본 디코딩 : 최대 1663, 평균 1499   ← 부풀려진 값
UTF-8 강제 디코딩      : 최대  699, 평균  670   ← Java 와 일치
```

- 올바른 조회 방법: `[System.Text.Encoding]::UTF8.GetString($resp.RawContentStream.ToArray())`
- **교훈**: "저장된 청크의 최소값(739)이 생성된 청크의 최대값(699)보다 크다"는 논리적으로
  불가능한 값이었다. 이런 값이 나오면 **코드보다 계측을 먼저 의심**해야 한다.
  같은 응답의 파일명이 `ì¬ëì¸_...` 로 깨져 있었던 것이 이미 단서였다
- 이 프로젝트에서 인코딩 문제는 네 번째다 (PowerShell BOM, 자바 로그 CP949,
  `PYTHONUTF8`, 그리고 이번 조회 디코딩) — 한글 프로젝트의 고질적 함정
- 참고: 위의 **겹침(overlap) 버그(751자)는 실재한다.** 그건 PowerShell 이 아니라
  JUnit 테스트로 JVM 안에서 직접 측정해 인코딩 계층이 개입하지 않았다

### 남은 과제
- **고아 벡터**: `embedAndStore`(벡터 저장) 이후 `documentRepository.save`(문서 등록) 전에
  업로드가 끊기면 벡터만 남고 문서 기록이 없어짐. 관측 시점 기준 Qdrant 73청크 vs H2 1문서
  (이 수치는 개수 집계라 인코딩 문제와 무관하며 유효함).
  `similarity_search` 는 컬렉션 전체를 뒤지므로 **삭제된 문서가 답변 근거로 계속 쓰임**

---

## v4.4 — 개발용 요청 로깅 + VS Code 디버그 환경

### 배경
- 계층이 4개(React → Spring → FastAPI → Ollama)인데 **Spring 계층만 요청 로그가 없어서**,
  요청이 어디까지 갔는지 확인할 방법이 없었음. FastAPI 는 uvicorn access log 가 있고,
  React 는 브라우저 Network 탭이 있는데 가운데만 깜깜했음
- SSE 스트리밍 중 브라우저가 "생성중"에서 멈추는 현상을 디버깅할 때, Spring 로그를
  직접 뒤져서야 원인(`IllegalStateException: response object has been recycled`)을 찾을 수 있었음
- 앞으로 검색·임베딩 속도를 개선하려면 **"얼마나 걸리는지" 측정 수단이 먼저** 필요

### 변경 사항
- `config/RequestLoggingFilter` 신규 (`OncePerRequestFilter`):
  `METHOD /path -> status (Xms)` 형태로 모든 요청 로깅. `try/finally` 로 실패한 요청도 남김
- `application.yml` 에 `logging.file.name: logs/spring.log` 추가 — 콘솔 설정
  (integratedTerminal / internalConsole)에 좌우되지 않고 **항상 파일로** 남도록.
  실시간 확인: `Get-Content backend-spring\logs\spring.log -Wait -Tail 5`
- `.vscode/launch.json` 에 "Spring Boot" 자바 디버그 설정 추가.
  `vmArgs` 에 `-Dfile.encoding=UTF-8 -Dsun.jnu.encoding=UTF-8` 필수 (없으면 한글 깨짐)

### 알아낸 것
- **SSE 엔드포인트의 시간은 이 필터로 못 잰다.** `upload()` 가 `SseEmitter` 를 반환하는 순간
  요청이 비동기로 전환되어 원래 스레드가 즉시 반환되므로, 업로드가 `63ms` 로 찍힌다.
  실제 작업(추출→청킹→임베딩)은 그 뒤 `sseExecutor` 스레드에서 진행됨.
  `request.isAsyncStarted()` 로 `[async]` 표시를 붙여 이 숫자를 믿지 않도록 표시함.
  **진짜 소요 시간 측정은 별도 과제** (서비스 내부 측정 또는 `AsyncListener`)
- 로그 메시지는 **ASCII 로** 작성할 것. Java 가 UTF-8 로 쓰는데 Windows 터미널이 CP949 로
  읽으면 한글이 깨진다. 배포 환경(Docker/클라우드 로그 뷰어)까지 고려하면 ASCII 가 안전
- PDF 추출 품질: 디버거로 `DocumentService.extractText()` 결과를 직접 확인한 결과,
  `setSortByPosition(true)` 는 다단 레이아웃 문서(삼성 노트북 설명서, 47,611자)에서
  **단을 가로질러 읽어 문장을 쪼갠다** ("데이터를 백업해" + 다른 단 내용 + "두세요.").
  `false` 로 두면 순서가 보존됨. 다만 주석에 적힌 "이력서·양식 문서엔 `true` 가 낫다"는
  주장은 아직 검증 전이라 `true` 유지 — **이력서 PDF 로 같은 실험을 하는 것이 남은 과제**

---

## v4.3 — 새 PC 환경 세팅 자동화

### 배경
- 노트북 외에 GPU(GTX 1660 Super) 있는 데스크탑에서도 동일하게 작업하고 싶은데,
  Ollama 모델 재설치·venv·npm install·.env 를 손으로 하면 오래 걸리고 누락되기 쉬움
- `CLAUDE.md`/`start_search.ps1`의 "사전 준비" 안내가 예전 모델명(`llama3.2:3b`,
  `nomic-embed-text`)을 그대로 가리키고 있어 실제 기본값(`qwen2.5:3b`, `bge-m3`)과 어긋나 있었음

### 변경 사항
- `setup.ps1` 신규: python/node/mvn/java/ollama PATH 확인 → Ollama 모델
  (`bge-m3`, `qwen2.5:3b`) pull → `backend-ai\venv` + requirements 설치 →
  `frontend\node_modules` 설치 → `backend-ai\.env` 생성까지 한 번에. 이미 되어있는
  항목은 스킵하므로 재실행해도 안전
- `CLAUDE.md`, `start_search.ps1`의 사전 준비 안내를 `setup.ps1` 실행 + 현재 모델명으로 수정

---

## v4.2 — 회귀 테스트 인프라 구축 (진행 중)

### 배경
- v4.0~v4.1의 RAG 품질 수정들이 회귀 테스트 없이 이루어져, 앞으로 리팩토링하다가
  같은 버그가 재발해도 잡을 안전망이 없었음
- 후니가 테스트 작성을 직접 익히고 싶어함 — 체크리스트만 주는 방식은 안 통해서
  작은 실행 가능한 토이 예제로 monkeypatch 등 개념을 먼저 보여주는 방식으로 진행

### 변경 사항
- `pytest` 설치 및 `requirements.txt` 반영
- `backend-ai/tests/` 신설, 5단계 난이도별 테스트 사다리로 진행:
  1. `test_config.py` — `settings.embed_model/embed_dim/full_context_threshold` 기본값 회귀 (완료)
  2. `test_pure_functions.py` — `llm_service._build_prompt`/`._messages`,
     `vector_repository._to_dict` 순수 함수 (완료)
  3. `vector_repository._embed` prefix 로직, `requests.post` monkeypatch (진행 중)
  4. `similarity_search` threshold 분기, fake Qdrant client (예정)
  5. `stream_response` 에러 경로 (예정)
- 실행: `./venv/Scripts/python.exe -m pytest tests/ -v` (bare `pytest`는 `backend-ai`가
  `sys.path`에 없어 `from config import settings` 실패)

**함께 수정 (별개 이슈):** `start_search.ps1`/`stop_search.ps1`/`office/run.ps1`/`office/stop.ps1`에
UTF-8 BOM 누락 — Windows PowerShell 5.1이 한글을 MS949로 읽어 문자열 종료가 깨지면서
스크립트가 실행되지 않던 문제, BOM 추가로 수정.

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
