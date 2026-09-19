/// <reference types="vite/client" />
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
      manifest: {
        name: "Suno Content",
        short_name: "Suno Content",
        description: "Matriz de Células, Laudos e filas humanas do Suno Content.",
        theme_color: "#0f172a",
        background_color: "#0f172a",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icone.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
          { src: "icone.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
