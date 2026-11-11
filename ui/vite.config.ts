import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server is bound to all interfaces so the Cloud preview can reach it.
// Extra preview hostnames come from __VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS
// instead of being hard-coded into this file. Vite 5 does not read this
// variable itself, so pass the exact hosts through to allowedHosts.
const previewHosts = (process.env.__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS ?? "")
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: "0.0.0.0",
    allowedHosts: previewHosts.length > 0 ? previewHosts : undefined,
  },
  build: {
    target: "chrome110",
    outDir: "dist",
    sourcemap: false,
  },
});
