import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import dayjs from 'dayjs'
import 'dayjs/locale/ru'
import { lazy, Suspense, useState, type ComponentType, type ReactElement } from 'react'
import { BrowserRouter, matchPath, Navigate, Route, Routes, useLocation, useNavigate, type Location } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import AppLayout from './components/Layout'
import { navRoles } from './components/nav'
import CardSlider from './components/shell/CardSlider'
import Login from './pages/Login'
import { theme } from './theme'

dayjs.locale('ru')

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })

// Страницы грузятся по мере открытия: начальный бандл меньше (графики, таблицы отчётов — отдельными чанками)
const page = (load: () => Promise<{ default: ComponentType }>) => lazy(load)

/**
 * Маршрут → раздел меню (права берутся из nav.ts) → страница. Без раздела — доступно всем вошедшим.
 * `list` — маршрут карточки: она открывается в слайдере поверх текущей страницы
 * (при открытии по прямой ссылке — поверх этого списка).
 */
const ROUTES: { path: string; list?: string; section?: string; Page: ComponentType }[] = [
  { path: 'orders', section: '/orders', Page: page(() => import('./pages/Orders')) },
  { path: 'orders/:id', list: '/orders', section: '/orders', Page: page(() => import('./pages/OrderDetail')) },
  { path: 'clients', section: '/clients', Page: page(() => import('./pages/Clients')) },
  { path: 'tasks', section: '/tasks', Page: page(() => import('./pages/Tasks')) },
  { path: 'tasks/:id', list: '/tasks', section: '/tasks', Page: page(() => import('./pages/TaskDetail')) },
  { path: 'trace/:lotId', list: '/stock', Page: page(() => import('./pages/Trace')) },
  { path: 'items', Page: page(() => import('./pages/Items')) },
  { path: 'recipes', section: '/recipes', Page: page(() => import('./pages/Recipes')) },
  { path: 'recipes/:id', list: '/recipes', section: '/recipes', Page: page(() => import('./pages/RecipeDetail')) },
  { path: 'stock', Page: page(() => import('./pages/Stock')) },
  { path: 'shipments', section: '/shipments', Page: page(() => import('./pages/Shipments')) },
  { path: 'shipments/:id', list: '/shipments', section: '/shipments', Page: page(() => import('./pages/ShipmentDetail')) },
  { path: 'moves', section: '/moves', Page: page(() => import('./pages/Moves')) },
  { path: 'purchase-orders', section: '/purchase-orders', Page: page(() => import('./pages/PurchaseOrders')) },
  { path: 'purchase-orders/:id', list: '/purchase-orders', section: '/purchase-orders', Page: page(() => import('./pages/PurchaseOrderDetail')) },
  { path: 'receipts', section: '/receipts', Page: page(() => import('./pages/Receipts')) },
  { path: 'receipts/:id', list: '/receipts', section: '/receipts', Page: page(() => import('./pages/ReceiptDetail')) },
  { path: 'suppliers', section: '/suppliers', Page: page(() => import('./pages/Suppliers')) },
  { path: 'invoices', section: '/invoices', Page: page(() => import('./pages/Invoices')) },
  { path: 'payments', section: '/payments', Page: page(() => import('./pages/Payments')) },
  { path: 'journal', section: '/journal', Page: page(() => import('./pages/Journal')) },
  { path: 'finance', section: '/finance', Page: page(() => import('./pages/FinanceReports')) },
  { path: 'accounts', section: '/accounts', Page: page(() => import('./pages/Accounts')) },
  { path: 'payroll', section: '/payroll', Page: page(() => import('./pages/Payroll')) },
  { path: 'payroll/:id', list: '/payroll', section: '/payroll', Page: page(() => import('./pages/PayrollDetail')) },
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

/** Страница перемонтируется при смене ?q= — переход из глобального поиска применяет новый фильтр. */
function RoutePage({ Page }: { Page: ComponentType }) {
  const { search } = useLocation()
  return <Page key={search} />
}

/** Страницы без меню (печатные формы) — только для вошедших. */
function RequireAuth({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? children : <Navigate to="/login" replace />
}

const CARDS = ROUTES.filter((r) => r.list)
const PAGES = ROUTES.filter((r) => !r.list)

type Place = Pick<Location, 'pathname' | 'search' | 'hash' | 'state' | 'key'>
const place = (pathname: string): Place => ({ pathname, search: '', hash: '', state: null, key: pathname })

/**
 * Страницы рисуются по «фону» — последнему адресу, который не карточка, а карточка — в слайдере поверх.
 * Ссылки на карточки остаются обычными (`/orders/5`): их не нужно помечать, а прямая ссылка
 * и кнопка «Назад» работают как раньше.
 */
function AppRoutes() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const card = CARDS.find((c) => matchPath(`/${c.path}`, location.pathname))

  // Состояние из предыдущих рендеров: где был пользователь до карточки и какая карточка открыта последней
  // (её содержимое нужно и во время анимации закрытия)
  const [background, setBackground] = useState<Place | null>(null)
  const [shown, setShown] = useState<{ card: (typeof CARDS)[number]; location: Place } | null>(null)
  if (!card && background !== location) setBackground(location)
  if (card && !background) setBackground(place(card.list!))
  if (card && shown?.location !== location) setShown({ card, location })

  const base = card ? (background ?? place(card.list!)) : location
  const close = () => background && navigate({ pathname: background.pathname, search: background.search })

  return (
    <>
      <Routes location={base}>
        <Route path="/login" element={<Login />} />
        <Route path="/shipments/:id/print"
          element={<RequireAuth><Suspense fallback={null}><ShipmentPrint /></Suspense></RequireAuth>} />
        <Route element={<AppLayout />}>
          <Route index element={<Home />} />
          {PAGES.map(({ path, section, Page }) => (
            <Route key={path} path={path} element={<Guard section={section}><RoutePage Page={Page} /></Guard>} />
          ))}
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {user && shown && (
        <CardSlider open={Boolean(card)} onClose={close}>
          <Routes location={shown.location}>
            <Route path={shown.card.path} element={<Guard section={shown.card.section}><RoutePage Page={shown.card.Page} /></Guard>} />
          </Routes>
        </CardSlider>
      )}
    </>
  )
}

export default function App() {
  return (
    <ConfigProvider locale={ruRU} theme={theme}>
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </AuthProvider>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  )
}
