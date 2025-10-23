'use client';

import { useState } from 'react';

export default function ProgressBar({ progress, status, showDetails = true }) {
  const getStatusColor = () => {
    switch (status) {
      case 'uploading':
        return 'bg-gradient-to-r from-blue-500 to-cyan-500';
      case 'completed':
        return 'bg-gradient-to-r from-green-500 to-emerald-500';
      case 'error':
        return 'bg-gradient-to-r from-red-500 to-pink-500';
      case 'paused':
        return 'bg-gradient-to-r from-yellow-500 to-orange-500';
      default:
        return 'bg-gradient-to-r from-gray-500 to-gray-600';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'uploading':
        return 'Uploading...';
      case 'completed':
        return 'Upload Complete';
      case 'error':
        return 'Upload Error';
      case 'paused':
        return 'Upload Paused';
      default:
        return 'Ready';
    }
  };

  return (
    <div className="w-full backdrop-blur-sm bg-white/5 border border-white/10 rounded-2xl p-6">
      <div className="flex justify-between items-center mb-4">
        <span className="text-lg font-semibold text-gray-200 flex items-center space-x-2">
          {status === 'uploading' && (
            <svg className="w-5 h-5 text-blue-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          {status === 'completed' && (
            <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          )}
          {status === 'error' && (
            <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
          <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            {getStatusText()}
          </span>
        </span>
        <span className="text-2xl font-bold text-gray-300">
          {Math.round(progress || 0)}%
        </span>
      </div>
      
      <div className="w-full backdrop-blur-sm bg-black/30 rounded-2xl h-4 border border-white/20 overflow-hidden">
        <div 
          className={`h-full rounded-2xl transition-all duration-500 ${getStatusColor()} relative`}
          style={{ width: `${progress || 0}%` }}
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse"></div>
        </div>
      </div>

      {showDetails && progress > 0 && (
        <div className="mt-4 flex justify-between text-sm text-gray-400">
          <span className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Progress: {Math.round(progress || 0)}%</span>
          </span>
          <span className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{getStatusText()}</span>
          </span>
        </div>
      )}
    </div>
  );
}