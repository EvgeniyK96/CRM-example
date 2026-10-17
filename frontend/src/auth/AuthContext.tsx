import { isAxiosError } from 'axios'
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, tokens } from '../api/client'
import type { Role, User } from '../api/types'

interface AuthState {
  user: User | null
  loading: boolean
  /** Сервер не ответил при загрузке профиля (сессия при этом сохраняется) */
  unavailable: boolean
  retry: () => void
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  can: (...roles: Role[]) => boolean
  /** Может ли пользователь управлять заданиями цеха (начальник цеха — только своего) */
  canManageDepartment: (departmentId: number) => boolean
}

const AuthContext = createContext<AuthState>(null!)

const fetchMe = () => api.get<User>('/auth/users/me/').then((r) => r.data)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!tokens.access)
  const [unavailable, setUnavailable] = useState(false)

  const load = useCallback(() => {
    if (!tokens.access) return
    fetchMe()
      .then((me) => {
        setUser(me)
        setUnavailable(false)
      })
      .catch((e) => {
        // Выходим только если сервер отверг токен; при недоступности сервера (перезапуск, сеть) сессию не теряем
        if (isAxiosError(e) && e.response?.status === 401) tokens.clear()
        else setUnavailable(true)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const retry = () => {
    setLoading(true)
    load()
  }

  const login = async (username: string, password: string) => {
    const { data } = await api.post('/auth/jwt/create/', { username, password })
    tokens.set(data.access, data.refresh)
    setUser(await fetchMe())
    setUnavailable(false)
  }

  const logout = () => {
    tokens.clear()
    setUser(null)
    setUnavailable(false)
  }

  const can = (...roles: Role[]) => !!user && (user.role === 'admin' || roles.includes(user.role))

  const canManageDepartment = (departmentId: number) =>
    can('shop_head') && (user?.role !== 'shop_head' || !user.production_department || user.production_department === departmentId)

  return (
    <AuthContext.Provider value={{ user, loading, unavailable, retry, login, logout, can, canManageDepartment }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext)
