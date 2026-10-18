import type { ThemeConfig } from 'antd'

/**
 * Оформление в стиле Битрикс24: фон-обои, тёмное полупрозрачное меню, светлая рабочая область.
 * Акцент — голубой #0b78b8: белый текст на нём даёт контраст 4.78:1 (WCAG AA),
 * фирменный светло-голубой Битрикс24 (#2fc6f6) с белым текстом — лишь 1.99:1.
 */
export const ACCENT = '#0b78b8'

export const WALLPAPER = [
  'radial-gradient(1200px 600px at 15% 10%, rgba(255,255,255,0.18), transparent 60%)',
  'radial-gradient(900px 500px at 85% 90%, rgba(91,206,233,0.35), transparent 60%)',
  'linear-gradient(135deg, #0a3561 0%, #12609b 45%, #2390c4 100%)',
].join(', ')

export const SHELL = {
  sider: 'rgba(3, 18, 36, 0.38)',
  workarea: '#eef2f4',
  titleColor: '#ffffff',
}

export const theme: ThemeConfig = {
  token: {
    colorPrimary: ACCENT,
    colorLink: ACCENT,
    borderRadius: 8,
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Layout: { bodyBg: 'transparent', headerBg: 'transparent', siderBg: 'transparent', headerHeight: 60, headerPadding: '0 24px' },
    Menu: {
      darkItemBg: 'transparent',
      darkSubMenuItemBg: 'transparent',
      darkPopupBg: '#0d2f52',
      darkItemColor: 'rgba(255,255,255,0.82)',
      darkItemHoverColor: '#ffffff',
      darkItemHoverBg: 'rgba(255,255,255,0.10)',
      darkItemSelectedBg: 'rgba(255,255,255,0.20)',
      darkItemSelectedColor: '#ffffff',
      darkGroupTitleColor: 'rgba(255,255,255,0.55)',
      itemBorderRadius: 8,
      itemMarginInline: 8,
    },
    Card: { borderRadiusLG: 12 },
  },
}
