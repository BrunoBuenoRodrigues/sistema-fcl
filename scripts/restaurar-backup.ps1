param(
    [Parameter(Mandatory = $true)]
    [string]$Backup,

    [switch]$Confirmar
)

if (-not $Confirmar) {
    throw "A restauração substitui o banco e os anexos atuais. Execute novamente com -Confirmar."
}

$raizProjeto = Split-Path -Parent $PSScriptRoot
$raizBackups = [System.IO.Path]::GetFullPath((Join-Path $raizProjeto "backups"))
$caminhoInformado = if ([System.IO.Path]::IsPathRooted($Backup)) {
    $Backup
} else {
    Join-Path $raizBackups $Backup
}
$caminhoBackup = [System.IO.Path]::GetFullPath($caminhoInformado)
$prefixoPermitido = $raizBackups.TrimEnd('\') + '\'

if (-not $caminhoBackup.StartsWith($prefixoPermitido, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "O backup deve estar dentro da pasta $raizBackups."
}

if (-not (Test-Path -LiteralPath $caminhoBackup -PathType Container)) {
    throw "Backup não encontrado: $caminhoBackup"
}

$nomeBackup = Split-Path -Leaf $caminhoBackup

if ($nomeBackup -notmatch '^20\d{6}T\d{6}Z$') {
    throw "Nome de backup inválido: $nomeBackup"
}

Set-Location -LiteralPath $raizProjeto

Write-Output "Criando backup de segurança antes da restauração..."
& docker compose exec -T backup /scripts/backup.sh
if ($LASTEXITCODE -ne 0) {
    throw "O backup de segurança falhou; a restauração foi cancelada."
}

& docker compose stop frontend backend backup
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível parar os serviços para restauração."
}

try {
    & docker compose run --rm -T --no-deps backup /scripts/restaurar.sh "/backups/$nomeBackup"
    if ($LASTEXITCODE -ne 0) {
        throw "A restauração falhou."
    }
}
finally {
    & docker compose up -d backend frontend backup
}

Write-Output "Restauração concluída. Aguarde os healthchecks dos serviços."
