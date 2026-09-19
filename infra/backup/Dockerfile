FROM postgres:16-alpine

COPY backup.sh restaurar.sh loop.sh /scripts/
RUN chmod +x /scripts/backup.sh /scripts/restaurar.sh /scripts/loop.sh

CMD ["/scripts/loop.sh"]
