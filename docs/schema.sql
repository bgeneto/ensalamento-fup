-- Ativa o suporte a chaves estrangeiras no SQLite.
PRAGMA foreign_keys = ON;

-- ---
-- 1. ESTRUTURA FÍSICA (Inventário)
-- ---

CREATE TABLE IF NOT EXISTS campus (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS predios (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    campus_id INTEGER NOT NULL,
    FOREIGN KEY (campus_id) REFERENCES campus (id)
);

CREATE TABLE IF NOT EXISTS tipos_sala (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS salas (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL, -- (Ex: "A1-09/9", "AT-53/26")
    predio_id INTEGER NOT NULL,
    tipo_sala_id INTEGER NOT NULL,
    capacidade INTEGER DEFAULT 0,
    andar TEXT,
    tipo_assento TEXT,

    UNIQUE (nome, predio_id),
    FOREIGN KEY (predio_id) REFERENCES predios (id),
    FOREIGN KEY (tipo_sala_id) REFERENCES tipos_sala (id)
);

CREATE TABLE IF NOT EXISTS caracteristicas (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS sala_caracteristicas (
    sala_id INTEGER NOT NULL,
    caracteristica_id INTEGER NOT NULL,
    PRIMARY KEY (sala_id, caracteristica_id),
    FOREIGN KEY (sala_id) REFERENCES salas (id) ON DELETE CASCADE,
    FOREIGN KEY (caracteristica_id) REFERENCES caracteristicas (id) ON DELETE CASCADE
);

-- ---
-- 2. DEFINIÇÃO DE HORÁRIOS (Sigaa)
-- ---

-- Tabela para os dias da semana (Sigaa)
CREATE TABLE IF NOT EXISTS dias_semana (
    id_sigaa INTEGER PRIMARY KEY, -- (2=SEG, 3=TER, ...)
    nome TEXT NOT NULL UNIQUE -- (Ex: "SEG", "TER")
);

-- Tabela para os blocos de horário ATÔMICOS (Sigaa)
CREATE TABLE IF NOT EXISTS horarios_bloco (
    codigo_bloco TEXT PRIMARY KEY, -- (Ex: "M1", "M2", "T1", "N1")
    turno TEXT NOT NULL, -- (Ex: "M", "T", "N")
    horario_inicio TIME NOT NULL,
    horario_fim TIME NOT NULL
);

-- ---
-- 3. ENSALAMENTO SEMESTRAL (Motor de Alocação)
-- ---

CREATE TABLE IF NOT EXISTS semestres (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE, -- (Ex: "2025.1", "2025.2")
    status TEXT DEFAULT 'Planejamento'
);

-- Dados brutos importados da API (RF-004)
CREATE TABLE IF NOT EXISTS demandas (
    id INTEGER PRIMARY KEY,
    semestre_id INTEGER NOT NULL,
    codigo_disciplina TEXT NOT NULL,
    nome_disciplina TEXT,
    professores_disciplina TEXT,
    turma_disciplina TEXT,
    vagas_disciplina INTEGER,

    -- O código Sigaa bruto (Ex: "24M12 6T34")
    horario_sigaa_bruto TEXT NOT NULL,

    nivel_disciplina TEXT,

    FOREIGN KEY (semestre_id) REFERENCES semestres (id)
);

CREATE TABLE IF NOT EXISTS regras (
    id INTEGER PRIMARY KEY,
    descricao TEXT NOT NULL,
    tipo_regra TEXT NOT NULL,
    config_json TEXT NOT NULL,
    prioridade INTEGER DEFAULT 1
);

-- Resultado do Motor de Alocação (RF-006)
-- Esta tabela armazena os blocos atômicos alocados
CREATE TABLE IF NOT EXISTS alocacoes_semestrais (
    id INTEGER PRIMARY KEY,
    demanda_id INTEGER NOT NULL,
    sala_id INTEGER NOT NULL,
    dia_semana_id INTEGER NOT NULL, -- (FK para dias_semana.id_sigaa)
    codigo_bloco TEXT NOT NULL, -- (FK para horarios_bloco.codigo_bloco)

    -- Chave de verificação de conflito para alocações semestrais
    UNIQUE (semestre_id, sala_id, dia_semana_id, codigo_bloco)
        REFERENCES semestres(id), -- Incluído para permitir que a chave única seja por semestre

    FOREIGN KEY (demanda_id) REFERENCES demandas (id) ON DELETE CASCADE,
    FOREIGN KEY (sala_id) REFERENCES salas (id),
    FOREIGN KEY (dia_semana_id) REFERENCES dias_semana (id_sigaa),
    FOREIGN KEY (codigo_bloco) REFERENCES horarios_bloco (codigo_bloco)
);

-- ---
-- 4. RESERVAS ESPORÁDICAS (Manual)
-- ---

-- Tabela para reservas avulsas (RF-011)
-- Armazena por data específica + bloco atômico
CREATE TABLE IF NOT EXISTS reservas_esporadicas (
    id INTEGER PRIMARY KEY,
    sala_id INTEGER NOT NULL,
    username_solicitante TEXT NOT NULL,
    titulo_evento TEXT NOT NULL,
    data_reserva DATE NOT NULL, -- (Ex: "2025-10-30")
    codigo_bloco TEXT NOT NULL, -- (FK para horarios_bloco.codigo_bloco)
    status TEXT DEFAULT 'Aprovada',

    -- Chave de verificação de conflito para reservas esporádicas
    UNIQUE (sala_id, data_reserva, codigo_bloco),

    FOREIGN KEY (sala_id) REFERENCES salas (id),
    FOREIGN KEY (username_solicitante) REFERENCES usuarios (username),
    FOREIGN KEY (codigo_bloco) REFERENCES horarios_bloco (codigo_bloco)
);


-- ---
-- 5. AUTENTICAÇÃO
-- ---

CREATE TABLE IF NOT EXISTS usuarios (
    username TEXT PRIMARY KEY NOT NULL,
    password_hash TEXT NOT NULL,
    nome_completo TEXT,
    role TEXT DEFAULT 'professor' -- (Ex: "admin", "professor")
);