import { ArrowLeftOutlined } from '@ant-design/icons'
import { Alert, Button, Card, DatePicker, Descriptions, Form, Input, Popconfirm, Select, Space, Table } from 'antd'
import type { Dayjs } from 'dayjs'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { toOptions, useApiAction, useDetail, useList } from '../api/hooks'
import { RECEIPT_STATUS } from '../api/statuses'
import type { Receipt, ReceiptLine, Supplier } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import LinesFormList from '../components/LinesFormList'
import { useItemLineColumns } from '../components/itemLineColumns'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtDateTime, fmtMoney, fmtQty, fromApiDate, toApiDate } from '../utils/format'

const URL = '/purchasing/receipts/'

export default function ReceiptDetail() {
  const { id } = useParams()
  const { can } = useAuth()
  const navigate = useNavigate()
  const { data: receipt, isLoading } = useDetail<Receipt>(URL, id)

  // Проведение меняет склад и статус заявки — обновляем всё
  const postReceipt = useApiAction(() => api.post(`${URL}${id}/post/`), { success: 'Приёмка проведена, партии созданы', invalidate: 'all' })
  const remove = useApiAction(() => api.delete(`${URL}${id}/`), {
    success: 'Черновик удалён', invalidate: [URL], onSuccess: () => navigate('/receipts'),
  })

  if (isLoading || !receipt) return <Card loading />

  const editable = receipt.status === 'draft' && can('storekeeper')

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Link to="/receipts"><ArrowLeftOutlined /> Все приёмки</Link>
      <Card
        title={<>Приёмка {receipt.number} <StatusTag map={RECEIPT_STATUS} value={receipt.status} /></>}
        extra={editable && (
          <Space>
            <Popconfirm title="Удалить черновик?" onConfirm={() => remove.mutate()}><Button danger>Удалить</Button></Popconfirm>
            <Popconfirm title="Провести приёмку? На складе появятся партии, документ станет неизменяемым." onConfirm={() => postReceipt.mutate()}>
              <Button type="primary" loading={postReceipt.isPending}>Провести</Button>
            </Popconfirm>
          </Space>
        )}
      >
        <Descriptions size="small" column={{ xs: 1, md: 3 }} items={[
          { label: 'Поставщик', children: receipt.supplier_name },
          { label: 'Дата', children: fmtDate(receipt.date) },
          { label: 'Накладная', children: receipt.invoice_number || '—' },
          {
            label: 'Заявка',
            children: receipt.order ? <Link to={`/purchase-orders/${receipt.order}`}>{receipt.order_number}</Link> : 'без заявки',
          },
          { label: 'Сумма', children: <span style={{ whiteSpace: 'nowrap' }}>{fmtMoney(receipt.total)}</span> },
          { label: 'Провёл', children: receipt.posted_at ? `${receipt.posted_by_name ?? '—'}, ${fmtDateTime(receipt.posted_at)}` : '—' },
        ]} />
      </Card>

      {editable ? <ReceiptEditor receipt={receipt} /> : <ReceiptLines lines={receipt.lines} />}
    </Space>
  )
}

function ReceiptLines({ lines }: { lines: ReceiptLine[] }) {
  return (
    <Card title="Принято" size="small">
      <Table<ReceiptLine> rowKey="id" size="small" pagination={false} dataSource={lines} columns={[
        { title: 'Сырьё', dataIndex: 'item_name' },
        { title: 'Количество', align: 'right', render: (_, l) => fmtQty(l.quantity, l.unit_code) },
        { title: 'Цена', dataIndex: 'price', align: 'right', render: fmtMoney },
        { title: 'Сумма', dataIndex: 'amount', align: 'right', render: fmtMoney },
        { title: 'Годен до', dataIndex: 'expiry_date', render: fmtDate },
        { title: 'Партия', dataIndex: 'lot_number', render: (v) => v ?? '—' },
      ]} />
    </Card>
  )
}

function ReceiptEditor({ receipt }: { receipt: Receipt }) {
  const [form] = Form.useForm()
  const suppliers = useList<Supplier>('/catalog/suppliers/', { is_active: true })
  // Строки из заявки нельзя переназначить на другое сырьё — только поправить количество, цену и срок
  const base = useItemLineColumns({ kind: 'raw', lockItem: (line) => !!line.order_line })
  const columns = [
    ...base.slice(0, 3),
    {
      title: 'Годен до',
      width: 'minmax(130px, 1fr)',
      render: (i: number) => (
        <Form.Item name={[i, 'expiry_date']}><DatePicker placeholder="по нормативу" style={{ width: '100%' }} /></Form.Item>
      ),
    },
    base[3],
  ]

  const save = useApiAction((v: object) => api.patch(`${URL}${receipt.id}/`, v), { success: 'Сохранено', invalidate: [URL] })

  const initial = {
    ...receipt,
    date: fromApiDate(receipt.date),
    lines: receipt.lines.map((l) => ({ ...l, expiry_date: fromApiDate(l.expiry_date) })),
  }

  const submit = (v: { date: Dayjs; lines?: (ReceiptLine & { expiry_date: Dayjs | null })[] }) =>
    save.mutate({
      ...v,
      date: toApiDate(v.date),
      lines: (v.lines ?? []).map((l) => ({ ...l, expiry_date: toApiDate(l.expiry_date) })),
    })

  return (
    <Card title="Строки приёмки (черновик)" size="small"
      extra={<Button type="primary" loading={save.isPending} onClick={() => form.submit()}>Сохранить</Button>}>
      <Alert type="info" showIcon style={{ marginBottom: 16 }}
        title="Если срок годности не указан, он рассчитается от даты приёмки по нормативу из номенклатуры." />
      <Form form={form} layout="vertical" initialValues={initial} onFinish={submit}>
        <Space wrap size="middle">
          <Form.Item name="supplier" label="Поставщик" rules={[{ required: true }]} style={{ width: 300 }}>
            <Select disabled={!!receipt.order} options={toOptions(suppliers.data, (s) => s.name)} />
          </Form.Item>
          <Form.Item name="date" label="Дата приёмки" rules={[{ required: true }]}><DatePicker /></Form.Item>
          <Form.Item name="invoice_number" label="Накладная поставщика"><Input /></Form.Item>
          <Form.Item name="comment" label="Комментарий" style={{ width: 300 }}><Input /></Form.Item>
        </Space>
        <LinesFormList columns={columns} newLine={{ price: '0', order_line: null }} hiddenFields={['order_line']} addLabel="Добавить сырьё" />
      </Form>
    </Card>
  )
}
