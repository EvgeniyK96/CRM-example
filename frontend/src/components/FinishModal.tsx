import { Form, Input, InputNumber, Modal, Typography } from 'antd'
import { api } from '../api/client'
import { useApiAction } from '../api/hooks'
import type { ProductionTask } from '../api/types'

const URL = '/production/tasks/'

/** Завершение задания: выпуск годной продукции и брак. */
export default function FinishModal({ task, open, onClose }: { task: ProductionTask; open: boolean; onClose: () => void }) {
  const [form] = Form.useForm()
  const finish = useApiAction((v: object) => api.post(`${URL}${task.id}/finish/`, v), {
    success: 'Задание завершено, партия продукции на складе', invalidate: 'all', onSuccess: onClose,
  })
  return (
    <Modal title={`Завершение ${task.number}`} open={open} onCancel={onClose} onOk={() => form.submit()}
      okText="Завершить" okButtonProps={{ loading: finish.isPending }} destroyOnHidden>
      <Typography.Paragraph type="secondary">
        Годная продукция поступит на склад и распределится по заказам — сначала с ближайшей отгрузкой.
        Если выпущено меньше плана, недостающее снова попадёт в потребность.
      </Typography.Paragraph>
      <Form form={form} layout="vertical" preserve={false} initialValues={{ actual_qty: task.planned_qty, defect_qty: '0' }}
        onFinish={(v) => finish.mutate(v)}>
        <Form.Item name="actual_qty" label="Выпущено годной продукции" rules={[{ required: true }]}>
          <InputNumber min="0" stringMode suffix={task.unit_code} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="defect_qty" label="Брак">
          <InputNumber min="0" stringMode suffix={task.unit_code} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="comment" label="Комментарий"><Input.TextArea rows={2} /></Form.Item>
      </Form>
    </Modal>
  )
}
