import { PlusOutlined } from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import { App, Button, Form, Input, InputNumber, Modal, Select, Table, Tag } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { errorText, toOptions, useList } from '../api/hooks'
import type { Department, Item, Recipe, RecipeStatus } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { RECIPE_STATUS } from './recipeStatus'

export default function Recipes() {
  const { can } = useAuth()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<RecipeStatus | undefined>('active')
  const [department, setDepartment] = useState<number>()
  const [open, setOpen] = useState(false)

  const recipes = useList<Recipe>('/recipes/', { search, status, product__department: department })
  const departments = useList<Department>('/hr/departments/', { is_production: true })
  const products = useList<Item>('/catalog/items/', { kind: 'product', is_active: true }, open)

  const create = useMutation({
    mutationFn: async (v: object) => (await api.post<Recipe>('/recipes/', v)).data,
    onSuccess: (r) => navigate(`/recipes/${r.id}`),
    onError: (e) => message.error(errorText(e)),
  })

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Input.Search placeholder="Продукт или артикул" allowClear onSearch={setSearch} style={{ maxWidth: 280 }} />
        <Select
          allowClear placeholder="Статус" style={{ width: 160 }} value={status} onChange={setStatus}
          options={Object.entries(RECIPE_STATUS).map(([value, s]) => ({ value, label: s.label }))}
        />
        <Select
          allowClear placeholder="Цех" style={{ width: 240 }} value={department} onChange={setDepartment}
          options={toOptions(departments.data, (d) => d.name)}
        />
        {can('technologist') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Новая рецептура</Button>}
      </div>
      <Table<Recipe>
        rowKey="id"
        size="middle"
        loading={recipes.isLoading}
        dataSource={recipes.data}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        onRow={(r) => ({ onClick: () => navigate(`/recipes/${r.id}`), style: { cursor: 'pointer' } })}
        columns={[
          { title: 'Продукт', dataIndex: 'product_name' },
          { title: 'Цех', dataIndex: 'department_name' },
          { title: 'Версия', dataIndex: 'version', width: 90, align: 'center' },
          { title: 'Выход партии', render: (_, r) => `${Number(r.output_qty)} ${r.product_unit}`, align: 'right' },
          { title: 'Строк', render: (_, r) => r.lines.length, width: 80, align: 'center' },
          { title: 'Статус', dataIndex: 'status', render: (s: RecipeStatus) => <Tag color={RECIPE_STATUS[s].color}>{RECIPE_STATUS[s].label}</Tag> },
        ]}
      />
      <Modal title="Новая рецептура" open={open} onCancel={() => setOpen(false)} destroyOnHidden footer={null}>
        <Form layout="vertical" onFinish={(v) => create.mutate(v)} initialValues={{ output_qty: '100' }}>
          <Form.Item name="product" label="Продукт" rules={[{ required: true }]}>
            <Select showSearch={{ optionFilterProp: 'label' }} options={toOptions(products.data, (p) => `${p.code} · ${p.name}`)} />
          </Form.Item>
          <Form.Item name="output_qty" label="Выход партии" rules={[{ required: true }]}>
            <InputNumber min="0.001" stringMode style={{ width: '100%' }} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={create.isPending}>Создать черновик</Button>
        </Form>
      </Modal>
    </>
  )
}
