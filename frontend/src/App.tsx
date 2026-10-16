import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import 'dayjs/locale/ru'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import AppLayout from './components/Layout'
import Employees from './pages/Employees'
import Home from './pages/Home'
import Login from './pages/Login'
import Users from './pages/Users'
import type { ReactElement } from 'react'
import type { Role } from './api/types'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })

function Guard({ roles, children }: { roles: Role[]; children: ReactElement }) {
  const { can } = useAuth()
  return can(...roles) ? children : <Navigate to="/" replace />
}

export default function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route element={<AppLayout />}>
                <Route index element={<Home />} />
                <Route path="employees" element={<Employees />} />
                <Route path="users" element={<Guard roles={[]}><Users /></Guard>} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ConfigProvider>
  )
}
