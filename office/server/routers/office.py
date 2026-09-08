from fastapi import APIRouter

import state

router = APIRouter()


@router.get("/office/state")
def office_state():
    s = state.get_state()
    # 고정 레이아웃 — 책상은 캐릭터 위치와 무관하게 항상 여기 있다
    s["desks"] = {n: list(xy) for n, xy in state.DESKS.items()}
    return s


@router.post("/office/summon")
def summon():
    return state.summon_all()


@router.post("/office/dismiss")
def dismiss():
    return state.dismiss_all()
