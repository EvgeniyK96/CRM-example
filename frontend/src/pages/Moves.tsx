import { DatePicker, Input, Select, Table, Typography } from 'antd'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import { useList } from '../api/hooks'
import { MOVE_KIND, statusOptions } from '../api/statuses'
import type { StockMove } from '../api/types'
import StatusTag from '../components/StatusTag'
import { fmtDateTime, fmtQty, toApiDate } from '../utils/format'

export default function Moves() {
  const [search, setSearch] = useState('')
  const [kinds, setKinds] = useState<string[]>([])
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)

  const moves = useList<StockMove>('/warehouse/moves/', {
    search,
    kind: kinds,
    date_from: toApiDate(range?.[0]) ?? undefined,
    date_to: toApiDate(range?.[1]) ?? undefined,
  })

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Input.Search placeholder="Партия, номенклатура, основание" allowClear onSearch={setSearch} style={{ maxWidth: 300 }} />
        <Select mode="multiple" allowClear placeholder="Вид движения" style={{ minWidth: 260 }} value={kinds} onChange={setKinds}
          options={statusOptions(MOVE_KIND)} />
        <DatePicker.RangePicker value={range} onChange={(v) => setRange(v)} />
      </div>
      <Table<StockMove>
        rowKey="id"
        size="middle"
        loading={moves.isLoading}
        dataSource={moves.data}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        columns={[
          { title: 'Дата', dataIndex: 'created_at', render: fmtDateTime, width: 150 },
          { title: 'Вид', dataIndex: 'kind', render: (k: string) => <StatusTag map={MOVE_KIND} value={k} /> },
          { title: 'Партия', dataIndex: 'lot_number' },
          { title: 'Номенклатура', dataIndex: 'item_name' },
          {
            title: 'Количество', align: 'right',
            render: (_, m) => (
              <Typography.Text type={Number(m.quantity) < 0 ? 'danger' : 'success'}>
                {Number(m.quantity) > 0 ? '+' : ''}{fmtQty(m.quantity, m.unit_code)}
              </Typography.Text>
            ),
          },
          { title: 'Основание', dataIndex: 'reference' },
          { title: 'Кто', dataIndex: 'created_by_name', render: (v) => v ?? '—' },
        ]}
      />
    </>
  )
}
