import { ArrowLeftOutlined } from '@ant-design/icons'
import { Button, Card, Descriptions, InputNumber, Modal, Popconfirm, Radio, Space, Table } from 'antd'
import dayjs from 'dayjs'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useApiAction, useDetail, useList } from '../api/hooks'
import { PAYROLL_STATUS } from '../api/statuses'
import type { PayrollPeriod, Payslip } from '../api/types'
import PayslipView from '../components/PayslipView'
import StatusTag from '../components/StatusTag'
import { fmtDateTime, fmtMoney } from '../utils/format'

const URL = '/payroll/periods/'
const SLIPS = '/payroll/payslips/'

function BonusInput({ slip }: { slip: Payslip }) {
  const [value, setValue] = useState<string | null>(slip.bonus)
  const save = useApiAction((bonus: string) => api.patch(`${SLIPS}${slip.id}/`, { bonus }), { invalidate: [SLIPS, URL] })
  const commit = () => value !== slip.bonus && save.mutate(value || '0')
  return (
    <InputNumber size="small" min="0" stringMode value={value} onChange={setValue} onBlur={commit} onPressEnter={commit}
      onClick={(e) => e.stopPropagation()} style={{ width: 120 }} disabled={save.isPending} />
  )
}

export default function PayrollDetail() {
  const { id } = useParams()
  const { data: period } = useDetail<PayrollPeriod>(URL, id)
  const slips = useList<Payslip>(SLIPS, { period: id })
  const [shown, setShown] = useState<Payslip | null>(null)
  const [method, setMethod] = useState<'bank' | 'cash'>('bank')

  const act = (name: string, body?: object) => () => api.post(`${URL}${id}/${name}/`, body)
  const recalc = useApiAction(act('calculate'), { success: 'Пересчитано по текущему табелю', invalidate: [URL, SLIPS] })
  const post = useApiAction(act('post'), { success: 'Ведомость проведена', invalidate: 'all' })
  const unpost = useApiAction(act('unpost'), { success: 'Проведение отменено', invalidate: 'all' })
  const pay = useApiAction(() => api.post(`${URL}${id}/pay/`, { method }), { success: 'Зарплата выплачена', invalidate: 'all' })

  if (!period) return <Card loading />
  const draft = period.status === 'draft'

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Link to="/payroll"><ArrowLeftOutlined /> Все ведомости</Link>
      <Card
        title={<>Зарплата за {dayjs(new Date(period.year, period.month - 1)).format('MMMM YYYY')} <StatusTag map={PAYROLL_STATUS} value={period.status} /></>}
        extra={
          <Space wrap>
            {draft && <Button loading={recalc.isPending} onClick={() => recalc.mutate()}>Пересчитать по табелю</Button>}
            {draft && (
              <Popconfirm title="Провести ведомость?" description="Будут сформированы проводки; изменения станут невозможны."
                onConfirm={() => post.mutate()}>
                <Button type="primary" loading={post.isPending}>Провести</Button>
              </Popconfirm>
            )}
            {period.status === 'posted' && (
              <>
                <Popconfirm title="Отменить проведение?" onConfirm={() => unpost.mutate()}><Button>Отменить проведение</Button></Popconfirm>
                <Popconfirm
                  title="Выплатить зарплату?"
                  description={<Radio.Group value={method} onChange={(e) => setMethod(e.target.value)}
                    options={[{ value: 'bank', label: 'С расчётного счёта' }, { value: 'cash', label: 'Из кассы' }]} />}
                  onConfirm={() => pay.mutate()}>
                  <Button type="primary" loading={pay.isPending}>Выплатить {fmtMoney(period.totals.net)}</Button>
                </Popconfirm>
              </>
            )}
          </Space>
        }
      >
        <Descriptions size="small" column={{ xs: 1, md: 3 }} items={[
          { label: 'Сотрудников', children: period.totals.employees },
          { label: 'Начислено', children: fmtMoney(period.totals.gross) },
          { label: 'Удержано', children: fmtMoney(period.totals.withheld) },
          { label: 'К выплате', children: <b>{fmtMoney(period.totals.net)}</b> },
          { label: 'Взносы работодателя', children: fmtMoney(period.totals.employer_total) },
          { label: 'Рассчитана', children: fmtDateTime(period.calculated_at) },
          { label: 'Проведена', children: fmtDateTime(period.posted_at) },
          { label: 'Выплачена', children: fmtDateTime(period.paid_at) },
        ]} />
      </Card>
      <Card size="small" title="Расчётные листки" extra={draft && 'Премию можно ввести прямо в таблице'}>
        <Table<Payslip> rowKey="id" size="small" loading={slips.isLoading} dataSource={slips.data} pagination={false}
          onRow={(s) => ({ onClick: () => setShown(s), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'Сотрудник', render: (_, s) => <><div>{s.employee_name}</div><small style={{ color: '#888' }}>{s.department_name}</small></> },
            { title: 'Оклад', dataIndex: 'salary', align: 'right', render: fmtMoney },
            { title: 'Дни', render: (_, s) => `${s.worked_days}/${s.norm_days}`, align: 'center' },
            {
              title: 'Отпуск / больн.', align: 'center',
              render: (_, s) => [s.vacation_days && `О ${s.vacation_days}`, s.sick_days && `Б ${s.sick_days}`].filter(Boolean).join(', ') || '—',
            },
            { title: 'Премия', render: (_, s) => (draft ? <BonusInput slip={s} /> : fmtMoney(s.bonus)), align: 'right' },
            { title: 'Начислено', dataIndex: 'gross', align: 'right', render: fmtMoney },
            { title: 'Удержано', dataIndex: 'withheld', align: 'right', render: fmtMoney },
            { title: 'К выплате', dataIndex: 'net', align: 'right', render: (v: string) => <b>{fmtMoney(v)}</b> },
          ]} />
      </Card>
      <Modal title="Расчётный листок" open={!!shown} onCancel={() => setShown(null)} width={640}
        footer={<Button onClick={() => window.print()}>Печать</Button>}>
        {shown && <PayslipView slip={shown} />}
      </Modal>
    </Space>
  )
}
