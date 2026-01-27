#!/bin/bash
# Quick fix for orphaned sequence issue - run this on the server
# This fixes the database directly, then you can pull code and rebuild

echo "=== Fixing orphaned sequence in production database ==="

# Connect to postgres and drop the orphaned sequence
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "
DO \$\$
BEGIN
    -- Check if sequence exists but table doesn't
    IF EXISTS (
        SELECT 1 FROM pg_class 
        WHERE relname = 'parameter_tunings_id_seq' 
        AND relkind = 'S'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_class 
        WHERE relname = 'parameter_tunings' 
        AND relkind = 'r'
    ) THEN
        -- Drop orphaned sequence
        DROP SEQUENCE IF EXISTS parameter_tunings_id_seq CASCADE;
        RAISE NOTICE 'Dropped orphaned sequence parameter_tunings_id_seq';
    ELSE
        RAISE NOTICE 'Sequence/table state is normal, no action needed';
    END IF;
END
\$\$;
"

echo ""
echo "=== Sequence fix complete ==="
echo "Now restart the backend:"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod restart backend"
