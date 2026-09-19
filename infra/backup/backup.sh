#!/bin/sh
set -eu

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
temporario="/backups/.tmp-${timestamp}"
destino="/backups/${timestamp}"
retencao_dias="${BACKUP_RETENCAO_DIAS:-30}"

case "$retencao_dias" in
    ''|*[!0-9]*|0)
        echo "BACKUP_RETENCAO_DIAS deve ser um número inteiro maior que zero." >&2
        exit 1
        ;;
esac

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

find /backups \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -name '20??????T??????Z' \
    -mtime "+$retencao_dias" \
    -exec rm -rf -- {} +

echo "$destino"
