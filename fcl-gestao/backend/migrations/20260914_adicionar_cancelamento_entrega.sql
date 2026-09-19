BEGIN;

ALTER TABLE entrega
    ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT;

ALTER TABLE entrega
    ADD COLUMN IF NOT EXISTS data_cancelamento TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE entrega
    ADD COLUMN IF NOT EXISTS id_usuario_cancelamento INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_entrega_usuario_cancelamento'
    ) THEN
        ALTER TABLE entrega
            ADD CONSTRAINT fk_entrega_usuario_cancelamento
            FOREIGN KEY (id_usuario_cancelamento)
            REFERENCES usuario(id_usuario);
    END IF;
END $$;

COMMIT;
