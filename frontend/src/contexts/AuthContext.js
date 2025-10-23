'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { AuthAPI } from '../utils/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    // Check if user is logged in on mount
    const checkAuth = () => {
      try {
        const userData = AuthAPI.getUser();
        const hasToken = AuthAPI.isLoggedIn();
        
        if (userData && hasToken) {
          setUser(userData);
          setIsLoggedIn(true);
        }
      } catch (error) {
        console.error('Auth check error:', error);
        // Clear invalid data
        AuthAPI.logout();
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (credentials) => {
    try {
      setIsLoading(true);
      const data = await AuthAPI.login(credentials);
      setUser(data.user);
      setIsLoggedIn(true);
      return data;
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (userData) => {
    try {
      setIsLoading(true);
      await AuthAPI.signup(userData);
      // Don't auto-login after signup, let user login manually
      return true;
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await AuthAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setIsLoggedIn(false);
    }
  };

  const value = {
    user,
    isLoggedIn,
    isLoading,
    login,
    signup,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};