import { Form, Input, InputNumber, Segmented, Select, Switch, Tag } from 'antd'
import { useState } from 'react'
import { CLIENT_KIND } from '../api/statuses'
import type { Client, ClientKind } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import CrudPage from '../components/CrudPage'
import StatusTag from '../components/StatusTag'

const KIND_OPTIONS = [
  { value: 'wholesale', label: 'Оптовый покупатель' },
  { value: 'store', label: 'Магазин' },
  { value: 'brand_store', label: 'Фирменный магазин' },
]

export default function Clients() {
  const { can } = useAuth()
  const [kind, setKind] = useState<ClientKind | 'all'>('all')

  return (
    <CrudPage<Client>
      url="/sales/clients/"
      entity="Клиент"
      canEdit={can('sales')}
      params={{ kind: kind === 'all' ? undefined : kind }}
      searchPlaceholder="Название, БИН, контакт, телефон"
      toolbar={
        <Segmented<ClientKind | 'all'>
          value={kind}
          onChange={setKind}
          options={[{ value: 'all', label: 'Все' }, { value: 'wholesale', label: 'Опт' }, { value: 'store', label: 'Магазины' },
            { value: 'brand_store', label: 'Фирменные' }]}
        />
      }
      initialValues={{ kind: kind === 'all' ? 'store' : kind, discount_percent: '0', payment_delay_days: 0, is_active: true }}
      columns={[
        { title: 'Клиент', dataIndex: 'name' },
        { title: 'Тип', dataIndex: 'kind', render: (k: string) => <StatusTag map={CLIENT_KIND} value={k} /> },
        { title: 'Контакт', render: (_, c) => [c.contact_person, c.phone].filter(Boolean).join(', ') || '—' },
        { title: 'Скидка', dataIndex: 'discount_percent', align: 'right', render: (v: string) => (Number(v) ? `${Number(v)}%` : '—') },
        {
          title: 'Оплата', dataIndex: 'payment_delay_days',
          render: (d: number) => (d ? `отсрочка ${d} дн.` : 'предоплата'),
        },
        { title: 'Статус', dataIndex: 'is_active', render: (a: boolean) => (a ? <Tag color="green">Активен</Tag> : <Tag>Неактивен</Tag>) },
      ]}
      form={
        <>
          <Form.Item name="kind" label="Тип клиента" rules={[{ required: true }]}><Select options={KIND_OPTIONS} /></Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="tax_id" label="БИН/ИНН"><Input /></Form.Item>
          <Form.Item name="contact_person" label="Контактное лицо"><Input /></Form.Item>
          <Form.Item name="phone" label="Телефон"><Input /></Form.Item>
          <Form.Item name="email" label="Email" rules={[{ type: 'email' }]}><Input /></Form.Item>
          <Form.Item name="legal_address" label="Юридический адрес"><Input /></Form.Item>
          <Form.Item name="delivery_address" label="Адрес доставки"><Input /></Form.Item>
          <Form.Item name="discount_percent" label="Скидка, %"><InputNumber min="0" max="99.99" stringMode style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="payment_delay_days" label="Отсрочка платежа, дней" extra="0 — работа по предоплате">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="note" label="Примечание"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="is_active" label="Активен" valuePropName="checked"><Switch /></Form.Item>
        </>
      }
    />
  )
}
