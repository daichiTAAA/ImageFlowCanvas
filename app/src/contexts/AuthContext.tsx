import React, { createContext, useContext, useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';

interface User {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  role: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

interface RegisterData {
  username: string;
  email?: string;
  password: string;
  full_name?: string;
  role?: string;
}

interface AuthResponse {
  token: string;
  user: User;
  expires_at: number;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for stored authentication on component mount
    const checkStoredAuth = async () => {
      try {
        const storedToken = localStorage.getItem('auth_token');
        const storedUser = localStorage.getItem('auth_user');
        
        if (storedToken && storedUser) {
          // Verify token is still valid
          const expiresAt = localStorage.getItem('auth_expires_at');
          if (expiresAt && parseInt(expiresAt) > Date.now() / 1000) {
            setToken(storedToken);
            setUser(JSON.parse(storedUser));
          } else {
            // Token expired, clear storage
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
            localStorage.removeItem('auth_expires_at');
          }
        }
      } catch (error) {
        console.error('Error checking stored auth:', error);
      } finally {
        setLoading(false);
      }
    };

    checkStoredAuth();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await invoke('login', {
        credentials: { username, password }
      }) as AuthResponse;

      setUser(response.user);
      setToken(response.token);

      // Store authentication data
      localStorage.setItem('auth_token', response.token);
      localStorage.setItem('auth_user', JSON.stringify(response.user));
      localStorage.setItem('auth_expires_at', response.expires_at.toString());
    } catch (error) {
      throw new Error(`Login failed: ${error}`);
    }
  };

  const register = async (userData: RegisterData) => {
    try {
      const response = await invoke('register', {
        request: userData
      }) as AuthResponse;

      setUser(response.user);
      setToken(response.token);

      // Store authentication data
      localStorage.setItem('auth_token', response.token);
      localStorage.setItem('auth_user', JSON.stringify(response.user));
      localStorage.setItem('auth_expires_at', response.expires_at.toString());
    } catch (error) {
      throw new Error(`Registration failed: ${error}`);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    
    // Clear stored authentication data
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    localStorage.removeItem('auth_expires_at');
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    register,
    logout,
    isAuthenticated: !!user && !!token,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};