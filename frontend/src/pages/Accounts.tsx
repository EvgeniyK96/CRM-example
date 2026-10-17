import { Form, Input, Select, Switch, Tag } from 'antd'
import type { Account } from '../api/types'
import CrudPage from '../components/CrudPage'

const TYPES = [
  { value: 'asset', label: 'Активы' }, { value: 'liability', label: 'Обязательства' }, { value: 'equity', label: 'Капитал' },
  { value: 'income', label: 'Доходы' }, { value: 'expense', label: 'Расходы' },
]

/** План счетов. Коды, на которые опираются автопроводки, удалить нельзя, пока по ним есть проводки. */
export default function Accounts() {
  return (
    <CrudPage<Account>
      url="/accounting/accounts/"
      entity="Счёт"
      canEdit
      searchPlaceholder="Код или название"
      initialValues={{ is_active: true, type: 'expense' }}
      columns={[
        { title: 'Код', dataIndex: 'code', width: 100 },
        { title: 'Название', dataIndex: 'name' },
        { title: 'Тип', dataIndex: 'type_display' },
        { title: 'Статус', dataIndex: 'is_active', render: (a: boolean) => (a ? <Tag color="green">Используется</Tag> : <Tag>Скрыт</Tag>) },
      ]}
      form={
        <>
          <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="type" label="Тип" rules={[{ required: true }]}><Select options={TYPES} /></Form.Item>
          <Form.Item name="is_active" label="Используется" valuePropName="checked"><Switch /></Form.Item>
        </>
      }
    />
  )
}
