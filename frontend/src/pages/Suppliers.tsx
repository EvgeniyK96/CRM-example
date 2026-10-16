import { Form, Input, Switch, Tag } from 'antd'
import type { Supplier } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import CrudPage from '../components/CrudPage'

export default function Suppliers() {
  const { can } = useAuth()
  return (
    <CrudPage<Supplier>
      url="/catalog/suppliers/"
      entity="Поставщик"
      canEdit={can('storekeeper', 'accountant')}
      searchPlaceholder="Название, БИН, контакт"
      initialValues={{ is_active: true }}
      columns={[
        { title: 'Название', dataIndex: 'name' },
        { title: 'БИН/ИНН', dataIndex: 'tax_id' },
        { title: 'Контактное лицо', dataIndex: 'contact_person' },
        { title: 'Телефон', dataIndex: 'phone' },
        { title: 'Что поставляет', dataIndex: 'note', ellipsis: true },
        { title: 'Статус', dataIndex: 'is_active', render: (a: boolean) => (a ? <Tag color="green">Активен</Tag> : <Tag>Неактивен</Tag>) },
      ]}
      form={
        <>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="tax_id" label="БИН/ИНН"><Input /></Form.Item>
          <Form.Item name="contact_person" label="Контактное лицо"><Input /></Form.Item>
          <Form.Item name="phone" label="Телефон"><Input /></Form.Item>
          <Form.Item name="email" label="Email" rules={[{ type: 'email' }]}><Input /></Form.Item>
          <Form.Item name="address" label="Адрес"><Input /></Form.Item>
          <Form.Item name="note" label="Примечание"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="is_active" label="Активен" valuePropName="checked"><Switch /></Form.Item>
        </>
      }
    />
  )
}
