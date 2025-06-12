import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath, URL } from 'node:url';
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";
import fs from 'fs';

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
  
  // Debug logging
  console.log('=== Vite Config Debug ===')
  console.log('Current directory:', process.cwd())
  console.log('Parent directory:', path.resolve(process.cwd(), '..'))
  console.log('Mode:', mode)
  console.log('Tunnel env AGENTS_SERVICE_URL:', tunnelEnv.AGENTS_SERVICE_URL)
  console.log('Parent env AGENTS_SERVICE_URL:', parentEnv.AGENTS_SERVICE_URL)
  console.log('Local env VITE_API_BASE_URL:', env.VITE_API_BASE_URL)
  
  // Check if we should use proxy (same domain) or direct URLs (cross-domain)
  const homepageUrl = tunnelEnv.HOMEPAGE_URL || parentEnv.HOMEPAGE_URL || ''
  const agentsUrl = tunnelEnv.AGENTS_SERVICE_URL || parentEnv.AGENTS_SERVICE_URL || 'http://localhost:8000'
  
  let shouldUseProxy = false
  if (homepageUrl && agentsUrl) {
    try {
      const homepageDomain = new URL(homepageUrl).hostname
      const agentsDomain = new URL(agentsUrl).hostname
      
      // Use proxy when:
      // 1. Both on localhost (development)
      // 2. Homepage is on a reserved domain and agents should be proxied through it
      // 3. Homepage is on amir.hirecj.ai (always use proxy for this domain)
      shouldUseProxy = (
        (homepageDomain === agentsDomain) || 
        (homepageDomain.includes('localhost') && agentsDomain.includes('localhost')) ||
        (homepageUrl.includes('amir.hirecj.ai')) // Always use proxy for amir.hirecj.ai
      )
    } catch {
      // Default to not using proxy on parse error
    }
  }
  
  // Merge with parent env taking precedence for service URLs
  // Tunnel env has highest priority
  const mergedEnv = {
    ...env,
    VITE_API_BASE_URL: shouldUseProxy ? '' : (env.VITE_API_BASE_URL || agentsUrl),
    VITE_AUTH_URL: env.VITE_AUTH_URL || tunnelEnv.AUTH_SERVICE_URL || parentEnv.AUTH_SERVICE_URL || 'http://localhost:8103',
    VITE_WS_BASE_URL: shouldUseProxy ? '' : (() => {
      const url = new URL(agentsUrl)
      return url.protocol === 'https:' ? `wss://${url.host}` : `ws://${url.host}`
    })(),
    VITE_PUBLIC_URL: env.VITE_PUBLIC_URL || tunnelEnv.VITE_PUBLIC_URL || tunnelEnv.HOMEPAGE_URL || parentEnv.HOMEPAGE_URL || ''
  }
  
  console.log('=== Vite Proxy Configuration ===')
  console.log('Homepage URL:', homepageUrl)
  console.log('Agents URL:', agentsUrl)
  console.log('Should use proxy:', shouldUseProxy)
  if (shouldUseProxy) {
    console.log('✅ PROXY MODE ACTIVE - All requests will be proxied through', homepageUrl)
    console.log('  API requests: /api/v1/* → ' + agentsUrl)
    console.log('  WebSocket: /ws/* → ' + agentsUrl)
  } else {
    console.log('❌ DIRECT MODE - Frontend will connect directly to backend')
  }
  console.log('=== Merged Environment ===')
  console.log('VITE_API_BASE_URL:', mergedEnv.VITE_API_BASE_URL || '(empty - using proxy)')
  console.log('VITE_AUTH_URL:', mergedEnv.VITE_AUTH_URL)
  console.log('VITE_WS_BASE_URL:', mergedEnv.VITE_WS_BASE_URL || '(empty - using proxy)')
  console.log('VITE_PUBLIC_URL:', mergedEnv.VITE_PUBLIC_URL)
  console.log('=========================')
  
  const isNgrok = mergedEnv.VITE_PUBLIC_URL?.includes('ngrok') || mergedEnv.VITE_PUBLIC_URL?.includes('hirecj.ai')
  
  return {
    plugins: [
      react()
    ],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL('./src', import.meta.url)),
        "@shared": fileURLToPath(new URL('./shared', import.meta.url)),
        "@assets": fileURLToPath(new URL('./attached_assets', import.meta.url)),
      },
    },
    root: process.cwd(),
    build: {
      outDir: path.resolve(process.cwd(), "dist/public"),
      emptyOutDir: true,
    },
    server: {
      port: 3456,
      host: true,
      proxy: {
        '/api/v1': {
          target: tunnelEnv.AGENTS_SERVICE_URL || parentEnv.AGENTS_SERVICE_URL || 'http://localhost:8000',  // hirecj-agents backend
          changeOrigin: true,
        },
        '/ws/chat': {
          target: tunnelEnv.AGENTS_SERVICE_URL || parentEnv.AGENTS_SERVICE_URL || 'http://localhost:8000',  // WebSocket proxy
          changeOrigin: true,
          ws: true
        },
        '/api': {
          target: 'http://localhost:3457',  // Express API server
          changeOrigin: true,
        }
      },
      // Fix HMR for ngrok
      hmr: isNgrok ? {
        protocol: 'wss',
        host: new URL(mergedEnv.VITE_PUBLIC_URL || 'http://localhost:3456').hostname,
        clientPort: 443
      } : true,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    },
    // Optimize dependencies properly
    optimizeDeps: {
      include: ['react', 'react-dom', 'react-dom/client'],
      force: false
    },
    // Define environment variables for the frontend
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(mergedEnv.VITE_API_BASE_URL),
      'import.meta.env.VITE_AUTH_URL': JSON.stringify(mergedEnv.VITE_AUTH_URL),
      'import.meta.env.VITE_WS_BASE_URL': JSON.stringify(mergedEnv.VITE_WS_BASE_URL),
      'import.meta.env.VITE_PUBLIC_URL': JSON.stringify(mergedEnv.VITE_PUBLIC_URL),
    }
  }
});
