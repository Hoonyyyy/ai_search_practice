"""board.py 테스트.

[HOONI] 아래 test_forced_assignee 는 예시다. 스펙 §8 / 계획 Task 9 체크리스트의
나머지 케이스를 직접 채워라:
  - add_card 후 list_cards() 에 나온다
  - patch_card(id, column="done") → 재조회(별도 호출)해도 유지
  - 없는 id patch_card → KeyError, 파일 안 바뀜
  - add_card(tag="bogus") → ValueError
  - 깨진 JSON 이 든 board.json → list_cards() 가 []
막히면 물어봐라.
"""
import board


def test_forced_assignee_for_test_and_security_tags():
    c1 = board.add_card("스트리밍 유닛테스트 추가", tag="test", assignee="Sophia")
    c2 = board.add_card("키 노출 점검", tag="security", assignee="Michelle")
    assert c1["assignee"] == "후니"
    assert c2["assignee"] == "후니"
    # feature 태그는 지정한 담당자 유지
    c3 = board.add_card("보드 UI 개선", tag="feature", assignee="Michelle")
    assert c3["assignee"] == "Michelle"
