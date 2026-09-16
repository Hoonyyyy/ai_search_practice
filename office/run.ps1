# office 사무실만 띄운다. 기존 rag_search 서비스(8080/8001/3000)와 무관.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .env)) {
    Write-Host "먼저 office/.env 를 만드세요. (.env.example 참고, GROQ_API_KEY 필요)" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path server\venv)) {
    Write-Host "server\venv 없음. 최초 1회:" -ForegroundColor Yellow
    Write-Host "  python -m venv server\venv; server\venv\Scripts\pip install -r server\requirements.txt"
    exit 1
}

$env:PYTHONUTF8 = "1"   # 한국어 로그 깨짐 방지 (MS949 회피)
$port = (Select-String -Path .env -Pattern '^OFFICE_PORT=(\d+)').Matches.Groups[1].Value
if (-not $port) { $port = "8899" }

Write-Host "office → http://127.0.0.1:$port" -ForegroundColor Green
& .\server\venv\Scripts\python -m uvicorn main:app --app-dir server --host 127.0.0.1 --port $port
