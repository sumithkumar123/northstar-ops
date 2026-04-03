import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/inventory': 'http://localhost:8000',
      '/sales': 'http://localhost:8000',
      '/ai': 'http://localhost:8000',
    }
  }
})
