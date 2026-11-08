import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The build is served by FastAPI (app/server.py) from dist/, with assets under /assets. In development, `npm run dev`
// proxies the API to a running app on port 8000.
export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist', assetsDir: 'assets', sourcemap: false },
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
});
