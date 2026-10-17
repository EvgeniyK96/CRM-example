import { Alert, Form, Input, InputNumber, Select, Switch, Tag } from 'antd'
import type { PayrollRate } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import CrudPage from '../components/CrudPage'

export default function PayrollRates() {
  const { can } = useAuth()
  return (
    <>
      <Alert type="info" showIcon style={{ marginBottom: 16 }}
        title="Учебные упрощённые ставки по образцу РК. Изменения применяются при следующем расчёте (пересчёте) ведомости." />
      <CrudPage<PayrollRate>
        url="/payroll/rates/"
        entity="Ставка"
        canEdit={can('accountant')}
        initialValues={{ payer: 'employer', base: 'gross', is_active: true }}
        columns={[
          { title: 'Код', dataIndex: 'code', width: 90 },
          { title: 'Название', dataIndex: 'name' },
          { title: 'Кто платит', dataIndex: 'payer', render: (p: string) => (p === 'employee' ? <Tag color="orange">Удержание</Tag> : <Tag color="blue">Работодатель</Tag>) },
          { title: 'База', dataIndex: 'base_display' },
          { title: 'Ставка', dataIndex: 'percent', align: 'right', render: (v: string) => `${Number(v)}%` },
          { title: 'Счёт', dataIndex: 'account_code' },
          { title: 'Статус', dataIndex: 'is_active', render: (a: boolean) => (a ? <Tag color="green">Применяется</Tag> : <Tag>Отключена</Tag>) },
        ]}
        form={
          <>
            <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="payer" label="Кто платит" rules={[{ required: true }]}>
              <Select options={[{ value: 'employee', label: 'Удерживается из зарплаты' }, { value: 'employer', label: 'Платит работодатель' }]} />
            </Form.Item>
            <Form.Item name="base" label="База" rules={[{ required: true }]}>
              <Select options={[{ value: 'gross', label: 'От начисленной суммы' }, { value: 'taxable', label: 'От облагаемого дохода' }]} />
            </Form.Item>
            <Form.Item name="percent" label="Ставка, %" rules={[{ required: true }]}><InputNumber min="0" max="100" stringMode style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="account_code" label="Счёт обязательства" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="is_active" label="Применяется" valuePropName="checked"><Switch /></Form.Item>
          </>
        }
      />
    </>
  )
}
