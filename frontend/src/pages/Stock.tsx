import { Button, Form, Input, InputNumber, Modal, Segmented, Switch, Table, Tag, Typography, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { useApiAction, useList } from '../api/hooks'
import type { ItemKind, Lot, StockRow } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { fmtDate, fmtMoney, fmtQty } from '../utils/format'

function ExpiryTag({ lot }: { lot: Lot }) {
  if (lot.expiry_status === 'expired') return <Tag color="red">Просрочена</Tag>
  if (lot.expiry_status === 'expiring') return <Tag color="orange">Истекает через {lot.days_left} дн.</Tag>
  return <Tag color="green">Годна ещё {lot.days_left} дн.</Tag>
}

function StockTag({ row }: { row: StockRow }) {
  if (Number(row.available) <= 0) return <Tag>Нет в наличии</Tag>
  if (row.below_min) return <Tag color="red">Ниже минимума</Tag>
  return <Tag color="green">В норме</Tag>
}

function LotsTable({ item, canWriteOff }: { item: number; canWriteOff: boolean }) {
  const lots = useList<Lot>('/warehouse/lots/', { item, in_stock: true })
  const [target, setTarget] = useState<Lot | null>(null)
  const [form] = Form.useForm()

  const writeOff = useApiAction(
    (v: { quantity: string; reason: string }) => api.post(`/warehouse/lots/${target!.id}/write_off/`, v),
    { success: 'Списано', invalidate: ['/warehouse/lots/', '/warehouse/stock/', '/warehouse/moves/'], onSuccess: () => setTarget(null) },
  )

  const columns: TableColumnsType<Lot> = [
    { title: 'Партия', dataIndex: 'number' },
    { title: 'Поставщик', dataIndex: 'supplier_name', render: (v) => v ?? '—' },
    { title: 'Поступила', dataIndex: 'date', render: fmtDate },
    { title: 'Годен до', dataIndex: 'expiry_date', render: fmtDate },
    { title: 'Срок', render: (_, lot) => <ExpiryTag lot={lot} /> },
    { title: 'Остаток', align: 'right', render: (_, lot) => fmtQty(lot.balance, lot.unit_code) },
    { title: 'Себестоимость ед.', dataIndex: 'unit_cost', align: 'right', render: fmtMoney },
    ...(canWriteOff
      ? [{ key: 'actions', render: (_: unknown, lot: Lot) => <Button size="small" danger onClick={() => setTarget(lot)}>Списать</Button> }]
      : []),
  ]

  return (
    <>
      <Table rowKey="id" size="small" pagination={false} loading={lots.isLoading} dataSource={lots.data} columns={columns} />
      <Modal
        title={`Списание с партии ${target?.number}`}
        open={!!target}
        onCancel={() => setTarget(null)}
        onOk={() => form.submit()}
        okText="Списать"
        okButtonProps={{ danger: true, loading: writeOff.isPending }}
        destroyOnHidden
      >
        <Typography.Paragraph type="secondary">
          {target?.item_name}: остаток {fmtQty(target?.balance, target?.unit_code)}
        </Typography.Paragraph>
        <Form form={form} layout="vertical" preserve={false} onFinish={(v) => writeOff.mutate(v)}
          initialValues={{ reason: target?.expiry_status === 'expired' ? 'Истёк срок годности' : '', quantity: target?.balance }}>
          <Form.Item name="quantity" label="Количество" rules={[{ required: true }]}>
            <InputNumber min="0.001" max={target?.balance} stringMode suffix={target?.unit_code} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="reason" label="Причина" rules={[{ required: true }]}><Input placeholder="Брак, порча, просрочка…" /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}

export default function Stock() {
  const { can } = useAuth()
  const [kind, setKind] = useState<ItemKind>('raw')
  const [belowMin, setBelowMin] = useState(false)
  const [search, setSearch] = useState('')
  const stock = useList<StockRow>('/warehouse/stock/', { kind, search, below_min: belowMin || undefined })

  const columns: TableColumnsType<StockRow> = [
    { title: 'Артикул', dataIndex: 'code', width: 110 },
    { title: 'Номенклатура', dataIndex: 'name' },
    { title: 'Доступно', align: 'right', render: (_, r) => <b>{fmtQty(r.available, r.unit_code)}</b> },
    {
      title: 'Просрочено', align: 'right',
      render: (_, r) => (Number(r.expired) > 0 ? <Typography.Text type="danger">{fmtQty(r.expired, r.unit_code)}</Typography.Text> : '—'),
    },
    ...(kind === 'raw' ? [{ title: 'Мин. остаток', align: 'right' as const, render: (_: unknown, r: StockRow) => fmtQty(r.min_stock, r.unit_code) }] : []),
    { title: 'Ближайший срок', dataIndex: 'nearest_expiry', render: fmtDate },
    { title: 'Состояние', render: (_, r) => <StockTag row={r} /> },
  ]

  return (
    <>
      <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <Segmented<ItemKind> value={kind} onChange={setKind} options={[{ value: 'raw', label: 'Сырьё' }, { value: 'product', label: 'Готовая продукция' }]} />
        <Input.Search placeholder="Артикул или название" allowClear onSearch={setSearch} style={{ maxWidth: 280 }} />
        <span><Switch checked={belowMin} onChange={setBelowMin} /> Только ниже минимума</span>
      </div>
      <Table<StockRow>
        rowKey="id"
        size="middle"
        loading={stock.isLoading}
        dataSource={stock.data}
        columns={columns}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        expandable={{
          expandedRowRender: (r) => <LotsTable item={r.id} canWriteOff={can('storekeeper')} />,
          rowExpandable: (r) => Number(r.balance) > 0,
          expandRowByClick: true,
        }}
      />
    </>
  )
}
