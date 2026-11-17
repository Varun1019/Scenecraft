import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

const removeCrossorigin = () => ({
  name: "remove-crossorigin",
  transformIndexHtml(html: string) {
    return html.replace(/ crossorigin(?:="[^"]*")?/g, "");
  }
});

export default defineConfig({
  base: "./",
  plugins: [react(), removeCrossorigin()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        sidepanel: resolve(__dirname, "sidepanel.html"),
        background: resolve(__dirname, "src/background/service-worker.ts"),
        content: resolve(__dirname, "src/content/content-main.ts"),
        injected: resolve(__dirname, "src/injected/network-interceptor.ts")
      },
      output: {
        entryFileNames: (chunkInfo) => {
          if (chunkInfo.name === "background" || chunkInfo.name === "content" || chunkInfo.name === "injected") {
            return "[name].js";
          }
          return "assets/[name]-[hash].js";
        },
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name].[ext]"
      }
    }
  }
});
