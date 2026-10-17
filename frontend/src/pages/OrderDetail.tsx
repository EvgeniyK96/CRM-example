import { ArrowLeftOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import {
  Alert, Button, Card, DatePicker, Descriptions, Form, Input, InputNumber, Popconfirm, Select, Space, Table, Typography,
} from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { toOptions, useApiAction, useDetail, useList } from '../api/hooks'
import { CLIENT_KIND, SALES_ORDER_STATUS, TASK_STATUS } from '../api/statuses'
import type { AvailabilityRow, Client, ProductionTask, SalesOrder, SalesOrderLine } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { useItemLineColumns } from '../components/itemLineColumns'
import LinesFormList from '../components/LinesFormList'
import ShipModal from '../components/ShipModal'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtDateTime, fmtMoney, fmtQty, fromApiDate, toApiDate } from '../utils/format'

const URL = '/sales/orders/'

export default function OrderDetail() {
  const { id } = useParams()
  const { can } = useAuth()
  const navigate = useNavigate()
  const { data: order, isLoading } = useDetail<SalesOrder>(URL, id)
  const [shipping, setShipping] = useState(false)

  // Подтверждение и отмена меняют резервы — обновляем все данные
  const action = (name: string, success: string) =>
    () => api.post(`${URL}${id}/${name}/`).then(() => success)
  const confirm = useApiAction(action('confirm', 'Заказ подтверждён'), { success: (m) => m, invalidate: 'all' })
  const reopen = useApiAction(action('reopen', 'Заказ возвращён в работу, резервы сняты'), { success: (m) => m, invalidate: 'all' })
  const cancel = useApiAction(action('cancel', 'Заказ отменён'), { success: (m) => m, invalidate: 'all' })
  const remove = useApiAction(() => api.delete(`${URL}${id}/`), {
    success: 'Черновик удалён', invalidate: [URL], onSuccess: () => navigate('/orders'),
  })

  if (isLoading || !order) return <Card loading />

  const isSales = can('sales')
  const isNew = order.status === 'new'
  const canReopen = order.status === 'confirmed' || order.status === 'ready'
  const canShip = order.status === 'ready' && can('storekeeper')

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Link to="/orders"><ArrowLeftOutlined /> Все заказы</Link>
      <Card
        title={<>Заказ {order.number} <StatusTag map={SALES_ORDER_STATUS} value={order.status} /></>}
        extra={(isSales || canShip) && (
          <Space wrap>
            {canShip && <Button type="primary" onClick={() => setShipping(true)}>Отгрузить</Button>}
            {isSales && isNew && (
              <Popconfirm title="Удалить заказ?" onConfirm={() => remove.mutate()}><Button danger>Удалить</Button></Popconfirm>
            )}
            {isSales && (isNew || canReopen) && (
              <Popconfirm title="Отменить заказ? Резервы будут сняты." onConfirm={() => cancel.mutate()}><Button>Отменить</Button></Popconfirm>
            )}
            {isSales && canReopen && (
              <Popconfirm title="Вернуть заказ в работу для изменений? Резервы будут сняты." onConfirm={() => reopen.mutate()}>
                <Button loading={reopen.isPending}>Вернуть в работу</Button>
              </Popconfirm>
            )}
            {isSales && isNew && (
              <Popconfirm
                title="Подтвердить заказ?"
                description="Свободная продукция будет зарезервирована, недостающее уйдёт в производство."
                onConfirm={() => confirm.mutate()}
              >
                <Button type="primary" loading={confirm.isPending}>Подтвердить</Button>
              </Popconfirm>
            )}
          </Space>
        )}
      >
        <Descriptions size="small" column={{ xs: 1, md: 3 }} items={[
          { label: 'Клиент', children: <>{order.client_name} <StatusTag map={CLIENT_KIND} value={order.client_kind} /></> },
          { label: 'Дата отгрузки', children: fmtDate(order.delivery_date) },
          { label: 'Сумма', children: <span style={{ whiteSpace: 'nowrap' }}>{fmtMoney(order.total)}</span> },
          { label: 'Адрес доставки', children: order.delivery_address || '—' },
          { label: 'Скидка', children: Number(order.discount_percent) ? `${Number(order.discount_percent)}%` : '—' },
          { label: 'Менеджер', children: order.created_by_name ?? '—' },
          { label: 'Создан', children: fmtDateTime(order.created_at) },
          {
            label: 'Подтверждён',
            children: order.confirmed_at ? `${order.confirmed_by_name ?? '—'}, ${fmtDateTime(order.confirmed_at)}` : '—',
          },
          { label: 'Комментарий', children: order.comment || '—' },
          ...(order.shipment
            ? [{ label: 'Накладная', children: <Link to={`/shipments/${order.shipment}`}>{order.shipment_number}</Link> }]
            : []),
        ]} />
      </Card>
      <ShipModal order={shipping ? order : null} onClose={() => setShipping(false)} />

      {isNew && isSales ? (
        <>
          <OrderEditor order={order} />
          <Availability order={order} />
        </>
      ) : (
        <OrderLines order={order} />
      )}
      {order.status !== 'new' && <OrderTasks order={order} />}
    </Space>
  )
}

