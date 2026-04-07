# Python 3.11 slim: 필요한 것만 포함된 경량 이미지
FROM python:3.11-slim

WORKDIR /app

# requirements.txt 먼저 복사해서 패키지 캐시를 활용한다.
# 패키지 목록이 안 바뀌면 매번 재설치하지 않아도 된다. (빌드 속도 향상)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 복사
COPY . .

# ChromaDB 데이터 디렉토리 미리 생성
RUN mkdir -p /app/data/chroma_db

EXPOSE 8001

# 0.0.0.0: 컨테이너 외부(Docker 네트워크)에서 접근 가능하도록 설정
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
