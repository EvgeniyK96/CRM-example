import { ArrowLeftOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import {
  Alert, App, Button, Card, DatePicker, Descriptions, Form, Input, InputNumber, Modal, Popconfirm, Space, Table, Typography,
} from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useApiAction, useDetail } from '../api/hooks'
import { SALES_ORDER_STATUS, TASK_STATUS } from '../api/statuses'
import type { ProductionTask, PurchaseOrder, Requirement, TaskAllocation, TaskConsumption } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtDateTime, fmtMoney, fmtQty, fromApiDate, toApiDate } from '../utils/format'

const URL = '/production/tasks/'

export default function TaskDetail() {
  const { id } = useParams()
  const { canManageDepartment } = useAuth()
  const { data: task, isLoading } = useDetail<ProductionTask>(URL, id)
  const [finishing, setFinishing] = useState(false)

  // Запуск, выпуск и отмена меняют склад и статусы заказов — обновляем всё
  const start = useApiAction(() => api.post(`${URL}${id}/start/`), { success: 'Задание запущено, сырьё списано', invalidate: 'all' })
  const cancel = useApiAction(() => api.post(`${URL}${id}/cancel/`), { success: 'Задание отменено', invalidate: 'all' })

  if (isLoading || !task) return <Card loading />

  const manage = canManageDepartment(task.department)

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Link to="/tasks"><ArrowLeftOutlined /> Все задания</Link>
      <Card
        title={<>Задание {task.number} <StatusTag map={TASK_STATUS} value={task.status} /></>}
        extra={manage && (
          <Space wrap>
            {task.status === 'planned' && (
              <>
                <Popconfirm title="Отменить задание?" description="Связанные заказы вернутся к планированию." onConfirm={() => cancel.mutate()}>
                  <Button>Отменить</Button>
                </Popconfirm>
                <Popconfirm title="Запустить задание?" description="Сырьё по рецептуре будет списано со склада (FEFO)."
                  onConfirm={() => start.mutate()}>
                  <Button type="primary" loading={start.isPending}>Запустить</Button>
                </Popconfirm>
              </>
            )}
            {task.status === 'in_progress' && <Button type="primary" onClick={() => setFinishing(true)}>Завершить</Button>}
          </Space>
        )}
      >
        <Descriptions size="small" column={{ xs: 1, md: 3 }} items={[
          { label: 'Цех', children: task.department_name },
          { label: 'Продукт', children: task.product_name },
          { label: 'Рецептура', children: <Link to={`/recipes/${task.recipe}`}>версия {task.recipe_version}</Link> },
          { label: 'План', children: `${fmtQty(task.planned_qty, task.unit_code)} на ${fmtDate(task.planned_date)}` },
          { label: 'Выпущено', children: task.actual_qty == null ? '—' : fmtQty(task.actual_qty, task.unit_code) },
          { label: 'Брак', children: Number(task.defect_qty) ? fmtQty(task.defect_qty, task.unit_code) : '—' },
          { label: 'Стоимость сырья', children: task.raw_cost == null ? '—' : fmtMoney(task.raw_cost) },
          { label: 'Себестоимость ед.', children: task.unit_cost == null ? '—' : fmtMoney(task.unit_cost) },
          {
            label: 'Партия продукции',
            children: task.output_lot ? <Link to={`/trace/${task.output_lot}`}>{task.output_lot_number}</Link> : '—',
          },
          { label: 'Создал', children: `${task.created_by_name ?? '—'}, ${fmtDateTime(task.created_at)}` },
          { label: 'Запустил', children: task.started_at ? `${task.started_by_name}, ${fmtDateTime(task.started_at)}` : '—' },
          { label: 'Завершил', children: task.finished_at ? `${task.finished_by_name}, ${fmtDateTime(task.finished_at)}` : '—' },
          { label: 'Комментарий', children: task.comment ? <span style={{ whiteSpace: 'pre-wrap' }}>{task.comment}</span> : '—' },
        ]} />
      </Card>

      {task.status === 'planned' && manage && <PlanEditor task={task} />}
      {task.status === 'planned' && <Requirements task={task} canRequest={manage} />}
      {(task.status === 'in_progress' || task.status === 'done') && <Consumptions task={task} />}
      {task.allocations.length > 0 && <Allocations task={task} />}

      <FinishModal task={task} open={finishing} onClose={() => setFinishing(false)} />
    </Space>
  )
}

