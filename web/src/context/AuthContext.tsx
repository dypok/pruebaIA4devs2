import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserSession } from '../types';
import { loginApi } from '../services/api';

interface AuthContextType {
  user: UserSession | null;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession | null>(() => {
    const savedToken = localStorage.getItem('sismowatch_token');
    const savedUser = localStorage.getItem('sismowatch_user');
    const savedRole = localStorage.getItem('sismowatch_role') as 'viewer' | 'admin' | null;

    if (savedToken && savedToken.split('.').length === 3 && savedUser && savedRole) {
      return { username: savedUser, role: savedRole, token: savedToken };
    }
    return null;
  });

  const login = async (username: string, pass: string) => {
    const data = await loginApi(username, pass);
    const session: UserSession = {
      username: data.username,
      role: data.role,
      token: data.access_token,
    };
    localStorage.setItem('sismowatch_token', data.access_token);
    localStorage.setItem('sismowatch_user', data.username);
    localStorage.setItem('sismowatch_role', data.role);
    setUser(session);
  };

  const logout = () => {
    localStorage.removeItem('sismowatch_token');
    localStorage.removeItem('sismowatch_user');
    localStorage.removeItem('sismowatch_role');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'admin',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth debe ser utilizado dentro de un AuthProvider');
  return context;
};
