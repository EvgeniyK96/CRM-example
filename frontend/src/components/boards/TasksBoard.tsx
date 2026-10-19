import { App } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useApiAction } from '../../api/hooks'
import { TASK_STATUS } from '../../api/statuses'
import type { ProductionTask } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { fmtDate, fmtQty } from '../../utils/format'
import FinishModal from '../FinishModal'
import Kanban from '../Kanban'

/** Канбан заданий: запуск, завершение и отмена переносом карточки — только в своём цехе. */
export default function TasksBoard({ rows }: { rows: ProductionTask[] }) {
  const { canManageDepartment } = useAuth()
  const { modal } = App.useApp()
  const navigate = useNavigate()
  const [finishing, setFinishing] = useState<ProductionTask | null>(null)

  // Запуск и отмена меняют склад и статусы заказов — обновляем всё
  const act = useApiAction(
    async ({ task, action }: { task: ProductionTask; action: 'start' | 'cancel' }) =>
      (await api.post<ProductionTask>(`/production/tasks/${task.id}/${action}/`)).data,
    { success: (t) => `${t.number}: ${TASK_STATUS[t.status].label.toLowerCase()}`, invalidate: 'all' },
  )

  const targets = (t: ProductionTask): string[] => {
    if (!canManageDepartment(t.department)) return []
    if (t.status === 'planned') return ['in_progress', 'cancelled']
    if (t.status === 'in_progress') return ['done']
    return []
  }

  const onMove = (task: ProductionTask, to: string) => {
    if (to === 'done') setFinishing(task)
    else if (to === 'in_progress') {
      modal.confirm({
        title: `Запустить ${task.number}?`,
        content: `Сырьё на ${fmtQty(task.planned_qty, task.unit_code)} «${task.product_name}» будет списано со склада (FEFO).`,
        okText: 'Запустить', cancelText: 'Отмена',
        onOk: () => act.mutateAsync({ task, action: 'start' }),
      })
    } else if (to === 'cancelled') {
      modal.confirm({
        title: `Отменить ${task.number}?`,
        content: 'Связанные заказы вернутся к планированию.',
        okText: 'Отменить задание', okButtonProps: { danger: true }, cancelText: 'Не отменять',
        onOk: () => act.mutateAsync({ task, action: 'cancel' }),
      })
    }
  }

  return (
    <>
      <Kanban<ProductionTask>
        rows={rows}
        statuses={TASK_STATUS}
        closed={['done', 'cancelled']}
        dateOf={(t) => t.planned_date}
        targets={targets}
        onMove={onMove}
        onOpen={(t) => navigate(`/tasks/${t.id}`)}
        card={(t) => (
          <>
            <div className="kanban-card-title"><span>{t.number}</span><span>{fmtQty(t.planned_qty, t.unit_code)}</span></div>
            <div className="kanban-card-line">{t.product_name}</div>
            <div className="kanban-card-meta">
              <span>{fmtDate(t.planned_date)} · {t.department_name}</span>
              <span>{t.allocations.length ? `заказов: ${t.allocations.length}` : 'на запас'}</span>
            </div>
          </>
        )}
      />
      {finishing && <FinishModal task={finishing} open onClose={() => setFinishing(null)} />}
    </>
  )
}
