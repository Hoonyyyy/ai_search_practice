r"""로컬 Qdrant 의 청크를 Elasticsearch 로 옮긴다 (하이브리드 검색 실험용).

벡터 검색과 키워드 검색(BM25)을 같은 청크로 비교하려면 ES 에도 똑같은 청크가
있어야 한다. 청킹을 다시 하지 않고, Qdrant 에 이미 저장된 payload 를 그대로 쓴다.

주의: Qdrant 임베디드는 한 프로세스만 파일을 열 수 있다.
      FastAPI(8001) 가 켜져 있으면 이 스크립트가 Qdrant 를 못 연다 - 먼저 끈다.

사용법:
    cd backend-ai
    .\venv\Scripts\python.exe evals\es_load.py
"""
import json
from pathlib import Path

import requests
from qdrant_client import QdrantClient

ES = "http://localhost:9200"
INDEX = "chunks"
QDRANT_PATH = Path(__file__).resolve().parent.parent / "data" / "qdrant"
COLLECTION = "documents"

# 필드마다 색인 방식을 정한다.
#   content  : 단어로 찾는다 → text + nori (조사·어미를 떼야 "배터리"로 "배터리를"을 찾는다)
#   doc_id   : 정확히 일치 → keyword
#   filename : 단어로도 찾고 정확히도 거른다 → text + keyword (multi-field)
#   chunk_index : 정렬용 숫자 → integer
#   owner    : 세션 ID. text 면 "user-aaa"가 user/aaa 로 쪼개져 다른 세션이 섞인다 → keyword
MAPPING = {
    "mappings": {
        "properties": {
            "content": {"type": "text", "analyzer": "nori"},
            "doc_id": {"type": "keyword"},
            "filename": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
            "chunk_index": {"type": "integer"},
            "owner": {"type": "keyword"},
        }
    }
}


def recreate_index():
    """다시 돌려도 같은 결과가 나오게, 있으면 지우고 새로 만든다."""
    requests.delete(f"{ES}/{INDEX}")
    resp = requests.put(f"{ES}/{INDEX}", json=MAPPING)
    resp.raise_for_status()


def read_chunks():
    """벡터는 필요 없다 - ES 에는 본문과 메타데이터만 넣는다."""
    client = QdrantClient(path=str(QDRANT_PATH))
    total = client.count(collection_name=COLLECTION).count
    points, _ = client.scroll(
        collection_name=COLLECTION, limit=total, with_payload=True, with_vectors=False
    )
    return points


def bulk_index(points):
    """_bulk 는 한 줄에 명령, 다음 줄에 문서를 쓰는 형식(NDJSON)이다.

    Qdrant 의 point id 를 ES 의 _id 로 그대로 쓴다 - 나중에 두 검색 결과를 합칠 때
    같은 청크인지 알아보는 기준이 된다.
    """
    lines = []
    for p in points:
        lines.append(json.dumps({"index": {"_index": INDEX, "_id": str(p.id)}}))
        lines.append(json.dumps(p.payload, ensure_ascii=False))
    body = ("\n".join(lines) + "\n").encode("utf-8")
    resp = requests.post(
        f"{ES}/_bulk?refresh=true",
        data=body,
        headers={"Content-Type": "application/x-ndjson"},
    )
    resp.raise_for_status()
    if resp.json().get("errors"):
        raise RuntimeError("일부 문서 색인 실패 - 응답의 items 를 확인")


def main():
    points = read_chunks()
    print(f"Qdrant 청크: {len(points)}개")
    by_file = {}
    for p in points:
        name = p.payload.get("filename", "?")
        by_file[name] = by_file.get(name, 0) + 1
    for name, count in by_file.items():
        print(f"  {name}: {count}청크")

    recreate_index()
    bulk_index(points)
    count = requests.get(f"{ES}/{INDEX}/_count").json()["count"]
    print(f"ES 색인 완료: {count}개")


if __name__ == "__main__":
    main()
