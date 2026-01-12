-- Infrastructure Provisioning Schema
-- Create tables for infrastructure provisioning projects, resources, and templates

-- Infrastructure provisioning projects
CREATE TABLE IF NOT EXISTS provisioning_projects (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    provider VARCHAR(50) NOT NULL,  -- aws, azure, gcp, terraform
    template_id INTEGER,
    state VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, provisioning, active, failed, destroyed
    terraform_state JSONB,
    variables JSONB,
    outputs JSONB,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    destroyed_at TIMESTAMP WITH TIME ZONE
);

-- Provisioned resources
CREATE TABLE IF NOT EXISTS provisioned_resources (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES provisioning_projects(id) ON DELETE CASCADE,
    resource_type VARCHAR(100) NOT NULL,  -- instance, network, load_balancer, etc.
    resource_id VARCHAR(255) NOT NULL,  -- Cloud provider resource ID
    name VARCHAR(255),
    provider VARCHAR(50) NOT NULL,
    region VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Infrastructure templates
CREATE TABLE IF NOT EXISTS infrastructure_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    provider VARCHAR(50) NOT NULL,
    template_type VARCHAR(50),  -- server, web_app, kubernetes, network
    template_content TEXT NOT NULL,  -- Terraform/CloudFormation/Ansible code
    variables_schema JSONB,
    is_public BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_provisioning_projects_tenant ON provisioning_projects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_provisioning_projects_state ON provisioning_projects(state);
CREATE INDEX IF NOT EXISTS idx_provisioning_projects_provider ON provisioning_projects(provider);
CREATE INDEX IF NOT EXISTS idx_provisioned_resources_project ON provisioned_resources(project_id);
CREATE INDEX IF NOT EXISTS idx_provisioned_resources_type ON provisioned_resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_infrastructure_templates_tenant ON infrastructure_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_infrastructure_templates_provider ON infrastructure_templates(provider);
CREATE INDEX IF NOT EXISTS idx_infrastructure_templates_type ON infrastructure_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_infrastructure_templates_public ON infrastructure_templates(is_public) WHERE is_public = TRUE;

-- Comments for documentation
COMMENT ON TABLE provisioning_projects IS 'Tracks infrastructure provisioning projects and their state';
COMMENT ON TABLE provisioned_resources IS 'Tracks individual resources created by provisioning projects';
COMMENT ON TABLE infrastructure_templates IS 'Stores reusable infrastructure templates (Terraform, CloudFormation, Ansible)';

