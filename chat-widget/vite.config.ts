import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
    "process.env": {},
  },
  server: {
    port: 3001,
  },
  build: {
    lib: {
      entry: "src/main.tsx",
      name: "TmChatWidget",
      fileName: "tm-chat-widget",
      formats: ["es", "umd"],
    },
  },
});
