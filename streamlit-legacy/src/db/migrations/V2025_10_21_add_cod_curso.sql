-- Migration: Add id_oferta_externo to demandas and unique index per semestre

BEGIN TRANSACTION;

-- Add the column if it does not exist
ALTER TABLE demandas ADD COLUMN codigo_curso TEXT;

COMMIT;
