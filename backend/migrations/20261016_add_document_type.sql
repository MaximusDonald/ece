-- Upgrade: persist the user-selected nature of each uploaded document.
ALTER TABLE document ADD COLUMN IF NOT EXISTS document_type VARCHAR(50);
