import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import dayjs from 'dayjs'
import 'dayjs/locale/ru'
import type { ReactElement } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import AppLayout from './components/Layout'
import { navRoles } from './components/nav'
import Absences from './pages/Absences'
import Accounts from './pages/Accounts'
import Analytics from './pages/Analytics'
import Clients from './pages/Clients'
import Employees from './pages/Employees'
import FinanceReports from './pages/FinanceReports'
import Home from './pages/Home'
import HROrders from './pages/HROrders'
import Invoices from './pages/Invoices'
import Items from './pages/Items'
import Journal from './pages/Journal'
import Login from './pages/Login'
import Moves from './pages/Moves'
import OrderDetail from './pages/OrderDetail'
import Orders from './pages/Orders'
import Payments from './pages/Payments'
import Payroll from './pages/Payroll'
import PayrollDetail from './pages/PayrollDetail'
import PayrollRates from './pages/PayrollRates'
import PurchaseOrderDetail from './pages/PurchaseOrderDetail'
import PurchaseOrders from './pages/PurchaseOrders'
import ReceiptDetail from './pages/ReceiptDetail'
import Receipts from './pages/Receipts'
import RecipeDetail from './pages/RecipeDetail'
import Recipes from './pages/Recipes'
import References from './pages/References'
import ShipmentDetail from './pages/ShipmentDetail'
import ShipmentPrint from './pages/ShipmentPrint'
import Shipments from './pages/Shipments'
import Stock from './pages/Stock'
import Suppliers from './pages/Suppliers'
import TaskDetail from './pages/TaskDetail'
import Tasks from './pages/Tasks'
import Timesheet from './pages/Timesheet'
import Trace from './pages/Trace'
import Users from './pages/Users'

dayjs.locale('ru')

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })

/** Пускает в раздел только роли, которым он показан в меню (см. nav.ts). */
function Guard({ section, children }: { section: string; children: ReactElement }) {
  const { can } = useAuth()
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
                <Route path="/shipments/:id/print" element={<RequireAuth><ShipmentPrint /></RequireAuth>} />
                <Route element={<AppLayout />}>
                  <Route index element={<Home />} />
                  <Route path="orders" element={<Guard section="/orders"><Orders /></Guard>} />
                  <Route path="orders/:id" element={<Guard section="/orders"><OrderDetail /></Guard>} />
                  <Route path="clients" element={<Guard section="/clients"><Clients /></Guard>} />
                  <Route path="tasks" element={<Guard section="/tasks"><Tasks /></Guard>} />
                  <Route path="tasks/:id" element={<Guard section="/tasks"><TaskDetail /></Guard>} />
                  <Route path="trace/:lotId" element={<Trace />} />
                  <Route path="invoices" element={<Guard section="/invoices"><Invoices /></Guard>} />
                  <Route path="payments" element={<Guard section="/payments"><Payments /></Guard>} />
                  <Route path="journal" element={<Guard section="/journal"><Journal /></Guard>} />
                  <Route path="finance" element={<Guard section="/finance"><FinanceReports /></Guard>} />
                  <Route path="accounts" element={<Guard section="/accounts"><Accounts /></Guard>} />
                  <Route path="payroll" element={<Guard section="/payroll"><Payroll /></Guard>} />
                  <Route path="payroll/:id" element={<Guard section="/payroll"><PayrollDetail /></Guard>} />
                  <Route path="payroll-rates" element={<Guard section="/payroll-rates"><PayrollRates /></Guard>} />
                  <Route path="hr-orders" element={<Guard section="/hr-orders"><HROrders /></Guard>} />
                  <Route path="absences" element={<Guard section="/absences"><Absences /></Guard>} />
                  <Route path="timesheet" element={<Guard section="/timesheet"><Timesheet /></Guard>} />
                  <Route path="analytics" element={<Guard section="/analytics"><Analytics /></Guard>} />
                  <Route path="items" element={<Items />} />
                  <Route path="recipes" element={<Guard section="/recipes"><Recipes /></Guard>} />
                  <Route path="recipes/:id" element={<Guard section="/recipes"><RecipeDetail /></Guard>} />
                  <Route path="stock" element={<Stock />} />
                  <Route path="shipments" element={<Guard section="/shipments"><Shipments /></Guard>} />
                  <Route path="shipments/:id" element={<Guard section="/shipments"><ShipmentDetail /></Guard>} />
                  <Route path="moves" element={<Guard section="/moves"><Moves /></Guard>} />
                  <Route path="purchase-orders" element={<Guard section="/purchase-orders"><PurchaseOrders /></Guard>} />
                  <Route path="purchase-orders/:id" element={<Guard section="/purchase-orders"><PurchaseOrderDetail /></Guard>} />
                  <Route path="receipts" element={<Guard section="/receipts"><Receipts /></Guard>} />
                  <Route path="receipts/:id" element={<Guard section="/receipts"><ReceiptDetail /></Guard>} />
                  <Route path="suppliers" element={<Guard section="/suppliers"><Suppliers /></Guard>} />
                  <Route path="employees" element={<Guard section="/employees"><Employees /></Guard>} />
                  <Route path="references" element={<Guard section="/references"><References /></Guard>} />
                  <Route path="users" element={<Guard section="/users"><Users /></Guard>} />
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
