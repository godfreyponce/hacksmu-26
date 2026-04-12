/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // EchoMap dark-green theme
        background: "var(--bg)",
        foreground: "var(--ink)",
        card: {
          DEFAULT: "rgba(8, 12, 9, 0.6)",
          foreground: "var(--ink)",
        },
        primary: {
          DEFAULT: "var(--leaf-strong)",
          foreground: "#042f20",
        },
        secondary: {
          DEFAULT: "rgba(126, 200, 160, 0.15)",
          foreground: "var(--leaf)",
        },
        muted: {
          DEFAULT: "rgba(232, 237, 229, 0.1)",
          foreground: "var(--muted)",
        },
        accent: {
          DEFAULT: "var(--leaf)",
          foreground: "#042f20",
        },
        destructive: {
          DEFAULT: "#f85149",
          foreground: "#fff",
        },
        border: "var(--border)",
        input: "var(--border)",
        ring: "var(--leaf)",
        // Elephant sound category colors
        rumble: "#7ec8a0",
        bark: "#f59e0b",
        roar: "#ef4444",
        trumpet: "#3b82f6",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "ping-slow": "ping 2s cubic-bezier(0, 0, 0.2, 1) infinite",
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
}
