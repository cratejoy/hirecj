/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_EDITOR_BACKEND_URL: string
  readonly VITE_PUBLIC_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}