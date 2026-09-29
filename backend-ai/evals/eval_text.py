"""채점용 문자열 정규화 — run_eval 과 run_answer_eval 이 같이 쓴다.

왜 공용으로 뺐나
---------------
전에는 두 스크립트가 같은 normalize() 를 각자 갖고 있었다. 그러다 보니
"보이지 않는 문자 때문에 정답이 오답으로 집계되는" 같은 결함을 고칠 때
한쪽만 고칠 위험이 있었다. 실제로 이 함수는 두 번 고쳐졌다.

  1차 (v4.10) U+202F NARROW NO-BREAK SPACE
      LLM 이 "50 cm" 의 공백으로 이걸 쓴다. 화면엔 보통 공백처럼 보인다.
      -> NFKC + 공백류를 보통 공백 하나로 접어서 해결

  2차 (2026-09-29) U+2011 NON-BREAKING HYPHEN
      LLM 이 "root-context.xml" 을 "root‑context.xml" 로 쓴다.
      NFKC 는 U+2011 을 U+2010(HYPHEN) 으로 바꿀 뿐 U+002D 로는 안 바꾼다.
      그래서 NFKC 를 통과해도 비교가 실패했다 - 정답인 답변이 오답으로 집계됐다.
      -> 하이픈·대시류를 전부 U+002D 로 접어서 해결

공통점: 사람 눈에는 같아 보이는 문자가 채점을 틀리게 만든다. 지표가 내려가면
모델이나 검색을 의심하게 되는데, 원인이 채점기에 있으면 영영 못 찾는다.
"""
import re
import unicodedata

# 하이픈·대시류. NFKC 로는 U+002D 까지 내려오지 않는 것들이다.
_DASHES = re.compile("[‐‑‒–—―−﹘﹣－]")


def normalize(text: str) -> str:
    """비교용 정규화. 뜻이 같은데 글자가 다른 경우를 없앤다.

    NFKC 로 호환 문자를 펴고, 모든 공백류를 보통 공백 하나로 접고,
    하이픈·대시류를 보통 하이픈으로 접는다.
    """
    folded = unicodedata.normalize("NFKC", text)
    folded = _DASHES.sub("-", folded)
    return re.sub(r"\s+", " ", folded)
