import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath, URL } from 'node:url';
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isNgrok = env.VITE_PUBLIC_URL?.includes('ngrok') || env.VITE_PUBLIC_URL?.includes('hirecj.ai')
  
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
          target: 'http://localhost:8000',  // hirecj-agents backend
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
        host: new URL(env.VITE_PUBLIC_URL || 'http://localhost:3456').hostname,
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
  }
});
