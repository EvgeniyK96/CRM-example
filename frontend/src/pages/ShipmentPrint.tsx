import type { CSSProperties } from 'react'
import { useParams } from 'react-router-dom'
import { useDetail } from '../api/hooks'
import type { Shipment, ShipmentItem } from '../api/types'
import { COMPANY } from '../config'
import { fmtDate, fmtMoney, fmtQty } from '../utils/format'

/** Строки накладной: по продукту, с перечнем партий и сроков годности (удостоверение для пищевой продукции). */
function groupByLine(items: ShipmentItem[]) {
  const lines = new Map<number, { item: ShipmentItem; quantity: number; lots: ShipmentItem[] }>()
  for (const i of items) {
    const line = lines.get(i.order_line) ?? { item: i, quantity: 0, lots: [] }
    line.quantity += Number(i.quantity)
    line.lots.push(i)
    lines.set(i.order_line, line)
  }
  return [...lines.values()]
}

const cell: CSSProperties = { border: '1px solid #000', padding: '4px 6px', verticalAlign: 'top' }
const right: CSSProperties = { ...cell, textAlign: 'right', whiteSpace: 'nowrap' }

/** Печатная форма расходной накладной (упрощённая). Открывается в отдельной вкладке. */
export default function ShipmentPrint() {
  const { id } = useParams()
  const { data: s } = useDetail<Shipment>('/sales/shipments/', id)
  if (!s) return null
  const lines = groupByLine(s.items)

  return (
    <div style={{ maxWidth: 800, margin: '24px auto', padding: '0 16px', fontFamily: 'Times New Roman, serif', fontSize: 14, color: '#000', background: '#fff' }}>
      <style>{'@media print { .no-print { display: none } body { margin: 0 } }'}</style>
      <div className="no-print" style={{ textAlign: 'right', marginBottom: 16 }}>
        <button onClick={() => window.print()}>Печать</button>
      </div>

      <h2 style={{ textAlign: 'center', margin: '0 0 4px' }}>Расходная накладная № {s.number}</h2>
      <p style={{ textAlign: 'center', marginTop: 0 }}>от {fmtDate(s.date)} · по заказу {s.order_number}</p>

      <p><b>Поставщик:</b> {COMPANY.name}, БИН {COMPANY.taxId}, {COMPANY.address}</p>
      <p>
        <b>Покупатель:</b> {s.client_name}{s.client_tax_id && `, БИН ${s.client_tax_id}`}
        {s.client_legal_address && `, ${s.client_legal_address}`}
      </p>
      <p><b>Адрес доставки:</b> {s.delivery_address || '—'}</p>
      {(s.vehicle || s.driver) && <p><b>Транспорт:</b> {[s.vehicle, s.driver].filter(Boolean).join(', ')}</p>}

      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
        <thead>
          <tr>
            {['№', 'Наименование', 'Партии / годна до', 'Ед.', 'Кол-во', 'Цена', 'Сумма'].map((h) => (
              <th key={h} style={{ ...cell, background: '#eee' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lines.map(({ item, quantity, lots }, idx) => (
            <tr key={item.order_line}>
              <td style={cell}>{idx + 1}</td>
              <td style={cell}>{item.item_name}</td>
              <td style={{ ...cell, fontSize: 12 }}>
                {lots.map((l) => <div key={l.id}>{l.lot_number} — до {fmtDate(l.expiry_date)} ({fmtQty(l.quantity)})</div>)}
              </td>
              <td style={cell}>{item.unit_code}</td>
              <td style={right}>{fmtQty(quantity)}</td>
              <td style={right}>{fmtMoney(item.price)}</td>
              <td style={right}>{fmtMoney(quantity * Number(item.price))}</td>
            </tr>
          ))}
          <tr>
            <td style={{ ...right, fontWeight: 'bold' }} colSpan={6}>Итого</td>
            <td style={{ ...right, fontWeight: 'bold' }}>{fmtMoney(s.total)}</td>
          </tr>
        </tbody>
      </table>

      <p style={{ marginTop: 12 }}>
        Условия оплаты: {s.payment_delay_days ? `отсрочка ${s.payment_delay_days} дн.` : 'предоплата'}
      </p>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 48 }}>
        <div>Отпустил ______________ / {s.created_by_name ?? ''}</div>
        <div>Получил ______________ / ______________</div>
      </div>
    </div>
  )
}
