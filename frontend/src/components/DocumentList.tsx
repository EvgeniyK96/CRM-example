import { PlusOutlined, ProjectOutlined, UnorderedListOutlined } from '@ant-design/icons'
import { Button, Form, Modal, Segmented, Spin, Table, type TableColumnsType } from 'antd'
import { useMemo, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useApiAction, useList } from '../api/hooks'
import { statusOptions, type StatusInfo } from '../api/statuses'
import FilterBar from './FilterBar'
import { filterParams, type FilterField, type FilterPreset, type FilterValues } from './filters'

type View = 'list' | 'board'

interface Props<T extends { id: number }> {
  /** API-эндпоинт списка, например '/purchasing/orders/' */
  url: string
  /** Маршрут карточки во фронтенде, например '/purchase-orders' */
  path: string
  statuses: Record<string, StatusInfo>
  columns: TableColumnsType<T>
  /** Постоянные параметры запроса (не видны в фильтре) */
  params?: Record<string, unknown>
  /** Поля фильтра страницы; «Статус» добавляется автоматически */
  filterFields?: FilterField[]
  presets?: FilterPreset[]
  /** Фильтр при открытии страницы (например, свой цех у начальника цеха) */
  defaultFilter?: FilterValues
  searchPlaceholder?: string
  canCreate: boolean
  createTitle: string
  createForm: ReactNode
  createInitial?: object
  fromForm?: (values: Record<string, unknown>) => object
  /** Канбан по статусам: если задан, появляется переключатель «Список / Канбан» */
  board?: (rows: T[]) => ReactNode
}

const viewKey = (path: string) => `view:${path}`

function readView(path: string): View {
  try {
    return localStorage.getItem(viewKey(path)) === 'board' ? 'board' : 'list'
  } catch {
    return 'list'
  }
}

/** Список документов с фильтром по статусу (или канбан); создание черновика открывает его карточку. */
export default function DocumentList<T extends { id: number }>(props: Props<T>) {
  const navigate = useNavigate()
  const [query] = useSearchParams()
  const [search, setSearch] = useState(query.get('q') ?? '')
  const [filter, setFilter] = useState<FilterValues>(props.defaultFilter ?? {})
  const [open, setOpen] = useState(false)
  const [view, setView] = useState<View>(() => (props.board ? readView(props.path) : 'list'))
  const board = view === 'board' && props.board
  // На канбане статусы — это колонки, фильтр по статусу не нужен
  const { statuses, filterFields } = props
  const fields = useMemo<FilterField[]>(() => [
    ...(board ? [] : [{ key: 'status', label: 'Статус', type: 'select' as const, multiple: true, options: statusOptions(statuses) }]),
    ...(filterFields ?? []),
  ], [board, statuses, filterFields])
  const rows = useList<T>(props.url, { search, ...filterParams(fields, filter), ...props.params })

  const create = useApiAction(async (v: object) => (await api.post<T>(props.url, v)).data, {
    invalidate: [props.url],
    onSuccess: (doc) => navigate(`${props.path}/${doc.id}`),
  })

  const changeView = (v: View) => {
    setView(v)
    try {
      localStorage.setItem(viewKey(props.path), v)
    } catch {
      // выбор не запомнится — не страшно
    }
  }

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        {props.board && (
          <Segmented<View> value={view} onChange={changeView} options={[
            { value: 'list', label: 'Список', icon: <UnorderedListOutlined /> },
            { value: 'board', label: 'Канбан', icon: <ProjectOutlined /> },
          ]} />
        )}
        <FilterBar fields={fields} presets={props.presets} value={filter} onChange={setFilter}
          search={search} onSearch={setSearch} searchPlaceholder={props.searchPlaceholder} storageKey={`filters:${props.path}`} />
        {props.canCreate && <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Создать</Button>}
      </div>
      {board ? (
        <Spin spinning={rows.isFetching}>{board(rows.data ?? [])}</Spin>
      ) : (
        <Table<T>
          rowKey="id"
          size="middle"
          loading={rows.isLoading}
          dataSource={rows.data}
          columns={props.columns}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          onRow={(doc) => ({ onClick: () => navigate(`${props.path}/${doc.id}`), style: { cursor: 'pointer' } })}
        />
      )}
      <Modal title={props.createTitle} open={open} onCancel={() => setOpen(false)} destroyOnHidden footer={null}>
        <Form layout="vertical" initialValues={props.createInitial} onFinish={(v) => create.mutate(props.fromForm ? props.fromForm(v) : v)}>
          {props.createForm}
          <Button type="primary" htmlType="submit" block loading={create.isPending}>Создать черновик</Button>
        </Form>
      </Modal>
    </>
  )
}
