from fastapi import APIRouter

import state

router = APIRouter()


@router.get("/office/state")
def office_state():
    return state.get_state()


@router.post("/office/summon")
def summon():
    return state.summon_all()


@router.post("/office/dismiss")
def dismiss():
    return state.dismiss_all()
