import { Descriptions, Table, Typography } from 'antd'
import type { Payslip } from '../api/types'
import { fmtMoney } from '../utils/format'

/** Расчётный листок: начисления, удержания, к выплате; взносы работодателя — справочно. */
export default function PayslipView({ slip }: { slip: Payslip }) {
  const accruals = [
    { name: `Оклад за отработанное (${slip.worked_days} из ${slip.norm_days} дн.)`, amount: slip.salary_accrued },
    ...(Number(slip.vacation_pay) ? [{ name: `Отпускные (${slip.vacation_days} календ. дн.)`, amount: slip.vacation_pay }] : []),
    ...(Number(slip.sick_pay) ? [{ name: `Больничные (${slip.sick_days} раб. дн.)`, amount: slip.sick_pay }] : []),
    ...(Number(slip.bonus) ? [{ name: 'Премия', amount: slip.bonus }] : []),
  ]
  const withholdings = slip.lines.filter((l) => l.payer === 'employee')
  const employer = slip.lines.filter((l) => l.payer === 'employer')

  return (
    <>
      <Descriptions size="small" column={2} items={[
        { label: 'Сотрудник', children: slip.employee_name },
        { label: 'Период', children: slip.period_label },
        { label: 'Подразделение', children: slip.department_name },
        { label: 'Должность', children: slip.position_name },
        { label: 'Оклад', children: fmtMoney(slip.salary) },
        ...(slip.unpaid_days ? [{ label: 'Без содержания', children: `${slip.unpaid_days} дн.` }] : []),
      ]} />
      <Typography.Title level={5}>Начислено</Typography.Title>
      <Table rowKey="name" size="small" pagination={false} showHeader={false} dataSource={accruals}
        columns={[{ dataIndex: 'name' }, { dataIndex: 'amount', align: 'right', render: fmtMoney }]}
        summary={() => (
          <Table.Summary.Row style={{ fontWeight: 600 }}>
            <Table.Summary.Cell index={0}>Итого начислено</Table.Summary.Cell>
            <Table.Summary.Cell index={1} align="right">{fmtMoney(slip.gross)}</Table.Summary.Cell>
          </Table.Summary.Row>
        )} />
      <Typography.Title level={5} style={{ marginTop: 16 }}>Удержано</Typography.Title>
      <Table rowKey="id" size="small" pagination={false} showHeader={false} dataSource={withholdings}
        columns={[
          { render: (_, l) => `${l.name}: ${Number(l.percent)}% от ${fmtMoney(l.base)}` },
          { dataIndex: 'amount', align: 'right', render: fmtMoney },
        ]}
        summary={() => (
          <Table.Summary.Row style={{ fontWeight: 600 }}>
            <Table.Summary.Cell index={0}>Итого удержано</Table.Summary.Cell>
            <Table.Summary.Cell index={1} align="right">{fmtMoney(slip.withheld)}</Table.Summary.Cell>
          </Table.Summary.Row>
        )} />
      <Typography.Title level={4} style={{ marginTop: 16, textAlign: 'right' }}>К выплате: {fmtMoney(slip.net)}</Typography.Title>
      <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
        Справочно, за счёт работодателя: {employer.map((l) => `${l.code} ${fmtMoney(l.amount)}`).join(', ')} —
        всего {fmtMoney(slip.employer_total)}.
      </Typography.Paragraph>
    </>
  )
}
