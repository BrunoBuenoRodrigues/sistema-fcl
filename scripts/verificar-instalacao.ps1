param(
    [switch]$TestarLogin
)

$ErrorActionPreference = "Stop"
$raizProjeto = Split-Path -Parent $PSScriptRoot
$arquivoAmbiente = Join-Path $raizProjeto ".env"
$raizBackups = Join-Path $raizProjeto "backups"
$falhas = 0

function Registrar-Resultado(
    [string]$Verificacao,
    [bool]$Sucesso,
    [string]$Detalhe
) {
    $estado = if ($Sucesso) { "OK" } else { "FALHA" }
    Write-Output "[$estado] $Verificacao - $Detalhe"

    if (-not $Sucesso) {
        $script:falhas++
    }
}

function Ler-Ambiente {
    $valores = @{}

    if (-not (Test-Path -LiteralPath $arquivoAmbiente -PathType Leaf)) {
        return $valores
    }

    foreach ($linha in Get-Content -LiteralPath $arquivoAmbiente) {
        if ($linha -match '^(?<chave>[^#=]+)=(?<valor>.*)$') {
            $valores[$matches.chave.Trim()] = $matches.valor
        }
    }

    return $valores
}

Set-Location -LiteralPath $raizProjeto
$ambiente = Ler-Ambiente
$porta = if ($ambiente["APP_PORT"]) { $ambiente["APP_PORT"] } else { "8080" }
$usuarioBanco = if ($ambiente["POSTGRES_USER"]) { $ambiente["POSTGRES_USER"] } else { "fcl" }
$nomeBanco = if ($ambiente["POSTGRES_DB"]) { $ambiente["POSTGRES_DB"] } else { "fcl_gestao" }
$urlBase = "http://localhost:$porta"

& docker compose config --quiet 2>$null
Registrar-Resultado "Configuração Docker" ($LASTEXITCODE -eq 0) "compose.yaml válido"

$servicosEsperados = @("db", "backend", "frontend", "backup", "monitor")
$servicosExecutando = @(& docker compose ps --status running --services 2>$null)
$servicosAusentes = @($servicosEsperados | Where-Object { $_ -notin $servicosExecutando })
Registrar-Resultado `
    "Serviços Docker" `
    ($servicosAusentes.Count -eq 0) `
    $(if ($servicosAusentes.Count -eq 0) { "db, backend, frontend, backup e monitor em execução" } else { "ausentes: $($servicosAusentes -join ', ')" })

try {
    $pagina = Invoke-WebRequest -UseBasicParsing -Uri $urlBase -TimeoutSec 10
    Registrar-Resultado "Frontend" ($pagina.StatusCode -eq 200) "HTTP $($pagina.StatusCode)"
    Registrar-Resultado `
        "Proteções do navegador" `
        ([bool]$pagina.Headers["Content-Security-Policy"] -and $pagina.Headers["X-Frame-Options"] -eq "SAMEORIGIN") `
        "CSP e proteção contra enquadramento"
}
catch {
    Registrar-Resultado "Frontend" $false $_.Exception.Message
}

try {
    $saude = Invoke-RestMethod -Uri "$urlBase/api/health" -TimeoutSec 10
    Registrar-Resultado "API e banco" ($saude.status -eq "ok") "healthcheck respondeu ok"
}
catch {
    Registrar-Resultado "API e banco" $false $_.Exception.Message
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri "$urlBase/api/docs" -TimeoutSec 10 -ErrorAction Stop | Out-Null
    Registrar-Resultado "Documentação de produção" $false "endpoint /api/docs está público"
}
catch {
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    Registrar-Resultado "Documentação de produção" ($status -eq 404) "HTTP $status"
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri "$urlBase/api/teste-banco" -TimeoutSec 10 -ErrorAction Stop | Out-Null
    Registrar-Resultado "Diagnóstico de banco em produção" $false "endpoint /api/teste-banco está público"
}
catch {
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    Registrar-Resultado "Diagnóstico de banco em produção" ($status -eq 404) "HTTP $status"
}

