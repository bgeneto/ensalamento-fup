CREATE TABLE IF NOT EXISTS app_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL DEFAULT '1',
    overrides_json TEXT NOT NULL DEFAULT '{}',
    defaults_revision TEXT,
    updated_by TEXT,
    change_reason TEXT,
    source TEXT NOT NULL DEFAULT 'ui',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES usuarios (username)
);

CREATE TABLE IF NOT EXISTS app_configuration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1',
    overrides_json TEXT NOT NULL DEFAULT '{}',
    effective_config_json TEXT NOT NULL DEFAULT '{}',
    changed_by TEXT,
    change_reason TEXT,
    source TEXT NOT NULL DEFAULT 'ui',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (changed_by) REFERENCES usuarios (username)
);

CREATE INDEX IF NOT EXISTS ix_app_configuration_history_key_created_at
ON app_configuration_history (config_key, created_at DESC);
