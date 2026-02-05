-- Migration: Create inquiries table for trial intake submissions
-- Idempotent - safe to run multiple times

CREATE TABLE IF NOT EXISTS inquiries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    company VARCHAR(255),
    company_size VARCHAR(50),
    infrastructure_type VARCHAR(50),
    itsm_tools TEXT,
    monitoring_tools TEXT,
    top_incident_pain VARCHAR(100),
    node_count_estimate VARCHAR(50),
    status VARCHAR(50) DEFAULT 'new',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_inquiries_email ON inquiries(email);
CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status);
CREATE INDEX IF NOT EXISTS idx_inquiries_created_at ON inquiries(created_at DESC);

COMMENT ON TABLE inquiries IS 'Trial intake submissions from marketing site book-pilot form';
