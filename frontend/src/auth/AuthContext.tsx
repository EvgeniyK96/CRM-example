import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, tokens } from '../api/client'
import type { Role, User } from '../api/types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  can: (...roles: Role[]) => boolean
}

const AuthContext = createContext<AuthState>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!tokens.access)

  const loadMe = useCallback(async () => {
    const { data } = await api.get<User>('/auth/users/me/')
    setUser(data)
  }, [])

  useEffect(() => {
    if (!tokens.access) return
    loadMe().catch(() => tokens.clear()).finally(() => setLoading(false))
  }, [loadMe])

  const login = async (username: string, password: string) => {
    const { data } = await api.post('/auth/jwt/create/', { username, password })
    tokens.set(data.access, data.refresh)
    await loadMe()
  }

  const logout = () => {
    tokens.clear()
    setUser(null)
  }

  const can = (...roles: Role[]) => !!user && (user.role === 'admin' || roles.includes(user.role))

  return <AuthContext.Provider value={{ user, loading, login, logout, can }}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext)
