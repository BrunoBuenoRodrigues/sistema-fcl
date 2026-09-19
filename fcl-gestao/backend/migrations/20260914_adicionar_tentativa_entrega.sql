BEGIN;

ALTER TABLE entrega
    ADD COLUMN IF NOT EXISTS motivo_nao_entrega TEXT;

ALTER TABLE entrega
    ADD COLUMN IF NOT EXISTS data_ultima_tentativa TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE entrega
    ADD COLUMN IF NOT EXISTS id_usuario_ultima_tentativa INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_entrega_usuario_ultima_tentativa'
    ) THEN
        ALTER TABLE entrega
            ADD CONSTRAINT fk_entrega_usuario_ultima_tentativa
            FOREIGN KEY (id_usuario_ultima_tentativa)
            REFERENCES usuario(id_usuario);
    END IF;
END $$;

COMMIT;
