"""사무실 상태 — 아바타 목표 좌표 + 상태값. JSON 영속."""
from paths import read_json, write_json
from personas import COLLEAGUES

_FILE = "office.json"
_NICKS = [c.nick for c in COLLEAGUES] + ["후니"]

# 격자 좌표 (타일 단위, 24x16 그리드). 웹이 TILE 을 곱해 픽셀로 렌더한다.
DESKS = {
    "Victoria": (3, 3), "Sophia": (3, 8),
    "Michelle": (8, 3), "Chloe": (8, 8), "후니": (12, 6),
}
MEETING_SEATS = {
    "Victoria": (16, 4), "Sophia": (16, 6),
    "Michelle": (21, 4), "Chloe": (21, 6), "후니": (18, 2),
}
STATUSES = {"desk", "thinking", "talking", "meeting", "warn"}


def _default() -> dict:
    return {
        "actors": {
            n: {"x": DESKS[n][0], "y": DESKS[n][1], "status": "desk"}
            for n in _NICKS
        },
        "meeting_id": None,
    }


def get_state() -> dict:
    state = read_json(_FILE, None)
    if not isinstance(state, dict) or "actors" not in state:
        return _default()
    # 페르소나가 바뀌었을 때를 대비해 누락 배우를 채운다.
    for n in _NICKS:
        state["actors"].setdefault(
            n, {"x": DESKS[n][0], "y": DESKS[n][1], "status": "desk"}
        )
    return state


def _save(state: dict) -> None:
    write_json(_FILE, state)


def set_status(nick: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"bad status: {status}")
    state = get_state()
    state["actors"][nick]["status"] = status
    _save(state)
    return state


def send_to(nick: str, xy: tuple[int, int]) -> dict:
    state = get_state()
    state["actors"][nick]["x"], state["actors"][nick]["y"] = xy
    _save(state)
    return state


def set_meeting(mid: str | None) -> dict:
    state = get_state()
    state["meeting_id"] = mid
    _save(state)
    return state


def summon_all() -> dict:
    state = get_state()
    for n in _NICKS:
        state["actors"][n]["x"], state["actors"][n]["y"] = MEETING_SEATS[n]
        state["actors"][n]["status"] = "meeting"
    _save(state)
    return state


def dismiss_all() -> dict:
    state = get_state()
    for n in _NICKS:
        state["actors"][n]["x"], state["actors"][n]["y"] = DESKS[n]
        state["actors"][n]["status"] = "desk"
    state["meeting_id"] = None
    _save(state)
    return state
