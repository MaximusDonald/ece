-- Downgrade: this removes collection logs and collection metadata.
DROP TABLE IF EXISTS source_collection_run;
ALTER TABLE legal_source DROP COLUMN IF EXISTS collection_enabled;
ALTER TABLE legal_source DROP COLUMN IF EXISTS last_collection_at;
ALTER TABLE legal_source DROP COLUMN IF EXISTS last_successful_collection_at;
ALTER TABLE legal_source DROP COLUMN IF EXISTS last_collection_status;
ALTER TABLE legal_source DROP COLUMN IF EXISTS last_collection_run_id;
ALTER TABLE legal_source DROP COLUMN IF EXISTS source_etag;
ALTER TABLE legal_source DROP COLUMN IF EXISTS source_last_modified;
