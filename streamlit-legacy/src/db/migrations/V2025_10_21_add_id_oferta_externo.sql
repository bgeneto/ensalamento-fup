-- Migration: Add id_oferta_externo to demandas and unique index per semestre

BEGIN TRANSACTION;

-- Add the column if it does not exist
ALTER TABLE demandas ADD COLUMN id_oferta_externo TEXT;

-- Create unique index to ensure idempotency: (semestre_id, id_oferta_externo)
CREATE UNIQUE INDEX IF NOT EXISTS ux_demandas_id_oferta_externo
ON demandas (id_oferta_externo);

COMMIT;
