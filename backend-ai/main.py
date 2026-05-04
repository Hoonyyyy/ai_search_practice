from fastapi import FastAPI
from routers import documents, search, llm

app = FastAPI(title="RAG AI Service", version="1.0.0")

app.include_router(documents.router, prefix="/ai")
app.include_router(search.router, prefix="/ai")
app.include_router(llm.router, prefix="/ai")


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}
