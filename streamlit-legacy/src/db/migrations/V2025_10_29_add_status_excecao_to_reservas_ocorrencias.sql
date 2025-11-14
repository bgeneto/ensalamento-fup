-- Add status_excecao column to reservas_ocorrencias table
-- This field stores exception status for individual occurrences (e.g., "Cancelada")

ALTER TABLE reservas_ocorrencias
ADD COLUMN status_excecao TEXT DEFAULT NULL;
