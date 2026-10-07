"""리랭커: 성공하면 점수 순으로 자르고, 꺼져 있거나 실패하면 None (= 벡터 순서를 쓴다).

실제 Jina 를 부르지 않는다. HTTP 연결(reranker._http)의 post 를 가짜로 바꿔 응답과 실패를 흉내낸다.
"""
import requests

from config import settings
from services import reranker

CHUNKS = [{"content": f"청크 {i}"} for i in range(5)]


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._body


def turn_on(monkeypatch):
    monkeypatch.setattr(settings, "rerank_provider", "jina")
    monkeypatch.setattr(settings, "jina_api_key", "test-key")


def test_off_by_default_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "rerank_provider", "")

    assert reranker.rerank("질문", CHUNKS, 4) is None


def test_reorders_by_api_result_and_cuts_to_top_k(monkeypatch):
    turn_on(monkeypatch)
    # API 는 점수 높은 순으로 index 를 돌려준다: 3번, 0번, 4번 ...
    body = {"results": [{"index": 3, "relevance_score": 0.9},
                        {"index": 0, "relevance_score": 0.7},
                        {"index": 4, "relevance_score": 0.2}]}
    monkeypatch.setattr(reranker._http, "post", lambda *a, **k: FakeResponse(200, body))

    ranked = reranker.rerank("질문", CHUNKS, 2)

    assert [c["content"] for c in ranked] == ["청크 3", "청크 0"]


def test_rate_limited_falls_back(monkeypatch):
    turn_on(monkeypatch)
    monkeypatch.setattr(reranker._http, "post", lambda *a, **k: FakeResponse(429, {}))

    assert reranker.rerank("질문", CHUNKS, 4) is None


def test_timeout_falls_back(monkeypatch):
    turn_on(monkeypatch)

    def slow(*a, **k):
        raise requests.Timeout()

    monkeypatch.setattr(reranker._http, "post", slow)

    assert reranker.rerank("질문", CHUNKS, 4) is None
