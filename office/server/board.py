"""업무 보드 — 카드 CRUD + 검증 + JSON 영속."""
import time
import uuid

from paths import read_json, write_json
from personas import ASSIGNEES

TAGS = {"test", "security", "feature", "fix", "spike"}
COLUMNS = ("todo", "doing", "review", "done")
_HOONI_TAGS = {"test", "security"}
_FILE = "board.json"


def list_cards() -> list[dict]:
    return read_json(_FILE, [])


def _save(cards: list[dict]) -> None:
    write_json(_FILE, cards)


def _check(assignee: str, tag: str, column: str) -> None:
    if tag not in TAGS:
        raise ValueError(f"bad tag: {tag}")
    if column not in COLUMNS:
        raise ValueError(f"bad column: {column}")
    if assignee not in ASSIGNEES:
        raise ValueError(f"bad assignee: {assignee}")


def add_card(title: str, detail: str = "", assignee: str = "후니",
             tag: str = "feature", draft_snippet: dict | None = None,
             column: str = "todo") -> dict:
    if not title or len(title) > 200:
        raise ValueError("title 은 1~200자")
    if tag in _HOONI_TAGS:
        assignee = "후니"  # 테스트·보안은 후니가 직접 작성
    _check(assignee, tag, column)
    card = {
        "id": uuid.uuid4().hex,
        "title": title,
        "detail": detail[:2000],
        "assignee": assignee,
        "tag": tag,
        "draft_snippet": draft_snippet,
        "column": column,
        "created_at": time.time(),
    }
    cards = list_cards()
    cards.append(card)
    _save(cards)
    return card


def patch_card(card_id: str, *, column: str | None = None,
               assignee: str | None = None, tag: str | None = None) -> dict:
    cards = list_cards()
    for c in cards:
        if c["id"] == card_id:
            if column is not None:
                if column not in COLUMNS:
                    raise ValueError(f"bad column: {column}")
                c["column"] = column
            if assignee is not None:
                if assignee not in ASSIGNEES:
                    raise ValueError(f"bad assignee: {assignee}")
                c["assignee"] = assignee
            if tag is not None:
                if tag not in TAGS:
                    raise ValueError(f"bad tag: {tag}")
                c["tag"] = tag
            _save(cards)
            return c
    raise KeyError(card_id)


def delete_card(card_id: str) -> None:
    cards = list_cards()
    kept = [c for c in cards if c["id"] != card_id]
    if len(kept) == len(cards):
        raise KeyError(card_id)
    _save(kept)
