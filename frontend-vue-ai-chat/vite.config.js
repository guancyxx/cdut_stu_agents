import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue({
      // Disable vue inspector to avoid template parsing errors
      template: {
        compilerOptions: {
          // Disable某些可能导致问题的特性
          whitespace: 'preserve'
        }
      }
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/ws': {
        target: 'ws://ai-agent-lite:8848',
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
