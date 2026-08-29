import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
  root: "web",
  plugins: [react()],
  worker: { format: "es" },
  server: {
    fs: { allow: ["..", "../.."] },
    ...(process.env.ORCHFLOWS_UI_API_ORIGIN ? {
      proxy: { "/api": process.env.ORCHFLOWS_UI_API_ORIGIN }
    } : {})
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    manifest: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        assetFileNames: "assets/[name]-[hash][extname]",
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js"
      }
    }
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    setupFiles: ["src/test-setup.ts"]
  }
});
