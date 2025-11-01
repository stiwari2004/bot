-- Migration script to upgrade embeddings from 384 to 1024 dimensions
-- Run this BEFORE changing the embedding model in config
-- This requires re-indexing all embeddings

-- Step 1: Alert operator that existing embeddings must be regenerated
DO $$
BEGIN
    RAISE NOTICE '⚠️  WARNING: This will invalidate all existing embeddings!';
    RAISE NOTICE '⚠️  You must run the reindex script after this migration!';
    RAISE NOTICE '⚠️  Continuing in 3 seconds...';
    PERFORM pg_sleep(3);
END $$;

-- Step 2: Drop existing embeddings table (keeping chunks)
-- We'll regenerate all embeddings with new model
TRUNCATE TABLE embeddings CASCADE;

-- Step 3: Drop and recreate index if it exists
DROP INDEX IF EXISTS idx_embeddings_vector_similarity;

-- Step 4: Add comment explaining dimensions
COMMENT ON TABLE embeddings IS 'Stores vector embeddings - now using 1024 dimensions (BAAI/bge-large-en-v1.5)';

-- Note: SQLAlchemy will recreate the table structure automatically
-- The important part is we've cleared old data

