#!/bin/sh
set -eu

diretorio="${1:-}"

case "$diretorio" in
    /backups/20??????T??????Z) ;;
    *)
        echo "Diretório de backup inválido." >&2
        exit 1
        ;;
esac

if [ ! -d "$diretorio" ]; then
    echo "Backup não encontrado: $diretorio" >&2
    exit 1
fi

(
    cd "$diretorio"
    sha256sum -c checksums.sha256
)

pg_restore \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    "$diretorio/banco.dump"

find /dados/uploads -mindepth 1 -delete
tar -xzf "$diretorio/anexos.tar.gz" -C /dados/uploads

echo "Backup restaurado: $diretorio"
