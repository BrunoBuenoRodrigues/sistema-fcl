BEGIN;

ALTER TABLE pedido_compra
    ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT;

ALTER TABLE pedido_compra
    ADD COLUMN IF NOT EXISTS data_cancelamento TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE pedido_compra
    ADD COLUMN IF NOT EXISTS id_usuario_cancelamento INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_pedido_usuario_cancelamento'
    ) THEN
        ALTER TABLE pedido_compra
            ADD CONSTRAINT fk_pedido_usuario_cancelamento
            FOREIGN KEY (id_usuario_cancelamento)
            REFERENCES usuario(id_usuario);
    END IF;
END $$;

COMMIT;
