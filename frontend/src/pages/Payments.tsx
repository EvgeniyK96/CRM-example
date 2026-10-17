import { Button, DatePicker, Input, Segmented, Table, Typography } from 'antd'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import { useList } from '../api/hooks'
import type { Payment } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import PaymentModal, { type PaymentPreset } from '../components/PaymentModal'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

export default function Payments() {
  const { can } = useAuth()
  const [direction, setDirection] = useState<'all' | 'incoming' | 'outgoing'>('all')
  const [search, setSearch] = useState('')
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [preset, setPreset] = useState<PaymentPreset | null>(null)
  const payments = useList<Payment>('/accounting/payments/', {
    direction: direction === 'all' ? undefined : direction, search,
    date_from: toApiDate(range?.[0]) ?? undefined, date_to: toApiDate(range?.[1]) ?? undefined,
  })

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Segmented value={direction} onChange={setDirection} options={[
          { value: 'all', label: 'Все' }, { value: 'incoming', label: 'Поступления' }, { value: 'outgoing', label: 'Оплаты поставщикам' },
        ]} />
        <Input.Search placeholder="Номер, контрагент, назначение" allowClear onSearch={setSearch} style={{ maxWidth: 280 }} />
        <DatePicker.RangePicker value={range} onChange={(v) => setRange(v)} />
        {can('accountant') && (
          <Button type="primary" onClick={() => setPreset({ direction: direction === 'outgoing' ? 'outgoing' : 'incoming' })}>
            Новый платёж
          </Button>
        )}
      </div>
      <Table<Payment> rowKey="id" size="middle" loading={payments.isLoading} dataSource={payments.data}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        columns={[
          { title: 'Номер', dataIndex: 'number' },
          { title: 'Дата', dataIndex: 'date', render: fmtDate },
          { title: 'Контрагент', render: (_, p) => p.client_name ?? p.supplier_name },
          { title: 'Способ', dataIndex: 'method_display' },
          {
            title: 'Сумма', align: 'right',
            render: (_, p) => (
              <Typography.Text type={p.direction === 'incoming' ? 'success' : 'danger'}>
                {p.direction === 'incoming' ? '+' : '−'}{fmtMoney(p.amount)}
              </Typography.Text>
            ),
          },
          {
            title: 'Разнесено по счетам',
            render: (_, p) => p.direction === 'outgoing' ? '—' : (
              <>
                {p.allocations.map((a) => <div key={a.invoice}>{a.invoice_number}: {fmtMoney(a.amount)}</div>)}
                {(() => {
                  const free = Number(p.amount) - p.allocations.reduce((s, a) => s + Number(a.amount), 0)
                  return free > 0.004 ? <Typography.Text type="secondary">аванс {fmtMoney(free)}</Typography.Text> : null
                })()}
              </>
            ),
          },
          { title: 'Назначение', dataIndex: 'comment' },
          { title: 'Автор', dataIndex: 'created_by_name', render: (v) => v ?? '—' },
        ]} />
      <PaymentModal preset={preset} onClose={() => setPreset(null)} />
    </>
  )
}
