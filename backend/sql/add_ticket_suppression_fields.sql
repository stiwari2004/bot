-- Add ticket suppression fields to tickets table
ALTER TABLE tickets 
ADD COLUMN IF NOT EXISTS suppressed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS suppressed_by_change_ticket_id INTEGER REFERENCES change_tickets(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS suppressed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS suppression_reason TEXT;

-- Create indexes for efficient suppression queries
CREATE INDEX IF NOT EXISTS idx_tickets_suppressed ON tickets(suppressed) 
    WHERE suppressed = TRUE;
CREATE INDEX IF NOT EXISTS idx_tickets_suppressed_by_change ON tickets(suppressed_by_change_ticket_id) 
    WHERE suppressed_by_change_ticket_id IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN tickets.suppressed IS 'Whether ticket is suppressed due to active change window';
COMMENT ON COLUMN tickets.suppressed_by_change_ticket_id IS 'Change ticket that caused suppression';
COMMENT ON COLUMN tickets.suppressed_at IS 'Timestamp when ticket was suppressed';
COMMENT ON COLUMN tickets.suppression_reason IS 'Reason for suppression (e.g., change window description)';

