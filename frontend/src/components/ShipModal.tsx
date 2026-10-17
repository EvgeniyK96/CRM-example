import { Form, Input, Modal, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useApiAction } from '../api/hooks'
import type { Shipment } from '../api/types'

interface Props {
  order: { id: number; number: string; client_name: string } | null
  onClose: () => void
}

/** Отгрузка заказа: партии списываются по FEFO, открывается созданная накладная. */
export default function ShipModal({ order, onClose }: Props) {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const ship = useApiAction(
    async (v: object) => (await api.post<Shipment>(`/sales/orders/${order!.id}/ship/`, v)).data,
    {
      success: (s) => `Отгружено, накладная ${s.number}`,
      invalidate: 'all',
      onSuccess: (s) => {
        onClose()
        navigate(`/shipments/${s.id}`)
      },
    },
  )

  return (
    <Modal title={`Отгрузка заказа ${order?.number}`} open={!!order} onCancel={onClose} onOk={() => form.submit()}
      okText="Отгрузить" okButtonProps={{ loading: ship.isPending }} destroyOnHidden>
      <Typography.Paragraph type="secondary">
        {order?.client_name}. Продукция спишется со склада по FEFO — сначала партии с ближайшим сроком годности.
      </Typography.Paragraph>
      <Form form={form} layout="vertical" preserve={false} onFinish={(v) => ship.mutate(v)}>
        <Form.Item name="vehicle" label="Транспорт"><Input placeholder="Марка и госномер" /></Form.Item>
        <Form.Item name="driver" label="Водитель"><Input /></Form.Item>
        <Form.Item name="comment" label="Комментарий"><Input.TextArea rows={2} /></Form.Item>
      </Form>
    </Modal>
  )
}
