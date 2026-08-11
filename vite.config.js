import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  root: resolve(import.meta.dirname, "app-ui"),
  build: {
    outDir: resolve(import.meta.dirname, "app/static-build"),
    emptyOutDir: true,
    sourcemap: false,
  },
});
