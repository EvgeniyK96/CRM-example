import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          // React и роутер — отдельным долгоживущим чанком: меняются редко, хорошо кешируются.
          // antd не группируем целиком — иначе таблицы и календари перестанут грузиться лениво со страницами.
          groups: [{ name: 'react', test: /node_modules[\\/](react|react-dom|react-router|scheduler)[\\/]/, priority: 2 }],
        },
      },
    },
  },
})
