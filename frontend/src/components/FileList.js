'use client';

import { useState, useEffect } from 'react';

export default function FileList({ onDownload, onDelete }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // In a real implementation, you would fetch this from your backend
    // For now, we'll simulate with localStorage
    const uploadedFiles = JSON.parse(localStorage.getItem('uploadedFiles') || '[]');
    setFiles(uploadedFiles);
    setLoading(false);
  }, []);

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Uploaded Files</h3>
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="text-gray-500 mt-2">Loading files...</p>
        </div>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Uploaded Files</h3>
        <div className="text-center py-8">
          <div className="text-4xl mb-2">📂</div>
          <p className="text-gray-500">No files uploaded yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold mb-4">Uploaded Files ({files.length})</h3>
      
      <div className="space-y-3">
        {files.map((file, index) => (
          <div 
            key={index}
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <div className="flex items-center space-x-4">
              <div className="text-2xl">📄</div>
              <div>
                <h4 className="font-medium text-gray-900">{file.name}</h4>
                <p className="text-sm text-gray-500">
                  {formatFileSize(file.size)} • {formatDate(file.uploadDate)}
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onDownload(file)}
                className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 transition-colors"
              >
                Download
              </button>
              <button
                onClick={() => onDelete(file)}
                className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}