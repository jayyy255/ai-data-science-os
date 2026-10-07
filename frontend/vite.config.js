import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: '127.0.0.1', proxy: { '/api': process.env.AIDSO_BACKEND_URL || 'http://127.0.0.1:8000' } },
})
