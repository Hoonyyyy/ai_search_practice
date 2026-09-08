from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings, OFFICE_DIR

app = FastAPI(title="Office", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok" if settings.groq_api_key else "degraded",
        "has_key": bool(settings.groq_api_key),
    }


app.mount("/", StaticFiles(directory=str(OFFICE_DIR / "web"), html=True), name="web")
