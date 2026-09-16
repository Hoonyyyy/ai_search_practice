"""동료 발언용 LLM 래퍼. provider = groq(빠름, 한도) | ollama(로컬, 무료, 느림).

backend-ai/services/llm_service.py 의 패턴을 따른다.
"""
import json
from typing import Iterator

import httpx

from config import settings


class GroqError(Exception):
    """provider 무관 LLM 오류. 메시지는 사용자에게 그대로 보여줄 수 있게 쓴다."""


class RateLimited(GroqError):
    pass


def provider() -> str:
    return settings.office_provider.lower()


# ── Groq ────────────────────────────────────────────────────
def _groq_client():
    from groq import Groq

    if not settings.groq_api_key:
        raise GroqError("GROQ_API_KEY 미설정")
    return Groq(api_key=settings.groq_api_key)


def _groq_kwargs(messages: list[dict], **extra) -> dict:
    kw = dict(model=settings.office_model, messages=messages, temperature=0.6, **extra)
    if "gpt-oss" in settings.office_model:
        kw["reasoning_effort"] = "low"
    return kw


def _wrap_groq(e: Exception) -> GroqError:
    msg = str(e)
    if "rate_limit" in msg or "429" in msg or "Rate limit" in msg:
        return RateLimited(
            "Groq 일일 토큰 한도를 다 썼어요. 잠시 뒤 리셋되거나, "
            "office/.env 에 OFFICE_PROVIDER=ollama 로 바꾸면 로컬 모델(느림)로 쓸 수 있어요."
        )
    return GroqError(f"Groq 오류: {msg}")


def _groq_stream(messages: list[dict]) -> Iterator[str]:
    try:
        stream = _groq_client().chat.completions.create(
            stream=True, max_tokens=240, **_groq_kwargs(messages)
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
    except GroqError:
        raise
    except Exception as e:  # noqa: BLE001
        raise _wrap_groq(e) from e


def _groq_json(messages: list[dict]) -> dict:
    try:
        resp = _groq_client().chat.completions.create(
            stream=False, max_tokens=900,
            response_format={"type": "json_object"}, **_groq_kwargs(messages),
        )
        return json.loads(resp.choices[0].message.content)
    except GroqError:
        raise
    except Exception as e:  # noqa: BLE001
        raise _wrap_groq(e) from e


# ── Ollama (로컬) ───────────────────────────────────────────
def _ollama_chat(messages: list[dict], fmt_json: bool = False) -> str:
    body = {
        "model": settings.office_ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.6, "num_predict": 300},
    }
    if fmt_json:
        body["format"] = "json"
    try:
        r = httpx.post(
            f"{settings.ollama_base_url}/api/chat", json=body, timeout=180
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")
    except httpx.HTTPError as e:
        raise GroqError(
            f"Ollama 오류: {e}. Ollama가 켜져 있고 '{settings.office_ollama_model}' 모델이 있는지 확인하세요."
        ) from e


def _ollama_stream(messages: list[dict]) -> Iterator[str]:
    yield _ollama_chat(messages)  # 로컬은 스트리밍 없이 한 번에


def _ollama_json(messages: list[dict]) -> dict:
    raw = _ollama_chat(messages, fmt_json=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise GroqError(f"Ollama JSON 파싱 실패: {e}") from e


# ── 공개 API ────────────────────────────────────────────────
def stream_turn(messages: list[dict]) -> Iterator[str]:
    if provider() == "ollama":
        yield from _ollama_stream(messages)
    else:
        yield from _groq_stream(messages)


def complete_json(messages: list[dict]) -> dict:
    if provider() == "ollama":
        return _ollama_json(messages)
    return _groq_json(messages)


def health() -> bool:
    try:
        if provider() == "ollama":
            httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5).raise_for_status()
        else:
            _groq_client().models.list()
        return True
    except Exception:  # noqa: BLE001
        return False
