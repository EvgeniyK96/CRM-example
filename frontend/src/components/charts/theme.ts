/**
 * Токены графиков — эталонная проверенная палитра (светлая тема).
 * Категориальные слоты назначаются строго по порядку; первые три проходят проверку
 * на различимость при дальтонизме (validate_palette.js: CVD ΔE ≥ 9.2). У бирюзового контраст
 * с фоном 2.74:1 — поэтому у каждого графика есть табличный вид и легенда.
 */
export const SERIES = ['#2a78d6', '#eb6834', '#1baf7a'] as const

export const CHART = {
  surface: '#fcfcfb',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  muted: '#898781',
  textPrimary: '#0b0b0b',
  textSecondary: '#52514e',
  deltaGood: '#006300',
  critical: '#d03b3b',
}

const compact = new Intl.NumberFormat('ru-RU', { notation: 'compact', maximumFractionDigits: 1 })

/** Подписи осей: 0 / 950 / 12 тыс. / 1,5 млн */
export const fmtCompact = (v: number) => compact.format(v)
