import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy pour le backend principal (collecte-depots)
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
      // Proxy pour le service de prétraitement
      '/features': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        secure: false,
      },
      '/datasets': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        secure: false,
      },
      // Proxy pour le service ML
      '/train': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        secure: false,
      },
      '/predict': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        secure: false,
      },
      '/ml': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        secure: false,
      },
      // Proxy pour le moteur de priorisation
      '/prioritize': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        secure: false,
      },
      '/policies': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        secure: false,
      },
      // Proxy pour l'analyse statique
      '/analyze': {
        target: 'http://localhost:8005',
        changeOrigin: true,
        secure: false,
      },
      '/metrics': {
        target: 'http://localhost:8005',
        changeOrigin: true,
        secure: false,
      },
      '/smells': {
        target: 'http://localhost:8005',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
