import { Button, Layout, Menu, Typography } from 'antd'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { NAV } from './nav'

export default function AppLayout() {
  const { user, loading, logout, can } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()

  if (loading) return null
  if (!user) return <Navigate to="/login" replace />

  // Пункты без группы — сверху; остальные собираются в группы в порядке появления
  const visible = NAV.filter((i) => i.roles === 'all' || can(...i.roles))
  const groups = [...new Set(visible.map((i) => i.group).filter(Boolean))] as string[]
  const items = [
    ...visible.filter((i) => !i.group).map(({ key, label }) => ({ key, label })),
    ...groups.map((g) => ({
      type: 'group' as const,
      key: g,
      label: g,
      children: visible.filter((i) => i.group === g).map(({ key, label }) => ({ key, label })),
    })),
  ]
  const section = '/' + pathname.split('/')[1]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider theme="light" width={230} style={{ overflow: 'auto', height: '100vh', position: 'sticky', top: 0 }}>
        <Typography.Title level={5} style={{ padding: '16px 24px', margin: 0 }}>CRM Фабрика</Typography.Title>
        <Menu mode="inline" selectedKeys={[section]} items={items} onClick={(e) => navigate(e.key)} />
      </Layout.Sider>
      {/* minWidth: 0 — иначе широкая таблица растягивает страницу вместо собственной прокрутки */}
      <Layout style={{ minWidth: 0 }}>
        <Layout.Header style={{ background: '#fff', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 16 }}>
          <span>{user.username} · {user.role_display}</span>
          <Button onClick={logout}>Выйти</Button>
        </Layout.Header>
        <Layout.Content style={{ padding: 24 }}><Outlet /></Layout.Content>
      </Layout>
    </Layout>
  )
}
