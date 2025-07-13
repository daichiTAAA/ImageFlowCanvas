import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, LoginRequest } from '../types'
import { apiService } from './api'

interface AuthContextType {
  user: User | null
  login: (loginData: LoginRequest) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      // Verify token and get user info
      apiService.getCurrentUser()
        .then((userData) => {
          setUser(userData)
        })
        .catch(() => {
          localStorage.removeItem('access_token')
        })
        .finally(() => {
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (loginData: LoginRequest) => {
    try {
      const response = await apiService.login(loginData)
      localStorage.setItem('access_token', response.access_token)
      
      const userData = await apiService.getCurrentUser()
      setUser(userData)
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    setUser(null)
    apiService.logout().catch(() => {}) // Silent fail
  }

  const value = {
    user,
    login,
    logout,
    isAuthenticated: !!user,
    loading
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}