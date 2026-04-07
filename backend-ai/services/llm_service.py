"""Ollama LLM 스트리밍 서비스."""
import json
import httpx
from config import settings
from typing import List, Dict, Generator

SYSTEM_PROMPT = """당신은 주어진 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.

규칙:
1. 반드시 제공된 컨텍스트(문서 내용)만을 근거로 답변하세요.
2. 컨텍스트에 없는 내용은 "제공된 문서에서 해당 정보를 찾을 수 없습니다."라고 답하세요.
3. 답변은 한국어로 작성하세요.
4. 출처가 되는 문서 내용을 간략히 인용하며 설명하세요.
5. 명확하고 구조적으로 답변하세요."""


def _build_prompt(question: str, chunks: List[Dict]) -> str:
    context_parts = [
        f"[문서 {i + 1}: {c.get('metadata', {}).get('filename', 'unknown')}]\n{c['content']}"
        for i, c in enumerate(chunks)
    ]
    return f"""다음 문서들을 참고하여 질문에 답변해주세요.

=== 참고 문서 ===
{chr(10).join(context_parts)}

=== 질문 ===
{question}"""


def stream_response(question: str, chunks: List[Dict]) -> Generator[str, None, None]:
    """Ollama에서 LLM 응답을 스트리밍하며 SSE 이벤트를 yield한다."""
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(question, chunks)},
        ],
        "stream": True,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", f"{settings.ollama_base_url}/api/chat", json=payload) as resp:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield f"data: {json.dumps({'type': 'text', 'content': token})}\n\n"
                    if data.get("done"):
                        yield f"data: {json.dumps({'type': 'done', 'input_tokens': data.get('prompt_eval_count', 0), 'output_tokens': data.get('eval_count', 0)})}\n\n"

    except httpx.ConnectError:
        yield f"data: {json.dumps({'type': 'error', 'content': 'Ollama 서버에 연결할 수 없습니다.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'input_tokens': 0, 'output_tokens': 0})}\n\n"
