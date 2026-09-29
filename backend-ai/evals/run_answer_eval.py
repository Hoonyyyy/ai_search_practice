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
import sys
import time
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
REFUSAL = "찾을 수 없습니다"
TOP_K = 4


def answer(question: str, top_k: int, owner: str):
    """검색 -> LLM 스트리밍. 실제 서비스와 같은 경로를 탄다.

    owner 는 그 질문이 대상으로 하는 문서의 세션이다. 운영에서 검색 범위는
    항상 문서 하나이므로(resolveSearchOwner), 평가도 같은 조건으로 둔다.
    """
    chunks = requests.post(
        f"{AI_URL}/ai/search",
        json={"query": question, "top_k": top_k, "owner": owner},
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
    error = None
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            event = json.loads(line[6:])
            if event.get("type") == "text":
                parts.append(event["content"])
            elif event.get("type") == "error":
                # 이 이벤트를 버리면 LLM 장애가 "빈 답변" 으로 보이고,
                # 채점기는 그걸 오답이나 환각으로 센다. 실제로 그렇게 기록된 적이 있다
                # (2026-09-29, Groq 무료 티어 한도). 장애는 품질 지표가 아니다.
                error = event.get("content", "(내용 없는 오류)")
    return "".join(parts).strip(), time.time() - started, error


RETRY_WAIT_SEC = 60


def answer_with_retry(question: str, top_k: int, owner: str, tries: int = 3):
    """빈 답변·오류는 다시 시도한다.

    Groq 무료 티어는 분당 토큰 한도가 있어 연속 호출에서 429 가 난다.
    한도 창이 20초보다 길어서, 짧게 쉬면 재시도가 같은 한도에 또 걸리고
    한 번 걸린 뒤로는 남은 질문이 줄줄이 실패한다(2026-09-29, top_k=10 에서 19건).
    top_k 를 키우면 질문당 컨텍스트가 커져 같은 문항 수로도 한도에 더 빨리 닿는다.

    끝까지 실패하면 그 사실을 그대로 돌려준다 - 조용히 0점 처리하지 않는다.
    """
    last_error = None
    for attempt in range(1, tries + 1):
        text, sec, error = answer(question, top_k, owner)
        if text and not error:
            return text, sec, None
        last_error = error or "빈 답변"
        if attempt < tries:
            print(f"      (재시도 {attempt}/{tries - 1} - {RETRY_WAIT_SEC}초 대기) {last_error[:60]}")
            time.sleep(RETRY_WAIT_SEC)
    return "", 0.0, last_error


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
    failed_answerable = []   # LLM 장애로 못 잰 것. 품질 집계에서 빼고 따로 보고한다.
    print("\n-- 답이 있는 질문 --")
    for item in answerable:
        text, sec, error = answer_with_retry(item["question"], args.top_k, owner_for(item["doc"]))
        if error:
            failed_answerable.append((item["question"], error))
            print(f"  측정실패 ({sec:5.1f}s) {item['question']}")
            print(f"        {error[:150]}")
            continue
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
    failed_negative = []
    print("\n-- 답이 없는 질문 --")
    for item in negative:
        # 답 없는 질문도 대상 문서가 정해져 있다. "노트북 가격"을 이력서에 물으면
        # 너무 쉽게 거절되므로, 주제가 가까운 문서를 범위로 둬야 진짜 시험이 된다.
        text, sec, error = answer_with_retry(item["question"], args.top_k, owner_for(item["doc"]))
        if error:
            failed_negative.append((item["question"], error))
            print(f"  측정실패 ({sec:5.1f}s) [{item['doc'][:14]}] {item['question']}")
            print(f"        {error[:150]}")
            continue
        refused = normalize(REFUSAL) in normalize(text)
        hallucinated += not refused
        print(f"  {'OK  ' if refused else '환각'} ({sec:5.1f}s) [{item['doc'][:14]}] {item['question']}")
        if not refused:
            print(f"        답변: {text[:150]}")
            print(f"        근거: {item['why']}")

    # 못 잰 질문은 분모에서 뺀다. 장애를 오답으로 세면 지표가 품질을 말하지 않게 된다.
    a = len(answerable) - len(failed_answerable)
    n = len(negative) - len(failed_negative)
    print(f"(top_k = {args.top_k})")
    print("\n" + "-" * 78)
    if a:
        print(f"답변 정확도   : {correct}/{a}  ({correct / a * 100:.1f}%)   기대 문자열이 답변에 포함됨")
        print(f"과잉 거절     : {refused_wrongly}/{a}  ({refused_wrongly / a * 100:.1f}%)   답이 있는데 거절함")
    if n:
        print(f"환각          : {hallucinated}/{n}  ({hallucinated / n * 100:.1f}%)   답이 없는데 답변함")

    failures = failed_answerable + failed_negative
    if failures:
        print(f"\n측정 실패     : {len(failures)}건  <-- LLM 장애. 분모에서 뺐다. 지표를 비교하기 전에 이걸 먼저 없앨 것")
        for q, err in failures:
            print(f"   - {q}  |  {err[:100]}")
    print()


if __name__ == "__main__":
    main()
