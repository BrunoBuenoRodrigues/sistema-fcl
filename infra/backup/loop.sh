#!/bin/sh
set -eu

intervalo_horas="${BACKUP_INTERVALO_HORAS:-24}"

case "$intervalo_horas" in
    ''|*[!0-9]*|0)
        echo "BACKUP_INTERVALO_HORAS deve ser um número inteiro maior que zero." >&2
        exit 1
        ;;
esac

while true; do
    if ! /scripts/backup.sh; then
        echo "Falha ao executar o backup automático." >&2
    fi

    sleep "$((intervalo_horas * 3600))"
done
