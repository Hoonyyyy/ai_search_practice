r"""리랭커 실험 — 후보를 질문과 같이 읽고 다시 채점하면 Recall 이 오르나.

v4.35 에서 벡터 20개 + BM25 20개를 합친 후보 안에 정답이 45문항 모두 있었다.
RRF 는 등수만 보고 4개를 골라 틀렸다. 리랭커(cross-encoder)는 (질문, 청크) 쌍을
직접 읽고 점수를 매긴다 - "비밀번호"와 "암호"가 같은 얘기라는 걸 사전 없이 알아볼 수 있다.

정확도만 보면 안 된다. 리랭커는 후보마다 모델을 한 번씩 돌려서 느리다.
그래서 Recall 과 리랭크 시간을 같이 출력한다.

--provider
  local  : bge-reranker-v2-m3 를 이 PC CPU 로. 2026-10-07 측정 - 후보 약 8개에 질문당 약 14초.
           PyTorch 가 수 GB 라 서비스 venv 와 분리한 rerank-venv 에서만 돈다.
               py -m venv C:\Users\onsyg\rerank-venv
               C:\Users\onsyg\rerank-venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cpu
               C:\Users\onsyg\rerank-venv\Scripts\pip install sentence-transformers requests
  jina   : Jina Reranker API. 키는 환경변수 JINA_API_KEY (채팅이나 코드에 붙이지 않는다)
  cohere : Cohere Rerank API. 키는 환경변수 COHERE_API_KEY
  API 방식은 requests 만 쓰므로 서비스 venv 로 돌려도 된다.

사용법 (FastAPI 8001 + ES 9200 이 켜져 있어야 한다):
    cd backend-ai
    .\venv\Scripts\python.exe evals\rerank_eval.py --provider jina --candidates 5
    .\venv\Scripts\python.exe evals\rerank_eval.py --provider jina --candidates 5 --dataset dataset_test.json
"""
import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

import requests

from eval_session import owner_for
from run_eval import find_rank, search, search_bm25

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).parent
LOCAL_MODEL = "BAAI/bge-reranker-v2-m3"  # 다국어(한국어 포함). 처음 실행 때 약 2GB 내려받는다
JINA_MODEL = "jina-reranker-v2-base-multilingual"
COHERE_MODEL = "rerank-v3.5"


def candidates(question: str, n: int, owner: str):
    """벡터 n개 + BM25 n개를 합친다. 같은 청크는 (문서, 몇 번째 청크) 로 한 번만 남긴다."""
    merged = {}
    for chunk in search(question, n, owner) + search_bm25(question, n, owner):
        key = (chunk["metadata"]["doc_id"], chunk["metadata"]["chunk_index"])
        merged.setdefault(key, chunk)
    return list(merged.values())


def make_scorer(provider: str):
    """(질문, 청크 본문 목록) -> 청크마다 점수 목록. 높을수록 관련이 크다."""
    if provider == "local":
        # 서비스 venv 에는 PyTorch 가 없다 - local 일 때만 불러온다
        from sentence_transformers import CrossEncoder
        print(f"모델 불러오는 중: {LOCAL_MODEL}")
        model = CrossEncoder(LOCAL_MODEL, max_length=512)
        return lambda q, docs: list(model.predict([(q, d) for d in docs]))

    if provider == "jina":
        url, model, key_name = "https://api.jina.ai/v1/rerank", JINA_MODEL, "JINA_API_KEY"
    else:
        url, model, key_name = "https://api.cohere.com/v2/rerank", COHERE_MODEL, "COHERE_API_KEY"
    key = os.environ.get(key_name)
    if not key:
        raise SystemExit(f"환경변수 {key_name} 가 없다. PowerShell 에서 $env:{key_name}=\"...\" 로 넣고 다시 실행")

    def score(q, docs):
        # 무료 키는 분당 사용량 제한이 있다. 2026-10-08 후보 20개로 돌리자 429(Too Many Requests).
        # 평가는 끝까지 돌아야 하므로 잠깐 쉬었다 다시 보낸다. 서비스에 붙일 때는
        # 기다리지 말고 벡터 결과로 대신해야 한다 - 사용자를 수십 초 세워둘 수는 없다.
        for attempt in range(6):
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "query": q, "documents": docs, "top_n": len(docs)},
                timeout=60,
            )
            if resp.status_code != 429:
                break
            wait = int(resp.headers.get("Retry-After", 0)) or 10 * (attempt + 1)
            print(f"      (429 사용량 제한 - {wait}초 쉬고 다시 시도)")
            time.sleep(wait)
            score.waited_ms += wait * 1000  # 리랭크 시간에서 빼려고 따로 센다
        resp.raise_for_status()
        # 응답은 점수 순으로 정렬돼 오고 index 가 원래 위치다 - 원래 순서로 되돌려 둔다
        scores = [0.0] * len(docs)
        for r in resp.json()["results"]:
            scores[r["index"]] = r["relevance_score"]
        return scores

    score.waited_ms = 0.0
    return score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["local", "jina", "cohere"], default="local")
    parser.add_argument("--dataset", default="dataset.json")
    parser.add_argument("--candidates", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    dataset = json.load(io.open(BASE / args.dataset, encoding="utf-8"))
    score = make_scorer(args.provider)
    print(f"리랭커: {args.provider} / 후보: 각 {args.candidates}개 / 질문셋: {args.dataset}")

    hits = 0
    rr_sum = 0.0
    rerank_ms = []
    print(f"\n   결과  순위  후보  리랭크ms  질문")
    print("-" * 78)
    for item in dataset:
        pool = candidates(item["question"], args.candidates, owner_for(item["doc"]))

        started = time.time()
        waited_before = getattr(score, "waited_ms", 0.0)
        scores = score(item["question"], [c["content"] for c in pool])
        took = (time.time() - started) * 1000 - (getattr(score, "waited_ms", 0.0) - waited_before)
        rerank_ms.append(took)

        ranked = [c for _, c in sorted(zip(scores, pool), key=lambda p: p[0], reverse=True)]
        rank = find_rank(ranked[: args.top_k], item["expect"])
        hits += rank is not None
        rr_sum += 1 / rank if rank else 0
        mark = "PASS" if rank else "FAIL"
        print(f"   {mark}  {rank or '-':>4}  {len(pool):>4}  {took:8.0f}  {item['question']}")

    n = len(dataset)
    print("-" * 78)
    print(f"Recall@{args.top_k}       : {hits}/{n}  ({hits / n * 100:.1f}%)")
    print(f"MRR@{args.top_k}          : {rr_sum / n:.3f}")
    print(f"리랭크 평균 시간 : {sum(rerank_ms) / n:.0f}ms  (첫 질문 제외 {sum(rerank_ms[1:]) / max(n - 1, 1):.0f}ms)")
    print("  * 검색(벡터+BM25) 시간은 빠져 있다. 실제 응답 시간 = 검색 + 리랭크")


if __name__ == "__main__":
    main()
