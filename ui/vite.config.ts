import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server is bound to all interfaces so the Cloud preview can reach it.
// Extra preview hostnames come from __VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS
// instead of being hard-coded into this file.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: "0.0.0.0",
  },
  build: {
    target: "chrome110",
    outDir: "dist",
    sourcemap: false,
  },
});
