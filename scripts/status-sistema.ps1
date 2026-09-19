param(
    [ValidateRange(1, 200)]
    [int]$Linhas = 20
)

$ErrorActionPreference = "Stop"
$raizProjeto = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $raizProjeto

Write-Output "Serviços:"
& docker compose ps
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível consultar os serviços Docker."
}

Write-Output ""
Write-Output "Monitoramento recente:"
& docker compose logs --tail $Linhas monitor
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível consultar o monitoramento."
}

$backupRecente = Get-ChildItem -LiteralPath (Join-Path $raizProjeto "backups") -Directory |
    Where-Object { $_.Name -match '^20\d{6}T\d{6}Z$' } |
    Sort-Object Name |
    Select-Object -Last 1

Write-Output ""
if ($backupRecente) {
    Write-Output "Backup mais recente: $($backupRecente.Name)"
}
else {
    Write-Output "Backup mais recente: não encontrado"
}
