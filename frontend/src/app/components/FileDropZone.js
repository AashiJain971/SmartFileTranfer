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
        relative border-2 border-dashed rounded-3xl p-12 text-center cursor-pointer backdrop-blur-xl overflow-hidden
        transition-all duration-500 hover:scale-[1.02] group
        ${isDragOver ? 'border-blue-400 bg-gradient-to-br from-blue-500/20 to-purple-500/20 shadow-2xl shadow-blue-500/25 scale-105' : 'border-gray-300 bg-gradient-to-br from-white to-gray-50 hover:border-blue-400/70 hover:shadow-xl'}
        ${className}
      `}
      style={{
        boxShadow: isDragOver 
          ? '0 25px 50px -12px rgba(59, 130, 246, 0.4), 0 0 0 1px rgba(59, 130, 246, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.3)'
          : '0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(255, 255, 255, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.2)'
      }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={openFileDialog}
    >
      {/* Animated Background Pattern */}
      <div className="absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
        <div className="absolute inset-0"
             style={{
               backgroundImage: `
                 radial-gradient(circle at 25% 25%, rgba(59, 130, 246, 0.1) 0%, transparent 50%),
                 radial-gradient(circle at 75% 75%, rgba(147, 51, 234, 0.1) 0%, transparent 50%)
               `,
               backgroundSize: '100px 100px'
             }} />
      </div>

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept={accept}
        onChange={handleFileInput}
      />
      
      <div className="relative z-10 mb-8">
        <div className={`w-20 h-20 mx-auto mb-6 rounded-2xl flex items-center justify-center transition-all duration-300 ${
          isDragOver 
            ? 'bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg scale-110' 
            : 'bg-gradient-to-br from-gray-100 to-gray-200 group-hover:from-blue-100 group-hover:to-purple-100 group-hover:scale-110'
        }`}>
          <svg className={`w-10 h-10 transition-colors duration-300 ${
            isDragOver ? 'text-white' : 'text-gray-500 group-hover:text-blue-600'
          }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
      </div>
      
      <h3 className="text-2xl font-bold mb-4 relative z-10">
        <span className={`transition-all duration-300 ${
          isDragOver 
            ? 'bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent'
            : 'bg-gradient-to-r from-gray-700 to-gray-900 bg-clip-text text-transparent group-hover:from-blue-600 group-hover:to-purple-600'
        }`}>
          {isDragOver ? 'Drop your file here!' : 'Drop your file here or click to browse'}
        </span>
      </h3>
      
      <p className={`mb-8 text-lg relative z-10 transition-colors duration-300 ${
        isDragOver ? 'text-blue-600' : 'text-gray-600 group-hover:text-gray-700'
      }`}>
        Supports all file types
        {maxSize && ` • Max size: ${formatMaxSize(maxSize)}`}
      </p>

      {/* Feature Pills */}
      <div className="flex flex-wrap justify-center gap-3 mb-8 relative z-10">
        <div className="px-3 py-2 bg-green-50 border border-green-200 rounded-xl flex items-center space-x-2">
          <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span className="text-xs font-medium text-green-800">Secure</span>
        </div>
        <div className="px-3 py-2 bg-blue-50 border border-blue-200 rounded-xl flex items-center space-x-2">
          <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span className="text-xs font-medium text-blue-800">Fast</span>
        </div>
        <div className="px-3 py-2 bg-purple-50 border border-purple-200 rounded-xl flex items-center space-x-2">
          <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          <span className="text-xs font-medium text-purple-800">Reliable</span>
        </div>
      </div>
      
      <button 
        type="button"
        className="group/btn relative px-10 py-4 bg-gradient-to-r from-blue-600 via-purple-600 to-blue-700 text-white font-bold rounded-2xl transition-all duration-300 hover:scale-105 shadow-xl hover:shadow-2xl relative z-10 overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #1d4ed8 100%)',
          boxShadow: '0 10px 25px -3px rgba(37, 99, 235, 0.4), 0 4px 6px -2px rgba(37, 99, 235, 0.05)'
        }}
        onClick={(e) => {
          e.stopPropagation();
          openFileDialog();
        }}
      >
        <div className="absolute inset-0 bg-white/10 rounded-2xl opacity-0 group-hover/btn:opacity-100 transition-opacity duration-300"></div>
        <div className="flex items-center space-x-3 relative z-10">
          <svg className="w-6 h-6 group-hover/btn:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2 2z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2" />
          </svg>
          <span className="text-lg">Choose File</span>
          <div className="px-2 py-1 bg-white/20 rounded-lg">
            <span className="text-xs font-medium">Browse</span>
          </div>
        </div>
      </button>

      {/* Drag Indicator */}
      {isDragOver && (
        <div className="absolute inset-4 border-2 border-dashed border-blue-400 rounded-2xl bg-blue-500/10 flex items-center justify-center">
          <div className="text-center">
            <svg className="w-16 h-16 mx-auto text-blue-500 animate-bounce mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <p className="text-blue-600 font-bold text-xl">Drop it like it's hot! 🔥</p>
          </div>
        </div>
      )}
    </div>
  );
}