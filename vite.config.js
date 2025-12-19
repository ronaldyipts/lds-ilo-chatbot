import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 若你後端是 Flask 跑在 http://localhost:5000
// 前端 dev server 跑在 http://localhost:5173
// 這裡用 proxy 避免 CORS 問題（推薦）
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0", // 允許通過 IP 地址訪問
    port: 5173,
    strictPort: false, // 如果端口被佔用，嘗試下一個可用端口
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
        secure: false
      }
    }
  }
});