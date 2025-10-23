-- Database schema for Smart File Transfer System with Authentication
-- Run these commands in your Supabase SQL editor

-- Create users table (if using custom user management)
-- Note: If using Supabase Auth, this table is created automatically as auth.users
-- This is for additional user profile information
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create user_sessions table for JWT session management
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(500) UNIQUE NOT NULL,
    refresh_token VARCHAR(500),
    expires_at TIMESTAMP NOT NULL,
    device_info VARCHAR(255),
    ip_address VARCHAR(45),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP DEFAULT NOW()
);

-- Create password_reset_tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    token VARCHAR(255),
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create file_sessions table (updated with user relationship)
CREATE TABLE IF NOT EXISTS file_sessions (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- ✅ LINK TO USER
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
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh_token ON user_sessions(refresh_token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_file_sessions_file_id ON file_sessions(file_id);
CREATE INDEX IF NOT EXISTS idx_file_sessions_user_id ON file_sessions(user_id);  -- ✅ INDEX FOR USER QUERIES
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

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_sessions_updated_at 
    BEFORE UPDATE ON file_sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Disable RLS for development (since we're using custom auth, not Supabase Auth)
-- In production, you might want to enable RLS with proper service role policies
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens DISABLE ROW LEVEL SECURITY;
ALTER TABLE file_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_chunks DISABLE ROW LEVEL SECURITY;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;