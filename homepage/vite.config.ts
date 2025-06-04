import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath, URL } from 'node:url';
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";

export default defineConfig(({ mode }) => {
  // Load env from current directory
  const env = loadEnv(mode, process.cwd(), '')
  
  // Also load env from parent directory for shared config
  const parentEnv = loadEnv(mode, path.resolve(process.cwd(), '..'), '')
  
  // Load tunnel env if it exists (highest priority)
  const tunnelEnv = loadEnv(mode, path.resolve(process.cwd(), '..'), 'tunnel')
  
  // Merge with parent env taking precedence for service URLs
  // Tunnel env has highest priority
  const mergedEnv = {
    ...env,
    VITE_API_BASE_URL: env.VITE_API_BASE_URL || tunnelEnv.AGENTS_SERVICE_URL || parentEnv.AGENTS_SERVICE_URL || 'http://localhost:8000',
    VITE_AUTH_URL: env.VITE_AUTH_URL || tunnelEnv.AUTH_SERVICE_URL || parentEnv.AUTH_SERVICE_URL || 'http://localhost:8103',
    VITE_WS_BASE_URL: env.VITE_WS_BASE_URL || (tunnelEnv.AGENTS_SERVICE_URL ? `wss://${new URL(tunnelEnv.AGENTS_SERVICE_URL).host}` : `ws://${new URL(parentEnv.AGENTS_SERVICE_URL || 'http://localhost:8000').host}`),
    VITE_PUBLIC_URL: env.VITE_PUBLIC_URL || tunnelEnv.VITE_PUBLIC_URL || parentEnv.HOMEPAGE_URL || ''
  }
  
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
