"""회의 퍼실리테이터 — 라운드로빈 발언 + 액션아이템 추출. 이벤트를 yield 한다."""
import json
import re
import time
import uuid
from typing import Iterator

import board
import context
import groq_client
import personas
from config import settings

_MID_RE = re.compile(r"^[0-9a-f]{32}$")

# 진행 중 회의를 중단하려고 표시해 둔 id 들. run_meeting 이 발언 사이에서 확인한다.
_cancelled: set[str] = set()


def cancel(mid: str) -> None:
    if not _MID_RE.match(mid):
        raise ValueError(f"bad meeting id: {mid!r}")
    _cancelled.add(mid)


def _mdir():
    d = settings.data_dir / "meetings"  # data_dir 을 매번 조회 (테스트 격리)
    d.mkdir(exist_ok=True)
    return d


def _mpath(mid: str):
    if not _MID_RE.match(mid):
        raise ValueError(f"bad meeting id: {mid!r}")
    return _mdir() / f"{mid}.json"


def get_meeting(mid: str) -> dict | None:
    p = _mpath(mid)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save(rec: dict) -> None:
    p = _mpath(rec["meeting_id"])
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")


def _retry_stream(messages: list[dict], tries: int = 2) -> str:
    last: Exception | None = None
    for i in range(tries):
        try:
            return "".join(groq_client.stream_turn(messages))
        except groq_client.GroqError as e:
            last = e
            time.sleep(1.0 * (i + 1))
    raise last  # type: ignore[misc]


def _first_code_block(text: str) -> dict | None:
    m = re.search(r"```(\w+)?\n(.*?)```", text, re.S)
    if not m:
        return None
    return {"lang": m.group(1) or "text", "code": m.group(2).strip()}


def run_meeting(topic: str, rounds: int = 2) -> Iterator[dict]:
    rounds = max(1, min(3, int(rounds)))
    topic = (topic or "").strip()[:2000]
    if not topic:
        yield {"type": "error", "message": "주제가 비었습니다"}
        return

    mid = uuid.uuid4().hex
    rec = {
        "meeting_id": mid, "topic": topic, "started_at": time.time(),
        "turns": [], "summary": "", "cards": [], "status": "running",
    }
    _save(rec)
    yield {"type": "start", "meeting_id": mid}

    brief = context.assemble_brief()
    seq = 0
    try:
        for _ in range(rounds):
            for c in personas.COLLEAGUES:
                if mid in _cancelled:
                    _cancelled.discard(mid)
                    rec["status"] = "cancelled"
                    _save(rec)
                    yield {"type": "cancelled", "message": "회의를 중단했습니다"}
                    return
                text = _retry_stream(
                    personas.turn_messages(c, brief, rec["turns"], topic)
                ).strip()
                seq += 1
                turn = {"speaker": c.nick, "text": text, "seq": seq}
                rec["turns"].append(turn)
                _save(rec)
                yield {"type": "turn", **turn}

        data = groq_client.complete_json(
            personas.extract_messages(brief, rec["turns"], topic)
        )
        rec["summary"] = data.get("summary", "")
        yield {"type": "summary", "text": rec["summary"]}

        made: list[dict] = []
        for item in data.get("action_items", []):
            try:
                snippet = item.get("draft_snippet")
                if not snippet:
                    for t in rec["turns"]:
                        snippet = _first_code_block(t["text"])
                        if snippet:
                            break
                made.append(board.add_card(
                    title=str(item["title"])[:200],
                    detail=str(item.get("detail", "")),
                    assignee=item.get("assignee", "후니"),
                    tag=item.get("tag", "feature"),
                    draft_snippet=snippet,
                ))
            except (KeyError, ValueError, TypeError):
                continue
        rec["cards"] = made
        rec["status"] = "done"
        _save(rec)
        yield {"type": "cards", "cards": made}
        yield {"type": "done"}
    except groq_client.GroqError as e:
        rec["status"] = "incomplete"
        _save(rec)
        yield {"type": "error", "message": f"Groq 오류: {e}"}
    finally:
        _cancelled.discard(mid)
