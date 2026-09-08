# office 서버(8899 등) 종료.
$port = "8899"
if (Test-Path "$PSScriptRoot\.env") {
    $m = Select-String -Path "$PSScriptRoot\.env" -Pattern '^OFFICE_PORT=(\d+)'
    if ($m) { $port = $m.Matches.Groups[1].Value }
}
$pids = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if ($pids) {
    $pids | ForEach-Object { Stop-Process -Id $_ -Force; Write-Host "종료: PID $_" }
} else {
    Write-Host "포트 $port 에서 실행 중인 프로세스 없음"
}
