r"""검색 품질 평가 — Recall@k.

dataset.json 의 질문을 하나씩 검색해서, 기대한 내용이 상위 k개 안에
들어왔는지 센다. 코드를 바꾸기 전후로 돌려서 숫자를 비교하는 것이 목적이다.

사용법:
    cd backend-ai
    .\venv\Scripts\python.exe evals\run_eval.py
    .\venv\Scripts\python.exe evals\run_eval.py --top-k 8
    .\venv\Scripts\python.exe evals\run_eval.py --mode bm25   # ES 키워드 검색으로
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
ES_URL = "http://localhost:9200"




def search(question: str, top_k: int, owner: str):
    """그 문서의 세션으로만 검색한다 - 운영에서 검색은 문서 하나만 본다."""
    resp = requests.post(
        f"{AI_URL}/ai/search",
        json={"query": question, "top_k": top_k, "owner": owner},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["chunks"]


def search_bm25(question: str, top_k: int, owner: str):
    """같은 질문을 ES 키워드 검색(BM25)으로 찾는다 - 벡터 검색과 비교용.

    owner 는 match 가 아니라 filter + term 이다. keyword 필드라 쪼개지지 않고,
    filter 라 점수에 끼지 않는다. 벡터 쪽 _owner_filter 와 같은 범위를 본다.
    ES 에 청크를 넣는 건 evals/es_load.py.
    """
    resp = requests.post(
        f"{ES_URL}/chunks/_search",
        json={
            "size": top_k,
            "query": {
                "bool": {
                    "must": {"match": {"content": question}},
                    "filter": {"term": {"owner": owner}},
                }
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    return [
        {
            "content": h["_source"]["content"],
            "metadata": {
                "filename": h["_source"]["filename"],
                "doc_id": h["_source"]["doc_id"],
                "chunk_index": h["_source"]["chunk_index"],
            },
        }
        for h in resp.json()["hits"]["hits"]
    ]


RRF_K = 60       # 관례값. 1등과 2등의 점수 차이가 너무 벌어지지 않게 한다
CANDIDATES = 20  # 합치기 전에 각 방식에서 몇 등까지 가져올지


def search_hybrid(question: str, top_k: int, owner: str):
    """벡터와 BM25 결과를 순위로 합친다 (RRF).

    점수를 그대로 더하지 않는다 - 벡터는 0~1, BM25 는 10 을 쉽게 넘어서
    더하면 BM25 가 순위를 다 정해 버린다. 등수는 둘 다 1,2,3... 이라 공평하다.
    각자 top_k 만 가져오면 한쪽 5~20등에 있던 정답이 합칠 기회도 못 얻는다.
    그래서 후보를 넉넉히 받고, 합친 뒤에 top_k 로 자른다.
    """
    vector = search(question, CANDIDATES, owner)
    bm25 = search_bm25(question, CANDIDATES, owner)
    # 한쪽이 0건이면 하이브리드가 아니라 나머지 한쪽 결과가 그대로 나온다.
    # 2026-10-07: 평가 세션이 만료 청소(1시간)로 Qdrant 에서 지워져 벡터가 0건인데,
    # ES 에는 사본이 남아 결과가 BM25 와 똑같이 나왔다. 조용히 넘어가지 않게 멈춘다.
    if not vector or not bm25:
        raise RuntimeError(
            f"한쪽 결과가 비었다 (vector {len(vector)}건, bm25 {len(bm25)}건) - "
            "reload_corpus 후 es_load 를 다시 돌릴 것"
        )
    scores = {}
    chunk_of = {}
    for results in (vector, bm25):
        for rank, chunk in enumerate(results, start=1):
            # 같은 청크인지는 (문서, 몇 번째 청크) 로 알아본다 - 두 저장소에 공통으로 있는 값
            key = (chunk["metadata"]["doc_id"], chunk["metadata"]["chunk_index"])
            scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank)
            chunk_of[key] = chunk
    best = sorted(scores, key=scores.get, reverse=True)[:top_k]
    return [chunk_of[key] for key in best]


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
    parser.add_argument("--mode", choices=["vector", "bm25", "hybrid"], default="vector")
    # dataset.json = 설정(가중치, RRF_K 등)을 바꿔볼 때 쓰는 연습용.
    # dataset_test.json = 설정을 다 정한 뒤 한 번만 돌리는 시험용. 이걸 보면서 설정을 고치면
    # 시험 문제를 보고 답을 맞추는 셈이라, 처음 보는 질문에서의 성능을 알 수 없게 된다.
    parser.add_argument("--dataset", default="dataset.json")
    args = parser.parse_args()
    search_fn = {"vector": search, "bm25": search_bm25, "hybrid": search_hybrid}[args.mode]
    print(f"검색 방식: {args.mode}")

    dataset = json.load(io.open(BASE / args.dataset, encoding="utf-8"))

    hits = 0
    doc_hits = 0
    rr_sum = 0.0
    total_ms = 0.0
    rows = []

    for item in dataset:
        started = time.time()
        chunks = search_fn(item["question"], args.top_k, owner_for(item["doc"]))
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
