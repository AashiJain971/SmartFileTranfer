// Authentication Manager based on the working HTML implementation
class AuthManager {
  constructor() {
    this.authState = {
      isLoggedIn: false,
      user: null,
      accessToken: null,
      refreshToken: null
    };
    this.init();
  }

  init() {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('accessToken');
      const user = localStorage.getItem('user');
      
      if (token && user) {
        this.authState.accessToken = token;
        this.authState.refreshToken = localStorage.getItem('refreshToken');
        this.authState.user = JSON.parse(user);
        this.authState.isLoggedIn = true;
      }
    }
  }

  async login(email, password) {
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    // Store tokens and user info (matching HTML implementation)
    this.authState.accessToken = data.access_token;
    this.authState.refreshToken = data.refresh_token;
    this.authState.user = data.user;
    this.authState.isLoggedIn = true;

    if (typeof window !== 'undefined') {
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      localStorage.setItem('user', JSON.stringify(data.user));
    }

    return data;
  }

  async signup(username, email, password) {
    const response = await fetch('http://localhost:8000/auth/signup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, email, password })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Signup failed');
    }

    return data;
  }

  async logout() {
    // Clear auth state
    this.authState.isLoggedIn = false;
    this.authState.user = null;
    this.authState.accessToken = null;
    this.authState.refreshToken = null;

    if (typeof window !== 'undefined') {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
    }
  }

  // Enhanced fetch with authentication (matching HTML implementation)
  async authenticatedFetch(url, options = {}) {
    if (!this.authState.accessToken) {
      throw new Error('No access token available. Please login.');
    }

    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${this.authState.accessToken}`
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      // Handle different auth errors (matching HTML implementation)
      if (response.status === 401) {
        const errorData = await response.json().catch(() => ({}));
        
        // Try to refresh token
        const refreshed = await this.refreshAccessToken();
        if (refreshed) {
          // Retry with new token
          return fetch(url, {
            ...options,
            headers: {
              ...options.headers,
              'Authorization': `Bearer ${this.authState.accessToken}`
            }
          });
        } else {
          // Refresh failed, logout
          this.logout();
          throw new Error(`Authentication failed: ${errorData.detail || 'Session expired'}`);
        }
      }

      if (response.status === 403) {
        throw new Error('Access forbidden - insufficient permissions');
      }

      return response;

    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Network error - check if backend server is running');
      }
      throw error;
    }
  }

  async refreshAccessToken() {
    try {
      const response = await fetch('http://localhost:8000/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: this.authState.refreshToken
        })
      });

      if (response.ok) {
        const data = await response.json();
        this.authState.accessToken = data.access_token;
        if (typeof window !== 'undefined') {
          localStorage.setItem('accessToken', data.access_token);
        }
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    return false;
  }

  getAuthState() {
    return this.authState;
  }

  // WebSocket URL with token (matching HTML implementation)
  getWebSocketUrl(fileId) {
    if (!this.authState.accessToken) {
      throw new Error('No access token available for WebSocket connection');
    }
    return `ws://localhost:8000/ws/upload/${fileId}?token=${encodeURIComponent(this.authState.accessToken)}`;
  }
}

export const authManager = new AuthManager();