import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool

import meeting
import state

router = APIRouter()


class MeetingReq(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    rounds: int = Field(default=2, ge=1, le=3)


@router.post("/meeting")
async def start_meeting(req: MeetingReq, request: Request):
    state.reap_stale_meeting()  # 새로고침 등으로 남은 유령 회의 청소
    if state.get_state().get("meeting_id"):
        raise HTTPException(409, "이미 진행 중인 회의가 있습니다")

    total_turns = req.rounds * len(meeting.personas.COLLEAGUES)

    async def gen():
        mid = None
        turn = 0
        try:
            async for ev in iterate_in_threadpool(meeting.run_meeting(req.topic, req.rounds)):
                if ev["type"] == "start":
                    mid = ev["meeting_id"]
                    state.set_meeting(mid)
                elif ev["type"] == "turn":
                    turn += 1
                    state.set_progress(f"{turn}/{total_turns}")
                elif ev["type"] == "summary":
                    state.set_progress("정리 중")

                if await request.is_disconnected():
                    if mid:
                        meeting.cancel(mid)
                    break

                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            state.dismiss_all()

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/meeting/{mid}/cancel")
def cancel_meeting(mid: str):
    try:
        meeting.cancel(mid)
    except ValueError:
        raise HTTPException(404, "meeting not found")
    state.dismiss_all()
    return {"cancelled": mid}


@router.get("/meeting/{mid}")
def get_meeting(mid: str):
    try:
        rec = meeting.get_meeting(mid)
    except ValueError:
        raise HTTPException(404, "meeting not found")
    if not rec:
        raise HTTPException(404, "meeting not found")
    return rec
