import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react(), tailwindcss()],
    // GitHub Pages 部署时需要设置 base path
    base: env.VITE_BASE_PATH || '/',
    server: {
      host: '0.0.0.0',
      port: 5173,
      allowedHosts: ['.loca.lt', '.serveousercontent.com'],
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      // 构建输出目录
      outDir: 'dist',
      // 生成 sourcemap 方便调试
      sourcemap: false,
    },
  }
})