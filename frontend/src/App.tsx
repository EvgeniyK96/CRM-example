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
import Clients from './pages/Clients'
import Employees from './pages/Employees'
import Home from './pages/Home'
import Items from './pages/Items'
import Login from './pages/Login'
import Moves from './pages/Moves'
import OrderDetail from './pages/OrderDetail'
import Orders from './pages/Orders'
import PurchaseOrderDetail from './pages/PurchaseOrderDetail'
import PurchaseOrders from './pages/PurchaseOrders'
import ReceiptDetail from './pages/ReceiptDetail'
import Receipts from './pages/Receipts'
import RecipeDetail from './pages/RecipeDetail'
import Recipes from './pages/Recipes'
import References from './pages/References'
import Stock from './pages/Stock'
import Suppliers from './pages/Suppliers'
import TaskDetail from './pages/TaskDetail'
import Tasks from './pages/Tasks'
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

export default function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route element={<AppLayout />}>
                  <Route index element={<Home />} />
                  <Route path="orders" element={<Guard section="/orders"><Orders /></Guard>} />
                  <Route path="orders/:id" element={<Guard section="/orders"><OrderDetail /></Guard>} />
                  <Route path="clients" element={<Guard section="/clients"><Clients /></Guard>} />
                  <Route path="tasks" element={<Guard section="/tasks"><Tasks /></Guard>} />
                  <Route path="tasks/:id" element={<Guard section="/tasks"><TaskDetail /></Guard>} />
                  <Route path="trace/:lotId" element={<Trace />} />
                  <Route path="items" element={<Items />} />
                  <Route path="recipes" element={<Guard section="/recipes"><Recipes /></Guard>} />
                  <Route path="recipes/:id" element={<Guard section="/recipes"><RecipeDetail /></Guard>} />
                  <Route path="stock" element={<Stock />} />
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
