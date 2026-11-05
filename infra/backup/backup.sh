#!/bin/sh
set -eu

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
temporario="/backups/.tmp-${timestamp}"
destino="/backups/${timestamp}"

if [ -e "$temporario" ] || [ -e "$destino" ]; then
    echo "Backup with the same timestamp already exists; nothing was overwritten." >&2
    exit 1
fi

mkdir -p "$temporario"

limpar_temporario() {
    rm -rf "$temporario"
}

trap limpar_temporario EXIT INT TERM

pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --no-owner \
    --no-privileges \
    --file="$temporario/banco.dump"

tar -czf "$temporario/anexos.tar.gz" -C /dados/uploads .

(
    cd "$temporario"
    sha256sum banco.dump anexos.tar.gz > checksums.sha256
)

mv "$temporario" "$destino"
trap - EXIT INT TERM

echo "$destino"
