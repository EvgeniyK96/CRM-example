import { App, Typography } from 'antd'
import dayjs from 'dayjs'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useApiAction } from '../../api/hooks'
import { CLIENT_KIND, SALES_ORDER_STATUS } from '../../api/statuses'
import type { SalesOrder } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { fmtDate, fmtMoney } from '../../utils/format'
import Kanban from '../Kanban'
import ShipModal from '../ShipModal'

const OPEN = ['new', 'confirmed', 'in_production', 'ready']

/** Канбан заказов. «В производстве» и «Отгружен» сервер ставит сам или через отгрузку — туда руками не переносим. */
export default function OrdersBoard({ rows }: { rows: SalesOrder[] }) {
  const { can } = useAuth()
  const { modal } = App.useApp()
  const navigate = useNavigate()
  const [shipping, setShipping] = useState<SalesOrder | null>(null)

  const act = useApiAction(
    async ({ order, action }: { order: SalesOrder; action: 'confirm' | 'reopen' | 'cancel' }) =>
      (await api.post<SalesOrder>(`/sales/orders/${order.id}/${action}/`)).data,
    { success: (o) => `${o.number}: ${SALES_ORDER_STATUS[o.status].label.toLowerCase()}`, invalidate: 'all' },
  )

  const targets = (o: SalesOrder): string[] => {
    const t: string[] = []
    if (can('sales')) {
      // Подтверждение само решает, нужен ли заказ производству (→ «Подтверждён») или всё есть на складе (→ «Готов»)
      if (o.status === 'new') t.push('confirmed', 'ready', 'cancelled')
      if (o.status === 'confirmed' || o.status === 'ready') t.push('new', 'cancelled')
    }
    if (can('storekeeper') && o.status === 'ready') t.push('shipped')
    return t
  }

  const onMove = (order: SalesOrder, to: string) => {
    if (to === 'shipped') setShipping(order)
    else if (to === 'new') act.mutate({ order, action: 'reopen' })
    else if (to === 'cancelled') {
      modal.confirm({
        title: `Отменить заказ ${order.number}?`,
        content: 'Резерв продукции снимется. Отменённый заказ нельзя вернуть в работу.',
        okText: 'Отменить заказ', okButtonProps: { danger: true }, cancelText: 'Не отменять',
        onOk: () => act.mutateAsync({ order, action: 'cancel' }),
      })
    } else act.mutate({ order, action: 'confirm' })
  }

  const today = dayjs().format('YYYY-MM-DD')

  return (
    <>
      <Kanban<SalesOrder>
        rows={rows}
        statuses={SALES_ORDER_STATUS}
        closed={['shipped', 'cancelled']}
        dateOf={(o) => o.delivery_date}
        summary={(list) => fmtMoney(list.reduce((s, o) => s + Number(o.total), 0))}
        targets={targets}
        onMove={onMove}
        onOpen={(o) => navigate(`/orders/${o.id}`)}
        card={(o) => {
          const overdue = OPEN.includes(o.status) && o.delivery_date < today
          return (
            <>
              <div className="kanban-card-title"><span>{o.number}</span><span>{fmtMoney(o.total)}</span></div>
              <div className="kanban-card-line">{o.client_name}</div>
              <div className="kanban-card-meta">
                <span>
                  Отгрузка{' '}
                  {overdue ? <Typography.Text type="danger" style={{ fontSize: 12 }}>{fmtDate(o.delivery_date)} — просрочен</Typography.Text> : fmtDate(o.delivery_date)}
                </span>
                <span>{CLIENT_KIND[o.client_kind]?.label}</span>
              </div>
            </>
          )
        }}
      />
      <ShipModal order={shipping} onClose={() => setShipping(null)} />
    </>
  )
}
