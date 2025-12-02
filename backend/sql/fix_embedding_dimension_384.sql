-- Fix embedding dimension mismatch
-- The database column was created with 1024 dimensions, but the model produces 384
-- This script updates the column to match the actual model being used

-- Step 1: Drop existing embeddings (they're incompatible)
-- Note: This will delete all existing embeddings - they'll be regenerated on next index
DO $$
BEGIN
    RAISE NOTICE '⚠️  WARNING: This will delete all existing embeddings!';
    RAISE NOTICE '⚠️  Embeddings will be regenerated automatically when runbooks are indexed.';
    RAISE NOTICE '⚠️  Continuing in 3 seconds...';
    PERFORM pg_sleep(3);
END $$;

-- Step 2: Delete all existing embeddings (they have wrong dimension)
TRUNCATE TABLE embeddings CASCADE;

-- Step 3: Drop the existing column
ALTER TABLE embeddings DROP COLUMN IF EXISTS embedding;

-- Step 4: Recreate column with correct dimension (384)
ALTER TABLE embeddings ADD COLUMN embedding vector(384) NOT NULL;

-- Step 5: Drop and recreate index if it exists
DROP INDEX IF EXISTS idx_embeddings_vector_similarity;
DROP INDEX IF EXISTS embeddings_embedding_idx;

-- Step 6: Add comment
COMMENT ON COLUMN embeddings.embedding IS 'Vector embedding - 384 dimensions (sentence-transformers/all-MiniLM-L6-v2)';

-- Step 7: Create new index for 384-dimensional vectors
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx 
ON embeddings USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Note: After running this, you may need to reindex runbooks
-- The embeddings will be regenerated automatically when runbooks are approved/indexed


