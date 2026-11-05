param(
    [switch]$Sobrescrever
)

$raizProjeto = Split-Path -Parent $PSScriptRoot
$arquivoAmbiente = Join-Path $raizProjeto ".env"
$diretorioBackupsAutomaticos = Join-Path $env:LOCALAPPDATA 'SistemaFCL\Backups\Automaticos'

New-Item -ItemType Directory -Path $diretorioBackupsAutomaticos -Force | Out-Null
$sidGrupoDocker = (Get-LocalGroup -Name 'docker-users').SID.Value
$sidUsuarioAtual = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls $diretorioBackupsAutomaticos /inheritance:r /grant:r `
    "*$($sidUsuarioAtual):(OI)(CI)F" `
    '*S-1-5-18:(OI)(CI)F' `
    '*S-1-5-32-544:(OI)(CI)F' `
    "*$($sidGrupoDocker):(OI)(CI)M" /T /C | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Could not grant Docker access to the automatic backup directory."
}

if ((Test-Path -LiteralPath $arquivoAmbiente) -and -not $Sobrescrever) {
    Write-Output "O arquivo .env já existe. Nenhuma alteração foi realizada."
    exit 0
}

function Novo-Segredo([int]$quantidadeBytes) {
    $bytes = New-Object byte[] $quantidadeBytes
    $gerador = [System.Security.Cryptography.RandomNumberGenerator]::Create()

    try {
        $gerador.GetBytes($bytes)
    }
    finally {
        $gerador.Dispose()
    }

    return -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

$linhas = @(
    "APP_HOST=127.0.0.1",
    "APP_PORT=8080",
    "POSTGRES_DB=fcl_gestao",
    "POSTGRES_USER=fcl",
    "POSTGRES_PASSWORD=$(Novo-Segredo 24)",
    "JWT_SECRET_KEY=$(Novo-Segredo 64)",
    "TOKEN_EXPIRACAO_MINUTOS=60",
    "LOGIN_MAX_TENTATIVAS=5",
    "LOGIN_BLOQUEIO_MINUTOS=15",
    "CORS_ORIGINS=http://localhost:8080",
    "ADMIN_INICIAL_NOME=Administrador",
    "ADMIN_INICIAL_LOGIN=admin",
    "ADMIN_INICIAL_SENHA=$(Novo-Segredo 16)",
    "BACKUP_HOST_DIR=$(if ($env:LOCALAPPDATA) { ($env:LOCALAPPDATA -replace '\\', '/') + '/SistemaFCL/Backups/Automaticos' } else { './backups/automaticos' })",
    "BACKUP_INTERVALO_HORAS=24",
    "BACKUP_MAX_IDADE_HORAS=26",
    "MONITOR_INTERVALO_MINUTOS=5",
    "LOG_MAX_SIZE=10m",
    "LOG_MAX_ARQUIVOS=5"
)

$utf8SemBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($arquivoAmbiente, $linhas, $utf8SemBom)

Write-Output "Arquivo .env criado com credenciais aleatórias fortes."
Write-Output "Login inicial: admin"
Write-Output "Consulte ADMIN_INICIAL_SENHA no arquivo .env para o primeiro acesso."
