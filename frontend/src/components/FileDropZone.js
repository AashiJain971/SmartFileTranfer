'use client';

import { useState, useRef } from 'react';

export default function FileDropZone({ onFileSelect, accept, maxSize, className = '' }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  const handleFileInput = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  const formatMaxSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div
      className={`
        border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer
        transition-all duration-200 hover:border-gray-400
        ${isDragOver ? 'border-blue-500 bg-blue-50' : ''}
        ${className}
      `}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={openFileDialog}
    >
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept={accept}
        onChange={handleFileInput}
      />
      
      <div className="text-6xl mb-4 text-gray-400">📁</div>
      
      <h3 className="text-lg font-semibold text-gray-700 mb-2">
        Drop your file here or click to browse
      </h3>
      
      <p className="text-gray-500 mb-4">
        Supports all file types
        {maxSize && ` • Max size: ${formatMaxSize(maxSize)}`}
      </p>
      
      <button 
        type="button"
        className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors"
        onClick={openFileDialog}
      >
        Choose File
      </button>
    </div>
  );
}