// API client for backend communication
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Helper function to get auth headers
const getAuthHeaders = () => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// Helper function for authenticated fetch
const authenticatedFetch = async (url, options = {}) => {
  const authHeaders = getAuthHeaders();
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...authHeaders,
      ...options.headers,
    },
  });

  // Handle 401 errors by attempting token refresh
  if (response.status === 401) {
    const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refreshToken') : null;
    
    if (refreshToken) {
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            refresh_token: refreshToken,
          }),
        });

        if (refreshResponse.ok) {
          const { access_token } = await refreshResponse.json();
          localStorage.setItem('accessToken', access_token);
          
          // Retry original request with new token
          return fetch(url, {
            ...options,
            headers: {
              'Authorization': `Bearer ${access_token}`,
              ...options.headers,
            },
          });
        }
      } catch (error) {
        // Refresh failed, clear storage and redirect to login
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      }
    }
  }

  return response;
};

// Authentication API
export class AuthAPI {
  static async signup(userData) {
    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Signup failed');
    }

    return response.json();
  }

  static async login(credentials) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    
    // Store tokens and user info
    if (typeof window !== 'undefined') {
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      localStorage.setItem('user', JSON.stringify(data.user));
    }

    return data;
  }

  static async logout() {
    try {
      await authenticatedFetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage regardless of API success
      if (typeof window !== 'undefined') {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
      }
    }
  }

  static async getCurrentUser() {
    const response = await authenticatedFetch(`${API_BASE_URL}/auth/me`);
    
    if (!response.ok) {
      throw new Error('Failed to get current user');
    }

    return response.json();
  }

  static isLoggedIn() {
    if (typeof window === 'undefined') return false;
    return !!localStorage.getItem('accessToken');
  }

  static getUser() {
    if (typeof window === 'undefined') return null;
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }

  static getWebSocketUrl(fileId) {
    if (typeof window === 'undefined') return null;
    const token = localStorage.getItem('accessToken');
    if (!token || !fileId) return null;
    return `ws://localhost:8000/ws/upload/${fileId}?token=${encodeURIComponent(token)}`;
  }
}

export class FileUploadAPI {
  static async startUpload(fileData) {
    const formData = new FormData();
    formData.append('file_id', fileData.file_id);
    formData.append('filename', fileData.filename);
    formData.append('total_chunks', fileData.total_chunks);
    formData.append('file_size', fileData.file_size);
    formData.append('file_hash', fileData.file_hash);

    const response = await authenticatedFetch(`${API_BASE_URL}/upload/start`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to start upload: ${response.statusText}`);
    }

    return response.json();
  }

  static async uploadChunk(chunkData) {
    const formData = new FormData();
    formData.append('file_id', chunkData.file_id);
    formData.append('chunk_number', chunkData.chunk_number);
    formData.append('total_chunks', chunkData.total_chunks);
    formData.append('chunk_hash', chunkData.chunk_hash);
    formData.append('chunk', chunkData.chunk);

    const response = await authenticatedFetch(`${API_BASE_URL}/upload/chunk`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to upload chunk: ${response.statusText}`);
    }

    return response.json();
  }

  static async getUploadStatus(fileId) {
    const response = await authenticatedFetch(`${API_BASE_URL}/upload/status/${fileId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.statusText}`);
    }

    return response.json();
  }

  static async completeUpload(fileId, expectedHash) {
    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('expected_hash', expectedHash);

    const response = await authenticatedFetch(`${API_BASE_URL}/upload/complete`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to complete upload: ${response.statusText}`);
    }

    return response.json();
  }

  static async cancelUpload(fileId) {
    const response = await authenticatedFetch(`${API_BASE_URL}/upload/cancel/${fileId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to cancel upload: ${response.statusText}`);
    }

    return response.json();
  }

  static async downloadFile(filename) {
    const response = await authenticatedFetch(`${API_BASE_URL}/upload/download/${encodeURIComponent(filename)}`);
    
    if (!response.ok) {
      throw new Error(`Failed to download file: ${response.statusText}`);
    }

    return response;
  }

  static async getFiles() {
    const response = await authenticatedFetch(`${API_BASE_URL}/upload/files`);
    
    if (!response.ok) {
      throw new Error(`Failed to get files: ${response.statusText}`);
    }

    return response.json();
  }

  static async deleteFile(filename) {
    const response = await authenticatedFetch(`${API_BASE_URL}/upload/files/${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete file: ${response.statusText}`);
    }

    return response.json();
  }

  static async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return response.ok;
    } catch (error) {
      return false;
    }
  }
}

// WebSocket URL generator
export const getWebSocketUrl = (fileId, token) => {
  const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = process.env.NEXT_PUBLIC_WS_URL || 'localhost:8000';
  return `${wsProtocol}//${wsHost}/ws/upload/${fileId}?token=${encodeURIComponent(token)}`;
};