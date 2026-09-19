$raizProjeto = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $raizProjeto

& docker compose exec -T backup /scripts/backup.sh

if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível concluir o backup."
}
