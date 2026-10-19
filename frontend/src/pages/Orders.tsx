import { DatePicker, Form, Input, Select } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { toOptions, useList } from '../api/hooks'
import { CLIENT_KIND, SALES_ORDER_STATUS, statusOptions } from '../api/statuses'
import type { Client, SalesOrder } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import OrdersBoard from '../components/boards/OrdersBoard'
import DocumentList from '../components/DocumentList'
import type { FilterField, FilterPreset } from '../components/filters'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

const OPEN = ['new', 'confirmed', 'in_production', 'ready']

export default function Orders() {
  const { can } = useAuth()
  const clients = useList<Client>('/sales/clients/', { is_active: true })
  const clientOptions = toOptions(clients.data, (c) => c.name)

  const fields: FilterField[] = [
    { key: 'client', label: 'Клиент', type: 'select', options: clientOptions },
    { key: 'client_kind', label: 'Тип клиента', type: 'select', options: statusOptions(CLIENT_KIND) },
    { key: 'delivery', label: 'Дата отгрузки', type: 'dateRange', params: ['delivery_from', 'delivery_to'] },
    ...(can('sales') ? [{ key: 'mine', label: 'Только мои', type: 'switch' as const }] : []),
  ]
  const presets: FilterPreset[] = [
    ...(can('sales') ? [{ key: 'mine', label: 'Мои заказы', values: () => ({ mine: true }) }] : []),
    { key: 'open', label: 'В работе', values: () => ({ status: OPEN }) },
    { key: 'today', label: 'Отгрузка сегодня', values: () => ({ delivery: [dayjs(), dayjs()] }) },
    { key: 'overdue', label: 'Просроченные', values: () => ({ status: OPEN, delivery: [null, dayjs().subtract(1, 'day')] }) },
    {
      key: 'shipped-month', label: 'Отгружены в этом месяце',
      values: () => ({ status: ['shipped'], delivery: [dayjs().startOf('month'), dayjs().endOf('month')] }),
    },
  ]

  return (
    <DocumentList<SalesOrder>
      url="/sales/orders/"
      path="/orders"
      statuses={SALES_ORDER_STATUS}
      filterFields={fields}
      presets={presets}
      searchPlaceholder="Фильтр + поиск: номер, клиент"
      board={(rows) => <OrdersBoard rows={rows} />}
      canCreate={can('sales')}
      createTitle="Новый заказ"
      createInitial={{ delivery_date: dayjs().add(1, 'day') }}
      fromForm={(v) => ({ ...v, delivery_date: toApiDate(v.delivery_date as Dayjs) })}
      createForm={
        <>
          <Form.Item name="client" label="Клиент" rules={[{ required: true }]}>
            <Select showSearch={{ optionFilterProp: 'label' }} options={clientOptions} />
          </Form.Item>
          <Form.Item name="delivery_date" label="Дата отгрузки" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} disabledDate={(d) => d.isBefore(dayjs(), 'day')} />
          </Form.Item>
          <Form.Item name="comment" label="Комментарий"><Input /></Form.Item>
        </>
      }
      columns={[
        { title: 'Номер', dataIndex: 'number', width: 110 },
        { title: 'Клиент', dataIndex: 'client_name' },
        { title: 'Тип', dataIndex: 'client_kind', render: (k: string) => <StatusTag map={CLIENT_KIND} value={k} /> },
        { title: 'Отгрузка', dataIndex: 'delivery_date', render: fmtDate },
        { title: 'Сумма', dataIndex: 'total', align: 'right', render: fmtMoney },
        { title: 'Менеджер', dataIndex: 'created_by_name', render: (v) => v ?? '—' },
        { title: 'Статус', dataIndex: 'status', render: (s: string) => <StatusTag map={SALES_ORDER_STATUS} value={s} /> },
      ]}
    />
  )
}
