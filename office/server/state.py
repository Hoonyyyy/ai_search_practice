"""사무실 상태 — 아바타 목표 좌표 + 상태값. JSON 영속."""
import random
import time

from paths import read_json, write_json
from personas import COLLEAGUES

_FILE = "office.json"
_NICKS = [c.nick for c in COLLEAGUES] + ["후니"]

# 격자 좌표 (타일 단위, 28x18 그리드). 웹이 TILE 을 곱해 픽셀로 렌더한다.
DESKS = {
    "Victoria": (3, 4), "Sophia": (3, 9),
    "Michelle": (9, 4), "Chloe": (9, 9), "후니": (13, 6),
}
MEETING_SEATS = {
    "Victoria": (18, 4), "Sophia": (18, 6),
    "Michelle": (24, 4), "Chloe": (24, 6), "후니": (21, 2),
}
STATUSES = {"desk", "thinking", "talking", "meeting", "warn", "break"}

# 회의가 없을 때 잠깐 다녀오는 곳들. 좌표는 web office.js 의 가구 위치와 맞춘다.
POIS = {
    "coffee": (18, 10),       # 커피 머신
    "water": (12, 13),        # 정수기 (라운지)
    "snack": (22, 10),        # 스낵 선반
    "pantry_seat_a": (20, 14),  # 탕비실 원형 식탁
    "pantry_seat_b": (23, 14),
    "bookshelf": (7, 13),     # 책장
    "sofa": (5, 14),          # 소파
}


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
    state["meeting_started"] = time.time() if mid else 0
    state["meeting_progress"] = ""
    _save(state)
    return state


def set_progress(text: str) -> None:
    state = get_state()
    if state.get("meeting_id"):
        state["meeting_progress"] = text
        _save(state)


def reap_stale_meeting(max_age: float = 150.0) -> bool:
    """새로고침 등으로 SSE가 끊겨 meeting_id 가 남아버린 경우를 청소한다."""
    state = get_state()
    mid = state.get("meeting_id")
    if not mid:
        return False
    age = time.time() - state.get("meeting_started", 0)
    stale = age > max_age
    if not stale:
        # 회의 기록이 이미 끝났는데 상태만 남은 경우
        try:
            import meeting as _m
            rec = _m.get_meeting(mid)
            if rec and rec.get("status") not in ("running", "summarized"):
                stale = True
        except Exception:  # noqa: BLE001
            pass
    if stale:
        dismiss_all()
    return stale


def summon_all() -> dict:
    state = get_state()
    for n in _NICKS:
        state["actors"][n]["x"], state["actors"][n]["y"] = MEETING_SEATS[n]
        state["actors"][n]["status"] = "meeting"
    _save(state)
    return state


def dismiss_all() -> dict:
    state = get_state()
    now = time.time()
    for n in _NICKS:
        state["actors"][n]["x"], state["actors"][n]["y"] = DESKS[n]
        state["actors"][n]["status"] = "desk"
        state["actors"][n]["goal"] = "desk"
        state["actors"][n]["until"] = now + random.uniform(8, 20)
    state["meeting_id"] = None
    _save(state)
    return state


def ambient_step(now: float) -> dict:
    """회의가 없을 때 동료 한 명씩 잠깐 탕비실 등에 다녀오게 한다. 주기적으로 호출."""
    state = get_state()
    if state.get("meeting_id"):
        return state
    changed = False
    for n in _NICKS:
        a = state["actors"][n]
        if a["status"] not in ("desk", "break"):
            continue
        if now < a.get("until", 0):
            continue
        if a.get("goal", "desk") == "desk":
            # 대부분 자리에서 일하고, 가끔만 탕비실 등에 다녀온다
            if random.random() < (0.03 if n == "후니" else 0.08):
                poi = random.choice(list(POIS))
                a["x"], a["y"] = POIS[poi]
                a["status"] = "break"
                a["goal"] = poi
                a["until"] = now + random.uniform(4, 8)   # 잠깐 있다가
                changed = True
        else:
            # 볼일 봤으면 반드시 자리로 복귀해 한참 일한다
            a["x"], a["y"] = DESKS[n]
            a["status"] = "desk"
            a["goal"] = "desk"
            a["until"] = now + random.uniform(30, 70)
            changed = True
    if changed:
        _save(state)
    return state
