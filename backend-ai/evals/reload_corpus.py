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

from eval_session import OWNERS, owner_for

SPRING = "http://127.0.0.1:8080"
CORPUS_DIR = Path(r"C:\Users\onsyg\Desktop\예시pdf")
FILES = list(OWNERS)  # 평가셋이 쓰는 문서 = 세션 매핑에 등록된 문서


def headers(doc: str):
    """문서마다 세션이 다르다 - 운영이 세션당 문서 1개만 두기 때문이다.

    업로드·목록·삭제가 모두 이 헤더를 요구한다.
    """
    return {"X-Session-Id": owner_for(doc)}


def list_documents(doc: str):
    """그 세션이 보는 목록. 예시 문서(owner NULL)도 같이 온다."""
    return requests.get(f"{SPRING}/api/documents", headers=headers(doc), timeout=30).json()


def delete_all(doc: str):
    """그 세션이 가진 문서만 지운다.

    예시 문서(sample=True, owner NULL)는 건너뛴다 - 서버가 403 으로 막고,
    로컬 화면에서 쓰는 문서라 지워서도 안 된다.
    """
    mine = [d for d in list_documents(doc) if not d.get("sample")]
    for d in mine:
        requests.delete(f"{SPRING}/api/documents/{d['doc_id']}", headers=headers(doc), timeout=60)
        print(f"  삭제: {d['filename']} ({d['chunk_count']}청크)")
    return len(mine)


def upload(doc: str):
    """SSE 스트림을 끝까지 읽어 업로드 완료를 기다린다."""
    path = CORPUS_DIR / doc
    started = time.time()
    with path.open("rb") as fh:
        resp = requests.post(
            f"{SPRING}/api/documents/upload",
            files={"file": (path.name, fh, "application/pdf")},
            headers=headers(doc),
            stream=True,
            timeout=900,
        )
        resp.raise_for_status()
        # 이벤트마다 필요한 값이 따로 온다(진행률은 total, 완료는 chunk_count).
        # 마지막 이벤트만 보면 놓치므로 계속 덮어쓰며 모은다.
        info = {}
        for line in resp.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                event = json.loads(line[6:])
                if event.get("stage") == "error":
                    raise RuntimeError(event.get("message"))
                info.update(event)
    count = info.get("chunk_count") or info.get("total_chunks") or "?"
    print(f"  업로드: {path.name}  {count}청크  {time.time() - started:.0f}초")


def main():
    for name in FILES:
        if not (CORPUS_DIR / name).exists():
            sys.exit(f"원본 PDF 없음: {CORPUS_DIR / name}")

    print("기존 문서 삭제")
    removed = sum(delete_all(name) for name in FILES)
    if removed == 0:
        print("  (없음)")

    print("\n재업로드 (문서마다 세션을 따로 쓴다 - 운영과 같은 조건)")
    for name in FILES:
        upload(name)

    print("\n결과")
    total = 0
    for name in FILES:
        mine = [d for d in list_documents(name) if not d.get("sample")]
        # 세션당 1개가 운영 규칙이다. 2개 이상이면 규칙이나 이 스크립트가 어긋난 것이다.
        flag = "" if len(mine) == 1 else f"   <-- 문서 {len(mine)}개! 세션당 1개여야 한다"
        for d in mine:
            print(f"  [{owner_for(name)}] {d['filename']}  {d['chunk_count']}청크{flag}")
            total += d["chunk_count"]
        if not mine:
            print(f"  [{owner_for(name)}] 없음{flag}")
    print(f"  합계 {total}청크")

    leftovers = requests.get(f"{SPRING}/api/documents/leftovers", timeout=30).json()
    print(f"  잔여 벡터 {leftovers['count']}건")


if __name__ == "__main__":
    main()
