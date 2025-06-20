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
  
  // Check if we should use proxy mode
  let shouldUseProxy = false
  if (editorUrl && editorBackendUrl) {
    try {
      const editorDomain = new URL(editorUrl).hostname
      const backendDomain = new URL(editorBackendUrl).hostname
      
      // Use proxy when:
      // 1. Both on localhost (development)
      // 2. Editor is on amir-editor.hirecj.ai (always use proxy for this domain)
      shouldUseProxy = (
        (editorDomain === backendDomain) || 
        (editorDomain.includes('localhost') && backendDomain.includes('localhost')) ||
        (editorUrl.includes('amir-editor.hirecj.ai')) // Always use proxy for reserved domain
      )
    } catch {
      // Default to not using proxy on parse error
    }
  }
  
  // Merge environment variables
  const mergedEnv = {
    ...env,
    VITE_PUBLIC_URL: editorUrl,
    VITE_EDITOR_BACKEND_URL: shouldUseProxy ? '' : editorBackendUrl
  }
  
  // Check if running through ngrok or reserved domain
  const isNgrok = editorUrl?.includes('ngrok') || editorUrl?.includes('.app') || editorUrl?.includes('hirecj.ai')
  
  console.log('=== Editor Vite Config ===')
  console.log('Editor URL:', editorUrl || 'http://localhost:3458')
  console.log('Editor Backend URL:', editorBackendUrl)
  console.log('Should use proxy:', shouldUseProxy)
  if (shouldUseProxy) {
    console.log('✅ PROXY MODE ACTIVE - All requests will be proxied through', editorUrl)
    console.log('  API requests: /api/* → ' + editorBackendUrl)
    console.log('  WebSocket: /ws/playground → ' + editorBackendUrl)
  } else {
    console.log('❌ DIRECT MODE - Frontend will connect directly to backend')
  }
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
        // Order matters - more specific paths first
        '/ws/playground': {
          target: tunnelEnv.EDITOR_BACKEND_URL || editorBackendUrl,
          changeOrigin: true,
          ws: true,
          secure: false,
          // Ensure headers are passed correctly for WebSocket upgrade
          headers: {
            'Origin': tunnelEnv.EDITOR_BACKEND_URL || editorBackendUrl
          },
          configure: (proxy, options) => {
            proxy.on('error', (err, req, res) => {
              console.error('[WS Proxy] ❌ Error:', err.message);
              console.error('[WS Proxy] Target:', options.target.href);
              console.error('[WS Proxy] Request URL:', req.url);
            });
            
            proxy.on('proxyReqWs', (proxyReq, req, socket, options, head) => {
              console.log('[WS Proxy] 🔄 WebSocket upgrade request');
              console.log('[WS Proxy] Target:', options.target.href);
              console.log('[WS Proxy] Client:', req.socket.remoteAddress);
              console.log('[WS Proxy] Headers:', req.headers);
              
              // Ensure proper headers for WebSocket upgrade
              proxyReq.setHeader('Origin', options.target.href);
            });
            
            proxy.on('open', (proxySocket) => {
              console.log('[WS Proxy] ✅ WebSocket opened');
              
              // Removed data logging to avoid terminal spam
              // proxySocket.on('data', (data) => {
              //   console.log('[WS Proxy] 📤 Data to backend:', data.toString().substring(0, 200));
              // });
            });
            
            proxy.on('close', (res, socket, head) => {
              console.log('[WS Proxy] 🔒 WebSocket closed');
            });
            
            proxy.on('proxyRes', (proxyRes, req, res) => {
              console.log('[WS Proxy] 📥 Response:', proxyRes.statusCode, proxyRes.statusMessage);
            });
          }
        },
        '/api': {
          target: tunnelEnv.EDITOR_BACKEND_URL || editorBackendUrl,
          changeOrigin: true,
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