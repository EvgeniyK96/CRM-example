import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons'
import { Button, Layout, Menu, Result, Spin, Tooltip } from 'antd'
import { createElement, Suspense, useState } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { SHELL, WALLPAPER } from '../theme'
import { NAV, navSection } from './nav'
import GlobalSearch from './shell/GlobalSearch'
import NotificationBell from './shell/NotificationBell'
import UserMenu from './shell/UserMenu'

const COLLAPSED_KEY = 'shell.siderCollapsed'

function readCollapsed() {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === '1'
  } catch {
    return false
  }
}

/** Оболочка в стиле Битрикс24: обои, тёмное полупрозрачное меню, шапка с поиском, светлая рабочая область. */
export default function AppLayout() {
  const { user, loading, unavailable, retry, can } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(readCollapsed)

  if (loading) return null
  if (unavailable) {
    return (
      <div style={{ minHeight: '100vh', background: WALLPAPER, display: 'grid', placeItems: 'center' }}>
        <Result status="warning" title={<span style={{ color: '#fff' }}>Сервер недоступен</span>}
          subTitle={<span style={{ color: 'rgba(255,255,255,0.8)' }}>Возможно, он перезапускается. Сессия сохранена.</span>}
          extra={<Button type="primary" onClick={retry}>Повторить</Button>} />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />

  const toggle = () => {
    setCollapsed(!collapsed)
    try {
      localStorage.setItem(COLLAPSED_KEY, collapsed ? '0' : '1')
    } catch {
      // настройка не сохранится — не страшно
    }
  }

  const visible = NAV.filter((i) => i.roles === 'all' || can(...i.roles))
  const item = (i: (typeof NAV)[number]) => ({ key: i.key, label: i.label, icon: createElement(i.icon) })
  // В свёрнутом меню группы не показываем — только иконки с подсказками
  const groups = [...new Set(visible.map((i) => i.group).filter(Boolean))] as string[]
  const items = collapsed
    ? visible.map(item)
    : [
      ...visible.filter((i) => !i.group).map(item),
      ...groups.map((g) => ({ type: 'group' as const, key: g, label: g, children: visible.filter((i) => i.group === g).map(item) })),
    ]
  const section = navSection(pathname)

  return (
    <Layout style={{ minHeight: '100vh', background: WALLPAPER, backgroundAttachment: 'fixed' }}>
      <Layout.Sider
        width={240}
        collapsedWidth={68}
        collapsed={collapsed}
        trigger={null}
        breakpoint="lg"
        onBreakpoint={(narrow) => narrow && setCollapsed(true)}  // на узком экране меню сворачивается само
        style={{ background: SHELL.sider, backdropFilter: 'blur(12px)', height: '100vh', position: 'sticky', top: 0, overflow: 'auto' }}
      >
        <div className="shell-logo" onClick={() => navigate('/')}>
          <span className="shell-logo-mark">Ф</span>
          {!collapsed && <span>CRM Фабрика</span>}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[section?.key ?? '/']} items={items} onClick={(e) => navigate(e.key)} />
      </Layout.Sider>
      <Layout style={{ minWidth: 0 }}>
        <Layout.Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Tooltip title={collapsed ? 'Развернуть меню' : 'Свернуть меню'}>
            <Button type="text" onClick={toggle} aria-label="Свернуть меню"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} style={{ color: '#fff' }} />
          </Tooltip>
          <div style={{ flex: 1, minWidth: 0 }}><GlobalSearch /></div>
          <NotificationBell />
          <UserMenu />
        </Layout.Header>
        <Layout.Content style={{ padding: '4px 24px 24px' }}>
          <h1 className="shell-title">
            {section?.key === '/' ? `Добро пожаловать, ${user.first_name || user.username}` : section?.label ?? 'CRM Фабрика'}
          </h1>
          <div className="shell-workarea" style={{ background: SHELL.workarea }}>
            {/* Страницы грузятся лениво: оболочка остаётся на месте, пока подгружается чанк */}
            <Suspense fallback={<Spin style={{ display: 'block', margin: '48px auto' }} />}><Outlet /></Suspense>
          </div>
        </Layout.Content>
      </Layout>
    </Layout>
  )
}
