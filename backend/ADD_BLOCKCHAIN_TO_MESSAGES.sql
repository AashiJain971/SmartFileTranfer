-- Add blockchain and IPFS fields to messages table
-- Execute this in Supabase SQL Editor after CREATE_TABLE.sql

ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS blockchain_tx_hash VARCHAR(66),
ADD COLUMN IF NOT EXISTS blockchain_block_number BIGINT,
ADD COLUMN IF NOT EXISTS ipfs_cid VARCHAR(100),
ADD COLUMN IF NOT EXISTS certificate_url VARCHAR(500);

-- Add indexes for quick lookups
CREATE INDEX IF NOT EXISTS idx_messages_blockchain_tx ON messages(blockchain_tx_hash);
CREATE INDEX IF NOT EXISTS idx_messages_ipfs_cid ON messages(ipfs_cid);

-- Comments
COMMENT ON COLUMN messages.blockchain_tx_hash IS 'Blockchain transaction hash for file audit trail';
COMMENT ON COLUMN messages.blockchain_block_number IS 'Block number where transaction was recorded';
COMMENT ON COLUMN messages.ipfs_cid IS 'IPFS Content Identifier for decentralized storage';
COMMENT ON COLUMN messages.certificate_url IS 'URL to download blockchain proof certificate';