function PlanEditor({ task }: { task: ProductionTask }) {
  const save = useApiAction((v: object) => api.patch(`${URL}${task.id}/`, v), { success: 'Сохранено', invalidate: [URL] })
  return (
    <Card size="small" title="План">
      <Form layout="inline" initialValues={{ ...task, planned_date: fromApiDate(task.planned_date) }}
        onFinish={(v) => save.mutate({ ...v, planned_date: toApiDate(v.planned_date as Dayjs) })}>
        <Form.Item name="planned_qty" label="Количество" rules={[{ required: true }]}>
          <InputNumber min="0.001" stringMode suffix={task.unit_code} style={{ width: 160 }} />
        </Form.Item>
        <Form.Item name="planned_date" label="Дата" rules={[{ required: true }]}>
          <DatePicker disabledDate={(d) => d.isBefore(dayjs(), 'day')} />
        </Form.Item>
        <Form.Item name="comment" label="Комментарий"><Input style={{ width: 260 }} /></Form.Item>
        <Button type="primary" htmlType="submit" loading={save.isPending}>Сохранить</Button>
      </Form>
    </Card>
  )
}

function Requirements({ task, canRequest }: { task: ProductionTask; canRequest: boolean }) {
  const { modal } = App.useApp()
  const query = useQuery({
    queryKey: [URL, String(task.id), 'requirements', task.planned_qty],
    queryFn: async () => (await api.get<Requirement[]>(`${URL}${task.id}/requirements/`)).data,
  })
  const shortages = query.data?.filter((r) => Number(r.shortage) > 0) ?? []

  const purchase = useApiAction(
    async () => (await api.post<{ orders: PurchaseOrder[]; skipped: string[] }>(`${URL}${task.id}/request_purchase/`)).data,
    {
      invalidate: ['/purchasing/orders/'],
      onSuccess: ({ orders, skipped }) => modal.success({
        title: 'Созданы черновики заявок поставщикам',
        content: (
          <>
            {orders.map((o) => (
              <div key={o.id}><Link to={`/purchase-orders/${o.id}`} onClick={() => Modal.destroyAll()}>{o.number}</Link> — {o.supplier_name}</div>
            ))}
            {skipped.length > 0 && (
              <Typography.Paragraph type="warning" style={{ marginTop: 8 }}>
                Без истории поставок (заявку нужно создать вручную): {skipped.join(', ')}
              </Typography.Paragraph>
            )}
          </>
        ),
      }),
    },
  )

  return (
    <Card size="small" title={`Сырьё на ${fmtQty(task.planned_qty, task.unit_code)}`}
      extra={shortages.length > 0 && canRequest && (
        <Button loading={purchase.isPending} onClick={() => purchase.mutate()}>Заявка поставщику на недостающее</Button>
      )}>
      {query.data && (
        <Alert style={{ marginBottom: 12 }} showIcon type={shortages.length ? 'error' : 'success'}
          title={shortages.length ? `Не хватает ${shortages.length} поз. — запуск невозможен` : 'Сырья достаточно для запуска'} />
      )}
      <Table<Requirement> rowKey="ingredient" size="small" pagination={false} loading={query.isLoading} dataSource={query.data}
        columns={[
          { title: 'Сырьё', dataIndex: 'ingredient_name' },
          { title: 'Нужно', align: 'right', render: (_, r) => fmtQty(r.quantity, r.unit_code) },
          { title: 'Доступно (без просрочки)', align: 'right', render: (_, r) => fmtQty(r.available, r.unit_code) },
          {
            title: 'Не хватает', align: 'right',
            render: (_, r) => Number(r.shortage) > 0 ? <Typography.Text type="danger" strong>{fmtQty(r.shortage, r.unit_code)}</Typography.Text> : '—',
          },
        ]} />
    </Card>
  )
}

