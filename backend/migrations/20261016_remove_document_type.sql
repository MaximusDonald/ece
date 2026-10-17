-- Downgrade: remove the optional document nature field.
ALTER TABLE document DROP COLUMN IF EXISTS document_type;
