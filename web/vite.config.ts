/// <reference types="vite/client" />
/// <reference types="vitest/config" />
// ADR 0005: FastAPI serve `web/dist`; em dev, o proxy evita CORS contra a API na 8000.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  base: "/",
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icone.svg"],
      // As prévias do carrossel abrem a API num iframe: navegação para /api nunca cai no index.html.
      workbox: { navigateFallbackDenylist: [/^\/api\//] },
      manifest: {
        name: "Suno Content",
        short_name: "Suno Content",
        description: "Notícias do mercado em texto analítico, carrossel e roteiro de vídeo.",
        theme_color: "#1b1b1b",
        background_color: "#1b1b1b",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icone.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
          { src: "icone.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
        ],
      },
    }),
  ],
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
  server: {
    proxy: {
      "/api": {
        target: process.env.SUNO_API ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
