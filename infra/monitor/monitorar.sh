#!/bin/sh
set -u

intervalo_minutos="${MONITOR_INTERVALO_MINUTOS:-5}"
backup_max_horas="${BACKUP_MAX_IDADE_HORAS:-26}"

validar_inteiro_positivo() {
    nome="$1"
    valor="$2"

    case "$valor" in
        ''|*[!0-9]*|0)
            echo "$nome deve ser um número inteiro maior que zero." >&2
            exit 1
            ;;
    esac
}

validar_inteiro_positivo "MONITOR_INTERVALO_MINUTOS" "$intervalo_minutos"
validar_inteiro_positivo "BACKUP_MAX_IDADE_HORAS" "$backup_max_horas"

verificar_backup() {
    backup_recente="$(
        find /backups \
            -mindepth 1 \
            -maxdepth 1 \
            -type d \
            -name '20??????T??????Z' \
            -print |
            sort |
            tail -n 1
    )"

    [ -n "$backup_recente" ] || return 1
    [ -s "$backup_recente/banco.dump" ] || return 1
    [ -s "$backup_recente/anexos.tar.gz" ] || return 1
    [ -s "$backup_recente/checksums.sha256" ] || return 1

    agora="$(date +%s)"
    modificado="$(stat -c %Y "$backup_recente")"
    idade_segundos="$((agora - modificado))"
    limite_segundos="$((backup_max_horas * 3600))"

    [ "$idade_segundos" -le "$limite_segundos" ] || return 1

    (
        cd "$backup_recente" || exit 1
        sha256sum -c checksums.sha256 >/dev/null 2>&1
    )
}

verificar() {
    instante="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    falhas=""

    if ! [ "$(wget -qO- -T 10 http://frontend/nginx-health 2>/dev/null)" = "ok" ]; then
        falhas="$falhas frontend"
    fi

    if ! wget -qO- -T 10 http://backend:8000/health 2>/dev/null | grep -q '"status":"ok"'; then
        falhas="$falhas backend-ou-banco"
    fi

    if ! verificar_backup; then
        falhas="$falhas backup"
    fi

    if [ -n "$falhas" ]; then
        rm -f /tmp/monitor-ok
        echo "[$instante] FALHA:$falhas" >&2
        return 1
    fi

    date +%s > /tmp/monitor-ok
    echo "[$instante] OK: frontend, backend, banco e backup"
}

while true; do
    verificar || true
    sleep "$((intervalo_minutos * 60))"
done
