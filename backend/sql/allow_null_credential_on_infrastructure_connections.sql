-- Allow infrastructure_connections.credential_id to be NULL so nodes can be
-- created from Discovery without a pre-existing SSH/infrastructure credential.
-- Users can add or change the credential later in Settings & Connections.
ALTER TABLE infrastructure_connections
  ALTER COLUMN credential_id DROP NOT NULL;
