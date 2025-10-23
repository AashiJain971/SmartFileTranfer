'use client';

import { useState, useCallback } from 'react';
import { FileUploadAPI } from '../../utils/api';
import { calculateSHA256, calculateChunkSHA256, createChunks, formatFileSize } from '../../utils/fileUtils';
import { useWebSocket } from '../../hooks/useWebSocket';
import FileDropZone from './FileDropZone';
import ProgressBar from './ProgressBar';

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
  const [isDragging, setIsDragging] = useState(false);

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

      // Generate file ID with higher entropy (like in the working HTML)
      let fileId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}-${Math.floor(Math.random() * 10000)}`;
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

      // Start upload session with retry logic (like in HTML)
      let retryCount = 0;
      let startResponse = null;
      
      while (retryCount < 3) {
        try {
          startResponse = await FileUploadAPI.startUpload({
            file_id: fileId,
            filename: selectedFile.name,
            total_chunks: totalChunks,
            file_size: selectedFile.size,
            file_hash: fileHash
          });
          break; // Success, exit retry loop
        } catch (error) {
          // Check for duplicate key or network monitor errors
          if (error.message && 
              (error.message.includes('mean requires at least one data point') || 
               error.message.includes('already exists') ||
               error.message.includes('duplicate key'))) {
            retryCount++;
            if (retryCount < 3) {
              // Generate new file ID for retry
              fileId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}-${Math.floor(Math.random() * 10000)}`;
              setUploadStats(prev => ({ ...prev, fileId }));
              console.log(`Retrying with new session ID (attempt ${retryCount + 1}/3)...`);
              await new Promise(resolve => setTimeout(resolve, retryCount * 1000));
              continue;
            }
          }
          throw error; // Re-throw if not a retryable error or max retries reached
        }
      }

      if (!startResponse) {
        throw new Error('Failed to start upload after 3 attempts');
      }

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
            chunk: chunk
          });

          uploadedCount++;
          setUploadStats(prev => ({ ...prev, uploadedChunks: uploadedCount }));
          setProgress((uploadedCount / totalChunks) * 90); // Reserve 10% for merging

          // Small delay to prevent overwhelming the server (like in HTML)
          if (i < chunks.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 100));
          }

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
      console.log('Completing upload with hash:', fileHash);
      const completeResponse = await FileUploadAPI.completeUpload(fileId, fileHash);
      console.log('Upload completed:', completeResponse);

      setProgress(100);
      setUploadState('completed');

      // Upload completed successfully
      console.log(`File ${selectedFile.name} uploaded successfully with ID: ${fileId}`);

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
        <div className="transform hover:scale-[1.02] transition-all duration-300">
          <FileDropZone 
            onFileSelect={handleFileSelect}
            className="mb-6"
          />
        </div>
      )}

      {/* Selected File Info */}
      {selectedFile && (
        <div className="bg-white rounded-3xl p-8 border border-gray-200 shadow-2xl transform hover:scale-[1.01] transition-all duration-300"
             style={{
               boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.15), 0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(255, 255, 255, 0.8)'
             }}>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold">
                <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                  Selected File
                </span>
              </h3>
            </div>
            <button 
              onClick={resetUpload}
              className="p-3 rounded-xl text-gray-500 hover:text-red-500 hover:bg-red-50 border border-gray-200 hover:border-red-200 transition-all duration-300 hover:scale-110"
              disabled={uploadState === 'uploading' || uploadState === 'preparing'}
              title="Remove file"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="flex items-center space-x-6 mb-6 p-6 rounded-2xl bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 hover:border-purple-300 transition-all duration-300">
            <div className="flex-shrink-0">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg transform hover:rotate-3 transition-transform duration-300">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
            <div className="flex-grow">
              <h4 className="font-bold text-gray-800 text-xl mb-2 flex items-center space-x-2">
                <span className="truncate max-w-xs">{selectedFile.name}</span>
                <div className="px-3 py-1 bg-green-100 border border-green-300 rounded-lg">
                  <span className="text-xs text-green-700 font-bold">Ready</span>
                </div>
              </h4>
              <div className="flex items-center space-x-4 text-sm">
                <div className="flex items-center space-x-2 bg-blue-100 px-3 py-1 rounded-lg border border-blue-200">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                  </svg>
                  <span className="font-bold text-blue-700">{formatFileSize(selectedFile.size)}</span>
                </div>
                <div className="flex items-center space-x-2 bg-purple-100 px-3 py-1 rounded-lg border border-purple-200">
                  <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a1.994 1.994 0 01-1.414.586H7a1 1 0 01-1-1V4a1 1 0 011-1z" />
                  </svg>
                  <span className="font-bold text-purple-700">
                    {selectedFile.name.split('.').pop()?.toUpperCase() || 'FILE'}
                  </span>
                </div>
                <div className="flex items-center space-x-2 bg-green-100 px-3 py-1 rounded-lg border border-green-200">
                  <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="font-bold text-green-700">Secure</span>
                </div>
              </div>
            </div>
          </div>

          {/* Chunk Size Selection */}
          <div className="mb-6 p-6 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-2xl">
            <label className="block text-sm font-bold text-gray-700 mb-4 flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <span className="text-lg">Upload Optimization</span>
              <div className="px-3 py-1 bg-blue-100 border border-blue-300 rounded-lg">
                <span className="text-xs text-blue-700 font-bold">Advanced</span>
              </div>
            </label>
            <select
              value={chunkSize}
              onChange={(e) => setChunkSize(parseInt(e.target.value))}
              disabled={uploadState !== 'idle'}
              className="w-full bg-white border border-gray-300 rounded-xl px-4 py-4 text-gray-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all duration-300 hover:border-purple-400 font-medium text-base"
            >
              <option value={262144} className="bg-white text-gray-800">🐌 256 KB - Slow/Mobile Network</option>
              <option value={1048576} className="bg-white text-gray-800">⚡ 1 MB - Standard (Recommended)</option>
              <option value={2097152} className="bg-white text-gray-800">🚀 2 MB - Fast Broadband</option>
              <option value={5242880} className="bg-white text-gray-800">💫 5 MB - Ultra-Fast Network</option>
            </select>
            <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-xl">
              <p className="text-sm text-yellow-800 flex items-center space-x-2">
                <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="font-medium">
                  <strong>Pro Tip:</strong> Larger chunks = faster upload on stable connections, smaller chunks = more reliable on unstable connections
                </span>
              </p>
            </div>
          </div>

          {/* Upload Progress */}
          {(uploadState !== 'idle') && (
            <div className="mb-6">
              <ProgressBar 
                progress={progress} 
                status={uploadState}
              />
              
              {uploadStats.totalChunks > 0 && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-2xl">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-cyan-100 rounded-lg flex items-center justify-center">
                        <svg className="w-4 h-4 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012 2v2M7 7h10" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-gray-700 font-medium">Progress</p>
                        <p className="text-cyan-600 font-bold">{uploadStats.uploadedChunks}/{uploadStats.totalChunks} chunks</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                        <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a1.994 1.994 0 01-1.414.586H7a1 1 0 01-1-1V4a1 1 0 011-1z" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-gray-700 font-medium">Upload ID</p>
                        <p className="text-purple-600 font-mono font-bold text-xs">{uploadStats.fileId?.slice(-8)}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                  <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <span className="text-red-700 font-bold text-lg">Upload Failed</span>
              </div>
              <p className="text-red-600 text-sm mt-3 ml-11 bg-red-100 p-3 rounded-lg border border-red-200">{error}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-4 pt-4 border-t border-gray-200">
            {uploadState === 'idle' && (
              <button
                onClick={startUpload}
                className="group relative px-8 py-4 bg-gradient-to-r from-green-500 via-blue-500 to-purple-600 text-white font-bold rounded-2xl transition-all duration-300 hover:scale-105 shadow-2xl hover:shadow-green-500/25 flex items-center space-x-3 overflow-hidden"
                style={{
                  background: 'linear-gradient(135deg, #10b981 0%, #3b82f6 50%, #8b5cf6 100%)',
                  boxShadow: '0 10px 25px -5px rgba(16, 185, 129, 0.4), 0 4px 6px -2px rgba(16, 185, 129, 0.05)'
                }}
              >
                <div className="absolute inset-0 bg-white/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <svg className="w-6 h-6 relative z-10 group-hover:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span className="relative z-10 text-lg">Start Secure Upload</span>
                <div className="relative z-10 px-2 py-1 bg-white/20 rounded-lg">
                  <span className="text-xs font-medium">✨ AI-Powered</span>
                </div>
              </button>
            )}
            
            {(uploadState === 'uploading' || uploadState === 'preparing') && (
              <button
                onClick={cancelUpload}
                className="group relative px-8 py-4 bg-gradient-to-r from-red-500 to-pink-500 text-white font-bold rounded-2xl transition-all duration-300 hover:scale-105 shadow-2xl hover:shadow-red-500/25 flex items-center space-x-3"
                style={{
                  boxShadow: '0 10px 25px -5px rgba(239, 68, 68, 0.4), 0 4px 6px -2px rgba(239, 68, 68, 0.05)'
                }}
              >
                <svg className="w-6 h-6 group-hover:rotate-90 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span className="text-lg">Cancel Upload</span>
              </button>
            )}
            
            {uploadState === 'completed' && (
              <div className="flex flex-wrap gap-4">
                <button
                  onClick={resetUpload}
                  className="group relative px-8 py-4 bg-gradient-to-r from-purple-500 to-blue-500 text-white font-bold rounded-2xl transition-all duration-300 hover:scale-105 shadow-2xl hover:shadow-purple-500/25 flex items-center space-x-3"
                  style={{
                    boxShadow: '0 10px 25px -5px rgba(147, 51, 234, 0.4), 0 4px 6px -2px rgba(147, 51, 234, 0.05)'
                  }}
                >
                  <svg className="w-6 h-6 group-hover:rotate-180 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <span className="text-lg">Upload Another File</span>
                </button>
                <div className="px-6 py-4 bg-gradient-to-r from-green-500/20 to-blue-500/20 border border-green-500/30 rounded-2xl flex items-center space-x-3">
                  <svg className="w-6 h-6 text-green-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-green-400 font-bold text-lg">Upload Complete!</span>
                </div>
              </div>
            )}
            
            {uploadState === 'error' && (
              <div className="flex flex-wrap gap-4">
                <button
                  onClick={startUpload}
                  className="group relative px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-bold rounded-2xl transition-all duration-300 hover:scale-105 shadow-2xl hover:shadow-blue-500/25 flex items-center space-x-3"
                  style={{
                    boxShadow: '0 10px 25px -5px rgba(59, 130, 246, 0.4), 0 4px 6px -2px rgba(59, 130, 246, 0.05)'
                  }}
                >
                  <svg className="w-5 h-5 group-hover:rotate-180 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>Retry Upload</span>
                </button>
                <button
                  onClick={resetUpload}
                  className="group relative px-6 py-3 bg-gradient-to-r from-gray-500 to-gray-600 text-white font-bold rounded-2xl transition-all duration-300 hover:scale-105 shadow-2xl hover:shadow-gray-500/25 flex items-center space-x-3"
                >
                  <svg className="w-5 h-5 group-hover:scale-110 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2 2z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2" />
                  </svg>
                  <span>Select New File</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}


    </div>
  );
}