# AI Search 전체 서비스 종료 (Windows / PowerShell)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root ".ai_search_pids.json"

function Kill-Port($port) {
    Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
}

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile | ConvertFrom-Json
    foreach ($p in @($pids.ai, $pids.spring, $pids.frontend)) {
        if ($p) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item $pidFile
}

# 포트 기준으로도 정리 (Start-Process 자식들이 남는 경우 대비)
Kill-Port 8001; Kill-Port 8080; Kill-Port 3000

Write-Host "종료 완료 (Ollama는 계속 실행됩니다)" -ForegroundColor Green
