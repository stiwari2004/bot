-- Enable Row-Level Security for multi-tenant isolation
-- This ensures tenants can only access their own data

-- Enable RLS on all tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE runbooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audits ENABLE ROW LEVEL SECURITY;

-- Create a function to get current tenant_id from session
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS integer AS $$
BEGIN
    RETURN current_setting('app.current_tenant_id', true)::integer;
END;
$$ LANGUAGE plpgsql STABLE;

-- RLS Policies for users table
DROP POLICY IF EXISTS "Users can only see their own tenant's users" ON users;
CREATE POLICY "Users can only see their own tenant's users" ON users
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

-- RLS Policies for documents table
DROP POLICY IF EXISTS "Users can only see their own tenant's documents" ON documents;
CREATE POLICY "Users can only see their own tenant's documents" ON documents
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

-- RLS Policies for chunks table (via document relationship)
DROP POLICY IF EXISTS "Users can only see their own tenant's chunks" ON chunks;
CREATE POLICY "Users can only see their own tenant's chunks" ON chunks
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = chunks.document_id
            AND d.tenant_id = get_current_tenant_id()
        )
    );

-- RLS Policies for embeddings table (via chunk/document relationship)
DROP POLICY IF EXISTS "Users can only see their own tenant's embeddings" ON embeddings;
CREATE POLICY "Users can only see their own tenant's embeddings" ON embeddings
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id = embeddings.chunk_id
            AND d.tenant_id = get_current_tenant_id()
        )
    );

-- RLS Policies for runbooks table
DROP POLICY IF EXISTS "Users can only see their own tenant's runbooks" ON runbooks;
CREATE POLICY "Users can only see their own tenant's runbooks" ON runbooks
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

-- RLS Policies for executions table
DROP POLICY IF EXISTS "Users can only see their own tenant's executions" ON executions;
CREATE POLICY "Users can only see their own tenant's executions" ON executions
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

-- RLS Policies for audits table
DROP POLICY IF EXISTS "Users can only see their own tenant's audits" ON audits;
CREATE POLICY "Users can only see their own tenant's audits" ON audits
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

-- Create helper function to set tenant context
CREATE OR REPLACE FUNCTION set_tenant_context(tenant_id integer)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_tenant_id', tenant_id::text, false);
END;
$$ LANGUAGE plpgsql;

-- Grant execute on helper function
GRANT EXECUTE ON FUNCTION get_current_tenant_id() TO postgres;
GRANT EXECUTE ON FUNCTION set_tenant_context(integer) TO postgres;

-- Note: In the application, you would call set_tenant_context(tenant_id) 
-- at the start of each database session based on the authenticated user's tenant

