"""동료 4명 정의 + 회의 프롬프트 빌더. 닉네임/직급/역할은 이 파일에서만 바꾼다."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Colleague:
    nick: str
    rank: str
    role: str
    system: str


_RULES = (
    "회의 규칙: (1) 2~3문장으로 짧게. 장황하게 쓰지 말 것. "
    "(2) 자기 역할 관점에서만. (3) 팀장 '후니'에게 존대. "
    "(4) 당신은 실제 코드베이스를 보지 못한다. 그러니 완성된 코드를 쓰지 말고, "
    "'무엇을·어디를·왜' 바꿔야 하는지 방향과 고려사항, 확인할 점을 말하라. "
    "정말 필요하면 3~5줄짜리 의사코드(pseudocode)만 허용. "
    "(5) 이미 나온 말 반복 금지. 구체적인 다음 행동 하나를 제시."
)

COLLEAGUES = [
    Colleague(
        "Victoria", "과장",
        "Spring 백엔드(:8080, 청킹, SSE 오케스트레이션)",
        "당신은 Victoria 과장. 침착하고 원칙주의. 인코딩·트랜잭션·경계값·예외 처리에 깐깐하다. " + _RULES,
    ),
    Colleague(
        "Sophia", "대리",
        "Python AI 서비스(:8001, 임베딩·벡터검색·LLM), RAG 검색 품질",
        "당신은 Sophia 대리. 실험적이고 수치로 말한다. '일단 벤치 돌려보죠'가 입버릇. " + _RULES,
    ),
    Colleague(
        "Michelle", "사원",
        "React 프론트(CRA, SSE 소비, UI)",
        "당신은 Michelle 사원. 밝고 빠르다. 사용자 경험과 엣지 UX를 챙긴다. " + _RULES,
    ),
    Colleague(
        "Chloe", "인턴",
        "QA·인프라(테스트, 배포, 재현 케이스)",
        "당신은 Chloe 인턴. 질문이 많고 꼼꼼하다. '이 케이스 재현돼요?'를 자주 묻는다. " + _RULES,
    ),
]

ASSIGNEES = {c.nick for c in COLLEAGUES} | {"후니"}


def by_nick(nick: str) -> Colleague | None:
    return next((c for c in COLLEAGUES if c.nick == nick), None)


def _transcript_text(transcript: list[dict], limit: int = 6) -> str:
    recent = transcript[-limit:]  # 토큰 절약: 최근 발언만
    return "\n".join(f"{t['speaker']}: {t['text']}" for t in recent) or "(아직 발언 없음)"


def turn_messages(c: Colleague, brief: str, transcript: list[dict], topic: str) -> list[dict]:
    return [
        {"role": "system", "content": c.system},
        {"role": "user", "content": (
            f"# 프로젝트 브리핑\n{brief}\n\n"
            f"# 회의 주제 (팀장 후니)\n{topic}\n\n"
            f"# 지금까지 대화\n{_transcript_text(transcript)}\n\n"
            f"이제 {c.nick} {c.rank} 차례입니다. 발언하세요."
        )},
    ]


def extract_messages(brief: str, transcript: list[dict], topic: str) -> list[dict]:
    return [
        {"role": "system", "content": (
            "회의록에서 실행 항목을 뽑아 JSON만 출력한다. 형식: "
            '{"summary": str, "action_items": [{"title": str, "detail": str, '
            '"assignee": "Victoria|Sophia|Michelle|Chloe|후니", '
            '"tag": "test|security|feature|fix|spike", '
            '"draft_snippet": {"lang": str, "code": str} | null}]}. '
            "summary 와 각 title·detail 은 반드시 한국어로 쓴다. "
            "action_items 의 각 원소는 반드시 위 형식의 객체다(문자열 금지). "
            "detail 은 '무엇을 왜 어떻게(방향)' + '구현 전 확인할 점'을 담는다. "
            "draft_snippet 은 회의에서 나온 짧은 의사코드가 있을 때만 채우고, 없으면 null. "
            "테스트·보안 항목의 assignee 는 반드시 후니."
        )},
        {"role": "user", "content": f"# 주제\n{topic}\n\n# 회의록\n{_transcript_text(transcript, limit=99)}"},
    ]
