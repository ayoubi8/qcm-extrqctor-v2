export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        qcm: {
          bg: "#020617",
          surface: "#0f172a",
          raised: "#111827",
          muted: "#1e293b",
          border: "#1e293b",
          primary: "#22d3ee",
          secondary: "#2dd4bf",
          tertiary: "#f59e0b",
          success: "#34d399",
          danger: "#f87171"
        }
      },
      borderRadius: {
        qcm: "6px",
        "qcm-card": "8px"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"]
      }
    }
  },
  plugins: []
};
