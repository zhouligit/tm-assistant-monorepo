import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
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
