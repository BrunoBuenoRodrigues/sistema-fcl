BEGIN;

UPDATE solicitacao_compra AS solicitacao
SET status = 'PEDIDO_REALIZADO'
WHERE solicitacao.status = 'APROVADA'
  AND EXISTS (
    SELECT 1
    FROM pedido_compra AS pedido
    WHERE pedido.id_solicitacao = solicitacao.id_solicitacao
  );

COMMIT;
