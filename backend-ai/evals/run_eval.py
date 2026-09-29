r"""검색 품질 평가 — Recall@k.

dataset.json 의 질문을 하나씩 검색해서, 기대한 내용이 상위 k개 안에
들어왔는지 센다. 코드를 바꾸기 전후로 돌려서 숫자를 비교하는 것이 목적이다.

사용법:
    cd backend-ai
    .\venv\Scripts\python.exe evals\run_eval.py
    .\venv\Scripts\python.exe evals\run_eval.py --top-k 8
"""
import argparse
import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

from eval_session import owner_for
from eval_text import normalize

# 출력을 파일이나 파이프로 넘기면 파이썬은 콘솔 코드페이지(윈도우 = cp949)로 쓴다.
# 그런데 LLM 답변에는 U+202F(NARROW NO-BREAK SPACE) 같은 문자가 섞여 있어
# cp949 로 인코딩되지 않고, 채점이 아니라 "출력"에서 평가가 통째로 죽는다.
# 비교는 normalize() 가 이미 처리하므로, 남은 문제는 표준출력뿐이다.
if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE = Path(__file__).parent
AI_URL = "http://127.0.0.1:8001"




def search(question: str, top_k: int, owner: str):
    """그 문서의 세션으로만 검색한다 - 운영에서 검색은 문서 하나만 본다."""
    resp = requests.post(
        f"{AI_URL}/ai/search",
        json={"query": question, "top_k": top_k, "owner": owner},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["chunks"]


def find_rank(chunks, expect: str):
    """기대 문자열이 몇 번째 결과에 들어있는지. 없으면 None."""
    needle = normalize(expect)
    for rank, chunk in enumerate(chunks, start=1):
        if needle in normalize(chunk["content"]):
            return rank
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    dataset = json.load(io.open(BASE / "dataset.json", encoding="utf-8"))

    hits = 0
    doc_hits = 0
    rr_sum = 0.0
    total_ms = 0.0
    rows = []

    for item in dataset:
        started = time.time()
        chunks = search(item["question"], args.top_k, owner_for(item["doc"]))
        took_ms = (time.time() - started) * 1000
        total_ms += took_ms

        rank = find_rank(chunks, item["expect"])
        got_docs = [c["metadata"]["filename"] for c in chunks]
        # 문서가 하나뿐이므로 이건 품질 지표가 아니라 누출 감지기다.
        # 100% 가 아니면 owner 필터가 새고 있다는 뜻이다.
        doc_ok = got_docs != [] and all(d == item["doc"] for d in got_docs)

        hits += rank is not None
        doc_hits += doc_ok

        rr_sum += 1 / rank if rank else 0

        rows.append((item, rank, doc_ok, took_ms, got_docs))

    n = len(dataset)
    k = args.top_k

    print(f"\n{'':2} {'결과':4} {'순위':>4}  {'ms':>6}  질문")
    print("-" * 78)
    for item, rank, doc_ok, took_ms, got_docs in rows:
        mark = "PASS" if rank else "FAIL"
        rank_s = str(rank) if rank else "-"
        print(f"   {mark:4} {rank_s:>4}  {took_ms:6.0f}  {item['question']}")
        if not rank:
            print(f"        기대: {item['expect']!r} / 가져온 문서: {got_docs}")
        elif not doc_ok:
            print(f"        (주의) 기대 문서 {item['doc']} 가 결과에 없음: {got_docs}")

    print("-" * 78)
    print(f"Recall@{k}     : {hits}/{n}  ({hits / n * 100:.1f}%)")
    print(f"MRR@{k}        : {rr_sum / n:.3f}")
    print(f"평균 검색 시간 : {total_ms / n:.0f}ms")

    # 문서가 하나뿐인 세션으로 검색하므로 100% 가 정상이다.
    # 떨어지면 품질 문제가 아니라 owner 필터가 새는 것이다.
    leak = n - doc_hits
    print(f"owner 누출     : {leak}건" + ("  (정상)" if leak == 0 else "  <-- 남의 문서 청크가 섞였다"))

    # 문서마다 청크 수가 크게 다르다(가이드 122 vs 이력서 14). 합쳐 보면 가려진다.
    print(f"\n{'문서':28} {'Recall':>10}  {'MRR':>6}  {'평균ms':>7}")
    print("-" * 78)
    for doc in sorted({item["doc"] for item, *_ in rows}):
        sub = [r for r in rows if r[0]["doc"] == doc]
        sn = len(sub)
        sh = sum(1 for _, rank, *_ in sub if rank)
        srr = sum(1 / rank for _, rank, *_ in sub if rank)
        sms = sum(r[3] for r in sub)
        print(f"{doc[:28]:28} {sh}/{sn} ({sh / sn * 100:5.1f}%)  {srr / sn:6.3f}  {sms / sn:7.0f}")
    print()


if __name__ == "__main__":
    main()
