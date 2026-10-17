import { DatePicker, Form, Input, InputNumber, Modal, Radio, Select } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { api } from '../api/client'
import { toOptions, useApiAction, useList } from '../api/hooks'
import type { Client, Invoice, Supplier } from '../api/types'
import { fmtMoney, toApiDate } from '../utils/format'

export interface PaymentPreset {
  direction: 'incoming' | 'outgoing'
  client?: number
  invoice?: number
  amount?: string
}

/** Ввод платежа. Поступление без счёта разнесётся на самые старые неоплаченные счета клиента. */
export default function PaymentModal({ preset, onClose }: { preset: PaymentPreset | null; onClose: () => void }) {
  const [form] = Form.useForm()
  const direction = Form.useWatch('direction', form) ?? preset?.direction
  const client = Form.useWatch('client', form) ?? preset?.client
  const clients = useList<Client>('/sales/clients/', { is_active: true })
  const suppliers = useList<Supplier>('/catalog/suppliers/', { is_active: true })
  const invoices = useList<Invoice>('/accounting/invoices/', { client, status: 'open' }, direction === 'incoming' && !!client)

  const save = useApiAction((v: object) => api.post('/accounting/payments/', v), {
    success: 'Платёж проведён', invalidate: 'all', onSuccess: onClose,
  })

  const submit = (v: Record<string, unknown>) => save.mutate({ ...v, date: toApiDate(v.date as Dayjs) })

  return (
    <Modal title="Новый платёж" open={!!preset} onCancel={onClose} onOk={() => form.submit()} okText="Провести"
      okButtonProps={{ loading: save.isPending }} destroyOnHidden>
      <Form form={form} layout="vertical" preserve={false} onFinish={submit}
        initialValues={{ method: 'bank', date: dayjs(), ...preset }}>
        <Form.Item name="direction" label="Направление">
          <Radio.Group optionType="button" options={[
            { value: 'incoming', label: 'Поступление от клиента' }, { value: 'outgoing', label: 'Оплата поставщику' },
          ]} />
        </Form.Item>
        {direction === 'incoming' ? (
          <>
            <Form.Item name="client" label="Клиент" rules={[{ required: true }]}>
              <Select showSearch={{ optionFilterProp: 'label' }} options={toOptions(clients.data, (c) => c.name)}
                onChange={() => form.setFieldValue('invoice', undefined)} />
            </Form.Item>
            <Form.Item name="invoice" label="В оплату счёта" extra="Не выбран — на самые старые неоплаченные счета">
              <Select allowClear options={toOptions(invoices.data, (i) => `${i.number} от ${dayjs(i.date).format('DD.MM.YYYY')}, остаток ${fmtMoney(i.remaining)}`)} />
            </Form.Item>
          </>
        ) : (
          <Form.Item name="supplier" label="Поставщик" rules={[{ required: true }]}>
            <Select showSearch={{ optionFilterProp: 'label' }} options={toOptions(suppliers.data, (s) => s.name)} />
          </Form.Item>
        )}
        <Form.Item name="amount" label="Сумма" rules={[{ required: true }]}>
          <InputNumber min="0.01" stringMode style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="method" label="Способ">
          <Radio.Group options={[{ value: 'bank', label: 'Расчётный счёт' }, { value: 'cash', label: 'Касса' }]} />
        </Form.Item>
        <Form.Item name="date" label="Дата" rules={[{ required: true }]}>
          <DatePicker style={{ width: '100%' }} disabledDate={(d) => d.isAfter(dayjs(), 'day')} />
        </Form.Item>
        <Form.Item name="comment" label="Назначение платежа"><Input /></Form.Item>
      </Form>
    </Modal>
  )
}
