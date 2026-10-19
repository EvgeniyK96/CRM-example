import { useQuery } from '@tanstack/react-query'
import { DatePicker, Segmented, Select, Table, Tag, Tooltip, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { api, type Page } from '../api/client'
import { toOptions, useList } from '../api/hooks'
import type { Department, WorkDayRow } from '../api/types'
import { fmtDate, fmtDuration, fmtTime, toApiDate } from '../utils/format'

type View = 'days' | 'totals'

interface Total {
  user: number
  user_name: string
  department_name: string | null
  days: number
  worked: number
  late: number
  short: number
  auto: number
}

const URL = '/hr/workdays/'

/** Отчёт по рабочему времени: дни сотрудников и итоги за период (отдел кадров, бухгалтерия). */
export default function WorkTime() {
  const [range, setRange] = useState<[Dayjs, Dayjs]>([dayjs().startOf('month'), dayjs()])
  const [department, setDepartment] = useState<number>()
  const [view, setView] = useState<View>('days')
  const departments = useList<Department>('/hr/departments/', { is_active: true })

  const params = { date_from: toApiDate(range[0]), date_to: toApiDate(range[1]), department, page_size: 1000 }
  const rows = useQuery({
    queryKey: [URL, params],
    queryFn: async () => (await api.get<Page<WorkDayRow>>(URL, { params })).data.results,
  })

  const totals = Object.values((rows.data ?? []).reduce<Record<number, Total>>((acc, r) => {
    const t = acc[r.user] ??= { user: r.user, user_name: r.user_name, department_name: r.department_name, days: 0, worked: 0, late: 0, short: 0, auto: 0 }
    t.days += 1
    t.worked += r.worked_seconds
    t.late += Number(r.late)
    t.short += Number(r.status === 'finished' && r.worked_seconds < r.norm_seconds)
    t.auto += Number(r.auto_closed)
    return acc
  }, {})).sort((a, b) => a.user_name.localeCompare(b.user_name))

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Segmented<View> value={view} onChange={setView} options={[{ value: 'days', label: 'По дням' }, { value: 'totals', label: 'Итоги' }]} />
        <DatePicker.RangePicker value={range} format="DD.MM.YYYY" allowClear={false}
          onChange={(v) => v?.[0] && v[1] && setRange([v[0], v[1]])} />
        <Select allowClear placeholder="Подразделение" style={{ width: 240 }} value={department} onChange={setDepartment}
          options={toOptions(departments.data, (d) => d.name)} />
      </div>
      {view === 'days' ? (
        <Table<WorkDayRow> rowKey={(r) => r.id ?? `${r.user}-${r.date}`} size="middle" loading={rows.isLoading} dataSource={rows.data}
          pagination={{ pageSize: 50, hideOnSinglePage: true }}
          columns={[
            { title: 'Дата', dataIndex: 'date', render: fmtDate, width: 110 },
            { title: 'Сотрудник', dataIndex: 'user_name' },
            { title: 'Подразделение', dataIndex: 'department_name', render: (v) => v ?? '—' },
            {
              title: 'Начало', dataIndex: 'started_at',
              render: (v, r) => <>{fmtTime(v)} {r.late && <Tag color="orange">опоздание</Tag>}</>,
            },
            {
              title: 'Конец', dataIndex: 'finished_at',
              render: (v, r) => r.status === 'working' ? <Tag color="green">работает</Tag>
                : r.status === 'paused' ? <Tag color="gold">пауза</Tag>
                  : <>{fmtTime(v)} {r.auto_closed && (
                    <Tooltip title="Сотрудник не завершил день — закрыт автоматически по норме, время оценочное">
                      <Tag color="red">не завершён</Tag>
                    </Tooltip>
                  )}</>,
            },
            {
              title: 'Отработано', dataIndex: 'worked_seconds', align: 'right',
              render: (v: number, r) => r.status === 'finished' && v < r.norm_seconds
                ? <Typography.Text type="danger">{fmtDuration(v)}</Typography.Text> : fmtDuration(v),
            },
            { title: 'Перерывы', dataIndex: 'break_seconds', align: 'right', render: fmtDuration },
            {
              title: 'Отчёт', dataIndex: 'report', ellipsis: { showTitle: false },
              render: (v: string) => v ? <Tooltip title={<span style={{ whiteSpace: 'pre-wrap' }}>{v}</span>}>{v}</Tooltip> : '—',
            },
          ]} />
      ) : (
        <Table<Total> rowKey="user" size="middle" loading={rows.isLoading} dataSource={totals} pagination={false}
          columns={[
            { title: 'Сотрудник', dataIndex: 'user_name' },
            { title: 'Подразделение', dataIndex: 'department_name', render: (v) => v ?? '—' },
            { title: 'Дней', dataIndex: 'days', align: 'right' },
            { title: 'Отработано', dataIndex: 'worked', align: 'right', render: fmtDuration },
            { title: 'В среднем за день', align: 'right', render: (_, t) => fmtDuration(t.worked / t.days) },
            { title: 'Опозданий', dataIndex: 'late', align: 'right', render: (v: number) => v || '—' },
            { title: 'Дней меньше нормы', dataIndex: 'short', align: 'right', render: (v: number) => v || '—' },
            { title: 'Не завершены', dataIndex: 'auto', align: 'right', render: (v: number) => v || '—' },
          ]} />
      )}
    </>
  )
}
