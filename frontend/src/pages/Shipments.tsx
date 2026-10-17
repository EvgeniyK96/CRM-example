import { Button, Card, DatePicker, Input, Select, Table, Tag } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toOptions, useList } from '../api/hooks'
import { CLIENT_KIND } from '../api/statuses'
import type { Client, SalesOrder, Shipment } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import ShipModal from '../components/ShipModal'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

function DeliveryTag({ date }: { date: string }) {
  const days = dayjs(date).startOf('day').diff(dayjs().startOf('day'), 'day')
  if (days < 0) return <Tag color="red">просрочена на {-days} дн.</Tag>
  if (days === 0) return <Tag color="orange">сегодня</Tag>
  return <Tag>через {days} дн.</Tag>
}

/** Очередь заказов, готовых к отгрузке. */
function ReadyOrders() {
  const { can } = useAuth()
  const [shipping, setShipping] = useState<SalesOrder | null>(null)
  const orders = useList<SalesOrder>('/sales/orders/', { status: 'ready', ordering: 'delivery_date' })

  return (
    <Card size="small" title="Готовы к отгрузке" style={{ marginBottom: 16 }}>
      <Table<SalesOrder> rowKey="id" size="small" pagination={false} loading={orders.isLoading} dataSource={orders.data}
        locale={{ emptyText: 'Нет заказов, готовых к отгрузке' }}
        columns={[
          { title: 'Заказ', render: (_, o) => <Link to={`/orders/${o.id}`}>{o.number}</Link> },
          { title: 'Клиент', dataIndex: 'client_name' },
          { title: 'Тип', dataIndex: 'client_kind', render: (k: string) => <StatusTag map={CLIENT_KIND} value={k} /> },
          { title: 'Адрес доставки', dataIndex: 'delivery_address' },
          { title: 'Отгрузка', render: (_, o) => <>{fmtDate(o.delivery_date)} <DeliveryTag date={o.delivery_date} /></> },
          { title: 'Сумма', dataIndex: 'total', align: 'right', render: fmtMoney },
          ...(can('storekeeper')
            ? [{ key: 'ship', render: (_: unknown, o: SalesOrder) => <Button type="primary" size="small" onClick={() => setShipping(o)}>Отгрузить</Button> }]
            : []),
        ]} />
      <ShipModal order={shipping} onClose={() => setShipping(null)} />
    </Card>
  )
}

export default function Shipments() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [client, setClient] = useState<number>()
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const clients = useList<Client>('/sales/clients/')
  const shipments = useList<Shipment>('/sales/shipments/', {
    search, client, date_from: toApiDate(range?.[0]) ?? undefined, date_to: toApiDate(range?.[1]) ?? undefined,
  })

  return (
    <>
      <ReadyOrders />
      <Card size="small" title="Журнал отгрузок">
        <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
          <Input.Search placeholder="Накладная, заказ, клиент, водитель" allowClear onSearch={setSearch} style={{ maxWidth: 300 }} />
          <Select allowClear showSearch={{ optionFilterProp: 'label' }} placeholder="Клиент" style={{ width: 260 }}
            value={client} onChange={setClient} options={toOptions(clients.data, (c) => c.name)} />
          <DatePicker.RangePicker value={range} onChange={(v) => setRange(v)} />
        </div>
        <Table<Shipment> rowKey="id" size="middle" loading={shipments.isLoading} dataSource={shipments.data}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          onRow={(s) => ({ onClick: () => navigate(`/shipments/${s.id}`), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'Накладная', dataIndex: 'number' },
            { title: 'Дата', dataIndex: 'date', render: fmtDate },
            { title: 'Заказ', dataIndex: 'order_number' },
            { title: 'Клиент', dataIndex: 'client_name' },
            { title: 'Водитель', dataIndex: 'driver', render: (v) => v || '—' },
            { title: 'Сумма', dataIndex: 'total', align: 'right', render: fmtMoney },
            { title: 'Себестоимость', dataIndex: 'cost', align: 'right', render: fmtMoney },
          ]} />
      </Card>
    </>
  )
}
