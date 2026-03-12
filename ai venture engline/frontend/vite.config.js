import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/upload': 'http://localhost:8000',
      '/stream-analysis': 'http://localhost:8000',
      '/memo': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
    },
  },
})
