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

import pytest


def test_forced_assignee_for_test_and_security_tags():
    c1 = board.add_card("스트리밍 유닛테스트 추가", tag="test", assignee="Sophia")
    c2 = board.add_card("키 노출 점검", tag="security", assignee="Michelle")
    assert c1["assignee"] == "후니"
    assert c2["assignee"] == "후니"
    # feature 태그는 지정한 담당자 유지
    c3 = board.add_card("보드 UI 개선", tag="feature", assignee="Michelle")
    assert c3["assignee"] == "Michelle"


def test_add_card_appears_in_list():
    # conftest.py 의 tmp_data fixture 덕분에 매 테스트는 빈 보드로 시작한다.
    assert board.list_cards() == []           # 시작: 카드 0개

    board.add_card("청킹 로직 리팩터", tag="feature", assignee="Victoria")

    cards = board.list_cards()
    assert len(cards) == 1                    # 이제 1개
    assert cards[0]["title"] == "청킹 로직 리팩터"
    assert cards[0]["assignee"] == "Victoria"
    assert cards[0]["column"] == "todo"       # add_card 기본 컬럼

def test_patch_card_persists_after_reload():
  card = board.add_card("제목", tag="feature", assignee="Victoria")

  board.patch_card(card["id"], column="done")

  cards = board.list_cards()    # 다시 불러오기
  assert cards[0]["column"] == "done"


def test_patch_nonexistent_card_raises_keyerror():
  with pytest.raises(KeyError):
    board.patch_card("존재하지-않는-id", column="done")


def test_add_card_with_bogus_tag_raises_valueerror():
  with pytest.raises(ValueError):
    board.add_card("제목", tag="bogus")


def test_list_cards_returns_empty_for_corrupted_json(tmp_path):
  (tmp_path / "board.json").write_text("이건 깨진 JSON {{{", encoding="utf-8")

  assert board.list_cards() == []

