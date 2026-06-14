import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server on :5173 (CORS-allowed by the FastAPI backend).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
