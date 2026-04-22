import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/ws': {
        target: 'ws://youtu-agent:8848',
        ws: true,
      },
      '/oj-api': {
        target: 'http://oj-backend:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/oj-api/, ''),
      },
    },
  },
})
