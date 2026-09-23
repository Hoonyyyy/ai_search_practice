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
import time
import unicodedata
from pathlib import Path

import requests

from eval_session import EVAL_OWNER

BASE = Path(__file__).parent
AI_URL = "http://127.0.0.1:8001"


def normalize(text: str) -> str:
    """비교용 정규화.

    LLM 과 PDF 는 눈에 안 보이는 공백을 섞어 쓴다. 예를 들어 LLM 은
    "50 cm" 의 공백으로 U+202F(NARROW NO-BREAK SPACE) 를 쓰는데, 화면에는
    보통 공백과 똑같이 보이지만 문자열 비교는 실패한다.
    NFKC 로 호환 문자를 펴고, 모든 공백류를 보통 공백 하나로 접는다.
    """
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text))


def search(question: str, top_k: int):
    resp = requests.post(
        f"{AI_URL}/ai/search",
        json={"query": question, "top_k": top_k, "owner": EVAL_OWNER},
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
        chunks = search(item["question"], args.top_k)
        took_ms = (time.time() - started) * 1000
        total_ms += took_ms

        rank = find_rank(chunks, item["expect"])
        got_docs = [c["metadata"]["filename"] for c in chunks]
        doc_ok = item["doc"] in got_docs

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
    print(f"문서 적중@{k}  : {doc_hits}/{n}  ({doc_hits / n * 100:.1f}%)")

    print(f"MRR@{k}   : {rr_sum / n:.3f}")


    print(f"평균 검색 시간 : {total_ms / n:.0f}ms\n")


if __name__ == "__main__":
    main()
