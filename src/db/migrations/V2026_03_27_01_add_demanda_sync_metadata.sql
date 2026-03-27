-- Migration: add sync metadata fields to demandas for API reconciliation support

BEGIN TRANSACTION;

ALTER TABLE demandas ADD COLUMN origem TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE demandas ADD COLUMN sync_status TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE demandas ADD COLUMN api_payload_hash TEXT;
ALTER TABLE demandas ADD COLUMN api_snapshot_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE demandas ADD COLUMN local_overrides_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE demandas ADD COLUMN last_seen_in_api_at DATETIME;
ALTER TABLE demandas ADD COLUMN last_synced_at DATETIME;
ALTER TABLE demandas ADD COLUMN removed_from_api_at DATETIME;
ALTER TABLE demandas ADD COLUMN preservar_local_em_remocao_api BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE demandas ADD COLUMN revalidation_required BOOLEAN NOT NULL DEFAULT 0;

UPDATE demandas
SET origem = CASE
    WHEN id_oferta_externo IS NULL OR TRIM(id_oferta_externo) = '' THEN 'manual'
    ELSE 'api'
END;

UPDATE demandas
SET sync_status = CASE
    WHEN origem = 'api' THEN 'active'
    ELSE 'manual'
END;

UPDATE demandas
SET api_snapshot_json = json_object(
    'codigo_curso', COALESCE(codigo_curso, ''),
    'codigo_disciplina', COALESCE(codigo_disciplina, ''),
    'nome_disciplina', COALESCE(nome_disciplina, ''),
    'turma_disciplina', COALESCE(turma_disciplina, ''),
    'vagas_disciplina', COALESCE(vagas_disciplina, 0),
    'professores_disciplina', COALESCE(professores_disciplina, ''),
    'horario_sigaa_bruto', COALESCE(horario_sigaa_bruto, '')
)
WHERE origem = 'api';

UPDATE demandas
SET last_seen_in_api_at = CURRENT_TIMESTAMP,
    last_synced_at = CURRENT_TIMESTAMP
WHERE origem = 'api';

COMMIT;