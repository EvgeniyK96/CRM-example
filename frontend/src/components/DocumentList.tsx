import { PlusOutlined } from '@ant-design/icons'
import { Button, Form, Input, Modal, Select, Table, type TableColumnsType } from 'antd'
import { useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useApiAction, useList } from '../api/hooks'
import { statusOptions, type StatusInfo } from '../api/statuses'

interface Props<T extends { id: number }> {
  /** API-эндпоинт списка, например '/purchasing/orders/' */
  url: string
  /** Маршрут карточки во фронтенде, например '/purchase-orders' */
  path: string
  statuses: Record<string, StatusInfo>
  columns: TableColumnsType<T>
  params?: Record<string, unknown>
  filters?: ReactNode
  searchPlaceholder?: string
  canCreate: boolean
  createTitle: string
  createForm: ReactNode
  createInitial?: object
  fromForm?: (values: Record<string, unknown>) => object
}

/** Список документов с фильтром по статусу; создание черновика открывает его карточку. */
export default function DocumentList<T extends { id: number }>(props: Props<T>) {
  const navigate = useNavigate()
  const [query] = useSearchParams()
  const [search, setSearch] = useState(query.get('q') ?? '')
  const [status, setStatus] = useState<string>()
  const [open, setOpen] = useState(false)
  const rows = useList<T>(props.url, { search, status, ...props.params })

  const create = useApiAction(async (v: object) => (await api.post<T>(props.url, v)).data, {
    invalidate: [props.url],
    onSuccess: (doc) => navigate(`${props.path}/${doc.id}`),
  })

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Input.Search placeholder={props.searchPlaceholder ?? 'Номер'} allowClear onSearch={setSearch} defaultValue={search} style={{ maxWidth: 260 }} />
        <Select allowClear placeholder="Статус" style={{ width: 200 }} value={status} onChange={setStatus} options={statusOptions(props.statuses)} />
        {props.filters}
        {props.canCreate && <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Создать</Button>}
      </div>
      <Table<T>
        rowKey="id"
        size="middle"
        loading={rows.isLoading}
        dataSource={rows.data}
        columns={props.columns}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        onRow={(doc) => ({ onClick: () => navigate(`${props.path}/${doc.id}`), style: { cursor: 'pointer' } })}
      />
      <Modal title={props.createTitle} open={open} onCancel={() => setOpen(false)} destroyOnHidden footer={null}>
        <Form layout="vertical" initialValues={props.createInitial} onFinish={(v) => create.mutate(props.fromForm ? props.fromForm(v) : v)}>
          {props.createForm}
          <Button type="primary" htmlType="submit" block loading={create.isPending}>Создать черновик</Button>
        </Form>
      </Modal>
    </>
  )
}
