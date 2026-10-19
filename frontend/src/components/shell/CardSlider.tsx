import { CloseOutlined } from '@ant-design/icons'
import { Drawer, Spin } from 'antd'
import { Suspense, type ReactNode } from 'react'
import { SHELL } from '../../theme'

interface Props {
  open: boolean
  onClose: () => void
  children: ReactNode
}

/**
 * Слайдер в стиле Битрикс24: карточка выезжает справа поверх списка, список остаётся виден под ней.
 * Закрывается «язычком» слева от панели, кликом по затемнению или Esc.
 */
export default function CardSlider({ open, onClose, children }: Props) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      placement="right"
      size="min(1120px, calc(100vw - 56px))"
      closable={false}
      rootClassName="card-slider"
      styles={{ body: { background: SHELL.workarea } }}
      drawerRender={(panel) => (
        <>
          <button type="button" className="card-slider-close" onClick={onClose} aria-label="Закрыть карточку" title="Закрыть (Esc)">
            <CloseOutlined />
          </button>
          {panel}
        </>
      )}
    >
      <Suspense fallback={<Spin style={{ display: 'block', margin: '48px auto' }} />}>{children}</Suspense>
    </Drawer>
  )
}
