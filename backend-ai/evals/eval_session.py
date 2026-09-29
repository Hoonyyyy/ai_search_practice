"""평가 하네스가 쓰는 세션 id — 문서마다 하나씩.

익명 세션이 생기면서 업로드와 검색이 모두 소유자를 요구한다.
코퍼스를 올리는 쪽(reload_corpus)과 검색하는 쪽(run_eval, run_answer_eval)이
반드시 같은 값을 써야 한다 - 다르면 검색이 0건이 되고, Recall도 정확도도
전부 0 으로 나온다. 코드는 멀쩡한데 지표만 무너지는, 제일 찾기 어려운 실패다.
그래서 값을 한 곳에만 적는다.

왜 문서마다 따로인가 (2026-09-29 변경)
-------------------------------------
전에는 문서 2개를 한 세션에 올려두고 검색이 둘 다 보게 했다. 그런데 운영은
세션당 문서 1개이고(document.max-per-session), 검색 범위도
DocumentService.resolveSearchOwner 가 "내 문서 아니면 예시 문서" 중 하나로 정한다.
즉 운영에서 검색이 두 문서에 걸치는 일은 없다.

한 세션에 몰아 올리면 평가는 제품에 없는 상황을 재게 된다.
  - 남의 문서 청크와 경쟁하므로 Recall 이 실제보다 비관적으로 나온다
  - "문서 적중률" 이 품질 지표처럼 보이지만, 문서가 하나면 항상 100% 다
    (그래서 이제는 품질 지표가 아니라 owner 필터 누출 감지기로 읽는다)
그래서 문서마다 세션을 따로 두고, 질문은 자기 문서만 검색한다.
"""

# dataset 의 doc 값 -> 그 문서를 담을 세션 id.
# 새 문서를 평가셋에 넣으면 여기에도 한 줄 추가해야 한다.
OWNERS = {
    "Galaxybook_guide.pdf": "eval-guide",
    "사람인_이력서_강현수.pdf": "eval-resume",
}


def owner_for(doc: str) -> str:
    """문서 이름으로 세션 id 를 찾는다. 오타를 조용히 넘기지 않는다.

    여기서 KeyError 를 내지 않고 기본값을 주면, 검색이 0건이 되고
    지표만 0 으로 떨어져 원인을 찾기 어려워진다. 그래서 크게 실패한다.
    """
    try:
        return OWNERS[doc]
    except KeyError:
        raise KeyError(
            f"평가셋의 doc '{doc}' 에 해당하는 세션 id 가 없다. "
            f"eval_session.OWNERS 에 추가할 것. 현재 등록: {sorted(OWNERS)}"
        ) from None
