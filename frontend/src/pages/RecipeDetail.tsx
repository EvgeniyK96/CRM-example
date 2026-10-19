import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  App, Button, Card, Descriptions, Form, Input, InputNumber, Popconfirm, Select, Space, Table, Tag, Typography,
} from 'antd'
import dayjs from 'dayjs'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { errorText, toOptions, useApiAction, useList } from '../api/hooks'
import type { Item, Recipe, RecipeCalculation, RecipeLine } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { RECIPE_STATUS } from '../api/statuses'
import LinesFormList, { type LineColumn } from '../components/LinesFormList'

const fmt = (d: string | null) => (d ? dayjs(d).format('DD.MM.YYYY HH:mm') : '—')

function useRecipeAction(id: string | undefined, name: 'activate' | 'copy') {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => (await api.post<Recipe>(`/recipes/${id}/${name}/`)).data,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['/recipes/'] })
      message.success(name === 'activate' ? 'Рецептура введена в действие' : `Создан черновик версии ${r.version}`)
      if (name === 'copy') navigate(`/recipes/${r.id}`)
    },
    onError: (e) => message.error(errorText(e)),
  })
}

export default function RecipeDetail() {
  const { id } = useParams()
  const { can } = useAuth()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: recipe, isLoading } = useQuery({
    queryKey: ['/recipes/', id],
    queryFn: async () => (await api.get<Recipe>(`/recipes/${id}/`)).data,
  })
  const versions = useList<Recipe>('/recipes/', { product: recipe?.product, ordering: '-version' }, !!recipe)

  const refresh = () => qc.invalidateQueries({ queryKey: ['/recipes/'] })
  const activate = useRecipeAction(id, 'activate')
  const copy = useRecipeAction(id, 'copy')
  const remove = useMutation({
    mutationFn: () => api.delete(`/recipes/${id}/`),
    onSuccess: () => {
      refresh()
      navigate('/recipes')
    },
    onError: (e) => message.error(errorText(e)),
  })

  if (isLoading || !recipe) return <Card loading />

  const isTech = can('technologist')
  const editable = recipe.status === 'draft' && isTech
  const status = RECIPE_STATUS[recipe.status]

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Card
        title={<>{recipe.product_name} · версия {recipe.version} <Tag color={status.color} style={{ marginLeft: 8 }}>{status.label}</Tag></>}
        extra={
          isTech && (
            <Space>
              {recipe.status === 'draft' && (
                <>
                  <Popconfirm title="Удалить черновик?" onConfirm={() => remove.mutate()}>
                    <Button danger>Удалить</Button>
                  </Popconfirm>
                  <Popconfirm title="Ввести в действие? Текущая активная версия уйдёт в архив." onConfirm={() => activate.mutate()}>
                    <Button type="primary" loading={activate.isPending}>Активировать</Button>
                  </Popconfirm>
                </>
              )}
              <Button onClick={() => copy.mutate()} loading={copy.isPending}>Новая версия на основе этой</Button>
            </Space>
          )
        }
      >
        <Descriptions
          size="small"
          column={{ xs: 1, md: 3 }}
          items={[
            { label: 'Цех', children: recipe.department_name },
            { label: 'Автор', children: recipe.created_by_name ?? '—' },
            { label: 'Создана', children: fmt(recipe.created_at) },
            { label: 'Выход партии', children: `${Number(recipe.output_qty)} ${recipe.product_unit}` },
            { label: 'Введена в действие', children: fmt(recipe.activated_at) },
          ]}
        />
      </Card>

      {editable ? <RecipeEditor recipe={recipe} onSaved={refresh} /> : <RecipeView recipe={recipe} />}

      <Calculator recipe={recipe} />

      <Card title="Версии рецептуры" size="small">
        <Table<Recipe>
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={versions.data}
          onRow={(r) => ({ onClick: () => navigate(`/recipes/${r.id}`), style: { cursor: 'pointer', fontWeight: r.id === recipe.id ? 600 : undefined } })}
          columns={[
            { title: 'Версия', dataIndex: 'version', width: 90 },
            { title: 'Статус', dataIndex: 'status', render: (s: Recipe['status']) => <Tag color={RECIPE_STATUS[s].color}>{RECIPE_STATUS[s].label}</Tag> },
            { title: 'Создана', dataIndex: 'created_at', render: fmt },
            { title: 'Введена в действие', dataIndex: 'activated_at', render: fmt },
          ]}
        />
      </Card>
    </Space>
  )
}

