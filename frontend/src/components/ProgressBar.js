'use client';

import { useState } from 'react';

export default function ProgressBar({ progress, status, showDetails = true }) {
  const getStatusColor = () => {
    switch (status) {
      case 'uploading':
        return 'bg-blue-500';
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'paused':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
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
    <div className="w-full">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-gray-700">
          {getStatusText()}
        </span>
        <span className="text-sm text-gray-500">
          {Math.round(progress || 0)}%
        </span>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div 
          className={`h-2.5 rounded-full transition-all duration-300 ${getStatusColor()}`}
          style={{ width: `${progress || 0}%` }}
        ></div>
      </div>

      {showDetails && progress > 0 && (
        <div className="mt-2 text-xs text-gray-600">
          <div className="flex justify-between">
            <span>Progress: {Math.round(progress || 0)}%</span>
            <span>Status: {getStatusText()}</span>
          </div>
        </div>
      )}
    </div>
  );
}