import { Form, InputNumber, Select } from 'antd'
import { toOptions, useList } from '../api/hooks'
import type { Item } from '../api/types'
import { fmtMoney } from '../utils/format'
import type { LineColumn } from './LinesFormList'

/** Колонки строк закупочных документов: сырьё, количество (с единицей), цена, сумма. */
export function useRawLineColumns({ lockItem }: { lockItem?: (line: Record<string, unknown>) => boolean } = {}): LineColumn[] {
  const raw = useList<Item>('/catalog/items/', { kind: 'raw' })
  const unitOf = (id?: number) => raw.data?.find((i) => i.id === id)?.unit_code

  return [
    {
      title: 'Сырьё',
      width: 'minmax(180px, 3fr)',
      render: (i) => (
        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => (
            <Form.Item name={[i, 'item']} rules={[{ required: true, message: 'Выберите сырьё' }]}>
              <Select showSearch={{ optionFilterProp: 'label' }} placeholder="Сырьё" loading={raw.isLoading}
                disabled={lockItem?.(getFieldValue(['lines', i]) ?? {})}
                options={toOptions(raw.data, (item) => `${item.code} · ${item.name}`)} />
            </Form.Item>
          )}
        </Form.Item>
      ),
    },
    {
      title: 'Количество',
      width: 'minmax(120px, 1fr)',
      render: (i) => (
        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => (
            <Form.Item name={[i, 'quantity']} rules={[{ required: true, message: 'Укажите' }]}>
              <InputNumber min="0.001" stringMode suffix={unitOf(getFieldValue(['lines', i, 'item']))} style={{ width: '100%' }} />
            </Form.Item>
          )}
        </Form.Item>
      ),
    },
    {
      title: 'Цена',
      width: 'minmax(100px, 1fr)',
      render: (i) => (
        <Form.Item name={[i, 'price']}>
          <InputNumber min="0" stringMode style={{ width: '100%' }} />
        </Form.Item>
      ),
    },
    {
      title: 'Сумма',
      width: 'minmax(90px, 1fr)',
      render: (i) => (
        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => (
            <div style={{ paddingTop: 5, textAlign: 'right' }}>
              {fmtMoney(Number(getFieldValue(['lines', i, 'quantity']) || 0) * Number(getFieldValue(['lines', i, 'price']) || 0))}
            </div>
          )}
        </Form.Item>
      ),
    },
  ]
}
