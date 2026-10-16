import { Form, Input, InputNumber, Select, Switch, Tabs, Tag } from 'antd'
import type { Category, Department, Position, Unit } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import CrudPage from '../components/CrudPage'

const KIND_OPTIONS = [{ value: 'raw', label: 'Сырьё' }, { value: 'product', label: 'Готовая продукция' }]

export default function References() {
  const { can } = useAuth()
  const tech = can('technologist')
  const hr = can('hr')

  const tabs = [
    {
      key: 'units',
      label: 'Единицы измерения',
      children: (
        <CrudPage<Unit>
          url="/catalog/units/"
          entity="Единица измерения"
          canEdit={tech}
          columns={[{ title: 'Обозначение', dataIndex: 'code', width: 160 }, { title: 'Название', dataIndex: 'name' }]}
          form={
            <>
              <Form.Item name="code" label="Обозначение" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
            </>
          }
        />
      ),
    },
    {
      key: 'categories',
      label: 'Категории',
      children: (
        <CrudPage<Category>
          url="/catalog/categories/"
          entity="Категория"
          canEdit={tech}
          columns={[{ title: 'Название', dataIndex: 'name' }, { title: 'Тип', dataIndex: 'kind_display' }]}
          form={
            <>
              <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="kind" label="Тип номенклатуры" rules={[{ required: true }]}><Select options={KIND_OPTIONS} /></Form.Item>
            </>
          }
        />
      ),
    },
    {
      key: 'departments',
      label: 'Цеха и отделы',
      children: (
        <CrudPage<Department>
          url="/hr/departments/"
          entity="Подразделение"
          canEdit={hr}
          initialValues={{ is_production: false, is_active: true }}
          columns={[
            { title: 'Название', dataIndex: 'name' },
            { title: 'Тип', dataIndex: 'is_production', render: (p: boolean) => (p ? <Tag color="orange">Цех</Tag> : <Tag>Отдел</Tag>) },
            { title: 'Действует', dataIndex: 'is_active', render: (a: boolean) => (a ? 'Да' : 'Нет') },
          ]}
          form={
            <>
              <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="is_production" label="Производственный цех" valuePropName="checked"><Switch /></Form.Item>
              <Form.Item name="is_active" label="Действует" valuePropName="checked"><Switch /></Form.Item>
            </>
          }
        />
      ),
    },
    {
      key: 'positions',
      label: 'Должности',
      children: (
        <CrudPage<Position>
          url="/hr/positions/"
          entity="Должность"
          canEdit={hr}
          initialValues={{ base_salary: '0' }}
          columns={[{ title: 'Название', dataIndex: 'name' }, { title: 'Базовый оклад', dataIndex: 'base_salary', align: 'right' }]}
          form={
            <>
              <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="base_salary" label="Базовый оклад"><InputNumber min="0" stringMode style={{ width: '100%' }} /></Form.Item>
            </>
          }
        />
      ),
    },
  ]

  return <Tabs items={tabs} />
}
