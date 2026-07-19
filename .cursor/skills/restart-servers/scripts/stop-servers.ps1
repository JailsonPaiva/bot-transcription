# Para todos os processos que usam a porta 8000 ou uvicorn/ngrok do bot_orcamento.
$ErrorActionPreference = "SilentlyContinue"

Write-Host "==> Encerrando uvicorn / python relacionados..."
Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object {
    $_.CommandLine -match 'uvicorn|multiprocessing\.spawn|app\.main:app'
} | ForEach-Object {
    Write-Host "  kill python PID=$($_.ProcessId)"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host "==> Encerrando listeners na porta 8000..."
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    Where-Object { $_ -and $_ -ne 0 } |
    ForEach-Object {
        Write-Host "  kill port8000 PID=$_"
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }

Write-Host "==> Encerrando ngrok..."
Get-Process -Name ngrok -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  kill ngrok PID=$($_.Id)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

$still = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($still) {
    Write-Host "ERRO: porta 8000 ainda em uso:"
    $still | Format-Table OwningProcess, State -AutoSize
    exit 1
}

Write-Host "OK: porta 8000 livre; processos antigos encerrados."
exit 0
