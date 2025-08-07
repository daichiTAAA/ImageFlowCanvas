-- Initial database schema for ImageFlowCanvas Inspection

-- Users table for authentication
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'inspector',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inspection targets table
CREATE TABLE inspection_targets (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    qr_code TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inspection sessions table
CREATE TABLE inspection_sessions (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    user_id INTEGER,
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (target_id) REFERENCES inspection_targets(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Images table
CREATE TABLE inspection_images (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    image_type TEXT DEFAULT 'capture',
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES inspection_sessions(id)
);

-- AI inspection results table
CREATE TABLE ai_inspection_results (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    pipeline_version TEXT,
    overall_result TEXT NOT NULL,
    confidence REAL NOT NULL,
    processing_time REAL NOT NULL,
    detailed_results TEXT, -- JSON blob
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES inspection_sessions(id)
);

-- Human verification results table
CREATE TABLE human_verification_results (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    final_result TEXT NOT NULL,
    notes TEXT,
    verification_time REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES inspection_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- System configuration table
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default configuration
INSERT INTO system_config (key, value) VALUES 
    ('api_endpoint', 'https://api.imageflowcanvas.com'),
    ('offline_mode', 'true'),
    ('camera_resolution', '1920x1080'),
    ('ai_confidence_threshold', '0.8');

-- Create indexes for performance
CREATE INDEX idx_inspection_sessions_target_id ON inspection_sessions(target_id);
CREATE INDEX idx_inspection_sessions_user_id ON inspection_sessions(user_id);
CREATE INDEX idx_inspection_images_session_id ON inspection_images(session_id);
CREATE INDEX idx_ai_results_session_id ON ai_inspection_results(session_id);
CREATE INDEX idx_human_results_session_id ON human_verification_results(session_id);
CREATE INDEX idx_targets_product_id ON inspection_targets(product_id);
CREATE INDEX idx_targets_batch_id ON inspection_targets(batch_id);