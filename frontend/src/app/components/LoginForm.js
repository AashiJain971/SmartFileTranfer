'use client';

import React, { useState, useEffect } from 'react';
import { authManager } from '../utils/auth';

export default function LoginForm({ onAuthSuccess }) {
  const [isSignup, setIsSignup] = useState(false);
  const [formData, setFormData] = useState({
    username: 'testuser',
    email: 'test@example.com',
    password: 'testpass123'
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  console.log('LoginForm component loaded');

  // Test connectivity on mount
  useEffect(() => {
    const testConnection = async () => {
      try {
        const response = await fetch('http://localhost:8000/health');
        const data = await response.json();
        console.log('Backend connection test:', data);
      } catch (error) {
        console.error('Backend connection failed:', error);
      }
    };
    testConnection();
  }, []);

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) {
      e.preventDefault();
    }
    console.log('handleSubmit called!');
    
    setIsLoading(true);
    setMessage({ text: '', type: '' });

    try {
      if (isSignup) {
        console.log('Attempting signup with:', formData);
        const result = await authManager.signup(formData.username, formData.email, formData.password);
        console.log('Signup result:', result);
        setMessage({ text: 'Account created successfully! Please login.', type: 'success' });
        setIsSignup(false);
      } else {
        console.log('Attempting login with:', formData);
        const loginResult = await authManager.login(formData.email, formData.password);
        console.log('Login successful:', loginResult);
        onAuthSuccess(loginResult.user);
      }
    } catch (error) {
      console.error('Auth error:', error);
      setMessage({ text: error.message || 'Authentication failed', type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e) => {
    console.log('Input changed:', e.target.name, '=', e.target.value);
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const toggleAuthMode = () => {
    console.log('Toggling auth mode');
    setIsSignup(!isSignup);
    setMessage({ text: '', type: '' });
  };

  return (
    <div className="max-w-md mx-auto mt-20 p-8 bg-white rounded-xl shadow-lg border border-gray-200">
      <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
        {isSignup ? 'Sign Up' : 'Login'}
      </h2>
      
      <div className="space-y-4">
        {isSignup && (
          <div>
            <input
              type="text"
              name="username"
              placeholder="Username"
              value={formData.username}
              onChange={handleInputChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        )}
        
        <div>
          <input
            type="email"
            name="email"
            placeholder="Email"
            value={formData.email}
            onChange={handleInputChange}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        
        <div>
          <input
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleInputChange}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <button
          type="button"
          disabled={isLoading}
          onClick={handleSubmit}
          className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
        >
          {isLoading ? 'Processing...' : (isSignup ? 'Sign Up' : 'Login')}
        </button>

        <button
          type="button"
          onClick={() => {
            console.log('Test button clicked');
            alert('JavaScript is working! Check console for logs.');
          }}
          className="w-full py-2 px-4 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors"
        >
          Test JavaScript
        </button>

        <button
          type="button"
          onClick={async () => {
            console.log('Testing backend connection...');
            try {
              const response = await fetch('http://localhost:8000/health');
              const data = await response.json();
              console.log('Backend health check:', data);
              alert('Backend is accessible! Status: ' + data.status);
            } catch (error) {
              console.error('Backend connection failed:', error);
              alert('Backend connection failed! Make sure backend is running on port 8000.');
            }
          }}
          className="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors"
        >
          Test Backend Connection
        </button>
      </div>

      {message.text && (
        <div className={`mt-4 p-3 rounded-lg text-sm ${
          message.type === 'error' 
            ? 'bg-red-100 text-red-700 border border-red-200' 
            : 'bg-green-100 text-green-700 border border-green-200'
        }`}>
          {message.text}
        </div>
      )}

      <div className="mt-6 text-center text-gray-600">
        <span>{isSignup ? 'Already have an account?' : "Don't have an account?"}</span>
        <button
          type="button"
          onClick={toggleAuthMode}
          className="ml-2 text-blue-600 hover:text-blue-700 font-medium"
        >
          {isSignup ? 'Login' : 'Sign up'}
        </button>
      </div>
    </div>
  );
}