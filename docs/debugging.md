# 디버깅 가이드

이 프로젝트는 **4개 계층이 체인**으로 엮여 있다:

```
React(3000) → Spring(8080) → FastAPI(8001) → Ollama(11434)
                  │                              Qdrant(임베디드 파일)
                  └ H2 파일 DB
```

디버깅의 90%는 **"어느 계층에서 깨졌는지 좁히는 것"**이다. 위에서부터 하나씩 격리해서 찌른다.

---

## 1. 계층별 격리 테스트 (제일 빠름, IDE 불필요)

### `api.http` 파일 사용
루트의 `api.http` 를 열면 각 요청을 클릭 한 번으로 실행할 수 있다.
- **IntelliJ**: 내장 HTTP Client — 그냥 파일 열면 ▶ 버튼이 생김
- **VS Code**: "REST Client" 확장 설치 → 요청 위 "Send Request"

순서대로 실행하면서 **처음 실패하는 계층**을 찾는다:

| 실행 | 실패하면 원인 |
|---|---|
| `1) Ollama` | Ollama 안 켜짐 / 모델 안 받음 (`ollama list` 확인) |
| `2) FastAPI` | Python 서비스 코드 / Qdrant / 임베딩 로직 |
| `3) Spring` | Spring 로직 / Spring↔FastAPI 통신 / 인코딩 |
| React (브라우저) | 프론트 SSE 파싱 / CORS |

### FastAPI Swagger UI
브라우저로 **http://localhost:8001/docs** → 모든 AI 엔드포인트를 폼으로 테스트. Spring 을 건너뛰고 AI 계층만 볼 때 최고.

---

## 2. RAG 품질 디버깅 (답변이 이상할 때)

답변이 틀리거나 환각이면 **거의 항상 아래 둘 중 하나**다:

### (a) 검색이 엉뚱한 청크를 가져옴
`api.http` 의 `2-3. 벡터 검색` 을 실행해서 **distance 와 content** 를 직접 본다.
- 질문과 상관없는 청크가 위에 오면 → 임베딩 모델 / 청킹 문제
- 정답 내용이 애초에 어느 청크에도 없으면 → PDF 추출 / 청킹 문제 (`3-2` 업로드 응답의 chunk 내용 확인)

### (b) LLM 이 받은 컨텍스트가 깨졌거나 부족함
`backend-ai/services/llm_service.py` 의 `_build_prompt` 결과를 로그로 찍어본다:

```python
def stream_response(question, chunks):
    prompt = _build_prompt(question, chunks)
    print("=== LLM PROMPT ===\n", prompt, "\n==================")  # 임시
    ...
```

그리고 `logs/backend-ai.*.log` (또는 uvicorn 콘솔)에서 확인.
- 한글이 `�` 로 깨져 있으면 → 인코딩 (Spring `file.encoding`, 이미 수정했지만 재발 시 여기 확인)
- 프롬프트에 정답이 들어있는데 답이 틀리면 → LLM 모델이 약함 (`LLM_MODEL` / `GROQ_MODEL` 교체)

---

## 3. IDE 디버거 붙이기

### Spring (IntelliJ) — 권장

1. `backend-spring/` 를 **별도 프로젝트로** 열기 (루트 말고)
2. `RagSearchApplication` 클래스 → 왼쪽 ▶ 옆 초록 벌레 아이콘으로 **Debug**
3. Run/Debug Configuration 에서 **VM options** 에 반드시 추가:
   ```
   -Dfile.encoding=UTF-8 -Dsun.jnu.encoding=UTF-8
   ```
   (pom 의 `jvmArguments` 는 `mvn spring-boot:run` 에만 적용됨. IntelliJ 직접 실행엔 안 먹음 → 안 넣으면 한글 깨짐)
4. 브레이크포인트 추천 위치:
   - `SearchService.query()` — 검색 전체 흐름
   - `AiServiceClient.searchVectors()` / `streamLlm()` — FastAPI 응답 확인
   - `DocumentService.splitText()` — 청킹 결과 (`chunks` 리스트를 Evaluate)
   - `DocumentService.extractText()` — PDF 추출 텍스트

> `mvn spring-boot:run` 이 이미 8080 을 물고 있으면 디버그 실행이 포트 충돌. `.\stop_search.ps1` 로 먼저 종료.

### FastAPI (VS Code) — 권장

