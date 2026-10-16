import { PlusOutlined } from '@ant-design/icons'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { App, Button, Form, Input, Modal, Popconfirm, Table, type TableColumnsType } from 'antd'
import { useState, type ReactNode } from 'react'
import { api } from '../api/client'
import { errorText, fieldErrors, useList } from '../api/hooks'

interface Props<T extends { id: number }> {
  url: string
  /** Название сущности для заголовка формы, например «Сотрудник» */
  entity: string
  columns: TableColumnsType<T>
  form: ReactNode
  canEdit: boolean
  params?: Record<string, unknown>
  toolbar?: ReactNode
  searchPlaceholder?: string
  initialValues?: object
  toForm?: (row: T) => object
  fromForm?: (values: Record<string, unknown>) => object
}

/** Таблица с поиском и модальной формой создания/редактирования для простых справочников. */
export default function CrudPage<T extends { id: number }>(props: Props<T>) {
  const { url, entity, canEdit, toForm, fromForm } = props
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [form] = Form.useForm()
  const [search, setSearch] = useState('')
  // undefined — форма закрыта, null — новая запись
  const [editing, setEditing] = useState<T | null | undefined>(undefined)

  const rows = useList<T>(url, { ...props.params, search })

  const onDone = (text: string) => {
    message.success(text)
    qc.invalidateQueries({ queryKey: [url] })
    setEditing(undefined)
  }
  const onError = (e: unknown) => {
    const fields = fieldErrors(e)
    form.setFields(fields)
    message.error(fields.length ? 'Проверьте выделенные поля' : errorText(e))
  }

  const save = useMutation({
    mutationFn: (values: object) => (editing ? api.patch(`${url}${editing.id}/`, values) : api.post(url, values)),
    onSuccess: () => onDone('Сохранено'),
    onError,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`${url}${id}/`),
    onSuccess: () => onDone('Удалено'),
    onError,
  })

  const initial = editing ? (toForm?.(editing) ?? editing) : props.initialValues

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Input.Search placeholder={props.searchPlaceholder ?? 'Поиск'} allowClear onSearch={setSearch} style={{ maxWidth: 320 }} />
        {props.toolbar}
        {canEdit && <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing(null)}>Добавить</Button>}
      </div>
      <Table<T>
        rowKey="id"
        size="middle"
        loading={rows.isLoading}
        dataSource={rows.data}
        columns={props.columns}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        onRow={(row) => ({ onClick: canEdit ? () => setEditing(row) : undefined, style: canEdit ? { cursor: 'pointer' } : undefined })}
      />
      <Modal
        title={`${entity}: ${editing ? 'редактирование' : 'новая запись'}`}
        open={editing !== undefined}
        onCancel={() => setEditing(undefined)}
        destroyOnHidden
        footer={[
          editing && (
            <Popconfirm key="del" title="Удалить запись?" onConfirm={() => remove.mutate(editing.id)}>
              <Button danger loading={remove.isPending} style={{ float: 'left' }}>Удалить</Button>
            </Popconfirm>
          ),
          <Button key="cancel" onClick={() => setEditing(undefined)}>Отмена</Button>,
          <Button key="ok" type="primary" loading={save.isPending} onClick={() => form.submit()}>Сохранить</Button>,
        ]}
      >
        <Form form={form} layout="vertical" preserve={false} initialValues={initial} onFinish={(v) => save.mutate(fromForm ? fromForm(v) : v)}>
          {props.form}
        </Form>
      </Modal>
    </>
  )
}
