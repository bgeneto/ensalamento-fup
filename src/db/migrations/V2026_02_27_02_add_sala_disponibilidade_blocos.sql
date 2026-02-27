CREATE TABLE IF NOT EXISTS sala_disponibilidade_blocos (
    id INTEGER PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sala_id INTEGER NOT NULL,
    codigo_bloco TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    CONSTRAINT ux_sala_disponibilidade_bloco UNIQUE (sala_id, codigo_bloco),
    FOREIGN KEY (sala_id) REFERENCES salas (id) ON DELETE CASCADE,
    FOREIGN KEY (codigo_bloco) REFERENCES horarios_bloco (codigo_bloco)
);

INSERT OR IGNORE INTO sala_disponibilidade_blocos (sala_id, codigo_bloco, enabled)
SELECT s.id, hb.codigo_bloco, 1
FROM salas s
CROSS JOIN horarios_bloco hb;
