import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const repoRoot = fileURLToPath(new URL('..', import.meta.url))

export function devServerConfig(mode, envDir = repoRoot) {
  // Load only server-side API settings; never expose database credentials to React.
  const env = loadEnv(mode, envDir, 'API_')
  return {
    port: 5173,
    strictPort: true,
    allowedHosts: process.env.TUNNEL_HOST?.split(',').map((host) => host.trim()).filter(Boolean) || [],
    proxy: {
      '/api': {
        target: env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  }
}

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  resolve: { alias: { '@': resolve(fileURLToPath(new URL('.', import.meta.url)), 'src') } },
  server: devServerConfig(mode),
}))
