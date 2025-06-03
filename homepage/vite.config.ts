import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";

export default defineConfig({
  plugins: [
    react()
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),
      "@shared": path.resolve(import.meta.dirname, "shared"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets"),
    },
  },
  root: path.resolve(import.meta.dirname),
  build: {
    outDir: path.resolve(import.meta.dirname, "dist/public"),
    emptyOutDir: true,
  },
  server: {
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
    // Force HMR to always use WebSocket
    hmr: {
      overlay: true,
      protocol: 'ws',
      host: 'localhost'
    },
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
});
