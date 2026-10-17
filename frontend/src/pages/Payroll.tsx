import { Button, DatePicker, Modal, Table } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useApiAction, useList } from '../api/hooks'
import { PAYROLL_STATUS } from '../api/statuses'
import type { PayrollPeriod } from '../api/types'
import StatusTag from '../components/StatusTag'
import { fmtMoney } from '../utils/format'

const URL = '/payroll/periods/'

export default function Payroll() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [month, setMonth] = useState<Dayjs>(dayjs().subtract(1, 'month'))
  const periods = useList<PayrollPeriod>(URL)
  const create = useApiAction(
    async () => (await api.post<PayrollPeriod>(URL, { year: month.year(), month: month.month() + 1 })).data,
    { success: 'Ведомость рассчитана по табелю', invalidate: [URL], onSuccess: (p) => navigate(`/payroll/${p.id}`) },
  )

  return (
    <>
      <Button type="primary" style={{ marginBottom: 16 }} onClick={() => setOpen(true)}>Рассчитать зарплату за месяц</Button>
      <Table<PayrollPeriod> rowKey="id" size="middle" loading={periods.isLoading} dataSource={periods.data} pagination={false}
        onRow={(p) => ({ onClick: () => navigate(`/payroll/${p.id}`), style: { cursor: 'pointer' } })}
        columns={[
          { title: 'Месяц', render: (_, p) => dayjs(new Date(p.year, p.month - 1)).format('MMMM YYYY') },
          { title: 'Сотрудников', render: (_, p) => p.totals.employees, align: 'center' },
          { title: 'Начислено', render: (_, p) => fmtMoney(p.totals.gross), align: 'right' },
          { title: 'Удержано', render: (_, p) => fmtMoney(p.totals.withheld), align: 'right' },
          { title: 'К выплате', render: (_, p) => <b>{fmtMoney(p.totals.net)}</b>, align: 'right' },
          { title: 'Взносы работодателя', render: (_, p) => fmtMoney(p.totals.employer_total), align: 'right' },
          { title: 'Статус', dataIndex: 'status', render: (s: string) => <StatusTag map={PAYROLL_STATUS} value={s} /> },
        ]} />
      <Modal title="Новая расчётная ведомость" open={open} onCancel={() => setOpen(false)} onOk={() => create.mutate()}
        okText="Рассчитать" okButtonProps={{ loading: create.isPending }}>
        <p>Начисления рассчитаются по табелю: оклад, отпускные, больничные; удержания и взносы — по действующим ставкам.</p>
        <DatePicker picker="month" value={month} allowClear={false} onChange={(v) => v && setMonth(v)}
          disabledDate={(d) => d.isAfter(dayjs(), 'month')} />
      </Modal>
    </>
  )
}
