r"""평가용 코퍼스를 지우고 다시 올린다.

청킹·추출 설정을 바꿔가며 비교하려면 매번 문서를 새로 넣어야 한다.
브라우저로 하면 한 번에 몇 분씩 걸려서 실험을 여러 번 돌리기 어렵다.

주의: 설정(chunk-size, setSortByPosition 등)은 Spring 기동 시점에 읽힌다.
      application.yml 이나 자바 코드를 고쳤다면 이 스크립트 전에 Spring 을
      반드시 재시작해야 한다. 실행 중인 JVM 은 시작할 때 읽은 값을 계속 쓴다.

사용법:
    cd backend-ai
    .\venv\Scripts\python.exe evals\reload_corpus.py
"""
import json
import sys
import time
from pathlib import Path

import requests

SPRING = "http://127.0.0.1:8080"
CORPUS_DIR = Path(r"C:\Users\onsyg\Desktop\예시pdf")
FILES = ["Galaxybook_guide.pdf", "사람인_이력서_강현수.pdf"]


def list_documents():
    return requests.get(f"{SPRING}/api/documents", timeout=30).json()


def delete_all():
    docs = list_documents()
    for d in docs:
        requests.delete(f"{SPRING}/api/documents/{d['doc_id']}", timeout=60)
        print(f"  삭제: {d['filename']} ({d['chunk_count']}청크)")
    return len(docs)


def upload(path: Path):
    """SSE 스트림을 끝까지 읽어 업로드 완료를 기다린다."""
    started = time.time()
    with path.open("rb") as fh:
        resp = requests.post(
            f"{SPRING}/api/documents/upload",
            files={"file": (path.name, fh, "application/pdf")},
            stream=True,
            timeout=900,
        )
        resp.raise_for_status()
        last = {}
        for line in resp.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                last = json.loads(line[6:])
                if last.get("stage") == "error":
                    raise RuntimeError(last.get("message"))
    print(f"  업로드: {path.name}  {last.get('chunk_count', '?')}청크  {time.time() - started:.0f}초")


def main():
    for name in FILES:
        if not (CORPUS_DIR / name).exists():
            sys.exit(f"원본 PDF 없음: {CORPUS_DIR / name}")

    print("기존 문서 삭제")
    if delete_all() == 0:
        print("  (없음)")

    print("\n재업로드")
    for name in FILES:
        upload(CORPUS_DIR / name)

    print("\n결과")
    total = 0
    for d in list_documents():
        print(f"  {d['filename']}  {d['chunk_count']}청크")
        total += d["chunk_count"]
    print(f"  합계 {total}청크")

    leftovers = requests.get(f"{SPRING}/api/documents/leftovers", timeout=30).json()
    print(f"  잔여 벡터 {leftovers['count']}건")


if __name__ == "__main__":
    main()
