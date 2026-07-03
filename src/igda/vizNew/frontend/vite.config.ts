import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(__dirname, "../static/dna-helix"),
    emptyOutDir: true,
    lib: {
      entry: path.resolve(__dirname, "src/main.tsx"),
      name: "IgdaDnaHelix",
      formats: ["iife"],
      fileName: () => "dna-helix.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});
