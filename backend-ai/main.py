from fastapi import FastAPI
from routers import documents, search, llm
from services.embedder import preload

app = FastAPI(title="RAG AI Service", version="1.0.0")

# Spring Boot가 내부적으로만 호출 - CORS 불필요
app.include_router(documents.router, prefix="/ai")
app.include_router(search.router, prefix="/ai")
app.include_router(llm.router, prefix="/ai")


@app.on_event("startup")
def startup():
    preload()


@app.get("/health")
def health():
    return {"status": "ok"}
