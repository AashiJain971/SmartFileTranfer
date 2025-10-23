'use client';

import { useState, useCallback } from 'react';
import { FileUploadAPI } from '../utils/api';
import { calculateSHA256, calculateChunkSHA256, createChunks, formatFileSize } from '../utils/fileUtils';
import { useWebSocket } from '../hooks/useWebSocket';
import FileDropZone from './FileDropZone';
import ProgressBar from './ProgressBar';
import LogViewer from './LogViewer';

export default function FileUploader() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadState, setUploadState] = useState('idle'); // idle, preparing, uploading, completed, error
  const [progress, setProgress] = useState(0);
  const [uploadStats, setUploadStats] = useState({
    uploadedChunks: 0,
    totalChunks: 0,
    fileId: null,
    fileName: null,
    fileSize: 0
  });
  const [error, setError] = useState(null);
  const [chunkSize, setChunkSize] = useState(1048576); // 1MB default

  // WebSocket connection
  const { messages, connectionStatus, clearMessages } = useWebSocket(uploadStats.fileId);

  const handleFileSelect = useCallback((file) => {
    setSelectedFile(file);
    setError(null);
    setProgress(0);
    setUploadState('idle');
    clearMessages();
  }, [clearMessages]);

  const startUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploadState('preparing');
      setError(null);

      // Generate file ID and calculate hash
      const fileId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const fileHash = await calculateSHA256(selectedFile);
      
      // Create chunks
      const chunks = createChunks(selectedFile, chunkSize);
      const totalChunks = chunks.length;

      // Update stats
      setUploadStats({
        fileId,
        fileName: selectedFile.name,
        fileSize: selectedFile.size,
        totalChunks,
        uploadedChunks: 0
      });

      // Start upload session
      const startResponse = await FileUploadAPI.startUpload({
        file_id: fileId,
        filename: selectedFile.name,
        total_chunks: totalChunks,
        file_size: selectedFile.size,
        file_hash: fileHash
      });

      console.log('Upload session started:', startResponse);
      setUploadState('uploading');

      // Upload chunks
      let uploadedCount = 0;
      const failedChunks = [];

      for (let i = 0; i < chunks.length; i++) {
        try {
          const chunk = chunks[i];
          const chunkHash = await calculateChunkSHA256(await chunk.arrayBuffer());
          
          await FileUploadAPI.uploadChunk({
            file_id: fileId,
            chunk_number: i,
            total_chunks: totalChunks,
            chunk_hash: chunkHash,
            chunk: chunk,
            attempt: 1
          });

          uploadedCount++;
          setUploadStats(prev => ({ ...prev, uploadedChunks: uploadedCount }));
          setProgress((uploadedCount / totalChunks) * 90); // Reserve 10% for merging

        } catch (error) {
          console.error(`Failed to upload chunk ${i}:`, error);
          failedChunks.push(i);
        }
      }

      // Retry failed chunks
      if (failedChunks.length > 0) {
        console.log(`Retrying ${failedChunks.length} failed chunks...`);
        for (const chunkIndex of failedChunks) {
          try {
            const chunk = chunks[chunkIndex];
            const chunkHash = await calculateChunkSHA256(await chunk.arrayBuffer());
            
            await FileUploadAPI.uploadChunk({
              file_id: fileId,
              chunk_number: chunkIndex,
              total_chunks: totalChunks,
              chunk_hash: chunkHash,
              chunk: chunk,
              attempt: 2
            });

            uploadedCount++;
            setUploadStats(prev => ({ ...prev, uploadedChunks: uploadedCount }));
            setProgress((uploadedCount / totalChunks) * 90);

          } catch (error) {
            console.error(`Failed to retry chunk ${chunkIndex}:`, error);
            throw new Error(`Upload failed: Could not upload chunk ${chunkIndex}`);
          }
        }
      }

      // Complete upload
      setProgress(95);
      const completeResponse = await FileUploadAPI.completeUpload(fileId, fileHash);
      console.log('Upload completed:', completeResponse);

      setProgress(100);
      setUploadState('completed');

      // Save to localStorage for file list
      const uploadedFiles = JSON.parse(localStorage.getItem('uploadedFiles') || '[]');
      uploadedFiles.push({
        name: selectedFile.name,
        size: selectedFile.size,
        uploadDate: new Date().toISOString(),
        fileId: fileId
      });
      localStorage.setItem('uploadedFiles', JSON.stringify(uploadedFiles));

    } catch (error) {
      console.error('Upload failed:', error);
      setError(error.message);
      setUploadState('error');
    }
  };

  const cancelUpload = async () => {
    if (uploadStats.fileId) {
      try {
        await FileUploadAPI.cancelUpload(uploadStats.fileId);
      } catch (error) {
        console.error('Failed to cancel upload:', error);
      }
    }
    
    setUploadState('idle');
    setProgress(0);
    setUploadStats({
      uploadedChunks: 0,
      totalChunks: 0,
      fileId: null,
      fileName: null,
      fileSize: 0
    });
    clearMessages();
  };

  const resetUpload = () => {
    setSelectedFile(null);
    setUploadState('idle');
    setProgress(0);
    setError(null);
    setUploadStats({
      uploadedChunks: 0,
      totalChunks: 0,
      fileId: null,
      fileName: null,
      fileSize: 0
    });
    clearMessages();
  };

  return (
    <div className="space-y-6">
      {/* File Selection */}
      {!selectedFile && (
        <FileDropZone 
          onFileSelect={handleFileSelect}
          className="mb-6"
        />
      )}

      {/* Selected File Info */}
      {selectedFile && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Selected File</h3>
            <button 
              onClick={resetUpload}
              className="text-gray-500 hover:text-gray-700"
              disabled={uploadState === 'uploading' || uploadState === 'preparing'}
            >
              ✕
            </button>
          </div>
          
          <div className="flex items-center space-x-4 mb-4">
            <div className="text-3xl">📄</div>
            <div>
              <h4 className="font-medium text-gray-900">{selectedFile.name}</h4>
              <p className="text-sm text-gray-500">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>

          {/* Chunk Size Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Chunk Size
            </label>
            <select
              value={chunkSize}
              onChange={(e) => setChunkSize(parseInt(e.target.value))}
              disabled={uploadState !== 'idle'}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value={262144}>256 KB (Slow network)</option>
              <option value={1048576}>1 MB (Default)</option>
              <option value={2097152}>2 MB (Fast network)</option>
              <option value={5242880}>5 MB (Very fast network)</option>
            </select>
          </div>

          {/* Upload Progress */}
          {(uploadState !== 'idle') && (
            <div className="mb-4">
              <ProgressBar 
                progress={progress} 
                status={uploadState}
              />
              
              {uploadStats.totalChunks > 0 && (
                <div className="mt-2 text-sm text-gray-600">
                  <div className="flex justify-between">
                    <span>Chunks: {uploadStats.uploadedChunks}/{uploadStats.totalChunks}</span>
                    <span>File ID: {uploadStats.fileId}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <span className="text-red-500">⚠️</span>
                <span className="text-red-700 text-sm font-medium">Upload Failed</span>
              </div>
              <p className="text-red-600 text-sm mt-1">{error}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex space-x-3">
            {uploadState === 'idle' && (
              <button
                onClick={startUpload}
                className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors"
              >
                Start Upload
              </button>
            )}
            
            {(uploadState === 'uploading' || uploadState === 'preparing') && (
              <button
                onClick={cancelUpload}
                className="bg-red-500 hover:bg-red-600 text-white px-6 py-2 rounded-lg transition-colors"
              >
                Cancel Upload
              </button>
            )}
            
            {uploadState === 'completed' && (
              <button
                onClick={resetUpload}
                className="bg-green-500 hover:bg-green-600 text-white px-6 py-2 rounded-lg transition-colors"
              >
                Upload Another File
              </button>
            )}
            
            {uploadState === 'error' && (
              <div className="space-x-3">
                <button
                  onClick={startUpload}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors"
                >
                  Retry Upload
                </button>
                <button
                  onClick={resetUpload}
                  className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-lg transition-colors"
                >
                  Select New File
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Log Viewer */}
      {uploadStats.fileId && (
        <LogViewer 
          messages={messages}
          connectionStatus={connectionStatus}
        />
      )}
    </div>
  );
}