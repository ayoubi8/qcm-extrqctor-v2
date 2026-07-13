export const designTokens = {
  color: {
    background: "#020617",
    surface: "#0f172a",
    surfaceRaised: "#111827",
    surfaceMuted: "#1e293b",
    border: "#1e293b",
    borderStrong: "#334155",
    text: "#f8fafc",
    textMuted: "#94a3b8",
    primary: "#22d3ee",
    primaryStrong: "#06b6d4",
    secondary: "#2dd4bf",
    tertiary: "#f59e0b",
    success: "#34d399",
    danger: "#f87171"
  },
  radius: {
    sm: "4px",
    md: "6px",
    lg: "8px"
  },
  shell: {
    sidebarWidth: "256px",
    topbarHeight: "64px",
    terminalHeight: "224px"
  },
  typography: {
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    monoFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"
  }
} as const;

export type DesignTokens = typeof designTokens;
