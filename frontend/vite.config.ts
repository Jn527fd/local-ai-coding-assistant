import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import path from "node:path"
import { defineConfig } from "vite"

export default defineConfig({
  base: "/",
  build: {
    sourcemap: false,
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: parseInt(process.env.PORT || "5173", 10),
    strictPort: true,
  },
  preview: {
    host: "0.0.0.0",
    port: parseInt(process.env.PORT || "5173", 10),
  },
})
