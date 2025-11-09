// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title FileRegistry
 * @dev Smart contract for recording file transfers on Ethereum blockchain
 * @notice This contract provides immutable audit trail for file transfers
 */
contract FileRegistry {
    
    // Structure to store file transfer metadata
    struct FileTransfer {
        string fileHash;        // SHA-256 hash of the file
        string fileName;        // Original filename
        string senderId;        // Sender user ID
        string receiverId;      // Receiver user ID
        string ipfsCid;         // IPFS Content Identifier
        uint256 fileSize;       // File size in bytes
        uint256 timestamp;      // Block timestamp
        address recorder;       // Address that recorded the transfer
        bool exists;            // Flag to check if record exists
    }
    
    // Mapping: fileHash => FileTransfer details
    mapping(string => FileTransfer) public transfers;
    
    // Array to track all file hashes (for enumeration)
    string[] public fileHashes;
    
    // Mapping to track transfers by user
    mapping(string => string[]) public userTransfers; // userId => fileHashes[]
    
    // Event emitted when a transfer is recorded
    event TransferRecorded(
        string indexed fileHash,
        string fileName,
        string senderId,
        string receiverId,
        string ipfsCid,
        uint256 fileSize,
        uint256 timestamp,
        address recorder
    );
    
    // Event emitted when a transfer is verified
    event TransferVerified(
        string indexed fileHash,
        address verifier,
        uint256 timestamp
    );
    
    /**
     * @dev Record a new file transfer on the blockchain
     * @param _fileHash SHA-256 hash of the file
     * @param _fileName Original filename
     * @param _senderId Sender user ID
     * @param _receiverId Receiver user ID (can be room ID for group chats)
     * @param _ipfsCid IPFS Content Identifier
     * @param _fileSize File size in bytes
     */
    function recordTransfer(
        string memory _fileHash,
        string memory _fileName,
        string memory _senderId,
        string memory _receiverId,
        string memory _ipfsCid,
        uint256 _fileSize
    ) public {
        require(bytes(_fileHash).length > 0, "File hash cannot be empty");
        require(bytes(_fileName).length > 0, "File name cannot be empty");
        require(bytes(_senderId).length > 0, "Sender ID cannot be empty");
        require(_fileSize > 0, "File size must be greater than 0");
        
        // Check if transfer already exists (prevent duplicates)
        require(!transfers[_fileHash].exists, "Transfer already recorded");
        
        // Create new transfer record
        transfers[_fileHash] = FileTransfer({
            fileHash: _fileHash,
            fileName: _fileName,
            senderId: _senderId,
            receiverId: _receiverId,
            ipfsCid: _ipfsCid,
            fileSize: _fileSize,
            timestamp: block.timestamp,
            recorder: msg.sender,
            exists: true
        });
        
        // Add to global list
        fileHashes.push(_fileHash);
        
        // Track sender's transfers
        userTransfers[_senderId].push(_fileHash);
        
        // Track receiver's transfers (if different from sender)
        if (keccak256(bytes(_senderId)) != keccak256(bytes(_receiverId))) {
            userTransfers[_receiverId].push(_fileHash);
        }
        
        // Emit event
        emit TransferRecorded(
            _fileHash,
            _fileName,
            _senderId,
            _receiverId,
            _ipfsCid,
            _fileSize,
            block.timestamp,
            msg.sender
        );
    }
    
    /**
     * @dev Get transfer details by file hash
     * @param _fileHash SHA-256 hash of the file
     * @return FileTransfer struct with all details
     */
    function getTransfer(string memory _fileHash) 
        public 
        view 
        returns (FileTransfer memory) 
    {
        require(transfers[_fileHash].exists, "Transfer not found");
        return transfers[_fileHash];
    }
    
    /**
     * @dev Check if a transfer exists
     * @param _fileHash SHA-256 hash of the file
     * @return bool true if transfer exists
     */
    function transferExists(string memory _fileHash) 
        public 
        view 
        returns (bool) 
    {
        return transfers[_fileHash].exists;
    }
    
    /**
     * @dev Get total number of recorded transfers
     * @return uint256 total count
     */
    function getTotalTransfers() public view returns (uint256) {
        return fileHashes.length;
    }
    
    /**
     * @dev Get transfers for a specific user
     * @param _userId User ID to query
     * @return string[] array of file hashes
     */
    function getUserTransfers(string memory _userId) 
        public 
        view 
        returns (string[] memory) 
    {
        return userTransfers[_userId];
    }
    
    /**
     * @dev Get paginated list of all transfers
     * @param _offset Starting index
     * @param _limit Number of records to return
     * @return string[] array of file hashes
     */
    function getTransfersPaginated(uint256 _offset, uint256 _limit) 
        public 
        view 
        returns (string[] memory) 
    {
        require(_offset < fileHashes.length, "Offset out of bounds");
        
        uint256 end = _offset + _limit;
        if (end > fileHashes.length) {
            end = fileHashes.length;
        }
        
        string[] memory result = new string[](end - _offset);
        for (uint256 i = _offset; i < end; i++) {
            result[i - _offset] = fileHashes[i];
        }
        
        return result;
    }
    
    /**
     * @dev Verify a transfer (can be called by anyone to confirm)
     * @param _fileHash SHA-256 hash of the file to verify
     */
    function verifyTransfer(string memory _fileHash) public {
        require(transfers[_fileHash].exists, "Transfer not found");
        
        emit TransferVerified(
            _fileHash,
            msg.sender,
            block.timestamp
        );
    }
    
    /**
     * @dev Get contract version
     * @return string version number
     */
    function version() public pure returns (string memory) {
        return "1.0.0";
    }
}
