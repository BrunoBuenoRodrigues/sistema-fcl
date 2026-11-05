param([Parameter(Mandatory = $true)][string]$Backup)

$ErrorActionPreference = 'Stop'
$dir = [System.IO.Path]::GetFullPath($Backup)
& (Join-Path $PSScriptRoot 'verificar-backup.ps1') -Backup $dir
$manifest = Get-Content -LiteralPath (Join-Path $dir 'manifest.txt')
$expected = @{}
$readingCounts = $false
foreach ($line in $manifest) {
    if ($line -eq 'table_counts:') { $readingCounts = $true; continue }
    if ($readingCounts -and $line -match '^([a-zA-Z0-9_]+)\|([0-9]+)$') { $expected[$matches[1]] = [long]$matches[2] }
}
if ($expected.Count -eq 0) { throw 'Manifesto sem contagens exatas; gere novamente com backup-completo.ps1.' }

$name = 'fcl-restore-test-' + [Guid]::NewGuid().ToString('N').Substring(0, 12)
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$secretBytes = New-Object byte[] 24
try { $rng.GetBytes($secretBytes) } finally { $rng.Dispose() }
$password = [Convert]::ToBase64String($secretBytes).TrimEnd('=').Replace('+','A').Replace('/','B')
$containerCreated = $false
try {
    & docker run -d --rm --name $name --label codex.fcl.backup-test=true --network none --tmpfs '/var/lib/postgresql/data:rw,noexec,nosuid,size=1g' -e "POSTGRES_PASSWORD=$password" -e 'POSTGRES_DB=fcl_gestao' postgres:16-alpine | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível iniciar PostgreSQL temporário isolado.' }
    $containerCreated = $true
    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        & docker exec $name pg_isready -U postgres -d fcl_gestao *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw 'PostgreSQL isolado não ficou pronto.' }
    & docker exec $name psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'CREATE ROLE fcl LOGIN; ALTER DATABASE fcl_gestao OWNER TO fcl;' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Preparação do usuário de teste falhou.' }
    $dump = (Resolve-Path -LiteralPath (Join-Path $dir 'database.dump')).Path
    & docker cp $dump "${name}:/tmp/database.dump" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cópia do dump para o ambiente de teste falhou.' }
    & docker exec $name pg_restore -U fcl -d fcl_gestao --no-owner --no-privileges /tmp/database.dump
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore falhou no banco isolado.' }

    $sqlCounts = "SELECT table_name || '|' || (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;"
    $actualLines = @(& docker exec $name psql -U fcl -d fcl_gestao -At -c $sqlCounts)
    if ($LASTEXITCODE -ne 0) { throw 'Consulta das contagens restauradas falhou.' }
    $actual = @{}
    foreach ($line in $actualLines) { if ($line -match '^([^|]+)\|([0-9]+)$') { $actual[$matches[1]] = [long]$matches[2] } }
    if ($actual.Count -ne $expected.Count) { throw "Quantidade de tabelas divergente: origem=$($expected.Count), restaurada=$($actual.Count)." }
    foreach ($table in $expected.Keys) {
        if (-not $actual.ContainsKey($table) -or $actual[$table] -ne $expected[$table]) { throw "Contagem divergente na tabela $table." }
        Write-Output "[OK] $table`: $($actual[$table]) registros"
    }

    $integritySql = "SELECT 'constraints=' || (SELECT count(*) FROM information_schema.table_constraints WHERE table_schema='public') UNION ALL SELECT 'foreign_keys=' || (SELECT count(*) FROM information_schema.table_constraints WHERE table_schema='public' AND constraint_type='FOREIGN KEY') UNION ALL SELECT 'sequences=' || (SELECT count(*) FROM information_schema.sequences WHERE sequence_schema='public') UNION ALL SELECT 'users=' || (SELECT count(*) FROM usuario);"
    $checks = @(& docker exec $name psql -U fcl -d fcl_gestao -At -c $integritySql)
    if ($LASTEXITCODE -ne 0) { throw 'Verificação de constraints/sequências/usuários falhou.' }
    foreach ($check in $checks) {
        if ($manifest -notcontains $check) { throw "Metadado de integridade divergente: $check" }
        Write-Output "[OK] $check"
    }

    $archive = (Resolve-Path -LiteralPath (Join-Path $dir 'attachments.tar.gz')).Path
    & docker cp $archive "${name}:/tmp/attachments.tar.gz" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cópia do arquivo de anexos falhou.' }
    & docker exec $name sh -c 'mkdir -p /tmp/restored-uploads && tar -xzf /tmp/attachments.tar.gz -C /tmp/restored-uploads'
    if ($LASTEXITCODE -ne 0) { throw 'Extração dos anexos falhou.' }
    $refsSql = "SELECT DISTINCT regexp_replace(v, '^/arquivos/entregas/', '') FROM entrega e CROSS JOIN LATERAL (VALUES (e.anexo_pedido), (e.comprovante_entrega)) AS refs(v) WHERE v LIKE '/arquivos/entregas/%' ORDER BY 1;"
    $refs = @(& docker exec $name psql -U fcl -d fcl_gestao -At -c $refsSql)
    if ($LASTEXITCODE -ne 0) { throw 'Consulta das referências a anexos falhou.' }
    $missing = @()
    foreach ($ref in $refs) {
        & docker exec $name sh -c 'test -f "/tmp/restored-uploads/entregas/$1"' sh $ref *> $null
        if ($LASTEXITCODE -ne 0) { $missing += $ref }
    }
    if ($missing.Count) {
        Write-Warning "A cópia tem $($missing.Count) referências sem arquivo correspondente; nenhum dado foi alterado."
        $missing | ForEach-Object { Write-Output "[AUSENTE] $_" }
        throw "Isolated restore verification failed: $($missing.Count) attachment reference(s) are missing."
    } else { Write-Output "[OK] Todas as $($refs.Count) referências a anexos foram encontradas." }
    Write-Output '[OK] Restauração PostgreSQL 16 validada em rede isolada, sem portas, volumes persistentes ou acesso ao banco de produção.'
} finally {
    if ($containerCreated) {
        $identity = & docker inspect --format '{{.Name}}|{{.HostConfig.NetworkMode}}' $name 2>$null
        $labelsJson = & docker inspect --format '{{json .Config.Labels}}' $name 2>$null
        $labels = $labelsJson | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $identity -eq "/$name|none" -and $labels.'codex.fcl.backup-test' -eq 'true') { & docker stop $name | Out-Null }
        else { Write-Warning "Container de teste '$name' não foi removido porque sua identidade não pôde ser confirmada." }
    }
    $password = $null
}