/** Производственные задания, которые закрывают этот заказ. */
function OrderTasks({ order }: { order: SalesOrder }) {
  const tasks = useList<ProductionTask>('/production/tasks/', { order: order.id })
  if (!tasks.data?.length) return null
  return (
    <Card title="Производство" size="small">
      <Table<ProductionTask> rowKey="id" size="small" pagination={false} dataSource={tasks.data} columns={[
        { title: 'Задание', render: (_, t) => <Link to={`/tasks/${t.id}`}>{t.number}</Link> },
        { title: 'Продукт', dataIndex: 'product_name' },
        { title: 'Цех', dataIndex: 'department_name' },
        { title: 'Дата', dataIndex: 'planned_date', render: fmtDate },
        {
          title: 'Для заказа', align: 'right',
          render: (_, t) => fmtQty(t.allocations.find((a) => a.order === order.id)?.quantity, t.unit_code),
        },
        { title: 'Статус', dataIndex: 'status', render: (s: string) => <StatusTag map={TASK_STATUS} value={s} /> },
      ]} />
    </Card>
  )
}

function OrderLines({ order }: { order: SalesOrder }) {
  const confirmed = order.status !== 'new' && order.status !== 'cancelled'
  return (
    <Card title="Состав заказа" size="small">
      <Table<SalesOrderLine> rowKey="id" size="small" pagination={false} dataSource={order.lines} columns={[
        { title: 'Продукция', dataIndex: 'item_name' },
        { title: 'Количество', align: 'right', render: (_, l) => fmtQty(l.quantity, l.unit_code) },
        { title: 'Цена', dataIndex: 'price', align: 'right', render: fmtMoney },
        { title: 'Сумма', dataIndex: 'amount', align: 'right', render: fmtMoney },
        ...(confirmed
          ? [
            { title: 'Со склада (резерв)', align: 'right' as const, render: (_: unknown, l: SalesOrderLine) => fmtQty(l.reserved_qty, l.unit_code) },
            {
              title: 'Произвести', align: 'right' as const,
              render: (_: unknown, l: SalesOrderLine) =>
                Number(l.to_produce) > 0 ? <Typography.Text type="warning" strong>{fmtQty(l.to_produce, l.unit_code)}</Typography.Text> : '—',
            },
          ]
          : []),
      ]} />
    </Card>
  )
}

