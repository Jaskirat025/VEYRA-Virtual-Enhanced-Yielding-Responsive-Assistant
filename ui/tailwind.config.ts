import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        gunmetal: {
          700: "#2a3439",
          800: "#1e262a",
          900: "#161c1f",
        },
        silver: {
          100: "#e4e8eb",
          300: "#c5cbd0",
          400: "#9aa3aa",
          500: "#8b949b",
        },
        accent: {
          DEFAULT: "#ff5a1f",
          strong: "#e64a12",
          soft: "rgba(255, 90, 31, 0.12)",
          ink: "#161c1f",
        },
      },
      fontFamily: {
        display: ["Rajdhani", "Segoe UI", "sans-serif"],
        body: ["Inter", "Segoe UI", "Microsoft YaHei UI", "sans-serif"],
        mono: ["JetBrains Mono", "Cascadia Mono", "monospace"],
      },
      borderRadius: {
        panel: "10px",
      },
      transitionDuration: {
        150: "150ms",
        220: "220ms",
        300: "300ms",
      },
      maxWidth: {
        content: "1080px",
      },
    },
  },
  plugins: [],
} satisfies Config;
