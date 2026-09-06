import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05070a",
          900: "#0a0e14",
          850: "#0d121a",
          800: "#111826",
          700: "#1a2332",
          600: "#26324688",
        },
        line: "#1f2a3c",
        accent: {
          DEFAULT: "#4dd0c8",
          dim: "#2a6e68",
        },
        risk: {
          low: "#3fbf7f",
          medium: "#e0b23f",
          high: "#e0793f",
          critical: "#e0473f",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
