"""테스트 하네스. 실제 Groq API 는 호출하지 않는다 — FakeGroq 를 주입한다."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    """모든 테스트가 임시 data 디렉토리를 쓰도록 강제 (board.json / office.json / meetings 격리)."""
    import config
    # data_dir 은 property 이므로 클래스에 patch 해야 한다. paths.py 가 매 호출 조회하므로 동작.
    monkeypatch.setattr(
        type(config.settings), "data_dir",
        property(lambda self: tmp_path), raising=False,
    )
    yield


class FakeGroq:
    """정해진 발언 시퀀스를 반환. fail_at 인덱스에서 GroqError 를 던진다.

    - turns: stream_turn 호출마다 순서대로 반환할 텍스트 리스트 (부족하면 wrap)
    - extract: complete_json 이 반환할 dict
    - fail_at: 이 인덱스(0-base)의 stream_turn 호출에서 예외
    """

    def __init__(self, turns, extract, fail_at=None):
        self.turns = turns
        self.extract = extract
        self.fail_at = fail_at
        self.calls = 0
        self.seen_messages = []  # 각 stream_turn 이 받은 messages 를 기록

    def stream_turn(self, messages):
        i = self.calls
        self.calls += 1
        self.seen_messages.append(messages)
        if self.fail_at is not None and i == self.fail_at:
            from groq_client import GroqError
            raise GroqError("fake failure")
        yield self.turns[i % len(self.turns)]

    def complete_json(self, messages):
        return self.extract


@pytest.fixture
def fake_groq(monkeypatch):
    """fake_groq(turns, extract, fail_at=None) -> FakeGroq. groq_client 함수를 교체한다."""
    def _install(turns, extract, fail_at=None):
        import groq_client
        fake = FakeGroq(turns, extract, fail_at)
        monkeypatch.setattr(groq_client, "stream_turn", fake.stream_turn)
        monkeypatch.setattr(groq_client, "complete_json", fake.complete_json)
        return fake
    return _install
