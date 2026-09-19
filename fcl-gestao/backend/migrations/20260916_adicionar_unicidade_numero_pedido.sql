BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_pedido_compra_numero_pedido'
          AND conrelid = 'pedido_compra'::regclass
    ) THEN
        ALTER TABLE pedido_compra
            ADD CONSTRAINT uq_pedido_compra_numero_pedido
            UNIQUE (numero_pedido);
    END IF;
END $$;

COMMIT;
