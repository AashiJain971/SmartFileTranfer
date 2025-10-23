// WebSocket hook for real-time updates
import { useState, useEffect, useRef } from 'react';

export const useWebSocket = (fileId) => {
  const [messages, setMessages] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [progress, setProgress] = useState(null);
  const ws = useRef(null);

  useEffect(() => {
    if (!fileId) return;

    const wsUrl = `ws://localhost:8000/ws/upload/${fileId}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      setConnectionStatus('Connected');
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Add to messages log
        setMessages(prev => [...prev, {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          type: data.type || 'message',
          data: data
        }]);

        // Update progress if it's a progress update
        if (data.type === 'chunk_completed' || data.type === 'upload_progress') {
          setProgress(data);
        }

      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.current.onclose = () => {
      setConnectionStatus('Disconnected');
    };

    ws.current.onerror = (error) => {
      setConnectionStatus('Error');
      console.error('WebSocket error:', error);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [fileId]);

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