import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const getBase = () => {
  if (process.env.GITHUB_REPOSITORY) {
    const name = process.env.GITHUB_REPOSITORY.split('/')[1];
    return `/${name}/`;
  }
  return '/';
};

export default defineConfig({
  base: getBase(),
  plugins: [react()],
});
