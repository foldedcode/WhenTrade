/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_BASE_URL: string
  readonly VITE_SUPABASE_URL: string
  readonly VITE_SUPABASE_ANON_KEY: string
  readonly VITE_APPKIT_PROJECT_ID: string
  readonly VITE_WEB3AUTH_CLIENT_ID: string
  readonly VITE_WEB3AUTH_NETWORK: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}