# AI Search 최초 1회 환경 세팅 (Windows / PowerShell)
#   실행: powershell -ExecutionPolicy Bypass -File .\setup.ps1
#
# 이 스크립트가 하는 일:
#   1. python/node/npm/mvn/java/ollama 가 PATH 에 있는지 확인 (없으면 안내 후 중단)
#   2. Ollama 실행 여부 확인 + 필요한 모델 pull (bge-m3, qwen2.5:3b)
#   3. backend-ai\venv 생성 + requirements 설치
#   4. frontend\node_modules 설치
#   5. backend-ai\.env 없으면 .env.example 에서 생성
#
# 이미 되어 있는 항목은 건너뛰므로 재실행해도 안전하다.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-Cmd($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

Write-Host "== 1. 필수 프로그램 확인 ==" -ForegroundColor Cyan
$missing = @()
foreach ($cmd in @("python", "node", "npm", "mvn", "java", "ollama")) {
    if (Test-Cmd $cmd) {
        Write-Host "  OK  $cmd" -ForegroundColor Green
    } else {
        Write-Host "  없음 $cmd" -ForegroundColor Red
        $missing += $cmd
    }
}
if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "다음 프로그램을 설치(또는 PATH 등록)한 뒤 다시 실행하세요: $($missing -join ', ')" -ForegroundColor Yellow
    Write-Host "  - python: https://www.python.org/downloads/ (3.10+)"
    Write-Host "  - node/npm: https://nodejs.org/ (LTS)"
    Write-Host "  - mvn: https://maven.apache.org/download.cgi (bin 폴더를 PATH 에 추가)"
    Write-Host "  - java: JDK 17 (Temurin 등)"
    Write-Host "  - ollama: winget install Ollama.Ollama  (또는 https://ollama.com/download)"
    exit 1
}

Write-Host ""
Write-Host "== 2. Ollama 확인 + 모델 pull ==" -ForegroundColor Cyan
try {
    Invoke-WebRequest -UseBasicParsing "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
} catch {
    throw "Ollama가 실행 중이 아닙니다. Ollama 앱을 먼저 실행한 뒤 다시 시도하세요."
}
foreach ($model in @("bge-m3", "qwen2.5:3b")) {
    Write-Host "  pull $model (이미 있으면 즉시 스킵됨)..." -ForegroundColor Yellow
    & ollama pull $model
}

Write-Host ""
Write-Host "== 3. Python 가상환경 (backend-ai) ==" -ForegroundColor Cyan
$venvPython = Join-Path $root "backend-ai\venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  venv 생성..." -ForegroundColor Yellow
    python -m venv (Join-Path $root "backend-ai\venv")
} else {
    Write-Host "  venv 이미 존재" -ForegroundColor Green
}
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -r (Join-Path $root "backend-ai\requirements.txt")
Write-Host "  requirements 설치 완료" -ForegroundColor Green

Write-Host ""
Write-Host "== 4. Frontend 의존성 (npm install) ==" -ForegroundColor Cyan
$nodeModules = Join-Path $root "frontend\node_modules"
if (-not (Test-Path $nodeModules)) {
    Push-Location (Join-Path $root "frontend")
    npm install
    Pop-Location
} else {
    Write-Host "  node_modules 이미 존재 (스킵)" -ForegroundColor Green
}

Write-Host ""
Write-Host "== 5. .env 파일 ==" -ForegroundColor Cyan
$envPath = Join-Path $root "backend-ai\.env"
$envExamplePath = Join-Path $root "backend-ai\.env.example"
if (-not (Test-Path $envPath)) {
    Copy-Item $envExamplePath $envPath
    Write-Host "  backend-ai\.env 생성됨 (기본값은 .env 없이도 동작 — Groq 쓰려면 GROQ_API_KEY 채우기)" -ForegroundColor Yellow
} else {
    Write-Host "  .env 이미 존재 (스킵)" -ForegroundColor Green
}

Write-Host ""
Write-Host "세팅 완료. 다음 명령으로 실행하세요:" -ForegroundColor Green
Write-Host "  .\start_search.ps1"
