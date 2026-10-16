import { Form, Input, InputNumber, Segmented, Select, Switch, Tag, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { toOptions, useList } from '../api/hooks'
import type { Category, Department, Item, ItemKind, Unit } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import CrudPage from '../components/CrudPage'

export default function Items() {
  const { can } = useAuth()
  const [kind, setKind] = useState<ItemKind>('product')
  const isProduct = kind === 'product'

  const units = useList<Unit>('/catalog/units/')
  const categories = useList<Category>('/catalog/categories/', { kind })
  const departments = useList<Department>('/hr/departments/', { is_production: true })

  const columns: TableColumnsType<Item> = [
    { title: 'Артикул', dataIndex: 'code', width: 110 },
    { title: 'Название', dataIndex: 'name' },
    { title: 'Категория', dataIndex: 'category_name' },
    { title: 'Ед.', dataIndex: 'unit_code', width: 70 },
    isProduct
      ? { title: 'Цех', dataIndex: 'department_name' }
      : { title: 'Мин. остаток', dataIndex: 'min_stock', align: 'right' },
    { title: 'Срок годности, дн.', dataIndex: 'shelf_life_days', align: 'right', width: 150 },
    ...(isProduct ? [{ title: 'Цена', dataIndex: 'sale_price', align: 'right' as const }] : []),
    { title: 'Статус', dataIndex: 'is_active', width: 100, render: (a: boolean) => (a ? <Tag color="green">Активна</Tag> : <Tag>Скрыта</Tag>) },
  ]

  return (
    <CrudPage<Item>
      key={kind}
      url="/catalog/items/"
      entity={isProduct ? 'Продукция' : 'Сырьё'}
      params={{ kind }}
      canEdit={can('technologist')}
      searchPlaceholder="Поиск по артикулу или названию"
      toolbar={
        <Segmented<ItemKind>
          value={kind}
          onChange={setKind}
          options={[{ value: 'product', label: 'Готовая продукция' }, { value: 'raw', label: 'Сырьё' }]}
        />
      }
      initialValues={{ kind, is_active: true, min_stock: '0', sale_price: '0' }}
      columns={columns}
      form={
        <>
          <Form.Item name="kind" hidden><Input /></Form.Item>
          <Form.Item name="code" label="Артикул" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="category" label="Категория"><Select allowClear options={toOptions(categories.data, (c) => c.name)} /></Form.Item>
          <Form.Item name="unit" label="Единица измерения" rules={[{ required: true }]}>
            <Select options={toOptions(units.data, (u) => `${u.code} — ${u.name}`)} />
          </Form.Item>
          {isProduct && (
            <Form.Item name="department" label="Цех-изготовитель" rules={[{ required: true }]}>
              <Select options={toOptions(departments.data, (d) => d.name)} />
            </Form.Item>
          )}
          <Form.Item name="shelf_life_days" label="Срок годности, дней" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          {isProduct ? (
            <Form.Item name="sale_price" label="Отпускная цена"><InputNumber min="0" stringMode style={{ width: '100%' }} /></Form.Item>
          ) : (
            <Form.Item name="min_stock" label="Минимальный остаток"><InputNumber min="0" stringMode style={{ width: '100%' }} /></Form.Item>
          )}
          <Form.Item name="is_active" label="Используется" valuePropName="checked"><Switch /></Form.Item>
        </>
      }
    />
  )
}
