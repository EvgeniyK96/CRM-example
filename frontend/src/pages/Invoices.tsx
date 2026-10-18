import { useQuery } from '@tanstack/react-query'
import { Button, Card, Col, Input, Row, Select, Statistic, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { toOptions, useList } from '../api/hooks'
import { INVOICE_STATUS } from '../api/statuses'
import type { Client, Invoice, Receivables } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import PaymentModal, { type PaymentPreset } from '../components/PaymentModal'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney } from '../utils/format'

const STATUS_FILTER = [
  { value: 'open', label: 'Не закрытые' }, { value: 'overdue', label: 'Просроченные' },
  { value: 'unpaid', label: 'Не оплаченные' }, { value: 'partial', label: 'Оплаченные частично' }, { value: 'paid', label: 'Оплаченные' },
]

function ReceivablesCard({ onClient }: { onClient: (id: number) => void }) {
  const { data } = useQuery({
    queryKey: ['/accounting/reports/receivables/'],
    queryFn: async () => (await api.get<Receivables>('/accounting/reports/receivables/')).data,
  })
  if (!data) return <Card loading style={{ marginBottom: 16 }} />
  return (
    <Card size="small" title="Дебиторская задолженность" style={{ marginBottom: 16 }}>
      <Row gutter={16} style={{ marginBottom: 12 }}>
        <Col><Statistic title="Долг клиентов" value={fmtMoney(data.total_debt)} /></Col>
        <Col><Statistic title="Из них просрочено" value={fmtMoney(data.total_overdue)}
          styles={{ content: Number(data.total_overdue) > 0 ? { color: '#cf1322' } : undefined }} /></Col>
      </Row>
      <Table rowKey="client" size="small" pagination={false} dataSource={data.rows}
        onRow={(r) => ({ onClick: () => onClient(r.client), style: { cursor: 'pointer' } })}
        columns={[
          { title: 'Клиент', dataIndex: 'client_name' },
          { title: 'Выставлено', dataIndex: 'invoiced', align: 'right', render: fmtMoney },
          { title: 'Оплачено', dataIndex: 'paid', align: 'right', render: fmtMoney },
          { title: 'Долг', dataIndex: 'debt', align: 'right', render: (v: string) => (Number(v) ? <b>{fmtMoney(v)}</b> : '—') },
          {
            title: 'Просрочено', dataIndex: 'overdue', align: 'right',
            render: (v: string) => (Number(v) ? <Typography.Text type="danger" strong>{fmtMoney(v)}</Typography.Text> : '—'),
          },
          { title: 'Аванс', dataIndex: 'advance', align: 'right', render: (v: string) => (Number(v) ? <Tag color="green">{fmtMoney(v)}</Tag> : '—') },
        ]} />
    </Card>
  )
}

export default function Invoices() {
  const { can } = useAuth()
  const [client, setClient] = useState<number>()
  const [query] = useSearchParams()
  const [search, setSearch] = useState(query.get('q') ?? '')
  // по ссылке на конкретный счёт показываем его, в каком бы статусе он ни был
  const [status, setStatus] = useState<string | undefined>(query.get('q') ? undefined : 'open')
  const [paying, setPaying] = useState<PaymentPreset | null>(null)
  const clients = useList<Client>('/sales/clients/')
  const invoices = useList<Invoice>('/accounting/invoices/', { client, status, search })
  const isAccountant = can('accountant')

  return (
    <>
      <ReceivablesCard onClient={setClient} />
      <Card size="small" title="Счета покупателям">
        <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
          <Input.Search placeholder="Счёт, клиент, заказ" allowClear onSearch={setSearch} defaultValue={search} style={{ maxWidth: 260 }} />
          <Select allowClear showSearch={{ optionFilterProp: 'label' }} placeholder="Клиент" style={{ width: 260 }}
            value={client} onChange={setClient} options={toOptions(clients.data, (c) => c.name)} />
          <Select allowClear placeholder="Статус" style={{ width: 220 }} value={status} onChange={setStatus} options={STATUS_FILTER} />
          {isAccountant && <Button type="primary" onClick={() => setPaying({ direction: 'incoming', client })}>Внести поступление</Button>}
        </div>
        <Table<Invoice> rowKey="id" size="middle" loading={invoices.isLoading} dataSource={invoices.data}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          columns={[
            { title: 'Счёт', dataIndex: 'number' },
            { title: 'Дата', dataIndex: 'date', render: fmtDate },
            { title: 'Клиент', dataIndex: 'client_name' },
            {
              title: 'Основание',
              render: (_, i) => i.shipment && <><Link to={`/shipments/${i.shipment}`}>{i.shipment_number}</Link> / <Link to={`/orders/${i.order}`}>{i.order_number}</Link></>,
            },
            {
              title: 'Оплатить до',
              render: (_, i) => <>{fmtDate(i.due_date)} {i.days_overdue > 0 && <Tag color="red">просрочен {i.days_overdue} дн.</Tag>}</>,
            },
            { title: 'Сумма', dataIndex: 'amount', align: 'right', render: fmtMoney },
            { title: 'Оплачено', dataIndex: 'paid', align: 'right', render: fmtMoney },
            { title: 'Остаток', dataIndex: 'remaining', align: 'right', render: (v: string) => (Number(v) ? <b>{fmtMoney(v)}</b> : '—') },
            { title: 'Статус', dataIndex: 'status', render: (s: string) => <StatusTag map={INVOICE_STATUS} value={s} /> },
            ...(isAccountant ? [{
              key: 'pay',
              render: (_: unknown, i: Invoice) => i.status !== 'paid' && (
                <Button size="small" onClick={() => setPaying({ direction: 'incoming', client: i.client, invoice: i.id, amount: i.remaining })}>
                  Оплата
                </Button>
              ),
            }] : []),
          ]} />
      </Card>
      <PaymentModal preset={paying} onClose={() => setPaying(null)} />
    </>
  )
}
