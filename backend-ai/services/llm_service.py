"""Groq LLM 스트리밍 서비스."""
import json
from groq import Groq
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
        f"[문서 {i + 1}]\n{c['content']}"
        for i, c in enumerate(chunks)
    ]
    return f"""다음 문서들을 참고하여 질문에 답변해주세요.

=== 참고 문서 ===
{chr(10).join(context_parts)}

=== 질문 ===
{question}"""


def stream_response(question: str, chunks: List[Dict]) -> Generator[str, None, None]:
    """Groq API에서 LLM 응답을 스트리밍하며 SSE 이벤트를 yield한다."""
    client = Groq(api_key=settings.groq_api_key)

    try:
        stream = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(question, chunks)},
            ],
            stream=True,
            temperature=0.3,
            max_tokens=1024,
            top_p=0.9,
        )

        input_tokens = 0
        output_tokens = 0

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"
            # Groq는 마지막 청크의 x_groq.usage에 토큰 정보를 담아 보낸다
            if hasattr(chunk, 'x_groq') and chunk.x_groq:
                usage = chunk.x_groq.usage
                if usage:
                    input_tokens = usage.prompt_tokens
                    output_tokens = usage.completion_tokens

        yield f"data: {json.dumps({'type': 'done', 'input_tokens': input_tokens, 'output_tokens': output_tokens})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': f'Groq API 오류: {str(e)}'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'input_tokens': 0, 'output_tokens': 0})}\n\n"
