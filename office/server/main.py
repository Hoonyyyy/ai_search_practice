import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import state
from config import settings, OFFICE_DIR
from routers import board, meeting, office


async def _ambient_loop():
    """회의가 없을 때 동료들이 탕비실 등을 오가게 하는 백그라운드 루프."""
    while True:
        await asyncio.sleep(3.5)
        try:
            state.reap_stale_meeting()
            state.ambient_step(time.time())
        except Exception:  # noqa: BLE001 — 루프는 절대 안 죽는다
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_ambient_loop())
    yield
    task.cancel()


app = FastAPI(title="Office", version="0.1.0", lifespan=lifespan)

app.include_router(office.router)
app.include_router(meeting.router)
app.include_router(board.router)


@app.get("/health")
def health():
    # 설정만 확인 (실 API 호출 없음)
    if settings.office_provider.lower() == "ollama":
        ready = True  # 로컬 — 회의 시작 시 실패하면 그때 안내
    else:
        ready = bool(settings.groq_api_key)
    return {
        "status": "ok" if ready else "degraded",
        "provider": settings.office_provider,
    }


app.mount("/", StaticFiles(directory=str(OFFICE_DIR / "web"), html=True), name="web")
