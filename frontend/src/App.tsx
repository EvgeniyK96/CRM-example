import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import dayjs from 'dayjs'
import 'dayjs/locale/ru'
import { lazy, Suspense, type ComponentType, type ReactElement } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import AppLayout from './components/Layout'
import { navRoles } from './components/nav'
import Login from './pages/Login'

dayjs.locale('ru')

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })

// Страницы грузятся по мере открытия: начальный бандл меньше (графики, таблицы отчётов — отдельными чанками)
const page = (load: () => Promise<{ default: ComponentType }>) => lazy(load)

/** Маршрут → раздел меню (права берутся из nav.ts) → страница. Без раздела — доступно всем вошедшим. */
const ROUTES: { path: string; section?: string; Page: ComponentType }[] = [
  { path: 'orders', section: '/orders', Page: page(() => import('./pages/Orders')) },
  { path: 'orders/:id', section: '/orders', Page: page(() => import('./pages/OrderDetail')) },
  { path: 'clients', section: '/clients', Page: page(() => import('./pages/Clients')) },
  { path: 'tasks', section: '/tasks', Page: page(() => import('./pages/Tasks')) },
  { path: 'tasks/:id', section: '/tasks', Page: page(() => import('./pages/TaskDetail')) },
  { path: 'trace/:lotId', Page: page(() => import('./pages/Trace')) },
  { path: 'items', Page: page(() => import('./pages/Items')) },
  { path: 'recipes', section: '/recipes', Page: page(() => import('./pages/Recipes')) },
  { path: 'recipes/:id', section: '/recipes', Page: page(() => import('./pages/RecipeDetail')) },
  { path: 'stock', Page: page(() => import('./pages/Stock')) },
  { path: 'shipments', section: '/shipments', Page: page(() => import('./pages/Shipments')) },
  { path: 'shipments/:id', section: '/shipments', Page: page(() => import('./pages/ShipmentDetail')) },
  { path: 'moves', section: '/moves', Page: page(() => import('./pages/Moves')) },
  { path: 'purchase-orders', section: '/purchase-orders', Page: page(() => import('./pages/PurchaseOrders')) },
  { path: 'purchase-orders/:id', section: '/purchase-orders', Page: page(() => import('./pages/PurchaseOrderDetail')) },
  { path: 'receipts', section: '/receipts', Page: page(() => import('./pages/Receipts')) },
  { path: 'receipts/:id', section: '/receipts', Page: page(() => import('./pages/ReceiptDetail')) },
  { path: 'suppliers', section: '/suppliers', Page: page(() => import('./pages/Suppliers')) },
  { path: 'invoices', section: '/invoices', Page: page(() => import('./pages/Invoices')) },
  { path: 'payments', section: '/payments', Page: page(() => import('./pages/Payments')) },
  { path: 'journal', section: '/journal', Page: page(() => import('./pages/Journal')) },
  { path: 'finance', section: '/finance', Page: page(() => import('./pages/FinanceReports')) },
  { path: 'accounts', section: '/accounts', Page: page(() => import('./pages/Accounts')) },
  { path: 'payroll', section: '/payroll', Page: page(() => import('./pages/Payroll')) },
  { path: 'payroll/:id', section: '/payroll', Page: page(() => import('./pages/PayrollDetail')) },
  { path: 'payroll-rates', section: '/payroll-rates', Page: page(() => import('./pages/PayrollRates')) },
  { path: 'employees', section: '/employees', Page: page(() => import('./pages/Employees')) },
  { path: 'hr-orders', section: '/hr-orders', Page: page(() => import('./pages/HROrders')) },
  { path: 'absences', section: '/absences', Page: page(() => import('./pages/Absences')) },
  { path: 'timesheet', section: '/timesheet', Page: page(() => import('./pages/Timesheet')) },
  { path: 'analytics', section: '/analytics', Page: page(() => import('./pages/Analytics')) },
  { path: 'references', section: '/references', Page: page(() => import('./pages/References')) },
  { path: 'users', section: '/users', Page: page(() => import('./pages/Users')) },
]

const Home = page(() => import('./pages/Home'))
const ShipmentPrint = page(() => import('./pages/ShipmentPrint'))

/** Пускает в раздел только роли, которым он показан в меню (см. nav.ts). */
function Guard({ section, children }: { section?: string; children: ReactElement }) {
  const { can } = useAuth()
  if (!section) return children
  const roles = navRoles(section)
  return roles === 'all' || can(...roles) ? children : <Navigate to="/" replace />
}

/** Страницы без меню (печатные формы) — только для вошедших. */
function RequireAuth({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/shipments/:id/print"
                  element={<RequireAuth><Suspense fallback={null}><ShipmentPrint /></Suspense></RequireAuth>} />
                <Route element={<AppLayout />}>
                  <Route index element={<Home />} />
                  {ROUTES.map(({ path, section, Page }) => (
                    <Route key={path} path={path} element={<Guard section={section}><Page /></Guard>} />
                  ))}
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  )
}
