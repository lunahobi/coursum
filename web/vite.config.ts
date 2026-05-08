import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  },
  test: {
    environment: "jsdom",
    setupFiles: [fileURLToPath(new URL("./src/test/setup.ts", import.meta.url))],
    include: ["src/**/*.{test,spec}.{ts,tsx,js,jsx}"],
    exclude: ["e2e/**", "node_modules/**", "dist/**"]
  }
});
