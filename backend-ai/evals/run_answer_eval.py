r"""답변 단계 평가 - 검색이 아니라 LLM 이 내놓은 최종 답변을 채점한다.

run_eval.py 는 "정답 청크를 가져왔는가"까지만 본다. 그런데 청크를 제대로
가져와도 LLM 이 못 읽거나, 엉뚱한 조각을 갖다 붙이는 일이 있다. 여기서는
그 마지막 단계를 본다.

두 가지 실패를 따로 센다.

  과잉 거절 - 문서에 답이 있는데 "찾을 수 없습니다"라고 한다
  환 각     - 문서에 답이 없는데 그럴듯한 답을 만들어낸다

둘은 반대 방향이라 한쪽만 보고 조이면 다른 쪽이 나빠진다. 그래서 같이 잰다.

사용법:
    cd backend-ai
    .\venv\Scripts\python.exe evals\run_answer_eval.py
    .\venv\Scripts\python.exe evals\run_answer_eval.py --limit 5
"""
import argparse
import io
import json
import re
import time
import unicodedata
from pathlib import Path

import requests

BASE = Path(__file__).parent
AI_URL = "http://127.0.0.1:8001"
REFUSAL = "찾을 수 없습니다"
TOP_K = 4


def normalize(text: str) -> str:
    """비교용 정규화.

    LLM 과 PDF 는 눈에 안 보이는 공백을 섞어 쓴다. 예를 들어 LLM 은
    "50 cm" 의 공백으로 U+202F(NARROW NO-BREAK SPACE) 를 쓰는데, 화면에는
    보통 공백과 똑같이 보이지만 문자열 비교는 실패한다.
    NFKC 로 호환 문자를 펴고, 모든 공백류를 보통 공백 하나로 접는다.
    """
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text))


def answer(question: str, top_k: int):
    """검색 -> LLM 스트리밍. 실제 서비스와 같은 경로를 탄다."""
    chunks = requests.post(
        f"{AI_URL}/ai/search",
        json={"query": question, "top_k": top_k},
        timeout=180,
    ).json()["chunks"]

    started = time.time()
    resp = requests.post(
        f"{AI_URL}/ai/llm/stream",
        json={"question": question, "chunks": chunks, "query_id": "answer-eval"},
        stream=True,
        timeout=900,
    )
    resp.raise_for_status()

    parts = []
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            event = json.loads(line[6:])
            if event.get("type") == "text":
                parts.append(event["content"])
    return "".join(parts).strip(), time.time() - started


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="답 있는 질문 개수 제한 (0=전부)")
    parser.add_argument("--top-k", type=int, default=TOP_K, help="LLM 에 넘길 청크 수")
    args = parser.parse_args()

    answerable = json.load(io.open(BASE / "dataset.json", encoding="utf-8"))
    negative = json.load(io.open(BASE / "dataset_negative.json", encoding="utf-8"))
    if args.limit:
        answerable = answerable[: args.limit]

    correct = refused_wrongly = 0
    print("\n-- 답이 있는 질문 --")
    for item in answerable:
        text, sec = answer(item["question"], args.top_k)
        norm = normalize(text)
        refused = normalize(REFUSAL) in norm
        hit = normalize(item["expect"]) in norm
        correct += hit
        refused_wrongly += refused
        mark = "OK  " if hit else ("거절" if refused else "오답")
        print(f"  {mark} ({sec:5.1f}s) {item['question']}")
        if not hit:
            print(f"        기대 {item['expect']!r} / 답변: {text[:150]}")

    hallucinated = 0
    print("\n-- 답이 없는 질문 --")
    for item in negative:
        text, sec = answer(item["question"], args.top_k)
        refused = normalize(REFUSAL) in normalize(text)
        hallucinated += not refused
        print(f"  {'OK  ' if refused else '환각'} ({sec:5.1f}s) {item['question']}")
        if not refused:
            print(f"        답변: {text[:150]}")
            print(f"        근거: {item['why']}")

    a, n = len(answerable), len(negative)
    print(f"(top_k = {args.top_k})")
    print("\n" + "-" * 78)
    print(f"답변 정확도   : {correct}/{a}  ({correct / a * 100:.1f}%)   기대 문자열이 답변에 포함됨")
    print(f"과잉 거절     : {refused_wrongly}/{a}  ({refused_wrongly / a * 100:.1f}%)   답이 있는데 거절함")
    print(f"환각          : {hallucinated}/{n}  ({hallucinated / n * 100:.1f}%)   답이 없는데 답변함")
    print()


if __name__ == "__main__":
    main()
