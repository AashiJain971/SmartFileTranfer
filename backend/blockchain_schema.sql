-- Blockchain Records Table (Mock Blockchain Storage)
-- This stores simulated blockchain transaction records
-- All records are stored in Supabase instead of real Ethereum

CREATE TABLE IF NOT EXISTS blockchain_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Transaction details
    tx_hash VARCHAR(66) UNIQUE NOT NULL,  -- Ethereum-style transaction hash (0x...)
    block_number BIGINT NOT NULL,         -- Simulated block number
    gas_used INTEGER NOT NULL,            -- Simulated gas used
    
    -- File details
    file_hash VARCHAR(64) NOT NULL,       -- SHA-256 hash of file
    file_name TEXT NOT NULL,              -- Original filename
    file_size BIGINT NOT NULL,            -- File size in bytes
    
    -- IPFS details (REAL!)
    ipfs_cid VARCHAR(100),                -- Real Pinata IPFS CID
    
    -- Transfer details
    sender_id UUID NOT NULL,              -- User who uploaded
    receiver_id UUID,                     -- Room ID or recipient
    
    -- Network details
    network VARCHAR(50) DEFAULT 'Simulated Ethereum Sepolia',
    chain_id INTEGER DEFAULT 11155111,    -- Sepolia chain ID
    
    -- Timestamps
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for fast queries
    CONSTRAINT unique_file_hash UNIQUE(file_hash)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_blockchain_tx_hash ON blockchain_records(tx_hash);
CREATE INDEX IF NOT EXISTS idx_blockchain_file_hash ON blockchain_records(file_hash);
CREATE INDEX IF NOT EXISTS idx_blockchain_sender ON blockchain_records(sender_id);
CREATE INDEX IF NOT EXISTS idx_blockchain_timestamp ON blockchain_records(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_blockchain_ipfs_cid ON blockchain_records(ipfs_cid);

-- Comments for documentation
COMMENT ON TABLE blockchain_records IS 'Mock blockchain records for file transfer audit trail';
COMMENT ON COLUMN blockchain_records.tx_hash IS 'Simulated Ethereum transaction hash';
COMMENT ON COLUMN blockchain_records.ipfs_cid IS 'Real IPFS CID from Pinata';
COMMENT ON COLUMN blockchain_records.network IS 'Network name (simulated)';

-- Grant permissions
GRANT ALL ON blockchain_records TO authenticated;

-- Function to get transaction by hash
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

-- Function to get recent transactions
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
