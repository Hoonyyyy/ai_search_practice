"""검색 후보를 다시 채점해 순서를 고친다 (리랭커).

벡터 검색은 질문과 청크를 따로 좌표로 바꿔 거리만 본다. 리랭커는 (질문, 청크) 쌍을
같이 읽고 점수를 매긴다. 평가(v4.36): 벡터 20개 → 리랭커 → 4개로 45문항 중 39 → 42.

실패해도 검색은 멈추면 안 된다. 무료 키는 분당 사용량 제한(429)이 있고 토큰이 떨어지면
거절된다. 그럴 때 기다리지 않고 None 을 돌려주면, 호출한 쪽이 벡터 순서를 그대로 쓴다.
"""
import time
from typing import Any, Dict, List, Optional

import requests

from config import settings

JINA_URL = "https://api.jina.ai/v1/rerank"


def enabled() -> bool:
    return settings.rerank_provider == "jina" and bool(settings.jina_api_key)


def rerank(query: str, chunks: List[Dict[str, Any]], top_k: int) -> Optional[List[Dict[str, Any]]]:
    """점수 순으로 top_k 개를 돌려준다. 꺼져 있거나 실패하면 None (= 벡터 순서를 쓸 것)."""
    if not enabled() or not chunks:
        return None

    started = time.time()
    try:
        resp = requests.post(
            JINA_URL,
            headers={"Authorization": f"Bearer {settings.jina_api_key}"},
            json={
                "model": settings.rerank_model,
                "query": query,
                "documents": [c["content"] for c in chunks],
                "top_n": top_k,
            },
            # 사용자를 세워두는 시간의 상한. 넘으면 리랭크 없이 진행한다.
            timeout=settings.rerank_timeout_s,
        )
        resp.raise_for_status()
        results = resp.json()["results"]
    except (requests.RequestException, KeyError, ValueError) as e:
        # 키 값이 섞이지 않게 예외 종류와 상태 코드만 남긴다
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"[rerank] 실패 → 벡터 순서 사용 ({type(e).__name__}, status={status}, "
              f"{(time.time() - started) * 1000:.0f}ms)", flush=True)
        return None

    # 응답은 점수 높은 순, index 는 보낸 목록에서의 위치
    ranked = [chunks[r["index"]] for r in results[:top_k]]
    print(f"[rerank] {len(chunks)}개 → {len(ranked)}개, {(time.time() - started) * 1000:.0f}ms", flush=True)
    return ranked
