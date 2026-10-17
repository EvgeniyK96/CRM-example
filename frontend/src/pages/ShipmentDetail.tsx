import { ArrowLeftOutlined, PrinterOutlined } from '@ant-design/icons'
import { Button, Card, Descriptions, Space, Table } from 'antd'
import { Link, useParams } from 'react-router-dom'
import { useDetail } from '../api/hooks'
import type { Shipment, ShipmentItem } from '../api/types'
import { fmtDate, fmtDateTime, fmtMoney, fmtQty } from '../utils/format'

export default function ShipmentDetail() {
  const { id } = useParams()
  const { data: s, isLoading } = useDetail<Shipment>('/sales/shipments/', id)
  if (isLoading || !s) return <Card loading />

  const margin = Number(s.total) - Number(s.cost)

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Link to="/shipments"><ArrowLeftOutlined /> Все отгрузки</Link>
      <Card
        title={`Накладная ${s.number} от ${fmtDate(s.date)}`}
        extra={
          <a href={`/shipments/${s.id}/print`} target="_blank" rel="noreferrer">
            <Button icon={<PrinterOutlined />}>Печатная форма</Button>
          </a>
        }
      >
        <Descriptions size="small" column={{ xs: 1, md: 3 }} items={[
          { label: 'Клиент', children: s.client_name },
          { label: 'Заказ', children: <Link to={`/orders/${s.order}`}>{s.order_number}</Link> },
          { label: 'Адрес доставки', children: s.delivery_address || '—' },
          { label: 'Транспорт', children: s.vehicle || '—' },
          { label: 'Водитель', children: s.driver || '—' },
          { label: 'Отгрузил', children: `${s.created_by_name ?? '—'}, ${fmtDateTime(s.created_at)}` },
          { label: 'Сумма', children: <span style={{ whiteSpace: 'nowrap' }}>{fmtMoney(s.total)}</span> },
          { label: 'Себестоимость', children: <span style={{ whiteSpace: 'nowrap' }}>{fmtMoney(s.cost)}</span> },
          {
            label: 'Валовая прибыль',
            children: <span style={{ whiteSpace: 'nowrap' }}>{fmtMoney(margin)} ({Number(s.total) ? Math.round((margin / Number(s.total)) * 100) : 0}%)</span>,
          },
        ]} />
      </Card>
      <Card size="small" title="Отгружено по партиям (FEFO)">
        <Table<ShipmentItem> rowKey="id" size="small" pagination={false} dataSource={s.items} columns={[
          { title: 'Продукция', dataIndex: 'item_name' },
          { title: 'Партия', render: (_, i) => <Link to={`/trace/${i.lot}`}>{i.lot_number}</Link> },
          { title: 'Произведена', dataIndex: 'lot_date', render: fmtDate },
          { title: 'Годна до', dataIndex: 'expiry_date', render: fmtDate },
          { title: 'Количество', align: 'right', render: (_, i) => fmtQty(i.quantity, i.unit_code) },
          { title: 'Цена', dataIndex: 'price', align: 'right', render: fmtMoney },
          { title: 'Сумма', align: 'right', render: (_, i) => fmtMoney(Number(i.quantity) * Number(i.price)) },
          { title: 'Себестоимость', align: 'right', render: (_, i) => fmtMoney(Number(i.quantity) * Number(i.unit_cost)) },
        ]} />
      </Card>
    </Space>
  )
}