1. VS Code 로 `backend-ai/` 폴더 열기
2. Python 인터프리터 선택: `Ctrl+Shift+P` → "Python: Select Interpreter" → `.\venv\Scripts\python.exe`
3. `.vscode/launch.json` 이 이미 있음 (아래) → F5 로 "FastAPI (uvicorn)" 실행
4. 브레이크포인트 추천:
   - `repositories/vector_repository.py` → `similarity_search`, `_embed`
   - `services/llm_service.py` → `stream_response`, `_build_prompt`

### React (VS Code 또는 브라우저)

- 간단히: 브라우저 **F12 → Network 탭** → `query` 요청 클릭 → "EventStream"/"Response" 에서 SSE 원본 확인. `meta` → `text`(여러 개) → `done` 순으로 와야 정상.
- 소스 디버깅: F12 → Sources → `webpack://` 아래 `src/` 에서 브레이크포인트. 또는 VS Code "Debugger for Chrome".
- 볼 파일: `src/api/search.ts` (SSE 파싱), `src/hooks/useSearch.ts` (상태)

---

## 4. 데이터 계층 직접 들여다보기

### H2 (문서 메타 + 쿼리 로그)
Spring 실행 중 → 브라우저로 **http://localhost:8080/h2-console**
- JDBC URL: `jdbc:h2:file:./data/ragsearch` (`backend-spring/` 기준 상대경로)
- User: `sa`, Password: 비움
- `SELECT * FROM QUERY_LOG ORDER BY TIMESTAMP DESC;` 로 실제 저장된 질문/답변/토큰/응답시간 확인

### Qdrant (벡터)
**임베디드 모드는 한 프로세스만 열 수 있다.** FastAPI 가 떠 있으면 별도 스크립트로 못 연다.
방법 A — FastAPI 끄고 조회:
```powershell
# stop_search.ps1 로 FastAPI 종료 후
cd backend-ai
.\venv\Scripts\python.exe -c "from qdrant_client import QdrantClient; c=QdrantClient(path='data/qdrant'); print(c.count('documents')); pts,_=c.scroll('documents', limit=100, with_payload=True); [print(p.payload['chunk_index'], p.payload['content'][:60]) for p in pts]"
```
방법 B — FastAPI 켠 채로 보려면 `api.http` 의 `2-3` 검색으로 우회.

### Ollama
- 로드된 모델: `ollama ps`
- 서버 로그 (GPU/CPU 판정 등): `%LOCALAPPDATA%\Ollama\server.log`

---

## 5. 로그 위치

| 서비스 | 위치 |
|---|---|
| FastAPI | `logs/backend-ai.*.log` 또는 uvicorn 실행 콘솔 |
| Spring | `logs/spring.*.log` / `logs/backend-spring.log`. 레벨은 `application.yml` 의 `logging.level.com.ragsearch: DEBUG` |
| React | `logs/frontend.*.log` / 브라우저 콘솔 |
| Ollama | `%LOCALAPPDATA%\Ollama\server.log` |

---

## 6. 흔한 증상 → 확인 순서

| 증상 | 확인 |
|---|---|
| 한글 `�` 깨짐 | Spring VM options 에 `-Dfile.encoding=UTF-8` 있는지 (IntelliJ 직접 실행 시) |
| 답변이 "찾을 수 없습니다"만 나옴 | `api.http` 2-3 으로 검색 결과 확인 → 청크가 0개면 업로드 실패, 있는데 엉뚱하면 임베딩 |
| 답변이 느림 (20초+) | `ollama ps` 로 CPU/GPU 확인. GPU 없으면 `LLM_PROVIDER=groq` (`.env`) |
| 업로드가 안 끝남 | `logs/backend-ai` 에서 Ollama 임베딩 호출 에러 / 타임아웃 |
| Spring 이 502/타임아웃 | FastAPI(8001) 살아있는지 `GET /health` |
| CORS 에러 (브라우저) | `application.yml` 의 `cors.allowed-origins` 에 `localhost:3000` 있는지 |
| 검색은 되는데 대시보드가 빔 | H2 console 에서 `QUERY_LOG` 테이블 확인 |

---

## 7. 테스트 코드

현재 자동화 테스트가 없다. 추가한다면 우선순위:
1. `DocumentService.splitText()` 단위 테스트 (청킹 경계 — 순수 함수라 테스트하기 쉬움)
2. `vector_repository` — in-memory Qdrant(`QdrantClient(":memory:")`) + Ollama mock 으로 검색 로직
3. Spring `@WebMvcTest` 로 컨트롤러 계약 (`AiServiceClient` 는 mock)
