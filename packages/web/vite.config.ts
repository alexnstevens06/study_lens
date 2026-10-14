import react from '@vitejs/plugin-react';
import { copyFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, type Plugin } from 'vite';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

function copyConfig(): Plugin {
  return {
    name: 'copy-study-lens-config',
    closeBundle() {
      copyFileSync(resolve(root, 'config.json'), resolve(dirname(fileURLToPath(import.meta.url)), 'dist/config.json'));
    },
  };
}

export default defineConfig({
  base: './',
  plugins: [react(), copyConfig()],
  resolve: {
    alias: {
      '@study-lens/core': resolve(root, 'packages/core/src/index.ts'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/context': 'http://127.0.0.1:8787',
      '/prompts': 'http://127.0.0.1:8787',
      '/config.json': 'http://127.0.0.1:8787',
    },
  },
});
