FROM postgres:16-alpine

COPY monitorar.sh /scripts/monitorar.sh
RUN chmod +x /scripts/monitorar.sh

CMD ["/scripts/monitorar.sh"]
