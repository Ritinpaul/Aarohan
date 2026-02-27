-- ================================================================
-- Aarohan++ Database Initialisation
-- Creates additional databases needed by the stack
-- ================================================================

-- Create the HAPI FHIR database
CREATE DATABASE hapi_fhir;

-- Create tables for mapping templates
CREATE TABLE IF NOT EXISTS mapping_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_format VARCHAR(50) NOT NULL,
    target_profile VARCHAR(255) NOT NULL,
    mappings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create tables for audit trail
CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    pipeline_id UUID NOT NULL,
    layer VARCHAR(50) NOT NULL,
    input_hash VARCHAR(64),
    output_hash VARCHAR(64),
    details JSONB NOT NULL DEFAULT '{}',
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for audit queries
CREATE INDEX IF NOT EXISTS idx_audit_pipeline ON audit_events(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);

-- Create tables for conversion history
CREATE TABLE IF NOT EXISTS conversion_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_filename VARCHAR(255),
    source_format VARCHAR(50),
    target_profile VARCHAR(255),
    target_network VARCHAR(50),
    readiness_score FLOAT,
    status VARCHAR(50) DEFAULT 'pending',
    context JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
