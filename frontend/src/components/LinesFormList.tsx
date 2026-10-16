import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Form, Input, Typography } from 'antd'
import type { ReactNode } from 'react'

export interface LineColumn {
  title: string
  /** Ширина колонки в CSS-гриде, например '2fr' или '140px' */
  width: string
  /** Содержимое ячейки; name — индекс строки для Form.Item name={[name, 'field']} */
  render: (name: number) => ReactNode
}

/**
 * Редактируемые строки документа (Form.List) в виде таблицы.
 * hiddenFields — поля строки без своего контрола (например, связь со строкой заявки):
 * antd отдаёт в onFinish только зарегистрированные поля, поэтому их нужно объявить явно.
 */
export default function LinesFormList({ columns, newLine, addLabel = 'Добавить строку', name = 'lines', hiddenFields = [] }: {
  columns: LineColumn[]
  newLine?: object
  addLabel?: string
  name?: string
  hiddenFields?: string[]
}) {
  const grid = { display: 'grid', gridTemplateColumns: `${columns.map((c) => c.width).join(' ')} 32px`, gap: 8 }
  return (
    <Form.List name={name}>
      {(fields, { add, remove }) => (
        <div style={{ overflowX: 'auto' }}>
          <div style={{ ...grid, marginBottom: 4 }}>
            {columns.map((c) => <Typography.Text key={c.title} type="secondary">{c.title}</Typography.Text>)}
          </div>
          {fields.map(({ key, name: index }) => (
            <div key={key} style={grid}>
              {columns.map((c) => <div key={c.title}>{c.render(index)}</div>)}
              {hiddenFields.map((f) => <Form.Item key={f} name={[index, f]} hidden><Input /></Form.Item>)}
              <Button icon={<DeleteOutlined />} onClick={() => remove(index)} aria-label="Удалить строку" />
            </div>
          ))}
          <Button type="dashed" icon={<PlusOutlined />} onClick={() => add(newLine)} style={{ marginBottom: 16 }}>{addLabel}</Button>
        </div>
      )}
    </Form.List>
  )
}