function Consumptions({ task }: { task: ProductionTask }) {
  const query = useQuery({
    queryKey: [URL, String(task.id), 'consumptions'],
    queryFn: async () => (await api.get<TaskConsumption[]>(`${URL}${task.id}/consumptions/`)).data,
  })
  return (
    <Card size="small" title="Списанное сырьё (по партиям, FEFO)">
      <Table<TaskConsumption> rowKey="id" size="small" pagination={false} loading={query.isLoading} dataSource={query.data}
        columns={[
          { title: 'Сырьё', dataIndex: 'item_name' },
          { title: 'Партия', render: (_, c) => <Link to={`/trace/${c.lot}`}>{c.lot_number}</Link> },
          { title: 'Поставщик', dataIndex: 'supplier_name', render: (v) => v ?? '—' },
          { title: 'Годен до', dataIndex: 'expiry_date', render: fmtDate },
          { title: 'Количество', align: 'right', render: (_, c) => fmtQty(c.quantity, c.unit_code) },
          { title: 'Сумма', align: 'right', render: (_, c) => fmtMoney(Number(c.quantity) * Number(c.unit_cost)) },
        ]} />
    </Card>
  )
}

function Allocations({ task }: { task: ProductionTask }) {
  return (
    <Card size="small" title="Для заказов клиентов">
      <Table<TaskAllocation> rowKey="id" size="small" pagination={false} dataSource={task.allocations} columns={[
        { title: 'Заказ', render: (_, a) => <Link to={`/orders/${a.order}`}>{a.order_number}</Link> },
        { title: 'Клиент', dataIndex: 'client_name' },
        { title: 'Отгрузка', dataIndex: 'delivery_date', render: fmtDate },
        { title: 'Распределено', align: 'right', render: (_, a) => fmtQty(a.quantity, task.unit_code) },
        { title: 'Выпущено для заказа', align: 'right', render: (_, a) => (task.status === 'done' ? fmtQty(a.fulfilled, task.unit_code) : '—') },
        { title: 'Статус заказа', dataIndex: 'order_status', render: (s: string) => <StatusTag map={SALES_ORDER_STATUS} value={s} /> },
      ]} />
    </Card>
  )
}

function FinishModal({ task, open, onClose }: { task: ProductionTask; open: boolean; onClose: () => void }) {
  const [form] = Form.useForm()
  const finish = useApiAction((v: object) => api.post(`${URL}${task.id}/finish/`, v), {
    success: 'Задание завершено, партия продукции на складе', invalidate: 'all', onSuccess: onClose,
  })
  return (
    <Modal title={`Завершение ${task.number}`} open={open} onCancel={onClose} onOk={() => form.submit()}
      okText="Завершить" okButtonProps={{ loading: finish.isPending }} destroyOnHidden>
      <Typography.Paragraph type="secondary">
        Годная продукция поступит на склад и распределится по заказам — сначала с ближайшей отгрузкой.
        Если выпущено меньше плана, недостающее снова попадёт в потребность.
      </Typography.Paragraph>
      <Form form={form} layout="vertical" preserve={false} initialValues={{ actual_qty: task.planned_qty, defect_qty: '0' }}
        onFinish={(v) => finish.mutate(v)}>
        <Form.Item name="actual_qty" label="Выпущено годной продукции" rules={[{ required: true }]}>
          <InputNumber min="0" stringMode suffix={task.unit_code} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="defect_qty" label="Брак">
          <InputNumber min="0" stringMode suffix={task.unit_code} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="comment" label="Комментарий"><Input.TextArea rows={2} /></Form.Item>
      </Form>
    </Modal>
  )
}
