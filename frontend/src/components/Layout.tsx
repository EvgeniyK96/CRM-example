import { Button, Layout, Menu, Typography } from 'antd'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { Role } from '../api/types'
import { useAuth } from '../auth/AuthContext'

interface Item { key: string; label: string; roles: Role[] | 'all' }

// Разделы добавляются по мере появления модулей
export const NAV: Item[] = [
  { key: '/', label: 'Главная', roles: 'all' },
  { key: '/employees', label: 'Сотрудники', roles: 'all' },
  { key: '/users', label: 'Пользователи', roles: [] },
]

export default function AppLayout() {
  const { user, loading, logout, can } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()

  if (loading) return null
  if (!user) return <Navigate to="/login" replace />

  const items = NAV.filter((i) => i.roles === 'all' || can(...i.roles)).map(({ key, label }) => ({ key, label }))

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider theme="light" width={220}>
        <Typography.Title level={5} style={{ padding: '16px 24px', margin: 0 }}>CRM Фабрика</Typography.Title>
        <Menu mode="inline" selectedKeys={[pathname]} items={items} onClick={(e) => navigate(e.key)} />
      </Layout.Sider>
      <Layout>
        <Layout.Header style={{ background: '#fff', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 16 }}>
          <span>{user.username} · {user.role_display}</span>
          <Button onClick={logout}>Выйти</Button>
        </Layout.Header>
        <Layout.Content style={{ padding: 24 }}><Outlet /></Layout.Content>
      </Layout>
    </Layout>
  )
}
