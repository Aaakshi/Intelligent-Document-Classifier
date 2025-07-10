
-- Create UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_name VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    doc_type VARCHAR(50),
    confidence FLOAT,
    file_size BIGINT,
    mime_type VARCHAR(100),
    content_hash VARCHAR(64),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metadata table
CREATE TABLE metadata (
    id SERIAL PRIMARY KEY,
    doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    key_entities JSONB,
    related_docs UUID[],
    risk_score FLOAT,
    summary TEXT,
    language VARCHAR(10),
    sentiment_score FLOAT,
    topics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    department VARCHAR(100),
    skills JSONB,
    workload_capacity INTEGER DEFAULT 10,
    timezone VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Routing rules table
CREATE TABLE routing_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    condition JSONB NOT NULL,
    assignee VARCHAR(100),
    team VARCHAR(100),
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document assignments table
CREATE TABLE document_assignments (
    id SERIAL PRIMARY KEY,
    doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    assigned_by VARCHAR(100),
    status VARCHAR(50) DEFAULT 'assigned',
    priority INTEGER DEFAULT 1,
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES users(id),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Web scraping sources table
CREATE TABLE scraping_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    source_type VARCHAR(50),
    scraping_rules JSONB,
    last_scraped TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraped content table
CREATE TABLE scraped_content (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES scraping_sources(id),
    url TEXT NOT NULL,
    title VARCHAR(500),
    content TEXT,
    content_hash VARCHAR(64),
    metadata JSONB,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin user
INSERT INTO users (username, email, full_name, role) 
VALUES ('admin', 'admin@company.com', 'Administrator', 'admin');

-- Insert default routing rules
INSERT INTO routing_rules (name, condition, assignee, priority) VALUES
('Contract Documents', '{"doc_type": "contract"}', 'legal-team', 1),
('Invoice Processing', '{"doc_type": "invoice"}', 'finance-team', 2),
('HR Documents', '{"doc_type": "hr"}', 'hr-team', 1),
('Technical Reports', '{"doc_type": "report", "category": "technical"}', 'engineering-team', 2);

-- Create indexes for better performance
CREATE INDEX idx_documents_doc_type ON documents(doc_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_metadata_doc_id ON metadata(doc_id);
CREATE INDEX idx_document_assignments_user_id ON document_assignments(user_id);
CREATE INDEX idx_document_assignments_status ON document_assignments(status);
CREATE INDEX idx_audit_logs_entity_type ON audit_logs(entity_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
