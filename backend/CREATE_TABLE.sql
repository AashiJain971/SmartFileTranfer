-- ============================================
-- SMARTFILETRANSFER - BLOCKCHAIN RECORDS TABLE
-- ============================================
-- Copy and paste this ENTIRE file into Supabase SQL Editor
-- Then click "RUN" to create the table
-- ============================================

-- Create blockchain_records table
CREATE TABLE IF NOT EXISTS blockchain_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    block_number BIGINT NOT NULL,
    gas_used INTEGER NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_name TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    ipfs_cid VARCHAR(100),
    sender_id UUID NOT NULL,
    receiver_id UUID,
    network VARCHAR(50) DEFAULT 'Simulated Ethereum Sepolia',
    chain_id INTEGER DEFAULT 11155111,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_file_hash UNIQUE(file_hash)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_blockchain_tx_hash ON blockchain_records(tx_hash);
CREATE INDEX IF NOT EXISTS idx_blockchain_file_hash ON blockchain_records(file_hash);
CREATE INDEX IF NOT EXISTS idx_blockchain_sender ON blockchain_records(sender_id);
CREATE INDEX IF NOT EXISTS idx_blockchain_timestamp ON blockchain_records(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_blockchain_ipfs_cid ON blockchain_records(ipfs_cid);

-- Grant permissions
GRANT ALL ON blockchain_records TO authenticated;

-- Helper function: Get transaction by hash
CREATE OR REPLACE FUNCTION get_blockchain_transaction(tx_hash_param VARCHAR)
RETURNS TABLE (
    tx_hash VARCHAR,
    block_number BIGINT,
    file_hash VARCHAR,
    file_name TEXT,
    ipfs_cid VARCHAR,
    sender_id UUID,
    receiver_id UUID,
    tx_timestamp TIMESTAMPTZ,
    network VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        br.tx_hash,
        br.block_number,
        br.file_hash,
        br.file_name,
        br.ipfs_cid,
        br.sender_id,
        br.receiver_id,
        br.timestamp,
        br.network
    FROM blockchain_records br
    WHERE br.tx_hash = tx_hash_param;
END;
$$ LANGUAGE plpgsql;

-- Helper function: Get recent transactions
CREATE OR REPLACE FUNCTION get_recent_blockchain_transactions(limit_param INTEGER DEFAULT 10)
RETURNS TABLE (
    tx_hash VARCHAR,
    block_number BIGINT,
    file_name TEXT,
    file_size BIGINT,
    tx_timestamp TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        br.tx_hash,
        br.block_number,
        br.file_name,
        br.file_size,
        br.timestamp
    FROM blockchain_records br
    ORDER BY br.timestamp DESC
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- DONE! Table created successfully
-- ============================================
-- Test with: SELECT * FROM blockchain_records LIMIT 1;
-- ============================================
