'use client';

import { useState, useEffect } from 'react';

export default function LandingPage({ onNavigate, serverStatus }) {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
    
    const handleMouseMove = (e) => {
      setMousePosition({
        x: (e.clientX / window.innerWidth) * 100,
        y: (e.clientY / window.innerHeight) * 100
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const features = [
    {
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      title: 'Hyper-Speed Transfer',
      description: 'Quantum-optimized chunking for lightning-fast uploads'
    },
    {
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
      title: 'Neural Security',
      description: 'AI-powered hash verification and integrity protection'
    },
    {
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
        </svg>
      ),
      title: 'Adaptive Flow',
      description: 'Smart network adaptation with real-time optimization'
    },
    {
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      ),
      title: 'Zero-Downtime',
      description: 'Resilient architecture with automatic retry systems'
    }
  ];

  return (
    <div className="min-h-screen bg-black relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0">
        {/* Gradient Orbs */}
        <div 
          className="absolute w-96 h-96 rounded-full opacity-30 blur-3xl transition-all duration-1000"
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            left: `${mousePosition.x * 0.1}%`,
            top: `${mousePosition.y * 0.1}%`,
          }}
        />
        <div 
          className="absolute w-80 h-80 rounded-full opacity-20 blur-3xl transition-all duration-1500"
          style={{
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            right: `${mousePosition.x * 0.05}%`,
            bottom: `${mousePosition.y * 0.05}%`,
          }}
        />
        <div 
          className="absolute w-72 h-72 rounded-full opacity-25 blur-3xl transition-all duration-2000"
          style={{
            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            left: `${50 + mousePosition.x * 0.03}%`,
            top: `${30 + mousePosition.y * 0.03}%`,
          }}
        />
        
        {/* Grid Pattern */}
        <div 
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(59, 130, 246, 0.5) 1px, transparent 1px),
              linear-gradient(90deg, rgba(59, 130, 246, 0.5) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
            transform: `translate(${mousePosition.x * 0.01}px, ${mousePosition.y * 0.01}px)`
          }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Navigation */}
        <nav className="p-6">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 bg-clip-text text-transparent">
              NexusFlow
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                serverStatus === 'online' ? 'bg-green-400 shadow-lg shadow-green-400/50' : 
                serverStatus === 'offline' ? 'bg-red-400 shadow-lg shadow-red-400/50' : 
                'bg-yellow-400 shadow-lg shadow-yellow-400/50'
              }`}></div>
              <span className="text-gray-300 text-sm">{serverStatus}</span>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center max-w-5xl mx-auto">
            {/* Main Title */}
            <h1 className={`text-6xl md:text-8xl font-black mb-8 transition-all duration-2000 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            }`}>
              <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent animate-pulse">
                NexusFlow
              </span>
              <br />
              <span className="bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-transparent">
                Transfer
              </span>
            </h1>

            {/* Subtitle */}
            <p className={`text-xl md:text-2xl text-gray-300 mb-12 leading-relaxed transition-all duration-2000 delay-300 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            }`}>
              <span className="bg-gradient-to-r from-blue-300 to-purple-300 bg-clip-text text-transparent">
                Next-generation quantum file transfer technology
              </span>
              <br />
              Built for the future, delivering at light speed
            </p>

            {/* CTA Buttons */}
            <div className={`flex flex-col sm:flex-row gap-6 justify-center items-center mb-16 transition-all duration-2000 delay-500 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            }`}>
              <button
                onClick={() => onNavigate('upload')}
                className="group relative px-10 py-5 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full text-white font-bold text-xl hover:scale-105 transition-all duration-300 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40"
              >
                <div className="flex items-center space-x-3">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <span className="relative z-10">Get Started</span>
                </div>
                <div className="absolute inset-0 bg-gradient-to-r from-blue-700 to-purple-700 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              </button>
              
              <button
                onClick={() => onNavigate('files')}
                className="group relative px-8 py-4 border-2 border-purple-500 rounded-full text-purple-300 font-semibold text-lg hover:bg-purple-500 hover:text-white transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25"
              >
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2 2z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2" />
                  </svg>
                  <span>View Files</span>
                </div>
              </button>
            </div>

            {/* Features Grid */}
            <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 transition-all duration-2000 delay-700 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            }`}>
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="group p-8 rounded-3xl backdrop-blur-xl bg-white/5 border border-white/10 hover:border-purple-500/30 transition-all duration-500 hover:scale-105 hover:shadow-2xl hover:shadow-purple-500/20 hover:bg-white/10"
                >
                  <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-white/10 backdrop-blur-sm mb-6 text-blue-400 group-hover:text-purple-400 group-hover:scale-110 transition-all duration-300">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-bold mb-4 bg-gradient-to-r from-blue-300 to-purple-300 bg-clip-text text-transparent">
                    {feature.title}
                  </h3>
                  <p className="text-gray-300 text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Stats Section */}
        <div className="py-16 px-6">
          <div className="max-w-5xl mx-auto">
            <div className={`grid grid-cols-1 md:grid-cols-3 gap-8 transition-all duration-2000 delay-1000 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            }`}>
              <div className="p-8 rounded-3xl backdrop-blur-xl bg-white/5 border border-white/10 text-center hover:bg-white/10 transition-all duration-500">
                <div className="text-5xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent mb-4">
                  99.9%
                </div>
                <div className="text-gray-300 text-lg font-medium">Transfer Success Rate</div>
                <div className="text-gray-500 text-sm mt-2">Quantum-verified reliability</div>
              </div>
              <div className="p-8 rounded-3xl backdrop-blur-xl bg-white/5 border border-white/10 text-center hover:bg-white/10 transition-all duration-500">
                <div className="text-5xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent mb-4">
                  10GB/s
                </div>
                <div className="text-gray-300 text-lg font-medium">Peak Transfer Speed</div>
                <div className="text-gray-500 text-sm mt-2">Neural-optimized throughput</div>
              </div>
              <div className="p-8 rounded-3xl backdrop-blur-xl bg-white/5 border border-white/10 text-center hover:bg-white/10 transition-all duration-500">
                <div className="text-5xl font-bold bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent mb-4">
                  24/7
                </div>
                <div className="text-gray-300 text-lg font-medium">Quantum Uptime</div>
                <div className="text-gray-500 text-sm mt-2">Continuous neural monitoring</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}