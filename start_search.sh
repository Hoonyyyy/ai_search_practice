#!/bin/bash
# AI Search 전체 서비스 시작 — 어느 디렉토리에서 실행해도 동작

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/.ai_search_pids"
LOG_DIR="$SCRIPT_DIR/logs"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${YELLOW}$1${NC}"; }
ok()  { echo -e "  ${GREEN}✓ $1${NC}"; }
err() { echo -e "  ${RED}✗ $1${NC}"; exit 1; }

if [ -f "$PID_FILE" ]; then
  echo -e "${RED}이미 실행 중입니다. ./stop_search.sh 로 먼저 종료하세요.${NC}"
  exit 1
fi

# Groq API 키 확인
if [ ! -f "$SCRIPT_DIR/backend-ai/.env" ]; then
  err "backend-ai/.env 파일이 없습니다.\n  echo 'GROQ_API_KEY=gsk_여기에키입력' > backend-ai/.env"
fi
if ! grep -q "GROQ_API_KEY" "$SCRIPT_DIR/backend-ai/.env"; then
  err "backend-ai/.env 에 GROQ_API_KEY가 없습니다."
fi

mkdir -p "$LOG_DIR"
> "$PID_FILE"

# ── 1. Python AI 서비스 ────────────────────────────────────────
log "[1/3] Python AI 서비스 시작 (포트 8001)..."
if [ ! -f "$SCRIPT_DIR/backend-ai/venv/bin/uvicorn" ]; then
  err "venv가 없습니다.\n  cd backend-ai && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

cd "$SCRIPT_DIR/backend-ai"
"$SCRIPT_DIR/backend-ai/venv/bin/uvicorn" main:app --port 8001 --log-level warning \
  > "$LOG_DIR/backend-ai.log" 2>&1 &
echo "AI_PID=$!" >> "$PID_FILE"

for i in $(seq 1 30); do
  curl -sf http://localhost:8001/health > /dev/null 2>&1 && break
  sleep 1
  [ "$i" -eq 30 ] && err "Python AI 서비스 시작 실패 — logs/backend-ai.log 확인"
done
ok "Python AI 서비스 준비 완료"

# ── 2. Spring Boot ─────────────────────────────────────────────
log "[2/3] Spring Boot 시작 (포트 8080)..."
cd "$SCRIPT_DIR/backend-spring"
mvn spring-boot:run -q > "$LOG_DIR/backend-spring.log" 2>&1 &
echo "SPRING_PID=$!" >> "$PID_FILE"

for i in $(seq 1 60); do
  curl -sf http://localhost:8080/api/documents > /dev/null 2>&1 && break
  sleep 2
  [ "$i" -eq 60 ] && err "Spring Boot 시작 실패 — logs/backend-spring.log 확인"
done
ok "Spring Boot 준비 완료"

# ── 3. React ───────────────────────────────────────────────────
log "[3/3] React 프론트엔드 시작 (포트 3001)..."
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
sleep 1
cd "$SCRIPT_DIR/frontend"
PORT=3001 BROWSER=none npm start > "$LOG_DIR/frontend.log" 2>&1 &
echo "FRONTEND_PID=$!" >> "$PID_FILE"

for i in $(seq 1 90); do
  curl -sf http://localhost:3001 > /dev/null 2>&1 && break
  sleep 1
  [ "$i" -eq 90 ] && err "React 시작 실패 — logs/frontend.log 확인"
done
ok "React 준비 완료"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  AI Search 실행 중 → http://localhost:3001  ${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  종료: ./stop_search.sh"
echo "  로그: $LOG_DIR/"
