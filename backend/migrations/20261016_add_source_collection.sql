-- Upgrade: add source collection state and durable collection-run history.
ALTER TABLE legal_source ADD COLUMN IF NOT EXISTS collection_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE legal_source ADD COLUMN IF NOT EXISTS last_collection_at TIMESTAMP NULL;
ALTER TABLE legal_source ADD COLUMN IF NOT EXISTS last_successful_collection_at TIMESTAMP NULL;
ALTER TABLE legal_source ADD COLUMN IF NOT EXISTS last_collection_status VARCHAR(20) NULL;
ALTER TABLE legal_source ADD COLUMN IF NOT EXISTS last_collection_run_id UUID NULL;
ALTER TABLE legal_source ADD COLUMN IF NOT EXISTS source_etag VARCHAR(500) NULL;
ALTER TABLE legal_source ADD COLUMN IF NOT EXISTS source_last_modified VARCHAR(200) NULL;

CREATE TABLE IF NOT EXISTS source_collection_run (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL REFERENCES legal_source(id),
    trigger_type VARCHAR(20) NOT NULL,
    triggered_by UUID NULL REFERENCES "user"(id),
    status VARCHAR(20) NOT NULL,
    requested_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL,
    http_status_code INTEGER NULL,
    previous_hash VARCHAR(64) NULL,
    collected_hash VARCHAR(64) NULL,
    changed BOOLEAN NULL,
    error_message TEXT NULL
);
CREATE INDEX IF NOT EXISTS ix_source_collection_run_source_id ON source_collection_run(source_id);
CREATE INDEX IF NOT EXISTS ix_source_collection_run_status ON source_collection_run(status);
