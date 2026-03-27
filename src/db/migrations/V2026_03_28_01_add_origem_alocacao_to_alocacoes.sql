-- Migration: track whether semester allocations were created manually or autonomously

BEGIN TRANSACTION;

ALTER TABLE alocacoes_semestrais
ADD COLUMN origem_alocacao TEXT NOT NULL DEFAULT 'autonoma';

UPDATE alocacoes_semestrais
SET origem_alocacao = 'autonoma'
WHERE origem_alocacao IS NULL OR TRIM(origem_alocacao) = '';

COMMIT;
