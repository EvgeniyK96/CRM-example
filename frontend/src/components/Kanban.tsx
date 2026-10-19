import {
  DndContext, DragOverlay, KeyboardSensor, MouseSensor, TouchSensor, useDraggable, useDroppable, useSensor, useSensors,
  type DragEndEvent, type DragStartEvent,
} from '@dnd-kit/core'
import { theme, Typography } from 'antd'
import { useState, type ReactNode } from 'react'
import type { StatusInfo } from '../api/statuses'

export interface KanbanProps<T extends { id: number; status: string }> {
  rows: T[]
  statuses: Record<string, StatusInfo>
  /** Колонки по порядку; по умолчанию — все статусы */
  columns?: string[]
  /** Колонки завершённых документов: показываем только последние, чтобы доска не разрасталась */
  closed?: string[]
  /** Дата для сортировки: в открытых колонках сверху ближайшие, в закрытых — последние */
  dateOf: (row: T) => string
  card: (row: T) => ReactNode
  /** Сводка в шапке колонки (например, сумма заказов) */
  summary?: (rows: T[]) => ReactNode
  /** Куда можно перенести документ (с учётом прав); пустой список — карточку нельзя перетаскивать */
  targets: (row: T) => string[]
  onMove: (row: T, to: string) => void
  onOpen: (row: T) => void
}

const CLOSED_LIMIT = 20

/**
 * Канбан в стиле Битрикс24: колонки — статусы, перенос карточки = действие над документом.
 * Сам канбан ничего не меняет — onMove вызывает то же действие API, что и кнопка в карточке,
 * поэтому бизнес-правила и права проверяет сервер.
 */
export default function Kanban<T extends { id: number; status: string }>(props: KanbanProps<T>) {
  const { token } = theme.useToken()
  const [dragged, setDragged] = useState<T | null>(null)
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),  // короткий клик — открыть карточку
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 6 } }),  // на телефоне — долгое нажатие
    // Пробел — взять и положить, Enter оставляем для открытия карточки
    useSensor(KeyboardSensor, { keyboardCodes: { start: ['Space'], end: ['Space'], cancel: ['Escape'] } }),
  )
  const columns = props.columns ?? Object.keys(props.statuses)
  const allowed = dragged ? props.targets(dragged) : []

  const onDragStart = (e: DragStartEvent) => setDragged(props.rows.find((r) => r.id === e.active.id) ?? null)
  const onDragEnd = (e: DragEndEvent) => {
    const row = dragged
    setDragged(null)
    const to = e.over?.id as string | undefined
    if (row && to && to !== row.status && props.targets(row).includes(to)) props.onMove(row, to)
  }

  return (
    <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd} onDragCancel={() => setDragged(null)}
      accessibility={{ screenReaderInstructions: { draggable: 'Пробел — взять карточку, стрелки — выбрать колонку, пробел — положить, Esc — отмена.' } }}>
      <div className="kanban">
        {columns.map((status) => {
          const isClosed = props.closed?.includes(status) ?? false
          const rows = props.rows.filter((r) => r.status === status)
            .sort((a, b) => props.dateOf(a).localeCompare(props.dateOf(b)) * (isClosed ? -1 : 1) || a.id - b.id)
          const info = props.statuses[status]
          const color = (token as unknown as Record<string, string>)[info.color] ?? token.colorTextQuaternary
          const limited = isClosed && rows.length > CLOSED_LIMIT
          return (
            <Column key={status} id={status} color={color} label={info.label} count={rows.length}
              summary={rows.length > 0 && props.summary?.(rows)}
              state={!dragged ? 'idle' : status === dragged.status ? 'source' : allowed.includes(status) ? 'allowed' : 'blocked'}>
              {(limited ? rows.slice(0, CLOSED_LIMIT) : rows).map((row) => (
                <Card key={row.id} id={row.id} disabled={props.targets(row).length === 0} onOpen={() => props.onOpen(row)}>
                  {props.card(row)}
                </Card>
              ))}
              {limited && (
                <Typography.Text type="secondary" style={{ fontSize: 12, textAlign: 'center' }}>
                  Показаны последние {CLOSED_LIMIT} из {rows.length} — остальные в режиме списка
                </Typography.Text>
              )}
            </Column>
          )
        })}
      </div>
      <DragOverlay dropAnimation={null}>
        {dragged && <div className="kanban-card kanban-card-overlay">{props.card(dragged)}</div>}
      </DragOverlay>
    </DndContext>
  )
}

type ColumnState = 'idle' | 'source' | 'allowed' | 'blocked'

function Column({ id, color, label, count, summary, state, children }: {
  id: string; color: string; label: string; count: number; summary: ReactNode; state: ColumnState; children: ReactNode
}) {
  const { setNodeRef, isOver } = useDroppable({ id, disabled: state === 'blocked' })
  return (
    <section ref={setNodeRef} className={`kanban-column kanban-${state}${isOver && state === 'allowed' ? ' kanban-over' : ''}`}
      aria-label={`${label}: ${count}`}>
      <header className="kanban-head" style={{ borderTopColor: color }}>
        <span className="kanban-title">{label}</span>
        <span className="kanban-count">{count}</span>
        {summary && <div className="kanban-summary">{summary}</div>}
      </header>
      <div className="kanban-cards">{children}</div>
    </section>
  )
}

function Card({ id, disabled, onOpen, children }: { id: number; disabled: boolean; onOpen: () => void; children: ReactNode }) {
  const { setNodeRef, attributes, listeners, isDragging } = useDraggable({ id, disabled })
  return (
    // Неперемещаемую карточку всё равно можно открыть — не помечаем её aria-disabled
    <div ref={setNodeRef} {...(disabled ? {} : attributes)} {...listeners} role="button" tabIndex={0}
      className={`kanban-card${isDragging ? ' kanban-card-ghost' : ''}${disabled ? '' : ' kanban-card-movable'}`}
      onClick={onOpen}
      onKeyDown={(e) => {
        listeners?.onKeyDown?.(e)
        if (e.key === 'Enter' && !e.defaultPrevented) onOpen()
      }}>
      {children}
    </div>
  )
}
