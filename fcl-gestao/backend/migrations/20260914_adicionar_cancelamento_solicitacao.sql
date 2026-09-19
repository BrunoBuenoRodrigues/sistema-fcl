BEGIN;

ALTER TABLE solicitacao_compra
    ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT;

ALTER TABLE solicitacao_compra
    ADD COLUMN IF NOT EXISTS data_cancelamento TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE solicitacao_compra
    ADD COLUMN IF NOT EXISTS id_usuario_cancelamento INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_solicitacao_usuario_cancelamento'
    ) THEN
        ALTER TABLE solicitacao_compra
            ADD CONSTRAINT fk_solicitacao_usuario_cancelamento
            FOREIGN KEY (id_usuario_cancelamento)
            REFERENCES usuario(id_usuario);
    END IF;
END $$;

COMMIT;
