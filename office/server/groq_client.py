"""Groq 호출 래퍼. backend-ai/services/llm_service.py 의 _stream_groq 패턴을 따른다."""
import json
from typing import Iterator

from config import settings


class GroqError(Exception):
    pass


def _client():
    from groq import Groq

    if not settings.groq_api_key:
        raise GroqError("GROQ_API_KEY 미설정")
    return Groq(api_key=settings.groq_api_key)


def _kwargs(messages: list[dict], **extra) -> dict:
    kw = dict(model=settings.office_model, messages=messages, temperature=0.6, **extra)
    if "gpt-oss" in settings.office_model:
        # gpt-oss 계열은 추론 모델 — 회의 발언엔 과한 추론이 지연만 늘린다.
        kw["reasoning_effort"] = "low"
    return kw


def stream_turn(messages: list[dict]) -> Iterator[str]:
    """한 명의 발언을 텍스트 델타로 스트리밍."""
    try:
        stream = _client().chat.completions.create(
            stream=True, max_tokens=320, **_kwargs(messages)
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
    except GroqError:
        raise
    except Exception as e:  # noqa: BLE001 — SDK 예외를 단일 타입으로 정규화
        raise GroqError(str(e)) from e


def complete_json(messages: list[dict]) -> dict:
    """회의 요약+액션아이템을 JSON object 로 받는다."""
    try:
        resp = _client().chat.completions.create(
            stream=False, max_tokens=900,
            response_format={"type": "json_object"}, **_kwargs(messages),
        )
        return json.loads(resp.choices[0].message.content)
    except GroqError:
        raise
    except Exception as e:  # noqa: BLE001 — JSON 파싱/SDK 예외 정규화
        raise GroqError(str(e)) from e


def health() -> bool:
    try:
        _client().models.list()
        return True
    except Exception:  # noqa: BLE001
        return False