$sqlContagens = @"
SELECT 'usuarios', count(*) FROM usuario
UNION ALL SELECT 'produtos', count(*) FROM produto
UNION ALL SELECT 'fornecedores', count(*) FROM fornecedor
UNION ALL SELECT 'clientes', count(*) FROM cliente
UNION ALL SELECT 'solicitacoes', count(*) FROM solicitacao_compra
UNION ALL SELECT 'pedidos', count(*) FROM pedido_compra
UNION ALL SELECT 'recebimentos', count(*) FROM recebimento
UNION ALL SELECT 'entregas', count(*) FROM entrega
ORDER BY 1;
"@

$linhasContagens = @(
    & docker compose exec -T db psql `
        -U $usuarioBanco `
        -d $nomeBanco `
        -At `
        -F "|" `
        -c $sqlContagens 2>$null
)
$consultaValida = $LASTEXITCODE -eq 0 -and $linhasContagens.Count -eq 8
Registrar-Resultado "Consulta ao PostgreSQL" $consultaValida "oito conjuntos de dados consultados"

if ($consultaValida) {
    Write-Output ""
    Write-Output "Contagens atuais:"
    foreach ($linha in $linhasContagens) {
        $partes = $linha.Split("|", 2)
        Write-Output "- $($partes[0]): $($partes[1])"
    }
}

$backupRecente = Get-ChildItem -LiteralPath $raizBackups -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^20\d{6}T\d{6}Z$' } |
    Sort-Object Name |
    Select-Object -Last 1

if (-not $backupRecente) {
    Registrar-Resultado "Backup" $false "nenhum backup automático encontrado"
}
else {
    $arquivosObrigatorios = @("banco.dump", "anexos.tar.gz", "checksums.sha256")
    $arquivosAusentes = @(
        $arquivosObrigatorios |
            Where-Object { -not (Test-Path -LiteralPath (Join-Path $backupRecente.FullName $_) -PathType Leaf) }
    )
    $idadeHoras = ((Get-Date).ToUniversalTime() - $backupRecente.LastWriteTimeUtc).TotalHours

    & docker compose exec -T backup sh -c "cd '/backups/$($backupRecente.Name)' && sha256sum -c checksums.sha256" 2>$null | Out-Null
    $checksumsValidos = $LASTEXITCODE -eq 0
    $backupValido = $arquivosAusentes.Count -eq 0 -and $checksumsValidos -and $idadeHoras -le 26
    Registrar-Resultado `
        "Backup" `
        $backupValido `
        "$($backupRecente.Name), integridade $(if ($checksumsValidos) { 'válida' } else { 'inválida' }), idade $([math]::Round($idadeHoras, 1))h"
}

if ($TestarLogin) {
    $login = Read-Host "Login para homologação"
    $senhaSegura = Read-Host "Senha" -AsSecureString
    $ponteiro = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($senhaSegura)

    try {
        $senha = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteiro)
        $corpo = @{ login = $login; senha = $senha } | ConvertTo-Json
        $respostaLogin = Invoke-RestMethod `
            -Method Post `
            -Uri "$urlBase/api/login" `
            -ContentType "application/json" `
            -Body $corpo `
            -TimeoutSec 10
        $cabecalhos = @{ Authorization = "Bearer $($respostaLogin.access_token)" }
        $usuarioAtual = Invoke-RestMethod -Uri "$urlBase/api/me" -Headers $cabecalhos -TimeoutSec 10
        Registrar-Resultado "Login real" ([bool]$usuarioAtual.ativo) "usuário ativo, perfil $($usuarioAtual.perfil)"
    }
    catch {
        Registrar-Resultado "Login real" $false "não foi possível autenticar"
    }
    finally {
        if ($ponteiro -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteiro)
        }
        $senha = $null
        $corpo = $null
    }
}

Write-Output ""
if ($falhas -gt 0) {
    throw "Homologação técnica concluída com $falhas falha(s)."
}

Write-Output "Homologação técnica concluída sem falhas."
