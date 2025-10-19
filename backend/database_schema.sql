-- Database schema for Smart File Transfer System
-- Run these commands in your Supabase SQL editor

-- Create file_sessions table
CREATE TABLE IF NOT EXISTS file_sessions (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) UNIQUE NOT NULL,
    filename VARCHAR(500) NOT NULL,
    total_chunks INTEGER NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(128) NOT NULL,
    uploaded_chunks INTEGER DEFAULT 0,
    progress DECIMAL(5,2) DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'uploading',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create uploaded_chunks table
CREATE TABLE IF NOT EXISTS uploaded_chunks (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) NOT NULL,
    chunk_number INTEGER NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(file_id, chunk_number)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_file_sessions_file_id ON file_sessions(file_id);
CREATE INDEX IF NOT EXISTS idx_file_sessions_status ON file_sessions(status);
CREATE INDEX IF NOT EXISTS idx_uploaded_chunks_file_id ON uploaded_chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_chunks_file_chunk ON uploaded_chunks(file_id, chunk_number);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at on file_sessions
CREATE TRIGGER update_file_sessions_updated_at 
    BEFORE UPDATE ON file_sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();