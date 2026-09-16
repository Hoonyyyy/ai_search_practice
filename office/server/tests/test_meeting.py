"""meeting.py 테스트 — fake_groq 로 실제 API 없이 검증.

[HOONI] 아래 test_round_robin_order 는 예시다. 나머지를 직접 채워라:
  - 각 turn 후 다음 stream_turn 이 받은 messages 에 이전 발언 텍스트가 들어간다
    (fake.seen_messages 검사)
  - cards 이벤트의 카드마다 title/assignee/tag 존재
  - extract 결과 tag=test 항목 → 카드 assignee == "후니"
  - 발언에 ```python ... ``` 있으면 카드 draft_snippet.lang == "python"
  - fail_at=2 → error 이벤트, get_meeting(mid)["turns"] 길이 2, status == "incomplete"
막히면 물어봐라.
"""
import meeting

_EXTRACT = {
    "summary": "요약",
    "action_items": [
        {"title": "A", "detail": "", "assignee": "Victoria", "tag": "feature", "draft_snippet": None},
    ],
}


def test_round_robin_order(fake_groq):
    fake = fake_groq(turns=["발언"], extract=_EXTRACT)
    events = list(meeting.run_meeting("테스트 주제", rounds=2))

    turns = [e for e in events if e["type"] == "turn"]
    assert [t["speaker"] for t in turns] == [
        "Victoria", "Sophia", "Michelle", "Chloe",
        "Victoria", "Sophia", "Michelle", "Chloe",
    ]
    assert [t["seq"] for t in turns] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "done"
