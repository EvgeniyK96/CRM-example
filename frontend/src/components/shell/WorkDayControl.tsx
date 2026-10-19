import { CheckCircleOutlined, ClockCircleOutlined, PauseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Descriptions, Input, Popover, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { useApiAction } from '../../api/hooks'
import type { WorkDaySummary } from '../../api/types'
import { fmtDuration, fmtTime } from '../../utils/format'

const URL = '/hr/workdays/'

const LABEL: Record<WorkDaySummary['status'], string> = {
  none: 'Начать день',
  working: 'Работаю',
  paused: 'Пауза',
  finished: 'День завершён',
}

/** Учёт рабочего дня в шапке, как в Битрикс24: начать → пауза / продолжить → завершить с отчётом. */
export default function WorkDayControl() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [report, setReport] = useState('')
  const [now, setNow] = useState(() => Date.now())

  const day = useQuery({
    queryKey: [URL, 'current'],
    queryFn: async () => (await api.get<WorkDaySummary>(`${URL}current/`)).data,
    refetchInterval: 5 * 60_000,
    refetchOnWindowFocus: true,
  })
  const fetchedAt = day.dataUpdatedAt

  // Таймер тикает раз в 20 секунд, пока день идёт; время с сервера + прошедшее с момента запроса
  const working = day.data?.status === 'working'
  useEffect(() => {
    if (!working) return
    const id = setInterval(() => setNow(Date.now()), 20_000)
    return () => clearInterval(id)
  }, [working])
  const worked = (day.data?.worked_seconds ?? 0) + (working ? Math.max(0, (now - fetchedAt) / 1000) : 0)

  const act = useApiAction(
    async (name: 'start' | 'pause' | 'finish') => (await api.post<WorkDaySummary>(`${URL}${name}/`, name === 'finish' ? { report } : {})).data,
    {
      onSuccess: (d) => {
        qc.setQueryData([URL, 'current'], d)
        qc.invalidateQueries({ queryKey: [URL], predicate: (q) => q.queryKey[1] !== 'current' })
        setNow(Date.now())
        if (d.status === 'finished') {
          setReport('')
          setOpen(false)
        }
      },
    },
  )

  if (!day.data) return null
  const d = day.data

  // Первое нажатие «Начать день» — сразу, без всплывающего окна
  if (d.status === 'none') {
    return (
      <button type="button" className="shell-workday shell-workday-none" onClick={() => act.mutate('start')} disabled={act.isPending}>
        <PlayCircleOutlined /> <span className="shell-workday-text">Начать день</span>
      </button>
    )
  }

  const icon = { working: <ClockCircleOutlined />, paused: <PauseCircleOutlined />, finished: <CheckCircleOutlined /> }[d.status]
  const panel = (
    <div className="workday-panel">
      <Typography.Text strong>{LABEL[d.status]} · {fmtDuration(worked)} из {fmtDuration(d.norm_seconds)}</Typography.Text>
      <Descriptions size="small" column={1} style={{ marginTop: 8 }} items={[
        { label: 'Начало', children: <>{fmtTime(d.started_at)} {d.late && <Tag color="orange">опоздание</Tag>}</> },
        { label: 'Перерывы', children: fmtDuration(d.break_seconds + (d.status === 'paused' ? (now - fetchedAt) / 1000 : 0)) },
        ...(d.finished_at ? [{ label: 'Завершён', children: fmtTime(d.finished_at) }] : []),
      ]} />
      {d.status !== 'finished' && (
        <Input.TextArea rows={2} placeholder="Отчёт за день (необязательно)" value={report} onChange={(e) => setReport(e.target.value)}
          style={{ margin: '8px 0' }} maxLength={4000} />
      )}
      <Space wrap>
        {d.status === 'working' && <Button icon={<PauseCircleOutlined />} onClick={() => act.mutate('pause')} loading={act.isPending}>Пауза</Button>}
        {d.status !== 'working' && (
          <Button icon={<PlayCircleOutlined />} onClick={() => act.mutate('start')} loading={act.isPending}>
            {d.status === 'finished' ? 'Продолжить день' : 'Продолжить'}
          </Button>
        )}
        {d.status !== 'finished' && <Button type="primary" onClick={() => act.mutate('finish')} loading={act.isPending}>Завершить день</Button>}
      </Space>
      {d.report && d.status === 'finished' && <Typography.Paragraph type="secondary" style={{ margin: '8px 0 0', whiteSpace: 'pre-wrap' }}>{d.report}</Typography.Paragraph>}
    </div>
  )

  return (
    <Popover open={open} onOpenChange={setOpen} trigger="click" placement="bottomRight" arrow={false} content={panel}>
      <button type="button" className={`shell-workday shell-workday-${d.status}`} aria-label={`${LABEL[d.status]}: ${fmtDuration(worked)}`}>
        {icon} <span className="shell-workday-text">{fmtDuration(worked)}</span>
      </button>
    </Popover>
  )
}