const lineColumns = [
  { title: 'Сырьё', dataIndex: 'ingredient_name' },
  { title: 'Нетто', render: (_: unknown, l: RecipeLine) => `${Number(l.quantity)} ${l.unit_code}`, align: 'right' as const },
  { title: 'Потери, %', dataIndex: 'loss_percent', render: (v: string) => Number(v), align: 'right' as const },
]

function RecipeView({ recipe }: { recipe: Recipe }) {
  return (
    <Card title="Состав" size="small">
      <Table rowKey="id" size="small" pagination={false} dataSource={recipe.lines} columns={lineColumns} />
      {recipe.note && <Typography.Paragraph style={{ marginTop: 16, whiteSpace: 'pre-wrap' }}>{recipe.note}</Typography.Paragraph>}
    </Card>
  )
}

function RecipeEditor({ recipe, onSaved }: { recipe: Recipe; onSaved: () => void }) {
  const [form] = Form.useForm()
  const raw = useList<Item>('/catalog/items/', { kind: 'raw', is_active: true })
  const unitOf = (ingredient?: number) => raw.data?.find((i) => i.id === ingredient)?.unit_code
  const save = useApiAction((v: object) => api.patch(`/recipes/${recipe.id}/`, v), { success: 'Черновик сохранён', onSuccess: onSaved })

  const columns: LineColumn[] = [
    {
      title: 'Сырьё',
      width: 'minmax(220px, 3fr)',
      render: (i) => (
        <Form.Item name={[i, 'ingredient']} rules={[{ required: true, message: 'Выберите сырьё' }]}>
          <Select showSearch={{ optionFilterProp: 'label' }} placeholder="Сырьё" options={toOptions(raw.data, (item) => item.name)} />
        </Form.Item>
      ),
    },
    {
      title: 'Нетто',
      width: 'minmax(150px, 1fr)',
      render: (i) => (
        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => (
            <Form.Item name={[i, 'quantity']} rules={[{ required: true, message: 'Укажите' }]}>
              <InputNumber min="0.001" stringMode suffix={unitOf(getFieldValue(['lines', i, 'ingredient']))} style={{ width: '100%' }} />
            </Form.Item>
          )}
        </Form.Item>
      ),
    },
    {
      title: 'Потери',
      width: 'minmax(110px, 1fr)',
      render: (i) => (
        <Form.Item name={[i, 'loss_percent']}>
          <InputNumber min="0" max="99.99" stringMode suffix="%" style={{ width: '100%' }} />
        </Form.Item>
      ),
    },
  ]

  return (
    <Card title="Состав (черновик)" size="small" extra={<Button type="primary" loading={save.isPending} onClick={() => form.submit()}>Сохранить</Button>}>
      <Form
        form={form}
        layout="vertical"
        initialValues={{ output_qty: recipe.output_qty, note: recipe.note, lines: recipe.lines }}
        onFinish={(v) => save.mutate(v)}
      >
        <Form.Item name="output_qty" label={`Выход партии, ${recipe.product_unit}`} rules={[{ required: true }]} style={{ maxWidth: 240 }}>
          <InputNumber min="0.001" stringMode style={{ width: '100%' }} />
        </Form.Item>
        <LinesFormList columns={columns} newLine={{ loss_percent: '0' }} addLabel="Добавить сырьё" />
        <Form.Item name="note" label="Технологические указания"><Input.TextArea rows={3} /></Form.Item>
      </Form>
    </Card>
  )
}

function Calculator({ recipe }: { recipe: Recipe }) {
  const [qty, setQty] = useState<string | null>(recipe.output_qty)
  const calc = useQuery({
    queryKey: ['/recipes/', recipe.id, 'calculate', qty, recipe.lines],
    queryFn: async () => (await api.get<RecipeCalculation>(`/recipes/${recipe.id}/calculate/`, { params: { qty } })).data,
    enabled: !!qty && Number(qty) > 0 && recipe.lines.length > 0,
  })

  return (
    <Card
      title="Потребность в сырье"
      size="small"
      extra={
        <Space>
          Выпуск:
          <InputNumber min="0.001" stringMode value={qty} onChange={setQty} suffix={recipe.product_unit} style={{ width: 160 }} />
        </Space>
      }
    >
      <Table
        rowKey="ingredient"
        size="small"
        pagination={false}
        loading={calc.isFetching}
        dataSource={calc.data?.lines}
        locale={{ emptyText: recipe.lines.length ? 'Укажите объём выпуска' : 'В рецептуре нет строк' }}
        columns={[
          { title: 'Сырьё', dataIndex: 'ingredient_name' },
          { title: 'Брутто (с учётом потерь)', render: (_, l) => `${Number(l.quantity)} ${l.unit_code}`, align: 'right' },
        ]}
      />
    </Card>
  )
}