function OrderEditor({ order }: { order: SalesOrder }) {
  const [form] = Form.useForm()
  const clients = useList<Client>('/sales/clients/', { is_active: true })
  // Пустая цена в строке — сервер возьмёт цену из прайса со скидкой заказа; здесь показываем её же
  const columns = useItemLineColumns({
    kind: 'product',
    defaultPrice: (item, get) => Number(item.sale_price) * (1 - Number(get('discount_percent') || 0) / 100),
  })
  const save = useApiAction((v: object) => api.patch(`${URL}${order.id}/`, v), { success: 'Сохранено', invalidate: [URL] })

  // Смена клиента подставляет его скидку и адрес доставки
  const onValuesChange = (changed: { client?: number }) => {
    const client = changed.client && clients.data?.find((c) => c.id === changed.client)
    if (client) form.setFieldsValue({ discount_percent: client.discount_percent, delivery_address: client.delivery_address })
  }

  const resetPrices = () =>
    form.setFieldValue('lines', (form.getFieldValue('lines') ?? []).map((l: SalesOrderLine) => ({ ...l, price: null })))

  return (
    <Card title="Состав заказа" size="small"
      extra={<Button type="primary" loading={save.isPending} onClick={() => form.submit()}>Сохранить</Button>}>
      <Form form={form} layout="vertical" onValuesChange={onValuesChange}
        initialValues={{ ...order, delivery_date: fromApiDate(order.delivery_date) }}
        onFinish={(v) => save.mutate({ ...v, delivery_date: toApiDate(v.delivery_date as Dayjs) })}>
        <Space wrap size="middle" align="start">
          <Form.Item name="client" label="Клиент" rules={[{ required: true }]} style={{ width: 300 }}>
            <Select showSearch={{ optionFilterProp: 'label' }} options={toOptions(clients.data, (c) => c.name)} />
          </Form.Item>
          <Form.Item name="delivery_date" label="Дата отгрузки" rules={[{ required: true }]}>
            <DatePicker disabledDate={(d) => d.isBefore(dayjs(), 'day')} />
          </Form.Item>
          <Form.Item name="discount_percent" label="Скидка, %" style={{ width: 120 }}>
            <InputNumber min="0" max="99.99" stringMode style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="delivery_address" label="Адрес доставки" style={{ width: 320 }}><Input /></Form.Item>
          <Form.Item name="comment" label="Комментарий" style={{ width: 320 }}><Input /></Form.Item>
        </Space>
        <LinesFormList columns={columns} newLine={{ price: null }} addLabel="Добавить продукцию" />
        <Button size="small" onClick={resetPrices}>Пересчитать цены по прайсу со скидкой</Button>
      </Form>
    </Card>
  )
}

function Availability({ order }: { order: SalesOrder }) {
  const query = useQuery({
    queryKey: [URL, String(order.id), 'availability', order.lines, order.delivery_date],
    queryFn: async () => (await api.get<AvailabilityRow[]>(`${URL}${order.id}/availability/`)).data,
    enabled: order.lines.length > 0,
  })
  const shortage = query.data?.filter((r) => Number(r.to_produce) > 0) ?? []

  return (
    <Card title={`Наличие на ${fmtDate(order.delivery_date)}`} size="small">
      {order.lines.length === 0 ? (
        <Typography.Text type="secondary">Добавьте позиции и сохраните заказ, чтобы проверить наличие.</Typography.Text>
      ) : (
        <>
          {query.data && (
            <Alert
              style={{ marginBottom: 12 }}
              type={shortage.length ? 'warning' : 'success'}
              showIcon
              title={shortage.length
                ? `Не хватает ${shortage.length} поз. — после подтверждения недостающее уйдёт в производство`
                : 'Всё есть на складе — после подтверждения заказ будет готов к отгрузке'}
            />
          )}
          <Table<AvailabilityRow> rowKey="line" size="small" pagination={false} loading={query.isFetching} dataSource={query.data}
            columns={[
              { title: 'Продукция', dataIndex: 'item_name' },
              { title: 'Заказано', align: 'right', render: (_, r) => fmtQty(r.quantity, r.unit_code) },
              { title: 'Свободно (годно на дату отгрузки)', align: 'right', render: (_, r) => fmtQty(r.free_stock, r.unit_code) },
              { title: 'Со склада', align: 'right', render: (_, r) => fmtQty(r.from_stock, r.unit_code) },
              {
                title: 'Произвести', align: 'right',
                render: (_, r) => Number(r.to_produce) > 0
                  ? <Typography.Text type="warning" strong>{fmtQty(r.to_produce, r.unit_code)}</Typography.Text> : '—',
              },
            ]} />
          <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            Расчёт по сохранённой версии заказа с учётом резервов других подтверждённых заказов.
          </Typography.Text>
        </>
      )}
    </Card>
  )
}
