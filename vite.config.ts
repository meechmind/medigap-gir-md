import path from 'path';
import { defineConfig } from 'vite'; // Removed loadEnv
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoName = process.env.GITHUB_REPOSITORY ? process.env.GITHUB_REPOSITORY.split('/')[1] : 'medigap-gir-md';

export default defineConfig({
  server: {
    port: 3000,
    host: '0.0.0.0',
  },
  base: `/${repoName}/`,
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    }
  }
});
