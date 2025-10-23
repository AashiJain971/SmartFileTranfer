'use client';

import { AuthProvider } from '../contexts/AuthContext';

export default function ClientLayout({ children }) {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  );
}