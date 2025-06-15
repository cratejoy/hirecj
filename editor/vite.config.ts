import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

export default defineConfig(({ mode }) => {
  // Load env from current directory
  const env = loadEnv(mode, process.cwd(), '')
  
  // Also load env from parent directory for shared config
  const parentEnv = loadEnv(mode, path.resolve(process.cwd(), '..'), '')
  
  // Load .env.tunnel manually
  let tunnelEnv: Record<string, string> = {}
  const tunnelPath = path.resolve(process.cwd(), '..', '.env.tunnel')
  if (fs.existsSync(tunnelPath)) {
    const content = fs.readFileSync(tunnelPath, 'utf-8')
    content.split('\n').forEach(line => {
      if (line && !line.startsWith('#') && line.includes('=')) {
        const [key, value] = line.split('=', 2)
        tunnelEnv[key.trim()] = value.trim()
      }
    })
  }
  
  // Get editor URL from tunnel or env
  const editorUrl = tunnelEnv.EDITOR_URL || env.VITE_PUBLIC_URL || ''
  const editorBackendUrl = tunnelEnv.EDITOR_BACKEND_URL || env.VITE_EDITOR_BACKEND_URL || 'http://localhost:8001'
  
  // Merge environment variables
  const mergedEnv = {
    ...env,
    VITE_PUBLIC_URL: editorUrl,
    VITE_EDITOR_BACKEND_URL: editorBackendUrl
  }
  
  // Check if running through ngrok
  const isNgrok = editorUrl?.includes('ngrok') || editorUrl?.includes('.app')
  
  console.log('=== Editor Vite Config ===')
  console.log('Editor URL:', editorUrl || 'http://localhost:3458')
  console.log('Editor Backend URL:', editorBackendUrl)
  console.log('Is ngrok:', isNgrok)
  console.log('=========================')
  
  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3458,
      host: true, // This allows all hosts
      proxy: {
        '/api': {
          target: editorBackendUrl,
          changeOrigin: true,
        },
        '/ws': {
          target: editorBackendUrl,
          changeOrigin: true,
          ws: true
        }
      },
      // Fix HMR for ngrok
      hmr: isNgrok && editorUrl ? {
        protocol: 'wss',
        host: new URL(editorUrl).hostname,
        clientPort: 443
      } : true,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    },
    // Define environment variables for the frontend
    define: {
      'import.meta.env.VITE_PUBLIC_URL': JSON.stringify(mergedEnv.VITE_PUBLIC_URL),
      'import.meta.env.VITE_EDITOR_BACKEND_URL': JSON.stringify(mergedEnv.VITE_EDITOR_BACKEND_URL),
    }
  }
})