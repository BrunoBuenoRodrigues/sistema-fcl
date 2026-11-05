param([string]$Destino)

$ErrorActionPreference = 'Stop'
$raizProjeto = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$arquivoAmbiente = Join-Path $raizProjeto '.env'
$compose = Join-Path $raizProjeto 'compose.yaml'
if (-not $Destino) { $Destino = Join-Path $env:LOCALAPPDATA 'SistemaFCL\Backups' }
$raizDestino = [System.IO.Path]::GetFullPath($Destino)
if ($raizDestino.StartsWith($raizProjeto.TrimEnd('\') + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'O destino precisa ficar fora do repositório.'
}
if (-not (Test-Path -LiteralPath $arquivoAmbiente -PathType Leaf)) { throw 'Arquivo .env não encontrado.' }

$envMap = @{}
foreach ($line in Get-Content -LiteralPath $arquivoAmbiente) {
    if ($line -match '^\s*(POSTGRES_DB|POSTGRES_USER)\s*=\s*(.*)\s*$') { $envMap[$matches[1]] = $matches[2].Trim('"', "'") }
}
$dbName = if ($envMap.POSTGRES_DB) { $envMap.POSTGRES_DB } else { 'fcl_gestao' }
$dbUser = if ($envMap.POSTGRES_USER) { $envMap.POSTGRES_USER } else { 'fcl' }
$timestamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$dir = Join-Path $raizDestino $timestamp
if (Test-Path -LiteralPath $dir) { throw "A pasta de backup ja existe: $dir" }
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls $dir /inheritance:r /grant:r "*$($userSid):(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' /C | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel restringir as permissoes do diretorio de backup.' }
$dbContainer = (& docker compose -f $compose ps -q db).Trim()
$backendContainer = (& docker compose -f $compose ps -q backend).Trim()
if ($LASTEXITCODE -ne 0 -or -not $dbContainer -or -not $backendContainer) { throw 'Containers db/backend não estão ativos.' }

$dumpTemp = "/tmp/fcl-$timestamp.dump"
$filesTemp = "/tmp/fcl-uploads-$timestamp.tar.gz"
try {
    & docker exec $dbContainer pg_dump -U $dbUser -d $dbName --format=custom --no-owner --no-privileges -f $dumpTemp
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump falhou.' }
    & docker exec $backendContainer tar -czf $filesTemp -C /app/uploads .
    if ($LASTEXITCODE -ne 0) { throw 'Criação do arquivo de anexos falhou.' }
    & docker cp "${dbContainer}:$dumpTemp" (Join-Path $dir 'database.dump') | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cópia do dump falhou.' }
    & docker cp "${backendContainer}:$filesTemp" (Join-Path $dir 'attachments.tar.gz') | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cópia dos anexos falhou.' }

    $sqlCounts = "SELECT table_name || '|' || (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;"
    $counts = @(& docker exec $dbContainer psql -U $dbUser -d $dbName -At -c $sqlCounts)
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível obter contagens exatas das tabelas.' }
    $version = (& docker exec $dbContainer psql -U $dbUser -d $dbName -At -c 'SHOW server_version').Trim()
    $integrity = @(& docker exec $dbContainer psql -U $dbUser -d $dbName -At -F '|' -c "SELECT (SELECT count(*) FROM information_schema.table_constraints WHERE table_schema='public'), (SELECT count(*) FROM information_schema.table_constraints WHERE table_schema='public' AND constraint_type='FOREIGN KEY'), (SELECT count(*) FROM information_schema.sequences WHERE sequence_schema='public'), (SELECT count(*) FROM usuario)")
    @("created_utc=$timestamp", "database=$dbName", "postgres_server=$version", "constraints=$((($integrity -join '').Split('|'))[0])", "foreign_keys=$((($integrity -join '').Split('|'))[1])", "sequences=$((($integrity -join '').Split('|'))[2])", "users=$((($integrity -join '').Split('|'))[3])", 'table_counts:') + $counts | Set-Content -LiteralPath (Join-Path $dir 'manifest.txt') -Encoding utf8

    Copy-Item -LiteralPath $arquivoAmbiente -Destination (Join-Path $dir 'config.env')
    Copy-Item -LiteralPath $compose -Destination (Join-Path $dir 'compose.yaml')
    Push-Location $dir
    try {
        Get-FileHash database.dump, attachments.tar.gz, config.env, compose.yaml, manifest.txt -Algorithm SHA256 |
            ForEach-Object { "$($_.Hash.ToLower())  $($_.Path | Split-Path -Leaf)" } |
            Set-Content -LiteralPath SHA256SUMS -Encoding ascii
    } finally { Pop-Location }

    Write-Output "Backup criado: $dir"
    Get-ChildItem -LiteralPath $dir -File | Select-Object Name, Length
} catch {
    throw "Backup incompleto em '$dir'. Preserve a pasta para diagnóstico; backups anteriores não foram removidos. $($_.Exception.Message)"
} finally {
    & docker exec $dbContainer rm -f $dumpTemp 2>$null | Out-Null
    & docker exec $backendContainer rm -f $filesTemp 2>$null | Out-Null
}
