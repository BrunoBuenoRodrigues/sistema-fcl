param([Parameter(Mandatory = $true)][string]$Backup)

$ErrorActionPreference = 'Stop'
$dir = [System.IO.Path]::GetFullPath($Backup)
if (-not (Test-Path -LiteralPath $dir -PathType Container)) { throw 'Pasta de backup não encontrada.' }
foreach ($name in @('database.dump', 'attachments.tar.gz', 'config.env', 'compose.yaml', 'manifest.txt', 'SHA256SUMS')) {
    if (-not (Test-Path -LiteralPath (Join-Path $dir $name) -PathType Leaf)) { throw "Arquivo ausente: $name" }
}
 $allowed = @('database.dump', 'attachments.tar.gz', 'config.env', 'compose.yaml', 'manifest.txt')
$seen = @{}
foreach ($line in Get-Content -LiteralPath (Join-Path $dir 'SHA256SUMS')) {
    if ($line -notmatch '^([0-9a-fA-F]{64})\s+(.+)$') { throw 'Formato inválido em SHA256SUMS.' }
    $expected, $name = $matches[1].ToLower(), $matches[2]
    if ($name -notin $allowed -or $seen.ContainsKey($name)) { throw "Entrada inesperada ou duplicada em SHA256SUMS: $name" }
    $path = Join-Path $dir $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Arquivo listado no checksum ausente: $name" }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw "Checksum inválido: $name" }
    $seen[$name] = $true
    Write-Output "[OK] SHA-256 $name"
}
if ($seen.Count -ne $allowed.Count) { throw 'SHA256SUMS não cobre todos os artefatos obrigatórios.' }
$dump = (Resolve-Path -LiteralPath (Join-Path $dir 'database.dump')).Path
$listing = & docker run --rm --network none -v "${dump}:/backup.dump:ro" postgres:16-alpine pg_restore --list /backup.dump 2>&1
if ($LASTEXITCODE -ne 0 -or -not ($listing -match 'TABLE DATA')) { throw 'pg_restore -l falhou ou o dump não contém dados de tabela.' }
$archive = (Resolve-Path -LiteralPath (Join-Path $dir 'attachments.tar.gz')).Path
$tarCheck = & docker run --rm --network none -v "${archive}:/attachments.tar.gz:ro" postgres:16-alpine tar -tzf /attachments.tar.gz 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Arquivo de anexos inválido.' }
if ($tarCheck | Where-Object { $_ -match '(^|/)\.\.(/|$)|^/' }) { throw 'O arquivo de anexos contém um caminho inseguro.' }
Write-Output "[OK] pg_restore -l; $(@($listing | Where-Object { $_ -match ' TABLE DATA ' }).Count) entradas de dados"
Write-Output "[OK] Arquivo de anexos legível; $(@($tarCheck).Count) entradas"
