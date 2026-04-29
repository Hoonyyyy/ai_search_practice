#!/bin/bash
# AI Search 전체 서비스 종료 — 어느 디렉토리에서 실행해도 동작

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/.ai_search_pids"

GREEN='\033[0;32m'; NC='\033[0m'

if [ ! -f "$PID_FILE" ]; then
  echo "실행 중인 서비스가 없습니다."
  exit 0
fi

source "$PID_FILE"

kill_by_pid() {
  local name=$1 pid=$2
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    echo "  $name 종료 (PID $pid)"
  fi
}

kill_by_port() {
  local pids
  pids=$(lsof -ti:"$1" 2>/dev/null) || true
  [ -n "$pids" ] && echo "$pids" | xargs kill -9 2>/dev/null || true
}

echo "서비스 종료 중..."

kill_by_pid "React"       "$FRONTEND_PID"; kill_by_port 3001; kill_by_port 3000
kill_by_pid "Spring Boot" "$SPRING_PID";   kill_by_port 8080
kill_by_pid "Python AI"   "$AI_PID";       kill_by_port 8001

rm -f "$PID_FILE"
echo -e "${GREEN}✓ 종료 완료${NC}"
