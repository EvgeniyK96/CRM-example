import { ArrowLeftOutlined } from '@ant-design/icons'
import { Button, Card, DatePicker, Descriptions, Form, Input, Popconfirm, Select, Space, Table } from 'antd'
import type { Dayjs } from 'dayjs'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { toOptions, useApiAction, useDetail, useList } from '../api/hooks'
import { PO_STATUS, RECEIPT_STATUS } from '../api/statuses'
import type { PurchaseOrder, PurchaseOrderLine, Receipt, Supplier } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import LinesFormList from '../components/LinesFormList'
import { useItemLineColumns } from '../components/itemLineColumns'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtDateTime, fmtMoney, fmtQty, fromApiDate, toApiDate } from '../utils/format'

const URL = '/purchasing/orders/'
const RECEIPTS = '/purchasing/receipts/'

export default function PurchaseOrderDetail() {
  const { id } = useParams()
  const { can } = useAuth()
  const navigate = useNavigate()
  const { data: order, isLoading } = useDetail<PurchaseOrder>(URL, id)
  const receipts = useList<Receipt>(RECEIPTS, { order: id }, !!order)

  const post = (action: string) => () => api.post(`${URL}${id}/${action}/`)
  const send = useApiAction(post('send'), { success: 'Заявка отправлена поставщику', invalidate: [URL] })
  const cancel = useApiAction(post('cancel'), { success: 'Заявка отменена', invalidate: [URL, RECEIPTS] })
  const receive = useApiAction(async () => (await api.post<Receipt>(`${URL}${id}/receive/`)).data, {
    invalidate: [RECEIPTS],
    onSuccess: (r) => navigate(`/receipts/${r.id}`),
  })
  const remove = useApiAction(() => api.delete(`${URL}${id}/`), {
    success: 'Черновик удалён', invalidate: [URL], onSuccess: () => navigate('/purchase-orders'),
  })

  if (isLoading || !order) return <Card loading />

  const isStore = can('storekeeper')
  const draft = order.status === 'draft'
  const awaiting = order.status === 'sent' || order.status === 'partial'

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Link to="/purchase-orders"><ArrowLeftOutlined /> Все заявки</Link>
      <Card
        title={<>Заявка {order.number} <StatusTag map={PO_STATUS} value={order.status} /></>}
        extra={isStore && (
          <Space wrap>
            {draft && (
              <Popconfirm title="Удалить черновик?" onConfirm={() => remove.mutate()}><Button danger>Удалить</Button></Popconfirm>
            )}
            {(draft || order.status === 'sent') && (
              <Popconfirm title="Отменить заявку?" onConfirm={() => cancel.mutate()}><Button>Отменить заявку</Button></Popconfirm>
            )}
            {draft && <Button type="primary" loading={send.isPending} onClick={() => send.mutate()}>Отправить поставщику</Button>}
            {awaiting && <Button type="primary" loading={receive.isPending} onClick={() => receive.mutate()}>Принять поставку</Button>}
          </Space>
        )}
      >
        <Descriptions size="small" column={{ xs: 1, md: 3 }} items={[
          { label: 'Поставщик', children: order.supplier_name },
          { label: 'Ожидается', children: fmtDate(order.expected_date) },
          { label: 'Сумма', children: <span style={{ whiteSpace: 'nowrap' }}>{fmtMoney(order.total)}</span> },
          { label: 'Автор', children: order.created_by_name ?? '—' },
          { label: 'Создана', children: fmtDateTime(order.created_at) },
          { label: 'Комментарий', children: order.comment || '—' },
        ]} />
      </Card>

      {draft && isStore ? <OrderEditor order={order} /> : <OrderLines lines={order.lines} />}

      {receipts.data && receipts.data.length > 0 && (
        <Card title="Приёмки по заявке" size="small">
          <Table<Receipt> rowKey="id" size="small" pagination={false} dataSource={receipts.data}
            onRow={(r) => ({ onClick: () => navigate(`/receipts/${r.id}`), style: { cursor: 'pointer' } })}
            columns={[
              { title: 'Номер', dataIndex: 'number' },
              { title: 'Дата', dataIndex: 'date', render: fmtDate },
              { title: 'Сумма', dataIndex: 'total', align: 'right', render: fmtMoney },
              { title: 'Статус', dataIndex: 'status', render: (s: string) => <StatusTag map={RECEIPT_STATUS} value={s} /> },
            ]} />
        </Card>
      )}
    </Space>
  )
}

function OrderLines({ lines }: { lines: PurchaseOrderLine[] }) {
  return (
    <Card title="Состав заявки" size="small">
      <Table<PurchaseOrderLine> rowKey="id" size="small" pagination={false} dataSource={lines} columns={[
        { title: 'Сырьё', dataIndex: 'item_name' },
        { title: 'Заказано', align: 'right', render: (_, l) => fmtQty(l.quantity, l.unit_code) },
        { title: 'Получено', align: 'right', render: (_, l) => fmtQty(l.received, l.unit_code) },
        { title: 'Цена', dataIndex: 'price', align: 'right', render: fmtMoney },
        { title: 'Сумма', dataIndex: 'amount', align: 'right', render: fmtMoney },
      ]} />
    </Card>
  )
}

function OrderEditor({ order }: { order: PurchaseOrder }) {
  const [form] = Form.useForm()
  const columns = useItemLineColumns({ kind: 'raw' })
  const suppliers = useList<Supplier>('/catalog/suppliers/', { is_active: true })
  const save = useApiAction((v: object) => api.patch(`${URL}${order.id}/`, v), { success: 'Сохранено', invalidate: [URL] })

  return (
    <Card title="Состав заявки (черновик)" size="small"
      extra={<Button type="primary" loading={save.isPending} onClick={() => form.submit()}>Сохранить</Button>}>
      <Form form={form} layout="vertical"
        initialValues={{ ...order, expected_date: fromApiDate(order.expected_date) }}
        onFinish={(v) => save.mutate({ ...v, expected_date: toApiDate(v.expected_date as Dayjs | null) })}>
        <Space wrap size="middle">
          <Form.Item name="supplier" label="Поставщик" rules={[{ required: true }]} style={{ width: 300 }}>
            <Select options={toOptions(suppliers.data, (s) => s.name)} />
          </Form.Item>
          <Form.Item name="expected_date" label="Ожидаемая дата"><DatePicker /></Form.Item>
          <Form.Item name="comment" label="Комментарий" style={{ width: 360 }}><Input /></Form.Item>
        </Space>
        <LinesFormList columns={columns} newLine={{ price: '0' }} addLabel="Добавить сырьё" />
      </Form>
    </Card>
  )
}
