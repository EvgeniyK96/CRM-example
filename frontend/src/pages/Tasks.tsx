import { useQuery } from '@tanstack/react-query'
import { Button, Card, DatePicker, Form, Input, InputNumber, Select, Table, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { toOptions, useApiAction, useList } from '../api/hooks'
import { TASK_STATUS } from '../api/statuses'
import type { DemandGroup, Department, Item, ProductionTask } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import DocumentList from '../components/DocumentList'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtQty, toApiDate } from '../utils/format'

const DEMAND = '/production/demand/'

/** Непокрытая потребность из подтверждённых заказов + кнопка «Сформировать задания». */
function DemandCard() {
  const navigate = useNavigate()
  const demand = useQuery({ queryKey: [DEMAND], queryFn: async () => (await api.get<DemandGroup[]>(DEMAND)).data })
  const plan = useApiAction(async () => (await api.post<ProductionTask[]>(DEMAND)).data, {
    success: (tasks) => `Создано заданий: ${tasks.length}`,
    invalidate: 'all',
    onSuccess: (tasks) => tasks.length === 1 && navigate(`/tasks/${tasks[0].id}`),
  })

  if (!demand.data?.length) return null
  return (
    <Card
      size="small"
      style={{ marginBottom: 16 }}
      title="Потребность из заказов, ещё не поставленная в задания"
      extra={<Button type="primary" loading={plan.isPending} onClick={() => plan.mutate()}>Сформировать задания</Button>}
    >
      <Table<DemandGroup> rowKey="product" size="small" pagination={false} dataSource={demand.data} columns={[
        { title: 'Продукт', dataIndex: 'product_name' },
        { title: 'Цех', dataIndex: 'department_name' },
        { title: 'Нужно произвести', align: 'right', render: (_, g) => <b>{fmtQty(g.quantity, g.unit_code)}</b> },
        { title: 'Ближайшая отгрузка', dataIndex: 'earliest_date', render: fmtDate },
        {
          title: 'Заказы',
          render: (_, g) => g.orders.map((o) => (
            <div key={o.order}>
              <Link to={`/orders/${o.order}`}>{o.order_number}</Link>{' '}
              <Typography.Text type="secondary">{o.client_name}, {fmtQty(o.quantity, g.unit_code)}</Typography.Text>
            </div>
          )),
        },
      ]} />
    </Card>
  )
}

export default function Tasks() {
  const { user, can } = useAuth()
  // Начальник цеха по умолчанию видит свой цех
  const [department, setDepartment] = useState<number | undefined>(user?.production_department ?? undefined)
  const departments = useList<Department>('/hr/departments/', { is_production: true })
  const products = useList<Item>('/catalog/items/', { kind: 'product', is_active: true })
  const ownProducts = products.data?.filter(
    (p) => !user?.production_department || user.role !== 'shop_head' || p.department === user.production_department,
  )

  return (
    <>
      {can('shop_head') && <DemandCard />}
      <DocumentList<ProductionTask>
        url="/production/tasks/"
        path="/tasks"
        statuses={TASK_STATUS}
        params={{ department }}
        searchPlaceholder="Номер, продукт"
        filters={
          <Select allowClear placeholder="Цех" style={{ width: 240 }} value={department} onChange={setDepartment}
            options={toOptions(departments.data, (d) => d.name)} />
        }
        canCreate={can('shop_head')}
        createTitle="Задание вне заказов (например, на запас)"
        createInitial={{ planned_date: dayjs() }}
        fromForm={(v) => ({ ...v, planned_date: toApiDate(v.planned_date as Dayjs) })}
        createForm={
          <>
            <Form.Item name="product" label="Продукт" rules={[{ required: true }]}>
              <Select showSearch={{ optionFilterProp: 'label' }}
                options={toOptions(ownProducts, (p) => `${p.name} — ${p.department_name}`)} />
            </Form.Item>
            <Form.Item name="planned_qty" label="Количество" rules={[{ required: true }]}>
              <InputNumber min="0.001" stringMode style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="planned_date" label="Плановая дата" rules={[{ required: true }]}>
              <DatePicker style={{ width: '100%' }} disabledDate={(d) => d.isBefore(dayjs(), 'day')} />
            </Form.Item>
            <Form.Item name="comment" label="Комментарий"><Input /></Form.Item>
          </>
        }
        columns={[
          { title: 'Номер', dataIndex: 'number', width: 110 },
          { title: 'Дата', dataIndex: 'planned_date', render: fmtDate, width: 110 },
          { title: 'Цех', dataIndex: 'department_name' },
          { title: 'Продукт', dataIndex: 'product_name' },
          { title: 'План', align: 'right', render: (_, t) => fmtQty(t.planned_qty, t.unit_code) },
          {
            title: 'Выпущено / брак', align: 'right',
            render: (_, t) => (t.actual_qty == null ? '—' : `${fmtQty(t.actual_qty)} / ${fmtQty(t.defect_qty)}`),
          },
          { title: 'Заказов', align: 'center', render: (_, t) => t.allocations.length || '—' },
          { title: 'Статус', dataIndex: 'status', render: (s: string) => <StatusTag map={TASK_STATUS} value={s} /> },
        ]}
      />
    </>
  )
}
