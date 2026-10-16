import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

const ACCESS = 'access'
const REFRESH = 'refresh'

export const tokens = {
  get access() { return localStorage.getItem(ACCESS) },
  get refresh() { return localStorage.getItem(REFRESH) },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS, access)
    if (refresh) localStorage.setItem(REFRESH, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS)
    localStorage.removeItem(REFRESH)
  },
}

api.interceptors.request.use((config) => {
  if (tokens.access) config.headers.Authorization = `Bearer ${tokens.access}`
  return config
})

let refreshing: Promise<string> | null = null

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry && tokens.refresh && !original.url?.includes('/auth/jwt/')) {
      original._retry = true
      refreshing ??= axios
        .post('/api/auth/jwt/refresh/', { refresh: tokens.refresh })
        .then((r) => {
          tokens.set(r.data.access)
          return r.data.access as string
        })
        .finally(() => { refreshing = null })
      try {
        const access = await refreshing
        original.headers.Authorization = `Bearer ${access}`
        return api(original)
      } catch {
        tokens.clear()
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export interface Page<T> { count: number; next: string | null; previous: string | null; results: T[] }
