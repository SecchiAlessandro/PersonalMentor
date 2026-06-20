import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
// Built as a sub-app of the PersonalMentor newspaper. `base: './'` keeps asset
// URLs relative so the build works under GitHub Pages at /PersonalMentor/web/coach/,
// and it is embedded via an <iframe> in the newspaper's "Personal Coach" tab.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  build: {
    outDir: '../output/web/coach',
    emptyOutDir: true,
  },
})
