"""LLM 스트리밍 서비스. provider = ollama(로컬) | groq(클라우드)."""
import json
from typing import List, Dict, Generator

import requests

from config import settings

SYSTEM_PROMPT = """당신은 주어진 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.

규칙:
1. 반드시 제공된 컨텍스트(문서 내용)만을 근거로 답변하세요. 추측하거나 지어내지 마세요.
2. 컨텍스트에 근거가 없으면 "제공된 문서에서 해당 정보를 찾을 수 없습니다."라고만 답하세요.
3. 답변은 한국어로, 질문에 필요한 만큼만 간결하게 작성하세요. 불필요한 배경 설명이나 사족은 붙이지 마세요.
4. 목록형 질문은 목록으로, 단답형 질문은 한두 문장으로 답하세요."""


def _build_prompt(question: str, chunks: List[Dict]) -> str:
    context_parts = [
        f"[문서 {i + 1}]\n{c['content']}"
        for i, c in enumerate(chunks)
    ]
    return f"""다음 문서들을 참고하여 질문에 답변해주세요.

=== 참고 문서 ===
{chr(10).join(context_parts)}

=== 질문 ===
{question}"""


def _messages(question: str, chunks: List[Dict]) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_prompt(question, chunks)},
    ]


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _stream_ollama(question: str, chunks: List[Dict]) -> Generator[str, None, None]:
    resp = requests.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": settings.llm_model,
            "messages": _messages(question, chunks),
            "stream": True,
            "keep_alive": settings.ollama_keep_alive,
            "options": {"temperature": 0.2, "top_p": 0.9, "num_predict": 640, "num_ctx": 4096},
        },
        stream=True,
        timeout=300,
    )
    resp.raise_for_status()
    in_tok = out_tok = 0
    for line in resp.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        content = data.get("message", {}).get("content")
        if content:
            yield _sse({"type": "text", "content": content})
        if data.get("done"):
            in_tok = data.get("prompt_eval_count", 0)
            out_tok = data.get("eval_count", 0)
    yield _sse({"type": "done", "input_tokens": in_tok, "output_tokens": out_tok})


def _stream_groq(question: str, chunks: List[Dict]) -> Generator[str, None, None]:
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    kwargs = dict(
        model=settings.groq_model,
        messages=_messages(question, chunks),
        stream=True,
        temperature=0.2,
        max_tokens=640,
        top_p=0.9,
    )
    # gpt-oss 계열은 추론 모델 — RAG 추출형 질문엔 과한 추론이 지연만 늘린다.
    if "gpt-oss" in settings.groq_model:
        kwargs["reasoning_effort"] = "low"
    stream = client.chat.completions.create(**kwargs)
    in_tok = out_tok = 0
    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield _sse({"type": "text", "content": delta.content})
        usage = getattr(chunk, "x_groq", None) and chunk.x_groq.usage
        if usage:
            in_tok = usage.prompt_tokens
            out_tok = usage.completion_tokens
    yield _sse({"type": "done", "input_tokens": in_tok, "output_tokens": out_tok})


def stream_response(question: str, chunks: List[Dict]) -> Generator[str, None, None]:
    """LLM 응답을 스트리밍하며 SSE 이벤트를 yield한다."""
    try:
        if settings.llm_provider == "groq":
            yield from _stream_groq(question, chunks)
        else:
            yield from _stream_ollama(question, chunks)
    except Exception as e:
        yield _sse({"type": "error", "content": f"LLM({settings.llm_provider}) 오류: {e}"})
        yield _sse({"type": "done", "input_tokens": 0, "output_tokens": 0})
