'use client';

import { useState, useEffect } from 'react';

export default function LogViewer({ messages, connectionStatus, className = '' }) {
  const [filter, setFilter] = useState('all');
  const [autoScroll, setAutoScroll] = useState(true);

  const filteredMessages = messages.filter(message => {
    if (filter === 'all') return true;
    return message.type === filter;
  });

  const getMessageTypeColor = (type) => {
    switch (type) {
      case 'upload_started':
        return 'text-blue-600';
      case 'chunk_completed':
        return 'text-green-600';
      case 'chunk_failed':
        return 'text-red-600';
      case 'merging_started':
        return 'text-yellow-600';
      case 'upload_completed':
        return 'text-green-700';
      case 'error':
        return 'text-red-700';
      default:
        return 'text-gray-600';
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  useEffect(() => {
    if (autoScroll) {
      const logContainer = document.getElementById('log-container');
      if (logContainer) {
        logContainer.scrollTop = logContainer.scrollHeight;
      }
    }
  }, [messages, autoScroll]);

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Upload Log</h3>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                connectionStatus === 'Connected' ? 'bg-green-500' : 
                connectionStatus === 'Error' ? 'bg-red-500' : 'bg-gray-500'
              }`}></div>
              <span className="text-sm text-gray-600">{connectionStatus}</span>
            </div>
            
            <select 
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              <option value="all">All Messages</option>
              <option value="upload_started">Upload Started</option>
              <option value="chunk_completed">Chunk Completed</option>
              <option value="chunk_failed">Chunk Failed</option>
              <option value="merging_started">Merging</option>
              <option value="upload_completed">Completed</option>
              <option value="error">Errors</option>
            </select>
            
            <label className="flex items-center space-x-2 text-sm">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded"
              />
              <span>Auto-scroll</span>
            </label>
          </div>
        </div>
      </div>
      
      <div 
        id="log-container"
        className="p-4 max-h-64 overflow-y-auto bg-gray-50 font-mono text-sm"
      >
        {filteredMessages.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No messages yet</p>
        ) : (
          <div className="space-y-1">
            {filteredMessages.map((message) => (
              <div key={message.id} className="flex items-start space-x-2">
                <span className="text-gray-400 text-xs whitespace-nowrap">
                  {formatTimestamp(message.timestamp)}
                </span>
                <span className={`font-medium ${getMessageTypeColor(message.type)}`}>
                  [{message.type.toUpperCase()}]
                </span>
                <span className="text-gray-700 flex-1">
                  {typeof message.data === 'object' ? JSON.stringify(message.data, null, 2) : message.data}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}