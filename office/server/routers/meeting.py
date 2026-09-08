import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import meeting
import state

router = APIRouter()


class MeetingReq(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    rounds: int = Field(default=2, ge=1, le=3)


@router.post("/meeting")
def start_meeting(req: MeetingReq):
    if state.get_state().get("meeting_id"):
        raise HTTPException(409, "이미 진행 중인 회의가 있습니다")

    def gen():
        try:
            for ev in meeting.run_meeting(req.topic, req.rounds):
                if ev["type"] == "start":
                    state.set_meeting(ev["meeting_id"])
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            state.dismiss_all()

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/meeting/{mid}")
def get_meeting(mid: str):
    try:
        rec = meeting.get_meeting(mid)
    except ValueError:
        raise HTTPException(404, "meeting not found")
    if not rec:
        raise HTTPException(404, "meeting not found")
    return rec
