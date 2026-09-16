# 🏢 후니네 팀 — 가상 사무실 (office)

혼자 하는 rag_search 개발을 팀처럼 느끼게 하는 로컬 웹앱.
픽셀 아트 사무실에서 AI 동료 4명(Victoria·Sophia·Michelle·Chloe)과 회의하면,
발언이 말풍선·팀 채팅으로 흐르고 결과가 업무 보드 카드로 쌓인다.

**기존 rag_search 코드와 완전 격리** — 이 `office/` 폴더 + `feature/office` 브랜치만
지우면 흔적 없이 사라진다. 자체 포트(8899), 자체 venv.

## 설치 (최초 1회)

```powershell
cd office
copy .env.example .env        # 그리고 .env 에 GROQ_API_KEY 채우기
python -m venv server\venv
server\venv\Scripts\pip install -r server\requirements.txt
```

## 동료들의 두뇌 (LLM)

`office/.env` 의 `OFFICE_PROVIDER`:

| | 속도 | 비용 | 비고 |
|---|---|---|---|
| `groq` (기본) | 빠름 (발언당 2~5초) | 무료, **일일 토큰 한도** (초과 시 회의 불가, 매일 리셋) | `GROQ_API_KEY` 필요 |
| `ollama` | 느림 (발언당 20~60초, GPU 없을 때) | 무료·무제한·오프라인 | rag_search 와 같은 로컬 Ollama (`qwen2.5:3b`) |

평소엔 `groq`, 한도가 터지면 `.env` 에서 `OFFICE_PROVIDER=ollama` 로 바꾸고 서버 재시작.
동료 회의만 토큰을 쓴다 — 캐릭터 움직임·보드·채팅 UI 는 LLM 과 무관하게 공짜로 돈다.

## 실행

```powershell
.\run.ps1        # → http://127.0.0.1:8899
.\stop.ps1
```

## 쓰는 법

1. 상단 입력창에 회의 주제 입력 (예: "bge-m3 한국어 검색 정확도 올리기")
2. **회의 소집** → 동료들이 회의실로 이동, 순서대로 발언
3. 회의 끝 → 요약 + 액션 아이템 카드가 오른쪽 보드에 생성
4. 카드를 드래그해서 열 이동 (할 일 → 진행 중 → 리뷰 대기 → 완료)
5. `test` / `security` 태그 카드는 자동으로 **후니** 담당 (직접 코딩용)

## 구조

| | |
|---|---|
| `server/` | FastAPI(8899). 정적 파일 서빙 + `/meeting` SSE + `/board` + `/office` |
| `server/personas.py` | 동료 4명 정의 — 닉네임·성격 바꾸려면 여기만 |
| `context/brief.md` | 동료들이 아는 프로젝트 배경 (후니가 관리) |
| `web/` | 바닐라 JS + Canvas. 외부 라이브러리 0개 |
| `data/` | 보드·회의 기록 JSON (gitignore) |

## 로드맵

- **Phase 1 (현재):** 회의·팀채팅·보드. 동료는 코드 조각을 채팅/카드로 제안만.
- Phase 2: 동료가 실제 레포 파일 읽기 (근거 있는 답변) + 멘토 Daniel
- Phase 3: 동료가 폐기용 브랜치에 diff → 후니 승인 시 적용
- Phase 4: 옵트인 자율 커밋 + 테스트

설계·계획 문서: `docs/2026-09-08-design.md`, `docs/2026-09-08-plan.md`
