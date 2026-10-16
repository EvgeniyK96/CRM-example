import { Form, InputNumber, Select } from 'antd'
import { toOptions, useList } from '../api/hooks'
import type { Item, ItemKind } from '../api/types'
import { fmtMoney } from '../utils/format'
import type { LineColumn } from './LinesFormList'

type Getter = (name: (string | number)[] | string) => unknown

interface Options {
  kind: ItemKind
  /** Запретить смену номенклатуры в строке (например, строка пришла из заявки) */
  lockItem?: (line: Record<string, unknown>) => boolean
  /** Цена, если в строке не указана своя (сервер подставит её же) */
  defaultPrice?: (item: Item, getFieldValue: Getter) => number
}

/** Колонки строк документа: номенклатура, количество (с единицей), цена, сумма. */
export function useItemLineColumns({ kind, lockItem, defaultPrice }: Options): LineColumn[] {
  const items = useList<Item>('/catalog/items/', { kind })
  const itemOf = (id: unknown) => items.data?.find((i) => i.id === id)

  const priceOf = (i: number, get: Getter) => {
    const own = get(['lines', i, 'price'])
    if (own != null && own !== '') return Number(own)
    const item = itemOf(get(['lines', i, 'item']))
    return item && defaultPrice ? defaultPrice(item, get) : 0
  }

  return [
    {
      title: kind === 'raw' ? 'Сырьё' : 'Продукция',
      width: 'minmax(180px, 3fr)',
      render: (i) => (
        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => (
            <Form.Item name={[i, 'item']} rules={[{ required: true, message: 'Выберите позицию' }]}>
              <Select showSearch={{ optionFilterProp: 'label' }} placeholder="Позиция" loading={items.isLoading}
                disabled={lockItem?.(getFieldValue(['lines', i]) ?? {})}
                options={toOptions(items.data?.filter((it) => it.is_active), (it) => `${it.code} · ${it.name}`)} />
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
              <InputNumber min="0.001" stringMode suffix={itemOf(getFieldValue(['lines', i, 'item']))?.unit_code} style={{ width: '100%' }} />
            </Form.Item>
          )}
        </Form.Item>
      ),
    },
    {
      title: 'Цена',
      width: 'minmax(100px, 1fr)',
      render: (i) => (
        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => (
            <Form.Item name={[i, 'price']}>
              <InputNumber min="0" stringMode style={{ width: '100%' }}
                placeholder={defaultPrice ? fmtMoney(priceOf(i, getFieldValue)) : undefined} />
            </Form.Item>
          )}
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
              {fmtMoney(Number(getFieldValue(['lines', i, 'quantity']) || 0) * priceOf(i, getFieldValue))}
            </div>
          )}
        </Form.Item>
      ),
    },
  ]
}
