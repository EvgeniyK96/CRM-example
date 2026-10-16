import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
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

const fetchMe = () => api.get<User>('/auth/users/me/').then((r) => r.data)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!tokens.access)

  useEffect(() => {
    if (!tokens.access) return
    fetchMe()
      .then(setUser)
      .catch(() => tokens.clear())
      .finally(() => setLoading(false))
  }, [])

  const login = async (username: string, password: string) => {
    const { data } = await api.post('/auth/jwt/create/', { username, password })
    tokens.set(data.access, data.refresh)
    setUser(await fetchMe())
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
