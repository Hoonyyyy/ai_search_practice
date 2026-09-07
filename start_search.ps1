# AI Search 전체 서비스 시작 (Windows / PowerShell)
#   실행: powershell -ExecutionPolicy Bypass -File .\start_search.ps1
# 사전 조건:
#   - Ollama 실행 중 + `ollama pull llama3.2:3b`, `ollama pull nomic-embed-text`
#   - backend-ai\venv 생성 및 requirements 설치
#   - frontend\node_modules 설치 (npm install)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Wait-Url($url, $tries, $delay, $name) {
    for ($i = 0; $i -lt $tries; $i++) {
        try { Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3 | Out-Null; return } catch {}
        Start-Sleep -Seconds $delay
    }
    throw "$name 시작 실패 — $logDir 로그 확인"
}

# ── 0. Ollama 확인 ──────────────────────────────────────────
try { Invoke-WebRequest -UseBasicParsing "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null }
catch { throw "Ollama가 실행 중이 아닙니다. Ollama 앱을 실행하세요." }

# ── 1. Python AI 서비스 (8001) ──────────────────────────────
Write-Host "[1/3] Python AI 서비스 시작 (8001)..." -ForegroundColor Yellow
$uvicorn = Join-Path $root "backend-ai\venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) { throw "venv 없음: cd backend-ai; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt" }
$ai = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory (Join-Path $root "backend-ai") `
    -FilePath $uvicorn -ArgumentList "main:app","--port","8001" `
    -RedirectStandardOutput (Join-Path $logDir "backend-ai.out.log") `
    -RedirectStandardError  (Join-Path $logDir "backend-ai.err.log")
Wait-Url "http://localhost:8001/health" 30 1 "Python AI 서비스"
Write-Host "  OK" -ForegroundColor Green

# ── 2. Spring Boot (8080) ───────────────────────────────────
Write-Host "[2/3] Spring Boot 시작 (8080)..." -ForegroundColor Yellow
$spring = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory (Join-Path $root "backend-spring") `
    -FilePath "mvn.cmd" -ArgumentList "spring-boot:run","-q" `
    -RedirectStandardOutput (Join-Path $logDir "backend-spring.out.log") `
    -RedirectStandardError  (Join-Path $logDir "backend-spring.err.log")
Wait-Url "http://localhost:8080/api/documents" 90 2 "Spring Boot"
Write-Host "  OK" -ForegroundColor Green

# ── 3. React (3000) ─────────────────────────────────────────
Write-Host "[3/3] React 시작 (3000)..." -ForegroundColor Yellow
$env:BROWSER = "none"
$frontend = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory (Join-Path $root "frontend") `
    -FilePath "npm.cmd" -ArgumentList "start" `
    -RedirectStandardOutput (Join-Path $logDir "frontend.out.log") `
    -RedirectStandardError  (Join-Path $logDir "frontend.err.log")
Wait-Url "http://localhost:3000" 120 1 "React"
Write-Host "  OK" -ForegroundColor Green

@{ ai = $ai.Id; spring = $spring.Id; frontend = $frontend.Id } | ConvertTo-Json |
    Set-Content -Encoding utf8 (Join-Path $root ".ai_search_pids.json")

Write-Host ""
Write-Host "  AI Search 실행 중 -> http://localhost:3000" -ForegroundColor Green
Write-Host "  종료: .\stop_search.ps1"
