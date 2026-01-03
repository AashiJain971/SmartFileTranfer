// WebSocket hook for real-time updates

import { useState, useEffect, useRef } from 'react';
import { AuthAPI } from '../utils/api';

export const useWebSocket = (fileId) => {
  const [messages, setMessages] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [progress, setProgress] = useState(null);
  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef(null);

  // Track token for reconnect on login/logout
  const [token, setToken] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('accessToken');
    }
    return null;
  });

  // Listen for token changes (login/logout)
  useEffect(() => {
    const handleStorage = () => {
      setToken(localStorage.getItem('accessToken'));
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  // Helper to open WebSocket
  const openWebSocket = () => {
    if (!fileId || !token) return;
    setConnectionStatus('Connecting...');
    const wsUrl = AuthAPI.getWebSocketUrl(fileId);
    ws.current = new window.WebSocket(wsUrl);

    ws.current.onopen = () => {
      setConnectionStatus('Connected');
      reconnectAttempts.current = 0;
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages(prev => [...prev, {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          type: data.type || 'message',
          data: data
        }]);
        if (data.type === 'chunk_completed' || data.type === 'upload_progress') {
          setProgress(data);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.current.onclose = () => {
      setConnectionStatus('Disconnected');
      // Auto-reconnect logic
      if (reconnectAttempts.current < 3) {
        reconnectAttempts.current += 1;
        reconnectTimeout.current = setTimeout(() => {
          openWebSocket();
        }, 5000 * reconnectAttempts.current); // Exponential backoff
        setConnectionStatus('Reconnecting...');
      }
    };

    ws.current.onerror = (error) => {
      setConnectionStatus('Error');
      console.error('WebSocket error:', error);
      ws.current.close();
    };
  };

  // Main effect: reconnect on fileId or token change
  useEffect(() => {
    if (!fileId || !token) {
      setConnectionStatus('Disconnected');
      return;
    }
    // Clean up previous
    if (ws.current) {
      ws.current.close();
    }
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    reconnectAttempts.current = 0;
    openWebSocket();
    return () => {
      if (ws.current) ws.current.close();
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [fileId, token]);

  const sendMessage = (message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  };

  return {
    messages,
    connectionStatus,
    progress,
    sendMessage,
    clearMessages: () => setMessages([])
  };
};