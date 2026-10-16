import { DatePicker, Form, Input, Select, Switch } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { toOptions, useList } from '../api/hooks'
import { CLIENT_KIND, SALES_ORDER_STATUS } from '../api/statuses'
import type { Client, SalesOrder } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import DocumentList from '../components/DocumentList'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

export default function Orders() {
  const { can } = useAuth()
  const [client, setClient] = useState<number>()
  const [mine, setMine] = useState(false)
  const clients = useList<Client>('/sales/clients/', { is_active: true })
  const clientOptions = toOptions(clients.data, (c) => c.name)

  return (
    <DocumentList<SalesOrder>
      url="/sales/orders/"
      path="/orders"
      statuses={SALES_ORDER_STATUS}
      params={{ client, mine: mine || undefined }}
      searchPlaceholder="Номер, клиент"
      filters={
        <>
          <Select allowClear showSearch={{ optionFilterProp: 'label' }} placeholder="Клиент" style={{ width: 260 }}
            value={client} onChange={setClient} options={clientOptions} />
          {can('sales') && <span style={{ alignSelf: 'center' }}><Switch checked={mine} onChange={setMine} /> Мои заказы</span>}
        </>
      }
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
