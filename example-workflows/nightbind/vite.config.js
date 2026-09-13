import { defineConfig } from "vite";
// Polling also catches atomic file replacements in the Windows agent workspace.
export default defineConfig({
  server: { watch: { usePolling: true, interval: 300 } },
});
