import { useQuery } from '@tanstack/react-query'
import { Card, DatePicker, Select, Space, Table, Tag, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { api } from '../api/client'
import { toOptions, useList } from '../api/hooks'
import type { Department, Timesheet as TimesheetData } from '../api/types'
import { useAuth } from '../auth/AuthContext'

const WEEKDAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
const CODE_COLORS: Record<string, string> = { О: '#d9f7be', Б: '#ffccc7', К: '#bae0ff', НН: '#f0f0f0' }
const LEGEND = [['Я', 'явка'], ['В', 'выходной / праздник'], ['О', 'отпуск'], ['Б', 'больничный'], ['К', 'командировка'], ['НН', 'без содержания']]

type Row = TimesheetData['rows'][number]

/** Табель учёта рабочего времени — строится автоматически из календаря и отсутствий. */
export default function Timesheet() {
  const { user } = useAuth()
  const [month, setMonth] = useState<Dayjs>(dayjs())
  const [department, setDepartment] = useState<number | undefined>(user?.production_department ?? undefined)
  const departments = useList<Department>('/hr/departments/')
  const params = { year: month.year(), month: month.month() + 1, department }
  const { data, isLoading } = useQuery({
    queryKey: ['/hr/timesheet/', params],
    queryFn: async () => (await api.get<TimesheetData>('/hr/timesheet/', { params })).data,
  })

  const dayColumns = (data?.days ?? []).map((d, i) => ({
    title: <div style={{ lineHeight: 1.1 }}>{d.day}<br /><small style={{ fontWeight: 400 }}>{WEEKDAYS[d.weekday]}</small></div>,
    key: `d${d.day}`,
    width: 34,
    align: 'center' as const,
    onCell: () => ({ style: { background: d.workday ? undefined : '#fafafa', padding: '4px 2px' } }),
    render: (_: unknown, r: Row) => {
      const code = r.cells[i]
      return code ? <span style={{ background: CODE_COLORS[code], padding: '1px 3px', borderRadius: 3, fontSize: 12 }}>{code}</span> : null
    },
  }))

  return (
    <Card
      title={`Табель за ${month.format('MMMM YYYY')}`}
      extra={
        <Space wrap>
          <DatePicker picker="month" value={month} allowClear={false} onChange={(v) => v && setMonth(v)} />
          <Select allowClear placeholder="Все подразделения" style={{ width: 240 }} value={department} onChange={setDepartment}
            options={toOptions(departments.data, (d) => d.name)} />
        </Space>
      }
    >
      <Space wrap style={{ marginBottom: 12 }}>
        <Typography.Text>Норма: <b>{data?.norm_days ?? '—'}</b> рабочих дней.</Typography.Text>
        {LEGEND.map(([code, label]) => (
          <Tag key={code} color={CODE_COLORS[code] ? undefined : 'default'} style={{ background: CODE_COLORS[code] }}>{code} — {label}</Tag>
        ))}
      </Space>
      <Table<Row> rowKey="employee" size="small" bordered pagination={false} loading={isLoading} dataSource={data?.rows}
        columns={[
          {
            title: 'Сотрудник', fixed: 'left', width: 200,
            render: (_, r) => <><div>{r.full_name}</div><Typography.Text type="secondary" style={{ fontSize: 12 }}>{r.department_name}</Typography.Text></>,
          },
          ...dayColumns,
          { title: 'Отраб.', dataIndex: 'worked_days', align: 'center', width: 60 },
          { title: 'Отпуск', dataIndex: 'vacation_days', align: 'center', width: 60, render: (v: number) => v || '' },
          { title: 'Больн.', dataIndex: 'sick_days', align: 'center', width: 60, render: (v: number) => v || '' },
          { title: 'НН', dataIndex: 'unpaid_days', align: 'center', width: 50, render: (v: number) => v || '' },
        ]}
        scroll={{ x: 'max-content' }} />
    </Card>
  )
}
