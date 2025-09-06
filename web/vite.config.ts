import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

export default defineConfig({
  plugins: [
    vue(),
    nodePolyfills({
      // Whether to polyfill `node:` protocol imports.
      protocolImports: true,
      globals: {
        Buffer: true,
        global: true,
        process: true,
      },
      // 包含 fs 模块
      include: ['fs', 'stream', 'util', 'events'],
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  define: {
    global: 'globalThis',
    'process.env': {},
    __HMR_CONFIG_NAME__: JSON.stringify('default')
  },
  server: {
    port: 3000,
    host: true,
    headers: {
      // 解决 Web3Auth 弹窗的 CORS 问题
      'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
      'Cross-Origin-Embedder-Policy': 'unsafe-none',
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    commonjsOptions: {
      transformMixedEsModules: true
    },
    target: 'esnext',
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'esnext',
      define: {
        global: 'globalThis',
      },
    },
    include: [
      'buffer',
      'process',
      '@web3auth/no-modal',
      '@web3auth/base',
      '@web3auth/ethereum-provider',
      '@web3auth/auth-adapter',
      '@web3auth/modal',
      'end-of-stream',
      'pump',
      'once'
    ],
  },
})