'use client';

import { useState, useEffect } from 'react';
import { SafeStorage } from '../utils/storage';

export default function StorageInfo() {
  const [storageInfo, setStorageInfo] = useState(null);
  const [fileCount, setFileCount] = useState(0);

  useEffect(() => {
    updateStorageInfo();
  }, []);

  const updateStorageInfo = () => {
    const info = SafeStorage.getStorageInfo();
    const files = SafeStorage.getUploadedFiles();
    setStorageInfo(info);
    setFileCount(files.length);
  };

  const clearAllFiles = () => {
    if (confirm('Are you sure you want to clear all file records? This will not delete the actual files from the server.')) {
      SafeStorage.clearItem('uploadedFiles');
      updateStorageInfo();
      window.location.reload();
    }
  };

  if (!storageInfo) return null;

  const isNearLimit = parseFloat(storageInfo.usedMB) > 3; // Warn if over 3MB

  return (
    <div className={`p-4 rounded-lg border ${isNearLimit ? 'bg-yellow-50 border-yellow-200' : 'bg-blue-50 border-blue-200'}`}>
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium text-gray-900">Local Storage Usage</h4>
          <div className="text-sm text-gray-600">
            <p>Files stored: {fileCount} (max {SafeStorage.MAX_FILES})</p>
            <p>Storage used: {storageInfo.usedMB} MB (limit: ~{storageInfo.estimatedLimit})</p>
          </div>
        </div>
        
        <div className="flex space-x-2">
          <button
            onClick={updateStorageInfo}
            className="text-sm px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Refresh
          </button>
          {fileCount > 0 && (
            <button
              onClick={clearAllFiles}
              className="text-sm px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
            >
              Clear All
            </button>
          )}
        </div>
      </div>
      
      {isNearLimit && (
        <div className="mt-2 text-sm text-yellow-700">
          ⚠️ Storage is getting full. Consider clearing old files to avoid upload issues.
        </div>
      )}
    </div>
  );
}