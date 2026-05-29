import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Monaco editor React wrapper — lazy-loaded via dynamic import in SkillEditorPage
          "monaco-react": ["@monaco-editor/react"],
          vendor: ["react", "react-dom"],
          query: ["@tanstack/react-query", "@tanstack/react-router"],
          charts: ["recharts"],
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:7010",
        changeOrigin: true,
      },
      "/auth": {
        target: "http://127.0.0.1:7010",
        changeOrigin: true,
      },
      "/internal": {
        target: "http://127.0.0.1:7010",
        changeOrigin: true,
      },
    },
  },
});
