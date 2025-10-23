'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import FileUploader from './components/FileUploader';
import FileList from './components/FileList';
import StorageInfo from './components/StorageInfo';
import { FileUploadAPI } from '../utils/api';

export default function Home() {
  const [currentPage, setCurrentPage] = useState('upload'); // Default to upload page for authenticated users
  const [serverStatus, setServerStatus] = useState('checking');
  const { user, logout } = useAuth(); // Use authentication context

  useEffect(() => {
    checkServerHealth();
  }, []);

  const checkServerHealth = async () => {
    const isHealthy = await FileUploadAPI.healthCheck();
    setServerStatus(isHealthy ? 'online' : 'offline');
  };

  const handleLogout = () => {
    logout();
  };

  const handleDownload = async (file) => {
    try {
      const response = await FileUploadAPI.downloadFile(file.name);
      const blob = await response.blob();
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      alert(`Failed to download file: ${error.message}`);
    }
  };

  const handleDelete = async (file) => {
    if (confirm(`Are you sure you want to delete "${file.name}"?`)) {
      try {
        await FileUploadAPI.deleteFile(file.name);
        // Refresh the page to update the file list
        window.location.reload();
      } catch (error) {
        console.error('Delete failed:', error);
        alert(`Failed to delete file: ${error.message}`);
      }
    }
  };

  const getLocalStorageStats = () => {
    let totalSize = 0;
    let itemCount = 0;
    
    for (let key in localStorage) {
      if (localStorage.hasOwnProperty(key)) {
        itemCount++;
        totalSize += localStorage[key].length;
      }
    }
    
    const usedMB = (totalSize / (1024 * 1024)).toFixed(2);
    const maxMB = 5; // Most browsers limit localStorage to 5-10MB
    const usagePercent = ((totalSize / (maxMB * 1024 * 1024)) * 100).toFixed(1);
    
    return {
      totalSize,
      usedMB,
      maxMB,
      usagePercent,
      itemCount,
      items: Object.keys(localStorage).map(key => ({
        key,
        size: localStorage[key].length,
        value: localStorage[key].substring(0, 100) + (localStorage[key].length > 100 ? '...' : '')
      }))
    };
  };

  // Redirect to login if not authenticated
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 border border-gray-200">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 via-purple-600 to-pink-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              Authentication Required
            </h1>
            <p className="text-gray-600 mt-2">Please sign in to access NexusFlow</p>
          </div>
          <a 
            href="/login" 
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 px-4 rounded-lg font-semibold hover:shadow-lg transition-all duration-200 text-center block"
          >
            Go to Login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Enhanced Glass Navigation Header */}
      <header className="backdrop-blur-xl bg-white/30 border-b border-white/40 shadow-2xl sticky top-0 z-50">
        <div className="w-full px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Left Section - Enhanced Logo */}
            <div className="flex items-center space-x-3 lg:space-x-4 flex-shrink-0">
              <button
                onClick={() => setCurrentPage('landing')}
                className="flex items-center space-x-2 group"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600 rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <span className="text-xl lg:text-2xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                  NexusFlow
                </span>
              </button>
              <div className="hidden sm:flex items-center space-x-2 px-3 py-2 rounded-full backdrop-blur-sm bg-white/40 border border-white/50 shadow-sm">
                <div className={`w-2 h-2 rounded-full ${
                  serverStatus === 'online' ? 'bg-green-500 shadow-sm shadow-green-500/50 animate-pulse' : 
                  serverStatus === 'offline' ? 'bg-red-500 shadow-sm shadow-red-500/50' : 'bg-yellow-500 shadow-sm shadow-yellow-500/50 animate-pulse'
                }`}></div>
                <span className="text-sm text-gray-700 capitalize font-medium">{serverStatus}</span>
              </div>
            </div>
            
            {/* Center Section - Enhanced Navigation */}
            <nav className="flex items-center space-x-1 bg-white/20 backdrop-blur-sm rounded-2xl p-1 border border-white/30 shadow-lg">
              <button
                onClick={() => setCurrentPage('upload')}
                className={`px-3 lg:px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center space-x-1 lg:space-x-2 ${
                  currentPage === 'upload' 
                    ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg transform scale-105' 
                    : 'text-gray-700 hover:text-blue-600 hover:bg-white/50 backdrop-blur-sm hover:scale-105'
                }`}
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                </svg>
                <span className="hidden sm:inline">Upload</span>
              </button>
              <button
                onClick={() => setCurrentPage('files')}
                className={`px-3 lg:px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center space-x-1 lg:space-x-2 ${
                  currentPage === 'files' 
                    ? 'bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-lg transform scale-105' 
                    : 'text-gray-700 hover:text-purple-600 hover:bg-white/50 backdrop-blur-sm hover:scale-105'
                }`}
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                </svg>
                <span className="hidden sm:inline">Files</span>
              </button>
              <button
                onClick={() => setCurrentPage('dashboard')}
                className={`px-3 lg:px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center space-x-1 lg:space-x-2 ${
                  currentPage === 'dashboard' 
                    ? 'bg-gradient-to-r from-green-500 to-teal-600 text-white shadow-lg transform scale-105' 
                    : 'text-gray-700 hover:text-green-600 hover:bg-white/50 backdrop-blur-sm hover:scale-105'
                }`}
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span className="hidden sm:inline">Dashboard</span>
              </button>
              <button
                onClick={() => setCurrentPage('analytics')}
                className={`px-3 lg:px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center space-x-1 lg:space-x-2 ${
                  currentPage === 'analytics' 
                    ? 'bg-gradient-to-r from-orange-500 to-red-600 text-white shadow-lg transform scale-105' 
                    : 'text-gray-700 hover:text-orange-600 hover:bg-white/50 backdrop-blur-sm hover:scale-105'
                }`}
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span className="hidden sm:inline">Analytics</span>
              </button>
              <button
                onClick={() => setCurrentPage('settings')}
                className={`px-3 lg:px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center space-x-1 lg:space-x-2 ${
                  currentPage === 'settings' 
                    ? 'bg-gradient-to-r from-gray-600 to-gray-800 text-white shadow-lg transform scale-105' 
                    : 'text-gray-700 hover:text-gray-600 hover:bg-white/50 backdrop-blur-sm hover:scale-105'
                }`}
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="hidden sm:inline">Settings</span>
              </button>
            </nav>

            {/* Right Section - Enhanced User Menu */}
            <div className="flex items-center space-x-2 lg:space-x-4 flex-shrink-0">
              {/* Notifications */}
              <button className="relative p-2 rounded-xl text-gray-600 hover:text-blue-600 hover:bg-white/50 transition-all duration-300">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5-5V9.09c0-2.89-1.85-4.73-4.7-4.73S5.6 6.2 5.6 9.09V12l-5 5h5m9 0v1a3 3 0 01-6 0v-1m6 0H9" />
                </svg>
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full text-xs flex items-center justify-center">
                  <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span>
                </span>
              </button>
              
              {/* User Avatar */}
              <div className="w-8 h-8 lg:w-10 lg:h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg hover:scale-110 transition-transform duration-300 cursor-pointer">
                <svg className="w-4 h-4 lg:w-5 lg:h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <span className="hidden md:inline text-sm text-gray-700 font-medium max-w-24 truncate">{user?.user?.username || user?.username}</span>
              <button
                onClick={handleLogout}
                className="p-2 rounded-xl text-gray-600 hover:text-red-500 hover:bg-red-50 transition-all duration-300 hover:scale-110"
                title="Logout"
              >
                <svg className="w-4 h-4 lg:w-5 lg:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="min-h-screen relative">
        {/* Enhanced 3D Background Pattern */}
        <div className="absolute inset-0 opacity-10"
             style={{
               backgroundImage: `
                 linear-gradient(rgba(59, 130, 246, 0.15) 1px, transparent 1px),
                 linear-gradient(90deg, rgba(59, 130, 246, 0.15) 1px, transparent 1px),
                 radial-gradient(circle at 25% 25%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
                 radial-gradient(circle at 75% 75%, rgba(59, 130, 246, 0.1) 0%, transparent 50%)
               `,
               backgroundSize: '60px 60px, 60px 60px, 800px 800px, 800px 800px'
             }} />
        
        <div className="relative z-10 w-full px-4 sm:px-6 lg:px-8 py-8">
          {serverStatus === 'offline' && (
            <div className="mb-8 p-6 bg-red-50 border border-red-200 rounded-2xl shadow-sm">
              <div className="flex items-center space-x-3">
                <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-red-700 font-semibold text-lg">Server Offline</span>
              </div>
              <p className="text-red-600 text-sm mt-3 ml-9">
                Connection lost. Please ensure the server is running on port 8000.
              </p>
              <button 
                onClick={checkServerHealth}
                className="mt-4 ml-9 px-4 py-2 bg-red-100 hover:bg-red-200 border border-red-300 rounded-lg text-red-700 text-sm transition-all duration-200"
              >
                Retry Connection
              </button>
            </div>
          )}

          {currentPage === 'upload' && (
            <div className="space-y-6">
              {/* Enhanced 3D Header Card */}
              <div className="relative bg-gradient-to-br from-white via-blue-50/30 to-purple-50/30 rounded-3xl p-8 border border-gray-200 shadow-2xl transform hover:shadow-3xl transition-all duration-500 overflow-hidden"
                   style={{
                     boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.15), 0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(255, 255, 255, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.7)',
                     background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.95) 50%, rgba(243, 244, 246, 0.9) 100%)'
                   }}>
                {/* Animated Background Pattern */}
                <div className="absolute inset-0 opacity-20">
                  <div className="absolute inset-0"
                       style={{
                         backgroundImage: `
                           radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.1) 0%, transparent 50%),
                           radial-gradient(circle at 80% 80%, rgba(147, 51, 234, 0.1) 0%, transparent 50%),
                           radial-gradient(circle at 40% 60%, rgba(236, 72, 153, 0.05) 0%, transparent 50%)
                         `,
                         backgroundSize: '400px 400px, 300px 300px, 500px 500px'
                       }} />
                </div>

                <div className="relative flex items-center justify-between mb-6">
                  <div>
                    <div className="flex items-center space-x-4 mb-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-blue-500 via-purple-600 to-pink-600 rounded-2xl flex items-center justify-center shadow-lg">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                        </svg>
                      </div>
                      <div className="px-4 py-2 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-200 rounded-xl">
                        <span className="text-sm font-bold text-blue-700">File Transfer Hub</span>
                      </div>
                    </div>
                    <h2 className="text-5xl font-black mb-4 transform hover:scale-105 transition-transform duration-300">
                      <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                        Upload Files
                      </span>
                    </h2>
                    <p className="text-gray-700 text-xl leading-relaxed max-w-2xl">
                      Experience lightning-fast, military-grade secure file transfers. 
                      <span className="text-blue-600 font-semibold"> Drag, drop, done.</span>
                    </p>
                  </div>
                  <div className="hidden lg:flex flex-col space-y-4">
                    <div className="flex items-center space-x-2 bg-gradient-to-r from-green-50 to-emerald-50 px-4 py-3 rounded-xl border border-green-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                      <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <span className="font-bold text-green-700">256-bit Encryption</span>
                    </div>
                    <div className="flex items-center space-x-2 bg-gradient-to-r from-blue-50 to-cyan-50 px-4 py-3 rounded-xl border border-blue-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                      <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-lg flex items-center justify-center">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <span className="font-bold text-blue-700">Quantum Speed</span>
                    </div>
                    <div className="flex items-center space-x-2 bg-gradient-to-r from-purple-50 to-pink-50 px-4 py-3 rounded-xl border border-purple-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                      <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                        </svg>
                      </div>
                      <span className="font-bold text-purple-700">100% Reliable</span>
                    </div>
                  </div>
                </div>

                {/* Stats Row for Mobile */}
                <div className="flex lg:hidden justify-center space-x-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center space-x-1 text-xs">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-green-600 font-medium">Secure</span>
                  </div>
                  <div className="flex items-center space-x-1 text-xs">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <span className="text-blue-600 font-medium">Fast</span>
                  </div>
                  <div className="flex items-center space-x-1 text-xs">
                    <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                    <span className="text-purple-600 font-medium">Reliable</span>
                  </div>
                </div>
              </div>
              
              {/* Full Width Upload Area */}
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                <div className="xl:col-span-8">
                  <div className="transform hover:scale-[1.02] transition-all duration-300">
                    <FileUploader />
                  </div>
                </div>
                <div className="xl:col-span-4">
                  <div className="transform hover:scale-[1.02] transition-all duration-300">
                    {/* Upload Guidelines Card */}
                    <div className="bg-gradient-to-br from-white to-gray-50 rounded-2xl border border-gray-200 shadow-lg p-6"
                         style={{
                           boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04), 0 0 0 1px rgba(255, 255, 255, 0.5)'
                         }}>
                      <div className="flex items-center space-x-3 mb-4">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900">Upload Guidelines</h3>
                      </div>
                      
                      <div className="space-y-4">
                        <div className="flex items-start space-x-3">
                          <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">Supported formats</p>
                            <p className="text-xs text-gray-600">PDF, DOCX, XLSX, PPTX, JPG, PNG, ZIP</p>
                          </div>
                        </div>

                        <div className="flex items-start space-x-3">
                          <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2M7 4h10M7 4v16a2 2 0 002 2h6a2 2 0 002-2V4M11 9h2M9 13h6m-6 4h6" />
                            </svg>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">File size limit</p>
                            <p className="text-xs text-gray-600">Maximum 100MB per file</p>
                          </div>
                        </div>

                        <div className="flex items-start space-x-3">
                          <div className="w-5 h-5 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg className="w-3 h-3 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0 0v2m0-2h2m-2 0h-2m6-6a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">Multiple uploads</p>
                            <p className="text-xs text-gray-600">Upload up to 10 files at once</p>
                          </div>
                        </div>

                        <div className="flex items-start space-x-3">
                          <div className="w-5 h-5 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg className="w-3 h-3 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">Security</p>
                            <p className="text-xs text-gray-600">Files are encrypted during transfer</p>
                          </div>
                        </div>
                      </div>

                      <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-200">
                        <div className="flex items-center space-x-2 mb-2">
                          <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                          <span className="text-sm font-semibold text-blue-700">Quick Tip</span>
                        </div>
                        <p className="text-xs text-blue-600">
                          For faster uploads, use a stable internet connection and upload files in smaller batches.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {currentPage === 'files' && (
            <div className="space-y-6">
              {/* 3D Header Card */}
              <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-lg transform hover:shadow-2xl transition-all duration-300"
                   style={{
                     boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04), 0 0 0 1px rgba(255, 255, 255, 0.5)',
                     background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.9) 100%)'
                   }}>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-4xl font-bold mb-3 transform hover:scale-105 transition-transform duration-300">
                      <span className="bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 bg-clip-text text-transparent">
                        Your Files
                      </span>
                    </h2>
                    <p className="text-gray-600 text-lg">
                      Manage and download your uploaded files. View details and organize your content.
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Full Width Grid */}
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                <div className="xl:col-span-8">
                  <div className="transform hover:scale-[1.01] transition-all duration-300">
                    <FileList 
                      onDownload={handleDownload}
                      onDelete={handleDelete}
                    />
                  </div>
                </div>
                <div className="xl:col-span-4">
                  <div className="transform hover:scale-[1.02] transition-all duration-300">
                    <StorageInfo />
                  </div>
                </div>
              </div>
            </div>
          )}

          {currentPage === 'dashboard' && (
            <div className="space-y-8">
              {/* Enhanced 3D Header */}
              <div className="relative bg-gradient-to-br from-green-50 to-blue-50 rounded-3xl p-8 border border-green-200 shadow-2xl transform hover:shadow-3xl transition-all duration-500"
                   style={{
                     boxShadow: '0 25px 50px -12px rgba(34, 197, 94, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.6)',
                     background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%)'
                   }}>
                <div className="absolute inset-0 bg-gradient-to-r from-green-400/5 to-blue-400/5 rounded-3xl"></div>
                <div className="relative flex items-center justify-between mb-6">
                  <div>
                    <h1 className="text-5xl font-black mb-4 transform hover:scale-105 transition-transform duration-300">
                      <span className="bg-gradient-to-r from-green-600 via-teal-600 to-blue-600 bg-clip-text text-transparent">
                        Storage Dashboard
                      </span>
                    </h1>
                    <p className="text-gray-700 text-xl leading-relaxed">
                      Real-time monitoring of your browser storage, file management, and data analytics
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="hidden md:flex items-center space-x-2 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-xl shadow-lg border border-white/50">
                      <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse shadow-sm"></div>
                      <span className="text-sm font-medium text-gray-700">Live Data</span>
                    </div>
                    <button
                      onClick={() => window.location.reload()}
                      className="flex items-center space-x-2 px-6 py-3 bg-white/90 backdrop-blur-sm hover:bg-white border border-gray-200 rounded-xl text-gray-700 font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-lg"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <span>Refresh Data</span>
                    </button>
                  </div>
                </div>
              </div>

              {(() => {
                const stats = getLocalStorageStats();
                const uploadedFiles = JSON.parse(localStorage.getItem('uploadedFiles') || '[]');
                const totalFileSize = uploadedFiles.reduce((sum, file) => sum + (file.size || 0), 0);
                
                return (
                  <div className="space-y-8">
                    {/* Enhanced 3D Storage Overview Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8">
                      {/* Storage Used Card */}
                      <div className="group bg-gradient-to-br from-blue-50 to-indigo-100 rounded-3xl p-8 border border-blue-200 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
                           style={{
                             boxShadow: '0 20px 25px -5px rgba(59, 130, 246, 0.1), 0 10px 10px -5px rgba(59, 130, 246, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
                           }}>
                        <div className="flex items-center space-x-4 mb-6">
                          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg transform group-hover:rotate-3 transition-transform duration-300">
                            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                            </svg>
                          </div>
                          <div>
                            <h3 className="text-xl font-bold text-gray-800 mb-1">Storage Used</h3>
                            <p className="text-4xl font-black text-blue-600 leading-none">{stats.usedMB}</p>
                            <p className="text-sm text-blue-500 font-medium">MB</p>
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="flex justify-between items-center">
                            <span className="text-sm font-medium text-gray-600">Usage</span>
                            <span className="text-sm font-bold text-blue-600">{stats.usagePercent}%</span>
                          </div>
                          <div className="w-full bg-white/60 rounded-full h-3 shadow-inner">
                            <div className="bg-gradient-to-r from-blue-500 to-indigo-600 h-3 rounded-full transition-all duration-500 shadow-sm" 
                                 style={{ width: `${Math.min(stats.usagePercent, 100)}%` }}></div>
                          </div>
                          <p className="text-xs text-gray-500">of ~{stats.maxMB}MB browser limit</p>
                        </div>
                      </div>

                      {/* Total Items Card */}
                      <div className="group bg-gradient-to-br from-green-50 to-emerald-100 rounded-3xl p-8 border border-green-200 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
                           style={{
                             boxShadow: '0 20px 25px -5px rgba(34, 197, 94, 0.1), 0 10px 10px -5px rgba(34, 197, 94, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
                           }}>
                        <div className="flex items-center space-x-4 mb-6">
                          <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center shadow-lg transform group-hover:rotate-3 transition-transform duration-300">
                            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                            </svg>
                          </div>
                          <div>
                            <h3 className="text-xl font-bold text-gray-800 mb-1">Total Items</h3>
                            <p className="text-4xl font-black text-green-600 leading-none">{stats.itemCount}</p>
                            <p className="text-sm text-green-500 font-medium">keys</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm text-gray-600">Stored in browser</p>
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                            <span className="text-xs text-green-600 font-medium">Active Storage</span>
                          </div>
                        </div>
                      </div>

                      {/* Files Count Card */}
                      <div className="group bg-gradient-to-br from-purple-50 to-violet-100 rounded-3xl p-8 border border-purple-200 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
                           style={{
                             boxShadow: '0 20px 25px -5px rgba(147, 51, 234, 0.1), 0 10px 10px -5px rgba(147, 51, 234, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
                           }}>
                        <div className="flex items-center space-x-4 mb-6">
                          <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-violet-600 rounded-2xl flex items-center justify-center shadow-lg transform group-hover:rotate-3 transition-transform duration-300">
                            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </div>
                          <div>
                            <h3 className="text-xl font-bold text-gray-800 mb-1">Files Count</h3>
                            <p className="text-4xl font-black text-purple-600 leading-none">{uploadedFiles.length}</p>
                            <p className="text-sm text-purple-500 font-medium">files</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm text-gray-600">Uploaded files</p>
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-purple-600 font-medium">Total Size:</span>
                            <span className="text-sm font-bold text-purple-600">{(totalFileSize / (1024 * 1024)).toFixed(2)} MB</span>
                          </div>
                        </div>
                      </div>

                      {/* Last Activity Card */}
                      <div className="group bg-gradient-to-br from-orange-50 to-amber-100 rounded-3xl p-8 border border-orange-200 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
                           style={{
                             boxShadow: '0 20px 25px -5px rgba(245, 101, 101, 0.1), 0 10px 10px -5px rgba(245, 101, 101, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
                           }}>
                        <div className="flex items-center space-x-4 mb-6">
                          <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-amber-600 rounded-2xl flex items-center justify-center shadow-lg transform group-hover:rotate-3 transition-transform duration-300">
                            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          </div>
                          <div>
                            <h3 className="text-xl font-bold text-gray-800 mb-1">Last Activity</h3>
                            <p className="text-lg font-bold text-orange-600 leading-tight">
                              {user?.created_at ? new Date(user.created_at).toLocaleTimeString() : 'N/A'}
                            </p>
                            <p className="text-sm text-orange-500 font-medium">login time</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm text-gray-600">Session started</p>
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
                            <span className="text-xs text-orange-600 font-medium">Active</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Large Storage Visualization */}
                    <div className="bg-gradient-to-br from-white to-gray-50 rounded-3xl border border-gray-200 shadow-2xl overflow-hidden transform hover:shadow-3xl transition-all duration-500"
                         style={{
                           boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
                         }}>
                      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6">
                        <div className="flex items-center justify-between">
                          <div>
                            <h2 className="text-2xl font-bold text-white mb-2">Storage Analytics</h2>
                            <p className="text-indigo-100">Detailed breakdown of your browser storage</p>
                          </div>
                          <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3">
                            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                          </div>
                        </div>
                      </div>

                      <div className="p-8">
                        {/* Advanced Storage Table */}
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="border-b border-gray-200">
                                <th className="text-left pb-4 font-bold text-gray-700">Storage Key</th>
                                <th className="text-left pb-4 font-bold text-gray-700">Size (bytes)</th>
                                <th className="text-left pb-4 font-bold text-gray-700">Data Preview</th>
                                <th className="text-left pb-4 font-bold text-gray-700">Actions</th>
                              </tr>
                            </thead>
                            <tbody className="space-y-2">
                              {stats.items.map((item, index) => (
                                <tr key={index} className="group hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 transition-all duration-200 border-b border-gray-100">
                                  <td className="py-4 pr-4">
                                    <div className="flex items-center space-x-3">
                                      <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m0 0a2 2 0 012 2m-2-2h-6m6 0v6a2 2 0 01-2 2H9a2 2 0 01-2-2V9a2 2 0 012-2h2M7 7V5a2 2 0 012-2h6a2 2 0 012 2v2H7z" />
                                        </svg>
                                      </div>
                                      <div>
                                        <p className="font-semibold text-gray-900 text-sm">{item.key}</p>
                                        <p className="text-xs text-gray-500">{item.key.includes('Files') ? 'File Data' : 'App Data'}</p>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="py-4 pr-4">
                                    <div className="flex items-center space-x-2">
                                      <span className="text-sm font-bold text-gray-700">{item.size.toLocaleString()}</span>
                                      <div className="w-20 bg-gray-200 rounded-full h-2">
                                        <div className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full" 
                                             style={{ width: `${Math.min((item.size / Math.max(...stats.items.map(i => i.size))) * 100, 100)}%` }}></div>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="py-4 pr-4">
                                    <div className="bg-gray-100 rounded-lg p-3 max-w-xs">
                                      <code className="text-xs text-gray-600 break-all">{item.value}</code>
                                    </div>
                                  </td>
                                  <td className="py-4">
                                    <button
                                      onClick={() => {
                                        if (confirm(`Delete "${item.key}"? This action cannot be undone.`)) {
                                          localStorage.removeItem(item.key);
                                          window.location.reload();
                                        }
                                      }}
                                      className="group-hover:opacity-100 opacity-0 px-4 py-2 bg-red-50 hover:bg-red-100 border border-red-200 text-red-600 rounded-lg text-xs font-medium transition-all duration-200 transform hover:scale-105"
                                    >
                                      Delete
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {currentPage === 'analytics' && (
            <div className="space-y-8">
              {/* Analytics Header */}
              <div className="relative bg-gradient-to-br from-orange-50 to-red-50 rounded-3xl p-8 border border-orange-200 shadow-2xl transform hover:shadow-3xl transition-all duration-500"
                   style={{
                     boxShadow: '0 25px 50px -12px rgba(245, 101, 101, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.6)',
                     background: 'linear-gradient(135deg, rgba(251, 146, 60, 0.05) 0%, rgba(239, 68, 68, 0.05) 100%)'
                   }}>
                <div className="absolute inset-0 bg-gradient-to-r from-orange-400/5 to-red-400/5 rounded-3xl"></div>
                <div className="relative flex items-center justify-between mb-6">
                  <div>
                    <h1 className="text-5xl font-black mb-4 transform hover:scale-105 transition-transform duration-300">
                      <span className="bg-gradient-to-r from-orange-600 via-red-600 to-pink-600 bg-clip-text text-transparent">
                        File Analytics
                      </span>
                    </h1>
                    <p className="text-gray-700 text-xl leading-relaxed">
                      Detailed insights and statistics about your file uploads and usage patterns
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="hidden md:flex items-center space-x-2 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-xl shadow-lg border border-white/50">
                      <div className="w-3 h-3 bg-orange-500 rounded-full animate-pulse shadow-sm"></div>
                      <span className="text-sm font-medium text-gray-700">Live Analytics</span>
                    </div>
                  </div>
                </div>
              </div>

              {(() => {
                const uploadedFiles = JSON.parse(localStorage.getItem('uploadedFiles') || '[]');
                const fileTypes = uploadedFiles.reduce((acc, file) => {
                  const ext = file.name?.split('.').pop()?.toLowerCase() || 'unknown';
                  acc[ext] = (acc[ext] || 0) + 1;
                  return acc;
                }, {});
                
                const totalSize = uploadedFiles.reduce((sum, file) => sum + (file.size || 0), 0);
                const avgFileSize = uploadedFiles.length > 0 ? totalSize / uploadedFiles.length : 0;
                
                return (
                  <div className="space-y-8">
                    {/* Analytics Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                      {/* Upload Trends */}
                      <div className="bg-gradient-to-br from-blue-50 to-cyan-100 rounded-3xl p-6 border border-blue-200 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-300">
                        <div className="flex items-center space-x-4 mb-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                            </svg>
                          </div>
                          <div>
                            <h3 className="text-lg font-bold text-gray-800">Upload Trends</h3>
                            <p className="text-sm text-gray-600">Recent activity</p>
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">This Session</span>
                            <span className="text-lg font-bold text-blue-600">{uploadedFiles.length}</span>
                          </div>
                          <div className="w-full bg-white/60 rounded-full h-2">
                            <div className="bg-gradient-to-r from-blue-500 to-cyan-600 h-2 rounded-full" 
                                 style={{ width: `${Math.min(uploadedFiles.length * 10, 100)}%` }}></div>
                          </div>
                        </div>
                      </div>

                      {/* File Types Distribution */}
                      <div className="bg-gradient-to-br from-purple-50 to-pink-100 rounded-3xl p-6 border border-purple-200 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-300">
                        <div className="flex items-center space-x-4 mb-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                          </div>
                          <div>
                            <h3 className="text-lg font-bold text-gray-800">File Types</h3>
                            <p className="text-sm text-gray-600">Distribution</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          {Object.entries(fileTypes).slice(0, 3).map(([type, count]) => (
                            <div key={type} className="flex justify-between items-center">
                              <span className="text-sm text-gray-600 uppercase">{type}</span>
                              <div className="flex items-center space-x-2">
                                <div className="w-16 bg-white/60 rounded-full h-2">
                                  <div className="bg-gradient-to-r from-purple-500 to-pink-600 h-2 rounded-full" 
                                       style={{ width: `${(count / uploadedFiles.length) * 100}%` }}></div>
                                </div>
                                <span className="text-sm font-bold text-purple-600">{count}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Performance Metrics */}
                      <div className="bg-gradient-to-br from-green-50 to-teal-100 rounded-3xl p-6 border border-green-200 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-300">
                        <div className="flex items-center space-x-4 mb-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-teal-600 rounded-xl flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                          </div>
                          <div>
                            <h3 className="text-lg font-bold text-gray-800">Performance</h3>
                            <p className="text-sm text-gray-600">Average metrics</p>
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Avg File Size</span>
                            <span className="text-sm font-bold text-green-600">{(avgFileSize / (1024 * 1024)).toFixed(2)} MB</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Success Rate</span>
                            <span className="text-sm font-bold text-green-600">100%</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Detailed Analytics Charts */}
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                      {/* File Size Distribution Chart */}
                      <div className="bg-white rounded-3xl border border-gray-200 shadow-xl p-6">
                        <div className="flex items-center justify-between mb-6">
                          <h3 className="text-2xl font-bold text-gray-800">File Size Distribution</h3>
                          <div className="bg-blue-50 px-3 py-1 rounded-lg">
                            <span className="text-sm text-blue-600 font-medium">{uploadedFiles.length} files</span>
                          </div>
                        </div>
                        <div className="space-y-4">
                          {uploadedFiles.slice(0, 5).map((file, index) => {
                            const sizePercent = totalSize > 0 ? ((file.size || 0) / totalSize) * 100 : 0;
                            return (
                              <div key={index} className="space-y-2">
                                <div className="flex justify-between items-center">
                                  <span className="text-sm font-medium text-gray-700 truncate max-w-48">{file.name || 'Unknown'}</span>
                                  <span className="text-sm text-gray-600">{((file.size || 0) / (1024 * 1024)).toFixed(2)} MB</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full transition-all duration-500" 
                                       style={{ width: `${sizePercent}%` }}></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* File Type Analysis */}
                      <div className="bg-white rounded-3xl border border-gray-200 shadow-xl p-6">
                        <div className="flex items-center justify-between mb-6">
                          <h3 className="text-2xl font-bold text-gray-800">File Type Analysis</h3>
                          <div className="bg-purple-50 px-3 py-1 rounded-lg">
                            <span className="text-sm text-purple-600 font-medium">{Object.keys(fileTypes).length} types</span>
                          </div>
                        </div>
                        <div className="space-y-4">
                          {Object.entries(fileTypes).map(([type, count], index) => {
                            const typePercent = uploadedFiles.length > 0 ? (count / uploadedFiles.length) * 100 : 0;
                            const colors = ['from-red-500 to-pink-600', 'from-blue-500 to-indigo-600', 'from-green-500 to-teal-600', 'from-yellow-500 to-orange-600', 'from-purple-500 to-violet-600'];
                            return (
                              <div key={type} className="space-y-2">
                                <div className="flex justify-between items-center">
                                  <div className="flex items-center space-x-2">
                                    <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${colors[index % colors.length]}`}></div>
                                    <span className="text-sm font-medium text-gray-700 uppercase">{type}</span>
                                  </div>
                                  <span className="text-sm text-gray-600">{count} files ({typePercent.toFixed(1)}%)</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div className={`bg-gradient-to-r ${colors[index % colors.length]} h-2 rounded-full transition-all duration-500`}
                                       style={{ width: `${typePercent}%` }}></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {currentPage === 'settings' && (
            <div className="space-y-8">
              {/* Settings Header */}
              <div className="relative bg-gradient-to-br from-gray-50 to-slate-100 rounded-3xl p-8 border border-gray-200 shadow-2xl transform hover:shadow-3xl transition-all duration-500"
                   style={{
                     boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.6)',
                     background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.03) 0%, rgba(0, 0, 0, 0.08) 100%)'
                   }}>
                <div className="relative flex items-center justify-between mb-6">
                  <div>
                    <h1 className="text-5xl font-black mb-4 transform hover:scale-105 transition-transform duration-300">
                      <span className="bg-gradient-to-r from-gray-700 via-gray-800 to-black bg-clip-text text-transparent">
                        Settings & Preferences
                      </span>
                    </h1>
                    <p className="text-gray-700 text-xl leading-relaxed">
                      Customize your NexusFlow experience and manage application settings
                    </p>
                  </div>
                  <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-4 shadow-lg">
                    <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {/* Upload Settings */}
                <div className="bg-white rounded-3xl border border-gray-200 shadow-xl p-8">
                  <div className="flex items-center space-x-4 mb-6">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                      </svg>
                    </div>
                    <h3 className="text-2xl font-bold text-gray-800">Upload Settings</h3>
                  </div>
                  <div className="space-y-6">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                      <div>
                        <h4 className="font-semibold text-gray-800">Auto-Upload</h4>
                        <p className="text-sm text-gray-600">Automatically upload files when dropped</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" defaultChecked />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                      <div>
                        <h4 className="font-semibold text-gray-800">Chunk Upload</h4>
                        <p className="text-sm text-gray-600">Split large files into chunks for faster upload</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" defaultChecked />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Maximum File Size (MB)</label>
                      <input type="range" min="1" max="100" defaultValue="100" className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>1 MB</span>
                        <span>100 MB</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* UI Preferences */}
                <div className="bg-white rounded-3xl border border-gray-200 shadow-xl p-8">
                  <div className="flex items-center space-x-4 mb-6">
                    <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17v4a2 2 0 002 2h4M13 13h4a2 2 0 012 2v4a2 2 0 01-2 2h-4m-6-4a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <h3 className="text-2xl font-bold text-gray-800">Interface</h3>
                  </div>
                  <div className="space-y-6">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                      <div>
                        <h4 className="font-semibold text-gray-800">Dark Mode</h4>
                        <p className="text-sm text-gray-600">Switch to dark theme</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                      <div>
                        <h4 className="font-semibold text-gray-800">Animations</h4>
                        <p className="text-sm text-gray-600">Enable smooth transitions and effects</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" defaultChecked />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">UI Scale</label>
                      <select className="w-full p-3 border border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent" defaultValue="Normal (100%)">
                        <option>Small (90%)</option>
                        <option>Normal (100%)</option>
                        <option>Large (110%)</option>
                        <option>Extra Large (125%)</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Storage Management */}
                <div className="bg-white rounded-3xl border border-gray-200 shadow-xl p-8">
                  <div className="flex items-center space-x-4 mb-6">
                    <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-teal-600 rounded-xl flex items-center justify-center">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                      </svg>
                    </div>
                    <h3 className="text-2xl font-bold text-gray-800">Storage</h3>
                  </div>
                  <div className="space-y-6">
                    <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-xl">
                      <div className="flex items-center space-x-3 mb-3">
                        <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                        </svg>
                        <span className="font-semibold text-yellow-800">Storage Warning</span>
                      </div>
                      <p className="text-yellow-700 text-sm">Browser storage is limited. Consider clearing old data regularly.</p>
                    </div>
                    <div className="space-y-3">
                      <button 
                        onClick={() => {
                          if (confirm('Clear all upload history? This cannot be undone.')) {
                            localStorage.removeItem('uploadedFiles');
                            window.location.reload();
                          }
                        }}
                        className="w-full p-3 bg-red-50 hover:bg-red-100 border border-red-200 text-red-600 rounded-xl font-medium transition-all duration-200"
                      >
                        Clear Upload History
                      </button>
                      <button 
                        onClick={() => {
                          if (confirm('Reset all settings to default? This cannot be undone.')) {
                            localStorage.clear();
                            window.location.reload();
                          }
                        }}
                        className="w-full p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-600 rounded-xl font-medium transition-all duration-200"
                      >
                        Reset All Settings
                      </button>
                    </div>
                  </div>
                </div>

                {/* Account & Security */}
                <div className="bg-white rounded-3xl border border-gray-200 shadow-xl p-8">
                  <div className="flex items-center space-x-4 mb-6">
                    <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-pink-600 rounded-xl flex items-center justify-center">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                    </div>
                    <h3 className="text-2xl font-bold text-gray-800">Security</h3>
                  </div>
                  <div className="space-y-6">
                    <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
                      <div className="flex items-center space-x-3 mb-2">
                        <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-semibold text-green-800">Secure Connection</span>
                      </div>
                      <p className="text-green-700 text-sm">All file transfers are encrypted and secure</p>
                    </div>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium text-gray-700">Current User</span>
                        <span className="text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-lg">{user?.user?.username || user?.username}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium text-gray-700">Login Time</span>
                        <span className="text-sm text-gray-600">{user?.created_at ? new Date(user.created_at).toLocaleString() : 'N/A'}</span>
                      </div>
                      <button 
                        onClick={handleLogout}
                        className="w-full p-3 bg-red-50 hover:bg-red-100 border border-red-200 text-red-600 rounded-xl font-medium transition-all duration-200 mt-4"
                      >
                        Sign Out
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Actions Panel */}
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-3xl border border-indigo-200 shadow-xl p-8">
                <h3 className="text-2xl font-bold text-gray-800 mb-6">Quick Actions</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button 
                    onClick={() => setCurrentPage('upload')}
                    className="flex items-center space-x-3 p-4 bg-white hover:bg-blue-50 border border-blue-200 rounded-xl transition-all duration-200 group"
                  >
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                    </svg>
                    <span className="font-medium text-gray-700 group-hover:text-blue-600">Upload Files</span>
                  </button>
                  <button 
                    onClick={() => setCurrentPage('dashboard')}
                    className="flex items-center space-x-3 p-4 bg-white hover:bg-green-50 border border-green-200 rounded-xl transition-all duration-200 group"
                  >
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    <span className="font-medium text-gray-700 group-hover:text-green-600">View Dashboard</span>
                  </button>
                  <button 
                    onClick={() => window.location.reload()}
                    className="flex items-center space-x-3 p-4 bg-white hover:bg-purple-50 border border-purple-200 rounded-xl transition-all duration-200 group"
                  >
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span className="font-medium text-gray-700 group-hover:text-purple-600">Refresh App</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="w-full px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between space-y-4 md:space-y-0">
            <div className="flex items-center space-x-3">
              <svg className="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <p className="text-gray-700 text-sm">
                <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent font-semibold text-lg">
                  NexusFlow Transfer
                </span>
              </p>
            </div>
            <div className="flex flex-col md:flex-row items-center space-y-2 md:space-y-0 md:space-x-6 text-sm text-gray-600">
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
                <span className="font-medium">FastAPI + WebSocket</span>
              </div>
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                <span className="font-medium">Next.js + React</span>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}